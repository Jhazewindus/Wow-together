local addonName, ns = ...

-- Where an instance's door is, learned by walking through it.
--
-- The five dungeons that are new in Forever ship with no entrance position,
-- and a quest route cannot end "then go to the entrance" without one. No
-- outside source has them. But the player supplies it the first time they go
-- in: the last place they stood outdoors before the loading screen is the
-- door, to within a few steps.
--
-- So while the player is outdoors their position is noted every few seconds,
-- and on arriving inside a dungeon or raid the last noted position is saved
-- as that instance's entrance. It is kept for the account (ns.db), which
-- ns.DungeonEntrance already reads first. An instance that has a published
-- entrance keeps it: this only fills gaps, and a second visit does not move
-- an entrance that was recorded on the first.

local INTERVAL = 3
local lastOutdoors, sampleElapsed

local function inside()
    local inInstance, kind = ns.ReadPublic(IsInInstance)
    return inInstance == true and (kind == "party" or kind == "raid"), kind
end

local function raidKey()
    if type(GetInstanceInfo) ~= "function" then return nil end
    local okay, name = pcall(GetInstanceInfo)
    if not okay or type(name) ~= "string" then return nil end
    local wanted = string.lower(string.gsub(name, "[^%w]", ""))
    for _, raid in ipairs(ns.instanceRaids or {}) do
        if string.lower(string.gsub(raid.name or "", "[^%w]", "")) == wanted then return raid.key end
    end
end

local function published(key)
    for _, group in ipairs(ns.DungeonGroups and ns.DungeonGroups() or {}) do
        if group.key == key then
            for _, point in ipairs(group.definition and group.definition.entrances or {}) do
                if ns.ValidTravelPoint(point) then return true end
            end
            return false
        end
    end
    return false
end

local function note()
    if not inside() and ns.PlayerSpot then
        local spot = ns.PlayerSpot()
        if type(spot) == "table" and ns.ValidTravelPoint(spot) then lastOutdoors = {mapID = spot.mapID, x = spot.x, y = spot.y} end
    end
end

function ns.RecordInstanceEntrance()
    local isInside, kind = inside()
    if not isInside or not lastOutdoors or not ns.db then return false end
    local key, instanceID
    if kind == "party" and ns.DungeonEntryKey then
        key, instanceID = ns.DungeonEntryKey()
    elseif kind == "raid" then
        key = raidKey()
        local _, _, _, _, _, _, _, id = ns.ReadPublic(GetInstanceInfo)
        instanceID = id
    end
    if type(key) ~= "string" then return false end
    ns.db.dungeonEntrances = type(ns.db.dungeonEntrances) == "table" and ns.db.dungeonEntrances or {}
    if published(key) then return false end
    local _, buildValue = ns.ReadPublic(GetBuildInfo)
    local build = ns.Public(buildValue) and tostring(buildValue) or "unknown"
    ns.db.dungeonEntranceObservations = type(ns.db.dungeonEntranceObservations) == "table"
        and ns.db.dungeonEntranceObservations or {}
    local byBuild = ns.db.dungeonEntranceObservations[build]
    if type(byBuild) ~= "table" then byBuild = {}; ns.db.dungeonEntranceObservations[build] = byBuild end
    if ns.ValidTravelPoint(byBuild[key]) then return false end
    local point = {mapID = lastOutdoors.mapID, x = lastOutdoors.x, y = lastOutdoors.y,
        build = build, instanceID = ns.GuideInteger(instanceID) and instanceID or nil,
        observed = true, source = "Noted on walking in"}
    byBuild[key] = point
    -- Keep the first personal point as the route anchor while retaining each
    -- build's observation separately for the manual research export.
    if not ns.ValidTravelPoint(ns.db.dungeonEntrances[key]) then ns.db.dungeonEntrances[key] = point end
    ns.activityRevision = (ns.activityRevision or 0) + 1
    if ns.Print then ns.Print("Entrance noted. Routes for this instance can now lead you to its door.") end
    return true, key
end

ns.On("PLAYER_ENTERING_WORLD", function()
    -- The instance's name is not always readable the instant the world loads.
    ns.After("timer:EntranceCapture", 1, function() ns.RecordInstanceEntrance() end)
end)

-- Sample outdoors without a repeating timer: timer queues in the addon test
-- harness must drain, and an always-rescheduling timer obscures real hangs.
local tracker = CreateFrame("Frame")
tracker:SetScript("OnUpdate", function(_, elapsed)
    local isInside = inside()
    if isInside then sampleElapsed = 0; return end
    if type(elapsed) ~= "number" or elapsed < 0 or elapsed ~= elapsed then return end
    sampleElapsed = (sampleElapsed or 0) + elapsed
    if sampleElapsed >= INTERVAL then
        sampleElapsed = sampleElapsed % INTERVAL
        note()
    end
end)

function ns.EntranceCaptureDiagnostics(output)
    local count = 0
    for _, rows in pairs(ns.db and type(ns.db.dungeonEntranceObservations) == "table"
        and ns.db.dungeonEntranceObservations or {}) do
        if type(rows) == "table" then
            for _, point in pairs(rows) do
                if type(point) == "table" and point.observed and ns.ValidTravelPoint(point) then count = count + 1 end
            end
        end
    end
    output("Instance entrances: " .. count .. " learned by walking in; position noted every " .. INTERVAL .. " s outdoors.")
end

-- Keep the player's observations personal, anonymous, build-specific, and
-- available through the existing manual /wt research export.
if ns.hooks and type(ns.hooks.researchExport) == "table" then
    ns.hooks.researchExport[#ns.hooks.researchExport + 1] = function()
        local events, observations = {}, ns.db and ns.db.dungeonEntranceObservations or {}
        local builds = {}
        for build in pairs(type(observations) == "table" and observations or {}) do
            if type(build) == "string" then builds[#builds + 1] = build end
        end
        table.sort(builds)
        for _, build in ipairs(builds) do
            local rows = observations[build]
            local keys = {}
            if type(rows) == "table" then
                for key in pairs(rows) do if type(key) == "string" then keys[#keys + 1] = key end end
            end
            table.sort(keys)
            for _, key in ipairs(keys) do
                local point = rows[key]
                if point and point.observed == true and point.build == build and ns.ValidTravelPoint(point) then
                    events[#events + 1] = {event = "dungeon-entrance", dungeonKey = key,
                        build = build, instanceID = ns.GuideInteger(point.instanceID) and point.instanceID or nil,
                        mapID = point.mapID, x = point.x, y = point.y,
                        source = "Noted on walking in"}
                end
            end
        end
        return events
    end
end

ns.NoteOutdoorSpot = note      -- for tests
