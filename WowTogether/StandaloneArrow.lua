local addonName, ns = ...

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

local function defaultPosition(frame)
    frame:ClearAllPoints()
    if ns.navigation then frame:SetPoint("BOTTOM", ns.navigation, "TOP", 0, 8)
    else frame:SetPoint("CENTER", UIParent, "CENTER", 0, 180) end
end

function ns.SaveStandaloneArrowPosition(frame)
    frame:StopMovingOrSizing()
    local left = ns.ReadPublic(frame.GetLeft, frame)
    local bottom = ns.ReadPublic(frame.GetBottom, frame)
    if finite(left) and finite(bottom) then
        frame:ClearAllPoints()
        frame:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", left, bottom)
        ns.db.standaloneArrowPosition = {left = left, bottom = bottom}
        return
    end
    local point, _, relative, x, y = frame:GetPoint()
    if ns.Public(point) and ns.Public(relative) and type(point) == "string" and type(relative) == "string"
        and finite(x) and finite(y) then
        ns.db.standaloneArrowPosition = {point = point, relative = relative, x = x, y = y}
    end
end

function ns.ResetStandaloneArrowPosition()
    ns.db.standaloneArrowPosition = nil
    if ns.standaloneNavigation then defaultPosition(ns.standaloneNavigation) end
end

function ns.CreateStandaloneArrow()
    if ns.standaloneNavigation then return end
    local frame = CreateFrame("Frame", "WowTogetherStandaloneArrow", UIParent)
    ns.standaloneNavigation = frame
    frame:SetSize(104, 130); defaultPosition(frame)
    frame:SetClampedToScreen(true); frame:SetFrameStrata("MEDIUM")
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", function(self) ns.SaveStandaloneArrowPosition(self) end)
    local saved = ns.db.standaloneArrowPosition
    if type(saved) == "table" then
        if finite(saved.left) and finite(saved.bottom) then
            frame:ClearAllPoints(); frame:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", saved.left, saved.bottom)
        elseif type(saved.point) == "string" and type(saved.relative) == "string" and finite(saved.x) and finite(saved.y) then
            frame:ClearAllPoints(); frame:SetPoint(saved.point, UIParent, saved.relative, saved.x, saved.y)
        end
    end

    frame.icon = CreateFrame("Frame", nil, frame); frame.icon:SetSize(80, 80); frame.icon:SetPoint("TOP", 0, 0); frame.icon.lines = {}
    frame.kindIcon = frame.icon:CreateTexture(nil, "ARTWORK"); frame.kindIcon:SetSize(38, 38); frame.kindIcon:SetPoint("CENTER")
    frame.symbol = ns.UILabel(frame.icon, "GameFontNormalLarge", 42, ns.UIColors.gold); frame.symbol:SetPoint("CENTER")
    frame.distance = ns.UILabel(frame, nil, 15, ns.UIColors.text); frame.distance:SetPoint("TOP", frame.icon, "BOTTOM", 0, -2)
    frame.time = ns.UILabel(frame, nil, 11, ns.UIColors.muted); frame.time:SetPoint("TOP", frame.distance, "BOTTOM", 0, -1)
    frame.reason = ns.UILabel(frame, nil, 10, ns.UIColors.muted)
    frame.reason:SetSize(220, 36); frame.reason:SetWordWrap(true); frame.reason:SetJustifyV("TOP"); frame.reason:Hide()
    frame.training = CreateFrame("Frame", nil, frame); frame.training:SetSize(176, 24)
    frame.training:SetPoint("TOP", frame.time, "BOTTOM", 0, -5)
    frame.training.done = ns.UIButton(frame.training, "Done", 80, function()
        if ns.IsInventoryServiceStep(frame.state and frame.state.stop) then ns.FinishInventoryService()
        else ns.FinishClassTraining(true) end
    end)
    frame.training.done:SetPoint("LEFT"); frame.training.done:SetHeight(22)
    frame.training.skip = ns.UIButton(frame.training, "Skip", 80, function()
        if ns.IsInventoryServiceStep(frame.state and frame.state.stop) then ns.FinishInventoryService()
        else ns.FinishClassTraining(false) end
    end)
    frame.training.skip:SetPoint("RIGHT"); frame.training.skip:SetHeight(22)
    frame.training:Hide()
    frame.tip = ns.SuggestionChipFacade("guideTip")
    frame.tip.text = {text = ""}
    frame.tip.close = {OnClick = ns.DismissGuideTip}
    function frame.tip:IsShown() return self.visible == true end
    function frame.tip:OnMouseUp(button)
        if button == "LeftButton" and self.value and self.value.kind == "service" then ns.AcceptInventoryServiceTip(self.value) end
    end
    frame:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        local presentation = self.state and ns.GuideStepPresentation(self.state.stop, nil,
            ns.routeSelection, ns.selectedRoute, self.state) or self.presentation
        if presentation then
            GameTooltip:AddLine(presentation.title, 1, 0.82, 0.3, true)
            for _, line in ipairs(ns.GuidePresentationTooltipLines(presentation, "arrow")) do GameTooltip:AddLine(line, 1, 1, 1, true) end
        end
        GameTooltip:Show()
    end)
    frame:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    frame.elapsed = 0
    frame:SetScript("OnUpdate", function(self, elapsed)
        if ns.navigation:IsShown() or not finite(elapsed) or elapsed < 0 then return end
        self.elapsed = self.elapsed + elapsed
        if self.elapsed >= 0.1 then self.elapsed = 0; ns.UpdateNavigation() end
    end)
    frame:Hide()
