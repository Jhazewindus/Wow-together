local addonName, ns = ...

-- Read-only data adapter. Never selects an EJ instance/tier/difficulty or opens
-- Blizzard's map. Native map coordinates are used only for matching boss names.
local function nameKey(value)
    value = ns.SafeTitle(value)
    return value and string.gsub(string.lower(value), "[^%w]", "")
end
local function publicTable(value) return ns.Public(value) and type(value) == "table" end
local function number(value, limit)
    return ns.Public(value) and type(value) == "number" and value == value and value >= 0 and value <= (limit or 1000000000)
end
local function matches(key, name)
    local info = ns.dungeonData and ns.dungeonData.dungeons[key]
    local target = nameKey(name)
    if not target or not info then return false end
    if target == nameKey(info.name) then return true end
    for _, alias in ipairs(info.aliases or {}) do if target == nameKey(alias) then return true end end
    return false
end
local function copy(value) local out = {}; for k, v in pairs(value) do out[k] = v end; return out end
local function dropSource(value, kind)
    local source = copy(value)
    source.kind = kind
    -- Shared item facts are decoded once on demand, rather than copied into
    -- every NPC's loot table during addon startup or opening a map.
    return setmetatable(source, {__index = function(row, field)
        local ids = field == "loot" and row.dropIDs or field == "sharedLoot" and row.sharedDropIDs
        if not ids then return end
        local result = {}
        for _, id in ipairs(ids) do
            local item = ns.dungeonJournalData.items and ns.dungeonJournalData.items[id]
            if item then result[#result + 1] = item end
        end
        rawset(row, field, result)
        return result
    end})
end
local function validPoint(value)
    return publicTable(value) and number(value.x, 1) and number(value.y, 1)
end
local function referenceFloor(map, stored, positions, ordinal)
    local floor = positions and positions.floors[ordinal]
    if map.reference then return floor end
    -- Same names do not establish geometry: every file identity and the
    -- dimensions must agree before old coordinates can join a native floor.
    for index, value in ipairs(positions and positions.floors or {}) do
        local original = stored.maps[index]
        if original and map.width == original.width and map.height == original.height
            and map.tileWidth == original.tileWidth and map.tileHeight == original.tileHeight
            and #map.tiles == #value.tiles then
            local equal = true
            for tile, asset in ipairs(value.tiles) do if map.tiles[tile] ~= asset then equal = false; break end end
            if equal then return value end
        end
    end
end
function ns.DungeonMapQuestVisible(point, query)
    local id, quest = point.id, ns.CatalogueQuest(point.id)
    if not quest or ns.IsRetiredQuest(id) or ns.Completed(id, query) == true then return false end
    if ns.CatalogueIdentityAllowed(id, ns.profile) == false then return false end
    if ns.ClassQuestEnabled and not ns.ClassQuestEnabled(id) then return false end
    return not (point.kind == "a" and ns.active and ns.active[id])
end
local function imageMap(id, title)
    local layers = C_Map and ns.ReadPublic(C_Map.GetMapArtLayers, id)
    local info = publicTable(layers) and layers[1]
    if not publicTable(info) then return end
    for _, field in ipairs({"layerWidth", "layerHeight", "tileWidth", "tileHeight"}) do
        if not number(info[field], 8192) or info[field] < 1 then return end
    end
    local count = math.ceil(info.layerWidth / info.tileWidth) * math.ceil(info.layerHeight / info.tileHeight)
    if count > 64 then return end
    local textures = ns.ReadPublic(C_Map.GetMapArtLayerTextures, id, 1)
    if not publicTable(textures) then return end
    local tiles = {}
    for index = 1, count do
        local asset = textures[index]
        if not ns.GuideInteger(asset, 1000000000) or asset < 1 then return end
        tiles[index] = asset
    end
    return {mapID = id, name = ns.SafeTitle(title) or "Dungeon floor", width = info.layerWidth,
        height = info.layerHeight, tileWidth = info.tileWidth, tileHeight = info.tileHeight, tiles = tiles}
end

function ns.DungeonViewerData(key)
    local stored = ns.dungeonJournalData and ns.dungeonJournalData.dungeons[key]
    local definition = ns.dungeonData and ns.dungeonData.dungeons[key]
    if not stored or not definition then return end
    local data = {key = key, name = definition.name, definition = definition, bosses = {}, trash = {}, containers = {}, maps = {}}
    local positions = ns.dungeonMapData and ns.dungeonMapData.dungeons[key]
    local byName = {}
    for index, boss in ipairs(stored.bosses) do
        data.bosses[index] = dropSource(boss, "boss"); byName[nameKey(boss.name)] = data.bosses[index]
        if not ns.GuideInteger(boss.level, 255) or boss.level < 1 then data.bosses[index].level = nil end
    end
    for index, npc in ipairs(stored.trash or {}) do data.trash[index] = dropSource(npc, "trash") end
    for index, object in ipairs(stored.containers or {}) do data.containers[index] = dropSource(object, "container") end
    local instanceID = ns.DungeonJournalInstance and ns.DungeonJournalInstance(key)
    if instanceID and type(EJ_GetEncounterInfoByIndex) == "function" then
        for index = 1, 96 do
            local name, _, id = ns.ReadPublic(EJ_GetEncounterInfoByIndex, index, instanceID)
            if not ns.GuideInteger(id) or id < 1 then break end
            local boss = byName[nameKey(name)]
            -- New dungeons can expose a journal before public databases do.
            -- Keep native encounter facts, but do not infer their loot tables.
            if not boss and (#stored.bosses == 0 or definition.era == "Forever") and ns.SafeTitle(name) then
                boss = {id = id, name = ns.SafeTitle(name), loot = {}, native = true}
                data.bosses[#data.bosses + 1] = boss; byName[nameKey(name)] = boss
            end
            if boss then
                boss.encounterID = id
                local _, _, _, _, portrait = ns.ReadPublic(EJ_GetCreatureInfo, 1, id)
                if ns.GuideInteger(portrait, 1000000000) and portrait > 0 then boss.portrait = portrait end
            end
        end
    end
    local mapID
    if instanceID and type(EJ_GetInstanceInfo) == "function" then
        local ok, _, _, _, _, _, _, id = pcall(EJ_GetInstanceInfo, instanceID)
        if ok and ns.GuideInteger(id) and id > 0 then mapID = id end
    end
    -- Discover by exact dungeon name; never confuse an outdoor entrance zone
    -- or a similarly named scenario with the instance interior.
    if not mapID and C_Map then
        local current = ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
        local roots = {947}
        local insideKey = ns.DungeonEntryKey()
        local function isDungeonMap(info)
            if not publicTable(info) or not matches(key, info.name) then return false end
            local dungeonType = Enum and Enum.UIMapType and Enum.UIMapType.Dungeon
            -- Orphan/micro maps occur on Classic interiors. Accept these only
            -- while the instance itself confirms this exact dungeon name.
            return insideKey == key or dungeonType and ns.Public(info.mapType) and info.mapType == dungeonType
        end
        if ns.GuideInteger(current) and current > 0 then
            for _ = 1, 8 do
                local info = ns.ReadPublic(C_Map.GetMapInfo, current)
                if not publicTable(info) then break end
                if isDungeonMap(info) then mapID = current; break end
                if not ns.GuideInteger(info.parentMapID) or info.parentMapID < 1 or info.parentMapID == current then break end
                current = info.parentMapID
            end
            if current ~= 947 then roots[#roots + 1] = current end
        end
        if not mapID then
            for _, root in ipairs(roots) do
                local children = ns.ReadPublic(C_Map.GetMapChildrenInfo, root, nil, true)
                if publicTable(children) then
                    for index = 1, math.min(#children, 1024) do
                        local info = children[index]
                        if isDungeonMap(info) and ns.GuideInteger(info.mapID) then
                            mapID = info.mapID; break
                        end
                    end
                end
                if mapID then break end
            end
        end
    end
    if mapID then
        local group = C_Map and ns.ReadPublic(C_Map.GetMapGroupID, mapID)
        local members = ns.GuideInteger(group) and ns.ReadPublic(C_Map.GetMapGroupMembersInfo, group)
        local seen = {}
        if publicTable(members) then
            for index = 1, math.min(#members, 32) do
                local info = members[index]
                if publicTable(info) and ns.GuideInteger(info.mapID) and not seen[info.mapID] then
                    seen[info.mapID] = true
                    local map = imageMap(info.mapID, info.name)
                    if map then data.maps[#data.maps + 1] = map end
                end
            end
        end
        if #data.maps == 0 then
            local map = imageMap(mapID, data.name)
            if map then data.maps[1] = map end
        end
    end
    if #data.maps == 0 then for index, map in ipairs(stored.maps) do data.maps[index] = copy(map) end end
    for floor, map in ipairs(data.maps) do
        map.bosses, map.quests = {}, {}
        local reference = referenceFloor(map, stored, positions, floor)
        local located = {}
        if reference then
            for _, point in ipairs(reference.bosses) do
                if validPoint(point) then map.bosses[#map.bosses + 1] = copy(point); located[point.id] = #map.bosses end
            end
            for _, point in ipairs(reference.quests) do if validPoint(point) then map.quests[#map.quests + 1] = copy(point) end end
        end
        if map.mapID and C_EncounterJournal then
            local encounters = ns.ReadPublic(C_EncounterJournal.GetEncountersOnMap, map.mapID)
            if publicTable(encounters) then
                for index = 1, math.min(#encounters, 96) do
                    local info = encounters[index]
                    if publicTable(info) and ns.GuideInteger(info.encounterID) and number(info.mapX, 1) and number(info.mapY, 1) then
                        local name = ns.ReadPublic(EJ_GetEncounterInfo, info.encounterID)
                        local boss = byName[nameKey(name)]
                        if boss then
                            local point = {id = boss.id, x = info.mapX, y = info.mapY, native = true}
                            local index = located[boss.id]
                            if index then map.bosses[index] = point else map.bosses[#map.bosses + 1] = point; located[boss.id] = #map.bosses end
                            for _, target in ipairs(positions and positions.targets or {}) do
                                if target.entityType == "npc" and ((not boss.native and target.entityID == boss.id)
                                    or nameKey(target.name) == nameKey(boss.name)) then
                                    for i = #map.quests, 1, -1 do
                                        local old = map.quests[i]
                                        if old.id == target.id and old.kind == target.kind and old.entityID == target.entityID then table.remove(map.quests, i) end
                                    end
                                    local questPoint = copy(target); questPoint.x, questPoint.y = point.x, point.y
                                    map.quests[#map.quests + 1] = questPoint
                                end
                            end
                        end
                    end
                end
            end
        end
        for _, point in ipairs(map.bosses) do
            for _, boss in ipairs(data.bosses) do if boss.id == point.id then boss.mapID, boss.mapFloor = map.mapID, floor; break end end
        end
    end
    return data
end

-- Item type eligibility, independent of spec, stats and skills already trained.
-- Missing/unrecognized metadata stays visible, including new beta item types.
ns.DungeonLootClasses = {{0, "All classes"}, {1, "Warrior"}, {2, "Paladin"}, {3, "Hunter"},
    {4, "Rogue"}, {5, "Priest"}, {7, "Shaman"}, {8, "Mage"}, {9, "Warlock"}, {11, "Druid"}}
local weapons = {
    [1] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15, 16, 18},
    [2] = {0, 1, 4, 5, 6, 7, 8}, [3] = {0, 1, 2, 3, 6, 7, 8, 10, 13, 15, 16, 18},
    [4] = {2, 3, 4, 7, 13, 15, 16, 18}, [5] = {4, 10, 15, 19},
    [7] = {0, 1, 4, 5, 10, 13, 15}, [8] = {7, 10, 15, 19},
    [9] = {7, 10, 15, 19}, [11] = {4, 5, 10, 13, 15},
}
for class, values in pairs(weapons) do
    local allowed = {}; for _, value in ipairs(values) do allowed[value] = true end
    weapons[class] = allowed
end
local armor = {
    [2] = {[1]=true, [2]=true, [3]=true, [4]=true, [7]=true, [11]=true}, -- Leather
    [3] = {[1]=true, [2]=true, [3]=true, [7]=true}, -- Mail, including later training
    [4] = {[1]=true, [2]=true}, [6] = {[1]=true, [2]=true, [7]=true}, -- Plate/shields
    [7] = {[2]=true}, [8] = {[11]=true}, [9] = {[7]=true}, -- Librams/idols/totems
}
function ns.DungeonLootClassAllowed(item, class)
    if not ns.GuideInteger(class, 255) or not weapons[class] then return true end
    if item.classID == 2 and ns.GuideInteger(item.subclass, 20) then
        local subtype = item.subclass
        if subtype <= 8 or subtype == 10 or subtype == 13 or subtype == 15
            or subtype == 16 or subtype == 18 or subtype == 19 then
            return weapons[class][subtype] == true
        end
    elseif item.classID == 4 then
        -- Cloaks, jewelry and off-hand frills are shared regardless of the
        -- database's armor subtype; class-specific restrictions need source data.
        if item.slot == 2 or item.slot == 11 or item.slot == 12 or item.slot == 16 or item.slot == 23 then return true end
        local allowed = ns.Public(item.subclass) and armor[item.subclass]
        if allowed then return allowed[class] == true end
    end
    return true
end
function ns.DungeonBossFloor(data, boss, current)
    if not data or not boss then return current end
    local found, native
    for floor, map in ipairs(data.maps) do
        for _, point in ipairs(map.bosses or {}) do
            if point.id == boss.id then
                if point.native and not native then found, native = floor, true
                elseif (point.native == true) == (native == true) and (not found or floor == current) then found = floor end
            end
        end
    end
    if found then return found end
    if ns.GuideInteger(boss.mapFloor, #data.maps) and boss.mapFloor > 0 then return boss.mapFloor end
    if ns.GuideInteger(boss.mapID) then
        for floor, map in ipairs(data.maps) do
            if map.mapID == boss.mapID then
                if found then return current end -- Shared map IDs do not identify a floor.
                found = floor
            end
        end
    end
    return found or current
end

function ns.DungeonViewerLoot(boss, query, category, class)
    local result = {}
    query = string.lower(ns.SafeTitle(query) or "")
    local drops = boss and boss.loot
    if category == "shared" then drops = boss and boss.sharedLoot end
    for _, item in ipairs(drops or {}) do
        local matchesCategory = category == "all" or category == "shared" or not category
            or category == "equipment" and (item.classID == 2 or item.classID == 4)
            or category == "other" and item.classID ~= 2 and item.classID ~= 4
        if matchesCategory and ns.DungeonLootClassAllowed(item, class)
            and (query == "" or string.find(string.lower(item.name), query, 1, true)) then result[#result + 1] = item end
    end
    return result
end

function ns.DungeonViewerItem(item)
    local info = copy(item)
    if C_Item and type(C_Item.GetItemInfo) == "function" then
        local ok, name, link, quality, _, required, _, _, _, _, icon = pcall(C_Item.GetItemInfo, item.id)
        if ok then
            if ns.SafeTitle(name) then info.name = ns.SafeTitle(name) end
            if ns.Public(link) and type(link) == "string" and string.match(link, "|Hitem:" .. item.id .. ":") then info.link = link end
            if ns.GuideInteger(quality, 7) then info.quality = quality end
            if ns.GuideInteger(required, 255) then info.requiredLevel = required end
            if ns.GuideInteger(icon, 1000000000) and icon > 0 then info.icon = icon end
        end
    end
    return info
end

function ns.DungeonEntryKey()
    local inside, kind = ns.ReadPublic(IsInInstance)
    if inside ~= true or kind ~= "party" or type(GetInstanceInfo) ~= "function" then return end
    local ok, name, instanceType, _, _, _, _, _, id = pcall(GetInstanceInfo)
    if not ok or not ns.Public(instanceType) or instanceType ~= "party" or not ns.SafeTitle(name) then return end
    for key in pairs(ns.dungeonData and ns.dungeonData.dungeons or {}) do
        if matches(key, name) then return key, ns.GuideInteger(id) and id or 0 end
    end
end
