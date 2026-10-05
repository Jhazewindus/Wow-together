"""Meaningful route/data checks under Lua 5.1; real beta rendering needs retesting."""
import unittest
from test_addon import Client


def quest(title='Synthetic quest', map_id=501, **extra):
    result = {'title': title, 'zone': 'Test Coast', 'mapID': map_id, 'level': 10,
              'minLevel': 5, 'side': 'Horde',
              'starts': [{'mapID': map_id, 'x': .2, 'y': .25, 'name': 'Starter', 'npc': True}],
              'objectives': [{'mapID': map_id, 'x': .6, 'y': .4, 'name': 'Target'}],
              'ends': [{'mapID': map_id, 'x': .2, 'y': .25, 'name': 'Starter', 'npc': True}]}
    result.update(extra)
    return result


def catalogue(c, quests):
    c.ns.catalogue = c.lua.table_from({'count': len(quests), 'quests': quests}, recursive=True)


def guide(c, ids=(900,), key='quest:900', focus=None):
    records = [c.ns.CatalogueRecord(i) for i in ids]
    return c.lua.table_from({'key': key, 'title': 'Synthetic route', 'records': records,
                             'target': records[0], 'focusKey': focus or c.ns.self}, recursive=True)


def route_client():
    c = Client(quests=())
    c.guide_environment(level=12)
    catalogue(c, {900: quest()})
    return c


def map_canvas(c):
    c.lua.execute(r'''
    canvas = CreateFrame('Frame')
    canvas:SetSize(1000, 800)
    MapCanvasDataProviderMixin = {
        OnAdded=function(self, map) self.owningMap = map end,
        OnMapChanged=function(self) self:RefreshAllData() end,
    }
    function WorldMapFrame:GetCanvas() return canvas end
    function WorldMapFrame:GetCanvasContainer() return self end
    WorldMapFrame.GetViewRect=false
    function WorldMapFrame:GetMapID() return self.mapID end
    function WorldMapFrame:AddDataProvider(p) self.provider = p; p:OnAdded(self) end
    function WorldMapFrame:SetMapID(id)
        self.mapID = id
        if type(self.provider) == 'table' then self.provider:OnMapChanged() end
    end
    ''')


