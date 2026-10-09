"""Teldrassil delivery, moonwell and unresolved escape facts."""
import copy,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
from test_063 import order
sys.path.insert(0,str(ROOT/'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class TeldrassilCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_seed_and_heart_delivery_keeps_handin_without_duplicate_farming(self):
  for i,item in [(922,5168),(927,5179)]:
   q=self.q[i];self.assertFalse(q['requirements']);self.assertFalse(q['objectives']);self.assertEqual(q['requiredItems'][0]['itemID'],item);self.assertEqual(q['providedItems'][0]['entityID'],item)
  self.assertEqual(self.q[927]['starts'][0]['sourceAction'],'loot');self.assertEqual(self.q[927]['starts'][0]['entityID'],3535)
 def test_necklace_container_is_not_handin_or_direct_jewel_drop(self):
  q=self.q[2459];self.assertEqual([i['itemID']for i in q['requiredItems']],[8050]);self.assertEqual([(r['entityID'],r['quantity'])for r in q['requirements']],[(7235,7),(8050,1)])
  self.assertEqual(q['objectives'][1]['itemID'],8049);self.assertEqual(q['missingRequirements'][0]['entityID'],8050);self.assertTrue(q['objectiveLocationsIncomplete'])
 def test_moonwell_uses_distinct_empty_phial_and_keeps_filled_output(self):
  c=client('Alliance',level=10);g=guide(c,(921,929,933,7383));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  for s in g.fixedPlan.values():
   if s.kind=='q':self.assertEqual(s.action,'use');self.assertTrue(c.ns.GuideStepAction(s).startswith('Use '))
  for i,empty,full in [(921,5185,5184),(929,5619,5639),(933,5621,5645),(7383,18152,18151)]:
   q=self.q[i];self.assertEqual(q['objectives'][0]['useItemID'],empty);self.assertEqual(q['objectives'][0]['itemID'],full);self.assertEqual(q['requiredItems'][0]['quantity'],1)
  self.assertFalse(self.q[934].get('starts'));self.assertFalse(self.q[934].get('ends'));self.assertEqual(self.q[934]['objectives'][0]['mapID'],1457)
 def test_planter_interaction_requires_actual_heart_handin(self):
  c=client('Alliance',level=12);g=guide(c,(941,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  s=next(s for s in g.fixedPlan.values()if s.kind=='q');self.assertEqual(s.action,'interact');self.assertTrue(c.ns.GuideStepAction(s).startswith('Interact with '))
  c.ns.active[927]='Heart';c.ns.readyToTurnIn[927]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(941,c.ns.self)[0]);c.lua.globals().finished[927]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(941,c.ns.self))
 def test_beta_delivery_inputs_and_escape_unknown_do_not_invent_chain(self):
  for i,item in [(98046,279291),(98065,279331),(99073,286069)]:
   self.assertEqual(self.q[i]['providedItems'][0]['entityID'],item);self.assertTrue(self.q[i]['providedItems'][0]['quantityUnknown']);self.assertFalse(self.q[i]['objectives'])
  self.assertTrue(self.q[99053]['objectiveLocationsIncomplete']);self.assertFalse(self.q[99053]['objectives']);self.assertFalse(self.q[99053].get('prerequisiteAny'))
  c=client('Alliance',level=10);c.ns.SetOption('classQuests',False);self.assertTrue(c.ns.ClassQuestEnabled(2561));self.assertEqual(self.q[2561]['classMask'],0)
 def test_fixed_orders_and_atomic_guard_preserve_progress(self):
  c=client('Alliance',level=10);c.ns.guideLevel='all'
  for g in c.ns.LevelingGuideChoices().values():
   if g.zone!='Teldrassil':continue
   c.ns.BuildGuideRoute(g,False);before=order(g);c.lua.globals().finished[922]=True;c.ns.active[2459]='Ferocitas';c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[921]['requiredItems'][0]['quantity']=2;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
