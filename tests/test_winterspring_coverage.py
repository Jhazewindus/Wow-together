"""Winterspring starters, supplied handoffs and evidenced ordinary scope."""
import copy
import sys
import unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
from test_063 import order
sys.path.insert(0,str(ROOT/'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections

class WinterspringCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']

    def test_object_investigations_interact_instead_of_speak(self):
        c=client('Alliance',level=58);g=guide(c,(4861,4863,5084));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        for s in g.fixedPlan.values():
            if s.kind=='q':
                self.assertEqual(s.action,'interact');self.assertEqual(s.entityType,'object')
                self.assertTrue(c.ns.GuideStepAction(s).startswith('Interact with '))
        self.assertEqual(self.q[4863]['prerequisiteAny'],[4861])

    def test_looted_starters_keep_acquisition_but_no_second_farm(self):
        for ident,item in [(4882,12558),(5123,12842)]:
            q=self.q[ident];self.assertEqual(q['starts'][0]['action'],'start-item')
            self.assertEqual((q['starts'][0]['sourceAction'],q['starts'][0]['itemID']),('loot',item))
            self.assertFalse(q['requirements']);self.assertFalse(q['objectives'])
            self.assertEqual(q['requiredItems'][0]['itemID'],item)
            c=client('Horde',level=58);g=guide(c,(ident,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
            work=next(s for s in g.fixedPlan.values()if s.kind=='q')
            self.assertEqual(work.action,'talk');self.assertIsNone(work.itemID)

    def test_delivery_handoffs_keep_items_and_real_handin_gates(self):
        for ident,item in [(4883,12558),(5128,12842),(5252,13347),(5253,13347)]:
            q=self.q[ident];self.assertFalse(q['requirements']);self.assertFalse(q['objectives'])
            self.assertFalse(q.get('objectiveLocationsIncomplete'));self.assertFalse(q.get('missingRequirements'))
            self.assertEqual(q['requiredItems'][0]['itemID'],item)
            self.assertEqual(q['providedItems'][0]['entityID'],item)
        c=client('Alliance',level=58);c.ns.active[5252]='Highborne';c.ns.readyToTurnIn[5252]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(5253,c.ns.self)[0])
        c.lua.globals().finished[5252]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(5253,c.ns.self))
        self.assertEqual(self.q[5253]['ends'][0]['mapID'],1457)

    def test_profession_only_records_stay_in_catalogue_outside_ordinary_scope(self):
        for faction in ['Horde','Alliance']:
            c=client(faction,level=58);c.ns.guideLevel='all'
            for ident in [5124,5126,8798]:
                self.assertTrue(c.ns.IsLevelingExcludedQuest(ident));self.assertIsNotNone(c.ns.CatalogueQuest(ident))
            g=next(g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Winterspring')
            self.assertFalse({5124,5126,8798}&{r.id for r in g.records.values()})
            self.assertFalse(c.ns.IsLevelingExcludedQuest(5163));self.assertFalse(c.ns.IsLevelingExcludedQuest(5247))
        self.assertTrue(self.q[5124]['objectiveLocationsIncomplete'])
        self.assertTrue(self.q[5124]['prerequisitesUnverified'])

    def test_yeti_keeps_all_three_use_targets_and_supplied_tool(self):
        q=self.q[5163];self.assertEqual(q['providedItems'][0]['entityID'],12928)
        self.assertTrue(q['providedItems'][0]['quantityUnknown'])
        self.assertEqual({(p['entityID'],p['mapID'],p['quantity'],p['action'])for p in q['objectives']},
                         {(10978,1452,1,'use'),(7583,1446,1,'use'),(10977,1449,1,'use')})
        self.assertEqual(q['prerequisiteAny'],[977])

    def test_unknown_mechanics_and_elite_work_remain_explicit(self):
        self.assertTrue(self.q[975]['objectiveLocationsIncomplete'])
        self.assertTrue(self.q[8471]['unmodeledObjectiveKinds'])
        self.assertTrue(self.q[8471]['objectiveLocationsIncomplete'])
        self.assertEqual(self.q[8471]['starts'][0]['itemID'],20742)
        c=client('Alliance',level=58);self.assertIsNotNone(c.ns.QuestGroupWarning(5056))
        c.ns.SetOption('classQuests',False);self.assertTrue(c.ns.ClassQuestEnabled(5163))

    def test_fixed_order_and_atomic_reapplication_preserve_user_progress(self):
        for faction in ['Alliance','Horde']:
            c=client(faction,level=58);c.ns.guideLevel='all'
            g=next(g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Winterspring')
            c.ns.BuildGuideRoute(g,False);before=order(g)
            self.assertEqual({r.id for r in g.records.values()},{s.id for s in g.fixedPlan.values()})
            c.lua.globals().finished[5123]=True;c.ns.active[5163]='Yeti'
            c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
        q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[])
        q[5128]['requiredItems'][0]['quantity']=2;old=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,old)
