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
    local data = {key = key, name = definition.name, definition = definition, bosses = {}, maps = {}}
    local byName = {}
    for index, boss in ipairs(stored.bosses) do
        data.bosses[index] = copy(boss); byName[nameKey(boss.name)] = data.bosses[index]
    end
    local instanceID = ns.DungeonJournalInstance and ns.DungeonJournalInstance(key)
    if instanceID and type(EJ_GetEncounterInfoByIndex) == "function" then
        for index = 1, 96 do
            local name, _, id = ns.ReadPublic(EJ_GetEncounterInfoByIndex, index, instanceID)
            if not ns.GuideInteger(id) or id < 1 then break end
            local boss = byName[nameKey(name)]
            -- New dungeons can expose a journal before public databases do.
            -- Keep native encounter facts, but do not infer their loot tables.
            if not boss and #stored.bosses == 0 and ns.SafeTitle(name) then
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
        if ns.GuideInteger(current) and current > 0 then
            for _ = 1, 8 do
                local info = ns.ReadPublic(C_Map.GetMapInfo, current)
                if not publicTable(info) then break end
                local dungeonType = Enum and Enum.UIMapType and Enum.UIMapType.Dungeon
                if dungeonType and ns.Public(info.mapType) and info.mapType == dungeonType and matches(key, info.name) then mapID = current; break end
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
                        if publicTable(info) and matches(key, info.name) and ns.GuideInteger(info.mapID)
                            and Enum and Enum.UIMapType and ns.Public(info.mapType) and info.mapType == Enum.UIMapType.Dungeon then
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
    for _, map in ipairs(data.maps) do
        map.bosses = {}
        if map.mapID and C_EncounterJournal then
            local encounters = ns.ReadPublic(C_EncounterJournal.GetEncountersOnMap, map.mapID)
            if publicTable(encounters) then
                for index = 1, math.min(#encounters, 96) do
                    local info = encounters[index]
                    if publicTable(info) and ns.GuideInteger(info.encounterID) and number(info.mapX, 1) and number(info.mapY, 1) then
                        local name = ns.ReadPublic(EJ_GetEncounterInfo, info.encounterID)
                        local boss = byName[nameKey(name)]
                        if boss then map.bosses[#map.bosses + 1] = {id = boss.id, x = info.mapX, y = info.mapY}; boss.mapID = map.mapID end
                    end
                end
            end
        end
    end
    return data
end

function ns.DungeonViewerLoot(boss, query, category)
    local result = {}
    query = string.lower(ns.SafeTitle(query) or "")
    for _, item in ipairs(boss and boss.loot or {}) do
        local matchesCategory = category == "all" or not category
            or category == "equipment" and (item.classID == 2 or item.classID == 4)
            or category == "other" and item.classID ~= 2 and item.classID ~= 4
        if matchesCategory and (query == "" or string.find(string.lower(item.name), query, 1, true)) then result[#result + 1] = item end
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
