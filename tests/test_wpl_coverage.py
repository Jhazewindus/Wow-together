"""Western Plaguelands supplies, component work and cauldron hand-in gates."""
import copy
import json
import sys
import unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
from test_063 import order
sys.path.insert(0,str(ROOT/'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class WplCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests=own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests']

    def test_cauldron_returns_deliver_supplied_bottles_and_keep_faction_destinations(self):
        for ident,parent,item,receiver,side in [(5223,5222,13192,11053,'Alliance'),(5232,5231,13191,11055,'Horde'),(5234,5233,13192,11055,'Horde'),(5236,5235,13193,11055,'Horde')]:
            q=self.quests[ident]
            self.assertFalse(q['requirements']);self.assertFalse(q.get('objectiveLocationsIncomplete'))
            self.assertEqual(q['side'],side)
            self.assertEqual([(r['itemID'],r['quantity'])for r in q['requiredItems']],[(item,1)])
            self.assertEqual(q['providedItems'][0]['entityID'],item)
            self.assertEqual((q['ends'][0]['entityID'],q['ends'][0]['action']),(receiver,'talk'))
            self.assertEqual(q['previousQuest']if q.get('previousQuest')else q['prerequisiteAny'][0],parent)
            c=client(side,level=55);c.ns.active[parent]='Cauldron target';c.ns.readyToTurnIn[parent]=True
            self.assertFalse(c.ns.CataloguePrerequisitesAllowed(ident,c.ns.self)[0])
            c.lua.globals().finished[parent]=True
            self.assertTrue(c.ns.CataloguePrerequisitesAllowed(ident,c.ns.self))

    def test_cauldron_key_farming_survives_delivery_corrections(self):
        expected={5216:13194,5229:13194,5219:13195,5231:13195,5222:13197,5233:13197,5225:13196,5235:13196}
        for ident,item in expected.items():
            q=self.quests[ident]
            self.assertEqual(q['requiredItems'][0]['itemID'],item)
            self.assertEqual(q['objectives'][0]['itemID'],item)
            self.assertTrue(q['requirements'])
            self.assertEqual(q['objectives'][0]['mapID'],1422)

    def test_two_halves_hands_in_only_assembled_charm_but_keeps_other_half_work(self):
        q=self.quests[5051]
        self.assertEqual([(r['itemID'],r['quantity'])for r in q['requiredItems']],[(12723,1)])
        self.assertEqual(q['providedItems'][0]['entityID'],12721)
        self.assertEqual(q['worldReferences']['provided'],q['providedItems'])
        self.assertEqual(q['objectives'][0]['itemID'],12722)
        self.assertEqual({r['entityID']for r in q['requirements']},{12723,12722})
        self.assertTrue(q['objectiveLocationsIncomplete'])
        self.assertEqual(q['previousQuest'],5050)

    def test_pamela_handin_does_not_require_consumed_assembly_components(self):
        q=self.quests[5149]
        self.assertEqual([(r['itemID'],r['quantity'])for r in q['requiredItems']],[(12885,1)])
        self.assertEqual({p['itemID']for p in q['objectives']},{12886,12887,12888})
        self.assertTrue(all(p['mapID']==1423 for p in q['objectives']))
        self.assertTrue(q['objectiveLocationsIncomplete']);self.assertTrue(q['prerequisitesUnverified'])

    def test_menethil_delivery_does_not_invent_a_scholomance_pickup(self):
        q=self.quests[5464]
        self.assertFalse(q.get('starts'));self.assertEqual(q['startRefs'][0]['entityID'],176631)
        self.assertEqual(q['objectives'][0]['entityID'],11036)
        self.assertEqual((q['objectives'][0]['mapID'],q['objectives'][0]['action']),(1423,'talk'))
        self.assertFalse(q['objectiveLocationsIncomplete'])
        self.assertEqual(q['previousQuest'],5463)
        self.assertEqual(self.quests[5465]['prerequisiteAny'],[5464])

    def test_distinct_branch_deliveries_keep_identity_and_class_option(self):
        self.assertEqual(self.quests[4986]['side'],'Alliance');self.assertEqual(self.quests[4987]['side'],'Horde')
        self.assertEqual(self.quests[4986]['ends'][0]['entityID'],4217)
        self.assertEqual(self.quests[4987]['ends'][0]['entityID'],5770)
        self.assertEqual(self.quests[8416]['classMask'],2)
        c=client('Alliance',class_id=2,level=55);g=guide(c,(8414,8416));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        q=next(s for s in g.fixedPlan.values()if s.id==8416 and s.kind=='q')
        self.assertIn('Ashlam',c.ns.GuideStepAction(q))
        c.ns.SetOption('classQuests',False);self.assertFalse(c.ns.ClassQuestEnabled(8416));self.assertTrue(c.ns.ClassQuestEnabled(4986))
        c=client('Horde',class_id=9,level=55)
        self.assertFalse(c.ns.CatalogueIdentityAllowed(8416,c.ns.profile)[0])

    def test_full_fixed_guide_and_mid_zone_progress_preserve_required_actions(self):
        for faction,class_id,count in [('Horde',9,197),('Alliance',9,204),('Alliance',2,210)]:
            c=client(faction,class_id=class_id,level=55);c.ns.guideLevel='all'
            choices=[g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Western Plaguelands']
            self.assertEqual(len(choices),1);g=choices[0];c.ns.BuildGuideRoute(g,False)
            self.assertEqual(len(list(g.fixedPlan.values())),count)
            before=order(g);self.assertEqual({r.id for r in g.records.values()},{s.id for s in g.fixedPlan.values()})
            c.lua.globals().finished[5215 if faction=='Alliance'else 5228]=True
            c.ns.active[5051]='Two Halves Become One';c.ns.BuildGuideRoute(g,False)
            self.assertEqual(order(g),before)
            self.assertTrue(any(s.id==5051 and s.kind=='q'for s in g.fixedPlan.values()))

    def test_unresolved_work_and_gate_conflicts_are_not_erased(self):
        for ident in [5862,6389,6390,5166,5167]:
            self.assertTrue(self.quests[ident]['missingRequirements'])
        self.assertEqual(self.quests[5092]['prerequisiteAny'],[5066,5090,5091])
        self.assertEqual(self.quests[5096]['prerequisiteAny'],[5093,5094,5095])
        self.assertTrue(self.quests[5342]['requirements'][0]['quantityUnknown'])
        self.assertTrue(self.quests[5504]['prerequisitesUnverified'])

    def test_corrections_are_idempotent_and_conflicts_leave_all_records_untouched(self):
        q=copy.deepcopy(self.quests);self.assertEqual(apply_stage_corrections(q),[])
        q[5149]['objectives'][0]['itemID']=12885;before=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,before)
