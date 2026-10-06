"""Behavioral regressions for resize cost, eligibility, invitations and NPC arrival."""
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest, route_client
from test_050 import world_positions
from test_navigation import navigator
from import_wowhead import prerequisite_facts


def party_client(name='Alice', peer='Bob', ids=(900,)):
    c = Client(name=name, peer=peer, quests=ids)
    c.guide_environment(level=12)
    catalogue(c, {900: quest(), 901: quest('Other route')})
    map_canvas(c)
    c.ns.ReadRouteLocations()
    c.receive('1|S|1|1|1|900', sender=peer+'-TestRealm')
    c.receive('1|P|12|2|501|Test Coast', sender=peer+'-TestRealm')
    c.receive('1|R|1|900|501|60000|40000|q', sender=peer+'-TestRealm')
    return c


class ResizeTests(unittest.TestCase):
    def test_only_one_owned_menu_remains_open_and_choices_still_apply(self):
        c = Client(default_guide=True)
        view, level = c.ns.ui.viewChoice, c.ns.ui.guideLevel
        view.OnClick()
        self.assertTrue(view.menu.IsShown(view.menu))
        level.OnClick()
        self.assertFalse(view.menu.IsShown(view.menu))
        self.assertTrue(level.menu.IsShown(level.menu))
        level.options['11-20'].OnClick()
        self.assertEqual(c.ns.guideLevel, '11-20')
        self.assertFalse(level.menu.IsShown(level.menu))
        c.ns.settings.section.OnClick()
        view.OnClick()
        self.assertFalse(c.ns.settings.section.menu.IsShown(c.ns.settings.section.menu))

    def test_drag_reflows_geometry_without_rebuilding_plans_per_pixel(self):
        c = Client()
        c.drain()
        c.lua.execute('''
        renders=0; originalRender=...
        nsRender=function() renders=renders+1; originalRender() end
        ''', c.ns.Render)
        c.ns.Render = c.lua.globals().nsRender
        c.lua.execute('''
        function windowLeft() return 180 end
        function windowTop() return 760 end
        ''')
        c.ns.window.GetLeft = c.lua.globals().windowLeft
        c.ns.window.GetTop = c.lua.globals().windowTop
        grip, window = c.ns.ui.resizeGrip, c.ns.window
        grip.OnMouseDown(grip, 'LeftButton')
        self.assertEqual(window.point[1], 'TOPLEFT')
        self.assertEqual((window.point[4], window.point[5]), (180, 760))
        for width in range(860, 1061, 5):
            window.SetSize(window, width, 780)
            window.OnSizeChanged(window, width, 780)
            c.ns.Refresh()  # Even incoming sync updates defer the full render.
        self.assertEqual(c.lua.globals().renders, 0)
        self.assertEqual(c.ns.ui.cards[1].width, 986)
        grip.OnMouseUp(grip, 'LeftButton')
        self.assertEqual(c.lua.globals().renders, 1)
        self.assertEqual(c.ns.db.windowSize.width, 1060)
        self.assertFalse(c.ns.ui.resizing)

    def test_programmatic_resize_changes_coalesce_into_one_render(self):
        c = Client()
        c.drain()
        c.lua.execute('renders=0; originalRender=...; function countedRender() renders=renders+1; originalRender() end', c.ns.Render)
        c.ns.Render = c.lua.globals().countedRender
        for width in range(860, 981, 5):
            c.ns.window.SetSize(c.ns.window, width, 750)
            c.ns.window.OnSizeChanged(c.ns.window, width, 750)
        self.assertEqual(c.lua.globals().renders, 0)
        self.assertEqual(len(c.lua.globals().timers), 1)
        c.drain()
        self.assertEqual(c.lua.globals().renders, 1)


