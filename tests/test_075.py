"""Alternative farming points and native locations for unmapped fixed steps."""
import json
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest
from test_063 import guide_client, order
from test_importers import detail
from import_wowhead import detail_facts


def drops(missing=0, far_first=True):
    points = [
        {'point':'start','type':1,'id':10,'name':'Giver','coord':[20,30]},
        {'point':'end','type':1,'id':10,'name':'Giver','coord':[20,30]},
        {'point':'sourcerequirement','type':1,'objective':0,'id':100,'name':'Far boar','item':'Flank','coord':[80,70]},
        {'point':'sourcerequirement','type':1,'objective':0,'id':200,'name':'Near boar','item':'Flank','coord':[30,35]}]
    if not far_first: points[2], points[3] = points[3], points[2]
    return detail_facts(detail(points, missing), {'id':42}, {14:501})


class AlternativeImportTests(unittest.TestCase):
    def test_alternatives_keep_coordinates_and_one_deterministic_primary(self):
        for far_first in (True, False):
            facts = drops(far_first=far_first)
            self.assertEqual(len(facts['objectives']), 1)
            self.assertEqual(facts['objectives'][0]['entityID'], 200)
            self.assertEqual(facts['objectives'][0]['alternativeCount'], 2)
            self.assertEqual({p['entityID'] for p in facts['objectiveAlternatives'][0]['locations']}, {100,200})
            self.assertNotIn('objectiveLocationsIncomplete', facts)
            self.assertNotIn('objectiveIndex', facts['objectives'][0])

    def test_real_missing_metadata_stays_missing_despite_one_known_item_area(self):
        facts = drops(missing=1)
        self.assertTrue(facts['objectiveLocationsIncomplete'])
        self.assertEqual(facts['objectives'][0]['itemName'], 'Flank')

    def test_no_map_join_does_not_invent_coordinates_or_area_map_id(self):
        points = [{'point':'sourcerequirement','type':1,'objective':0,'id':i,'name':'Drop source','coord':[30,35]}
                  for i in (100,200)]
        facts = detail_facts(detail(points), {'id':42}, {})
        self.assertNotIn('objectives', facts)
        self.assertEqual(facts['unmappedLocations'][0]['sourceAreaID'], 14)
        self.assertNotIn('mapID', facts['unmappedLocations'][0])
        self.assertEqual(len(facts['npcTargets']), 2)

    def test_alternative_candidate_on_another_map_is_not_preferred_by_raw_xy(self):
        page = detail([]).split('new Mapper(')[0] + 'new Mapper(' + json.dumps({'objectives':{
            '14': {'zone':'Durotar','levels':[[{'point':'start','type':1,'id':10,'coord':[20,30]},
                {'point':'sourcerequirement','type':1,'objective':0,'id':200,'coord':[50,50]}]]},
            '15': {'zone':'Other zone','levels':[[{'point':'sourcerequirement','type':1,'objective':0,'id':100,'coord':[20,30]}]]}
            },'missing':0}) + ');'
        facts = detail_facts(page, {'id':42}, {14:501,15:502})
        self.assertEqual(facts['objectives'][0]['entityID'], 200)
        self.assertEqual(len(facts['objectiveAlternatives'][0]['locations']), 2)

    def test_fixed_guide_does_not_turn_alternative_sources_into_two_required_visits(self):
        c=guide_client(1)
        q=quest('Alternative drops');q.update(drops())
        catalogue(c,{900:q})
        g=guide(c,(900,),key='alternatives');g.fixedRoute=True
        c.ns.GenerateFixedGuide(g,False)
        work=[p for p in g.fixedPlan.values() if p.kind=='q']
        self.assertEqual(len(work),1)
        self.assertEqual(work[0].entityID,200)
        self.assertEqual(work[0].alternativeCount,2)
        self.assertFalse(work[0].unknownLocation)


def native_client():
    c = guide_client(1)
    data = quest('Partial drops', objectiveLocationsIncomplete=True,
                 objectives=[{'mapID':501,'x':.6,'y':.5,'entityID':200,'name':'Near boar','itemName':'Flank','action':'collect','npc':True}])
    catalogue(c,{900:data})
    g = guide(c,(900,),key='partial');g.fixedRoute=True;g.fullGuide=True;g.zone='Test Coast'
    c.lua.execute('''
    entries={{questID=900,title='Partial drops'}}
    C_QuestLog.GetQuestObjectives=function() return {
      {text='Flank: 8/8',type='item',numFulfilled=8,numRequired=8,finished=true},
      {text='Snout: 0/8',type='item',numFulfilled=0,numRequired=8,finished=false}}
    end
    C_QuestLog.GetNextWaypoint=function() return 501,.7,.6 end
    C_QuestLog.IsComplete=function() return false end
    function GetPlayerFacing() return 0 end
    C_Map.GetMapWorldSize=function() return 1000,1000 end
    ''')
    c.ns.ReadQuests();c.ns.ReadProgress();c.ns.ReadRouteLocations()
    c.ns.ActivateRoute(g);c.ns.UpdateNavigation()
    return c,g


