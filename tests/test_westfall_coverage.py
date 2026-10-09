"""Westfall object interactions, real use gaps and full saved chapter behavior."""
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


class WestfallCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']

    def test_treasure_chain_interacts_with_objects_without_changing_loot_start(self):
        c=client('Alliance',level=16);g=guide(c,(136,138,139,140));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        expected={136:(35,"Captain's Footlocker"),138:(36,'Broken Barrel'),139:(34,'Old Jug'),140:(33,'Locked Chest')}
        for s in g.fixedPlan.values():
            if s.kind=='q':
                self.assertEqual(s.action,'interact')
                self.assertEqual(c.ns.GuideStepAction(s),'Interact with '+expected[s.id][1])
                self.assertEqual(s.entityID,expected[s.id][0])
        start=self.quests[136]['starts'][0]
        self.assertEqual((start['action'],start['sourceAction'],start['itemID']),('start-item','loot',1357))
        c.ns.active[136]='Treasure';c.ns.readyToTurnIn[136]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(138,c.ns.self)[0])
        c.lua.globals().finished[136]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(138,c.ns.self))

    def test_alba_uses_an_actual_observation_not_an_average_or_patrol(self):
        for ident in [92742,92744,92745,92747,92748,92752]:
            for role in ['starts','ends']:
                for p in self.quests[ident][role]:
                    if p['entityID']==253092:
                        self.assertEqual((p['mapID'],p['x'],p['y']),(1436,.524,.529))
                        self.assertFalse(p.get('patrol'))
        # Two Alba actors are distinct; the Deadmines-exit actor is not moved to the hub.
        self.assertEqual(self.quests[92819]['starts'][0]['entityID'],253279)
        self.assertAlmostEqual(self.quests[92819]['starts'][0]['x'],.3869)
        self.assertEqual(self.quests[92747]['level'],15)

    def test_detonator_work_is_unknown_and_never_substituted_with_the_giver(self):
        q=self.quests[92819]
        self.assertTrue(q['objectiveLocationsIncomplete']);self.assertFalse(q['objectives'])
        self.assertFalse(q['requirements'])
        c=client('Alliance',level=18);g=guide(c,(92819,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        work=next(s for s in g.fixedPlan.values()if s.kind=='q')
        self.assertTrue(work.unknownLocation);self.assertIsNone(work.x);self.assertIsNone(work.y)
        self.assertIsNone(work.entityID);self.assertIsNone(work.quantity)
        self.assertNotIn('Speak to',c.ns.GuideStepAction(work))

    def test_dynamite_is_not_given_by_sprite_or_a_profession_only_quest(self):
        q=self.quests[92749]
        self.assertEqual([(r['itemID'],r['quantity'])for r in q['requiredItems']],[(4365,10)])
        self.assertTrue(q['objectiveLocationsIncomplete']);self.assertFalse(q['objectives'])
        self.assertFalse(q.get('providedItems'))
        c=client('Alliance',class_id=9,level=16);c.ns.SetOption('classQuests',False)
        self.assertFalse(c.ns.IsProfessionQuest(92749));self.assertTrue(c.ns.ClassQuestEnabled(92749))
        self.assertTrue(c.ns.CatalogueIdentityAllowed(92749,c.ns.profile))
        c=client('Horde',level=16);self.assertFalse(c.ns.CatalogueIdentityAllowed(92749,c.ns.profile)[0])

    def test_defias_escort_and_actual_handin_unlock_are_preserved(self):
        c=client('Alliance',level=18);g=guide(c,(65,132,135,141,142,155));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        steps=list(g.fixedPlan.values());index=next(i for i,s in enumerate(steps)if s.id==155 and s.kind=='q')
        self.assertEqual((steps[index-1].id,steps[index-1].kind),(155,'a'))
        self.assertEqual(steps[index].action,'escort')
        self.assertEqual(self.quests[155]['prerequisiteAny'],[142])
        self.assertEqual(self.quests[166]['prerequisiteAny'],[155])
        c.ns.active[155]='Defias';c.ns.readyToTurnIn[155]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(166,c.ns.self)[0])
        c.lua.globals().finished[155]=True;self.assertTrue(c.ns.CataloguePrerequisitesAllowed(166,c.ns.self))

    def test_all_chapters_keep_full_orders_during_mid_zone_progress(self):
        for faction,chapters in [('Alliance',{'1-10':26,'11-20':127}),('Horde',{'11-20':24})]:
            c=client(faction,level=16);c.ns.guideLevel='all'
            choices=[g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Westfall']
            self.assertEqual({g.key.split(':')[-1]for g in choices},set(chapters))
            for g in choices:
                c.ns.BuildGuideRoute(g,False);before=order(g)
                self.assertEqual(len(list(g.fixedPlan.values())),chapters[g.key.split(':')[-1]])
                self.assertEqual({r.id for r in g.records.values()},{s.id for s in g.fixedPlan.values()})
                c.lua.globals().finished[36]=True;c.ns.active[92749]='A Dynamite Plan'
                c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)

    def test_corrections_are_atomic_and_repeat_without_mutating_world_checks(self):
        q=copy.deepcopy(self.quests);self.assertEqual(apply_stage_corrections(q),[])
        q[136]['ends'][0]['entityID']=36;before=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,before)
        q=copy.deepcopy(self.quests);q[92742]['starts'][0]['y']=.25;before=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,before)

    def test_skyborn_handoff_keeps_its_actual_parent_and_full_race_scope(self):
        c=client('Alliance',level=16)
        self.assertFalse(c.ns.CatalogueIdentityAllowed(98021,c.ns.profile)[0])
        c.lua.execute("function UnitRace() return 'Skyborn','Skyborn',95 end")
        c.ns.ReadProfile();c.ns.UpdateRoster();c.ns.guideLevel='all'
        self.assertTrue(c.ns.CatalogueIdentityAllowed(98021,c.ns.profile))
        self.assertEqual(self.quests[98021]['prerequisiteAny'],[94947])
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(98021,c.ns.self)[0])
        g=next(g for g in c.ns.LevelingGuideChoices().values()
               if g.zone=='Westfall' and g.sectionLow==11)
        c.ns.BuildGuideRoute(g,False);before=order(g)
        self.assertEqual(len(list(g.fixedPlan.values())),224)
        self.assertIn(94947,{r.id for r in g.records.values()})
        self.assertIn(98021,{r.id for r in g.records.values()})
        c.ns.active[94947]='Welcome to Azeroth';c.ns.readyToTurnIn[94947]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(98021,c.ns.self)[0])
        c.lua.globals().finished[94947]=True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(98021,c.ns.self))
        c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
