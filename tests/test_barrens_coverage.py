"""Barrens preparation inputs, actual object actions and retained hand-ins."""
import copy,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
sys.path.insert(0,str(ROOT/'tools'));from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class BarrensCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_consumed_inputs_are_not_additional_handins(self):
  for i,output,inputs in [(882,5101,{10338}),(3924,11149,{11147,11148})]:
   q=self.q[i];self.assertEqual([v['itemID']for v in q['requiredItems']],[output]);self.assertTrue(inputs.issubset({v.get('itemID')for v in q['objectives']}));self.assertTrue(q['objectiveLocationsIncomplete'])
  self.assertEqual([p['quantity']for p in self.q[3924]['objectives']],[1,5]);self.assertNotEqual(self.q[882]['objectives'][0]['x'],self.q[882]['objectives'][1]['x'])
 def test_console_key_and_valves_keep_actual_parent_handins(self):
  for i in [894,900,901]:self.assertEqual(self.q[i]['ends'][0]['action'],'interact')
  self.assertEqual({p['entityID']for p in self.q[900]['objectives']},{4072,61935,61936});self.assertTrue(all(p['action']=='interact'and p['quantity']==1 for p in self.q[900]['objectives']))
  self.assertEqual(self.q[901]['requiredItems'][0]['itemID'],5089)
  c=client('Horde',level=20);c.ns.active[894]='Samophlange';c.ns.readyToTurnIn[894]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(900,c.ns.self)[0]);c.lua.globals().finished[894]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(900,c.ns.self))
 def test_feathers_are_acquired_tool_and_each_nest_is_one_target(self):
  q=self.q[905];self.assertFalse(q.get('requiredItems'));self.assertFalse(q.get('providedItems'));self.assertEqual({p['entityID']for p in q['objectives']},{6906,6907,6908})
  self.assertTrue(all(p['action']=='use'and p['quantity']==1 and p['useItemID']==5165 for p in q['objectives']))
  c=client('Horde',level=20);g=guide(c,(905,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  work=[s for s in g.fixedPlan.values()if s.kind=='q'];self.assertEqual(len(work),3)
  for s in work:self.assertIn('Sunscale Feather',c.ns.StopInstruction(s));self.assertNotIn('Talk to',c.ns.StopInstruction(s))
 def test_vials_keep_unknown_count_and_unmapped_placements(self):
  q=self.q[98095];self.assertEqual(q['providedItems'][0]['entityID'],279395);self.assertTrue(q['providedItems'][0]['quantityUnknown']);self.assertTrue(q['objectiveLocationsIncomplete']);self.assertFalse(q['objectives']);self.assertEqual([r['quantity']for r in q['requirements']],[1,1,1]);self.assertEqual(q['ends'][0]['mapID'],1424)
  self.assertEqual(self.q[79192]['ends'][0]['action'],'interact')
 def test_atomic_guard_and_higher_chapter_bracers_scope(self):
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[882]['requiredItems'][0]['quantity']=2;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
  c=client('Horde',level=30)
  self.assertEqual(self.q[855]['minLevel'],9);self.assertFalse(self.q[855].get('prerequisiteAny'))
