local addonName, ns = ...

local cachedBaselineSignature, cachedBaseline
local keptLowValue = {}

function ns.KeepLowValueQuest(id)
    if not ns.GuideInteger(id) or id <= 0 then return false end
    keptLowValue[id] = true
    if ns.Refresh then ns.Refresh() end
    return true
end

function ns.AbandonLowValueQuest(id)
    if not ns.GuideInteger(id) or id <= 0 or not ns.active[id] then return false end
    local combat = type(InCombatLockdown) == "function" and InCombatLockdown()
    if not ns.Public(combat) or combat == true then
        ns.Print("Leave combat before abandoning a quest.")
        return false
    end
    local log = C_QuestLog
    local index = log and ns.ReadPublic(log.GetLogIndexForQuestID, id)
    if not index then return false end
    if log.SetSelectedQuest then ns.ReadPublic(log.SetSelectedQuest, id) end
    if log and type(log.AbandonQuest) == "function" then
        local okay = pcall(log.AbandonQuest)
        if not okay then return false end
    elseif type(AbandonQuest) == "function" then
        local okay = pcall(AbandonQuest)
        if not okay then return false end
    else return false end
    keptLowValue[id] = nil
    if ns.ReadQuests then ns.ReadQuests() end
    if ns.Refresh then ns.Refresh() end
    return true
end

-- Prefer worthwhile leveling work, rather than the entire green difficulty
-- band. Lower quests can still qualify through their useful continuations.
local function preferredFloor(level)
    return math.max(1, level - 3)
end

function ns.PreferredQuestLevels(query)
    local level = ns.PartyLevelFloor(query)
    if level then return preferredFloor(level), level + 3 end
end

function ns.PartyLevelFloor(query)
    if query and query.floor then return query.floor[1], query.floor[2], query.floor[3] end
    local level, key, name
    for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
        local value = person.profile and person.profile.level
        if person.synced and ns.GuideInteger(value) and value > 0 and
            (not level or value < level or value == level and person.key < key) then
            level, key, name = value, person.key, person.name
        end
    end
    key, name = key or ns.self, name or "You"
    if query then query.floor = {level, key, name} end
    return level, key, name
end

function ns.GuideFocus(records, query)
    local _, fallback = ns.PartyLevelFloor(query)
    local chosen, progress
    for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
        if person.synced then
            local done, checked, total = 0, 0, 0
            local active = person.key == ns.self and ns.active or ns.members[person.key].active
            for _, record in ipairs(records or {}) do
                if ns.ClassQuestEnabled(record.id) and ns.CatalogueIdentityAllowed(record.id, person.profile) ~= false then
                    total = total + 1
                    local completed = ns.CatalogueCompletion(person.key, record.id, query)
                    if completed ~= nil or active and active[record.id] then checked = checked + 1 end
                    if completed == true and not (active and active[record.id]) then done = done + 1 end
                end
            end
            -- Unknown history cannot establish that someone is behind.
            if total > 0 and checked == total then
                local value = done / total
                if not chosen or value < progress or value == progress and person.key < chosen then
                    chosen, progress = person.key, value
                end
            end
        end
    end
    return chosen or fallback
end

function ns.IsGroupQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and (quest.questType == "Elite" or quest.questType == "Raid") or false
end

function ns.QuestGroupWarning(id)
    if not ns.IsGroupQuest(id) then return end
    local quest = ns.CatalogueQuest(id)
    if quest.questType == "Raid" then return "Raid quest: bring a raid group, or use Skip quest." end
    return "Elite quest: bring a party for its objectives, or use Skip quest."
end

function ns.FocusCanStartRecord(record, key)
    local quest = ns.CatalogueQuest(record.id)
    if not quest then return true end
    local active = key == ns.self and ns.active or ns.members[key] and ns.members[key].active
    local profile = key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
    if active and active[record.id] or ns.CatalogueCompletion(key, record.id) == true
        or ns.CatalogueIdentityAllowed(record.id, profile) == false then return true end
    if quest.previousQuest or quest.prerequisiteAny or quest.prerequisiteAll then
        return ns.CatalogueAllowed(record.id, profile, key) == true
    end
    return true
end

