local addonName, ns = ...

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

function ns.FormatDistance(value)
    if ns.Option("distanceUnits") == "metres" then return string.format("%.0f m", value * 0.9144) end
    return string.format("%.0f yd", value)
end

local function duration(value)
    return string.format("%dm %02ds", math.floor(value / 60), math.floor(value % 60))
end

function ns.RouteContext(stop, mapID, facts)
    if stop.kind == "loading" then
        return stop.action == "scan" and ("Checking your quests and completion history.\n"
            .. (ns.guideScanning and ns.guideScanning.guide.fixedRoute and "The guide's fixed step order is retained." or "Checking the route for your next steps."))
            or "Checking progress and prerequisites.\nComparing nearby pickups, work and returns."
    end
    local travelSummary = ns.TravelPathSummary(stop)
    if travelSummary then return travelSummary end
    if ns.routeSelection and ns.routeSelection.mode == "travel" then
        if stop.travelLeg or stop.flightPlan then
            return (stop.travelLeg and stop.travelLeg.method == "walk" and "Follow the crossing towards Orgrimmar."
                or "Use this transport towards Orgrimmar.") .. "\nQuickest known route; travel times are estimates."
        end
        return ns.routePaused or "Reach Orgrimmar.\nTravel guide • Levels 1–60."
    end
    if stop.kind == "notice" and not stop.sourceStop and ns.routeSelection and ns.routeSelection.fullGuide then
        if ns.selectedRoute and ns.selectedRoute.complete then return "Guide complete.\nChoose another guide or Scan to check progress." end
        return (ns.routeSelection.zone or ns.MapName(ns.routeSelection.homeMapID or ns.routeSelection.mapID or 0)) .. " • Guide retained.\nVisit its quest giver or Scan after progressing."
    end
    if stop.kind == "notice" and not stop.sourceStop then return "Scan can reconsider skipped steps.\nSettings can reset all skips for this character." end
    if stop.kind == "corpse" then
        return (stop.approximate and "Recorded death position; check nearby." or "Your quest guide is retained.")
            .. "\nResume questing after recovering your body."
    end
    if stop.flightPlan then
        local plan = stop.flightPlan
        return (plan.measured and "Timed flight route: " or "Estimated flight route: ") .. duration(plan.seconds)
            .. "\nFly to " .. plan.destination.name .. (plan.walkingSeconds and plan.walkingSeconds > plan.seconds
                and ("; saves ~" .. duration(plan.walkingSeconds - plan.seconds) .. ".") or ".")
    end
    if stop.travelLeg then return "Travel towards " .. ns.MapName(stop.goal.mapID) .. ".\n" .. (stop.travelLeg.method == "walk"
        and "Use the crossing; follow roads and terrain." or "Board the correct transport; waiting time varies.") end
    if stop.action == "flight-check" then return "Check this nearby flight master.\nUnlock status has not been confirmed." end
    if ns.routePaused and not stop.sourceStop then
        if ns.routeSelection and ns.routeSelection.fixedRoute then return ns.routePaused end
        return "Waiting for confirmed party progress.\nYour last route is retained."
    end
    facts = facts or ns.GuideStepFacts(stop)
    stop = facts.stop
    local reason = ns.GuideStepHint(stop, facts)
    if stop.unknownLocation then reason = "Exact location missing; use the quest tracker."
    elseif stop.clientLocation then reason = "Location supplied by your quest tracker." end
    local forPlayer = ns.SafeTitle(stop.forPlayer)
    local who = forPlayer and (" • For " .. forPlayer) or ""
    local context = ns.StopLocationText(stop, mapID) .. who
    local useful, exception = ns.LevelingValue(stop.id)
    if ns.routeSelection and ns.routeSelection.catchupRequired and ns.routeSelection.catchupRequired[stop.id] then
        reason = "Finish this prerequisite to catch your party up."
    elseif useful == true and exception then reason = exception
    elseif useful == false then reason = "Quest-log work you chose to keep in this route." end
    if ns.IsGroupQuest(stop.id) then reason = "Group / elite: bring a party. " .. reason end
    return reason .. "\n" .. context
end

