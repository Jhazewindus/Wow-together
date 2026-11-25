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


class HistoryTests(unittest.TestCase):
    def test_a_real_session_is_kept_on_reset_and_a_short_one_is_not(self):
        c, t = farm()
        gold_host.quote(c, 2771, 300)
        gold_host.loot(c, 2771, 20)
        c.lua.execute('clock = clock + 120')
        t.Reset()
        self.assertEqual(len(list(c.lua.globals().WowTogetherGoldDB.trackerHistory.values())), 0)   # Two minutes: not a session.
        gold_host.loot(c, 2771, 20)
        c.lua.execute('clock = clock + 1200')
        t.Reset()
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

    def test_reset_takes_two_clicks(self):
        c, t = self.session()
        reset = t.window.reset
        reset.OnClick(reset)
        self.assertEqual(reset.caption.text, 'Sure?')
        self.assertEqual(len(rows(t.Summary())), 5)                                 # Nothing lost on one click.
        reset.OnClick(reset)
        self.assertEqual(rows(t.Summary()), [])
        self.assertEqual(reset.caption.text, 'Reset')

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
        self.assertEqual(panel.plan.text, '2 to look up, 1 looked up in the last hour.')
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
        self.assertEqual(panel.plan.text, 'All 120 were looked up less than an hour ago.')
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
        self.assertTrue(view.farms[2].basis.text.startswith('zone only'))           # It can only name the zone.
        self.assertEqual(first.go.caption.text, 'Start')
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
        self.assertEqual(self.names(view), ['Rock Elemental', 'Iron Deposit', 'Young Panther', 'Water tier 4'])   # Best: every kind, by estimate.
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
        self.assertEqual(self.names(view), ['Rock Elemental', 'Iron Deposit', 'Young Panther', 'Water tier 4'])   # Still the best of everything.

    def test_a_remembered_kind_that_has_emptied_falls_back_to_the_best(self):
        c, t, page, view = self.page()
        c.lua.execute('WowTogetherGoldDB.settings["gold.farmKind"] = "Skinning"')
        t.RenderPage(page)
        self.assertEqual(list(c.lua.globals().asked.values())[-1], 'best')


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
