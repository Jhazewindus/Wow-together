local addonName, ns = ...

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

function ns.StopInstruction(stop)
    if stop.kind == "travel" then return stop.label end
    if stop.kind == "corpse" then return "Return to your corpse" end
    if stop.kind == "f" then return stop.label end
    if stop.npcName and stop.npcName ~= "" and (stop.kind == "a" or stop.kind == "t" or stop.action == "talk") then
        return "Talk to " .. stop.npcName
    end
    if stop.kind == "t" then return "Turn in " .. stop.title end
    if stop.kind == "a" then return "Pick up " .. stop.title end
    local target = stop.itemName or stop.targetName or stop.npcName
    local action = stop.action
    for _, objective in ipairs((ns.ProgressForMember(stop.memberKey or ns.self, stop.id) or {}).objectives or {}) do
        if target and ns.ObjectiveMatchesPoint(objective.text, {name = target}) then
            if objective.kind == "monster" then action = "kill"
            elseif objective.kind == "item" then action = "collect" end
            target = ns.ObjectiveLabel(objective.text)
            target = string.gsub(target, "%s+slain$", "")
            target = string.gsub(target, "%s+killed$", "")
            target = string.gsub(target, "%s+collected$", "")
            break
        end
    end
    if action == "kill" then return "Kill " .. (target or stop.title) end
    if action == "collect" or action == "loot" or action == "item" then return "Pick up " .. (target or stop.title) end
    return stop.label or ("Work on " .. stop.title)
end

function ns.FormatDistance(value)
    if ns.Option("distanceUnits") == "metres" then return string.format("%.0f m", value * 0.9144) end
    return string.format("%.0f yd", value)
end

local function duration(value)
    return string.format("%dm %02ds", math.floor(value / 60), math.floor(value % 60))
end

