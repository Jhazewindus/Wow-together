"""Hostile settlement ground crossings, faction ownership and retained guides.

Synthetic public map geometry checks behavior, not actual guards or roads.
"""
import json
import unittest

from test_addon import Client, ROOT
from test_070 import network_client, point
from test_routes import guide, map_canvas
from test_060 import flight_client


def area(c, owner='Alliance'):
    c.ns.travelData.settlements=c.lua.table_from([{'name':'Enemy town','faction':owner,
        'mapID':501,'minX':.45,'maxX':.55,'minY':.30,'maxY':.40}],recursive=True)


class SettlementTravelTests(unittest.TestCase):
    def client(self, detour=True):
        c=network_client(nodes={
            'P':{'mapID':501,'x':.25,'y':.75,'name':'Published south crossing'},
            'Q':{'mapID':501,'x':.75,'y':.75,'name':'Published southeast crossing'}},
            edges=[{'from':'P','to':'Q','method':'walk','seconds':100}])
        area(c)
        if not detour: c.ns.travelData.nodes=c.lua.table();c.ns.travelData.edges=c.lua.table()
        return c

    def test_a_direct_crossing_uses_existing_detour_points_without_invented_nodes(self):
        c=self.client()
        a,b=point(c,501,.2,.35),point(c,501,.8,.35)
        self.assertEqual(c.ns.HostileWalkCrossing(a,b).name,'Enemy town')
        path=c.ns.FindTravelPath(a,b,False)
        self.assertEqual([(s.fromID,s.toID) for s in path.legs.values()],
            [('START','P'),('P','Q'),('Q','GOAL')])
        for leg in path.legs.values(): self.assertIsNone(c.ns.HostileWalkCrossing(leg['from'],leg.to))

    def test_ally_neutral_and_unscoped_settlements_do_not_block_transit(self):
        c=self.client(False)
        for owner in ('Horde','Both',None):
            area(c,owner)
            self.assertIsNone(c.ns.HostileWalkCrossing(point(c,501,.2,.35),point(c,501,.8,.35)))
            self.assertEqual(len(c.ns.FindTravelPath(point(c,501,.2,.35),point(c,501,.8,.35),False).legs),1)
        area(c,'Alliance');c.ns.profile.faction='Alliance'
        self.assertIsNotNone(c.ns.FindTravelPath(point(c,501,.2,.35),point(c,501,.8,.35),False))

    def test_segment_intersection_checks_full_segment_not_just_endpoints(self):
        c=self.client(False)
        self.assertIsNone(c.ns.HostileTravelArea(point(c,501,.2,.35)))
        self.assertIsNone(c.ns.HostileTravelArea(point(c,501,.8,.35)))
        self.assertIsNotNone(c.ns.HostileWalkCrossing(point(c,501,.2,.35),point(c,501,.8,.35)))
        self.assertIsNone(c.ns.HostileWalkCrossing(point(c,501,.2,.7),point(c,501,.8,.7)))
        self.assertIsNotNone(c.ns.HostileWalkCrossing(point(c,501,.5,.1),point(c,501,.5,.8)))

    def test_margins_use_both_physical_map_axes_and_private_scales_are_safe(self):
        c=self.client(False)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 10000,1000 end')
        self.assertIsNotNone(c.ns.HostileTravelArea(point(c,501,.5,.21)))
        self.assertIsNone(c.ns.HostileTravelArea(point(c,501,.43,.35)))
        c.lua.execute('C_Map.GetMapWorldSize=function() return secret,secret end')
        self.assertIsNotNone(c.ns.HostileWalkCrossing(point(c,501,.2,.35),point(c,501,.8,.35)))
        p=point(c);p.x=c.lua.globals().secret
        self.assertIsNone(c.ns.HostileWalkCrossing(p,point(c,501,.8,.35)))

    def test_an_intentional_destination_or_exit_does_not_skip_real_quest_work(self):
        c=self.client(False)
        a,b=point(c,501,.2,.35),point(c,501,.5,.35)
        self.assertIsNotNone(c.ns.FindTravelPath(a,b,False))
        self.assertIsNotNone(c.ns.FindTravelPath(b,a,False))
        self.assertIsNone(c.ns.HostileWalkCrossing(b,a,None,True,False))
        self.assertIsNone(c.ns.HostileWalkCrossing(a,b,None,False,True))
        self.assertFalse(c.ns.Completed(900))

    def test_missing_bypass_keeps_the_guide_and_shows_caution_without_a_direct_arrow(self):
        c=self.client(False)
        stop={'id':900,'kind':'q','title':'Current quest','mapID':501,'x':.8,'y':.35,'label':'Work here'}
        c.ns.ActivateRoute(guide(c,(900,)),c.lua.table_from({'mapID':501,'stops':[stop]},recursive=True))
        c.ns.UpdateNavigation()
        state=c.ns.navigation.state
        self.assertTrue(state.visible)
        self.assertIsNone(state.angle)
        self.assertIn('Route around Enemy town',state.status)
        self.assertIn('No mapped bypass',c.ns.navigation.context.text)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind,'q')
        self.assertFalse(c.ns.Completed(900));self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_preview_lines_through_town_are_hidden_but_markers_and_other_lines_remain(self):
        c=self.client(False);map_canvas(c)
        c.ns.db.config.travelNetwork=False;c.ns.db.config.fullRoute=True
        stops=[{'id':900,'kind':'q','title':'Across town','mapID':501,'x':.9,'y':.37},
            {'id':901,'kind':'t','title':'Nearby return','mapID':501,'x':.95,'y':.30}]
        c.ns.ActivateRoute(guide(c,(900,901)),c.lua.table_from({'mapID':501,'stops':stops},recursive=True))
        c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame,501)
        c.ns.DrawRoute()
        self.assertGreaterEqual(c.ns.routeStats.pins,2)
        self.assertEqual(c.ns.routeStats.hostileLines,1)
        self.assertEqual(c.ns.routeStats.lines,1)
        area(c,'Horde');c.ns.ResetTravelPath();c.ns.DrawRoute()
        self.assertEqual(c.ns.routeStats.hostileLines,0)
        self.assertEqual(c.ns.routeStats.lines,2)

    def test_cross_zone_projection_detects_crossing_on_the_rendered_map(self):
        c=self.client(False)
        # Map 502 is east of map 501 in the public transform, not the same x/y.
        a,b=point(c,502,-.8,.35),point(c,501,.8,.35)
        self.assertIsNotNone(c.ns.HostileWalkCrossing(a,b))
        self.assertIsNone(c.ns.HostileWalkCrossing(point(c,502,.1,.35),b))

    def test_cached_known_flight_cannot_reintroduce_an_enemy_travel_point(self):
        c=network_client(nodes={'A':{'mapID':501,'x':.2,'y':.35},
            'TAXI_28':{'mapID':502,'x':.4,'y':.35},'B':{'mapID':503,'x':.8,'y':.35}},
            edges=[{'from':'A','to':'TAXI_28','seconds':10,'method':'walk'},
                {'from':'TAXI_28','to':'B','seconds':10,'method':'walk'}])
        c.ns.db.flights[c.ns.self].nodes[28]=c.lua.table_from({'id':28,'known':True,'name':'Astranaar',
            'point':{'mapID':502,'x':.4,'y':.35}},recursive=True)
        self.assertIsNone(c.ns.FindTravelPath(point(c,501,.2,.35),point(c,503,.8,.35),True))
        c.ns.profile.faction='Alliance'
        self.assertIsNotNone(c.ns.FindTravelPath(point(c,501,.2,.35),point(c,503,.8,.35),True))

    def test_unknown_neutral_taxi_ownership_is_not_inferred_from_town_or_known_flag(self):
        c=self.client(False)
        owned=c.lua.table_from({'known':True,'faction':'Alliance'})
        self.assertFalse(c.ns.TravelNodeAllowed('TAXI_9000',point(c,501,.2,.8),owned))
        owned.faction='Both'
        self.assertTrue(c.ns.TravelNodeAllowed('TAXI_9000',point(c,501,.2,.8),owned))
        c.ns.guideServiceData.taxis[9001]=c.lua.table_from({'name':'Neutral hub'})
        self.assertTrue(c.ns.TravelNodeAllowed('TAXI_9001',point(c,501,.2,.8)))

    def test_flight_fallback_rejects_hostile_owners_and_ground_access_not_the_flight_ride(self):
        c=flight_client();c.ns.ReadFlightMap();area(c)
        stop=c.ns.selectedRoute.stops[1]
        # Flying over an enemy town is allowed; only approach/exit walks matter.
        self.assertIsNotNone(c.ns.FindFlightPlan(stop))
        state=c.ns.db.flights[c.ns.self]
        state.nodes[22].faction='Alliance'
        self.assertIsNone(c.ns.FindFlightPlan(stop))
        state.nodes[22].faction=None
        state.nodes[11].point.x=.7;state.nodes[11].world.x=7000
        self.assertIsNone(c.ns.FindFlightPlan(stop))

    def test_caution_cache_refreshes_for_faction_and_clears_on_a_connected_path(self):
        c=self.client(False)
        c.lua.execute('clock=1;function GetTime()return clock end')
        stop=point(c,501,.8,.35);stop.id,stop.kind,stop.title=900,'q','Current quest'
        c.ns.db.config.travelNetwork=False
        self.assertIsNotNone(c.ns.TravelDestination(stop).unsafeTransit)
        c.ns.profile.faction='Alliance'
        self.assertIsNone(c.ns.TravelDestination(stop).unsafeTransit)
        c.ns.profile.faction='Horde'
        self.assertIsNotNone(c.ns.TravelDestination(stop).unsafeTransit)
        # A newly connected path wins even during the fallback cache's second.
        c.ns.HasTravelPathTo=c.lua.eval('function()return true end')
        self.assertIsNone(c.ns.TravelDestination(stop).unsafeTransit)

    def test_cleared_map_does_not_retain_hostile_line_diagnostics(self):
        c=self.client(False);map_canvas(c)
        stop=point(c,501,.8,.35);stop.id,stop.kind,stop.title=900,'q','Current quest'
        c.ns.ActivateRoute(guide(c,(900,)),c.lua.table_from({'mapID':501,'stops':[stop]},recursive=True))
        c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame,501)
        c.ns.DrawRoute();self.assertEqual(c.ns.routeStats.hostileLines,1)
        c.ns.ClearRoute();self.assertEqual(c.ns.routeStats.hostileLines,0)

    def test_shipped_astranaar_data_and_all_known_taxi_owners_agree(self):
        c=Client(quests=());c.guide_environment(level=23)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 7000,5000 end')
        self.assertEqual(c.ns.travelData.nodes['TAXI_28'].faction,'Alliance')
        self.assertEqual(c.ns.HostileWalkCrossing(point(c,1440,.3,.49),point(c,1440,.42,.49)).name,'Astranaar')
        c.ns.profile.faction='Alliance'
        self.assertIsNone(c.ns.HostileWalkCrossing(point(c,1440,.3,.49),point(c,1440,.42,.49)))
        for id,meta in c.ns.guideServiceData.taxis.items():
            node=c.ns.travelData.nodes['TAXI_'+str(id)]
            if node and meta.faction: self.assertEqual(node.faction,meta.faction,id)
        self.assertEqual(len(c.ns.travelData.settlements),48)
        self.assertEqual(json.loads((ROOT/'WowTogether/TravelData.json').read_text())['settlement_footprints'],48)


if __name__=='__main__':unittest.main()
