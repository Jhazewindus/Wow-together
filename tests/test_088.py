"""Named branching confirmation and area objectives; live beta checks remain needed."""
import unittest

from test_routes import catalogue, guide, map_canvas, quest, route_client
from test_076 import offer


def confirmation_client(mapped=True):
    c = route_client()
    c.ns.SetOption('soloMode', True)
    map_canvas(c)
    c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 501)
    start = {'mapID': 501, 'x': .3, 'y': .4, 'name': 'Test Giver', 'npc': True, 'entityID': 123}
    catalogue(c, {900: quest('Branching Quest', prerequisitesRead=True, prerequisitesUnverified=True,
                           starts=[start] if mapped else [],
                           startRefs=[{'entityType': 'npc', 'entityID': 123, 'name': 'Test Giver'}])})
    g = guide(c)
    g.fixedRoute, g.fullGuide, g.mode, g.mapID, g.homeMapID = True, True, 'zone', 501, 501
    c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,1000 end; function GetPlayerFacing() return 0 end')
    c.ns.ActivateRoute(g)
    c.ns.Refresh()
    return c, g


def area_client(count=3):
    c = route_client()
    c.ns.SetOption('soloMode', True)
    # Use a supplied immutable objective phase without the dashboard rebuilding
    # this synthetic single-quest guide from unrelated catalogue fixtures.
    c.ns.Render = None
    c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,1000 end; function GetPlayerFacing() return 0 end')
    data, stops, active, progress = {}, [], {}, {}
    for i in range(count):
        ident = 900 + i
        target = 'Test Creature ' + str(i)
        data[ident] = quest('Quest ' + str(i), prerequisitesRead=True)
        stop = {'id': ident, 'kind': 'q', 'title': data[ident]['title'], 'mapID': 501,
                'x': .3 + i * .01, 'y': .4, 'targetName': target, 'npcName': target,
                'action': 'kill', 'quantity': 7, 'entityID': 100 + i, 'objectiveKey': 'npc:' + str(100 + i)}
        if i == 1:
            stop.update(action='gather', itemName='Test Apples', targetName='Test Apple Tree', npcName=None,
                        objectiveKey='item:200')
        stops.append(stop)
        active[ident] = True
        progress[ident] = {'objectives': [{'text': stop.get('itemName', target), 'have': i,
                                         'need': 7, 'kind': 'item' if i == 1 else 'monster'}]}
    catalogue(c, data)
    c.ns.routeSelection = guide(c, tuple(data))
    c.ns.selectedRoute = c.lua.table_from({'mapID': 501, 'stops': stops}, recursive=True)
    c.ns.active = c.lua.table_from(active)
    c.ns.localProgress = c.lua.table_from(progress, recursive=True)
    c.ns.Refresh()
    return c