class EligibilityTests(unittest.TestCase):
    def test_real_burning_blade_requires_a_completed_vile_familiars_variant(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=4)
        c.ns.profile.mapID = 1411
        q = c.ns.CatalogueQuest(794)
        self.assertEqual(list(q.prerequisiteAny.values()), [792, 1499])
        self.assertFalse(c.ns.CatalogueAllowed(794, c.ns.profile, c.ns.self)[0])
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(794), c.ns.self)), 0)
        self.assertTrue(c.ns.CatalogueScopeIDs()[792])
        self.assertTrue(c.ns.CatalogueScopeIDs()[1499])
        c.lua.globals().finished[1499] = True
        self.assertTrue(c.ns.CatalogueAllowed(794, c.ns.profile, c.ns.self))

    def test_variant_parser_preserves_or_gate_without_inventing_a_linear_chain(self):
        page = '<table class="series"><tr><a href="/forever/quest=10">Variants</a><a href="/forever/quest=11">Variants</a></tr><tr><b>Current</b></tr></table>'
        self.assertEqual(prerequisite_facts(page, 12)['prerequisiteAny'], [10, 11])
        ambiguous = page.replace('>Variants</a><', '>Different</a><', 1)
        facts = prerequisite_facts(ambiguous, 12)
        self.assertTrue(facts['prerequisitesUnverified'])
        self.assertNotIn('previousQuest', facts)
        self.assertNotIn('prerequisiteAny', facts)

    def test_unknown_peer_history_does_not_satisfy_either_variant(self):
        c = route_client()
        catalogue(c, {900: quest(prerequisiteAny=[889, 890])})
        c.receive('1|S|5|1|1|')
        c.receive('1|P|12|2|501|Test Coast')
        key = 'Bob-TestRealm'
        self.assertIsNone(c.ns.CatalogueAllowed(900, c.ns.members[key].profile, key)[0])
        c.receive('1|C|5|1|1|')
        c.receive('1|K|5|1|1|889,890')
        self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.members[key].profile, key)[0])
        c.receive('1|C|6|1|1|889')
        self.assertTrue(c.ns.CatalogueAllowed(900, c.ns.members[key].profile, key))

    def test_unclear_branch_and_missing_faction_cannot_be_new_pickups(self):
        c = route_client()
        catalogue(c, {900: quest(prerequisitesUnverified=True), 901: quest('Unknown faction', side=None)})
        self.assertIsNone(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(900), c.ns.self)), 0)
        self.assertIsNone(c.ns.CatalogueAllowed(901, c.ns.profile, c.ns.self)[0])
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)), 0)
        c.ns.offered[900] = True  # An actual, currently open NPC offer is evidence.
        self.assertEqual(c.ns.RouteStages(c.ns.CatalogueRecord(900), c.ns.self)[1].kind, 'a')

    def test_list_only_quest_requires_details_or_a_live_offer(self):
        c = route_client()
        catalogue(c, {900: quest()})
        c.ns.catalogue.detailSource = 'Synthetic source'
        self.assertIsNone(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(900), c.ns.self)), 0)
        c.ns.offered[900] = True
        self.assertEqual(c.ns.RouteStages(c.ns.CatalogueRecord(900), c.ns.self)[1].kind, 'a')
        c.ns.offered[900] = None
        c.ns.CatalogueQuest(900).prerequisitesRead = True
        self.assertTrue(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self))

    def test_horde_guides_and_library_exclude_alliance_only_quests(self):
        c = route_client()
        catalogue(c, {900: quest('Horde route'), 901: quest('Alliance route', side='Alliance', xp=100000),
                      902: quest('Neutral in Alliance starter zone', map_id=1429, side='Both', xp=100000)})
        c.lua.globals().grouped = False
        c.unit_names({'player': ['Alice', 'TestRealm']})
        for choice in c.ns.GuideChoices().values():
            self.assertNotEqual(choice.target.id, 901)
            self.assertNotEqual(choice.mapID, 1429)
            route = c.ns.BuildGuideRoute(choice, False)
            self.assertNotIn(901, [s.id for s in route.stops.values()])
        c.ns.librarySearch = 'Alliance'
        self.assertEqual({i.id for i in c.ns.LibraryItems().values()}, {902})  # Neutral manual browsing remains possible.

    def test_adjacent_data_and_native_links_reject_distant_or_unlinked_zones(self):
        c = route_client()
        world_positions(c)
        point = c.lua.table_from({'mapID': 502, 'x': .2, 'y': .3})
        self.assertTrue(c.ns.DiscoveryZoneAllowed(502, point))
        self.assertFalse(c.ns.DiscoveryZoneAllowed(503, c.lua.table_from({'mapID': 503, 'x': .2, 'y': .3})))
        c.lua.globals().mapOffset[502] = 20000
        self.assertFalse(c.ns.DiscoveryZoneAllowed(502, point))
        c.lua.globals().mapOffset[502] = 400
        c.lua.globals().separateContinent = True
        self.assertFalse(c.ns.DiscoveryZoneAllowed(502, point))
        c.ns.profile.mapID = 1411
        c.lua.globals().C_Map.GetWorldPosFromMapPos = None
        self.assertTrue(c.ns.DiscoveryZoneAllowed(1413, c.lua.table_from({'mapID': 1413, 'x': .2, 'y': .3})))
        self.assertFalse(c.ns.DiscoveryZoneAllowed(1429, point))

    def test_secret_and_transport_links_do_not_become_adjacent_zones(self):
        c = route_client()
        c.nearby_zone_link()
        c.lua.execute("C_Map.GetMapLinksForMap=function() return {{linkedUiMapID=secret,atlasName='zone-link'},{linkedUiMapID=502,atlasName='boat-link'}} end")
        self.assertIsNone(c.ns.NearbyZoneMaps(501)[502])

    def test_ready_native_flag_uses_receiver_even_when_waypoint_still_points_at_mob(self):
        c = route_client()
        c.ns.active[900] = 'Synthetic quest'
        c.lua.execute('C_QuestLog.IsComplete=function() return true end; C_QuestLog.GetNextWaypoint=function() return 501,.6,.4 end')
        c.ns.ReadRouteLocations()
        stop = c.ns.RouteStop(c.ns.CatalogueRecord(900), c.ns.self)
        self.assertEqual(stop.kind, 't')
        self.assertAlmostEqual(stop.x, .2)
        self.assertEqual(stop.npcName, 'Starter')


