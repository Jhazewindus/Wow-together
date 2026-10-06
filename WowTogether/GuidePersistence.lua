local addonName, ns = ...

-- Store only guide instructions, never frames, functions or peer quest credit.
local guideFields = {"key", "title", "zone", "mode", "mapID", "homeMapID", "fullGuide", "fixedRoute", "personal",
    "rangeLow", "rangeHigh", "reason", "kind", "destination", "catchup", "guideKey", "xpStartLevel", "xpStart",
    "xpFinishLevel", "xpReward", "xpUnknown", "xpBaseline", "xpUnavailable", "xpAssumedStart", "classQuestScope"}
local recordFields = {"id", "title", "level", "mapID", "x", "y", "npc", "source", "lineID", "lineName", "seriesRoot", "seriesName"}
local stepFields = {"id", "kind", "mapID", "x", "y", "title", "label", "entityID", "action", "itemName", "targetName",
    "npcName", "published", "planned", "unknownLocation", "guideStep", "planNeedsReview", "learnedSource", "alternativeCount",
    "quantity", "itemID", "objectiveKey", "useItemName", "spellID", "entityType", "worldFallback", "legacyStepKey", "sourceAction",
    "progressName", "objectiveLabel", "quantityUnknown", "sourceZone"}
local cachedGuide, cachedPlan, cachedBatch, cachedVisit
ns.guideResumeStatus = "No saved guide to resume."

local function fields(source, keys)
    local result = {}
    for _, key in ipairs(keys) do
        local value = source[key]
        if ns.Public(value) then
            local kind = type(value)
            if kind == "boolean" or kind == "string" and #value <= 1000
                or kind == "number" and value == value and math.abs(value) < math.huge then result[key] = value end
        end
    end
    return result
end

