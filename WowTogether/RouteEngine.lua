local addonName, ns = ...

-- The route engine.
--
-- One function turns a set of spots into the loop with the least walking:
-- ns.PlanLoop(points, options). Every farm goes through it (creature spawn
-- points, ore veins, herbs, fishing pools), because every loop a module
-- starts is planned here. It does four things, in order:
--
--   1. CHOOSE. A loop holds a limited number of stops and a zone may have
--      many more spots than that. The engine keeps the ones that lie closest
--      together: it finds the spot whose nearest neighbours are nearest,
--      then keeps adding whichever remaining spot is closest to the group.
--      A spot may carry a `value` (how much it is worth); a valuable spot
--      counts as closer, so a rich vein a little out of the way still makes
--      the loop.
--   2. ORDER. The chosen stops are put in the order with the least walking:
--      the true shortest tour for ten stops or fewer, and a nearest-neighbour
--      tour with its crossings removed above that (ns.TrailLoop).
--   3. START. The loop is turned so that it begins at the stop nearest to
--      where the player is standing, if they are in that zone.
--   4. MEASURE. The plan says how far a lap is and how long it takes on
--      foot, so a farm can say so before it is started.
--
-- SIZING. How many stops is the right number? A spot that has been
-- harvested takes a while to come back. Walk a loop that is shorter than
-- that and the spots are still empty when you return; walk one that is much
-- longer and you spend the extra time on the road for nothing. So when the
-- caller says how long a spot takes to come back (`respawn`) and how long a
-- stop takes to work (`harvestSeconds`), the engine tries every size from a
-- few stops up to the limit and keeps the one with the most harvests an
-- hour:  stops / max(lap time, respawn).  Below the respawn time more stops
-- are free; above it each added stop has to be worth its walk.
--
-- What it cannot do: see the ground. An addon has no terrain, so distance is
-- the straight line between two spots, measured in yards with the zone's real
-- proportions. A cliff or a lake between two stops is not known to it. Where
-- the player's own play shows a spot is not worth visiting, that is for the
-- caller to act on, by leaving the spot out or lowering its value.

local MAX_INPUT, MAX_STOPS = 80, 24
local RUN_YARDS_PER_SECOND = 7

local function finite(value) return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge end

