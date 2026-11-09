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

local function nextDisplayedStops(state, limit)
    if not state or state.stop.historyPreview or not ns.selectedRoute or type(ns.selectedRoute.stops) ~= "table" then return {} end
    local stops, goal = ns.selectedRoute.stops, ns.GuideDestination(state.stop)
    if not goal then return {} end
    for index, stop in ipairs(stops) do
        if stop == goal or stop.id == goal.id and stop.kind == goal.kind
            and (not stop.memberKey or not goal.memberKey or stop.memberKey == goal.memberKey) then
            local result = {}
            for nextIndex = index + 1, #stops do
                result[#result + 1] = stops[nextIndex]
                if #result >= (limit or 1) then break end
            end
            return result
        end
    end
    local result = {}
    for index = 2, math.min(#stops, (limit or 1) + 1) do result[#result + 1] = stops[index] end
    return result
end

local function nextDisplayedStop(state)
    return nextDisplayedStops(state, 1)[1]
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

local glanceFallback = {
    accept = "!", turnin = "?", turninIncomplete = "?", kill = "x", collect = "+",
    use = "+", talk = "...", travel = ">", party = "&", farm = "$", dungeon = "D",
    fly = ">", hearth = ">", teleport = ">", ship = ">", wait = "&",
}

local presentationSymbols = {
    ["travel-fly"] = "fly", ["travel-hearth"] = "hearth",
    ["travel-teleport"] = "teleport", ["travel-ship"] = "ship",
    ["travel-walk"] = "travel", wait = "wait", farm = "farm", dungeon = "dungeon",
}

local function symbolKindForPresentation(stop, presentation)
    return presentationSymbols[presentation and presentation.kind]
        or ns.StepSymbolKind(stop, presentation and presentation.facts)
end

local function setGeneratedIcon(texture, name)
    local path
    if type(ns.StepIconTexture) == "function" then path = ns.StepIconTexture(name)
    else
        local icons = ns.STEP_ICON_TEXTURES
        path = type(icons) == "table" and icons[name]
    end
    if type(path) ~= "string" or path == "" then return false end
    local asset = path .. ".tga"
    local fileID = type(GetFileIDFromPath) == "function" and ns.ReadPublic(GetFileIDFromPath, asset)
    if type(fileID) == "number" and fileID > 0 then texture:SetTexture(fileID)
    else texture:SetTexture(asset) end
    return true
end

local function glanceText(presentation, state)
    local facts, stop = presentation.facts or {}, presentation.goal or presentation.stop
    local object = facts.target or facts.item or facts.npc or facts.objective and facts.objective.text
        or stop.label or stop.title or presentation.title
    if type(object) ~= "string" or object == "" then object = presentation.what or presentation.title end
    for _, verb in ipairs({"Kill ", "Collect ", "Talk to ", "Turn in ", "Go to "}) do
        if object:sub(1, #verb) == verb then object = object:sub(#verb + 1); break end
    end
    local parts = {object}
    if facts.progress and not string.match(presentation.kind or "", "^travel%-") then
        parts[#parts + 1] = facts.progress
    end
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

local function peekInstruction(stop)
    local facts = ns.GuideStepFacts(stop)
    local presentation = ns.GuideStepPresentation(stop, facts, ns.routeSelection, ns.selectedRoute)
    local object = facts.target or facts.item or facts.npc or facts.objective and facts.objective.text
        or stop.targetName or stop.itemName or stop.npcName or stop.title
    if type(object) ~= "string" or object == "" then object = presentation and presentation.what or stop.label or "the next step" end
    local action = facts.action or stop.action
    local verb = stop.kind == "a" and "Accept"
        or stop.kind == "t" and "Turn in"
        or action == "kill" and "Kill"
        or (action == "collect" or action == "loot" or action == "gather" or action == "item") and "Collect"
        or action == "use" and "Use"
        or action == "talk" and "Talk to"
        or action == "escort" and "Escort"
        or action == "interact" and "Interact with"
        or (stop.kind == "travel" or stop.kind == "f") and "Go to"
    if not verb and presentation and presentation.what and not string.find(presentation.what, "^Work on ") then
        return presentation.what
    end
    verb = verb or "Go to"
    local count = facts.progress or (facts.need and tostring(facts.need))
        or (stop.quantity and tostring(stop.quantity))
    return verb .. " " .. object .. (count and (" " .. count) or "")
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
        return {visible = true, busy = true, status = scan and "Scanning guide…" or work.status or "Loading route…",
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

function ns.DrawNavigationArrow(angle, icon, color)
    icon = icon or ns.navigation.icon
    local cosine, sine = math.cos(angle), math.sin(angle)
    local shape = {{0, 21}, {-12, -6}, {0, 0}, {12, -6}, {0, 21}}
    local scale = finite(icon:GetWidth()) and math.max(1, icon:GetWidth() / 48) or 1
    color = color or {1, 0.82, 0.30, 1}
    for index = 1, #shape - 1 do
        local line = icon.lines[index]
        if not line then line = icon:CreateLine(nil, "OVERLAY"); icon.lines[index] = line end
        local a, b = shape[index], shape[index + 1]
        line:SetThickness(3 * scale); line:SetColorTexture(unpack(color))
        line:SetStartPoint("CENTER", icon, (a[1] * cosine - a[2] * sine) * scale, (a[1] * sine + a[2] * cosine) * scale)
        line:SetEndPoint("CENTER", icon, (b[1] * cosine - b[2] * sine) * scale, (b[1] * sine + b[2] * cosine) * scale)
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
    local zoneExit = state.stop and state.stop.reasonCode == "zone-exit"
    if frame.zoneExit ~= zoneExit then frame.zoneExit = zoneExit; ns.LayoutNavigation() end
    frame.next.caption:SetText(zoneExit and "Follow" or ">")
    frame.next:SetWidth(zoneExit and 62 or 24)
    ns.RefreshEliteSpawnMarkers()
    frame:SetShown(state.visible == true and ns.Option("routeArrow") and not ns.guideWindowHidden)
    if ns.UpdateSuggestionChipAnchor then ns.UpdateSuggestionChipAnchor() end
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
    frame.modeVisible = modeVisible == true
    frame.step:SetText(presentation.stepLine or "")
    frame.stepButton:SetShown(true)
    local progress = presentation.progress and not string.match(presentation.kind or "", "^travel%-")
        and (" " .. presentation.progress) or ""
    frame.status:SetText(presentation.what .. progress)
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
        local key = symbolKindForPresentation(state.stop, presentation)
        local glyph, texture = ns.StepSymbolFor(key)
        frame.icon:ClearAllPoints(); frame.icon:SetSize(20, 20); frame.icon:SetPoint("TOPLEFT", 14, -50)
        frame.kindIcon:SetSize(20, 20); frame.kindIcon:SetTexture(texture or presentation.icon)
        frame.kindIcon:SetVertexColor(unpack(ns.UIColors.text))
        frame.kindIcon:SetShown(texture ~= nil and not state.busy)
        frame.symbol:SetText(texture and "" or glanceFallback[key] or glyph or ">")
        frame.symbol:SetTextColor(unpack(ns.UIColors.text))
        frame.symbol:SetShown(texture == nil and not state.busy)
        frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", 42, -50)
        frame.status:SetSize(frame:GetWidth() - 56, 22); frame.status:SetWordWrap(false)
        frame.status:SetText(glanceText(presentation, state))
        frame.status:SetTextColor(unpack(ns.UIColors.text))
        frame.status:Show()
        frame.context:Hide(); frame.distance:Hide(); frame.peek:Hide()
        local upcoming = nextDisplayedStops(state, 2)
        for index = 1, 2 do
            local row, stop = frame.glanceRows[index], upcoming[index]
            if stop then
                local facts = ns.GuideStepFacts(stop)
                local nextPresentation = ns.GuideStepPresentation(stop, facts, ns.routeSelection, ns.selectedRoute)
                local rowKey = symbolKindForPresentation(stop, nextPresentation)
                local rowGlyph, rowTexture = ns.StepSymbolFor(rowKey)
                row.icon:SetTexture(rowTexture or nextPresentation.icon)
                row.icon:SetVertexColor(unpack(ns.UIColors.muted))
                row.icon:SetShown(rowTexture ~= nil)
                row.symbol:SetText(rowTexture and "" or glanceFallback[rowKey] or rowGlyph or ">")
                row.symbol:SetTextColor(unpack(ns.UIColors.muted))
                row.symbol:SetShown(rowTexture == nil)
                row.text:SetText(glanceText(nextPresentation, {stop = stop}))
                row.text:SetTextColor(unpack(ns.UIColors.muted))
                row.frame:Show()
            else
                row.text:SetText(""); row.frame:Hide()
            end
        end
    else
        frame.icon:ClearAllPoints(); frame.icon:SetSize(48, 48); frame.icon:SetPoint("TOPLEFT", 16, -50)
        frame.kindIcon:SetSize(34, 34)
        frame.kindIcon:SetVertexColor(1, 1, 1, 1)
        frame.symbol:SetTextColor(1, 1, 1, 1)
        frame.context:Show(); frame.distance:Show()
        frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", 82, -52)
        frame.status:SetSize(frame:GetWidth() - 96, 18)
        frame.context:SetShown(presentation.why ~= nil and presentation.why ~= "")
        frame.distance:Show()
        frame.status:Show()
        for _, row in ipairs(frame.glanceRows) do
            row.icon:SetVertexColor(1, 1, 1, 1)
            row.text:SetText(""); row.frame:Hide()
        end
    end
    local nextStop = not glance and ns.Option("guidePeek") and nextDisplayedStop(state) or nil
    if nextStop then
        local nextWhat = peekInstruction(nextStop)
        local nextZone = nextStop.mapID and ns.MapName(nextStop.mapID)
        frame.peek:SetText("Next: " .. (nextWhat or nextStop.title or "Next step")
            .. (nextZone and (" (" .. nextZone .. ")") or ""))
        frame.peek:SetShown(true)
    else frame.peek:SetText(""); frame.peek:Hide() end
    updateTooltip(frame)
    ns.HideNavigationGeometry(frame.icon)
    frame.icon:SetShown(true)
    if not glance then
        local kind = symbolKindForPresentation(state.stop, presentation)
        local glyph, texture = ns.StepSymbolFor(kind)
        frame.kindIcon:SetTexture(texture or presentation.icon)
        frame.kindIcon:SetVertexColor(unpack(ns.UIColors.text))
        frame.kindIcon:SetShown(texture ~= nil and not state.busy)
        frame.symbol:SetText(texture and "" or glanceFallback[kind] or glyph or "•")
        frame.symbol:SetTextColor(unpack(ns.UIColors.text))
        frame.symbol:SetShown(texture == nil and not state.busy)
    end
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
    frame.continue:SetShown(continue and not zoneExit); frame.continue:SetEnabled(continue and not zoneExit)
    frame.skipStep:SetShown(not continue and not zoneExit); frame.skipQuest:SetShown(not continue and not zoneExit)
    frame.back:SetShown(not zoneExit); frame.next:SetShown(true)
    frame.next:SetEnabled(zoneExit and state.stop.nextGuide ~= nil or not zoneExit and not state.idle and state.stop.kind ~= "loading")
    if zoneExit then ns.UIHelp(frame.next, "Follow the next zone guide.")
    else ns.UIHelp(frame.next, "Preview the next guide step.") end
    local paused = ns.PausedSessionCheckpoint and ns.PausedSessionCheckpoint()
    frame.stop:SetEnabled(not state.idle or paused ~= nil)
    frame.pause.caption:SetText(frame.pause.hasIcon and "" or (paused and ">" or "II"))
    frame.pause:SetEnabled(paused ~= nil or not state.idle and not state.busy)
    ns.UIHelp(frame.pause, paused and "Resume your saved guide using current progress." or "Save your guide, pause it and see your session summary.")
    ns.UIHelp(frame.close, paused and "Close this window. Your paused guide stays saved." or "Exit guide. Stop and close this window.")
    if state.idle then frame.symbol:Hide(); frame.context:SetText("") end
    if state.busy and not glance then frame.symbol:SetShown(not ns.DrawNavigationSpinner(frame.icon)) end
end

function ns.SaveNavigationPosition()
    local frame = ns.navigation
    frame:StopMovingOrSizing()
    local point, _, relative, x, y = frame:GetPoint()
    if ns.Public(point) and ns.Public(relative) and type(point) == "string" and type(relative) == "string"
        and finite(x) and finite(y) then ns.db.arrowPosition = {point = point, relative = relative, x = x, y = y} end
    if ns.UpdateSuggestionChipAnchor then ns.UpdateSuggestionChipAnchor() end
end

function ns.LayoutNavigation(layoutFrame)
    local frame = ns.navigation
    if not frame or not frame.layoutReady then return end
    local width = frame:GetWidth()
    if not finite(width) then return end
    local glance = ns.Option("guideGlance") == true
    local chipHeight = ns.SuggestionChipStripHeight and ns.SuggestionChipStripHeight() or 0
    if layoutFrame == frame and not glance then
        frame.normalHeight = math.max(168, math.min(480, (frame:GetHeight() or 168) - chipHeight))
    end
    local baseHeight = glance and 150 or (frame.normalHeight or 168)
    local wantedHeight = baseHeight + chipHeight
    if math.abs((frame:GetHeight() or 0) - wantedHeight) > 0.5 then frame:SetHeight(wantedHeight) end
    local left = 82
    local offset = (width - 360) / 2
    frame.title:SetWidth(width - 108); frame.step:SetWidth(width - 28)
    frame.stepButton:SetWidth(width - 28)
    if glance then
        frame.icon:ClearAllPoints(); frame.icon:SetSize(20, 20); frame.icon:SetPoint("TOPLEFT", 14, -50)
        frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", 42, -50)
        frame.status:SetSize(width - 56, 22); frame.status:SetWordWrap(false)
        for index, row in ipairs(frame.glanceRows) do
            row.frame:ClearAllPoints(); row.frame:SetPoint("TOPLEFT", 14, -50 - index * 22)
            row.frame:SetSize(width - 28, 22)
            row.icon:ClearAllPoints(); row.icon:SetSize(20, 20); row.icon:SetPoint("LEFT", 0, 0)
            row.symbol:ClearAllPoints(); row.symbol:SetPoint("CENTER", row.icon)
            row.text:ClearAllPoints(); row.text:SetPoint("LEFT", 28, 0)
            row.text:SetSize(width - 56, 22); row.text:SetWordWrap(false)
        end
    else
        frame.icon:ClearAllPoints(); frame.icon:SetSize(48, 48); frame.icon:SetPoint("TOPLEFT", 16, -50)
        frame.status:ClearAllPoints(); frame.status:SetPoint("TOPLEFT", left, -52)
        frame.status:SetSize(width - left - 14, 18); frame.status:SetWordWrap(false)
    end
    frame.context:ClearAllPoints(); frame.context:SetPoint("TOPLEFT", left, -71)
    frame.context:SetSize(width - left - 14, 14); frame.context:SetWordWrap(false)
    frame.distance:ClearAllPoints(); frame.distance:SetPoint("TOPLEFT", left, -87)
    frame.distance:SetWidth(width - left - 14); frame.distance:SetWordWrap(false)
    frame.peek:ClearAllPoints(); frame.peek:SetPoint("TOPLEFT", left, -103)
    frame.peek:SetWidth(width - left - 14); frame.peek:SetWordWrap(false)
    local training = frame.trainingLayout
    local buttonBottom = chipHeight + 8
    frame.skipStep:SetWidth(training and 84 or 80)
    frame.skipStep:ClearAllPoints(); frame.skipStep:SetPoint("BOTTOMLEFT", offset + (training and 36 or 42), buttonBottom)
    frame.skipQuest:SetWidth(training and 88 or 80)
    frame.skipQuest:ClearAllPoints(); frame.skipQuest:SetPoint("BOTTOMLEFT", offset + (training and 124 or 128), buttonBottom)
    frame.continue:ClearAllPoints(); frame.continue:SetPoint("BOTTOMLEFT", offset + 42, buttonBottom)
    frame.back:ClearAllPoints(); frame.back:SetPoint("BOTTOMLEFT", offset + 12, buttonBottom)
    frame.next:ClearAllPoints()
    if frame.zoneExit then frame.next:SetPoint("BOTTOMRIGHT", -12, buttonBottom)
    else frame.next:SetPoint("BOTTOMLEFT", offset + 316, buttonBottom) end
    frame.scan:ClearAllPoints(); frame.scan:SetPoint("BOTTOMRIGHT", -38, buttonBottom)
    frame.tip.point = {"TOPLEFT", frame.work}
    frame.questItem:SetWidth(width); frame.questItem.caption:SetWidth(width - 50)
    ns.LayoutAreaObjectives(width)
    if ns.UpdateSuggestionChipAnchor then ns.UpdateSuggestionChipAnchor() end
end

function ns.SaveNavigationSize()
    local frame = ns.navigation
    frame:StopMovingOrSizing()
    local width, height = frame:GetWidth(), frame:GetHeight()
    if finite(width) and finite(height) then
        local chipHeight = ns.SuggestionChipStripHeight and ns.SuggestionChipStripHeight() or 0
        local baseHeight = height - chipHeight
        if ns.Option("guideGlance") ~= true then frame.normalHeight = math.max(168, math.min(480, baseHeight)) end
        ns.db.arrowSize = {width = math.max(360, math.min(720, width)), height = frame.normalHeight or 168}
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
    frame.pause = ns.UIButton(frame, "II", 26, function()
        if ns.PausedSessionCheckpoint() then ns.ResumeGuideSession() else ns.PauseGuideSession() end
    end)
    frame.pause:SetHeight(20); frame.pause:SetPoint("TOPRIGHT", -80, -8)
    frame.pause.caption:ClearAllPoints(); frame.pause.caption:SetPoint("CENTER")
    frame.pause.caption:SetSize(24, 18); frame.pause.caption:SetFont("Fonts\\ARIALN.TTF", 10, "")
    frame.pause.icon = frame.pause:CreateTexture(nil, "ARTWORK")
    frame.pause.icon:SetSize(16, 16); frame.pause.icon:SetPoint("CENTER")
    frame.pause.hasIcon = setGeneratedIcon(frame.pause.icon, "pause")
    if not frame.pause.hasIcon then
        local pausePath = "Interface\\TimeManager\\PauseButton"
        local pauseID = type(GetFileIDFromPath) == "function" and ns.ReadPublic(GetFileIDFromPath, pausePath)
        if type(pauseID) == "number" and pauseID > 0 then
            frame.pause.icon:SetTexture(pauseID); frame.pause.hasIcon = true
        else frame.pause.icon:Hide() end
    end
    if frame.pause.hasIcon then
        frame.pause.icon:SetVertexColor(unpack(ns.UIColors.gold)); frame.pause.caption:SetText("")
    else frame.pause.caption:SetText("II") end
    ns.UIHelp(frame.pause, "Pause or resume your guide.")
    frame.menu = ns.UIButton(frame, "", 26, function()
        if ns.window and not ns.window:IsShown() then ns.ToggleWindow(); ns.SetFilter("recommended")
        elseif ns.window then ns.window:Hide() end
    end)
    frame.menu:SetHeight(20); frame.menu:SetPoint("TOPRIGHT", -48, -8)
    frame.menu.caption:ClearAllPoints(); frame.menu.caption:SetPoint("CENTER")
    frame.menu.caption:SetSize(24, 18); frame.menu.caption:SetFont("Fonts\\ARIALN.TTF", 10, "")
    frame.menu.bars = {}
    for index = 1, 3 do
        local bar = frame.menu:CreateTexture(nil, "ARTWORK")
        bar:SetColorTexture(unpack(ns.UIColors.gold))
        bar:SetSize(12, 2); bar:SetPoint("CENTER", 0, (index - 2) * 4)
        frame.menu.bars[index] = bar
    end
    frame.menu.icon = frame.menu:CreateTexture(nil, "ARTWORK")
    frame.menu.icon:SetSize(16, 16); frame.menu.icon:SetPoint("CENTER")
    frame.menu.hasIcon = setGeneratedIcon(frame.menu.icon, "menu")
    if frame.menu.hasIcon then
        frame.menu.icon:SetVertexColor(unpack(ns.UIColors.gold))
        for _, bar in ipairs(frame.menu.bars) do bar:Hide() end
    else frame.menu.icon:Hide() end
    ns.UIHelp(frame.menu, "Open the guide hub.")
    frame.close = ns.UIClose(frame, function()
        ns.guideWindowHidden = true; frame:Hide()
        if ns.UpdateSuggestionChipAnchor then ns.UpdateSuggestionChipAnchor() end
    end)
    frame.close:SetSize(20, 18); frame.close:SetPoint("TOPRIGHT", -12, -9)
    frame.close.caption:ClearAllPoints(); frame.close.caption:SetPoint("CENTER"); frame.close.caption:SetSize(16, 14)
    frame.close.caption:SetText("x")
    frame.close.icon = frame.close:CreateTexture(nil, "ARTWORK")
    frame.close.icon:SetSize(14, 14); frame.close.icon:SetPoint("CENTER")
    frame.close.hasIcon = setGeneratedIcon(frame.close.icon, "close")
    if frame.close.hasIcon then
        frame.close.icon:SetVertexColor(unpack(ns.UIColors.gold)); frame.close.caption:SetText("")
    else frame.close.icon:Hide() end
    ns.UIHelp(frame.close, "Hide the guide window.")
    frame.step = ns.UILabel(frame, nil, 10, ns.UIColors.muted); frame.step:SetPoint("TOPLEFT", 14, -30); frame.step:SetSize(332, 14)
    frame.stepButton = CreateFrame("Button", nil, frame)
    frame.stepButton:SetSize(332, 14); frame.stepButton:SetPoint("TOPLEFT", 14, -30)
    frame.stepButton:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    frame.stepButton:SetScript("OnMouseUp", function(_, button)
        if button == "RightButton" then
            if ns.routeSelection and (ns.routeSelection.mode == "zone" or ns.routeSelection.mode == "bundle") then
                frame.modeMenu:Show()
            end
        else
            ns.SetOption("guideGlance", not ns.Option("guideGlance")); ns.UpdateNavigation(); ns.LayoutNavigation()
        end
    end)
    ns.UIHelp(frame.stepButton, "Click to switch between full and Glance step text. Right-click to choose zone routing mode.")
    frame.modeMenu = CreateFrame("Frame", nil, frame, "BackdropTemplate")
    frame.modeMenu:SetSize(156, 62); frame.modeMenu:SetFrameStrata("DIALOG"); ns.UIPanel(frame.modeMenu)
    frame.modeMenu:SetPoint("TOPLEFT", frame.stepButton, "BOTTOMLEFT", 0, -2)
    frame.modeMenu.efficient = ns.UIButton(frame.modeMenu, "Efficient", 140, function()
        if ns.routeSelection then ns.SetGuideEfficiencyMode(ns.routeSelection, "efficient") end
        frame.modeMenu:Hide(); ns.UpdateNavigation()
    end)
    frame.modeMenu.efficient:SetPoint("TOPLEFT", 8, -4); frame.modeMenu.efficient:SetHeight(24)
    frame.modeMenu.complete = ns.UIButton(frame.modeMenu, "Complete", 140, function()
        if ns.routeSelection then ns.SetGuideEfficiencyMode(ns.routeSelection, "complete") end
        frame.modeMenu:Hide(); ns.UpdateNavigation()
    end)
    frame.modeMenu.complete:SetPoint("TOPLEFT", 8, -32); frame.modeMenu.complete:SetHeight(24)
    frame.modeMenu:Hide()
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
    frame.glanceRows = {}
    for index = 1, 2 do
        local row = {frame = CreateFrame("Frame", nil, frame)}
        row.icon = row.frame:CreateTexture(nil, "ARTWORK"); row.icon:SetSize(20, 20); row.icon:SetPoint("LEFT", 0, 0)
        row.symbol = row.frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        row.symbol:SetFont("Fonts\\FRIZQT__.TTF", 18, "OUTLINE"); row.symbol:SetPoint("CENTER", row.icon)
        row.text = ns.UILabel(row.frame, nil, 11, ns.UIColors.muted)
        row.text:SetPoint("LEFT", 28, 0); row.text:SetSize(304, 22); row.text:SetWordWrap(false)
        row.frame:SetSize(332, 22); row.frame:SetPoint("TOPLEFT", 14, -50 - index * 22)
        row.frame:Hide(); frame.glanceRows[index] = row
    end
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
    frame.scan.hasIcon = setGeneratedIcon(frame.scan.icon, "scan")
    if frame.scan.hasIcon then frame.scan.icon:SetVertexColor(unpack(ns.UIColors.gold))
    else frame.scan.icon:SetTexture("Interface\\Buttons\\UI-RefreshButton") end
    ns.UIHelp(frame.scan, "Re-scan quest log and rebuild the route")
    frame.continue = ns.UIButton(frame, "Continue anyway", 166, ns.ContinueGuideAnyway, true)
    frame.continue:SetHeight(24); frame.continue:SetPoint("BOTTOMLEFT", 42, 8); frame.continue:Hide()
    ns.UIHelp(frame.continue, "Include quests outside the recommended level range for this guide. Pickup requirements and manual skips still apply; elite quests may need a party. Saved across reloads; Stop guide restores the normal range.")
    frame.back = ns.UIButton(frame, "<", 24, function() ns.PreviewGuideStep(-1) end)
    frame.back:SetHeight(24); frame.back:SetPoint("BOTTOMLEFT", 12, 8)
    frame.next = ns.UIButton(frame, ">", 24, function()
        local stop = frame.state and frame.state.stop
        if stop and stop.reasonCode == "zone-exit" and stop.nextGuide then ns.RequestStartRoute(stop.nextGuide)
        else ns.PreviewGuideStep(1) end
    end)
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
    frame.normalHeight = frame:GetHeight()
    frame.layoutReady = true
    ns.LayoutNavigation()
    ns.UpdateNavigationBackground()
    frame.titleToggle = CreateFrame("Button", nil, frame)
    frame.titleToggle:SetSize(158, 22); frame.titleToggle:SetPoint("TOPLEFT", 10, -6)
    frame.titleToggle:SetScript("OnMouseUp", function(_, button)
        if button == "RightButton" then ns.SetOption("guideOpaque", not ns.Option("guideOpaque")); ns.UpdateNavigationBackground() end
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
    if ns.UpdateSuggestionChipAnchor then ns.UpdateSuggestionChipAnchor() end
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
