"""Thoradin object frames, real hand-ins and saved cross-continent chain scope."""
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


class ThoradinCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']

    def test_shared_handoffs_use_same_observed_object_and_real_map_frame(self):
        q=self.quests
        a,b=q[79974]['ends'][0],q[79975]['starts'][0]
        self.assertEqual((a['entityID'],a['mapID'],a['x'],a['y']),
                         (b['entityID'],b['mapID'],b['x'],b['y']))
        a,b=q[79975]['ends'][0],q[79976]['starts'][0]
        self.assertEqual((a['entityID'],a['mapID'],a['x'],a['y']),
                         (b['entityID'],b['mapID'],b['x'],b['y']))
        self.assertEqual((a['entityID'],a['mapID'],a['sourceAreaID']), (406918,1417,45))
        self.assertAlmostEqual(a['x'],.2248)
        self.assertAlmostEqual(a['y'],.2423)
        satchel=q[79976]['ends'][0]
        self.assertEqual((satchel['entityID'],satchel['mapID']), (424006,1417))
        self.assertAlmostEqual(satchel['x'],.2247)
        self.assertAlmostEqual(satchel['y'],.2423)
        for role in ('starts','ends'):
            self.assertTrue(all(p['entityType']=='object' for p in q[79976][role]))
        self.assertFalse(q[79976].get('objectives'))
        self.assertFalse(q[79976].get('requirements'))

    def test_followups_wait_for_actual_handin_not_acceptance_or_ready_flag(self):
        c=client()
        for parent,follow in ((79974,79975),(79975,79976)):
            c.ns.active[parent]=self.quests[parent]['title'];c.ns.readyToTurnIn[parent]=True
            self.assertFalse(c.ns.CataloguePrerequisitesAllowed(follow,c.ns.self)[0])
            c.lua.globals().finished[parent]=True
            self.assertTrue(c.ns.CataloguePrerequisitesAllowed(follow,c.ns.self))

    def test_object_work_uses_concise_interaction_without_fabricated_item_count(self):
        c=client();g=guide(c,(79974,79975,79976));g.fixedRoute=True
        c.ns.GenerateFixedGuide(g,False)
        step=next(s for s in g.fixedPlan.values()if s.id==79976 and s.kind=='q')
        self.assertEqual(c.ns.GuideStepAction(step),'Interact with Hastily Rolled-Up Satchel')
        self.assertIsNone(step.quantity)
        self.assertFalse(c.ns.Completed(79976))

    def test_faction_class_variants_retain_all_nine_actions_and_saved_key(self):
        for faction in ('Horde','Alliance'):
            for class_id in (1,8,9):
                c=client(faction,class_id=class_id,level=32);c.ns.guideLevel='all'
                c.ns.SetOption('classQuests',False)
                g=next(g for g in c.ns.LevelingGuideChoices().values()if g.zone=="Thoradin's Wall")
                self.assertEqual(g.key,"level-zone:eastern-kingdoms/thoradins-wall:levels:31-40")
                c.ns.BuildGuideRoute(g,False);before=order(g)
                self.assertEqual(len(list(g.fixedPlan.values())),9)
                self.assertEqual({int(s.id) for s in g.fixedPlan.values()},{79974,79975,79976})
                c.lua.globals().finished[79974]=True;c.ns.active[79975]="Eagle's Fist"
                c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
                self.assertTrue(c.ns.ClassQuestEnabled(79976))
        self.assertEqual(self.quests[79976]['minLevel'],14)
        self.assertEqual(self.quests[79976]['categoryPath'],'eastern-kingdoms/thoradins-wall')

    def test_corrections_are_atomic_and_reapplication_preserves_newer_facts(self):
        rows=copy.deepcopy(self.quests);self.assertEqual(apply_stage_corrections(rows),[])
        rows[79976]['starts'][0]['mapID']=1424;before=copy.deepcopy(rows)
        with self.assertRaises(ValueError):apply_stage_corrections(rows)
        self.assertEqual(rows,before)
