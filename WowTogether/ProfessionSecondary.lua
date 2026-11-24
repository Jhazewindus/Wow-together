local addonName, ns = ...

-- First Aid and Cooking: secondary professions planned like the six crafting ones.
--
-- Every recipe, with the skill it is learned at and the skill it turns
-- yellow, green and grey, its reagents and where it comes from, as read from
-- client build 1.60.1.70862 (wowforever.be First Aid recipe table, read
-- 22 November 2026). In Forever First Aid also makes the healing potions and
-- new curatives. Recipes whose spell ID that table does not give carry a
-- negative ID; the planner matches those to the client's recipe list by name.
--
-- Ranks are not all trained: Expert is a book sold by a vendor and Artisan
-- is the quest Triage. Those NPCs are listed with the rank they unlock so
-- the guide can send the player to them.
local ICON = "Interface\\Icons\\"
local function recipe(id, name, learn, yellow, green, grey, source, fee, output, made, icon, materials, note)
    return {id = id, name = name, learn = learn, yellow = yellow, green = green, grey = grey, source = source,
        trainingCost = fee, outputID = output, outputQuantity = made, icon = ICON .. icon, materials = materials, note = note}
end

local MANUAL = "Manual sold by Deneb Walker (Stromgarde, Arathi Highlands) or Balai Lok'Wein (Brackenwall, Dustwallow Marsh)"

