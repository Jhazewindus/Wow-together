"""Price precedence and the public core auction quote boundary."""
import unittest

from test_skeleton import ROOT, load_gold
from test_addon import Client


def price_client():
    client = Client(quests=(), default_guide=True)
    client.lua.execute('''
        faction = "Alliance"
        itemQuality, vendorPrice, coreQuotes = {}, {}, {}
        UnitFactionGroup = function() return faction end
        C_Item = {GetItemInfo = function(id)
            return "Item", nil, itemQuality[id], nil, nil, nil, nil, nil, nil, nil, vendorPrice[id]
        end}
        WowTogetherModuleAPI.AuctionQuote = function(id)
            local quote = coreQuotes[id]
            if quote then return quote.copper, quote.age end
        end
    ''')
    private = load_gold(client)
    source = (ROOT / "WowTogether_Gold" / "GoldPrices.lua").read_text()
    client.lua.execute("assert(loadstring(...))(select(2, ...))", source, "WowTogether_Gold", private)
    return client, private.GoldPrices, private


class GoldPriceTests(unittest.TestCase):
    def test_core_auction_quote_precedes_vendor_and_reports_freshness(self):
        client, prices, _ = price_client()
        client.lua.execute('vendorPrice[42]=50; itemQuality[42]=2; coreQuotes[42]={copper=120,age=3600}')
        quote = prices.Price(42)
        self.assertEqual((quote.copper, quote.source, quote.age, quote.confidence),
                         (120, 'core auction quote', 3600, 1))
        self.assertEqual(quote.sampleBasis, 'saved core auction scan')

    def test_vendor_is_used_when_the_core_has_no_quote(self):
        client, prices, _ = price_client()
        client.lua.execute('vendorPrice[42]=50; itemQuality[42]=2')
        quote = prices.Price(42)
        self.assertEqual((quote.copper, quote.source, quote.confidence), (50, 'vendor', .3))
        client.lua.execute('coreQuotes[42]={copper=10,age=10}')
        self.assertEqual(prices.Price(42).copper, 10)  # The brief says a quote wins even below vendor.

    def test_invalid_and_unavailable_prices_return_nil(self):
        _, prices, _ = price_client()
        self.assertIsNone(prices.Price(-1))
        self.assertIsNone(prices.Price(42))

    def test_scanner_is_optional_and_core_quote_is_read_back(self):
        client, prices, _ = price_client()
        self.assertFalse(prices.StartScan(client.lua.table_from([42]))[0])
        client.lua.execute('''
            _G.WowTogetherModuleAPI.StartFarmCandidateScan = function(ids, onQuote)
                assert(#ids == 1 and ids[1] == 42)
                onQuote(42, {minBuyout=80, median=90, count=3, complete=true})
                coreQuotes[42] = {copper=90, age=0}
                return true
            end
        ''')
        self.assertTrue(prices.StartScan(client.lua.table_from([42, 42])))
        quote = prices.Price(42)
        self.assertEqual((quote.copper, quote.source), (90, 'core auction quote'))

    def test_price_command_and_probe_state_the_source(self):
        client, prices, _ = price_client()
        client.lua.execute('vendorPrice[42]=50; itemQuality[42]=0; coreQuotes[42]={copper=75,age=2}')
        client.lua.globals().SlashCmdList.WOWTOGETHER('gold prices 42')
        logs = client.lua.globals().logs
        output = logs[len(logs)]
        self.assertIn('core auction quote', output)
        self.assertIn('75 copper', output)
        client.lua.globals().SlashCmdList.WOWTOGETHER('gold prices')
        self.assertIn('core auction quote, then vendor', logs[len(logs)])
        report = []
        prices.Probe(lambda text: report.append(text))
        self.assertIn('core auction quote', report[0])


if __name__ == '__main__':
    unittest.main()
