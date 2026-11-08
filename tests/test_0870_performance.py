"""Fixed route stays repeatable after Questie data updates and caches geometry."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from benchmark_addon import client, digest  # noqa: E402


class RouteGeometryCacheTests(unittest.TestCase):
    def test_mulgore_order_is_stable_and_repeated_distances_are_cached(self):
        c = client()
        guide = c.ns.ZoneGuideForMap(1412, True)
        c.ns.GenerateFixedGuide(guide, False)

        fingerprint = digest("|".join(":".join(str(stop[key]) for key in
            ("id", "kind", "mapID", "x", "y", "guideStep")) for stop in guide.fixedPlan.values()))
        self.assertEqual(fingerprint, "bc436338f5f35d5a26a8076e0f7a42993ee973d890ab7adca5d0388126737664")
        planned_quests = [int(stop['id']) for stop in guide.fixedPlan.values() if stop['kind'] == 'q']
        self.assertIn(98430, planned_quests)  # Questie now supplies its Mulgore starter.

        cache = guide.optimization.geometryCache
        self.assertGreater(cache.calls, 0)
        self.assertGreater(cache.hits, cache.misses)
        self.assertEqual(cache.calls, cache.hits + cache.misses)
        self.assertEqual(cache.resets, 0)

    def test_guide_browser_reuses_prerequisite_walks_for_one_fresh_query(self):
        c = client()
        query = c.ns.NewQuestQuery()
        choices = c.ns.LevelingGuideChoices(True, query, "party")
        cache = query.levelPathCache
        self.assertTrue(cache)
        size = lambda: sum(sum(1 for _ in paths.items()) for _, paths in cache.items())
        before = size()

        for index in range(1, len(choices) + 1):
            c.ns.GuideLevelSuitable(choices[index], query)

        after = size()
        self.assertGreater(before, 0)
        self.assertEqual(after, before, "Repeated browser checks should reuse this query's prerequisite results")


if __name__ == "__main__":
    unittest.main()
