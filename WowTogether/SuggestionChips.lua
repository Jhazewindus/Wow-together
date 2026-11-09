local addonName, ns = ...

-- One shared, non-modal action strip. It lives in the route card while the
-- card is visible and uses a compact screen-level frame while the card is hidden.
local active, generation, currentFrame = nil, 0, nil
local standaloneFrame, embeddedFrame
local dismissed = {}

local function trigger(kind, key)
    return tostring(kind or "tip") .. ":" .. tostring(key or "default")
end

local function suppression()
    if type(ns.char) ~= "table" then return dismissed end
    if type(ns.char.dismissedSuggestionChips) ~= "table" then ns.char.dismissedSuggestionChips = {} end
    return ns.char.dismissedSuggestionChips
end

local function stripHeight(text, width)
    if type(text) ~= "string" then text = "" end
    local textWidth = math.max(80, width - 148)
    return #text * 5.6 > textWidth and 40 or 30
end

local function setPanel(frame, embedded)
    if ns.UIPanel then
        ns.UIPanel(frame, embedded and {0.095, 0.102, 0.106, 0.99} or {0.065, 0.071, 0.075, 0.96})
    end
end

local function createFrame(parent, embedded)
    local frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    frame.embedded = embedded
    frame:SetFrameStrata("HIGH")
    frame:SetClampedToScreen(true)
    setPanel(frame, embedded)
    frame.text = ns.UILabel and ns.UILabel(frame, nil, 10, ns.UIColors and ns.UIColors.text)
        or frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.text:SetPoint("LEFT", 10, 0)
    frame.text:SetWordWrap(embedded == true)
    frame.actions = {}
    for index = 1, 2 do
        local button = CreateFrame("Button", nil, frame)
        button.caption = ns.UILabel and ns.UILabel(button, nil, 10, ns.UIColors and ns.UIColors.gold)
            or button:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        button.caption:SetPoint("CENTER")
        button.caption:SetWordWrap(false)
        button:SetScript("OnEnter", function() button.caption:SetAlpha(1) end)
        button:SetScript("OnLeave", function() button.caption:SetAlpha(0.8) end)
        frame.actions[index] = button
    end
    frame.separator = ns.UILabel and ns.UILabel(frame, nil, 10, ns.UIColors and ns.UIColors.muted)
        or frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.separator:SetText("·"); frame.separator:Hide()
    if embedded then
        frame.divider = frame:CreateTexture(nil, "ARTWORK")
        frame.divider:SetColorTexture(0.28, 0.26, 0.22, 1)
        frame.divider:SetHeight(1); frame.divider:SetPoint("TOPLEFT", 0, 0); frame.divider:SetPoint("TOPRIGHT", 0, 0)
    end
    frame:SetScript("OnUpdate", function(self, elapsed)
        if self ~= currentFrame or not active or type(elapsed) ~= "number" or elapsed < 0 then return end
        active.age = (active.age or 0) + elapsed
        if active.age >= 30 then ns.HideSuggestionChip(true) end
    end)
    frame:Hide()
    return frame
end

local function ensureStandalone()
    if not standaloneFrame then standaloneFrame = createFrame(UIParent, false) end
    return standaloneFrame
end

local function ensureEmbedded(parent)
    if not embeddedFrame then embeddedFrame = createFrame(parent, true)
    elseif embeddedFrame:GetParent() ~= parent then embeddedFrame:SetParent(parent) end
    return embeddedFrame
end

