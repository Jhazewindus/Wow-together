"""Whole quest-flow comparisons: identical work/endpoints, no invented timing."""
import unittest

from test_addon import Client
from test_063 import guide_client, zone, order
from test_061 import world_quest, run_plan
from test_routes import catalogue


def fixture():
    c = guide_client(3)
    catalogue(c, {900: world_quest('Near work', minLevel=1, xp=100),
                  901: world_quest('Cave work', minLevel=1, xp=100),
                  902: world_quest('Unlocked cave work', minLevel=1, xp=100, previousQuest=900)})
    stops = [{'id': ident, 'kind': kind, 'title': c.ns.CatalogueQuest(ident).title,
              'mapID': 501, 'x': x, 'y': 0}
             for ident, kind, x in ((900, 'a', 0), (901, 'a', 0), (900, 'q', .1),
                                   (901, 'q', .9), (900, 't', 0), (902, 'a', 0),
                                   (902, 'q', .9), (901, 't', 0), (902, 't', 0))]
    c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,1000 end')
    distance = c.lua.eval('function(a,b) if a.mapID~=b.mapID then return 15000 end; return math.abs(a.x-b.x)*1000 end')
    return c, c.lua.table_from(stops, recursive=True), distance


def sequence(plan):
    return [(s.id, s.kind) for s in plan.values()]


