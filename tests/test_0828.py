"""Dungeon sync must not rebuild hidden browsers or lose shared event handlers.

The shipped catalogue exercises the reported workload. These are Lua 5.1 host
checks, not a measurement of the beta client's script watchdog or frame rate.
"""
import unittest

from test_addon import Client
from test_063 import guide_client
from test_074 import scanning_client
from test_0815 import entries


def observe_browser(c):
    c.lua.globals().regressionNS = c.ns
    c.lua.execute('''
        browserReads, dashboardReads = 0, 0
        local browser, render = regressionNS.GuideBrowserChoices, regressionNS.Render
        regressionNS.GuideBrowserChoices=function(...)
            browserReads=browserReads+1; return browser(...)
        end
        regressionNS.Render=function(...)
            dashboardReads=dashboardReads+1; return render(...)
        end
    ''')


class DungeonRefreshTests(unittest.TestCase):
    def dungeon_client(self):
        c = Client(quests=(962, 1486, 1491), use_catalogue=True, default_guide=True)
        c.guide_environment(level=23)
        c.lua.execute('''
            function UnitClass() return 'Priest','PRIEST',5 end
            function UnitRace() return 'Undead','Scourge',5 end
            function GetZoneText() return 'Wailing Caverns' end
            C_Map.GetBestMapForUnit=function() return nil end
        ''')
        c.ns.ReadProfile()
        c.ns.filter, c.ns.guideLevel = 'guides', '31-40'
        c.unit_names({'player': ('Need', 'Pass'), 'party1': ('Friend', 'One'),
                      'party2': ('Friend', 'Two'), 'party3': ('Friend', 'Three'),
                      'party4': ('Friend', 'Four')})
        group = next(g for g in c.ns.DungeonGroups().values() if g.key == 'wailing-caverns')
        c.ns.ActivateRoute(c.ns.DungeonGuide(group))
        c.ns.ShowDungeonViewer('wailing-caverns', True)
        c.drain()
        c.ns.window.Hide(c.ns.window)
        observe_browser(c)
        return c

    def test_reported_party_dungeon_background_sync_does_not_scan_closed_browser(self):
        c = self.dungeon_client()
        self.assertEqual(c.ns.catalogue.count, 5230)
        self.assertEqual(c.ns.profile.mapID, 0)
        self.assertEqual(len(c.ns.partyNames), 4)
        selected = c.ns.routeSelection.key
        c.ns.SyncNow(False)
        sent = c.drain()
        self.assertGreater(len(sent), 0)
        self.assertEqual(c.lua.globals().browserReads, 0)
        self.assertEqual(c.lua.globals().dashboardReads, 0)
        self.assertEqual(c.ns.routeSelection.key, selected)
        self.assertTrue(c.ns.dungeonViewer.IsShown(c.ns.dungeonViewer))

    def test_incoming_snapshot_updates_progress_without_hidden_dashboard_work(self):
        c = self.dungeon_client()
        c.receive('1|S|91|1|1|962,1486', sender='Friend One-ClassicBetaPvP')
        c.receive('1|C|91|1|1|1491', sender='Friend One-ClassicBetaPvP')
        c.receive('1|K|91|1|1|962,1486,1491', sender='Friend One-ClassicBetaPvP')
        c.drain()
        self.assertTrue(c.ns.members['Friend-One'].active[962])
        self.assertTrue(c.ns.members['Friend-One'].completed[1491])
        self.assertEqual(c.lua.globals().browserReads, 0)
        self.assertEqual(c.lua.globals().dashboardReads, 0)

    def test_visible_browser_still_refreshes_and_hidden_manual_sync_can_render(self):
        c = self.dungeon_client()
        c.ns.window.Show(c.ns.window)
        c.ns.SyncNow(False)
        self.assertEqual(c.lua.globals().browserReads, 0)
        c.drain()
        self.assertGreater(c.lua.globals().browserReads, 0)
        before = c.lua.globals().browserReads
        c.ns.window.Hide(c.ns.window)
        c.ns.SyncNow(True)
        self.assertGreater(c.lua.globals().browserReads, before)

    def test_hidden_sync_still_advances_the_selected_fixed_guide(self):
        c, g = scanning_client()
        c.lua.globals().grouped = True
        c.ns.db.config.soloMode = False
        c.ns.ApplyPartyMode()
        before = [(s.id, s.kind) for s in g.fixedPlan.values()]
        observe_browser(c)
        entries(c, 900, 901)
        c.ns.SyncNow(False)
        c.drain()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
        self.assertEqual(before, [(s.id, s.kind) for s in c.ns.routeSelection.fixedPlan.values()])
        self.assertEqual(c.lua.globals().dashboardReads, 0)

    def test_unready_quest_log_background_sync_keeps_previous_snapshot_without_render(self):
        c = self.dungeon_client()
        c.lua.execute('C_QuestLog.GetInfo=function() return nil end')
        c.ns.SyncNow(False)
        self.assertFalse(c.ns.questReady)
        self.assertIsNotNone(c.ns.active[962])
        self.assertEqual(c.lua.globals().dashboardReads, 0)

    def test_zone_entry_and_objective_events_do_not_rebuild_hidden_browser(self):
        c = self.dungeon_client()
        c.ns.frame.OnEvent(c.ns.frame, 'ZONE_CHANGED_NEW_AREA')
        c.ns.frame.OnEvent(c.ns.frame, 'QUEST_WATCH_UPDATE')
        c.drain()
        self.assertEqual(c.lua.globals().browserReads, 0)
        self.assertTrue(c.ns.dungeonViewer.IsShown(c.ns.dungeonViewer))

    def test_visible_refresh_burst_coalesces_and_uses_fresh_history_after_timer(self):
        c = guide_client(2)
        c.ns.filter = 'guides'
        c.drain()
        c.ns.window.Show(c.ns.window)
        observe_browser(c)
        c.lua.execute('''
            local browser=regressionNS.GuideBrowserChoices
            regressionNS.GuideBrowserChoices=function(...)
                local choices=browser(...)
                browserCompleted=choices[1] and choices[1].completed
                return choices
            end
        ''')
        for _ in range(30):
            c.ns.Refresh(True)
        self.assertEqual(c.lua.globals().dashboardReads, 0)
        c.lua.globals().finished[900] = True
        c.drain()
        self.assertEqual(c.lua.globals().dashboardReads, 1)
        self.assertEqual(c.lua.globals().browserReads, 1)
        self.assertEqual(c.lua.globals().browserCompleted, 1)

    def test_closing_dashboard_cancels_queued_background_render(self):
        c = self.dungeon_client()
        c.ns.window.Show(c.ns.window)
        c.ns.Refresh(True)
        c.ns.window.Hide(c.ns.window)
        c.drain()
        self.assertEqual(c.lua.globals().dashboardReads, 0)


