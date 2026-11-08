local addonName, ns = ...

-- Bundled walkable ground, as road polylines in normalized zone-map
-- coordinates (0..1). Each polyline is a sequence of {x, y} pairs in walking
-- order; the engine interpolates long segments, joins polylines whose points
-- lie within a few yards of each other, and treats every segment as proven
-- ground (no terrain-silhouette check, no off-road penalty).
--
-- This is the same shape that `/wt roads export` prints from ground this
-- character has actually walked, so verified in-game recordings can be
-- pasted here and shipped to the whole party. Keep entries that were walked
-- in the beta; anything traced from map art should say so in `source`.
--
-- Per map:  [mapID] = {name = "...", roads = {{id = "...", source = "...",
--                      points = {{x, y}, ...}}, ...}}
ns.travelRoadData = {schema = 1, maps = {
    -- Ashenvale (1440): the Astranaar - Splintertree Post trunk road and the
    -- Felwood road, traced approximately from the zone map. Replace these
    -- with recorded ground (`/wt roads export`) after walking them once.
    [1440] = {name = "Ashenvale", roads = {
        {id = "astranaar-splintertree", source = "map-art-trace", points = {
            {0.345, 0.480}, {0.360, 0.500}, {0.385, 0.535}, {0.394, 0.574},
            {0.419, 0.574}, {0.447, 0.567}, {0.474, 0.560}, {0.496, 0.553},
            {0.541, 0.546}, {0.557, 0.535}, {0.580, 0.550}, {0.610, 0.580},
            {0.630, 0.596}, {0.674, 0.581}, {0.710, 0.603}, {0.733, 0.617}}},
        {id = "felwood-road", source = "map-art-trace", points = {
            {0.559, 0.268}, {0.560, 0.300}, {0.565, 0.330}, {0.575, 0.360},
            {0.589, 0.390}, {0.602, 0.420}, {0.615, 0.455}, {0.626, 0.480},
            {0.634, 0.505}, {0.630, 0.540}, {0.620, 0.575}, {0.610, 0.580}}},
        {id = "darkshore-maestra-astranaar", source = "map-art-trace", points = {
            {0.280, 0.128}, {0.292, 0.126}, {0.287, 0.169}, {0.274, 0.211},
            {0.263, 0.261}, {0.260, 0.318}, {0.263, 0.361}, {0.269, 0.411},
            {0.265, 0.439}, {0.274, 0.464}, {0.292, 0.468}, {0.325, 0.460},
            {0.345, 0.480}}},
    }},
}}
