"""Fresh personal guide scans, bounded event work and explicit level exceptions.

Lua 5.1 fixtures validate decisions and state, not live Forever timing or FPS.
"""
import unittest

from test_addon import Client
from test_050 import solo, world_positions
from test_061 import world_quest, run_plan
from test_063 import zone, order
from test_074 import scanning_client, tick
from test_routes import catalogue, map_canvas


def entries(c, *ids):
    c.lua.globals().entries = c.lua.table_from([
        {'questID': id, 'title': 'Quest ' + str(id), 'isHeader': False}
        for id in ids], recursive=True)


def count_work(c):
    c.lua.execute('''
    work={log=0,guide=0,route=0,dashboard=0}
    for name,key in pairs({ReadQuests='log',ReadGuide='guide',
        UpdateSelectedRoute='route',Render='dashboard'}) do
        local original=ns[name]
        ns[name]=function(...) work[key]=work[key]+1; return original(...) end
    end
    ''')


def focused_client():
    # Zone guides contain multiple quests; finish the second one so the
    # lifecycle check follows only the first quest, without other hub pickups.
    c, g = scanning_client()
    c.lua.globals().finished[901] = True
    c.ns.Refresh(True); c.drain()
    return c, g


class FreshScanTests(unittest.TestCase):
    def test_scan_advances_from_fresh_log_even_while_dashboard_is_resizing(self):
        c, g = scanning_client()
        before = order(g)
        c.ns.ui.resizing = True
        entries(c, 900, 901)
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertTrue(c.ns.ui.resizeDirty)
        self.assertEqual(order(g), before)
        self.assertIn('2 active', c.ns.guideScanStatus)

    def test_large_scan_restarts_after_progress_changes_between_history_batches(self):
        c, g = scanning_client(85)
        before = order(g)
        c.ns.ScanGuideProgress(); tick(c)
        self.assertIsNotNone(c.ns.guideScanning)
        entries(c, *range(901, 985))
        c.lua.globals().finished[900] = True
        c.ns.handlers.QUEST_LOG_UPDATE()
        c.drain()
        self.assertIn('85/85 checked; 1 completed; 84 active', c.ns.guideScanStatus)
        self.assertEqual(c.ns.navigation.state.stop.id, 901)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
        self.assertEqual(order(g), before)

    def test_failed_scan_preserves_manual_skips_and_last_complete_snapshot(self):
        c, g = scanning_client()
        entries(c, 900); c.ns.ReadQuests()
        c.ns.db.guideSkips[c.ns.self].quests[901] = True
        c.ns.db.config.scanSkipped = True
        c.lua.execute('reads=0; C_QuestLog.GetInfo=function() reads=reads+1; return nil end')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertFalse(c.ns.questReady)
        self.assertIsNotNone(c.ns.active[900])
        self.assertTrue(c.ns.GuideQuestSkipped(901))
        self.assertIn('scan paused', c.ns.guideScanStatus)
        self.assertIsNone(c.ns.guideScanning)
        self.assertLessEqual(c.lua.globals().reads, 3)

    def test_scan_retries_temporarily_missing_log_and_then_finishes(self):
        c, g = scanning_client()
        entries(c, 900, 901)
        c.lua.execute('''reads=0; C_QuestLog.GetInfo=function(i)
            reads=reads+1; if reads==1 then return nil end; return entries[i] end''')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertTrue(c.ns.questReady)
        self.assertIn('2 active', c.ns.guideScanStatus)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')

    def test_scan_rechecks_history_if_final_snapshot_changes_during_read(self):
        c, g = scanning_client()
        c.lua.globals().ns = c.ns
        c.lua.execute('''logReads=0
        C_QuestLog.GetNumQuestLogEntries=function()
            logReads=logReads+1
            if logReads==2 then
                entries={{questID=900,title='One'},{questID=901,title='Two'}}
                ns.handlers.QUEST_LOG_UPDATE()
            end
            return #entries
        end''')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertIn('2 active', c.ns.guideScanStatus)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')

    def test_cancelled_scan_does_not_apply_reconsider_skips(self):
        c, g = scanning_client(85)
        c.ns.db.guideSkips[c.ns.self].quests[901] = True
        c.ns.db.config.scanSkipped = True
        c.ns.ScanGuideProgress(); tick(c)
        c.ns.ClearRoute(); c.drain()
        self.assertTrue(c.ns.GuideQuestSkipped(901))
        self.assertIsNone(c.ns.routeSelection)


