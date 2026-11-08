local addonName, ns = ...

-- The current travel line on the minimap: the same points the world map
-- draws (recorded/bundled ground, crossings, then the next stops), projected
-- around the player at the minimap's current yard scale and clipped to its
-- round or square edge. Transports and personal teleports break the line,
-- as on the map. Unprotected textures only; nothing here is a secure frame.
local REFRESH, MAX_POINTS = 0.15, 220
local DIAMETER = {
    indoor = {[0] = 300, [1] = 240, [2] = 180, [3] = 120, [4] = 80, [5] = 50},
    outdoor = {[0] = 466 + 2 / 3, [1] = 400, [2] = 333 + 1 / 3, [3] = 266 + 2 / 3, [4] = 200, [5] = 133 + 1 / 3},
}
local overlay, lines, shadows, used, elapsed = nil, {}, {}, 0, 0

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

-- Minimap radius in yards. Modern clients report it; older ones expose the
-- zoom step, which maps to the well-known indoor/outdoor diameters.
local function radiusYards()
    if C_Minimap and type(C_Minimap.GetViewRadius) == "function" then
        local radius = ns.ReadPublic(C_Minimap.GetViewRadius)
        if finite(radius) and radius > 0 then return radius end
    end
    local zoom = ns.ReadPublic(Minimap.GetZoom, Minimap)
    if not finite(zoom) then return end
    local outdoorZoom = tonumber(ns.ReadPublic(GetCVar, "minimapZoom"))
    local set = DIAMETER[outdoorZoom == zoom and "outdoor" or "indoor"]
    local diameter = set[math.floor(zoom)]
    return diameter and diameter / 2
end

local function shape()
    local kind = type(GetMinimapShape) == "function" and ns.ReadPublic(GetMinimapShape)
    return kind == "SQUARE" and "SQUARE" or "ROUND"
end

local function hideAll()
    for index = 1, used do lines[index]:Hide(); shadows[index]:Hide() end
    used = 0
end

-- Clip a segment to the circle of radius r centred on the player.
local function clipCircle(x1, y1, x2, y2, r)
    local dx, dy = x2 - x1, y2 - y1
    local a = dx * dx + dy * dy
    if a == 0 then
        if x1 * x1 + y1 * y1 <= r * r then return x1, y1, x2, y2 end
        return
    end
    local b, c = 2 * (x1 * dx + y1 * dy), x1 * x1 + y1 * y1 - r * r
    local disc = b * b - 4 * a * c
    if disc < 0 then return end
    local root = math.sqrt(disc)
    local start, finish = math.max(0, (-b - root) / (2 * a)), math.min(1, (-b + root) / (2 * a))
    if start >= finish then return end
    return x1 + start * dx, y1 + start * dy, x1 + finish * dx, y1 + finish * dy
end

local function segment(x1, y1, x2, y2, alpha)
    used = used + 1
    local shadow, line = shadows[used], lines[used]
    if not shadow then
        shadow = overlay:CreateLine(nil, "OVERLAY", nil, 2); shadows[used] = shadow
        line = overlay:CreateLine(nil, "OVERLAY", nil, 3); lines[used] = line
    end
    shadow:SetThickness(3.5); shadow:SetColorTexture(0.12, 0.085, 0.025, 0.7 * alpha)
    shadow:SetStartPoint("CENTER", overlay, x1, y1); shadow:SetEndPoint("CENTER", overlay, x2, y2); shadow:Show()
    line:SetThickness(1.8); line:SetColorTexture(1, 0.82, 0.30, alpha)
    line:SetStartPoint("CENTER", overlay, x1, y1); line:SetEndPoint("CENTER", overlay, x2, y2); line:Show()
end