class FlowTests(unittest.TestCase):
    def test_early_unlock_avoids_second_cave_visit_and_keeps_every_action(self):
        c, plan, distance = fixture()
        original = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        actual = sequence(plan)
        self.assertGreater(result.moves, 0)
        self.assertEqual(sorted(actual), sorted(original))
        self.assertEqual((actual[0], actual[-1]), (original[0], original[-1]))
        self.assertLess(actual.index((900, 't')), actual.index((902, 'a')))
        self.assertLess(actual.index((902, 'a')), actual.index((901, 'q')))
        self.assertEqual(abs(actual.index((902, 'q')) - actual.index((901, 'q'))), 1)
        self.assertLess(result.after.distance, result.before.distance)
        self.assertLessEqual(result.after.peakLog, result.before.peakLog)
        self.assertTrue(result.after.valid)

    def test_complete_external_chain_is_pulled_before_overlapping_work(self):
        c, plan, distance = fixture()
        c.ns.catalogue.quests[902].previousQuest = None
        c.ns.catalogue.quests[902].prerequisiteAll = c.lua.table_from([900, 901])
        # B must turn in first; no shortcut can collect C before that hand-in.
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(result.moves, 0)  # Invalid baseline is not silently repaired/pruned.
        self.assertFalse(result.before.valid)

    def test_or_gate_preserves_one_real_handin_without_requiring_every_branch(self):
        c, plan, distance = fixture()
        q = c.ns.catalogue.quests[902]
        q.previousQuest = None; q.prerequisiteAny = c.lua.table_from([899, 900])
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertGreater(result.moves, 0)
        actual = sequence(plan)
        self.assertLess(actual.index((900, 't')), actual.index((902, 'a')))

    def test_review_and_missing_geography_are_recovery_boundaries(self):
        for field in ('unknownLocation', 'planNeedsReview'):
            c, plan, distance = fixture()
            plan[5][field] = True
            before = sequence(plan)
            result = c.ns.ImproveQuestFlow(plan, distance, False, None)
            self.assertEqual(sequence(plan), before)
            self.assertEqual(result.moves, 0)

    def test_cannot_make_future_pickup_more_dependent_on_unmeasured_xp(self):
        c, plan, distance = fixture()
        c.ns.catalogue.quests[901].xp = 2000
        c.ns.catalogue.quests[902].minLevel = 5
        c.ns.xpBaseline = c.lua.table_from({1:100, 2:200, 3:400, 4:800, 5:1600})
        # Delaying a useful reward until after a level-gated pickup increases
        # missing progression, even if both versions visit the same points.
        model = c.ns.NewGuideFlowModel(plan, distance, None)
        earlier = [plan[i] for i in (1, 2, 3, 4, 5, 8, 6, 7, 9)]
        good = model.evaluate(c.lua.table_from(earlier))
        bad = model.evaluate(plan)
        self.assertLess(good.levelDeficitXP, bad.levelDeficitXP)
        self.assertTrue(bad.progressionNeedsReview)
        self.assertEqual(bad.combatXPUnknown, 0)  # Unknown targets never get fabricated combat XP.

    def test_known_capacity_fails_replay_instead_of_claiming_room(self):
        c, plan, distance = fixture()
        check = c.ns.NewGuideFlowModel(plan, distance, c.lua.table_from({'logCapacity':1})).evaluate(plan)
        self.assertFalse(check.valid)
        self.assertEqual(check.peakLog, 2)
        self.assertEqual(check.logOverflow, 1)
        unknown = c.ns.NewGuideFlowModel(plan, distance, None).evaluate(plan)
        self.assertFalse(unknown.logCapacityKnown)

    def test_same_mob_kills_share_a_lower_bound_only_when_bundled(self):
        c, plan, distance = fixture()
        for i, quantity in ((4, 7), (7, 10)):
            plan[i].action, plan[i].entityID, plan[i].quantity = 'kill', 123, quantity
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(result.before.minimumKills, 17)
        self.assertEqual(result.after.minimumKills, 10)
        self.assertEqual(result.after.combatXPUnknown, 2)
        self.assertEqual(result.after.questXP, result.before.questXP)

    def test_loot_quantities_are_not_converted_into_fake_kill_or_drop_rates(self):
        c, plan, distance = fixture()
        for i in (4, 7): plan[i].action, plan[i].entityID, plan[i].quantity = 'collect', 123, 10
        check = c.ns.NewGuideFlowModel(plan, distance, None).evaluate(plan)
        self.assertEqual(check.minimumKills, 0)
        self.assertEqual(check.combatXPUnknown, 2)
        self.assertNotIn('seconds', check.keys())

    def test_already_accepted_shared_kills_are_not_counted_twice_for_separated_steps(self):
        c, plan, distance = fixture()
        c.ns.catalogue.quests[902].previousQuest = None
        for i, qty in ((4,7),(7,10)):plan[i].action,plan[i].entityID,plan[i].quantity='kill',123,qty
        early = c.lua.table_from([plan[i] for i in (1,2,6,3,4,5,7,8,9)])
        result = c.ns.NewGuideFlowModel(early,distance,None).evaluate(early)
        self.assertEqual(result.minimumKills,10)

    def test_simulation_rejects_deleted_duplicated_reversed_work_and_changed_endpoint(self):
        c, plan, distance = fixture(); model = c.ns.NewGuideFlowModel(plan, distance, None)
        variants = ([plan[i] for i in range(1, 9)],
                    [plan[i] for i in (1, 2, 3, 4, 5, 6, 6, 8, 9)],
                    [plan[i] for i in (1, 2, 3, 4, 6, 5, 7, 8, 9)],
                    [plan[i] for i in (1, 2, 3, 4, 5, 6, 7, 9, 8)])
        for variant in variants: self.assertFalse(model.evaluate(c.lua.table_from(variant)).valid)

    def test_escort_is_not_split_by_cave_work(self):
        c, plan, distance = fixture(); plan[7].action = 'escort'
        c.ns.ImproveQuestFlow(plan, distance, False, None)
        actual = sequence(plan)
        self.assertEqual(actual.index((902, 'q')), actual.index((902, 'a')) + 1)

    def test_lower_distance_cannot_push_difficult_work_ahead_of_valuable_xp(self):
        c, plan, distance = fixture()
        c.ns.catalogue.quests[900].xp = 0
        c.ns.catalogue.quests[901].xp = 1000
        c.ns.catalogue.quests[902].level = 9
        c.ns.xpBaseline = c.lua.table_from({i:100 for i in range(1,61)})
        plan = c.lua.table_from([plan[i] for i in (1,2,3,4,8,5,6,7,9)])
        baseline = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertLessEqual(result.after.difficultyPressure, result.before.difficultyPressure)
        # A move that merely arrives earlier at the same hard objective does
        # not receive an invented combat-time benefit.
        self.assertEqual(sequence(plan), baseline)

    def test_unlock_reason_names_the_chain_and_why_returning_helps(self):
        c, plan, distance = fixture()
        c.ns.ImproveQuestFlow(plan, distance, False, None)
        g = zone(c);g.fixedPlan = plan
        parent = next(s for s in plan.values() if s.id==900 and s.kind=='t')
        decision = c.ns.GuideDestinationDecision(parent,g,c.lua.table_from({'stops':plan}))
        self.assertEqual(decision.code,'unlock-loop')
        self.assertIn('Unlocked cave work',decision.why)
        self.assertIn('Cave work',decision.why)
        self.assertIn('same area',decision.why)
        c.lua.globals().finished[901] = True
        c.ns.guideProgressRevision = (c.ns.guideProgressRevision or 0) + 1
        self.assertNotEqual(c.ns.GuideDestinationDecision(parent,g,None).code,'unlock-loop')

    def test_started_guide_survives_progress_scan_and_movement_with_same_order(self):
        c = guide_client(26); g = zone(c)
        c.ns.ShowGuideOnMap(g); run_plan(c)
        original = order(g)
        c.lua.execute("entries={{questID=900,title='Quest 0',isHeader=false}};C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .8,.9 end} end")
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(order(c.ns.routeSelection), original)