class PersonalProgressTests(unittest.TestCase):
    def test_burst_reads_one_fresh_snapshot_and_does_not_rebuild_hidden_dashboard(self):
        for visible in (False, True):
            c, g = scanning_client()
            c.ns.window.SetShown(c.ns.window, visible)
            c.lua.globals().ns = c.ns
            count_work(c)
            entries(c, 900, 901)
            for _ in range(60): c.ns.handlers.QUEST_LOG_UPDATE()
            work = c.lua.globals().work
            self.assertEqual(work.log, 0)
            self.assertEqual(work.route, 0)
            c.drain()
            self.assertEqual(work.log, 1)
            self.assertEqual(work.guide, 1)
            self.assertEqual(work.route, 1)
            self.assertEqual(work.dashboard, int(visible))
            self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
            self.assertEqual(c.ns.guideProgressStats.coalesced, 59)
            self.assertEqual(len(c.lua.globals().sent), 0)

    def test_accept_then_ready_then_hand_in_uses_fresh_native_progress(self):
        c, g = focused_client()
        c.lua.execute('''objectiveReady=false
        C_QuestLog.GetQuestObjectives=function() return {{text='Targets slain',
            type='monster',numFulfilled=objectiveReady and 3 or 0,
            numRequired=3,finished=objectiveReady}} end
        C_QuestLog.IsComplete=function() return objectiveReady end''')
        entries(c, 900); c.ns.handlers.QUEST_ACCEPTED(1, 900); c.drain()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
        self.assertEqual(c.ns.localProgress[900].objectives[1].have, 0)
        c.lua.globals().objectiveReady = True
        c.ns.handlers.QUEST_LOG_UPDATE(); c.drain()
        self.assertEqual(c.ns.navigation.state.stop.kind, 't')
        self.assertFalse(c.ns.Completed(900))
        # Hand-in can arrive while GetInfo and the completion flag still lag.
        c.ns.handlers.QUEST_TURNED_IN(900); c.drain()
        self.assertIsNone(c.ns.active[900])
        self.assertTrue(c.ns.Completed(900))
        self.assertTrue(c.ns.selectedRoute.complete)

    def test_accept_waits_for_log_entry_and_recovers_on_bounded_retry(self):
        c, g = focused_client()
        c.ns.handlers.QUEST_ACCEPTED(1, 900); tick(c)
        self.assertFalse(c.ns.questReady)
        self.assertIn('accepted quest', c.ns.status)
        self.assertFalse(c.ns.selectedRoute.complete)
        entries(c, 900); c.drain()
        self.assertTrue(c.ns.questReady)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
        self.assertEqual(c.ns.guideProgressStats.retries, 1)

    def test_abandon_before_delayed_accept_entry_does_not_block_future_scans(self):
        c, g = focused_client()
        c.ns.handlers.QUEST_ACCEPTED(1, 900)
        c.ns.handlers.QUEST_REMOVED(900)
        c.drain(); c.ns.ScanGuideProgress(); c.drain()
        self.assertTrue(c.ns.questReady)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'a')
        self.assertFalse(c.ns.Completed(900))

    def test_reaccept_clears_lingering_turn_in_without_hiding_new_active_entry(self):
        c, g = focused_client()
        c.ns.catalogue.quests[900].repeatable = True
        entries(c, 900); c.ns.ReadQuests()
        c.ns.handlers.QUEST_TURNED_IN(900)
        self.assertTrue(c.ns.ReadQuests())
        self.assertIsNone(c.ns.active[900])
        c.ns.handlers.QUEST_ACCEPTED(1, 900)
        self.assertTrue(c.ns.ReadQuests())
        self.assertIsNotNone(c.ns.active[900])

    def test_incomplete_quest_event_retries_are_bounded_and_preserve_old_active(self):
        c, g = focused_client()
        entries(c, 900); c.ns.ReadQuests()
        c.lua.execute('C_QuestLog.GetInfo=function() return secret end')
        c.ns.handlers.QUEST_LOG_UPDATE(); c.drain()
        self.assertFalse(c.ns.questReady)
        self.assertIsNotNone(c.ns.active[900])
        self.assertEqual(c.ns.guideProgressStats.updates, 3)
        self.assertEqual(c.ns.guideProgressStats.retries, 2)
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_surfaced_read_error_does_not_permanently_block_future_quest_updates(self):
        c, g = focused_client()
        original = c.ns.ReadGuide
        c.ns.ReadGuide = c.lua.eval('function() error("read fixture failure") end')
        c.ns.handlers.QUEST_LOG_UPDATE()
        with self.assertRaisesRegex(Exception, 'read fixture failure'): tick(c)
        c.ns.ReadGuide = original
        entries(c, 900); c.ns.handlers.QUEST_LOG_UPDATE(); c.drain()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')

    def test_native_objective_refresh_keeps_nearby_work_panel_and_live_counts(self):
        c = solo(); map_canvas(c)
        data = {900: world_quest('Boar hunt'), 901: world_quest('Apple gathering')}
        data[900]['objectives'] = [{'mapID': 501, 'x': .3, 'y': .4,
            'name': 'Test Boar', 'entityID': 100, 'npc': True, 'quantity': 7}]
        data[901]['objectives'] = [{'mapID': 501, 'x': .31, 'y': .4,
            'name': 'Test Apples', 'entityID': 200, 'item': True, 'quantity': 7,
            'action': 'gather'}]
        catalogue(c, data)
        entries(c, 900, 901)
        c.lua.execute('''apples=1
        C_Map.GetMapWorldSize=function() return 1000,1000 end
        function GetPlayerFacing() return 0 end
        C_QuestLog.GetQuestObjectives=function(id) return {{
            text=id==900 and 'Test Boar' or 'Test Apples',
            numFulfilled=id==900 and 0 or apples,numRequired=7,
            type=id==900 and 'monster' or 'item',finished=false}} end''')
        c.ns.ReadQuests(); c.ns.ReadGuide()
        g = zone(c); c.ns.ShowGuideOnMap(g); run_plan(c); c.drain()
        before = order(g)
        panel = c.ns.navigation.work
        self.assertTrue(panel.IsShown(panel))
        self.assertEqual(len(panel['items']), 2)
        c.lua.globals().apples = 4
        c.ns.handlers.QUEST_LOG_UPDATE(); c.drain()
        self.assertTrue(panel.IsShown(panel))
        self.assertEqual(len(panel['items']), 2)
        self.assertIn('4/7', [r.count.text for r in panel.rows.values()])
        self.assertEqual(order(g), before)


