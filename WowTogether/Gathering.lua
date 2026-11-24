local addonName, ns = ...

-- Gathering paths: Mining, Herbalism, Skinning and Fishing.
--
-- A gathering profession has no recipe to choose. What a player needs to
-- know is which nodes or beasts still give skill at their current skill,
-- where those are for their faction and level, what unlocks next, and when
-- to visit a trainer. This file answers that from the character's own skill,
-- level, faction and zone.
--
-- Facts and where they come from (checked 22 November 2026):
--   * Skill needed for every vein and herb is Classic's, unchanged in
--     Forever; guides reading the launch client agree on every figure used
--     here. A node gives a point every time until 25 above its requirement,
--     less often after that, and nothing from 100 above.
--   * Skinning: beasts up to level 10 need skill 1, levels 11-20 need
--     (level - 10) x 10, level 21 and up need level x 5. The server decides
--     this; it is Classic's rule and Forever guides confirm it.
--   * Veins turn yellow 25 above their requirement, green 65 above and
--     grey 100 above in Forever (wowforever.be vein table, launch build);
--     herbs are taken to turn green 50 above, as in Classic.
--   * Fishing levels by the number of fish caught, wherever they are caught.
--     Each zone has a skill from which a cast is possible and a skill from
--     which every cast is a catch; lures add to the skill. Expert is a book
--     from Old Man Heming in Booty Bay and Artisan is Nat Pagle's quest
--     (wowforever.be Fishing guide, read 22 November 2026).
--   * Zones are where each node is found in Classic. Forever's spawns have
--     not been verified; of its new zones only Zephras Isle and Mount Hyjal
--     appear, where a source names them.
-- Nothing here gathers, targets or travels for the player.

local MINING, HERBALISM, SKINNING, FISHING = 186, 182, 393, 356
ns.GATHERING_IDS = {MINING, HERBALISM, SKINNING, FISHING}
-- How far above its requirement a node turns green.
local GREEN = {[MINING] = 65, [HERBALISM] = 50}

-- Level range and home faction of each zone, to keep advice to places the
-- character can reasonably be. Contested zones have no faction.
local ZONES = {
    ["Durotar"] = {1, 10, "Horde"}, ["Mulgore"] = {1, 10, "Horde"}, ["Tirisfal Glades"] = {1, 10, "Horde"},
    ["Elwynn Forest"] = {1, 10, "Alliance"}, ["Dun Morogh"] = {1, 10, "Alliance"}, ["Teldrassil"] = {1, 10, "Alliance"},
    ["The Barrens"] = {10, 25, "Horde"}, ["Silverpine Forest"] = {10, 20, "Horde"},
    ["Westfall"] = {10, 20, "Alliance"}, ["Loch Modan"] = {10, 20, "Alliance"}, ["Darkshore"] = {10, 20, "Alliance"},
    ["Redridge Mountains"] = {15, 25, "Alliance"}, ["Duskwood"] = {18, 30, "Alliance"}, ["Wetlands"] = {20, 30, "Alliance"},
    ["Stonetalon Mountains"] = {15, 27}, ["Ashenvale"] = {18, 30}, ["Hillsbrad Foothills"] = {20, 30},
    ["Thousand Needles"] = {25, 35}, ["Alterac Mountains"] = {30, 40}, ["Arathi Highlands"] = {30, 40},
    ["Desolace"] = {30, 40}, ["Stranglethorn Vale"] = {30, 45}, ["Dustwallow Marsh"] = {35, 45},
    ["Badlands"] = {35, 45}, ["Swamp of Sorrows"] = {35, 45}, ["Feralas"] = {40, 50}, ["The Hinterlands"] = {40, 50},
    ["Tanaris"] = {40, 50}, ["Searing Gorge"] = {43, 50}, ["Azshara"] = {45, 55}, ["Blasted Lands"] = {45, 55},
    ["Un'Goro Crater"] = {48, 55}, ["Felwood"] = {48, 55}, ["Burning Steppes"] = {50, 58},
    ["Western Plaguelands"] = {51, 58}, ["Eastern Plaguelands"] = {53, 60}, ["Winterspring"] = {53, 60},
    ["Silithus"] = {55, 60}, ["Zephras Isle"] = {1, 10}, ["Mount Hyjal"] = {58, 60}, ["Moonglade"] = {55, 60},
    ["Deadwind Pass"] = {55, 60},
}

local STARTING = {"Durotar", "Mulgore", "Tirisfal Glades", "Elwynn Forest", "Dun Morogh", "Teldrassil"}
local SECOND = {"The Barrens", "Silverpine Forest", "Westfall", "Loch Modan", "Darkshore"}

