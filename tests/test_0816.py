"""Readable anonymous travel points; host geometry does not verify beta terrain."""
import unittest

from test_addon import Client
from test_063 import guide_client
from test_068 import maps
from test_070 import network_client, point
from test_routes import guide


REPORTED = 'CONVERGENCE_C1413_540_266'


def junction_client(name=None):
    c = guide_client(2)
    maps(c)
    junction = c.ns.travelData.nodes[REPORTED]
    if name is not None:
        junction.name = name
    c.ns.travelData = c.lua.table_from({'nodes': {
        REPORTED: junction,
        'B': {'mapID': 502, 'x': .1, 'y': .37, 'name': 'West gate'},
    }, 'edges': [{'from': REPORTED, 'to': 'B', 'seconds': 0, 'method': 'walk'}],
        'factors': {}}, recursive=True)
    c.lua.execute('''
      bounds[1413]={x=0,width=1000}
      playerMap,playerX,playerY=1413,.3,.2659
      C_Map.GetMapInfo=function(id)
        return {name=id==1413 and 'The Barrens' or 'Test Hills'}
      end
    ''')
    goal = c.lua.table_from({'id': 900, 'kind': 'a', 'title': 'Remote quest',
        'mapID': 502, 'x': .2, 'y': .37, 'label': 'Accept Remote quest'})
    c.ns.ActivateRoute(guide(c, (900,)), c.lua.table_from({'mapID': 502, 'stops': [goal]}, recursive=True))
    c.ns.UpdateNavigation()
    return c, goal


class WaypointDirectionsTests(unittest.TestCase):
    def test_reported_point_uses_real_coordinates_in_arrow_map_and_tooltip(self):
        c, goal = junction_client()
        stop = c.ns.navigation.state.stop
        expected = 'Go to waypoint — The Barrens (54.0, 26.6)'
        self.assertEqual(stop.label, expected)
        self.assertEqual(c.ns.navigation.status.text, expected)
        self.assertIn(expected, c.ns.GuideStepDescription(stop))
        self.assertIn('Travel towards Test Hills.', c.ns.navigation.context.text)
        self.assertIn('this waypoint', c.ns.navigation.context.text)
        self.assertNotIn('crossing', c.ns.navigation.context.text)
        self.assertAlmostEqual(stop.x, .5402)
        self.assertAlmostEqual(stop.y, .2659)
        self.assertEqual([(s.fromID, s.toID) for s in c.ns.travelPath.legs.values()],
            [('START', REPORTED), (REPORTED, 'B'), ('B', 'GOAL')])
        c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 1413)
        c.ns.DrawRoute()
        pin = next(p for p in c.ns.routeProvider.pins.values() if p.stop.kind == 'travel')
        self.assertEqual(pin.stop.label, expected)
        c.lua.execute('''
          tooltipLines={}
          GameTooltip=CreateFrame('Frame')
          function GameTooltip:AddLine(text) tooltipLines[#tooltipLines+1]=text end
        ''')
        pin.OnEnter(pin)
        lines = '\n'.join(c.lua.globals().tooltipLines.values())
        self.assertIn(expected, lines)
        self.assertNotIn('Convergence', lines)
        # Arrival advances only the travel leg, never the retained quest order.
        c.lua.execute('playerX=.5402;playerY=.2659')
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.travelPath.cursor, 2)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, goal.id)
        self.assertFalse(c.ns.Completed(goal.id))
        self.assertIsNone(c.lua.globals().waypoint)

    def test_every_shipped_anonymous_junction_has_readable_zone_and_percent_coordinates(self):
        c = network_client()
        # This fixture gives every zone the same artificial world origin and
        # joins it to a synthetic map by a zero-length walk. Isolate naming
        # from real barrier geography; terrain projection has its own checks.
        c.ns.travelTerrainData = c.lua.table_from({'maps': {}}, recursive=True)
        shipped = Client(quests=()).ns.travelData.nodes
        c.lua.execute('C_Map.GetMapInfo=nil')
        points = [(key, p) for key, p in shipped.items() if key.startswith('CONVERGENCE_')]
        self.assertEqual(len(points), 30)
        for key, junction in points:
            with self.subTest(node=key):
                # Retain source facts; synthetic attachment makes each point the
                # first leg without claiming a real terrain/pathing reproduction.
                values = dict(junction.items())
                c.ns.travelData = c.lua.table_from({'nodes': {key: values,
                    'B': {'mapID': 502, 'x': .1, 'y': .37}},
                    'edges': [{'from': key, 'to': 'B', 'seconds': 0, 'method': 'walk'}],
                    'factors': {}}, recursive=True)
                c.lua.globals().bounds[junction.mapID] = c.lua.table_from({'x': 0, 'width': 1000})
                path = c.ns.FindTravelPath(point(c, junction.mapID, 0, 0), point(c, 502, .2), False)
                leg = path.legs[1]
                self.assertTrue(leg.waypoint)
                self.assertIn('waypoint — ', leg.name)
                self.assertNotIn('Convergence', leg.name)
                self.assertNotIn(key, leg.name)
                self.assertNotIn('_', leg.name)
                self.assertIn(f'({junction.x * 100:.1f}, {junction.y * 100:.1f})', leg.name)
                self.assertEqual(leg.toID, key)
                self.assertEqual(leg.to.x, junction.x)

    def test_readable_junction_landmark_name_is_preserved(self):
        c, _ = junction_client('Named road junction')
        self.assertEqual(c.ns.navigation.state.stop.label, 'Head to Named road junction')
        self.assertIsNone(c.ns.navigation.state.stop.travelLeg.waypoint)

    def test_unavailable_or_restricted_zone_name_uses_public_container_fallback(self):
        for native in ('nil', 'secret', '{name=secret}', 'error("uncached")'):
            with self.subTest(native=native):
                c, goal = junction_client()
                c.lua.execute('C_Map.GetMapInfo=function() return ' + native + ' end')
                c.ns.ResetTravelPath()
                stop = c.ns.TravelNetworkDestination(goal)
                self.assertEqual(stop.label, 'Go to waypoint — The Barrens (54.0, 26.6)')
        c, goal = junction_client()
        junction = c.ns.travelData.nodes[REPORTED]
        junction.name, junction.container = c.lua.globals().secret, None
        c.lua.execute('C_Map.GetMapInfo=nil')
        c.ns.ResetTravelPath()
        self.assertEqual(c.ns.TravelNetworkDestination(goal).label,
            'Go to waypoint — Map 1413 (54.0, 26.6)')

    def test_diagnostics_keep_leg_identity_and_final_goal_without_raw_ids_in_directions(self):
        c, _ = junction_client()
        output = []
        c.ns.TravelDiagnostics(output.append)
        self.assertIn('START -> ' + REPORTED, '\n'.join(output))
        self.assertIn('target The Barrens (54.0, 26.6)', '\n'.join(output))
        self.assertIn('Travel goal: Remote quest (900); Test Hills (20.0, 37.0).', output)
        self.assertNotIn(REPORTED, c.ns.navigation.status.text)
        c.ns.ClearRoute()
        output.clear()
        c.ns.TravelDiagnostics(output.append)
        self.assertFalse(any(line.startswith('Travel leg:') for line in output))


if __name__ == '__main__':
    unittest.main()
