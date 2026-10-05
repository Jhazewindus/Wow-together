"""Cross-zone data, map transforms and dependency-preserving route regressions.

Native APIs below are synthetic; they do not certify Forever map geometry.
"""
import json
import unittest

from test_importers import detail
from quest_enrichment import enrich, entity_facts, quest_relations, representative_coords
from legacy_quest_facts import calibrate, matches, sql_rows
from test_063 import guide_client, zone
from test_061 import world_quest
from test_routes import catalogue
from test_addon import Client


class SourceFactsTests(unittest.TestCase):
    def test_named_item_source_wins_over_a_slightly_closer_unrelated_alternate(self):
        refs={'starts':[],'ends':[],'requirements':[{'entityType':'item','entityID':10,'name':'Forest Spider Venom','quantity':8}]}
        primary={'mapID':501,'x':.3,'y':.4,'entityID':7,'npc':True,'name':'Deathweb','itemName':'Forest Spider Venom','sourceObjective':0}
        normal={'mapID':501,'x':.3,'y':.39,'entityID':8,'npc':True,'name':'Forest Spider','itemName':'Forest Spider Venom','sourceObjective':0}
        q={'mapID':501,'starts':[{'mapID':501,'x':.3,'y':.4}],'objectives':[dict(primary)],
            'objectiveAlternatives':[{'sourceObjective':0,'itemName':'Forest Spider Venom','locations':[primary,normal]}]}
        enrich(q,refs,{'npc':{},'object':{},'item':{}})
        self.assertEqual(q['objectives'][0]['entityID'],8)
        self.assertEqual(q['objectives'][0]['legacyStepKey'],'q:501:npc:7')
        q['objectiveAlternatives'][0]['itemName']='Another item'
        q['objectives']=[dict(primary)];enrich(q,refs,{'npc':{},'object':{},'item':{}})
        self.assertEqual(q['objectives'][0]['entityID'],7) # Unproven item/source joins cannot change the destination.
    def test_provided_items_are_not_farming_objectives_and_explicit_use_is_retained(self):
        table = '''<table class="icon-list">
        <tr data-icon-list-quantity="5"><td><a href="/forever/npc=7">Workers Awoken</a></td></tr>
        <tr data-icon-list-quantity="1"><td><a href="/forever/item=8">Wake-up Tool</a> (Provided)</td></tr></table>'''
        page = '<meta name="description" content="Use the Wake-up Tool on Sleeping Workers when they are sleeping.">' + table
        page += detail([{'type':1,'id':7,'name':'Sleeping Worker','coord':[30,40]}])
        refs=quest_relations(page)
        self.assertEqual(len(refs['requirements']),1)
        self.assertEqual(refs['requirements'][0]['action'],'use')
        self.assertEqual(refs['requirements'][0]['useItemName'],'Wake-up Tool')
        self.assertEqual(refs['provided'][0]['entityID'],8)
        unrelated=quest_relations(page.replace('Use the Wake-up Tool on Sleeping Workers','Return the Wake-up Tool'))
        self.assertNotIn('action',unrelated['requirements'][0])

    def test_item_source_join_maps_real_drops_and_bundles_two_items_at_one_spawn(self):
        refs={'starts':[],'ends':[],'requirements':[
            {'entityType':'item','entityID':10,'name':'Flank','quantity':8},
            {'entityType':'item','entityID':11,'name':'Snout','quantity':8}]}
        source={'entityType':'npc','entityID':7,'name':'Boar','action':'loot'}
        entities={'npc':{7:{'name':'Boar','locations':[{'mapID':501,'x':.4,'y':.5}]}},'object':{},
            'item':{id:{'sources':[source]} for id in (10,11)}}
        quest={'mapID':501,'prerequisitesRead':True,'objectiveLocationsIncomplete':True}
        enrich(quest,refs,entities)
        self.assertFalse(quest.get('objectiveLocationsIncomplete'))
        self.assertEqual({p['itemID'] for p in quest['objectives']},{10,11})
        self.assertEqual({(p['x'],p['y']) for p in quest['objectives']},{(.4,.5)})
        self.assertEqual({p['quantity'] for p in quest['objectives']},{8})

    def test_unmapped_item_stays_named_and_incomplete(self):
        refs={'starts':[],'ends':[],'requirements':[{'entityType':'item','entityID':10,'name':'Missing drop','quantity':8}]}
        q={'mapID':501};enrich(q,refs,{'npc':{},'object':{},'item':{}})
        self.assertTrue(q['objectiveLocationsIncomplete'])
        self.assertEqual(q['missingRequirements'][0]['name'],'Missing drop')
        self.assertEqual(q['objectives'],[])

    def test_low_level_item_goal_uses_an_appropriate_drop_not_a_nearby_high_level_mob(self):
        refs={'starts':[],'ends':[],'requirements':[{'entityType':'item','entityID':10,'name':'Supplies','quantity':8}]}
        entities={'npc':{7:{'locations':[{'mapID':501,'x':.3,'y':.4}]},8:{'locations':[{'mapID':501,'x':.8,'y':.7}]}},
            'object':{},'item':{10:{'sources':[
                {'entityType':'npc','entityID':7,'name':'Boss','action':'loot','minlevel':60},
                {'entityType':'npc','entityID':8,'name':'Bandit','action':'loot','minlevel':12}]}}}
        q={'mapID':501,'level':12,'starts':[{'mapID':501,'x':.3,'y':.4}]};enrich(q,refs,entities)
        self.assertEqual(q['objectives'][0]['entityID'],8)
        entities['item'][10]['sources'][0]['action']='buy'
        q={'mapID':501,'level':12,'starts':[{'mapID':501,'x':.3,'y':.4}]};enrich(q,refs,entities)
        self.assertEqual(q['objectives'][0]['entityID'],7) # A high-level friendly vendor is usable.

    def test_entity_page_identity_and_actual_spawn_medoid_are_required(self):
        page='<link rel="canonical" href="https://www.wowhead.com/forever/npc=7/boar"><h1>Boar</h1>'
        page+='var g_mapperData = '+json.dumps({'14':[{'uiMapId':1411,'coords':[[40,40],[40,42],[43,40]]}]})+';'
        facts=entity_facts(page,'npc',7)
        self.assertTrue(all((p['x']*100,p['y']*100) in [(40,40),(40,42),(43,40)] for p in facts['locations']))
        with self.assertRaises(ValueError):entity_facts(page,'npc',8)
        self.assertEqual(representative_coords([[40,40],[40,42],[43,40]]),[[40,40]])

    def test_sql_is_lexed_as_data_and_changed_quests_never_get_legacy_facts(self):
        self.assertEqual(list(sql_rows("(1,'A \\'quoted\\' (name)',2),(3,'Second',4)")),
                         [['1',"A 'quoted' (name)",'2'],['3','Second','4']])
        old={'Title':'Quest','QuestLevel':12,'MinLevel':10}
        q={'title':'Quest','level':12,'minLevel':10,'foreverStatus':'unchanged'}
        self.assertTrue(matches(q,old))
        for change in ({'foreverStatus':'updated'},{'minLevel':9},{'title':'New quest'},{'levelingExcluded':'Collector reward'}):
            self.assertFalse(matches(dict(q,**change),old))

    def test_offline_calibration_rejects_changed_or_insufficient_map_anchors(self):
        entities={'npc':{}};legacy={'npc':{}}
        for id,(x,y) in enumerate(((.1,.1),(.8,.8),(.2,.7),(.7,.2),(.5,.4)),1):
            entities['npc'][id]={'locations':[{'mapID':1411,'x':x,'y':y}]}
            legacy['npc'][id]={'worldLocations':[(1,1000*(1-y),2000*(1-x))]}
        transforms=calibrate(entities,legacy)
        self.assertEqual(transforms[1411]['anchors'],5)
        entities['npc'][1]['locations'][0]['x']=.55
        self.assertNotIn(1411,calibrate(entities,legacy))