local function with(first, more)
    local list = {}
    for _, zone in ipairs(first) do list[#list + 1] = zone end
    for _, zone in ipairs(more or {}) do list[#list + 1] = zone end
    return list
end

local NODES = {
    [MINING] = {
        {"Copper Vein", 1, with(with(STARTING, SECOND), {"Zephras Isle"})},
        {"Tin Vein", 65, {"The Barrens", "Silverpine Forest", "Westfall", "Loch Modan", "Darkshore", "Redridge Mountains",
            "Stonetalon Mountains", "Ashenvale", "Duskwood", "Wetlands", "Hillsbrad Foothills", "Thousand Needles"}},
        {"Silver Vein", 75, {"The Barrens", "Redridge Mountains", "Ashenvale", "Duskwood", "Wetlands", "Hillsbrad Foothills",
            "Thousand Needles", "Arathi Highlands"}},
        {"Iron Deposit", 125, {"Thousand Needles", "Alterac Mountains", "Arathi Highlands", "Desolace", "Stranglethorn Vale",
            "Dustwallow Marsh", "Badlands", "Swamp of Sorrows"}},
        {"Gold Vein", 155, {"Thousand Needles", "Alterac Mountains", "Arathi Highlands", "Desolace", "Stranglethorn Vale",
            "Badlands", "Tanaris"}},
        {"Mithril Deposit", 175, {"Stranglethorn Vale", "Badlands", "Swamp of Sorrows", "Feralas", "The Hinterlands", "Tanaris",
            "Searing Gorge", "Azshara", "Blasted Lands", "Felwood", "Burning Steppes"}},
        {"Truesilver Deposit", 230, {"Badlands", "Feralas", "The Hinterlands", "Tanaris", "Searing Gorge", "Azshara",
            "Blasted Lands", "Felwood", "Burning Steppes", "Winterspring"}},
        {"Dark Iron Deposit", 230, {"Searing Gorge", "Burning Steppes"}},
        {"Small Thorium Vein", 245, {"The Hinterlands", "Tanaris", "Searing Gorge", "Azshara", "Blasted Lands", "Un'Goro Crater",
            "Felwood", "Burning Steppes", "Western Plaguelands", "Eastern Plaguelands", "Winterspring", "Silithus"}},
        {"Rich Thorium Vein", 275, {"Azshara", "Un'Goro Crater", "Burning Steppes", "Eastern Plaguelands", "Winterspring", "Silithus"}},
        {"Heavy Thorium Vein", 300, {"Mount Hyjal"}},
    },
    [HERBALISM] = {
        {"Peacebloom", 1, with(STARTING, SECOND)}, {"Silverleaf", 1, with(STARTING, SECOND)},
        {"Earthroot", 15, with({"Durotar", "Mulgore", "Elwynn Forest", "Dun Morogh", "Teldrassil"}, SECOND)},
        {"Mageroyal", 50, with(SECOND, {"Redridge Mountains", "Stonetalon Mountains", "Ashenvale"})},
        {"Briarthorn", 70, with(SECOND, {"Redridge Mountains", "Ashenvale", "Duskwood", "Wetlands", "Hillsbrad Foothills"})},
        {"Stranglekelp", 85, {"The Barrens", "Westfall", "Darkshore", "Wetlands", "Hillsbrad Foothills", "Stranglethorn Vale"}},
        {"Bruiseweed", 100, {"Redridge Mountains", "Stonetalon Mountains", "Ashenvale", "Duskwood", "Wetlands", "Hillsbrad Foothills",
            "Thousand Needles", "Alterac Mountains"}},
        {"Wild Steelbloom", 115, {"Stonetalon Mountains", "Ashenvale", "Duskwood", "Wetlands", "Thousand Needles", "Arathi Highlands",
            "Stranglethorn Vale", "Badlands"}},
        {"Grave Moss", 120, {"Duskwood", "Wetlands", "Alterac Mountains", "Arathi Highlands", "Desolace"}},
        {"Kingsblood", 125, {"Ashenvale", "Duskwood", "Wetlands", "Hillsbrad Foothills", "Thousand Needles", "Arathi Highlands",
            "Desolace", "Stranglethorn Vale", "Dustwallow Marsh"}},
        {"Liferoot", 150, {"Ashenvale", "Wetlands", "Hillsbrad Foothills", "Alterac Mountains", "Arathi Highlands", "Desolace",
            "Stranglethorn Vale", "Dustwallow Marsh"}},
        {"Fadeleaf", 160, {"Alterac Mountains", "Arathi Highlands", "Stranglethorn Vale", "Dustwallow Marsh", "Badlands",
            "Swamp of Sorrows", "The Hinterlands"}},
        {"Goldthorn", 170, {"Alterac Mountains", "Arathi Highlands", "Stranglethorn Vale", "Dustwallow Marsh", "Badlands",
            "Swamp of Sorrows", "Feralas", "The Hinterlands"}},
        {"Khadgar's Whisker", 185, {"Alterac Mountains", "Arathi Highlands", "Stranglethorn Vale", "Dustwallow Marsh", "Badlands",
            "Swamp of Sorrows", "Feralas", "The Hinterlands"}},
        {"Wintersbite", 195, {"Alterac Mountains"}},
        {"Firebloom", 205, {"Badlands", "Tanaris", "Searing Gorge", "Blasted Lands"}},
        {"Purple Lotus", 210, {"Stranglethorn Vale", "Badlands", "Feralas", "The Hinterlands", "Tanaris", "Azshara"}},
        {"Arthas' Tears", 220, {"Felwood", "Western Plaguelands", "Eastern Plaguelands"}},
        {"Sungrass", 230, {"Feralas", "The Hinterlands", "Azshara", "Blasted Lands", "Un'Goro Crater", "Felwood", "Burning Steppes",
            "Western Plaguelands", "Eastern Plaguelands", "Silithus"}},
        {"Blindweed", 235, {"Swamp of Sorrows", "Un'Goro Crater"}},
        {"Ghost Mushroom", 245, {"Desolace", "The Hinterlands"}},
        {"Gromsblood", 250, {"Ashenvale", "Desolace", "Blasted Lands", "Felwood"}},
        {"Golden Sansam", 260, {"Feralas", "The Hinterlands", "Azshara", "Un'Goro Crater", "Felwood", "Burning Steppes",
            "Eastern Plaguelands", "Silithus"}},
        {"Dreamfoil", 270, {"Azshara", "Un'Goro Crater", "Felwood", "Burning Steppes", "Western Plaguelands", "Eastern Plaguelands",
            "Silithus"}},
        {"Mountain Silversage", 280, {"Azshara", "Un'Goro Crater", "Felwood", "Burning Steppes", "Western Plaguelands",
            "Eastern Plaguelands", "Winterspring", "Silithus"}},
        {"Plaguebloom", 285, {"Felwood", "Western Plaguelands", "Eastern Plaguelands"}},
        {"Icecap", 290, {"Winterspring"}},
        {"Black Lotus", 300, {"Burning Steppes", "Eastern Plaguelands", "Winterspring", "Silithus"}},
    },
}

local NAMES = {[MINING] = "Mining", [HERBALISM] = "Herbalism", [SKINNING] = "Skinning", [FISHING] = "Fishing"}
local ICONS = {[MINING] = "Interface\\Icons\\Trade_Mining", [HERBALISM] = "Interface\\Icons\\Spell_Nature_NatureTouchGrow",
    [SKINNING] = "Interface\\Icons\\INV_Misc_Pelt_Wolf_01", [FISHING] = "Interface\\Icons\\Trade_Fishing"}

-- Fishing: skill to cast at all, skill for a catch on every cast, and the zones of each tier.
local WATERS = {
    {1, 25, {"Durotar", "Mulgore", "Tirisfal Glades", "Elwynn Forest", "Dun Morogh", "Teldrassil", "Zephras Isle"}},
    {1, 75, {"The Barrens", "Silverpine Forest", "Westfall", "Loch Modan", "Darkshore"}},
    {55, 150, {"Ashenvale", "Duskwood", "Hillsbrad Foothills", "Redridge Mountains", "Stonetalon Mountains", "Wetlands"}},
    {130, 225, {"Alterac Mountains", "Arathi Highlands", "Desolace", "Dustwallow Marsh", "Stranglethorn Vale", "Swamp of Sorrows",
        "Thousand Needles"}},
    {205, 300, {"Azshara", "Felwood", "Feralas", "The Hinterlands", "Moonglade", "Tanaris", "Un'Goro Crater", "Western Plaguelands"}},
    {330, 425, {"Burning Steppes", "Deadwind Pass", "Eastern Plaguelands", "Silithus", "Winterspring"}},
}

-- Item relations used by Gold's zone-level search. Ore inputs are the same
-- item IDs used by ProfessionPlanner.lua's smelting recipes. Herb IDs are
-- matched to the WoW Forever Herbalism item records (for example, RaidDex's
-- current 1.60.1 item pages); no node amounts or chances are inferred here.
local ORE_ITEMS = {
    ["Copper Vein"] = 2770, ["Tin Vein"] = 2771, ["Silver Vein"] = 2775,
    ["Iron Deposit"] = 2772, ["Gold Vein"] = 2776, ["Mithril Deposit"] = 3858,
    ["Dark Iron Deposit"] = 11370,
    ["Truesilver Deposit"] = 7911, ["Small Thorium Vein"] = 10620,
    ["Rich Thorium Vein"] = 10620, ["Heavy Thorium Vein"] = 10620,
}
local HERB_ITEMS = {
    ["Peacebloom"] = 2447, ["Silverleaf"] = 765, ["Earthroot"] = 2449,
    ["Mageroyal"] = 785, ["Briarthorn"] = 2450, ["Stranglekelp"] = 3820,
    ["Bruiseweed"] = 2453, ["Wild Steelbloom"] = 3355, ["Grave Moss"] = 3369,
    ["Kingsblood"] = 3356, ["Liferoot"] = 3357, ["Fadeleaf"] = 3818,
    ["Goldthorn"] = 3821, ["Khadgar's Whisker"] = 3358, ["Wintersbite"] = 3819,
    ["Firebloom"] = 4625, ["Purple Lotus"] = 8831, ["Arthas' Tears"] = 8836,
    ["Sungrass"] = 8838, ["Blindweed"] = 8839, ["Ghost Mushroom"] = 8845,
    ["Gromsblood"] = 8846, ["Golden Sansam"] = 13464, ["Dreamfoil"] = 13463,
    ["Mountain Silversage"] = 13465, ["Plaguebloom"] = 13466,
    ["Icecap"] = 13467, ["Black Lotus"] = 13468,
}
-- Zone-specific Forever catch facts only. The source confirms Whimsyfin in
-- Redridge; it does not support assigning it to every zone in water tier 3.
-- Other fish are omitted until a zone-specific source is available.
local FISH_ZONE_CATCHES = {
    ["Redridge Mountains"] = {{251524, "Whimsyfin"}},
}
local FISH_ZONE_SOURCES = {
    ["Redridge Mountains"] = "WoW Forever Fishing guide: Whimsyfin in Redridge Mountains; https://foreverwow.com/professions/fishing/",
}
-- Lures, weakest first: name, bonus, Fishing skill needed to use it.
local LURES = {{"Shiny Bauble", 25, 1}, {"Nightcrawlers", 50, 50}, {"Bright Baubles", 75, 100}, {"Aquadynamic Fish Attractor", 100, 100}}
local NOTES = {
    [MINING] = "Carry a Mining Pick. Smelting gives skill too: copper to 70, tin to 75, iron from 125 to 140, gold from 155 to 185.",
    [HERBALISM] = "Stranglekelp grows underwater along coasts. Herbs inside caves and dungeons are not listed.",
    [SKINNING] = "Carry a Skinning Knife. Skin what you kill while questing: beasts near your own level are the ones that give points.",
    [FISHING] = "Skill comes from the number of fish you catch, not from where: fish wherever every cast is a catch. Your capital city counts as a 75 water.",
}
-- The four ranks, the same for every profession: cap, skill and level to train the next.
local RANKS = {{"Apprentice", 75, 1, 1}, {"Journeyman", 150, 50, 10}, {"Expert", 225, 125, 20}, {"Artisan", 300, 200, 35}}

ns.gatheringData = ns.gatheringData or {}

function ns.IsGatheringProfession(id) return NAMES[id] ~= nil end
function ns.RecordGatheringSkill(id, name, skill, maximum)
    if not NAMES[id] then return false end
    ns.gatheringData[id] = {id = id, name = name or NAMES[id], skill = skill, maximum = maximum}
    return true
end
-- After a complete read of the two primary slots: forget what is no longer learned.
function ns.FinishGatheringRead(seen)
    for id in pairs(NAMES) do if not seen[id] then ns.gatheringData[id] = nil end end
end

-- Skill a beast of this level needs to be skinned.
function ns.SkinningSkillForLevel(level)
    if level <= 10 then return 1 end
    if level <= 20 then return (level - 10) * 10 end
    return level * 5
end
-- Highest beast level this skill can skin.
function ns.SkinningLevelForSkill(skill)
    if skill < 10 then return 10 end
    if skill < 100 then return 10 + math.floor(skill / 10) end
    return math.floor(skill / 5)
end

-- "orange", "yellow", "green" or "grey" for a requirement at a skill, or nil when it cannot be gathered yet.
function ns.GatheringColor(required, skill, green)
    if skill < required then return nil end
    if skill < required + 25 then return "orange" end
    if skill < required + (green or 50) then return "yellow" end
    if skill < required + 100 then return "green" end
    return "grey"
end

local function zoneFits(zone, level, faction)
    local facts = ZONES[zone]
    if not facts then return nil end
    if facts[3] and faction and facts[3] ~= faction then return nil end
    -- Rank: 0 in the zone's range, then how far outside it. More than five
    -- levels above the character is left out as too dangerous to farm.
    if level < facts[1] - 5 then return nil end
    if level < facts[1] then return facts[1] - level + 10 end
    if level > facts[2] then return (level - facts[2]) * 0.5 end
    return 0
end

-- Zones for a list of candidates, best fit first, the character's own zone leading.
local function rankZones(zones, level, faction, here)
    local ranked = {}
    for _, zone in ipairs(zones) do
        local fit = zoneFits(zone, level, faction)
        if fit then ranked[#ranked + 1] = {zone = zone, fit = zone == here and -1 or fit} end
    end
    table.sort(ranked, function(a, b) if a.fit ~= b.fit then return a.fit < b.fit end return a.zone < b.zone end)
    local names = {}
    for index = 1, math.min(4, #ranked) do names[index] = ranked[index].zone end
    return names
end

-- Internal cursor source for the public module API. Rows are one node (or
-- fishing water tier) in one zone; map IDs are resolved against the client's
-- public map names by ModuleAPI.lua, and no spawn coordinates are provided.
local farmFacts = {}
local function addFarmFact(professionID, profession, node, required, zone, loot, nodeSource, skillSource, yieldSource)
    local zoneFacts = ZONES[zone]
    if not zoneFacts then return end
    farmFacts[#farmFacts + 1] = {professionID = professionID, profession = profession,
        node = node, requiredSkill = required, zone = zone,
        zoneMinLevel = zoneFacts[1], zoneMaxLevel = zoneFacts[2], zoneFaction = zoneFacts[3],
        loot = loot or {}, sources = {profession = "Gathering.lua profession IDs and learned-skill read",
            node = nodeSource, skill = skillSource,
            zone = "Gathering.lua zone/node lists; base-game zone coverage, not Forever spawn verification",
            mapID = "C_Map.GetMapInfo zone-name match through core KnownZoneMaps",
            yield = yieldSource}}
end

for _, professionID in ipairs({MINING, HERBALISM}) do
    local nodes = NODES[professionID] or {}
    for _, node in ipairs(nodes) do
        local name, required, zones = node[1], node[2], node[3]
        local itemID = professionID == MINING and ORE_ITEMS[name] or HERB_ITEMS[name]
        local loot = itemID and {{itemID = itemID,
            source = professionID == MINING
                and "ProfessionPlanner.lua smeltingRecipes ore input; Forever ore yield not independently recorded"
                or "WoW Forever herb item record; item ID " .. itemID .. " (Forever Icy Veins Herbalism and Wowhead item data)"}} or {}
        for _, zone in ipairs(zones) do
            addFarmFact(professionID, NAMES[professionID], name, required, zone, loot,
                "Gathering.lua NODES", "Gathering.lua node skill requirement", loot[1] and loot[1].source or "No sourced item ID; omitted")
        end
    end
end

-- Skinning has no fixed node names or single yield item. Report a zone-level
-- beast band using the same formula as the profession advice, without loot.
for zone, zoneFacts in pairs(ZONES) do
    local low, high = zoneFacts[1], zoneFacts[2]
    addFarmFact(SKINNING, NAMES[SKINNING], "Beasts level " .. low .. "–" .. high,
        ns.SkinningSkillForLevel(low), zone, {}, "Gathering.lua zone level band",
        "Gathering.lua SkinningSkillForLevel", "Skinning yield depends on the beast; no fixed item ID supplied")
end

for tierIndex, tier in ipairs(WATERS) do
    for _, zone in ipairs(tier[3]) do
        local loot, fishes = {}, FISH_ZONE_CATCHES[zone] or {}
        local source = FISH_ZONE_SOURCES[zone]
        for _, fish in ipairs(fishes) do loot[#loot + 1] = {itemID = fish[1], source = source} end
        local yieldSource = source or "No zone-specific Forever catch list; fish IDs omitted"
        addFarmFact(FISHING, NAMES[FISHING], "Water tier " .. tierIndex, tier[1], zone,
            loot, "Gathering.lua WATERS zone assignment", "Gathering.lua minimum cast skill", yieldSource)
    end
end

function ns.GatheringFarmFactCount() return #farmFacts end
function ns.GatheringFarmFact(index)
    if not ns.GuideInteger(index, #farmFacts) or index < 1 then return nil end
    local fact, learned = farmFacts[index], ns.gatheringData[farmFacts[index].professionID]
    if not learned or not ns.GuideInteger(learned.skill, 1000) or learned.skill < fact.requiredSkill then return nil end
    local profile = ns.profile or {}
    if not ns.GuideInteger(profile.level, 255) or profile.level < 1 then return nil end
    if fact.zoneFaction and fact.zoneFaction ~= profile.faction then return nil end
    if not zoneFits(fact.zone, profile.level, profile.faction) then return nil end
    return {professionID = fact.professionID, profession = fact.profession, node = fact.node,
        requiredSkill = fact.requiredSkill, ownSkill = learned.skill, zone = fact.zone,
        zoneMinLevel = fact.zoneMinLevel, zoneMaxLevel = fact.zoneMaxLevel,
        zoneFaction = fact.zoneFaction, loot = fact.loot, sources = fact.sources}
end

-- Optional read-only bridge to GatherLite's public instance methods. Its
-- third-party coordinates are evidence for browsing a zone, marked
-- unconfirmed; Gold must use the player's own observations before routing.
function ns.GatheringFarmPoints(profession, nodeName, mapID)
    local professionType = profession == "Mining" and "mining"
        or profession == "Herbalism" and "herbalism"
        or profession == "Fishing" and "fishing"
        or profession == "Treasure" and "containers" or nil
    if not professionType or type(nodeName) ~= "string" or #nodeName < 1 or #nodeName > 100
        or string.find(nodeName, "[%z\1-\31\127]")
        or not ns.GuideInteger(mapID, 1000000) or mapID < 1 then return {} end
    local libStub = type(LibStub) == "function" and ns.ReadPublic(LibStub, "AceAddon-3.0")
    local addon = libStub and type(libStub.GetAddon) == "function"
        and ns.ReadPublic(libStub.GetAddon, libStub, "GatherLite", true)
    if not addon or type(addon.GetNodesForMap) ~= "function" or type(addon.GetNodeObject) ~= "function" then return {} end
    local nodes = ns.ReadPublic(addon.GetNodesForMap, addon, professionType, mapID)
    if type(nodes) ~= "table" then return {} end
    local began = type(debugprofilestop) == "function" and ns.ReadPublic(debugprofilestop)
    if type(began) ~= "number" then return {} end
    local wanted = string.lower(string.gsub(nodeName, "[^%w]+", "_"))
    local matchAny = profession == "Fishing" or profession == "Treasure"
    local result = {}
    for _, node in ipairs(nodes) do
        local clock = ns.ReadPublic(debugprofilestop)
        if type(clock) ~= "number" or clock - began >= 1 then break end
        if type(node) == "table" and ns.Public(node) and node.mapID == mapID
            and node.type == professionType and type(node.object) == "number" then
            local object = ns.ReadPublic(addon.GetNodeObject, addon, node.object)
            if type(object) == "table" and ns.Public(object) and (matchAny or object.name == wanted)
                and type(node.posX) == "number" and type(node.posY) == "number"
                and node.posX >= 0 and node.posX <= 1 and node.posY >= 0 and node.posY <= 1 then
                result[#result + 1] = {mapID = mapID, x = node.posX, y = node.posY,
                    source = "GatherLite runtime node; legacy, unconfirmed"}
                if #result >= 24 then break end
            end
        end
    end
    return result
end

function ns.GatheringFarmYield(profession, nodeName, zoneName, mapID)
    if type(profession) ~= "string" or type(nodeName) ~= "string"
        or type(zoneName) ~= "string" or not ns.GuideInteger(mapID, 1000000) then return nil end
    local data = ns.gatheringFarmData
    if type(data) ~= "table" or type(data.records) ~= "table" then return nil end
    local lookupNode = profession == "Fishing" and zoneName or nodeName
    local row = data.records[profession .. "|" .. lookupNode .. "|" .. mapID]
    if type(row) ~= "table" or type(row.loot) ~= "table" then return nil end
    return row.loot, row.source
end

-- Fishing's last two ranks are a book and a quest, not lessons.
local function fishingRank(skill, maximum, level)
    maximum = maximum or 75
    if maximum <= 75 then
        return skill >= 50 and "Train Journeyman now at a Fishing trainer: it raises your cap from 75 to 150."
            or "Train Journeyman at a Fishing trainer from skill 50."
    elseif maximum <= 150 then
        return (skill >= 125 and "Buy" or "From skill 125, buy") .. " the book Expert Fishing - The Bass and You from Old Man Heming in Booty Bay to raise your cap to 225."
    elseif maximum <= 225 then
        if level and level < 35 then return "Artisan is Nat Pagle's quest in Dustwallow Marsh; it needs character level 35 and skill 225." end
        return (skill >= 225 and "Do" or "At skill 225, do") .. " Nat Pagle's quest in Dustwallow Marsh (Nat Pagle, Angler Extreme) to raise your cap to 300."
    end
    return nil
end

local function rankAdvice(skill, maximum, level)
    for index, rank in ipairs(RANKS) do
        local following = RANKS[index + 1]
        if (maximum or rank[2]) <= rank[2] and following then
            if skill >= following[3] then
                if level and level < following[4] then
                    return following[1] .. " needs character level " .. following[4] .. "; your cap stays " .. rank[2] .. " until then."
                end
                return "Train " .. following[1] .. " now: it raises your cap from " .. rank[2] .. " to " .. following[2] .. "."
            end
            return "Train " .. following[1] .. " from skill " .. following[3] .. " (character level " .. following[4] .. ")."
        end
    end
    return nil
end

-- What to gather at this skill. `level`, `faction` and `here` (zone name)
-- place the advice; they default to the character's own.
function ns.GatheringPlan(id, skill, maximum, level, faction, here)
    if not NAMES[id] then return nil end
    local profile = ns.profile or {}
    level, faction, here = level or profile.level or 1, faction or profile.faction, here or profile.zone
    local plan = {id = id, name = NAMES[id], skill = skill, maximum = maximum, level = level, here = here,
        now = {}, local_ = {}, note = NOTES[id], rank = rankAdvice(skill, maximum, level)}
    if id == FISHING then
        plan.rank = fishingRank(skill, maximum, level)
        -- The strongest lure the character may use, and the hardest waters
        -- where every cast is then a catch.
        for _, lure in ipairs(LURES) do if skill >= lure[3] then plan.lure = {name = lure[1], bonus = lure[2]} end end
        local zones, lured = {}, {}
        for _, tier in ipairs(WATERS) do
            local always = tier[2]
            for _, zone in ipairs(tier[3]) do
                if zone == here then
                    plan.water = {zone = zone, cast = tier[1], always = always, canCast = skill >= tier[1],
                        sure = skill >= always, need = math.max(0, always - skill)}
                    for _, lure in ipairs(LURES) do
                        if not plan.water.sure and not plan.water.lure and skill >= lure[3] and skill + lure[2] >= always then
                            plan.water.lure = lure[1]
                        end
                    end
                end
            end
            if skill >= always then plan.sureTier = always; zones = tier[3]
            elseif plan.lure and skill >= tier[1] and skill + plan.lure.bonus >= always then plan.lureTier = always; lured = tier[3] end
        end
        plan.zones = rankZones(zones, level, faction, here)
        plan.lureZones = rankZones(lured, level, faction, here)
        for _, tier in ipairs(WATERS) do
            if skill < tier[2] and (not plan.nextUnlock or tier[2] < plan.nextUnlock.skill) then
                plan.nextUnlock = {name = "A catch on every cast in " .. tier[3][1] .. " and similar waters", skill = tier[2]}
            end
        end
        return plan
    end
    if id == SKINNING then
        local top = ns.SkinningLevelForSkill(skill)
        -- A point every time while the requirement is within 25 of the skill.
        local sure = top
        while sure > 1 and ns.SkinningSkillForLevel(sure - 1) > skill - 25 do sure = sure - 1 end
        plan.beastTop, plan.beastSure = top, sure
        plan.ownLevelNeeds = ns.SkinningSkillForLevel(level)
        plan.behind = math.max(0, plan.ownLevelNeeds - skill)
        local zones = {}
        for zone, facts in pairs(ZONES) do
            if facts[1] <= top and facts[2] >= sure then zones[#zones + 1] = zone end
        end
        plan.zones = rankZones(zones, level, faction, here)
        if top < 60 then plan.nextUnlock = {name = "Level " .. (top + 1) .. " beasts", skill = ns.SkinningSkillForLevel(top + 1)} end
        return plan
    end
    local zones, seen = {}, {}
    for _, node in ipairs(NODES[id]) do
        local name, required, where = node[1], node[2], node[3]
        local color = ns.GatheringColor(required, skill, GREEN[id])
        if color and color ~= "grey" then
            plan.now[#plan.now + 1] = {name = name, skill = required, color = color, sureUntil = required + 25, greyAt = required + 100}
        elseif not color and (not plan.nextUnlock or required < plan.nextUnlock.skill) then
            plan.nextUnlock = {name = name, skill = required}
        end
        for _, zone in ipairs(where) do
            if zone == here then
                plan.local_[#plan.local_ + 1] = {name = name, skill = required, color = color, short = color == nil and required - skill or nil}
            end
        end
    end
    table.sort(plan.now, function(a, b) if a.skill ~= b.skill then return a.skill > b.skill end return a.name < b.name end)
    -- The two hardest nodes that still give points decide where to go.
    for index = 1, math.min(2, #plan.now) do
        for _, node in ipairs(NODES[id]) do
            if node[1] == plan.now[index].name then
                for _, zone in ipairs(node[3]) do if not seen[zone] then seen[zone] = true; zones[#zones + 1] = zone end end
            end
        end
    end
    plan.zones = rankZones(zones, level, faction, here)
    return plan
end

local COLOR_TEXT = {orange = "a point every time", yellow = "a point most times", green = "a point now and then"}

function ns.GatheringText(plan)
    local lines = {}
    lines[#lines + 1] = "Skill " .. plan.skill .. (plan.maximum and (" / " .. plan.maximum) or "")
    lines[#lines + 1] = ""
    if plan.id == FISHING then
        lines[#lines + 1] = "WHERE EVERY CAST IS A CATCH"
        lines[#lines + 1] = #plan.zones > 0 and table.concat(plan.zones, ", ")
            or (plan.sureTier and "Waters that need " .. plan.sureTier .. " or less" or "Nowhere yet without a lure: use a Shiny Bauble in a starting zone until 25.")
        if plan.lure and #plan.lureZones > 0 then
            lines[#lines + 1] = "With " .. plan.lure.name .. " (+" .. plan.lure.bonus .. "): " .. table.concat(plan.lureZones, ", ")
        end
        if plan.water then
            lines[#lines + 1] = ""
            lines[#lines + 1] = "IN " .. string.upper(plan.water.zone)
            if not plan.water.canCast then
                lines[#lines + 1] = "You cannot fish here yet: it needs skill " .. plan.water.cast .. "."
            elseif plan.water.sure then
                lines[#lines + 1] = "Every cast is a catch here."
            else
                lines[#lines + 1] = "Fish get away here until skill " .. plan.water.always .. " (" .. plan.water.need .. " to go)."
                    .. (plan.water.lure and (" " .. plan.water.lure .. " covers the gap.") or " No lure you can use covers that gap.")
            end
        end
        lines[#lines + 1] = ""
        lines[#lines + 1] = "NEXT"
        if plan.nextUnlock then
            lines[#lines + 1] = plan.nextUnlock.name .. " at skill " .. plan.nextUnlock.skill .. " (" .. (plan.nextUnlock.skill - plan.skill) .. " to go)"
        end
        if plan.rank then lines[#lines + 1] = plan.rank end
        lines[#lines + 1] = ""
        lines[#lines + 1] = plan.note
        return table.concat(lines, "\n")
    end
    if plan.id == SKINNING then
        lines[#lines + 1] = "GIVES SKILL NOW"
        lines[#lines + 1] = "Beasts of level " .. plan.beastSure .. (plan.beastSure < plan.beastTop and ("–" .. plan.beastTop) or "")
            .. " give a point every time. Level " .. plan.beastTop .. " is the highest you can skin."
        lines[#lines + 1] = ""
        lines[#lines + 1] = "AT YOUR LEVEL"
        if plan.behind > 0 then
            lines[#lines + 1] = "Beasts of your level (" .. plan.level .. ") need skill " .. plan.ownLevelNeeds .. ": you are "
                .. plan.behind .. " short. Skin level " .. plan.beastSure .. "–" .. plan.beastTop .. " beasts to catch up."
        else
            lines[#lines + 1] = "You can skin everything you fight at level " .. plan.level .. " (needs " .. plan.ownLevelNeeds .. ")."
        end
    else
        lines[#lines + 1] = "GIVES SKILL NOW"
        if #plan.now == 0 then lines[#lines + 1] = "Nothing you can gather gives skill at the moment." end
        for index, node in ipairs(plan.now) do
            if index > 5 then lines[#lines + 1] = "…and " .. (#plan.now - 5) .. " easier ones"; break end
            lines[#lines + 1] = node.name .. " (" .. node.skill .. ") • " .. COLOR_TEXT[node.color]
                .. (node.color == "orange" and (" until " .. node.sureUntil) or (", none from " .. node.greyAt))
        end
        if plan.here and #plan.local_ > 0 then
            lines[#lines + 1] = ""
            lines[#lines + 1] = "IN " .. string.upper(plan.here)
            for _, node in ipairs(plan.local_) do
                lines[#lines + 1] = node.name .. " • " .. (node.short and ("needs " .. node.skill .. ", you are " .. node.short .. " short")
                    or node.color == "grey" and "no skill any more" or COLOR_TEXT[node.color])
            end
        end
    end
    if #plan.zones > 0 then
        lines[#lines + 1] = ""
        lines[#lines + 1] = "WHERE"
        local names = {}
        for index, zone in ipairs(plan.zones) do names[index] = zone .. (zone == plan.here and " (you are here)" or "") end
        lines[#lines + 1] = table.concat(names, ", ")
    end
    lines[#lines + 1] = ""
    lines[#lines + 1] = "NEXT"
    if plan.nextUnlock then
        lines[#lines + 1] = plan.nextUnlock.name .. " at skill " .. plan.nextUnlock.skill .. " (" .. math.max(0, plan.nextUnlock.skill - plan.skill) .. " to go)"
    else
        lines[#lines + 1] = "Everything is unlocked."
    end
    if plan.rank then lines[#lines + 1] = plan.rank end
    lines[#lines + 1] = ""
    lines[#lines + 1] = plan.note
    lines[#lines + 1] = "Zones are Classic's locations; Forever's spawns and new nodes are not verified."
    return table.concat(lines, "\n")
end

-- One line for a card or the chat: the most useful fact right now.
function ns.GatheringSummary(plan)
    if plan.id == FISHING then
        if plan.water and plan.water.canCast then
            return plan.water.sure and "Every cast is a catch here"
                or (plan.water.lure and ("Use " .. plan.water.lure .. " here") or (plan.water.need .. " skill short for a sure catch here"))
        end
        return plan.zones[1] and ("Sure catches in " .. plan.zones[1]) or "Use a Shiny Bauble in a starting zone"
    end
    if plan.id == SKINNING then
        return plan.behind > 0 and (plan.behind .. " skill short for level " .. plan.level .. " beasts")
            or ("Skins up to level " .. plan.beastTop)
    end
    for _, node in ipairs(plan.local_) do
        if node.color and node.color ~= "grey" then return node.name .. " here gives skill" end
    end
    if plan.now[1] then return plan.now[1].name .. (plan.zones[1] and (" • " .. plan.zones[1]) or "") end
    return plan.nextUnlock and ("Next: " .. plan.nextUnlock.name .. " at " .. plan.nextUnlock.skill) or "Nothing gives skill right now"
end

local viewer
local function createViewer()
    if viewer then return viewer end
    local colors = ns.UIColors
    viewer = CreateFrame("Frame", "WowTogetherGatheringViewer", UIParent, "BackdropTemplate")
    ns.gatheringViewer = viewer
    viewer:SetSize(440, 420); viewer:SetPoint("CENTER"); viewer:SetFrameStrata("DIALOG")
    viewer:SetClampedToScreen(true); viewer:SetMovable(true); viewer:EnableMouse(true)
    viewer:RegisterForDrag("LeftButton")
    viewer:SetScript("OnDragStart", viewer.StartMoving); viewer:SetScript("OnDragStop", viewer.StopMovingOrSizing)
    ns.UIPanel(viewer); ns.UIClose(viewer)
    viewer.icon = viewer:CreateTexture(nil, "ARTWORK")
    viewer.icon:SetSize(30, 30); viewer.icon:SetPoint("TOPLEFT", 18, -16)
    viewer.title = ns.UILabel(viewer, "GameFontNormalLarge", 17, colors.gold)
    viewer.title:SetPoint("LEFT", viewer.icon, "RIGHT", 10, 0)
    viewer.body = ns.UILabel(viewer, nil, 12, colors.text)
    viewer.body:SetPoint("TOPLEFT", 18, -58); viewer.body:SetPoint("TOPRIGHT", -18, -58)
    viewer.body:SetJustifyH("LEFT"); viewer.body:SetJustifyV("TOP"); viewer.body:SetWordWrap(true)
    if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherGatheringViewer") end
    return viewer
end

-- The window is as tall as its text, within the screen.
local function fit()
    local height = ns.ReadPublic(viewer.body.GetStringHeight, viewer.body)
    if type(height) == "number" and height > 0 then viewer:SetHeight(math.max(160, math.min(640, height + 78))) end
end

function ns.RefreshGatheringViewer()
    if not viewer or not viewer:IsShown() or not viewer.professionID then return end
    local id, info = viewer.professionID, ns.gatheringData[viewer.professionID]
    viewer.icon:SetTexture(ICONS[id]); viewer.title:SetText(NAMES[id])
    if not info then
        viewer.body:SetText("Learn " .. NAMES[id] .. " from a trainer to see what to gather here.\n\n" .. NOTES[id])
    else
        viewer.body:SetText(ns.GatheringText(ns.GatheringPlan(id, info.skill, info.maximum)))
    end
    fit()
end

function ns.ShowGatheringViewer(id)
    if not NAMES[id] then return end
    if ns.ReadProfessionSkills then ns.ReadProfessionSkills() end
    local frame = createViewer()
    frame.professionID = id; frame:Show(); frame:Raise()
    ns.RefreshGatheringViewer()
end

-- Cards for the profession browser, learned ones first.
function ns.GatheringChoices()
    local choices = {}
    for _, id in ipairs(ns.GATHERING_IDS) do
        local key, info = id, ns.gatheringData[id]
        local plan = info and ns.GatheringPlan(id, info.skill, info.maximum)
        choices[#choices + 1] = {title = NAMES[id], category = info and "YOUR PROFESSION" or "GATHERING PROFESSION", gathering = id,
            count = info and ("Skill " .. info.skill .. " / " .. (info.maximum or "?")) or "Learn & gather",
            detail = plan and ns.GatheringSummary(plan) or "What gives skill, where, and when to train",
            icon = ICONS[id], click = function() ns.ShowGatheringViewer(key) end, learned = info ~= nil}
    end
    table.sort(choices, function(a, b) if a.learned ~= b.learned then return a.learned end return a.title < b.title end)
    return choices
end

-- /wt gather: the advice in a few chat lines, without opening anything.
function ns.GatheringCommand()
    if ns.ReadProfessionSkills then ns.ReadProfessionSkills() end
    local any = false
    for _, id in ipairs(ns.GATHERING_IDS) do
        local info = ns.gatheringData[id]
        if info then
            any = true
            local plan = ns.GatheringPlan(id, info.skill, info.maximum)
            ns.Print(NAMES[id] .. " " .. info.skill .. ": " .. ns.GatheringSummary(plan)
                .. (plan.nextUnlock and (". Next: " .. plan.nextUnlock.name .. " at " .. plan.nextUnlock.skill) or "")
                .. (plan.rank and (". " .. plan.rank) or ""))
        end
    end
    if not any then ns.Print("No gathering profession learned. Open the profession browser to see Mining, Herbalism and Skinning.") end
end

-- What this zone offers the character's gathering professions, in one line.
-- Nil when nothing here gives skill, so nothing is said.
function ns.GatheringZoneTip(zone)
    local parts = {}
    for _, id in ipairs(ns.GATHERING_IDS) do
        local info = ns.gatheringData[id]
        if info then
            local plan = ns.GatheringPlan(id, info.skill, info.maximum, nil, nil, zone)
            if id == FISHING then
                -- Fishing is the same everywhere; the zone tip says nothing about it.
            elseif id == SKINNING then
                local facts = ZONES[zone]
                if facts and plan.behind > 0 and facts[1] <= plan.beastTop then
                    parts[#parts + 1] = "Skinning is " .. plan.behind .. " short for beasts your level: skin level "
                        .. plan.beastSure .. "–" .. plan.beastTop .. " ones"
                end
            else
                local names = {}
                for _, node in ipairs(plan.local_) do
                    if node.color == "orange" or node.color == "yellow" then names[#names + 1] = node.name end
                end
                if #names > 0 then
                    parts[#parts + 1] = table.concat(names, ", ") .. (#names == 1 and " gives " or " give ") .. NAMES[id] .. " skill"
                end
            end
        end
    end
    if #parts == 0 then return nil end
    return "Gathering in " .. zone .. ": " .. table.concat(parts, "; ") .. "."
end

-- Said once per zone and session, a moment after arriving, when the option is on.
local told = {}
local function onZone()
    if ns.Option and ns.Option("gatheringTips") == false then return end
    local function tell()
        if ns.ReadProfessionSkills then ns.ReadProfessionSkills() end
        local zone = ns.ReadPublic(GetRealZoneText)
        if type(zone) ~= "string" or zone == "" or told[zone] then return end
        told[zone] = true
        local tip = ns.GatheringZoneTip(zone)
        if tip then ns.Print(tip) end
    end
    if C_Timer and type(C_Timer.After) == "function" then ns.After("timer:Gathering", 3, tell) else tell() end
end
if ns.On then ns.On("ZONE_CHANGED_NEW_AREA", onZone) end
ns.GatheringZoneArrived = onZone

-- Emit a real gather observation only after a local loot message confirms the
-- item. Mining/herbalism require a GameObject loot source; Fishing requires a
-- just-sent Fishing cast and a fish item. This captures measured map positions
-- without copying old spawn priors or making any player action.
local observedItemProfession, pendingNodeLoot = {}, {}
for _, fact in ipairs(farmFacts) do
    for _, item in ipairs(fact.loot) do observedItemProfession[item.itemID] = fact.professionID end
end
local fishingSpells = {[7620] = true, [7731] = true, [7732] = true, [18248] = true, [33095] = true}
local fishingCast, skinningCast

local function observationPosition()
    if ns.ReadProfile then ns.ReadProfile() end
    local profile = ns.profile or {}
    if not ns.GuideInteger(profile.mapID, 1000000) or profile.mapID < 1 then return nil end
    local point = ns.PlayerPoint and ns.PlayerPoint(profile.mapID)
    if not point or not ns.Public(point.x) or not ns.Public(point.y)
        or type(point.x) ~= "number" or type(point.y) ~= "number"
        or point.x < 0 or point.x > 1 or point.y < 0 or point.y > 1 then return nil end
    return {mapID = profile.mapID, x = point.x, y = point.y}
end

local function emitObservation(professionID, itemID, quantity, location, source)
    if not location or type(ns.RunHooks) ~= "function" then return end
    ns.RunHooks("gatheringObserved", {professionID = professionID, profession = NAMES[professionID],
        mapID = location.mapID, x = location.x, y = location.y, itemID = itemID,
        quantity = quantity, source = source, observedAt = ns.ReadPublic(GetTime)})
end

local function lootSourceKind()
    if type(GetLootSourceInfo) ~= "function" then return false end
    local guid = ns.ReadPublic(GetLootSourceInfo, 1)
    if type(guid) ~= "string" then return nil end
    local upper = string.upper(guid)
    if string.sub(upper, 1, 6) == "0XF110" or string.sub(guid, 1, 11) == "GameObject-" then return "gameobject" end
    if string.sub(upper, 1, 6) == "0XF130" or string.sub(guid, 1, 9) == "Creature-" then return "creature" end
    return nil
end

if ns.On then
    ns.On("UNIT_SPELLCAST_SENT", function(unit, _, target, spellID)
        if unit ~= "player" then return end
        local location = observationPosition()
        local now = ns.ReadPublic(GetTime) or 0
        if location and fishingSpells[spellID] then fishingCast = {location = location, expires = now + 90} end
        if location and spellID == 8613 then
            local targetGUID = type(UnitGUID) == "function" and ns.ReadPublic(UnitGUID, "target")
            skinningCast = {location = location, expires = now + 30, targetGUID = targetGUID}
        end
    end)
    ns.On("LOOT_OPENED", function()
        local sourceKind = lootSourceKind()
        if fishingCast and sourceKind == "gameobject" then fishingCast.source = "fishing-pool" end
        if not sourceKind then return end
        local location = observationPosition()
        local count = type(GetNumLootItems) == "function" and ns.ReadPublic(GetNumLootItems) or 0
        if not location or not ns.GuideInteger(count, 40) then return end
        local now = ns.ReadPublic(GetTime) or 0
        for slot = 1, count do
            local link = type(GetLootSlotLink) == "function" and ns.ReadPublic(GetLootSlotLink, slot)
            local itemID = type(link) == "string" and tonumber(string.match(link, "|Hitem:(%d+):"))
            local professionID = itemID and observedItemProfession[itemID]
            if (professionID == MINING or professionID == HERBALISM) and sourceKind == "gameobject" then
                local quantity
                if type(GetLootSlotInfo) == "function" then local _, _, found = ns.ReadPublic(GetLootSlotInfo, slot); quantity = found end
                pendingNodeLoot[itemID] = {professionID = professionID, itemID = itemID,
                    quantity = ns.GuideInteger(quantity, 10000) and math.max(1, quantity) or 1,
                    location = location, expires = now + 20}
            end
        end
    end)
    ns.On("CHAT_MSG_LOOT", function(message)
        if type(message) ~= "string" then return end
        local templates = {}
        if type(LOOT_ITEM_SELF) == "string" and ns.Public(LOOT_ITEM_SELF) then templates[#templates + 1] = LOOT_ITEM_SELF end
        if type(LOOT_ITEM_SELF_MULTIPLE) == "string" and ns.Public(LOOT_ITEM_SELF_MULTIPLE) then
            templates[#templates + 1] = LOOT_ITEM_SELF_MULTIPLE
        end
        local own = false
        for _, template in ipairs(templates) do
            if type(template) == "string" then
                local prefix = string.match(template, "^(.-)%%s")
                if prefix and prefix ~= "" and string.sub(message, 1, #prefix) == prefix then own = true; break end
            end
        end
        if not own then return end
        local itemID = tonumber(string.match(message, "|Hitem:(%d+):"))
        if not itemID then return end
        local quantity = tonumber(string.match(message, "|h%s*[xX](%d+)")
            or string.match(message, "%]%s*x(%d+)"))
        local pending = pendingNodeLoot[itemID]
        local now = ns.ReadPublic(GetTime) or 0
        if pending and pending.expires >= now then
            pendingNodeLoot[itemID] = nil
            emitObservation(pending.professionID, itemID, quantity or pending.quantity, pending.location, "gather-node")
            return
        end
        local professionID = observedItemProfession[itemID]
        if fishingCast and fishingCast.expires >= now then
            local cast = fishingCast; fishingCast = nil
            emitObservation(FISHING, itemID, quantity or 1, cast.location, cast.source or "open-water-catch")
        elseif skinningCast and skinningCast.expires >= now and lootSourceKind() == "creature" then
            local cast = skinningCast; skinningCast = nil
            emitObservation(SKINNING, itemID, quantity or 1, cast.location, "skinning-yield")
        end
    end)
end

function ns.GatheringDiagnostics(output)
    local parts = {}
    for _, id in ipairs(ns.GATHERING_IDS) do
        local info = ns.gatheringData[id]
        parts[#parts + 1] = NAMES[id] .. " " .. (info and (info.skill .. "/" .. tostring(info.maximum)) or "not learned")
    end
    output("Gathering: " .. table.concat(parts, "; ") .. ". Advice uses Classic node requirements and locations; no gathering is automated.")
end
