"""A scan of the whole auction house: a category at a time, materials first, one lowest price per item."""
import unittest

from test_addon import Client


HOUSE = r'''
    local ns = ...
    function GetRealmName() return "Testrealm" end
    function UnitFactionGroup() return "Horde", "Horde" end
    ns.profile.faction = "Horde"
    clock = 1795000000
    function GetServerTime() return clock end
    uptime = 100
    function GetTime() return uptime end
    atAuction, throttleReady = true, true
    ns.AuctionHouseVisible = function() return atAuction end
    queries, moreRequests = {}, 0
    -- class ID -> pages of listings: {itemID, minPrice, totalQuantity}
    house = {
        [7] = {{{2771, 310, 40}, {2775, 2400, 6}}, {{2771, 290, 12}, {3356, 420, 30}}},      -- trade goods, two pages
        [0] = {{{6359, 90, 200}}},                                                            -- consumables
        [2] = {{{15210, 45000, 1}}},                                                          -- weapons, last
    }
    local current, page
    local function rows(list)
        local out = {}
        for _, row in ipairs(list or {}) do
            out[#out + 1] = {itemKey = {itemID = row[1], itemLevel = 0, itemSuffix = 0}, minPrice = row[2], totalQuantity = row[3]}
        end
        return out
    end
    C_AuctionHouse = {
        IsThrottledMessageSystemReady = function() return throttleReady end,
        SendBrowseQuery = function(query)
            current, page = query.itemClassFilters[1].classID, 1
            queries[#queries + 1] = current
        end,
        GetBrowseResults = function() return rows(house[current] and house[current][1]) end,
        HasFullBrowseResults = function() return not (house[current] and house[current][page + 1]) end,
        RequestMoreBrowseResults = function() moreRequests = moreRequests + 1; page = page + 1 end,
    }
    function answer()                  -- the game delivers the page that was asked for
        if page == 1 then ns.frame.OnEvent(ns.frame, "AUCTION_HOUSE_BROWSE_RESULTS_UPDATED")
        else ns.frame.OnEvent(ns.frame, "AUCTION_HOUSE_BROWSE_RESULTS_ADDED", rows(house[current][page])) end
    end
    progress = {}
    function startScan() return ns.StartFullPriceScan(function(update) progress[#progress + 1] = update end) end
'''


def house():
    c = Client(quests=(), default_guide=True, party_mode='never')
    c.drain()
    c.lua.execute(HOUSE, c.ns)
    return c


def run(c, limit=60):
    """Answers every request until the scan ends."""
    g = c.lua.globals()
    for _ in range(limit):
        if not c.ns.FullPriceScanRunning():
            break
        g.answer(); c.drain()


class OrderAndResultTests(unittest.TestCase):
    def test_materials_are_scanned_first_and_weapons_last(self):
        c = house(); g = c.lua.globals()
        self.assertTrue(g.startScan())
        run(c)
        asked = list(g.queries.values())
        self.assertEqual(asked[:4], [7, 0, 5, 3])                                   # Trade goods, consumables, reagents, gems.
        self.assertEqual(asked[-2:], [4, 2])                                        # Armour, then weapons.
        self.assertEqual(len(asked), 12)

    def test_every_page_of_a_category_is_read(self):
        c = house(); g = c.lua.globals()
        g.startScan(); run(c)
        self.assertEqual(g.moreRequests, 1)                                         # Trade goods had a second page.
        self.assertEqual(c.ns.BrowseQuote(3356).unitPrice, 420)                     # An item only on that second page.

    def test_an_item_keeps_its_lowest_price_and_all_its_quantity(self):
        c = house(); g = c.lua.globals()
        g.startScan(); run(c)
        quote = c.ns.BrowseQuote(2771)
        self.assertEqual((quote.unitPrice, quote.quantity), (290, 52))              # Listed twice: 310 and 290.
        self.assertFalse(quote.complete)                                            # A lowest price is not an order book.

    def test_the_end_reports_what_was_priced(self):
        c = house(); g = c.lua.globals()
        g.startScan(); run(c)
        last = list(g.progress.values())[-1]
        self.assertEqual((last.running, last.completed, last['items']), (False, True, 5))
        self.assertEqual(last.message, 'Done: 5 items priced from 6 listings.')
        self.assertEqual(c.ns.BrowsePriceCount(), 5)


class LookupTests(unittest.TestCase):
    def test_any_price_lookup_falls_back_to_the_whole_house_scan(self):
        c = house(); g = c.lua.globals()
        self.assertIsNone(c.ns.AuctionQuote(6359))
        g.startScan(); run(c)
        self.assertEqual(c.ns.AuctionQuote(6359).unitPrice, 90)
        api = g.WowTogetherModuleAPI
        self.assertEqual(api.AuctionQuote(6359)[0], 90)                             # What the gold package reads.

    def test_a_fresh_order_book_for_an_item_is_still_preferred(self):
        c = house(); g = c.lua.globals()
        g.startScan(); run(c)
        c.lua.execute('local ns = ...; ns.marketQuotes[2771] = {unitPrice = 275, time = clock - 60, offers = {{275, 5}}, complete = true}', c.ns)
        self.assertEqual(c.ns.AuctionQuote(2771).unitPrice, 275)

    def test_prices_expire_after_three_days(self):
        c = house(); g = c.lua.globals()
        g.startScan(); run(c)
        c.lua.execute('clock = clock + 2 * 86400')
        self.assertIsNotNone(c.ns.BrowseQuote(2771))
        c.lua.execute('clock = clock + 2 * 86400')
        self.assertIsNone(c.ns.BrowseQuote(2771))

    def test_a_rescan_replaces_an_items_old_price_even_if_it_went_up(self):
        c = house(); g = c.lua.globals()
        g.startScan(); run(c)
        c.lua.execute('house[7] = {{{2771, 500, 3}}}; clock = clock + 3600')
        g.startScan(); run(c)
        quote = c.ns.BrowseQuote(2771)
        self.assertEqual((quote.unitPrice, quote.quantity), (500, 3))