class TravelComparisonTests(unittest.TestCase):
    def client(self):
        c = guide_client(1)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,1000 end')
        c.ns.travelData = c.lua.table_from({'nodes':{
            'WEST':{'mapID':501, 'x':0, 'y':0},
            'EAST':{'mapID':502, 'x':0, 'y':0},
            'OTHER':{'mapID':503, 'x':0, 'y':0}}, 'edges':[
                {'from':'WEST','to':'EAST','method':'ship','seconds':100,'faction':'Horde'},
                {'from':'WEST','to':'OTHER','method':'taxi','seconds':1}],
            'settlements':[], 'factors':{}}, recursive=True)
        distance = c.lua.eval('function(a,b) if a.mapID~=b.mapID then return 15000 end;return math.abs(a.x-b.x)*1000 end')
        return c, distance

    def test_cross_zone_reference_uses_transport_and_never_assumes_a_flight(self):
        c, distance = self.client()
        cost, reset = c.ns.NewFixedTravelCost(distance, False, None)
        a = c.lua.table_from({'mapID':501,'x':0,'y':0})
        b = c.lua.table_from({'mapID':502,'x':0,'y':0})
        self.assertEqual(cost(a,b), (700,'network-estimate'))
        target = c.lua.table_from({'mapID':503,'x':0,'y':0})
        self.assertEqual(cost(a,target), (15000,'unmapped-estimate'))
        self.assertIsNone(c.ns.PublishedTravelDistance('WEST','EAST'))  # Existing flight geometry remains walk-only.

    def test_faction_incompatible_transport_is_not_a_generic_shortcut(self):
        c, distance = self.client(); c.ns.profile.faction = 'Alliance'
        cost, _ = c.ns.NewFixedTravelCost(distance, False, None)
        self.assertEqual(cost(c.ns.travelData.nodes.WEST,c.ns.travelData.nodes.EAST), (15000,'unmapped-estimate'))

    def test_default_geometry_queries_cannot_corrupt_yielding_guide_graph(self):
        c, distance = self.client()
        c.lua.globals().flowNS = c.ns; c.lua.globals().flowDistance = distance
        c.lua.execute('''
        for i=1,240 do table.insert(flowNS.travelData.edges,
            {from='WEST',to='EAST',method='ship',seconds=100,faction='Horde'}) end
        flowJob=coroutine.create(function()
            local cost=flowNS.NewFixedTravelCost(flowDistance,true)
            return cost(flowNS.travelData.nodes.WEST,flowNS.travelData.nodes.EAST)
        end)
        assert(coroutine.resume(flowJob));assert(coroutine.status(flowJob)=='suspended')
        while coroutine.status(flowJob)~='dead' do
            assert(flowNS.PublishedTravelDistance('WEST','EAST')==nil)
            local ok,length,basis=coroutine.resume(flowJob);assert(ok)
            if coroutine.status(flowJob)=='dead' then assert(length==700 and basis=='network-estimate') end
        end
        ''')


if __name__ == '__main__': unittest.main()
