"""Wetlands object/use facts, counted travel work and full chapter scope."""
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


class WetlandsCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']

    def test_search_and_corpse_handoffs_interact_with_actual_objects(self):
        c=client('Alliance',level=32);g=guide(c,(281,284,285,631));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        expected={281:(261,'Damaged Crate'),284:(142151,'Sealed Barrel'),285:(259,'Half-buried Barrel'),631:(2652,"Ebenezer Rustlocke's Corpse")}
        for s in g.fixedPlan.values():
            if s.kind=='q':
                self.assertEqual((s.action,s.entityType,s.entityID),('interact','object',expected[s.id][0]))
                self.assertEqual(c.ns.GuideStepAction(s),'Interact with '+expected[s.id][1])
        self.assertEqual(self.quests[284]['previousQuest'],281)
        self.assertEqual(self.quests[285]['previousQuest'],284)
        self.assertEqual(self.quests[632]['prerequisiteAny'],[631])

    def test_catapult_uses_supplied_tinder_without_farming_or_false_count(self):
        c=client('Alliance',level=32);g=guide(c,(465,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        s=next(s for s in g.fixedPlan.values()if s.kind=='q')
        self.assertEqual((s.action,s.entityID),('use',1609))
        self.assertEqual(self.quests[465]['ends'][0]['useItemID'],3339)
        self.assertEqual(c.ns.GuideStepAction(s),'Use Dwarven Tinder on Dragonmaw Catapult')
        self.assertIsNone(s.quantity);self.assertFalse(self.quests[465]['requirements'])
        self.assertEqual(self.quests[465]['providedItems'][0]['entityID'],3339)
        self.assertEqual(self.quests[465]['prerequisiteAny'],[464])

    def test_algaz_keeps_both_kills_and_separate_actual_traversal(self):
        c=client('Alliance',level=23);g=guide(c,(455,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        work=[s for s in g.fixedPlan.values()if s.kind=='q']
        self.assertEqual(len(work),3)
        self.assertEqual({s.entityID:s.quantity for s in work if s.action=='kill'},{2102:6,2103:8})
        event=next(s for s in work if s.action=='event')
        self.assertEqual(event.objectiveKey,'event:455');self.assertIsNone(event.entityID);self.assertIsNone(event.quantity)
        self.assertEqual(event.mapID,1437);self.assertAlmostEqual(event.x,.5372);self.assertAlmostEqual(event.y,.7033)
        self.assertEqual(c.ns.GuideStepAction(event),'Complete Dun Algaz traversal')
        self.assertEqual(self.quests[455]['previousQuest'],468)

    def test_water_inputs_remain_distinct_from_unknown_outputs_and_areas(self):
        for ident,provided,output in [(94497,265732,265734),(94499,265747,265748),(94500,265772,265773)]:
            q=self.quests[ident]
            self.assertEqual(q['providedItems'][0]['entityID'],provided)
            self.assertTrue(q['providedItems'][0]['quantityUnknown'])
            self.assertEqual(q['requirements'][0]['entityID'],output)
            self.assertTrue(q['requirements'][0]['quantityUnknown'])
            self.assertFalse(q['objectives']);self.assertTrue(q['objectiveLocationsIncomplete'])
            self.assertEqual((q['classMask'],q['minLevel']),(64,20))
        q=self.quests[94501];self.assertEqual(q['providedItems'][0]['entityID'],7810)
        self.assertFalse(q['requirements']);self.assertFalse(q['objectives'])
        self.assertEqual(q['ends'][0]['mapID'],1432)

    def test_class_setting_filters_water_work_without_excluding_ordinary_quests(self):
        for race in [1,3,4,7,95]:
            c=client('Alliance',class_id=7,level=25);c.lua.execute('local r=...;function UnitRace() return "Test","Test",r end',race)
            c.ns.ReadProfile();c.ns.UpdateRoster();c.ns.guideLevel='all'
            g=next(g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Wetlands'and g.sectionLow==21)
            self.assertIn(94497,{r.id for r in g.records.values()});c.ns.SetOption('classQuests',False)
            self.assertFalse(c.ns.ClassQuestEnabled(94497));self.assertTrue(c.ns.ClassQuestEnabled(98246))
        c=client('Alliance',class_id=9,level=25);self.assertFalse(c.ns.CatalogueIdentityAllowed(94497,c.ns.profile)[0])
        c=client('Horde',class_id=7,level=25);c.ns.guideLevel='all'
        self.assertFalse(any(g.zone=='Wetlands'for g in c.ns.LevelingGuideChoices().values()))

    def test_full_chapters_preserve_fixed_orders_after_real_handin(self):
        c=client('Alliance',class_id=7,level=25);c.ns.guideLevel='all'
        choices=[g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Wetlands']
        self.assertEqual({g.sectionLow for g in choices},{11,21,31})
        for g in choices:
            c.ns.BuildGuideRoute(g,False);before=order(g)
            self.assertEqual(len(list(g.fixedPlan.values())),{11:6,21:180,31:77}[g.sectionLow])
            self.assertEqual({r.id for r in g.records.values()},{s.id for s in g.fixedPlan.values()})
            c.lua.globals().finished[455]=True;c.ns.active[98246]='Trying Times'
            c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
        c.ns.active[631]='Span';c.ns.readyToTurnIn[631]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(632,c.ns.self)[0])
        c.lua.globals().finished[631]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(632,c.ns.self))

    def test_unknown_elites_and_existing_actual_gates_are_preserved(self):
        for ident in [87318,87491,88756,88757,88758]:
            q=self.quests[ident];self.assertEqual(q['questType'],'Elite');self.assertFalse(q.get('starts'));self.assertFalse(q.get('ends'));self.assertFalse(q.get('objectives'))
        self.assertTrue(self.quests[484]['prerequisitesUnverified'])
        self.assertEqual(self.quests[484]['previousQuest'],469)
        self.assertEqual(self.quests[471]['prerequisiteAny'],[484])
        for ident in [98208,98246,98293]:self.assertTrue(self.quests[ident]['objectiveLocationsIncomplete'])

    def test_menethil_ship_paths_keep_explicit_boarding_and_arrival(self):
        c=client('Alliance',level=25)
        # Synthetic public map sizes/continents verify graph behavior, not native terrain.
        c.lua.execute('''
        function CreateVector2D(x,y) return {GetXY=function() return x,y end} end
        C_Map.GetMapWorldSize=function() return 5000,5000 end
        C_Map.GetWorldPosFromMapPos=function(map,p)
          local x,y=p:GetXY();return map==1437 and 1 or 0,CreateVector2D(x*5000,y*5000)
        end
        ''')
        for source,target in [('DOCK_MENETHIL_THERAMORE','DOCK_THERAMORE'),('DOCK_MENETHIL','DOCK_AUBERDINE_MENETHIL')]:
            nodes=c.ns.travelData.nodes
            edges=[e for e in c.ns.travelData.edges.values()if e['from']==source and e.to==target]
            self.assertEqual(len(edges),1);self.assertEqual((edges[0].method,edges[0].faction),('ship','Alliance'))
            path=c.ns.FindTravelPath(nodes[source],nodes[target],False);self.assertIsNotNone(path)
            legs=list(path.legs.values());self.assertTrue(any(s.method=='ship'for s in legs))
            self.assertEqual(path.goal.mapID,nodes[target].mapID)
            self.assertFalse(any(e.method=='walk'for e in edges))

    def test_corrections_are_idempotent_and_fail_atomically_on_conflicts(self):
        q=copy.deepcopy(self.quests);self.assertEqual(apply_stage_corrections(q),[])
        for ident,field in [(455,'objectives'),(94500,'providedItems'),(281,'ends')]:
            q=copy.deepcopy(self.quests);q[ident][field][0]['entityID']=999999;before=copy.deepcopy(q)
            with self.assertRaises(ValueError):apply_stage_corrections(q)
            self.assertEqual(q,before)
