"""Dustwallow faction handoffs, supplied deliveries and placeholder scope."""
import copy,json,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
sys.path.insert(0,str(ROOT/'tools'));from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class DustwallowCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_faction_object_pickups_preserve_real_recipients(self):
  for a,h,obj,an,hn in [(1219,1238,20985,4947,4791),(1253,1251,20992,4944,4926),(1252,1269,21042,4944,4926),(1284,1268,21015,4944,4926)]:
   for i,faction,npc in [(a,'Alliance',an),(h,'Horde',hn)]:
    q=self.q[i];self.assertEqual(q['side'],faction);self.assertEqual(q['starts'][0]['entityID'],obj);self.assertEqual(q['starts'][0]['action'],'interact');self.assertEqual(q['ends'][0]['entityID'],npc)
    c=client(faction,level=35);g=guide(c,(i,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False);s=next(p for p in g.fixedPlan.values()if p.kind=='a');self.assertEqual(s.action,'interact');self.assertNotIn('Talk to',c.ns.StopInstruction(s))
  self.assertEqual(self.q[1239]['providedItems'][0]['entityID'],5918);self.assertEqual(self.q[1239]['starts'][0]['action'],'interact')
 def test_supplied_orb_and_amulet_do_not_create_duplicate_farms(self):
  for i,iid,recipient in [(4976,12642,6266),(6601,16888,10182)]:
   q=self.q[i];self.assertFalse(q.get('requirements'));self.assertFalse(q.get('objectives'));self.assertFalse(q.get('missingRequirements'));self.assertFalse(q.get('objectiveLocationsIncomplete'));self.assertEqual(q['providedItems'][0]['entityID'],iid);self.assertEqual(q['requiredItems'][0]['quantity'],1);self.assertEqual(q['ends'][0]['entityID'],recipient)
  self.assertEqual(self.q[4976]['ends'][0]['mapID'],1413);self.assertTrue(self.q[6601]['ends'][0]['patrol']);self.assertEqual(self.q[6601]['ends'][0]['mapID'],1442)
 def test_actual_handins_for_deliveries_and_faction_chains(self):
  for child,parent,faction in [(4976,4961,'Horde'),(6601,6585,'Horde'),(1239,1238,'Horde'),(1319,1253,'Alliance'),(1321,1251,'Horde')]:
   c=client(faction,level=60);c.ns.active[parent]='Parent';c.ns.readyToTurnIn[parent]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(child,c.ns.self)[0]);c.lua.globals().finished[parent]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(child,c.ns.self))
  self.assertEqual(self.q[6585]['prerequisiteAll'],[6582,6583,6584]);self.assertEqual(self.q[1133]['previousQuest'],1132)
 def test_placeholders_retained_but_excluded_unknown_report_not_guessed(self):
  for i in [1263,1272,1281,1283]:self.assertEqual(self.q[i]['levelingExcluded'],'Unfinished change-to-gossip placeholder');self.assertFalse(self.q[i].get('starts'));self.assertFalse(self.q[i].get('ends'))
  self.assertFalse(self.q[1288].get('levelingExcluded'));self.assertFalse(self.q[1288].get('starts'));self.assertFalse(self.q[1288].get('ends'));self.assertTrue(self.q[1203]['missingRequirements']);self.assertEqual(self.q[1203]['classMask'],0)
  for i in [1282,4962]:self.assertTrue(self.q[i]['prerequisitesUnverified'])
 def test_class_option_elites_and_accepted_deferred_work_preserved(self):
  c=client('Horde',level=40);c.ns.SetOption('classQuests',False);self.assertFalse(c.ns.ClassQuestEnabled(4976));self.assertFalse(c.ns.ClassQuestEnabled(1948));self.assertTrue(c.ns.ClassQuestEnabled(1203));self.assertIsNotNone(c.ns.QuestGroupWarning(6582))
  for faction,ids,active in [('Horde',[4976],4976),('Horde',[6601],None),('Alliance',[1253],None),('Alliance',[1288,1203],1203)]:
   c=client(faction,level=60);c.ns.partyNames=c.lua.table();g=guide(c,ids);g.fixedRoute=True;c.ns.routeSelection=g
   if active:c.ns.active[active]=self.q[active]['title']
   c.ns.GenerateFixedGuide(g,False);c.ns.questReady=True;c.ns.selectedRoute=c.ns.BuildFixedGuideRoute(g,False);c.ns.UpdateFixedGuideRoute(g);self.assertFalse(c.ns.selectedRoute.complete);self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished,len(ids))
 def test_guard_is_atomic_and_idempotent(self):
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[4976]['requiredItems'][0]['quantity']=2;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
