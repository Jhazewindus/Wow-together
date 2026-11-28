"""A dungeon's quest route when the character is below the level of the dungeon's own quests."""
import json
import unittest

from test_addon import Client
import test_leveling_path as T


def character(level):
    c = Client(quests=(), use_catalogue=True, party_mode='never', saved_variables={'config': {'uiNext': True, 'levelingPath': False}})
    c.guide_environment(level=level)
    c.lua.execute(T.SCENE, c.ns, level, 0.3, 'Horde', 1434, 'Stranglethorn Vale')
    c.ns.ReadProfile(); c.drain()
    return c


def kroldok(c):
    return next(group for group in c.ns.DungeonGroups().values() if group.key == 'kroldok-stronghold')


def guide_for(c, group):
    result = c.ns.DungeonGuide(group)
    return result if isinstance(result, tuple) else (result, None)


class LeadUpTests(unittest.TestCase):
    """Seen in play at level 36: Follow and Start quest route on Krol'dok Stronghold did nothing at all."""

    def test_below_the_quests_level_the_route_is_the_chain_that_leads_to_them(self):
        c = character(36)
        guide, why = guide_for(c, kroldok(c))
        self.assertIsNotNone(guide, why)                                            # It was nil: an empty guide.
        self.assertTrue(guide.ahead)
        self.assertEqual(guide.opensAt, 38)
        self.assertEqual(guide.title, "Prepare for Krol'dok Stronghold")
        ids = [record.id for record in guide.records.values()]
        self.assertIn(93786, ids)                                                   # A Message in Blood: takable at 35.
        self.assertGreaterEqual(len(ids), 15)                                       # The five quests and what comes before them.
        self.assertIn('open at level 38', guide.reason)

    def test_starting_it_gives_a_route_with_something_to_do_now(self):
        c = character(36)
        started = c.ns.ShowDungeonQuests(kroldok(c), True)
        c.drain()
        self.assertTrue(started[0] if isinstance(started, tuple) else started)
        self.assertIn('route stop(s)', c.ns.guideAction)
        self.assertNotIn('No unfinished quests', c.ns.guideAction)

    def test_at_the_quests_level_it_is_the_ordinary_route(self):
        c = character(40)
        guide, why = guide_for(c, kroldok(c))
        self.assertIsNotNone(guide, why)
        self.assertFalse(guide.ahead)
        self.assertEqual(guide.title, "Get Krol'dok Stronghold quests")

    def test_far_too_low_for_any_of_it_is_refused_with_the_level_it_opens_at(self):
        c = character(20)
        guide, why = guide_for(c, kroldok(c))
        self.assertIsNone(guide)
        self.assertIn('open at level 38', why)
        self.assertIn('nothing that leads up to them can be started', why)

    def test_a_refusal_is_shown_on_the_instances_page_not_swallowed(self):
        c = character(20)
        started = c.ns.ShowDungeonQuests(kroldok(c), True)
        self.assertFalse(started[0])
        page = c.ns.instancePage
        self.assertTrue(page.IsShown(page))                                         # Something happened on screen...
        self.assertIn('open at level 38', page.hint.text)                           # ...and it says why.


class PageTests(unittest.TestCase):
    def test_the_page_says_what_the_button_will_do_for_this_character(self):
        c = character(36)
        c.ns.ShowInstancePage(kroldok(c))
        page = c.ns.instancePage
        self.assertEqual(page.collect.caption.text, 'Start the lead-up')
        self.assertIn('You are level 36 and these quests open at 38', page.hint.text)
        self.assertTrue(page.collect.enabled)

    def test_pressing_it_starts_the_route_and_gets_out_of_the_way(self):
        c = character(36)
        c.ns.ShowInstancePage(kroldok(c))
        page = c.ns.instancePage
        page.collect.OnClick(page.collect)
        c.drain()
        self.assertFalse(page.IsShown(page))
        self.assertIn('route stop(s)', c.ns.guideAction)

    def test_when_nothing_can_be_started_the_button_is_off_and_the_reason_is_there_before_you_press(self):
        c = character(20)
        c.ns.ShowInstancePage(kroldok(c))
        page = c.ns.instancePage
        self.assertFalse(page.collect.enabled)
        self.assertIn('open at level 38', page.hint.text)

    def test_at_level_the_page_reads_as_before(self):
        c = character(40)
        c.ns.ShowInstancePage(kroldok(c))
        page = c.ns.instancePage
        self.assertEqual(page.collect.caption.text, 'Start quest route')
        self.assertEqual(page.hint.text, 'Leads you to every pickup and prerequisite, then to the entrance.')


