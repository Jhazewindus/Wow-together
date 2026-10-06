"""Nearby pickups must improve the current trip without bypassing pickup gates."""
import unittest

from test_addon import Client
from test_routes import catalogue, map_canvas, quest
from test_050 import nearby, solo


def local_client():
    c = solo()
    c.ns.db.config.currentQuestsFirst = True
    catalogue(c, {900: nearby('Our current work'), 901: nearby('Nearby pickup'),
                  902: nearby('Already ready')})
    c.lua.execute("entries={{questID=900,title='Our current work',isHeader=false},{questID=902,title='Already ready',isHeader=false}}; C_QuestLog.IsComplete=function(id) return id==902 end")
    c.ns.ReadQuests(); c.ns.ReadRouteLocations()
    return c


def valley_client():
    c = Client(quests=(5441,), completed=(788,), use_catalogue=True)
    c.lua.globals().grouped = False
    c.unit_names({'player': ['Alice', 'TestRealm']})
    c.guide_environment(level=4, current_quests_first=True)
    c.lua.execute('''
    C_Map.GetBestMapForUnit=function() return 1411 end
    C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .446,.686 end} end
    C_Map.GetMapInfo=function() return {name='Durotar'} end
    ''')
    c.ns.ReadProfile(); c.ns.ReadRouteLocations()
    return c


