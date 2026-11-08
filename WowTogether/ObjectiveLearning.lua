local addonName, ns = ...

-- Objective locations are account-wide facts tied to the exact client build.
-- They remain observations until promoted by a human-reviewed correction.
local MAX_OBJECTIVES, MAX_POINTS, MIN_SAMPLES = 2000, 6, 3
local MAX_PENDING = 400
local pending, received, questStarts = {}, {}, {}
local counters = {received = 0, rejected = 0}

local function buildID()
    local _, build = ns.ReadPublic(GetBuildInfo)
    return ns.Public(build) and tostring(build) or "unknown"
end

local function objectiveCount(store)
    local total = 0
    for _, quests in pairs(store or {}) do
        for _, objectives in pairs(quests) do
            for _ in pairs(objectives) do total = total + 1 end
        end
    end
    return total
end

local function pruneBuilds()
    local all = ns.db.objectiveAreas
    local builds = {}
    for key in pairs(all) do builds[#builds + 1] = key end
    table.sort(builds, function(a, b)
        local ta, tb = all[a].updated or 0, all[b].updated or 0
        if ta ~= tb then return ta < tb end
        return tostring(a) < tostring(b)
    end)
    while #builds > 2 do
        all[table.remove(builds, 1)] = nil
    end
end

local function timestamp()
    local value = ns.ReadPublic(time)
    return ns.GuideInteger(value) and value or 0
end

function ns.InitializeObjectiveLearning()
    if type(ns.db.objectiveAreas) ~= "table" then ns.db.objectiveAreas = {} end
    if type(ns.db.objectiveSequence) ~= "number" or ns.db.objectiveSequence < 0 then ns.db.objectiveSequence = 0 end
    if type(ns.db.objectiveMessageSequence) ~= "table" then ns.db.objectiveMessageSequence = {} end
    received = ns.db.objectiveMessageSequence
    ns.objectiveBuild = buildID()
    local store = ns.db.objectiveAreas[ns.objectiveBuild]
    if type(store) ~= "table" then store = {}; ns.db.objectiveAreas[ns.objectiveBuild] = store end
    for questID, objectives in pairs(store) do
        if not ns.GuideInteger(questID) or questID <= 0 or type(objectives) ~= "table" then store[questID] = nil
        else
            for index, record in pairs(objectives) do
                if not ns.GuideInteger(index, 12) or index <= 0 or type(record) ~= "table" or type(record.points) ~= "table" then
                    objectives[index] = nil
                else
                    for i = #record.points, 1, -1 do
                        local point = record.points[i]
                        if type(point) ~= "table" or not ns.GuideInteger(point.mapID) or point.mapID <= 0
                            or type(point.x) ~= "number" or type(point.y) ~= "number"
                            or point.x < 0 or point.x > 1 or point.y < 0 or point.y > 1 then
                            table.remove(record.points, i)
                        else
                            point.n = ns.GuideInteger(point.n) and point.n or 1
                            point.observers = type(point.observers) == "table" and point.observers or {}
                        end
                    end
                    if #record.points == 0 then objectives[index] = nil end
                end
            end
            if next(objectives) == nil then store[questID] = nil end
        end
    end
    pruneBuilds()
end

local function distance(a, b)
    if a.mapID ~= b.mapID then return math.huge end
    local width, height
    if C_Map then width, height = ns.ReadPublic(C_Map.GetMapWorldSize, a.mapID) end
    if type(width) ~= "number" or type(height) ~= "number" then return math.huge end
    return math.sqrt(((a.x - b.x) * width)^2 + ((a.y - b.y) * height)^2)
end

local function trimObjective(objective)
    while #objective.points > MAX_POINTS do
        local ai, bi, nearest = nil, nil, math.huge
        for i = 1, #objective.points do
            for j = i + 1, #objective.points do
                local d = distance(objective.points[i], objective.points[j])
                if d < nearest then ai, bi, nearest = i, j, d end
            end
        end
        if not ai then table.remove(objective.points, 1)
        else
            local a, b = objective.points[ai], objective.points[bi]
            if a.mapID == b.mapID and a.n + b.n > 0 then
                local total = a.n + b.n
                a.x, a.y = (a.x * a.n + b.x * b.n) / total, (a.y * a.n + b.y * b.n) / total
                a.n = total
                for observer in pairs(b.observers or {}) do a.observers[observer] = true end
            end
            table.remove(objective.points, bi)
        end
    end
end

local function appendSample(build, questID, index, point, observer)
    if type(ns.db.objectiveAreas[build]) ~= "table" then ns.db.objectiveAreas[build] = {} end
    local store = ns.db.objectiveAreas[build]
    local quests = store[questID]
    if type(quests) ~= "table" then quests = {}; store[questID] = quests end
    local objective = quests[index]
    if type(objective) ~= "table" then
        if objectiveCount(store) >= MAX_OBJECTIVES then
            local oldQuest, oldIndex, oldest
            for id, records in pairs(store) do
                for oldKey, candidate in pairs(records) do
                    if not oldest or (candidate.updated or 0) < oldest then
                        oldQuest, oldIndex, oldest = id, oldKey, candidate.updated or 0
                    end
                end
            end
            if oldQuest then
                store[oldQuest][oldIndex] = nil
                if next(store[oldQuest]) == nil then store[oldQuest] = nil end
            end
        end
        quests = store[questID] or {}; store[questID] = quests
        objective = {points = {}, updated = 0}; quests[index] = objective
    end
    local target
    for _, candidate in ipairs(objective.points) do
        if distance(candidate, point) <= 60 then target = candidate; break end
    end
    if target then
        local n = target.n or 1
        target.x, target.y = (target.x * n + point.x) / (n + 1), (target.y * n + point.y) / (n + 1)
        target.n = n + 1
    else
        target = {x = point.x, y = point.y, mapID = point.mapID, n = 1, observers = {}}
        objective.points[#objective.points + 1] = target
    end
    target.observers = target.observers or {}
    target.observers[observer] = true
    objective.updated = timestamp()
    trimObjective(objective)
    pruneBuilds()
end

local function playerPoint()
    if ns.ReadPublic(UnitOnTaxi, "player") == true or ns.ReadPublic(UnitIsDeadOrGhost, "player") == true then return end
    local inInstance = ns.ReadPublic(IsInInstance)
    if inInstance == true then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) or mapID <= 0 then return end
    local point = ns.PlayerPoint(mapID)
    if not point or not ns.ValidTravelPoint(point) then return end
    return {mapID = mapID, x = point.x, y = point.y}
end

local function eligible(questID)
    if not ns.Option("learnObjectives") or not ns.active[questID] then return false end
    if ns.IsRepeatableQuest and ns.IsRepeatableQuest(questID) then return false end
    local quest = ns.CatalogueQuest(questID)
    if quest and (quest.repeatable or quest.daily or quest.weekly) then return false end
    return true
end

function ns.RecordObjectiveProgress()
    if not ns.db or not ns.ObjectiveSnapshotDelta then return end
    local point = playerPoint()
    if not point then return end
    for questID in pairs(ns.active or {}) do
        if eligible(questID) then
            local deltas = ns.ObjectiveSnapshotDelta(questID)
            for index, delta in pairs(deltas or {}) do
                local kind = delta.kind or "other"
                local samplePosition = point
                if kind == "event" or kind == "escort" then
                    samplePosition = questStarts[questID]
                    if questStarts[questID] then questStarts[questID] = nil end
                end
                if samplePosition then
                    local objective = {mapID = samplePosition.mapID, x = samplePosition.x, y = samplePosition.y}
                    appendSample(ns.objectiveBuild or buildID(), questID, index, objective, ns.self or "player")
                    ns.db.objectiveSequence = ns.db.objectiveSequence + 1
                    local msg = table.concat({"1", "O", ns.objectiveBuild or buildID(), questID, index, samplePosition.mapID,
                        string.format("%.5f,%.5f", samplePosition.x, samplePosition.y), ns.db.objectiveSequence}, "|")
                    if #msg <= 255 then
                        pending[#pending + 1] = msg
                        while #pending > MAX_PENDING do table.remove(pending, 1) end
                    end
                end
            end
        end
    end
end

function ns.LearnedObjectivePoint(questID, index, includeUnconfirmed)
    local objectives = ns.db and ns.db.objectiveAreas and ns.db.objectiveAreas[ns.objectiveBuild or buildID()]
        and ns.db.objectiveAreas[ns.objectiveBuild or buildID()][questID]
    local record = objectives and objectives[index]
    local best, total = nil, 0
    for _, point in ipairs(record and record.points or {}) do
        total = total + (point.n or 1)
        if not best or (point.n or 0) > (best.n or 0) then best = point end
    end
    if not best or not includeUnconfirmed and total < MIN_SAMPLES then return end
    local result = {}; for key, value in pairs(best) do result[key] = value end
    result.totalSamples = total
    return result
end

function ns.ObjectiveLearningSharePump(room)
    if not ns.Option("shareObservations") or not ns.PartyFeaturesEnabled() or not IsInGroup() or not IsInGroup(LE_PARTY_CATEGORY_HOME) then return room end
    room = room or 0
    while room > 0 and pending[1] do
        if not ns.QueueMessage(pending[1]) then break end
        table.remove(pending, 1); room = room - 1
    end
    return room
end

function ns.ReceiveObjectiveMessage(message, sender)
    if string.sub(message, 1, 4) ~= "1|O|" then return false end
    local build, questID, index, mapID, coords, sequence = string.match(message,
        "^1|O|([%w%-]+)|(%d+)|(%d+)|(%d+)|([%d%.]+,[%d%.]+)|(%d+)$")
    -- 1|O is an existing quest-offer transport kind. Objective messages have
    -- the longer, coordinate-bearing shape; preserve every legacy offer packet.
    if not build then return false end
    if not ns.Option("shareObservations") then return true, false, "objective sharing off" end
    questID, index, mapID, sequence = tonumber(questID), tonumber(index), tonumber(mapID), tonumber(sequence)
    if not build or #build > 16 or not ns.GuideInteger(questID) or questID <= 0
        or not ns.GuideInteger(index, 12) or index <= 0 or not ns.GuideInteger(mapID, 1000000) or mapID <= 0
        or not ns.GuideInteger(sequence) or sequence <= 0 then
        counters.rejected = counters.rejected + 1; return true, false, "invalid objective message"
    end
    if sequence <= (received[sender] or 0) then return true, false, "duplicate objective message" end
    local x, y = string.match(coords, "^([%d%.]+),([%d%.]+)$"); x, y = tonumber(x), tonumber(y)
    if not x or not y or x < 0 or x > 1 or y < 0 or y > 1 then
        counters.rejected = counters.rejected + 1; return true, false, "invalid objective coordinate"
    end
    received[sender] = sequence
    local store = ns.db.objectiveMessageSequence
    store[sender] = sequence
    appendSample(build, questID, index, {mapID = mapID, x = x, y = y}, sender)
    counters.received = counters.received + 1
    return true, true
end

function ns.ObjectiveAreaResearchEvents()
    local events, profile = {}, ns.profile or {}
    local saved = ns.char and ns.char.questResearch
    for build, quests in pairs(ns.db and ns.db.objectiveAreas or {}) do
        for questID, objectives in pairs(quests) do
            for index, record in pairs(objectives) do
                for _, point in ipairs(record.points or {}) do
                    local observerCount = 0; for _ in pairs(point.observers or {}) do observerCount = observerCount + 1 end
                    local event = {event = "objective-area", build = build, session = saved and saved.session or 0,
                        observerID = ns.QuestResearchObserverID and ns.QuestResearchObserverID(),
                        classID = profile.classID, raceID = profile.raceID, level = profile.level, faction = profile.faction,
                        questID = questID,
                        objectiveIndex = index, mapID = point.mapID, x = point.x, y = point.y,
                        n = point.n or 1, observers = observerCount,
                        points = {{mapID = point.mapID, x = point.x, y = point.y, n = point.n or 1}}}
                    events[#events + 1] = event
                end
            end
        end
    end
    return events
end

function ns.ObjectiveLearningDiagnostics(output)
    local store = ns.db and ns.db.objectiveAreas and ns.db.objectiveAreas[ns.objectiveBuild] or {}
    local objectives, points = 0, 0
    for _, records in pairs(store) do for _, record in pairs(records) do objectives = objectives + 1; points = points + #record.points end end
    output("Observed objective areas: " .. objectives .. " objectives, " .. points .. " points; " .. counters.received .. " received.")
end

ns.On("QUEST_ACCEPTED", function(id)
    if ns.GuideInteger(id) and ns.active then questStarts[id] = playerPoint() end
end)
ns.On("PLAYER_ENTERING_WORLD", function() if ns.db then ns.InitializeObjectiveLearning() end end)
