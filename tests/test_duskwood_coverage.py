"""Duskwood grave objects, cross-zone drops and unfinished complete scope."""
import copy,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
sys.path.insert(0,str(ROOT/'tools'));from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class DuskwoodCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_cross_zone_drop_relations_counts_search_and_elite_warning(self):
  q=self.q[1383];self.assertFalse(q.get('missingRequirements'));self.assertFalse(q.get('objectiveLocationsIncomplete'))
  self.assertEqual([(p['entityID'],p['itemID'],p['quantity'],p['mapID'])for p in q['objectives']],[(768,6080,5,1435),(1081,6081,1,1435),(4687,6082,1,1443)])
  self.assertTrue(q['objectives'][2]['patrol']);self.assertEqual([v['quantity']for v in q['requiredItems']],[5,1,1]);self.assertAlmostEqual(q['objectives'][0]['x'],.67)
  c=client();g=guide(c,(1383,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  work=[p for p in g.fixedPlan.values()if p.kind=='q'];self.assertEqual(len(work),3)
  for p in work:self.assertIn(p.itemName,c.ns.StopInstruction(p));self.assertNotIn('Talk to',c.ns.StopInstruction(p))
  self.assertIsNotNone(c.ns.QuestGroupWarning(1383))
 def test_grave_interaction_not_npc_or_extra_ring_farm(self):
  c=client('Alliance',level=35);g=guide(c,(225,231));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  points=[p for p in g.fixedPlan.values()if p.entityID==61];self.assertEqual(len(points),3)  # compiler retains recipient work plus real return
  for p in points:
   self.assertEqual(p.action,'interact');self.assertNotIn('Talk to',c.ns.StopInstruction(p))
   if p.kind!='t':self.assertIn('A Weathered Grave',c.ns.StopInstruction(p))
  self.assertEqual(self.q[231]['providedItems'][0]['entityID'],2162);self.assertFalse(self.q[231].get('requirements'));self.assertEqual(self.q[231]['previousQuest'],229)
 def test_real_handins_and_supplied_long_chain_deliveries(self):
  for faction,child,parent in [('Horde',1383,1372),('Alliance',231,229),('Alliance',322,324)]:
   c=client(faction,level=42);c.ns.active[parent]='Parent';c.ns.readyToTurnIn[parent]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(child,c.ns.self)[0]);c.lua.globals().finished[parent]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(child,c.ns.self))
  for i,iid in [(1388,6086),(1391,6089),(149,1453),(322,2712)]:self.assertEqual(self.q[i]['providedItems'][0]['entityID'],iid);self.assertFalse(self.q[i].get('requirements'))
 def test_class_setting_profession_exclusion_and_unknown_missions(self):
  c=client('Alliance',class_id=7,level=35);c.ns.SetOption('classQuests',False)
  self.assertFalse(c.ns.ClassQuestEnabled(79362));self.assertFalse(c.ns.ClassQuestEnabled(79363));self.assertTrue(c.ns.ClassQuestEnabled(225));self.assertEqual(self.q[79362]['classMask'],64)
  self.assertEqual(self.q[90]['levelingExcluded'],'Cooking-only quest (skill 50)');self.assertTrue(self.q[90]['objectives']);self.assertTrue(self.q[90]['prerequisitesUnverified'])
  for i in range(81733,81741):self.assertTrue(self.q[i]['objectiveLocationsIncomplete']);self.assertTrue(self.q[i]['missingRequirements']);self.assertEqual(self.q[i]['questType'],'Elite')
  self.assertFalse(self.q[98447].get('starts'));self.assertFalse(self.q[98447].get('ends'));self.assertTrue(self.q[322]['prerequisitesUnverified'])
 def test_accepted_and_deferred_work_never_false_completes_atomic_guards(self):
  for faction,level,ids,active in [('Horde',42,[1383],1383),('Horde',42,[1383],None),('Alliance',35,[231],None),('Alliance',27,[81733,98447],81733)]:
   c=client(faction,level=level);c.ns.partyNames=c.lua.table();g=guide(c,ids);g.fixedRoute=True;c.ns.routeSelection=g
   if active:c.ns.active[active]=self.q[active]['title']
   c.ns.GenerateFixedGuide(g,False);c.ns.questReady=True;c.ns.selectedRoute=c.ns.BuildFixedGuideRoute(g,False);c.ns.UpdateFixedGuideRoute(g)
   self.assertFalse(c.ns.selectedRoute.complete);self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished,len(ids))
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[1383]['requiredItems'][1]['quantity']=2;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