class ConfirmationTests(unittest.TestCase):
    def test_warning_names_giver_without_promoting_eligibility(self):
        c, g = confirmation_client()
        allowed, reason = c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)
        self.assertIsNone(allowed)
        self.assertIn('branching prerequisite', reason)
        self.assertIn('Talk to Test Giver.', reason)
        self.assertIn('Talk to Test Giver', c.ns.navigation.status.text)
        self.assertIsNotNone(c.ns.navigation.state.angle)
        self.assertFalse(c.ns.Completed(900))
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertEqual(c.ns.navigation.work.heading.text, 'Confirm with Test Giver')
        self.assertTrue(c.ns.CurrentQuestConfirmation().confirmation)

    def test_map_and_nameplate_star_are_distinct_and_do_not_call_native_waypoint(self):
        c, g = confirmation_client()
        c.lua.execute("""
        C_Map.SetUserWaypoint=function() error('automatic waypoint forbidden') end
        plates={nameplate1=CreateFrame('Frame')}
        C_NamePlate={GetNamePlateForUnit=function(unit) return plates[unit] end}
        function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end
        """)
        c.ns.AttachRouteProvider(); c.ns.DrawRoute()
        pin = c.ns.routeProvider.pins[1]
        self.assertEqual(pin.width, 30)
        self.assertIn('UI-RaidTargetingIcon_1', pin.icon.texture)
        c.ns.handlers.NAME_PLATE_UNIT_ADDED('nameplate1')
        hint = c.ns.npcHints['nameplate1']
        self.assertTrue(hint.target.confirmation)
        self.assertIn('Confirm:', hint.questNames.text)
        self.assertIn('UI-RaidTargetingIcon_1', hint.icon.texture)
        c.ns.SetOption('nameplateHints', False)
        self.assertFalse(hint.IsShown(hint))

    def test_explicit_map_button_can_set_and_clean_only_its_own_waypoint(self):
        c, g = confirmation_client()
        c.lua.execute("""
        nativeWaypoint=nil; cleared=0; waypointCalls=0
        C_Map.SetUserWaypoint=function(p) nativeWaypoint={uiMapID=p.map, position={GetXY=function() return p.x,p.y end}}; waypointCalls=waypointCalls+1 end
        C_Map.GetUserWaypoint=function() return nativeWaypoint end
        C_Map.ClearUserWaypoint=function() nativeWaypoint=nil; cleared=cleared+1 end
        """)
        self.assertEqual(c.lua.globals().waypointCalls, 0)
        self.assertTrue(c.ns.ShowConfirmationOnMap())
        self.assertEqual(c.lua.globals().waypointCalls, 1)
        self.assertEqual(c.lua.globals().WorldMapFrame.mapID, 501)
        c.ns.ClearConfirmationWaypoint(c.ns.CurrentQuestConfirmation())
        self.assertEqual(c.lua.globals().cleared, 0)
        # Ownership survives a namespace restart/reload, not just this frame.
        self.assertIsNotNone(c.ns.db.confirmationWaypoints[c.ns.self])
        c.ns.confirmationWaypoint = None
        c.ns.active[900] = True; c.ns.Refresh()
        self.assertEqual(c.lua.globals().cleared, 1)
        self.assertIsNone(c.ns.CurrentQuestConfirmation())

    def test_players_replacement_waypoint_is_preserved_and_combat_defers_cleanup(self):
        c, g = confirmation_client()
        c.lua.execute("""
        nativeWaypoint=nil; cleared=0
        C_Map.SetUserWaypoint=function(p) nativeWaypoint={uiMapID=p.map, position={GetXY=function() return p.x,p.y end}} end
        C_Map.GetUserWaypoint=function() return nativeWaypoint end
        C_Map.ClearUserWaypoint=function() nativeWaypoint=nil; cleared=cleared+1 end
        """)
        c.ns.ShowConfirmationOnMap()
        c.lua.execute("nativeWaypoint={uiMapID=501,position={GetXY=function() return .8,.8 end}}")
        c.ns.active[900] = True; c.ns.Refresh()
        self.assertEqual(c.lua.globals().cleared, 0)
        c.ns.active[900] = None
        c.ns.UpdateSelectedRoute(None, c.ns.NewQuestQuery()); c.ns.Refresh()
        c.ns.ShowConfirmationOnMap()
        c.lua.execute('combat=true')
        self.assertFalse(c.ns.ShowConfirmationOnMap())
        c.ns.active[900] = True; c.ns.Refresh()
        self.assertEqual(c.lua.globals().cleared, 0)
        c.lua.execute('combat=false'); c.ns.Refresh()
        self.assertEqual(c.lua.globals().cleared, 1)

    def test_unsupported_waypoints_still_show_addon_marker_and_map(self):
        c, g = confirmation_client()
        c.lua.execute("C_Map.GetUserWaypoint=nil; C_Map.SetUserWaypoint=function() error('unsupported') end")
        self.assertTrue(c.ns.ShowConfirmationOnMap())
        self.assertIsNone(c.ns.confirmationWaypoint)
        self.assertTrue(c.ns.routeProvider.pins[1].IsShown(c.ns.routeProvider.pins[1]))
        c.lua.execute('C_Map.CanSetUserWaypointOnMap=function() return secret end')
        self.assertTrue(c.ns.ShowConfirmationOnMap())

    def test_actual_offer_clears_confirmation_and_keeps_fixed_order(self):
        c, g = confirmation_client()
        before = [(s.id, s.kind, s.x, s.y) for s in g.fixedPlan.values()]
        offer(c, (900,))
        self.assertIsNone(c.ns.CurrentQuestConfirmation())
        self.assertTrue(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self))
        self.assertEqual(before, [(s.id, s.kind, s.x, s.y) for s in g.fixedPlan.values()])
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'a')

    def test_blocked_or_other_unknown_requirements_never_get_branch_marker(self):
        for change in ('q.minLevel=99', "q.side='Alliance'", 'q.previousQuest=899',
                       'q.prerequisitesUnverified=nil; q.prerequisitesRead=false',
                       'ns.db.guideSkips[ns.self].quests[900]=true'):
            c, g = confirmation_client()
            c.lua.execute('local ns=...; local q=ns.catalogue.quests[900]; ' + change, c.ns)
            if 'prerequisitesRead' in change:
                c.ns.catalogue.detailSource = 'fixture'
            self.assertIsNone(c.ns.CurrentQuestConfirmation())

    def test_unmapped_giver_keeps_name_and_nameplate_hint_without_fake_coordinates(self):
        c, g = confirmation_client(mapped=False)
        stop = c.ns.CurrentQuestConfirmation()
        self.assertEqual(stop.npcName, 'Test Giver')
        self.assertTrue(stop.unknownLocation)
        self.assertIsNone(stop.x)
        self.assertFalse(c.ns.ShowConfirmationOnMap())
        self.assertTrue(c.ns.NPCTargets()[0][123].confirmation)
        self.assertIsNone(c.ns.navigation.state.angle)

    def test_item_started_quests_do_not_gain_a_friendly_giver_confirmation_marker(self):
        c, g = confirmation_client()
        c.ns.selectedRoute.pendingStop.action = 'start-item'
        self.assertIsNone(c.ns.CurrentQuestConfirmation())
        self.assertIsNone(c.ns.NPCTargets()[0][123])

    def test_confirmation_directions_can_use_existing_travel_network_while_pickup_is_paused(self):
        c, g = confirmation_client()
        stop = c.ns.CurrentQuestConfirmation()
        c.lua.execute('local ns=...; travelCalls=0; ns.FindTravelPath=function() travelCalls=travelCalls+1 end; ns.ResetTravelPath()', c.ns)
        c.ns.TravelNetworkDestination(stop)
        self.assertEqual(c.lua.globals().travelCalls, 1)
        self.assertIsNotNone(c.ns.routePaused)
        self.assertIsNone(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])

    def test_movement_updates_reuse_confirmation_until_a_progress_event(self):
        c, g = confirmation_client()
        c.lua.execute('clock=1; historyCalls=0; function GetTime() return clock end; C_QuestLog.IsQuestFlaggedCompleted=function() historyCalls=historyCalls+1; return false end')
        first = c.ns.CurrentQuestConfirmation()
        for _ in range(5): c.ns.UpdateNavigation()
        self.assertTrue(c.lua.eval('rawequal')(first, c.ns.CurrentQuestConfirmation()))
        self.assertEqual(c.lua.globals().historyCalls, 1)
        c.ns.offered[900] = True; c.ns.Refresh()
        self.assertIsNone(c.ns.CurrentQuestConfirmation())


