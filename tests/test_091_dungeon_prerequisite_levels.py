"""Dungeon route includes real prequests and reports their higher level gate."""
import unittest

from test_0817 import shipped, wow_bit, groups


class DungeonPrerequisiteLevelTests(unittest.TestCase):
    def test_heart_of_disruption_waits_for_blood_in_the_streets_at_level_30(self):
        c = shipped(26)
        wow_bit(c)
        heart = c.ns.CatalogueQuest(96984)
        self.assertEqual(heart.previousQuest, 92434)
        self.assertIn('wowhead.com/forever/quest=96984', heart.prerequisiteSource)

        guide = c.ns.DungeonGuide(groups(c)['city-of-dalaran'], 96984)
        self.assertTrue(guide.collectionRequired[92434])
        route = c.ns.BuildDungeonRoute(guide, False, False)
        self.assertFalse(any(int(stop.id) in (92434, 96984) for stop in route.stops.values()))
        self.assertIn('Reach level 30 to accept Blood in the Streets.', route.pendingReason)
        later = {int(step.id): step for step in route.later.values()}
        self.assertIn(92434, later)
        self.assertIn('Reach level 30 to accept Blood in the Streets.', later[92434].reason)

    def test_level_30_routes_the_prequest_before_heart_then_advances(self):
        c = shipped(30)
        wow_bit(c)
        dungeon = groups(c)['city-of-dalaran']
        guide = c.ns.DungeonGuide(dungeon, 96984)
        route = c.ns.BuildDungeonRoute(guide, False, False)
        ids = [int(stop.id) for stop in route.stops.values()]
        self.assertEqual([i for i in ids if i in (92434, 96984)], [92434, 92434, 92434, 96984])

        c.lua.globals().finished[92434] = True
        guide = c.ns.DungeonGuide(dungeon, 96984)
        route = c.ns.BuildDungeonRoute(guide, False, False)
        ids = [int(stop.id) for stop in route.stops.values()]
        self.assertNotIn(92434, ids)
        self.assertIn(96984, ids)


if __name__ == '__main__':
    unittest.main()