local recipes = {
    recipe(3275, "Linen Bandage", 1, 30, 45, 60, "start", nil, 1251, 1, "inv_misc_bandage_15", {{2589, 1}}),
    recipe(1244431, "Minor Healing Potion", 1, 55, 75, 95, "trainer", 105, 118, 1, "inv_potion_49", {{3371, 1}, {2678, 1}, {2447, 1}}),
    recipe(1230117, "First Aid Kit", 20, 20, 22, 25, "trainer", 105, 279968, 1, "inv_misc_bandage_11", {{1251, 3}, {159, 1}}),
    recipe(3276, "Heavy Linen Bandage", 40, 50, 75, 100, "trainer", 105, 2581, 1, "inv_misc_bandage_18", {{2589, 2}}),
    recipe(1244432, "Lesser Healing Potion", 55, 85, 105, 125, "trainer", 157, 858, 1, "inv_potion_50", {{3371, 1}, {2678, 2}, {2450, 1}}),
    recipe(7934, "Anti-Venom", 80, 80, 115, 150, "trainer", 250, 6452, 3, "inv_misc_slime_01", {{1475, 1}}),
    recipe(3277, "Wool Bandage", 80, 80, 115, 150, "trainer", 250, 3530, 1, "inv_misc_bandage_14", {{2592, 1}}),
    recipe(-255716, "Simple Poultice", 90, 90, 125, 160, "trainer", 263, 255716, 3, "inv_10_alchemy2_quenchingfluid_color2", {{3174, 1}, {2678, 1}, {2723, 1}}),
    recipe(1244433, "Healing Potion", 110, 135, 155, 175, "trainer", 842, 929, 1, "inv_potion_51", {{3372, 1}, {2692, 1}, {2453, 1}}),
    recipe(3278, "Heavy Wool Bandage", 115, 115, 150, 185, "trainer", 1000, 3531, 1, "inv_misc_bandage_17", {{2592, 2}}),
    recipe(-255720, "Woolen Tourniquet", 120, 120, 155, 190, "trainer", 1263, 255720, 1, "inv_misc_bandage_05", {{2592, 2}, {2321, 2}}),
    recipe(7935, "Strong Anti-Venom", 130, 130, 165, 200, "drop", nil, 6453, 3, "inv_misc_slime_01", {{1288, 1}}),
    recipe(1262996, "Toxin Study", 140, 140, 142, 145, "drop", nil, 279940, 1, "inv_misc_potiona3", {{6452, 1}, {8544, 2}, {4470, 2}}),
    recipe(7928, "Silk Bandage", 150, 150, 180, 210, "trainer", 5000, 6450, 1, "inv_misc_bandage_01", {{4306, 1}}),
    recipe(1259343, "Clever Poultice", 160, 160, 190, 220, "drop", nil, 255717, 3, "inv_10_alchemy2_quenchingfluid_color4", {{1468, 1}, {3713, 1}, {2686, 1}}),
    recipe(-1710, "Greater Healing Potion", 175, 175, 195, 215, "drop", nil, 1710, 1, "inv_potion_52", {{3372, 1}, {2692, 3}, {3357, 1}}),
    recipe(7929, "Heavy Silk Bandage", 180, 180, 210, 240, "vendor", nil, 6451, 1, "inv_misc_bandage_02", {{4306, 2}}, MANUAL),
    recipe(10840, "Mageweave Bandage", 210, 210, 240, 270, "vendor", nil, 8544, 1, "inv_misc_bandage_19", {{4338, 1}}, MANUAL),
    recipe(1259348, "Leather Tourniquet", 220, 220, 250, 280, "unknown", nil, 255721, 1, "inv_misc_bandage_06", {{4304, 2}, {4291, 2}}),
    recipe(1259344, "Superior Poultice", 225, 225, 255, 285, "unknown", nil, 255718, 3, "inv_10_alchemy2_quenchingfluid_color3", {{7070, 1}, {2692, 1}, {2596, 1}}),
    recipe(1259341, "Potent Anti-Venom", 230, 230, 260, 290, "drop", nil, 255715, 3, "ability_creature_poison_02", {{255645, 1}}),
    recipe(-3928, "Superior Healing Potion", 230, 230, 250, 270, "unknown", nil, 3928, 1, "inv_potion_53", {{8925, 1}, {3713, 1}, {8838, 1}}),
    recipe(10841, "Heavy Mageweave Bandage", 240, 240, 270, 300, "trainer", nil, 8545, 1, "inv_misc_bandage_20", {{4338, 2}}),
    recipe(18629, "Runecloth Bandage", 260, 260, 290, 320, "trainer", nil, 14529, 1, "inv_misc_bandage_11", {{14047, 1}}),
    recipe(1259349, "Surgical Tourniquet", 280, 280, 310, 340, "unknown", nil, 255722, 1, "inv_misc_bandage_09", {{8170, 2}, {14047, 2}, {8343, 2}}),
    recipe(18630, "Heavy Runecloth Bandage", 290, 290, 320, 350, "trainer", nil, 14530, 1, "inv_misc_bandage_12", {{14047, 2}}),
    recipe(-13446, "Major Healing Potion", 290, 290, 310, 330, "vendor", nil, 13446, 1, "inv_potion_54", {{8925, 1}, {3713, 3}, {13464, 1}},
        "Manual sold by Pexmit (Mount Hyjal)"),
    recipe(1259345, "Powerful Poultice", 295, 295, 325, 355, "unknown", nil, 255719, 3, "inv_10_alchemy2_quenchingfluid_color1", {{7080, 1}, {2692, 1}, {2594, 1}}),
    recipe(1263001, "Plague Doctor's Laboratory", 300, 300, 300, 300, "unknown", nil, 279951, 1, "inv_10_alchemy_incenseholder_color1", {{4470, 2}, {6453, 2}, {14530, 5}}),
    recipe(23787, "Powerful Anti-Venom", 300, 300, 330, 360, "vendor", nil, 19440, 3, "inv_drink_14", {{19441, 1}},
        "Formula sold by the Argent Dawn quartermasters"),
    recipe(-232433, "Dense Runecloth Bandage", 315, 315, 327, 340, "vendor", nil, 232433, 1, "inv_misc_bandage_netherweave_heavy", {{14530, 2}},
        "Sold in Silithus"),
}

-- `rankOnly`: this NPC unlocks exactly that rank and is not a trainer for
-- anything else. `recipesFrom`: they do teach recipes, from that skill up.
local function trainer(faction, name, hub, mapID, x, y, maximum, rankOnly, recipesFrom)
    return {faction = faction, name = name, hub = hub, mapID = mapID, x = x / 100, y = y / 100, maximum = maximum or 150,
        dungeon = false, rankOnly = rankOnly, recipesFrom = recipesFrom}
end

