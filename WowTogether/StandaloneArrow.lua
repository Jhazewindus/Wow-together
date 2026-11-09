local addonName, ns = ...

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

local function setText(frame, cacheKey, text)
    if frame[cacheKey] ~= text then frame[cacheKey] = text; frame:SetText(text) end
end

function ns.CreateStandaloneArrow()
    if ns.standaloneNavigation then return end
    local frame = CreateFrame("Frame", "WowTogetherStandaloneArrow", UIParent)
    ns.standaloneNavigation = frame
    frame:SetSize(180, 102); frame:SetPoint("CENTER", UIParent, "CENTER", 0, 110)
    frame:SetClampedToScreen(true); frame:SetFrameStrata("MEDIUM")
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local anchor, _, relative, x, y = self:GetPoint()
        if ns.Public(anchor) and ns.Public(relative) and type(anchor) == "string" and type(relative) == "string"
            and finite(x) and finite(y) then ns.db.standaloneArrowPosition = {point = anchor, relative = relative, x = x, y = y} end
    end)
    local saved = ns.db.standaloneArrowPosition
    if type(saved) == "table" and type(saved.point) == "string" and type(saved.relative) == "string" and finite(saved.x) and finite(saved.y) then
        frame:ClearAllPoints(); frame:SetPoint(saved.point, UIParent, saved.relative, saved.x, saved.y)
    end
    frame.timer = ns.UILabel(frame, nil, 11, ns.UIColors.gold); frame.timer:SetPoint("TOP", 0, 0)
    frame.timer:SetSize(176, 16); frame.timer:SetWordWrap(false)
    frame.icon = CreateFrame("Frame", nil, frame); frame.icon:SetSize(52, 52); frame.icon:SetPoint("TOP", 0, -18); frame.icon.lines = {}
    frame.kindIcon = frame.icon:CreateTexture(nil, "ARTWORK"); frame.kindIcon:SetSize(34, 34); frame.kindIcon:SetPoint("CENTER")
    frame.symbol = ns.UILabel(frame.icon, "GameFontNormalLarge", 24); frame.symbol:SetPoint("CENTER")
    frame.distance = ns.UILabel(frame, nil, 12, ns.UIColors.gold); frame.distance:SetPoint("TOP", 0, -71)
    frame.title = ns.UILabel(frame, nil, 11); frame.title:SetPoint("TOP", 0, -87); frame.title:SetSize(176, 14); frame.title:SetWordWrap(false)
    frame.reason = ns.UILabel(frame, nil, 10, ns.UIColors.muted)
    frame.reason:SetSize(248, 42); frame.reason:SetWordWrap(true); frame.reason:SetJustifyV("TOP")
    frame.reason:Hide()
    frame.training = CreateFrame("Frame", nil, frame); frame.training:SetSize(176, 24)
    frame.training:SetPoint("TOP", 0, -105)
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
        local presentation = self.presentation or self.state and ns.GuideStepPresentation(self.state.stop, nil,
            ns.routeSelection, ns.selectedRoute, self.state)
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
        if self.elapsed >= 0.1 then self.elapsed = 0; ns.UpdateNavigation(true) end
    end)
    frame:Hide()
end

function ns.LayoutStandaloneDetails(frame)
    local reasonShown = frame.reason:IsShown()
    local height = frame.training:IsShown() and 130 or 102
    if frame.detailHeight == height and frame.detailReasonShown == reasonShown then return end
    frame.detailHeight, frame.detailReasonShown = height, reasonShown
    frame.reason:ClearAllPoints(); frame.reason:SetPoint("TOP", frame, "TOP", 0, -height - 4)
    if reasonShown then
        local measured = ns.ReadPublic(frame.reason.GetStringHeight, frame.reason)
        local lines = finite(measured) and math.max(26, measured + 2) or 42
        frame.reason:SetHeight(lines); height = height + lines + 4
    end
    frame:SetWidth(frame.reason:IsShown() and 248 or 180)
    frame:SetHeight(height)
end

local function updateStandaloneArrow(state, presentation)
    local frame = ns.standaloneNavigation
    if not frame then return end
    frame.state = state
    local shown = state.visible == true and not state.idle and ns.Option("standaloneArrow")
    if frame:IsShown() ~= shown then frame:SetShown(shown) end
    if not shown then
        if frame.wasShown then
            frame.wasShown = nil
            ns.HideNavigationGeometry(frame.icon)
        end
        return
    end
    frame.wasShown = true
    local training = (ns.IsClassTrainingStep(state.stop) or ns.IsInventoryServiceStep(state.stop)) and not state.flight and not state.busy
        and not ns.navigationPreview and not ns.Option("routeArrow")
    frame.training:SetShown(training == true)
    frame.reason:Hide()
    ns.LayoutStandaloneDetails(frame)
    if state.busy or state.arrived or state.angle == nil then ns.HideNavigationGeometry(frame.icon)
    else ns.HideNavigationSpinner(frame.icon) end
    if not presentation then
        local roundedDistance = finite(state.distance) and math.floor(state.distance + 0.5) or nil
        if frame.presentationStop ~= state.stop or frame.presentationLabel ~= state.stop.label
            or frame.presentationDistance ~= roundedDistance or frame.presentationRevision ~= (ns.guideProgressRevision or 0)
            or not frame.presentation then
            presentation = ns.GuideStepPresentation(state.stop, nil, ns.routeSelection, ns.selectedRoute, state)
            frame.presentationStop, frame.presentationLabel = state.stop, state.stop.label
            frame.presentationDistance, frame.presentationRevision = roundedDistance, ns.guideProgressRevision or 0
        else presentation = frame.presentation end
    end
    frame.presentation = presentation
    setText(frame.timer, "cachedText", presentation.time or ""); frame.timer:SetShown(presentation.time ~= nil)
    frame.distance:Hide()
    local drawable = type(frame.icon.CreateLine) == "function"
    local iconOnly = state.arrived or state.flight or presentation.kind == "travel-hearth" or presentation.kind == "travel-teleport"
    frame.kindIcon:SetTexture(presentation.icon); frame.kindIcon:SetShown(state.angle == nil and iconOnly)
    setText(frame.symbol, "cachedText", "…")
    frame.symbol:SetShown(state.angle == nil and not iconOnly)
    if drawable then
        if state.busy then frame.symbol:SetShown(not ns.DrawNavigationSpinner(frame.icon))
        elseif state.arrived then frame.symbol:Hide()
        elseif state.angle ~= nil then ns.DrawNavigationArrow(state.angle, frame.icon) end
    end
    local title = frame.presentationText
    if frame.presentationTextFor ~= presentation then
        title = presentation.what .. (presentation.progress and (" " .. presentation.progress) or "")
        frame.presentationTextFor, frame.presentationText = presentation, title
    end
    setText(frame.title, "cachedText", title)
end

function ns.UpdateStandaloneArrow(state, presentation)
    local before = ns.StartMemorySample and ns.StartMemorySample(ns.MemorySampleSection.arrow)
    updateStandaloneArrow(state, presentation)
    if ns.EndMemorySample then ns.EndMemorySample(ns.MemorySampleSection.arrow, before) end
end
