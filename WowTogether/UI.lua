local addonName, ns = ...

local colors = {
    background = {0.065, 0.071, 0.075, 0.98},
    panel = {0.095, 0.102, 0.106, 0.98},
    border = {0.27, 0.25, 0.21, 1},
    gold = {0.88, 0.73, 0.46, 1},
    muted = {0.65, 0.67, 0.66, 1},
    text = {0.91, 0.90, 0.86, 1},
    success = {0.48, 0.76, 0.66, 1},
}

local function panel(frame, fill, edge)
    frame:SetBackdrop({bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1, insets = {left = 1, right = 1, top = 1, bottom = 1}})
    frame:SetBackdropColor(unpack(fill or colors.panel))
    frame:SetBackdropBorderColor(unpack(edge or colors.border))
end

local function label(parent, style, size, color)
    local text = parent:CreateFontString(nil, "OVERLAY", style or "GameFontHighlightSmall")
    local heading = style and string.find(style, "Normal", 1, true)
    text:SetFont(heading and "Fonts\\FRIZQT__.TTF" or "Fonts\\ARIALN.TTF", size or 12, "")
    text:SetJustifyH("LEFT")
    text:SetTextColor(unpack(color or colors.text))
    return text
end

function ns.UIButtonTone(frame, primary)
    frame.primary = primary == true
    frame:SetBackdropColor(unpack(frame.primary and {0.20, 0.17, 0.115, 1} or colors.panel))
    frame:SetBackdropBorderColor(unpack(frame.primary and colors.gold or colors.border))
    frame.caption:SetTextColor(unpack(frame.primary and colors.gold or colors.text))
end

local function button(parent, caption, width, callback, primary)
    local frame = CreateFrame("Button", nil, parent, "BackdropTemplate")
    frame:SetSize(width, 26)
    panel(frame)
    frame.caption = label(frame, nil, 12)
    frame.caption:SetPoint("LEFT", 8, 0)
    frame.caption:SetPoint("RIGHT", -8, 0)
    frame.caption:SetJustifyH("CENTER")
    frame.caption:SetWordWrap(false)
    frame.caption:SetText(caption)
    ns.UIButtonTone(frame, primary)
    frame:SetScript("OnClick", callback)
    frame:SetScript("OnEnter", function(self) self:SetBackdropBorderColor(unpack(colors.gold)) end)
    frame:SetScript("OnLeave", function(self)
        self:SetBackdropBorderColor(unpack((self.primary or (self.filterKey and ns.filter == self.filterKey)) and colors.gold or colors.border))
    end)
    frame:SetScript("OnDisable", function(self) self.caption:SetAlpha(0.4) end)
    frame:SetScript("OnEnable", function(self) self.caption:SetAlpha(1) end)
    return frame
end

ns.UIPanel, ns.UILabel, ns.UIButton = panel, label, button
ns.UIColors = colors

function ns.UIDivider(parent, y)
    local line = parent:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(unpack(colors.border)); line:SetHeight(1)
    line:SetPoint("TOPLEFT", 1, y); line:SetPoint("TOPRIGHT", -1, y)
    return line
end

function ns.UIClose(parent, callback)
    local close = button(parent, "×", 24, callback or function() parent:Hide() end)
    close:SetHeight(24); close:SetPoint("TOPRIGHT", -10, -10)
    ns.UIHelp(close, "Close")
    return close
end

local function searchBox(parent, hint)
    local edit = CreateFrame("EditBox", nil, parent, "BackdropTemplate")
    panel(edit, colors.background)
    edit:SetFont("Fonts\\ARIALN.TTF", 12, ""); edit:SetTextColor(unpack(colors.text))
    edit:SetTextInsets(10, 10, 0, 0); edit:SetAutoFocus(false)
    edit.placeholder = label(edit, nil, 11, colors.muted)
    edit.placeholder:SetPoint("LEFT", 10, 0); edit.placeholder:SetPoint("RIGHT", -10, 0)
    edit.placeholder:SetWordWrap(false); edit.placeholder:SetText(hint)
    edit:SetScript("OnEditFocusGained", function(self)
        self.placeholder:Hide(); self:SetBackdropBorderColor(unpack(colors.gold))
    end)
    edit:SetScript("OnEditFocusLost", function(self)
        local value = self:GetText()
        self.placeholder:SetShown(ns.Public(value) and (value == nil or value == ""))
        self:SetBackdropBorderColor(unpack(colors.border))
    end)
    return edit
end

local function scrollTop(filter)
    return filter == "library" and -246 or filter == "guides" and -214 or -150
end

function ns.ToggleWindow()
    ns.window:SetShown(not ns.window:IsShown())
    ns.Refresh()
end

function ns.IsPartyView(filter)
    return filter == "all" or filter == "shared" or filter == "different" or filter == "suggestions"
end

function ns.SetFilter(filter)
    if not ns.PartyFeaturesEnabled() and ns.IsPartyView(filter) then filter = "guides" end
    ns.filter = filter
    ns.ui.scroll:SetVerticalScroll(0)
    if ns.ui.librarySearch then
        for _, control in ipairs(ns.ui.libraryControls) do control:SetShown(filter == "library") end
    end
    for _, control in ipairs(ns.ui.guideControls or {}) do control:SetShown(filter == "guides") end
    ns.ui.scroll:ClearAllPoints()
    ns.ui.scroll:SetPoint("TOPLEFT", 26, scrollTop(filter))
    ns.ui.scroll:SetPoint("BOTTOMRIGHT", -44, 64)
    ns.Refresh()
end

