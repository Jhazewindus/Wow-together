"""Current elite-objective spawn overlays, lifecycle and scoped source facts."""
import json
import sys
import unittest

from test_addon import Client, ROOT
from test_routes import catalogue, guide, map_canvas, quest
from test_074 import scanning_client

sys.path.insert(0, str(ROOT / 'tools'))
from build_elite_spawns import reference_allowed, target_ids


def fixture():
    c = Client(quests=(900,))
    c.guide_environment(level=12)
    target = {'mapID': 501, 'x': .6, 'y': .4, 'name': 'Elite beast',
              'npc': True, 'entityID': 700, 'action': 'kill', 'quantity': 7,
              'objectiveKey': 'npc:700'}
    catalogue(c, {900: quest('Elite hunt', questType='Elite', objectives=[target])})
    c.ns.questEntities = c.lua.table_from({'npc': {700: {'name': 'Elite beast', 'classification': 1},
                                                701: {'name': 'Other beast', 'classification': 2}}}, recursive=True)
    c.ns.eliteSpawnData = c.lua.table_from({'npcs': {700: {'published': [[501, .6, .4], [501, .7, .5], [501, .8, .6]],
                                                            'reference': [[501, .4, .4]], 'referenceQuestIDs': [900]},
                                                      701: {'published': [[501, .5, .5]]}}}, recursive=True)
    map_canvas(c)
    c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 501)
    c.lua.globals().WorldMapFrame.Show(c.lua.globals().WorldMapFrame)
    selected = guide(c)
    c.ns.ActivateRoute(selected, c.ns.BuildGuideRoute(selected, False))
    c.ns.DrawRoute()
    return c


def shown(c):
    return [pin for pin in (c.ns.routeProvider.elitePins or c.lua.table()).values() if pin.IsShown(pin)]