def world_client():
    c=guide_client(1)
    q=world_quest('Mapped through client')
    q.pop('starts');q.pop('ends');q['objectives']=[]
    q.update(foreverStatus='unchanged',legacyFactsSource='Source',objectiveLocationsIncomplete=True,
        worldReferences={'starts':[{'entityType':'npc','entityID':7,'name':'Giver'}],
                         'ends':[{'entityType':'npc','entityID':7,'name':'Giver'}],
                         'requirements':[{'entityType':'item','entityID':10,'name':'Drop','quantity':8}]})
    catalogue(c,{900:q})
    c.ns.questEntities=c.lua.table_from({'npc':{
        7:{'name':'Giver','worldLocations':[[1,200,300]]},
        8:{'name':'Boar','worldLocations':[[1,400,500]]}},
        'item':{10:{'name':'Drop','sources':[{'entityType':'npc','entityID':8,'name':'Boar','action':'loot'}]}},'object':{}},recursive=True)
    c.ns.worldQuestChecks=c.lua.table_from({1:[{'mapID':501,'x':x,'y':y,'continent':1,'worldX':1000*x,'worldY':1000*y}
        for x,y in ((.1,.2),(.3,.6),(.8,.4))]},recursive=True)
    c.lua.execute('''
      CreateVector2D=function(x,y) return {x=x,y=y,GetXY=function(self) return self.x,self.y end} end
      projectionCalls=0
      C_Map.GetMapPosFromWorldPos=function(continent,v,map)
        projectionCalls=projectionCalls+1
        if map~=501 or continent~=1 then return nil end
        return map,CreateVector2D(v.x/1000,v.y/1000)
      end
      C_Map.GetWorldPosFromMapPos=function(map,v)
        if map~=501 then return nil end
        return 1,CreateVector2D(v.x*1000,v.y*1000)
      end
    ''')
    return c


