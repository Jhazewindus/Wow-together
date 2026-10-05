local addonName, ns = ...

-- UI maps have different normalized coordinate systems. Public world positions
-- join them; raw x/y from one zone must never be used as coordinates in another.
local bases = {}
local function number(value)
    return ns.Public(value) and type(value) == "number" and value == value and math.abs(value) < math.huge
end
local function coordinate(value)
    return number(value) and math.abs(value) < 1000000
end
local function world(mapID, x, y)
    if not C_Map or type(CreateVector2D) ~= "function" then return end
    local continent, vector = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, mapID, CreateVector2D(x, y))
    if not ns.GuideInteger(continent) or not ns.Public(vector)
        or type(vector) ~= "table" and type(vector) ~= "userdata" then return end
    local wx, wy = ns.ReadPublic(vector.GetXY, vector)
    if number(wx) and number(wy) then return continent, wx, wy, vector end
end

function ns.ResetMapProjection() bases = {} end

local function project(point, mapID, context)
    if point.mapID == mapID then return {mapID = mapID, x = point.x, y = point.y} end
    local continent, wx, wy, vector = world(point.mapID, point.x, point.y)
    if not continent then return end
    local targetContinent
    if context then
        context.continents = context.continents or {}
        targetContinent = context.continents[mapID]
        if targetContinent == nil then
            targetContinent = world(mapID, 0, 0)
            context.continents[mapID] = targetContinent or false
        end
    else targetContinent = world(mapID, 0, 0) end
    if targetContinent ~= continent then return end
    local resultMap, position = ns.ReadPublic(C_Map.GetMapPosFromWorldPos, continent, vector, mapID)
    if resultMap == mapID and ns.Public(position) and (type(position) == "table" or type(position) == "userdata") then
        local x, y = ns.ReadPublic(position.GetXY, position)
        if coordinate(x) and coordinate(y) then return {mapID = mapID, x = x, y = y} end
    end
    -- Some clients return nil for a destination outside this zone. Three public
    -- map/world pairs provide the same affine transform without fake coordinates.
    local basis = bases[mapID]
    if not basis then
        local c0, x0, y0 = world(mapID, 0, 0)
        local c1, x1, y1 = world(mapID, 1, 0)
        local c2, x2, y2 = world(mapID, 0, 1)
        if c0 ~= continent or c1 ~= continent or c2 ~= continent then return end
        local ux, uy, vx, vy = x1 - x0, y1 - y0, x2 - x0, y2 - y0
        local determinant = ux * vy - uy * vx
        if not number(determinant) or math.abs(determinant) < 0.000001 then return end
        basis = {continent = c0, x = x0, y = y0, ux = ux, uy = uy, vx = vx, vy = vy, determinant = determinant}
        bases[mapID] = basis
    end
    if basis.continent ~= continent then return end
    local dx, dy = wx - basis.x, wy - basis.y
    local x, y = (dx * basis.vy - dy * basis.vx) / basis.determinant,
        (basis.ux * dy - basis.uy * dx) / basis.determinant
    if coordinate(x) and coordinate(y) then return {mapID = mapID, x = x, y = y} end
end

function ns.ProjectMapPoint(point, mapID, context)
    if not ns.Public(point) or type(point) ~= "table" or not ns.GuideInteger(point.mapID) or point.mapID <= 0
        or not ns.GuideInteger(mapID) or mapID <= 0 or not coordinate(point.x) or not coordinate(point.y) then return end
    if not context or point.mapID == mapID then return project(point, mapID, context) end
    -- A redraw owns this cache; it is discarded before the next position/API
    -- read. Numeric keys preserve exact coordinates, with no rounding of stops.
    context.points = context.points or {}
    local targets = context.points
    targets[mapID] = targets[mapID] or {}
    local sources = targets[mapID]
    sources[point.mapID] = sources[point.mapID] or {}
    local xs = sources[point.mapID]
    xs[point.x] = xs[point.x] or {}
    local ys = xs[point.x]
    local cached = ys[point.y]
    if cached ~= nil then return cached or nil end
    local result = project(point, mapID, context)
    ys[point.y] = result or false
    return result
end