class EliteSpawnTests(unittest.TestCase):
    def test_every_current_target_location_is_marked_without_altering_route(self):
        c = fixture()
        self.assertEqual(len(shown(c)), 3)
        self.assertEqual(c.ns.routeStats.eliteSpawns, 3)
        self.assertEqual({p.spawn.entityID for p in shown(c)}, {700})
        before = [(p.id, p.kind, p.x, p.y) for p in c.ns.selectedRoute.stops.values()]
        c.ns.DrawRoute(); c.ns.UpdateNavigation()
        self.assertEqual(before, [(p.id, p.kind, p.x, p.y) for p in c.ns.selectedRoute.stops.values()])
        self.assertTrue(all(p.icon.texture.endswith('UI-RaidTargetingIcon_8') for p in shown(c)))
        self.assertEqual(c.ns.routeProvider.pins[1].icon.texture, shown(c)[0].icon.texture)

    def test_future_objective_mobs_are_not_marked_even_in_full_route(self):
        c = fixture()
        q = c.ns.CatalogueQuest(900)
        q.objectives[2] = c.lua.table_from({'mapID': 501, 'x': .5, 'y': .5, 'name': 'Other beast',
            'npc': True, 'entityID': 701, 'action': 'kill', 'quantity': 10, 'objectiveKey': 'npc:701'})
        c.ns.ActivateRoute(guide(c), c.ns.BuildGuideRoute(guide(c), False))
        c.ns.SetOption('fullRoute', True)
        self.assertEqual({p.spawn.entityID for p in shown(c)}, {700})

    def test_completion_hides_current_mob_even_if_another_goal_is_unfinished(self):
        c = fixture()
        c.ns.localProgress[900] = c.lua.table_from({'objectives': [
            {'text': 'Elite beast slain', 'kind': 'monster', 'have': 7, 'need': 7, 'finished': True},
            {'text': 'Other beast slain', 'kind': 'monster', 'have': 0, 'need': 10, 'finished': False}]}, recursive=True)
        c.ns.UpdateNavigation()
        self.assertEqual(shown(c), [])
        self.assertEqual(c.ns.routeStats.eliteSpawns, 0)

    def test_accept_and_turn_in_steps_never_have_spawn_skulls(self):
        c = fixture()
        for kind in ('a', 't'):
            c.ns.selectedRoute.stops[1].kind = kind
            c.ns.DrawRoute()
            self.assertEqual(shown(c), [])

    def test_normal_mobs_and_talk_use_escort_actions_are_not_skull_targets(self):
        c = fixture()
        c.ns.questEntities.npc[700].classification = 0
        c.ns.DrawRoute(); self.assertEqual(shown(c), [])
        c.ns.questEntities.npc[700].classification = 1
        for action in ('talk', 'use', 'escort', 'heal', 'buy', 'event'):
            c.ns.selectedRoute.stops[1].action = action
            c.ns.DrawRoute(); self.assertEqual(shown(c), [])

    def test_loot_from_an_elite_uses_the_same_spawn_points(self):
        c = fixture(); stop = c.ns.selectedRoute.stops[1]
        stop.action, stop.itemName, stop.itemID = 'loot', 'Elite fang', 800
        stop.objectiveKey = 'item:800'
        c.ns.DrawRoute()
        self.assertEqual(len(shown(c)), 3)

    def test_skip_stop_switch_and_toggle_clear_the_owned_overlay(self):
        for action in ('skip', 'stop', 'switch', 'toggle'):
            c = fixture()
            self.assertEqual(len(shown(c)), 3)
            if action == 'skip': c.ns.SkipGuide('step')
            elif action == 'stop': c.ns.StopGuide(False)
            elif action == 'toggle': c.ns.SetOption('eliteSpawnHints', False)
            else:
                c.ns.selectedRoute.stops[1].entityID = 701
                c.ns.selectedRoute.stops[1].objectiveKey = 'npc:701'
                c.ns.DrawRoute()
                self.assertEqual({p.spawn.entityID for p in shown(c)}, {701})
                continue
            self.assertEqual(shown(c), [])

    def test_preview_scan_flight_and_ghost_do_not_show_a_hunt_overlay(self):
        for mode in ('preview', 'scan', 'flight', 'ghost', 'confirmation', 'training'):
            c = fixture()
            if mode == 'preview': c.ns.navigationPreview = c.lua.table()
            elif mode == 'scan': c.ns.guideScanning = c.lua.table()
            elif mode == 'flight': c.lua.execute('function UnitOnTaxi() return true end')
            elif mode == 'ghost': c.lua.execute('function UnitIsGhost() return true end')
            elif mode == 'confirmation':
                c.lua.globals().testNS = c.ns
                c.lua.execute('testNS.CurrentQuestConfirmation=function() return {unknownLocation=true} end')
            else:
                c.lua.globals().testNS = c.ns
                c.lua.execute('testNS.CurrentClassTrainingStop=function() return {kind="trainer", mapID=501,x=.2,y=.2} end')
            c.ns.DrawRoute(); self.assertEqual(shown(c), [])

    def test_unaccepted_objective_and_manual_skip_have_no_spawn_points(self):
        c = fixture(); c.ns.active[900] = None
        self.assertEqual(len(c.ns.EliteSpawnPoints()), 0)
        c.ns.active[900] = 'Elite hunt'
        c.ns.db.guideSkips[c.ns.self] = c.lua.table_from({'quests': {900: True}, 'steps': {}}, recursive=True)
        self.assertEqual(len(c.ns.EliteSpawnPoints()), 0)

    def test_reference_points_require_unchanged_identity_and_quest_scope(self):
        c = fixture(); q = c.ns.CatalogueQuest(900)
        q.foreverStatus, q.legacyFactsSource = 'unchanged', 'Reviewed fallback'
        self.assertEqual(len(c.ns.EliteSpawnPoints()), 4)
        q.foreverStatus = 'changed'
        self.assertEqual(len(c.ns.EliteSpawnPoints()), 3)
        q.foreverStatus = 'unchanged'; c.ns.eliteSpawnData.npcs[700].referenceQuestIDs[1] = 901
        # Changing the status boundary invalidates the cached point selection.
        c.ns.DrawRoute(); self.assertEqual(len(c.ns.EliteSpawnPoints()), 3)

    def test_completed_overlay_clears_in_combat_and_geometry_remains_live(self):
        c = fixture()
        c.lua.execute('function InCombatLockdown() return true end')
        c.lua.globals().WorldMapFrame.SetSize(c.lua.globals().WorldMapFrame, 1200, 900)
        c.ns.routeProvider.RefreshAllData(c.ns.routeProvider)
        self.assertEqual(len(shown(c)), 3)
        self.assertAlmostEqual(shown(c)[0].point[4], .6 * 1000)  # Canvas fallback stays on its canvas.
        c.ns.localProgress[900] = c.lua.table_from({'objectives': [
            {'text': 'Elite beast slain', 'kind': 'monster', 'have': 7, 'need': 7, 'finished': True}]}, recursive=True)
        c.ns.UpdateNavigation()
        self.assertEqual(shown(c), [])

    def test_skulls_remain_until_the_last_synced_member_finishes(self):
        c = fixture()
        c.receive('1|S|1|1|1|900')
        peer = c.ns.members['Bob-TestRealm']
        peer.progress = c.lua.table_from({900: {'activeRevision': peer.activeRevision, 'objectives': [
            {'text': 'Elite beast slain', 'kind': 'monster', 'have': 1, 'need': 7, 'finished': False}]}}, recursive=True)
        c.ns.localProgress[900] = c.lua.table_from({'objectives': [
            {'text': 'Elite beast slain', 'kind': 'monster', 'have': 7, 'need': 7, 'finished': True}]}, recursive=True)
        c.ns.UpdateNavigation()
        self.assertEqual(len(shown(c)), 3)
        peer.progress[900].objectives[1].have = 7
        peer.progress[900].objectives[1].finished = True
        c.ns.UpdateNavigation(); self.assertEqual(shown(c), [])

    def test_zoom_and_pan_project_spawn_markers_with_the_viewport(self):
        c = fixture()
        c.lua.execute('''
        WorldMapFrame:SetSize(1000,800)
        viewLeft, viewTop, viewWidth, viewHeight = .5,.3,.4,.4
        function WorldMapFrame:GetViewRect()
            return {GetLeft=function() return viewLeft end, GetTop=function() return viewTop end,
                GetRight=function() return viewLeft + viewWidth end, GetBottom=function() return viewTop + viewHeight end}
        end
        ''')
        c.ns.DrawRoute()
        surface = c.ns.RouteSurface(c.lua.globals().WorldMapFrame)
        self.assertEqual(surface.mode, 'Viewport projection')
        self.assertEqual(len(shown(c)), 3)
        pin = shown(c)[0]
        self.assertAlmostEqual(pin.point[4], (.6 - .5) / .4 * surface.width)
        self.assertAlmostEqual(pin.point[5], -(.4 - .3) / .4 * surface.height)
        c.lua.execute('viewLeft, viewTop, viewWidth, viewHeight = .7,.5,.2,.2')
        c.ns.DrawRoute(); self.assertEqual(len(shown(c)), 2)

    def test_projection_clips_offscreen_and_reuses_pins(self):
        c = fixture(); pins = len(c.ns.routeProvider.elitePins)
        c.ns.eliteSpawnData.npcs[700].published[4] = c.lua.table_from([501, 4, .5])
        c.ns.DrawRoute(); self.assertEqual(len(shown(c)), 3)
        c.ns.DrawRoute(); self.assertEqual(len(c.ns.routeProvider.elitePins), pins)
        c.lua.globals().WorldMapFrame.mapID = 777
        c.ns.DrawRoute(); self.assertEqual(shown(c), [])