class RouteTests(unittest.TestCase):
    def test_shipped_facts_and_uncertain_drop_sources(self):
        c = Client(quests=(), use_catalogue=True)
        q = c.ns.CatalogueQuest(97223)
        self.assertEqual(q.title, 'Bloodtalon Matriarch')
        self.assertEqual(q.minLevel, 5)
        self.assertEqual(q.starts[1].name, "Xar'Ti")
        self.assertEqual(q.starts[1].mapID, 1411)
        self.assertAlmostEqual(q.starts[1].x, .552)
        self.assertEqual(q.objectives[1].entityID, 268530)
        skull = c.ns.CatalogueQuest(827)
        self.assertEqual(skull.previousQuest, 828)
        self.assertTrue(skull.objectiveLocationsIncomplete)
        self.assertIsNone(skull.objectives)
        # Kill requirements use entity IDs, not small objective-slot numbers.
        self.assertEqual(len(c.ns.CatalogueQuest(837).objectives), 4)

    def test_level_faction_class_race_and_previous_step_checks(self):
        c = route_client()
        catalogue(c, {900: quest(classMask=1, raceMask=128, previousQuest=899),
                      899: quest('Previous step')})
        c.lua.globals().pyBand = lambda a, b: int(a) & int(b)
        c.lua.globals().pyShift = lambda a, b: int(a) << int(b)
        c.lua.execute('bit={band=function(a,b) return pyBand(a,b) end, lshift=function(a,b) return pyShift(a,b) end}')
        p = c.ns.profile
        self.assertIsNone(c.ns.CatalogueAllowed(900, p, c.ns.self)[0])
        p.classID, p.raceID = 8, 8
        self.assertFalse(c.ns.CatalogueAllowed(900, p, c.ns.self)[0])
        p.classID, p.raceID = 1, 2
        self.assertFalse(c.ns.CatalogueAllowed(900, p, c.ns.self)[0])
        p.raceID = 8
        self.assertFalse(c.ns.CatalogueAllowed(900, p, c.ns.self)[0])
        c.lua.globals().finished[899] = True
        self.assertTrue(c.ns.CatalogueAllowed(900, p, c.ns.self))
        p.level = 4
        self.assertFalse(c.ns.CatalogueAllowed(900, p, c.ns.self)[0])
        p.level, p.faction = 12, 'Alliance'
        self.assertFalse(c.ns.CatalogueAllowed(900, p, c.ns.self)[0])

    def test_class_and_race_capabilities_and_secret_ids(self):
        c = route_client()
        c.lua.execute("function UnitClass() return 'Mage', 'MAGE', 8 end; function UnitRace() return 'Troll', 'Troll', 8 end")
        c.ns.ReadProfile()
        self.assertEqual(c.ns.profile.classID, 8)
        self.assertEqual(c.ns.profile.raceID, 8)
        c.ns.SyncNow()
        messages = [msg for _, msg, _ in c.drain()]
        self.assertTrue(any(msg.endswith('|8|8') and msg.startswith('1|P|') for msg in messages))
        c.lua.execute("function UnitClass() return secret, secret, secret end; function UnitRace() return nil end")
        c.ns.ReadProfile()
        self.assertEqual(c.ns.profile.classID, 0)
        self.assertEqual(c.ns.profile.raceID, 0)

    def test_pickup_objective_and_return_are_separate_ordered_stages(self):
        c = route_client()
        route = c.ns.BuildGuideRoute(guide(c), True)
        self.assertEqual([route.stops[i].kind for i in range(1, len(route.stops)+1)], ['a', 'q', 't'])
        self.assertEqual(route.stops[1].label, 'Talk to Starter')
        self.assertIn('Target', route.stops[2].label)
        self.assertAlmostEqual(route.origin.x, .21)
        self.assertTrue(route.stops[2].planned)

    def test_partial_objectives_never_imply_immediate_turn_in(self):
        c = route_client()
        catalogue(c, {900: quest(objectives=[], objectiveLocationsIncomplete=True)})
        route = c.ns.BuildGuideRoute(guide(c), False)
        self.assertEqual(len(route.stops), 1)
        self.assertTrue(route.partial)
        c.ns.active[900] = 'Synthetic quest'
        c.ns.ReadRouteLocations()
        self.assertIsNone(c.ns.routeLocations[900])
        self.assertEqual(len(c.ns.BuildGuideRoute(guide(c), False).stops), 0)

    def test_delivery_quest_can_route_to_receiver(self):
        c = route_client()
        catalogue(c, {900: quest(objectives=[], ends=[{'mapID': 501, 'x': .8, 'y': .6, 'name': 'Receiver'}])})
        c.ns.active[900] = 'Delivery'
        c.ns.ReadRouteLocations()
        p = c.ns.routeLocations[900]
        self.assertEqual(p.kind, 'q')
        self.assertAlmostEqual(p.x, .8)

    def test_active_location_overrides_pickup_and_secrets_are_skipped(self):
        c = route_client()
        c.ns.active[900] = 'Synthetic quest'
        c.lua.execute('C_QuestLog.GetNextWaypoint=function() return 501, .71, .63 end')
        c.ns.ReadRouteLocations()
        stop = c.ns.RouteStop(c.ns.CatalogueRecord(900), c.ns.self)
        self.assertEqual(stop.kind, 'q')
        self.assertAlmostEqual(stop.x, .71)
        c.lua.execute('C_QuestLog.GetNextWaypoint=function() return 501, secret, .63 end; C_QuestLog.GetQuestsOnMap=function() return {{questID=901,x=secret,y=.2,isQuestStart=true}} end')
        c.ns.ReadRouteLocations()
        self.assertAlmostEqual(c.ns.routeLocations[900].x, .6)  # Published objective fallback.
        self.assertIsNone(c.ns.routeLocations[901])

    def test_routes_stop_at_cross_zone_stage_and_exclude_foreign_blocks(self):
        c = route_client()
        catalogue(c, {900: quest(objectives=[{'mapID': 502, 'x': .5, 'y': .5, 'name': 'Other zone'}]),
                      901: quest('Other zone pickup', map_id=502,
                                 ends=[{'mapID': 501, 'x': .3, 'y': .4, 'name': 'Return'}])})
        route = c.ns.BuildGuideRoute(guide(c, (900, 901), key='zone-route:501'), False)
        self.assertEqual(route.mapID, 501)
        self.assertEqual(len(route.stops), 1)
        self.assertEqual(route.otherMaps, 5)

    def test_native_canvas_geometry_resizing_map_changes_and_shared_pin(self):
        c = route_client()
        map_canvas(c)
        self.assertTrue(c.ns.ShowGuideOnMap(guide(c)))
        provider = c.ns.routeProvider
        self.assertEqual(c.ns.routeStats.lines, 3)
        self.assertEqual(c.ns.routeStats.pins, 2)  # Pickup and return share a pin.
        self.assertEqual(provider.pins[1].number.text, '1/3')
        self.assertAlmostEqual(provider.lines[1].startPoint[3], 210)
        self.assertAlmostEqual(provider.lines[1].endPoint[3], 200)
        self.assertAlmostEqual(provider.lines[1].endPoint[4], -200)
        canvas = c.lua.globals().canvas
        canvas.SetSize(canvas, 2000, 1600)
        provider.OnCanvasSizeChanged(provider)
        c.drain()
        self.assertAlmostEqual(provider.lines[1].endPoint[3], 400)
        self.assertAlmostEqual(provider.lines[1].endPoint[4], -400)
        world = c.lua.globals().WorldMapFrame
        world.SetMapID(world, 502)
        self.assertEqual(c.ns.routeStats.lines, 0)
        self.assertFalse(provider.pins[1].IsShown(provider.pins[1]))
        world.SetMapID(world, 501)
        self.assertEqual(c.ns.routeStats.lines, 3)
        c.ns.Diagnostics()
        self.assertIn('Rendered route pins: 2; lines: 3', c.ns.diagnosticsText.text)

    def test_route_markers_follow_acceptance_turn_in_and_completion_without_waypoint(self):
        c = route_client()
        map_canvas(c)
        c.ns.ShowGuideOnMap(guide(c))
        c.lua.execute("entries={{questID=900,title='Accepted quest',isHeader=false}}; C_QuestLog.GetNextWaypoint=function() return 501,.71,.63 end")
        c.ns.SyncNow(False)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'q')
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .71)
        self.assertIsNone(c.lua.globals().waypoint)
        c.lua.execute('C_QuestLog.IsComplete=function() return true end; C_QuestLog.GetNextWaypoint=function() return 501,.2,.25 end')
        c.ns.SyncNow(False)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 't')
        self.assertEqual(len(c.ns.selectedRoute.stops), 1)
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .2)
        c.lua.execute('entries={}; finished[900]=true')
        c.ns.SyncNow(False)
        # A detected party member still has to confirm completion.
        self.assertIsNotNone(c.ns.routeSelection)
        c.receive('1|S|1|1|1|')
        c.receive('1|C|2|1|1|900')
        c.receive('1|K|2|1|1|900')
        self.assertIsNone(c.ns.selectedRoute)
        self.assertEqual(c.ns.routeStats.lines, 0)

    def test_combat_retains_route_progress_and_defers_clearing_without_waypoint(self):
        c = route_client()
        map_canvas(c)
        c.ns.ShowGuideOnMap(guide(c))
        c.lua.execute("combat=true; entries={{questID=900,title='Accepted quest',isHeader=false}}; C_QuestLog.GetNextWaypoint=function() return 501,.71,.63 end")
        c.ns.SyncNow(False)
        self.assertIsNone(c.lua.globals().waypoint)
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .71)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .71)
        self.assertIsNone(c.lua.globals().waypoint)
        c.lua.globals().combat = True
        c.ns.ClearRoute()
        self.assertIsNone(c.ns.routeSelection)
        self.assertTrue(c.ns.routeClearPending)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertEqual(c.ns.routeStats.pins, 0)

    def test_route_packets_require_matching_active_revision_and_roster(self):
        c = route_client()
        c.receive('1|R|2|900|501|71000|63000|q')
        self.assertIsNone(c.ns.RoutePointForMember('Bob-TestRealm', 900))
        c.receive('1|S|2|1|1|900')
        p = c.ns.RoutePointForMember('Bob-TestRealm', 900)
        self.assertAlmostEqual(p.x, .71)
        c.receive('1|R|1|900|501|10000|10000|q')
        self.assertAlmostEqual(c.ns.RoutePointForMember('Bob-TestRealm', 900).x, .71)
        c.receive('1|R|2|900|501|100001|10000|q')
        self.assertAlmostEqual(c.ns.RoutePointForMember('Bob-TestRealm', 900).x, .71)
        c.receive('1|R|2|900|501|10000|10000|q', sender='Mallory-TestRealm')
        self.assertIsNone(c.ns.members['Mallory-TestRealm'])
        c.receive('1|R|2|900|0|0|0|x')
        self.assertIsNone(c.ns.RoutePointForMember('Bob-TestRealm', 900))

    def test_removed_local_destinations_send_tombstones(self):
        c = route_client()
        catalogue(c, {})
        c.lua.execute("entries={{questID=900,title='Live only',isHeader=false}}; C_QuestLog.GetNextWaypoint=function() return 501,.71,.63 end")
        c.ns.SyncNow()
        messages = [msg for _, msg, _ in c.drain()]
        self.assertTrue(any(msg.startswith('1|R|') and msg.endswith('|q') for msg in messages))
        c.lua.execute('C_QuestLog.GetNextWaypoint=nil')
        c.ns.SyncNow(False)
        messages = [msg for _, msg, _ in c.drain()]
        self.assertTrue(any(msg.startswith('1|R|') and msg.endswith('|900|0|0|0|x') for msg in messages))

    def test_library_search_details_and_selected_zone_history_scope(self):
        c = route_client()
        catalogue(c, {900: quest(), 901: quest('Hill story', map_id=502),
                      902: {'title': 'No coordinates', 'zone': 'Test Coast', 'mapID': 501}})
        c.ns.librarySearch = 'hill'
        self.assertEqual(c.ns.LibraryItems()[1].id, 901)
        c.ns.ShowQuestDetails(902)
        self.assertIn('no quest-giver coordinates', c.ns.questDetails.body.text)
        self.assertFalse(c.ns.CatalogueScopeIDs()[901] or False)
        c.ns.OpenLibraryZone('map:502', 502)
        self.assertTrue(c.ns.CatalogueScopeIDs()[901])
        c.ns.SyncNow()
        messages = [msg for _, msg, _ in c.drain()]
        self.assertIn('1|Z|502', messages)
        self.assertTrue(any(msg.startswith('1|K|') and '901' in msg.split('|')[-1].split(',') for msg in messages))
        c.ns.libraryMapID = None
        c.receive('1|Z|502')
        self.assertTrue(c.ns.CatalogueScopeIDs()[901])
        c.receive('1|Z|0')
        self.assertIsNone(c.ns.CatalogueScopeIDs()[901])

    def test_remote_pending_history_cannot_create_a_pickup_route(self):
        c = route_client()
        c.receive('1|P|5|2|501|Test Coast')
        c.receive('1|S|1|1|1|')
        record = c.ns.CatalogueRecord(900)
        self.assertIsNone(c.ns.RouteStop(record, 'Bob-TestRealm'))
        c.receive('1|C|1|1|1|')
        c.receive('1|K|1|1|1|900')
        self.assertEqual(c.ns.RouteStop(record, 'Bob-TestRealm').kind, 'a')

    def test_published_chain_advances_from_completion_history(self):
        c = route_client()
        catalogue(c, {900: quest(seriesRoot=900, seriesName='Synthetic story', series=[900, 901], seriesPosition=1),
                      901: quest('Next step', previousQuest=900, seriesRoot=900,
                                 seriesName='Synthetic story', series=[900, 901], seriesPosition=2)})
        first = c.ns.GuideChoices()[1]
        self.assertEqual(first.kind, 'Questline')
        self.assertEqual(first.target.id, 900)
        c.lua.globals().finished[900] = True
        second = c.ns.GuideChoices()[1]
        self.assertEqual(second.kind, 'Questline')
        self.assertEqual(second.target.id, 901)
        c.lua.globals().finished[901] = True
        self.assertEqual(len(c.ns.GuideChoices()), 0)

    def test_two_clients_agree_on_lower_level_focus_with_real_zone_data(self):
        clients = [Client(name='Barry', peer='Shamoone', quests=(), use_catalogue=True),
                   Client(name='Shamoone', peer='Barry', quests=(), use_catalogue=True)]
        for c, level, peer_level in zip(clients, (12, 22), (22, 12)):
            c.guide_environment(level)
            c.lua.execute("C_Map.GetBestMapForUnit=function() return 1411 end; C_Map.GetMapInfo=function() return {name='Durotar'} end")
            c.ns.ReadGuide()
            sender = c.lua.globals().peer + '-TestRealm'
            c.receive('1|S|1|1|1|', sender)
            c.receive(f'1|P|{peer_level}|2|1411|Durotar', sender)
            c.receive('1|C|1|1|1|', sender)
            ids = sorted(int(i) for i in c.ns.CatalogueScopeIDs().keys())
            parts = [ids[i:i+18] for i in range(0, len(ids), 18)]
            for index, part in enumerate(parts, 1):
                c.receive(f'1|K|1|{index}|{len(parts)}|' + ','.join(map(str, part)), sender)
        choices = [c.ns.GuideChoices()[1] for c in clients]
        self.assertEqual(choices[0].target.id, choices[1].target.id)
        self.assertEqual(choices[0].focusKey, 'Barry-TestRealm')
        self.assertEqual(choices[1].focusKey, 'Barry-TestRealm')
        self.assertTrue(all(g.catchup for g in choices))
        self.assertTrue(all(g.hasPoint for g in choices))
        self.assertTrue(all(g.nextStop.label.startswith('Talk to ') for g in choices))

    def test_equal_levels_choose_the_same_character_focus_on_both_clients(self):
        clients = [Client(name='Alice', peer='Bob', quests=()), Client(name='Bob', peer='Alice', quests=())]
        for c in clients:
            c.guide_environment(level=12)
            catalogue(c, {900: quest()})
            sender = c.lua.globals().peer + '-TestRealm'
            c.receive('1|S|1|1|1|', sender)
            c.receive('1|P|12|2|501|Test Coast', sender)
            c.receive('1|C|1|1|1|', sender)
            c.receive('1|K|1|1|1|900', sender)
        self.assertTrue(all(c.ns.GuideChoices()[1].focusKey == 'Alice-TestRealm' for c in clients))


if __name__ == '__main__':
    unittest.main()
