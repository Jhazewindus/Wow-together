local addonName, ns = ...

local defaults = {autoAccept = false, npcHints = true, classQuests = false,
    dungeonPrompts = true, zonePrompts = true, trackerOpacity = 0.08,
    trackerHeight = 350, circuitRadius = 0.16, circuitLimit = 6, mapLegend = true, professionBatch = 5, routeArrow = true,
    currentQuestsFirst = true, nearbyPickups = true}

function ns.Option(key)
    local value = ns.db and ns.db.config and ns.db.config[key]
    if value == nil then return defaults[key] end
    return value
end

function ns.InitializeConfig()
    if type(ns.db.config) ~= "table" then ns.db.config = {} end
    for key, value in pairs(defaults) do
        local configured = ns.db.config[key]
        if type(configured) ~= type(value) or (type(configured) == "number"
            and (configured ~= configured or configured == math.huge or configured == -math.huge)) then ns.db.config[key] = value end
    end
    ns.db.config.trackerOpacity = math.max(0, math.min(0.8, ns.db.config.trackerOpacity))
    ns.db.config.trackerHeight = math.max(180, math.min(600, ns.db.config.trackerHeight))
    ns.db.config.circuitRadius = math.max(0.08, math.min(0.24, ns.db.config.circuitRadius))
    ns.db.config.circuitLimit = math.max(2, math.min(6, math.floor(ns.db.config.circuitLimit)))
    ns.db.config.professionBatch = math.max(1, math.min(20, math.floor(ns.db.config.professionBatch)))
end

function ns.SetOption(key, value)
    if defaults[key] == nil or type(value) ~= type(defaults[key]) then return end
    ns.db.config[key] = value
    ns.InitializeConfig()
    if ns.RenderSettings then ns.RenderSettings() end
    if ns.UpdateNPCHints then ns.UpdateNPCHints() end
    if ns.DrawRoute then ns.DrawRoute() end
    ns.Refresh()
end

function ns.AutoAcceptOpenedQuest(id)
    if not ns.Option("autoAccept") or type(AcceptQuest) ~= "function" or ns.RouteInCombat()
        or not ns.GuideInteger(id) or id <= 0 or ns.autoAcceptAttempt == id then return end
    if type(CanAcceptQuest) == "function" then
        local allowed = CanAcceptQuest()
        if not ns.Public(allowed) or allowed ~= true then return end
    end
    ns.autoAcceptAttempt = id
    -- Opt-in, one opened quest dialog only. No gossip selection or turn-in.
    AcceptQuest()
    ns.ScheduleSync()
end

function ns.CreateSettings()
    local frame = CreateFrame("Frame", "WowTogetherSettings", UIParent, "BackdropTemplate")
    ns.settings = frame
    frame:SetSize(560, 668); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
    frame:SetClampedToScreen(true); ns.UIPanel(frame)
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    local title = ns.UILabel(frame, "GameFontNormalLarge", 20)
    title:SetPoint("TOPLEFT", 22, -20); title:SetText("Wow Together settings")
    local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton"); close:SetPoint("TOPRIGHT", -4, -4)
    frame.checks = {}
    for index, entry in ipairs({{"autoAccept", "Auto-accept the quest dialog I open (beta test; off by default)"},
        {"npcHints", "Show quest NPC hints outside combat"}, {"classQuests", "Include class quests in party guides (label restrictions)"},
        {"dungeonPrompts", "Suggest collecting dungeon quests when in level range"},
        {"zonePrompts", "Suggest nearby zone transitions from known questlines"}, {"mapLegend", "Show the small map route legend"},
        {"routeArrow", "Show the movable direction arrow for my selected route"},
        {"currentQuestsFirst", "Finish our current quests first (ready turn-ins before new pickups)"},
        {"nearbyPickups", "Include eligible nearby pickups in our current quest trip"}}) do
        local key = entry[1]
        local check = CreateFrame("CheckButton", nil, frame, "UICheckButtonTemplate")
        check:SetPoint("TOPLEFT", 20, -52 - (index - 1) * 34); check:SetSize(26, 26)
        check.caption = ns.UILabel(check, nil, 11); check.caption:SetPoint("LEFT", check, "RIGHT", 7, 0)
        check.caption:SetWidth(472); check.caption:SetText(entry[2])
        check:SetScript("OnClick", function(self) ns.SetOption(key, self:GetChecked() == true) end)
        if key == "autoAccept" then check:SetEnabled(type(AcceptQuest) == "function") end
        frame.checks[key] = check
    end
    frame.values = {}
    local presets = {{"trackerOpacity", "Tracker background", {0, 0.08, 0.25, 0.5}, {"Clear", "Subtle", "25%", "50%"}},
        {"trackerHeight", "Tracker height", {220, 350, 500}, {"Small", "Medium", "Tall"}},
        {"circuitRadius", "Walking detour budget", {0.10, 0.16, 0.22}, {"Short", "Balanced", "Wider"}},
        {"circuitLimit", "Quests per circuit", {2, 4, 6}, {"2", "4", "6"}},
        {"professionBatch", "Profession craft batch", {1, 5, 10, 20}, {"1", "5", "10", "20"}}}
    for index, entry in ipairs(presets) do
        local key = entry[1]
        local caption = ns.UILabel(frame, nil, 11); caption:SetPoint("TOPLEFT", 22, -372 - (index - 1) * 43)
        caption:SetText(entry[2]); caption:SetWidth(180)
        for column, value in ipairs(entry[3]) do
            local control = ns.UIButton(frame, entry[4][column], 74, function() ns.SetOption(key, value) end)
            control:SetPoint("TOPLEFT", 202 + (column - 1) * 80, -362 - (index - 1) * 43)
            control.optionKey, control.optionValue = key, value
            frame.values[#frame.values + 1] = control
        end
    end
    frame.note = ns.UILabel(frame, nil, 11)
    frame.note:SetPoint("BOTTOMLEFT", 22, 20); frame.note:SetWidth(510); frame.note:SetHeight(65)
    frame:Hide()
    if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherSettings") end
end

function ns.RenderSettings()
    if not ns.settings then return end
    for key, check in pairs(ns.settings.checks) do check:SetChecked(ns.Option(key)) end
    for _, control in ipairs(ns.settings.values) do
        control:SetBackdropBorderColor(ns.Option(control.optionKey) == control.optionValue and 0.93 or 0.19,
            ns.Option(control.optionKey) == control.optionValue and 0.73 or 0.23, 0.39, 1)
    end
    ns.settings.note:SetText("Party sync is automatic on group, quest, objective, level, and zone changes.\nProfession recipes and shopping plans stay on your client. Auto-accept only handles opened dialogs; verify it on your beta build.")
end

function ns.ToggleSettings()
    ns.settings:SetShown(not ns.settings:IsShown()); ns.RenderSettings()
end
