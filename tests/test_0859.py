"""Reported Forever Dun Morogh chain gates pickup on the preceding hand-in."""
import sys
import unittest

from test_addon import Client, ROOT
from test_routes import guide

sys.path.insert(0, str(ROOT / 'tools'))
from import_warcraftdb import apply_corrections


def dun_morogh():
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=7)
    c.lua.execute('''
        grouped=false
        function UnitFactionGroup() return 'Alliance' end
        function UnitClass() return 'Hunter','HUNTER',3 end
        function UnitRace() return 'Dwarf','Dwarf',3 end
    ''')
    c.ns.ReadProfile(); c.ns.UpdateRoster()
    c.ns.guideLevel = '1-10'
    return c


class RimeChainTests(unittest.TestCase):
    def test_correction_is_idempotent_and_keeps_tester_provenance(self):
        records = {99161: {'title': "Rime's Wrath"}, 99162: {'title': 'Treacherous Cold'}}
        self.assertEqual(apply_corrections(records), [99161])
        self.assertEqual(records[99161]['previousQuest'], 99162)
        self.assertIn('Tester report', records[99161]['prerequisiteSource'])
        self.assertEqual(apply_corrections(records), [99161])

    def test_changed_identity_or_conflicting_predecessor_requires_review(self):
        for altered in ({'title': 'Different quest'},
                        {'title': "Rime's Wrath", 'previousQuest': 111}):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                apply_corrections({99161: altered, 99162: {'title': 'Treacherous Cold'}})

    def test_accepting_or_finishing_objectives_does_not_unlock_rime(self):
        c = dun_morogh()
        q = c.ns.CatalogueQuest(99161)
        self.assertEqual(q.previousQuest, 99162)
        self.assertFalse(c.ns.CatalogueAllowed(99161, c.ns.profile, c.ns.self)[0])
        c.ns.active[99162] = 'Treacherous Cold'
        c.ns.readyToTurnIn[99162] = True
        allowed, reason = c.ns.CatalogueAllowed(99161, c.ns.profile, c.ns.self)
        self.assertFalse(allowed)
        self.assertIn('Treacherous Cold', reason)
        c.lua.globals().finished[99162] = True
        self.assertTrue(c.ns.CatalogueAllowed(99161, c.ns.profile, c.ns.self))

    def test_shared_dependency_applies_to_other_compatible_classes_and_races(self):
        for class_id, race_id in ((3, 3), (8, 7), (1, 1)):
            with self.subTest(class_id=class_id, race_id=race_id):
                # Completion is retained for a character. Use a new character
                # fixture rather than trying to revoke a confirmed hand-in.
                c = dun_morogh()
                c.ns.profile.classID, c.ns.profile.raceID = class_id, race_id
                self.assertFalse(c.ns.CatalogueAllowed(99161, c.ns.profile, c.ns.self)[0])
                c.lua.globals().finished[99162] = True
                self.assertTrue(c.ns.CatalogueAllowed(99161, c.ns.profile, c.ns.self))

    def test_fixed_and_adaptive_pickups_wait_for_handin_even_if_offer_is_seen(self):
        c = dun_morogh()
        c.ns.active[99162] = 'Treacherous Cold'
        c.ns.offered[99161] = True
        g = guide(c, (99161, 99162)); g.fixedRoute = True
        route = c.ns.BuildGuideRoute(g, False)
        self.assertNotIn(99161, {s.id for s in route.previewStops.values()})
        g.fixedRoute = False
        self.assertIsNone(c.ns.RouteStop(c.ns.CatalogueRecord(99161), c.ns.self))
        c.lua.globals().finished[99162] = True
        self.assertIsNotNone(c.ns.RouteStop(c.ns.CatalogueRecord(99161), c.ns.self))

    def test_fixed_guide_places_all_cold_work_and_handin_before_rime_pickup(self):
        c = dun_morogh()
        g = next(g for g in c.ns.LevelingGuideChoices().values()
                 if g.key == 'level-zone:eastern-kingdoms/dun-morogh:levels:1-10')
        c.ns.GenerateFixedGuide(g, False)
        stages = [(s.id, s.kind) for s in g.fixedPlan.values()]
        pickup = stages.index((99161, 'a'))
        self.assertLess(stages.index((99162, 't')), pickup)
        for index, (ident, kind) in enumerate(stages):
            if ident == 99162:
                self.assertLess(index, pickup)
        self.assertEqual([kind for ident, kind in stages if ident == 99161], ['a', 'q', 't'])
        self.assertGreater(sum(ident == 99162 and kind == 'q' for ident, kind in stages), 1)


if __name__ == '__main__':
    unittest.main()
