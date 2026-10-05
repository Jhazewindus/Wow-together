"""Repeatables, personal guide skips, scoped scans and safe combat geometry."""
import json
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest
from test_050 import nearby, solo
from test_052 import viewport
from test_056 import current_client, preview_client
from import_wowhead import detail_facts


def plain(value):
    return {key: plain(item) if hasattr(item, 'items') else item for key, item in value.items()}


class RepeatableTests(unittest.TestCase):
    def test_spirit_of_the_wind_is_retained_in_library_but_not_leveling_discovery(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=25)
        self.assertTrue(c.ns.CatalogueQuest(889).repeatable)
        self.assertFalse(c.ns.LevelingQuestEnabled(889))
        c.ns.ShowQuestDetails(889)
        self.assertIn('Repeatable', c.ns.questDetails.body.text)

    def test_repeatable_pickups_and_active_repeatables_are_not_automatic_leveling_work(self):
        c = current_client({900: nearby('Real work'), 901: nearby('Buff', repeatable=True)})
        c.ns.catalogue.quests[902] = c.lua.table_from(nearby('Reputation repeat', repeatable=True), recursive=True)
        choice = c.ns.GuideChoices()[1]
        self.assertEqual({r.id for r in choice.records.values()}, {900})
        c.ns.db.config.currentQuestsFirst = False
        for row in c.ns.GuideChoices().values():
            self.assertFalse(any(r.id in (901, 902) for r in row.records.values()))

    def test_recurrence_comes_from_facts_box_not_comments_or_title(self):
        metadata = '$.extend(g_quests[42], '+json.dumps({'id': 42, 'name': 'Daily supplies'})+');'
        ordinary = metadata + '<div class="comment">This is repeatable</div>'
        self.assertIsNone(detail_facts(ordinary, {'id': 42}, {}).get('repeatable'))
        for fact in ('Repeatable', 'Daily', 'Weekly'):
            page = metadata + 'WH.markup.printHtml('+json.dumps('[ul][li]'+fact+'[/li][/ul]')+', "infobox-contents-0", {});'
            self.assertTrue(detail_facts(page, {'id': 42}, {})['repeatable'])


class SkipAndScanTests(unittest.TestCase):
    def test_skip_step_advances_preview_without_marking_quest_completed(self):
        c = preview_client()
        old = c.ns.selectedRoute.stops[1]
        key = c.ns.GuideStepKey(old)
        c.ns.navigation.skipStep.OnClick()
        self.assertNotEqual(c.ns.GuideStepKey(c.ns.selectedRoute.stops[1]), key)
        self.assertFalse(c.ns.Completed(900))
        self.assertTrue(c.ns.active[900])
        c.ns.ResetGuideSkips()
        self.assertEqual(c.ns.GuideStepKey(c.ns.selectedRoute.stops[1]), key)

    def test_skips_survive_a_new_lua_client_and_remain_character_specific(self):
        c = preview_client()
        c.ns.navigation.skipStep.OnClick()
        c.ns.navigation.skipQuest.OnClick()
        saved = plain(c.ns.db)
        other = Client(quests=(900,), saved_variables=saved)
        self.assertTrue(other.ns.GuideQuestSkipped(900))
        self.assertTrue(other.ns.db.guideSkips[other.ns.self].steps[900])
        different = Client(name='Carol', quests=(900,), saved_variables=saved)
        self.assertFalse(different.ns.GuideQuestSkipped(900))

    def test_skipping_a_quest_keeps_other_work_and_does_not_unlock_its_followup(self):
        c = current_client({900: nearby('Skip me'), 901: nearby('Keep me')})
        c.ns.catalogue.quests[902] = c.lua.table_from(nearby('Locked followup', previousQuest=900), recursive=True)
        map_canvas(c); c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        skipped = c.ns.selectedRoute.stops[1].id
        c.ns.navigation.skipQuest.OnClick()
        self.assertFalse(any(s.id == skipped for s in c.ns.selectedRoute.stops.values()))
        self.assertFalse(c.ns.Completed(skipped))
        self.assertFalse(c.ns.CatalogueAllowed(902, c.ns.profile, c.ns.self)[0])

    def test_npc_destination_skip_is_stable_when_its_coordinates_change(self):
        c = preview_client()
        stop = c.ns.selectedRoute.stops[1]
        stop.entityID = 123
        c.ns.SkipGuide('step')
        stop.x, stop.y = .8, .2
        self.assertEqual(len(c.ns.FilterGuideStages(c.lua.table_from([stop]))), 0)

    def test_guide_start_and_button_scan_selected_series_and_preserve_real_history(self):
        c = solo()
        catalogue(c, {900: nearby('Already done', series=[900, 901], seriesRoot=900),
                      901: nearby('Next quest', previousQuest=900),
                      999: nearby('Unrelated')})
        c.lua.globals().finished[900] = True
        map_canvas(c)
        chosen = guide(c, (900, 901), key='series:900')
        c.ns.ShowGuideOnMap(chosen)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        self.assertEqual(set(c.ns.partyRouteHistoryScope.keys()), {900, 901})
        self.assertIn('1 completed', c.ns.guideScanStatus)
        c.ns.navigation.scan.OnClick()
        self.assertIsNone(c.ns.guideScanWindow)
        self.assertIn('replanned', c.ns.navigation.notice.text)
        self.assertFalse(c.ns.Completed(901))

    def test_unknown_history_stays_unknown_and_scan_scope_is_bounded(self):
        c = solo()
        catalogue(c, {900: nearby('Unknown')})
        chosen = guide(c)
        c.lua.execute('C_QuestLog.IsQuestFlaggedCompleted=function() return secret end')
        c.ns.ScanGuideProgress(chosen)
        self.assertIn('0/1 checked', c.ns.guideScanStatus)
        self.assertIn('unknown', c.ns.guideScanStatus)
        c.ns.catalogue.quests[900].series = c.lua.table_from(list(range(1, 1000)))
        c.ns.RouteHistoryScope(chosen.records)
        self.assertLessEqual(len(list(c.ns.partyRouteHistoryScope.keys())), 512)

    def test_scan_budget_prioritizes_selected_quests_and_their_prerequisites(self):
        c = solo()
        catalogue(c, {900: nearby('Long series', series=list(range(1, 1000))),
                      9900: nearby('Selected quest', previousQuest=9901)})
        chosen = guide(c, (900, 9900))
        c.ns.RouteHistoryScope(chosen.records)
        scope = set(c.ns.partyRouteHistoryScope.keys())
        self.assertTrue({900, 9900, 9901}.issubset(scope))
        self.assertEqual(len(scope), 512)


