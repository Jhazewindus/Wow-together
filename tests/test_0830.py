"""Dungeon preparation: all-zone collections, prerequisites and pickup UI."""
import unittest

from test_addon import Client
from test_050 import solo, dungeon, world_positions
from test_routes import catalogue, quest, map_canvas, guide as quest_guide


def group(c, data):
    for q in data.values():
        q.setdefault('categoryPath', 'dungeons/test-cavern')
    catalogue(c, data)
    c.ns.db.dungeonEntrances = c.lua.table_from({'test-cavern': {'mapID': 501, 'x': .9, 'y': .8}}, recursive=True)
    return next(g for g in c.ns.DungeonGroups().values() if g.key == 'test-cavern')


def accept(c, *ids):
    c.lua.globals().entries = c.lua.table_from([{'questID': i, 'title': 'Accepted', 'isHeader': False} for i in ids], recursive=True)
    c.ns.ReadQuests()


class DungeonCollectionTests(unittest.TestCase):
    def test_all_twenty_six_pickups_across_three_maps_are_retained(self):
        c = solo(); world_positions(c)
        g = group(c, {i: quest(str(i), map_id=501 + (i % 3)) for i in range(900, 926)})
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), True)
        self.assertEqual({s.id for s in route.stops.values() if s.kind == 'a'}, set(range(900, 926)))
        self.assertEqual(len(route.stops), 27)
        self.assertTrue(route.stops[27].dungeonEntrance)
        self.assertFalse(route.partial)
        self.assertGreater(route.otherMaps, 0)

    def test_required_chain_is_collected_completed_then_goal_picked_up(self):
        c = solo()
        g = group(c, {900: quest('Dungeon goal', previousQuest=899),
                      899: quest('Outside prerequisite', categoryPath='kalimdor/test-coast')})
        guide = c.ns.DungeonGuide(g)
        route = c.ns.BuildDungeonRoute(guide, True)
        steps = [(s.id, s.kind) for s in route.stops.values() if not s.dungeonEntrance]
        self.assertEqual(steps, [(899, 'a'), (899, 'q'), (899, 't'), (900, 'a')])
        self.assertTrue(route.stops[4].planned)
        self.assertEqual({r.id for r in guide.records.values()}, {899, 900})

    def test_shared_prerequisite_runs_once_and_both_goals_follow_return(self):
        c = solo()
        g = group(c, {900: quest(previousQuest=899), 901: quest(previousQuest=899),
                      899: quest(categoryPath='kalimdor/test-coast')})
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), True)
        steps = [(s.id, s.kind) for s in route.stops.values() if not s.dungeonEntrance]
        self.assertEqual(steps.count((899, 'a')), 1)
        for id in (900, 901): self.assertLess(steps.index((899, 't')), steps.index((id, 'a')))

    def test_confirmed_beta_offer_can_override_only_marked_older_prerequisites(self):
        for source, expected in (('Published converted-baseline prerequisites', {900}), ('Beta source', {899, 900})):
            c = solo()
            g = group(c, {900: quest(previousQuest=899, prerequisiteSource=source),
                          899: quest(categoryPath='kalimdor/test-coast')})
            c.ns.offered[900] = True
            guide = c.ns.DungeonGuide(g)
            self.assertEqual({r.id for r in guide.records.values()}, expected)

    def test_accepted_goal_does_not_start_an_obsolete_prerequisite_chain(self):
        c = solo(); g = group(c, {900: quest(previousQuest=899), 899: quest(categoryPath='kalimdor/test-coast')})
        accept(c, 900)
        guide = c.ns.DungeonGuide(g)
        self.assertEqual({r.id for r in guide.records.values()}, {900})
        route = c.ns.BuildDungeonRoute(guide, True)
        self.assertEqual(len(route.stops), 1); self.assertTrue(route.stops[1].dungeonEntrance)

    def test_accepted_goal_stays_collected_when_published_level_is_stale(self):
        c = solo(); g = group(c, {900: quest(minLevel=20, level=25)})
        accept(c, 900)
        guide = c.ns.DungeonGuide(g)
        self.assertIsNotNone(guide)
        route = c.ns.BuildDungeonRoute(guide, True)
        self.assertEqual(len(route.stops), 1); self.assertTrue(route.stops[1].dungeonEntrance)

    def test_actual_offer_with_unknown_pickup_level_does_not_use_target_level_as_a_gate(self):
        c = solo(); g = group(c, {900: quest(minLevel=None, level=25)})
        self.assertIsNone(c.ns.DungeonGuide(g))
        c.ns.offered[900] = True
        guide = c.ns.DungeonGuide(g)
        self.assertEqual(c.ns.BuildDungeonRoute(guide, True).stops[1].id, 900)

    def test_any_prerequisite_picks_one_compatible_branch_and_does_not_infer_candidates(self):
        c = solo()
        g = group(c, {900: quest(prerequisiteAny=[897, 898]), 901: quest(prerequisiteCandidates=[896]),
                      897: quest('Wrong faction', side='Alliance', categoryPath='kalimdor/test-coast'),
                      898: quest('Matching branch', categoryPath='kalimdor/test-coast'),
                      896: quest('Unproven', categoryPath='kalimdor/test-coast')})
        guide = c.ns.DungeonGuide(g)
        ids = {r.id for r in guide.records.values()}
        self.assertIn(898, ids); self.assertNotIn(897, ids); self.assertNotIn(896, ids)

    def test_unmapped_or_unavailable_prerequisite_does_not_bypass_gate(self):
        for changes in ({'starts': [], 'objectives': [], 'ends': []}, {'minLevel': 20}, {'side': 'Alliance'}):
            c = solo()
            g = group(c, {900: quest(previousQuest=899),
                          899: quest(categoryPath='kalimdor/test-coast', **changes)})
            route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), True)
            self.assertFalse(any(s.id == 900 or s.dungeonEntrance for s in route.stops.values()))
            self.assertEqual(route.missing, 1)
            self.assertTrue(route.partial)

    def test_actual_missing_offer_after_prerequisite_return_defers_goal(self):
        c = solo()
        g = group(c, {900: quest(previousQuest=899), 899: quest(categoryPath='kalimdor/test-coast')})
        c.lua.execute('finished[899]=true')
        c.ns.ObservedPickupAvailable = c.lua.eval('function(id) if id==900 then return false end end')
        guide = c.ns.DungeonGuide(g)
        route = c.ns.BuildDungeonRoute(guide, True)
        self.assertEqual(len(route.stops), 0); self.assertEqual(route.missing, 1)
        c.ns.ObservedPickupAvailable = c.lua.eval('function(id) if id==900 then return true end end')
        self.assertEqual(c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), True).stops[1].id, 900)

    def test_partial_prerequisite_still_routes_known_pickup_without_unlocking_child(self):
        c = solo()
        g = group(c, {900: quest(previousQuest=899),
                      899: quest(categoryPath='kalimdor/test-coast', ends=[])})
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), True)
        self.assertEqual(route.stops[1].id, 899)
        self.assertEqual(route.stops[1].kind, 'a')
        self.assertFalse(any(s.id == 900 or s.dungeonEntrance for s in route.stops.values()))
        self.assertTrue(route.partial)

    def test_accepted_goals_are_collected_not_sent_to_objectives(self):
        c = solo(); g = dungeon(c)
        accept(c, 900)
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), True)
        self.assertEqual([(s.id, s.kind) for s in route.stops.values() if not s.dungeonEntrance], [(901, 'a')])
        accept(c, 900, 901)
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), True)
        self.assertEqual(len(route.stops), 1); self.assertTrue(route.stops[1].dungeonEntrance)

    def test_entering_matching_dungeon_completes_preparation_without_quest_credit(self):
        c = solo(); map_canvas(c); g = dungeon(c)
        accept(c, 900, 901)
        c.ns.ShowDungeonQuests(g, True); c.drain()
        c.ns.DungeonEntryKey = c.lua.eval("function() return 'different-dungeon' end")
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertFalse(c.ns.selectedRoute.complete)
        c.ns.DungeonEntryKey = c.lua.eval("function() return 'test-cavern' end")
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertFalse(c.ns.Completed(900)); self.assertFalse(c.ns.Completed(901))

    def test_entering_before_quests_are_collected_does_not_claim_finished_preparation(self):
        c = solo(); map_canvas(c); g = dungeon(c)
        c.ns.ShowDungeonQuests(g, True); c.drain()
        c.ns.DungeonEntryKey = c.lua.eval("function() return 'test-cavern' end")
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_individual_quest_routes_only_that_pickup_without_entrance(self):
        c = solo(); map_canvas(c); g = dungeon(c, start_map=502)
        c.ns.ShowDungeonQuests(g, True, 901); c.drain()
        self.assertEqual(c.ns.routeSelection.pickupQuestID, 901)
        self.assertEqual([(s.id, s.kind) for s in c.ns.selectedRoute.stops.values()], [(901, 'a')])
        self.assertEqual(c.ns.selectedRoute.mapID, 502)
        accept(c, 901); c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertTrue(c.ns.selectedRoute.complete)

    def test_initial_order_uses_directed_travel_links_not_only_distance(self):
        c = solo(); map_canvas(c)
        c.ns.SetOption('travelNetwork', False)
        g = group(c, {900: quest('Walk-near', starts=[{'mapID': 501, 'x': .25, 'y': .4, 'name': 'Near'}]),
                      901: quest('Fast flight', starts=[{'mapID': 502, 'x': .8, 'y': .8, 'name': 'Flight'}])})
        c.lua.execute('''local ns=...
        pathCalls=0
        ns.FindTravelPath=function(a,b)
          pathCalls=pathCalls+1
          if b.mapID==502 then return {seconds=5,legs={}} end
          if a.mapID==502 then return {seconds=20,legs={}} end
          return {seconds=1000,legs={}}
        end''', c.ns)
        c.ns.ShowDungeonQuests(g, True)
        self.assertIsNotNone(c.ns.routePlanning)
        c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        self.assertGreater(c.lua.globals().pathCalls, 0)
        calls = c.lua.globals().pathCalls
        for _ in range(4): c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(c.lua.globals().pathCalls, calls)

    def test_loading_can_be_cancelled_without_replacing_current_guide(self):
        c = solo(); g = dungeon(c)
        c.ns.ShowDungeonQuests(g, True)
        self.assertIsNotNone(c.ns.routePlanning)
        c.ns.ClearRoute(); c.drain()
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.routePlanning)

    def test_switching_to_dungeon_preparation_reuses_the_same_small_window(self):
        c = solo(); map_canvas(c); g = dungeon(c)
        c.ns.SetOption('arrow', True)
        c.ns.ShowGuideOnMap(quest_guide(c, (900,)))
        c.ns.UpdateNavigation()
        window = c.ns.navigation
        c.ns.ShowDungeonQuests(g, True); c.drain(); c.ns.UpdateNavigation()
        self.assertTrue(c.lua.eval('rawequal')(window, c.ns.navigation))
        self.assertEqual(c.ns.routeSelection.mode, 'dungeon')

    def test_switching_guides_cancels_an_old_dungeon_planning_job(self):
        c = solo(); map_canvas(c); g = dungeon(c)
        c.ns.ShowDungeonQuests(g, True)
        other = c.ns.DungeonGuide(g, 901)
        c.ns.ActivateRoute(other)
        c.drain()
        self.assertEqual(c.ns.routeSelection.pickupQuestID, 901)

    def test_single_pickup_survives_saved_guide_restore(self):
        c = solo(); map_canvas(c); g = dungeon(c)
        c.ns.ShowDungeonQuests(g, True, 901); c.drain(); c.ns.SaveSelectedGuide()
        saved = c.ns.db.guideState[c.ns.self]
        c.ns.routeSelection = None; c.ns.pendingSavedGuide = saved
        c.ns.RestoreSavedGuide(); c.drain()
        self.assertEqual(c.ns.routeSelection.pickupQuestID, 901)
        self.assertEqual([s.id for s in c.ns.selectedRoute.stops.values()], [901])

    def test_no_outside_quests_are_auto_accepted_and_manual_skips_remain(self):
        c = solo(); map_canvas(c)
        g = group(c, {900: quest('Goal', previousQuest=899),
                      899: quest('Required', categoryPath='kalimdor/test-coast'),
                      898: quest('Outside guide', categoryPath='kalimdor/test-coast')})
        c.ns.SetOption('autoAccept', True)
        c.ns.ShowDungeonQuests(g, True); c.drain()
        c.ns.offered[899] = True
        c.ns.offered[898] = True
        self.assertTrue(c.ns.CanAutoAcceptGuideQuest(899))
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(898))
        c.ns.db.guideSkips[c.ns.self].quests[899] = True
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(g), False)
        self.assertEqual(len(route.stops), 0)
        self.assertTrue(c.ns.GuideQuestSkipped(899))