function ns.CreateUI()
    local window = CreateFrame("Frame", "WowTogetherWindow", UIParent, "BackdropTemplate")
    ns.window = window
    ns.ui = {cards = {}, filterButtons = {}}
    ns.filter = "guides"
    local saved = ns.db.windowSize
    local width = type(saved) == "table" and type(saved.width) == "number" and math.max(760, math.min(1280, saved.width)) or 860
    local height = type(saved) == "table" and type(saved.height) == "number" and math.max(580, math.min(1000, saved.height)) or 640
    window:SetSize(width, height)
    window:SetResizable(true)
    if type(window.SetResizeBounds) == "function" then window:SetResizeBounds(760, 580, 1280, 1000) end
    window:SetPoint("CENTER")
    window:SetClampedToScreen(true)
    window:SetFrameStrata("HIGH")
    panel(window, colors.background)
    window:SetMovable(true)
    window:EnableMouse(true)
    window:RegisterForDrag("LeftButton")
    window:SetScript("OnDragStart", function(self) if not ns.ui.resizing then self:StartMoving() end end)
    window:SetScript("OnDragStop", window.StopMovingOrSizing)
    if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherWindow") end

    local accent = window:CreateTexture(nil, "ARTWORK")
    accent:SetColorTexture(unpack(colors.gold))
    accent:SetPoint("TOPLEFT", 1, -1)
    accent:SetPoint("TOPRIGHT", -1, -1)
    accent:SetHeight(2)
    local icon = window:CreateTexture(nil, "ARTWORK")
    icon:SetTexture("Interface\\Icons\\INV_Misc_Map_01")
    icon:SetSize(28, 28)
    icon:SetPoint("TOPLEFT", 26, -19)
    icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    local eyebrow = label(window, "GameFontNormalSmall", nil, colors.gold)
    eyebrow:SetPoint("TOPLEFT", 65, -39)
    eyebrow:SetText("FOREVER  /  YOUR NEXT ADVENTURE")
    local title = label(window, "GameFontNormalLarge", 20, colors.text)
    title:SetPoint("TOPLEFT", 64, -16)
    title:SetText("Wow Together")
    local subtitle = label(window, nil, nil, colors.muted)
    ns.ui.subtitle = subtitle
    subtitle:Hide()
    subtitle:SetText("Choose a questline, compare your party, and find the next stop.")
    ns.ui.zone = label(window, "GameFontNormal", nil, colors.gold)
    ns.ui.zone:SetPoint("TOPRIGHT", -154, -22)
    ns.ui.zone:SetWidth(200)
    ns.ui.zone:SetJustifyH("RIGHT")
    ns.UIClose(window)
    ns.UIDivider(window, -58)

    ns.ui.metrics = {}
    local captions = {"PARTY SYNC", "SHARED ACTIVE", "YOUR QUESTS"}
    for i, caption in ipairs(captions) do
        local metric = CreateFrame("Frame", nil, window, "BackdropTemplate")
        metric:SetSize(260, 20)
        metric:SetPoint("TOPLEFT", 26 + (i - 1) * 274, -64)
        metric.caption = label(metric, nil, 10, colors.muted)
        metric.caption:SetPoint("LEFT", 0, 0)
        metric.caption:SetText(caption)
        metric.value = label(metric, nil, 12, colors.gold)
        metric.value:SetPoint("RIGHT", -18, 0)
        ns.ui.metrics[i] = metric
    end
    ns.ui.party = label(window, nil, nil, colors.muted)
    ns.ui.party:SetPoint("TOPLEFT", 26, -88)
    ns.ui.party:SetWidth(808)
    ns.ui.party:SetHeight(16)
    ns.ui.party:SetWordWrap(false)
    ns.ui.party:SetJustifyV("TOP")
    local filters = {{"guides", "Leveling guides"}, {"library", "All quests"}, {"all", "Party quests"},
        {"shared", "Shared quests"}, {"different", "Party progression"}, {"dungeons", "Dungeon guides"},
        {"professions", "Profession guides"}, {"review", "Quest log review"}}
    ns.ui.viewChoice = ns.UIDropdown(window, filters, 200, ns.SetFilter)
    ns.ui.viewChoice:SetPoint("TOPLEFT", 26, -112); ns.ui.viewChoice:SetChoice(ns.filter)
    ns.ui.viewDescription = label(window, nil, 11, colors.muted)
    ns.ui.viewDescription:SetPoint("LEFT", ns.ui.viewChoice, "RIGHT", 16, 0)
    ns.ui.viewDescription:SetText("Choose a guide or explore your party's progress.")
    ns.ui.status = label(window, nil, nil, colors.muted)
    local config = button(window, "Settings", 86, function() ns.ToggleSettings() end)
    config:SetPoint("TOPRIGHT", -48, -10); config:SetHeight(24)
    ns.ui.status:SetPoint("BOTTOMLEFT", 184, 31)
    ns.ui.status:SetWidth(450)
    ns.ui.status:SetJustifyH("LEFT")

    local scroll = CreateFrame("ScrollFrame", nil, window, "UIPanelScrollFrameTemplate")
    ns.ui.scroll = scroll
    scroll:SetPoint("TOPLEFT", 26, scrollTop(ns.filter))
    scroll:SetPoint("BOTTOMRIGHT", -44, 64)
    local content = CreateFrame("Frame", nil, scroll)
    content:SetSize(786, 250)
    scroll:SetScrollChild(content)
    ns.ui.content = content
    local search = searchBox(window, "Search quests or zones")
    ns.ui.librarySearch = search
    search:SetSize(430, 26)
    search:SetPoint("TOPLEFT", 186, -146)
    search:SetAutoFocus(false)
    search:SetScript("OnTextChanged", function(self)
        local value = self:GetText()
        if not ns.Public(value) or type(value) ~= "string" then return end
        self.placeholder:SetShown(value == "")
        ns.QueueLibrarySearch(value)
    end)
    search:SetScript("OnEnterPressed", function(self) ns.ApplyLibrarySearch(); self:ClearFocus() end)
    search:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    search:Hide()
    ns.ui.libraryBack = button(window, "All zones", 140, function() ns.OpenLibraryZone(nil, nil) end)
    ns.ui.libraryBack:SetPoint("TOPLEFT", 26, -146)
    ns.ui.libraryBack:Hide()
    ns.ui.libraryControls = {search, ns.ui.libraryBack}
    ns.ui.librarySubmit = button(window, "Search", 100, function() ns.ApplyLibrarySearch(); search:ClearFocus() end, true)
    ns.ui.librarySubmit:SetPoint("TOPRIGHT", -26, -146)
    ns.ui.libraryControls[#ns.ui.libraryControls + 1] = ns.ui.librarySubmit
    ns.ui.levelButtons = {}
    for _, preset in ipairs({{"all", "All levels"}, {"party", "Near party"}, {"1-10", "1–10"}, {"11-20", "11–20"},
        {"21-30", "21–30"}, {"31-40", "31–40"}, {"41-50", "41–50"}, {"51+", "51+"}}) do
        local key = preset[1]
        local chip = button(window, preset[2], 80, function() ns.SetLibraryLevel(key) end)
        chip:SetHeight(26)
        chip.levelKey = key
        ns.ui.levelButtons[#ns.ui.levelButtons + 1] = chip
        ns.ui.libraryControls[#ns.ui.libraryControls + 1] = chip
    end
    ns.ui.libraryPrev = button(window, "‹", 36, function() ns.libraryPage = math.max(1, (ns.libraryPage or 1) - 1); ns.ui.scroll:SetVerticalScroll(0); ns.Refresh() end)
    ns.ui.libraryPrev:SetPoint("TOPLEFT", 26, -214)
    ns.ui.libraryNext = button(window, "›", 36, function() ns.libraryPage = (ns.libraryPage or 1) + 1; ns.ui.scroll:SetVerticalScroll(0); ns.Refresh() end)
    ns.ui.libraryNext:SetPoint("TOPLEFT", 68, -214)
    ns.ui.libraryCount = label(window, nil, 10, colors.muted)
    ns.ui.libraryCount:SetPoint("TOPLEFT", 118, -221)
    for _, control in ipairs({ns.ui.libraryPrev, ns.ui.libraryNext, ns.ui.libraryCount}) do ns.ui.libraryControls[#ns.ui.libraryControls + 1] = control end
    for _, control in ipairs(ns.ui.libraryControls) do control:Hide() end
    ns.ui.guideLevel = ns.UIDropdown(window, {{"party", "My party's bracket"}, {"all", "All levels"},
        {"1-10", "Levels 1–10"}, {"11-20", "Levels 11–20"}, {"21-30", "Levels 21–30"},
        {"31-40", "Levels 31–40"}, {"41-50", "Levels 41–50"}, {"51+", "Levels 51+"}}, 170, ns.SetGuideLevel)
    ns.ui.guideLevel:SetPoint("TOPLEFT", 26, -146)
    ns.ui.guideLevel:SetChoice(ns.guideLevel)
    local guideSearch = searchBox(window, "Search zones, quests or NPCs")
    ns.ui.guideSearch = guideSearch
    guideSearch:SetSize(400, 26); guideSearch:SetPoint("TOPLEFT", 214, -146)
    guideSearch:SetAutoFocus(false)
    guideSearch:SetScript("OnTextChanged", function(self)
        local value = self:GetText()
        if ns.Public(value) and type(value) == "string" then self.placeholder:SetShown(value == ""); ns.QueueGuideSearch(value) end
    end)
    guideSearch:SetScript("OnEnterPressed", function(self) ns.ApplyGuideSearch(); self:ClearFocus() end)
    guideSearch:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    ns.ui.guideSubmit = button(window, "Search", 100, function() ns.ApplyGuideSearch(); guideSearch:ClearFocus() end, true)
    ns.ui.guideSubmit:SetPoint("TOPRIGHT", -26, -146)
    ns.ui.guidePrev = button(window, "‹", 36, function() ns.guidePage = math.max(1, ns.guidePage - 1); ns.ui.scroll:SetVerticalScroll(0); ns.Refresh() end)
    ns.ui.guidePrev:SetPoint("TOPLEFT", 26, -180)
    ns.ui.guideNext = button(window, "›", 36, function() ns.guidePage = ns.guidePage + 1; ns.ui.scroll:SetVerticalScroll(0); ns.Refresh() end)
    ns.ui.guideNext:SetPoint("TOPLEFT", 68, -180)
    ns.ui.guideCount = label(window, nil, 10, colors.muted)
    ns.ui.guideCount:SetPoint("TOPLEFT", 118, -187)
    ns.ui.guideControls = {ns.ui.guideLevel, guideSearch, ns.ui.guideSubmit, ns.ui.guidePrev, ns.ui.guideNext, ns.ui.guideCount}
    ns.ui.empty = label(content, "GameFontNormalLarge", nil, colors.muted)
    ns.ui.empty:SetPoint("TOPLEFT", 18, -35)
    ns.ui.empty:SetWidth(730)
    ns.ui.empty:SetJustifyH("CENTER")

    ns.ui.hint = label(window, nil, nil, colors.muted)
    ns.ui.hint:SetPoint("BOTTOMLEFT", 26, 44)
    ns.ui.hint:SetWidth(808)
    ns.ui.hint:SetHeight(14); ns.ui.hint:SetWordWrap(false)
    ns.ui.hint:SetText("Show route draws numbered stops and lines on your world map.\nUse Quest library to browse zones, search names, and check requirements.")
    local probe = button(window, "Diagnostics", 132, function() ns.Diagnostics() end)
    probe:SetPoint("BOTTOMLEFT", 26, 12)
    local tracker = button(window, "Tracker", 84, function() ns.ToggleTracker() end)
    ns.ui.trackerButton = tracker
    tracker:SetPoint("BOTTOMLEFT", 168, 12)
    local sync = button(window, "Sync party", 160, function() ns.SyncNow(true) end, true)
    ns.ui.syncButton = sync
    sync:SetPoint("BOTTOMRIGHT", -26, 12)
    local grip = CreateFrame("Button", nil, window)
    ns.ui.resizeGrip = grip
    grip:SetSize(18, 18)
    grip:SetPoint("BOTTOMRIGHT", -3, 3)
    local texture = grip:CreateTexture(nil, "ARTWORK")
    texture:SetAllPoints()
    texture:SetTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    grip:SetScript("OnMouseDown", function(_, mouseButton)
        if mouseButton ~= "LeftButton" then return end
        -- A CENTER anchor grows both sides and fights screen clamping. Keep
        -- the top-left corner fixed for the native bottom-right size gesture.
        local left, top = ns.ReadPublic(window.GetLeft, window), ns.ReadPublic(window.GetTop, window)
        if type(left) == "number" and type(top) == "number" then
            window:ClearAllPoints(); window:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", left, top)
        end
        ns.ui.resizing = true
        window:StartSizing("BOTTOMRIGHT")
    end)
    grip:SetScript("OnMouseUp", function() ns.FinishWindowResize() end)
    window:SetScript("OnSizeChanged", function()
        -- Only geometry changes during the gesture. Do not rebuild the quest
        -- catalogue, recommendations, map route or tracker for every pixel.
        ns.Layout()
        if not ns.ui.resizing then ns.QueueWindowRender() end
    end)
    window:SetScript("OnHide", function() if ns.ui.resizing then ns.FinishWindowResize() end end)
    ns.Layout()
    window:Hide()
end

function ns.FinishWindowResize()
    ns.window:StopMovingOrSizing()
    ns.ui.resizing, ns.ui.resizeDirty = nil, nil
    local width, height = ns.ReadPublic(ns.window.GetWidth, ns.window), ns.ReadPublic(ns.window.GetHeight, ns.window)
    if type(width) == "number" and type(height) == "number" then
        ns.db.windowSize = {width = width, height = height}
    end
    ns.Layout(); ns.Refresh()
end

function ns.QueueWindowRender()
    if ns.ui.resizeRenderQueued or not C_Timer or type(C_Timer.After) ~= "function" then return end
    ns.ui.resizeRenderQueued = true
    C_Timer.After(0.15, function()
        ns.ui.resizeRenderQueued = nil
        if ns.ui.resizing then ns.ui.resizeDirty = true else ns.Render() end
    end)
end

function ns.Layout()
    if not ns.ui or not ns.ui.metrics then return end
    local width = ns.window:GetWidth() or 860
    ns.ui.contentWidth = width - 74
    local metricWidth = (width - 80) / 3
    for index, metric in ipairs(ns.ui.metrics) do
        metric:SetSize(metricWidth, 20)
        metric:ClearAllPoints()
        metric:SetPoint("TOPLEFT", 26 + (index - 1) * (metricWidth + 14), -64)
    end
    ns.ui.party:SetWidth(width - 52)
    ns.ui.hint:SetWidth(width - 52)
    ns.ui.status:ClearAllPoints()
    ns.ui.status:SetPoint("BOTTOMLEFT", 272, 19)
    ns.ui.status:SetWidth(width - 458)
    ns.ui.status:SetWordWrap(false)
    ns.ui.content:SetWidth(ns.ui.contentWidth)
    ns.ui.empty:SetWidth(ns.ui.contentWidth - 36)
    if ns.ui.librarySearch then ns.ui.librarySearch:SetWidth(width - 324) end
    if ns.ui.guideSearch then ns.ui.guideSearch:SetWidth(width - 352); ns.ui.guideCount:SetWidth(width - 154) end
    if ns.ui.levelButtons then
        local chipWidth = (width - 94) / 8
        for index, chip in ipairs(ns.ui.levelButtons) do
            chip:SetWidth(chipWidth)
            chip:ClearAllPoints()
            chip:SetPoint("TOPLEFT", 26 + (index - 1) * (chipWidth + 6), -180)
        end
        ns.ui.libraryCount:SetWidth(width - 154)
    end
    ns.ui.viewDescription:SetWidth(width - 292)
    ns.ui.viewDescription:SetWordWrap(false)
    for _, card in ipairs(ns.ui.cards) do
        card:SetWidth(ns.ui.contentWidth)
        ns.LayoutGuideCardTheme(card)
        card.title:SetWidth(ns.ui.contentWidth - 146)
        card.reason:SetWidth(ns.ui.contentWidth - 24)
        local count = card.memberCount or 0
        local cellWidth = (ns.ui.contentWidth - 24 - math.max(0, count - 1) * 6) / math.max(1, count)
        for index = 1, count do
            local cell = card.memberCells[index]
            cell:SetWidth(cellWidth); cell:ClearAllPoints()
            cell:SetPoint("TOPLEFT", 12 + (index - 1) * (cellWidth + 6), -card.memberTop)
            cell.name:SetWidth(cellWidth - 12); cell.state:SetWidth(cellWidth - 12); cell.history:SetWidth(cellWidth - 12)
        end
    end
end

local function makeCard()
    local card = CreateFrame("Button", nil, ns.ui.content, "BackdropTemplate")
    panel(card)
    card.accent = card:CreateTexture(nil, "ARTWORK")
    card.accent:SetPoint("TOPLEFT", 0, 0)
    card.accent:SetPoint("BOTTOMLEFT", 0, 0)
    card.accent:SetWidth(2)
    card.category = label(card, nil, 9, colors.muted)
    card.category:SetPoint("TOPLEFT", 14, -10)
    card.category:SetHeight(12); card.category:SetWordWrap(false)
    card.title = label(card, "GameFontNormalLarge", 14, {0.94, 0.94, 0.90, 1})
    card.title:SetPoint("TOPLEFT", 14, -26)
    card.title:SetWidth(660)
    card.title:SetHeight(18); card.title:SetWordWrap(false)
    card.title:SetJustifyV("TOP")
    card.count = label(card, nil, 12, colors.gold)
    card.count:SetPoint("TOPRIGHT", -14, -28)
    card.count:SetWidth(118); card.count:SetJustifyH("RIGHT"); card.count:SetWordWrap(false)
    card.reason = label(card, nil, 11, colors.muted)
    card.reason:SetPoint("TOPLEFT", 14, -51)
    card.reason:SetWidth(760)
    card.reason:SetHeight(56)
    card.reason:SetJustifyV("TOP")
    card.memberCells = {}
    local function activate()
        if card.activity then card.activity.click()
        elseif card.libraryItem then
            local item = card.libraryItem
            if item.zoneKey then ns.OpenLibraryZone(item.zoneKey, item.mapID)
            elseif card.guide and card.guide.hasPoint then ns.ShowGuideOnMap(card.guide)
            else ns.ShowQuestDetails(item.id) end
        elseif card.guide then
            ns.selectedGuide = card.guide.key
            if ns.filter == "guides" and card.guide.fullGuide then ns.ShowGuideQuestList(card.guide); return end
            if card.guide.fullGuide or card.guide.hasPoint then ns.ShowGuideOnMap(card.guide) else ns.ShowQuestDetails(card.guide.target.id) end
        end
    end
    card.mapButton = button(card, "Show route", 128, activate)
    card.detailsButton = button(card, "Quest details", 116, function()
        if card.activity and card.activity.dungeon then ns.ShowDungeonQuestList(card.activity.dungeon); return end
        if card.guide and not card.libraryItem and not card.guide.personal then ns.RequestStartRoute(card.guide); return end
        local id = card.libraryItem and card.libraryItem.id or (card.guide and card.guide.target.id)
        if id then ns.ShowQuestDetails(id) end
    end, true)
    card.buyButton = button(card, "Buy list", 96, function()
        if card.guide then ns.ShowShoppingList(ns.QuestShoppingList(card.guide.records), "Your quest buy list") end
    end)
    card.buyButton:SetPoint("BOTTOMLEFT", 138, 10)
    card.catchupButton = button(card, "Catch up party", 138, function()
        if card.guide then ns.ShowPartyCatchup(card.guide, true) end
    end)
    card.catchupButton:SetPoint("BOTTOMLEFT", 240, 10)
    card.detailsButton:SetPoint("BOTTOMLEFT", 14, 10)
    card.mapButton:SetPoint("BOTTOMRIGHT", -14, 10)
    card:RegisterForClicks("LeftButtonUp")
    card:SetScript("OnClick", activate)
    return card
end

local function renderMembers(card, members, top)
    card.memberCount, card.memberTop = #members, top
    for _, cell in ipairs(card.memberCells) do cell:Hide() end
    local width = (ns.ui.contentWidth - 24 - (#members - 1) * 6) / math.max(1, #members)
    for index, member in ipairs(members) do
        local cell = card.memberCells[index]
        if not cell then
            cell = CreateFrame("Frame", nil, card, "BackdropTemplate")
            panel(cell, colors.background)
            cell:EnableMouse(true)
            cell.name = label(cell, nil, 11, {0.90, 0.92, 0.94, 1})
            cell.name:SetPoint("TOPLEFT", 7, -5)
            cell.state = label(cell, nil, 10)
            cell.state:SetPoint("TOPLEFT", 7, -18)
            cell.history = label(cell, nil, 9, colors.muted)
            cell.history:SetPoint("TOPLEFT", 7, -30)
            cell:SetScript("OnEnter", function(self)
                if not GameTooltip then return end
                GameTooltip:SetOwner(self, "ANCHOR_TOP")
                GameTooltip:AddLine(self.fullName, 1, 1, 1)
                GameTooltip:AddLine(self.description, 0.85, 0.89, 0.92, true)
                GameTooltip:AddLine("Unfinished history does not confirm level, faction, or prerequisites.", 0.93, 0.73, 0.39, true)
                GameTooltip:Show()
            end)
            cell:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
            card.memberCells[index] = cell
        end
        cell:ClearAllPoints()
        cell:SetPoint("TOPLEFT", 12 + (index - 1) * (width + 6), -top)
        cell:SetSize(width, 43)
        cell.name:SetWidth(width - 14)
        cell.name:SetHeight(12)
        cell.name:SetWordWrap(false)
        cell.state:SetWidth(width - 14)
        cell.state:SetHeight(12)
        cell.state:SetWordWrap(false)
        cell.history:SetWidth(width - 14)
        cell.history:SetHeight(11)
        cell.history:SetWordWrap(false)
        local state, color
        if member.active and member.ready then state, color = "Ready to turn in", {0.56, 0.78, 0.94, 1}
        elseif member.active then state, color = "Active", {0.44, 0.84, 0.63, 1}
        elseif member.offered then state, color = "Quest giver offered", {0.56, 0.78, 0.94, 1}
        elseif member.history == "completed" then state, color = "Completed", colors.muted
        else state, color = "Not in log", colors.gold end
        cell.name:SetText(member.name)
        cell.state:SetText(state)
        cell.state:SetTextColor(unpack(color))
        cell.history:SetText(member.history == "completed" and "History: completed"
            or (member.history == "not_completed" and "History: unfinished" or "History: pending"))
        cell.fullName, cell.description = member.name, member.status
        cell:Show()
    end
end

function ns.Render(queryContext, routeUpdated)
    if not ns.ui then return end
    local partyEnabled = ns.PartyFeaturesEnabled()
    if ns.ui.partyMode ~= partyEnabled then
        ns.ui.partyMode = partyEnabled
        ns.ui.viewChoice:SetVisibleEntries(function(key) return partyEnabled or not ns.IsPartyView(key) end)
        ns.ui.trackerButton:SetShown(partyEnabled); ns.ui.syncButton:SetShown(partyEnabled)
        ns.ui.subtitle:SetText(partyEnabled and "Choose a questline, compare your party, and find the next stop."
            or "Follow your leveling guide and find the next stop.")
        ns.ui.viewDescription:SetText(partyEnabled and "Choose a guide or explore your party's progress." or "Choose a solo guide or browse quests.")
        ns.ui.guideLevel.entries[1][2] = partyEnabled and "My party's bracket" or "My level bracket"
        ns.ui.guideLevel.options.party.caption:SetText(ns.ui.guideLevel.entries[1][2])
        for _, chip in ipairs(ns.ui.levelButtons) do if chip.levelKey == "party" then chip.caption:SetText(partyEnabled and "Near party" or "My level") end end
    end
    queryContext = queryContext or ns.NewQuestQuery()
    local rows = (ns.filter == "all" or ns.filter == "shared" or ns.filter == "different" or ns.filter == "suggestions") and ns.Rows(queryContext) or {}
    local synced, shared, own = 1, 0, 0
    for _, member in pairs(ns.members) do if member.active and not member.syncPending then synced = synced + 1 end end
    for _, row in ipairs(rows) do if row.active >= 2 then shared = shared + 1 end end
    for _ in pairs(ns.active or {}) do own = own + 1 end
    ns.ui.metrics[1].caption:SetText(partyEnabled and "PARTY SYNC" or "PLAY MODE")
    ns.ui.metrics[1].value:SetText(partyEnabled and (synced .. " / " .. (#(ns.partyNames or {}) + 1)) or "SOLO")
    local choices = ns.filter == "guides" and ns.GuideBrowserChoices(nil, queryContext) or {}
    ns.ui.hint:SetText(ns.filter == "guides"
        and "Start a guide to follow its quest order. Search by zone, quest or NPC."
        or "Choose a quest to see its route or requirements.")
    if not routeUpdated and ns.UpdateSelectedRoute then ns.UpdateSelectedRoute(choices, queryContext) end
    ns.ui.metrics[2].caption:SetText(ns.filter == "library" and "CATALOGUE QUESTS" or (ns.filter == "guides" and "QUEST GUIDES" or "SHARED ACTIVE"))
    ns.ui.metrics[2].value:SetText(tostring(ns.filter == "library" and ns.catalogue.count or (ns.filter == "guides" and #choices or shared)))
    ns.ui.metrics[3].value:SetText(tostring(own))
    local peers = {"You" .. (ns.profile and ns.profile.level > 0 and (" • Lv " .. ns.profile.level) or " • level pending")}
    for _, name in ipairs(ns.partyNames or {}) do
        local member = ns.members[name]
        local profile = member and member.profile
        local syncLabel = member and member.syncPending and " |cffe4b66arefreshing|r" or (member and member.active and " |cff70d6a0synced|r" or " |cffe4b66awaiting|r")
        peers[#peers + 1] = ns.MemberLabel(name) .. (profile and profile.level > 0 and (" • Lv " .. profile.level) or " • level pending") .. syncLabel
    end
    ns.ui.party:SetText(#peers > 0 and table.concat(peers, "    /    ") or "Join a party to compare progress with friends running Wow Together.")
    local zone = type(GetZoneText) == "function" and GetZoneText() or nil
    ns.ui.zone:SetText(ns.Public(zone) and type(zone) == "string" and zone or "")
    local transport = ns.TransportState()
    local status
    if transport.queued > 0 then
        status = transport.retrying and "Delivery slowed; retrying" or ("Sending updates: " .. transport.queued .. " left")
    elseif string.find(ns.status, "Delivery failed", 1, true) then status = "Delivery failed; see Diagnostics"
    elseif not ns.questReady then status = "Quest data unavailable; see Diagnostics"
    elseif not partyEnabled then status = ns.routePlanningError or ns.guideAction or "Solo leveling ready"
    elseif not ns.syncReady then status = "Sync unavailable; see Diagnostics"
    else status = ns.routePlanningError or ns.guideAction or (synced > 1 and "Party progress received" or "Waiting for friends") end
    ns.ui.status:SetText(status)
    ns.ui.viewChoice:SetChoice(ns.filter)
    for _, card in ipairs(ns.ui.cards) do card:Hide() end
    local visible, top = 0, 0
    local display = {}
    if ns.filter == "library" then
        local items, total, pages = ns.LibraryPageItems()
        for _, item in ipairs(items) do display[#display + 1] = {libraryItem = item} end
        ns.ui.libraryCount:SetText(total .. " results • Page " .. ns.libraryPage .. " / " .. pages .. " • Enter or pause to search")
        ns.ui.libraryPrev:SetEnabled(ns.libraryPage > 1)
        ns.ui.libraryNext:SetEnabled(ns.libraryPage < pages)
        for _, chip in ipairs(ns.ui.levelButtons) do chip:SetBackdropBorderColor(unpack(chip.levelKey == ns.libraryLevel and colors.gold or colors.border)) end
    elseif ns.filter == "guides" then
        local pages = math.max(1, math.ceil(#choices / 12))
        ns.guidePage = math.max(1, math.min(pages, ns.guidePage or 1))
        for index = (ns.guidePage - 1) * 12 + 1, math.min(#choices, ns.guidePage * 12) do
            display[#display + 1] = {guide = choices[index], recommended = index == 1 and choices[index].levelReady == true}
        end
        local low, high = ns.GuideLevelRange(nil, queryContext)
        ns.ui.guideCount:SetText("Levels " .. low .. "–" .. high .. " • " .. #choices .. " guides • Page " .. ns.guidePage .. " / " .. pages .. " • Enter or pause to search")
        ns.ui.guidePrev:SetEnabled(ns.guidePage > 1); ns.ui.guideNext:SetEnabled(ns.guidePage < pages)
        ns.ui.guideLevel:SetChoice(ns.guideLevel)
    elseif ns.filter == "suggestions" then
        for _, suggestion in ipairs(ns.Suggestions()) do
            display[#display + 1] = {row = suggestion.row, suggestion = suggestion}
        end
    elseif ns.filter == "dungeons" then
        for _, group in ipairs(ns.DungeonGroups()) do
            local dungeon = group
            local activity = {title = group.name, category = "DUNGEON QUEST COLLECTION", dungeon = group,
                detail = ns.DungeonOverviewSummary(group) .. "\n" .. ns.DungeonCollectionSummary(group),
                action = #group.ids > 0 and "Start route" or "View details", click = function()
                    local guide = ns.DungeonGuide(dungeon)
                    if guide and guide.hasPoint then ns.RequestStartRoute(guide) else ns.ShowDungeonQuestList(dungeon) end
                end}
            display[#display + 1] = {activity = activity}
        end
    elseif ns.filter == "professions" then
        for _, activity in ipairs(ns.ProfessionChoices()) do display[#display + 1] = {activity = activity} end
    elseif ns.filter == "review" then
        for _, review in ipairs(ns.QuestLogReview()) do
            local id = review.id
            display[#display + 1] = {activity = {title = review.title, category = "QUEST LOG REVIEW",
                detail = "Consider abandoning if you no longer want this quest. " .. review.reason .. " Review the game quest log before deciding; no quest is abandoned automatically.",
                action = "Review quest", click = function() ns.ShowQuestDetails(id) end}}
        end
    else
        if ns.filter == "all" then
            for _, guide in ipairs(ns.CurrentQuestChoices() or {}) do display[#display + 1] = {guide = guide} end
        end
        for _, row in ipairs(rows) do
            local show = ns.filter == "all" or (ns.filter == "shared" and row.active >= 2)
                or (ns.filter == "different" and row.active < row.people)
            if show then display[#display + 1] = {row = row} end
        end
    end
    for _, item in ipairs(display) do
        local row, suggestion, guide, libraryItem, activity = item.row, item.suggestion, item.guide, item.libraryItem, item.activity
        if libraryItem and libraryItem.id then
            local record = ns.CatalogueRecord(libraryItem.id)
            guide = {key = "quest:" .. libraryItem.id, title = libraryItem.quest.title, records = {record}, target = record, focusKey = ns.self,
                personal = ns.IsProfessionQuest(libraryItem.id)}
            local plan = ns.BuildGuideRoute(guide, false)
            guide.hasPoint = #plan.stops > 0
        end
        visible = visible + 1
        local card = ns.ui.cards[visible]
        if not card then card = makeCard(); ns.ui.cards[visible] = card end
        card:ClearAllPoints()
        card:SetScript("OnEnter", nil); card:SetScript("OnLeave", nil)
        card:SetPoint("TOPLEFT", 0, -top)
        card.title:SetWidth(ns.ui.contentWidth - 146)
        card.category:SetWidth(ns.ui.contentWidth - 28)
        card.reason:SetWidth(ns.ui.contentWidth - 24)
        for _, cell in ipairs(card.memberCells) do cell:Hide() end
        card.memberCount = 0
        card.guide = guide
        card.libraryItem = libraryItem
        card.activity = activity
        card.mapButton:SetShown(guide ~= nil or libraryItem ~= nil or activity ~= nil)
        card.detailsButton:SetShown(guide ~= nil or (activity and activity.dungeon) ~= nil)
        card.detailsButton.caption:SetText("Quest details")
        card.detailsButton:SetEnabled(true)
        card.buyButton:SetShown(guide ~= nil and #ns.QuestShoppingList(guide.records, queryContext) > 0)
        card.catchupButton:SetShown(guide ~= nil and guide.mode == "zone" and guide.fullGuide
            and not guide.catchup and partyEnabled and #(ns.partyNames or {}) > 0 and ns.ReadPublic(IsInRaid) ~= true)
        card.mapButton:SetEnabled(true)
        local height
        if activity then
            height = 138
            card.accent:SetColorTexture(unpack(colors.gold)); card.category:SetText(activity.category)
            card.title:SetText(activity.title); card.count:SetText(activity.dungeon and activity.dungeon.definition
                and ("Lv " .. activity.dungeon.definition.runLevelLow .. "–" .. activity.dungeon.definition.runLevelHigh) or "")
            card.reason:Show(); card.reason:SetHeight(46); card.reason:SetText(activity.detail)
            ns.UIHelp(card, activity.title .. "\n" .. activity.detail)
            card.mapButton.caption:SetText(activity.action)
            if activity.dungeon then card.detailsButton.caption:SetText("Quest list") end
        elseif libraryItem then
            height = libraryItem.id and 122 or 108
            card.accent:SetColorTexture(unpack(colors.gold))
            card.category:SetText(libraryItem.id and (ns.ClassQuestLabel(libraryItem.id) or (ns.IsProfessionQuest(libraryItem.id) and "PERSONAL PROFESSION QUEST") or ns.CatalogueZone(libraryItem.quest)) or "EXPLORE A ZONE")
            card.title:SetText(libraryItem.id and libraryItem.quest.title or libraryItem.zone)
            card.count:SetText(libraryItem.id and ("Lv " .. (libraryItem.quest.level or "?")) or tostring(libraryItem.count))
            card.reason:Show()
            card.reason:SetHeight(height - 90)
            if libraryItem.id then
                local quest = libraryItem.quest
                local _, reason = ns.CatalogueAllowed(libraryItem.id, ns.profile, ns.self, queryContext)
                card.reason:SetText("Requires level " .. (quest.minLevel or "unknown") .. " • " .. (quest.side or "Faction not supplied")
                    .. "\n" .. (reason or (quest.starts and ("Start: " .. quest.starts[1].name) or "Quest giver coordinates are not supplied.")))
                card.mapButton.caption:SetText(guide.hasPoint and "Show route" or "View details")
            else
                card.reason:SetText(libraryItem.count .. " known quests • " .. libraryItem.mapped .. " with published pickup locations")
                card.mapButton.caption:SetText("Browse quests")
            end
            ns.UIHelp(card, card.title:GetText() .. "\n" .. card.reason:GetText())
        elseif guide then
            height = 122
            if guide.mode == "bundle" then height = height + 52 end
            local selected = ns.routeSelection and ns.routeSelection.key == guide.key
            card.accent:SetColorTexture(unpack(selected and colors.success or item.recommended and colors.gold or colors.border))
            if guide.mode == "travel" then
                card.category:SetText("TRAVEL GUIDE")
            elseif ns.filter == "guides" then
                card.category:SetText(guide.upcoming and "UPCOMING ZONE GUIDE" or item.recommended and "RECOMMENDED ZONE GUIDE"
                    or guide.levelReady and "ALTERNATIVE ZONE GUIDE" or "ZONE GUIDE")
            else
                card.category:SetText(item.recommended and (guide.catchup and "RECOMMENDED / CATCH UP FIRST" or "RECOMMENDED NEXT STEP")
                    or (string.upper(guide.kind) .. " / ALTERNATIVE"))
            end
            card.title:SetText(guide.title)
            card.count:SetText((guide.fullGuide or guide.mode == "travel") and guide.minLevel and ("Lv " .. (guide.mainLevelLow or guide.minLevel) .. "–" .. (guide.mainLevelHigh or guide.maxLevel)) or (guide.level and ("Quest Lv " .. guide.level) or ""))
            card.reason:SetHeight(height - 90)
            local nextTitle = guide.nextStop and guide.nextStop.label or guide.target.title
            local _, requirement = ns.CatalogueAllowed(guide.target.id, ns.profile, ns.self, queryContext)
            local coverage = guide.coverage
            local detail = guide.fullGuide and (coverage and ("Published: " .. coverage.pickups .. "/" .. coverage.quests .. " pickups • "
                .. coverage.objectives .. "/" .. coverage.quests .. " objectives • " .. coverage.turnins .. "/" .. coverage.quests .. " turn-ins")
                or (guide.knownStops .. " selected quest(s) have a known pickup location."))
                or guide.hasPoint and (guide.knownStops .. " mapped stops • Next: " .. nextTitle)
                or (requirement or "No NPC or objective coordinates are available for this step yet.")
            local summary = guide.fullGuide and (#guide.records .. " quests • " .. (selected and "Following this guide" or "Fixed quest order")) or guide.reason
            card.reason:SetText(summary .. "\n" .. (guide.upcoming and "Preview its quest list now; starting early shows a level warning."
                or guide.fullGuide and ns.GuideXPText(guide, queryContext) or detail))
            if guide.fullGuide then
                ns.GuideXPHelp(card)
                -- Keep source counts and long descriptions available without
                -- filling each guide row with diagnostic metadata.
                local xpHelp = card:GetScript("OnEnter")
                card:SetScript("OnEnter", function(self)
                    if xpHelp then xpHelp(self) end
                    if GameTooltip then GameTooltip:AddLine(guide.title, 1, 1, 1, true); GameTooltip:AddLine(detail, 0.65, 0.67, 0.66, true); GameTooltip:Show() end
                end)
            else ns.UIHelp(card, guide.title .. "\n" .. summary .. "\n" .. detail) end
            card.reason:Show()
            card.mapButton.caption:SetText(ns.filter == "guides" and guide.fullGuide and "Show quest list" or (guide.hasPoint and "Show route" or "View details"))
            card.detailsButton.caption:SetText("Start route")
            card.detailsButton:SetShown(not guide.personal or guide.mode == "travel")
            card.detailsButton:SetEnabled(guide.fullGuide == true or guide.hasPoint == true)
        else
            height = suggestion and 169 or 110
            card.accent:SetColorTexture(unpack(row.active >= 2 and {0.35, 0.77, 0.57, 1} or colors.gold))
            card.category:SetText(suggestion and string.upper(suggestion.category)
                or (row.active >= 2 and "SHARED ACTIVE QUEST" or (row.people == 1 and "YOUR ACTIVE QUEST" or "DIFFERENT PROGRESS")))
            card.title:SetText(row.title)
            card.count:SetText(row.active .. " / " .. row.people)
            card.reason:SetShown(suggestion ~= nil)
            if suggestion then
                local waiting = #(ns.partyNames or {}) + 1 - row.people
                local caveat = waiting > 0 and (" " .. waiting .. " detected party member(s) still need to sync.") or ""
                card.reason:SetHeight(56)
                card.reason:SetText(suggestion.reason .. caveat .. "\nNext: " .. suggestion.action)
            end
            renderMembers(card, row.members, suggestion and 118 or 59)
        end
        card:SetSize(ns.ui.contentWidth, height)
        ns.ApplyGuideCardTheme(card, not libraryItem and guide or nil, activity and activity.dungeon)
        card:Show()
        top = top + height + 8
    end
    ns.ui.visibleCards = visible
    if ns.filter == "dungeons" or ns.filter == "professions" then
        ns.ui.metrics[2].caption:SetText(ns.filter == "dungeons" and "DUNGEON GUIDES" or "PERSONAL GUIDES")
        ns.ui.metrics[2].value:SetText(tostring(visible))
    end
    ns.ui.empty:SetShown(visible == 0)
    ns.ui.empty:SetText(ns.filter == "library" and "No imported quests match this search.\nTry a quest or zone name."
        or (ns.filter == "review" and "No unfinished quests need a low-value review.\nReady turn-ins and class/profession quests are kept."
        or (ns.filter == "guides" and "No zone guides match this bracket and search.\nChoose another bracket or clear the search to browse future guides."
        or (ns.filter == "suggestions" and "Sync with a friend to get party suggestions."
        or (#rows == 0 and "Your adventure starts with a quest.\nAccept one, then sync your party."
        or "No quests in this view yet.\nTry All quests or compare more progress with friends.")))))
    ns.ui.content:SetHeight(math.max(250, top))
end

function ns.ShowDiagnostics(report, caption, onRefresh)
    if not ns.diagnosticsWindow then
        local window = CreateFrame("Frame", "WowTogetherDiagnostics", UIParent, "BackdropTemplate")
        ns.diagnosticsWindow = window
        window:SetSize(660, 560)
        window:SetClampedToScreen(true)
        window:SetPoint("CENTER")
        window:SetFrameStrata("DIALOG")
        panel(window, colors.background, colors.gold)
        window:SetMovable(true)
        window:EnableMouse(true)
        window:RegisterForDrag("LeftButton")
        window:SetScript("OnDragStart", window.StartMoving)
        window:SetScript("OnDragStop", window.StopMovingOrSizing)
        local title = window:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        window.title = title
        title:SetPoint("TOPLEFT", 20, -20)
        title:SetText("Wow Together — Diagnostics")
        ns.UIClose(window)
        local hint = window:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        hint:SetPoint("TOPLEFT", 20, -48)
        hint:SetText("Select all, then Ctrl+C. The window closes after copying.")
        local scroll = CreateFrame("ScrollFrame", nil, window, "UIPanelScrollFrameTemplate")
        scroll:SetPoint("TOPLEFT", 20, -75)
        scroll:SetPoint("BOTTOMRIGHT", -40, 60)
        ns.diagnosticsScroll = scroll
        local edit = CreateFrame("EditBox", nil, scroll)
        ns.diagnosticsText = edit
        edit:SetMultiLine(true)
        if type(edit.SetMaxLetters) == "function" then edit:SetMaxLetters(0) end
        edit:SetAutoFocus(false)
        edit:SetFontObject("ChatFontNormal")
        edit:SetSize(575, 900)
        edit:SetScript("OnEscapePressed", function(self)
            self:ClearFocus()
            window:Hide()
        end)
        edit:SetScript("OnKeyDown", function(_, key)
            if not ns.Public(key) or key ~= "C" or type(IsControlKeyDown) ~= "function" then return end
            local control = IsControlKeyDown()
            if not ns.Public(control) or not control then return end
            if not C_Timer or type(C_Timer.After) ~= "function" then return end
            local generation = ns.diagnosticsGeneration
            -- Native EditBox copying runs first. Do not intercept or replace it.
            C_Timer.After(0.1, function()
                if generation == ns.diagnosticsGeneration then window:Hide(); edit:ClearFocus() end
            end)
        end)
        scroll:SetScrollChild(edit)
        window:SetScript("OnHide", function() edit:ClearFocus() end)
        local selectAll = CreateFrame("Button", nil, window, "UIPanelButtonTemplate")
        selectAll:SetSize(110, 24)
        selectAll:SetPoint("BOTTOMLEFT", 20, 20)
        selectAll:SetText("Select all")
        selectAll:SetScript("OnClick", function()
            edit:SetFocus()
            edit:HighlightText()
        end)
        local refresh = CreateFrame("Button", nil, window, "UIPanelButtonTemplate")
        refresh:SetSize(110, 24)
        refresh:SetPoint("BOTTOMRIGHT", -20, 20)
        refresh:SetText("Refresh")
        refresh:SetScript("OnClick", function() ns.reportRefresh() end)
    end
    ns.diagnosticsGeneration = (ns.diagnosticsGeneration or 0) + 1
    ns.reportRefresh = onRefresh or ns.Diagnostics
    ns.diagnosticsWindow.title:SetText(caption or "Wow Together — Diagnostics")
    local _, lineCount = string.gsub(report, "\n", "\n")
    ns.diagnosticsText:SetHeight(math.max(900, (lineCount + 1) * 30))
    ns.diagnosticsText:SetText(report)
    ns.diagnosticsText:ClearFocus()
    ns.diagnosticsScroll:SetVerticalScroll(0)
    ns.diagnosticsWindow:Show()
end