class SharedEventTests(unittest.TestCase):
    def test_dungeon_viewer_reuses_existing_subscriptions(self):
        c = Client(use_catalogue=True, default_guide=True)
        for event in ('ITEM_DATA_LOAD_RESULT', 'PLAYER_REGEN_ENABLED', 'QUEST_LOG_UPDATE',
                      'QUEST_TURNED_IN', 'ZONE_CHANGED_NEW_AREA'):
            with self.subTest(event=event):
                self.assertEqual(c.ns.frame.registrationAttempts[event], 1)
                self.assertTrue(c.ns.frame.registeredEvents[event])
                self.assertIsNotNone(c.ns.handlers[event])
                self.assertIsNone(c.ns.eventFailures[event])

    def test_replacing_handler_never_registers_twice_and_errors_still_surface(self):
        c = Client()
        event = 'PLAYER_REGEN_ENABLED'
        self.assertTrue(c.ns.On(event, c.lua.eval('function() replacementRan=true end')))
        c.ns.frame.OnEvent(c.ns.frame, event)
        self.assertTrue(c.lua.globals().replacementRan)
        self.assertEqual(c.ns.frame.registrationAttempts[event], 1)

    def test_quest_event_preserves_progress_handler_and_refreshes_dungeon_markers(self):
        c = Client(quests=(5724,), use_catalogue=True, default_guide=True)
        c.guide_environment(level=15)
        c.ns.ShowDungeonViewer('ragefire-chasm', True)
        f = c.ns.dungeonViewer
        maur = next(p for p in f.questPins.values() if p.IsShown(p) and p.group.entityID == 11834)
        self.assertIsNotNone(maur)
        updates = c.ns.guideProgressStats.updates
        c.lua.globals().finished[5722] = True
        c.ns.frame.OnEvent(c.ns.frame, 'QUEST_LOG_UPDATE')
        c.drain()
        self.assertGreater(c.ns.guideProgressStats.updates, updates)
        self.assertFalse(any(p.IsShown(p) and p.group.entityID == 11834 for p in f.questPins.values()))

    def test_party_event_registers_again_after_explicit_solo_unsubscription(self):
        c = Client()
        c.ns.db.config.soloMode = True
        c.ns.ApplyPartyMode()
        self.assertIsNone(c.ns.handlers.CHAT_MSG_ADDON)
        self.assertIsNone(c.ns.frame.registeredEvents.CHAT_MSG_ADDON)
        c.ns.db.config.soloMode = False
        c.ns.ApplyPartyMode()
        self.assertTrue(c.ns.frame.registeredEvents.CHAT_MSG_ADDON)
        self.assertIsNotNone(c.ns.handlers.CHAT_MSG_ADDON)
        self.assertIsNone(c.ns.eventFailures.CHAT_MSG_ADDON)


if __name__ == '__main__':
    unittest.main()
