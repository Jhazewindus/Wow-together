local addonName, ns = ...

-- A personal preparation guide. Dungeon quests need only their pickup;
-- unfinished prerequisites need their full accept/work/return sequence.
local costs, costCount, costContext, lastPlan, lastReturns = {}, 0, nil, nil, nil

local function complete(id) return ns.Completed(id) == true and not ns.active[id] end
local function pointKey(p)
    return string.format("%d:%.5f:%.5f", p.mapID, p.x, p.y)
end

local function travelCost(a, b, cooperative)
    if not a then return 0 end
    local context = table.concat({ns.profile.faction or "", ns.self or "", ns.travelRevision or 0,
        ns.TravelWalkSpeed(), ns.profile.level or 0, tostring(ns.Option("suggestFlights")), tostring(ns.travelData), tostring(ns.catalogue)}, ":")
    if context ~= costContext or costCount > 4096 then costs, costCount, costContext = {}, 0, context end
    local key = pointKey(a) .. ">" .. pointKey(b)
    local cached = costs[key]
    if cached then return cached end
    local distance = ns.TravelPointDistance(a, b)
    local estimate = distance and distance * 1.25 / ns.TravelWalkSpeed()
        or (a.mapID == b.mapID and ns.NormalizedDistance(a, b) * 10000 or 100000)
    -- Expensive graph comparisons belong to the scheduled initial plan. Event
    -- refreshes reuse these directed costs or a cheap distance estimate.
    if cooperative then
        local path = ns.FindTravelPath(a, b, ns.Option("suggestFlights"))
        if path then estimate = path.seconds end
        costs[key], costCount = estimate, costCount + 1
        if costCount % 8 == 0 then coroutine.yield() end
    end
    return estimate
end

local function eligibleIdentity(id)
    local q = ns.CatalogueQuest(id)
    return q and ns.DungeonQuestRelevant(id) == true
        and (ns.active[id] or (q.minLevel or q.level or 255) <= (ns.profile.level or 0)
            or ns.PickupOfferEvidence(ns.self, id) == true and ns.CatalogueAllowed(id, ns.profile, ns.self) == true)
        and not ns.GuideQuestSkipped(id)
        and not ns.CatalogueAlternativeTaken(id, ns.self)
end

local function eligiblePrerequisiteIdentity(id)
    local q = ns.CatalogueQuest(id)
    return q and ns.CatalogueIdentityAllowed(id, ns.profile) == true
        and (ns.active[id] or (q.minLevel or q.level or 255) <= (ns.profile.level or 0)
            or ns.PickupOfferEvidence(ns.self, id) == true and ns.CatalogueAllowed(id, ns.profile, ns.self) == true)
        and not ns.CatalogueAlternativeTaken(id, ns.self)
end

local function itemStartDungeon(id)
    local quest = ns.CatalogueQuest(id)
    for _, reference in ipairs(quest and quest.startRefs or {}) do
        if reference.entityType == "item" and ns.GuideInteger(reference.entityID) then
            local item = ns.questEntities and ns.questEntities.item
                and ns.questEntities.item[reference.entityID]
            local matchedGroup, matchedSource, ambiguousSource = nil, nil, false
            for _, source in ipairs(item and item.sources or {}) do
                local sources = ns.questEntities and ns.questEntities[source.entityType]
                local entity = sources and sources[source.entityID]
                if source.action == "loot" or source.action == "gather" then
                    local sourceAreas = entity and entity.sourceAreaIDs or {}
                    if #sourceAreas == 0 then
                        ambiguousSource = true
                    else
                        for _, areaID in ipairs(sourceAreas) do
                            local areaGroup
                            for _, group in ipairs(ns.DungeonGroups()) do
                                for _, dungeonAreaID in ipairs(group.definition and group.definition.areaIDs or {}) do
                                    if areaID == dungeonAreaID then areaGroup = group; break end
                                end
                                if areaGroup then break end
                            end
                            if not areaGroup then
                                ambiguousSource = true
                            elseif matchedGroup and matchedGroup.key ~= areaGroup.key then
                                ambiguousSource = true
                            else
                                matchedGroup, matchedSource = areaGroup, source
                            end
                        end
                    end
                else
                    ambiguousSource = true
                end
            end
            if matchedGroup and not ambiguousSource then
                return matchedGroup, {item = ns.SafeTitle(item.name or reference.name) or "the quest item",
                    source = ns.SafeTitle(matchedSource.name or "the creature") or "the creature"}
            end
        end
    end
end

