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
        if quest.previousQuest then gates[id].all[#gates[id].all + 1] = quest.previousQuest
        elseif not quest.prerequisiteAny then gates[id].all = ns.LearnedPrerequisiteIDs(id) end
        for _, previous in ipairs(quest.prerequisiteAny or gates[id].all) do
            children[previous] = children[previous] or {}; children[previous][#children[previous] + 1] = id
        end
    end
    -- Retain the compiler's useful NPC hand-off bundles: turning in a parent
    -- before gathering nearby new quests is part of the plan's purpose.
    local hubs = {}
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
            if (hub.before == stop or hub.after == stop) and pos(hub.before) >= pos(hub.after) then return false end
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
    return {before = before, after = cost(), moved = moved, heuristic = "Dependency-preserving local search"}
end