local trainers = {
    trainer("Alliance", "Dannelor", "Craftsmen's Terrace, Darnassus", 1457, 51.6, 12.6),
    trainer("Alliance", "Shaina Fuller", "Cathedral of Light, Stormwind City", 1453, 42.8, 26.6),
    trainer("Alliance", "Nissa Firestone", "Great Forge, Ironforge", 1455, 54.8, 58.6),
    trainer("Alliance", "Byancie", "Dolanaar, Teldrassil", 1438, 55.2, 56.8),
    trainer("Alliance", "Michelle Belle", "Goldshire, Elwynn Forest", 1429, 43.4, 65.6),
    trainer("Alliance", "Thamner Pol", "Kharanos, Dun Morogh", 1426, 47.2, 52.6),
    trainer("Alliance", "Fremal Doohickey", "Menethil Harbor, Wetlands", 1437, 10.8, 61.2),
    trainer("Horde", "Arnok", "Valley of Spirits, Orgrimmar", 1454, 34.0, 84.4),
    trainer("Horde", "Mary Edras", "Rogues' Quarter, Undercity", 1458, 73.6, 55.6),
    trainer("Horde", "Pand Stonebinder", "Spirit Rise, Thunder Bluff", 1456, 29.6, 21.4),
    trainer("Horde", "Rawrk", "Razor Hill, Durotar", 1411, 54.0, 42.0),
    trainer("Horde", "Nurse Neela", "Brill, Tirisfal Glades", 1420, 61.8, 52.8),
    trainer("Horde", "Vira Younghoof", "Bloodhoof Village, Mulgore", 1412, 46.8, 60.8),
    -- Expert is a book, not a lesson: these vendors sell "Expert First Aid - Under Wraps".
    trainer("Alliance", "Deneb Walker (sells the Expert First Aid book)", "Stromgarde Keep, Arathi Highlands", 1417, 27.0, 58.8, 225, 225),
    trainer("Horde", "Balai Lok'Wein (sells the Expert First Aid book)", "Brackenwall Village, Dustwallow Marsh", 1445, 36.4, 30.4, 225, 225),
    -- Artisan is the quest Triage, from these doctors; they also teach the last bandages.
    trainer("Alliance", "Doctor Gustaf VanHowzen (quest: Triage)", "Theramore Isle, Dustwallow Marsh", 1445, 67.6, 48.8, 300, 300, 240),
    trainer("Horde", "Doctor Gregory Victor (quest: Triage)", "Hammerfall, Arathi Highlands", 1417, 73.4, 36.8, 300, 300, 240),
}

-- Cooking.
--
-- Every dish up to skill 125 is from the same build's recipe table, with its
-- own thresholds, reagents and source. That table is not served in full
-- above 125, so beyond it only the five dishes the source's two 1-300 routes
-- use are listed (`estimated`): their reagents and item IDs are the source's,
-- their thresholds are Classic's (learned, +40, +60, +80, the pattern every
-- unchanged dish below 125 follows) and agree with the craft counts the
-- source gives for those routes. Other dishes above 125 are picked up from
-- the client once learned, without thresholds. Winter Veil dishes are marked
-- seasonal and are never suggested unless already known.
local FOOD = "INV_Misc_Food_15"
local function dish(id, name, learn, yellow, green, grey, source, fee, output, made, materials, note)
    return recipe(id, name, learn, yellow, green, grey, source, fee, output, made, FOOD, materials, note)
end
local FISH_VENDOR = {
    smallfish = "Recipe sold by Catherine Leland (Stormwind) or Sewa Mistrunner (Thunder Bluff)",
    snapper = "Recipe sold by Tharynn Bouden (Goldshire) or Naal Mistrunner (Thunder Bluff)",
    catfish = "Recipe sold by Catherine Leland (Stormwind) or Naal Mistrunner (Thunder Bluff)",
    trout = "Recipe sold by Tansy Puddlefizz (Ironforge) or Shankys (Orgrimmar)",
    redgill = "Recipe sold by Kelsey Yance (Booty Bay)",
    salmon = "Recipe sold by Gikkix (Steamwheedle Port, Tanaris)",
}