class DungeonQuestCardTests(unittest.TestCase):
    def test_clean_cards_show_pickup_and_status_without_record_button(self):
        c = solo(); g = dungeon(c)
        c.ns.ShowDungeonQuestList(g)
        f = c.ns.dungeonWindow
        self.assertIsNone(f.record)
        self.assertEqual(len(f.visibleQuests), 2)
        self.assertEqual(f.rows[1].title.text, 'Local quest')
        self.assertIn('Hub', f.rows[1].pickup.text)
        self.assertEqual(f.rows[1].state.text, 'Ready to collect')
        self.assertEqual(f.rows[1].route.caption.text, 'Route to pickup')
        self.assertIn('2 to collect', f.summary.text)

    def test_selecting_card_starts_only_its_pickup_route_and_closes_list(self):
        c = solo(); map_canvas(c); g = dungeon(c)
        c.ns.ShowDungeonQuestList(g)
        c.ns.dungeonWindow.rows[2].OnClick(); c.drain()
        self.assertEqual(c.ns.routeSelection.pickupQuestID, 901)
        self.assertFalse(c.ns.dungeonWindow.IsShown(c.ns.dungeonWindow))
        self.assertEqual(len(c.ns.selectedRoute.stops), 1)

    def test_filters_are_status_specific_and_updates_reuse_rows(self):
        c = solo(); g = dungeon(c); accept(c, 900)
        c.ns.ShowDungeonQuestList(g)
        f = c.ns.dungeonWindow
        f.filter.options['active'].OnClick()
        self.assertEqual([r.id for r in f.visibleQuests.values()], [900])
        count = len(f.rows)
        f.filter.options['pending'].OnClick()
        self.assertEqual([r.id for r in f.visibleQuests.values()], [901])
        self.assertEqual(len(f.rows), count)

    def test_closed_journal_does_not_prevent_visible_list_updates(self):
        c = solo(); g = dungeon(c)
        c.ns.ShowDungeonQuestList(g)
        accept(c, 900)
        c.ns.frame.OnEvent(c.ns.frame, 'QUEST_LOG_UPDATE'); c.drain()
        self.assertIn('1 in your log', c.ns.dungeonWindow.summary.text)

    def test_shipped_bfd_collection_and_single_routes_remain_faction_safe(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=30)
        c.lua.execute("function UnitRace() return 'Orc','Orc',2 end;function UnitClass() return 'Shaman','SHAMAN',7 end")
        c.ns.ReadProfile()
        g = next(g for g in c.ns.DungeonGroups().values() if g.key == 'blackfathom-deeps')
        guide = c.ns.DungeonGuide(g)
        for r in guide.records.values(): self.assertNotEqual(c.ns.CatalogueQuest(r.id).side, 'Alliance')
        alliance = next(i for i in g.ids.values() if c.ns.CatalogueQuest(i).side == 'Alliance')
        self.assertIsNone(c.ns.DungeonGuide(g, alliance))


if __name__ == '__main__':
    unittest.main()
