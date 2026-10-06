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

function ns.DungeonGuide(group, pickupQuestID)
    local records, goals, required, dependencies, seen = {}, {}, {}, {}, {}
    local function visit(id, depth)
        if seen[id] or depth > 24 or #records >= 512 then return end
        seen[id] = true
        local q = ns.CatalogueQuest(id)
        if not q then return end
        records[#records + 1] = ns.CatalogueRecord(id)
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
            if eligibleIdentity(previous) then
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
            visit(previous, depth + 1)
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
        collectionRequired = required, collectionDependencies = dependencies, focusKey = ns.self,
        mapID = ns.profile.mapID, level = group.level, zone = group.name, profilesReady = true, entrance = entrance,
        reason = "Collect the quests and finish required prerequisites before entering.",
        destination = pickupQuestID and "Go to the quest giver." or "Collect quests, then go to the dungeon entrance.",
        pendingReason = "Waiting for a quest offer, prerequisite or pickup location."}
    for _, record in ipairs(records) do
        local stages = ns.RouteStages(record, ns.self)
        if #stages > 0 then guide.hasPoint = true; break end
    end
    if entrance then guide.hasPoint = true
    elseif not pickupQuestID then guide.reason = guide.reason .. " Entrance not located yet." end
    return guide
end

local function taskKey(stop) return stop.id .. ":" .. ns.GuideStepKey(stop) end

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
    local progress = ns.DungeonRunProgress(guide)
    local phase = guide.dungeonPhase or "collect"
    local inside = ns.DungeonEntryKey() == guide.dungeonKey
    if phase == "collect" and progress.total > 0 and progress.collected == progress.total
        and (inside or progress.ready > 0 and progress.ready + progress.finished + progress.skipped == progress.total) then
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
            copy.collectionGoals, copy.collectionRequired, copy.collectionDependencies = {}, {}, {}
            for _, record in ipairs(copy.records) do copy.collectionGoals[record.id] = true end
            guide = copy
        end
    end
    local tasks, terminal, byID, missing = {}, {}, {}, 0
    local visiting = {}
    local function append(id)
        if complete(id) then return true end
        if visiting[id] then return false end
        if byID[id] ~= nil then return byID[id] end
        visiting[id] = true
        local dependencies, parentsReady = {}, true
        for _, previous in ipairs(guide.collectionDependencies[id] or {}) do
            if not append(previous) then parentsReady = false end
            if terminal[previous] then dependencies[#dependencies + 1] = terminal[previous] end
        end
        local record = ns.CatalogueRecord(id)
        local goalOnly = guide.collectionGoals[id] and not guide.collectionRequired[id]
        local stages = record and eligibleIdentity(id) and ns.RouteStages(record, ns.self) or {}
        if goalOnly and ns.active[id] then stages = {} end
        -- Preview a known chain's later pickup only after its required mapped
        -- returns. Actual offers are checked again when progress promotes it.
        if #stages == 0 and not ns.active[id] and parentsReady and #dependencies > 0
            and eligibleIdentity(id) and ns.CataloguePrerequisitesAllowed(id, ns.self) == false then
            local q = ns.CatalogueQuest(id)
            local pickup = ns.NPCPickupPoint(id) or q.starts and q.starts[1]
            if ns.ValidTravelPoint(pickup) then
                stages[1] = ns.PublishedGuideStop(record, pickup, "a"); stages[1].planned = true
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
        local collected = goalOnly and ns.active[id] ~= nil
        local mapped = parentsReady and (#stages > 0 or collected)
        local valid = mapped
        if goalOnly and not collected then
            if stages[1] and stages[1].kind == "a" then stages = {stages[1]} else stages = {}; valid, mapped = false, false end
        elseif not goalOnly and (#stages == 0 or stages[#stages].kind ~= "t") then valid = false end
        if mapped then
            for _, stop in ipairs(stages) do
                local task = {stop = stop, parents = dependencies, key = taskKey(stop)}
                tasks[#tasks + 1] = task; dependencies = {#tasks}
            end
            if valid then terminal[id] = dependencies[1] end
        end
        visiting[id], byID[id] = nil, valid
        return valid
    end
    local goalIDs = {}; for id in pairs(guide.collectionGoals or {}) do goalIDs[#goalIDs + 1] = id end; table.sort(goalIDs)
    for _, id in ipairs(goalIDs) do if not append(id) then missing = missing + 1 end end
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
    if entrance and missing == 0 then
        stops[#stops + 1] = {id = guide.target.id, mapID = entrance.mapID, x = entrance.x, y = entrance.y, kind = "q",
            action = "travel", dungeonEntrance = true, published = entrance.published,
            label = "Go to " .. (guide.dungeon and guide.dungeon.name or guide.title) .. " entrance",
            title = guide.dungeon and guide.dungeon.name or guide.title, planned = #stops > 0}
    end
    local mapID = stops[1] and stops[1].mapID or ns.profile.mapID
    for _, stop in ipairs(stops) do if stop.mapID ~= mapID then otherMaps = otherMaps + 1 end end
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops,
        origin = includeOrigin and start and start.mapID == mapID and start or nil, focusKey = ns.self,
        missing = missing, remote = 0, limited = #tasks - #order, otherMaps = otherMaps,
        partial = missing > 0 or #tasks ~= #order or not guide.pickupQuestID and not entrance}
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
