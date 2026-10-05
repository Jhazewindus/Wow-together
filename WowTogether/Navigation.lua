local addonName, ns = ...

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

function ns.StopInstruction(stop)
    if stop.npcName and stop.npcName ~= "" and (stop.kind == "a" or stop.kind == "t" or not stop.action) then
        return "Talk to " .. stop.npcName
    end
    if stop.kind == "t" then return "Turn in " .. stop.title end
    if stop.kind == "a" then return "Pick up " .. stop.title end
    return stop.label or ("Work on " .. stop.title)
end

function ns.NavigationState()
    if not ns.Option("routeArrow") then return {status = "Disabled in settings"} end
    local route = ns.routeSelection and ns.selectedRoute
    local stop = route and route.stops and route.stops[1]
    if not stop then return {status = "No route selected"} end
    local state = {visible = true, stop = stop}
    if ns.routePaused then state.status = "Waiting for party updates"; return state end
    if ns.navigation and type(ns.navigation.icon.CreateLine) ~= "function" then state.status = "Arrow drawing unavailable"; return state end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) or mapID <= 0 then state.status = "Position unavailable"; return state end
    if mapID ~= stop.mapID then state.status = "Travel to " .. ns.MapName(stop.mapID); return state end
    local position = ns.PlayerPoint(mapID)
    if not position then state.status = "Position unavailable"; return state end
    local width, height = ns.ReadPublic(C_Map.GetMapWorldSize, mapID)
    if not finite(width) or not finite(height) or width <= 0 or height <= 0
        or width >= 1000000 or height >= 1000000 then state.status = "Map scale unavailable"; return state end
    local east, north = (stop.x - position.x) * width, (position.y - stop.y) * height
    state.distance = math.sqrt(east * east + north * north)
    if state.distance <= 8 then
        state.status = ns.StopInstruction(stop); state.arrived = true; return state
    end
    local facing = ns.ReadPublic(GetPlayerFacing)
    if not finite(facing) then state.status = "Direction unavailable"; return state end
    -- Facing is counterclockwise from north; map X goes east and map Y south.
    state.angle = math.atan2(-east, north) - facing
    state.status = "Follow next route stop"
    return state
end

function ns.DrawNavigationArrow(angle)
    local icon = ns.navigation.icon
    local cosine, sine = math.cos(angle), math.sin(angle)
    local shape = {{0, 21}, {-12, -6}, {0, 0}, {12, -6}, {0, 21}}
    for index = 1, #shape - 1 do
        local line = icon.lines[index]
        if not line then line = icon:CreateLine(nil, "OVERLAY"); icon.lines[index] = line end
        local a, b = shape[index], shape[index + 1]
        line:SetThickness(3); line:SetColorTexture(1, 0.82, 0.30, 1)
        line:SetStartPoint("CENTER", icon, a[1] * cosine - a[2] * sine, a[1] * sine + a[2] * cosine)
        line:SetEndPoint("CENTER", icon, b[1] * cosine - b[2] * sine, b[1] * sine + b[2] * cosine)
        line:Show()
    end
end

function ns.UpdateNavigation()
    local frame = ns.navigation
    if not frame then return end
    local state = ns.NavigationState()
    frame.state = state
    frame:SetShown(state.visible == true)
    if not state.visible then return end
    frame.title:SetText(state.stop.title)
    frame.distance:SetText(state.distance and (string.format("%.0f yd", state.distance) .. (state.arrived and " • Here" or "")) or "")
    frame.status:SetText(state.angle and ns.StopInstruction(state.stop) or state.status)
    for _, line in ipairs(frame.icon.lines) do line:Hide() end
    frame.symbol:SetText("…"); frame.symbol:SetTextColor(0.96, 0.76, 0.35, 1)
    frame.symbol:SetShown(state.angle == nil and not state.arrived)
    if state.arrived then ns.DrawNavigationArrow(math.pi)
    elseif state.angle ~= nil then ns.DrawNavigationArrow(state.angle) end
end

function ns.SaveNavigationPosition()
    local frame = ns.navigation
    frame:StopMovingOrSizing()
    local point, _, relative, x, y = frame:GetPoint()
    if ns.Public(point) and ns.Public(relative) and type(point) == "string" and type(relative) == "string"
        and finite(x) and finite(y) then ns.db.arrowPosition = {point = point, relative = relative, x = x, y = y} end
end

function ns.CreateNavigation()
    local frame = CreateFrame("Frame", "WowTogetherRouteArrow", UIParent)
    ns.navigation = frame
    frame:SetSize(220, 118); frame:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, 160)
    frame:SetClampedToScreen(true); frame:SetFrameStrata("MEDIUM")
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", ns.SaveNavigationPosition)
    local saved = ns.db.arrowPosition
    if type(saved) == "table" and type(saved.point) == "string" and type(saved.relative) == "string"
        and finite(saved.x) and finite(saved.y) then
        frame:ClearAllPoints(); frame:SetPoint(saved.point, UIParent, saved.relative, saved.x, saved.y)
    end
    frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.title:SetFont("Fonts\\FRIZQT__.TTF", 11, "OUTLINE"); frame.title:SetPoint("TOP", 0, -4)
    frame.title:SetSize(214, 18); frame.title:SetWordWrap(false)
    frame.icon = CreateFrame("Frame", nil, frame); frame.icon:SetSize(52, 52); frame.icon:SetPoint("TOP", 0, -29)
    frame.icon.lines = {}
    frame.symbol = frame.icon:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    frame.symbol:SetFont("Fonts\\FRIZQT__.TTF", 26, "OUTLINE"); frame.symbol:SetPoint("CENTER")
    frame.distance = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    frame.distance:SetFont("Fonts\\FRIZQT__.TTF", 12, "OUTLINE"); frame.distance:SetPoint("BOTTOM", 0, 21)
    frame.status = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.status:SetFont("Fonts\\FRIZQT__.TTF", 10, "OUTLINE"); frame.status:SetPoint("BOTTOM", 0, 3)
    frame.status:SetSize(214, 17); frame.status:SetWordWrap(false)
    frame:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        if self.state and self.state.stop then GameTooltip:AddLine(self.state.stop.label, 1, 0.82, 0.3, true) end
        GameTooltip:AddLine("Drag to move • /wt arrow to toggle", 1, 1, 1, true)
        GameTooltip:AddLine("Direction relative to your character; follow roads and terrain.", 0.75, 0.8, 0.85, true)
        GameTooltip:Show()
    end)
    frame:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    frame.elapsed = 0
    -- No event reports continuous facing/position changes. Poll at 10 Hz only
    -- while this owned, unprotected frame is visible with a selected route.
    frame:SetScript("OnUpdate", function(self, elapsed)
        if not finite(elapsed) or elapsed < 0 then return end
        self.elapsed = self.elapsed + elapsed
        if self.elapsed < 0.1 then return end
        self.elapsed = 0
        ns.UpdateNavigation()
    end)
    frame:Hide()
    ns.UpdateNavigation()
end

function ns.ToggleNavigation() ns.SetOption("routeArrow", not ns.Option("routeArrow")) end

function ns.NavigationDiagnostics(output)
    local state = ns.navigation and ns.navigation.state or ns.NavigationState()
    output("Navigation arrow: " .. state.status)
    if state.distance then output("Arrow distance: " .. string.format("%.0f yards", state.distance)) end
    output("Route lines draw on the world map; the minimap button opens the addon.")
end
