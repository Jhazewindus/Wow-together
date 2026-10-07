local addonName, ns = ...

local ROW_HEIGHT, VIEW_HEIGHT = 44, 396
local phases = {a = "Pick up", q = "Objectives", t = "Turn in"}
local colors = {a = {1, 0.82, 0.3}, q = {0.92, 0.88, 0.76}, t = {0.55, 0.84, 0.58}}

local function layout(frame)
    local width, height = frame:GetWidth() - 76, math.max(100, frame:GetHeight() - 164)
    frame.viewHeight = height
    frame.title:SetWidth(frame:GetWidth() - 80); frame.summary:SetWidth(frame:GetWidth() - 50)
    frame.scroll:SetSize(width, height); frame.content:SetWidth(width); frame.slider:SetHeight(height - 32)
    frame.empty:SetSize(width - 40, math.max(80, height - 40))
    for _, row in ipairs(frame.rows) do
        row:SetWidth(width); row.title:SetWidth(width - 250); row.detail:SetWidth(width - 60)
    end
end

local function status(stop, query)
    if ns.GuideQuestSkipped(stop.id) or #ns.FilterGuideStages({stop}) == 0 then return "Skipped" end
    if ns.Completed(stop.id, query) == true then return "Done" end
    if not ns.LevelingWorkAllowed(stop.id, ns.self, query) then return "Outside level range" end
    local active = ns.active and ns.active[stop.id]
    if active then
        if stop.kind == "a" then return "Accepted" end
        if ns.readyToTurnIn[stop.id] or ns.QuestProgressReady(ns.self, stop.id) then
            return stop.kind == "t" and "Ready" or "Done"
        end
        return stop.kind == "q" and "In progress" or "Later"
    end
    if ns.LevelingValue(stop.id, query) == false then return "Outside level range" end
    local allowed = ns.CatalogueAllowed(stop.id, ns.profile, ns.self, query)
    return allowed == true and stop.kind == "a" and "Available" or "Later"
end

local function create()
    if ns.guideQuestList then return ns.guideQuestList end
    local frame = CreateFrame("Frame", "WowTogetherGuideQuestList", UIParent, "BackdropTemplate")
    ns.guideQuestList = frame
    frame:SetSize(740, 560); frame:SetPoint("CENTER"); frame:SetClampedToScreen(true)
    frame:SetFrameStrata("DIALOG"); ns.UIPanel(frame, ns.UIColors.background)
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    frame.title = ns.UILabel(frame, "GameFontNormalLarge", 18); frame.title:SetPoint("TOPLEFT", 22, -18); frame.title:SetSize(660, 24); frame.title:SetWordWrap(false)
    frame.summary = ns.UILabel(frame, nil, 11, ns.UIColors.muted); frame.summary:SetPoint("TOPLEFT", 22, -51); frame.summary:SetSize(690, 42)
    ns.UIClose(frame); ns.UIDivider(frame, -99)
    frame.scroll = CreateFrame("ScrollFrame", nil, frame); frame.scroll:SetPoint("TOPLEFT", 22, -110); frame.scroll:SetSize(664, VIEW_HEIGHT)
    frame.content = CreateFrame("Frame", nil, frame.scroll); frame.content:SetSize(664, VIEW_HEIGHT); frame.scroll:SetScrollChild(frame.content)
    frame.slider = CreateFrame("Slider", nil, frame, "UIPanelScrollBarTemplate")
    frame.slider:SetPoint("TOPLEFT", frame.scroll, "TOPRIGHT", 14, -16); frame.slider:SetSize(16, VIEW_HEIGHT - 32)
    frame.slider:SetValueStep(ROW_HEIGHT); frame.slider:SetScript("OnValueChanged", function(_, value)
        if frame.rendering or not ns.Public(value) or type(value) ~= "number" or value ~= value then return end
        frame.offset = math.max(0, math.min(frame.maximum or 0, value)); ns.RenderGuideQuestList()
    end)
    frame.scroll:EnableMouseWheel(true)
    frame.scroll:SetScript("OnMouseWheel", function(_, delta)
        if not ns.Public(delta) or type(delta) ~= "number" then return end
        frame.offset = math.max(0, math.min(frame.maximum or 0, (frame.offset or 0) - delta * ROW_HEIGHT * 2))
        ns.RenderGuideQuestList()
    end)
    frame.empty = ns.UILabel(frame.scroll, nil, 12, ns.UIColors.muted)
    frame.empty:SetPoint("TOPLEFT", 20, -20); frame.empty:SetWordWrap(true); frame.empty:SetJustifyV("TOP"); frame.empty:Hide()
    frame.start = ns.UIButton(frame, "Start route", 136, function()
        if not frame:IsShown() or not frame.plan or not frame.startGuide then return end
        local guide = frame.startGuide
        frame:Hide(); ns.RequestStartRoute(guide)
    end, true)
    frame.start:SetPoint("BOTTOMRIGHT", -22, 18); frame.start:SetEnabled(false)
    frame.more = ns.UIDropdown(frame, {{"buy", "Quest supplies"}, {"catchup", "Catch up party"}}, 160, function(value)
        if not frame.guide then return end
        if value == "buy" then ns.ShowShoppingList(ns.QuestShoppingList(frame.guide.records), "Your quest buy list")
        elseif value == "catchup" then ns.ShowPartyCatchup(frame.guide, true) end
    end)
    frame.more:SetPoint("BOTTOMLEFT", 22, 18); frame.more.caption:SetText("More"); frame.more:Hide()
    frame.note = ns.UILabel(frame, nil, 10); frame.note:SetPoint("BOTTOMLEFT", 22, 19)
    frame.note:Hide()
    frame.rows, frame.generation, frame.offset = {}, 0, 0
    frame:SetScript("OnHide", function() frame.generation = frame.generation + 1 end)
    ns.EnableWindowResize(frame, {key = "guide-quests", minWidth = 560, minHeight = 380, maxWidth = 1200, maxHeight = 1000,
        layout = layout, onFinish = ns.RenderGuideQuestList})
    frame:Hide()
    return frame