local cooking = {
    dish(7751, "Brilliant Smallfish", 1, 45, 65, 85, "vendor", nil, 6290, 1, {{6291, 1}}, FISH_VENDOR.smallfish),
    dish(-2679, "Charred Wolf Meat", 1, 45, 65, 85, "start", nil, 2679, 1, {{2672, 1}}),
    dish(-12224, "Crispy Bat Wing", 1, 45, 65, 85, "vendor", nil, 12224, 1, {{12223, 1}, {2678, 1}}),
    dish(-17197, "Gingerbread Cookie", 1, 45, 65, 85, "seasonal", nil, 17197, 1, {{6889, 1}, {17194, 1}}),
    dish(-6888, "Herb Baked Egg", 1, 45, 65, 85, "start", nil, 6888, 1, {{6889, 1}, {2678, 1}}),
    dish(-2681, "Roasted Boar Meat", 1, 45, 65, 85, "start", nil, 2681, 1, {{769, 1}}),
    dish(-787, "Slitherskin Mackerel", 1, 45, 65, 85, "vendor", nil, 787, 1, {{6303, 1}}),
    dish(-5472, "Kaldorei Spider Kabob", 10, 50, 70, 90, "quest", nil, 5472, 1, {{5465, 1}}),
    dish(-2680, "Spiced Wolf Meat", 10, 50, 70, 90, "trainer", 50, 2680, 1, {{2672, 1}, {2678, 1}}),
    dish(-5473, "Scorpid Surprise", 20, 60, 80, 100, "vendor", nil, 5473, 1, {{5466, 1}}),
    dish(-2888, "Beer Basted Boar Ribs", 25, 60, 80, 100, "vendor", nil, 2888, 1, {{2886, 1}, {2894, 1}}),
    dish(1249957, "Peace Tea", 25, 30, 37, 45, "drop", nil, 249865, 1, {{159, 1}, {2447, 2}}),
    dish(1270633, "Skywall Souffle", 25, 30, 37, 45, "quest", nil, 263509, 1, {{6889, 2}, {10284, 1}}),
    dish(1250156, "Tasty Raptor Bites", 25, 35, 55, 75, "drop", nil, 250079, 1, {{3685, 1}, {2678, 4}}),
    dish(1249963, "Venomous Smoothie", 25, 30, 37, 45, "favor", nil, 249871, 1, {{159, 1}, {2678, 1}, {1475, 1}}),
    dish(-17198, "Egg Nog", 35, 75, 95, 115, "seasonal", nil, 17198, 1, {{6889, 1}, {1179, 1}, {17196, 1}, {17194, 1}}),
    dish(1270635, "Pincer Bites", 35, 40, 47, 55, "quest", nil, 263512, 1, {{2675, 1}, {10284, 1}}),
    dish(-5474, "Roasted Kodo Meat", 35, 75, 95, 115, "vendor", nil, 5474, 2, {{5467, 1}, {2678, 1}}),
    dish(-6890, "Smoked Bear Meat", 40, 80, 100, 120, "vendor", nil, 6890, 1, {{3173, 1}}),
    dish(-5525, "Boiled Clams", 50, 90, 110, 130, "trainer", 100, 5525, 1, {{5503, 1}, {159, 1}}),
    dish(-2684, "Coyote Steak", 50, 90, 110, 130, "trainer", 100, 2684, 1, {{2673, 1}}),
    dish(-5476, "Fillet of Frenzy", 50, 90, 110, 130, "vendor", nil, 5476, 2, {{5468, 1}, {2678, 1}}),
    dish(-724, "Goretusk Liver Pie", 50, 90, 110, 130, "vendor", nil, 724, 1, {{723, 1}, {2678, 1}}),
    dish(-6316, "Loch Frenzy Delight", 50, 90, 110, 130, "vendor", nil, 6316, 1, {{6317, 1}, {2678, 1}}),
    dish(7753, "Longjaw Mud Snapper", 50, 90, 110, 130, "vendor", nil, 4592, 1, {{6289, 1}}, FISH_VENDOR.snapper),
    dish(-5095, "Rainbow Fin Albacore", 50, 90, 110, 130, "vendor", nil, 5095, 1, {{6361, 1}}),
    dish(-5477, "Strider Stew", 50, 90, 110, 130, "vendor", nil, 5477, 2, {{5469, 1}, {4536, 1}}),
    dish(-3220, "Blood Sausage", 60, 100, 120, 140, "vendor", nil, 3220, 2, {{3173, 1}, {3172, 1}, {3174, 1}}),
    dish(-7676, "Thistle Tea", 60, 100, 120, 140, "vendor", nil, 7676, 1, {{2452, 1}, {159, 1}}),
    dish(1250157, "Breakfast Omelette", 75, 80, 87, 95, "drop", nil, 250080, 1, {{6889, 1}, {2678, 4}}),
    dish(-2683, "Crab Cake", 75, 115, 135, 155, "trainer", 200, 2683, 1, {{2674, 1}, {2678, 1}}),
    dish(1250154, "Twice-Spiced Raptor Slice", 75, 115, 132, 150, "quest", nil, 250077, 1, {{12184, 1}, {2678, 2}}),
    dish(-733, "Westfall Stew", 75, 115, 135, 155, "vendor", nil, 733, 1, {{729, 1}, {730, 1}, {731, 1}}),
    dish(-3662, "Crocolisk Steak", 80, 120, 140, 160, "vendor", nil, 3662, 1, {{2924, 1}, {2678, 1}}),
    dish(-2687, "Dry Pork Ribs", 80, 120, 140, 160, "trainer", 150, 2687, 1, {{2677, 1}, {2678, 1}}),
    dish(-21072, "Smoked Sagefish", 80, 120, 140, 160, "vendor", nil, 21072, 1, {{21071, 1}, {2678, 1}}),
    dish(-2682, "Cooked Crab Claw", 85, 125, 145, 165, "vendor", nil, 2682, 1, {{2675, 1}, {2678, 1}}),
    dish(-6657, "Savory Deviate Delight", 85, 125, 145, 165, "drop", nil, 6657, 1, {{6522, 1}, {2678, 1}}),
    dish(1252566, "Savory Whimsyfin Delight", 85, 125, 145, 165, "drop", nil, 251525, 1, {{251524, 1}, {2678, 1}}),
    dish(-5526, "Clam Chowder", 90, 130, 150, 170, "vendor", nil, 5526, 1, {{5503, 1}, {1179, 1}, {2678, 1}}),
    dish(-5478, "Dig Rat Stew", 90, 130, 150, 170, "quest", nil, 5478, 2, {{5051, 1}}),
    dish(-3663, "Murloc Fin Soup", 90, 130, 150, 170, "vendor", nil, 3663, 1, {{1468, 2}, {2692, 1}}),
    dish(7755, "Bristle Whisker Catfish", 100, 140, 160, 180, "vendor", nil, 4593, 1, {{6308, 1}}, FISH_VENDOR.catfish),
    dish(-5479, "Crispy Lizard Tail", 100, 140, 160, 180, "vendor", nil, 5479, 2, {{5470, 1}, {2692, 1}}),
    dish(-1082, "Redridge Goulash", 100, 135, 155, 175, "vendor", nil, 1082, 1, {{1081, 1}, {1080, 1}}),
    dish(1249958, "Royal Tea", 100, 105, 115, 125, "drop", nil, 249866, 1, {{1179, 1}, {785, 2}}),
    dish(-1017, "Seasoned Wolf Kabob", 100, 140, 160, 180, "vendor", nil, 1017, 3, {{1015, 2}, {2678, 1}}),
    dish(1249964, "Slimy Smoothie", 100, 105, 112, 120, "favor", nil, 249872, 1, {{1179, 1}, {2678, 2}, {3174, 1}}),
    dish(-3726, "Big Bear Steak", 110, 150, 170, 190, "vendor", nil, 3726, 1, {{3730, 1}, {2692, 1}}),
    dish(-3666, "Gooey Spider Cake", 110, 150, 170, 190, "vendor", nil, 3666, 1, {{2251, 2}, {2692, 1}}),
    dish(-5480, "Lean Venison", 110, 150, 170, 190, "vendor", nil, 5480, 2, {{5471, 1}, {2678, 4}}),
    dish(-2685, "Succulent Pork Ribs", 110, 130, 150, 170, "vendor", nil, 2685, 1, {{2677, 2}, {2692, 1}}),
    dish(-3664, "Crocolisk Gumbo", 120, 160, 180, 200, "vendor", nil, 3664, 1, {{3667, 1}, {2692, 1}}),
    dish(-5527, "Goblin Deviled Clams", 125, 165, 185, 205, "trainer", 300, 5527, 1, {{5504, 1}, {2692, 1}}),
    dish(-3727, "Hot Lion Chops", 125, 175, 195, 215, "vendor", nil, 3727, 1, {{3731, 1}, {2692, 1}}),
    -- Above 125: the dishes of the source's routes, with Classic thresholds.
    dish(-4457, "Barbecued Buzzard Wing", 175, 215, 235, 255, "trainer", nil, 4457, 1, {{3404, 1}, {2692, 1}}),
    dish(20916, "Mithril Headed Trout", 175, 215, 235, 255, "vendor", nil, 8364, 1, {{8365, 1}}, FISH_VENDOR.trout),
    dish(-17222, "Spider Sausage", 200, 240, 260, 280, "trainer", nil, 17222, 1, {{12205, 2}}),
    dish(18241, "Filet of Redgill", 225, 265, 285, 305, "vendor", nil, 13930, 1, {{13758, 1}}, FISH_VENDOR.redgill),
    dish(18244, "Poached Sunscale Salmon", 250, 290, 310, 330, "vendor", nil, 13932, 1, {{13760, 1}}, FISH_VENDOR.salmon),
}
for index = #cooking - 4, #cooking do cooking[index].estimated = true end

