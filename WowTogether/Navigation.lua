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

local function updateTooltip(frame, opening)
    if not GameTooltip then return end
    if not opening and ns.ReadPublic(GameTooltip.IsOwned, GameTooltip, frame) ~= true then return end
    local state = frame.state
    local stop = state and state.stop
    local description = stop and ns.GuideStepDescription(stop) or ""
    local status = stop and stop.kind == "notice" and state.status or ""
    local context = frame.context and frame.context:GetText() or ""
    local previous = frame.tooltipContent
    if not opening and previous and previous[1] == description and previous[2] == status and previous[3] == context then return end
    if opening or type(GameTooltip.ClearLines) ~= "function" then GameTooltip:SetOwner(frame, "ANCHOR_RIGHT")
    else GameTooltip:ClearLines() end
    frame.tooltipContent = {description, status, context}
    if description ~= "" then GameTooltip:AddLine(description, 1, 1, 1, true) end
    if status ~= "" then GameTooltip:AddLine(status, 1, 0.82, 0.3, true) end
    if context ~= "" then GameTooltip:AddLine(context, 0.8, 0.85, 0.9, true) end
    GameTooltip:AddLine("Drag to move.", 1, 1, 1, true)
    GameTooltip:Show()
end

function ns.RouteContext(stop, mapID, facts)
    if stop.professionStep then return stop.description end
    if stop.unsafeTransit then return "No mapped bypass is known. Follow roads around the town." end
    if ns.IsClassTrainingStep(stop) then
        local training = stop.kind == "trainer" and stop or stop.goal
        return "Optional • level " .. training.trainingLevel .. " training check.\nTrain manually; Done training resumes quests."
    end
    if stop.confirmation then
        return "Check this NPC's offers; pickup is unconfirmed.\n" .. ns.StopLocationText(stop, mapID)
    end
    if stop.kind == "loading" then
        return stop.action == "scan" and "Checking quest progress…" or "Preparing your route…"
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
    if stop.kind == "notice" and not stop.sourceStop then
        if ns.routeSelection and ns.routeSelection.mode == "dungeon" then return ns.routePaused or "Finish the dungeon quests." end
        return "Scan can reconsider skipped steps.\nSettings can reset all skips for this character."
    end
    if stop.kind == "corpse" then
        return (stop.approximate and "Recorded death position; check nearby." or "Your quest guide is retained.")
            .. "\nResume questing after recovering your body."
    end
    if stop.flightPlan then
        local plan = stop.flightPlan
        return (plan.measured and "Timed flight: ~" or "Estimated flight: ") .. ns.FormatTravelDuration(plan.flightSeconds)
            .. "; journey ~" .. ns.FormatTravelDuration(plan.seconds)
            .. "\nFly to " .. plan.destination.name .. (plan.walkingSeconds and plan.walkingSeconds > plan.seconds
                and ("; saves ~" .. ns.FormatTravelDuration(plan.walkingSeconds - plan.seconds) .. ".") or ".")
    end
    if stop.travelLeg then return "Travel towards " .. ns.MapName(stop.goal.mapID) .. ".\n" .. (stop.travelLeg.method == "walk"
        and "Use the crossing; follow roads and terrain." or "Board the correct transport; waiting time varies.") end
    if stop.action == "flight-check" then return "Check this nearby flight master.\nUnlock status has not been confirmed." end
    if ns.routePaused and not stop.sourceStop then
        if ns.routeSelection and ns.routeSelection.fixedRoute then return ns.routePaused end
        if ns.routeSelection and ns.routeSelection.mode == "dungeon" then return ns.routePaused end
        return "Waiting for confirmed party progress.\nYour last route is retained."
    end
    facts = facts or ns.GuideStepFacts(stop)
    stop = facts.stop
    local reason = ns.GuideStepHint(stop, facts)
    if stop.unknownLocation then reason = "Exact location missing; use the quest tracker."
    end
    local forPlayer = ns.SafeTitle(stop.forPlayer)
    local who = forPlayer and (" • For " .. forPlayer) or ""
    local context = ns.StopLocationText(stop, mapID) .. who
    local useful, exception = ns.LevelingValue(stop.id)
    local quest, low = ns.CatalogueQuest(stop.id), ns.PreferredQuestLevels()
    if useful == true and exception and quest and low and (quest.level or 0) > 0 and quest.level < low then
        facts.lowerLevelPrerequisite = quest.level
        facts.lowerLevelClassQuest = ns.IsClassQuest(stop.id)
        if not facts.lowerLevelClassQuest then exception = "Prerequisite: " .. exception end
    end
    if ns.routeSelection and ns.routeSelection.catchupRequired and ns.routeSelection.catchupRequired[stop.id] then
        reason = "Finish this prerequisite to catch your party up."
    elseif useful == true and exception then reason = exception
    elseif useful == false then reason = stop.kind == "t" and "Ready for turn-in; collect its reward."
        or "Quest-log work you chose to keep in this route." end
    local groupWarning = ns.QuestGroupWarning(stop.id)
    if groupWarning then reason = groupWarning .. " " .. reason end
    return reason .. "\n" .. context
