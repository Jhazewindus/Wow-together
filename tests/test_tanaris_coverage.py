"""Tanaris inputs, deliveries and evidenced ordinary/endgame scope boundaries."""
import copy
import json
import sys
import unittest
from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide
from test_063 import order
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class TanarisFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']

    def test_testing_inputs_are_not_999_item_turnin_goals(self):
        q = self.quests[654]
        expected = {9440:8,9441:8,9438:8,8523:1}
        self.assertEqual({r['itemID']:r['quantity'] for r in q['requiredItems']}, expected)
        self.assertEqual({r['entityID']:r['quantity'] for r in q['requirements']}, expected)
        raw = [p for p in q['objectives'] if p.get('itemID') in (9437,9439,9442)]
        self.assertEqual(len(raw), 3)
        self.assertTrue(all('quantity' not in p and p['quantityUnknown'] for p in raw))
        self.assertTrue(q['objectiveLocationsIncomplete'])
        self.assertEqual({r['entityID'] for r in q['missingRequirements']}, {9440,9441,9438})
        kit = next(p for p in q['objectives'] if p['itemID']==8523)
        self.assertEqual((kit['action'],kit['entityID'],kit['quantity']), ('buy',7683,1))

    def test_unknown_raw_input_inventory_does_not_finish_acceptable_sample_work(self):
        c=client();g=guide(c,(654,));g.fixedRoute=True;c.ns.GenerateFixedGuide(g,False)
        c.ns.active[654]='Tanaris Field Sampling'
        c.lua.execute('C_Item={GetItemCount=function() return 999 end}')
        raw=next(s for s in g.fixedPlan.values() if s.kind=='q' and s.itemID==9437)
        self.assertIsNone(c.ns.GuideItemProgress(raw,c.ns.self,None))
        self.assertFalse(c.ns.Completed(654))
        self.assertNotIn('999',c.ns.GuideStepAction(raw))

    def test_five_supplied_deliveries_keep_native_handins_and_faction_variants(self):
        for ident,item in ((4508,11844),(4509,11844),(7732,19020),(8922,21985),(8923,22382)):
            q=self.quests[ident]
            self.assertFalse(q.get('requirements'));self.assertFalse(q.get('objectiveLocationsIncomplete'))
            self.assertEqual([(r['itemID'],r['quantity'])for r in q['requiredItems']],[(item,1)])
            self.assertTrue(all(p['action']=='talk'for p in q['ends']))
            self.assertFalse(q.get('levelingExcluded'))
        self.assertEqual(self.quests[7732]['prerequisiteAll'],[7730,7731])
        self.assertEqual(self.quests[4508]['side'],'Alliance')
        self.assertEqual(self.quests[4509]['side'],'Horde')
        c=client();c.ns.active[7730]='Zukk\'ash Infestation';c.ns.readyToTurnIn[7730]=True
        c.lua.globals().finished[7731]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(7732,c.ns.self)[0])
        c.lua.globals().finished[7730]=True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(7732,c.ns.self))

    def test_raid_campaign_quarantine_keeps_catalogue_gaps_and_ordinary_elites(self):
        excluded=[r for r in self.quests.values()if r.get('levelingExcluded','').startswith('Level-60 Ahn')]
        self.assertEqual(len(excluded),43)
        for q in excluded:self.assertEqual((q['level'],q['minLevel']),(60,60))
        self.assertTrue(self.quests[8730]['objectiveLocationsIncomplete'])
        self.assertEqual(self.quests[8728]['prerequisiteAll'],[8578,8587,8620])
        self.assertEqual(self.quests[8742]['prerequisiteAll'],[8729,8730,8741])
        for ident in (654,648,1560,4507,8181,8182,8365,8366):
            self.assertFalse(self.quests[ident].get('levelingExcluded'))

    def test_rules_remain_atomic_and_idempotent(self):
        q=copy.deepcopy(self.quests);self.assertEqual(apply_stage_corrections(q),[])
        q[654]['objectives'][1]['quantity']=999;before=copy.deepcopy(q)
        with self.assertRaises(ValueError):apply_stage_corrections(q)
        self.assertEqual(q,before)

    def test_both_factions_keep_whole_chapters_and_saved_mid_zone_order(self):
        for faction in ('Horde','Alliance'):
            c=client(faction,level=45);c.ns.guideLevel='all'
            guides=[g for g in c.ns.LevelingGuideChoices().values()if g.zone=='Tanaris']
            self.assertEqual({g.key.split(':')[-1]for g in guides},{'41-50','51-60'})
            for g in guides:
                c.ns.BuildGuideRoute(g,False);before=order(g)
                self.assertFalse({int(r.id)for r in g.records.values()} & {8288,8730,8742,8761})
                c.ns.active[654]='Tanaris Field Sampling';c.lua.globals().finished[1690]=True
                c.ns.BuildGuideRoute(g,False);self.assertEqual(order(g),before)