def mob_client():
    c = current_client({900: nearby('Two mob types')})
    c.ns.catalogue.quests[900].objectives = c.lua.table_from([
        {'mapID': 501, 'x': .3, 'y': .3, 'name': 'Test Hunter', 'entityID': 111, 'npc': True, 'action': 'kill'},
        {'mapID': 501, 'x': .4, 'y': .4, 'name': 'Test Guard', 'entityID': 222, 'npc': True, 'action': 'kill'}], recursive=True)
    c.lua.execute('''
    killed=0
    C_QuestLog.GetQuestObjectives=function() return {
      {text='Test Hunters killed: '..killed..'/7',numFulfilled=killed,numRequired=7,finished=false,type='monster'},
      {text='Test Guards slain: 0/10',numFulfilled=0,numRequired=10,finished=false,type='monster'}} end
    C_QuestLog.UnitIsRelatedToActiveQuest=function() return true end
    plates={nameplate1=CreateFrame('Frame'),nameplate2=CreateFrame('Frame')}
    C_NamePlate={GetNamePlateForUnit=function(unit) return plates[unit] end}
    function UnitGUID(unit) return 'Creature-0-1-2-3-'..(unit=='nameplate1' and 111 or 222)..'-ABC' end
    ''')
    c.ns.ReadProgress()
    c.ns.handlers.NAME_PLATE_UNIT_ADDED('nameplate1')
    c.ns.handlers.NAME_PLATE_UNIT_ADDED('nameplate2')
    return c


class ObjectiveHintTests(unittest.TestCase):
    def test_finished_mob_type_hides_skull_despite_generic_related_flag(self):
        c = mob_client()
        self.assertEqual(c.ns.npcHintCount, 2)
        c.lua.globals().killed = 7
        c.ns.ReadProgress(); c.ns.UpdateNPCHints()
        self.assertFalse(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))
        self.assertTrue(c.ns.npcHints['nameplate2'].IsShown(c.ns.npcHints['nameplate2']))
        self.assertEqual(c.ns.npcHintCount, 1)

    def test_private_counts_do_not_establish_finished_objectives(self):
        c = mob_client()
        c.lua.globals().killed = c.lua.globals().secret
        # A client can publish text while its counters/flags are restricted.
        c.lua.execute("C_QuestLog.GetQuestObjectives=function() return {{text='Test Hunters killed',numFulfilled=secret,numRequired=7,finished=secret,type='monster'}} end")
        c.ns.ReadProgress(); c.ns.UpdateNPCHints()
        self.assertTrue(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))

    def test_same_mob_remains_marked_for_another_unfinished_quest(self):
        c = mob_client()
        c.lua.globals().killed = 7
        c.ns.catalogue.quests[901] = c.ns.catalogue.quests[900]
        c.ns.active[901] = 'Other quest'
        c.ns.ReadProgress()
        c.ns.localProgress[901].objectives[1].have = 0
        c.ns.UpdateNPCHints()
        self.assertTrue(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))


class CombatGeometryTests(unittest.TestCase):
    def client(self):
        c = current_client({900: nearby('Active')})
        viewport(c); c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        return c

    def test_pan_and_zoom_reproject_owned_overlay_in_combat_without_waypoint_actions(self):
        c = self.client()
        c.lua.execute('combat=true; view.left=.1; view.right=.5; view.top=.2; view.bottom=.6; C_Map.SetUserWaypoint=function() error("combat waypoint") end')
        provider = c.ns.routeProvider
        old = provider.lines[1].startPoint[3]
        provider.OnCanvasPanChanged(provider)
        self.assertNotEqual(provider.lines[1].startPoint[3], old)
        self.assertAlmostEqual(provider.lines[1].startPoint[3], 220)
        self.assertAlmostEqual(provider.lines[1].startPoint[4], -255)

    def test_protected_or_restricted_owned_frame_still_defers_redraw(self):
        for private in (False, True):
            c = self.client()
            provider = c.ns.routeProvider
            old = provider.lines[1].startPoint[3]
            if private:
                provider.overlay.IsProtected = c.lua.eval('function() return secret end')
            else:
                provider.overlay.protected = True
            c.lua.execute('combat=true; view.left=.1; view.right=.5')
            provider.OnCanvasPanChanged(provider)
            self.assertTrue(c.ns.routeRedrawPending)
            self.assertEqual(provider.lines[1].startPoint[3], old)


if __name__ == '__main__':
    unittest.main()