function ns.DungeonGuide(group, pickupQuestID)
    local records, goals, required, dependencies, deferred, seen = {}, {}, {}, {}, {}, {}
    local dungeonName = string.lower(group.name or "")
    local locationSlug
    for _, entrance in ipairs(group.definition and group.definition.entrances or {}) do
        local zone = entrance.container and string.match(entrance.container, "^[^.]+%.(.+)$")
        if zone then locationSlug = string.lower(string.gsub(zone, "_", "-")); break end
    end
    local function inDungeonScope(quest)
        if quest.zone and string.lower(quest.zone) == dungeonName then return true end
        if quest.categoryPath == "dungeons/" .. group.key then return true end
        local hint = group.definition and group.definition.locationHint
        if quest.questType == "Dungeon" and hint and quest.categoryPath then
            local slug = string.lower(hint):gsub("[^%w]+", "-"):gsub("^-", ""):gsub("-$", "")
            if string.find(quest.categoryPath, slug, 1, true) then return true end
        end
        if quest.questType == "Dungeon" and locationSlug and quest.categoryPath
            and string.find(quest.categoryPath, locationSlug, 1, true) then return true end
        return false
    end
    local function hasMappedStart(quest)
        for _, point in ipairs(quest.starts or {}) do if ns.ValidTravelPoint(point) then return true end end
        return false
    end
    local function visit(id, depth)
        if seen[id] or depth > 24 or #records >= 512 then return end
        seen[id] = true
        local q = ns.CatalogueQuest(id)
        if not q then return end
        if q.prerequisitesUnverified then deferred[id] = true end
        records[#records + 1] = ns.CatalogueRecord(id)
        -- Explicit group membership (Wowhead category or supplemental Method
        -- table) is authoritative evidence that the quest's work belongs to
        -- this instance, even when its catalogue zone predates that mapping.
        local inside = inDungeonScope(q) or goals[id] == true
        if inside and not hasMappedStart(q) then deferred[id] = true end
        dependencies[id] = {}
        -- An accepted quest needs no earlier pickup chain. A confirmed beta
        -- offer may also override explicitly marked older-world prerequisites,
        -- but only when the shared eligibility policy permits that override.
        if ns.active[id] or ns.PickupOfferEvidence(ns.self, id) == true
            and ns.CatalogueAllowed(id, ns.profile, ns.self) == true then return end
        local parents, added = {}, {}
        local function add(previous)
            if ns.GuideInteger(previous) and previous > 0 and previous ~= id and not added[previous] and not complete(previous) then
                parents[#parents + 1], added[previous] = previous, true
            end
        end
        add(q.previousQuest)
        for _, previous in ipairs(q.prerequisiteAll or {}) do add(previous) end
        for _, previous in ipairs(ns.LearnedPrerequisiteIDs and ns.LearnedPrerequisiteIDs(id) or {}) do add(previous) end
        local anyMet, best, score = false, nil, nil
        for _, previous in ipairs(q.prerequisiteAny or {}) do
            if complete(previous) then anyMet = true; break end
            if eligiblePrerequisiteIdentity(previous) then
                local candidate = ns.CatalogueQuest(previous)
                local point = ns.NPCPickupPoint(previous) or candidate.starts and candidate.starts[1]
                local value = ns.active[previous] and -1 or point and ns.ValidTravelPoint(point)
                    and travelCost(ns.PlayerPoint(ns.profile.mapID), point, false) or 200000
                if not score or value < score or value == score and previous < best then best, score = previous, value end
            end
        end
        if not anyMet and best then add(best) end
        for _, previous in ipairs(parents) do
            required[previous], dependencies[id][#dependencies[id] + 1] = true, previous
            if deferred[id] then deferred[previous] = true end
            visit(previous, depth + 1)
            if inDungeonScope(ns.CatalogueQuest(previous) or {}) then deferred[id] = true end
        end
    end
    for _, id in ipairs(group.ids) do
        if (not pickupQuestID or id == pickupQuestID) and eligibleIdentity(id) and not complete(id) then
            goals[id] = true; visit(id, 0)
        end
    end
    if #records == 0 then return end
    local entrance = not pickupQuestID and ns.DungeonEntrance(group) or nil
    local guide = {key = "dungeon:" .. group.key .. (pickupQuestID and (":quest:" .. pickupQuestID) or ""),
        dungeonKey = group.key, dungeon = group, pickupQuestID = pickupQuestID, mode = "dungeon", personal = true,
        title = pickupQuestID and ("Get " .. ns.QuestTitle(pickupQuestID)) or ("Get " .. group.name .. " quests"),
        kind = "Dungeon preparation", records = records, target = records[1], collectionGoals = goals,
        collectionRequired = required, collectionDependencies = dependencies, collectionDeferred = deferred,
        collectionInDungeon = {}, focusKey = ns.self,
        mapID = ns.profile.mapID, level = group.level, zone = group.name, profilesReady = true, entrance = entrance,
        reason = "Collect the quests and finish required prerequisites before entering.",
        destination = pickupQuestID and "Go to the quest giver." or "Collect quests, then go to the dungeon entrance.",
        pendingReason = "Waiting for a quest offer, prerequisite or pickup location."}
    for _, record in ipairs(records) do
        guide.collectionInDungeon[record.id] = goals[record.id] == true
            or inDungeonScope(ns.CatalogueQuest(record.id) or {})
        local stages = ns.RouteStages(record, ns.self)
        if #stages > 0 then guide.hasPoint = true end
    end
    if entrance then guide.hasPoint = true
    elseif not pickupQuestID then guide.reason = guide.reason .. " Entrance not located yet." end
    return guide
end

local function taskKey(stop) return stop.id .. ":" .. ns.GuideStepKey(stop) end

local function prerequisiteDungeon(id, guide)
    if not guide.collectionRequired[id] or guide.collectionGoals[id] then return end
    local itemGroup, itemSource = itemStartDungeon(id)
    if itemGroup then return itemGroup, itemSource end
    local quest = ns.CatalogueQuest(id)
    local key = quest and quest.categoryPath and string.match(quest.categoryPath, "^dungeons/([%w%-]+)$")
    if not key or key == guide.dungeonKey then return end
    for _, group in ipairs(ns.DungeonGroups()) do if group.key == key then return group end end
end

function ns.DungeonRunProgress(guide)
    local progress = {total = 0, collected = 0, ready = 0, finished = 0, skipped = 0}
    for id in pairs(guide.collectionGoals or {}) do
        progress.total = progress.total + 1
        if complete(id) then progress.finished = progress.finished + 1; progress.collected = progress.collected + 1
        elseif ns.GuideQuestSkipped(id) then progress.skipped = progress.skipped + 1; progress.collected = progress.collected + 1
        elseif ns.active[id] then
            progress.collected = progress.collected + 1
            if ns.readyToTurnIn[id] or ns.QuestProgressReady(ns.self, id) then progress.ready = progress.ready + 1 end
        end
    end
    return progress
end

function ns.AdvanceDungeonGuide(guide)
    if guide.pickupQuestID or not guide.collectionGoals then return end
    guide.collectionDeferred = guide.collectionDeferred or {}
    local progress = ns.DungeonRunProgress(guide)
    local phase = guide.dungeonPhase or "collect"
    local inside = ns.DungeonEntryKey() == guide.dungeonKey
    local preparationComplete = true
    for id in pairs(guide.collectionGoals) do
        if not guide.collectionDeferred[id] and not complete(id) and not ns.GuideQuestSkipped(id) and not ns.active[id] then
            preparationComplete = false; break
        end
    end
    if phase == "collect" and progress.total > 0
        and (inside or preparationComplete and progress.ready > 0
            and progress.ready + progress.finished + progress.skipped == progress.total) then
        phase = "run"
    end
    if phase == "run" and progress.ready > 0
        and (not inside or progress.ready + progress.finished + progress.skipped == progress.total) then phase = "return" end
    if phase ~= (guide.dungeonPhase or "collect") then
        guide.dungeonPhase = phase
        guide.title = guide.dungeon.name .. " quests"
        ns.routeSignature, ns.routePaused = nil, nil
        ns.ResetTravelPath()
        ns.SaveSelectedGuide()
    end
end

local function returnRoute(guide, includeOrigin, cooperative)
    local progress, tasks, pending, missing = ns.DungeonRunProgress(guide), {}, nil, 0
    if guide.dungeonPhase == "return" then
        for _, record in ipairs(guide.records) do
            local id = record.id
            if guide.collectionGoals[id] and not complete(id) and not ns.GuideQuestSkipped(id) and ns.active[id]
                and (ns.readyToTurnIn[id] or ns.QuestProgressReady(ns.self, id)) then
                local stop = ns.RouteStop(record, ns.self)
                if stop and stop.kind == "t" and #ns.FilterGuideStages({stop}) > 0 then tasks[#tasks + 1] = stop
                elseif not stop then
                    missing = missing + 1
                    pending = pending or {id = id, kind = "t", title = record.title}
                end
            end
        end
    end
    table.sort(tasks, function(a, b) return a.id < b.id end)
    local start, stops, used = ns.PlayerPoint(ns.profile.mapID), {}, {}
    if lastReturns and lastReturns.key == guide.key and not cooperative and not ns.forceRouteReplan then
        for _, key in ipairs(lastReturns.steps) do
            for index, stop in ipairs(tasks) do
                if not used[index] and taskKey(stop) == key then stops[#stops + 1], used[index] = stop, true; break end
            end
        end
    end
    while #stops < #tasks do
        local best, score
        for index, stop in ipairs(tasks) do
            if not used[index] then
                local value = travelCost(stops[#stops] or start, stop, cooperative)
                if not score or value < score then best, score = index, value end
            end
        end
        stops[#stops + 1], used[best] = tasks[best], true
    end
    local keys, otherMaps = {}, 0
    for _, stop in ipairs(stops) do keys[#keys + 1] = taskKey(stop) end
    lastReturns = {key = guide.key, steps = keys}
    local mapID = stops[1] and stops[1].mapID or ns.profile.mapID
    for _, stop in ipairs(stops) do if stop.mapID ~= mapID then otherMaps = otherMaps + 1 end end
    local remaining = progress.total - progress.finished - progress.skipped
    local reason = missing > 0 and ("Turn-in location missing for " .. pending.title .. ". Check the quest log.")
        or ("Finish " .. remaining .. " quest" .. (remaining == 1 and "" or "s") .. " in " .. guide.dungeon.name
            .. ". " .. progress.ready .. "/" .. remaining .. " ready to turn in.")
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops,
        origin = includeOrigin and start and start.mapID == mapID and start or nil, focusKey = ns.self,
        missing = missing, remote = 0, limited = 0, otherMaps = otherMaps, partial = missing > 0,
        pendingStop = pending, pendingReason = reason, dungeonPhase = guide.dungeonPhase, dungeonProgress = progress}
end

function ns.BuildDungeonRoute(guide, includeOrigin, cooperative)
    ns.AdvanceDungeonGuide(guide)
    if guide.dungeonPhase == "run" or guide.dungeonPhase == "return" then return returnRoute(guide, includeOrigin, cooperative) end
    if not guide.collectionGoals then
        local fresh = guide.dungeon and ns.DungeonGuide(guide.dungeon, guide.pickupQuestID)
        if fresh then guide = fresh
        else
            local copy = {}; for key, value in pairs(guide) do copy[key] = value end
            copy.collectionGoals, copy.collectionRequired, copy.collectionDependencies, copy.collectionDeferred,
                copy.collectionInDungeon = {}, {}, {}, {}, {}
            for _, record in ipairs(copy.records) do copy.collectionGoals[record.id] = true end
            guide = copy
        end
    end
    guide.collectionDeferred, guide.collectionInDungeon = guide.collectionDeferred or {}, guide.collectionInDungeon or {}
    local tasks, later, terminal, byID, missing, pendingReason, deferredNote = {}, {}, {}, {}, 0, nil, nil
    local entranceBlocked, blockReason = false, nil
    local visiting = {}
    local function hasUnverifiedParent(id, seenParents)
        seenParents = seenParents or {}
        if seenParents[id] then return false end
        seenParents[id] = true
        for _, parentID in ipairs(guide.collectionDependencies[id] or {}) do
            local parent = ns.CatalogueQuest(parentID)
            if parent and parent.prerequisitesUnverified then return true end
            if hasUnverifiedParent(parentID, seenParents) then return true end
        end
        return false
    end
    local function append(id)
        if complete(id) then return true end
        if visiting[id] then return false end
        if byID[id] ~= nil then return byID[id] end
        if guide.collectionDeferred[id] == "dependent" then
            byID[id] = true
            return true
        end
        if guide.collectionDeferred[id] == true then
            visiting[id] = true
            for _, previous in ipairs(guide.collectionDependencies[id] or {}) do append(previous) end
            visiting[id] = nil
            byID[id] = true
            local record, quest = ns.CatalogueRecord(id), ns.CatalogueQuest(id)
            local reason = ns.QuestStartGapReason(id)
            if quest and quest.prerequisitesUnverified then
                local giver = ns.QuestGiverName(id)
                reason = giver and ("Ask " .. giver .. " which quest unlocks " .. ns.QuestTitle(id) .. ". Keep it under Later until then.")
                    or ("Ask the quest giver which quest unlocks " .. ns.QuestTitle(id) .. ". Keep it under Later until then.")
            end
            if record and not (not (quest and quest.prerequisitesUnverified) and hasUnverifiedParent(id)) then
                later[#later + 1] = {id = id, title = record.title, reason = reason
                    or ("A prerequisite for " .. record.title .. " is not mapped yet.")}
            end
            if reason and (not deferredNote or string.find(reason, " from ", 1, true)
                and not string.find(deferredNote, " from ", 1, true)) then deferredNote = reason end
            return true
        end
        visiting[id] = true
        local dependencies, parentsReady = {}, true
        local deferredParent = false
        for _, previous in ipairs(guide.collectionDependencies[id] or {}) do
            if not append(previous) then
                parentsReady = false
                if guide.pickupQuestID and not guide.collectionInDungeon[previous] then entranceBlocked = true end
            end
            if guide.collectionDeferred[previous] then deferredParent = true end
            if terminal[previous] then dependencies[#dependencies + 1] = terminal[previous] end
        end
        if deferredParent then
            guide.collectionDeferred[id], visiting[id], byID[id] = "dependent", nil, true
            return true
        end
        local record = ns.CatalogueRecord(id)
        local quest = ns.CatalogueQuest(id)
        local dungeonWork = guide.collectionDeferred[id] == true or guide.collectionInDungeon[id] == true
        local inDungeonGoal = guide.collectionGoals[id] == true and guide.collectionInDungeon[id] == true
        if not parentsReady and not dungeonWork then
            if guide.pickupQuestID then
                entranceBlocked = true
                blockReason = blockReason or ("Finish the mapped prerequisite chain for " .. ns.QuestTitle(id) .. " before entering.")
            end
        end
        local identityReady = guide.collectionRequired[id] and not guide.collectionGoals[id]
            and eligiblePrerequisiteIdentity(id) or eligibleIdentity(id)
        if not identityReady and not dungeonWork then
            if guide.pickupQuestID then entranceBlocked = true end
            local _, eligibilityReason = ns.CatalogueAllowed(id, ns.profile, ns.self)
            if guide.pickupQuestID then
                blockReason = blockReason or eligibilityReason
                    or ("Quest eligibility for " .. ns.QuestTitle(id) .. " needs checking before entering.")
            end
        end
        local routedPrerequisite = guide.collectionRequired[id] and not guide.collectionGoals[id]
        if not guide.collectionDeferred[id] and not routedPrerequisite and not ns.active[id]
            and ns.PickupOfferEvidence(ns.self, id) == false then
            if guide.pickupQuestID then entranceBlocked = true end
            local _, reason = ns.CatalogueAllowed(id, ns.profile, ns.self)
            if guide.pickupQuestID then
                blockReason = blockReason or reason or ("The quest offer for " .. ns.QuestTitle(id) .. " is not available yet.")
            end
        end
        local goalOnly = guide.collectionGoals[id] and not guide.collectionRequired[id]
        local stages = record and identityReady and ns.RouteStages(record, ns.self) or {}
        local mapped, valid, checklistOnly = nil, nil, false
        if goalOnly and ns.active[id] then stages = {} end
        local prerequisiteGroup, itemSource = prerequisiteDungeon(id, guide)
        local previousDungeon
        if guide.collectionRequired[id] and not guide.collectionGoals[id] then
            for _, parentID in ipairs(guide.collectionDependencies[id] or {}) do
                local parent = ns.CatalogueQuest(parentID)
                local key = parent and parent.categoryPath and string.match(parent.categoryPath, "^dungeons/([%w%-]+)$")
                if key and key ~= guide.dungeonKey then
                    for _, group in ipairs(ns.DungeonGroups()) do
                        if group.key == key then previousDungeon = group; break end
                    end
                end
                if previousDungeon then break end
            end
        end
        if itemSource and prerequisiteGroup and #stages == 0 then
            local point = ns.DungeonEntrance(prerequisiteGroup)
            if point then
                stages[1] = {id = id, mapID = point.mapID, x = point.x, y = point.y, kind = "q",
                    action = "travel", dungeonEntrance = true, dungeonKey = prerequisiteGroup.key,
                    published = point.published, planned = true,
                    label = "Enter " .. prerequisiteGroup.name .. "; loot " .. itemSource.item .. " from " .. itemSource.source,
                    title = prerequisiteGroup.name}
            end
        end
        -- Keep known objective areas and route to the known turn-in for
        -- prerequisite quests even when some objective locations are absent.
        -- The in-game quest log remains authoritative and holds the player
        -- until every objective is complete.
        local hasObjectiveStage = false
        for _, stop in ipairs(stages) do if stop.kind == "q" then hasObjectiveStage = true; break end end
        if guide.collectionRequired[id] and not guide.collectionGoals[id]
            and quest and (quest.objectiveLocationsIncomplete or not hasObjectiveStage) and #stages > 0
            and stages[#stages].kind ~= "t" then
            local finish = quest.ends and quest.ends[1]
            if ns.ValidTravelPoint(finish) then
                local turnIn = ns.PublishedGuideStop(record, finish, "t")
                turnIn.label = "After completing this quest, return to " .. (finish.name or record.title)
                turnIn.planned = true
                stages[#stages + 1] = turnIn
            end
        end
        -- Preview a known chain's later pickup only after its required mapped
        -- returns. Actual offers are checked again when progress promotes it.
        if #stages == 0 and not ns.active[id] and parentsReady
            and (guide.collectionRequired[id] or #dependencies > 0)
            and identityReady and (ns.CataloguePrerequisitesAllowed(id, ns.self) == false
                or quest and quest.prerequisitesUnverified) then
            local q = ns.CatalogueQuest(id)
            local pickup = ns.NPCPickupPoint(id) or q.starts and q.starts[1]
            if ns.ValidTravelPoint(pickup) then
                stages[1] = ns.PublishedGuideStop(record, pickup, "a"); stages[1].planned = true
                if quest.prerequisitesUnverified then
                    stages[1].label = "Check with " .. (pickup.name or record.title) .. " whether " .. record.title .. " is offered"
                end
                if not goalOnly then
                    for _, point in ipairs(q.objectives or {}) do
                        if ns.ValidTravelPoint(point) then stages[#stages + 1] = ns.PublishedGuideStop(record, point, "q") end
                    end
                    local finish = q.ends and q.ends[1]
                    if ns.ValidTravelPoint(finish) then stages[#stages + 1] = ns.PublishedGuideStop(record, finish, "t") end
                end
                stages = ns.FilterGuideStages(stages)
            end
        end
        -- A quest can begin inside a dungeon while its source NPC has no
        -- captured coordinates. When its prerequisite is itself a dungeon
        -- quest, use that known entrance as an honest checklist anchor and
        -- retain any mapped outdoor return step.
        if #stages == 0 and previousDungeon and not ns.active[id] then
            local point = ns.DungeonEntrance(previousDungeon)
            if point then
                stages[1] = {id = id, mapID = point.mapID, x = point.x, y = point.y, kind = "q",
                    action = "travel", dungeonEntrance = true, dungeonKey = previousDungeon.key,
                    published = point.published, planned = true,
                    label = "Inside " .. previousDungeon.name .. ", follow the quest tracker for " .. record.title,
                    title = previousDungeon.name}
                local finish = quest and quest.ends and quest.ends[1]
                if ns.ValidTravelPoint(finish) then
                    local turnIn = ns.PublishedGuideStop(record, finish, "t")
                    turnIn.label = "After completing this quest, return to " .. (finish.name or record.title)
                    turnIn.planned = true
                    stages[#stages + 1] = turnIn
                end
                checklistOnly = true
                missing = missing + 1
                pendingReason = pendingReason or ("No interior map pin is available for " .. record.title
                    .. " in " .. previousDungeon.name .. "; follow its quest tracker inside.")
            end
        end
        if prerequisiteGroup and not complete(id) then
            local prerequisiteEntrance = ns.DungeonEntrance(prerequisiteGroup)
            local alreadyInside = ns.DungeonEntryKey() == prerequisiteGroup.key
            local dungeonScoped = quest and quest.categoryPath == "dungeons/" .. prerequisiteGroup.key
            if #stages == 0 and dungeonScoped and prerequisiteEntrance then
                stages[1] = {id = id, mapID = prerequisiteEntrance.mapID,
                    x = prerequisiteEntrance.x, y = prerequisiteEntrance.y, kind = "q", action = "travel",
                    dungeonEntrance = true, dungeonKey = prerequisiteGroup.key,
                    published = prerequisiteEntrance.published, planned = true,
                    label = "Enter " .. prerequisiteGroup.name .. ", then follow the quest tracker for " .. record.title,
                    title = prerequisiteGroup.name}
            end
            if prerequisiteEntrance and (#stages > 0 or ns.active[id]) then
                local planned, insertedEntrance = {}, false
                local function addEntrance()
                    if insertedEntrance or alreadyInside then return end
                    planned[#planned + 1] = {id = id, mapID = prerequisiteEntrance.mapID,
                        x = prerequisiteEntrance.x, y = prerequisiteEntrance.y, kind = "q", action = "travel",
                        dungeonEntrance = true, dungeonKey = prerequisiteGroup.key,
                        published = prerequisiteEntrance.published, planned = true,
                        label = "Enter " .. prerequisiteGroup.name .. " for " .. record.title,
                        title = prerequisiteGroup.name}
                    insertedEntrance = true
                end
                for _, stop in ipairs(stages) do
                    if stop.dungeonEntrance and stop.dungeonKey == prerequisiteGroup.key then insertedEntrance = true end
                    if stop.kind ~= "a" then addEntrance() end
                    planned[#planned + 1] = stop
                end
                addEntrance()
                stages = planned
                local finish = quest and quest.ends and quest.ends[1]
                local hasReturn = stages[#stages] and stages[#stages].kind == "t"
                if not hasReturn and ns.ValidTravelPoint(finish) then
                    local turnIn = ns.PublishedGuideStop(record, finish, "t")
                    turnIn.label = "Return to " .. (finish.name or record.title)
                    stages[#stages + 1] = turnIn
                    hasReturn = true
                end
                local inDungeonChecklist = not hasReturn and dungeonScoped
                if inDungeonChecklist then
                    checklistOnly = true
                    for _, stop in ipairs(stages) do
                        if stop.dungeonEntrance and stop.dungeonKey == prerequisiteGroup.key then
                            stop.label = "Enter " .. prerequisiteGroup.name .. ", then follow the quest tracker for " .. record.title
                        end
                    end
                    missing = missing + 1
                    pendingReason = pendingReason or ("No interior map pin is available for " .. record.title
                        .. " in " .. prerequisiteGroup.name .. "; follow its quest tracker inside.")
                end
                mapped = parentsReady and #stages > 0
                valid = mapped and (hasReturn or inDungeonChecklist)
                if not hasReturn and not inDungeonChecklist then
                    if guide.pickupQuestID then entranceBlocked = true end
                    if guide.pickupQuestID then
                        blockReason = blockReason or ("Complete " .. record.title .. " in " .. prerequisiteGroup.name
                            .. " and check the quest log; its return location is not mapped yet.")
                    end
                end
            else
                if guide.pickupQuestID then entranceBlocked = true end
                if guide.pickupQuestID then
                    blockReason = blockReason or ("The prerequisite run in " .. prerequisiteGroup.name
                        .. " is not mapped yet. Check the quest log for " .. record.title .. ".")
                end
                mapped, valid = false, false
            end
        end
        local collected = goalOnly and ns.active[id] ~= nil
        if not prerequisiteGroup then
            mapped = parentsReady and (#stages > 0 or collected)
            valid = mapped
        end
        if goalOnly and not collected then
            if stages[1] and stages[1].kind == "a" then stages = {stages[1]}
            else
                stages = {}; valid, mapped = false, false
            end
        elseif not goalOnly and not checklistOnly and (#stages == 0 or stages[#stages].kind ~= "t") then
            if #stages > 0 and not dungeonWork and not inDungeonGoal then
                if guide.pickupQuestID then entranceBlocked = true end
                if guide.pickupQuestID then
                    blockReason = blockReason or ("The return step for " .. record.title .. " is not ready before entering.")
                end
            end
            valid = false
        end
        if mapped then
            local laterReason
            for _, stop in ipairs(stages) do
                local decision = ns.GuideDestinationDecision(stop, guide)
                if not decision.specificBenefit or decision.needsReview then laterReason = decision.why; break end
            end
            if laterReason then
                local _, eligibilityReason = ns.CatalogueAllowed(id, ns.profile, ns.self)
                local reason = eligibilityReason or laterReason
                later[#later + 1] = {id = id, title = record.title, reason = reason}
                pendingReason = pendingReason or (record.title .. " stays under Later: " .. reason)
                if guide.collectionRequired[id] and not guide.collectionGoals[id] then
                    if guide.pickupQuestID then
                        entranceBlocked = true
                        blockReason = blockReason or pendingReason
                    end
                end
                mapped, valid = false, false
            else
                for _, stop in ipairs(stages) do
                    local task = {stop = stop, parents = dependencies, key = taskKey(stop)}
                    tasks[#tasks + 1] = task; dependencies = {#tasks}
                end
                if valid then terminal[id] = dependencies[1] end
            end
        else
            local reason
            if quest and quest.prerequisitesUnverified then
                local giver = ns.QuestGiverName(id)
                reason = giver and ("Ask " .. giver .. " which quest unlocks " .. record.title .. ". Keep it under Later until then.")
                    or ("Ask the quest giver which quest unlocks " .. record.title .. ". Keep it under Later until then.")
            else
                reason = ns.QuestStartGapReason(id)
                    or ("A pickup or route step for " .. record.title .. " is not mapped yet.")
            end
            if not (quest and not quest.prerequisitesUnverified and hasUnverifiedParent(id)) then
                later[#later + 1] = {id = id, title = record.title, reason = reason}
            end
            if not pendingReason or string.find(reason, " from ", 1, true) and not string.find(pendingReason, " from ", 1, true) then
                pendingReason = reason
            end
        end
        visiting[id], byID[id] = nil, valid
        return valid
    end
    local goalIDs = {}; for id in pairs(guide.collectionGoals or {}) do goalIDs[#goalIDs + 1] = id end; table.sort(goalIDs)
    local unreadyGoals = 0
    for _, id in ipairs(goalIDs) do
        if not append(id) then missing, unreadyGoals = missing + 1, unreadyGoals + 1 end
    end
    if #goalIDs > 0 and (guide.pickupQuestID or unreadyGoals == #goalIDs) then
        entranceBlocked = true
        blockReason = blockReason or pendingReason
    end
    local start = ns.PlayerPoint(ns.profile.mapID)
    local entrance = guide.entrance
    local order, used = {}, {}
    -- Preserve an existing preparation itinerary when progress merely removes
    -- finished steps. A new selection/Scan explicitly permits a fresh plan.
    local reusable = lastPlan and lastPlan.key == guide.key and not cooperative and not ns.forceRouteReplan
    if reusable then
        local indices = {}; for i, task in ipairs(tasks) do indices[task.key] = i end
        for _, key in ipairs(lastPlan.steps) do
            local i = indices[key]
            if i then
                local ready = true; for _, parent in ipairs(tasks[i].parents) do if not used[parent] then ready = false end end
                if ready then order[#order + 1], used[i] = i, true end
            end
        end
    end
    local function cost(a, b) return travelCost(a, b, cooperative) end
    while #order < #tasks do
        local last = #order > 0 and tasks[order[#order]].stop or start
        local best, score
        for index, task in ipairs(tasks) do
            if not used[index] then
                local ready = true; for _, parent in ipairs(task.parents) do if not used[parent] then ready = false; break end end
                if ready then
                    local value = cost(last, task.stop)
                    if not score or value < score or value == score and task.key < tasks[best].key then best, score = index, value end
                end
            end
        end
        if not best then break end
        order[#order + 1], used[best] = best, true
    end
    -- Improve the greedy itinerary by relocating visits without crossing a
    -- prerequisite. Bound work; never claim a global/terrain-perfect optimum.
    if cooperative and #order <= 40 then
        for pass = 1, 2 do
            local changed = false
            for from = 1, #order do
                local item, positions = order[from], {}
                for i, index in ipairs(order) do positions[index] = i end
                local low, high = 1, #order
                for _, parent in ipairs(tasks[item].parents) do low = math.max(low, positions[parent] + 1) end
                for i, task in ipairs(tasks) do
                    for _, parent in ipairs(task.parents) do if parent == item then high = math.min(high, positions[i] - 1) end end
                end
                local before = from > 1 and tasks[order[from - 1]].stop or start
                local after = from < #order and tasks[order[from + 1]].stop or entrance
                local removal = (before and cost(before, tasks[item].stop) or 0) + (after and cost(tasks[item].stop, after) or 0)
                    - (before and after and cost(before, after) or 0)
                local best, saving = nil, 0
                for target = low, high do
                    if target ~= from then
                        local leftIndex = target < from and target - 1 or target
                        local rightIndex = target < from and target or target + 1
                        local left = leftIndex > 0 and tasks[order[leftIndex]].stop or start
                        local right = rightIndex <= #order and tasks[order[rightIndex]].stop or entrance
                        local addition = (left and cost(left, tasks[item].stop) or 0) + (right and cost(tasks[item].stop, right) or 0)
                            - (left and right and cost(left, right) or 0)
                        if removal - addition > saving + .01 then best, saving = target, removal - addition end
                    end
                end
                if best then table.remove(order, from); table.insert(order, best, item); changed = true end
                coroutine.yield()
            end
            if not changed then break end
        end
    end
    local stops, keys, otherMaps = {}, {}, 0
    for _, index in ipairs(order) do stops[#stops + 1], keys[#keys + 1] = tasks[index].stop, tasks[index].key end
    lastPlan = {key = guide.key, steps = keys}
    if entrance and #tasks == #order and not entranceBlocked then
        stops[#stops + 1] = {id = guide.target.id, mapID = entrance.mapID, x = entrance.x, y = entrance.y, kind = "q",
            action = "travel", dungeonEntrance = true, published = entrance.published,
            dungeonKey = guide.dungeonKey,
            label = "Go to " .. (guide.dungeon and guide.dungeon.name or guide.title) .. " entrance",
            title = guide.dungeon and guide.dungeon.name or guide.title, planned = #stops > 0}
    end
    local mapID = stops[1] and stops[1].mapID or ns.profile.mapID
    for _, stop in ipairs(stops) do if stop.mapID ~= mapID then otherMaps = otherMaps + 1 end end
    if missing > 0 and stops[#stops] and stops[#stops].dungeonEntrance then
        local remaining = "Some quest pickups or returns are still unmapped. The confirmed route still leads to the entrance; check the dungeon journal for the rest."
        pendingReason = pendingReason and (pendingReason .. " " .. remaining) or remaining
    end
    pendingReason = blockReason or pendingReason
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops,
        origin = includeOrigin and start and start.mapID == mapID and start or nil, focusKey = ns.self,
        missing = missing, remote = 0, limited = #tasks - #order, otherMaps = otherMaps,
        later = later,
        partial = missing > 0 or #tasks ~= #order or not guide.pickupQuestID and not entrance,
        entranceBlocked = entranceBlocked,
        pendingReason = pendingReason or deferredNote and (deferredNote .. " This is picked up during the dungeon run.")}
end

function ns.DungeonPreparationArrived(guide)
    if guide.pickupQuestID or not guide.dungeon or not guide.collectionGoals then return false end
    for id in pairs(guide.collectionGoals) do
        if not ns.active[id] and ns.Completed(id) ~= true then return false end
    end
    return ns.DungeonEntryKey and ns.DungeonEntryKey() == guide.dungeon.key or false
end

function ns.ShowDungeonQuests(group, startDirectly, pickupQuestID)
    ns.ReadProfile()
    ns.ReadQuests()
    local guide = ns.DungeonGuide(group, pickupQuestID)
    if not guide then ns.guideAction = "No unfinished quests match your level and character."; ns.Refresh(); return end
    ns.dungeonHistoryScope = {}
    for _, record in ipairs(guide.records) do ns.dungeonHistoryScope[record.id] = true end
    ns.ScheduleSync()
    if not guide.hasPoint and not startDirectly then ns.ShowDungeonQuestList(group); return end
    if ns.dungeonWindow then ns.dungeonWindow:Hide() end
    if ns.dungeonViewer then ns.dungeonViewer:Hide() end
    if guide.hasPoint then ns.RequestStartRoute(guide)
    else ns.ActivateRoute(guide); ns.Refresh() end
end