class UsefulPrerequisiteTests(unittest.TestCase):
    def test_scan_keeps_useful_low_prerequisite_explains_unlock_and_filters_junk(self):
        c = solo(); map_canvas(c)
        catalogue(c, {
            900: world_quest('Useful setup', level=16),
            901: world_quest('Useful reward', level=20, previousQuest=900),
            902: world_quest('Low junk', level=16),
            903: world_quest('Future work', level=30, minLevel=28)})
        c.lua.globals().playerLevel = 16; c.ns.ReadGuide()
        g = zone(c)
        c.lua.globals().playerLevel = 21; c.ns.ReadGuide()
        c.ns.ShowGuideOnMap(g); run_plan(c); c.drain()
        before = order(g)
        entries(c, 902)  # Unfinished current low junk follows the same filter.
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(c.ns.PreferredQuestLevels(), (18, 24))
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900})
        self.assertIn('Lower-level prerequisite', c.ns.navigation.step.text)
        self.assertIn('Unlocks Useful reward (level 20)', c.ns.navigation.context.text)
        self.assertFalse(c.ns.GuideQuestSkipped(902))
        self.assertFalse(c.ns.GuideQuestSkipped(903))
        self.assertEqual(order(g), before)

    def test_ready_low_hand_in_is_kept_without_recommending_more_low_work(self):
        c, g = focused_client()
        c.lua.globals().playerLevel = 21
        entries(c, 900)
        c.lua.execute('C_QuestLog.IsComplete=function() return true end')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(c.ns.navigation.state.stop.kind, 't')
        self.assertFalse(c.ns.Completed(900))

    def test_actual_barrens_data_distinguishes_useful_chain_from_unrelated_low_quest(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=21)
        c.lua.globals().grouped = False
        c.unit_names({'player': ['Alice', 'TestRealm']})
        self.assertIn('Serena Bloodfeather (level 20)', c.ns.LevelingValue(875)[1])
        self.assertEqual(c.ns.LevelingValue(888)[0], False)