class PartyRouteTests(unittest.TestCase):
    def test_two_clients_exchange_real_start_packets_and_follow_without_echoing_invites(self):
        a, b = party_client(), party_client('Bob', 'Alice')
        a.ns.SyncNow(True); b.ns.SyncNow(True)
        for _ in range(4):
            for _, packet, _ in a.drain(): b.receive(packet, sender='Alice-TestRealm')
            for _, packet, _ in b.drain(): a.receive(packet, sender='Bob-TestRealm')
        self.assertTrue(a.ns.StartPartyRoute(guide(a)))
        packets = a.drain()
        for _, packet, _ in packets: b.receive(packet, sender='Alice-TestRealm')
        self.assertTrue(b.ns.partyRoutePrompt.IsShown(b.ns.partyRoutePrompt))
        self.assertIsNone(b.ns.routeSelection)
        b.ns.partyRoutePrompt.follow.OnClick()
        self.assertEqual(b.ns.selectedRoute.stops[1].id, 900)
        self.assertFalse(any(p.startswith('1|V|') for _, p, _ in b.drain()))

    def test_show_route_is_local_and_start_route_sends_selected_future_steps(self):
        c = party_client()
        catalogue(c, {900: quest(), 901: quest('Later step', previousQuest=900)})
        selected = guide(c, (900, 901), key='series:900')
        c.ns.ShowGuideOnMap(selected)
        self.assertFalse(any('|V|' in m for _, m, _ in c.drain()))
        self.assertTrue(c.ns.StartPartyRoute(selected))
        packets = [m for _, m, _ in c.drain() if m.startswith('1|V|')]
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].split('|')[-1], '900,901')

    def test_prompt_keeps_old_route_until_follow_and_uses_each_members_progress(self):
        c = party_client(name='Bob', peer='Alice')
        c.ns.ShowGuideOnMap(guide(c, ids=(901,), key='quest:901'))
        previous = c.ns.routeSelection.key
        c.receive('1|V|1|1|1|current|501|900|900', sender='Alice-TestRealm')
        prompt = c.ns.partyRoutePrompt
        self.assertTrue(prompt.IsShown(prompt))
        self.assertEqual(c.ns.routeSelection.key, previous)
        prompt.keep.OnClick()
        self.assertEqual(c.ns.routeSelection.key, previous)
        c.receive('1|V|2|1|1|current|501|900|900', sender='Alice-TestRealm')
        c.lua.execute('C_QuestLog.IsComplete=function(id) return id==900 end')
        c.ns.ReadRouteLocations()
        prompt.follow.OnClick()
        self.assertFalse(prompt.IsShown(prompt))
        stops = list(c.ns.selectedRoute.stops.values())
        self.assertEqual(stops[0].kind, 't')
        self.assertTrue(any(s.kind == 'q' and s.forPlayer == c.ns.MemberLabel('Alice-TestRealm') for s in stops))
        self.assertFalse(any(m.startswith('1|V|') for _, m, _ in c.drain()))

    def test_multipart_out_of_order_is_atomic_and_duplicates_do_not_change_route(self):
        c = party_client()
        c.receive('1|V|5|2|2|normal|501|900|908')
        self.assertIsNone(c.ns.partyRoutePrompt)
        c.receive('1|V|5|1|2|normal|501|900|900,901,902,903,904,905,906,907')
        self.assertEqual(len(c.ns.partyRoutePrompt.invite.ids), 9)
        before = c.ns.syncStats.ignored
        c.receive('1|V|5|1|1|normal|501|901|901')
        self.assertGreater(c.ns.syncStats.ignored, before)
        self.assertEqual(c.ns.partyRoutePrompt.invite.target, 900)
        c.receive('1|H')  # A reloaded peer may restart its invitation counter.
        c.receive('1|V|1|1|1|normal|501|901|901')
        self.assertEqual(c.ns.partyRoutePrompt.invite.target, 901)

    def test_invalid_packets_outsiders_and_departed_senders_cannot_replace_route(self):
        c = party_client()
        for packet in ('1|V|0|1|1|normal|501|900|900', '1|V|1|1|4|normal|501|900|900',
                       '1|V|1|1|1|wrong|501|900|900', '1|V|1|1|1|normal|501|900|900,900',
                       '1|V|1|1|1|normal|501|900|0900', '1|V|1|1|1|normal|501|900|901'):
            c.receive(packet)
        c.receive('1|V|2|1|1|normal|501|900|900', sender='Mallory-TestRealm')
        self.assertIsNone(c.ns.partyRoutePrompt)
        c.receive('1|V|3|1|1|normal|501|900|900')
        invite = c.ns.partyRoutePrompt.invite
        c.lua.globals().peer = None
        c.ns.UpdateRoster()
        self.assertFalse(c.ns.partyRoutePrompt.IsShown(c.ns.partyRoutePrompt))
        self.assertFalse(c.ns.FollowPartyRoute(invite))

    def test_invitation_and_waypoint_wait_until_combat_ends(self):
        c = party_client()
        c.lua.globals().combat = True
        c.receive('1|V|1|1|1|current|501|900|900')
        self.assertIsNone(c.ns.partyRoutePrompt)
        self.assertIsNone(c.lua.globals().waypoint)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertTrue(c.ns.partyRoutePrompt.IsShown(c.ns.partyRoutePrompt))

    def test_follow_waits_for_prerequisites_then_retries_only_after_data_changes(self):
        c = party_client()
        c.lua.globals().entries = c.lua.table()
        c.ns.ReadQuests()
        catalogue(c, {900: quest(previousQuest=899)})
        c.receive('1|S|5|1|1|')
        c.receive('1|C|5|1|1|')
        c.receive('1|K|5|1|1|899,900')
        c.receive('1|V|1|1|1|normal|501|900|900')
        c.ns.partyRoutePrompt.follow.OnClick()
        self.assertIsNone(c.lua.globals().waypoint)
        self.assertIsNotNone(c.ns.waitingPartyRoute)
        c.drain()  # No timer polling loop while the earlier quest is unfinished.
        self.assertIsNone(c.lua.globals().waypoint)
        c.lua.globals().finished[899] = True
        c.ns.handlers.QUEST_TURNED_IN()
        c.drain()
        self.assertIsNone(c.ns.waitingPartyRoute)
        self.assertIsNone(c.lua.globals().waypoint)
        self.assertEqual(c.ns.selectedRoute.mapID, 501)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'a')

    def test_solo_start_and_main_guide_start_button(self):
        c = party_client()
        c.lua.globals().grouped = False
        c.unit_names({'player': ['Alice', 'TestRealm']})
        c.ns.SetOption('currentQuestsFirst', True)
        c.ns.SetFilter('all')
        card = c.ns.ui.cards[1]
        self.assertEqual(card.detailsButton.caption.text, 'Start route')
        card.detailsButton.OnClick()
        if c.ns.startGuidePrompt is not None:
            self.assertTrue(c.ns.startGuidePrompt.IsShown(c.ns.startGuidePrompt))
            c.ns.startGuidePrompt.selected.OnClick()
        self.assertIn('started for you', c.ns.partyRouteStatus)
        self.assertFalse(any(m.startswith('1|V|') for _, m, _ in c.drain()))

    def test_start_retains_navigation_if_map_frame_cannot_load(self):
        c = party_client()
        c.lua.globals().WorldMapFrame = None
        self.assertTrue(c.ns.StartPartyRoute(guide(c)))
        self.assertIsNotNone(c.ns.selectedRoute)
        self.assertTrue(any(m.startswith('1|V|') for _, m, _ in c.drain()))

    def test_invitation_with_missing_live_record_waits_for_metadata(self):
        c = party_client()
        catalogue(c, {})
        c.receive('1|V|1|1|1|normal|501|999|999')
        c.ns.partyRoutePrompt.follow.OnClick()
        self.assertIsNotNone(c.ns.waitingPartyRoute)
        c.receive('1|G|999|0|501|21000|37000|5|n|Live Quest||Live NPC')
        c.drain()
        self.assertIsNone(c.ns.waitingPartyRoute)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 999)