class NearbyPickupTests(unittest.TestCase):
    def test_published_valley_quests_bundle_with_lazy_peons_and_real_apple_source(self):
        c = valley_client()
        choice = c.ns.GuideChoices()[1]
        self.assertEqual(choice.mode, 'bundle')
        self.assertTrue(choice.pickupIDs[4402])
        self.assertTrue(choice.pickupIDs[792])
        self.assertIn('Galgar', choice.reason)
        self.assertIn('Zureetha Fargaze', choice.reason)
        route = c.ns.BuildGuideRoute(choice, True)
        self.assertTrue(any(s.id == 5441 and s.kind == 'q' for s in route.stops.values()))
        apples = [s for s in route.stops.values() if s.id == 4402]
        self.assertEqual([s.kind for s in apples], ['a', 'q', 't'])
        self.assertEqual(apples[1].entityID, 171938)
        self.assertEqual(apples[1].itemID, 11583)
        self.assertEqual(apples[1].quantity, 10)
        self.assertFalse(apples[1].unknownLocation)
        self.assertFalse(route.partial)
        self.assertTrue(all(s.mapID == 1411 for s in route.stops.values()))

    def test_general_vile_familiars_needs_no_warlock_intro_but_medallion_still_needs_completion(self):
        c = valley_client()
        choice = c.ns.GuideChoices()[1]
        self.assertIsNone(c.ns.CatalogueQuest(792).previousQuest)
        self.assertTrue(choice.pickupIDs[792])
        self.assertTrue(choice.pickupIDs[4402])
        self.assertFalse(c.ns.CatalogueAllowed(794, c.ns.profile, c.ns.self)[0])
        c.ns.active[792] = 'Vile Familiars'
        self.assertFalse(c.ns.CatalogueAllowed(794, c.ns.profile, c.ns.self)[0])
        c.lua.globals().finished[792] = True
        self.assertTrue(c.ns.CatalogueAllowed(794, c.ns.profile, c.ns.self))

    def test_ready_turn_ins_precede_pickups_then_shared_work_and_returns(self):
        c = local_client()
        route = c.ns.BuildGuideRoute(c.ns.GuideChoices()[1], True)
        self.assertEqual([(s.id, s.kind) for s in route.stops.values()],
                         [(902, 't'), (901, 'a'), (900, 'q'), (901, 'q'), (900, 't'), (901, 't')])

    def test_settings_allow_strict_current_log_plans_and_update_the_open_route(self):
        self.assertTrue(Client(quests=()).ns.Option('nearbyPickups'))
        c = local_client()
        map_canvas(c)
        c.ns.SetFilter('guides')
        c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        self.assertEqual(c.ns.routeSelection.mode, 'bundle')
        c.ns.SetOption('nearbyPickups', False)
        self.assertEqual(c.ns.routeSelection.mode, 'current')
        self.assertFalse(any(s.kind == 'a' for s in c.ns.selectedRoute.stops.values()))
        c.ns.SetOption('nearbyPickups', True)
        self.assertEqual(c.ns.routeSelection.mode, 'bundle')

    def test_close_npc_does_not_justify_distant_work_returns_or_ineligible_quests(self):
        c = local_client()
        c.ns.SetOption('classQuests', False)
        for id, data in {
            903: nearby('Wrong faction', side='Alliance'),
            904: nearby('Too high', level=30),
            905: nearby('Locked', previousQuest=999),
            906: nearby('Personal', categoryPath='professions/cooking'),
            907: nearby('Dungeon', categoryPath='dungeons/test'),
            908: nearby('Class', categoryPath='classes/warlock'),
            909: quest('Distant work', starts=[{'mapID': 501, 'x': .21, 'y': .37, 'name': 'Hub'}], xp=999999),
            910: quest('Distant pickup', starts=[{'mapID': 501, 'x': .9, 'y': .9, 'name': 'Far'}]),
            911: quest('Distant return', starts=[{'mapID': 501, 'x': .21, 'y': .37, 'name': 'Hub'}],
                       ends=[{'mapID': 501, 'x': .9, 'y': .9, 'name': 'Far'}]),
            912: quest('Other map', map_id=502),
            913: nearby('Unknown gates', prerequisitesUnverified=True),
        }.items():
            c.ns.catalogue.quests[id] = c.lua.table_from(data, recursive=True)
        choice = c.ns.GuideChoices()[1]
        self.assertEqual({r.id for r in choice.records.values()}, {900, 901, 902})

    def test_walking_budget_changes_an_eligible_detour_but_not_its_pickup_gate(self):
        c = local_client()
        c.ns.catalogue.quests[901].objectives[1].x = .32
        c.ns.SetOption('circuitRadius', .10)
        self.assertEqual(c.ns.GuideChoices()[1].mode, 'current')
        c.ns.SetOption('circuitRadius', .16)
        self.assertEqual(c.ns.GuideChoices()[1].mode, 'bundle')

    def test_bounded_selection_does_not_grow_with_catalogue_size(self):
        c = local_client()
        catalogue(c, {i: nearby(str(i)) for i in range(900, 1200)})
        c.ns.SetOption('circuitLimit', 4)
        choice = c.ns.GuideChoices()[1]
        self.assertEqual(len(list(choice.pickupIDs.items())), 4)
        self.assertLessEqual(len(c.ns.BuildGuideRoute(choice, True).stops), 20)
        self.assertEqual(len(choice.records), 6)

    def test_pickup_advances_to_objectives_and_ready_return_using_live_progress(self):
        c = local_client()
        map_canvas(c)
        choice = c.ns.GuideChoices()[1]
        c.ns.ShowGuideOnMap(choice)
        c.lua.execute("entries={{questID=901,title='Nearby pickup',isHeader=false}}")
        c.ns.ReadQuests(); c.ns.ReadRouteLocations(); c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertFalse(any(s.kind == 'a' for s in c.ns.selectedRoute.stops.values()))
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'q')
        c.lua.execute('C_QuestLog.IsComplete=function() return true end')
        c.ns.ReadRouteLocations(); c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 't')
        c.lua.execute('entries={}; finished[901]=true')
        c.ns.ReadQuests(); c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)

    def test_unknown_active_destinations_do_not_start_unrelated_pickup_discovery(self):
        c = local_client()
        c.lua.execute("entries={{questID=999,title='Unknown active',isHeader=false}}")
        c.ns.ReadQuests(); c.ns.ReadRouteLocations()
        choice = c.ns.GuideChoices()[1]
        self.assertEqual(choice.mode, 'current')
        self.assertFalse(choice.hasPoint)

    def test_refreshing_recommendations_after_acceptance_preserves_selected_pickup_roles(self):
        c = local_client()
        c.ns.catalogue.quests[903] = c.lua.table_from(nearby('Another pickup'), recursive=True)
        map_canvas(c)
        old = c.ns.GuideChoices()[1]
        c.ns.ShowGuideOnMap(old)
        c.lua.execute("entries={{questID=900,title='Our current work',isHeader=false},{questID=901,title='Nearby pickup',isHeader=false},{questID=902,title='Already ready',isHeader=false}}")
        c.ns.ReadQuests(); c.ns.ReadRouteLocations()
        choices = c.ns.GuideChoices()
        self.assertFalse(choices[1].pickupIDs[901])
        c.ns.UpdateSelectedRoute(choices)
        self.assertEqual(c.ns.routeSelection.key, old.key)
        self.assertTrue(c.ns.routeSelection.pickupIDs[901])
        self.assertTrue(c.ns.routeSelection.pickupIDs[903])


