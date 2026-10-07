"""Whole overlapping trips can improve even when each individual move cannot."""
import unittest

from test_063 import guide_client, zone, order
from test_061 import world_quest
from test_routes import catalogue
from test_066 import reload


def trip_fixture(count=2, onward=True):
    c = guide_client(count + 1)
    ids = list(range(900, 901 + count))
    # An independent later loop has the same maximum held quests. This avoids
    # claiming that a combined trip is better if it increases log pressure.
    if onward:
        ids += list(range(910, 911 + count))
    catalogue(c, {i: world_quest('Quest ' + str(i), minLevel=1, xp=0) for i in ids})
    stages = [(900, 'a', 0), (900, 'q', .9)]
    stages += [(i, 'a', 0) for i in range(901, 901 + count)]
    stages += [(i, 'q', .9) for i in range(901, 901 + count)]
    stages += [(i, 't', 0) for i in range(900, 901 + count)]
    if onward:
        stages += [(i, 'a', 0) for i in range(910, 911 + count)]
        stages += [(i, 'q', .1) for i in range(910, 911 + count)]
        stages += [(i, 't', 0) for i in range(910, 911 + count)]
    plan = c.lua.table_from([{'id': i, 'kind': kind, 'mapID': 501,
                             'x': x, 'y': 0, 'title': 'Quest ' + str(i)}
                            for i, kind, x in stages], recursive=True)
    distance = c.lua.eval('''function(a,b)
        if a.mapID ~= b.mapID then return 15000, 'unmapped-estimate' end
        return math.abs(a.x-b.x)*1000, 'local-estimate'
    end''')
    return c, plan, distance


def sequence(plan):
    return [(s.id, s.kind) for s in plan.values()]


class CompleteTripTests(unittest.TestCase):
    def test_two_later_quests_remove_a_return_that_single_moves_leave(self):
        c, plan, distance = trip_fixture()
        old = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        # 0.8.51 retained this 3,800-unit full route. Combining both closures
        # removes a 1,800-unit duplicate visit, retaining the onward loop.
        self.assertEqual(result.before.distance, 3800)
        self.assertEqual(result.after.distance, 2000)
        self.assertEqual(result.after.peakLog, result.before.peakLog)
        self.assertTrue(result.after.valid)
        self.assertEqual(sorted(sequence(plan)), sorted(old))
        self.assertEqual((sequence(plan)[0], sequence(plan)[-1]), (old[0], old[-1]))
        self.assertTrue(any(change.kind == 'objective-trip' for change in result.changes.values()))
        actual = sequence(plan)
        for ident in (901, 902):
            self.assertLess(actual.index((ident, 'a')), actual.index((900, 'q')))
            self.assertLess(actual.index((ident, 'q')), actual.index((900, 't')))

    def test_three_quests_are_considered_when_pairs_leave_the_return_needed(self):
        c, plan, distance = trip_fixture(3)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual((result.before.distance, result.after.distance), (3800, 2000))
        self.assertTrue(result.after.valid)
        self.assertEqual(result.after.peakLog, 4)
        trip = next(change for change in result.changes.values() if change.kind == 'objective-trip')
        self.assertEqual(set(trip.questIDs.values()), {901, 902, 903})
        self.assertEqual(trip.actions, 6)

    def test_shorter_trip_cannot_increase_peak_held_quests(self):
        c, plan, distance = trip_fixture(onward=False)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(result.after.distance, result.before.distance)
        self.assertEqual(result.after.peakLog, 2)  # Existing early hand-in still helps.
        self.assertFalse(any(change.kind == 'objective-trip' for change in result.changes.values()))

    def test_missing_or_review_boundary_prevents_collective_move(self):
        for field in ('unknownLocation', 'planNeedsReview'):
            c, plan, distance = trip_fixture()
            plan[3][field] = True
            old = sequence(plan)
            result = c.ns.ImproveQuestFlow(plan, distance, False, None)
            self.assertEqual(sequence(plan), old)
            self.assertEqual(result.moves, 0)

    def test_unknown_drop_counts_and_use_item_stages_remain_original_objects(self):
        c, plan, distance = trip_fixture()
        plan[5].action, plan[5].entityID, plan[5].quantityUnknown = 'collect', 123, True
        plan[6].action, plan[6].useItemName, plan[6].spellID = 'use', 'Test item', 456
        original = list(plan.values())
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(result.after.distance, 2000)
        self.assertEqual(result.after.minimumKills, 0)
        self.assertTrue(original[4].quantityUnknown)
        self.assertEqual((original[5].useItemName, original[5].spellID), ('Test item', 456))
        actual = sequence(plan)
        self.assertLess(actual.index((902, 'a')), actual.index((902, 'q')))
        self.assertLess(actual.index((902, 'q')), actual.index((902, 't')))

    def test_immediate_escort_is_not_detached_or_treated_as_generic_work(self):
        c, plan, distance = trip_fixture()
        plan[5].action = 'escort'
        plan = c.lua.table_from([plan[i] for i in (1, 2, 3, 5, 4, 6) + tuple(range(7, len(plan) + 1))])
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertTrue(result.after.valid)
        actual = sequence(plan)
        self.assertEqual(actual.index((901, 'q')), actual.index((901, 'a')) + 1)

    def test_other_zone_is_not_an_overlapping_objective_from_matching_coordinates(self):
        c, plan, distance = trip_fixture()
        plan[6].mapID = 502
        old = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(sorted(sequence(plan)), sorted(old))
        self.assertFalse(any(change.kind == 'objective-trip' for change in result.changes.values()))
        self.assertLessEqual(result.after.uncertainTravelLegs, result.before.uncertainTravelLegs)
        self.assertLess(sequence(plan).index((900, 'q')), sequence(plan).index((902, 'q')))

    def test_level_reward_must_not_move_behind_future_pickups(self):
        c, plan, distance = trip_fixture()
        c.ns.catalogue.quests[910].xp = 100
        c.ns.catalogue.quests[901].minLevel = 2
        c.ns.xpBaseline = c.lua.table_from({1: 100, 2: 1000, 3: 2000})
        plan = c.lua.table_from([plan[i] for i in (1, 2, 10, 13, 16, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 17, 18)])
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertTrue(result.after.valid)
        self.assertEqual(result.before.levelDeficitXP, 0)
        self.assertEqual(result.after.levelDeficitXP, 0)
        actual = sequence(plan)
        self.assertLess(actual.index((910, 't')), actual.index((901, 'a')))

    def test_started_trip_and_its_reason_survive_reload_without_replanning(self):
        c, plan, distance = trip_fixture()
        c.ns.ImproveQuestFlow(plan, distance, False, None)
        g = zone(c)
        for index, stop in plan.items(): stop.guideStep = index
        g.fixedPlan = plan
        c.ns.ActivateRoute(g)
        fresh = reload(c)
        self.assertEqual(order(fresh.ns.routeSelection), order(g))
        pickup = next(s for s in fresh.ns.routeSelection.fixedPlan.values() if s.id == 901 and s.kind == 'a')
        fresh.ns.active[900] = 'Quest 900'
        reason = fresh.ns.GuideDestinationDecision(pickup, fresh.ns.routeSelection, fresh.ns.selectedRoute)
        self.assertEqual(reason.code, 'pickup-loop')
        self.assertIn('before leaving', reason.why)


if __name__ == '__main__': unittest.main()
