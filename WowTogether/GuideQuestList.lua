local addonName, ns = ...

local ROW_HEIGHT, VIEW_HEIGHT = 44, 408
local phases = {a = "Pick up", q = "Objectives", t = "Turn in"}
local colors = {a = {1, 0.82, 0.3}, q = {0.92, 0.88, 0.76}, t = {0.55, 0.84, 0.58}}

local function status(stop, query)
    if ns.GuideQuestSkipped(stop.id) or #ns.FilterGuideStages({stop}) == 0 then return "Skipped" end
    if ns.Completed(stop.id, query) == true then return "Done" end
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
    frame.note = ns.UILabel(frame, nil, 10); frame.note:SetPoint("BOTTOMLEFT", 22, 19)
    frame.note:SetText("Read-only preview • Start route in Leveling guides when you are ready.")
    frame.rows, frame.generation, frame.offset = {}, 0, 0
    frame:SetScript("OnHide", function() frame.generation = frame.generation + 1 end)
    frame:Hide()
    return frame
end

function ns.RenderGuideQuestList()
    local frame = ns.guideQuestList
    if not frame or not frame:IsShown() or frame.rendering then return end
    frame.rendering = true
    for _, row in ipairs(frame.rows) do row:Hide() end
    local plan, query = frame.plan or {}, ns.NewQuestQuery()
    frame.maximum = math.max(0, #plan * ROW_HEIGHT - VIEW_HEIGHT)
    frame.offset = math.min(frame.offset or 0, frame.maximum)
    frame.content:SetHeight(math.max(VIEW_HEIGHT, #plan * ROW_HEIGHT))
    frame.scroll:SetVerticalScroll(frame.offset); frame.slider:SetMinMaxValues(0, frame.maximum); frame.slider:SetValue(frame.offset)
    frame.slider:SetShown(frame.maximum > 0)
    local first = math.floor(frame.offset / ROW_HEIGHT) + 1
    for index = first, math.min(#plan, first + math.ceil(VIEW_HEIGHT / ROW_HEIGHT)) do
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
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT"); GameTooltip:AddLine(self.title:GetText(), 1, 0.82, 0.3, true)
                GameTooltip:AddLine(self.detail:GetText(), 1, 1, 1, true); GameTooltip:Show()
            end)
            row:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
            frame.rows[slot] = row
        end
        local color, quest = colors[stop.kind] or colors.q, ns.CatalogueQuest(stop.id)
        row:ClearAllPoints(); row:SetPoint("TOPLEFT", 0, -(index - 1) * ROW_HEIGHT)
        row.number:SetText(index); row.number:SetTextColor(unpack(color))
        row.title:SetText((phases[stop.kind] or "Quest") .. " • " .. stop.title); row.title:SetTextColor(unpack(color))
        row.detail:SetText(ns.StopInstruction(stop) .. " • " .. (stop.unknownLocation and "Exact location not mapped" or ns.MapName(stop.mapID)))
        row.state:SetText((quest and quest.level and ("Lv " .. quest.level .. " • ") or "") .. status(stop, query))
        row.stop, row.step = stop, index; row:Show()
    end
    frame.rendering = nil
end

function ns.ShowGuideQuestList(guide)
    if not guide or not guide.fullGuide then return end
    local frame = create()
    frame.generation = frame.generation + 1
    local generation = frame.generation
    frame.plan, frame.offset, frame.guide = nil, 0, guide
    frame.title:SetText(guide.zone .. " • Quest order")
    frame.summary:SetText("Loading the complete guide order…"); frame:Show(); ns.RenderGuideQuestList()
    local current = ns.routeSelection
    local existing = guide.fixedPlan or current and current.key == guide.key and current.fixedPlan
    local copy = {}; for key, value in pairs(guide) do copy[key] = value end
    local job = not existing and coroutine.create(function() return ns.GenerateFixedGuide(copy, true) end)
    local function advance()
        if frame.generation ~= generation or not frame:IsShown() then return end
        local okay, plan = true, existing
        if job then okay, plan = coroutine.resume(job) end
        if not okay then frame.summary:SetText("Guide preview failed. Check Diagnostics or send a test report."); return end
        if job and coroutine.status(job) ~= "dead" then C_Timer.After(0.01, advance); return end
        frame.plan = {}
        local quests = {}
        for _, stop in ipairs(plan) do
            if not ns.IsLevelingExcludedQuest(stop.id) then frame.plan[#frame.plan + 1] = stop; quests[stop.id] = true end
        end
        local count = 0; for _ in pairs(quests) do count = count + 1 end
        frame.summary:SetText(count .. " quests • " .. #frame.plan .. " steps • Pickup → objectives → turn-in in guide order.\n"
            .. ns.GuideXPText(current and current.key == guide.key and current or copy))
        ns.GuideXPHelp(frame)
        ns.RenderGuideQuestList()
    end
    if existing then advance()
    elseif C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0.01, advance)
    else frame.summary:SetText("Guide preview scheduler unavailable on this build.") end
end
