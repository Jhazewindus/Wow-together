"""Newly published Alcaz quests are visible without inventing route facts."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_dungeon_level_gates import own_lua
from import_dungeons import is_named_category_page
from test_0817 import shipped, groups


class AlcazDungeonCoverageTests(unittest.TestCase):
    def test_importer_rejects_wowheads_generic_fallback_category(self):
        expected = 'https://www.wowhead.com/forever/quests/dungeons/alcaz-prison'
        generic = '<link rel="canonical" href="https://www.wowhead.com/forever/quests/dungeons">'
        named = '<link rel="canonical" href="' + expected + '">'
        prefixed = '<link rel="canonical" href="https://www.wowhead.com/forever/quests/dungeons/16544-city-of-dalaran">'
        self.assertFalse(is_named_category_page(generic, 'blackmaw-hold'))
        self.assertTrue(is_named_category_page(named, 'alcaz-prison'))
        self.assertTrue(is_named_category_page(prefixed, 'city-of-dalaran'))
        with self.assertRaises(ValueError):
            is_named_category_page(named, 'shapers-terrace')

    def test_alcaz_list_and_four_records_have_source_hashes_and_keep_unknowns(self):
        dungeon_data = json.loads((ROOT / 'WowTogether/DungeonData.json').read_text())
        quest_catalogue = own_lua(ROOT / 'WowTogether_QuestData/QuestCatalogue.lua', 'catalogue')['quests']
        alcaz = dungeon_data['dungeons']['alcaz-prison']
        expected = {96335, 96337, 96377, 96772}
        self.assertEqual(set(alcaz['questIDs']), expected)
        self.assertEqual(dungeon_data['quest_categories']['alcaz-prison']['quests'], 4)
        self.assertEqual(set(dungeon_data['unknown_quest_categories']), {'blackmaw-hold', 'shapers-terrace'})
        self.assertTrue(expected <= set(quest_catalogue))
        titles = {
            96335: 'The Man in the Iron Chains',
            96337: 'More Valuable Than Gold',
            96377: 'State Secrets',
            96772: "The Dragon's Journal",
        }
        for quest_id, title in titles.items():
            with self.subTest(quest_id=quest_id):
                quest = quest_catalogue[quest_id]
                self.assertEqual(quest['title'], title)
                self.assertEqual(quest['categoryPath'], 'dungeons/alcaz-prison')
                self.assertIn('SHA-256', quest['dungeonSource'])
                self.assertTrue(quest['prerequisitesRead'])
                self.assertFalse(quest.get('prerequisitesUnverified', False))
                self.assertTrue(quest['objectiveLocationsIncomplete'])
                self.assertFalse(quest.get('starts'))
                self.assertFalse(quest.get('ends'))
                self.assertFalse(quest.get('previousQuest'))

    def test_alcaz_level_gate_and_unknown_prerequisite_are_both_reported(self):
        c = shipped(45)
        c.ns.profile.faction = 'Alliance'
        c.ns.profile.raceID = 1
        allowed, level_reason = c.ns.CatalogueAllowed(96772, c.ns.profile, c.ns.self)
        self.assertFalse(allowed)
        self.assertEqual(level_reason, 'Requires level 46.')
        c.ns.profile.level = 46
        group = groups(c)['alcaz-prison']
        guide = c.ns.DungeonGuide(group, 96772)
        route = c.ns.BuildDungeonRoute(guide, False, False)
        self.assertEqual(len(route.stops), 0)
        self.assertIn('pickup location for The Dragon\'s Journal is not mapped yet', route.pendingReason)
        later = {int(step.id): step for step in route.later.values()}
        self.assertIn(96772, later)
        self.assertIn('pickup location for The Dragon\'s Journal is not mapped yet', later[96772].reason)

    def test_scarlet_guide_routes_razorfen_kraul_prequest_before_hearts_of_zeal(self):
        # Hearts of Zeal (1113) is the Scarlet objective; Going, Going, Guano!
        # (1109) is the Horde prerequisite and must be completed in RFK first.
        c = shipped(30)
        c.ns.profile.faction = 'Horde'
        c.ns.profile.raceID = 2
        scarlet = groups(c)['scarlet-monastery']
        self.assertEqual(c.ns.CatalogueQuest(1113).previousQuest, 1109)
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(scarlet, 1113), False, False)
        stops = [route.stops[i] for i in range(1, len(route.stops) + 1)]
        self.assertEqual([stop.id for stop in stops], [1109, 1109, 1109, 1113])
        self.assertEqual([stop.kind for stop in stops], ['a', 'q', 't', 'a'])
        self.assertEqual(stops[1].dungeonKey, 'razorfen-kraul')
        self.assertEqual(stops[-1].title, 'Hearts of Zeal')


if __name__ == '__main__':
    unittest.main()
