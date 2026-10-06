local addonName, ns = ...

-- Compile from catalogue geography and chain dependencies, never the player's
-- position, quest log, completion flags or current level. Progress is a separate
-- pass over this immutable order. Unknown locations are explicit instructions.
local function copy(value)
    local result = {}; for key, item in pairs(value) do result[key] = item end; return result
end

function ns.GuideLocationCoverage(records)
    local result = {quests = #records, pickups = 0, objectives = 0, turnins = 0, details = 0}
    for _, record in ipairs(records) do
        local quest = ns.CatalogueQuest(record.id) or {}
        if quest.starts and #quest.starts > 0 then result.pickups = result.pickups + 1 end
        if quest.objectives and #quest.objectives > 0 then result.objectives = result.objectives + 1 end
        if quest.ends and #quest.ends > 0 then result.turnins = result.turnins + 1 end
        if quest.prerequisitesRead then result.details = result.details + 1 end
    end
    return result
end

local function stages(record)
    local quest, result, lastLocated = ns.CatalogueQuest(record.id), {}, nil
    if not quest then return result end
    local function add(point, kind, requirement)
        local stop = ns.PublishedGuideStop(record, point, kind)
        if not stop then stop = {id = record.id, kind = kind, title = record.title, unknownLocation = true,
            mapID = record.mapID, label = "Location not recorded for " .. record.title,
            planningAnchor = lastLocated}
            local reference = requirement or (kind == "a" and quest.startRefs or kind == "t" and quest.endRefs or {})[1]
            if reference then
                stop.targetName, stop.quantity, stop.action = reference.name, reference.quantity, reference.action
                stop.entityID, stop.entityType = reference.entityID, reference.entityType
                stop.objectiveKey = kind == "q" and (reference.entityType .. ":" .. reference.entityID) or nil
                if reference.entityType == "npc" then stop.npcName = reference.name end
                if reference.entityType == "item" then stop.itemName, stop.itemID = reference.name, reference.entityID end
                stop.useItemName, stop.spellID = reference.useItemName, reference.spellID
            end
        else lastLocated = stop end
        stop.planned, stop.learnedSource = true, ns.LearnedStepSource(record.id, ns.profile, ns.self)
        result[#result + 1] = stop
    end
    add(quest.starts and quest.starts[1], "a")
    if quest.objectives and #quest.objectives > 0 then
        for _, point in ipairs(quest.objectives) do add(point, "q") end
    elseif not quest.objectiveLocationsIncomplete then add(quest.ends and quest.ends[1], "q") end
    if quest.objectiveLocationsIncomplete or not quest.objectives and not quest.ends then
        if quest.missingRequirements and #quest.missingRequirements > 0 then
            for _, requirement in ipairs(quest.missingRequirements) do add(nil, "q", requirement) end
        else add(nil, "q") end
    end
    add(quest.ends and quest.ends[1], "t")
    return result
end

local function distance(a, b, metrics)
    -- Missing objective geography is a data gap, not a distant destination.
    -- Use this quest's last published place for ordering only; never give an
    -- unmapped step fake coordinates or draw its anchor as an objective.
    if b.unknownLocation then b = b.planningAnchor; if not b then return 12000 end end
    if a and a.unknownLocation then a = a.planningAnchor; if not a then return 12000 end end
    if not a then return 0 end
    if a.mapID ~= b.mapID then return ns.TravelPointDistance(a, b, metrics) or 15000 end
    return ns.WalkingDistance(b.mapID, a, b, metrics) or ns.NormalizedDistance(a, b) * 6000
end

function ns.GenerateFixedGuide(guide, cooperative)
    local tasks, done, ordered, work = {}, {}, {}, 0
    local metrics, learned, locations = {}, {}, {cooperative = cooperative}
    for _, record in ipairs(guide.records) do
        if not ns.IsLevelingExcludedQuest(record.id) and ns.CatalogueIdentityAllowed(record.id, ns.profile) ~= false and not ns.IsRepeatableQuest(record.id)
            and not ns.IsProfessionQuest(record.id) then
            ns.ResolveWorldQuestLocations(record.id, locations)
            local list = stages(record)
            if #list > 0 then tasks[#tasks + 1] = {id = record.id, stages = list, next = 1} end
        end
        work = work + 1
        if cooperative and work % 8 == 0 then coroutine.yield() end
    end
    table.sort(tasks, function(a, b) return a.id < b.id end)
    local function unlocked(id, handedIn)
        local quest = ns.CatalogueQuest(id)
        if quest.previousQuest and not done[quest.previousQuest] and quest.previousQuest ~= handedIn then return false end
        for _, previous in ipairs(quest.prerequisiteAll or {}) do
            if not done[previous] and previous ~= handedIn then return false end
        end
        if quest.prerequisiteAny then
            local met = false; for _, previous in ipairs(quest.prerequisiteAny) do if done[previous] or previous == handedIn then met = true end end
            if not met then return false end
        elseif not quest.previousQuest and not quest.prerequisiteAll then
            if not learned[id] then learned[id] = ns.LearnedPrerequisiteIDs(id) end
            for _, previous in ipairs(learned[id]) do if not done[previous] and previous ~= handedIn then return false end end
        end
        return true
    end
    local previous, urgent
    while true do
        local available, floor = {}, 255
        for _, task in ipairs(tasks) do
            local stop = task.stages[task.next]
            if stop and (stop.kind ~= "a" or unlocked(task.id)) then
                available[#available + 1] = task
                floor = math.min(floor, ns.CatalogueQuest(task.id).level or 0)
            end
            work = work + 1
            if cooperative and work % 200 == 0 then coroutine.yield(); metrics, learned = {}, {} end
        end
        if #available == 0 then break end
        local best, score
        for _, task in ipairs(available) do
            local stop, quest = task.stages[task.next], ns.CatalogueQuest(task.id)
            local value = distance(previous, stop, metrics) + math.max(0, (quest.level or 0) - floor - 2) * 2500
            if stop.kind == "a" then value = value - 100 end
            if task == urgent then value = -math.huge end
            if stop.kind == "t" then
                -- Prefer a nearby hand-in that opens another pickup at this
                -- hub. This depends on published geography, not player position.
                for _, child in ipairs(tasks) do
                    work = work + 1
                    if cooperative and work % 200 == 0 then coroutine.yield(); metrics, learned = {}, {} end
                    local pickup = child.stages[child.next]
                    if pickup and pickup.kind == "a" and not unlocked(child.id) and unlocked(child.id, stop.id)
                        and not pickup.unknownLocation and distance(stop, pickup, metrics) <= 150 then
                        value = value - 250; break
                    end
                end
            end
            if not score or value < score or value == score and task.id < best.id then best, score = task, value end
        end
        local stop = best.stages[best.next]
        ordered[#ordered + 1], best.next = stop, best.next + 1
        -- Accepting an escort can start the event immediately. Complete its
        -- work stage before scheduling unrelated pickups or a farming detour.
        local nextStop = best.stages[best.next]
        urgent = nextStop and nextStop.action == "escort" and best or nil
        if not stop.unknownLocation then previous = stop end
        if stop.kind == "t" then done[stop.id] = true end
    end
    -- Missing external prerequisites/cycles must not produce an invented path.
    for _, task in ipairs(tasks) do
        if task.stages[task.next] then
            for index = task.next, #task.stages do
                local stop = task.stages[index]
                stop.planNeedsReview = true
                ordered[#ordered + 1] = stop
            end
        end
    end
    guide.optimization = ns.OptimizeFixedPlan(ordered, function(a, b) return distance(a, b, metrics) end,
        cooperative, function() metrics, learned = {}, {} end)
    for index, stop in ipairs(ordered) do stop.guideStep = index end
    guide.fixedPlan = ordered
    return ordered
end

local function doneFor(stop, key, query)
    if ns.CatalogueCompletion(key, stop.id, query) == true then return true end
    local active = key == ns.self and ns.active or ns.members[key] and ns.members[key].active
    if stop.kind == "a" then return active and active[stop.id] ~= nil end
    if stop.kind == "q" then
        if ns.QuestProgressReady(key, stop.id) == true or key == ns.self and ns.readyToTurnIn[stop.id] == true then return true end
        local progress, matched = ns.ProgressForMember(key, stop.id), false
        for _, objective in ipairs(progress and progress.objectives or {}) do
            if ns.ObjectiveMatchesPoint(objective.text, {name = stop.targetName or stop.npcName, itemName = stop.itemName, progressName = stop.progressName}) then
                matched = true
                if not ns.ObjectiveFinished(objective) then return false end
            end
        end
        return matched
    end
    return false
end

local function remaining(stop, query, guide)
    if not ns.ClassQuestEnabled(stop.id) or ns.IsLevelingExcludedQuest(stop.id)
        or ns.GuideQuestSkipped(stop.id) or #ns.FilterGuideStages({stop}) == 0 then return nil end
    local waiting, chosen, unfinished
    for _, person in ipairs(query.profiles) do
        if ns.CatalogueIdentityAllowed(stop.id, person.profile) ~= false then
            local keep = ns.LevelingWorkAllowed(stop.id, person.key, query)
                or guide.catchupRequired and guide.catchupRequired[stop.id]
            -- Keep the compiled order intact. Level-filtered steps receive no
            -- completion/skip credit and can return if party context changes.
            if not person.synced or not doneFor(stop, person.key, query) then
                unfinished = true
                if keep then
                    if not person.synced then waiting = true
                    else chosen = chosen or person end
                end
            end
        end
    end
    return chosen, waiting, unfinished
end

local function completionProgress(guide, query)
    -- Empty runnable work is not quest completion. Check the complete scope
    -- once per quest, including work hidden by level/group filters or skips.
    -- Disabled optional/class and incompatible identity quests stay outside it.
    local result = {total = 0, completed = 0, unfinished = 0, skipped = 0, unknown = 0}
    for _, record in ipairs(guide.records) do
        if ns.ClassQuestEnabled(record.id) and not ns.IsLevelingExcludedQuest(record.id)
            and not ns.IsRepeatableQuest(record.id) and not ns.IsProfessionQuest(record.id) then
            local applicable, finished, unknown = false, true, false
            for _, person in ipairs(query.profiles) do
                if ns.CatalogueIdentityAllowed(record.id, person.profile) ~= false then
                    applicable = true
                    local active = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
                    local completed = ns.CatalogueCompletion(person.key, record.id, query)
                    if not person.synced or active and active[record.id] or completed ~= true then finished = false end
                    if not person.synced or completed == nil and not (active and active[record.id]) then unknown = true end
                end
            end
            if applicable then
                result.total = result.total + 1
                if finished then result.completed = result.completed + 1
                else
                    result.unfinished = result.unfinished + 1
                    if ns.GuideQuestSkipped(record.id) then result.skipped = result.skipped + 1 end
                    if unknown then result.unknown = result.unknown + 1 end
                end
            end
        end
    end
    return result
end

function ns.BuildFixedGuideRoute(guide, includeOrigin, cooperative, query)
    local plan = guide.fixedPlan or ns.GenerateFixedGuide(guide, cooperative)
    query = query or ns.NewQuestQuery()
    local stops, preview, eligibility, mapped, incomplete, unknown, pending, pendingStop = {}, {}, {}, {}, 0, 0, nil, nil
    local filteredSteps = 0
    local deferred, firstDeferred, firstReason = {}, nil, nil
    guide.observedDeferrals = guide.observedDeferrals or {}
    for _, stop in ipairs(plan) do
        local person, waiting, unfinished = remaining(stop, query, guide)
        if unfinished then incomplete = incomplete + 1 end
        if unfinished and not person and not waiting then filteredSteps = filteredSteps + 1 end
        if person or waiting then
            local current = copy(stop)
            current = ns.NPCPickupStop(current) or current
            if current.unknownLocation then unknown = unknown + 1 end
            local active, allowed, reason, offered
            if person then
                current = ns.ClientObjectiveStop(current, person.key) or current
                current.memberKey, current.forPlayer = person.key, person.name
                active = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
                allowed, reason = ns.CatalogueAllowed(stop.id, person.profile, person.key, query)
                offered = ns.PickupOfferEvidence(person.key, stop.id)
                if active and active[stop.id] then allowed = true end
            end
            if person and not waiting and not (active and active[stop.id]) and allowed == false then
                -- A temporary pickup gate is not completed credit or a manual
                -- skip. Retain every stage in the fixed plan and reconsider it
                -- on ordinary progress/offer updates, before later fixed steps.
                deferred[stop.id] = true
                if not firstDeferred then firstDeferred, firstReason = current, reason end
                if ns.routeSelection == guide and person.key == ns.self and offered == false and not guide.observedDeferrals[stop.id] then
                    guide.observedDeferrals[stop.id] = true
                    ns.RecordQuestResearch("defer-pickup", {questID = stop.id, guideKey = guide.key,
                        stepKey = ns.GuideStepKey(stop), stepKind = stop.kind, guideStep = stop.guideStep})
                end
            else
                if person then
                    if ns.routeSelection == guide and person.key == ns.self and offered == true and allowed == true and guide.observedDeferrals[stop.id] then
                        guide.observedDeferrals[stop.id] = nil
                        ns.RecordQuestResearch("restore-pickup", {questID = stop.id, guideKey = guide.key,
                            stepKey = ns.GuideStepKey(stop), stepKind = stop.kind, guideStep = stop.guideStep})
                    end
                    if allowed == true then eligibility[stop.id] = true end
                    if not pending and #stops == 0 then
                        if waiting then pending = "Waiting for your party's quest history."
                        elseif current.unknownLocation then pending = stop.blockedReason or
                            (ns.StopInstruction(current) .. ". Exact location missing.")
                        elseif stop.kind == "a" and allowed ~= true then pending = reason or "Check this quest's pickup requirements at its NPC."
                        elseif stop.kind ~= "a" and not (active and active[stop.id]) then pending = "Accept " .. stop.title .. " before this step."
                        elseif stop.kind == "t" and not ns.QuestProgressReady(person.key, stop.id)
                            and not (person.key == ns.self and ns.readyToTurnIn[stop.id]) then pending = "Finish " .. stop.title .. " before handing it in." end
                    end
                elseif waiting and not pending and #stops == 0 then pending = "Waiting for your party's quest history." end
                if pending and not pendingStop then pendingStop = current end
                if not current.unknownLocation then
                    if not pending then stops[#stops + 1] = current end
                    if eligibility[stop.id] then preview[#preview + 1] = current; mapped[stop.id] = true end
                end
            end
        end
    end
    if #stops == 0 and not pending and firstDeferred then
        pendingStop, pending = firstDeferred, firstReason or "No pickups are currently available. Progress and NPC offers will recheck this guide."
    end
    local progress, level = completionProgress(guide, query), ns.PartyLevelFloor(query)
    if #stops == 0 and not pending then
        if progress.total == 0 then pending = "No quests in this guide match your character and settings."
        elseif progress.unfinished > 0 then
            if filteredSteps > 0 and ns.GuideInteger(guide.earlyStartLevel) and level and level < guide.earlyStartLevel then
                pending = "Guide for later: recommended from level " .. guide.earlyStartLevel .. "; current level " .. level .. "."
            elseif filteredSteps > 0 then
                pending = "Guide paused: unfinished quests are outside your leveling range or need a group."
            elseif #plan == 0 then pending = "Guide steps are unavailable. Scan guide or choose another guide."
            elseif ns.GuideSelectionHasSkips(guide) then
                pending = "Remaining guide steps are skipped. Reset guide skips in Settings to restore them."
            else pending = "Quest completion is not confirmed. Scan guide to check progress." end
        end
    end
    local first = stops[1]
    local mapID = first and first.mapID or guide.homeMapID or guide.mapID
    local count, deferredCount = 0, 0
    for _ in pairs(mapped) do count = count + 1 end
    for _ in pairs(deferred) do deferredCount = deferredCount + 1 end
    guide.pendingReason = pending
    local route = {key = guide.key, title = guide.title, mapID = mapID, stops = stops, previewStops = preview,
        origin = includeOrigin and ns.PlayerPoint(mapID) or nil, missing = unknown, otherMaps = 0,
        fixed = true, guideQuests = #guide.records, totalSteps = #plan, remainingSteps = incomplete,
        completionProgress = progress, filteredSteps = filteredSteps,
        eligibleMappedQuests = count, deferredQuests = deferredCount, partial = unknown > 0,
        pendingReason = pending, pendingStop = pendingStop, focusKey = guide.focusKey}
    return ns.AddNPCVisitPickups(guide, route, query)
end

function ns.UpdateFixedGuideRoute(guide, query)
    local before = ns.selectedRoute and ns.selectedRoute.stops[1]
    local route = ns.BuildFixedGuideRoute(guide, false, false, query)
    local after = route.stops[1]
    if before and after then ns.RememberGuideStep(before, after) end
    ns.selectedRoute, ns.routePaused = route, route.pendingReason
    if not before or not after or before.guideStep ~= after.guideStep then ns.navigationPreview = nil end
    if route.completionProgress.total > 0 and route.completionProgress.unfinished == 0 then
        ns.CompleteSelectedGuide(guide); return
    end
    ns.DrawRoute()
end