local function setActionLayout(frame, chip)
    local actionWidths, actionsWidth = {}, 0
    for index = 1, 2 do
        local item = chip.actions[index]
        local button = frame.actions[index]
        button:ClearAllPoints()
        if item then
            local width = math.max(32, math.min(76, #tostring(item.label or "Open") * 6 + 8))
            actionWidths[index] = width
            actionsWidth = actionsWidth + width
            button:SetSize(width, 22)
            button.caption:SetWidth(width)
            button.caption:SetText(item.label or "Open")
            button.caption:SetAlpha(0.82)
            button:SetScript("OnClick", function()
                if active ~= chip then return end
                ns.HideSuggestionChip(true)
                if type(item.callback) == "function" then item.callback() end
            end)
            button:Show()
        else
            button:Hide()
        end
    end
    local right = -8
    local first, second = chip.actions[1], chip.actions[2]
    if second then
        frame.actions[2]:SetPoint("RIGHT", frame, "RIGHT", right, 0)
        if first then
            frame.separator:ClearAllPoints(); frame.separator:SetPoint("RIGHT", frame.actions[2], "LEFT", -3, 0); frame.separator:Show()
            frame.actions[1]:SetPoint("RIGHT", frame.separator, "LEFT", -3, 0)
        else frame.separator:Hide() end
    elseif first then
        frame.separator:Hide(); frame.actions[1]:SetPoint("RIGHT", frame, "RIGHT", right, 0)
    else
        frame.separator:Hide()
    end
    frame.text:SetText(chip.text)
    frame.text:ClearAllPoints(); frame.text:SetPoint("LEFT", 10, 0)
    local rightAction = frame.actions[1]:IsShown() and frame.actions[1]
        or frame.actions[2]:IsShown() and frame.actions[2]
    frame.text:SetPoint("RIGHT", rightAction or frame, rightAction and "LEFT" or "RIGHT", -8, 0)
    frame.text:SetWordWrap(frame.embedded == true)
    if frame.embedded then
        local hudWidth = ns.navigation and ns.navigation:GetWidth() or 360
        local height = stripHeight(chip.text, hudWidth)
        frame:SetHeight(height); frame.embeddedHeight = height; frame.text:SetHeight(height - 2)
    else
        local width = math.max(260, math.min(620, #tostring(chip.text or "") * 5.6 + actionsWidth + 48))
        frame:SetSize(width, 34); frame.text:SetHeight(24)
    end
end

local function visibleHUD()
    local hud = ns.navigation
    if hud and type(hud.IsShown) == "function" and hud:IsShown() then return hud end
end

local function place()
    if not active then
        if standaloneFrame then standaloneFrame:Hide() end
        if embeddedFrame then embeddedFrame:Hide() end
        currentFrame = nil
        return
    end
    local hud = visibleHUD()
    local frame = hud and ensureEmbedded(hud) or ensureStandalone()
    if currentFrame and currentFrame ~= frame then currentFrame:Hide() end
    currentFrame = frame
    ns.suggestionChipFrame = frame
    setActionLayout(frame, active)
    frame:ClearAllPoints()
    if hud then
        frame:SetPoint("BOTTOMLEFT", hud, "BOTTOMLEFT", 0, 0)
        frame:SetPoint("BOTTOMRIGHT", hud, "BOTTOMRIGHT", 0, 0)
    else
        local arrow = ns.standaloneNavigation
        if arrow and arrow:IsShown() then frame:SetPoint("BOTTOM", arrow, "BOTTOM", 0, -38)
        else frame:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, 150) end
    end
    frame:Show()
end

local function markDismissed(item)
    if not item then return end
    suppression()[item.id] = true
    dismissed[item.id] = true
end

function ns.SuggestionChipStripHeight()
    local hud = visibleHUD()
    if not active or not hud then return 0 end
    return stripHeight(active.text, hud:GetWidth())
end

function ns.HideSuggestionChip(dismiss)
    if not active then return end
    local old = active
    active = nil
    generation = generation + 1
    if dismiss ~= false then markDismissed(old) end
    if standaloneFrame then standaloneFrame:Hide() end
    if embeddedFrame then embeddedFrame:Hide() end
    currentFrame = nil
    if ns.LayoutNavigation then ns.LayoutNavigation() end
end

function ns.ClearSuggestionChip(kind, key)
    local id = trigger(kind, key)
    suppression()[id], dismissed[id] = nil, nil
    if active and active.id == id then ns.HideSuggestionChip(false) end
end

function ns.ClearSuggestionChipKind(kind)
    local prefix = tostring(kind or "tip") .. ":"
    for id in pairs(suppression()) do if string.sub(id, 1, #prefix) == prefix then suppression()[id] = nil end end
    for id in pairs(dismissed) do if string.sub(id, 1, #prefix) == prefix then dismissed[id] = nil end end
    if active and active.kind == kind then ns.HideSuggestionChip(false) end
end

function ns.HasSuggestionChipKind(kind)
    return active ~= nil and active.kind == kind
end

function ns.CurrentSuggestionChip()
    return active
end

function ns.ExpireSuggestionChip()
    if active then ns.HideSuggestionChip(true); return true end
    return false
end

function ns.ShowSuggestionChip(kind, key, text, actions)
    local id = trigger(kind, key)
    local blocked = suppression()[id] or dismissed[id]
    if blocked then return false end
    if active and active.id == id then place(); return true end
    active = {kind = kind, key = key, id = id, text = text or "", actions = actions or {}, age = 0}
    generation = generation + 1
    if ns.LayoutNavigation then ns.LayoutNavigation() end
    place()
    return true
end

function ns.UpdateSuggestionChipAnchor()
    if active then place() end
end

-- Compatibility facades preserve the old prompt API for addons and tests;
-- these are Lua tables, not modal frames.
function ns.SuggestionChipFacade(kind)
    local facade = {kind = kind}
    function facade:IsShown() return ns.HasSuggestionChipKind(kind) end
    function facade:Show() return self:IsShown() end
    function facade:Hide() if self:IsShown() then ns.HideSuggestionChip(true) end end
    function facade:ClearAllPoints() self.point = nil end
    function facade:SetPoint(...) self.point = {...} end
    return facade
end
