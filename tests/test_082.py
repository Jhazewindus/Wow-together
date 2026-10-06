"""Published map geometry regressions; these are not live-client validation."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))

from forever_map_geometry import geometry_facts
from legacy_quest_facts import mapped_locations
from lua_data_literal import literal
from quest_event_areas import apply_event_areas
from test_063 import guide_client, zone
from test_066 import reload
from test_061 import world_quest
from test_routes import catalogue
from forever_beta_facts import apply_fields, base_fields, objective_facts, merge_beta_facts, static_fields
from quest_enrichment import enrich, warcraftdb_objective_facts, warcraftdb_map_facts
from quest_observation_facts import coordinate_observations, apply_observations


def report():
    return {'format': 1, 'tool': 'QuestieDB convert-forever', 'geometry': {
        'target_build': '1.60.1.69893', 'target_tables': {
            table: {'coverage': 'ok', 'rows': 61, 'snapshot_sha256': 'a'*64}
            for table in ('ui_map', 'ui_map_assignment')}, 'transforms': [
                {'map_id': 1, 'area_transform_supported': True, 'ui_map_id': 501,
                 'area_id': 100, 'target_bounds': {'left': -2000, 'right': -7000,
                                               'top': 2000, 'bottom': -2000}}]}}


class WarcraftDBNativeMapTests(unittest.TestCase):
    def fixture(self):
        raw={'data':{'name':'Sample the wells','objectives':[
            {'link_node':'item','link_id':10,'amount':1},
            {'link_node':'item','link_id':11,'amount':1}]},'extra':{'quest_map':{
            'floors':[{'id':501,'base_tiles':['do not copy']}],
            'starts':[{'ui_map_id':501,'u':.1,'v':.2}],
            'turn_ins':[{'ui_map_id':501,'u':.1,'v':.2}],
            'objectives':[{'ui_map_id':501,'objective_index':1,'points':[{'u':.4,'v':.5}]}]}}}
        quest={'title':'Sample the wells','prerequisitesRead':True,'mapID':501}
        refs={'starts':[],'ends':[],'requirements':[{'entityType':'item','entityID':11,
            'name':'Water sample','quantity':1,'action':'collect'}]}
        entities={k:{} for k in ('item','npc','object')}
        return raw,quest,refs,entities

    def test_original_objective_index_survives_provided_item_filtering(self):
        raw,q,refs,entities=self.fixture()
        self.assertEqual(warcraftdb_map_facts(raw,q,refs,entities,{501}),3)
        self.assertEqual((q['objectives'][0]['itemID'],q['objectives'][0]['x']),(11,.4))
        self.assertNotIn('missingRequirements',q);self.assertNotIn('objectiveLocationsIncomplete',q)
        self.assertNotIn('base_tiles',str(q));self.assertNotIn('npc',q['starts'][0])

    def test_existing_destinations_and_exact_target_counts_take_precedence(self):
        raw,q,refs,entities=self.fixture()
        q['starts']=[{'mapID':501,'x':.9,'y':.8,'name':'Known giver'}]
        raw['data']['objectives'][1]['amount']=7
        warcraftdb_map_facts(raw,q,refs,entities,{501})
        self.assertEqual(q['starts'][0]['x'],.9);self.assertFalse(q.get('objectives'))

    def test_unknown_map_wrong_quest_identity_and_nonfinite_points_cannot_fill_gaps(self):
        for change in ('map','identity','nan','range','index'):
            raw,q,refs,entities=self.fixture();m=raw['extra']['quest_map']
            if change=='map':m['floors'][0]['id']=999
            if change=='identity':raw['data']['name']='A different quest'
            if change=='nan':m['objectives'][0]['points'][0]['u']=float('nan')
            if change=='range':m['objectives'][0]['points'][0]['v']=1.1
            if change=='index':m['objectives'][0]['objective_index']=True
            warcraftdb_map_facts(raw,q,refs,entities,{501})
            with self.subTest(change=change):self.assertFalse(q.get('objectives'))

    def test_polygon_uses_a_published_point_without_inventing_a_spawn_or_centroid(self):
        raw,q,refs,entities=self.fixture()
        raw['extra']['quest_map']['objectives'][0]['points']=[{'u':.4,'v':.5},{'u':.8,'v':.9}]
        warcraftdb_map_facts(raw,q,refs,entities,{501})
        self.assertEqual((q['objectives'][0]['x'],q['objectives'][0]['y']),(.4,.5))
        self.assertEqual(q['objectives'][0]['entityType'],'item')


class PublishedGeometryTests(unittest.TestCase):
    def test_world_axes_are_converted_to_the_exact_published_rectangle(self):
        transforms, areas, source = geometry_facts(report())
        entity = {'worldLocations': [(1, 0, -4000), (0, 0, -4000), (1, 9000, 9000)]}
        points = mapped_locations(entity, transforms, transforms)
        self.assertEqual(areas, {100: 501})
        self.assertEqual(len(points), 1)
        self.assertEqual((points[0]['mapID'], points[0]['x'], points[0]['y']), (501, .4, .5))
        self.assertIn('published Forever', points[0]['locationSource'])
        self.assertEqual(source['outdoor_maps'], 1)

    def test_instance_and_unsupported_map_views_cannot_create_destinations(self):
        data = report()
        a = dict(data['geometry']['transforms'][0], ui_map_id=502, area_id=101, map_id=30)
        b = dict(a, ui_map_id=503, area_id=102, map_id=1, area_transform_supported=False)
        data['geometry']['transforms'].extend((a, b))
        transforms, areas, _ = geometry_facts(data)
        self.assertEqual(set(transforms), {501})
        self.assertEqual(areas, {100: 501})

    def test_unreviewed_build_and_incomplete_target_snapshots_are_rejected(self):
        for change in ('build', 'coverage', 'checksum', 'duplicate', 'rectangle'):
            data = report()
            if change == 'build': data['geometry']['target_build'] = '1.60.1.future'
            if change == 'coverage': data['geometry']['target_tables']['ui_map']['coverage'] = 'partial'
            if change == 'checksum': data['geometry']['target_tables']['ui_map']['snapshot_sha256'] = ''
            if change == 'duplicate': data['geometry']['transforms'] *= 2
            if change == 'rectangle': data['geometry']['transforms'][0]['target_bounds']['right'] = -2000
            with self.subTest(change=change), self.assertRaises(ValueError): geometry_facts(data)

    def test_a_changed_map_rectangle_changes_coordinates_without_moving_the_spawn(self):
        data = report(); other = copy.deepcopy(data)
        other['geometry']['transforms'][0]['target_bounds']['left'] = -1000
        entity = {'worldLocations': [(1, 0, -4000)]}
        original = mapped_locations(entity, geometry_facts(data)[0], (501,))
        changed = mapped_locations(entity, geometry_facts(other)[0], (501,))
        self.assertEqual(original[0]['x'], .4)
        self.assertEqual(changed[0]['x'], .5)
        self.assertEqual(entity['worldLocations'], [(1, 0, -4000)])


class EventAreaTests(unittest.TestCase):
    def fixture(self):
        q = {'title':'Well Cleansing', 'minLevel':4, 'level':6, 'foreverStatus':'unchanged',
             'legacyFactsSource':'Facts', 'objectiveLocationsIncomplete':True}
        row = {1:q['title'], 4:4, 5:6, 8:{1:'Use the Cleansing Totem at the well.'},
               9:{1:'Cleanse the Water Well', 2:{215:{1:{1:51.76, 2:68.43}}}}, 11:5411}
        return {900:q}, {900:row}, {900:{'SpecialFlags':2}}, {5411:{'name':'Cleansing Totem'}}

    def apply(self, records, rows, old, items):
        return apply_event_areas(records, rows, set(), {900}, old, items, {215:1412})

    def test_exact_event_location_and_provided_item_replace_an_unknown_step(self):
        records, rows, old, items = self.fixture(); result = self.apply(records, rows, old, items)
        point = records[900]['objectives'][0]
        self.assertEqual(result['event_areas_used'], [900])
        self.assertEqual((point['mapID'], point['x'], point['y']), (1412, .5176, .6843))
        self.assertEqual((point['action'], point['useItemName'], point['name']), ('use', 'Cleansing Totem', 'Water Well'))
        self.assertNotIn('objectiveLocationsIncomplete', records[900])
        self.assertNotIn('Use the Cleansing Totem at the well.', str(records))

    def test_changed_identity_missing_proof_and_multiple_endpoints_keep_the_gap(self):
        for change in ('updated', 'identity', 'unproven', 'multiple'):
            records, rows, old, items = self.fixture()
            if change == 'updated': records[900]['foreverStatus'] = 'updated'
            if change == 'identity': rows[900][4] = 3
            if change == 'unproven': records[900].pop('legacyFactsSource')
            if change == 'multiple': rows[900][9][2][215][2] = {1:40, 2:40}
            result = self.apply(records, rows, old, items)
            with self.subTest(change=change):
                self.assertFalse(result['event_areas_used'])
                self.assertTrue(records[900]['objectiveLocationsIncomplete'])

    def test_public_data_parser_cannot_evaluate_function_calls(self):
        value = literal('{"A \\"quoted\\" name", nil, {[215]={{51.76,68.43}}}}')
        self.assertEqual(value[1], 'A "quoted" name')
        self.assertEqual(value[3][215][1][1], 51.76)
        for source in ('{os.execute("bad")}', '{1}; print("bad")', '{[1]=1,[1]=2}', '{1/0}'):
            with self.subTest(source=source), self.assertRaises(ValueError): literal(source)

    def test_escort_pickup_and_work_remain_adjacent_through_optimization(self):
        c = guide_client(1); escort = world_quest('Escort the guide'); other = world_quest('Nearby supplies')
        escort.update(level=12, minLevel=1, starts=[{'mapID':501,'x':.1,'y':.1,'name':'Guide','npc':True}],
            objectives=[{'mapID':501,'x':.9,'y':.9,'name':'Guide','action':'escort'}],
            ends=[{'mapID':501,'x':.9,'y':.8,'name':'Contact','npc':True}])
        other.update(level=12, minLevel=1, starts=[{'mapID':501,'x':.105,'y':.105}],
            objectives=[{'mapID':501,'x':.2,'y':.2}], ends=[{'mapID':501,'x':.2,'y':.25}])
        catalogue(c, {900:escort,901:other}); g = zone(c)
        c.ns.GenerateFixedGuide(g, False)
        plan = list(g.fixedPlan.values()); pickup = next(i for i,s in enumerate(plan) if s.id==900 and s.kind=='a')
        self.assertEqual((plan[pickup+1].id, plan[pickup+1].action), (900, 'escort'))
        self.assertLessEqual(g.optimization.after, g.optimization.before+1e-6)

    def test_event_and_item_at_area_instructions_do_not_turn_into_kill_labels(self):
        c = guide_client(1)
        stop = c.lua.table_from({'id':900,'kind':'q','title':'Cleansing','targetName':'Water Well',
            'action':'use','sourceAction':'use-at','useItemName':'Cleansing Totem'})
        self.assertEqual(c.ns.StopInstruction(stop), 'Use Cleansing Totem at Water Well')
        stop.action='escort';stop.targetName='Guide'
        self.assertEqual(c.ns.StopInstruction(stop), 'Escort Guide')


class BetaFactTests(unittest.TestCase):
    def data(self):
        row={'name':'Study the ruins','requiredLevel':1,'questLevel':4,'requiredRaces':8589934770,
            'startedBy':{1:{1:101}},'finishedBy':{1:{1:102}},'zoneOrSort':100,
            'objectives':{1:{1:{1:103,3:'action:event'}}}}
        data={'quest':{900:row},'npc':{i:{'name':name,'spawns':{100:{1:{1:x,2:20}}}}
            for i,name,x in ((101,'Guide',10),(102,'Contact',30),(103,'Event credit',20))},'object':{},'item':{}}
        origins={k:{i:{field:'beta-reviewed' for field in r} for i,r in rows.items()} for k,rows in data.items()}
        return data,{100:501},{'source':'https://example.test/facts','skipped_nonliteral_fields':[]},origins

    def merge(self, data=None, records=None, refs=None):
        source=self.data()
        if data is not None:source=data
        records=records if records is not None else {900:{'title':'Study the ruins','level':4,'minLevel':1}}
        refs=refs if refs is not None else {}
        entities={k:{} for k in ('npc','object','item')}
        with patch('forever_beta_facts.read_beta_facts',return_value=source):
            provenance=merge_beta_facts(records,refs,entities,{},None)
        for ident,relation in refs.items():enrich(records[ident],relation,entities)
        return records,refs,entities,provenance

    def test_parser_excludes_dynamic_code_assumptions_and_nonliteral_calls(self):
        text='''function Provider:Load()
    return {
        [900] = { -- Study the ruins
            [questKeys.requiredRaces] = 0, -- Assumption: universal
            [questKeys.requiredLevel] = evil(),
            [questKeys.startedBy] = {nil, nil, {202}},
        },
    }
end
function Provider:LoadDynamic()
    return {
        [900] = {
            [questKeys.requiredLevel] = 60,
        },
    }
end'''
        rows,skipped,assumptions=static_fields(text,'quest',{})
        self.assertNotIn('requiredLevel',rows[900]);self.assertNotIn('requiredRaces',rows[900])
        self.assertEqual(rows[900]['startedBy'],{1:None,2:None,3:{1:202}})
        self.assertEqual(skipped,[['quest',900,'requiredLevel']]);self.assertEqual(len(assumptions),1)

    def test_baseline_parser_preserves_numeric_slots_and_rejects_execution(self):
        text="QuestieDB.questKeys = {\n    ['name'] = 1,\n    ['requiredLevel'] = 4,\n}\nQuestieDB.questData = [[return {\n[900] = {'Study',nil,nil,4},\n}]]"
        self.assertEqual(base_fields(text,'quest'),{900:{'name':'Study','requiredLevel':4}})
        with self.assertRaises(ValueError):base_fields(text.replace("'Study'","evil()"),'quest')

    def test_nested_add_remove_keeps_item_starter_slot_three(self):
        row={'startedBy':{1:{1:101},3:{1:202}}}
        apply_fields(row,{'startedBy_remove':{1:{1:101}},'startedBy_add':{3:{1:203}}})
        self.assertEqual(row['startedBy'],{1:{},3:{1:202,2:203}})

    def test_beta_event_type_corrects_a_primary_kill_without_losing_its_count(self):
        refs={900:{'starts':[],'ends':[],'requirements':[{'entityType':'npc','entityID':103,'name':'Find ruins','quantity':1,'action':'kill'}]}}
        records,refs,_,p=self.merge(refs=refs)
        point=records[900]['objectives'][0]
        self.assertEqual((point['action'],point['quantity'],point['name']),('event',1,'Event credit'))
        self.assertEqual(p['corrected_objective_quest_ids'],[900])

    def test_unknown_count_is_not_invented_and_no_source_prose_is_bundled(self):
        source=self.data();source[0]['quest'][900]['objectivesText']={1:'Study these mysterious ruins for the guide.'}
        records,refs,_,_=self.merge(source)
        self.assertNotIn('quantity',refs[900]['requirements'][0])
        self.assertTrue(records[900]['objectives'][0]['quantityUnknown'])
        self.assertNotIn('mysterious',str(records))

    def test_provided_items_are_delivery_steps_not_unmapped_farming_steps(self):
        source=self.data();row=source[0]['quest'][900];row.pop('objectives');row['sourceItemId']=201
        source[0]['item'][201]={'name':'Report'};source[3]['quest'][900].pop('objectives')
        refs={900:{'starts':[],'ends':[],'requirements':[{'entityType':'item','entityID':201,'name':'Report','quantity':1}]}}
        records,refs,_,_=self.merge(source,refs=refs)
        self.assertFalse(refs[900]['requirements']);self.assertFalse(records[900].get('objectiveLocationsIncomplete'))

    def test_new_current_beta_inverse_relations_fill_quests_without_a_core_row(self):
        source=self.data();source[0]['npc'][101]['questStarts']={1:901};source[3]['npc'][101]['questStarts']='beta-observation'
        records={901:{'title':'Another quest','level':4,'minLevel':1}}
        records,_,_,p=self.merge(source,records)
        self.assertEqual(records[901]['starts'][0]['entityID'],101)
        self.assertIn([901,'starts'],p['inverse_beta_relations_used'])

    def test_native_map_identity_conflicts_are_rejected(self):
        source=self.data()
        with patch('forever_beta_facts.read_beta_facts',return_value=source),self.assertRaises(ValueError):
            merge_beta_facts({}, {}, {'npc':{},'item':{},'object':{}},{100:502},None)

    def test_current_unrestricted_mask_is_not_replaced_by_old_faction_race_gate(self):
        source=self.data()
        source[3]['quest'][900]['requiredRaces']='converted-baseline'
        records={900:{'title':'Study the ruins','level':4,'minLevel':1,'raceMask':0,'side':'Horde'}}
        records,_,_,_=self.merge(source,records)
        self.assertEqual(records[900]['raceMask'],0)
        self.assertNotIn('allowedRaceIDs',records[900])

    def test_credit_alternatives_form_one_goal_not_seven_required_kills(self):
        row={'objectives':{5:{1:{1:{1:101,2:102},2:101,4:'action:interact'}}},
            'objectivesText':{1:'Heal 7 injured druids.'}}
        data=self.data()[0];facts=objective_facts(row,data)
        self.assertEqual(len(facts),1)
        self.assertEqual((facts[0]['action'],facts[0]['quantity'],facts[0]['alternativeEntityIDs']),('interact',7,[101,102]))

    def test_aggregate_healing_keeps_seven_credits_instead_of_one_npc_count(self):
        source=self.data();row=source[0]['quest'][900]
        row['objectives']={5:{1:{1:{1:101,2:102},2:101,4:'action:interact'}}}
        row['objectivesText']={1:'Heal 7 injured druids.'}
        refs={900:{'starts':[],'ends':[],'requirements':[
            {'entityType':'npc','entityID':101,'name':'Injured Druids healed','quantity':1,'action':'kill'}]}}
        records,_,_,_=self.merge(source,refs=refs)
        goal=records[900]['requirements'][0]
        self.assertEqual((goal['action'],goal['quantity'],goal['objectiveLabel']),('heal',7,'Injured druids'))
        self.assertNotIn('Heal 7 injured druids.',str(records))

    def test_structured_provided_item_is_removed_even_without_a_detail_page(self):
        raw={'data':{'provided_item':{'id':201,'name':'Tool'},'objectives':[
            {'link_node':'item','link_id':201,'description':'Tool','amount':1,'type':1},
            {'link_node':'item','link_id':202,'description':'Dust','amount':5,'type':1}]}}
        requirements,provided=warcraftdb_objective_facts(raw)
        self.assertEqual([(r['entityID'],r['quantity']) for r in requirements],[(202,5)])
        self.assertEqual(provided[0]['entityID'],201)

    def test_all_prerequisites_are_required_for_pickup_and_compiled_before_child(self):
        c=guide_client(1);quests={i:world_quest(str(i)) for i in (900,901,902)}
        for q in quests.values():q.update(level=12,minLevel=1)
        quests[902]['prerequisiteAll']=[900,901]
        catalogue(c,quests);c.lua.globals().finished[900]=True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(902,c.ns.self)[0])
        c.lua.globals().finished[901]=True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(902,c.ns.self))
        g=zone(c);c.ns.GenerateFixedGuide(g,False);positions={(s.id,s.kind):i for i,s in enumerate(g.fixedPlan.values())}
        self.assertLess(positions[900,'t'],positions[902,'a']);self.assertLess(positions[901,'t'],positions[902,'a'])

    def test_skyborne_race_gates_do_not_truncate_high_mask_bits(self):
        c=guide_client(1);q=world_quest('Skyborne quest');q.update(raceMask=8589934592,allowedRaceIDs=[96])
        catalogue(c,{900:q});c.ns.profile.raceID=96
        self.assertTrue(c.ns.CatalogueIdentityAllowed(900,c.ns.profile))
        c.ns.profile.raceID=2
        self.assertFalse(c.ns.CatalogueIdentityAllowed(900,c.ns.profile)[0])

    def test_reloaded_fixed_healing_step_keeps_its_shared_label_and_target_ids(self):
        c=guide_client(1)
        q=world_quest('Heal the injured')
        q.update(level=12,minLevel=1)
        q['objectives']=[{'mapID':501,'x':.2,'y':.3,'name':'Credit NPC','npc':True,'entityID':101,
            'action':'heal','quantity':7,'alternativeEntityIDs':[101,102],
            'objectiveLabel':'Injured druids','progressName':'Injured druids healed'}]
        catalogue(c,{900:q,901:world_quest('Other work')});g=zone(c);c.ns.ActivateRoute(g)
        fresh=reload(c,active=(900,))
        work=next(s for s in fresh.ns.routeSelection.fixedPlan.values() if s.kind=='q')
        self.assertEqual(fresh.ns.StopInstruction(work),'Heal 7 × Injured druids')
        self.assertEqual(list(work.alternativeEntityIDs.values()),[101,102])
        self.assertEqual(work.progressName,'Injured druids healed')

    def test_nearby_objectives_keep_the_current_targets_item_and_count(self):
        c=guide_client(1);q=world_quest('Two nearby goals')
        q['objectives']=[{'mapID':501,'x':.2,'y':.3,'name':'First area','itemName':'First item',
            'itemID':201,'action':'collect','quantity':3},
            {'mapID':501,'x':.21,'y':.3,'name':'Second area','itemName':'Second item',
            'itemID':202,'action':'collect','quantity':7}]
        catalogue(c,{900:q});c.ns.active[900]=True
        c.ns.routeLocations[900]=c.lua.table_from({'mapID':501,'x':.21,'y':.3,'kind':'q','name':'Second area'})
        stop=c.ns.RouteStop(c.ns.CatalogueRecord(900),c.ns.self)
        self.assertEqual((stop.itemID,stop.quantity),(202,7))
        c.ns.routeLocations[900].quantity=9
        stop=c.ns.RouteStop(c.ns.CatalogueRecord(900),c.ns.self)
        self.assertEqual(stop.quantity,9)


class CommunityCoordinateTests(unittest.TestCase):
    def page(self, body, **fields):
        row=dict(id=123,dataTree=16,outofdate=0,deleted=0,body=body)
        row.update(fields)
        return 'var lv_comments0 = '+json.dumps([row])+';'

    def test_only_explicit_identity_zone_and_coordinate_facts_are_retained(self):
        page=self.page('Found in [zone=215]: [li][item=201] is located at 58.6, 47.3[/li]')
        result=coordinate_observations(page,900,{215:1412})
        self.assertEqual((result[0][0],result[0][1],result[0][2]['mapID']),('item',201,1412))
        self.assertEqual((result[0][2]['x'],result[0][2]['y']),(.586,.473))
        self.assertNotIn('Found in',str(result))

    def test_ambiguous_zones_conflicting_points_and_other_game_comments_stay_unknown(self):
        for body,fields in (('[item=201] at 58.6, 47.3',{}),
            ('[zone=215] [zone=14] [item=201] at 58.6, 47.3',{}),
            ('[zone=215] [item=201] at 58.6, 47.3; [item=201] at 15, 15',{}),
            ('[zone=215] [item=201] at 58.6, 47.3',{'dataTree':1}),
            ('[zone=215] [item=201] at 58.6, 47.3',{'outofdate':1})):
            with self.subTest(body=body,fields=fields):
                self.assertEqual(coordinate_observations(self.page(body,**fields),900,{215:1412,14:1411}),[])

    def test_ground_item_observation_fills_only_a_matching_unknown_requirement(self):
        pages={900:self.page('[zone=215] [item=201] at 58.6, 47.3')}
        records={900:{'title':'Find notes'}}
        refs={900:{'starts':[],'ends':[],'requirements':[{'entityType':'item','entityID':201,'name':'Notes','quantity':1}]}}
        entities={'npc':{},'object':{},'item':{201:{'name':'Notes','locations':[]}}}
        report=apply_observations(pages,records,refs,entities,{215:1412})
        enrich(records[900],refs[900],entities)
        self.assertEqual(records[900]['objectives'][0]['action'],'collect')
        self.assertEqual(report['coordinate_observations_used'][0]['commentID'],123)
        self.assertNotIn('at 58.6',str(records))


if __name__ == '__main__': unittest.main()
