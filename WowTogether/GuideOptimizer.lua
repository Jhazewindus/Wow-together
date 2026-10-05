local addonName, ns = ...

local BEAM_WIDTH, QUESTS_PER_TRIP, MAX_STOPS = 24, 6, 20
local function distance(mapID, a, b)
    if not a or not b then return 0 end
    return ns.WalkingDistance(mapID, a, b) or ns.NormalizedDistance(a, b) * 6000
end

local function activeForParty(id)
    for _, person in ipairs(ns.PartyProfiles()) do
        local active = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
        if active and active[id] then return true end
    end
    return false
end

local function availableTasks(guide)
    local tasks, missing, complete, live = {}, 0, 0, ns.AllGuideRecords()
    local focus = ns.GuideFocus(guide.records)
    guide.focusKey = focus
    for _, record in ipairs(guide.records) do
        if ns.PartyQuestFinished(record.id) then complete = complete + 1
        elseif not ns.GuideQuestSkipped(record.id) and ns.FocusCanStartRecord(record, focus)
            and (ns.LevelingValue(record.id) ~= false or activeForParty(record.id)) then
            local candidate = live[record.id] or record
            local stages = ns.PartyRouteStages(candidate, focus)
            if #stages > 0 then
                local first = stages[1]
                tasks[#tasks + 1] = {id = record.id, stages = stages, first = first,
                    xp = ns.CatalogueQuest(record.id) and ns.CatalogueQuest(record.id).xp or 0,
                    active = activeForParty(record.id), ready = first.kind == "t"}
            else
                missing = missing + 1
                local _, reason = ns.CatalogueAllowed(record.id, ns.profile, ns.self)
                guide.pendingReason = guide.pendingReason or reason
            end
        else
            missing = missing + 1
            local _, reason = ns.CatalogueAllowed(record.id, ns.profile, ns.self)
            guide.pendingReason = guide.pendingReason or reason
        end
    end
    return tasks, missing, complete
end