class BundleInvitationTests(unittest.TestCase):
    def clients(self):
        a, b = local_client(), local_client()
        b.lua.globals().player, b.lua.globals().peer = 'Bob', 'Alice'
        for c, name, peer in ((a, 'Alice', 'Bob'), (b, 'Bob', 'Alice')):
            c.lua.globals().grouped = True
            c.unit_names({'player': [name, 'TestRealm'], 'party1': [peer, 'TestRealm']})
            c.receive('1|S|1|1|1|900,902', sender=peer+'-TestRealm')
            c.receive('1|P|12|2|501|Test Coast', sender=peer+'-TestRealm')
            c.receive('1|C|1|1|1|', sender=peer+'-TestRealm')
            c.receive('1|K|1|1|1|900,901,902', sender=peer+'-TestRealm')
            map_canvas(c)
        return a, b

    def test_party_follow_preserves_pickup_roles_and_keeps_unfinished_friends_marked(self):
        a, b = self.clients()
        choice = a.ns.GuideChoices()[1]
        self.assertTrue(a.ns.StartPartyRoute(choice))
        invitations = [m for _, m, _ in a.drain() if m.startswith('1|V|')]
        self.assertTrue(invitations)
        for packet in invitations:
            b.receive(packet, sender='Alice-TestRealm')
        invite = b.ns.partyRoutePrompt.invite
        self.assertEqual(invite.mode, 'bundle')
        self.assertTrue(invite.pickupIDs[901])
        self.assertIsNone(b.ns.selectedRoute)  # A prompt does not switch the route.
        b.ns.db.config.nearbyPickups = False  # Explicit Follow route accepts this selection.
        b.ns.partyRoutePrompt.follow.OnClick()
        self.assertEqual(b.ns.routeSelection.mode, 'bundle')
        self.assertTrue(b.ns.routeSelection.pickupIDs[901])
        self.assertTrue(any(s.id == 901 and s.kind == 'a' for s in b.ns.selectedRoute.stops.values()))
        # Alice accepts this newly bundled quest; Bob still needs its pickup.
        b.receive('1|S|2|1|1|901', sender='Alice-TestRealm')
        b.receive('1|R|2|901|501|24000|40000|q', sender='Alice-TestRealm')
        b.ns.UpdateSelectedRoute(b.lua.table())
        self.assertTrue(any(s.id == 901 and s.kind == 'a' for s in b.ns.selectedRoute.stops.values()))
        self.assertTrue(any(s.id == 901 and s.kind == 'q' for s in b.ns.selectedRoute.stops.values()))
        # Bob hands in; Alice's unfinished work remains, then clears on her turn-in.
        b.lua.execute('entries={}; finished[901]=true')
        b.ns.ReadQuests(); b.ns.UpdateSelectedRoute(b.lua.table())
        self.assertTrue(any(s.id == 901 and s.kind == 'q' for s in b.ns.selectedRoute.stops.values()))
        b.receive('1|S|3|1|1|', sender='Alice-TestRealm')
        b.receive('1|C|3|1|1|901', sender='Alice-TestRealm')
        b.ns.UpdateSelectedRoute(b.lua.table())
        self.assertTrue(b.ns.selectedRoute.complete)
        self.assertEqual(len(b.ns.selectedRoute.stops), 0)

    def test_pickup_role_is_invalid_in_other_modes_or_when_malformed(self):
        _, b = self.clients()
        for packet in ('1|V|10|1|1|current|501|900|900,901+',
                       '1|V|10|1|1|bundle|501|900|900,901++',
                       '1|V|10|1|1|bundle|501|900|900,0901+',
                       '1|V|10|1|1|bundle|501|900|900,901+,901'):
            handled, accepted, _ = b.ns.ReceivePartyRouteMessage(packet, 'Alice-TestRealm')
            self.assertTrue(handled)
            self.assertFalse(accepted)
        self.assertIsNone(b.ns.pendingPartyRouteInvite)

    def test_multipart_out_of_order_keeps_pickup_flags_and_original_roles(self):
        _, b = self.clients()
        b.receive('1|V|8|2|2|bundle|501|900|908+,909+', sender='Alice-TestRealm')
        self.assertIsNone(b.ns.pendingPartyRouteInvite)
        b.receive('1|V|8|1|2|bundle|501|900|900,901+,902,903+,904,905,906+,907', sender='Alice-TestRealm')
        invite = b.ns.partyRoutePrompt.invite
        self.assertEqual({id for id, yes in invite.pickupIDs.items() if yes}, {901, 903, 906, 908, 909})
        self.assertEqual(len(invite.ids), 10)


if __name__ == '__main__':
    unittest.main()