class PacingTests(unittest.TestCase):
    def test_nothing_is_sent_while_the_game_says_wait(self):
        c = house(); g = c.lua.globals()
        g.throttleReady = False
        g.startScan()
        for _ in range(5):
            c.lua.eval('function() local list = timers; timers = {}; for _, cb in ipairs(list) do cb() end end')()
        self.assertEqual(len(list(g.queries.values())), 0)
        g.throttleReady = True
        c.drain()
        self.assertEqual(list(g.queries.values()), [7])

    def test_closing_the_auction_house_stops_it_and_keeps_what_was_read(self):
        c = house(); g = c.lua.globals()
        g.startScan()
        g.answer(); c.drain()                                                       # First page of trade goods.
        c.ns.frame.OnEvent(c.ns.frame, 'AUCTION_HOUSE_CLOSED')
        self.assertFalse(c.ns.FullPriceScanRunning())
        self.assertIn('The auction house was closed. 2 prices were saved.', list(g.progress.values())[-1].message)
        self.assertEqual(c.ns.BrowseQuote(2775).unitPrice, 2400)

    def test_a_category_that_never_answers_is_skipped_after_twenty_seconds(self):
        c = house(); g = c.lua.globals()
        c.lua.execute('''
            held = {}
            C_Timer.After = function(delay, callback) held[#held + 1] = callback end
        ''')
        g.startScan()
        c.lua.execute('uptime = uptime + 5; local list = held; held = {}; for _, callback in ipairs(list) do callback() end')
        self.assertEqual(list(g.queries.values()), [7])                             # Five seconds: still waiting.
        g.startScan()                                                                # (Refused: one is running.)
        c.lua.execute('C_Timer.After(20, function() end)')
        c.lua.execute('uptime = uptime + 25')
        c.ns.StopFullPriceScan(); g.queries = c.lua.table()
        g.startScan()
        c.lua.execute('uptime = uptime + 25; local list = held; held = {}; for _, callback in ipairs(list) do callback() end')
        self.assertEqual(list(g.queries.values())[:2], [7, 0])                      # It gave up on trade goods and moved on.

    def test_only_one_scan_runs_and_only_at_an_auction_house(self):
        c = house(); g = c.lua.globals()
        g.atAuction = False
        result = g.startScan()
        self.assertEqual((result[0], result[1]), (False, 'Open the auction house first.'))
        g.atAuction = True
        self.assertTrue(g.startScan())
        again = g.startScan()
        self.assertFalse(again[0])

    def test_a_client_without_the_browse_functions_is_told_so(self):
        c = house(); g = c.lua.globals()
        c.lua.execute('C_AuctionHouse.GetBrowseResults = nil')
        self.assertFalse(c.ns.FullPriceScanSupported())
        result = g.startScan()
        self.assertFalse(result[0])
        self.assertIn('cannot browse the whole auction house', result[1])


if __name__ == '__main__':
    unittest.main()


class BankAltTests(unittest.TestCase):
    """A character the addon has never looked at can still scan."""

    def test_the_scan_reads_realm_and_faction_from_the_game_itself(self):
        c = house(); g = c.lua.globals()
        c.lua.execute('local ns = ...; ns.profile.faction = "Unknown"', c.ns)      # As on a bank alt: no window, no guide.
        self.assertTrue(g.startScan())
        run(c)
        self.assertIsNotNone(c.ns.db.browsePrices['Testrealm:Horde'])
        self.assertEqual(c.ns.BrowseQuote(2771).unitPrice, 290)

    def test_it_still_scans_when_the_game_will_not_say(self):
        c = house(); g = c.lua.globals()
        c.lua.execute('local ns = ...; ns.profile.faction = "Unknown"; function UnitFactionGroup() return nil end; function GetRealmName() return nil end', c.ns)
        self.assertTrue(g.startScan())
        run(c)
        self.assertEqual(c.ns.BrowsePriceCount(), 5)

    def test_each_faction_keeps_its_own_prices(self):
        c = house(); g = c.lua.globals()
        g.startScan(); run(c)
        self.assertEqual(c.ns.BrowseQuote(2775).unitPrice, 2400)
        c.lua.execute('function UnitFactionGroup() return "Alliance", "Alliance" end')
        self.assertIsNone(c.ns.BrowseQuote(2775))                                   # A different auction house.
        c.lua.execute('function UnitFactionGroup() return "Horde", "Horde" end')
        self.assertEqual(c.ns.BrowseQuote(2775).unitPrice, 2400)                    # And the Horde scan is still there.
