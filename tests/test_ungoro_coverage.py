"""Un'Goro factual stages, alternative farms and actual hand-in boundaries."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
from test_063 import order
sys.path.insert(0,str(ROOT/'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class UngoroCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']

    def test_container_contents_are_not_collected_from_a_flight_master(self):
        q=self.quests[3845]
        self.assertEqual({r['itemID']:r['quantity']for r in q['requiredItems']},{11104:1,11105:1,11106:1})
        self.assertEqual(q['providedItems'][0]['entityID'],11107)
        self.assertEqual(q['worldReferences']['provided'],q['providedItems'])
        self.assertFalse(q['objectives']);self.assertTrue(q['objectiveLocationsIncomplete'])
        self.assertEqual({r['entityID']for r in q['missingRequirements']},{11104,11105,11106})
        c=client(level=55);g=guide(c,(3844,3845,3908));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        self.assertFalse(any(s.entityID==10583 for s in g.fixedPlan.values()))
        self.assertTrue(any(s.id==3845 and s.kind=='q' and s.unknownLocation for s in g.fixedPlan.values()))

    def test_heart_alternatives_do_not_become_two_mandatory_farms(self):
        q=self.quests[4084]
        self.assertEqual({r['itemID']:r['quantity']for r in q['requiredItems']},{11172:11,11173:1})
        heart=[p for p in q['objectives']if p.get('itemID')==11173]
        self.assertEqual([(p['entityID'],p['mapID'],p['quantity'])for p in heart],[(7139,1448,1)])
        alternatives=next(a['locations']for a in q['objectiveAlternatives']if a['itemName']=='Irontree Heart')
        self.assertEqual({p['entityID']for p in alternatives},{7138,7139})
        self.assertTrue(all(p['objectiveKey']=='item:11173'for p in alternatives))
        c=client(level=55);g=guide(c,(4084,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        self.assertEqual(sum(s.kind=='q'and s.objectiveKey=='item:11173'for s in g.fixedPlan.values()),1)

    def test_lost_finds_ringo_and_does_not_farm_the_supplied_canteen(self):
        q=self.quests[4492]
        self.assertFalse(q['requirements']);self.assertFalse(q['requiredItems'])
        self.assertEqual(q['providedItems'][0]['entityID'],15722)
        self.assertEqual((q['objectives'][0]['entityID'],q['objectives'][0]['action']),(9999,'talk'))
        self.assertEqual((q['objectives'][0]['x'],q['objectives'][0]['y']),(.519,.4985))
        self.assertEqual(self.quests[4491]['prerequisiteAny'],[4492])
        c=client(level=55);c.ns.active[4492]='Lost!';c.ns.readyToTurnIn[4492]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(4491,c.ns.self)[0])
        c.lua.globals().finished[4492]=True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(4491,c.ns.self))
        escort=self.quests[4491]
        self.assertEqual(escort['providedItems'][0]['entityID'],11804)
        g=guide(c,(4492,4491));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        steps=list(g.fixedPlan.values())
        index=next(i for i,s in enumerate(steps)if s.id==4491 and s.kind=='q')
        self.assertEqual((steps[index-1].id,steps[index-1].kind),(4491,'a'))
        self.assertEqual(c.ns.GuideStepAction(steps[index]),'Escort Ringo')

    def test_toxic_test_uses_the_tool_without_inventing_a_count_or_class_gate(self):
        q=self.quests[9051];self.assertEqual(q['classMask'],1024)
        self.assertEqual(q['providedItems'][0]['entityID'],22432)
        self.assertTrue(q['requirements'][0]['quantityUnknown'])
        self.assertEqual(q['requirements'][0]['alternativeEntityIDs'],[6498,6499,6500])
        c=client(class_id=11,level=55);g=guide(c,(9052,9051));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        work=[s for s in g.fixedPlan.values()if s.id==9051 and s.kind=='q']
        self.assertTrue(work)
        self.assertTrue(all('Devilsaur Barb'in c.ns.GuideStepAction(s)for s in work))
        c.ns.SetOption('classQuests',False);self.assertFalse(c.ns.ClassQuestEnabled(9051))
        self.assertTrue(c.ns.ClassQuestEnabled(4084));self.assertTrue(c.ns.ClassQuestEnabled(4492))
        c=client(class_id=9,level=55)
        self.assertFalse(c.ns.CatalogueIdentityAllowed(9051,c.ns.profile)[0])

    def test_mid_zone_progress_preserves_both_complete_fixed_orders(self):
        for faction in ('Horde','Alliance'):
            c=client(faction,level=55);c.ns.guideLevel='all'
            choices=[g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Ungoro Crater']
            self.assertEqual(len(choices),1)
            g=choices[0];c.ns.BuildGuideRoute(g,False);before=order(g)
            self.assertEqual({r.id for r in g.records.values()},{s.id for s in g.fixedPlan.values()})
            c.lua.globals().finished[3844]=True;c.ns.active[4084]='Silver Heart'
            c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
            self.assertTrue(any(s.id==4084 and s.kind=='q'for s in g.fixedPlan.values()))

    def test_scoped_apostrophe_spelling_audits_both_chapters_without_hiding_gaps(self):
        global_path=ROOT/'WowTogether/GuideAudit.json';before=global_path.read_bytes()
        with tempfile.TemporaryDirectory()as folder:
            output=Path(folder)/'audit.json'
            run=subprocess.run([sys.executable,str(ROOT/'tools/audit_quest_guides.py'),'--zone',"Un'Goro Crater",'--output',str(output),'--require-complete'],cwd=ROOT,capture_output=True,text=True,timeout=120)
            self.assertEqual(run.returncode,2,run.stdout+run.stderr)
            report=json.loads(output.read_text())
        self.assertEqual(global_path.read_bytes(),before)
        self.assertEqual({(g['faction'],g['key'].split(':')[-1])for g in report['guides']},{('Horde','51-60'),('Alliance','51-60')})
        gaps=set().union(*(set(g['missing_location_quest_ids_by_stage']['q'])for g in report['guides']))
        self.assertIn(3845,gaps);self.assertIn(4146,gaps);self.assertIn(4321,gaps)
        self.assertNotIn(4084,gaps);self.assertNotIn(4492,gaps)

    def test_reviewed_alternatives_and_supplied_items_are_atomic_and_idempotent(self):
        q=copy.deepcopy(self.quests);self.assertEqual(apply_stage_corrections(q),[])
        q[4084]['objectiveAlternatives'][0]['locations'][0]['entityID']=9999
        before=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,before)
        q=copy.deepcopy(self.quests);q[3845]['worldReferences']['provided'][0]['entityID']=99999
        before=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,before)
