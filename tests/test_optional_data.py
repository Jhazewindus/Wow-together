"""Load-on-demand data packs, exercised through the host addon bootstrap."""
import unittest

from test_addon import Client


NATIVE_WAYPOINTS = r'''
C_Map = {GetBestMapForUnit=function() return 1411 end}
C_QuestLog.GetNextWaypoint = function(id) return 1411, .5, .5 end
C_QuestLog.IsComplete = function() return false end
'''


class OptionalDataTests(unittest.TestCase):
    def test_startup_and_catalogue_summary_do_not_parse_quest_payload(self):
        client = Client(quests=(), use_lazy_data=True, default_guide=True)
        self.assertEqual(client.data_addons_loaded, set())
        self.assertEqual(client.ns.catalogue.count, 5230)
        self.assertEqual(client.ns.catalogue.captured, "2026-10-10")
        self.assertEqual(len(client.ns.xpBaseline), 60)
        self.assertEqual(client.data_addons_loaded, set())

        quest = client.ns.CatalogueQuest(789)
        self.assertEqual(quest.title, "Sting of the Scorpid")
        self.assertEqual(client.data_addons_loaded, {"WowTogether_QuestData"})

    def test_native_active_quest_waypoint_does_not_load_catalogue(self):
        client = Client(use_lazy_data=True, default_guide=True, before_load=NATIVE_WAYPOINTS)
        self.assertEqual(client.data_addons_loaded, set())
        self.assertEqual(client.ns.optionalDataState["WowTogether_QuestData"], None)

    def test_profession_and_dungeon_payloads_load_only_on_request(self):
        client = Client(quests=(), use_lazy_data=True, default_guide=True)
        self.assertTrue(client.ns.EnsureOptionalData("WowTogether_ProfessionData"))
        self.assertTrue(client.ns.professionGuideData.professions)
        self.assertIn("WowTogether_ProfessionData", client.data_addons_loaded)
        self.assertNotIn("WowTogether_DungeonData", client.data_addons_loaded)

        self.assertTrue(client.ns.EnsureOptionalData("WowTogether_DungeonData"))
        self.assertTrue(client.ns.dungeonJournalData.dungeons)
        self.assertTrue(client.ns.dungeonMapData.dungeons)
        self.assertIn("WowTogether_DungeonData", client.data_addons_loaded)

    def test_guide_location_coverage_requires_locations_for_known_requirements(self):
        client = Client(quests=(), default_guide=True)
        rows = client.ns.catalogue.quests
        rows[900] = client.lua.table_from({
            "starts": client.lua.table_from([{"mapID": 1, "x": .1, "y": .2}]),
            "objectives": client.lua.table_from([{"mapID": 1, "x": .3, "y": .4}]),
            "ends": client.lua.table_from([{"mapID": 1, "x": .5, "y": .6}]),
            "requirements": client.lua.table_from({"mob": {"action": "kill"}}),
            "prerequisitesRead": True,
        }, recursive=True)
        rows[901] = client.lua.table_from({
            "starts": client.lua.table_from([{"mapID": 1, "x": .1, "y": .2}]),
            "ends": client.lua.table_from([{"mapID": 1, "x": .5, "y": .6}]),
            "requirements": client.lua.table_from({"item": {"action": "collect"}}),
            "objectiveLocationsIncomplete": True,
            "prerequisitesRead": True,
        }, recursive=True)
        records = client.lua.table_from([{"id": 900}, {"id": 901}], recursive=True)
        coverage = client.ns.GuideLocationCoverage(records)
        self.assertEqual(coverage.quests, 2)
        self.assertEqual(coverage.pickups, 2)
        self.assertEqual(coverage.objectives, 1)
        self.assertEqual(coverage.completeObjectives, 1)
        self.assertEqual(coverage.turnins, 2)
        self.assertEqual(coverage.details, 2)
        self.assertEqual(coverage.fullyLocated, 1)


if __name__ == "__main__":
    unittest.main()
