local addonName, ns = ...

-- Improve the immutable catalogue route, preserving per-quest stages and
-- hand-in prerequisites. Only shorter, close-level relocations are accepted.
-- This is a bounded local search, not a claim of a terrain-optimal route.
local function optimizeSteps(plan, distance, cooperative, onYield, guard)
    local stages, pickups, handins, positions, work = {}, {}, {}, {}, 0
    for index, stop in ipairs(plan) do
        positions[stop] = index
        stages[stop.id] = stages[stop.id] or {}; stages[stop.id][#stages[stop.id] + 1] = stop
        if stop.kind == "a" then pickups[stop.id] = stop end
        if stop.kind == "t" then handins[stop.id] = stop end
    end
    local neighbors, children, gates = {}, {}, {}
    for id, list in pairs(stages) do
        for index, stop in ipairs(list) do neighbors[stop] = {before = list[index - 1], after = list[index + 1]} end
        local quest = ns.CatalogueQuest(id) or {}
        gates[id] = {any = quest.prerequisiteAny, all = {}}
        for _, previous in ipairs(quest.prerequisiteAll or {}) do gates[id].all[#gates[id].all + 1] = previous end
        if quest.previousQuest then gates[id].all[#gates[id].all + 1] = quest.previousQuest
        elseif not quest.prerequisiteAny and not quest.prerequisiteAll then gates[id].all = ns.LearnedPrerequisiteIDs(id) end
        local parents = {}; for _, previous in ipairs(gates[id].all) do parents[#parents + 1] = previous end
        for _, previous in ipairs(quest.prerequisiteAny or {}) do parents[#parents + 1] = previous end
        for _, previous in ipairs(parents) do
            children[previous] = children[previous] or {}; children[previous][#children[previous] + 1] = id
        end
    end
    -- Retain the compiler's useful NPC hand-off bundles: turning in a parent
    -- before gathering nearby new quests is part of the plan's purpose.
    local hubs = {}
    for _, list in pairs(stages) do
        for index = 2, #list do
            if list[index].action == "escort" then
                hubs[#hubs + 1] = {before = list[index - 1], after = list[index], adjacent = true}
            end
        end
    end
    for parent, list in pairs(children) do
        local handin = handins[parent]
        if handin and not handin.unknownLocation then
            local unlocks = false
            for _, id in ipairs(list) do
                local pickup = pickups[id]
                if pickup and not pickup.unknownLocation and pickup.mapID == handin.mapID
                    and ns.NormalizedDistance(pickup, handin) <= 0.015 then unlocks = true; break end
            end
            if unlocks then
                for _, pickup in pairs(pickups) do
                    if positions[pickup] > positions[handin] and not pickup.unknownLocation and pickup.mapID == handin.mapID
                        and ns.NormalizedDistance(pickup, handin) <= 0.015 then
                        hubs[#hubs + 1] = {before = handin, after = pickup}
                    end
                end
            end
        end
    end
    local function cost()
        local value = 0
        for index = 2, #plan do value = value + distance(plan[index - 1], plan[index]) end
        return value
    end
    local before, moved = cost(), 0
    local function proposal(first, last, after)
        if not guard then return true end
        local result, block = {}, {}
        for index = first, last do block[#block + 1] = plan[index] end
        for index, point in ipairs(plan) do
            if index < first or index > last then result[#result + 1] = point end
            if index == after then for _, stop in ipairs(block) do result[#result + 1] = stop end end
        end
        return guard.check(result) and result
    end
    local function valid(stop, from, after)
        local target = after < from and after + 1 or after
        local function pos(other)
            if not other then return nil end
            local index = positions[other]
            if index == from then return target end
            if target < from and index >= target and index < from then return index + 1 end
            if target > from and index > from and index <= target then return index - 1 end
            return index
        end
        local links, p = neighbors[stop], target
        if links.before and pos(links.before) >= p or links.after and pos(links.after) <= p then return false end
        local function allowed(id)
            local pickup, gate = pickups[id], gates[id]
            if not pickup or not gate then return true end
            for _, parent in ipairs(gate.all) do
                if not handins[parent] or pos(handins[parent]) >= pos(pickup) then return false end
            end
            if gate.any then
                for _, parent in ipairs(gate.any) do
                    if handins[parent] and pos(handins[parent]) < pos(pickup) then return true end
                end
                return false
            end
            return true
        end
        if stop.kind == "a" and not allowed(stop.id) then return false end
        if stop.kind == "t" then
            for _, child in ipairs(children[stop.id] or {}) do if not allowed(child) then return false end end
        end
        for _, hub in ipairs(hubs) do
            if hub.adjacent then
                if pos(hub.after) ~= pos(hub.before) + 1 then return false end
            elseif (hub.before == stop or hub.after == stop) and pos(hub.before) >= pos(hub.after) then return false end
        end
        return true
    end
    for _ = 1, 2 do
        local changed = false
        for index = 2, #plan - 1 do
            local stop, best, saving, bestPlan = plan[index], nil, 0, nil
            if not stop.planNeedsReview and not stop.unknownLocation then
                local oldCost = distance(plan[index - 1], stop) + distance(stop, plan[index + 1])
                    - distance(plan[index - 1], plan[index + 1])
                local level = (ns.CatalogueQuest(stop.id) or {}).level or 0
                for after = math.max(1, index - 24), math.min(#plan - 1, index + 24) do
                    local anchor, nextStop = plan[after], plan[after + 1]
                    local otherLevel = (ns.CatalogueQuest(anchor.id) or {}).level or 0
                    if after ~= index and after ~= index - 1 and not anchor.planNeedsReview and not nextStop.planNeedsReview
                        and not anchor.unknownLocation and not nextStop.unknownLocation
                        and math.abs(level - otherLevel) <= 2 and valid(stop, index, after) then
                        local delta = oldCost - distance(anchor, stop) - distance(stop, nextStop) + distance(anchor, nextStop)
                        if delta > saving + 0.001 then
                            local proposed = proposal(index, index, after)
                            if proposed then best, saving, bestPlan = after, delta, proposed end
                        end
                    end
                    work = work + 1
                    if cooperative and work % 200 == 0 then
                        coroutine.yield(); if onYield then onYield() end
                    end
                end
            end
            if best then
                table.remove(plan, index)
                table.insert(plan, best < index and best + 1 or best, stop)
                for i = math.min(index, best), math.max(index, best) + 1 do if plan[i] then positions[plan[i]] = i end end
                moved, changed = moved + 1, true
                if guard then guard.commit(bestPlan, {stop}, "network-step") end
            end
        end
        if not changed then break end
    end
    -- Move short nearby bundles together. A single-step search cannot move
    -- an escort pickup/work pair or a dependency-locked hub hand-off intact.
    local function validBlock(first, last, after)
        local size = last - first + 1
        local target = after < first and after + 1 or after - size + 1
        local function pos(stop)
            local index = positions[stop]
            if index >= first and index <= last then return target + index - first end
            if target < first and index >= target and index < first then return index + size end
            if target > first and index > last and index <= after then return index - size end
            return index
        end
        for _, list in pairs(stages) do
            for index = 2, #list do if pos(list[index - 1]) >= pos(list[index]) then return false end end
        end
        for id, pickup in pairs(pickups) do
            local gate = gates[id]
            if not pickup.planNeedsReview then
                for _, parent in ipairs(gate.all) do
                    if not handins[parent] or pos(handins[parent]) >= pos(pickup) then return false end
                end
                if gate.any then
                    local okay = false
                    for _, parent in ipairs(gate.any) do if handins[parent] and pos(handins[parent]) < pos(pickup) then okay = true; break end end
                    if not okay then return false end
                end
            end
        end
        for _, hub in ipairs(hubs) do
            if pos(hub.before) >= pos(hub.after) or hub.adjacent and pos(hub.after) ~= pos(hub.before) + 1 then return false end
        end
        return true
    end
    local bundles = 0
    for _ = 1, 2 do
        local changed = false
        for first = 2, #plan - 2 do
            local best, saving, stop, bestPlan = nil, 0, plan[first], nil
            local level = (ns.CatalogueQuest(stop.id) or {}).level or 0
            -- Same-hub pickup/hand-in runs can be larger than an escort pair.
            -- Keep mixed-action bundles bounded at four; larger runs must be
            -- one visit type with every point within 150 yards of its anchor.
            local sizes, largeSize = {2, 3, 4}, nil
            if stop.kind == "a" or stop.kind == "t" then
                for index = first, math.min(first + 7, #plan - 1) do
                    local point = plan[index]
                    local other = (ns.CatalogueQuest(point.id) or {}).level or 0
                    if point.unknownLocation or point.planNeedsReview or point.mapID ~= stop.mapID
                        or point.kind ~= stop.kind or math.abs(other - level) > 2
                        or distance(stop, point) > 150 then break end
                    if index - first + 1 > 4 then largeSize = index - first + 1 end
                end
            end
            -- Evaluate the largest homogeneous visit once, rather than every
            -- overlapping prefix. Small mixed/escort bundles retain their search.
            if largeSize then sizes[#sizes + 1] = largeSize end
            for _, size in ipairs(sizes) do
                if size > #plan - first then break end
                local last, localBundle = first + size - 1, true
                for index = first, last do
                    local point = plan[index]
                    local other = (ns.CatalogueQuest(point.id) or {}).level or 0
                    if point.unknownLocation or point.planNeedsReview or point.mapID ~= stop.mapID
                        or math.abs(other - level) > 2 or distance(stop, point) > 300
                        or size > 4 and (stop.kind ~= "a" and stop.kind ~= "t" or point.kind ~= stop.kind
                            or distance(stop, point) > 150) then localBundle = false; break end
                end
                if localBundle then
                    local old = distance(plan[first - 1], stop) + distance(plan[last], plan[last + 1])
                        - distance(plan[first - 1], plan[last + 1])
                    for after = math.max(1, first - 32), math.min(#plan - 1, last + 32) do
                        if after < first - 1 or after > last then
                            local anchor, nextStop = plan[after], plan[after + 1]
                            local other = (ns.CatalogueQuest(anchor.id) or {}).level or 0
                            if not anchor.unknownLocation and not nextStop.unknownLocation and not anchor.planNeedsReview
                                and not nextStop.planNeedsReview and math.abs(other - level) <= 2 then
                                local delta = old - distance(anchor, stop) - distance(plan[last], nextStop) + distance(anchor, nextStop)
                                if delta > saving + 0.001 and validBlock(first, last, after) then
                                    local proposed = proposal(first, last, after)
                                    if proposed then best, saving, bestPlan = {last = last, after = after}, delta, proposed end
                                end
                            end
                        end
                        work = work + 1
                        if cooperative and work % 200 == 0 then coroutine.yield(); if onYield then onYield() end end
                    end
                end
            end
            if best then
                local block = {}
                for index = first, best.last do block[#block + 1] = plan[index] end
                for _ = first, best.last do table.remove(plan, first) end
                local target = best.after < first and best.after + 1 or best.after - #block + 1
                for index, point in ipairs(block) do table.insert(plan, target + index - 1, point) end
                for index, point in ipairs(plan) do positions[point] = index end
                bundles, changed = bundles + 1, true
                if guard then guard.commit(bestPlan, block, "network-bundle") end
            end
        end
        if not changed then break end
    end
    return {before = before, after = cost(), moved = moved, bundles = bundles}
end

-- Compare graph-aware alternatives against the established complete flow.
-- Reuse the same bounded step/bundle search; no runtime/player transport is
-- assumed. Changed legs need published connections or short local estimates.
-- Every accepted move keeps reward/progression/log/kill and recovery guards.
function ns.ImproveFixedTravelOrder(plan, distance, cooperative, onYield, options)
    local work, tried = 0, 0
    local function tick()
        work = work + 1
        -- These are cheap region/edge/replay operations. Graph expansion and
        -- the step search retain their own finer yields; do not schedule a
        -- timer for every tiny table scan in the additional guard.
        if cooperative and work % 1000 == 0 then coroutine.yield(); if onYield then onYield() end end
    end
    local model = ns.NewGuideFlowModel(plan, distance)
    local current = model.evaluate(plan, tick)
    local result = {before = current, after = current, candidates = 0, moves = 0, changes = {}}
    if not current.valid then return result end
    local hasNetwork = false
    for index = 2, #plan do
        local _, basis = distance(plan[index - 1], plan[index])
        if basis == "network-estimate" then hasNetwork = true; break end
        tick()
    end
    if not hasNetwork then return result end
    local minimumSaving = math.max(50, current.distance * 0.0005)
    local regions, region = {}, 0
    for _, stop in ipairs(plan) do
        if stop.unknownLocation or stop.planNeedsReview then region = region + 1 end
        regions[stop] = region
    end
    local function preserves(before, after)
        if not after.valid or after.questXP < before.questXP then return false end
        for _, field in ipairs({"peakLog", "levelDeficitXP", "minimumKills", "difficultyPressure",
            "missingLevelCurve", "uncertainTravelLegs", "blockedTravelLegs"}) do
            if after[field] > before[field] then return false end
        end
        for stop, reward in pairs(before.workRewards) do if after.workRewards[stop] < reward then return false end end
        return true
    end
    local replays, states, pending = nil, nil, setmetatable({}, {__mode = "k"})
    local guard = {}
    function guard.check(proposed)
        tried = tried + 1
        -- A known point cannot cross an uncertain branch just because the
        -- candidate's two attachment endpoints happen to be mapped.
        local nextStop, seenRegion = {}, 0
        for index, stop in ipairs(proposed) do
            if stop.unknownLocation or stop.planNeedsReview then seenRegion = seenRegion + 1 end
            if regions[stop] ~= seenRegion then return false end
            if index > 1 then nextStop[proposed[index - 1]] = stop end
            tick()
        end
        local estimate, network = current.distance, false
        for index = 2, #plan do
            local a, b = plan[index - 1], plan[index]
            if nextStop[a] ~= b then
                local old, oldBasis = distance(a, b)
                local new, newBasis = distance(a, nextStop[a])
                if (oldBasis ~= "local-estimate" and oldBasis ~= "network-estimate")
                    or (newBasis ~= "local-estimate" and newBasis ~= "network-estimate") then return false end
                network = network or oldBasis == "network-estimate" or newBasis == "network-estimate"
                estimate = estimate - old + new
            end
            tick()
        end
        if not network or current.distance - estimate < minimumSaving then return false end
        local value = model.evaluate(proposed, tick)
        if not preserves(current, value) or current.distance - value.distance < minimumSaving then return false end
        if not replays then
            replays, states = {}, {}
            if options and options.levelLow and options.levelHigh then
                local low, high = math.max(1, options.levelLow), math.min(60, options.levelHigh)
                local middle = math.floor((low + high) / 2)
                local cap = ns.xpBaseline and ns.xpBaseline[middle]
                local seen = {}
                for _, state in ipairs({{low, 0}, {middle, 0}, {high, 0}, {middle, cap and math.floor(cap / 2) or 0}}) do
                    local key = state[1] .. ":" .. state[2]
                    if not seen[key] then
                        seen[key] = true
                        local replay = ns.NewGuideFlowModel(plan, nil, {startLevel = state[1], startXP = state[2]})
                        replays[#replays + 1], states[#states + 1] = replay, replay.evaluate(plan, tick)
                    end
                end
            end
        end
        local progress = {}
        for index, replay in ipairs(replays) do
            local value = replay.evaluate(proposed, tick)
            if not preserves(states[index], value) then return false end
            progress[index] = value
        end
        -- Keep replays for proposals still held by the bounded search. Weak
        -- keys release discarded alternatives rather than retaining them all.
        pending[proposed] = {value = value, progress = progress}
        return true
    end
    function guard.commit(proposed, block, kind)
        local value = pending[proposed]
        local ids, seen = {}, {}
        for _, stop in ipairs(block) do if not seen[stop.id] then ids[#ids + 1], seen[stop.id] = stop.id, true end end
        result.changes[#result.changes + 1] = {kind = kind, questIDs = ids, actions = #block,
            travelSaved = current.distance - value.value.distance,
            rewardBeforeWorkGained = value.value.rewardXPBeforeWork - current.rewardXPBeforeWork}
        current, states, pending = value.value, value.progress, setmetatable({}, {__mode = "k"})
    end
    local searched = optimizeSteps(plan, distance, cooperative, onYield, guard)
    result.after, result.candidates = current, tried
    result.moves, result.steps, result.bundles = searched.moved + searched.bundles, searched.moved, searched.bundles
    return result
end

-- Geometry is only a proposal generator. Corrected NPC/object points must not
-- let this first pass delay rewards or grow the log before the later guards
-- begin. Evaluate the entire journey with the same current facts and prices.
function ns.ImproveFixedGeometry(plan, geometry, cost, cooperative, onYield, options)
    cost = cost or geometry
    local model = ns.NewGuideFlowModel(plan, cost)
    local current = model.evaluate(plan)
    local initial, work = current, 0
    local regions, region = {}, 0
    for _, stop in ipairs(plan) do
        if stop.unknownLocation or stop.planNeedsReview then region = region + 1 end
        regions[stop] = region
    end
    local function tick()
        work = work + 1
        if cooperative and work % 1000 == 0 then coroutine.yield(); if onYield then onYield() end end
    end
    local function preserves(before, after)
        if not after.valid or after.distance > before.distance + .001 or after.questXP < before.questXP then return false end
        for _, field in ipairs({"peakLog", "levelDeficitXP", "minimumKills", "difficultyPressure",
            "missingLevelCurve", "uncertainTravelLegs", "blockedTravelLegs"}) do
            if after[field] > before[field] then return false end
        end
        for stop, reward in pairs(before.workRewards) do if after.workRewards[stop] < reward then return false end end
        return true
    end
    local replays, states = {}, {}
    if options and options.levelLow and options.levelHigh then
        local low, high = math.max(1, options.levelLow), math.min(60, options.levelHigh)
        local middle = math.floor((low + high) / 2)
        local cap, seen = ns.xpBaseline and ns.xpBaseline[middle], {}
        for _, state in ipairs({{low, 0}, {middle, 0}, {high, 0}, {middle, cap and math.floor(cap / 2) or 0}}) do
            local key = state[1] .. ":" .. state[2]
            if not seen[key] then
                seen[key] = true
                local replay = ns.NewGuideFlowModel(plan, nil, {startLevel = state[1], startXP = state[2]})
                replays[#replays + 1], states[#states + 1] = replay, replay.evaluate(plan, tick)
            end
        end
    end
    local pending, rejected = setmetatable({}, {__mode = "k"}), 0
    local guard = {}
    function guard.check(proposed)
        local nextRegion = 0
        for _, stop in ipairs(proposed) do
            if stop.unknownLocation or stop.planNeedsReview then nextRegion = nextRegion + 1 end
            if regions[stop] ~= nextRegion then rejected = rejected + 1; return false end
            tick()
        end
        local value = model.evaluate(proposed, tick)
        if not preserves(current, value) then rejected = rejected + 1; return false end
        local progress = {}
        for index, replay in ipairs(replays) do
            local nextValue = replay.evaluate(proposed, tick)
            if not preserves(states[index], nextValue) then rejected = rejected + 1; return false end
            progress[index] = nextValue
        end
        pending[proposed] = {value, progress}
        return true
    end
    function guard.commit(proposed)
        current, states = pending[proposed][1], pending[proposed][2]
        pending = setmetatable({}, {__mode = "k"})
    end
    local before = 0
    for index = 2, #plan do before = before + geometry(plan[index - 1], plan[index]); tick() end
    local result = current.valid and optimizeSteps(plan, geometry, cooperative, onYield, guard)
        or {before = before, after = before, moved = 0, bundles = 0}
    result.protection = {before = initial, after = current, rejected = rejected, replayStates = #states}
    return result
end

function ns.OptimizeFixedPlan(plan, distance, cooperative, onYield, flowDistance, flowOptions, terrainDistance, connectionDistance)
    local legacy = ns.ImproveFixedGeometry(plan, distance, flowDistance, cooperative, onYield, flowOptions)
    local flow = ns.ImproveQuestFlow(plan, flowDistance or distance, cooperative, onYield, flowOptions)
    local network = flowDistance and ns.ImproveFixedTravelOrder(plan, flowDistance, cooperative, onYield, flowOptions)
    -- Repricing the original greedy route can discard useful established
    -- reward visits. Start with that full flow, then guard each terrain-aware
    -- change against the same rewards, progression and required action set.
    local function comparePrices(priorDistance, nextDistance)
        if not priorDistance or not nextDistance then return end
        local changed = false
        for index = 2, #plan do
            local old, oldBasis = priorDistance(plan[index - 1], plan[index])
            local new, newBasis = nextDistance(plan[index - 1], plan[index])
            if math.abs(old - new) > 0.001 or oldBasis ~= newBasis then changed = true; break end
        end
        if changed then return ns.ImproveFixedTravelOrder(plan, nextDistance, cooperative, onYield, flowOptions) end
    end
    local terrain = comparePrices(flowDistance, terrainDistance)
    -- Corrected connection prices start from the complete established guide,
    -- including its terrain-aware reward visits. A better attachment alone
    -- must not discard rewards or turn the greedy seed into a worse journey.
    local connections = comparePrices(terrainDistance or flowDistance, connectionDistance)
    return {before = connections and connections.before.distance or terrain and terrain.before.distance or flowDistance and flow.before.distance or legacy.before,
        after = connections and connections.after.distance or terrain and terrain.after.distance or network and network.after.distance or flow.after.distance,
        legacyBefore = legacy.before, legacyAfter = legacy.after,
        moved = legacy.moved, bundles = legacy.bundles, geometricGuard = legacy.protection,
        flow = flow, network = network, terrain = terrain, connections = connections,
        heuristic = "Dependency-preserving step, bundle and quest-flow search"}
end
