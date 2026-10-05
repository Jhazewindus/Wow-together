local addonName, ns = ...

-- Overland connections for the known base-world UI maps. This is geography
-- data, not level recommendations or road paths. Retest it as Forever changes;
-- boats, zeppelins, portals and distant quest-chain handoffs are not neighbours.
local edges = {
    {1411, 1413}, {1411, 1454}, {1412, 1413}, {1412, 1456},
    {1413, 1440}, {1413, 1441}, {1413, 1442}, {1413, 1445},
    {1440, 1439}, {1440, 1442}, {1440, 1447}, {1440, 1448},
    {1441, 1444}, {1441, 1446}, {1442, 1443}, {1443, 1444},
    {1446, 1449}, {1449, 1451}, {1448, 1450}, {1448, 1452}, {1450, 1452},
    {1420, 1421}, {1420, 1422}, {1420, 1458}, {1421, 1424},
    {1424, 1416}, {1424, 1417}, {1424, 1425}, {1416, 1422}, {1422, 1423},
    {1417, 1437}, {1437, 1432}, {1432, 1426}, {1432, 1418}, {1426, 1455},
    {1418, 1427}, {1427, 1428}, {1428, 1433}, {1433, 1429}, {1433, 1431},
    {1429, 1436}, {1429, 1431}, {1429, 1453}, {1436, 1431},
    {1431, 1434}, {1431, 1430}, {1430, 1435}, {1435, 1419},
}
local neighbours = {}
for _, edge in ipairs(edges) do
    for index = 1, 2 do
        local from, to = edge[index], edge[3 - index]
        neighbours[from] = neighbours[from] or {}; neighbours[from][to] = true
    end
end
local zoneFactions = {
    [1411] = "Horde", [1412] = "Horde", [1420] = "Horde", [1421] = "Horde",
    [1454] = "Horde", [1456] = "Horde", [1458] = "Horde",
    [1426] = "Alliance", [1429] = "Alliance", [1432] = "Alliance", [1436] = "Alliance",
    [1438] = "Alliance", [1439] = "Alliance", [1453] = "Alliance", [1455] = "Alliance", [1457] = "Alliance",
}
local linkCache = {}
function ns.ResetZoneConnections() linkCache = {} end

function ns.KnownZoneMaps()
    local result = {}
    for id in pairs(neighbours) do result[id] = true end
    for id in pairs(zoneFactions) do result[id] = true end
    if ns.profile and ns.profile.mapID > 0 then result[ns.profile.mapID] = true end
    return result
end

function ns.NearbyZoneMaps(mapID)
    local result = {}; if not ns.GuideInteger(mapID, 1000000) or mapID <= 0 then return result end
    if linkCache[mapID] then return linkCache[mapID] end
    result[mapID] = true
    for id in pairs(neighbours[mapID] or {}) do result[id] = true end
    -- A new beta zone can expose a direct map link. Accept only same-parent
    -- zone maps and reject transport links; a map link alone is not a road.
    local zoneType = Enum and Enum.UIMapType and Enum.UIMapType.Zone
    local from = C_Map and ns.ReadPublic(C_Map.GetMapInfo, mapID)
    local links = C_Map and ns.ReadPublic(C_Map.GetMapLinksForMap, mapID)
    if not ns.Public(zoneType) or type(zoneType) ~= "number" or type(from) ~= "table" or type(links) ~= "table"
        or not ns.Public(from.parentMapID) or not ns.GuideInteger(from.parentMapID) or from.parentMapID <= 0 then return result end
    for index, link in ipairs(links) do
        if index > 40 then break end
        if ns.Public(link) and type(link) == "table" and ns.Public(link.linkedUiMapID)
            and ns.GuideInteger(link.linkedUiMapID, 1000000) and link.linkedUiMapID > 0 and ns.Public(link.atlasName) then
            local atlas = type(link.atlasName) == "string" and string.lower(link.atlasName) or ""
            local transport = string.find(atlas, "portal", 1, true) or string.find(atlas, "boat", 1, true)
                or string.find(atlas, "zeppelin", 1, true) or string.find(atlas, "flight", 1, true)
            local to = ns.ReadPublic(C_Map.GetMapInfo, link.linkedUiMapID)
            if not transport and atlas ~= "" and type(to) == "table" and ns.Public(to.mapType) and ns.Public(to.parentMapID)
                and to.mapType == zoneType and to.parentMapID == from.parentMapID then result[link.linkedUiMapID] = true end
        end
    end
    linkCache[mapID] = result
    return result
end

function ns.DiscoveryZoneAllowed(mapID, point)
    local current = ns.profile and ns.profile.mapID or 0
    local faction = ns.profile and ns.profile.faction
    if zoneFactions[mapID] and faction and faction ~= "Unknown" and zoneFactions[mapID] ~= faction then return false end
    if mapID == current then return true end
    if not ns.NearbyZoneMaps(current)[mapID] then return false end
    local position = ns.PlayerPoint(current)
    local distance = position and point and ns.CrossMapDistance and ns.CrossMapDistance(position, point)
    -- Known overland neighbours remain useful without world-position APIs.
    -- Newly exposed links must also have a public, short walking estimate.
    if distance then return distance <= 7500 end
    return neighbours[current] and neighbours[current][mapID] == true or false
end

function ns.ZonePreference(mapID)
    return ns.profile and mapID == ns.profile.mapID and 600 or 0
end
