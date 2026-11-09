local addonName, ns = ...

-- One shared, non-modal action strip for short-lived suggestions. Prompt
-- sources keep their domain callbacks; this module owns visibility and
-- dismissal so two sources can never occupy the HUD at once.
local active, generation, frame, buttons = nil, 0, nil, {}
local dismissed = {}

local function trigger(kind, key)
    return tostring(kind or "tip") .. ":" .. tostring(key or "default")
end

local function suppression()
    if type(ns.char) ~= "table" then return dismissed end
    if type(ns.char.dismissedSuggestionChips) ~= "table" then ns.char.dismissedSuggestionChips = {} end
    return ns.char.dismissedSuggestionChips
end

local function ensureFrame()
    if frame then return frame end
    frame = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
    frame:SetSize(520, 34)
    frame:SetFrameStrata("HIGH")
    frame:SetClampedToScreen(true)
    if ns.UIPanel then ns.UIPanel(frame, {0.065, 0.071, 0.075, 0.96}) end
    frame.text = ns.UILabel and ns.UILabel(frame, nil, 11, ns.UIColors and ns.UIColors.muted)
        or frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.text:SetPoint("LEFT", 10, 0)
    frame.text:SetWidth(320)
    frame.text:SetWordWrap(false)
    for index = 1, 2 do
        local button = CreateFrame("Button", nil, frame, "BackdropTemplate")
        button:SetSize(78, 24)
        if ns.UIPanel then ns.UIPanel(button) end
        button.caption = ns.UILabel and ns.UILabel(button, nil, 11, ns.UIColors and ns.UIColors.gold)
            or button:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        button.caption:SetPoint("CENTER")
        button.caption:SetWordWrap(false)
        buttons[index] = button
    end
    buttons[2]:SetPoint("RIGHT", -6, 0)
    buttons[1]:SetPoint("RIGHT", buttons[2], "LEFT", -4, 0)
    frame:SetScript("OnUpdate", function(self, elapsed)
        if not active or type(elapsed) ~= "number" or elapsed < 0 then return end
        self.age = (self.age or 0) + elapsed
        if self.age >= 30 then ns.HideSuggestionChip(true) end
    end)
    frame:Hide()
    ns.suggestionChipFrame = frame
    return frame
end

local function place()
    if not frame then return end
    frame:ClearAllPoints()
    local hud = ns.navigation and ns.navigation:IsShown() and ns.navigation
        or ns.standaloneNavigation and ns.standaloneNavigation:IsShown() and ns.standaloneNavigation
    if hud then frame:SetPoint("BOTTOM", hud, "BOTTOM", 0, -38)
    else frame:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, 150) end
end

local function markDismissed(item)
    if not item then return end
    suppression()[item.id] = true
    dismissed[item.id] = true
end

function ns.HideSuggestionChip(dismiss)
    if not active then return end
    local old = active
    active = nil
    generation = generation + 1
    if dismiss ~= false then markDismissed(old) end
    if frame then frame.age = 0; frame:Hide() end
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
    active = {kind = kind, key = key, id = id, text = text or "", actions = actions or {}}
    generation = generation + 1
    local chip = active
    local strip = ensureFrame()
    strip.age = 0
    strip.text:SetText(chip.text)
    for index = 1, 2 do
        local item = chip.actions[index]
        local button = buttons[index]
        if item then
            button.caption:SetText(item.label or "Open")
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
    place()
    strip:Show()
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
