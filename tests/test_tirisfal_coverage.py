"""Tirisfal class deliveries, actual head drop and interaction work."""
import copy,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
from test_063 import order
sys.path.insert(0,str(ROOT/'tools'));from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class TirisfalCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_scroll_keeps_class_race_parent_and_supplied_delivery(self):
  q=self.q[3095];self.assertFalse(q['requirements']);self.assertFalse(q['missingRequirements']);self.assertEqual(q['providedItems'][0]['entityID'],9546);self.assertEqual(q['requiredItems'][0]['itemID'],9546);self.assertEqual((q['classMask'],q['allowedRaceIDs'],q['prerequisiteAny']),(1,[5],[364]))
  c=client('Horde',class_id=1,level=10);c.ns.SetOption('classQuests',False);self.assertFalse(c.ns.ClassQuestEnabled(3095));self.assertTrue(c.ns.ClassQuestEnabled(6395))
 def test_paladin_head_has_actual_drop_spawn_and_keeps_other_counts(self):
  q=self.q[91317];self.assertFalse(q.get('objectiveLocationsIncomplete'));self.assertFalse(q['missingRequirements']);self.assertEqual((q['classMask'],q['allowedRaceIDs']),(2,[5]))
  p=q['objectives'][-1];self.assertEqual((p['entityID'],p['itemID'],p['quantity'],p['mapID'],p['action']),(259431,270435,1,1420,'loot'));self.assertAlmostEqual(p['x'],.114);self.assertAlmostEqual(p['y'],.6436)
  self.assertEqual([p['quantity']for p in q['objectives']],[8,6,1])
 def test_residue_starter_retains_first_loot_without_duplicate_farm(self):
  q=self.q[95328];self.assertEqual((q['starts'][0]['action'],q['starts'][0]['sourceAction'],q['starts'][0]['itemID']),('start-item','loot',268812));self.assertFalse(q['objectives']);self.assertFalse(q['requirements']);self.assertEqual(q['requiredItems'][0]['itemID'],268812);self.assertEqual(q['ends'][0]['mapID'],1458)
 def test_termite_supply_use_output_and_real_barrel_parent(self):
  q=self.q[5901];self.assertEqual(q['providedItems'][0]['entityID'],15042);self.assertTrue(q['providedItems'][0]['quantityUnknown']);self.assertEqual((q['objectives'][0]['action'],q['objectives'][0]['itemID'],q['objectives'][0]['quantity']),('gather',15043,100));self.assertEqual(q['objectives'][0]['mapID'],1423)
  c=client('Horde',level=55);g=guide(c,(5901,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False);work=next(s for s in g.fixedPlan.values()if s.kind=='q');text=c.ns.StopInstruction(work);self.assertTrue(text.startswith('Gather '));self.assertIn('100',text);self.assertIn('Plagueland Termites',text);self.assertNotIn('100 × Large Termite Mound',text)
  self.assertEqual(self.q[5902]['prerequisiteAny'],[5901]);self.assertEqual(self.q[5902]['ends'][0]['action'],'interact');self.assertEqual(self.q[5902]['providedItems'][0]['entityID'],15044)
  c=client('Horde',level=55);c.ns.active[5901]='Termites';c.ns.readyToTurnIn[5901]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(5902,c.ns.self)[0]);c.lua.globals().finished[5901]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(5902,c.ns.self))
 def test_grave_and_victims_interact_without_extra_burial_handin(self):
  q=self.q[6395];self.assertFalse(q['requiredItems']);self.assertEqual(q['requirements'][0]['entityID'],178090);self.assertEqual(q['objectives'][0]['action'],'interact');self.assertEqual(q['objectives'][1]['itemID'],16333)
  q=self.q[98389];self.assertEqual(q['objectives'][0]['action'],'interact');self.assertEqual(q['objectives'][0]['quantity'],6)
  c=client('Horde',level=5);g=guide(c,(6395,98389));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  for s in g.fixedPlan.values():
   if s.kind=='q'and s.entityID in [178090,271961]:self.assertTrue(c.ns.GuideStepAction(s).startswith('Interact with '))
 def test_unknown_mechanics_pickups_quantities_and_atomic_guard_remain(self):
  for i in [99144,96896,99134,99141]:self.assertTrue(self.q[i]['objectiveLocationsIncomplete'])
  self.assertEqual(self.q[99134]['providedItems'][0]['entityID'],286176)
  for i in [1470,1498,1818,1819,1881,1885]:self.assertTrue(self.q[i]['prerequisitesUnverified'])
  self.assertTrue(self.q[1819]['requirements'][0]['quantityUnknown']);self.assertTrue(self.q[96897]['requirements'][-1]['quantityUnknown'])
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[91317]['requiredItems'][0]['quantity']=2;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
