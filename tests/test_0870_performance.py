"""Route compilation cache reduces repeated work without changing guide order."""
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
        self.assertEqual(fingerprint, "851e8ebcc4b09a8a99f0e2394adcfddade93522fb13ab20be41385b851533dbd")

        cache = guide.optimization.geometryCache
        self.assertGreater(cache.calls, 0)
        self.assertGreater(cache.hits, cache.misses)
        self.assertEqual(cache.calls, cache.hits + cache.misses)
        self.assertEqual(cache.resets, 0)


if __name__ == "__main__":
    unittest.main()
