"""Actual-level zone eligibility and public world-space cross-zone rendering.

Synthetic coordinates test geometry/state, not beta terrain or native map behavior.
"""
import math
import unittest
from test_063 import guide_client
from test_061 import world_quest
from test_routes import catalogue, guide
from test_addon import Client


def maps(c):
    c.lua.execute('''
    bounds={[501]={x=0,width=1000},[502]={x=1000,width=1000},[503]={x=2000,width=1000},[10]={x=0,width=3000}}
    playerMap,playerX,playerY=501,.21,.37
    function CreateVector2D(x,y) return {GetXY=function() return x,y end} end
    function GetPlayerFacing() return 0 end
    C_Map.GetBestMapForUnit=function() return playerMap end
    C_Map.GetPlayerMapPosition=function(map) if map==playerMap then return CreateVector2D(playerX,playerY) end end
    C_Map.GetMapWorldSize=function(map) return bounds[map].width,1000 end
    C_Map.GetWorldPosFromMapPos=function(map,p)
      local b=bounds[map];if not b then return end
      local x,y=p:GetXY();return differentContinents and map or 1,CreateVector2D(b.x+x*b.width,y*1000)
    end
    C_Map.GetMapPosFromWorldPos=function(continent,p,map)
      local b=bounds[map];if not b then return end
      local x,y=p:GetXY();x=(x-b.x)/b.width;y=y/1000
      if outsideNil and (x<0 or x>1 or y<0 or y>1) then return end
      return map,CreateVector2D(x,y)
    end
    ''')


def traveling():
    c = guide_client(2); maps(c)
    g = guide(c, (900,))
    route = c.lua.table_from({'mapID':502,'stops':[{'id':900,'kind':'a','mapID':502,'x':.2,'y':.37,
        'title':'Remote pickup','label':'Talk to the remote NPC'}]},recursive=True)
    c.ns.ActivateRoute(g,route);c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame,501)
    c.ns.DrawRoute();return c


class LevelEligibilityTests(unittest.TestCase):
    def test_shipped_catalogue_hides_ashenvale_for_a_level_twelve_horde_player(self):
        c=Client(quests=(),use_catalogue=True);c.guide_environment(level=12)
        c.lua.globals().grouped=False;c.ns.profile.classID=7;c.ns.profile.raceID=2
        zones={g.zone for g in c.ns.LevelingGuideChoices().values()}
        self.assertNotIn('Ashenvale',zones)
        self.assertIn('The Barrens',zones)
        c.ns.profile.level=20
        self.assertIn('Ashenvale',{g.zone for g in c.ns.LevelingGuideChoices().values()})

    def test_same_bracket_does_not_make_level_twenty_zone_suitable_at_twelve(self):
        c=guide_client(4)
        catalogue(c,{900:world_quest('Current work'),901:world_quest('Current second'),
            902:world_quest('Future first','Ashenvale',1440,20,minLevel=20),
            903:world_quest('Future second','Ashenvale',1440,20,minLevel=20)})
        self.assertEqual([g.zone for g in c.ns.LevelingGuideChoices().values()],['Test Coast'])
        c.ns.guideLevel='all'
        self.assertEqual([g.zone for g in c.ns.LevelingGuideChoices().values()],['Test Coast','Ashenvale'])
        c.ns.profile.level=20
        self.assertEqual([g.zone for g in c.ns.LevelingGuideChoices().values()],['Ashenvale','Test Coast'])

    def test_actual_pickup_minimum_and_useful_difficulty_are_both_checked(self):
        for level,minimum in ((13,20),(20,5)):
            c=guide_client(2)
            catalogue(c,{900:world_quest(level=level,minLevel=minimum),901:world_quest(level=level,minLevel=minimum)})
            self.assertEqual(len(c.ns.LevelingGuideChoices()),0)

    def test_unknown_level_record_cannot_qualify_an_otherwise_future_zone(self):
        c=guide_client(2)
        catalogue(c,{900:world_quest('Future work',level=20,minLevel=20),
                     901:world_quest('No level data',level=0,minLevel=None)})
        self.assertEqual(len(c.ns.LevelingGuideChoices()),0)
        c.ns.guideLevel='all'
        self.assertEqual(len(c.ns.LevelingGuideChoices()),1)
        self.assertTrue(c.ns.LevelingGuideChoices()[1].upcoming)

    def test_blocked_high_level_parent_cannot_make_child_zone_look_ready(self):
        for minimum in (5,20):
            c=guide_client(3)
            catalogue(c,{899:world_quest('Required parent','Other Zone',502,20,minLevel=minimum),
                900:world_quest('Child',previousQuest=899),901:world_quest('Another child',previousQuest=899)})
            self.assertEqual(len(c.ns.LevelingGuideChoices()),0)

    def test_unfinished_same_level_parents_remain_part_of_discovery_and_fixed_plan(self):
        c=guide_client(2)
        catalogue(c,{900:world_quest('Parent'),901:world_quest('Child',previousQuest=900)})
        g=c.ns.LevelingGuideChoices()[1]
        self.assertIsNotNone(g)
        c.ns.GenerateFixedGuide(g,False)
        stages=[(s.id,s.kind) for s in g.fixedPlan.values()]
        self.assertLess(stages.index((900,'t')),stages.index((901,'a')))

    def test_low_level_useful_chain_and_alternative_prerequisite_are_not_lost(self):
        c=guide_client(4)
        catalogue(c,{899:world_quest('Too high parent','Other Zone',502,20,minLevel=20),
            900:world_quest('Useful low parent',level=3),
            901:world_quest('Useful continuation',prerequisiteAny=[899,900])})
        self.assertEqual([g.zone for g in c.ns.LevelingGuideChoices().values()],['Test Coast'])

    def test_level_up_refresh_and_search_do_not_change_selected_fixed_sequence(self):
        c=guide_client(2);g=c.ns.LevelingGuideChoices()[1];c.ns.ActivateRoute(g)
        before=[(s.id,s.kind) for s in g.fixedPlan.values()]
        c.ns.guideSearch='Quest';c.ns.profile.level=20;c.ns.Refresh()
        self.assertEqual(len(c.ns.LevelingGuideChoices()),0)
        self.assertEqual([(s.id,s.kind) for s in c.ns.routeSelection.fixedPlan.values()],before)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))