end

function ns.RenderGuideQuestList()
    local frame = ns.guideQuestList
    if not frame or not frame:IsShown() or frame.rendering then return end
    frame.rendering = true
    for _, row in ipairs(frame.rows) do row:Hide() end
    local plan, quests, query = {}, {}, ns.NewQuestQuery()
    for _, stop in ipairs(frame.plan or {}) do
        if ns.ClassQuestEnabled(stop.id) then plan[#plan + 1], quests[stop.id] = stop, true end
    end
    frame.visiblePlan = plan
    frame.reasonRoute = {stops = plan}
    if frame.plan then
        local count = 0; for _ in pairs(quests) do count = count + 1 end
        frame.summary:SetText(frame.guide.mode == "travel" and "Travel guide"
            or (count .. " quests • " .. #plan .. " steps\n" .. ns.GuideXPText(frame.xpGuide or frame.guide, query)))
    end
    frame.empty:SetShown(frame.plan ~= nil and #plan == 0)
    frame.empty:SetText(frame.guide.mode == "travel"
        and ("Travel to " .. frame.guide.zone .. " using your known flight paths and transport connections.")
        or "No quests to show with your current settings.")
    local viewHeight = frame.viewHeight or VIEW_HEIGHT
    frame.maximum = math.max(0, #plan * ROW_HEIGHT - viewHeight)
    frame.offset = math.min(frame.offset or 0, frame.maximum)
    frame.content:SetHeight(math.max(viewHeight, #plan * ROW_HEIGHT))
    frame.scroll:SetVerticalScroll(frame.offset); frame.slider:SetMinMaxValues(0, frame.maximum); frame.slider:SetValue(frame.offset)
    frame.slider:SetShown(frame.maximum > 0)
    local first = math.floor(frame.offset / ROW_HEIGHT) + 1
    for index = first, math.min(#plan, first + math.ceil(viewHeight / ROW_HEIGHT)) do
        local stop, slot = plan[index], index - first + 1
        local row = frame.rows[slot]
        if not row then
            row = CreateFrame("Frame", nil, frame.content)
            row:SetSize(664, ROW_HEIGHT)
            ns.UIDivider(row, -ROW_HEIGHT + 1)
            row.number = ns.UILabel(row, nil, 11); row.number:SetPoint("TOPLEFT", 6, -9); row.number:SetWidth(34)
            row.title = ns.UILabel(row, "GameFontNormal", 12); row.title:SetPoint("TOPLEFT", 48, -7); row.title:SetSize(414, 16); row.title:SetWordWrap(false)
            row.detail = ns.UILabel(row, nil, 11, ns.UIColors.muted); row.detail:SetPoint("TOPLEFT", 48, -26); row.detail:SetSize(604, 14); row.detail:SetWordWrap(false)
            row.state = ns.UILabel(row, nil, 10, ns.UIColors.muted); row.state:SetPoint("TOPRIGHT", -6, -9)
            row.state:SetSize(178, 14); row.state:SetJustifyH("RIGHT"); row.state:SetWordWrap(false)
            row:EnableMouse(true)
            row:SetScript("OnEnter", function(self)
                if not GameTooltip or not self.stop then return end
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:AddLine(ns.GuideStepDescription(self.stop, nil, frame.guide,
                    frame.reasonRoute), 1, 1, 1, true)
                GameTooltip:Show()
            end)
            row:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
            frame.rows[slot] = row
        end
        local color, quest = colors[stop.kind] or colors.q, ns.CatalogueQuest(stop.id)
        row:ClearAllPoints(); row:SetPoint("TOPLEFT", 0, -(index - 1) * ROW_HEIGHT)
        row.number:SetText(stop.guideStep or index); row.number:SetTextColor(unpack(color))
        row.title:SetText((phases[stop.kind] or "Quest") .. " • " .. stop.title); row.title:SetTextColor(unpack(color))
        row.detail:SetText(ns.StopInstruction(stop) .. " • " .. ns.StopLocationText(stop))
        row.state:SetText((quest and quest.level and ("Lv " .. quest.level .. " • ") or "")
            .. (ns.IsGroupQuest(stop.id) and (quest.questType .. " • ") or "") .. status(stop, query))
        row.stop, row.step = stop, stop.guideStep or index; row:Show()
    end
    layout(frame); frame.rendering = nil
end

function ns.ShowGuideQuestList(guide)
    if not guide or not (guide.fullGuide or guide.mode == "travel") then return end
    local frame = create()
    frame.generation = frame.generation + 1
    local generation = frame.generation
    frame.plan, frame.visiblePlan, frame.xpGuide, frame.offset, frame.guide, frame.startGuide = nil, nil, nil, 0, guide, nil
    frame.start:SetEnabled(false); frame.more:Hide()
    frame.title:SetText(guide.title or (guide.zone .. " leveling guide"))
    frame:SetFrameLevel((ns.window and ns.window:GetFrameLevel() or 0) + 30)
    frame.summary:SetText("Loading quests…"); frame:Show(); ns.RenderGuideQuestList()
    if guide.mode == "travel" then
        frame.plan, frame.startGuide = {}, guide
        frame.start:SetEnabled(true); ns.RenderGuideQuestList(); return
    end
    local current = ns.routeSelection
    local existing = guide.fixedPlan or current and current.key == guide.key and current.fixedPlan
    local copy = {}; for key, value in pairs(guide) do copy[key] = value end
    local job = not existing and coroutine.create(function() return ns.GenerateFixedGuide(copy, true) end)
    local function advance()
        if frame.generation ~= generation or not frame:IsShown() then return end
        local okay, plan = true, existing
        if job then okay, plan = coroutine.resume(job) end
        if not okay then frame.summary:SetText("Couldn't load quests. Please try again."); return end
        if job and coroutine.status(job) ~= "dead" then C_Timer.After(0.01, advance); return end
        frame.plan = {}
        for _, stop in ipairs(plan) do
            if not ns.IsLevelingExcludedQuest(stop.id) then frame.plan[#frame.plan + 1] = stop end
        end
        frame.xpGuide = current and current.key == guide.key and current or copy
        frame.startGuide = frame.xpGuide
        frame.start:SetEnabled(true)
        local supplies = #ns.QuestShoppingList(guide.records) > 0
        local catchup = guide.mode == "zone" and not guide.catchup and ns.PartyFeaturesEnabled()
            and #(ns.partyNames or {}) > 0 and ns.ReadPublic(IsInRaid) ~= true
        frame.more:SetVisibleEntries(function(value) return value == "buy" and supplies or value == "catchup" and catchup end)
        frame.more:SetShown(supplies or catchup)
        ns.RenderGuideQuestList()
    end
    if existing then advance()
    elseif C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0.01, advance)
    else frame.summary:SetText("Quest list unavailable.") end
end