-- Which `limit` of the points to keep. `gap(i, j)` is the distance in yards.
local function choose(points, limit, gap)
    local count = #points
    if count <= limit then
        local all = {}
        for index = 1, count do all[index] = index end
        return all
    end
    -- A valuable spot is treated as nearer: its distances shrink with its worth.
    local weight = {}
    for index = 1, count do
        local value = points[index].value
        weight[index] = finite(value) and value > 0 and 1 / math.sqrt(math.min(value, 100)) or 1
    end
    local function near(i, j) return gap(i, j) * weight[j] end
    -- The seed: the spot whose `limit - 1` nearest neighbours are nearest.
    local seed, best = 1, math.huge
    for index = 1, count do
        local gaps = {}
        for other = 1, count do if other ~= index then gaps[#gaps + 1] = near(index, other) end end
        table.sort(gaps)
        local total = 0
        for nearest = 1, math.min(limit - 1, #gaps) do total = total + gaps[nearest] end
        if total < best then seed, best = index, total end
    end
    local chosen, taken, nearest = {seed}, {[seed] = true}, {}
    for index = 1, count do nearest[index] = near(seed, index) end
    while #chosen < limit do
        local pick, distance = nil, math.huge
        for index = 1, count do
            if not taken[index] and nearest[index] < distance then pick, distance = index, nearest[index] end
        end
        if not pick then break end
        taken[pick] = true; chosen[#chosen + 1] = pick
        for index = 1, count do
            if not taken[index] then
                local toPick = near(pick, index)
                if toPick < nearest[index] then nearest[index] = toPick end
            end
        end
    end
    return chosen
end

-- Turns a closed loop (first point repeated at the end) so it starts at `first`.
local function rotate(loop, first)
    local stops = #loop.points - 1
    if stops < 2 or first == 1 then return end
    local points, legs = {}, {}
    for offset = 0, stops - 1 do
        local index = (first - 1 + offset) % stops + 1
        points[#points + 1] = loop.points[index]
        legs[#legs + 1] = loop.legs[index]
    end
    points[#points + 1] = points[1]
    loop.points, loop.legs = points, legs
end

-- points: 1 to 80 tables with mapID, x, y, and optionally value.
-- options.stops: how many the loop may hold (default and most: 24).
-- options.from: {mapID, x, y} to start nearest to; default is the player.
-- options.from == false: do not turn the loop.
-- Returns the loop ({points, legs, seconds} as ns.TrailLoop gives it) with
-- yards, stops, available and startsNearPlayer added; or nil and a reason.
function ns.PlanLoop(points, options)
    options = type(options) == "table" and options or {}
    if type(points) ~= "table" or #points == 0 then return nil, "No spots to plan a loop from." end
    if #points > MAX_INPUT then return nil, "Too many spots: a loop is planned from " .. MAX_INPUT .. " at most." end
    for _, point in ipairs(points) do
        if type(point) ~= "table" or not ns.ValidTravelPoint(point) then return nil, "A spot has no valid location." end
    end
    local limit = math.max(1, math.min(MAX_STOPS, finite(options.stops) and math.floor(options.stops) or MAX_STOPS))
    local cache, known = {}, {}
    local function gap(i, j)
        if i == j then return 0 end
        local low, high = i < j and i or j, i < j and j or i
        local key = low * 1000 + high
        local value = known[key]
        if value == nil then
            value = ns.TravelPointDistance(points[i], points[j], cache)
            if not finite(value) or value < 0 then
                -- No scale for this map: fall back to the map's own proportions.
                local dx, dy = points[i].x - points[j].x, points[i].y - points[j].y
                value = points[i].mapID == points[j].mapID and math.sqrt(dx * dx + dy * dy) * 4000 or 100000
            end
            known[key] = value
        end
        return value
    end
    -- The spots in the order the chooser took them: the first K are the best K.
    local ranked = {}
    for _, index in ipairs(choose(points, limit, gap)) do ranked[#ranked + 1] = points[index] end
    local respawn = finite(options.respawn) and options.respawn > 0 and options.respawn or nil
    local harvest = finite(options.harvestSeconds) and options.harvestSeconds >= 0 and options.harvestSeconds or 0
    local loop, lap
    if respawn and #ranked > 3 then
        local bestRate
        for size = 3, #ranked do
            local some = {}
            for index = 1, size do some[index] = ranked[index] end
            local candidate = ns.TrailLoop(some)
            if candidate and finite(candidate.seconds) then
                local seconds = candidate.seconds + size * harvest
                local rate = size / math.max(seconds, respawn)
                -- A bigger loop has to be clearly better, or the shorter walk wins.
                if not bestRate or rate > bestRate * 1.001 then bestRate, loop, lap = rate, candidate, seconds end
            end
        end
    end
    if not loop then
        loop = ns.TrailLoop(ranked)
        if loop and finite(loop.seconds) then lap = loop.seconds + #ranked * harvest end
    end
    if not loop then return nil, "No walking loop is available for these spots." end
    local stops = math.max(0, #loop.points - 1)
    -- Begin at the stop nearest the player.
    local from = options.from
    if from == nil and stops > 0 and ns.PlayerPoint then from = ns.PlayerPoint(loop.points[1].mapID) end
    if type(from) == "table" and ns.ValidTravelPoint(from) and stops > 1 then
        local first, nearest = 1, math.huge
        for index = 1, stops do
            local distance = ns.TravelPointDistance(from, loop.points[index], cache)
            if finite(distance) and distance < nearest then first, nearest = index, distance end
        end
        if nearest < math.huge then rotate(loop, first); loop.startsNearPlayer = true end
    end
    loop.seconds = finite(loop.seconds) and loop.seconds or 0
    loop.yards = loop.seconds * RUN_YARDS_PER_SECOND
    loop.stops, loop.available = stops, #points
    -- A lap including the time spent working each stop, and what it was sized for.
    loop.lapSeconds = finite(lap) and lap or loop.seconds
    loop.respawn, loop.harvestSeconds = respawn, harvest
    if respawn then
        loop.perHour = stops * 3600 / math.max(loop.lapSeconds, respawn)
        -- Every known spot is in and the lap is still shorter than the respawn: spots will be empty on return.
        loop.short = loop.lapSeconds < respawn and stops >= math.min(limit, #points) and (respawn - loop.lapSeconds) or nil
    end
    return loop
end

-- Where the player is standing: the zone map and the position on it.
function ns.PlayerSpot()
    if not C_Map or type(C_Map.GetBestMapForUnit) ~= "function" or not ns.PlayerPoint then return nil end
    local mapID = ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID, 1000000) or mapID < 1 then return nil end
    return ns.PlayerPoint(mapID)
end

function ns.RouteEngineDiagnostics(output)
    output("Route engine: plans a loop of up to " .. MAX_STOPS .. " stops from up to " .. MAX_INPUT
        .. " spots; straight-line distance in yards at " .. RUN_YARDS_PER_SECOND .. " yards a second on foot.")
end