function ns.NavigationState()
    if not ns.Option("routeArrow") and not ns.Option("standaloneArrow") then return {status = "Disabled in settings"} end
    if ns.guideScanning or ns.routePlanning then
        local scan = ns.guideScanning
        local work = scan or ns.routePlanning
        return {visible = true, busy = true, status = scan and "Scanning guide…" or "Loading route…",
            stop = {id = 0, kind = "loading", action = scan and "scan" or "plan", title = work.guide.title}}
    end
    if ns.routeSelection and ns.routeSelection.mode == "travel" then ns.UpdateTravelGuide(ns.routeSelection, true) end
    local route = ns.routeSelection and ns.selectedRoute
    local stop = ns.navigationPreview and ns.navigationPreview.stop or route and route.stops and route.stops[1]
    if not stop and ns.routeSelection then
        local pending = route and route.pendingStop
        stop = {kind = "notice", id = pending and pending.id or 0, title = pending and pending.title or ns.routeSelection.title, mapID = route and route.mapID or 0,
            stepKind = pending and pending.kind, guideStep = pending and pending.guideStep,
            sourceStop = pending,
            learnedSource = pending and pending.learnedSource,
            x = 0, y = 0, label = ns.routePaused or "Waiting for the next available guide step."}
    end
    stop = ns.CorpseDestination() or ns.TravelDestination(stop)
    local flight = ns.FlightState()
    if flight then
        return {visible = true, stop = stop or {title = "Flight travel", kind = "f", label = "Flying", id = 0, mapID = 0},
            status = "Flying to " .. flight.name, flight = flight}
    end
    if not stop then return {status = "No route selected"} end
    local state = {visible = true, stop = stop}
    if stop.kind == "notice" then state.status = stop.label; return state end
    if stop.positionUnavailable then state.status = "Corpse position unavailable on this build"; return state end
    if ns.routePaused then state.status = "Waiting for party updates"; return state end
    if ns.navigation and type(ns.navigation.icon.CreateLine) ~= "function" then state.status = "Arrow drawing unavailable"; return state end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) or mapID <= 0 then state.status = "Position unavailable"; return state end
    local destination = stop
    if mapID ~= stop.mapID then
        destination = ns.ProjectMapPoint(stop, mapID)
        if not destination then state.status = "Travel to " .. ns.MapName(stop.mapID); return state end
        state.crossZone = true
    end
    local position = ns.PlayerPoint(mapID)
    if not position then state.status = "Position unavailable"; return state end
    local width, height = ns.ReadPublic(C_Map.GetMapWorldSize, mapID)
    if not finite(width) or not finite(height) or width <= 0 or height <= 0
        or width >= 1000000 or height >= 1000000 then state.status = "Map scale unavailable"; return state end
    local east, north = (destination.x - position.x) * width, (position.y - destination.y) * height
    state.distance = math.sqrt(east * east + north * north)
    if state.distance <= 8 then
        state.status = ns.GuideStepAction(stop); state.arrived = true; return state
    end
    local facing = ns.ReadPublic(GetPlayerFacing)
    if not finite(facing) then state.status = "Direction unavailable"; return state end
    -- Facing is counterclockwise from north; map X goes east and map Y south.
    state.angle = math.atan2(-east, north) - facing
    state.status = state.crossZone and ("Travel to " .. ns.MapName(stop.mapID)) or "Follow next route stop"
    return state
end

function ns.DrawNavigationArrow(angle, icon)
    icon = icon or ns.navigation.icon
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

function ns.HideNavigationGeometry(icon)
    for _, line in ipairs(icon.lines) do line:Hide() end
    for _, line in ipairs(icon.spinnerLines or {}) do line:Hide() end
end

function ns.DrawNavigationSpinner(icon)
    if type(icon.CreateLine) ~= "function" then return false end
    icon.spinnerLines = icon.spinnerLines or {}
    local now = ns.ReadPublic(GetTime)
    icon.spinnerPhase = finite(now) and -now * 4 or (icon.spinnerPhase or 0) - 0.4
    for index = 1, 12 do
        local line = icon.spinnerLines[index]
        if not line then line = icon:CreateLine(nil, "OVERLAY"); icon.spinnerLines[index] = line end
        local angle = icon.spinnerPhase + index * math.pi / 8
        line:SetThickness(3); line:SetColorTexture(1, 0.82, 0.30, index / 12)
        line:SetStartPoint("CENTER", icon, math.cos(angle) * 18, math.sin(angle) * 18)
        angle = angle + math.pi / 8
        line:SetEndPoint("CENTER", icon, math.cos(angle) * 18, math.sin(angle) * 18)
        line:Show()
    end
    return true
end

