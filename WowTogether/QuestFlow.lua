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
    local function near(a, b, radius)
        return a and b and not a.unknownLocation and not b.unknownLocation and a.mapID == b.mapID
            and ns.ValidTravelPoint(a) and ns.ValidTravelPoint(b)
            and (distance and distance(a, b) or ns.WalkingDistance(a.mapID, a, b)
                or ns.NormalizedDistance(a, b) * 6000) <= radius
    end
    model.near = near
    local function threshold(level) return options.xpCurve and options.xpCurve[level] or ns.xpBaseline and ns.xpBaseline[level] end
    function model.evaluate(candidate, tick)
        local result = {valid = model.structureValid and #candidate == model.size and candidate[1] == model.first and candidate[#candidate] == model.last,
            distance = 0, peakLog = 0, levelDeficitXP = 0, missingLevelCurve = 0, questXP = 0,
            unknownRewards = 0, externalPrerequisites = model.external, missingLocations = 0,
            minimumKills = 0, combatXPUnknown = 0, requiredItemsUnknown = 0, finishLevel = model.startLevel,
            uncertainTravelLegs = 0, blockedTravelLegs = 0, difficultyPressure = 0}
        local counts, seen, done, accepted, credits, log, level, xp = {}, {}, {}, {}, {}, 0, model.startLevel, 0
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
    local function candidate(target, after)
        local selected, count, failed = {}, 0, false
        local function include(stop)
            local index = stop and positions[stop]
            if not index then failed = true; return end
            if index <= after or selected[stop] then return end
            if index == #plan or stop.unknownLocation or stop.planNeedsReview or count >= 24 then failed = true; return end
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
        include(target)
        if failed or count == 0 then return end
        -- Unmapped/review steps are recovery boundaries, not permission to
        -- move a known objective across a branch whose access is uncertain.
        local last = after
        for stop in pairs(selected) do last = math.max(last, positions[stop]) end
        for index = after + 1, last do
            if plan[index].unknownLocation or plan[index].planNeedsReview then return end
        end
        local result, block = {}, {}
        for _, stop in ipairs(plan) do if selected[stop] then block[#block + 1] = stop end end
        for index, stop in ipairs(plan) do
            if not selected[stop] then result[#result + 1] = stop end
            if index == after then for _, point in ipairs(block) do result[#result + 1] = point end end
        end
        return result, block
    end
    for _ = 1, 2 do
        local changed = false
        for first = 2, #plan - 1 do
            local anchor = plan[first]
            if anchor.kind == "q" and not anchor.unknownLocation and not anchor.planNeedsReview and anchor.action ~= "escort" then
                local best, bestMetrics, bestBlock
                local considered = 0
                for index = first + 2, math.min(#plan - 1, first + 128) do
                    local target = plan[index]
                    if target.kind == "q" and target.id ~= anchor.id and target.action ~= "escort"
                        and model.near(anchor, target, 300) then
                        local proposed, block = candidate(target, first - 1)
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
                            local worthwhile = estimate <= current.distance - minimumSaving or sharedKills and estimate <= current.distance + 0.001
                            local value = worthwhile and (estimate < reference.distance - 0.001 or sharedKills and estimate <= reference.distance + 0.001)
                                and model.evaluate(proposed, tick)
                            if value and value.valid and value.peakLog <= current.peakLog
                                and value.levelDeficitXP <= current.levelDeficitXP and value.missingLevelCurve <= current.missingLevelCurve
                                and value.questXP >= current.questXP and value.minimumKills <= current.minimumKills
                                and value.difficultyPressure <= current.difficultyPressure
                                and value.uncertainTravelLegs <= current.uncertainTravelLegs and value.blockedTravelLegs <= current.blockedTravelLegs
                                and (value.distance < reference.distance - 0.001
                                    or math.abs(value.distance - reference.distance) <= 0.001 and value.minimumKills < reference.minimumKills) then
                                best, bestMetrics, bestBlock = proposed, value, block
                            end
                        end
                        if considered >= 8 then break end
                    end
                    tick()
                end
                if best then
                    local ids, seen = {}, {}
                    for _, stop in ipairs(bestBlock) do if not seen[stop.id] then ids[#ids + 1], seen[stop.id] = stop.id, true end end
                    changes[#changes + 1] = {questIDs = ids, nearQuestID = anchor.id, travelSaved = current.distance - bestMetrics.distance,
                        killsSaved = current.minimumKills - bestMetrics.minimumKills, actions = #bestBlock}
                    for _, stop in ipairs(bestBlock) do
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
    return {before = baseline, after = current, candidates = tried, moves = accepted, changes = changes}
end
