local addonName, ns = ...

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value and value > -math.huge and value < math.huge
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
    frame.symbol = ns.UILabel(frame.icon, "GameFontNormalLarge", 24); frame.symbol:SetPoint("CENTER")
    frame.distance = ns.UILabel(frame, nil, 12, ns.UIColors.gold); frame.distance:SetPoint("TOP", 0, -71)
    frame.title = ns.UILabel(frame, nil, 11); frame.title:SetPoint("TOP", 0, -87); frame.title:SetSize(176, 14); frame.title:SetWordWrap(false)
    frame.training = CreateFrame("Frame", nil, frame); frame.training:SetSize(176, 24)
    frame.training:SetPoint("TOP", 0, -105)
    frame.training.done = ns.UIButton(frame.training, "Done", 80, function() ns.FinishClassTraining(true) end)
    frame.training.done:SetPoint("LEFT"); frame.training.done:SetHeight(22)
    frame.training.skip = ns.UIButton(frame.training, "Skip", 80, function() ns.FinishClassTraining(false) end)
    frame.training.skip:SetPoint("RIGHT"); frame.training.skip:SetHeight(22)
    frame.training:Hide()
    frame:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        if self.state and self.state.stop then GameTooltip:AddLine(ns.GuideStepDescription(self.state.stop), 1, 0.82, 0.3, true) end
        if self.guideTip then GameTooltip:AddLine(self.guideTip.detail, 1, 0.82, 0.3, true) end
        GameTooltip:AddLine("Drag to move • Configure in Arrow and map", 1, 1, 1, true); GameTooltip:Show()
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

function ns.UpdateStandaloneArrow(state)
    local frame = ns.standaloneNavigation
    if not frame then return end
    frame.state = state
    frame:SetShown(state.visible == true and not state.idle and ns.Option("standaloneArrow"))
    local training = ns.IsClassTrainingStep(state.stop) and not state.flight and not state.busy
        and not ns.navigationPreview and not ns.Option("routeArrow")
    frame.training:SetShown(training == true); frame:SetHeight(training and 130 or 102)
    ns.HideNavigationGeometry(frame.icon)
    if not frame:IsShown() then return end
    local clock = ns.NavigationTravelTime(state)
    frame.timer:SetText(clock or ""); frame.timer:SetShown(clock ~= nil)
    local drawable = type(frame.icon.CreateLine) == "function"
    frame.symbol:SetText(state.flight and "…" or state.arrived and "↓" or "…")
    frame.symbol:SetShown(not drawable or not state.arrived and state.angle == nil)
    if drawable then
        if state.busy then frame.symbol:SetShown(not ns.DrawNavigationSpinner(frame.icon))
        elseif state.arrived then ns.DrawNavigationArrow(math.pi, frame.icon)
        elseif state.angle ~= nil then ns.DrawNavigationArrow(state.angle, frame.icon) end
    end
    frame.distance:SetText(state.flight and "Flying" or state.distance and ns.FormatDistance(state.distance) or state.status)
    frame.title:SetText(state.stop.title)
end
