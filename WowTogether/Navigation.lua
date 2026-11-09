local addonName, ns = ...

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

function ns.FormatDistance(value)
    if ns.Option("distanceUnits") == "metres" then return string.format("%.0f m", value * 0.9144) end
    return string.format("%.0f yd", value)
end

function ns.FormatTravelDuration(value)
    return string.format("%dm %02ds", math.floor(value / 60), math.floor(value % 60))
end

function ns.NavigationTravelTime(state)
    local flight = state.flight
    if flight then
        if finite(flight.remaining) and flight.remaining > 0 then
            return (flight.estimated and "Est. flight " or "Flight ~") .. ns.FormatTravelDuration(flight.remaining) .. " left"
        end
        if finite(flight.elapsed) then return ns.FormatTravelDuration(flight.elapsed) .. " flying" end
        return "Flight time unavailable"
    end
    if finite(state.walkSeconds) and state.walkSeconds > 0 and not state.arrived then
        return "~" .. ns.FormatTravelDuration(state.walkSeconds) .. " travel"
    end
end

local function nextDisplayedStop(state)
    if not state or state.stop.historyPreview or not ns.selectedRoute or type(ns.selectedRoute.stops) ~= "table" then return nil end
    local stops, goal = ns.selectedRoute.stops, ns.GuideDestination(state.stop)
    for index, stop in ipairs(stops) do
        if stop == goal or stop.id == goal.id and stop.kind == goal.kind
            and (not stop.memberKey or not goal.memberKey or stop.memberKey == goal.memberKey) then
            return stops[index + 1]
        end
    end
    return stops[2]
end

local function updateTooltip(frame, opening)
    if not GameTooltip then return end
    if not opening and ns.ReadPublic(GameTooltip.IsOwned, GameTooltip, frame) ~= true then return end
    local state = frame.state
    local stop = state and state.stop
    local presentation = frame.presentation or stop and ns.GuideStepPresentation(stop, nil, ns.routeSelection, ns.selectedRoute, state)
    local content = presentation and (presentation.title .. "\n" .. ns.GuidePresentationTooltip(presentation, false)) or ""
    local previous = frame.tooltipContent
    if not opening and previous == content then return end
    if opening or type(GameTooltip.ClearLines) ~= "function" then GameTooltip:SetOwner(frame, "ANCHOR_RIGHT")
    else GameTooltip:ClearLines() end
    frame.tooltipContent = content
    if presentation then
        GameTooltip:AddLine(presentation.title, 1, 0.82, 0.3, true)
        for _, line in ipairs(ns.GuidePresentationTooltipLines(presentation, false)) do GameTooltip:AddLine(line, 1, 1, 1, true) end
    end
    GameTooltip:Show()
end

local function glanceDistance(yards)
    if not finite(yards) then return nil end
    if yards < 1000 then return string.format("%.0f yd", yards) end
    return string.format("%.1f km", yards / 1093.6133)
end