class LevelReadyZoneTests(unittest.TestCase):
    def client(self):
        c = solo(); world_positions(c); map_canvas(c)
        catalogue(c, {
            900: world_quest('Old home', level=12),
            901: world_quest('Other home', level=12),
            902: world_quest('Hills first', 'Test Hills', 502, 22),
            903: world_quest('Hills second', 'Test Hills', 502, 23)})
        c.ns.db.config.dungeonPrompts = False
        c.ns.db.config.zonePrompts = True
        g = zone(c)
        c.ns.ShowGuideOnMap(g); run_plan(c); c.drain()
        return c, g

    def test_level_up_offers_suitable_adjacent_guide_without_replacing_current(self):
        c, g = self.client()
        self.assertIsNone(c.ns.LevelingZoneTransition())
        c.lua.globals().playerLevel = 21
        c.ns.handlers.PLAYER_LEVEL_UP(21); c.drain()
        p = c.ns.activityPrompt
        self.assertTrue(p.IsShown(p))
        self.assertIn('Test Hills', p.title.text)
        self.assertIn('At level 21', p.text.text)
        self.assertEqual(c.ns.routeSelection.key, g.key)
        p.later.OnClick(); c.ns.ScheduleActivitySuggestions(); c.drain()
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertFalse(p.IsShown(p))

    def test_accepting_level_prompt_starts_full_zone_guide(self):
        c, g = self.client()
        c.lua.globals().playerLevel = 21
        c.ns.handlers.PLAYER_LEVEL_UP(21); c.drain()
        c.ns.activityPrompt.accept.OnClick(); run_plan(c); c.drain()
        self.assertEqual(c.ns.routeSelection.key, 'level-zone:kalimdor/test-hills')
        self.assertEqual({r.id for r in c.ns.routeSelection.records.values()}, {902, 903})

    def test_zone_suggestion_waits_until_scan_finishes(self):
        c, g = self.client()
        c.lua.globals().playerLevel = 21; c.ns.ReadGuide()
        c.ns.ScheduleActivitySuggestions()
        c.ns.ScanGuideProgress(); tick(c)
        self.assertIsNotNone(c.ns.guideScanning)
        self.assertFalse(c.ns.activityPrompt and c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        c.drain()
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))

    def test_useful_current_work_and_pending_location_do_not_trigger_level_prompt(self):
        c, g = self.client()
        # Only low work remains at 21; adding a pending NPC/location step must
        # not let the new level suggestion replace that confirmation.
        c.lua.globals().playerLevel = 21; c.ns.ReadGuide(); c.ns.Refresh(True)
        c.ns.selectedRoute.pendingStop = c.lua.table_from({'id': 900, 'kind': 'a'})
        self.assertIsNone(c.ns.LevelingZoneTransition())
        c.ns.selectedRoute.pendingStop = None
        c.ns.selectedRoute.stops[1] = c.lua.table_from({'id': 900, 'kind': 't', 'mapID': 501})
        self.assertIsNone(c.ns.LevelingZoneTransition())

    def test_missing_starters_wrong_faction_and_distant_zones_are_not_ready_suggestions(self):
        for condition in ('missing', 'alliance', 'distant', 'locked'):
            c, g = self.client()
            for id in (902, 903):
                q = c.ns.catalogue.quests[id]
                if condition == 'missing': q.starts = None
                if condition == 'alliance': q.side = 'Alliance'
                if condition == 'distant':
                    q.mapID = 503
                    for field in ('starts', 'objectives', 'ends'):
                        for p in q[field].values(): p.mapID = 503
                if condition == 'locked': q.minLevel = 25
            c.ns.catalogue.count = 4
            c.lua.globals().playerLevel = 21; c.ns.ReadGuide(); c.ns.Refresh(True)
            self.assertIsNone(c.ns.LevelingZoneTransition(), condition)


if __name__ == '__main__':
    unittest.main()
