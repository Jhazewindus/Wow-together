local addonName, ns = ...

-- Approximate mesa footprints reviewed against the pre-Cataclysm zone map.
-- Geography only: no borrowed routing implementation, collision or elevation
-- data. Provenance and the limits of these outlines are in TRAVEL_DATA.md.
ns.travelTerrainData = {schema = 1, maps = {
    [1441] = {name = "Thousand Needles", padding = 0.005, obstacles = {
        {id = "western-needle", name = "the pinnacle", polygon = {{0.272,0.336},{0.289,0.329},{0.302,0.353},{0.291,0.385},{0.271,0.377}}},
        {id = "northern-needle", name = "the pinnacle", polygon = {{0.325,0.328},{0.340,0.322},{0.352,0.345},{0.344,0.373},{0.327,0.369}}},
        {id = "western-central-needle", name = "the pinnacle", polygon = {{0.337,0.436},{0.353,0.431},{0.367,0.446},{0.362,0.477},{0.343,0.480},{0.332,0.463}}},
        {id = "central-needle", name = "the pinnacle", polygon = {{0.379,0.458},{0.393,0.450},{0.405,0.469},{0.399,0.496},{0.383,0.496},{0.375,0.478}}},
        {id = "north-freewind-needle", name = "the pinnacle", polygon = {{0.438,0.407},{0.451,0.402},{0.465,0.424},{0.456,0.455},{0.439,0.453},{0.431,0.434}}},
        {id = "freewind", name = "Freewind Post's mesa", elevated = true, polygon = {{0.437,0.491},{0.449,0.477},{0.465,0.486},{0.474,0.511},{0.463,0.530},{0.441,0.527},{0.430,0.510}}},
        {id = "east-freewind-needle", name = "the pinnacle", polygon = {{0.484,0.449},{0.495,0.444},{0.504,0.462},{0.499,0.487},{0.485,0.486},{0.478,0.471}}},
        {id = "eastern-central-needle", name = "the pinnacle", polygon = {{0.527,0.506},{0.541,0.501},{0.553,0.520},{0.546,0.546},{0.529,0.546},{0.520,0.529}}},
        {id = "southern-needle", name = "the pinnacle", polygon = {{0.424,0.546},{0.439,0.541},{0.448,0.563},{0.438,0.582},{0.422,0.577},{0.417,0.558}}},
        {id = "south-freewind-needle", name = "the pinnacle", polygon = {{0.470,0.543},{0.486,0.538},{0.498,0.556},{0.492,0.577},{0.472,0.579},{0.463,0.562}}},
        {id = "east-valley-needle", name = "the pinnacle", polygon = {{0.608,0.500},{0.622,0.494},{0.635,0.515},{0.628,0.548},{0.610,0.550},{0.601,0.528}}},
        {id = "south-east-needle", name = "the pinnacle", polygon = {{0.620,0.575},{0.633,0.570},{0.645,0.590},{0.638,0.617},{0.621,0.617},{0.613,0.596}}},
    }},
}}