class ArrivalTests(unittest.TestCase):
    def test_arrival_draws_down_arrow_and_accept_instruction_without_auto_completion(self):
        c = navigator(.21, .37)
        stop = c.ns.selectedRoute.stops[1]
        stop.npcName = 'Receiver'
        c.lua.execute('function AcceptQuest() error("unexpected acceptance") end')
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.status.text, 'Accept from Receiver')
        self.assertEqual(c.ns.navigation.title.text, stop.title)
        self.assertFalse(c.ns.navigation.symbol.IsShown(c.ns.navigation.symbol))
        line = c.ns.navigation.icon.lines[1]
        self.assertTrue(line.IsShown(line))
        self.assertAlmostEqual(line.startPoint[4], -21)
        self.assertIsNotNone(c.ns.routeSelection)
        self.assertFalse(c.ns.Completed(900))

    def test_friendly_nameplate_has_quest_names_and_down_pointer(self):
        c = party_client()
        catalogue(c, {900: quest(ends=[{'mapID': 501, 'x': .2, 'y': .25, 'name': 'Receiver', 'entityID': 100, 'npc': True}])})
        c.lua.execute('''
        C_QuestLog.IsComplete=function() return true end
        plate=CreateFrame('Frame'); plate.namePlateUnitToken='nameplate1'
        C_NamePlate={GetNamePlates=function() return {plate} end, GetNamePlateForUnit=function() return plate end}
        function UnitGUID() return 'Creature-0-1-1-1-100-ABC' end
        ''')
        c.ns.ReadRouteLocations(); c.ns.UpdateNPCHints()
        hint = c.ns.npcHints['nameplate1']
        self.assertEqual(hint.questNames.text, c.ns.QuestTitle(900))
        self.assertTrue(hint.pointer.IsShown(hint.pointer))
        self.assertFalse(hint.icon.IsShown(hint.icon))
        c.lua.globals().combat = True
        c.ns.handlers.PLAYER_REGEN_DISABLED()
        self.assertFalse(hint.IsShown(hint))


if __name__ == '__main__':
    unittest.main()