class EntranceTests(unittest.TestCase):
    """A dungeon that ships without an entrance learns it the first time the player walks in."""

    def setUp(self):
        self.c = character(40)
        self.c.lua.execute('''
            local ns = ...
            instance, instanceName, instanceKind = false, "Krol'dok Stronghold", "party"
            function IsInInstance() return instance, instance and instanceKind or "none" end
            function GetInstanceInfo() return instanceName, instanceKind, 1, "Normal", 5, 0, false, 9001 end
            here = {mapID = 2548, x = 0.412, y = 0.633}
            ns.PlayerSpot = function() return here end
        ''', self.c.ns)

    def walk_in(self):
        self.c.ns.NoteOutdoorSpot()                                                 # The last few seconds outdoors.
        self.c.lua.execute('instance = true; here = nil')                           # Through the door: no map position inside.
        result = self.c.ns.RecordInstanceEntrance()
        return result[0] if isinstance(result, tuple) else result

    def test_kroldok_has_no_entrance_until_you_have_been_in(self):
        group = kroldok(self.c)
        self.assertIsNone(self.c.ns.DungeonEntrance(group))
        self.assertTrue(self.walk_in())
        entrance = self.c.ns.DungeonEntrance(group)
        self.assertEqual((entrance.mapID, entrance.x, entrance.y), (2548, 0.412, 0.633))
        self.assertIn('Entrance noted', list(self.c.lua.globals().printed.values())[-1])

    def test_learned_entrance_is_in_the_manual_anonymous_build_specific_research_export(self):
        self.walk_in()
        export = json.loads(self.c.ns.ExportQuestResearch())
        events = [row for row in export['events'] if row.get('event') == 'dungeon-entrance']
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]['dungeonKey'], events[0]['instanceID']), ('kroldok-stronghold', 9001))
        self.assertEqual((events[0]['mapID'], events[0]['x'], events[0]['y']), (2548, 0.412, 0.633))
        self.assertEqual(events[0]['build'], '70009')
        self.assertNotIn('character', events[0])

    def test_then_the_quest_route_can_end_at_the_door(self):
        self.walk_in()
        self.c.lua.execute('instance = false; here = {mapID = 2548, x = 0.2, y = 0.2}')
        guide, why = guide_for(self.c, kroldok(self.c))
        self.assertIsNotNone(guide.entrance)
        self.assertNotIn('Entrance not located', guide.reason)

    def test_a_second_visit_does_not_move_it(self):
        self.walk_in()
        self.c.lua.execute('instance = false; here = {mapID = 2548, x = 0.9, y = 0.9}')
        self.assertFalse(self.walk_in())
        self.assertEqual(self.c.ns.DungeonEntrance(kroldok(self.c)).x, 0.412)

    def test_a_dungeon_that_ships_with_an_entrance_keeps_it(self):
        self.c.lua.execute('instanceName = "Scholomance"')
        self.assertFalse(self.walk_in())
        self.assertIsNone(self.c.ns.db.dungeonEntrances and self.c.ns.db.dungeonEntrances['scholomance'])

    def test_nothing_is_recorded_without_a_position_from_outside(self):
        self.c.lua.execute('instance = true; here = nil')
        result = self.c.ns.RecordInstanceEntrance()
        self.assertFalse(result[0] if isinstance(result, tuple) else result)


if __name__ == '__main__':
    unittest.main()
