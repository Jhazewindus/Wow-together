local addonName, ns = ...

-- Geometry only while dragging. Content/planning work belongs in onFinish.
local active
local function number(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -1000000 and value < 1000000
end
function ns.AnchorWindowTopLeft(frame)
    local left, top = ns.ReadPublic(frame.GetLeft, frame), ns.ReadPublic(frame.GetTop, frame)
    local scale = ns.ReadPublic(frame.GetEffectiveScale, frame)
    local parentScale = ns.ReadPublic(UIParent.GetEffectiveScale, UIParent)
    if not number(left) or not number(top) then return false end
    local ratio = number(scale) and number(parentScale) and parentScale > 0 and scale / parentScale or 1
    frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", left * ratio, top * ratio)
    return true
end
local function persist(frame)
    local config = frame.resizeConfig
    if not config.key or not ns.db then return end
    ns.db.uiWindows = type(ns.db.uiWindows) == "table" and ns.db.uiWindows or {}
    local size = {width = frame:GetWidth(), height = frame:GetHeight()}
    local left, top = ns.ReadPublic(frame.GetLeft, frame), ns.ReadPublic(frame.GetTop, frame)
    if number(left) and number(top) then
        local scale, parentScale = ns.ReadPublic(frame.GetEffectiveScale, frame), ns.ReadPublic(UIParent.GetEffectiveScale, UIParent)
        local ratio = number(scale) and number(parentScale) and parentScale > 0 and scale / parentScale or 1
        size.left, size.top = left * ratio, top * ratio
    end
    ns.db.uiWindows[config.key] = size
end
function ns.FinishWindowSizing(frame)
    local config = frame and frame.resizeConfig
    if not config then return end
    frame:StopMovingOrSizing(); frame.sizing = nil
    if active == frame then active = nil end
    if config.layout then config.layout(frame) end
    persist(frame)
    if config.onFinish then config.onFinish(frame) end
end
function ns.BeginWindowSizing(frame, key)
    if key ~= "LeftButton" or not frame.resizeConfig then return end
    if ns.ReadPublic(frame.IsProtected, frame) == true and ns.RouteInCombat() then return end
    if active and active ~= frame then ns.FinishWindowSizing(active) end
    ns.AnchorWindowTopLeft(frame)
    if ns.CloseUIMenus then ns.CloseUIMenus() end
    frame.sizing, active = true, frame
    if frame.resizeConfig.onBegin then frame.resizeConfig.onBegin(frame) end
    frame:StartSizing("BOTTOMRIGHT")
end
function ns.EnableWindowResize(frame, config)
    frame.resizeConfig = config
    frame:SetResizable(true); frame:SetMovable(true); frame:SetClampedToScreen(true)
    if type(frame.SetResizeBounds) == "function" then
        frame:SetResizeBounds(config.minWidth, config.minHeight, config.maxWidth, config.maxHeight)
    end
    local grip = config.grip or CreateFrame("Button", nil, frame)
    frame.grip = grip
    if not config.grip then
        grip:SetSize(16, 16); grip:SetPoint("BOTTOMRIGHT", -2, 2)
        grip.icon = grip:CreateTexture(nil, "ARTWORK"); grip.icon:SetAllPoints()
        grip.icon:SetTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    end
    grip:SetScript("OnMouseDown", function(_, key) ns.BeginWindowSizing(frame, key) end)
    grip:SetScript("OnMouseUp", function(_, key)
        if not key or key == "LeftButton" then ns.FinishWindowSizing(frame) end
    end)
    frame:SetScript("OnSizeChanged", function()
        if frame.resizeBoundsBusy then return end
        local width, height = frame:GetWidth(), frame:GetHeight()
        if not number(width) or not number(height) then return end
        width = math.max(config.minWidth, math.min(config.maxWidth, width))
        height = math.max(config.minHeight, math.min(config.maxHeight, height))
        frame.resizeBoundsBusy = true
        if width ~= frame:GetWidth() or height ~= frame:GetHeight() then frame:SetSize(width, height) end
        if config.layout then config.layout(frame) end
        frame.resizeBoundsBusy = nil
    end)
    local previousHide = frame:GetScript("OnHide")
    frame:SetScript("OnHide", function(...)
        if frame.sizing then ns.FinishWindowSizing(frame) end
        if previousHide then previousHide(...) end
        ns.CloseUIMenus()
    end)
    local previousDrag = frame:GetScript("OnDragStop")
    frame:SetScript("OnDragStop", function(...)
        frame:StopMovingOrSizing(); persist(frame)
        if previousDrag then previousDrag(...) end
    end)
    local saved = config.key and ns.db and ns.db.uiWindows and ns.db.uiWindows[config.key]
    if type(saved) == "table" then
        if number(saved.width) and number(saved.height) then
            frame:SetSize(math.max(config.minWidth, math.min(config.maxWidth, saved.width)),
                math.max(config.minHeight, math.min(config.maxHeight, saved.height)))
        end
        if number(saved.left) and number(saved.top) then
            frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", saved.left, saved.top)
        end
    end
    if config.layout then config.layout(frame) end
end

-- Small choice popups share responsive text and an evenly spaced button row.
function ns.ResizeChoicePopup(frame, key, buttons, minimumWidth, minimumHeight)
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    ns.EnableWindowResize(frame, {key = key, minWidth = minimumWidth, minHeight = minimumHeight,
        maxWidth = 900, maxHeight = 600, layout = function(self)
            local width, height = self:GetWidth(), self:GetHeight()
            self.title:SetSize(width - 58, 32); self.title:SetWordWrap(true)
            self.text:SetSize(width - 44, height - 116); self.text:SetWordWrap(true); self.text:SetJustifyV("TOP")
            local buttonWidth = (width - 44 - (#buttons - 1) * 10) / #buttons
            for index, button in ipairs(buttons) do
                button:SetWidth(buttonWidth); button:ClearAllPoints()
                button:SetPoint("BOTTOMLEFT", 22 + (index - 1) * (buttonWidth + 10), 18)
            end
        end})
end
ns.On("GLOBAL_MOUSE_UP", function(key)
    if ns.Public(key) and key == "LeftButton" and active then ns.FinishWindowSizing(active) end
end)
