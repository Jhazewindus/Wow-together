local addonName, ns = ...

-- Keep the last known outdoor position in memory. PLAYER_ENTERING_WORLD fires
-- after the loading screen, so the indoor position cannot be used as an
-- entrance. Observations are personal and separated by client build.
local SAMPLE_INTERVAL = 0.5
local elapsed = 0
local lastOutdoor

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

local function buildKey()
    local _, build = ns.ReadPublic(GetBuildInfo)
    if ns.Public(build) and (type(build) == "string" or type(build) == "number") then
        return tostring(build)
    end
    return "unknown"
end

local function inInstance()
    local inside, kind = ns.ReadPublic(IsInInstance)
    return inside == true and kind ~= "none"
end

local function updateOutdoorPosition()
    if inInstance() then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID, 1000000) or mapID < 1 then return end
    local point = ns.PlayerPoint(mapID)
    if type(point) ~= "table" or not ns.Public(point)
        or point.mapID ~= mapID or not finite(point.x) or not finite(point.y)
        or point.x < 0 or point.x > 1 or point.y < 0 or point.y > 1 then return end
    lastOutdoor = {mapID = mapID, x = point.x, y = point.y}
end

local function saveEntrance()
    if not inInstance() or not lastOutdoor or type(ns.char) ~= "table" then return end
    if type(GetInstanceInfo) ~= "function" then return end
    local okay, name, _, _, _, _, _, _, instanceID = pcall(GetInstanceInfo)
    local cleanName = ns.Public(name) and ns.SafeTitle(name)
    if not okay or not cleanName
        or not ns.Public(instanceID) or not ns.GuideInteger(instanceID, 10000000) or instanceID < 1 then return end
    local build = buildKey()
    ns.char.instanceEntrances = type(ns.char.instanceEntrances) == "table" and ns.char.instanceEntrances or {}
    local observations = ns.char.instanceEntrances[build]
    if type(observations) ~= "table" then observations = {}; ns.char.instanceEntrances[build] = observations end
    local key = tostring(instanceID) .. "|" .. cleanName
    local observedAt = ns.ReadPublic(GetServerTime)
    observations[key] = {name = cleanName, instanceID = instanceID, build = build,
        mapID = lastOutdoor.mapID, x = lastOutdoor.x, y = lastOutdoor.y,
        observedAt = finite(observedAt) and observedAt or nil,
        source = "Observed from the last outdoor position before PLAYER_ENTERING_WORLD."}
end

function ns.InitializeInstanceObservations()
    ns.char.instanceEntrances = type(ns.char.instanceEntrances) == "table" and ns.char.instanceEntrances or {}
    updateOutdoorPosition()
    if ns.instanceObservationFrame then return end
    local frame = CreateFrame("Frame")
    ns.instanceObservationFrame = frame
    frame:SetScript("OnUpdate", function(_, dt)
        elapsed = elapsed + (finite(dt) and dt or 0)
        if elapsed < SAMPLE_INTERVAL then return end
        elapsed = 0
        updateOutdoorPosition()
    end)
end

ns.On("PLAYER_ENTERING_WORLD", saveEntrance)

function ns.InstanceEntranceObservations()
    local all = ns.char and ns.char.instanceEntrances
    local current = type(all) == "table" and all[buildKey()]
    local result = {}
    for _, row in pairs(type(current) == "table" and current or {}) do
        if type(row) == "table" and ns.Public(row) and ns.SafeTitle(row.name)
            and ns.GuideInteger(row.instanceID, 10000000) and row.instanceID > 0
            and ns.GuideInteger(row.mapID, 1000000) and row.mapID > 0
            and finite(row.x) and row.x >= 0 and row.x <= 1
            and finite(row.y) and row.y >= 0 and row.y <= 1 then
            result[#result + 1] = {event = "instance-entrance", name = ns.SafeTitle(row.name),
                instanceID = row.instanceID, build = buildKey(), mapID = row.mapID,
                x = row.x, y = row.y, observedAt = finite(row.observedAt) and row.observedAt or nil,
                source = "Observed from the last outdoor position before PLAYER_ENTERING_WORLD."}
        end
    end
    table.sort(result, function(a, b)
        if a.instanceID ~= b.instanceID then return a.instanceID < b.instanceID end
        return a.name < b.name
    end)
    return result
end

function ns.InstanceEntranceDiagnostics(output)
    local rows = ns.InstanceEntranceObservations()
    output("Personal instance entrances: " .. #rows .. " observed for build " .. buildKey() .. ".")
end

ns.ResearchExportHook(ns.InstanceEntranceObservations)
