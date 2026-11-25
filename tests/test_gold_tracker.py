"""The farm tracker: what a session brought in, what it is worth, and the price scan."""
import unittest

from test_addon import Client
import gold_host


def farm(saved=None):
    c = Client(quests=(), default_guide=True, party_mode='never')
    c.drain()
    space = gold_host.load_gold(c, saved)
    c.lua.execute('local ns = ...; printed = {}; ns.Print = function(text) printed[#printed + 1] = text end; '
                  'WowTogetherModuleAPI.Print = ns.Print', c.ns)
    return c, space.GoldTracker


def rows(summary):
    return [(row.name, row.count, row.value, row.source) for row in summary.rows.values()]


class RecordingTests(unittest.TestCase):
    def test_only_what_the_player_loots_is_counted(self):
        c, t = farm(); fire = c.ns.frame.OnEvent
        gold_host.loot(c, 2771, 3)
        gold_host.loot(c, 2775)
        link = gold_host.item_link(c, 4306)
        fire(c.ns.frame, 'CHAT_MSG_LOOT', 'Eli receives loot: %s.' % link)          # Somebody else's.
        fire(c.ns.frame, 'CHAT_MSG_LOOT', 'You receive item: %s.' % link)           # Bought, crafted or a quest reward.
        fire(c.ns.frame, 'CHAT_MSG_LOOT', 'You create: %s.' % link)
        self.assertEqual(sorted((name, count) for name, count, _, _ in rows(t.Summary())), [('Silver Ore', 1), ('Tin Ore', 3)])

    def test_the_first_loot_starts_the_clock_unless_that_is_switched_off(self):
        c, t = farm()
        self.assertFalse(t.Running())
        gold_host.loot(c, 2771)
        self.assertTrue(t.Running())
        c.lua.execute('clock = clock + 90')
        self.assertEqual(t.Seconds(), 90)

        c, t = farm({'settings': {'gold.trackerAutoStart': False}})
        gold_host.loot(c, 2771)
        self.assertFalse(t.Running())
        self.assertEqual(rows(t.Summary()), [])                                     # Not counted until the player starts it.
        t.Start(); gold_host.loot(c, 2771)
        self.assertEqual(rows(t.Summary())[0][1], 1)

    def test_coins_are_read_from_the_games_own_wording(self):
        c, t = farm(); fire = c.ns.frame.OnEvent
        gold_host.loot(c, 2771)
        fire(c.ns.frame, 'CHAT_MSG_MONEY', 'You loot 3 Silver, 20 Copper')
        fire(c.ns.frame, 'CHAT_MSG_MONEY', 'Your share of the loot is 1 Gold, 2 Silver.')
        self.assertEqual(t.Summary().coin, 320 + 10200)

    def test_experience_gained_while_farming_is_counted_across_a_level(self):
        c, t = farm()
        c.lua.execute('xp, xpMax = 1000, 5000; function UnitXP() return xp end; function UnitXPMax() return xpMax end')
        gold_host.loot(c, 2771)
        fire = c.ns.frame.OnEvent
        fire(c.ns.frame, 'PLAYER_XP_UPDATE', 'player')                              # First reading: nothing to compare with yet.
        c.lua.execute('xp = 1400'); fire(c.ns.frame, 'PLAYER_XP_UPDATE', 'player')
        c.lua.execute('xp, xpMax = 200, 6000'); fire(c.ns.frame, 'PLAYER_XP_UPDATE', 'player')   # Levelled up.
        self.assertEqual(t.Summary().xp, 400 + (5000 - 1400) + 200)


class ValueTests(unittest.TestCase):
    def test_an_auction_price_is_used_where_one_is_saved_and_the_vendor_price_otherwise(self):
        c, t = farm()
        gold_host.quote(c, 2771, 310)
        gold_host.loot(c, 2771, 10)       # Auction: 10 x 3s 10c.
        gold_host.loot(c, 2836, 4)        # No quote: vendor, 4 x 15c.
        gold_host.loot(c, 99999, 2)       # Unknown to the client: no price at all.
        summary = t.Summary()
        self.assertEqual(rows(summary), [('Tin Ore', 10, 3100, 'auction'), ('Coarse Stone', 4, 60, 'vendor'), ('Item 99999', 2, 0, None)])
        self.assertEqual((summary.auction, summary.vendor, summary.unpriced), (3100, 60, 2))
        self.assertEqual(summary.total, 3160)

    def test_a_new_price_revalues_what_was_already_looted(self):
        c, t = farm()
        gold_host.loot(c, 2771, 10)
        self.assertEqual(t.Summary().total, 250)                                    # Vendor price.
        gold_host.quote(c, 2771, 310)                                               # A scan comes back.
        self.assertEqual(t.Summary().total, 3100)

    def test_rates_are_per_hour_of_farming(self):
        c, t = farm()
        gold_host.quote(c, 2771, 300)
        gold_host.loot(c, 2771, 5)
        for _ in range(3):                                                          # Ten minutes, looting as you go.
            c.lua.execute('clock = clock + 200')
            gold_host.loot(c, 2771, 5)
        summary = t.Summary()
        self.assertEqual(summary.seconds, 600)
        self.assertAlmostEqual(summary.perHour, 36000)                              # 20 ore at 3s in ten minutes.
        self.assertAlmostEqual(summary.piecesPerHour, 120)

    def test_money_rates_and_the_clock_read_naturally(self):
        c, t = farm()
        self.assertEqual([t.Money(v) for v in (0, 8, 4012, 70700, 124000, 2500000)], ['0c', '8c', '40s 12c', '7g 7s', '12g 40s', '250g'])
        self.assertEqual([t.Rate(v) for v in (40, 8600, 183400)], ['40c', '86s', '18.3g'])
        self.assertEqual(t.Clock(1395), '00:23:15')


class OtherPriceSourceTests(unittest.TestCase):
    """Prices are read from TradeSkillMaster or Auctionator when one is installed."""

    def with_tsm(self, market=None, lowest=None, saved=None):
        c, t = farm(saved)
        c.lua.execute('''
            local market, lowest = ...
            asked = {}
            TSM_API = {GetCustomPriceValue = function(source, item)
                asked[#asked + 1] = source .. " " .. item
                local id = tonumber(string.match(item, "^i:(%d+)$"))
                if source == "dbmarket" then return market[id] end
                if source == "dbminbuyout" then return lowest[id] end
            end}
        ''', c.lua.table_from(market or {}), c.lua.table_from(lowest or {}))
        return c, t

    def price(self, c, item):
        quote = c.lua.globals().goldSpace.GoldPrices.Price(item)
        return (quote.copper, quote.source, quote.label) if quote else None

    def test_tradeskillmasters_lowest_buyout_is_used_ahead_of_the_vendor_price(self):
        c, t = self.with_tsm(market={2771: 480}, lowest={2771: 420})
        self.assertEqual(self.price(c, 2771), (420, 'TradeSkillMaster', 'TradeSkillMaster lowest buyout'))
        self.assertIn('dbminbuyout i:2771', list(c.lua.globals().asked.values()))
        self.assertEqual(self.price(c, 2836), (15, 'vendor', 'vendor'))            # TSM knows nothing of it.

    def test_its_market_value_is_the_fallback_when_nothing_is_listed(self):
        c, t = self.with_tsm(market={2775: 2300})
        self.assertEqual(self.price(c, 2775), (2300, 'TradeSkillMaster', 'TradeSkillMaster market value'))

    def test_a_setting_prefers_market_value(self):
        c, t = self.with_tsm(market={2771: 480}, lowest={2771: 420}, saved={'settings': {'gold.marketValue': True}})
        self.assertEqual(self.price(c, 2771), (480, 'TradeSkillMaster', 'TradeSkillMaster market value'))

    def test_a_scan_under_an_hour_old_wins_and_an_older_one_does_not(self):
        c, t = self.with_tsm(market={2771: 420})
        gold_host.quote(c, 2771, 310, age=600)
        self.assertEqual(self.price(c, 2771)[:2], (310, 'core auction quote'))
        gold_host.quote(c, 2771, 310, age=7200)
        self.assertEqual(self.price(c, 2771)[:2], (420, 'TradeSkillMaster'))

    def test_an_auction_price_below_the_vendor_price_is_not_used(self):
        c, t = self.with_tsm(market={2775: 40})                                     # A vendor pays 75c.
        self.assertEqual(self.price(c, 2775), (75, 'vendor', 'vendor'))

    def test_auctionator_is_read_when_tradeskillmaster_is_not_there(self):
        c, t = farm()
        c.lua.execute('Auctionator = {API = {v1 = {GetAuctionPriceByItemID = function(caller, id) if id == 4306 then return 760 end end}}}')
        self.assertEqual(self.price(c, 4306), (760, 'Auctionator', 'Auctionator'))
        self.assertEqual(list(c.lua.globals().goldSpace.GoldPrices.Sources().values()), ['Auctionator'])

    def test_it_can_be_switched_off(self):
        c, t = self.with_tsm(market={2771: 420}, saved={'settings': {'gold.otherPrices': False}})
        self.assertEqual(self.price(c, 2771), (25, 'vendor', 'vendor'))

    def test_an_addon_that_errors_or_returns_nonsense_is_ignored(self):
        c, t = farm()
        c.lua.execute('TSM_API = {GetCustomPriceValue = function() error("not ready") end}')
        self.assertEqual(self.price(c, 2771), (25, 'vendor', 'vendor'))
        c.lua.execute('TSM_API = {GetCustomPriceValue = function() return "soon" end}')
        self.assertEqual(self.price(c, 2771), (25, 'vendor', 'vendor'))

    def test_the_tracker_values_the_session_with_it_and_says_where_prices_came_from(self):
        c, t = self.with_tsm(market={2771: 420, 6359: 90})
        gold_host.loot(c, 2771, 10); gold_host.loot(c, 6359, 20); gold_host.loot(c, 2836, 4)
        summary = t.Summary()
        self.assertEqual((summary.auction, summary.vendor), (4200 + 1800, 60))
        t.Show()
        self.assertIn('2 items at auction price from TradeSkillMaster', t.window.body.basis.text)
        self.assertEqual(t.window.body.rows[1].value.text, '42s')

    def test_what_it_already_prices_does_not_need_scanning(self):
        c, t = self.with_tsm(market={2771: 420})
        c.lua.execute('local space = ...; space.GoldFarms.ScanItems = function() return {2771, 2775} end; '
                      'space.GoldObservations.SeenItems = function() return {} end', c.lua.globals().goldSpace)
        ids, groups = t.ScanPlan()
        self.assertEqual(list(ids.values()), [2775])                                # Only the gap.
        self.assertEqual(groups.fresh, 1)


