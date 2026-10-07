local addonName, ns = ...

-- A complete-guide comparison, not a new router. Unknown combat/drop/XP facts
-- are never converted into invented seconds. A started plan is not replanned.
function ns.NewGuideFlowModel(plan, distance, options)
    options = options or {}
    local model = {stages = {}, pickups = {}, handins = {}, gates = {}, quests = {}, killTargets = {}, size = #plan,
        first = plan[1], last = plan[#plan], ordinal = {}, external = 0}
    local startLevel = 60
    for _, stop in ipairs(plan) do
        local list = model.stages[stop.id] or {}; model.stages[stop.id] = list
        list[#list + 1], model.ordinal[stop] = stop, #list + 1
        if stop.kind == "a" then model.pickups[stop.id] = stop end
        if stop.kind == "t" then model.handins[stop.id] = stop end
        if stop.kind == "q" and stop.action == "kill" and stop.entityID and not stop.quantityUnknown and type(stop.quantity) == "number" then
            model.killTargets[stop.entityID] = model.killTargets[stop.entityID] or {}
            model.killTargets[stop.entityID][#model.killTargets[stop.entityID] + 1] = stop
        end
    end
    for id in pairs(model.stages) do
        local quest = ns.CatalogueQuest(id) or {}; model.quests[id] = quest
        local all = {}; for _, parent in ipairs(quest.prerequisiteAll or {}) do all[#all + 1] = parent end
        if quest.previousQuest then all[#all + 1] = quest.previousQuest
        elseif not quest.prerequisiteAny and not quest.prerequisiteAll then all = ns.LearnedPrerequisiteIDs(id) end
        model.gates[id] = {all = all, any = quest.prerequisiteAny}
        startLevel = math.min(startLevel, math.max(1, quest.minLevel or 1))
        for _, parent in ipairs(all) do if not model.handins[parent] then model.external = model.external + 1 end end
        if quest.prerequisiteAny then
            local known = false
            for _, parent in ipairs(quest.prerequisiteAny) do if model.handins[parent] then known = true end end
            if not known then model.external = model.external + 1 end
        end
    end
    model.structureValid = true
    for _, list in pairs(model.stages) do
        if list[1].kind ~= "a" or list[#list].kind ~= "t" then model.structureValid = false end
        for i = 2, #list - 1 do if list[i].kind ~= "q" then model.structureValid = false end end
    end
    model.startLevel = options.startLevel or startLevel
    model.initialLog = ns.GuideInteger(options.initialLog, 10000) and options.initialLog or 0
    model.startXP = ns.GuideInteger(options.startXP) and options.startXP or 0
    local function near(a, b, radius)
        return a and b and not a.unknownLocation and not b.unknownLocation and a.mapID == b.mapID
            and ns.ValidTravelPoint(a) and ns.ValidTravelPoint(b)
            and (distance and distance(a, b) or ns.WalkingDistance(a.mapID, a, b)
                or ns.NormalizedDistance(a, b) * 6000) <= radius
    end
    model.near = near
    model.hubUnlocks = {}
    for id, gate in pairs(model.gates) do
        local pickup = model.pickups[id]
        for _, parents in ipairs({gate.all, gate.any or {}}) do
            for _, parent in ipairs(parents) do
                local handin = model.handins[parent]
                if near(handin, pickup, 150) then model.hubUnlocks[handin] = true end
            end
        end
    end
    local function threshold(level) return options.xpCurve and options.xpCurve[level] or ns.xpBaseline and ns.xpBaseline[level] end
    function model.evaluate(candidate, tick)
        local result = {valid = model.structureValid and #candidate == model.size and candidate[1] == model.first and candidate[#candidate] == model.last,
            distance = 0, peakLog = model.initialLog, levelDeficitXP = 0, missingLevelCurve = 0, questXP = 0,
            unknownRewards = 0, externalPrerequisites = model.external, missingLocations = 0,
            minimumKills = 0, combatXPUnknown = 0, requiredItemsUnknown = 0, finishLevel = model.startLevel,
            uncertainTravelLegs = 0, blockedTravelLegs = 0, difficultyPressure = 0}
        local counts, seen, done, accepted, credits, log, level, xp = {}, {}, {}, {}, {}, model.initialLog, model.startLevel, model.startXP
        for index, stop in ipairs(candidate) do
            local quest = model.quests[stop.id] or {}
            if seen[stop] or model.ordinal[stop] ~= (counts[stop.id] or 0) + 1 then result.valid = false end
            seen[stop], counts[stop.id] = true, (counts[stop.id] or 0) + 1
            if index > 1 and distance then
                local length, basis = distance(candidate[index - 1], stop)
                result.distance = result.distance + length
                if basis == "unmapped-estimate" then result.uncertainTravelLegs = result.uncertainTravelLegs + 1 end
                if basis == "blocked" then result.blockedTravelLegs = result.blockedTravelLegs + 1 end
            end
            if stop.unknownLocation then result.missingLocations = result.missingLocations + 1 end
            if stop.action == "escort" and (index == 1 or candidate[index - 1] ~= model.stages[stop.id][model.ordinal[stop] - 1]) then result.valid = false end
            if stop.kind == "a" then
                accepted[stop.id] = true
                if not stop.planNeedsReview then
                    local gate = model.gates[stop.id]
                    for _, parent in ipairs(gate.all) do if not done[parent] then result.valid = false end end
                    if gate.any then
                        local met = false; for _, parent in ipairs(gate.any) do if done[parent] then met = true end end
                        if not met then result.valid = false end
                    end
                end
                log = log + 1; result.peakLog = math.max(result.peakLog, log)
                -- Quest-reward-only baseline: the shortfall is explicitly the
                -- XP still needed from kills/exploration/other work, not proof
                -- that a future pickup is currently available.
                local required = math.max(1, math.min(60, quest.minLevel or 1))
                while level < required do
                    local cap = threshold(level)
                    if not cap or cap <= 0 then result.missingLevelCurve = result.missingLevelCurve + 1; level = required; xp = 0; break end
                    result.levelDeficitXP = result.levelDeficitXP + math.max(0, cap - xp)
                    level, xp = level + 1, 0
                end
                if quest.requiredItems and #quest.requiredItems > 0 then
                    result.requiredItemsUnknown = result.requiredItemsUnknown + 1
                end
            elseif stop.kind == "t" then
                log = log - 1; done[stop.id] = true
                if type(quest.xp) == "number" and quest.xp >= 0 then
                    local difference = level - (quest.level or level)
                    local reward = math.floor(quest.xp * (difference <= 5 and 1 or math.max(0.1, 1 - (difference - 5) * 0.2)))
                    result.questXP, xp = result.questXP + reward, xp + reward
                    while level < 60 do
                        local cap = threshold(level)
                        if not cap or cap <= 0 or xp < cap then break end
                        level, xp = level + 1, xp - cap
                    end
                else result.unknownRewards = result.unknownRewards + 1 end
            end
            -- Already accepted, identical nearby kill requirements can receive
            -- the same kills even if their displayed work steps are separated.
            -- Later pickups cannot receive retroactive credit. This is a lower
            -- bound, never a drop rate or a claim about special beta conditions.
            if stop.kind == "q" then
                result.difficultyPressure = result.difficultyPressure + math.max(0, (quest.level or level) - level - 3)
                if stop.action == "kill" and stop.entityID and not stop.quantityUnknown and type(stop.quantity) == "number" then
                    local mob = stop.entityID
                    local prior = credits[stop.id] and credits[stop.id][mob] or 0
                    local kills = math.max(0, stop.quantity - prior)
                    result.minimumKills = result.minimumKills + kills
                    local credited = {}
                    for _, target in ipairs(model.killTargets[mob]) do
                        if not credited[target.id] and accepted[target.id] and not done[target.id]
                            and (target.id == stop.id or near(stop, target, 300)) then
                            credited[target.id] = true
                            credits[target.id] = credits[target.id] or {}
                            credits[target.id][mob] = (credits[target.id][mob] or 0) + kills
                        end
                    end
                end
                if stop.action == "kill" or stop.action == "collect" or stop.action == "loot" then
                    result.combatXPUnknown = result.combatXPUnknown + 1
                end
            end
            if tick then tick() end
        end
        for id, list in pairs(model.stages) do if counts[id] ~= #list then result.valid = false end end
        result.finishLevel = level
        result.finishLog, result.finishXP = log, xp
        result.initialLog, result.startXP = model.initialLog, model.startXP
        result.logCapacityKnown = type(options.logCapacity) == "number"
        result.logOverflow = result.logCapacityKnown and math.max(0, result.peakLog - options.logCapacity) or 0
        if result.logOverflow > 0 then result.valid = false end
        result.progressionNeedsReview = result.levelDeficitXP > 0 or result.missingLevelCurve > 0 or result.unknownRewards > 0
        return result
    end
    return model
end

-- Pull the complete dependency closure of later work into an existing trip.
-- This can move an unlock turn-in + pickup + cave objectives together even
-- when they are far apart in the original sequence. All endpoints/work remain.
function ns.ImproveQuestFlow(plan, distance, cooperative, onYield)
    local model = ns.NewGuideFlowModel(plan, distance)
    local work, tried, accepted = 0, 0, 0
    local function tick()
        work = work + 1
        if cooperative and work % 200 == 0 then coroutine.yield(); if onYield then onYield() end end
    end
    local baseline = model.evaluate(plan, tick)
    local current, changes = baseline, {}
    -- Tiny attachment/coordinate differences are below the useful precision
    -- of this estimated geography. Do not churn a working guide for them.
    local minimumSaving = math.max(50, baseline.distance * 0.0005)
    if not baseline.valid then return {before = baseline, after = baseline, candidates = 0, moves = 0, changes = changes} end
    local positions = {}; local function reindex() for index, stop in ipairs(plan) do positions[stop] = index end end
    reindex()
    local function changedCost(proposed)
        local nextStop, value = {}, current.distance
        for index = 2, #proposed do nextStop[proposed[index - 1]] = proposed[index] end
        for index = 2, #plan do
            local a, b = plan[index - 1], plan[index]
            if nextStop[a] ~= b then
                value = value - distance(a, b)
                if nextStop[a] then value = value + distance(a, nextStop[a]) end
            end
        end
        return value
    end
    local function candidate(targets, after, visitOnly)
        local selected, count, failed = {}, 0, false
        local function include(stop)
            local index = stop and positions[stop]
            if not index then failed = true; return end
            if index <= after or selected[stop] then return end
            if index == #plan or stop.unknownLocation or stop.planNeedsReview or count >= 24
                or visitOnly and stop.kind == "q" then failed = true; return end
            selected[stop], count = true, count + 1
            local list = model.stages[stop.id]
            for i = 1, model.ordinal[stop] - 1 do include(list[i]) end
            if stop.kind == "a" then
                local gate = model.gates[stop.id]
                for _, parent in ipairs(gate.all) do include(model.handins[parent]) end
                if gate.any then
                    local chosen
                    for _, parent in ipairs(gate.any) do
                        local handin = model.handins[parent]
                        if handin and (not chosen or positions[handin] < positions[chosen]) then chosen = handin end
                    end
                    include(chosen)
                end
            end
            local nextStop = list[model.ordinal[stop] + 1]
            if nextStop and nextStop.action == "escort" then include(nextStop) end
        end
        for _, target in ipairs(targets) do include(target) end
        if failed or count == 0 then return end
        -- Unmapped/review steps are recovery boundaries, not permission to
        -- move a known objective across a branch whose access is uncertain.
        local last, lastPickup = after, after
        for stop in pairs(selected) do
            last = math.max(last, positions[stop])
            if stop.kind == "a" then lastPickup = math.max(lastPickup, positions[stop]) end
        end
        for index = after + 1, last do
            if plan[index].unknownLocation or plan[index].planNeedsReview then return end
            -- Finish an existing nearby unlock visit before pulling unrelated
            -- pickups ahead of it. A dependency block can still carry that
            -- hand-in and its follow-up together.
            if visitOnly and index < lastPickup and not selected[plan[index]]
                and model.hubUnlocks[plan[index]] then return end
        end
        local result, block = {}, {}
        for _, stop in ipairs(plan) do if selected[stop] then block[#block + 1] = stop end end
        for index, stop in ipairs(plan) do
            if not selected[stop] then result[#result + 1] = stop end
            if index == after then for _, point in ipairs(block) do result[#result + 1] = point end end
        end
        return result, block, last
    end
    local function hubBenefitPossible(block, after, last)
        local accepts, handins = false, false
        for _, stop in ipairs(block) do
            accepts = accepts or stop.kind == "a"
            handins = handins or stop.kind == "t"
            local quest = model.quests[stop.id]
            if stop.kind == "t" and type(quest.xp) == "number" and quest.xp > 0 then return true end
        end
        -- Moving only reward-less hand-ins around other hand-ins cannot free
        -- capacity at a pickup. Moving accepts around other accepts cannot
        -- share combat credit. Avoid full replays of those equivalent visits.
        for index = after + 1, last do
            if handins and plan[index].kind == "a" or accepts and plan[index].kind == "q" then return true end
        end
        return false
    end
    -- Keep the established objective-loop pass as the baseline. A subsequent
    -- hub pass can improve progression/log space without claiming that equal
    -- walking distance alone is a faster route. Finally consider a complete
    -- overlapping trip: moving one of its quests alone can leave the second
    -- visit necessary, hiding the benefit of moving their dependency closures
    -- together. Preserve the earlier passes as this pass's baseline.
    for _, pass in ipairs({"objective", "hub", "trip"}) do
        local hubPass, tripPass = pass == "hub", pass == "trip"
        for _ = 1, 2 do
            local changed = false
            for first = 2, #plan - 1 do
                local anchor = plan[first]
                if (not hubPass and anchor.kind == "q" or hubPass and (anchor.kind == "a" or anchor.kind == "t"))
                    and not anchor.unknownLocation and not anchor.planNeedsReview and anchor.action ~= "escort" then
                    local best, bestMetrics, bestBlock
                    local considered = 0
                    local tripTargets, tripPositions = {}, {}
                    if tripPass then
                        for index = first + 2, math.min(#plan - 1, first + 128) do
                            local target = plan[index]
                            if target.kind == "q" and target.id ~= anchor.id and target.action ~= "escort"
                                and not target.unknownLocation and not target.planNeedsReview and model.near(anchor, target, 300) then
                                tripTargets[#tripTargets + 1] = target
                                tripPositions[target] = #tripTargets
                            end
                            tick()
                        end
                    end
                    for index = first + 2, math.min(#plan - 1, first + 128) do
                        local target = plan[index]
                        local sameVisit = hubPass and (target.kind == "a" or target.kind == "t")
                        if (sameVisit or not hubPass and target.kind == "q") and target.id ~= anchor.id and target.action ~= "escort"
                            and (tripPass and tripPositions[target] or not tripPass and model.near(anchor, target, hubPass and 100 or 300)) then
                            local alternatives = {{target}}
                            if tripPass then
                                alternatives = {}
                                local group, ids = {target}, {[anchor.id] = true, [target.id] = true}
                                for otherIndex = tripPositions[target] + 1, #tripTargets do
                                    local other = tripTargets[otherIndex]
                                    if not ids[other.id] then
                                        group[#group + 1], ids[other.id] = other, true
                                        local targets = {}; for _, point in ipairs(group) do targets[#targets + 1] = point end
                                        alternatives[#alternatives + 1] = targets
                                        if #group == 3 then break end
                                    end
                                    tick()
                                end
                            end
                            for _, targets in ipairs(alternatives) do
                                local proposed, block, last = candidate(targets, first - 1, hubPass)
                                if proposed then
                                    tried, considered = tried + 1, considered + 1
                                    local reference = bestMetrics or current
                                    local estimate = changedCost(proposed)
                                    local sharedKills = anchor.action == "kill" and target.action == "kill" and anchor.entityID == target.entityID
                                        and type(anchor.quantity) == "number" and type(target.quantity) == "number"
                                        and not anchor.quantityUnknown and not target.quantityUnknown
                                    -- Zero-length and already bundled candidates do
                                    -- not need a full state replay. This keeps large
                                    -- same-hub guides cooperative without timer churn.
                                    local worthwhile = estimate <= current.distance - minimumSaving
                                        or (sharedKills or hubPass and hubBenefitPossible(block, first - 1, last))
                                            and estimate <= current.distance + 0.001
                                    local value = worthwhile and (estimate < reference.distance - 0.001 or (sharedKills or hubPass) and estimate <= reference.distance + 0.001)
                                        and model.evaluate(proposed, tick)
                                    local progression = value and (value.peakLog < current.peakLog
                                        or value.levelDeficitXP < current.levelDeficitXP or value.difficultyPressure < current.difficultyPressure
                                        or value.questXP > current.questXP)
                                    if value and value.valid and value.peakLog <= current.peakLog
                                        and value.levelDeficitXP <= current.levelDeficitXP and value.missingLevelCurve <= current.missingLevelCurve
                                        and value.questXP >= current.questXP and value.minimumKills <= current.minimumKills
                                        and value.difficultyPressure <= current.difficultyPressure
                                        and value.uncertainTravelLegs <= current.uncertainTravelLegs and value.blockedTravelLegs <= current.blockedTravelLegs
                                        and (value.distance <= current.distance - minimumSaving or value.minimumKills < current.minimumKills
                                            or hubPass and progression)
                                        and (value.distance < reference.distance - 0.001
                                            or math.abs(value.distance - reference.distance) <= 0.001
                                                and (value.minimumKills < reference.minimumKills or hubPass and progression)) then
                                        best, bestMetrics, bestBlock = proposed, value, block
                                    end
                                end
                                if considered >= 8 then break end
                            end
                            if considered >= 8 then break end
                        end
                        tick()
                    end
                    if best then
                        local ids, seen = {}, {}
                        for _, stop in ipairs(bestBlock) do if not seen[stop.id] then ids[#ids + 1], seen[stop.id] = stop.id, true end end
                        changes[#changes + 1] = {questIDs = ids, nearQuestID = anchor.id, travelSaved = current.distance - bestMetrics.distance,
                            killsSaved = current.minimumKills - bestMetrics.minimumKills, actions = #bestBlock,
                            kind = hubPass and "hub-progression" or tripPass and "objective-trip" or "objective-loop", logPeakReduced = current.peakLog - bestMetrics.peakLog,
                            levelDeficitReduced = current.levelDeficitXP - bestMetrics.levelDeficitXP,
                            difficultyReduced = current.difficultyPressure - bestMetrics.difficultyPressure,
                            rewardXPGained = bestMetrics.questXP - current.questXP}
                        for _, stop in ipairs(bestBlock) do
                            if hubPass and stop.kind == "t" and model.near(stop, anchor, 100) then
                                if bestMetrics.levelDeficitXP < current.levelDeficitXP or bestMetrics.difficultyPressure < current.difficultyPressure then
                                    stop.flowRewardFirst = true
                                elseif bestMetrics.peakLog < current.peakLog then stop.flowLogSpace = true end
                            end
                            if stop.kind == "q" and stop.id ~= anchor.id and model.near(stop, anchor, 300) then
                                stop.flowWithQuestID, anchor.flowWithQuestID = anchor.id, stop.id
                                local pickup = model.pickups[stop.id]
                                if pickup then pickup.flowWithQuestID = anchor.id end
                                local gate = model.gates[stop.id]
                                for _, parent in ipairs(gate.all) do
                                    local handin = model.handins[parent]
                                    if handin then handin.flowUnlockQuestID, handin.flowWithQuestID = stop.id, anchor.id end
                                end
                            end
                        end
                        for index, stop in ipairs(best) do plan[index] = stop end
                        current, accepted, changed = bestMetrics, accepted + 1, true; reindex()
                    end
                end
            end
            if not changed then break end
        end
    end
    return {before = baseline, after = current, candidates = tried, moves = accepted, changes = changes}
end