class NativeTransformTests(unittest.TestCase):
    def test_verified_transform_recovers_named_givers_and_drops_without_shared_point_mutation(self):
        c=world_client();ctx=c.lua.table();c.ns.ResolveWorldQuestLocations(900,ctx)
        q=c.ns.CatalogueQuest(900)
        self.assertEqual((q.starts[1].x,q.starts[1].y),(.2,.3))
        self.assertEqual(q.starts[1].name,'Giver')
        self.assertEqual((q.objectives[1].x,q.objectives[1].y),(.4,.5))
        self.assertEqual(q.objectives[1].itemName,'Drop')
        self.assertEqual(q.objectives[1].quantity,8)
        self.assertFalse(q.objectiveLocationsIncomplete)
        self.assertIsNone(q.starts[1].itemName)
        self.assertFalse(c.lua.eval('rawequal')(q.starts[1],q.ends[1]))
        count=c.lua.globals().projectionCalls;c.ns.ResolveWorldQuestLocations(900,ctx)
        self.assertEqual(c.lua.globals().projectionCalls,count)
        self.assertEqual(len(q.objectives),1)

    def test_private_missing_or_contradictory_projection_keeps_gaps(self):
        for replacement in ('C_Map.GetMapPosFromWorldPos=nil',
                            'C_Map.GetMapPosFromWorldPos=function() return secret,secret end',
                            'C_Map.GetMapPosFromWorldPos=function(_,_,m) return m,CreateVector2D(.99,.99) end'):
            c=world_client();c.lua.execute(replacement);c.ns.ResolveWorldQuestLocations(900,c.lua.table())
            self.assertIsNone(c.ns.CatalogueQuest(900).starts)
            self.assertTrue(c.ns.CatalogueQuest(900).objectiveLocationsIncomplete)

    def test_changed_quest_is_not_projected_even_with_working_native_transform(self):
        c=world_client();c.ns.CatalogueQuest(900).foreverStatus='updated'
        c.ns.ResolveWorldQuestLocations(900,c.lua.table())
        self.assertEqual(c.lua.globals().projectionCalls,0)
        self.assertIsNone(c.ns.CatalogueQuest(900).starts)

    def test_swapped_native_axes_must_be_confirmed_by_three_published_anchors(self):
        c=world_client();c.lua.execute('''
          C_Map.GetMapPosFromWorldPos=function(continent,v,map)
            if map~=501 or continent~=1 then return nil end
            return map,CreateVector2D(v.y/1000,v.x/1000)
          end
        ''')
        c.ns.ResolveWorldQuestLocations(900,c.lua.table())
        self.assertEqual((c.ns.CatalogueQuest(900).starts[1].x,c.ns.CatalogueQuest(900).starts[1].y),(.2,.3))


