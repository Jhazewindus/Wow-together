"""Hillsbrad head drops, preparation text and unfinished fixed scope."""
import copy,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
sys.path.insert(0,str(ROOT/'tools'));from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class HillsbradCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_elite_heads_use_actual_drop_actors_and_alterac_frame(self):
  q=self.q[519];self.assertFalse(q.get('missingRequirements'));self.assertFalse(q.get('objectiveLocationsIncomplete'));self.assertEqual(q['questType'],'Elite');self.assertEqual(q['previousQuest'],518)
  self.assertEqual([(p['entityID'],p['itemID'],p['quantity'],p['mapID'])for p in q['objectives']],[(2420,3550,1,1416),(2421,3551,1,1416),(2422,3552,1,1416)])
 def test_cloth_is_not_a_flight_master_drop(self):
  q=self.q[565];self.assertNotIn(2432,{p['entityID']for p in q['objectives']});self.assertNotIn(2432,{p['entityID']for p in q['npcTargets']});self.assertEqual({v['entityID']for v in q['missingRequirements']},{2997,3719});self.assertEqual([v['quantity']for v in q['requiredItems']],[1,1,1,10]);self.assertEqual(q['classMask'],0)
  for alt in q['objectiveAlternatives']:self.assertNotIn(2432,{p.get('entityID')for p in alt['locations']})
 def test_actual_interactions_and_three_single_flame_uses(self):
  self.assertEqual(self.q[524]['ends'][0]['action'],'interact');self.assertEqual(self.q[553]['ends'][0]['action'],'interact');self.assertEqual(next(p for p in self.q[532]['objectives']if p['entityID']==1761)['action'],'interact')
  q=self.q[553];self.assertEqual(q['providedItems'][0]['entityID'],3710);self.assertTrue(all(p['useItemID']==3710 and p['quantity']==1 for p in q['objectives']))
  c=client('Horde',level=33);g=guide(c,(553,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
  for p in g.fixedPlan.values():
   if p.kind=='q':self.assertIn('Rod of Helcular',c.ns.StopInstruction(p));self.assertNotIn('Talk to',c.ns.StopInstruction(p))
 def test_real_handed_in_parents_and_cross_zone_support_retained(self):
  for child,parent in [(528,527),(529,528),(532,529),(539,532),(541,539),(550,541),(513,509),(515,513),(517,515),(524,517),(98095,98094)]:self.assertEqual(self.q[child]['previousQuest'],parent)
  self.assertEqual(self.q[546]['prerequisiteAny'],[527]);c=client('Horde',level=25);c.ns.active[527]='Battle';c.ns.readyToTurnIn[527]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(546,c.ns.self)[0]);c.lua.globals().finished[527]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(546,c.ns.self))
  self.assertEqual(self.q[98094]['providedItems'][0]['entityID'],279394);self.assertEqual(self.q[98095]['providedItems'][0]['entityID'],279395)
 def test_unfinished_accepted_deferred_and_high_work_never_completes(self):
  for level,ids,active in [(25,[527],527),(25,[528],None),(21,[519],None),(25,[527,528,519,98094],527)]:
   c=client('Horde',level=level);c.ns.partyNames=c.lua.table();c.ns.questReady=True;g=guide(c,ids);g.fixedRoute=True;c.ns.routeSelection=g
   if active:c.ns.active[active]=self.q[active]['title']
   c.ns.GenerateFixedGuide(g,False);c.ns.questReady=True;c.ns.selectedRoute=c.ns.BuildFixedGuideRoute(g,False);c.ns.UpdateFixedGuideRoute(g);r=c.ns.selectedRoute
   self.assertFalse(r.complete);self.assertEqual(r.completionProgress.unfinished,len(ids));self.assertEqual(r.completionProgress.completed,0)
   if ids==[528]:self.assertEqual(r.deferredQuests,1)
   if ids==[527]:self.assertTrue(r.stops[1]or r.pendingReason)
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[519]['requiredItems'][0]['quantity']=2;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
