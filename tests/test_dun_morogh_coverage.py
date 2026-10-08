"""Dun Morogh reviewed facts and source-gap preservation under Lua 5.1."""
import copy
import sys
import unittest
from test_addon import Client, ROOT
from test_0859 import dun_morogh
from test_063 import order
from test_routes import guide
sys.path.insert(0, str(ROOT/'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class DunMoroghCoverageTests(unittest.TestCase):
    def test_boar_point_keeps_both_requirements_and_unmapped_copper(self):
        c = dun_morogh(); q = c.ns.CatalogueQuest(95217)
        self.assertEqual({(r.itemID,r.quantity) for r in q.requiredItems.values()}, {(2840,12),(267416,4)})
        self.assertTrue(q.objectiveLocationsIncomplete)
        self.assertEqual((q.missingRequirements[1].entityID,q.missingRequirements[1].quantity),(2840,12))
        p = q.objectives[1]
        self.assertEqual((p.entityID,p.mapID,p.x,p.y,p.itemID,p.quantity), (1689,1426,.738,.526,267416,4))
        self.assertEqual(p.action,'loot')
        g = guide(c,(95217,));g.fixedRoute = True
        c.ns.GenerateFixedGuide(g,False)
        work = [s for s in g.fixedPlan.values() if s.kind == 'q']
        self.assertEqual(len(work),2)
        self.assertEqual({s.itemID for s in work},{2840,267416})
        self.assertTrue(next(s for s in work if s.itemID == 2840).unknownLocation)
        self.assertIn('Copper Bar',c.ns.GuideStepAction(next(s for s in work if s.itemID == 2840)))

    def test_location_correction_is_atomic_and_does_not_clear_gaps(self):
        records = own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
        original = copy.deepcopy(records)
        self.assertEqual(apply_stage_corrections(records),[])
        self.assertEqual(records,original)
        records[95217]['objectives'][0]['x'] = .1
        invalid = copy.deepcopy(records)
        with self.assertRaises(ValueError):apply_stage_corrections(records)
        self.assertEqual(records,invalid)

    def test_rime_identities_and_tester_gate_remain_distinct(self):
        c = dun_morogh(); a,b = c.ns.CatalogueQuest(99160),c.ns.CatalogueQuest(99161)
        self.assertEqual(a.title,b.title)
        self.assertEqual((a.objectives[1].entityID,a.objectives[1].quantity),(276003,10))
        self.assertEqual((b.objectives[1].entityID,b.objectives[1].itemID,b.objectives[1].quantity),(276009,286325,1))
        self.assertEqual(b.previousQuest,99162)
        self.assertIn('Tester report',b.prerequisiteSource)
        self.assertIn('build 70245',b.prerequisiteSource)
        c.ns.active[99162] = 'Treacherous Cold';c.ns.readyToTurnIn[99162] = True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(99161,c.ns.self)[0])
        c.lua.globals().finished[99162] = True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(99161,c.ns.self))

    def test_unresolved_pickup_and_senir_conditions_are_retained(self):
        c = dun_morogh(); treaty = c.ns.CatalogueQuest(98423)
        self.assertFalse(treaty.starts and len(treaty.starts))
        self.assertEqual((treaty.startRefs[1].entityType,treaty.startRefs[1].entityID),('item',281030))
        self.assertEqual(treaty.ends[1].entityID,2784)
        self.assertEqual(c.ns.CatalogueQuest(282).previousQuest,218)
        self.assertTrue(c.ns.CatalogueQuest(282).prerequisitesUnverified)
        self.assertNotEqual(c.ns.CatalogueQuest(282).startRefs[1].entityID,c.ns.CatalogueQuest(420).startRefs[1].entityID)

    def test_complete_zone_keeps_fixed_order_for_dwarf_and_gnome(self):
        for race in (3,7):
            c = dun_morogh();c.ns.profile.raceID = race
            g = next(g for g in c.ns.LevelingGuideChoices().values() if g.key=='level-zone:eastern-kingdoms/dun-morogh:levels:1-10')
            c.ns.BuildGuideRoute(g,False)
            before = order(g);planned = {s.id for s in g.fixedPlan.values()}
            self.assertTrue({r.id for r in g.records.values()}.issubset(planned))
            self.assertTrue({99160,99161,99162}.issubset(planned))
            c.ns.active[99162]='Treacherous Cold'
            c.lua.globals().finished[179]=True
            c.ns.BuildGuideRoute(g,False)
            self.assertEqual(order(g),before)

if __name__ == '__main__':unittest.main()