class GuideInstructionTests(unittest.TestCase):
    def test_real_scorpid_tail_goal_prefers_the_published_worker_area(self):
        c=Client(quests=(),use_catalogue=True)
        q=c.ns.CatalogueQuest(789)
        self.assertEqual(q.objectives[1].name,'Scorpid Worker')
        self.assertEqual(q.objectives[1].quantity,10)
        self.assertEqual({p.name for p in q.objectiveAlternatives[1].locations.values()},{'Scorpid Worker','Sarkoth'})
    def test_named_kill_loot_and_item_use_instructions(self):
        c=guide_client(1)
        stop=c.lua.table_from({'id':900,'kind':'q','title':'Supplies','quantity':8,'itemName':'Flank',
            'npcName':'Boar','targetName':'Boar','action':'loot'})
        self.assertEqual(c.ns.StopInstruction(stop),'Pick up 8 × Flank from Boar')
        stop.itemName=None;stop.action='kill'
        self.assertEqual(c.ns.StopInstruction(stop),'Kill 8 × Boar')
        stop.action='use';stop.useItemName='Wake-up Tool'
        self.assertEqual(c.ns.StopInstruction(stop),'Use Wake-up Tool on 8 × Boar')
        stop.action='interact';stop.npcName=None;stop.targetName='Supply crate'
        self.assertEqual(c.ns.StopInstruction(stop),'Interact with Supply crate')

    def test_item_started_quest_names_the_drop_source_instead_of_a_dialogue_giver(self):
        c=guide_client(1)
        stop=c.lua.table_from({'id':900,'kind':'a','title':'Letter','itemName':'Sealed Letter','npcName':'Bandit',
            'action':'start-item','sourceAction':'loot'})
        self.assertEqual(c.ns.StopInstruction(stop),'Loot Sealed Letter from Bandit; use it to start the quest')

    def test_real_lazy_peons_uses_supplied_tool_instead_of_killing_or_farming_it(self):
        c=Client(quests=(),use_catalogue=True)
        q=c.ns.CatalogueQuest(5441)
        self.assertFalse(q.objectiveLocationsIncomplete)
        self.assertEqual(q.objectives[1].action,'use')
        self.assertEqual(q.objectives[1].useItemName,"Foreman's Blackjack")
        self.assertEqual(len(q.objectives),1)

    def test_uncategorized_new_zones_are_not_merged_into_one_global_guide(self):
        c=guide_client(1)
        data={900:world_quest('First island quest','Island A',801),901:world_quest('Second island quest','Island A',801),
              902:world_quest('First forest quest','Forest B',802),903:world_quest('Second forest quest','Forest B',802)}
        for q in data.values():q['categoryPath']='uncategorized'
        catalogue(c,data)
        choices=list(c.ns.LevelingGuideChoices().values())
        self.assertEqual({g.homeMapID for g in choices},{801,802})
        self.assertTrue(all(len(g.records)==2 for g in choices))

    def test_outdoor_crafting_category_stays_out_of_leveling_guides(self):
        c=guide_client(2)
        for q in c.ns.catalogue.quests.values():q.categoryPath='kalimdor/crafting'
        self.assertTrue(c.ns.IsProfessionQuest(900))
        self.assertEqual(len(c.ns.LevelingGuideChoices()),0)

    def test_native_offer_overrides_only_older_world_prerequisite(self):
        c=guide_client(2);q=c.ns.CatalogueQuest(901)
        q.previousQuest=900;q.prerequisiteSource='Identity-matched unchanged quest: Source'
        c.ns.offered[901]=True
        self.assertTrue(c.ns.CatalogueAllowed(901,c.ns.profile,c.ns.self))
        q.prerequisiteSource='Tester report: beta'
        self.assertFalse(c.ns.CatalogueAllowed(901,c.ns.profile,c.ns.self)[0])

    def test_separate_item_steps_share_an_area_but_not_new_skip_credit(self):
        c=guide_client(1)
        stops=c.lua.table_from([
            {'id':900,'kind':'q','mapID':501,'entityID':7,'objectiveKey':'item:10','legacyStepKey':'q:501:npc:7'},
            {'id':900,'kind':'q','mapID':501,'entityID':7,'objectiveKey':'item:11'}],recursive=True)
        self.assertNotEqual(c.ns.GuideStepKey(stops[1]),c.ns.GuideStepKey(stops[2]))
        c.ns.db.guideSkips[c.ns.self].steps[900]=c.lua.table_from({'q:501:npc:7':True})
        filtered=c.ns.FilterGuideStages(stops)
        self.assertEqual(len(filtered),1)
        self.assertEqual(filtered[1].objectiveKey,'item:11')


if __name__=='__main__':unittest.main()