local function chooseBatch(guide, tasks, mapID, position)
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
                and distance(mapID, position, task.first) <= math.min(150, ns.Option("circuitRadius") * 6000) then
                selected[#selected + 1], seen[task.id] = task, true
                stops = stops + #task.stages
            end
        end
        guide.batchIDs = {}; for _, task in ipairs(selected) do guide.batchIDs[#guide.batchIDs + 1] = task.id end
        return selected
    end
    while #selected < QUESTS_PER_TRIP do
        local best, cost
        for _, task in ipairs(tasks) do
            if not seen[task.id] and task.first.mapID == mapID and stops + #task.stages <= MAX_STOPS then
                local d = distance(mapID, previous, task.first)
                local detour, last = 0, task.first
                for _, stage in ipairs(task.stages) do
                    if stage.mapID ~= mapID then break end
                    detour = detour + distance(mapID, last, stage); last = stage
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
        if #selected > 0 and previous and distance(mapID, previous, best.first) > ns.Option("circuitRadius") * 6000 then break end
        selected[#selected + 1], seen[best.id], previous = best, true, best.first
        stops = stops + #best.stages
    end
    guide.batchIDs = {}; for _, task in ipairs(selected) do guide.batchIDs[#guide.batchIDs + 1] = task.id end
    return selected
end

local function optimize(tasks, mapID, position, cooperative)
    local initial, total, work = {}, 0, 0
    for i, task in ipairs(tasks) do initial[i] = 1; total = total + #task.stages end
    local beam = {{next = initial, stops = {}, last = position, cost = 0}}
    for _ = 1, math.min(total, MAX_STOPS) do
        local expanded, signatures = {}, {}
        for _, state in ipairs(beam) do
            for index, task in ipairs(tasks) do
                local stop = task.stages[state.next[index]]
                if stop then
                    local nextState = {}; for k, value in ipairs(state.next) do nextState[k] = value end
                    nextState[index] = nextState[index] + 1
                    local cost = state.cost + distance(mapID, state.last, stop)
                    local key = table.concat(nextState, ",") .. ":" .. index
                    local previous = signatures[key]
                    if not previous or cost < previous.cost then
                        local ordered = {}; for k, value in ipairs(state.stops) do ordered[k] = value end
                        ordered[#ordered + 1] = stop
                        local candidate = {next = nextState, stops = ordered, last = stop, cost = cost}
                        signatures[key] = candidate
                    end
                    work = work + 1
                    if cooperative and work % 150 == 0 then coroutine.yield() end
                end
            end
        end
        for _, candidate in pairs(signatures) do expanded[#expanded + 1] = candidate end
        table.sort(expanded, function(a, b)
            if a.cost ~= b.cost then return a.cost < b.cost end
            local ak, bk = {}, {}
            for _, stop in ipairs(a.stops) do ak[#ak + 1] = stop.id .. stop.kind end
            for _, stop in ipairs(b.stops) do bk[#bk + 1] = stop.id .. stop.kind end
            return table.concat(ak, ",") < table.concat(bk, ",")
        end)
        beam = {}; for i = 1, math.min(BEAM_WIDTH, #expanded) do beam[i] = expanded[i] end
        if #beam == 0 then break end
    end
    return beam[1] and beam[1].stops or {}, beam[1] and beam[1].cost or 0
end

local function completePreview(tasks, position, cooperative)
    local nextStage, ordered, previous, work = {}, {}, position, 0
    for index in ipairs(tasks) do nextStage[index] = 1 end
    while true do
        local best, cost
        for index, task in ipairs(tasks) do
            local stop = task.stages[nextStage[index]]
            if stop then
                local d = previous and previous.mapID ~= stop.mapID and 15000 or distance(stop.mapID, previous, stop)
                if not cost or d < cost or d == cost and stop.id < tasks[best].id then best, cost = index, d end
            end
            work = work + 1
            if cooperative and work % 200 == 0 then coroutine.yield() end
        end
        if not best then break end
        previous = tasks[best].stages[nextStage[best]]
        ordered[#ordered + 1], nextStage[best] = previous, nextStage[best] + 1
    end
    return ordered
end

function ns.BuildLevelingRoute(guide, includeOrigin, cooperative)
    guide.pendingReason = nil
    local tasks, missing, complete = availableTasks(guide)
    local mapID = guide.mapID or 0
    local current = ns.profile and ns.profile.mapID or 0
    local hasMap = false
    for _, task in ipairs(tasks) do if task.first.mapID == mapID then hasMap = true end end
    for _, task in ipairs(tasks) do if task.first.mapID == current then mapID, hasMap = current, true; break end end
    if not hasMap and tasks[1] then mapID = tasks[1].first.mapID end
    local position = current == mapID and ns.PlayerPoint(mapID) or nil
    local batch = chooseBatch(guide, tasks, mapID, position)
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
    local stops, cost = optimize(localTasks, mapID, position, cooperative)
    if #stops == 0 and not guide.pendingReason then
        guide.pendingReason = complete == #guide.records and "This guide's selected quests are completed."
            or "Visit a quest giver in " .. guide.zone .. "; the next pickup or objective location is not known yet."
    end
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops, origin = includeOrigin and position or nil,
        previewStops = completePreview(tasks, position, cooperative), eligibleMappedQuests = #tasks,
        missing = missing, otherMaps = otherMaps, limited = math.max(0, #tasks - #batch), focusKey = guide.focusKey,
        partial = partial or missing > 0 or otherMaps > 0, estimatedWalkingCost = cost,
        guideQuests = #guide.records, tripQuests = #batch, completed = complete, optimized = true}
end

function ns.CancelGuidePlanning()
    ns.planningGeneration = (ns.planningGeneration or 0) + 1
    ns.routePlanning = nil
end

local function fingerprint(guide)
    if guide.fixedRoute then return "fixed:" .. guide.key end
    local values = {ns.profile and ns.profile.mapID or 0, ns.profile and ns.profile.level or 0,
        ns.db.questLearning and ns.db.questLearning.revision or 0}
    for _, record in ipairs(guide.records) do
        values[#values + 1] = record.id .. ":" .. tostring(ns.active[record.id] ~= nil) .. ":" .. tostring(ns.Completed(record.id))
            .. ":" .. tostring(ns.QuestProgressReady(ns.self, record.id))
            .. ":" .. tostring((ns.ObservedPickupAvailable(record.id))) .. ":" .. tostring(ns.offered[record.id])
            .. ":" .. tostring(ns.GuideQuestSkipped(record.id))
        local skipped = ns.db.guideSkips and ns.db.guideSkips[ns.self]
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
        local okay, result = coroutine.resume(job)
        if not okay then
            ns.routePlanning = nil
            ns.routePlanningError = "Route generation failed; copy Diagnostics for investigation."
            if ns.Public(result) and type(result) == "string" then ns.routePlanningErrorDetail = string.sub(result, 1, 400) end
            ns.guideAction = ns.routePlanningError; ns.Refresh(); return
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
        ns.guideAction = "Route scheduler unavailable on this build; copy Diagnostics."
        ns.Refresh(); return false
    end
    C_Timer.After(0.01, advance)
    return true
end
