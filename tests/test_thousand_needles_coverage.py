"""Thousand Needles real preparation, supplied deliveries and full route scope."""
import copy,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
sys.path.insert(0,str(ROOT/'tools'));from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class ThousandNeedlesCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_endurance_keeps_food_trigger_distinct_from_real_claw_drop(self):
  q=self.q[1150];self.assertEqual([v['itemID']for v in q['requiredItems']],[5843]);self.assertEqual([v['entityID']for v in q['requirements']],[5843]);self.assertFalse(q.get('missingRequirements'))
  a,b=q['objectives'];self.assertEqual((a['entityType'],a['entityID'],a['action']),('object',20447,'interact'));self.assertTrue(a['quantityUnknown']);self.assertNotIn('itemID',a);self.assertEqual((b['entityID'],b['itemID'],b['action'],b['quantity']),(4490,5843,'loot',1));self.assertAlmostEqual(b['x'],.26);self.assertAlmostEqual(b['y'],.556)
  self.assertEqual([p['entityID']for p in q['objectiveAlternatives'][0]['locations']],[4490])
 def test_supplied_report_blueprints_booster_never_duplicate_farming(self):
  for i,iid in [(5361,13507),(1183,5852),(1188,5862)]:
   q=self.q[i];self.assertFalse(q.get('requirements'));self.assertFalse(q.get('objectives'));self.assertFalse(q.get('missingRequirements'));self.assertEqual(q['providedItems'][0]['entityID'],iid);self.assertEqual(q['requiredItems'][0]['itemID'],iid)
  self.assertEqual(self.q[5361]['ends'][0]['mapID'],1443);self.assertEqual(self.q[1183]['prerequisiteAny'],[1182]);self.assertEqual(self.q[1188]['prerequisiteAny'],[1187]);self.assertTrue(self.q[1182]['objectives']);self.assertTrue(self.q[1187]['objectives'])
 def test_fire_and_cage_have_real_tools_and_separate_loot_points(self):
  for i,obj,iid,out in [(5088,175944,12785,12925),(5151,176195,12942,12946)]:
   q=self.q[i];a,b=q['objectives'];self.assertEqual((a['entityType'],a['entityID'],a['action'],a['useItemID']),('object',obj,'use',iid));self.assertTrue(a['quantityUnknown']);self.assertEqual(b['itemID'],out);self.assertEqual(b['quantity'],1);self.assertEqual(q['providedItems'][0]['entityID'],iid);self.assertNotEqual((a['x'],a['y']),(b['x'],b['y']))
  self.assertTrue(self.q[5151]['providedItems'][0]['quantityUnknown']);self.assertEqual(self.q[5088]['providedItems'][0]['quantity'],1)
 def test_original_action_text_does_not_invent_target_counts(self):
  c=client('Horde',level=30);g=guide(c,(1150,5088,5151));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  for s in g.fixedPlan.values():
   if s.kind=='q'and s.entityID==20447:self.assertTrue(c.ns.StopInstruction(s).startswith('Interact with Harpy Foodstuffs'))
   if s.kind=='q'and s.entityID in [175944,176195]:
    text=c.ns.StopInstruction(s);self.assertTrue(text.startswith('Use '));self.assertIn('Incendia Powder'if s.id==5088 else'Panther Cage Key',text);self.assertNotIn('100',text)
 def test_useful_intro_real_handins_class_setting_and_missing_beta_facts(self):
  self.assertEqual(self.q[4841]['previousQuest'],4542);self.assertEqual(self.q[4966]['previousQuest'],4881);self.assertTrue(self.q[4966]['requirements'][0]['quantityUnknown'])
  c=client('Horde',level=30);c.ns.active[4542]='Message';c.ns.readyToTurnIn[4542]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(4841,c.ns.self)[0]);c.lua.globals().finished[4542]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(4841,c.ns.self))
  c.ns.SetOption('classQuests',False);self.assertTrue(c.ns.ClassQuestEnabled(5361))
  for i in [98069,98156]:self.assertTrue(self.q[i]['objectiveLocationsIncomplete'])
  self.assertFalse(self.q[98156].get('starts'));self.assertEqual(self.q[98156]['previousQuest'],98155);self.assertEqual(self.q[1194]['starts'][0]['action'],'interact');self.assertTrue(self.q[1194]['providedItems'][0]['quantityUnknown'])
  for i in [1120,1121]:self.assertEqual(self.q[i]['prerequisiteAny'],[1119]);self.assertTrue(self.q[i]['prerequisitesUnverified'])
 def test_atomic_guard_remains_idempotent_and_rejects_changed_output(self):
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[1150]['requiredItems'][0]['quantity']=2;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