local function glanceText(presentation, state)
    local facts, stop = presentation.facts or {}, presentation.goal or presentation.stop
    local object = facts.target or facts.item or facts.npc or facts.objective and facts.objective.text
        or stop.label or stop.title or presentation.title
    if type(object) ~= "string" or object == "" then object = presentation.what or presentation.title end
    object = string.gsub(object, "^(Kill|Collect|Talk to|Turn in|Go to) ", "")
    local parts = {object}
    if facts.progress then parts[#parts + 1] = facts.progress end
    local travelKind = presentation.kind == "travel-fly" and "fly"
        or presentation.kind == "travel-hearth" and "hearth"
        or presentation.kind == "travel-walk" and "walk"
        or presentation.kind == "travel-ship" and "ship"
        or presentation.kind == "travel-teleport" and "teleport"
        or state.flight and "fly"
    if travelKind then parts[#parts + 1] = travelKind end
    local distance = glanceDistance(state.distance)
    if distance then parts[#parts + 1] = distance
    elseif presentation.location then parts[#parts + 1] = presentation.location end
    return table.concat(parts, " · ")
end

-- Compatibility surface for older integrations. New renderers consume fields.
function ns.RouteContext(stop, mapID, facts, travelDistance)
    local presentation = ns.GuideStepPresentation(stop, facts, ns.routeSelection, ns.selectedRoute)
    if not presentation then return end
    if presentation.why and presentation.status then return presentation.why .. "\n" .. presentation.status end
    return presentation.why or presentation.status or presentation.location
end

function ns.NavigationState()
    if not ns.Option("routeArrow") and not ns.Option("standaloneArrow") then return {status = "Disabled in settings"} end
    if ns.guideStopped and not ns.routeSelection and not ns.routePlanning then
        local saved = ns.PausedSessionCheckpoint and ns.PausedSessionCheckpoint()
        return {visible = ns.guideWindowIdle == true, idle = true, status = saved and "Session saved. Resume when ready." or "Choose a guide to begin.",
            stop = {id = 0, kind = "notice", title = saved and saved.guide.title or "No guide selected", mapID = 0}}
    end
    if ns.guideScanning or ns.routePlanning then
        local scan = ns.guideScanning
        local work = scan or ns.routePlanning
        return {visible = true, busy = true, status = scan and "Scanning guide…" or "Loading route…",
            stop = {id = 0, kind = "loading", action = scan and "scan" or "plan", title = work.guide.title}}
    end
    if ns.routeSelection and ns.routeSelection.mode == "travel" then ns.UpdateTravelGuide(ns.routeSelection, true) end
    local route = ns.routeSelection and ns.selectedRoute
    local profession = ns.routeSelection and ns.routeSelection.mode == "profession"
    local confirmation = not profession and ns.CurrentQuestConfirmation()
    local stop = ns.navigationPreview and ns.navigationPreview.stop or confirmation and not confirmation.unknownLocation and confirmation
        or route and route.stops and route.stops[1]
    if not stop and ns.routeSelection then
        local pending = route and route.pendingStop
        stop = {kind = "notice", id = pending and pending.id or 0, title = pending and pending.title or ns.routeSelection.title, mapID = route and route.mapID or 0,
            stepKind = pending and pending.kind, guideStep = pending and pending.guideStep,
            sourceStop = pending,
            learnedSource = pending and pending.learnedSource,
            x = 0, y = 0, label = ns.routePaused or "Waiting for the next available guide step."}
    end
    if not profession and not ns.navigationPreview then
        stop = ns.InventoryServiceDestination(stop)
        if not confirmation and not ns.IsInventoryServiceStep(stop) then stop = ns.ClassTrainingDestination(stop) end
    end
    stop = ns.CorpseDestination() or ns.TravelDestination(stop)
    local flight = ns.FlightState()
    if flight then
        return {visible = true, stop = stop or {title = "Flight travel", kind = "f", label = "Flying", id = 0, mapID = 0},
            status = "Flying to " .. flight.name, flight = flight}
    end
    if not stop then return {status = "No route selected"} end
    local state = {visible = true, stop = stop}
    if stop.professionStep and stop.unknownLocation then state.status = stop.label; return state end
    if stop.unsafeTransit or stop.unsafeTerrain then state.status = stop.label; return state end
    if stop.kind == "notice" then state.status = stop.label; return state end
    if stop.transportWaiting or stop.personalTransport then state.status = stop.label; return state end
    if stop.positionUnavailable then state.status = "Corpse position unavailable on this build"; return state end
    if ns.routePaused and not (confirmation and not confirmation.unknownLocation) and stop.kind ~= "corpse" then state.status = "Waiting for party updates"; return state end
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
    state.walkSeconds = state.distance / ns.TravelWalkSpeed()
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
    ns.RefreshEliteSpawnMarkers()
    frame:SetShown(state.visible == true and ns.Option("routeArrow") and not ns.guideWindowHidden)
    ns.UpdateStandaloneArrow(state)
    ns.UpdateQuestItemButton(state)
    ns.UpdateAreaObjectives(state)
    ns.UpdateGuideTip(state)
    if not state.visible then ns.HideNavigationGeometry(frame.icon); return end
    local facts = ns.GuideStepFacts(state.stop)
    local presentation = ns.GuideStepPresentation(state.stop, facts, ns.routeSelection, ns.selectedRoute, state)
    frame.presentation = presentation
    frame.title:SetText(presentation.title)
    local guide = ns.routeSelection
    local modeVisible = guide and (guide.mode == "zone" or guide.mode == "bundle")
    frame.modeButton:SetShown(modeVisible == true)
    if modeVisible then
        local mode = ns.GuideEfficiencyMode(guide)
        frame.modeButton.caption:SetText(mode == "complete" and "Eff" or "Full")
        ns.UIHelp(frame.modeButton, mode == "complete" and "Switch to Efficient routing for this guide." or "Complete the zone, including lower-value quests after better work.")
    end
    frame.step:SetText(presentation.stepLine or "")
    frame.stepButton:SetShown(true)
    frame.status:SetText(presentation.what .. (presentation.progress and (" " .. presentation.progress) or ""))
    frame.status:SetTextColor(unpack(ns.UIColors.text))
    frame.context:SetText(presentation.why or "")
    frame.distance:SetText(presentation.status .. (presentation.time and (" • " .. presentation.time) or "")
        .. ((presentation.kind == "travel-hearth" or presentation.kind == "travel-teleport") and " • Route re-plans after you land" or ""))
    local statusColor = presentation.statusColor == "green" and ns.UIColors.success
        or presentation.statusColor == "gold" and ns.UIColors.gold
        or presentation.statusColor == "muted" and ns.UIColors.muted or ns.UIColors.text
    frame.distance:SetTextColor(unpack(statusColor))
    local glance = ns.Option("guideGlance") == true
    frame.glance = glance
    if glance then
        local key = ns.StepSymbolKind(state.stop, presentation.facts)
        local glyph, texture = ns.StepSymbolFor(key)
        frame.kindIcon:SetSize(20, 20); frame.kindIcon:SetTexture(texture or presentation.icon)
        frame.kindIcon:SetShown(texture ~= nil and not state.busy)
        frame.symbol:SetText(glyph or "➤"); frame.symbol:SetShown(texture == nil and not state.busy)
        frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", 54, -58)
        frame.status:SetSize(frame:GetWidth() - 66, 28); frame.status:SetWordWrap(false)
        frame.status:SetText(glanceText(presentation, state))
        frame.status:Show()
        frame.context:Hide(); frame.distance:Hide(); frame.peek:Hide()
    else
        frame.kindIcon:SetSize(34, 34)
        frame.context:Show(); frame.distance:Show()
        frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", frame.separateArrow and 14 or 82, -52)
        frame.status:SetSize(frame:GetWidth() - (frame.separateArrow and 28 or 96), 18)
        frame.context:SetShown(presentation.why ~= nil and presentation.why ~= "")
        frame.distance:Show()
        frame.status:Show()
    end
    local nextStop = not glance and ns.Option("guidePeek") and nextDisplayedStop(state) or nil
    if nextStop then
        local nextWhat = ns.StopInstruction(nextStop)
        local nextZone = nextStop.mapID and ns.MapName(nextStop.mapID)
        frame.peek:SetText("Next: " .. (nextWhat or nextStop.title or "Next step")
            .. (nextZone and (" (" .. nextZone .. ")") or ""))
        frame.peek:SetShown(true)
    else frame.peek:SetText(""); frame.peek:Hide() end
    updateTooltip(frame)
    ns.HideNavigationGeometry(frame.icon)
    local separate = ns.standaloneNavigation and ns.standaloneNavigation:IsShown()
    frame.icon:SetShown(not separate)
    if frame.separateArrow ~= separate then
        frame.separateArrow = separate
        ns.LayoutNavigation()
    end
    local iconOnly = state.arrived or state.flight or presentation.kind == "travel-hearth" or presentation.kind == "travel-teleport"
    frame.kindIcon:SetTexture(presentation.icon)
    frame.kindIcon:SetShown(state.angle == nil and iconOnly and not state.busy)
    frame.symbol:SetText("…"); frame.symbol:SetTextColor(0.96, 0.76, 0.35, 1)
    frame.symbol:SetShown(state.busy and state.angle == nil or state.angle == nil and not iconOnly and not state.busy)
    local training = ns.IsClassTrainingStep(state.stop)
    local service = ns.IsInventoryServiceStep(state.stop)
    frame.skipStep.caption:SetText(service and "Skip visit" or training and "Skip training" or "Skip step")
    frame.skipQuest.caption:SetText(service and "Done" or training and "Done training" or "Skip quest")
    if frame.trainingLayout ~= (training or service) then
        frame.trainingLayout = training or service
        ns.LayoutNavigation()
    end
    local editable = not ns.navigationPreview and not state.flight and state.stop.kind ~= "corpse"
        and (state.stop.kind ~= "notice" or state.stop.id > 0) and state.stop.kind ~= "loading"
    local quests = not (ns.routeSelection and ns.routeSelection.mode == "travel")
    frame.skipStep:SetEnabled(editable and quests); frame.skipQuest:SetEnabled(editable and quests); frame.scan:SetEnabled(not state.idle and not state.flight and state.stop.kind ~= "loading")
    if state.stop.flightDiscovery then
        frame.skipStep.caption:SetText("Keep walking")
        frame.skipStep:SetEnabled(editable); frame.skipQuest:SetEnabled(false)
    end
    frame.back:SetEnabled(not state.idle and state.stop.kind ~= "loading"); frame.next:SetEnabled(not state.idle and state.stop.kind ~= "loading")
    if service then
        frame.skipStep:SetEnabled(editable); frame.skipQuest:SetEnabled(editable)
        frame.back:SetEnabled(false); frame.next:SetEnabled(false)
        if not frame.serviceControls then
            ns.UIHelp(frame.skipStep, "Dismiss this vendor visit and resume your guide. No quest is skipped.")
            ns.UIHelp(frame.skipQuest, "Finish this vendor visit and resume your guide. Buy, sell and repair manually.")
            frame.serviceControls = true
        end
    elseif frame.serviceControls then
        frame.serviceControls = nil
        ns.UIHelp(frame.skipStep, "Skip this guide step. Training stops postpone their personal reminder.")
        ns.UIHelp(frame.skipQuest, "Skip this quest. During training, Done training resumes quests.")
    end
    if ns.routeSelection and ns.routeSelection.mode == "profession" then
        local route = ns.selectedRoute
        frame.step:SetText("Personal crafting guide")
        frame.skipStep.caption:SetText("Next recipe"); frame.skipQuest.caption:SetText("Materials")
        frame.skipStep:SetEnabled(editable and route and route.recipe ~= nil)
        frame.skipQuest:SetEnabled(route and route.materials and #route.materials > 0)
        frame.back:SetEnabled(false); frame.next:SetEnabled(false)
        if not frame.professionControls then
            ns.UIHelp(frame.skipStep, "Try another suitable recipe at your current skill. This does not change your skill or quest skips.")
            ns.UIHelp(frame.skipQuest, "Open the materials and buy list for this crafting batch.")
            ns.UIHelp(frame.scan, "Refresh your current profession skill, recipes and materials.")
            frame.professionControls = true
        end
    else
        if frame.professionControls then
            ns.UIHelp(frame.skipStep, "Skip this guide step. Training stops postpone their personal reminder.")
            ns.UIHelp(frame.skipQuest, "Skip this quest. During training, Done training resumes quests.")
            ns.UIHelp(frame.scan, "Check current quest progress while keeping the guide order.")
            frame.professionControls = nil
        end
    end
    local continue = ns.CanContinueGuideAnyway() and not ns.navigationPreview and not state.flight
        and state.stop.kind == "notice" and not state.busy
    frame.continue:SetShown(continue); frame.continue:SetEnabled(continue)
    frame.skipStep:SetShown(not continue); frame.skipQuest:SetShown(not continue)
    local paused = ns.PausedSessionCheckpoint and ns.PausedSessionCheckpoint()
    frame.stop:SetEnabled(not state.idle or paused ~= nil)
    frame.pause.caption:SetText(paused and "▶" or "⏸")
    frame.pause:SetEnabled(paused ~= nil or not state.idle and not state.busy)
    ns.UIHelp(frame.pause, paused and "Resume your saved guide using current progress." or "Save your guide, pause it and see your session summary.")
    ns.UIHelp(frame.close, paused and "Close this window. Your paused guide stays saved." or "Exit guide. Stop and close this window.")
    if state.idle then frame.symbol:Hide(); frame.context:SetText("") end
    if not separate then
        if state.busy then frame.symbol:SetShown(not ns.DrawNavigationSpinner(frame.icon))
        elseif state.arrived then frame.symbol:Hide()
        elseif state.angle ~= nil then ns.DrawNavigationArrow(state.angle) end
    end
end

function ns.SaveNavigationPosition()
    local frame = ns.navigation
    frame:StopMovingOrSizing()
    local point, _, relative, x, y = frame:GetPoint()
    if ns.Public(point) and ns.Public(relative) and type(point) == "string" and type(relative) == "string"
        and finite(x) and finite(y) then ns.db.arrowPosition = {point = point, relative = relative, x = x, y = y} end
end

function ns.LayoutNavigation()
    local frame = ns.navigation
    if not frame or not frame.layoutReady then return end
    local width = frame:GetWidth()
    if not finite(width) then return end
    local left = frame.separateArrow and 14 or 82
    local offset = (width - 360) / 2
    frame.title:SetWidth(width - 108); frame.step:SetWidth(width - 28)
    frame.stepButton:SetWidth(width - 28)
    frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", left, -52)
    frame.status:SetSize(width - left - 14, 18); frame.status:SetWordWrap(false)
    frame.context:ClearAllPoints(); frame.context:SetPoint("TOPLEFT", left, -71)
    frame.context:SetSize(width - left - 14, 14); frame.context:SetWordWrap(false)
    frame.distance:ClearAllPoints(); frame.distance:SetPoint("TOPLEFT", left, -87)
    frame.distance:SetWidth(width - left - 14); frame.distance:SetWordWrap(false)
    frame.peek:ClearAllPoints(); frame.peek:SetPoint("TOPLEFT", left, -103)
    frame.peek:SetWidth(width - left - 14); frame.peek:SetWordWrap(false)
    local training = frame.trainingLayout
    frame.skipStep:SetWidth(training and 84 or 80)
    frame.skipStep:ClearAllPoints(); frame.skipStep:SetPoint("BOTTOMLEFT", offset + (training and 36 or 42), 8)
    frame.skipQuest:SetWidth(training and 88 or 80)
    frame.skipQuest:ClearAllPoints(); frame.skipQuest:SetPoint("BOTTOMLEFT", offset + (training and 124 or 128), 8)
    frame.continue:ClearAllPoints(); frame.continue:SetPoint("BOTTOMLEFT", offset + 42, 8)
    frame.back:ClearAllPoints(); frame.back:SetPoint("BOTTOMLEFT", offset + 12, 8)
    frame.next:ClearAllPoints(); frame.next:SetPoint("BOTTOMLEFT", offset + 316, 8)
    frame.tip.point = {"TOPLEFT", frame.work}
    frame.questItem:SetWidth(width); frame.questItem.caption:SetWidth(width - 50)
    ns.LayoutAreaObjectives(width)
end

function ns.SaveNavigationSize()
    local frame = ns.navigation
    frame:StopMovingOrSizing()
    local width, height = frame:GetWidth(), frame:GetHeight()
    if finite(width) and finite(height) then
        ns.db.arrowSize = {width = math.max(360, math.min(720, width)), height = math.max(168, math.min(480, height))}
    end
    ns.SaveNavigationPosition()
end

function ns.UpdateNavigationBackground()
    local frame = ns.navigation
    if not frame then return end
    local opaque = ns.Option("guideOpaque")
    local color, alpha = ns.UIColors.background, opaque and 1 or 0.18
    -- Fade only the fill, never the text, arrow or child controls.
    for _, panel in ipairs({frame, frame.work, frame.questItem}) do
        panel:SetBackdropColor(color[1], color[2], color[3], alpha)
    end
    frame.solid = opaque
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
    frame.title:SetSize(158, 18); frame.title:SetWordWrap(false)
    frame.modeButton = ns.UIButton(frame, "Full", 48, function()
        local guide = ns.routeSelection
        if guide then ns.SetGuideEfficiencyMode(guide, ns.GuideEfficiencyMode(guide) == "efficient" and "complete" or "efficient") end
    end)
    frame.modeButton:SetHeight(18); frame.modeButton:SetPoint("BOTTOMRIGHT", -88, 8)
    frame.modeButton.caption:ClearAllPoints(); frame.modeButton.caption:SetPoint("CENTER")
    frame.modeButton.caption:SetSize(44, 14); frame.modeButton.caption:SetFont("Fonts\\ARIALN.TTF", 8, "")
    ns.UIHelp(frame.modeButton, "Choose Efficient or Complete zone routing.")
    frame.pause = ns.UIButton(frame, "⏸", 26, function()
        if ns.PausedSessionCheckpoint() then ns.ResumeGuideSession() else ns.PauseGuideSession() end
    end)
    frame.pause:SetHeight(20); frame.pause:SetPoint("TOPRIGHT", -80, -8)
    frame.pause.caption:ClearAllPoints(); frame.pause.caption:SetPoint("CENTER")
    frame.pause.caption:SetSize(24, 18); frame.pause.caption:SetFont("Fonts\\ARIALN.TTF", 14, "")
    ns.UIHelp(frame.pause, "Pause or resume your guide.")
    frame.menu = ns.UIButton(frame, "☰", 26, function()
        if ns.window and not ns.window:IsShown() then ns.ToggleWindow(); ns.SetFilter("recommended")
        elseif ns.window then ns.window:Hide() end
    end)
    frame.menu:SetHeight(20); frame.menu:SetPoint("TOPRIGHT", -48, -8)
    frame.menu.caption:ClearAllPoints(); frame.menu.caption:SetPoint("CENTER")
    frame.menu.caption:SetSize(24, 18); frame.menu.caption:SetFont("Fonts\\ARIALN.TTF", 14, "")
    ns.UIHelp(frame.menu, "Open the guide hub.")
    frame.close = ns.UIClose(frame, function() ns.guideWindowHidden = true; frame:Hide() end)
    frame.close:SetSize(20, 18); frame.close:SetPoint("TOPRIGHT", -12, -9)
    frame.close.caption:ClearAllPoints(); frame.close.caption:SetPoint("CENTER"); frame.close.caption:SetSize(16, 14)
    ns.UIHelp(frame.close, "Hide the guide window.")
    frame.step = ns.UILabel(frame, nil, 10, ns.UIColors.muted); frame.step:SetPoint("TOPLEFT", 14, -30); frame.step:SetSize(332, 14)
    frame.stepButton = CreateFrame("Button", nil, frame)
    frame.stepButton:SetSize(332, 14); frame.stepButton:SetPoint("TOPLEFT", 14, -30)
    frame.stepButton:SetScript("OnClick", function()
        ns.SetOption("guideGlance", not ns.Option("guideGlance")); ns.UpdateNavigation()
    end)
    ns.UIHelp(frame.stepButton, "Click to switch between full and Glance step text.")
    ns.UIDivider(frame, -48)
    frame.icon = CreateFrame("Frame", nil, frame); frame.icon:SetSize(48, 48); frame.icon:SetPoint("TOPLEFT", 16, -50)
    frame.icon.lines = {}
    frame.kindIcon = frame.icon:CreateTexture(nil, "ARTWORK"); frame.kindIcon:SetSize(34, 34); frame.kindIcon:SetPoint("CENTER")
    frame.symbol = frame.icon:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    frame.symbol:SetFont("Fonts\\FRIZQT__.TTF", 26, "OUTLINE"); frame.symbol:SetPoint("CENTER")
    frame.distance = ns.UILabel(frame, nil, 11, ns.UIColors.gold)
    frame.distance:SetPoint("TOPLEFT", 82, -87); frame.distance:SetSize(264, 14); frame.distance:SetWordWrap(false)
    frame.status = ns.UILabel(frame, nil, 12)
    frame.status:SetPoint("TOPLEFT", 82, -52)
    frame.status:SetSize(264, 18); frame.status:SetWordWrap(false); frame.status:SetJustifyV("TOP")
    frame.context = ns.UILabel(frame, nil, 10, ns.UIColors.muted)
    frame.context:SetPoint("TOPLEFT", 82, -71)
    frame.context:SetSize(264, 14); frame.context:SetWordWrap(false); frame.context:SetJustifyV("TOP")
    frame.peek = ns.UILabel(frame, nil, 10, ns.UIColors.muted)
    frame.peek:SetPoint("TOPLEFT", 82, -103); frame.peek:SetSize(264, 14); frame.peek:SetWordWrap(false)
    frame.skipStep = ns.UIButton(frame, "Skip step", 80, function() ns.SkipGuide("step") end)
    frame.skipStep:SetHeight(24); frame.skipStep:SetPoint("BOTTOMLEFT", 42, 8)
    frame.skipQuest = ns.UIButton(frame, "Skip quest", 80, function()
        if ns.IsInventoryServiceStep(frame.state and frame.state.stop) then ns.FinishInventoryService()
        elseif ns.IsClassTrainingStep(frame.state and frame.state.stop) then ns.FinishClassTraining(true)
        else ns.SkipGuide("quest") end
    end)
    frame.skipQuest:SetHeight(24); frame.skipQuest:SetPoint("BOTTOMLEFT", 128, 8)
    ns.UIHelp(frame.skipStep, "Skip this step for this character. Training stops postpone this reminder until the next even level; they never skip a quest or learn a prerequisite.")
    ns.UIHelp(frame.skipQuest, "Skip the current quest. During a training stop, Done training records your personal check and resumes quests; no skills are purchased automatically.")
    frame.scan = ns.UIButton(frame, "", 22, function() ns.ScanGuideProgress() end)
    frame.scan:SetHeight(18); frame.scan:SetPoint("BOTTOMRIGHT", -38, 8)
    frame.scan.icon = frame.scan:CreateTexture(nil, "ARTWORK"); frame.scan.icon:SetSize(14, 14); frame.scan.icon:SetPoint("CENTER")
    frame.scan.icon:SetTexture("Interface\\Buttons\\UI-RefreshButton")
    ns.UIHelp(frame.scan, "Re-scan quest log and rebuild the route")
    frame.continue = ns.UIButton(frame, "Continue anyway", 166, ns.ContinueGuideAnyway, true)
    frame.continue:SetHeight(24); frame.continue:SetPoint("BOTTOMLEFT", 42, 8); frame.continue:Hide()
    ns.UIHelp(frame.continue, "Include quests outside the recommended level range for this guide. Pickup requirements and manual skips still apply; elite quests may need a party. Saved across reloads; Stop guide restores the normal range.")
    frame.back = ns.UIButton(frame, "‹", 24, function() ns.PreviewGuideStep(-1) end)
    frame.back:SetHeight(24); frame.back:SetPoint("BOTTOMLEFT", 12, 8)
    frame.next = ns.UIButton(frame, "›", 24, function() ns.PreviewGuideStep(1) end)
    frame.next:SetHeight(24); frame.next:SetPoint("BOTTOMRIGHT", -12, 8)
    frame.background = {OnClick = function() ns.SetOption("guideOpaque", not ns.Option("guideOpaque")) end}
    frame.stop = {enabled = true, OnClick = function()
        ns.StopGuide(false)
        if ns.window and not ns.window:IsShown() then ns.ToggleWindow() end
        if ns.window and ns.window:IsShown() then ns.SetFilter("recommended") end
    end}
    function frame.stop:SetEnabled(value) self.enabled = value end
    function frame.stop:IsEnabled() return self.enabled ~= false end
    frame.tip = ns.SuggestionChipFacade("guideTip")
    frame.tip.text = {text = ""}; frame.tip.point = {"TOPLEFT", frame.work}
    frame.tip.close = {OnClick = ns.DismissGuideTip}
    function frame.tip:IsShown() return self.visible == true end
    function frame.tip:OnMouseUp(button)
        if button == "LeftButton" and self.value and self.value.kind == "service" then ns.AcceptInventoryServiceTip(self.value) end
    end
    ns.CreateQuestItemButton(frame)
    ns.CreateAreaObjectives(frame)
    ns.EnableWindowResize(frame, {minWidth = 360, minHeight = 168, maxWidth = 720, maxHeight = 480,
        layout = ns.LayoutNavigation, onFinish = ns.SaveNavigationSize})
    local size = ns.db.arrowSize
    if type(size) == "table" and finite(size.width) and finite(size.height) then
        frame:SetSize(math.max(360, math.min(720, size.width)), math.max(168, math.min(480, size.height)))
    end
    frame.layoutReady = true
    ns.LayoutNavigation()
    ns.UpdateNavigationBackground()
    frame.titleToggle = CreateFrame("Button", nil, frame)
    frame.titleToggle:SetSize(158, 22); frame.titleToggle:SetPoint("TOPLEFT", 10, -6)
    frame.titleToggle:SetScript("OnMouseUp", function(_, button)
        if button == "RightButton" then ns.SetOption("guideOpaque", not ns.Option("guideOpaque")) end
    end)
    ns.UIHelp(frame.titleToggle, "Right-click the title bar to toggle a solid background.")
    frame:SetScript("OnEnter", function(self)
        updateTooltip(self, true)
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

function ns.ToggleNavigation()
    local enabled = not ns.Option("routeArrow")
    if enabled then ns.guideWindowHidden = nil end
    ns.SetOption("routeArrow", enabled)
end

function ns.OpenGuideWindow()
    ns.guideWindowHidden = nil
    if not ns.routeSelection and not ns.routePlanning then
        ns.guideStopped, ns.guideWindowIdle = true, true
    end
    if not ns.navigation then ns.CreateNavigation() end
    if not ns.Option("routeArrow") then ns.SetOption("routeArrow", true) end
    ns.UpdateNavigation()
    ns.navigation:Raise()
    if ns.window then ns.window:Hide() end
end

function ns.NavigationDiagnostics(output)
    local state = ns.navigation and ns.navigation.state or ns.NavigationState()
    output("Navigation arrow: " .. state.status)
    output(ns.stepIconStatus or "Step icons: not probed")
    if state.distance then output("Arrow distance: " .. string.format("%.0f yards", state.distance)) end
    output("Standalone arrow: " .. (ns.Option("standaloneArrow") and "on" or "off"))
    output("Travel network: " .. (ns.Option("travelNetwork") and (ns.travelNetworkStatus or "Ready; select a route.") or "off"))
    output("Route lines draw on the world map; the minimap button opens the addon.")
end
