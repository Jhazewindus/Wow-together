local addonName, ns = ...

local ROW_HEIGHT, VIEW_HEIGHT = 44, 396

local function layout(frame)
    local width, height = frame:GetWidth() - 76, math.max(100, frame:GetHeight() - 164)
    frame.viewHeight = height
    frame.title:SetWidth(frame:GetWidth() - 210); frame.summary:SetWidth(frame:GetWidth() - 50)
    frame.scroll:SetSize(width, height); frame.content:SetWidth(width); frame.slider:SetHeight(height - 32)
    frame.empty:SetSize(width - 40, math.max(80, height - 40))
    for _, row in ipairs(frame.rows) do row:SetWidth(width); row.title:SetWidth(width - 210) end
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
    frame.efficiency = ns.UIButton(frame, "Complete zone", 126, function()
        if not frame.guide or not ns.SetGuideEfficiencyMode then return end
        local guide = frame.guide
        ns.SetGuideEfficiencyMode(guide, ns.GuideEfficiencyMode(guide) == "efficient" and "complete" or "efficient")
        ns.ShowGuideQuestList(guide)
    end)
    frame.efficiency:SetPoint("TOPRIGHT", -54, -16)
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
        if not frame:IsShown() or not frame.startGuide then return end
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
    local policyGuide = ns.routeSelection and ns.routeSelection.key == frame.guide.key and ns.routeSelection or frame.guide
    query.guide = policyGuide
    if ns.PrepareGuidePolicy then ns.PrepareGuidePolicy(policyGuide, query) end
    local efficientZone = frame.guide.mode == "zone" and ns.GuideEfficiencyMode(frame.guide) == "efficient"
        and not ns.GuideDifficultyOverride(policyGuide)
    for _, stop in ipairs(frame.plan or {}) do
        if ns.ClassQuestEnabled(stop.id) and (not efficientZone or ns.LevelingValue(stop.id, query) ~= false) then
            plan[#plan + 1], quests[stop.id] = stop, true
        end
    end
    frame.visiblePlan = plan
    frame.reasonRoute = {stops = plan}
    local also = {}
    if frame.guide.mode == "zone" and ns.GuideEfficiencyMode(frame.guide) == "efficient"
        and not ns.GuideDifficultyOverride(policyGuide) then
        for _, record in ipairs(frame.guide.records or {}) do
            if not quests[record.id] and ns.ClassQuestEnabled(record.id) then
                local _, valueReason = ns.LevelingValue(record.id, query)
                local chain = ns.ChainValue and ns.ChainValue(record.id, query)
                local zoneExit = chain and ns.GuideZoneFinishing and ns.GuideZoneFinishing(frame.guide, nil, nil, query) and not chain.committed
                local lowValueReason = type(valueReason) == "string" and string.find(valueReason, "^in%-log%-low%-value:") ~= nil
                local inLogLowValue = zoneExit and ns.active[record.id] ~= nil and (lowValueReason or chain.inLogLowValue == true)
                if chain and (not chain.included or zoneExit) then
                    local quest = ns.CatalogueQuest(record.id)
                    also[#also + 1] = {id = record.id, kind = "a", mapID = quest and quest.mapID or frame.guide.mapID,
                        x = quest and quest.starts and quest.starts[1] and quest.starts[1].x,
                        y = quest and quest.starts and quest.starts[1] and quest.starts[1].y,
                        title = ns.QuestTitle(record.id),
                        reasonCode = inLogLowValue and "in-log-low-value" or zoneExit and "zone-finishing" or "chain-value",
                        inLogLowValue = inLogLowValue and #plan == 0 or false,
                        label = inLogLowValue and ((ns.QuestTitle(record.id) or record.title) .. " is worth ~"
                            .. tostring(math.floor((chain.xp or 0) + 0.5)) .. " XP for a ~"
                            .. tostring(math.floor((chain.minutes or 0) + 0.5)) .. " min trip.")
                            or zoneExit and ("Finish current work first. " .. chain.reason) or chain.reason,
                        optional = true}
                end
            end
        end
    end
    table.sort(also, function(a, b) return a.id < b.id end)
    local displayPlan = {}
    for _, stop in ipairs(plan) do displayPlan[#displayPlan + 1] = stop end
    if #also > 0 then
        displayPlan[#displayPlan + 1] = {sectionHeader = true, title = "Also in this zone (" .. #also .. ")"}
        if frame.showAlsoInZone then for _, stop in ipairs(also) do displayPlan[#displayPlan + 1] = stop end end
    end
    frame.displayPlan = displayPlan
    if frame.plan then
        local count = 0; for _ in pairs(quests) do count = count + 1 end
        local mode = ns.GuideEfficiencyMode and ns.GuideEfficiencyMode(frame.guide) or "efficient"
        frame.efficiency:SetShown(frame.guide.mode == "zone" or frame.guide.mode == "bundle")
        frame.efficiency.caption:SetText(mode == "complete" and "Efficient" or "Complete zone")
        frame.summary:SetText(frame.guide.mode == "travel" and "Travel guide"
            or (count .. " quests • " .. #plan .. " steps • " .. (mode == "complete" and "Complete the zone" or "Efficient")
                .. "\n" .. ns.GuideXPText(frame.xpGuide or frame.guide, query)))
    end
    frame.empty:SetShown(frame.plan ~= nil and #plan == 0)
    frame.empty:SetText(frame.guide.mode == "travel"
        and ("Travel to " .. frame.guide.zone .. " using your known flight paths and transport connections.")
        or "No quests to show with your current settings.")
    local viewHeight = frame.viewHeight or VIEW_HEIGHT
    frame.maximum = math.max(0, #displayPlan * ROW_HEIGHT - viewHeight)
    frame.offset = math.min(frame.offset or 0, frame.maximum)
    frame.content:SetHeight(math.max(viewHeight, #displayPlan * ROW_HEIGHT))
    frame.scroll:SetVerticalScroll(frame.offset); frame.slider:SetMinMaxValues(0, frame.maximum); frame.slider:SetValue(frame.offset)
    frame.slider:SetShown(frame.maximum > 0)
    local first = math.floor(frame.offset / ROW_HEIGHT) + 1
    for index = first, math.min(#displayPlan, first + math.ceil(viewHeight / ROW_HEIGHT)) do
        local stop, slot = displayPlan[index], index - first + 1
        local row = frame.rows[slot]
        if not row then
            row = CreateFrame("Frame", nil, frame.content)
            row:SetSize(664, ROW_HEIGHT)
            ns.UIDivider(row, -ROW_HEIGHT + 1)
            row.number = ns.UILabel(row, nil, 10, ns.UIColors.muted); row.number:Hide()
            row.icon = row:CreateTexture(nil, "ARTWORK"); row.icon:SetSize(18, 18); row.icon:SetPoint("TOPLEFT", 6, -6)
            row.title = ns.UILabel(row, "GameFontNormal", 12); row.title:SetPoint("TOPLEFT", 30, -7); row.title:SetSize(470, 16); row.title:SetWordWrap(false)
            row.state = ns.UILabel(row, nil, 10, ns.UIColors.muted); row.state:SetPoint("TOPRIGHT", -6, -9)
            row.state:SetSize(150, 14); row.state:SetJustifyH("RIGHT"); row.state:SetWordWrap(false)
            row.abandon = ns.UIButton(row, "Abandon", 62, function()
                if row.stop and row.stop.inLogLowValue then ns.AbandonLowValueQuest(row.stop.id) end
            end)
            row.abandon:SetHeight(17); row.abandon:SetPoint("BOTTOMRIGHT", -72, 3); row.abandon:Hide()
            row.keep = ns.UIButton(row, "Keep", 58, function()
                if row.stop and row.stop.inLogLowValue then ns.KeepLowValueQuest(row.stop.id) end
            end)
            row.keep:SetHeight(17); row.keep:SetPoint("BOTTOMRIGHT", -6, 3); row.keep:Hide()
            row:EnableMouse(true)
            row:SetScript("OnEnter", function(self)
                if not GameTooltip or not self.stop then return end
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                if self.sectionHeader then
                    GameTooltip:AddLine(self.stop.title, 1, 0.82, 0.3, true)
                    GameTooltip:AddLine("Click to show or hide lower-value quests in this zone.", 1, 1, 1, true)
                    GameTooltip:Show(); return
                end
                local presentation = ns.GuideStepPresentation(self.stop, nil, frame.guide, frame.reasonRoute)
                GameTooltip:AddLine(presentation.title, 1, 0.82, 0.3, true)
                if self.stop.reasonCode == "chain-value" or self.stop.reasonCode == "zone-finishing"
                    or self.stop.reasonCode == "in-log-low-value" then
                    GameTooltip:AddLine(self.stop.label, 1, 1, 1, true)
                end
                for _, line in ipairs(ns.GuidePresentationTooltipLines(presentation, true)) do GameTooltip:AddLine(line, 1, 1, 1, true) end
                GameTooltip:Show()
            end)
            row:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
            row:SetScript("OnMouseUp", function(self)
                if self.sectionHeader then frame.showAlsoInZone = not frame.showAlsoInZone; ns.RenderGuideQuestList() end
            end)
            frame.rows[slot] = row
        end
        row.sectionHeader = stop.sectionHeader == true
        local quest = ns.CatalogueQuest(stop.id)
        if row.sectionHeader then
            row:ClearAllPoints(); row:SetPoint("TOPLEFT", 0, -(index - 1) * ROW_HEIGHT)
            row.abandon:Hide(); row.keep:Hide()
            row.icon:Hide(); row.number:Hide(); row.title:SetText(stop.title); row.title:SetTextColor(unpack(ns.UIColors.gold))
            row.state:SetText(frame.showAlsoInZone and "Hide" or "Show")
            row.state:SetTextColor(unpack(ns.UIColors.muted)); row.stop, row.step = stop, index; row:Show()
        else
        local presentation = ns.GuideStepPresentation(stop, nil, frame.guide, frame.reasonRoute)
        local active = ns.navigation and ns.navigation.state and ns.navigation.state.stop
        local current = active and active.id == stop.id and active.kind == stop.kind
            or ns.selectedRoute and ns.selectedRoute.stops and ns.selectedRoute.stops[1]
                and ns.selectedRoute.stops[1].id == stop.id and ns.selectedRoute.stops[1].kind == stop.kind
        row:ClearAllPoints(); row:SetPoint("TOPLEFT", 0, -(index - 1) * ROW_HEIGHT)
        row.icon:Show(); row.number:Show()
        row.icon:SetTexture(presentation.icon); row.icon:SetAlpha(presentation.status == "Optional, on the way" and 0.6 or 1)
        row.number:SetText(stop.guideStep or index)
        row.title:SetText(stop.title); row.title:SetTextColor(unpack(current and ns.UIColors.text or ns.UIColors.muted))
        row.title:SetWidth(stop.inLogLowValue and 310 or 470)
        local shortStatus = presentation.status
        local level = quest and (quest.minLevel or quest.level)
        if shortStatus == "Done" then shortStatus = "✓"
        elseif shortStatus == "Later" or string.match(shortStatus or "", "^Later") then shortStatus = "Later" .. (level and (" " .. level) or "")
        elseif shortStatus == "Optional, on the way" then shortStatus = "" end
        row.state:SetText(shortStatus)
        local stateColor = presentation.statusColor == "green" and ns.UIColors.success
            or presentation.statusColor == "gold" and ns.UIColors.gold
            or current and ns.UIColors.text or ns.UIColors.muted
        row.state:SetTextColor(unpack(stateColor))
        row.stop, row.step = stop, stop.guideStep or index; row:Show()
        row.abandon:SetShown(stop.inLogLowValue == true)
        row.keep:SetShown(stop.inLogLowValue == true)
        end
    end
    layout(frame); frame.rendering = nil
end

function ns.ShowGuideQuestList(guide)
    if not guide or not (guide.fullGuide or guide.mode == "travel") then return end
    local frame = create()
    frame.generation = frame.generation + 1
    local generation = frame.generation
    local current = ns.routeSelection
    local startGuide = current and current.key == guide.key and current or guide
    frame.plan, frame.visiblePlan, frame.xpGuide, frame.offset, frame.guide, frame.startGuide = nil, nil, nil, 0, guide, startGuide
    frame.showAlsoInZone = false
    frame.start:SetEnabled(true); frame.more:Hide()
    frame.title:SetText(guide.title or (guide.zone .. " leveling guide"))
    frame.efficiency:SetShown(guide.mode == "zone" or guide.mode == "bundle")
    frame.efficiency.caption:SetText(ns.GuideEfficiencyMode(guide) == "complete" and "Efficient" or "Complete zone")
    frame:SetFrameLevel((ns.window and ns.window:GetFrameLevel() or 0) + 30)
    frame.summary:SetText("Preparing the ordered quest list… You can start the route now.")
    frame:Show(); ns.RenderGuideQuestList()
    if guide.mode == "travel" then
        frame.plan, frame.startGuide = {}, guide
        frame.start:SetEnabled(true); ns.RenderGuideQuestList(); return
    end
    local existing = guide.fixedPlan or current and current.key == guide.key and current.fixedPlan
    local copy = {}; for key, value in pairs(guide) do copy[key] = value end
    local job = not existing and coroutine.create(function() return ns.GenerateFixedGuide(copy, true) end)
    local function advance()
        if frame.generation ~= generation or not frame:IsShown() then return end
        local okay, plan = true, existing
        if job then okay, plan = coroutine.resume(job) end
        if not okay then frame.summary:SetText("Couldn't load the quest list. Start route is still available."); return end
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
