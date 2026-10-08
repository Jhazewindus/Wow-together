"""Reviewed Mulgore facts; host behavior does not establish native beta offers."""
import copy
import sys
import unittest
from test_addon import Client, ROOT
from test_089 import identity
from test_063 import order
from test_routes import guide
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections, apply_stage_corrections

CHAIN = (99079, 99081, 99101, 99080, 99082)


def client():
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=12)
    c.lua.globals().grouped = False
    identity(c)
    c.lua.execute("function UnitRace() return 'Tauren','Tauren',6 end")
    c.ns.ReadProfile(); c.ns.UpdateRoster()
    return c


class MulgoreCoverageTests(unittest.TestCase):
    def test_both_hunt_and_malah_chains_wait_for_actual_handins(self):
        c = client()
        for chain in ((747, 750, 780), CHAIN):
            g = guide(c, chain); g.fixedRoute = True
            c.ns.GenerateFixedGuide(g, False)
            stages = [(s.id, s.kind) for s in g.fixedPlan.values()]
            for parent, child in zip(chain, chain[1:]):
                with self.subTest(child=child):
                    self.assertEqual(c.ns.CatalogueQuest(child).previousQuest, parent)
                    self.assertLess(stages.index((parent, 't')), stages.index((child, 'a')))
                    c.ns.active[parent] = c.ns.QuestTitle(parent)
                    c.ns.readyToTurnIn[parent] = True
                    c.ns.offered[child] = True
                    self.assertFalse(c.ns.CataloguePrerequisitesAllowed(child, c.ns.self)[0])
                    c.lua.globals().finished[parent] = True
                    self.assertTrue(c.ns.CataloguePrerequisitesAllowed(child, c.ns.self))

    def test_known_parent_does_not_remove_offer_confirmation(self):
        c = client()
        for ident, parent, npc in ((99101,99081,3222),(99082,99080,2993)):
            c.lua.globals().finished[parent] = True
            q = c.ns.CatalogueQuest(ident)
            self.assertTrue(q.pickupRequiresOffer)
            self.assertTrue(q.prerequisitesUnverified)
            self.assertFalse(c.ns.CatalogueAllowed(ident, c.ns.profile, c.ns.self)[0])
            c.lua.execute(f"UnitGUID=function() return 'Creature-0-1-2-3-{npc}-ABC' end")
            c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID':ident}], recursive=True), True)
            self.assertTrue(c.ns.CatalogueAllowed(ident, c.ns.profile, c.ns.self))

    def test_baine_points_agree_without_changing_objective_work(self):
        c = client()
        for ident in (745,746,763,767,99080,99082,99101):
            q = c.ns.CatalogueQuest(ident)
            for role in ('starts','ends'):
                for point in q[role].values():
                    if point.entityID == 2993:
                        self.assertEqual((point.mapID, point.x, point.y), (1412,.474,.602))
        q = c.ns.CatalogueQuest(780)
        self.assertEqual({(p.itemID,p.quantity,p.entityID) for p in q.objectives.values()},
                         {(4848,8,2966),(4849,8,2966)})
        self.assertTrue(all(abs(p.x-.576)<1e-8 and p.y==.852 for p in q.objectives.values()))

    def test_corrections_preserve_unknowns_and_reject_new_location_conflicts(self):
        quests = own_lua(ROOT/'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']
        before = copy.deepcopy(quests)
        apply_corrections(quests)
        self.assertEqual(apply_stage_corrections(quests), [])
        self.assertEqual(quests, before)
        q = quests[99101]
        q['ends'][0]['x'] = .1
        invalid = copy.deepcopy(quests)
        with self.assertRaises(ValueError): apply_stage_corrections(quests)
        self.assertEqual(quests, invalid)

    def test_darker_truth_pickup_remains_unknown_and_edition_stays_excluded(self):
        c = client()
        q = c.ns.CatalogueQuest(96294)
        self.assertFalse(q.starts and len(q.starts))
        self.assertEqual(q.requiredItems[1].itemID, 273659)
        self.assertTrue(c.ns.IsLevelingExcludedQuest(5844))
        self.assertTrue(c.ns.IsLevelingExcludedQuest(774))

    def test_tauren_scope_keeps_racial_continuations_and_fixed_order(self):
        c = client(); c.ns.guideLevel = '1-10'
        g = next(g for g in c.ns.LevelingGuideChoices().values()
                 if g.key == 'level-zone:kalimdor/mulgore:levels:1-10')
        c.ns.BuildGuideRoute(g, False)
        planned = {s.id for s in g.fixedPlan.values()}
        self.assertTrue({747,750,780,758,759,760}.issubset(planned))
        self.assertTrue(set(CHAIN).issubset(planned))
        self.assertTrue({r.id for r in g.records.values()}.issubset(planned))
        before = order(g)
        c.lua.globals().finished[747] = True
        c.ns.active[750] = 'The Hunt Continues'
        c.ns.BuildGuideRoute(g, False)
        self.assertEqual(order(g), before)

    def test_class_and_race_gates_remain_scoped(self):
        c = client()
        c.ns.SetOption('classQuests', False)
        self.assertFalse(c.ns.ClassQuestEnabled(1519))
        self.assertTrue(c.ns.ClassQuestEnabled(747))
        c.ns.SetOption('classQuests', True)
        self.assertTrue(c.ns.ClassQuestEnabled(1519))
        for ident, race in ((5655,8),(5661,5)):
            c.ns.profile.classID, c.ns.profile.raceID = 5, race
            self.assertTrue(c.ns.CatalogueIdentityAllowed(ident,c.ns.profile))
            c.ns.profile.raceID = 6
            self.assertFalse(c.ns.CatalogueIdentityAllowed(ident,c.ns.profile)[0])

if __name__ == '__main__': unittest.main()
