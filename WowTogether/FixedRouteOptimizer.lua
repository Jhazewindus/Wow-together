local addonName, ns = ...

-- Improve the immutable catalogue route, preserving per-quest stages and
-- hand-in prerequisites. Only shorter, close-level relocations are accepted.
-- This is a bounded local search, not a claim of a terrain-optimal route.
function ns.OptimizeFixedPlan(plan, distance, cooperative, onYield)
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
            local stop, best, saving = plan[index], nil, 0
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
                        if delta > saving + 0.001 then best, saving = after, delta end
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
            local best, saving, stop = nil, 0, plan[first]
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
                                if delta > saving + 0.001 and validBlock(first, last, after) then best, saving = {last = last, after = after}, delta end
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
            end
        end
        if not changed then break end
    end
    return {before = before, after = cost(), moved = moved, bundles = bundles, heuristic = "Dependency-preserving step and bundle search"}
end