function ns.RouteContext(stop, mapID)
    if ns.routeSelection and ns.routeSelection.mode == "travel" then
        if stop.travelLeg or stop.flightPlan then
            return (stop.travelLeg and stop.travelLeg.method == "walk" and "Follow the crossing towards Orgrimmar."
                or "Use this transport towards Orgrimmar.") .. "\nQuickest known route; travel times are estimates."
        end
        return ns.routePaused or "Reach Orgrimmar.\nTravel guide • Levels 1–60."
    end
    if stop.kind == "loading" then return "Checking progress and prerequisites.\nComparing nearby pickups, work and returns." end
    if stop.kind == "notice" and ns.routeSelection and ns.routeSelection.fullGuide then
        if ns.selectedRoute and ns.selectedRoute.complete then return "Guide complete.\nChoose another guide or Scan to check progress." end
        return ns.routeSelection.zone .. " • Guide retained.\nVisit its quest giver or Scan after progressing."
    end
    if stop.kind == "notice" then return "Scan can reconsider skipped steps.\nSettings can reset all skips for this character." end
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
    if ns.routePaused then
        if ns.routeSelection and ns.routeSelection.fixedRoute then return ns.routePaused end
        return "Waiting for confirmed party progress.\nYour last route is retained."
    end
    local reason
    if stop.kind == "t" then reason = "Hand in a completed quest."
    elseif stop.kind == "a" then
        local selected = ns.routeSelection
        reason = selected and selected.pickupIDs and selected.pickupIDs[stop.id]
            and "Nearby pickup along this trip." or "Pick up a selected quest."
    else reason = stop.npcName and not stop.action and "Visit this NPC for an active quest." or "Finish active quest objectives." end
    local zone = ns.MapName(stop.mapID)
    local who = stop.forPlayer and (" • For " .. stop.forPlayer) or ""
    local context = mapID and mapID ~= stop.mapID and ("Travel to " .. zone .. who) or (zone .. who)
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
    if ns.routePlanning then
        return {visible = true, status = "Loading route…", stop = {id = 0, kind = "loading", title = ns.routePlanning.guide.title}}
    end
    if ns.routeSelection and ns.routeSelection.mode == "travel" then ns.UpdateTravelGuide(ns.routeSelection, true) end
    local route = ns.routeSelection and ns.selectedRoute
    local stop = ns.navigationPreview and ns.navigationPreview.stop or route and route.stops and route.stops[1]
    if not stop and ns.routeSelection then
        local pending = route and route.pendingStop
        stop = {kind = "notice", id = pending and pending.id or 0, title = pending and pending.title or ns.routeSelection.title, mapID = route and route.mapID or 0,
            stepKind = pending and pending.kind, guideStep = pending and pending.guideStep,
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
        state.status = ns.StopInstruction(stop); state.arrived = true; return state
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

function ns.UpdateNavigation()
    local frame = ns.navigation
    if not frame then return end
    local state = ns.NavigationState()
    frame.state = state
    frame:SetShown(state.visible == true and ns.Option("routeArrow"))
    ns.UpdateStandaloneArrow(state)
    if not state.visible then return end
    frame.title:SetText(state.stop.title)
    local clock = state.flight and (state.flight.remaining and ("~" .. duration(state.flight.remaining) .. " remaining")
        or state.flight.elapsed and (duration(state.flight.elapsed) .. " flying") or "Flight time unavailable")
    frame.distance:SetText(clock or (state.distance and (ns.FormatDistance(state.distance) .. (state.arrived and " • Here" or "")) or ""))
    frame.status:SetText(state.angle and ns.StopInstruction(state.stop) or state.status)
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    frame.context:SetText(ns.RouteContext(state.stop, mapID))
    for _, line in ipairs(frame.icon.lines) do line:Hide() end
    frame.symbol:SetText("…"); frame.symbol:SetTextColor(0.96, 0.76, 0.35, 1)
    frame.symbol:SetShown(state.angle == nil and not state.arrived and not state.flight)
    frame.step:SetText(state.stop.kind == "loading" and "Generating an efficient trip" or state.stop.historyPreview and "History preview • published location" or
        (ns.routeSelection and ns.routeSelection.mode == "travel" and "Travel guide • Levels 1–60" or
            ns.navigationPreview and "Preview step • arrows browse; Scan returns to the plan" or
            (state.stop.guideStep and ("Zone guide step " .. state.stop.guideStep) or "Current guide step")))
    local editable = not ns.navigationPreview and not state.flight and state.stop.kind ~= "corpse"
        and (state.stop.kind ~= "notice" or state.stop.id > 0) and state.stop.kind ~= "loading"
    local quests = not (ns.routeSelection and ns.routeSelection.mode == "travel")
    frame.skipStep:SetEnabled(editable and quests); frame.skipQuest:SetEnabled(editable and quests); frame.scan:SetEnabled(not state.flight and state.stop.kind ~= "loading")
    frame.back:SetEnabled(state.stop.kind ~= "loading"); frame.next:SetEnabled(state.stop.kind ~= "loading")
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
    local frame = CreateFrame("Frame", "WowTogetherRouteArrow", UIParent, "BackdropTemplate")
    ns.navigation = frame
    frame:SetSize(344, 248); frame:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, 160); ns.UIPanel(frame)
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
    frame.title:SetSize(320, 22); frame.title:SetWordWrap(false)
    frame.step = ns.UILabel(frame, nil, 10); frame.step:SetPoint("TOP", 0, -30); frame.step:SetSize(320, 18); frame.step:SetJustifyH("CENTER")
    frame.icon = CreateFrame("Frame", nil, frame); frame.icon:SetSize(52, 52); frame.icon:SetPoint("TOP", 0, -53)
    frame.icon.lines = {}
    frame.symbol = frame.icon:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    frame.symbol:SetFont("Fonts\\FRIZQT__.TTF", 26, "OUTLINE"); frame.symbol:SetPoint("CENTER")
    frame.distance = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    frame.distance:SetFont("Fonts\\FRIZQT__.TTF", 12, "OUTLINE"); frame.distance:SetPoint("TOP", 0, -112)
    frame.status = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.status:SetFont("Fonts\\FRIZQT__.TTF", 12, "OUTLINE"); frame.status:SetPoint("TOP", 0, -139)
    frame.status:SetSize(320, 32); frame.status:SetWordWrap(true); frame.status:SetJustifyV("TOP")
    frame.context = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.context:SetFont("Fonts\\FRIZQT__.TTF", 10, "OUTLINE"); frame.context:SetPoint("TOP", 0, -174)
    frame.context:SetSize(320, 30); frame.context:SetWordWrap(false)
    frame.skipStep = ns.UIButton(frame, "Skip step", 80, function() ns.SkipGuide("step") end)
    frame.skipStep:SetHeight(24); frame.skipStep:SetPoint("BOTTOMLEFT", 35, 12)
    frame.skipQuest = ns.UIButton(frame, "Skip quest", 80, function() ns.SkipGuide("quest") end)
    frame.skipQuest:SetHeight(24); frame.skipQuest:SetPoint("BOTTOMLEFT", 121, 12)
    ns.UIHelp(frame.skipStep, "Skip this step for this character. This does not record NPC availability or learn a prerequisite.")
    ns.UIHelp(frame.skipQuest, "Skip this quest for this character. A missing pickup is learned from actual NPC offers before and after a hand-in, not from this button.")
    frame.scan = ns.UIButton(frame, "Scan guide", 80, function() ns.ScanGuideProgress() end)
    frame.scan:SetHeight(24); frame.scan:SetPoint("BOTTOMLEFT", 207, 12)
    frame.back = ns.UIButton(frame, "‹", 24, function() ns.PreviewGuideStep(-1) end)
    frame.back:SetHeight(24); frame.back:SetPoint("BOTTOMLEFT", 6, 12)
    frame.next = ns.UIButton(frame, "›", 24, function() ns.PreviewGuideStep(1) end)
    frame.next:SetHeight(24); frame.next:SetPoint("BOTTOMRIGHT", -6, 12)
    frame:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        if self.state and self.state.stop then GameTooltip:AddLine(self.state.stop.label, 1, 0.82, 0.3, true) end
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