end

function ns.NavigationState()
    if not ns.Option("routeArrow") and not ns.Option("standaloneArrow") then return {status = "Disabled in settings"} end
    if ns.guideStopped and not ns.routeSelection and not ns.routePlanning then
        return {visible = ns.guideWindowIdle == true, idle = true, status = "Choose a guide to begin.",
            stop = {id = 0, kind = "notice", title = "No guide selected", mapID = 0}}
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
    if not profession and not ns.navigationPreview and not confirmation then stop = ns.ClassTrainingDestination(stop) end
    stop = ns.CorpseDestination() or ns.TravelDestination(stop)
    local flight = ns.FlightState()
    if flight then
        return {visible = true, stop = stop or {title = "Flight travel", kind = "f", label = "Flying", id = 0, mapID = 0},
            status = "Flying to " .. flight.name, flight = flight}
    end
    if not stop then return {status = "No route selected"} end
    local state = {visible = true, stop = stop}
    if stop.professionStep and stop.unknownLocation then state.status = stop.label; return state end
    if stop.unsafeTransit then state.status = stop.label; return state end
    if stop.kind == "notice" then state.status = stop.label; return state end
    if stop.transportWaiting then state.status = stop.label; return state end
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
    frame:SetShown(state.visible == true and ns.Option("routeArrow"))
    ns.UpdateStandaloneArrow(state)
    ns.UpdateQuestItemButton(state)
    ns.UpdateAreaObjectives(state)
    ns.UpdateGuideTip(state)
    if not state.visible then ns.HideNavigationGeometry(frame.icon); return end
    frame.title:SetText(state.stop.title)
    local facts = ns.GuideStepFacts(state.stop)
    local clock = ns.NavigationTravelTime(state)
    local distance = state.distance and (ns.FormatDistance(state.distance) .. (state.arrived and " • Here" or "")) or ""
    if facts.progress then distance = distance .. (distance ~= "" and " • " or "") .. facts.progress end
    frame.distance:SetText(state.flight and clock or distance .. (clock and (distance ~= "" and " • " or "") .. clock or ""))
    frame.status:SetText(state.angle and ns.GuideStepAction(state.stop, facts) or state.status)
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    frame.context:SetText(ns.RouteContext(state.stop, mapID, facts))
    updateTooltip(frame)
    ns.HideNavigationGeometry(frame.icon)
    local separate = ns.standaloneNavigation and ns.standaloneNavigation:IsShown()
    frame.icon:SetShown(not separate)
    if frame.separateArrow ~= separate then
        frame.separateArrow = separate
        ns.LayoutNavigation()
    end
    frame.symbol:SetText("…"); frame.symbol:SetTextColor(0.96, 0.76, 0.35, 1)
    frame.symbol:SetShown(state.angle == nil and not state.arrived and not state.flight)
    frame.step:SetText(state.idle and "" or state.stop.kind == "loading" and (state.stop.action == "scan" and "Checking guide progress" or "Preparing route") or state.stop.historyPreview and "Previous step" or
        (ns.routeSelection and ns.routeSelection.mode == "travel" and "Travel guide • Levels 1–60" or
            ns.navigationPreview and "Step preview" or
            (state.stop.npcVisitPickup and "Collect quests at this NPC" or state.stop.guideStep and ("Zone guide step " .. state.stop.guideStep) or "Current guide step")))
    local training = ns.IsClassTrainingStep(state.stop)
    if training then frame.step:SetText("Optional class training") end
    frame.skipStep.caption:SetText(training and "Skip training" or "Skip step")
    frame.skipQuest.caption:SetText(training and "Done training" or "Skip quest")
    if frame.trainingLayout ~= training then
        frame.trainingLayout = training
        ns.LayoutNavigation()
    end
    if facts.lowerLevelPrerequisite and not state.stop.historyPreview and not ns.navigationPreview then
        frame.step:SetText((state.stop.guideStep and ("Step " .. state.stop.guideStep .. " • ") or "")
            .. (facts.lowerLevelClassQuest and "Class progression • Lv " or "Lower-level prerequisite • Lv ") .. facts.lowerLevelPrerequisite)
    end
    if state.areaObjectives and #state.areaObjectives > 1 then
        frame.title:SetText("Complete nearby objectives")
        frame.step:SetText(#state.areaObjectives .. " tasks • Arrow points to the current objective")
    end
    local editable = not ns.navigationPreview and not state.flight and state.stop.kind ~= "corpse"
        and (state.stop.kind ~= "notice" or state.stop.id > 0) and state.stop.kind ~= "loading"
    local quests = not (ns.routeSelection and ns.routeSelection.mode == "travel")
    frame.skipStep:SetEnabled(editable and quests); frame.skipQuest:SetEnabled(editable and quests); frame.scan:SetEnabled(not state.idle and not state.flight and state.stop.kind ~= "loading")
    frame.back:SetEnabled(not state.idle and state.stop.kind ~= "loading"); frame.next:SetEnabled(not state.idle and state.stop.kind ~= "loading")
    if ns.routeSelection and ns.routeSelection.mode == "profession" then
        local route = ns.selectedRoute
        frame.step:SetText("Personal crafting guide")
        frame.skipStep.caption:SetText("Next recipe"); frame.skipQuest.caption:SetText("Materials"); frame.scan.caption:SetText("Refresh")
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
        frame.scan.caption:SetText("Scan guide")
        if frame.professionControls then
            ns.UIHelp(frame.skipStep, "Skip this guide step. Training stops postpone their personal reminder.")
            ns.UIHelp(frame.skipQuest, "Skip this quest. During training, Done training resumes quests.")
            ns.UIHelp(frame.scan, "Check current quest progress while keeping the guide order.")
            frame.professionControls = nil
        end
    end
    frame.stop:SetEnabled(not state.idle)
    if state.idle then frame.symbol:Hide(); frame.context:SetText("") end
    if not separate then
        if state.busy then frame.symbol:SetShown(not ns.DrawNavigationSpinner(frame.icon))
        elseif state.arrived then ns.DrawNavigationArrow(math.pi)
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
    local width, height = frame:GetWidth(), frame:GetHeight()
    if not finite(width) or not finite(height) then return end
    local left = frame.separateArrow and 14 or 82
    local offset = (width - 360) / 2
    frame.title:SetWidth(width - 138); frame.step:SetWidth(width - 28)
    frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", left, -52)
    frame.status:SetSize(width - left - 14, math.max(28, height - 140))
    frame.distance:ClearAllPoints(); frame.distance:SetPoint("BOTTOMLEFT", left, 72)
    frame.distance:SetWidth(width - left - 14)
    frame.context:ClearAllPoints(); frame.context:SetPoint("BOTTOMLEFT", 14, 40)
    frame.context:SetWidth(width - 28)
    local training = frame.trainingLayout
    frame.skipStep:SetWidth(training and 84 or 80)
    frame.skipStep:ClearAllPoints(); frame.skipStep:SetPoint("BOTTOMLEFT", offset + (training and 36 or 42), 8)
    frame.skipQuest:SetWidth(training and 88 or 80)
    frame.skipQuest:ClearAllPoints(); frame.skipQuest:SetPoint("BOTTOMLEFT", offset + (training and 124 or 128), 8)
    frame.scan:ClearAllPoints(); frame.scan:SetPoint("BOTTOMLEFT", offset + (training and 218 or 214), 8)
    frame.back:ClearAllPoints(); frame.back:SetPoint("BOTTOMLEFT", offset + 12, 8)
    frame.next:ClearAllPoints(); frame.next:SetPoint("BOTTOMLEFT", offset + 316, 8)
    frame.tip:SetWidth(width); frame.tip.text:SetWidth(width - 44)
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
    for _, panel in ipairs({frame, frame.tip, frame.work, frame.questItem}) do
        panel:SetBackdropColor(color[1], color[2], color[3], alpha)
    end
    ns.UIButtonTone(frame.background, opaque)
    ns.UIHelp(frame.background, opaque and "Guide background: opaque. Click for see-through."
        or "Guide background: see-through. Click for opaque.")
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
    frame.title:SetSize(306, 18); frame.title:SetWordWrap(false)
    frame.background = ns.UIButton(frame, "BG", 22, function() ns.SetOption("guideOpaque", not ns.Option("guideOpaque")) end)
    frame.background:SetHeight(18); frame.background:SetPoint("TOPRIGHT", -72, -10)
    frame.background.caption:ClearAllPoints(); frame.background.caption:SetPoint("CENTER")
    frame.background.caption:SetSize(18, 14); frame.background.caption:SetFont("Fonts\\ARIALN.TTF", 9, "")
    frame.stop = ns.UIButton(frame, "ST", 24, function() ns.StopGuide(false) end)
    frame.stop:SetHeight(18); frame.stop:SetPoint("TOPRIGHT", -42, -10)
    frame.stop.caption:ClearAllPoints(); frame.stop.caption:SetPoint("CENTER")
    frame.stop.caption:SetSize(18, 14); frame.stop.caption:SetFont("Fonts\\ARIALN.TTF", 9, "")
    ns.UIHelp(frame.stop, "Stop guide. Keep this window open.")
    frame.close = ns.UIClose(frame, function() ns.StopGuide(true) end)
    frame.close:SetSize(20, 18); frame.close:SetPoint("TOPRIGHT", -10, -10)
    frame.close.caption:ClearAllPoints(); frame.close.caption:SetPoint("CENTER"); frame.close.caption:SetSize(16, 14)
    ns.UIHelp(frame.close, "Exit guide. Stop and close this window.")
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
    frame.skipQuest = ns.UIButton(frame, "Skip quest", 80, function()
        if ns.IsClassTrainingStep(frame.state and frame.state.stop) then ns.FinishClassTraining(true)
        else ns.SkipGuide("quest") end
    end)
    frame.skipQuest:SetHeight(24); frame.skipQuest:SetPoint("BOTTOMLEFT", 128, 8)
    ns.UIHelp(frame.skipStep, "Skip this step for this character. Training stops postpone this reminder until the next even level; they never skip a quest or learn a prerequisite.")
    ns.UIHelp(frame.skipQuest, "Skip the current quest. During a training stop, Done training records your personal check and resumes quests; no skills are purchased automatically.")
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
    ns.CreateQuestItemButton(frame)
    ns.CreateAreaObjectives(frame)
    frame:SetResizable(true)
    if type(frame.SetResizeBounds) == "function" then frame:SetResizeBounds(360, 168, 720, 480) end
    frame.grip = CreateFrame("Button", nil, frame)
    frame.grip:SetSize(14, 14); frame.grip:SetPoint("BOTTOMRIGHT", -2, 2)
    frame.grip.icon = frame.grip:CreateTexture(nil, "ARTWORK"); frame.grip.icon:SetAllPoints()
    frame.grip.icon:SetTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    frame.grip:SetScript("OnMouseDown", function(_, key) if key == "LeftButton" then frame:StartSizing("BOTTOMRIGHT") end end)
    frame.grip:SetScript("OnMouseUp", function(_, key) if key == "LeftButton" then ns.SaveNavigationSize() end end)
    frame:SetScript("OnSizeChanged", function()
        local width, height = frame:GetWidth(), frame:GetHeight()
        if not finite(width) or not finite(height) then return end
        local w, h = math.max(360, math.min(720, width)), math.max(168, math.min(480, height))
        if w ~= width or h ~= height then frame:SetSize(w, h) end
        ns.LayoutNavigation()
    end)
    local size = ns.db.arrowSize
    if type(size) == "table" and finite(size.width) and finite(size.height) then
        frame:SetSize(math.max(360, math.min(720, size.width)), math.max(168, math.min(480, size.height)))
    end
    frame.layoutReady = true
    ns.LayoutNavigation()
    ns.UpdateNavigationBackground()
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

function ns.ToggleNavigation() ns.SetOption("routeArrow", not ns.Option("routeArrow")) end

function ns.OpenGuideWindow()
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
    if state.distance then output("Arrow distance: " .. string.format("%.0f yards", state.distance)) end
    output("Standalone arrow: " .. (ns.Option("standaloneArrow") and "on" or "off"))
    output("Travel network: " .. (ns.Option("travelNetwork") and (ns.travelNetworkStatus or "Ready; select a route.") or "off"))
    output("Route lines draw on the world map; the minimap button opens the addon.")
end