end

local function shortTime(state)
    if state.arrived then return "" end
    if finite(state.walkSeconds) and state.walkSeconds > 0 then
        local seconds = math.floor(state.walkSeconds + 0.5)
        return seconds < 60 and ("~" .. seconds .. " s") or ("~" .. math.floor((seconds + 30) / 60) .. " min")
    end
    local flight = state.flight
    if flight and finite(flight.remaining) and flight.remaining > 0 then
        local seconds = math.floor(flight.remaining + 0.5)
        local minutes, remainder = math.floor(seconds / 60), seconds % 60
        if minutes == 0 then return "~" .. seconds .. " s" end
        return "~" .. minutes .. " min" .. (remainder > 0 and (" " .. remainder .. " s") or "")
    end
    return ""
end

function ns.LayoutStandaloneDetails(frame)
    local size = ns.Option("standaloneArrowScale")
    frame:SetScale(finite(size) and size or 1)
    frame:SetWidth(104)
    frame:SetHeight(frame.training:IsShown() and 152 or 130)
end

function ns.UpdateStandaloneArrow(state)
    local frame = ns.standaloneNavigation
    if not frame then return end
    frame.state = state
    local stop = state and state.stop
    local target = stop and stop.kind ~= "loading" and stop.kind ~= "notice" and stop.kind ~= "wait"
        and (state.angle ~= nil or finite(state.distance) or state.arrived or state.flight)
    local visible = state and state.visible == true and not state.idle and not state.busy
        and target and ns.Option("standaloneArrow") == true
    frame:SetShown(visible == true)
    local training = visible and (ns.IsClassTrainingStep(stop) or ns.IsInventoryServiceStep(stop))
        and not state.flight and not ns.navigation:IsShown()
    frame.training:SetShown(training == true)
    ns.LayoutStandaloneDetails(frame)
    ns.HideNavigationGeometry(frame.icon)
    if not frame:IsShown() then return end
    local presentation = ns.GuideStepPresentation(stop, nil, ns.routeSelection, ns.selectedRoute, state)
    frame.presentation = presentation
    local orange = {0.85, 0.35, 0.25, 1}
    local green = {0.36, 0.72, 0.39, 1}
    local gold = {0.88, 0.73, 0.36, 1}
    frame.kindIcon:Hide(); frame.symbol:Hide()
    if state.arrived then
        frame.symbol:SetText("✓"); frame.symbol:SetTextColor(unpack(green)); frame.symbol:Show()
        frame.distance:SetText("Here"); frame.distance:SetTextColor(unpack(green)); frame.time:SetText("")
    elseif state.flight or presentation.kind == "travel-hearth" or presentation.kind == "travel-teleport"
        or presentation.kind == "travel-ship" then
        local texture = presentation.icon
        frame.kindIcon:SetTexture(texture); frame.kindIcon:SetShown(type(texture) == "string")
        if type(texture) ~= "string" then frame.symbol:SetText("✧"); frame.symbol:SetTextColor(unpack(gold)); frame.symbol:Show() end
        frame.distance:SetText(presentation.what or presentation.title or "Travel")
        frame.distance:SetTextColor(unpack(ns.UIColors.text)); frame.time:SetText(shortTime(state))
    elseif state.angle ~= nil then
        local angle = math.atan2(math.sin(state.angle), math.cos(state.angle))
        local wrongWay = math.abs(angle) > math.rad(120)
        ns.DrawNavigationArrow(angle, frame.icon, wrongWay and orange or gold)
        frame.distance:SetText(ns.FormatDistance(state.distance or 0))
        frame.distance:SetTextColor(unpack(ns.UIColors.text)); frame.time:SetText(shortTime(state))
        if wrongWay then frame.time:SetText((shortTime(state) ~= "" and shortTime(state) .. " · " or "") .. "behind you") end
    else
        frame.distance:SetText(state.status or "Direction unavailable")
        frame.distance:SetTextColor(unpack(ns.UIColors.muted)); frame.time:SetText("")
    end
end
