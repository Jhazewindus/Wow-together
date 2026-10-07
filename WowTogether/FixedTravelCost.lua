local addonName, ns = ...

-- Reuse the published travel graph for complete-guide comparisons. Personal
-- flights/hearths/mounts never enter a generic plan. Local attachments and
-- uncovered roads remain estimates; transport weights are published estimates.
function ns.NewFixedTravelCost(fallback, cooperative, onYield)
    local policy = {faction = ns.profile and ns.profile.faction, safety = ns.TravelSafetyContext(), metrics = {}}
    local nearest, memo, count = {}, {}, 0
    local work = 0
    local function tick()
        work = work + 1
        if cooperative and work % 100 == 0 then coroutine.yield(); if onYield then onYield() end end
    end
    policy.tick = tick
    local maps = {}
    for id, point in pairs(ns.travelData and ns.travelData.nodes or {}) do
        if ns.ValidTravelPoint(point) and ns.TravelNodeAllowed(id, point, nil, policy.safety)
            and not (point.container and (string.find(point.container, "wizards_sanctum", 1, true)
                or string.find(point.container, "blackrock_mountain", 1, true))) then
            maps[point.mapID] = maps[point.mapID] or {}
            maps[point.mapID][#maps[point.mapID] + 1] = {id = id, point = point}
        end
    end
    for _, list in pairs(maps) do table.sort(list, function(a, b) return a.id < b.id end) end
    local function anchors(point)
        if nearest[point] then return nearest[point] end
        local result = {}
        for _, node in ipairs(maps[point.mapID] or {}) do
            if not ns.HostileWalkCrossing(point, node.point, policy.safety, true, false) then
                local length = fallback(point, node.point)
                if length <= 1500 then
                    local index = #result + 1
                    for i, old in ipairs(result) do if length < old.cost then index = i; break end end
                    table.insert(result, index, {id = node.id, cost = length * 1.25})
                    if #result > 3 then table.remove(result) end
                end
            end
            tick()
        end
        nearest[point] = result
        return result
    end
    local function distance(a, b)
        if a and a.unknownLocation or b.unknownLocation or not ns.ValidTravelPoint(a) or not ns.ValidTravelPoint(b) then
            return fallback(a, b), "unmapped-estimate"
        end
        if memo[a] and memo[a][b] then return unpack(memo[a][b]) end
        local sameMap = a.mapID == b.mapID
        local direct = fallback(a, b)
        local blocked = ns.HostileWalkCrossing(a, b, policy.safety, true, true)
        local best, basis
        if sameMap and not blocked and direct <= 400 then best, basis = direct, "local-estimate"
        else
            for _, from in ipairs(anchors(a)) do
                for _, to in ipairs(anchors(b)) do
                    local road = ns.PublishedTravelDistance(from.id, to.id, policy)
                    local value = road and from.cost + road + to.cost
                    if value and (not best or value < best) then best, basis = value, "network-estimate" end
                end
            end
            if sameMap and not blocked and best then best = math.max(best, direct) end
        end
        if not best then best, basis = math.max(direct, blocked and 20000 or 0), blocked and "blocked" or "unmapped-estimate" end
        if count >= 4096 then memo, count = {}, 0 end
        memo[a] = memo[a] or {}; memo[a][b] = {best, basis}; count = count + 1
        return best, basis
    end
    local function reset()
        nearest, memo, count = {}, {}, 0
        policy.metrics = {}
    end
    return distance, reset
end
