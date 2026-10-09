"""Zephras exact racial uses, unknown island work and preserved gates."""
import copy,sys,unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
from test_063 import order
sys.path.insert(0,str(ROOT/'tools'));from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections
class ZephrasCoverageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.q=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']
 def test_racial_use_names_are_abilities_without_invented_item_spell_or_count(self):
  for i,race,ability,obj in [(92597,95,'Read Ley Line',450002),(92598,96,'Skysight',450001)]:
   q=self.q[i];self.assertEqual(q['allowedRaceIDs'],[race]);self.assertEqual(q['classMask'],0);self.assertFalse(q.get('providedItems'));self.assertFalse(q.get('requiredItems'));p=q['objectives'][0]
   self.assertEqual((p['action'],p['sourceAction'],p['useItemName'],p['entityID'],p['mapID']),('use','use-at',ability,obj,2521));self.assertTrue(p['quantityUnknown']);self.assertIsNone(p.get('useItemID'));self.assertIsNone(p.get('spellID'))
   c=client('Alliance'if race==95 else'Horde',level=4);c.lua.execute('local r=...;function UnitRace() return "Test","Test",r end',race);c.ns.ReadProfile();c.ns.UpdateRoster();profile=c.lua.table_from({'faction':'Alliance'if race==95 else'Horde','classID':1,'raceID':race});self.assertTrue(c.ns.CatalogueIdentityAllowed(i,profile));profile.raceID=1 if race==95 else 2;self.assertFalse(c.ns.CatalogueIdentityAllowed(i,profile)[0]);g=guide(c,(i,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False);s=next(s for s in g.fixedPlan.values()if s.kind=='q');self.assertEqual(c.ns.GuideStepAction(s),'Use '+ability+' at '+p['name'])
 def test_missing_two_quest_records_keep_all_stages_unknown(self):
  for i in [94901,94902]:
   q=self.q[i];self.assertFalse(q.get('starts'));self.assertFalse(q.get('objectives'));self.assertFalse(q.get('ends'));self.assertFalse(q['startRefs']);self.assertFalse(q['endRefs'])
   c=client('Alliance',level=12);g=guide(c,(i,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False);self.assertEqual({s.kind for s in g.fixedPlan.values()},{'a','q','t'});self.assertTrue(all(s.unknownLocation for s in g.fixedPlan.values()))
 def test_handoffs_require_real_and_or_parent_handins(self):
  self.assertEqual(self.q[92579]['prerequisiteAll'],[92550,93927]);self.assertEqual(self.q[92685]['prerequisiteAll'],[92682,92683,92684]);self.assertEqual(self.q[92467]['prerequisiteAny'],[1516,1519,92466])
  c=client('Horde',level=10);c.ns.active[92550]='Havoc';c.ns.readyToTurnIn[92550]=True;c.lua.globals().finished[93927]=True;self.assertFalse(c.ns.CataloguePrerequisitesAllowed(92579,c.ns.self)[0]);c.lua.globals().finished[92550]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(92579,c.ns.self))
 def test_repeatables_placeholders_class_options_and_unknown_offers_stay(self):
  c=client('Horde',level=12);c.ns.guideLevel='all'
  for g in c.ns.LevelingGuideChoices().values():
   if g.zone=='Zephras Isle':self.assertFalse({93459,92454,92480,93173,94559}&{r.id for r in g.records.values()})
  for i in [92464,92466,92595,92596,94484,94493]:self.assertTrue(self.q[i]['prerequisitesUnverified'])
  self.assertEqual(self.q[92466]['classMask'],64);c.ns.SetOption('classQuests',False);self.assertFalse(c.ns.ClassQuestEnabled(92466));self.assertTrue(c.ns.ClassQuestEnabled(92598))
 def test_fixed_progress_and_atomic_reapplication(self):
  c=client('Alliance',level=10);c.ns.guideLevel='all'
  for g in c.ns.LevelingGuideChoices().values():
   if g.zone!='Zephras Isle':continue
   c.ns.BuildGuideRoute(g,False);old=order(g);c.lua.globals().finished[92460]=True;c.ns.active[92550]='Havoc';c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),old)
  q=copy.deepcopy(self.q);self.assertEqual(apply_stage_corrections(q),[]);q[92597]['objectives'][0]['mapID']=1438;old=copy.deepcopy(q)
  with self.assertRaises(ValueError):apply_stage_corrections(q)
  self.assertEqual(q,old)
