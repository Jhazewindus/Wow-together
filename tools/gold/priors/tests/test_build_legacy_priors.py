import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import build_legacy_priors as priors


class LegacyPriorsTests(unittest.TestCase):
    def test_extracts_only_numeric_top_level_fix_keys(self):
        source = """
        local fixes = {}
        function fixes:Load()
            return {
                [100] = { -- top-level id
                    nested = { [900] = true },
                    text = \"[800] = { not syntax }\",
                },
                [200] = {},
                -- [300] = {} ignored comment
            }
        end
        """
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixes.lua"
            path.write_text(source, encoding="utf-8")
            self.assertEqual(priors.extract_fix_ids(path), {100, 200})

    def test_build_marks_only_matching_npc_and_item_ids(self):
        facts = {
            "creature_template": [
                {"Entry": 10, "Name": "Changed npc", "MinLevel": 1, "MaxLevel": 2, "Rank": 0, "LootId": 10},
                {"Entry": 11, "Name": "Same npc", "MinLevel": 3, "MaxLevel": 4, "Rank": 1, "LootId": 11},
            ],
            "creature": [
                {"id": 10, "map": 0, "position_x": 12.5, "position_y": 20, "spawntimesecsmin": 30, "spawntimesecsmax": 45},
            ],
            "gameobject_template": [{"entry": 20, "name": "Object", "type": 3, "data1": 20}],
            "gameobject": [
                {"id": 20, "map": 1, "position_x": 2, "position_y": 3, "spawntimesecsmin": 60, "spawntimesecsmax": 60},
            ],
            "item_template": [
                {"entry": 30, "name": "Changed item", "startquest": 0, "BuyPrice": 5},
                {"entry": 31, "name": "Same item", "startquest": 4, "BuyPrice": 6},
            ],
            "creature_loot_template": [{"entry": 10, "item": 30, "ChanceOrQuestChance": -100, "mincountOrRef": 1}],
            "gameobject_loot_template": [{"entry": 20, "item": 31, "ChanceOrQuestChance": 5, "mincountOrRef": 2}],
        }
        outputs = priors.build_outputs(facts, {"npc": {10}, "item": {30}})
        npc_rows = outputs["creatures.json"]["rows"]
        item_rows = outputs["items.json"]["rows"]
        self.assertEqual([row["changed"] for row in npc_rows], [True, False])
        self.assertEqual([row["changed"] for row in item_rows], [True, False])
        self.assertEqual(npc_rows[0]["spawns"][0]["respawnSecondsMax"], 45)
        self.assertEqual(outputs["gameobjects.json"]["rows"][0]["spawns"][0]["respawnSecondsMin"], 60)
        self.assertEqual(outputs["creature_loot.json"]["rows"][0]["itemId"], 30)
        self.assertEqual(outputs["gameobject_loot.json"]["rows"][0]["ownerLootId"], 20)

    def test_output_has_source_pins_gpl_and_restriction_notice(self):
        outputs = priors.build_outputs(
            {
                "creature_template": [], "creature": [], "gameobject_template": [], "gameobject": [],
                "item_template": [], "creature_loot_template": [], "gameobject_loot_template": [],
            },
            {"npc": set(), "item": set()},
        )
        for payload in outputs.values():
            self.assertNotIn("generated", payload)
            self.assertEqual(payload["provenance"]["commit"], priors.CMANGOS_COMMIT)
            self.assertEqual(payload["provenance"]["snapshotSha256"], priors.CMANGOS_SHA256)
            self.assertEqual(payload["provenance"]["license"], "GPL-3.0")
            self.assertIn("not affiliated with Blizzard", payload["copyrightNotice"])
            self.assertIn("non-commercial", payload["copyrightNotice"])
        self.assertEqual(outputs["creatures.json"]["provenance"]["changedFlag"]["commit"], priors.QUESTIE_COMMIT)
        self.assertEqual(outputs["items.json"]["provenance"]["changedFlag"]["use"], "ID membership only; no Questie fact values are imported.")
        self.assertNotIn("changedFlag", outputs["gameobjects.json"]["provenance"])

    def test_pinned_manifests_match_external_manifest_hashes(self):
        source = json.loads(priors.SOURCE_MANIFEST.read_text(encoding="utf-8"))
        upstream = json.loads(priors.QUESTIE_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(source["cmangos"]["sha256"], priors.CMANGOS_SHA256)
        self.assertEqual(source["questieChangedIdFlags"]["commit"], upstream["commit"])
        for item in source["questieChangedIdFlags"]["files"].values():
            self.assertEqual(upstream["files_sha256"][item["path"]], item["sha256"])


if __name__ == "__main__":
    unittest.main()