function ns.QuestDifficultyLabel(id)
    if ns.IsDungeonQuest(id) then return "Dungeon / group" end
    if ns.IsGroupQuest(id) then return "Group / elite" end
    return "Normal quest"
end

local function nextQuests(id, key)
    local result = {}
    for nextID in pairs(ns.CatalogueFollowers(id)) do result[nextID] = true end
    for _, nextID in ipairs(ns.LearnedFollowers and ns.LearnedFollowers(id, key) or {}) do result[nextID] = true end
    return result
end

local function questMinutes(id)
    local quest = ns.CatalogueQuest(id)
    if not quest then return 8 end
    local total, count = 0, 0
    for _, objective in ipairs(quest.objectives or {}) do
        local amount = ns.GuideInteger(objective.quantity, 1000) and math.max(1, objective.quantity) or 1
        local action = objective.action or objective.sourceAction
        local seconds = action == "kill" and 35 or (action == "collect" or action == "loot" or action == "gather") and 45 or 75
        total, count = total + amount * seconds, count + 1
    end
    if count == 0 then return 8 end
    return math.max(4, total / 60 + 3) -- objective estimate plus travel and turn-in time
end

local function baselineRate(level, query)
    local guide = ns.routeSelection
    local signature = table.concat({tostring(ns.catalogue), level, guide and guide.key or "", #((guide and guide.records) or {}),
        ns.guideProgressRevision or 0, ns.questHistoryCount or 0, ns.objectiveDisplayRevision or 0,
        ns.xpSampleRevision or 0, ns.char and ns.char.questLearning and ns.char.questLearning.revision or 0}, ":")
    if signature == cachedBaselineSignature then return cachedBaseline end
    local candidates = {}
    local function consider(id, low, high)
        local quest = ns.CatalogueQuest(id)
        local questLevel = quest and (quest.level or quest.minLevel or 0)
        low, high = low or level - 3, high or level + 3
        if quest and questLevel >= low and questLevel <= high and ns.GuideInteger(quest.xp, 10000000)
            and quest.xp > 0 and ns.CatalogueCompletion(ns.self, id, query) ~= true
            and ns.ClassQuestEnabled(id) and not ns.IsLevelingExcludedQuest(id) and not ns.IsProfessionQuest(id)
            and not ns.IsRepeatableQuest(id) then
            candidates[#candidates + 1] = (ns.QuestXP(id, level) or quest.xp) / questMinutes(id)
        end
    end
    for _, record in ipairs(guide and guide.records or {}) do consider(record.id) end
    if #candidates < 3 then
        candidates = {}
        local nextGuide = ns.NextZoneBaselineGuide and ns.NextZoneBaselineGuide(guide, true)
        if nextGuide then
            for _, record in ipairs(nextGuide.records or {}) do consider(record.id, nextGuide.rangeLow, nextGuide.rangeLow + 3) end
        end
    end
    if #candidates < 3 then
        candidates = {}
        for questLevel = math.max(1, level - 3), math.min(60, level + 3) do
            for _, id in ipairs(ns.CatalogueQuestIDsAtLevel(questLevel)) do consider(id) end
        end
    end
    table.sort(candidates)
    if #candidates == 0 then cachedBaselineSignature, cachedBaseline = signature, nil; return nil end
    local middle = math.floor((#candidates + 1) / 2)
    cachedBaselineSignature, cachedBaseline = signature,
        #candidates % 2 == 1 and candidates[middle] or (candidates[middle] + candidates[middle + 1]) / 2
    return cachedBaseline
end

local function chainPaths(root, key, query, level)
    local profile = key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
    local paths, functionStack = {}, 0
    local function walk(path, seen)
        if #path >= 8 or functionStack >= 256 then paths[#paths + 1] = path; return end
        local last = path[#path]
        local nextIDs = {}
        for nextID in pairs(nextQuests(last, key)) do nextIDs[#nextIDs + 1] = nextID end
        table.sort(nextIDs, function(a, b)
            local qa, qb = ns.CatalogueQuest(a), ns.CatalogueQuest(b)
            local la, lb = qa and (qa.level or qa.minLevel or 0) or 0, qb and (qb.level or qb.minLevel or 0) or 0
            if la ~= lb then return la < lb end
            return a < b
        end)
        local added = false
        for _, nextID in ipairs(nextIDs) do
            if not seen[nextID] then
                functionStack = functionStack + 1
                local quest = ns.CatalogueQuest(nextID)
                if quest and not ns.IsLevelingExcludedQuest(nextID) and not quest.repeatable and not ns.IsProfessionQuest(nextID)
                    and ns.ClassQuestEnabled(nextID) and ns.CatalogueIdentityAllowed(nextID, profile) == true
                    then
                    local branch = {}; for index, value in ipairs(path) do branch[index] = value end
                    branch[#branch + 1] = nextID
                    local branchSeen = {}; for id in pairs(seen) do branchSeen[id] = true end; branchSeen[nextID] = true
                    walk(branch, branchSeen); added = true
                end
            end
        end
        if not added then paths[#paths + 1] = path end
    end
    walk({root}, {[root] = true})
    return paths
end

local function computeChainValue(id, query)
    local root = ns.CatalogueQuest(id)
    if not root then return nil end
    local level, key = ns.PartyLevelFloor(query)
    if not level then return nil end
    local baseline = baselineRate(level, query)
    local candidates, profile = chainPaths(id, key, query, level), key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
    if not baseline or baseline <= 0 then
        local path = candidates[1]
        if not path then return nil end
        return {questID = id, steps = path, totalSteps = #path, completedSteps = 0,
            remainingSteps = #path, xp = nil, minutes = nil, rate = nil, baseline = nil,
            committed = false, finalGreen = false, included = false,
            reason = "Chain worth cannot be estimated: current-level XP pace data is missing; review it under Also in this zone."}
    end
    local best
    for _, path in ipairs(candidates) do
        local xp, minutes, projectedLevel, projectedXP, completed = 0, 0, level, 0, 0
        local finalDifference = nil
        for _, stepID in ipairs(path) do
            local quest = ns.CatalogueQuest(stepID)
            local questLevel = quest and (quest.level or quest.minLevel or projectedLevel) or projectedLevel
            local earned = ns.QuestXP(stepID, projectedLevel) or quest and quest.xp or 0
            finalDifference = projectedLevel - questLevel
            local isDone = ns.CatalogueCompletion(key, stepID, query) == true
            if not isDone then
                xp, minutes = xp + earned, minutes + questMinutes(stepID)
                local threshold = ns.xpCurve and ns.xpCurve[projectedLevel] or ns.xpBaseline and ns.xpBaseline[projectedLevel]
                if threshold and threshold > 0 then
                    projectedXP = projectedXP + earned
                    while projectedLevel < 60 and projectedXP >= threshold do
                        projectedXP = projectedXP - threshold; projectedLevel = projectedLevel + 1
                        threshold = ns.xpCurve and ns.xpCurve[projectedLevel] or ns.xpBaseline and ns.xpBaseline[projectedLevel]
                        if not threshold or threshold <= 0 then break end
                    end
                end
            end
            local breadcrumb = stepID == path[1] and ns.CatalogueBreadcrumbTargets
                and #(ns.CatalogueBreadcrumbTargets(stepID) or {}) > 0
            if isDone and not breadcrumb then completed = completed + 1 end
        end
        local rate = minutes > 0 and xp / minutes or 0
        -- A final quest no more than five levels above the projected player
        -- still fits the chain; the explicit Stonetalon level-24 example
        -- keeps its level-27 endpoint eligible even before it turns green.
        local finalInRange = finalDifference and finalDifference >= -5 and finalDifference <= 5
        local committed = keptLowValue[id] == true or completed >= ns.ROUTE_WEIGHTS.chainCommitSteps
            and completed / #path > ns.ROUTE_WEIGHTS.chainCommitShare and finalDifference and finalDifference >= -5
        local included = committed or (#path > 1 and rate >= baseline * ns.ROUTE_WEIGHTS.chainEfficiency and finalInRange)
        local candidate = {questID = id, steps = path, totalSteps = #path, completedSteps = completed,
            remainingSteps = #path - completed, xp = xp, minutes = minutes, rate = rate, baseline = baseline,
            committed = committed, finalGreen = finalInRange == true, included = included,
            reason = committed and ("Finishing this chain: " .. tostring(#path - completed) .. " quests left, ~" .. tostring(math.floor(xp + 0.5)) .. " XP.")
                or ("Chain worth ~" .. tostring(math.floor(xp + 0.5)) .. " XP in ~" .. tostring(math.floor(minutes + 0.5))
                    .. " min; " .. (included and "on pace (included)." or "below your pace here (skip)."))}
        if not best or candidate.included and not best.included or candidate.rate > best.rate then best = candidate end
    end
    return best
end

function ns.ChainValue(id, query)
    if not query then return computeChainValue(id, query) end
    local profileKey = ns.PartyLevelFloor(query)
    local guide = query.guide or ns.routeSelection
    local key = table.concat({tostring(id), tostring(profileKey), tostring(guide and guide.key),
        tostring(guide and guide.mode), tostring(ns.guideProgressRevision or 0),
        tostring(ns.char and ns.char.questLearning and ns.char.questLearning.revision or 0)}, ":")
    local cache = query.policyCache
    if not cache then cache = {}; query.policyCache = cache end
    cache.chains = cache.chains or {}
    local cached = cache.chains[key]
    if cached ~= nil then return cached ~= false and cached or nil end
    local value = computeChainValue(id, query)
    cache.chains[key] = value or false
    if ns.policyMetrics then ns.policyMetrics.chainValueCalls = (ns.policyMetrics.chainValueCalls or 0) + 1 end
    return value
end

function ns.GuideEfficiencyMode(guide)
    local modes = ns.char and ns.char.guideModes
    local mode = guide and modes and modes[guide.key]
    return mode == "complete" and "complete" or "efficient"
end

function ns.SetGuideEfficiencyMode(guide, mode)
    if not guide or type(guide.key) ~= "string" or not ns.char then return false end
    ns.char.guideModes = type(ns.char.guideModes) == "table" and ns.char.guideModes or {}
    ns.char.guideModes[guide.key] = mode == "complete" and "complete" or nil
    guide.fixedPlan = nil
    if ns.routeSelection and ns.routeSelection.key == guide.key then ns.routeSelection.fixedPlan = nil end
    if ns.Refresh then ns.Refresh() end
    return true
end

function ns.GuideZoneFinishing(guide, profile, projection, query)
    if not guide or guide.mode ~= "zone" or ns.GuideEfficiencyMode(guide) == "complete" then return false end
    profile = profile or ns.profile or {}
    local level = profile.level
    if not ns.GuideInteger(level) then return false end
    local cache, cacheKey
    if query then
        local revisions = table.concat({tostring(guide.key), tostring(guide.mode), tostring(guide.rangeHigh),
            tostring(level), tostring(ns.guideProgressRevision or 0), tostring(ns.questHistoryCount or 0),
            tostring(ns.objectiveDisplayRevision or 0), tostring(ns.xpSampleRevision or 0)}, ":")
        local state = query.policyXPState
        if query.policyXPRevision ~= revisions or not state then
            state = ns.XPState and ns.XPState() or nil
            query.policyXPRevision, query.policyXPState = revisions, state
        end
        cache = query.policyCache
        if not cache then cache = {}; query.policyCache = cache end
        cache.zoneFinishing = cache.zoneFinishing or {}
        cacheKey = table.concat({revisions, tostring(state and state.level), tostring(state and state.xp),
            tostring(state and state.xpMax), tostring(ns.GuideEfficiencyMode(guide))}, ":")
        local cached = cache.zoneFinishing[cacheKey]
        if cached ~= nil then return cached end
    end
    local result = false
    if ns.Option("xpModel") then
        if ns.ZoneExitProjection then projection = projection or ns.ZoneExitProjection(guide, profile, query) end
        if projection and not projection.curveIncomplete then result = projection.level - level <= 1 end
    else
        result = ns.GuideInteger(guide.rangeHigh) and level >= guide.rangeHigh - 1 or false
    end
    if cache then
        cache.zoneFinishing[cacheKey] = result
        if ns.policyMetrics then ns.policyMetrics.zoneFinishingCalls = (ns.policyMetrics.zoneFinishingCalls or 0) + 1 end
    end
    return result
end

local function legacyUsefulQuestReason(id, key, level, query)
    if not ns.GuideInteger(level) then return end
    local queue, seen, cursor = {id}, {[id] = true}, 1
    local lower = preferredFloor(level)
    while queue[cursor] and cursor <= 128 do
        local previous = queue[cursor]; cursor = cursor + 1
        for nextID in pairs(nextQuests(previous, key)) do
            if not seen[nextID] then
                seen[nextID] = true
                local quest = ns.CatalogueQuest(nextID)
                local profile = key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
                if quest and not ns.IsLevelingExcludedQuest(nextID) and not quest.repeatable and not ns.IsProfessionQuest(nextID)
                    and ns.ClassQuestEnabled(nextID) and ns.CatalogueIdentityAllowed(nextID, profile) == true
                    and ns.CatalogueCompletion(key, nextID, query) ~= true then
                    local value = quest.level or 0
                    local dungeon = ns.IsDungeonQuest(nextID) and (quest.minLevel or value) <= level + 5 and value <= level + 8
                    if dungeon or value >= lower and value <= level + 3 then
                        return "Unlocks " .. quest.title .. (ns.IsDungeonQuest(nextID) and " (dungeon quest)." or " (level " .. value .. ").")
                    end
                    if #queue < 128 then queue[#queue + 1] = nextID end
                end
            end
        end
    end
end

function ns.UsefulQuestReason(id, key, level, query)
    local chain = ns.ChainValue(id, query)
    return chain and chain.reason or legacyUsefulQuestReason(id, key, level or ns.PartyLevelFloor(query), query)
end

local function levelingValue(id, query)
    local quest = ns.CatalogueQuest(id)
    if not quest then return true end
    local level, key = ns.PartyLevelFloor(query)
    if not level then return nil end
    local activeGuide = ns.routeSelection
    if ns.GuideEfficiencyMode(activeGuide) == "complete" and activeGuide
        and (activeGuide.mode == "zone" or activeGuide.mode == "bundle") then
        for _, record in ipairs(activeGuide.records or {}) do
            if record.id == id then return true, "Complete the zone; this quest is in the selected guide." end
        end
    end
    local zoneFinishing = query and query.zoneFinishing
    if zoneFinishing == nil then zoneFinishing = ns.GuideZoneFinishing(activeGuide, nil, nil, query) end
    if zoneFinishing then
        if ns.active[id] ~= nil then
            local activeChain = ns.ChainValue(id, query)
            if activeChain and activeChain.baseline and not activeChain.included and not activeChain.committed then
                activeChain.inLogLowValue = true
                local sentence = (ns.QuestTitle(id) or quest.title or "This quest") .. " is worth ~"
                    .. tostring(math.floor((activeChain.xp or 0) + 0.5)) .. " XP for a ~"
                    .. tostring(math.floor((activeChain.minutes or 0) + 0.5)) .. " min trip."
                return false, "in-log-low-value:" .. sentence
            end
            return true, "Finish the quest already in your log."
        end
        if ns.readyToTurnIn[id] == true then return true, "Turn in this ready quest." end
    end
    -- Difficulty informs the player's choice; solo status must not hide work.
    -- Keep the normal level/identity/prerequisite gates and explicit skips.
    local value = quest.level or 0
    if value == 0 then return true end
    if value > level + 3 then return false, "Above the lowest player's level range." end
    if ns.IsClassQuest(id) then return true, "Class progression." end
    if value >= preferredFloor(level) then return true end
    local activeGuide = query and query.guide or ns.routeSelection
    local efficientGuide = not activeGuide or (activeGuide.mode == "zone" or activeGuide.mode == "bundle")
        and not activeGuide.catchup
    if not efficientGuide then
        local reason = legacyUsefulQuestReason(id, key, level, query)
        if not reason then
            for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
                if person.synced then reason = legacyUsefulQuestReason(id, person.key, level, query) end
                if reason then break end
            end
        end
        if reason then return true, reason end
        return false, "Below preferred quest levels " .. preferredFloor(level) .. "–" .. (level + 3) .. "; no worthwhile follow-up is known."
    end
    local chain = ns.ChainValue(id, query)
    if chain then
        if zoneFinishing and not chain.committed then
            return false, chain.reason
        end
        if ns.GuideEfficiencyMode(ns.routeSelection) == "complete" then
            return true, chain.reason
        end
        if chain.included then return true, chain.reason end
        return false, chain.reason
    end
    if ns.Option("xpModel") and ns.XPLevelingValue then return ns.XPLevelingValue(id, query) end
    local reason = ns.UsefulQuestReason(id, key, level, query)
    if not reason then
        for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
            if person.synced then reason = ns.UsefulQuestReason(id, person.key, level, query) end
            if reason then break end
        end
    end
    if reason then return true, reason end
    return false, "Below preferred quest levels " .. preferredFloor(level) .. "–" .. (level + 3) .. "; no worthwhile follow-up is known."
end

function ns.PrepareGuidePolicy(guide, query)
    if not query then return end
    query.guide = guide or query.guide
    local level = ns.profile and ns.profile.level
    local state = query.policyXPState
    local revisions = table.concat({tostring(guide and guide.key), tostring(guide and guide.mode),
        tostring(guide and guide.rangeHigh), tostring(level), tostring(ns.guideProgressRevision or 0),
        tostring(ns.questHistoryCount or 0), tostring(ns.objectiveDisplayRevision or 0),
        tostring(ns.xpSampleRevision or 0)}, ":")
    if query.policyXPRevision ~= revisions or not state then
        state = ns.XPState and ns.XPState() or nil
        query.policyXPRevision, query.policyXPState = revisions, state
    end
    local preparedKey = table.concat({revisions, tostring(state and state.level), tostring(state and state.xp),
        tostring(state and state.xpMax), tostring(guide and ns.GuideEfficiencyMode(guide))}, ":")
    if query.policyPreparedFor == guide and query.policyPreparedKey == preparedKey then return query.zoneFinishing end
    query.policyPreparedFor, query.policyPreparedKey = guide, preparedKey
    query.zoneProjection = ns.Option("xpModel") and guide and guide.mode == "zone"
        and ns.ZoneExitProjection and ns.ZoneExitProjection(guide, ns.profile, query) or nil
    query.zoneFinishing = ns.GuideZoneFinishing(guide, ns.profile, query.zoneProjection, query)
    return query.zoneFinishing
end

function ns.LevelingValue(id, query)
    if not query then return levelingValue(id) end
    query.values = query.values or {}
    local cached = query.values[id]
    if cached then return cached[1], cached[2] end
    local value, reason = levelingValue(id, query)
    query.values[id] = {value, reason}
    return value, reason
end

-- Being in a quest log is not a reason to bypass the leveling band. Retain a
-- ready hand-in for that character without sending others to finish old work.
function ns.LevelingWorkAllowed(id, key, query)
    if not ns.ClassQuestEnabled(id) then return false end
    if ns.LevelingValue(id, query) ~= false then return true end
    local active = key == ns.self and ns.active or ns.members[key] and ns.members[key].active
    return active and active[id] ~= nil and (ns.QuestProgressReady(key, id) == true
        or key == ns.self and ns.readyToTurnIn[id] == true) or false
end

function ns.GuideDifficultyOverride(guide)
    return guide ~= nil and guide.fullGuide == true and guide.fixedRoute == true
        and (guide.mode == "zone" or guide.mode == "bundle") and guide.continueOutsideLevels == true
end

-- This is a choice for one active leveling guide, not a global pickup gate.
-- Identity, actual requirements and skips are still checked by its callers.
function ns.GuideWorkAllowed(guide, id, key, query)
    return guide and guide.mode == "dungeon" and (guide.collectionRequired and guide.collectionRequired[id] == true
        or guide.collectionGoals and guide.collectionGoals[id] == true)
        or ns.LevelingWorkAllowed(id, key, query)
        or ns.GuideDifficultyOverride(guide) and ns.ClassQuestEnabled(id)
end

function ns.QuestLogReview()
    local result = {}
    for id in pairs(ns.active or {}) do
        local useful, reason = ns.LevelingValue(id)
        if ns.IsRepeatableQuest(id) then reason = "Repeatable; outside the leveling plan."; useful = false end
        if useful == false and not ns.readyToTurnIn[id] and not ns.IsProfessionQuest(id) and not ns.IsClassQuest(id) then
            result[#result + 1] = {id = id, title = ns.QuestTitle(id), reason = reason}
        end
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end