class ReopenGuideTests(unittest.TestCase):
    def test_main_button_reopens_exited_guide_as_idle_without_reviving_it(self):
        c, _ = scanning_client()
        frame = c.ns.navigation
        frame.close.OnClick(); self.assertFalse(frame.IsShown(frame))
        c.ns.window.Show(c.ns.window)
        c.ns.ui.openGuideButton.OnClick()
        self.assertTrue(frame.IsShown(frame))
        self.assertFalse(c.ns.window.IsShown(c.ns.window))
        self.assertEqual(frame.title.text, 'No guide selected')
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.selectedRoute)
        c.drain(); self.assertIsNone(c.ns.routeSelection)

    def test_reopening_hidden_active_panel_preserves_current_guide_and_progress(self):
        c, _ = scanning_client()
        selection, route = c.ns.routeSelection, c.ns.selectedRoute
        key = selection.key
        before = [(p.id, p.kind) for p in route.stops.values()]
        c.ns.SetOption('routeArrow', False)
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))
        c.ns.ui.openGuideButton.OnClick()
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertEqual(c.ns.routeSelection.key, key)
        self.assertEqual([(p.id, p.kind) for p in c.ns.selectedRoute.stops.values()], before)


class EliteDataTests(unittest.TestCase):
    def test_dataset_is_lazy_and_preserves_many_spawns_for_a_real_elite(self):
        c = Client(use_catalogue=True)
        stat = next(v for v in c.ns.PackedDataStats().values() if v.name == 'elite-spawns')
        self.assertEqual(stat.loadedRows, 0)
        row = c.ns.eliteSpawnData.npcs[678]  # Mosh'Ogg Mauler, not a one-point centroid.
        self.assertGreater(len(row.reference), 6)
        stat = next(v for v in c.ns.PackedDataStats().values() if v.name == 'elite-spawns')
        self.assertEqual(stat.loadedRows, 1)
        manifest = json.loads((ROOT / 'WowTogether/EliteSpawnData.json').read_text())
        self.assertGreater(manifest['counts']['referencePoints'], 3000)
        self.assertEqual(manifest['counts']['targets'], stat.totalRows)

    def test_source_target_selection_excludes_givers_and_requires_unchanged_fallback(self):
        q = {'objectives': [{'npc': True, 'entityID': 7, 'action': 'kill'}],
             'npcTargets': [{'npc': True, 'entityID': 8, 'action': 'talk'}],
             'starts': [{'npc': True, 'entityID': 9}], 'requirements': []}
        self.assertEqual(target_ids(q), {7})
        self.assertFalse(reference_allowed(q))
        q.update(legacyFactsSource='Pinned', foreverStatus='unchanged')
        self.assertTrue(reference_allowed(q))
        q['foreverStatus'] = 'changed'; self.assertFalse(reference_allowed(q))


if __name__ == '__main__':
    unittest.main()