class ClockTests(unittest.TestCase):
    def test_a_break_does_not_dilute_the_hourly_figures(self):
        c, t = farm()
        gold_host.loot(c, 2771)
        for _ in range(3):
            c.lua.execute('clock = clock + 200')
            gold_host.loot(c, 2771)                                                 # Last loot at ten minutes.
        c.lua.execute('clock = clock + 299'); t.Tick()
        self.assertTrue(t.Running())                                                # Not yet five minutes idle.
        c.lua.execute('clock = clock + 2'); t.Tick()
        self.assertFalse(t.Running())
        self.assertEqual(t.Seconds(), 660)                                          # Ten minutes, plus one of the gap.
        c.lua.execute('clock = clock + 3600')
        self.assertEqual(t.Seconds(), 660)
        gold_host.loot(c, 2771)                                                     # Back at it: the clock picks up.
        self.assertTrue(t.Running())

    def test_the_clock_is_right_with_the_window_closed(self):
        # Nothing ticks while the window is shut; the gap is settled when it is next looked at.
        c, t = farm()
        gold_host.loot(c, 2771)
        c.lua.execute('clock = clock + 100')
        gold_host.loot(c, 2771)
        c.lua.execute('clock = clock + 1200')                                       # Twenty minutes of questing, no loot.
        self.assertEqual(t.Summary().seconds, 160)                                  # 100 s, plus one minute of the gap.
        gold_host.loot(c, 2771)
        c.lua.execute('clock = clock + 40')
        self.assertEqual(t.Summary().seconds, 200)

    def test_pause_and_resume(self):
        c, t = farm()
        gold_host.loot(c, 2771)
        c.lua.execute('clock = clock + 100'); t.Pause()
        c.lua.execute('clock = clock + 500'); t.Start()
        c.lua.execute('clock = clock + 50')
        self.assertEqual(t.Seconds(), 150)

    def test_a_session_survives_a_reload_and_comes_back_paused(self):
        c, t = farm()
        gold_host.loot(c, 2771, 5)
        c.lua.execute('clock = clock + 300'); t.Pause()
        saved = c.lua.globals().WowTogetherGoldDB
        again, t2 = farm({'tracker': {'items': {2771: 5}, 'active': 300, 'coin': 0, 'xp': 0, 'loots': 1, 'zone': 'Hillsbrad Foothills'}})
        self.assertFalse(t2.Running())
        self.assertEqual(t2.Seconds(), 300)
        self.assertEqual(rows(t2.Summary())[0][:2], ('Tin Ore', 5))
        self.assertEqual(saved.tracker.active, 300)