local function step(source)
    local result = fields(source, stepFields)
    local alternatives = source.alternativeEntityIDs
    if ns.Public(alternatives) and type(alternatives) == "table" and #alternatives <= 256 then
        local ids, seen = {}, {}
        for _, id in ipairs(alternatives) do
            if not ns.Public(id) or not ns.GuideInteger(id) or id <= 0 or seen[id] then return result end
            ids[#ids + 1], seen[id] = id, true
        end
        if #ids > 0 then result.alternativeEntityIDs = ids end
    end
    return result
end

local function descriptor(guide, depth)
    local result = fields(guide, guideFields)
    if not result.key then return end
    if guide.mode == "travel" then return result end
    result.records, result.pickupIDs, result.batchIDs, result.catchupTargets, result.catchupRequired, result.npcVisitPickupIDs = {}, {}, {}, {}, {}, {}
    local ids = {}
    for index, record in ipairs(guide.records or {}) do
        if index > 512 then return end
        if ns.GuideInteger(record.id) and record.id > 0 then
            result.records[#result.records + 1], ids[record.id] = fields(record, recordFields), true
        end
    end
    for _, key in ipairs({"pickupIDs", "catchupTargets", "catchupRequired"}) do
        for id in pairs(ids) do if guide[key] and guide[key][id] == true then result[key][id] = true end end
    end
    for _, id in ipairs(guide.batchIDs or {}) do if ids[id] then result.batchIDs[#result.batchIDs + 1] = id end end
    for _, id in ipairs(guide.npcVisitPickupIDs or {}) do if ids[id] then result.npcVisitPickupIDs[#result.npcVisitPickupIDs + 1] = id end end
    if guide.fixedPlan then
        result.fixedPlan = {}
        for index, stop in ipairs(guide.fixedPlan) do
            if index > 4096 then return end
            result.fixedPlan[index] = step(stop)
        end
    end
    if guide.baseGuide and depth == 0 then result.baseGuide = descriptor(guide.baseGuide, 1) end
    return #result.records > 0 and result or nil
end

function ns.InitializeGuidePersistence()
    if type(ns.db.guideState) ~= "table" then ns.db.guideState = {} end
    local saved = ns.db.guideState[ns.self]
    if type(saved) == "table" and saved.schema == 1 and type(saved.guide) == "table" then
        ns.pendingSavedGuide = saved
        ns.guideResumeStatus = "Saved guide will resume after login."
    end
end

function ns.SaveSelectedGuide()
    local guide = ns.routeSelection
    if not ns.db or not ns.db.guideState or not ns.self or not guide then return end
    if cachedGuide == guide and cachedPlan == guide.fixedPlan and cachedBatch == guide.batchIDs and cachedVisit == guide.npcVisitPickupIDs then return end
    local saved = descriptor(guide, 0)
    if not saved then return end
    ns.db.guideState[ns.self] = {schema = 1, addon = ns.VERSION, guide = saved}
    cachedGuide, cachedPlan, cachedBatch = guide, guide.fixedPlan, guide.batchIDs
    cachedVisit = guide.npcVisitPickupIDs
end

function ns.ClearSavedGuide()
    ns.pendingSavedGuide, ns.resumingGuide = nil, nil
    cachedGuide, cachedPlan, cachedBatch, cachedVisit = nil, nil, nil, nil
    if ns.db and ns.db.guideState and ns.self then ns.db.guideState[ns.self] = nil end
end

local function restore(saved, reusePlan, depth)
    if type(saved) == "table" and saved.mode == "travel" then return ns.RestoreTravelGuide(saved.key) end
    if type(saved) ~= "table" or type(saved.records) ~= "table" or #saved.records == 0 or #saved.records > 512 then return end
    local guide, ids = fields(saved, guideFields), {}
    if type(guide.key) ~= "string" or guide.key == "" or not ns.SafeTitle(guide.title) then return end
    guide.records, guide.focusKey, guide.profilesReady = {}, ns.self, true
    for _, record in ipairs(saved.records) do
        if type(record) ~= "table" or not ns.GuideInteger(record.id) or record.id <= 0 or ids[record.id] then return end
        local current = ns.CatalogueRecord(record.id) or fields(record, recordFields)
        if not ns.SafeTitle(current.title) then return end
        guide.records[#guide.records + 1], ids[record.id] = current, true
    end
    guide.target = guide.records[1]
    if guide.mode == "zone" and guide.fullGuide and not guide.catchup and not guide.classQuestScope then
        -- Older releases omitted disabled class quests from the checkpoint.
        -- Restore the full catalogue scope once; later toggles reuse its order.
        local records = ns.LevelingGuideRecords(guide.key)
        if records and #records >= 2 then
            guide.records, guide.target, guide.classQuestScope, reusePlan = records, records[1], true, false
            ids = {}; for _, record in ipairs(records) do ids[record.id] = true end
        end
    end
    guide.pickupIDs, guide.batchIDs, guide.catchupTargets, guide.catchupRequired = {}, {}, {}, {}
    for _, key in ipairs({"pickupIDs", "catchupTargets", "catchupRequired"}) do
        if type(saved[key]) == "table" then for id in pairs(ids) do if saved[key][id] == true then guide[key][id] = true end end end
    end
    if type(saved.batchIDs) == "table" then
        for index, id in ipairs(saved.batchIDs) do if index <= 6 and ids[id] then guide.batchIDs[#guide.batchIDs + 1] = id end end
    end
    if type(saved.npcVisitPickupIDs) == "table" then
        guide.npcVisitPickupIDs = {}
        local seen = {}
        for index, id in ipairs(saved.npcVisitPickupIDs) do
            if index <= 512 and ids[id] and not seen[id] then
                guide.npcVisitPickupIDs[#guide.npcVisitPickupIDs + 1], seen[id] = id, true
            end
        end
    end
    if reusePlan and guide.fixedRoute and type(saved.fixedPlan) == "table" and #saved.fixedPlan <= 4096 then
        local plan = {}
        for index, source in ipairs(saved.fixedPlan) do
            if type(source) ~= "table" then return end
            local stop = step(source)
            if not ids[stop.id] or (stop.kind ~= "a" and stop.kind ~= "q" and stop.kind ~= "t")
                or not ns.GuideInteger(stop.mapID) or stop.guideStep ~= index then return end
            if not stop.unknownLocation and (type(stop.x) ~= "number" or type(stop.y) ~= "number"
                or stop.x < 0 or stop.x > 1 or stop.y < 0 or stop.y > 1) then return end
            plan[index] = stop
        end
        if #plan > 0 then guide.fixedPlan = plan end
    end
    if depth == 0 and saved.baseGuide then guide.baseGuide = restore(saved.baseGuide, reusePlan, 1) end
    if guide.mode == "dungeon" then
        for _, group in ipairs(ns.DungeonGroups()) do
            if guide.key == "dungeon:" .. group.key then guide.dungeon, guide.entrance = group, ns.DungeonEntrance(group); break end
        end
        if not guide.dungeon then return end
    end
    return guide
end

function ns.RestoreSavedGuide()
    local saved = ns.pendingSavedGuide
    if not saved or ns.routeSelection or ns.routePlanning then return end
    if ns.RouteInCombat() then return end
    ns.ReadQuests(); ns.ReadGuide(); ns.ReadProgress()
    local guide = restore(saved.guide, saved.addon == ns.VERSION, 0)
    ns.pendingSavedGuide = nil
    if not guide then
        ns.ClearSavedGuide(); ns.guideResumeStatus = "Saved guide data was invalid; select a guide again."; return
    end
    ns.guideResumeStatus = "Resuming " .. guide.title .. " using current quest progress."
    ns.resumingGuide = guide
    ns.RouteHistoryScope(guide.records)
    ns.ScheduleSync()
    if guide.fullGuide then ns.PlanLevelingGuide(guide, false)
    else
        local route = ns.BuildGuideRoute(guide, false)
        ns.ActivateRoute(guide, route); ns.resumingGuide = nil; ns.Refresh()
    end
end

ns.On("PLAYER_LOGOUT", function() ns.SaveSelectedGuide() end)
