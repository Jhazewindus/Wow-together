"""Fact-based guide instructions; host fixtures cannot certify game rendering."""
import unittest

from test_addon import Client
from test_navigation import navigator
from test_routes import catalogue, quest, route_client


def step(c, **fields):
    data = {'id': 900, 'kind': 'q', 'title': 'Supplies', 'mapID': 501,
            'x': .4, 'y': .6, 'itemName': 'Boar Flank', 'targetName': 'Battleboar',
            'npcName': 'Battleboar', 'action': 'loot', 'quantity': 8}
    data.update(fields)
    return c.lua.table_from(data, recursive=True)


def progress(c, objectives):
    c.ns.localProgress[900] = c.lua.table_from({'objectives': objectives}, recursive=True)


class GuideTextTests(unittest.TestCase):
    def test_each_drop_goal_matches_its_item_not_the_shared_creature(self):
        c = route_client()
        progress(c, [{'text': 'Boar Snout: 8/8', 'kind': 'item', 'have': 8, 'need': 8},
                     {'text': 'Boar Flank: 3/8', 'kind': 'item', 'have': 3, 'need': 8}])
        stop = step(c)
        self.assertEqual(c.ns.GuideStepAction(stop), 'Loot 5 more Boar Flank')
        self.assertEqual(c.ns.StopInstruction(stop), 'Loot 5 more Boar Flank from Battleboar')
        self.assertEqual(c.ns.GuideStepFacts(stop).progress, '3/8')
        stop.itemName = 'Boar Snout'
        self.assertEqual(c.ns.GuideStepAction(stop), 'Objective complete: Boar Snout')
        self.assertEqual(c.ns.GuideStepHint(stop), 'This objective is finished.')

    def test_unknown_or_unmatched_progress_does_not_invent_remaining_counts(self):
        c = route_client()
        progress(c, [{'text': 'Another item', 'kind': 'item', 'have': 5, 'need': 20}])
        stop = step(c)
        self.assertEqual(c.ns.GuideStepAction(stop), 'Loot 8 × Boar Flank')
        self.assertIsNone(c.ns.GuideStepFacts(stop).progress)
        stop.quantity = None
        self.assertEqual(c.ns.GuideStepAction(stop), 'Loot Boar Flank')
        stop.quantity = 8; stop.quantityUnknown = True
        self.assertEqual(c.ns.GuideStepAction(stop), 'Loot Boar Flank')
        progress(c, [{'text': 'Boar Flank', 'finished': True}])
        self.assertEqual(c.ns.GuideStepAction(stop), 'Objective complete: Boar Flank')

    def test_public_native_kill_goal_supplies_action_and_count_without_a_data_guess(self):
        c = route_client()
        progress(c, [{'text': 'Battleboar slain: 7/10', 'kind': 'monster', 'have': 7, 'need': 10}])
        stop = step(c, itemName=None, action=None)
        self.assertEqual(c.ns.GuideStepAction(stop), 'Kill 3 more Battleboar')
        self.assertEqual(c.ns.GuideStepFacts(stop).progress, '7/10')

    def test_item_goal_cannot_be_reclassified_as_a_kill(self):
        c = route_client()
        progress(c, [{'text': 'Boar Flank', 'kind': 'monster', 'have': 3, 'need': 8}])
        self.assertEqual(c.ns.GuideStepAction(step(c)), 'Loot 5 more Boar Flank')

    def test_lazy_peons_uses_exact_requirement_identity_for_progress(self):
        c = Client(quests=(), use_catalogue=True)
        q = c.ns.CatalogueQuest(5441)
        stop = c.ns.PublishedGuideStop(c.ns.CatalogueRecord(5441), q.objectives[1], 'q')
        c.ns.localProgress[5441] = c.lua.table_from({'objectives': [
            {'text': 'Peons Awoken: 2/5', 'kind': 'monster', 'have': 2, 'need': 5}]}, recursive=True)
        self.assertEqual(c.ns.GuideStepAction(stop), "Use Foreman's Blackjack on Lazy Peon")
        self.assertEqual(c.ns.GuideStepFacts(stop).progress, '2/5')
        description = c.ns.GuideStepDescription(stop)
        self.assertIn("Quest item: Foreman's Blackjack (provided)", description)
        self.assertIn('3 more Lazy Peon', description)

    def test_ground_objects_vendor_items_and_unlocated_items_have_distinct_hints(self):
        c = route_client()
        stop = step(c, action='gather', itemName='Apple', targetName='Apple tree', npcName=None)
        self.assertEqual(c.ns.GuideStepAction(stop), 'Gather 8 × Apple')
        self.assertEqual(c.ns.GuideStepHint(stop), 'Collect from Apple tree.')
        stop.targetName = 'Apple'; stop.action = 'collect'
        self.assertEqual(c.ns.GuideStepHint(stop), 'Collect the required quest items.')
        stop.action = 'buy'; stop.npcName = 'Merchant'
        self.assertEqual(c.ns.GuideStepAction(stop), 'Buy 8 × Apple')
        self.assertIn('vendor', c.ns.GuideStepHint(stop))

    def test_accept_and_turn_in_name_the_npc_and_preserve_the_quest_on_hover(self):
        c = route_client()
        for kind, action, full in [('a', 'Accept from Gornek', 'Accept Cutting Teeth from Gornek'),
                                 ('t', 'Turn in to Gornek', 'Turn in Cutting Teeth to Gornek')]:
            stop = step(c, kind=kind, action=None, itemName=None, title='Cutting Teeth', npcName='Gornek')
            self.assertEqual(c.ns.GuideStepAction(stop), action)
            self.assertIn(full, c.ns.GuideStepDescription(stop))
            self.assertIsNone(c.ns.GuideStepFacts(stop).progress)

    def test_location_shows_real_coordinates_and_cross_zone_destination(self):
        c = route_client()
        stop = step(c)
        self.assertEqual(c.ns.StopLocationText(stop, 501), 'Test Coast • 40.0, 60.0')
        self.assertEqual(c.ns.StopLocationText(stop, 502), 'Travel to Test Coast • 40.0, 60.0')
        stop.sourceZone = 'Known landmark'
        self.assertEqual(c.ns.StopLocationText(stop), 'Known landmark • Test Coast • 40.0, 60.0')

    def test_planning_anchors_missing_and_restricted_coordinates_are_never_described_as_real(self):
        c = route_client()
        stop = step(c, unknownLocation=True)
        self.assertEqual(c.ns.StopLocationText(stop), 'Test Coast • location not mapped')
        self.assertNotIn('40.0', c.ns.RouteContext(stop, 501))
        self.assertIn('quest tracker', c.ns.RouteContext(stop, 501))
        stop.unknownLocation = None
        for value in (c.lua.globals().secret, float('nan'), float('inf'), 2):
            stop.x = value
            self.assertEqual(c.ns.StopLocationText(stop), 'Test Coast • location not mapped')

    def test_restricted_counts_and_names_are_not_printed_or_calculated(self):
        c = route_client()
        c.lua.execute('''
          secretIndexReads = 0
          setmetatable(secret, {__index=function() secretIndexReads=secretIndexReads+1; error('secret read') end})
        ''')
        stop = step(c)
        stop.quantity = c.lua.globals().secret
        progress(c, [{'text': 'Boar Flank', 'have': c.lua.globals().secret, 'need': c.lua.globals().secret}])
        self.assertEqual(c.ns.GuideStepAction(stop), 'Loot Boar Flank')
        self.assertIsNone(c.ns.GuideStepFacts(stop).progress)
        stop.npcName = c.lua.globals().secret
        stop.targetName = c.lua.globals().secret
        self.assertNotIn('Battleboar', c.ns.GuideStepDescription(stop))
        self.assertEqual(c.lua.globals().secretIndexReads, 0)

    def test_party_member_counts_require_a_current_snapshot(self):
        c = route_client()
        stop = step(c, memberKey='Bob-TestRealm')
        progress(c, [{'text': 'Boar Flank', 'have': 7, 'need': 8}])
        c.ns.members['Bob-TestRealm'] = c.lua.table_from({'active': {900: True}, 'activeRevision': 2,
            'progress': {900: {'activeRevision': 2, 'objectives': [{'text': 'Boar Flank', 'have': 3, 'need': 8}]}}}, recursive=True)
        self.assertEqual(c.ns.GuideStepFacts(stop).progress, '3/8')
        c.ns.members['Bob-TestRealm'].syncPending = True
        self.assertIsNone(c.ns.GuideStepFacts(stop).progress)

    def test_panel_combines_action_distance_and_progress_without_changing_the_route(self):
        c = navigator()
        stop = step(c, x=.21, y=.27)
        c.ns.selectedRoute.stops[1] = stop
        progress(c, [{'text': 'Boar Flank', 'have': 3, 'need': 8}])
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.status.text, 'Loot 5 more Boar Flank')
        self.assertEqual(c.ns.navigation.distance.text, '100 yd • 3/8')
        self.assertEqual(c.ns.navigation.context.text.splitlines(),
                         ['Kill and loot Battleboar.', 'Test Coast • 21.0, 27.0'])
        self.assertEqual(c.ns.selectedRoute.stops[1].x, .21)

    def test_pending_step_keeps_its_facts_and_blocking_reason(self):
        c = navigator()
        stop = step(c, unknownLocation=True)
        c.ns.selectedRoute.stops = c.lua.table()
        c.ns.selectedRoute.pendingStop = stop
        c.ns.routePaused = 'Finish the prerequisite before this step.'
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.status.text, 'Finish the prerequisite before this step.')
        self.assertIn('location not mapped', c.ns.navigation.context.text)
        self.assertIn('Battleboar', c.ns.GuideStepDescription(c.ns.navigation.state.stop))

    def test_patrol_hint_is_only_used_for_explicit_published_patrols(self):
        c = route_client()
        c.ns.questEntities = c.lua.table_from({'npc': {123: {'patrols': [{'points': [1, 2]}]}}}, recursive=True)
        stop = step(c, kind='a', action=None, entityID=123, itemName=None)
        self.assertIn('patrols', c.ns.GuideStepHint(stop))
        stop.entityID = 124
        self.assertIn('offer list', c.ns.GuideStepHint(stop))

    def test_blocked_pickup_is_not_described_as_current_objective_work(self):
        c = navigator()
        stop = step(c, kind='a', action=None, itemName=None, npcName='Gornek')
        c.ns.selectedRoute.stops = c.lua.table()
        c.ns.selectedRoute.pendingStop = stop
        c.ns.routePaused = 'Finish Cutting Teeth first.'
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.status.text, 'Finish Cutting Teeth first.')
        self.assertNotIn('Kill', c.ns.GuideStepDescription(c.ns.navigation.state.stop))

    def test_unknown_item_starter_does_not_invent_a_creature_drop(self):
        c = route_client()
        stop = step(c, kind='a', action='start-item', itemName='Sealed Letter', npcName=None, targetName=None)
        self.assertEqual(c.ns.GuideStepAction(stop), 'Find Sealed Letter')
        self.assertNotIn('Loot', c.ns.StopInstruction(stop))