class AreaObjectiveTests(unittest.TestCase):
    def test_fixed_guide_progress_filters_goals_without_changing_compiled_sequence(self):
        c = area_client()
        g = c.ns.routeSelection
        g.fixedRoute, g.fullGuide, g.mapID = True, True, 501
        g.fixedPlan = c.ns.selectedRoute.stops
        before = [(s.id, s.kind) for s in g.fixedPlan.values()]
        c.ns.selectedRoute = c.ns.BuildFixedGuideRoute(g, False)
        c.ns.Refresh()
        self.assertEqual(len(c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])), 3)
        c.ns.localProgress[900].objectives[1].have = 7
        c.ns.selectedRoute = c.ns.BuildFixedGuideRoute(g, False); c.ns.Refresh()
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        self.assertEqual(len(c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])), 2)
        self.assertEqual(before, [(s.id, s.kind) for s in g.fixedPlan.values()])

    def test_kill_and_gather_tasks_share_list_with_independent_progress(self):
        c = area_client()
        items = c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])
        self.assertEqual([i.stop.id for i in items.values()], [900, 901, 902])
        self.assertEqual([i.facts.progress for i in items.values()], ['0/7', '1/7', '2/7'])
        self.assertIn('Gather', items[2].action)
        self.assertEqual(c.ns.navigation.work.height, 126)
        self.assertEqual(c.ns.navigation.work.rows[2].count.text, '1/7')
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        self.assertFalse(c.ns.Completed(901))

    def test_completed_skipped_and_unaccepted_goals_are_removed_individually(self):
        c = area_client(4)
        c.ns.localProgress[901].objectives[1].have = 7
        c.ns.active[902] = None
        c.ns.db.guideSkips[c.ns.self].quests[903] = True
        c.ns.Refresh()
        items = c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])
        self.assertEqual([i.stop.id for i in items.values()], [900])
        self.assertFalse(c.ns.navigation.work.IsShown(c.ns.navigation.work))

    def test_each_shared_creature_drop_keeps_its_own_item_identity(self):
        c = area_client(2)
        for i, item in enumerate(('Boar Flank', 'Boar Snout'), 1):
            stop = c.ns.selectedRoute.stops[i]
            stop.id, stop.action, stop.itemName, stop.npcName, stop.targetName = 900, 'loot', item, 'Battleboar', 'Battleboar'
            stop.objectiveKey = 'item:' + str(i)
        c.ns.localProgress[900].objectives = c.lua.table_from([
            {'text': 'Boar Flank', 'have': 3, 'need': 8, 'kind': 'item'},
            {'text': 'Boar Snout', 'have': 1, 'need': 8, 'kind': 'item'}], recursive=True)
        c.ns.Refresh()
        items = c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])
        self.assertEqual(len(items), 2)
        self.assertEqual([i.facts.progress for i in items.values()], ['3/8', '1/8'])

    def test_phase_zone_unknown_location_and_distance_boundaries_stop_grouping(self):
        for fields in ({'kind': 't'}, {'kind': 'a'}, {'kind': 'f'}, {'mapID': 502},
                       {'x': .9}, {'unknownLocation': True}, {'action': 'escort'}):
            c = area_client()
            for key, value in fields.items(): c.ns.selectedRoute.stops[2][key] = value
            c.ns.Refresh()
            self.assertEqual(len(c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])), 1)
        c = area_client()
        c.lua.execute('C_Map.GetMapWorldSize=function() return secret,1000 end')
        c.ns.Refresh()
        self.assertEqual(len(c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])), 0)

    def test_lists_scroll_without_dropping_objectives_and_tips_move_below(self):
        c = area_client(6)
        panel = c.ns.navigation.work
        self.assertEqual(len(panel.rows), 6)
        self.assertIn('Scroll', panel.heading.text)
        panel.scroll.OnMouseWheel(panel.scroll, -2)
        self.assertEqual(panel.offset, 64)
        self.assertTrue(c.lua.eval('rawequal')(c.ns.navigation.tip.point[2], panel))
        self.assertFalse(panel.map.IsShown(panel.map))
        c.ns.navigationPreview = c.lua.table_from({'stop': c.ns.selectedRoute.stops[1]})
        c.ns.Refresh()
        self.assertFalse(panel.IsShown(panel))

    def test_cached_area_avoids_rescans_between_arrow_ticks_and_refresh_updates_it(self):
        c = area_client()
        first = c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])
        c.ns.navigation.OnUpdate(c.ns.navigation, .1)
        self.assertTrue(c.lua.eval('rawequal')(first, c.ns.AreaObjectives(c.ns.selectedRoute.stops[1])))
        c.ns.localProgress[901].objectives[1].have = 4; c.ns.Refresh()
        self.assertEqual(c.ns.navigation.work.rows[2].count.text, '4/7')

    def test_different_members_counts_stay_independent_for_the_same_objective(self):
        c = area_client(2)
        own, other = c.ns.selectedRoute.stops[1], c.ns.selectedRoute.stops[2]
        other.id, other.action, other.itemName, other.targetName, other.npcName = own.id, own.action, None, own.targetName, own.npcName
        other.objectiveKey, other.memberKey, other.forPlayer = own.objectiveKey, 'Bob-TestRealm', 'Bob'
        c.ns.members['Bob-TestRealm'] = c.lua.table_from({'active': {900: True}, 'activeRevision': 7,
            'progress': {900: {'activeRevision': 7, 'objectives': [{'text': own.targetName, 'have': 5, 'need': 7, 'kind': 'monster'}]}}}, recursive=True)
        c.ns.Refresh()
        items = c.ns.AreaObjectives(own)
        self.assertEqual([i.facts.progress for i in items.values()], ['0/7', '5/7'])
        self.assertIn('Bob', c.ns.navigation.work.rows[2].quest.text)
        c.ns.members['Bob-TestRealm'].syncPending = True; c.ns.Refresh()
        self.assertEqual(len(c.ns.AreaObjectives(own)), 1)


if __name__ == '__main__':
    unittest.main()