class SessionEndTests(unittest.TestCase):
    """The tracker counts all the time, so a session ends by itself after a long break."""

    def history(self, c):
        return list(c.lua.globals().WowTogetherGoldDB.trackerHistory.values())

    def stretch(self, c, minutes=10, item=2771):
        """Loot steadily for a while."""
        for _ in range(minutes * 60 // 100):
            gold_host.loot(c, item, 2)
            c.lua.execute('clock = clock + 100')

    def test_half_an_hour_without_loot_ends_the_session_and_the_next_loot_starts_a_new_one(self):
        c, t = farm()
        self.stretch(c, minutes=10)
        c.lua.execute('clock = clock + 1900')                                       # A long break.
        gold_host.loot(c, 4306, 1)
        past = self.history(c)
        self.assertEqual(len(past), 1)                                              # The first stretch was kept...
        self.assertEqual(past[0].top[1].name, 'Tin Ore')
        self.assertEqual(rows(t.Summary()), [('Silk Cloth', 1, 150, 'vendor')])     # ...and this is a fresh one.
        self.assertTrue(t.Running())

    def test_a_short_break_stays_in_the_same_session(self):
        c, t = farm()
        self.stretch(c, minutes=10)
        c.lua.execute('clock = clock + 900')                                        # Fifteen minutes: paused, not over.
        gold_host.loot(c, 4306, 1)
        self.assertEqual(self.history(c), [])
        self.assertEqual(sorted(name for name, _, _, _ in rows(t.Summary())), ['Silk Cloth', 'Tin Ore'])

    def test_a_session_the_player_paused_is_kept_for_them(self):
        c, t = farm()
        self.stretch(c, minutes=10)
        t.Show()
        t.window.toggle.OnClick(t.window.toggle)                                    # Pause, by hand.
        c.lua.execute('clock = clock + 7200')
        self.assertEqual(len(rows(t.Summary())), 1)                                 # Still there two hours later.
        self.assertEqual(self.history(c), [])

    def test_a_session_from_before_a_long_logout_is_closed_on_return(self):
        c, t = farm({'tracker': {'items': {2771: 40}, 'active': 900, 'coin': 0, 'xp': 0, 'loots': 20,
                                 'zone': 'Hillsbrad Foothills', 'lastLootWall': 1795000000 + 1000 - 7200}})
        self.assertEqual(rows(t.Summary()), [])                                     # Two hours ago: over.
        past = self.history(c)
        self.assertEqual((past[0].zone, past[0].seconds), ('Hillsbrad Foothills', 900))

    def test_a_session_is_named_after_the_zone_most_of_it_was_spent_in(self):
        c, t = farm()
        gold_host.loot(c, 2771, 2)                                                  # It began in Hillsbrad...
        c.lua.execute('zoneText = "Arathi Highlands"; clock = clock + 60')
        gold_host.loot(c, 2771, 30)                                                 # ...but was mostly Arathi.
        self.assertEqual(t.Summary().zone, 'Arathi Highlands')


class LogoutTests(unittest.TestCase):
    """A session's time is saved with it, so logging out mid-session does not lose it."""

    def fish(self, c, minutes):
        c.lua.execute('fishing = true; function IsFishingLoot() return fishing end')
        for _ in range(minutes):
            c.ns.frame.OnEvent(c.ns.frame, 'LOOT_READY')
            gold_host.loot(c, 6359, 1)
            c.lua.execute('clock = clock + 60')

    def test_the_time_farmed_is_on_disk_while_the_session_is_still_running(self):
        # It was only written when the session paused: an hour of fishing saved as 0 seconds.
        c, t = farm()
        self.fish(c, 58)
        saved = c.lua.globals().WowTogetherGoldDB.tracker
        self.assertGreaterEqual(saved.active, 57 * 60)
        self.assertTrue(t.Running())

    def test_logging_out_settles_the_clock(self):
        c, t = farm()
        self.fish(c, 20)
        c.ns.frame.OnEvent(c.ns.frame, 'PLAYER_LOGOUT')
        self.assertEqual(c.lua.globals().WowTogetherGoldDB.tracker.active, 20 * 60)
        self.assertFalse(t.Running())

    def test_an_hour_of_fishing_survives_a_character_switch_and_becomes_a_fishing_farm(self):
        c, t = farm()
        self.fish(c, 58)
        c.ns.frame.OnEvent(c.ns.frame, 'PLAYER_LOGOUT')
        saved = c.lua.globals().WowTogetherGoldDB
        state = {'tracker': {'items': {6359: 58}, 'active': saved.tracker.active, 'coin': 0, 'xp': 0, 'loots': 58,
                             'zone': 'Hillsbrad Foothills', 'zones': {'Hillsbrad Foothills': 58}, 'kinds': {'Fishing': 58},
                             'lastLootWall': saved.tracker.lastLootWall}}
        back, t2 = farm(state)                                                      # Logged in again, on any character.
        self.assertEqual(t2.Summary().seconds, 58 * 60)
        back.lua.execute('clock = clock + 9000')                                    # Later: the session closes itself.
        t2.Tick()
        history = list(back.lua.globals().WowTogetherGoldDB.trackerHistory.values())
        self.assertEqual((history[0].zone, history[0].seconds, history[0].kind), ('Hillsbrad Foothills', 58 * 60, 'Fishing'))
        farms = [(f.name, f.category, f.minutes) for f in t2.OwnFarms().values()]
        self.assertEqual(farms, [('Your fishing', 'Fishing', 58)])

    def test_fishing_is_still_recognised_when_the_game_does_not_say_a_loot_is_a_catch(self):
        c, t = farm(); fire = c.ns.frame.OnEvent
        c.lua.execute('''
            IsFishingLoot = nil
            function GetLootSourceInfo() return "GameObject-0-1-2-3-35591-000" end          -- the bobber
            function GetSpellInfo(id) return id == 7620 and "Fishing" or nil end
        ''')
        fire(c.ns.frame, 'UNIT_SPELLCAST_CHANNEL_START', 'player', 'cast', 7620)
        c.lua.execute('clock = clock + 22')                                         # The bobber sits a while before the bite.
        fire(c.ns.frame, 'LOOT_READY'); gold_host.loot(c, 6359, 1)
        self.assertEqual(c.lua.globals().WowTogetherGoldDB.tracker.kinds.Fishing, 1)


class PaceTests(unittest.TestCase):
    """The tracker knows how fast the player really gathers: one harvest per loot window."""

    def test_each_catch_is_one_harvest_however_the_game_announces_it(self):
        c, t = farm()
        c.lua.execute('function IsFishingLoot() return true end')
        for _ in range(20):
            c.ns.frame.OnEvent(c.ns.frame, 'LOOT_READY')
            c.ns.frame.OnEvent(c.ns.frame, 'LOOT_OPENED')                           # Both fire for one catch.
            gold_host.loot(c, 6359, 1)
            gold_host.loot(c, 2836, 1)                                              # Two items came out of that one catch.
            c.lua.execute('clock = clock + 30')
        self.assertEqual(c.lua.globals().WowTogetherGoldDB.tracker.harvests.Fishing, 20)
        pace, minutes = t.KindPace('Fishing')
        self.assertEqual((round(pace), minutes), (120, 10))                         # Twenty catches in ten minutes.
        self.assertIsNone(t.KindPace('Mining'))

    def test_past_sessions_count_and_a_short_one_does_not(self):
        c, t = farm({'trackerHistory': [
            {'zone': 'A', 'seconds': 1800, 'total': 1, 'perHour': 2, 'kind': 'Fishing', 'harvests': 70, 'items': {6359: 70}},
            {'zone': 'B', 'seconds': 1800, 'total': 1, 'perHour': 2, 'kind': 'Fishing', 'harvests': 50, 'items': {6359: 50}},
            {'zone': 'C', 'seconds': 200, 'total': 1, 'perHour': 2, 'kind': 'Fishing', 'harvests': 90, 'items': {6359: 90}},
            {'zone': 'D', 'seconds': 1800, 'total': 1, 'perHour': 2, 'kind': 'Killing', 'harvests': 300, 'items': {4306: 300}}]})
        pace, minutes = t.KindPace('Fishing')
        self.assertEqual((pace, minutes), (120, 60))                                # 120 catches over the two real sessions.

    def test_an_older_fishing_session_without_a_harvest_count_still_gives_a_pace(self):
        c, t = farm({'trackerHistory': [
            {'zone': 'A', 'seconds': 1800, 'total': 1, 'perHour': 2, 'kind': 'Fishing', 'items': {6359: 40, 2836: 20}}]})
        self.assertEqual(t.KindPace('Fishing')[0], 120)                             # Sixty fish in half an hour.


class PartialFishDataTests(unittest.TestCase):
    def test_a_fishing_farm_whose_fish_list_is_incomplete_says_so(self):
        c, t = farm()
        partial = c.lua.table_from({'category': 'Fishing', 'routable': False, 'auctionPriced': 1,
                                    'top': [{'itemID': 6308, 'chance': 0.40}, {'itemID': 8366, 'chance': 0.003}]}, recursive=True)
        whole = c.lua.table_from({'category': 'Fishing', 'routable': False, 'auctionPriced': 1,
                                  'top': [{'itemID': 6308, 'chance': 0.55}, {'itemID': 6359, 'chance': 0.40}]}, recursive=True)
        self.assertEqual(t.FarmBasis(partial, False), 'no route  •  partial farm data  •  auction prices')
        self.assertEqual(t.FarmBasis(whole, False), 'no route  •  farm data  •  auction prices')
        self.assertAlmostEqual(t.FishCoverage(partial), 0.403)
        self.assertIsNone(t.FishCoverage(c.lua.table_from({'category': 'Killing', 'top': []}, recursive=True)))


class JoinedFarmTests(unittest.TestCase):
    """The player's own result and the farm data's farm for the same place are one row, with the best of each."""

    def page(self, history, data):
        c, t = farm({'trackerHistory': history})
        c.lua.execute('''
            local space, data = ...
            started = nil
            space.GoldFarms.CATEGORIES = {"Killing", "Mining", "Herbalism", "Skinning", "Fishing"}
            space.GoldFarms.Categories = function() return {Killing = 2, Mining = 0, Herbalism = 0, Skinning = 0, Fishing = 2} end
            space.GoldFarms.Suggestions = function(limit, category)
                local list = {}
                for _, row in ipairs(data) do
                    if category == nil or row.category == category then
                        local copy = {}
                        for key, value in pairs(row) do copy[key] = value end
                        list[#list + 1] = copy
                    end
                end
                return list
            end
            space.GoldFarms.Start = function(key) started = key; return true end
        ''', c.lua.globals().goldSpace, c.lua.table_from(data, recursive=True))
        page = c.lua.eval('function() local f = CreateFrame("Frame", nil, UIParent); f:SetSize(900, 400); return f end')()
        t.RenderPage(page)
        return c, t, page, page.goldPage

    FISHING = [{'zone': 'Stranglethorn Vale', 'seconds': 1380, 'total': 30000, 'perHour': 7900, 'kind': 'Fishing',
                'harvests': 50, 'items': {6359: 606}, 'coin': 0}]                   # 606 fish at 5c in 23 min: 79s an hour.
    DATA = [{'key': 'gather:356:1434', 'name': 'Water tier 4', 'zone': 'Stranglethorn Vale', 'category': 'Fishing', 'estimate': 400,
             'routable': True, 'seededRoute': True, 'knownSpots': 60, 'auctionPriced': 1, 'paceAssumed': True},
            {'key': 'gather:356:1435', 'name': 'Water tier 4', 'zone': 'Swamp of Sorrows', 'category': 'Fishing', 'estimate': 400,
             'routable': False, 'auctionPriced': 1, 'paceAssumed': True},
            {'key': 'mob:1', 'name': 'Young Panther', 'zone': 'Stranglethorn Vale', 'category': 'Killing', 'estimate': 68000, 'routable': True, 'paceAssumed': True},
            {'key': 'mob:2', 'name': 'Bloodscalp Scout', 'zone': 'Stranglethorn Vale', 'category': 'Killing', 'estimate': 41000, 'routable': True, 'paceAssumed': True}]

    def rows(self, view):
        return [(row.name.text, row.estimate.text, row.basis.text, row.go.caption.text) for row in view.farms.values() if row.IsShown(row)]

    def chip(self, view, title):
        chip = next(chip for chip in view.chips.values() if chip.title == title)
        chip.OnClick(chip)

    def test_my_fishing_and_the_datas_fishing_in_one_zone_are_one_row(self):
        c, t, page, view = self.page(self.FISHING, self.DATA)
        self.chip(view, 'Fishing')
        shown = self.rows(view)
        self.assertEqual(len(shown), 2)                                             # Not three: no separate "Your fishing".
        self.assertEqual(shown[0], ('Fishing  •  Stranglethorn Vale', '79s/h', 'loop, 60 known spots  •  your results, 23 min  •  auction prices', 'Start route'))
        self.assertEqual(shown[1][0], 'Fishing  •  Swamp of Sorrows')               # Never fished there: the data's row as it was.
        self.assertEqual(shown[1][1], '4s/h')

    def test_start_on_the_joined_row_starts_the_datas_route(self):
        c, t, page, view = self.page(self.FISHING, self.DATA)
        self.chip(view, 'Fishing')
        view.farms[1].go.OnClick(view.farms[1].go)
        self.assertEqual(c.lua.globals().started, 'gather:356:1434')

    def test_a_zone_the_data_does_not_cover_keeps_my_own_row(self):
        history = [dict(self.FISHING[0], zone='Thunder Bluff')]
        c, t, page, view = self.page(history, self.DATA)
        self.chip(view, 'Fishing')
        names = [name for name, _, _, _ in self.rows(view)]
        self.assertIn('Your fishing  •  Thunder Bluff', names)
        self.assertEqual(len(names), 3)

    def test_killing_is_not_joined_because_a_zones_kills_are_not_one_creatures(self):
        history = [{'zone': 'Stranglethorn Vale', 'seconds': 1800, 'total': 50000, 'perHour': 100000, 'kind': 'Killing', 'items': {4306: 300}, 'coin': 0}]
        c, t, page, view = self.page(history, self.DATA)
        self.chip(view, 'Killing')
        names = [name for name, _, _, _ in self.rows(view)]
        self.assertEqual(sorted(names), ['Bloodscalp Scout  •  Stranglethorn Vale', 'Young Panther  •  Stranglethorn Vale', 'Your killing  •  Stranglethorn Vale'])


class NoRouteTests(unittest.TestCase):
    """A farm with no known spots says so before and after it is pressed. In play: Start, and nothing happened."""

    def page(self):
        c, t = farm()
        c.lua.execute('''
            local space = ...
            started = nil
            space.GoldFarms.CATEGORIES = {"Killing", "Mining", "Herbalism", "Skinning", "Fishing"}
            space.GoldFarms.Categories = function() return {Killing = 0, Mining = 0, Herbalism = 0, Skinning = 0, Fishing = 2} end
            space.GoldFarms.Suggestions = function()
                return {{key = "pools", name = "Water tier 4", zone = "Stranglethorn Vale", category = "Fishing", estimate = 2000, routable = true, knownSpots = 60, seededRoute = true},
                        {key = "open", name = "Water tier 4", zone = "Swamp of Sorrows", category = "Fishing", estimate = 1900, routable = false}}
            end
            space.GoldFarms.Start = function(key) started = key; return true end
        ''', c.lua.globals().goldSpace)
        page = c.lua.eval('function() local f = CreateFrame("Frame", nil, UIParent); f:SetSize(900, 400); return f end')()
        t.RenderPage(page)
        return c, t, page.goldPage

    def test_the_two_kinds_of_farm_look_different(self):
        c, t, view = self.page()
        route, none = view.farms[1], view.farms[2]
        self.assertEqual((route.go.caption.text, none.go.caption.text), ('Start route', 'Track'))
        self.assertTrue(route.go.primary)
        self.assertFalse(none.go.primary)                                           # The dull button: nothing to follow.
        self.assertIn('loop, 60 known spots', route.basis.text)
        self.assertIn('no route', none.basis.text)

    def test_pressing_a_farm_with_no_route_says_what_to_do(self):
        c, t, view = self.page()
        none = view.farms[2]
        none.go.OnClick(none.go)
        self.assertEqual(c.lua.globals().started, 'open')                           # The session is still counted against it.
        said = list(c.lua.globals().printed.values())[-1]
        self.assertIn('No route: no spots are known in Swamp of Sorrows', said)
        self.assertIn('the spots you find become a route', said)
        t.Show()
        self.assertIn('No route: no spots are known in Swamp of Sorrows', t.window.body.basis.text)   # And on screen, not only in chat.

    def test_pressing_a_farm_with_a_route_leaves_no_such_note(self):
        c, t, view = self.page()
        view.farms[2].go.OnClick(view.farms[2].go)
        view.farms[1].go.OnClick(view.farms[1].go)
        t.Show()
        self.assertNotIn('No route', t.window.body.basis.text)


class SpotTests(unittest.TestCase):
    """Where the player harvests is remembered, by kind and zone, and survives a reload."""

    def setUp(self):
        self.c, self.t = farm()
        self.c.lua.execute('''
            here = {mapID = 1435, x = 0.50, y = 0.50}
            WowTogetherModuleAPI.PlayerSpot = function() return here end
            function IsFishingLoot() return true end''')

    def catch(self, x, y, times=1):
        self.c.lua.execute('here = {mapID = 1435, x = %f, y = %f}' % (x, y))
        for _ in range(times):
            self.c.ns.frame.OnEvent(self.c.ns.frame, 'LOOT_READY')
            gold_host.loot(self.c, 6359, 1)
            self.c.lua.execute('clock = clock + 25')

    def spots(self, kind='Fishing', zone=1435):
        return [(round(s.x, 3), round(s.y, 3), s.n) for s in self.t.Spots(kind, zone).values()]

    def test_each_place_fished_is_one_spot_however_long_you_stand_there(self):
        self.catch(0.50, 0.50, times=40)
        self.assertEqual(self.spots(), [(0.5, 0.5, 40)])

    def test_moving_along_the_shore_makes_new_spots_and_a_step_does_not(self):
        self.catch(0.50, 0.50, times=3)
        self.catch(0.502, 0.501, times=2)                                           # A few yards: the same spot.
        self.catch(0.56, 0.50, times=1)                                             # Along the bank: another.
        self.catch(0.50, 0.62, times=5)
        self.assertEqual(self.spots(), [(0.5, 0.5, 5), (0.5, 0.62, 5), (0.56, 0.5, 1)])

    def test_spots_are_kept_apart_by_kind_and_by_zone(self):
        self.catch(0.50, 0.50)
        self.assertEqual(self.spots('Mining'), [])
        self.assertEqual(self.spots('Fishing', 1434), [])

    def test_only_eighty_are_kept_and_the_least_used_makes_way(self):
        self.catch(0.10, 0.10, times=3)                                             # A favourite.
        for index in range(1, 81):
            self.catch(0.10 + index * 0.01, 0.50)
        kept = self.spots()
        self.assertEqual(len(kept), 80)
        self.assertIn((0.1, 0.1, 3), kept)                                          # Still there.

    def test_they_survive_a_reload(self):
        self.catch(0.50, 0.50, times=4)
        self.catch(0.60, 0.50, times=2)
        again, t2 = farm(gold_host.saved_data(self.c))
        self.assertEqual([(round(s.x, 2), round(s.y, 2), s.n) for s in t2.Spots('Fishing', 1435).values()], [(0.5, 0.5, 4), (0.6, 0.5, 2)])

    def test_a_row_says_how_many_of_your_spots_it_has(self):
        t = self.t
        make = lambda fields: self.c.lua.table_from(fields, recursive=True)
        self.assertEqual(t.FarmBasis(make({'routable': False, 'ownSpots': 2, 'auctionPriced': 1}), False),
                         'no route yet, 2 of 3 spots found  •  farm data  •  auction prices')
        self.assertEqual(t.FarmBasis(make({'routable': True, 'ownSpots': 5, 'auctionPriced': 1}), False),
                         'loop, 5 spots of yours  •  farm data  •  auction prices')
        self.assertEqual(t.FarmBasis(make({'routable': True, 'knownSpots': 60, 'ownSpots': 4, 'auctionPriced': 1}), False),
                         'loop, 60 known spots, 4 yours  •  farm data  •  auction prices')


class ReloadTests(unittest.TestCase):
    """What the gold package records survives a reload. It never did: it worked in a table the game did not save."""

    def fish(self, c, minutes):
        c.lua.execute('fishing = true; function IsFishingLoot() return fishing end')
        for _ in range(minutes):
            c.ns.frame.OnEvent(c.ns.frame, 'LOOT_READY')
            gold_host.loot(c, 6359, 1)
            c.lua.execute('clock = clock + 60')

    def test_past_sessions_settings_and_the_window_come_back_after_a_reload(self):
        c, t = farm()
        self.fish(c, 20)
        t.Stop()
        t.Show()
        c.lua.globals().WowTogetherGoldDB.settings['gold.farmKind'] = 'Fishing'
        disk = gold_host.saved_data(c)
        self.assertEqual(len(disk['trackerHistory']), 1)                            # It is in what the game writes...

        again, t2 = farm(disk)                                                      # ...and there after the reload.
        history = list(again.lua.globals().WowTogetherGoldDB.trackerHistory.values())
        self.assertEqual((history[0].zone, history[0].kind, history[0].seconds), ('Hillsbrad Foothills', 'Fishing', 1200))
        self.assertEqual([(f.name, f.category) for f in t2.OwnFarms().values()], [('Your fishing', 'Fishing')])
        self.assertEqual(again.lua.globals().WowTogetherGoldDB.settings['gold.farmKind'], 'Fishing')
        self.assertTrue(t2.window.IsShown(t2.window))                               # The window was on screen: it is again.

    def test_a_running_session_comes_back_with_its_items_and_its_time(self):
        c, t = farm()
        self.fish(c, 12)
        disk = gold_host.saved_data(c)
        again, t2 = farm(disk)
        summary = t2.Summary()
        self.assertEqual(summary.seconds, 12 * 60)
        self.assertEqual(rows(summary)[0][:2], ('Firefin Snapper', 12))
        self.assertFalse(t2.Running())                                              # Paused until the next loot.

    def test_what_is_recorded_after_a_reload_is_saved_too(self):
        c, t = farm()
        self.fish(c, 10); t.Stop()
        again, t2 = farm(gold_host.saved_data(c))
        self.fish(again, 10); t2.Stop()
        disk = gold_host.saved_data(again)
        self.assertEqual(len(disk['trackerHistory']), 2)                            # The old session and the new one.

    def test_the_table_the_package_works_in_is_the_one_the_game_saves(self):
        c, t = farm({'trackerHistory': [{'zone': 'Arathi Highlands', 'seconds': 900, 'total': 5000, 'perHour': 20000, 'top': []}]})
        g = c.lua.globals()
        self.assertTrue(c.lua.eval('function(space) return WowTogetherGoldDB == space.db end')(g.goldSpace))
        self.assertEqual(g.WowTogetherGoldDB.trackerHistory[1].zone, 'Arathi Highlands')
        self.assertEqual(g.WowTogetherGoldDB.schema, 1)

    def test_saved_data_is_still_taken_if_the_loaded_event_is_missed(self):
        import os
        c = Client(quests=(), default_guide=True, party_mode='never'); c.drain()
        lua = c.lua
        lua.execute(gold_host.ITEMS)
        lua.globals().WowTogetherGoldDB = None
        space = lua.table()
        folder = os.path.join(gold_host.ROOT, 'WowTogether_Gold')
        load = lua.eval('function(source, name, addon, namespace) local chunk, problem = loadstring(source, name); '
                        'if not chunk then error(problem) end; return chunk(addon, namespace) end')
        for line in open(os.path.join(folder, 'WowTogether_Gold.toc'), encoding='utf-8'):
            line = line.strip()
            if line.endswith('.lua'):
                load(open(os.path.join(folder, line), encoding='utf-8').read(), line, 'WowTogether_Gold', space)
        lua.globals().WowTogetherGoldDB = lua.table_from({'trackerHistory': [{'zone': 'Desolace', 'seconds': 700, 'total': 900, 'perHour': 4600, 'top': []}]}, recursive=True)
        c.drain()                                                                   # No event: the one-second fallback runs.
        self.assertEqual(space.db.trackerHistory[1].zone, 'Desolace')


class ActivityChangeTests(unittest.TestCase):
    """A session is one activity in one place: change either, and a new one starts by itself."""

    def setUp(self):
        self.c, self.t = farm()
        self.c.lua.execute('''
            fishing = false
            function IsFishingLoot() return fishing end
            source = "Creature-0-1-2-3-4-5"
            function GetLootSourceInfo() return source end
        ''')

    def catch(self, count=1, item=6359):
        self.c.lua.execute('fishing = true')
        self.c.ns.frame.OnEvent(self.c.ns.frame, 'LOOT_READY'); gold_host.loot(self.c, item, count)

    def kill(self, count=1, item=4306):
        self.c.lua.execute('fishing = false')
        self.c.ns.frame.OnEvent(self.c.ns.frame, 'LOOT_READY'); gold_host.loot(self.c, item, count)

    def wait(self, seconds=60):
        self.c.lua.execute('clock = clock + %d' % seconds)

    def history(self):
        return list(self.c.lua.globals().WowTogetherGoldDB.trackerHistory.values())

    def test_fishing_then_killing_becomes_two_sessions(self):
        for _ in range(15):
            self.catch(); self.wait()                                               # Fifteen minutes of fishing.
        for _ in range(5):
            self.kill(); self.wait()                                                # Then mobs, and it stays mobs.
        past = self.history()
        self.assertEqual(len(past), 1)
        self.assertEqual((past[0].kind, past[0].seconds, past[0]['items'][6359]), ('Fishing', 15 * 60, 15))
        self.assertIsNone(past[0]['items'][4306])                                   # The cloth is not in the fishing run.
        summary = self.t.Summary()
        self.assertEqual(summary.kind, 'Killing')
        self.assertEqual(rows(summary)[0][:2], ('Silk Cloth', 5))                   # It is in the new one...
        self.assertEqual(summary.seconds, 5 * 60)                                   # ...which began when the killing did.
        self.assertTrue(self.t.Running())
        self.assertIn('your fishing in Hillsbrad Foothills is saved. Now counting killing', list(self.c.lua.globals().printed.values())[-1])

    def test_a_mob_that_interrupts_the_fishing_does_not_end_the_run(self):
        for _ in range(10):
            self.catch(); self.wait()
        self.kill(2); self.wait(20)                                                 # Something attacked.
        self.kill(1); self.wait(20)
        for _ in range(3):
            self.catch(); self.wait()
        self.assertEqual(self.history(), [])
        summary = self.t.Summary()
        self.assertEqual(summary.kind, 'Fishing')
        self.assertEqual(sorted(name for name, _, _, _ in rows(summary)), ['Firefin Snapper', 'Silk Cloth'])   # Its loot still counts.

    def test_killing_and_skinning_the_same_beasts_is_one_run(self):
        self.c.lua.execute('function GetSpellInfo(id) return id == 8613 and "Skinning" or nil end')
        for _ in range(12):
            self.kill(); self.wait(20)
            self.c.ns.frame.OnEvent(self.c.ns.frame, 'UNIT_SPELLCAST_SUCCEEDED', 'player', 'cast', 8613)
            self.c.ns.frame.OnEvent(self.c.ns.frame, 'LOOT_READY'); gold_host.loot(self.c, 2319, 1)
            self.wait(40)
        self.assertEqual(self.history(), [])
        kinds = self.c.lua.globals().WowTogetherGoldDB.tracker.kinds
        self.assertEqual((kinds.Killing, kinds.Skinning), (12, 12))

    def test_the_same_farming_in_another_zone_is_a_new_session(self):
        for _ in range(8):
            self.kill(); self.wait()
        self.c.lua.globals().zoneText = 'Arathi Highlands'
        for _ in range(5):
            self.kill(); self.wait()
        past = self.history()
        self.assertEqual((past[0].zone, past[0].kind, past[0].seconds), ('Hillsbrad Foothills', 'Killing', 8 * 60))
        self.assertEqual(self.t.Summary().zone, 'Arathi Highlands')

    def test_a_slow_change_still_counts_after_two_minutes(self):
        for _ in range(10):
            self.catch(); self.wait()
        self.kill(); self.wait(130)                                                 # Few loots, but it has been killing for a while.
        self.kill()
        self.assertEqual(len(self.history()), 1)

    def test_loot_of_an_unknown_kind_never_splits_a_run(self):
        for _ in range(10):
            self.catch(); self.wait()
        for _ in range(8):
            gold_host.loot(self.c, 2836, 1); self.wait(30)                          # No loot window seen: kind unknown.
        self.assertEqual(self.history(), [])

    def test_a_short_run_before_a_change_is_dropped_not_saved(self):
        for _ in range(3):
            self.catch(); self.wait()                                               # Three minutes: not a session.
        for _ in range(5):
            self.kill(); self.wait()
        self.assertEqual(self.history(), [])
        self.assertEqual(self.t.Summary().kind, 'Killing')


class HistoryTests(unittest.TestCase):
    def test_a_real_session_is_kept_on_stop_and_a_short_one_is_not(self):
        c, t = farm()
        gold_host.quote(c, 2771, 300)
        gold_host.loot(c, 2771, 20)
        c.lua.execute('clock = clock + 120')
        t.Stop()
        self.assertEqual(len(list(c.lua.globals().WowTogetherGoldDB.trackerHistory.values())), 0)   # Two minutes: not a session.
        gold_host.loot(c, 2771, 20)
        c.lua.execute('clock = clock + 1200')
        t.Stop()
        history = list(c.lua.globals().WowTogetherGoldDB.trackerHistory.values())
        self.assertEqual(len(history), 1)
        self.assertEqual((history[0].zone, history[0].seconds, history[0].total, history[0].perHour), ('Hillsbrad Foothills', 1200, 6000, 18000))
        self.assertEqual(history[0].top[1].name, 'Tin Ore')
        self.assertEqual(rows(t.Summary()), [])                                     # A clean slate.
        self.assertEqual(t.Seconds(), 0)

    def test_the_best_rate_in_a_zone_is_remembered(self):
        c, t = farm({'trackerHistory': [
            {'zone': 'Hillsbrad Foothills', 'seconds': 1800, 'total': 96000, 'perHour': 192000, 'top': []},
            {'zone': 'Hillsbrad Foothills', 'seconds': 2520, 'total': 221000, 'perHour': 315700, 'top': []},
            {'zone': 'Arathi Highlands', 'seconds': 1500, 'total': 88000, 'perHour': 211200, 'top': []}]})
        self.assertEqual(t.BestFor('Hillsbrad Foothills').perHour, 315700)
        self.assertIsNone(t.BestFor('Desolace'))


class WindowTests(unittest.TestCase):
    def session(self):
        c, t = farm()
        for item, copper in ((2771, 310), (2775, 2400), (4306, 760)):
            gold_host.quote(c, item, copper)
        for item, count in ((2771, 42), (2775, 6), (2836, 38), (4306, 11), (3924, 7)):
            gold_host.loot(c, item, count)
            c.lua.execute('clock = clock + 290')                                    # Looting as the session goes on.
        c.lua.execute('clock = clock - 55')                                         # 23 min 15 s in all.
        t.Show()
        return c, t

    def test_the_window_ranks_what_earned_most(self):
        c, t = self.session()
        body = t.window.body
        shown = [(row.name.text, row.count.text, row.value.text) for row in body.rows.values() if row.IsShown(row)]
        self.assertEqual(shown, [('Silver Ore', '×6', '1g 44s'), ('Tin Ore', '×42', '1g 30s'), ('Silk Cloth', '×11', '83s 60c'),
                                 ('Raptor Hide Scrap', '×7', '12s 67c'), ('Coarse Stone', '×38', '5s 70c')])
        self.assertEqual(t.window.clock.text, '00:23:15')
        self.assertEqual(body.tiles[1].caption.text, 'GOLD PER HOUR')
        self.assertEqual(body.tiles[2].value.text, '3g 76s')
        self.assertIn('Auction 3g 57s', body.split.text)
        self.assertIn('3 items at auction price', body.basis.text)
        self.assertIn('2 at vendor price', body.basis.text)

    def test_reset_throws_the_session_away_and_takes_two_clicks(self):
        c, t = self.session()
        reset = t.window.reset
        reset.OnClick(reset)
        self.assertEqual(reset.caption.text, 'Sure?')
        self.assertEqual(len(rows(t.Summary())), 5)                                 # Nothing lost on one click.
        reset.OnClick(reset)
        self.assertEqual(rows(t.Summary()), [])
        self.assertEqual(reset.caption.text, 'Reset')
        self.assertEqual(len(list(c.lua.globals().WowTogetherGoldDB.trackerHistory.values())), 0)   # Thrown away: not kept.

    def test_stop_ends_the_session_and_keeps_it(self):
        c, t = self.session()
        self.assertEqual([t.window.toggle.caption.text, t.window.stop.caption.text, t.window.reset.caption.text], ['Pause', 'Stop', 'Reset'])
        t.window.stop.OnClick(t.window.stop)
        history = list(c.lua.globals().WowTogetherGoldDB.trackerHistory.values())
        self.assertEqual(len(history), 1)                                           # Twenty-three minutes: kept.
        self.assertEqual(history[0].seconds, 1395)
        self.assertEqual(rows(t.Summary()), [])                                     # And a clean slate.
        self.assertFalse(t.window.stop.enabled)                                     # Nothing to stop now.

    def test_folding_keeps_the_figures_on_one_line(self):
        c, t = self.session()
        t.window.fold.OnClick(t.window.fold)
        self.assertFalse(t.window.body.IsShown(t.window.body))
        self.assertIn('00:23:15', t.window.clock.text)
        self.assertIn('/h', t.window.clock.text)
        self.assertIn('3g 76s', t.window.clock.text)
        t.window.fold.OnClick(t.window.fold)
        self.assertTrue(t.window.body.IsShown(t.window.body))

    def test_the_command_opens_and_closes_it(self):
        c, t = farm()
        slash = c.lua.globals().SlashCmdList["WOWTOGETHER"]
        slash('gold')
        self.assertTrue(t.window.IsShown(t.window))
        slash('gold')
        self.assertFalse(t.window.IsShown(t.window))


class PriceScanTests(unittest.TestCase):
    """The scan prices what farms drop, what was seen and what was farmed; it lives at the auction house."""

    def prepared(self, farm_items=(1206, 1705, 2771), seen=(4306, 3924), loot=True):
        c, t = farm()
        gold_host.quote(c, 2771, 310)                                              # Ten minutes old: fresh.
        if loot:
            for item, count in ((2771, 42), (2775, 6), (3924, 7)):
                gold_host.loot(c, item, count)
        c.lua.execute('''
            local space, farmItems, seenItems = ...
            scans, atAuction, reranked = {}, false, 0
            WowTogetherModuleAPI.AuctionHouseVisible = function() return atAuction end
            WowTogetherModuleAPI.StartFarmCandidateScan = function(ids, onQuote)
                if not atAuction then return false, "Open the auction house first." end
                scans[#scans + 1] = {ids = ids, onQuote = onQuote}
                return true
            end
            space.GoldFarms.ScanItems = function() return farmItems end
            space.GoldFarms.PricesChanged = function() reranked = reranked + 1 end
            space.GoldObservations.SeenItems = function() return seenItems end
        ''', c.lua.globals().goldSpace, c.lua.table_from(list(farm_items)), c.lua.table_from(list(seen)))
        return c, t

    def plan(self, t):
        ids, groups = t.ScanPlan()
        return list(ids.values()), groups

    def test_it_covers_what_farms_drop_what_was_seen_and_what_was_farmed(self):
        c, t = self.prepared()
        ids, groups = self.plan(t)
        self.assertEqual(ids, [2775, 4306, 1206, 1705])        # Farmed, then seen, then farm drops; each once.
        self.assertEqual((groups.farmed, groups.seen, groups.farms, groups.total), (2, 1, 2, 5))
        self.assertEqual(groups.fresh, 1)                       # Tin Ore was priced ten minutes ago: left alone.
        self.assertNotIn(3924, ids)                             # Grey: a vendor buys it; nobody lists it.

    def test_there_is_something_to_scan_before_any_farming(self):
        # "Farm something first" was the wrong idea: the scan is what tells you where to farm.
        c, t = self.prepared(loot=False, seen=())
        ids, groups = self.plan(t)
        self.assertEqual(ids, [1206, 1705])                     # (Tin Ore, also a farm drop, is already fresh.)
        t.ShowScan(); panel = t.scanPanel
        self.assertEqual(panel.counts[1].label.text, 'Dropped by farms near your level')
        self.assertEqual(panel.counts[1].count.text, '3')
        self.assertEqual(panel.plan.text, '2 to look up, 1 already priced or checked.')
        self.assertEqual(panel.go.caption.text, 'Scan 2 items')
        self.assertNotIn('Farm something first', panel.status.text + panel.plan.text)

    def test_the_button_only_works_at_an_auction_house(self):
        c, t = self.prepared(); g = c.lua.globals()
        t.ShowScan(); panel = t.scanPanel
        self.assertEqual(panel.status.text, 'Open an auction house to scan.')
        self.assertFalse(panel.go.enabled)
        g.atAuction = True
        t.RefreshScan()
        self.assertTrue(panel.go.enabled)
        self.assertEqual(panel.status.text, 'Ready.')

    def test_a_long_list_is_scanned_in_batches_and_the_farms_are_ranked_again(self):
        items = list(range(50001, 50121))                                           # 120 farm drops.
        c, t = self.prepared(farm_items=items, seen=(), loot=False); g = c.lua.globals()
        g.atAuction = True
        t.ShowScan(); panel = t.scanPanel
        self.assertTrue(t.StartScan())
        self.assertFalse(t.StartScan())                                             # One scan at a time.
        sizes = []
        for batch in range(1, 4):
            ids = list(g.scans[batch].ids.values()); sizes.append(len(ids))
            self.assertEqual(panel.go.caption.text, 'Stop')
            for item in ids:
                price = (item - 50000) * 100 if item % 2 == 0 else None             # Half of them are listed.
                g.scans[batch].onQuote(c.lua.table_from({'itemID': item, 'minBuyout': price}))
            c.drain()                                                                # The next batch starts by itself.
        self.assertEqual(sizes, [50, 50, 20])
        self.assertEqual(panel.status.text, 'Done: 60 of 120 are for sale and now have a price. The rest are not listed. Farms are ranked with them.')
        self.assertEqual(g.reranked, 1)
        self.assertEqual(panel.foundHeading.text, 'WORTH MOST')
        self.assertEqual(panel.rows[1].price.text, '1g 20s each')                   # The dearest thing it found, first.
        self.assertEqual(panel.go.caption.text, 'Up to date')                       # Unlisted items are not asked about again...
        self.assertEqual(panel.plan.text, 'Nothing left to look up: all 120 are priced or were checked in the last hour.')
        c.lua.execute('clock = clock + 3700')
        t.RefreshScan()
        self.assertEqual(panel.go.caption.text, 'Scan 120 items')                   # ...until an hour has passed.

    def test_closing_the_auction_house_stops_the_scan_and_says_how_far_it_got(self):
        c, t = self.prepared(farm_items=list(range(50001, 50061)), seen=(), loot=False); g = c.lua.globals()
        g.atAuction = True
        t.ShowScan(); t.StartScan()
        for item in list(g.scans[1].ids.values())[:10]:
            g.scans[1].onQuote(c.lua.table_from({'itemID': item, 'minBuyout': 500}))
        c.ns.frame.OnEvent(c.ns.frame, 'AUCTION_HOUSE_CLOSED')
        self.assertIn('closed after 10 of 60', t.scanPanel.status.text)
        self.assertEqual(g.reranked, 1)                                             # What it did find is used.

    def test_a_scan_that_cannot_start_says_why(self):
        c, t = self.prepared()
        t.ShowScan()
        self.assertFalse(t.StartScan())
        self.assertEqual(t.scanPanel.status.text, 'Open the auction house first.')

    def test_the_button_sits_under_the_auction_window_and_the_panel_beside_it(self):
        c, t = self.prepared()
        c.lua.execute('AuctionHouseFrame = CreateFrame("Frame", "AuctionHouseFrame", UIParent)')
        c.ns.frame.OnEvent(c.ns.frame, 'AUCTION_HOUSE_SHOW')
        button = t.auctionButton
        self.assertEqual((button.point[1], button.point[3]), ('TOPRIGHT', 'BOTTOMRIGHT'))   # Below the window, at the right.
        self.assertTrue(t.scanPanel.IsShown(t.scanPanel))                                   # Offered at once: there are prices to look up.
        self.assertEqual((t.scanPanel.point[1], t.scanPanel.point[3]), ('TOPLEFT', 'TOPRIGHT'))


class ScanEverythingTests(unittest.TestCase):
    """The panel offers a scan of the whole auction house, and asks before starting."""

    def panel(self, supported=True):
        c, t = farm()
        c.lua.execute('''
            local space, supported = ...
            atAuction, started, stopped, reranked = true, 0, 0, 0
            WowTogetherModuleAPI.AuctionHouseVisible = function() return atAuction end
            WowTogetherModuleAPI.FullPriceScanSupported = function() return supported end
            WowTogetherModuleAPI.StartFullPriceScan = function(onProgress) started = started + 1; report = onProgress; return true end
            WowTogetherModuleAPI.StopFullPriceScan = function() stopped = stopped + 1; report({running = false, message = "Stopped. 40 prices were saved.", items = 40}) end
            space.GoldFarms.PricesChanged = function() reranked = reranked + 1 end
            space.GoldFarms.ScanItems = function() return {} end
            space.GoldObservations.SeenItems = function() return {} end
        ''', c.lua.globals().goldSpace, supported)
        t.ShowScan()
        return c, t, t.scanPanel

    def test_it_asks_first_and_says_how_long_it_takes(self):
        c, t, panel = self.panel(); g = c.lua.globals()
        self.assertTrue(panel.everything.IsShown(panel.everything))
        panel.everything.OnClick(panel.everything)
        self.assertEqual(g.started, 0)                                              # Not yet.
        self.assertTrue(panel.confirm.IsShown(panel.confirm))
        self.assertIn('a couple of minutes', panel.confirm.text)
        self.assertIn('materials first', panel.confirm.text)
        self.assertFalse(panel.everythingNote.IsShown(panel.everythingNote))        # Nothing else is drawn over the question.
        self.assertFalse(panel.go.IsShown(panel.go))
        panel.no.OnClick(panel.no)
        self.assertFalse(panel.confirm.IsShown(panel.confirm))
        self.assertEqual(g.started, 0)
        panel.everything.OnClick(panel.everything)
        panel.yes.OnClick(panel.yes)
        self.assertEqual(g.started, 1)

    def test_progress_is_shown_and_the_farms_are_ranked_again_at_the_end(self):
        c, t, panel = self.panel(); g = c.lua.globals()
        panel.everything.OnClick(panel.everything); panel.yes.OnClick(panel.yes)
        g.report(c.lua.table_from({'running': True, 'category': 2, 'categories': 12, 'name': 'Consumables', 'message': 'Scanning Consumables…', 'items': 310}))
        self.assertEqual(panel.status.text, 'Scanning Consumables…  310 items so far.')
        self.assertEqual(panel.go.caption.text, 'Stop')
        self.assertFalse(panel.everything.IsShown(panel.everything))
        g.report(c.lua.table_from({'running': False, 'completed': True, 'category': 13, 'categories': 12, 'items': 1840,
                                   'message': 'Done: 1840 items priced from 5210 listings.'}))
        self.assertEqual(panel.status.text, 'Done: 1840 items priced from 5210 listings.')
        self.assertEqual(g.reranked, 1)
        self.assertTrue(panel.everything.IsShown(panel.everything))

    def test_stop_ends_it(self):
        c, t, panel = self.panel(); g = c.lua.globals()
        panel.everything.OnClick(panel.everything); panel.yes.OnClick(panel.yes)
        g.report(c.lua.table_from({'running': True, 'category': 1, 'categories': 12, 'message': 'Scanning Trade goods…', 'items': 0}))
        panel.go.OnClick(panel.go)
        self.assertEqual(g.stopped, 1)
        self.assertEqual(panel.status.text, 'Stopped. 40 prices were saved.')

    def test_a_client_that_cannot_browse_everything_only_offers_the_item_scan(self):
        c, t, panel = self.panel(supported=False)
        self.assertFalse(panel.everything.IsShown(panel.everything))


class FarmTooltipTests(unittest.TestCase):
    """A farm's tooltip is a short summary, not the raw working."""

    def test_it_names_the_pace_the_few_items_that_matter_and_where_prices_came_from(self):
        c, t = farm()
        c.lua.execute('''
            lines = {}
            GameTooltip = {SetOwner = function() end, Show = function() end, Hide = function() end,
                AddLine = function(self, text) lines[#lines + 1] = text end,
                AddDoubleLine = function(self, left, right) lines[#lines + 1] = left .. " | " .. right end}
        ''')
        farm_row = c.lua.table_from({'name': 'Bloodscalp Scout', 'zone': 'Stranglethorn Vale', 'kind': 'mob', 'estimate': 53000,
            'pace': 120, 'paceAssumed': True, 'paceUnit': 'kills', 'routable': True, 'measured': False,
            'top': [{'itemID': 4306, 'chance': 0.295, 'each': 150, 'auction': False, 'share': 0.9},
                    {'itemID': 1705, 'chance': 0.0002, 'each': 600, 'auction': False, 'share': 0.01}],
            'others': 73, 'auctionPriced': 0, 'vendorPriced': 2}, recursive=True)
        t.FarmTooltip(c.lua.table(), farm_row)
        lines = list(c.lua.globals().lines.values())
        self.assertLessEqual(len(lines), 14)                                        # It was a hundred lines of working.
        self.assertEqual(lines[0], 'Bloodscalp Scout')
        self.assertIn('Estimate | 5.3g an hour', lines)
        self.assertIn('Pace | 120 kills an hour, assumed', lines)
        self.assertTrue(any('Silk Cloth | 30%  •  1s 50c' in line for line in lines))
        self.assertTrue(any('Lesser Moonstone | 0.02%  •  6s' in line for line in lines))
        self.assertIn('and 73 other drops', lines)
        self.assertTrue(any('Priced at vendor value only' in line for line in lines))
        self.assertFalse(any('CMaNGOS' in line or 'lower bound' in line for line in lines))
        self.assertEqual(t.FarmBasis(farm_row), 'loop  •  farm data  •  vendor prices')


class ApiTests(unittest.TestCase):
    def test_the_gold_package_can_draw_in_the_addons_style_without_touching_its_palette(self):
        c, t = farm()
        api = c.lua.globals().WowTogetherModuleAPI
        for name in ('UIPanel', 'UILabel', 'UIButton', 'UIClose', 'UIHelp'):
            self.assertIsNotNone(api[name], name)
        api.UIColors.gold[1] = 0
        self.assertNotEqual(c.ns.UIColors.gold[1], 0)                               # A copy, not the core's own table.


if __name__ == '__main__':
    unittest.main()


class GoldPageTests(unittest.TestCase):
    """The Gold page in the main window: everything is a button, nothing a typed command."""

    def page(self, saved=None):
        c, t = farm(saved)
        page = c.lua.eval('function() local f = CreateFrame("Frame", nil, UIParent); f:SetSize(584, 400); return f end')()
        return c, t, page

    def test_the_page_shows_the_session_and_its_buttons(self):
        c, t, page = self.page()
        gold_host.quote(c, 2771, 310)
        gold_host.loot(c, 2771, 42); gold_host.loot(c, 2836, 8)
        c.lua.execute('clock = clock + 240')
        t.RenderPage(page)
        view = page.goldPage
        self.assertEqual(view.clock.text, '00:04:00')
        self.assertEqual([tile.caption.text for tile in view.tiles.values()], ['GOLD PER HOUR', 'TOTAL', 'ITEMS PER HOUR', 'XP PER HOUR'])
        self.assertEqual(view.rows[1].name.text, 'Tin Ore')
        self.assertEqual(view.toggle.caption.text, 'Pause')
        self.assertEqual(view.window.caption.text, 'Show on screen')
        view.toggle.OnClick(view.toggle)
        self.assertFalse(t.Running())
        self.assertEqual(view.toggle.caption.text, 'Resume')
        view.window.OnClick(view.window)
        self.assertTrue(t.window.IsShown(t.window))                                 # The session, on screen.
        self.assertEqual(view.window.caption.text, 'Hide from screen')
        self.assertIsNone(view.scan)                                                # The scan belongs to the auction house.
        self.assertIsNone(t.window.body.scan)

    def test_the_page_has_pause_stop_and_reset(self):
        c, t, page = self.page()
        for _ in range(4):                                                          # Ten minutes, looting as it goes.
            gold_host.loot(c, 2771, 4)
            c.lua.execute('clock = clock + 150')
        t.RenderPage(page); view = page.goldPage
        self.assertEqual([view.toggle.caption.text, view.stop.caption.text, view.reset.caption.text], ['Pause', 'Stop', 'Reset'])
        view.stop.OnClick(view.stop)
        self.assertEqual(len(list(c.lua.globals().WowTogetherGoldDB.trackerHistory.values())), 1)
        self.assertEqual(rows(t.Summary()), [])

    def test_reset_on_the_page_takes_two_clicks_too(self):
        c, t, page = self.page()
        gold_host.loot(c, 2771, 4)
        t.RenderPage(page); view = page.goldPage
        view.reset.OnClick(view.reset)
        self.assertEqual(view.reset.caption.text, 'Sure?')
        self.assertEqual(len(rows(t.Summary())), 1)
        view.reset.OnClick(view.reset)
        self.assertEqual(rows(t.Summary()), [])

    def test_suggested_farms_have_start_and_stop_buttons(self):
        c, t, page = self.page()
        c.lua.execute('''
            local space = ...
            started, stopped = {}, 0
            active = nil
            space.GoldFarms.Suggestions = function()
                return {{key = "mob:1", name = "Syndicate Footpad", zone = "Hillsbrad Foothills", estimate = 250000,
                         basis = "120 kills an hour (assumed)", routable = true, active = active == "mob:1"},
                        {key = "gather:tin", name = "Tin Vein", zone = "Hillsbrad Foothills", estimate = 180000,
                         basis = "30 nodes an hour (assumed)", routable = false, active = false}}
            end
            space.GoldFarms.Start = function(key) started[#started + 1] = key; active = key; return true end
            space.GoldFarms.Stop = function() stopped = stopped + 1; active = nil; return true end
        ''', self.space(c))
        t.RenderPage(page); view = page.goldPage
        first = view.farms[1]
        self.assertEqual(first.name.text, 'Syndicate Footpad  •  Hillsbrad Foothills')
        self.assertEqual(first.estimate.text, '25.0g/h')
        self.assertTrue(first.basis.text.startswith('loop'))                        # It can lead you round.
        self.assertTrue(view.farms[2].basis.text.startswith('no route'))            # It can only name the zone.
        self.assertEqual(first.go.caption.text, 'Start route')
        self.assertEqual(view.farms[2].go.caption.text, 'Track')                    # And its button does not promise a route.
        first.go.OnClick(first.go)
        self.assertEqual(list(c.lua.globals().started.values()), ['mob:1'])
        self.assertEqual(first.go.caption.text, 'Stop')
        first.go.OnClick(first.go)
        self.assertEqual(c.lua.globals().stopped, 1)

    def space(self, c):
        return c.lua.globals().goldSpace

    def test_past_sessions_are_listed_with_what_they_mostly_were(self):
        c, t, page = self.page({'trackerHistory': [
            {'zone': 'Stranglethorn Vale', 'seconds': 3300, 'total': 412000, 'perHour': 449400,
             'top': [{'itemID': 4306, 'name': 'Silk Cloth', 'count': 60, 'value': 9000}]}]})
        t.RenderPage(page); view = page.goldPage
        self.assertEqual(view.history[1].name.text, 'Stranglethorn Vale  •  mostly Silk Cloth')
        self.assertEqual((view.history[1].count.text, view.history[1].value.text), ('55 min', '44.9g/h'))


class FarmKindTests(unittest.TestCase):
    """Farms are offered by kind: killing, and each gathering profession."""

    def page(self):
        c, t = farm()
        page = c.lua.eval('function() local f = CreateFrame("Frame", nil, UIParent); f:SetSize(900, 400); return f end')()
        c.lua.execute('''
            local space = ...
            asked = {}
            local all = {
                {key = "k1", name = "Rock Elemental", zone = "Badlands", category = "Killing", estimate = 104000, routable = true},
                {key = "m1", name = "Iron Deposit", zone = "Arathi Highlands", category = "Mining", estimate = 96000, routable = false},
                {key = "k2", name = "Young Panther", zone = "Stranglethorn Vale", category = "Killing", estimate = 69000, routable = true},
                {key = "f1", name = "Water tier 4", zone = "Stranglethorn Vale", category = "Fishing", estimate = 41000, routable = false},
            }
            space.GoldFarms.CATEGORIES = {"Killing", "Mining", "Herbalism", "Skinning", "Fishing"}
            space.GoldFarms.Categories = function() return {Killing = 2, Mining = 1, Herbalism = 0, Skinning = 0, Fishing = 1} end
            space.GoldFarms.Suggestions = function(limit, category)
                asked[#asked + 1] = category or "best"
                local list = {}
                for _, farm in ipairs(all) do
                    if (category == nil or farm.category == category) and #list < limit then list[#list + 1] = farm end
                end
                return list
            end
        ''', c.lua.globals().goldSpace)
        t.RenderPage(page)
        return c, t, page, page.goldPage

    def names(self, view):
        return [row.name.text.split('  •  ')[0] for row in view.farms.values() if row.IsShown(row)]

    def chip(self, view, title):
        return next(chip for chip in view.chips.values() if chip.title == title)

    def test_there_is_a_chip_for_the_best_for_killing_and_for_each_profession(self):
        c, t, page, view = self.page()
        self.assertEqual([chip.title for chip in view.chips.values()], ['Best', 'Killing', 'Mining', 'Herbs', 'Skinning', 'Fishing'])
        self.assertEqual(self.names(view), ['Rock Elemental', 'Iron Deposit', 'Young Panther', 'Fishing'])   # Best: every kind, by estimate.
        self.assertTrue(self.chip(view, 'Best').primary)

    def test_a_chip_narrows_the_list_to_its_kind(self):
        c, t, page, view = self.page()
        killing = self.chip(view, 'Killing')
        killing.OnClick(killing)
        self.assertEqual(self.names(view), ['Rock Elemental', 'Young Panther'])
        self.assertTrue(killing.primary)
        self.assertFalse(self.chip(view, 'Best').primary)
        mining = self.chip(view, 'Mining')
        mining.OnClick(mining)
        self.assertEqual(self.names(view), ['Iron Deposit'])
        self.assertEqual(c.lua.globals().WowTogetherGoldDB.settings['gold.farmKind'], 'Mining')        # Remembered.

    def test_a_kind_with_nothing_for_this_character_cannot_be_chosen(self):
        c, t, page, view = self.page()
        herbs = self.chip(view, 'Herbs')
        self.assertEqual(herbs.count, 0)
        herbs.OnClick(herbs)
        self.assertEqual(self.names(view), ['Rock Elemental', 'Iron Deposit', 'Young Panther', 'Fishing'])   # Still the best of everything.

    def test_a_remembered_kind_that_has_emptied_falls_back_to_the_best(self):
        c, t, page, view = self.page()
        c.lua.execute('WowTogetherGoldDB.settings["gold.farmKind"] = "Skinning"')
        t.RenderPage(page)
        self.assertEqual(list(c.lua.globals().asked.values())[-1], 'best')


class OwnFarmTests(unittest.TestCase):
    """What the player has actually farmed is offered as a farm, valued at today's prices."""

    def fish(self, c, minutes=20, zone=None):
        """A stretch of fishing: the game says each loot is a catch."""
        if zone:
            c.lua.globals().zoneText = zone
        c.lua.execute('fishing = true; function IsFishingLoot() return fishing end')
        for _ in range(minutes * 60 // 60):
            c.ns.frame.OnEvent(c.ns.frame, 'LOOT_READY')
            gold_host.loot(c, 6359, 1)
            c.lua.execute('clock = clock + 60')

    def own(self, t):
        return [(f.name, f.zone, f.category, f.minutes) for f in t.OwnFarms().values()]

    def test_a_fishing_session_is_recognised_as_fishing(self):
        c, t = farm()
        self.fish(c, minutes=20)
        self.assertEqual(t.Summary().kind, 'Fishing')
        self.assertEqual(self.own(t), [('Your fishing', 'Hillsbrad Foothills', 'Fishing', 20)])

    def test_kills_veins_and_skins_are_told_apart(self):
        c, t = farm(); fire = c.ns.frame.OnEvent
        c.lua.execute('''
            function IsFishingLoot() return false end
            source = "Creature-0-1-2-3-4-5"
            function GetLootSourceInfo() return source end
            spells = {[2575] = "Mining", [8613] = "Skinning", [2366] = "Herb Gathering"}
            function GetSpellInfo(id) return spells[id] end
        ''')
        fire(c.ns.frame, 'LOOT_READY'); gold_host.loot(c, 4306, 3)                          # A corpse.
        c.lua.execute('source = "GameObject-0-1-2-3-4-5"')
        fire(c.ns.frame, 'UNIT_SPELLCAST_SUCCEEDED', 'player', 'cast', 2575)
        fire(c.ns.frame, 'LOOT_READY'); gold_host.loot(c, 2771, 4)                          # A vein.
        c.lua.execute('source = "Creature-0-1-2-3-4-6"')
        fire(c.ns.frame, 'UNIT_SPELLCAST_SUCCEEDED', 'player', 'cast', 8613)
        fire(c.ns.frame, 'LOOT_READY'); gold_host.loot(c, 2319, 2)                          # A skinned corpse.
        kinds = c.lua.globals().WowTogetherGoldDB.tracker.kinds
        self.assertEqual((kinds.Killing, kinds.Mining, kinds.Skinning), (3, 4, 2))

    def test_a_session_under_ten_minutes_is_not_a_farm_yet(self):
        c, t = farm()
        self.fish(c, minutes=6)
        self.assertEqual(self.own(t), [])

    def test_past_sessions_are_valued_at_todays_prices(self):
        c, t = farm()
        self.fish(c, minutes=20)                                                            # 20 fish, 5c each at a vendor.
        c.lua.execute('clock = clock + 2000'); t.Tick()                                     # The session ends itself.
        before = list(t.OwnFarms().values())[0].estimate
        gold_host.quote(c, 6359, 90)                                                        # A scan finds they sell for 90c.
        after = list(t.OwnFarms().values())[0].estimate
        self.assertGreater(after, before * 10)

    def test_the_best_session_in_each_zone_of_each_kind_is_the_one_shown(self):
        c, t = farm({'trackerHistory': [
            {'zone': 'Stranglethorn Vale', 'seconds': 1800, 'total': 40000, 'perHour': 80000, 'kind': 'Fishing', 'items': {6359: 100}, 'coin': 0},
            {'zone': 'Stranglethorn Vale', 'seconds': 1800, 'total': 90000, 'perHour': 180000, 'kind': 'Fishing', 'items': {6359: 400}, 'coin': 0},
            {'zone': 'Stranglethorn Vale', 'seconds': 1800, 'total': 50000, 'perHour': 100000, 'kind': 'Killing', 'items': {4306: 30}, 'coin': 0}]})
        farms = self.own(t)
        self.assertEqual(sorted(farms), [('Your fishing', 'Stranglethorn Vale', 'Fishing', 30), ('Your killing', 'Stranglethorn Vale', 'Killing', 30)])
        fishing = next(f for f in t.OwnFarms().values() if f.category == 'Fishing')
        self.assertEqual(fishing.estimate, 400 * 5 * 2)                                     # The 400-fish session, not the 100.

    def test_a_session_saved_by_an_older_build_still_counts(self):
        c, t = farm({'trackerHistory': [
            {'zone': 'Thunder Bluff', 'seconds': 3480, 'total': 184, 'perHour': 190,
             'top': [{'itemID': 6359, 'name': 'Firefin Snapper', 'count': 68, 'value': 68}]}]})
        farms = list(t.OwnFarms().values())
        self.assertEqual((farms[0].name, farms[0].zone, farms[0].category), ('Your session', 'Thunder Bluff', None))
        gold_host.quote(c, 6359, 90)
        self.assertGreater(list(t.OwnFarms().values())[0].estimate, 6000)                   # Its top item, at the new price.

    def test_it_appears_under_its_chip_on_the_gold_page(self):
        c, t = farm()
        self.fish(c, minutes=20, zone='Stranglethorn Vale')
        page = c.lua.eval('function() local f = CreateFrame("Frame", nil, UIParent); f:SetSize(900, 400); return f end')()
        t.RenderPage(page); view = page.goldPage
        chip = next(chip for chip in view.chips.values() if chip.title == 'Fishing')
        self.assertEqual(chip.count, 1)                                                     # No longer empty.
        first = view.farms[1]
        self.assertEqual(first.name.text, 'Your fishing  •  Stranglethorn Vale')
        self.assertEqual(first.basis.text, 'measured over 20 min, this session')
        self.assertEqual(first.go.caption.text, 'Track')
        # The farm data has no fishing farms at all; the chip must still open on the player's own.
        c.lua.execute('''
            local space = ...
            space.GoldFarms.CATEGORIES = {"Killing", "Mining", "Herbalism", "Skinning", "Fishing"}
            space.GoldFarms.Categories = function() return {Killing = 2, Mining = 0, Herbalism = 0, Skinning = 0, Fishing = 0} end
            space.GoldFarms.Suggestions = function(limit, category)
                if category == "Fishing" then return {} end
                return {{key = "k1", name = "Rock Elemental", zone = "Badlands", category = "Killing", estimate = 119000, routable = true, paceAssumed = true},
                        {key = "k2", name = "Young Panther", zone = "Stranglethorn Vale", category = "Killing", estimate = 74000, routable = true, paceAssumed = true}}
            end
        ''', c.lua.globals().goldSpace)
        t.RenderPage(page)
        killing = next(chip for chip in view.chips.values() if chip.title == 'Killing')
        killing.OnClick(killing)
        self.assertTrue(killing.primary)
        chip.OnClick(chip)                                                          # What did nothing in play.
        self.assertTrue(chip.primary)
        self.assertFalse(killing.primary)
        shown = [row.name.text for row in view.farms.values() if row.IsShown(row)]
        self.assertEqual(shown, ['Your fishing  •  Stranglethorn Vale'])            # Only fishing, and it is the player's.


    def test_a_measured_rate_outranks_a_somewhat_higher_estimate_but_not_a_much_higher_one(self):
        c, t = farm({'trackerHistory': [
            {'zone': 'Stranglethorn Vale', 'seconds': 1800, 'total': 40000, 'perHour': 80000, 'kind': 'Fishing', 'items': {6359: 8000}, 'coin': 0}]})
        c.lua.execute('''
            local space = ...
            space.GoldFarms.CATEGORIES = {"Killing", "Mining", "Herbalism", "Skinning", "Fishing"}
            space.GoldFarms.Categories = function() return {Killing = 2, Mining = 0, Herbalism = 0, Skinning = 0, Fishing = 0} end
            space.GoldFarms.Suggestions = function()
                return {{key = "far", name = "Far Better", zone = "Badlands", category = "Killing", estimate = 200000, routable = true, paceAssumed = true},
                        {key = "bit", name = "A Bit Better", zone = "Badlands", category = "Killing", estimate = 110000, routable = true, paceAssumed = true}}
            end
        ''', c.lua.globals().goldSpace)
        page = c.lua.eval('function() local f = CreateFrame("Frame", nil, UIParent); f:SetSize(900, 400); return f end')()
        t.RenderPage(page)
        names = [row.name.text.split('  •  ')[0] for row in page.goldPage.farms.values() if row.IsShown(row)]
        # Yours measured 8g an hour. An estimate of 20g still leads; an estimate of 11g does not.
        self.assertEqual(names, ['Far Better', 'Your fishing', 'A Bit Better'])
        self.assertEqual(page.goldPage.farms[3].estimate.text, '11.0g/h')                   # The figure shown is the real one.

class FarmListScrollTests(unittest.TestCase):
    """All the farms can be reached: five show, the rest scroll, best first."""

    def page(self, count=12):
        c, t = farm()
        page = c.lua.eval('function() local f = CreateFrame("Frame", nil, UIParent); f:SetSize(900, 400); return f end')()
        c.lua.execute('''
            local space, count = ...
            asked = nil
            space.GoldFarms.CATEGORIES = {"Killing", "Mining", "Herbalism", "Skinning", "Fishing"}
            space.GoldFarms.Categories = function() return {Killing = count, Mining = 0, Herbalism = 0, Skinning = 0, Fishing = 0} end
            space.GoldFarms.Suggestions = function(limit)
                asked = limit
                local list = {}
                for index = 1, math.min(limit, count) do
                    list[index] = {key = "k" .. index, name = "Farm " .. index, zone = "Zone", category = "Killing",
                        estimate = (count - index + 1) * 10000, routable = true, paceAssumed = true}
                end
                return list
            end
        ''', c.lua.globals().goldSpace, count)
        t.RenderPage(page)
        return c, t, page, page.goldPage

    def test_every_farm_gets_a_row_in_order_of_gold_per_hour(self):
        c, t, page, view = self.page(12)
        self.assertGreaterEqual(c.lua.globals().asked, 12)                          # It asks for the whole list, not five.
        shown = [(row.name.text, row.estimate.text) for row in view.farms.values() if row.IsShown(row)]
        self.assertEqual(len(shown), 12)
        self.assertEqual(shown[0], ('Farm 1  •  Zone', '12.0g/h'))
        self.assertEqual(shown[-1], ('Farm 12  •  Zone', '1.0g/h'))
        self.assertEqual(view.farmCount.text, '12 farms, best first: scroll for more')

    def test_the_wheel_moves_one_farm_at_a_time_and_stops_at_both_ends(self):
        c, t, page, view = self.page(12)
        self.assertEqual(view.farmOffset, 0)
        t.ScrollFarms(page, 1)
        self.assertEqual(view.farmOffset, 50)
        t.ScrollFarms(page, 100)
        self.assertEqual(view.farmOffset, (12 - 5) * 50)                            # The last five are showing.
        t.ScrollFarms(page, -100)
        self.assertEqual(view.farmOffset, 0)
        view.farmScroll.OnMouseWheel(view.farmScroll, -1)                           # Wheel down.
        self.assertEqual(view.farmOffset, 50)

    def test_a_short_list_has_no_scroll_bar_or_count(self):
        c, t, page, view = self.page(3)
        self.assertEqual(view.farmCount.text, '')
        self.assertFalse(view.farmThumb.IsShown(view.farmThumb))
        t.ScrollFarms(page, 3)
        self.assertEqual(view.farmOffset, 0)

    def test_choosing_another_kind_starts_its_list_at_the_top(self):
        c, t, page, view = self.page(12)
        t.ScrollFarms(page, 4)
        killing = next(chip for chip in view.chips.values() if chip.title == 'Killing')
        killing.OnClick(killing)
        self.assertEqual(view.farmOffset, 0)


class EntryPointTests(unittest.TestCase):
    """Where the windows open from, without typing anything."""

    def test_starting_a_suggested_farm_puts_the_tracker_on_screen(self):
        c, t = farm()
        space = c.lua.globals().goldSpace
        self.assertIsNone(t.window)
        space.GoldFarms.Start('no such farm')                                       # Even a farm that cannot start shows why, there.
        self.assertTrue(t.window.IsShown(t.window))

    def test_the_auction_house_gets_a_price_scan_button(self):
        c, t = farm()
        c.lua.execute('AuctionHouseFrame = CreateFrame("Frame", "AuctionHouseFrame", UIParent)')
        c.ns.frame.OnEvent(c.ns.frame, 'AUCTION_HOUSE_SHOW')
        button = t.auctionButton
        self.assertEqual(button.caption.text, 'Price scan')
        self.assertIsNone(t.scanPanel)                                              # Nothing to price yet: it stays out of the way.
        button.OnClick(button)
        self.assertTrue(t.scanPanel.IsShown(t.scanPanel))

    def test_a_button_can_open_the_gold_page_in_the_main_window(self):
        c, t = farm()
        api = c.lua.globals().WowTogetherModuleAPI
        self.assertTrue(api.OpenModulePage('Gold'))
        self.assertTrue(c.ns.window.IsShown(c.ns.window))
        self.assertEqual(c.ns.filter, 'module:gold')
        self.assertFalse(api.OpenModulePage('Nobody'))