local function draw()
    if not overlay then return end
    if not ns.Option("minimapRoute") or not ns.selectedRoute or ns.navigationPreview
        or ns.ReadPublic(UnitOnTaxi, "player") == true or not ns.ReadPublic(Minimap.IsVisible, Minimap) then
        hideAll(); ns.minimapRouteStatus = "Hidden (setting, no route, flight or minimap hidden)."; return
    end
    local route = ns.RouteForDisplay()
    if not route or route.flying then hideAll(); ns.minimapRouteStatus = "No displayable route."; return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local origin = ns.GuideInteger(mapID) and mapID > 0 and ns.PlayerPoint(mapID)
    local width, height
    if origin then width, height = ns.ReadPublic(C_Map.GetMapWorldSize, mapID) end
    local radius = radiusYards()
    local size = ns.ReadPublic(Minimap.GetWidth, Minimap)
    if not origin or not finite(width) or not finite(height) or width <= 0 or height <= 0 or not radius
        or not finite(size) or size <= 0 then
        hideAll(); ns.minimapRouteStatus = "Position, map scale or minimap zoom unavailable."; return
    end
    local displayed = ns.RouteDisplayStops(route)
    local points = {}
    local travel = displayed[1] and ns.TravelLinePoints(origin, displayed[1])
    if travel then
        for _, point in ipairs(travel) do points[#points + 1] = point end
        for index = 2, #displayed do points[#points + 1] = displayed[index] end
    else
        points[1] = origin
        for _, stop in ipairs(displayed) do points[#points + 1] = stop end
    end
    local rotate = ns.ReadPublic(GetCVar, "rotateMinimap") == "1"
    local facing = rotate and ns.ReadPublic(GetPlayerFacing)
    local cosine, sine = 1, 0
    if rotate and finite(facing) then cosine, sine = math.cos(facing), math.sin(facing) end
    local scale, half, round = size / (2 * radius), size / 2, shape() == "ROUND"
    local projection, screen = {}, {}
    for index, point in ipairs(points) do
        if index > MAX_POINTS then break end
        local projected = point and ns.ProjectMapPoint(point, mapID, projection)
        if projected then
            local east, north = (projected.x - origin.x) * width, (origin.y - projected.y) * height
            -- A rotating minimap keeps the facing direction up.
            local sx, sy = east * cosine + north * sine, north * cosine - east * sine
            screen[index] = {sx * scale, sy * scale}
        else screen[index] = false end
    end
    hideAll()
    local alpha = ns.routePaused and 0.45 or 1
    local safety, terrain = ns.TravelSafetyContext(), ns.Option("travelNetwork") and ns.TravelTerrainContext()
    for index = 2, math.min(#points, MAX_POINTS) do
        local a, b = screen[index - 1], screen[index]
        if a and b and not ns.HostileWalkCrossing(points[index - 1], points[index], safety, index == 2, false)
            and not (terrain and ns.TerrainWalkCrossing(points[index - 1], points[index], terrain)) then
            local x1, y1, x2, y2
            if round then x1, y1, x2, y2 = clipCircle(a[1], a[2], b[1], b[2], half)
            else
                x1, y1, x2, y2 = ns.ClipRouteSegment(a[1] + half, half - a[2], b[1] + half, half - b[2], size, size)
                if x1 then x1, y1, x2, y2 = x1 - half, half - y1, x2 - half, half - y2 end
            end
            if x1 and math.abs(x2 - x1) + math.abs(y2 - y1) >= 0.5 then segment(x1, y1, x2, y2, alpha) end
        end
    end
    ns.minimapRouteStatus = used .. " line(s) at " .. string.format("%.0f", radius) .. "-yard radius" .. (rotate and ", rotating" or "") .. "."
end

function ns.CreateMinimapRoute()
    if overlay or not Minimap or type(CreateFrame) ~= "function" then return end
    overlay = CreateFrame("Frame", nil, Minimap)
    overlay:SetAllPoints(Minimap)
    overlay:EnableMouse(false)
    if type(overlay.CreateLine) ~= "function" then overlay = nil; ns.minimapRouteStatus = "Line drawing unavailable."; return end
    local level = ns.ReadPublic(Minimap.GetFrameLevel, Minimap)
    if type(level) == "number" then overlay:SetFrameLevel(level + 3) end
    overlay:SetScript("OnUpdate", function(_, dt)
        elapsed = elapsed + (finite(dt) and dt or 0)
        if elapsed < REFRESH then return end
        elapsed = 0
        local okay, err = pcall(draw)
        if not okay then hideAll(); ns.minimapRouteStatus = "Minimap line error: " .. tostring(err) end
    end)
    ns.minimapRoute = overlay
end

function ns.MinimapRouteDiagnostics(output)
    output("Minimap line: " .. (ns.minimapRouteStatus or (ns.Option("minimapRoute") and "not drawn yet" or "disabled in settings")) .. ".")
end
