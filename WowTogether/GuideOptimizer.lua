local addonName, ns = ...

local BEAM_WIDTH, QUESTS_PER_TRIP, MAX_STOPS = 24, 6, 20
local costModels = setmetatable({}, {__mode = "k"})
-- Exact trip ordering is attempted while the progress-vector state space
-- (product of stage counts + 1, times the task count) stays within this
-- budget; larger trips fall back to the bounded beam search.
local EXACT_STATE_BUDGET = 60000
local function distance(mapID, a, b, metrics)
    if not a or not b then return 0 end
    local byMap = metrics and costModels[metrics]
    if metrics and not byMap then byMap = {}; costModels[metrics] = byMap end
    local model = byMap and byMap[mapID]
    if not model then
        model = ns.RouteCostModel({travel = function(from, to)
            return ns.WalkingDistance(mapID, from, to, metrics)
                or ns.NormalizedDistance(from, to) * ns.ROUTE_WEIGHTS.normalizedDistanceScale
        end})
        if byMap then byMap[mapID] = model end
    end
    return model:travel(a, b)
end

local function resetMetrics(metrics)
    for mapID in pairs(metrics) do metrics[mapID] = nil end
    costModels[metrics] = nil
end

local function activeForParty(id, readyOnly, personal)
    if personal then
        return ns.active[id] ~= nil and (not readyOnly or ns.QuestProgressReady(ns.self, id) == true
            or ns.readyToTurnIn[id] == true)
    end
    for _, person in ipairs(ns.PartyProfiles()) do
        local active = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
        if active and active[id] and (not readyOnly or ns.QuestProgressReady(person.key, id) == true
            or person.key == ns.self and ns.readyToTurnIn[id] == true) then return true end
    end
    return false
end