class NativeObjectiveTests(unittest.TestCase):
    def test_shipped_battleboars_maps_both_items_to_the_proven_common_source(self):
        c=Client(quests=(),use_catalogue=True)
        q=c.ns.CatalogueQuest(780)
        self.assertEqual(q.objectives[1].name,'Battleboar')
        self.assertAlmostEqual(q.objectives[1].x,.576)
        self.assertAlmostEqual(q.objectives[1].y,.852)
        self.assertEqual(q.objectives[2].entityID,q.objectives[1].entityID)
        self.assertEqual((q.objectives[2].x,q.objectives[2].y),(q.objectives[1].x,q.objectives[1].y))
        self.assertEqual(q.objectives[2].quantity,8)
        self.assertEqual(q.objectives[1].itemName,'Battleboar Flank')
        self.assertFalse(q.objectiveLocationsIncomplete)
        self.assertEqual({p.entityID for p in q.objectiveAlternatives[1].locations.values()}, {2954,2966})
        self.assertEqual({p.itemName for p in q.objectives.values()}, {'Battleboar Flank', 'Battleboar Snout'})

    def test_native_position_fills_only_the_unmapped_stage_and_keeps_fixed_order(self):
        c,g = native_client()
        before=order(g)
        stop=c.ns.selectedRoute.stops[1]
        self.assertTrue(stop.clientLocation)
        self.assertEqual((stop.kind,stop.x,stop.y),('q',.7,.6))
        self.assertTrue(g.fixedPlan[3].unknownLocation)
        self.assertIsNone(g.fixedPlan[3].x)
        self.assertFalse(c.ns.routePaused)
        self.assertIn('quest tracker',c.ns.navigation.context.text)
        c.lua.execute('C_QuestLog.GetNextWaypoint=function() return 501,.8,.65 end')
        c.ns.ReadRouteLocations();c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].x,.8)
        self.assertEqual(order(g),before)
        self.assertFalse(c.ns.Completed(900))

    def test_published_fallback_is_not_recycled_as_the_missing_item_area(self):
        c,g=native_client()
        c.lua.execute('C_QuestLog.GetNextWaypoint=function() return nil end; C_QuestLog.GetQuestsOnMap=function() return {} end')
        c.ns.ReadRouteLocations();c.ns.UpdateFixedGuideRoute(g)
        self.assertTrue(c.ns.routeLocations[900].published)
        self.assertEqual(len(c.ns.selectedRoute.stops),0)
        self.assertIn('location missing',c.ns.routePaused)

    def test_private_or_wrong_kind_native_location_cannot_fill_missing_step(self):
        for api in ('C_QuestLog.GetNextWaypoint=function() return secret,.7,.6 end',
                    'C_QuestLog.GetNextWaypoint=function() return 501,secret,.6 end'):
            c,g=native_client()
            c.lua.execute(api+'; C_QuestLog.GetQuestsOnMap=function() return {} end')
            c.ns.ReadRouteLocations();c.ns.UpdateFixedGuideRoute(g)
            self.assertEqual(len(c.ns.selectedRoute.stops),0)
        c,g=native_client()
        c.ns.routeLocations[900].kind='a';c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(len(c.ns.selectedRoute.stops),0)

    def test_completed_quest_advances_to_hand_in_and_missing_location_is_not_saved(self):
        c,g=native_client()
        c.lua.execute('C_QuestLog.IsComplete=function() return true end')
        c.ns.ReadRouteLocations();c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind,'t')
        self.assertIsNone(c.ns.selectedRoute.stops[1].clientLocation)
        c.ns.SaveSelectedGuide()
        saved=c.ns.db.guideState[c.ns.self].guide.fixedPlan[3]
        self.assertTrue(saved.unknownLocation)
        self.assertIsNone(saved.x)

    def test_partial_data_routes_known_area_before_the_remaining_placeholder(self):
        c,g=native_client()
        c.lua.execute('C_QuestLog.GetQuestObjectives=function() return {{text="Flank: 0/8",type="item",numFulfilled=0,numRequired=8,finished=false}} end')
        c.ns.ReadProgress();c.ns.UpdateFixedGuideRoute(g)
        stop=c.ns.selectedRoute.stops[1]
        self.assertEqual(stop.targetName,'Near boar')
        self.assertEqual(stop.x,.6)
        self.assertFalse(stop.clientLocation)

    def test_skip_step_uses_fixed_placeholder_key_after_native_location_changes(self):
        c,g=native_client()
        c.ns.SkipGuide('step')
        c.lua.execute('C_QuestLog.GetNextWaypoint=function() return 501,.8,.65 end')
        c.ns.ReadRouteLocations();c.ns.UpdateFixedGuideRoute(g)
        self.assertFalse(any(p.clientLocation for p in c.ns.selectedRoute.stops.values()))
        self.assertTrue(c.ns.db.guideSkips[c.ns.self].steps[900]['q:501:unknown'])
        self.assertFalse(c.ns.Completed(900))


if __name__=='__main__': unittest.main()
