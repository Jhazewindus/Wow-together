local addonName, ns = ...

-- Which test build this is. Test builds all carry the release version
-- number, so a report could not say which one it came from. Whoever packages
-- a test build sets a string here (date, time, a word for what changed); the
-- login line, /wt probe, /wt perf and /wt hud print it. In the repository
-- and in a release it stays nil, and nothing is printed.
ns.testBuild = nil
