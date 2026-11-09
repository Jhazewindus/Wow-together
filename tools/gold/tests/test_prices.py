"""Price source precedence, expiry, confidence, and optional scan bridge."""
import unittest

from test_skeleton import ROOT, load_gold
from test_addon import Client


def price_client():
    client = Client(quests=(), default_guide=True)
    client.lua.execute('''
        serverTime = 100000
        faction = "Alliance"
        itemQuality, vendorPrice = {}, {}
        GetServerTime = function() return serverTime end
        UnitFactionGroup = function() return faction end
        C_Item = {GetItemInfo = function(id)
            return "Item", nil, itemQuality[id], nil, nil, nil, nil, nil, nil, nil, vendorPrice[id]
        end}
    ''')
    private = load_gold(client)
    source = (ROOT / "WowTogether_Gold" / "GoldPrices.lua").read_text()
    client.lua.execute("assert(loadstring(...))(select(2, ...))", source, "WowTogether_Gold", private)
    return client, private.GoldPrices, private


class GoldPriceTests(unittest.TestCase):
    def test_tsm_precedes_scan_and_vendor_without_storing_tsm_data(self):
        client, prices, private = price_client()
        client.lua.execute('''
            vendorPrice[42] = 50; itemQuality[42] = 2
            TSM_API = {
                ToItemString = function(item) return item end,
                GetCustomPriceValue = function(method, item)
                    if method == "DBMarket" and item == "i:42" then return 120 end
                end,
            }
        ''')
        self.assertTrue(prices.StoreQuote(42, client.lua.table_from(
            {'minBuyout': 180, 'median': 200, 'count': 4, 'complete': True})))
        quote = prices.Price(42)
        self.assertEqual((quote.copper, quote.source, quote.confidence), (120, 'TSM DBMarket', .7))
        self.assertEqual(quote.sampleSize, 'unknown')
        self.assertIsNone(quote.age)
        self.assertEqual(quote.provenance.method, 'DBMarket')
        self.assertIsNone(private.db.prices['Test Realm:Alliance'][42].source)

    def test_tsm_alternates_and_vendor_floor(self):
        client, prices, _ = price_client()
        client.lua.execute('''
            vendorPrice[42] = 50; itemQuality[42] = 2
            TSM_API = {
                ToItemString = function(item) return item end,
                GetCustomPriceValue = function(method)
                    if method == "DBMinBuyout" then return 75 end
                end,
            }
        ''')
        self.assertEqual(prices.Price(42).source, 'TSM DBMinBuyout')
        client.lua.execute('TSM_API.GetCustomPriceValue = function() return 40 end')
        floor = prices.Price(42)
        self.assertEqual((floor.copper, floor.source, floor.confidence), (50, 'vendor floor', 1))
        client.lua.execute('itemQuality[42] = 0; TSM_API.GetCustomPriceValue = function() return 500 end')
        grey = prices.Price(42)
        self.assertEqual((grey.copper, grey.source, grey.confidence), (50, 'vendor', 1))

    def test_scan_store_age_expiry_scope_and_vendor_fallback(self):
        client, prices, private = price_client()
        client.lua.execute('vendorPrice[42] = 30; itemQuality[42] = 2')
        self.assertTrue(prices.StoreQuote(42, client.lua.table_from(
            {'minBuyout': 90, 'median': 100, 'count': 8, 'complete': True})))
        fresh = prices.Price(42)
        self.assertEqual((fresh.copper, fresh.confidence, fresh.sampleSize), (100, 1, 8))
        self.assertEqual(fresh.age, 0)
        client.lua.execute('serverTime = serverTime + 7 * 3600')
        self.assertEqual(prices.Price(42).confidence, .7)
        client.lua.execute('faction = "Horde"')
        self.assertEqual((prices.Price(42).source, prices.Price(42).confidence), ('vendor', .3))
        client.lua.execute('faction = "Alliance"; serverTime = 100000 + 24 * 3600')
        self.assertEqual(prices.Price(42).source, 'vendor')
        self.assertIsNone(private.db.prices['Test Realm:Alliance'][42])

    def test_missing_tsm_and_scanner_are_safe_and_scan_is_feature_detected(self):
        client, prices, private = price_client()
        self.assertEqual(prices.StartScan(client.lua.table_from([42]))[0], False)
        client.lua.execute('''
            _G.WowTogetherModuleAPI.StartFarmCandidateScan = function(ids, onQuote)
                assert(#ids == 1 and ids[1] == 42)
                onQuote(42, {minBuyout=80, median=90, count=3, complete=true})
                return true
            end
        ''')
        self.assertTrue(prices.StartScan(client.lua.table_from([42, 42])))
        self.assertEqual(prices.Price(42).copper, 90)
        self.assertEqual(private.db.prices['Test Realm:Alliance'][42].count, 3)

    def test_gold_prices_command_reports_source_confidence_and_sample(self):
        client, prices, _ = price_client()
        client.lua.execute('vendorPrice[42] = 50; itemQuality[42] = 0')
        client.lua.globals().SlashCmdList.WOWTOGETHER('gold prices 42')
        logs = client.lua.globals().logs
        output = logs[len(logs)]
        self.assertIn('vendor', output)
        self.assertIn('confidence 100%', output)
        self.assertIn('samples 1', output)
        client.lua.globals().SlashCmdList.WOWTOGETHER('gold prices')
        self.assertIn('farm AH scan available', logs[len(logs)])


if __name__ == '__main__':
    unittest.main()