function ns.UpdateNavigation()
    local frame = ns.navigation
    if not frame then return end
    local state = ns.NavigationState()
    frame.state = state
    frame:SetShown(state.visible == true and ns.Option("routeArrow"))
    ns.UpdateStandaloneArrow(state)
    ns.UpdateGuideTip(state)
    if not state.visible then ns.HideNavigationGeometry(frame.icon); return end
    frame.title:SetText(state.stop.title)
    local facts = ns.GuideStepFacts(state.stop)
    local clock = state.flight and (state.flight.remaining and state.flight.remaining > 0 and ((state.flight.estimated and "Estimated " or "~") .. duration(state.flight.remaining) .. " remaining")
        or state.flight.elapsed and (duration(state.flight.elapsed) .. " flying") or "Flight time unavailable")
    local distance = state.distance and (ns.FormatDistance(state.distance) .. (state.arrived and " • Here" or "")) or ""
    if facts.progress then distance = distance .. (distance ~= "" and " • " or "") .. facts.progress end
    frame.distance:SetText(clock or distance)
    frame.status:SetText(state.angle and ns.GuideStepAction(state.stop, facts) or state.status)
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    frame.context:SetText(ns.RouteContext(state.stop, mapID, facts))
    ns.HideNavigationGeometry(frame.icon)
    frame.symbol:SetText("…"); frame.symbol:SetTextColor(0.96, 0.76, 0.35, 1)
    frame.symbol:SetShown(state.angle == nil and not state.arrived and not state.flight)
    frame.step:SetText(state.stop.kind == "loading" and (state.stop.action == "scan" and "Checking guide progress" or "Generating an efficient trip") or state.stop.historyPreview and "History preview • published location" or
        (ns.routeSelection and ns.routeSelection.mode == "travel" and "Travel guide • Levels 1–60" or
            ns.navigationPreview and "Preview step • arrows browse; Scan returns to the plan" or
            (state.stop.npcVisitPickup and "Collect quests at this NPC" or state.stop.guideStep and ("Zone guide step " .. state.stop.guideStep) or "Current guide step")))
    local editable = not ns.navigationPreview and not state.flight and state.stop.kind ~= "corpse"
        and (state.stop.kind ~= "notice" or state.stop.id > 0) and state.stop.kind ~= "loading"
    local quests = not (ns.routeSelection and ns.routeSelection.mode == "travel")
    frame.skipStep:SetEnabled(editable and quests); frame.skipQuest:SetEnabled(editable and quests); frame.scan:SetEnabled(not state.flight and state.stop.kind ~= "loading")
    frame.back:SetEnabled(state.stop.kind ~= "loading"); frame.next:SetEnabled(state.stop.kind ~= "loading")
    if state.busy then frame.symbol:SetShown(not ns.DrawNavigationSpinner(frame.icon))
    elseif state.arrived then ns.DrawNavigationArrow(math.pi)
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
    local frame = CreateFrame("Frame", "WowTogetherRouteArrow", UIParent, "BackdropTemplate")
    ns.navigation = frame
    frame:SetSize(360, 168); frame:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, 160); ns.UIPanel(frame, ns.UIColors.background)
    frame:SetClampedToScreen(true); frame:SetFrameStrata("MEDIUM")
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", ns.SaveNavigationPosition)
    local saved = ns.db.arrowPosition
    if type(saved) == "table" and type(saved.point) == "string" and type(saved.relative) == "string"
        and finite(saved.x) and finite(saved.y) then
        frame:ClearAllPoints(); frame:SetPoint(saved.point, UIParent, saved.relative, saved.x, saved.y)
    end
    frame.title = ns.UILabel(frame, "GameFontNormal", 13, ns.UIColors.gold)
    frame.title:SetPoint("TOPLEFT", 14, -10)
    frame.title:SetSize(332, 18); frame.title:SetWordWrap(false)
    frame.step = ns.UILabel(frame, nil, 10, ns.UIColors.muted); frame.step:SetPoint("TOPLEFT", 14, -30); frame.step:SetSize(332, 14)
    ns.UIDivider(frame, -48)
    frame.icon = CreateFrame("Frame", nil, frame); frame.icon:SetSize(48, 48); frame.icon:SetPoint("TOPLEFT", 16, -50)
    frame.icon.lines = {}
    frame.symbol = frame.icon:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    frame.symbol:SetFont("Fonts\\FRIZQT__.TTF", 26, "OUTLINE"); frame.symbol:SetPoint("CENTER")
    frame.distance = ns.UILabel(frame, nil, 11, ns.UIColors.gold)
    frame.distance:SetPoint("TOPLEFT", 82, -82); frame.distance:SetSize(264, 14); frame.distance:SetWordWrap(false)
    frame.status = ns.UILabel(frame, nil, 12)
    frame.status:SetPoint("TOPLEFT", 82, -52)
    frame.status:SetSize(264, 28); frame.status:SetWordWrap(true); frame.status:SetJustifyV("TOP")
    frame.context = ns.UILabel(frame, nil, 10, ns.UIColors.muted)
    frame.context:SetPoint("TOPLEFT", 14, -101)
    frame.context:SetSize(332, 26); frame.context:SetWordWrap(false); frame.context:SetJustifyV("TOP")
    frame.skipStep = ns.UIButton(frame, "Skip step", 80, function() ns.SkipGuide("step") end)
    frame.skipStep:SetHeight(24); frame.skipStep:SetPoint("BOTTOMLEFT", 42, 8)
    frame.skipQuest = ns.UIButton(frame, "Skip quest", 80, function() ns.SkipGuide("quest") end)
    frame.skipQuest:SetHeight(24); frame.skipQuest:SetPoint("BOTTOMLEFT", 128, 8)
    ns.UIHelp(frame.skipStep, "Skip this step for this character. This does not record NPC availability or learn a prerequisite.")
    ns.UIHelp(frame.skipQuest, "Skip this quest for this character. A missing pickup is learned from actual NPC offers before and after a hand-in, not from this button.")
    frame.scan = ns.UIButton(frame, "Scan guide", 96, function() ns.ScanGuideProgress() end)
    frame.scan:SetHeight(24); frame.scan:SetPoint("BOTTOMLEFT", 214, 8)
    frame.back = ns.UIButton(frame, "‹", 24, function() ns.PreviewGuideStep(-1) end)
    frame.back:SetHeight(24); frame.back:SetPoint("BOTTOMLEFT", 12, 8)
    frame.next = ns.UIButton(frame, "›", 24, function() ns.PreviewGuideStep(1) end)
    frame.next:SetHeight(24); frame.next:SetPoint("BOTTOMRIGHT", -12, 8)
    frame.tip = CreateFrame("Frame", nil, frame, "BackdropTemplate")
    frame.tip:SetSize(360, 28); frame.tip:SetPoint("TOPLEFT", frame, "BOTTOMLEFT", 0, -4)
    ns.UIPanel(frame.tip, ns.UIColors.background); frame.tip:EnableMouse(true)
    frame.tip.text = ns.UILabel(frame.tip, nil, 10, ns.UIColors.gold)
    frame.tip.text:SetPoint("LEFT", 10, 0); frame.tip.text:SetSize(316, 18); frame.tip.text:SetWordWrap(false)
    frame.tip.close = ns.UIButton(frame.tip, "×", 20, ns.DismissGuideTip)
    frame.tip.close:SetHeight(20); frame.tip.close:SetPoint("RIGHT", -4, 0)
    frame.tip.close.caption:ClearAllPoints(); frame.tip.close.caption:SetPoint("CENTER"); frame.tip.close.caption:SetSize(16, 16)
    frame.tip:SetScript("OnEnter", function(self)
        if not GameTooltip or not self.value then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT"); GameTooltip:AddLine(self.value.detail, 1, 0.82, 0.3, true); GameTooltip:Show()
    end)
    frame.tip:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    frame.tip:Hide()
    frame:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        if self.state and self.state.stop then GameTooltip:AddLine(ns.GuideStepDescription(self.state.stop), 1, 1, 1, true) end
        if self.state and self.state.stop.kind == "notice" then GameTooltip:AddLine(self.state.status, 1, 0.82, 0.3, true) end
        if self.context then GameTooltip:AddLine(self.context:GetText() or "", 0.8, 0.85, 0.9, true) end
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
    ns.CreateStandaloneArrow()
    frame:Hide()
    ns.UpdateNavigation()
end

function ns.ToggleNavigation() ns.SetOption("routeArrow", not ns.Option("routeArrow")) end

function ns.NavigationDiagnostics(output)
    local state = ns.navigation and ns.navigation.state or ns.NavigationState()
    output("Navigation arrow: " .. state.status)
    if state.distance then output("Arrow distance: " .. string.format("%.0f yards", state.distance)) end
    output("Standalone arrow: " .. (ns.Option("standaloneArrow") and "on" or "off"))
    output("Travel network: " .. (ns.Option("travelNetwork") and (ns.travelNetworkStatus or "Ready; select a route.") or "off"))
    output("Route lines draw on the world map; the minimap button opens the addon.")
end