local cooks = {
    trainer("Alliance", "Alegorn", "Craftsmen's Terrace, Darnassus", 1457, 49.8, 21.0),
    trainer("Alliance", "Cook Ghilm", "Gol'Bolar Quarry, Dun Morogh", 1426, 68.4, 54.6),
    trainer("Alliance", "Crystal Boughman", "Lakeshire, Redridge Mountains", 1433, 22.8, 43.6),
    trainer("Alliance", "Daryl Riknussun", "The Great Forge, Ironforge", 1455, 60.4, 38.0),
    trainer("Alliance", "Gremlock Pilsnor", "Kharanos, Dun Morogh", 1426, 47.6, 52.4),
    trainer("Alliance", "Stephen Ryback", "Old Town, Stormwind City", 1453, 78.2, 53.0),
    trainer("Alliance", "Tomas", "Goldshire, Elwynn Forest", 1429, 44.2, 66.0),
    trainer("Alliance", "Zarrin", "Dolanaar, Teldrassil", 1438, 57.0, 61.2),
    trainer("Alliance", "Katherine Lee", "Dalaran, Alterac Mountains", 1416, 12.6, 65.8),
    trainer("Horde", "Aska Mistrunner", "Thunder Bluff", 1456, 51.0, 52.8),
    trainer("Horde", "Eunice Burch", "Undercity", 1458, 62.6, 44.6),
    trainer("Horde", "William Pickman", "Brill, Tirisfal Glades", 1420, 61.8, 51.6),
    trainer("Horde", "Mudduk", "Grom'gol Base Camp, Stranglethorn Vale", 1434, 31.4, 28.0),
    trainer("Horde", "Pyall Silentstride", "Bloodhoof Village, Mulgore", 1412, 45.0, 61.6),
    trainer("Horde", "Slagg", "Hammerfall, Arathi Highlands", 1417, 74.0, 33.8),
    trainer("Horde", "Zamja", "The Drag, Orgrimmar", 1454, 57.6, 53.6),
    -- Expert is the Expert Cookbook (10 gold); Artisan is the quest Clamlette Surprise.
    trainer("Alliance", "Shandrina (sells the Expert Cookbook)", "near Talondeep Path, Ashenvale", 1440, 49.6, 67.0, 225, 225),
    trainer("Horde", "Wulan (sells the Expert Cookbook)", "Shadowprey Village, Desolace", 1443, 26.2, 69.8, 225, 225),
    trainer("Both", "Dirge Quikcleave (quest: Clamlette Surprise)", "Gadgetzan, Tanaris", 1446, 52.6, 28.0, 300, 300),
}

ns.professionExtraData = {
    [185] = {
        id = 185, name = "Cooking", slug = "cooking", icon = ICON .. FOOD, secondary = true, partialAbove = 125,
        recipes = cooking, trainers = cooks,
        ranks = {
            {name = "Apprentice", maximum = 75, skill = 0, level = 0},
            {name = "Journeyman", maximum = 150, skill = 50, level = 0},
            {name = "Expert", maximum = 225, skill = 125, level = 0},
            {name = "Artisan", maximum = 300, skill = 225, level = 35},
        },
    },
    [129] = {
        id = 129, name = "First Aid", slug = "first-aid", icon = ICON .. "Spell_Holy_SealOfSacrifice", secondary = true,
        recipes = recipes, trainers = trainers,
        ranks = {
            {name = "Apprentice", maximum = 75, skill = 0, level = 0},
            {name = "Journeyman", maximum = 150, skill = 50, level = 0},
            {name = "Expert", maximum = 225, skill = 125, level = 0},
            {name = "Artisan", maximum = 300, skill = 225, level = 35},
        },
    },
}