-- Pull verified, unfinished prerequisites into ordinary live leveling routes
-- so a blocked destination can be reached through its actual quest chain.
local function prerequisiteRecords(guide)
    local records, seen = {}, {}
    for _, record in ipairs(guide.records or {}) do
        if record and record.id and not seen[record.id] then
            records[#records + 1], seen[record.id] = record, true
        end
    end
    local cursor = 1
    local recordLimit = guide.classLineGuide and 1024 or 256
    while cursor <= #records and #records < recordLimit do
        local id = records[cursor].id
        local quest = ns.CatalogueQuest(id)
        if quest then
            local parents, added = {}, {}
            local function add(parent)
                if ns.GuideInteger(parent) and parent > 0 and parent ~= id and not added[parent]
            and (guide.personal and ns.Completed(parent) ~= true or not guide.personal and ns.CatalogueCompletion(ns.self, parent) ~= true) then
                    parents[#parents + 1], added[parent] = parent, true
                end
            end
            add(quest.previousQuest)
            for _, parent in ipairs(quest.prerequisiteAll or {}) do add(parent) end
            if not quest.prerequisitesUnverified then
                for _, parent in ipairs(ns.LearnedPrerequisiteIDs and ns.LearnedPrerequisiteIDs(id) or {}) do add(parent) end
            end
            if quest.prerequisiteAny and not quest.prerequisitesUnverified then
                local met, best, score = false, nil, nil
                for _, parent in ipairs(quest.prerequisiteAny) do
                    if ns.CatalogueCompletion(ns.self, parent) == true then met = true; break end
                    local candidate = ns.CatalogueQuest(parent)
                    local allowed = ns.CatalogueIdentityAllowed(parent, ns.profile)
                    if candidate and allowed == true and (candidate.minLevel or candidate.level or 255) <= (ns.profile.level or 0)
                        and not ns.GuideQuestSkipped(parent) then
                        local point = ns.NPCPickupPoint(parent) or candidate.starts and candidate.starts[1]
                        local value = point and ns.PlayerPoint(point.mapID)
                            and ns.TravelPointDistance(ns.PlayerPoint(point.mapID), point) or 100000
                        if ns.active[parent] then value = -1 end
                        if not score or value < score or value == score and parent < best then best, score = parent, value end
                    end
                end
                if not met and best then
                    add(best)
                    if guide.collectionDependencies then guide.collectionDependencies[id] = {best} end
                    if guide.collectionAlternatives then guide.collectionAlternatives[best] = #quest.prerequisiteAny end
                end
            end
            for _, parent in ipairs(parents) do
                local candidate = ns.CatalogueQuest(parent)
                local allowed = candidate and ns.CatalogueIdentityAllowed(parent, ns.profile)
                local levelReady = candidate and (candidate.minLevel or candidate.level or 255) <= (ns.profile.level or 0)
                if not seen[parent] and candidate and allowed == true and levelReady
                    and (guide.classLineGuide or ns.ClassQuestEnabled(parent))
                    and not ns.GuideQuestSkipped(parent) and #records < recordLimit then
                    local record = ns.CatalogueRecord(parent)
                    if record then records[#records + 1], seen[parent] = record, true end
                end
            end
        end
        cursor = cursor + 1
    end
    return records
end

local function availableTasks(guide)
    local tasks, missing, complete, live = {}, 0, 0, ns.AllGuideRecords()
    local records = {}
    for _, record in ipairs(prerequisiteRecords(guide)) do
        if guide.classLineGuide or ns.ClassQuestEnabled(record.id) then records[#records + 1] = record end
    end
    local focus = guide.personal and ns.self or ns.GuideFocus(records)
    guide.focusKey = focus
    for _, record in ipairs(records) do
        local finished = guide.personal and ns.Completed(record.id) == true or not guide.personal and ns.PartyQuestFinished(record.id)
        if finished then complete = complete + 1
        else
            local seriesPrevious = guide.classLineGuide and ns.ClassQuestSeriesPrevious(record.id)
            local seriesBlocked = seriesPrevious and ns.Completed(seriesPrevious) ~= true
            local seriesReason = seriesBlocked and ("Finish " .. ns.QuestTitle(seriesPrevious) .. " first.")
            local active = activeForParty(record.id, false, guide.personal)
            local readyTask = not seriesBlocked and (guide.personal or ns.FocusCanStartRecord(record, focus))
                and (guide.classLineGuide and (ns.CatalogueAllowed(record.id, ns.profile, ns.self) == true
                    or active or ns.QuestProgressReady(ns.self, record.id) == true)
                    or not guide.classLineGuide and (ns.LevelingValue(record.id) ~= false
                        or activeForParty(record.id, true, guide.personal)
                        or guide.catchupRequired and guide.catchupRequired[record.id]))
            if not ns.GuideQuestSkipped(record.id) and readyTask then
                local candidate = live[record.id] or record
                local stages = guide.classLineGuide and ns.RouteStages(candidate, ns.self)
                    or ns.LevelingRouteStages(candidate, focus, guide.personal)
                if #stages > 0 then
                    local first = stages[1]
                    tasks[#tasks + 1] = {id = record.id, stages = stages, first = first,
                        xp = ns.CatalogueQuest(record.id) and ns.CatalogueQuest(record.id).xp or 0,
                        active = active, ready = first.kind == "t"}
                else
                    missing = missing + 1
                    local _, reason = ns.CatalogueAllowed(record.id, ns.profile, ns.self)
                    guide.pendingReason = guide.pendingReason or reason or seriesReason or ns.QuestStartGapReason(record.id)
                end
            else
                missing = missing + 1
                local _, reason = ns.CatalogueAllowed(record.id, ns.profile, ns.self)
                guide.pendingReason = guide.pendingReason or seriesReason or reason or ns.QuestStartGapReason(record.id)
                local quest = ns.CatalogueQuest(record.id)
                if guide.classLineGuide and not seriesBlocked and quest and quest.minLevel
                    and (ns.profile.level or 0) < quest.minLevel
                    and ns.CatalogueIdentityAllowed(record.id, ns.profile) == true
                    and ns.CataloguePrerequisitesAllowed(record.id, ns.self) == true
                    and (not guide.nextLevel or quest.minLevel < guide.nextLevel) then
                    guide.nextLevel = quest.minLevel
                end
            end
        end
    end
    if guide.classLineGuide and #tasks == 0 and guide.nextLevel then
        guide.pendingReason = "Reach level " .. guide.nextLevel .. " to continue your class guide."
    end
    return tasks, missing, complete, #records
end

local function splitReasonReadyTasks(guide, tasks)
    local ready, later = {}, {}
    for _, task in ipairs(tasks) do
        local current, decision = ns.GuideReasonCanBeCurrent(task.first, guide)
        if current then ready[#ready + 1] = task
        else later[#later + 1] = {id = task.id, title = task.first.title,
            level = (ns.CatalogueQuest(task.id) or {}).level, reason = decision.code} end
    end
    return ready, later
end

local function chooseBatch(guide, tasks, mapID, position, metrics)
    local selected, seen, previous, stops = {}, {}, position, 0
    -- Keep the trip's quest set until its work is finished; accepting a pickup
    -- must not discard its objective or change the rest of the committed loop.
    for _, id in ipairs(guide.batchIDs or {}) do
        for _, task in ipairs(tasks) do
            if task.id == id and task.first.mapID == mapID and stops + #task.stages <= MAX_STOPS then
                selected[#selected + 1], seen[id], previous = task, true, task.first
                stops = stops + #task.stages
            end
        end
    end
    if #selected > 0 then
        -- A turn-in can unlock another pickup at the NPC we are visiting. Add
        -- nearby newly eligible work without throwing away the committed trip.
        for _, task in ipairs(tasks) do
            if not seen[task.id] and task.first.kind == "a" and task.first.mapID == mapID and position
                and #selected < QUESTS_PER_TRIP and stops + #task.stages <= MAX_STOPS
                and distance(mapID, position, task.first, metrics) <= math.min(150, ns.Option("circuitRadius") * ns.ROUTE_WEIGHTS.circuitRadiusScale) then
                selected[#selected + 1], seen[task.id] = task, true
                stops = stops + #task.stages
            end
        end
        guide.batchIDs = {}; for _, task in ipairs(selected) do guide.batchIDs[#guide.batchIDs + 1] = task.id end
        return selected
    end
    -- Candidates are still priced from the last chosen pickup, which keeps
    -- the greedy chain compact. The detour cutoff, however, measures the
    -- candidate against the nearest stop already in the trip (origin,
    -- pickups, objectives and hand-ins): a quest beside the origin or an
    -- earlier stop is still worth the trip even if the last pickup drifted.
    -- The exact ordering pass afterwards decides the actual visit order.
    local anchors = {}
    if position then anchors[1] = position end
    local function anchor(task)
        for _, stage in ipairs(task.stages) do
            if stage.mapID ~= mapID then break end
            anchors[#anchors + 1] = stage
        end
    end
    local function nearest(task)
        local best = math.huge
        for _, point in ipairs(anchors) do best = math.min(best, distance(mapID, point, task.first, metrics)) end
        return best
    end
    for _, task in ipairs(selected) do anchor(task) end
    local radius = ns.Option("circuitRadius") * ns.ROUTE_WEIGHTS.circuitRadiusScale
    while #selected < QUESTS_PER_TRIP do
        local best, cost
        for _, task in ipairs(tasks) do
            if not seen[task.id] and task.first.mapID == mapID and stops + #task.stages <= MAX_STOPS then
                local d = distance(mapID, previous, task.first, metrics)
                local detour, last = 0, task.first
                for _, stage in ipairs(task.stages) do
                    if stage.mapID ~= mapID then break end
                    detour = detour + distance(mapID, last, stage, metrics); last = stage
                end
                -- Walking dominates. XP is a bounded tie preference, never a
                -- reason to cross a zone for an otherwise unrelated pickup.
                local value = d + detour * 0.12 - math.min(80, task.xp / 20)
                if task.active then value = value - 250 end
                if task.ready and d < 400 then value = value - 600 end
                if not cost or value < cost or value == cost and task.id < best.id then best, cost = task, value end
            end
        end
        if not best then break end
        if #selected > 0 and #anchors > 0 and nearest(best) > radius then break end
        selected[#selected + 1], seen[best.id], previous = best, true, best.first
        stops = stops + #best.stages
        anchor(best)
    end
    guide.batchIDs = {}; for _, task in ipairs(selected) do guide.batchIDs[#guide.batchIDs + 1] = task.id end
    return selected
end

local function orderKey(state)
    if not state.orderKey then
        local keys = {}; for _, stop in ipairs(state.stops) do keys[#keys + 1] = stop.id .. stop.kind end
        state.orderKey = table.concat(keys, ",")
    end
    return state.orderKey
end

-- Every trip stop plus the origin, with a symmetric distance matrix computed
-- once per trip. Row/column 0 is the origin; an unknown origin costs nothing.
local function tripMatrix(tasks, mapID, position, cooperative, metrics)
    local points, index, work = {}, {}, 0
    metrics = metrics or {}
    for i, task in ipairs(tasks) do
        index[i] = {}
        for k, stop in ipairs(task.stages) do points[#points + 1] = stop; index[i][k] = #points end
    end
    local matrix = {}
    for a = 0, #points do matrix[a] = {} end
    for a = 1, #points do
        matrix[0][a] = distance(mapID, position, points[a], metrics)
        matrix[a][0] = matrix[0][a]
        matrix[a][a] = 0
        for b = a + 1, #points do
            local d = distance(mapID, points[a], points[b], metrics)
            matrix[a][b], matrix[b][a] = d, d
            work = work + 1
            if cooperative and work % 150 == 0 then coroutine.yield(); resetMetrics(metrics) end
        end
    end
    return points, index, matrix
end

-- Exact shortest interleaving of the per-quest stage sequences. A state is
-- the per-task progress vector (mixed-radix code) plus the task whose stage was
-- visited last, so identical prefixes with the same endpoint share one entry.
-- Codes only grow along transitions, so a single increasing sweep is a
-- topological order. Returns nil when the trip exceeds the state budget.
local function exactOrder(tasks, points, index, matrix, cooperative, metrics)
    local count, radix, stride, states, total = #tasks, {}, {}, 1, 0
    for i, task in ipairs(tasks) do
        radix[i], stride[i] = #task.stages + 1, states
        states, total = states * radix[i], total + #task.stages
    end
    if total == 0 then return {}, 0 end
    if total > MAX_STOPS or states * count > EXACT_STATE_BUDGET then return nil end
    local width = count + 1
    local best, parent, work = {}, {}, 0
    -- Fill sequentially so Lua keeps both tables in their array parts.
    for state = 1, states * width - 1 do best[state], parent[state] = false, false end
    best[0] = 0
    -- Walk the progress vector as an odometer: code = sum(progress[i] * stride[i]).
    local progress = {}
    for i = 1, count do progress[i] = 0 end
    for code = 0, states - 2 do
        local base = code * width
        for last = 0, count do
            local cost = best[base + last]
            if cost then
                local row = matrix[last == 0 and 0 or index[last][progress[last]]]
                for i = 1, count do
                    local step = progress[i] + 1
                    if step < radix[i] then
                        local nextState = (code + stride[i]) * width + i
                        local value = cost + row[index[i][step]]
                        local previous = best[nextState]
                        if not previous or value < previous then best[nextState], parent[nextState] = value, base + last end
                    end
                end
                work = work + 1
                if cooperative and work % 150 == 0 then coroutine.yield(); resetMetrics(metrics) end
            end
        end
        local i = 1
        while i <= count do
            progress[i] = progress[i] + 1
            if progress[i] < radix[i] then break end
            progress[i], i = 0, i + 1
        end
    end
    local finalBase, state, cost = (states - 1) * width, nil, nil
    for last = 1, count do
        local value = best[finalBase + last]
        if value and (not cost or value < cost) then state, cost = finalBase + last, value end
    end
    if not state then return nil end
    local ordered = {}
    while state and state ~= 0 do
        local code, last = math.floor(state / width), state % width
        ordered[#ordered + 1] = points[index[last][math.floor(code / stride[last]) % radix[last]]]
        state = parent[state]
    end
    for i = 1, math.floor(#ordered / 2) do ordered[i], ordered[#ordered - i + 1] = ordered[#ordered - i + 1], ordered[i] end
    return ordered, cost
end

local function beamOrder(tasks, points, index, matrix, cooperative, metrics)
    local initial, total, work = {}, 0, 0
    for i, task in ipairs(tasks) do initial[i] = 1; total = total + #task.stages end
    local beam = {{next = initial, stops = {}, last = 0, cost = 0}}
    for _ = 1, math.min(total, MAX_STOPS) do
        local expanded, signatures = {}, {}
        for _, state in ipairs(beam) do
            for i, task in ipairs(tasks) do
                local stop = task.stages[state.next[i]]
                if stop then
                    local nextState = {}; for k, value in ipairs(state.next) do nextState[k] = value end
                    nextState[i] = nextState[i] + 1
                    local to = index[i][state.next[i]]
                    local cost = state.cost + matrix[state.last][to]
                    local key = table.concat(nextState, ",") .. ":" .. i
                    local previous = signatures[key]
                    if not previous or cost < previous.cost then
                        local ordered = {}; for k, value in ipairs(state.stops) do ordered[k] = value end
                        ordered[#ordered + 1] = stop
                        signatures[key] = {next = nextState, stops = ordered, last = to, cost = cost}
                    end
                    work = work + 1
                    if cooperative and work % 150 == 0 then coroutine.yield(); resetMetrics(metrics) end
                end
            end
        end
        for _, candidate in pairs(signatures) do expanded[#expanded + 1] = candidate end
        table.sort(expanded, function(a, b)
            if a.cost ~= b.cost then return a.cost < b.cost end
            return orderKey(a) < orderKey(b)
        end)
        beam = {}; for i = 1, math.min(BEAM_WIDTH, #expanded) do beam[i] = expanded[i] end
        if #beam == 0 then break end
    end
    return beam[1] and beam[1].stops or {}, beam[1] and beam[1].cost or 0
end

local function optimize(tasks, mapID, position, cooperative, metrics)
    metrics = metrics or {}
    local points, index, matrix = tripMatrix(tasks, mapID, position, cooperative, metrics)
    local stops, cost = exactOrder(tasks, points, index, matrix, cooperative, metrics)
    if stops then return stops, cost, "exact" end
    stops, cost = beamOrder(tasks, points, index, matrix, cooperative, metrics)
    return stops, cost, "beam"
end
ns.OptimizeTripOrder = optimize

local function completePreview(tasks, position, cooperative, metrics)
    local nextStage, ordered, previous, work = {}, {}, position, 0
    metrics = metrics or {}
    for index in ipairs(tasks) do nextStage[index] = 1 end
    while true do
        local best, cost
        for index, task in ipairs(tasks) do
            local stop = task.stages[nextStage[index]]
            if stop then
                local d = previous and previous.mapID ~= stop.mapID and 15000 or distance(stop.mapID, previous, stop, metrics)
                if not cost or d < cost or d == cost and stop.id < tasks[best].id then best, cost = index, d end
            end
            work = work + 1
            if cooperative and work % 200 == 0 then coroutine.yield(); resetMetrics(metrics) end
        end
        if not best then break end
        previous = tasks[best].stages[nextStage[best]]
        ordered[#ordered + 1], nextStage[best] = previous, nextStage[best] + 1
    end
    return ordered
end

function ns.BuildLevelingRoute(guide, includeOrigin, cooperative)
    guide.pendingReason = nil
    local tasks, missing, complete, enabled = availableTasks(guide)
    local laterTasks
    tasks, laterTasks = splitReasonReadyTasks(guide, tasks)
    local mapID = guide.mapID or 0
    local current = ns.profile and ns.profile.mapID or 0
    local hasMap = false
    for _, task in ipairs(tasks) do if task.first.mapID == mapID then hasMap = true end end
    for _, task in ipairs(tasks) do if task.first.mapID == current then mapID, hasMap = current, true; break end end
    if not hasMap and tasks[1] then mapID = tasks[1].first.mapID end
    local position = current == mapID and ns.PlayerPoint(mapID) or nil
    local metrics = {}
    local batch = chooseBatch(guide, tasks, mapID, position, metrics)
    local localTasks, otherMaps, partial = {}, 0, false
    for _, task in ipairs(batch) do
        local stages = {}
        for _, stop in ipairs(task.stages) do
            if stop.mapID ~= mapID then otherMaps = otherMaps + 1; break end
            stages[#stages + 1] = stop
        end
        localTasks[#localTasks + 1] = {id = task.id, stages = stages}
        local quest = ns.CatalogueQuest(task.id)
        if quest and quest.objectiveLocationsIncomplete then partial = true end
    end
    local stops, cost, method = optimize(localTasks, mapID, position, cooperative, metrics)
    if ns.Option("xpModel") and guide.mode == "zone" and ns.ZoneExitProjection then
        local projection = ns.ZoneExitProjection(guide, ns.profile)
        local nextGuide = projection and projection.nextGuide
        if nextGuide and projection.level < (nextGuide.rangeLow or 1) then
            local state, required = ns.XPState(), 0
            if state then
                local level, xp = state.level, state.xp
                while level < nextGuide.rangeLow do
                    local threshold = ns.xpCurve and ns.xpCurve[level] or ns.xpBaseline and ns.xpBaseline[level]
                    if not threshold then required = nil; break end
                    required = required + math.max(0, threshold - xp)
                    xp, level = 0, level + 1
                end
            end
            local area
            for index = #stops, 1, -1 do if stops[index].kind == "q" then area = stops[index]; break end end
            if required and required > 0 and area then
                stops[#stops + 1] = {id = 0, kind = "notice", mapID = area.mapID,
                    x = area.x, y = area.y, reasonCode = "zone-exit", optional = true,
                    label = "Grind " .. required .. " XP near " .. (area.title or guide.zone)
                        .. "; next zone starts at level " .. nextGuide.rangeLow .. ".",
                    title = guide.zone}
            end
        end
    end
    if #stops == 0 and not guide.pendingReason then
        guide.pendingReason = #laterTasks > 0 and "No specific quest reason is ready yet; generic steps are listed under Later."
            or complete == enabled and "This guide's selected quests are completed."
            or "Visit a quest giver in " .. guide.zone .. "; the next pickup or objective location is not known yet."
    end
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops, origin = includeOrigin and position or nil,
        previewStops = completePreview(tasks, position, cooperative, metrics), eligibleMappedQuests = #tasks,
        missing = missing, later = laterTasks, otherMaps = otherMaps, limited = math.max(0, #tasks - #batch), focusKey = guide.focusKey,
        partial = partial or missing > 0 or otherMaps > 0, estimatedWalkingCost = cost,
        guideQuests = #guide.records, tripQuests = #batch, completed = complete, optimized = true, tripSearch = method,
        pendingReason = guide.pendingReason}
end

function ns.CancelGuidePlanning()
    ns.planningGeneration = (ns.planningGeneration or 0) + 1
    ns.routePlanning = nil
    ns.routePlanningError, ns.routePlanningErrorDetail = nil, nil
end

local function fingerprint(guide)
    if guide.fixedRoute then return "fixed:" .. guide.key end
    local values = {tostring(ns.Option("classQuests")), ns.profile and ns.profile.mapID or 0, ns.profile and ns.profile.level or 0,
        ns.char.questLearning and ns.char.questLearning.revision or 0}
    for _, record in ipairs(guide.records) do
        values[#values + 1] = record.id .. ":" .. tostring(ns.active[record.id] ~= nil) .. ":" .. tostring(ns.Completed(record.id))
            .. ":" .. tostring(ns.QuestProgressReady(ns.self, record.id))
            .. ":" .. tostring((ns.ObservedPickupAvailable(record.id))) .. ":" .. tostring(ns.offered[record.id])
            .. ":" .. tostring(ns.GuideQuestSkipped(record.id))
        local quest = ns.CatalogueQuest(record.id)
        for _, point in ipairs(quest and quest.objectives or {}) do
            local item = ns.GuideItemProgress({id = record.id, kind = "q", itemID = point.itemID,
                action = point.action, quantity = point.quantity, quantityUnknown = point.quantityUnknown}, ns.self)
            if item then values[#values + 1] = "bag:" .. point.itemID .. ":" .. item.have .. ":" .. item.need end
        end
        local skipped = ns.char and ns.char.guideSkips
        local steps = {}; for key, value in pairs(skipped and skipped.steps[record.id] or {}) do if value == true then steps[#steps + 1] = key end end
        table.sort(steps); values[#values + 1] = table.concat(steps, ",")
    end
    for _, person in ipairs(ns.PartyProfiles()) do
        local member = ns.members[person.key]
        values[#values + 1] = person.key .. ":" .. tostring(person.synced) .. ":" .. (member and member.activeRevision or 0)
            .. ":" .. (member and member.completionRevision or 0)
            .. ":" .. (member and member.historyRevision or 0) .. ":" .. (person.profile and person.profile.level or 0)
            .. ":" .. (member and member.offerRevision or 0)
    end
    return table.concat(values, "|")
end

function ns.PlanLevelingGuide(guide, invite)
    ns.guideStopped, ns.guideWindowIdle = nil, nil
    if ns.guideScanning and not ns.guideScanning.executing then ns.CancelGuideScan() end
    if not guide then return false end
    ns.CancelGuidePlanning()
    ns.routePlanningError, ns.routePlanningErrorDetail = nil, nil
    ns.ScanGuideProgress(guide, false)
    local generation, before = ns.planningGeneration, fingerprint(guide)
    local job = coroutine.create(function() return ns.BuildGuideRoute(guide, true, true) end)
    ns.routePlanning = {guide = guide, generation = generation}
    ns.UpdateNavigation()
    local restarts = 0
    local function advance()
        if generation ~= ns.planningGeneration then return end
        -- Fine graph/replay yields should not each cost a timer frame. Keep
        -- work bounded by both elapsed public CPU time and a resume limit.
        -- Missing/private/backwards timers retain one resume per callback.
        local start = ns.ReadPublic(debugprofilestop)
        local timed = ns.Public(start) and type(start) == "number" and start == start
            and start >= 0 and start < math.huge
        local okay, result
        for _ = 1, 16 do
            okay, result = coroutine.resume(job)
            if generation ~= ns.planningGeneration then return end
            if not okay or coroutine.status(job) == "dead" or not timed then break end
            local now = ns.ReadPublic(debugprofilestop)
            if not ns.Public(now) or type(now) ~= "number" or now ~= now or now >= math.huge
                or now < start or now - start >= 3 then break end
        end
        if not okay then
            ns.routePlanning = nil
            ns.routePlanningError = "Route generation failed; copy Diagnostics for investigation."
            if ns.Public(result) and type(result) == "string" then ns.routePlanningErrorDetail = string.sub(result, 1, 400) end
            ns.Refresh(); ns.guideAction = ns.routePlanningError; return
        end
        if coroutine.status(job) ~= "dead" then C_Timer.After(0.01, advance); return end
        if fingerprint(guide) ~= before and restarts < 2 then
            restarts = restarts + 1; before = fingerprint(guide)
            job = coroutine.create(function() return ns.BuildGuideRoute(guide, true, true) end)
            C_Timer.After(0.01, advance); return
        end
        ns.routePlanning, ns.routePlanningError, ns.routePlanningErrorDetail = nil, nil, nil
        if guide.fixedRoute then result = ns.BuildFixedGuideRoute(guide, true) end
        if fingerprint(guide) ~= before then
            ns.guideAction = "Quest data changed during generation. Start route again when sync finishes."
            ns.Refresh(); return
        end
        ns.preparedLevelingRoute = {guide = guide, route = result}
        if invite then ns.StartPartyRoute(guide) else ns.ShowGuideOnMap(guide) end
        ns.preparedLevelingRoute = nil
        ns.Refresh()
    end
    if not C_Timer or type(C_Timer.After) ~= "function" then
        ns.routePlanning = nil
        ns.routePlanningError = "Route scheduler unavailable on this build; copy Diagnostics."
        ns.Refresh(); ns.guideAction = ns.routePlanningError; return false
    end
    C_Timer.After(0.01, advance)
    return true
end