class ProjectionTests(unittest.TestCase):
    def test_coordinates_project_beyond_zone_border_and_onto_parent_map(self):
        c=guide_client(2);maps(c)
        p=c.lua.table_from({'mapID':502,'x':.5,'y':.4})
        self.assertAlmostEqual(c.ns.ProjectMapPoint(p,501).x,1.5)
        self.assertAlmostEqual(c.ns.ProjectMapPoint(p,10).x,.5)
        self.assertAlmostEqual(c.ns.ProjectMapPoint(p,10).y,.4)

    def test_affine_fallback_handles_outside_nil_missing_api_and_rotated_world_axes(self):
        for mode in ('outside','missing','rotated'):
            c=guide_client(2);maps(c)
            if mode=='outside': c.lua.globals().outsideNil=True
            else: c.lua.execute('C_Map.GetMapPosFromWorldPos=nil')
            if mode=='rotated':
                c.lua.execute('C_Map.GetWorldPosFromMapPos=function(map,p) local x,y=p:GetXY();local b=bounds[map];return 1,CreateVector2D(-y*1000,b.x+x*b.width) end')
            p=c.lua.table_from({'mapID':502,'x':.2,'y':.37})
            result=c.ns.ProjectMapPoint(p,501)
            self.assertAlmostEqual(result.x,1.2);self.assertAlmostEqual(result.y,.37)

    def test_secret_missing_different_continent_and_degenerate_world_data_have_no_projection(self):
        for replacement in ('differentContinents=true', 'C_Map.GetWorldPosFromMapPos=nil',
            'C_Map.GetWorldPosFromMapPos=function() return secret,secret end',
            'C_Map.GetWorldPosFromMapPos=function() return 1,CreateVector2D(secret,0) end',
            'C_Map.GetMapPosFromWorldPos=nil;C_Map.GetWorldPosFromMapPos=function() return 1,CreateVector2D(0,0) end'):
            c=guide_client(2);maps(c);c.lua.execute(replacement)
            self.assertIsNone(c.ns.ProjectMapPoint(c.lua.table_from({'mapID':502,'x':.2,'y':.37}),501))

    def test_current_zone_line_starts_at_live_position_and_clips_at_border(self):
        c=traveling();p=c.ns.routeProvider
        self.assertEqual(c.ns.routeStats.lines,1)
        self.assertEqual(c.ns.routeStats.pins,0)
        self.assertAlmostEqual(p.lines[1].startPoint[3],210)
        self.assertAlmostEqual(p.lines[1].endPoint[3],1000)
        c.lua.globals().playerX=.5;p.legend.OnUpdate(p.legend,1)
        self.assertAlmostEqual(p.lines[1].startPoint[3],500)
        self.assertEqual(c.ns.selectedRoute.stops[1].mapID,502)

    def test_losing_public_position_clears_the_old_origin_line(self):
        for replacement in ('C_Map.GetBestMapForUnit=function() return secret end',
                            'C_Map.GetPlayerMapPosition=function() return nil end'):
            c=traveling();p=c.ns.routeProvider;c.lua.execute(replacement)
            p.legend.OnUpdate(p.legend,1)
            self.assertIsNone(p.playerOrigin)
            self.assertEqual(c.ns.routeStats.lines,0)

    def test_missing_cross_zone_coordinates_are_explained_without_drawing(self):
        c=traveling();c.lua.execute('C_Map.GetWorldPosFromMapPos=nil');c.ns.ResetMapProjection();c.ns.DrawRoute()
        self.assertEqual(c.ns.routeStats.lines,0)
        self.assertIn('Travel to',c.ns.routeProvider.legend.caption.text)
        self.assertIn('unavailable',c.ns.routeStats.status)

    def test_destination_zone_and_continent_view_join_correct_world_coordinates(self):
        c=traveling();m=c.lua.globals().WorldMapFrame;p=c.ns.routeProvider
        m.SetMapID(m,502);c.ns.DrawRoute()
        self.assertAlmostEqual(p.lines[1].startPoint[3],0)
        self.assertAlmostEqual(p.lines[1].endPoint[3],200)
        self.assertEqual(c.ns.routeStats.pins,1)
        m.SetMapID(m,10);c.ns.DrawRoute()
        self.assertAlmostEqual(p.lines[1].startPoint[3],70)
        self.assertAlmostEqual(p.lines[1].endPoint[3],400)
        self.assertEqual(c.ns.routeStats.pins,1)

    def test_cross_zone_arrow_distance_updates_and_continues_after_crossing(self):
        c=traveling();c.ns.UpdateNavigation()
        self.assertTrue(c.ns.navigation.state.crossZone)
        self.assertAlmostEqual(c.ns.navigation.state.distance,990)
        self.assertAlmostEqual(c.ns.navigation.state.angle,-math.pi/2)
        c.lua.globals().playerX=.5;c.ns.UpdateNavigation()
        self.assertAlmostEqual(c.ns.navigation.state.distance,700)
        c.lua.globals().playerMap=502;c.lua.globals().playerX=.1;c.ns.UpdateNavigation()
        self.assertAlmostEqual(c.ns.navigation.state.distance,100)
        self.assertFalse(c.ns.navigation.state.crossZone)

    def test_unprojectable_step_breaks_line_instead_of_shortcutting_it(self):
        c=traveling();c.lua.globals().differentContinents=True
        self.assertIsNone(c.ns.NavigationState().angle)
        c.ns.selectedRoute.mapID=501
        c.ns.selectedRoute.stops=c.lua.table_from([
            {'id':900,'kind':'q','mapID':501,'x':.3,'y':.37,'title':'First','label':'First'},
            {'id':901,'kind':'q','mapID':502,'x':.4,'y':.37,'title':'Transport','label':'Transport'},
            {'id':900,'kind':'t','mapID':501,'x':.8,'y':.37,'title':'Later','label':'Later'}],recursive=True)
        c.ns.db.config.fullRoute=True;c.ns.DrawRoute()
        self.assertEqual(c.ns.routeStats.lines,1)
        self.assertEqual(c.ns.routeStats.pins,2)


if __name__=='__main__': unittest.main()
