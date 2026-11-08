import json
import tempfile
import unittest
from pathlib import Path

from tools.ingest_observations import ingest
from tools.promote_candidates import promote


def row(kind, observer, **values):
    return {"event": kind, "_observer": observer, "_source_file": observer + ".json", "build": "70009", **values}


class ObservationIngestTests(unittest.TestCase):
    def test_pickups_require_two_nearby_observations_and_use_a_median(self):
        events = [
            row("pickup-location", "Alice", questID=10, npcID=42, mapID=1, x=.2, y=.4, session=1),
            row("pickup-location", "Bob", questID=10, npcID=42, mapID=1, x=.202, y=.4, session=1),
            row("pickup-location", "Solo", questID=11, npcID=43, mapID=1, x=.5, y=.5, session=1),
        ]
        result = ingest(events)["candidates"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["kind"], "npc-location")
        self.assertEqual(result[0]["facts"]["x"], .201)
        self.assertEqual(result[0]["confidence"]["observers"], 2)

    def test_objective_candidate_requires_three_samples_and_multiple_characters_or_sessions(self):
        events = [
            row("objective-area", "Alice", questID=12, objectiveIndex=1, mapID=1, x=.2, y=.4, n=3, session=1),
            row("objective-area", "Alice", questID=12, objectiveIndex=1, mapID=1, x=.2, y=.4, n=1, session=2),
        ]
        candidates = ingest(events)["candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["kind"], "objective-facts")
        self.assertEqual(candidates[0]["facts"]["samples"], 4)

    def test_skip_signal_is_review_only_and_requires_three_observers(self):
        events = [row("skip-quest", name, questID=13, session=1) for name in ("Alice", "Bob", "Cara")]
        candidate, = ingest(events)["candidates"]
        self.assertEqual(candidate["kind"], "skip-signal")

    def test_promotion_requires_observers_and_conflicts_stay_for_human_review(self):
        candidates = {"candidates": [
            {"id": "ready", "questID": 20, "title": "Known Quest", "kind": "npc-location",
             "facts": {"mapID": 1, "x": .3, "y": .4}, "source": "Observed by Alice and Bob on build 70009.",
             "confidence": {"observers": 2, "sessions": 2, "builds": ["70009"]}},
            {"id": "conflict", "questID": 21, "title": "Conflict Quest", "kind": "npc-location",
             "facts": {"mapID": 1, "x": .8, "y": .9}, "source": "Observed by Alice and Bob on build 70009.",
             "confidence": {"observers": 2, "sessions": 2, "builds": ["70009"]}},
            {"id": "single", "questID": 22, "title": "Solo Quest", "kind": "npc-location",
             "facts": {}, "source": "One observer.", "confidence": {"observers": 1}},
        ]}
        current = [{"questID": 21, "title": "Conflict Quest", "stageCorrection": {
            "kind": "npc-location", "roles": ["starts"], "after": {"mapID": 1, "x": .1, "y": .1}}}]
        updated, conflicts = promote(candidates, current, 2)
        self.assertEqual([row["promotedFrom"] for row in updated[1:]], ["ready"])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("Conflict Quest", conflicts[0])


if __name__ == "__main__":
    unittest.main()
