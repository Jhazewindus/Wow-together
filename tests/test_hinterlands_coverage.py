"""Cross-zone item joins and faction/escort boundaries in The Hinterlands."""
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


class HinterlandsCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']

    def test_rhapsody_retains_every_item_goal_and_maps_only_proven_sources(self):
        q=self.quests[1452]
        self.assertEqual({r['itemID']:r['quantity']for r in q['requiredItems']},{6257:3,6258:3,6259:3})
        self.assertEqual([(p['itemID'],p['entityID'],p['mapID'],p['quantity'],p['action'])for p in q['objectives']],
                         [(6257,5428,1446,3,'loot'),(6258,5268,1444,3,'loot'),(6259,5260,1444,3,'loot')])
        self.assertFalse(q['objectiveLocationsIncomplete']);self.assertFalse(q['missingRequirements'])
        self.assertEqual(q['previousQuest'],1451)
        self.assertEqual(q['minLevel'],38)
        # These actual published positions are not inferred centroids or a patrol.
        self.assertEqual([(p['x'],p['y'])for p in q['objectives'][1:]],[(.6128,.616),(.612,.6139)])
        self.assertTrue(all(not p.get('patrol')for p in q['objectives']))

    def test_parcel_delivery_keeps_actual_item_and_parent_handin(self):
        q=self.quests[2938]
        self.assertFalse(q['requirements']);self.assertFalse(q.get('objectiveLocationsIncomplete'))
        self.assertEqual([(r['itemID'],r['quantity'])for r in q['requiredItems']],[(9436,1)])
        self.assertEqual((q['ends'][0]['entityID'],q['ends'][0]['mapID'],q['ends'][0]['action']),(2055,1458,'talk'))
        c=client();c.ns.active[2937]='Summoning Shadra';c.ns.readyToTurnIn[2937]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(2938,c.ns.self)[0])
        c.lua.globals().finished[2937]=True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(2938,c.ns.self))

    def test_both_factions_preserve_complete_saved_routes_and_escort_adjacency(self):
        for faction in ('Horde','Alliance'):
            c=client(faction,level=45);c.ns.guideLevel='all'
            guides=[g for g in c.ns.LevelingGuideChoices().values()if g.zone=='The Hinterlands']
            self.assertEqual({g.key.split(':')[-1]for g in guides},{'41-50','51-60'})
            for g in guides:
                c.ns.BuildGuideRoute(g,False);before=order(g)
                self.assertTrue({r.id for r in g.records.values()} <= {s.id for s in g.fixedPlan.values()})
                c.lua.globals().finished[485]=True;c.ns.active[836]='Rescue OOX-09/HL!'
                c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
        c=client();g=guide(c,(485,836,2742));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        steps=list(g.fixedPlan.values())
        for ident in (836,2742):
            idx=next(i for i,s in enumerate(steps)if s.id==ident and s.kind=='q')
            self.assertEqual((steps[idx-1].id,steps[idx-1].kind),(ident,'a'))

    def test_faction_boundaries_and_ordinary_work_ignore_class_optout(self):
        c=client();c.ns.SetOption('classQuests',False)
        self.assertTrue(c.ns.ClassQuestEnabled(7846));self.assertTrue(c.ns.ClassQuestEnabled(1452))
        self.assertFalse(c.ns.CatalogueIdentityAllowed(1452,c.ns.profile)[0])
        self.assertTrue(c.ns.CatalogueIdentityAllowed(7846,c.ns.profile))
        c=client('Alliance')
        self.assertTrue(c.ns.CatalogueIdentityAllowed(1452,c.ns.profile))
        self.assertFalse(c.ns.CatalogueIdentityAllowed(7846,c.ns.profile)[0])
        self.assertEqual(self.quests[7846]['prerequisiteAny'],[7845])
        self.assertEqual(self.quests[7847]['prerequisiteAny'],[7846])

    def test_input_conflicts_are_atomic_and_reapplication_is_idempotent(self):
        q=copy.deepcopy(self.quests);self.assertEqual(apply_stage_corrections(q),[])
        q[1452]['objectives'][1]['entityID']=5262;before=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,before)
