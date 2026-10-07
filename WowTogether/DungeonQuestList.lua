local addonName, ns = ...

local function layout(frame)
    local width = frame:GetWidth()
    frame.title:SetWidth(width - 72); frame.subtitle:SetWidth(width - 44)
    frame.summary:SetWidth(width - 204); frame.hint:SetWidth(width - 224); frame.hint:SetHeight(36); frame.hint:SetWordWrap(true)
    frame.content:SetWidth(width - 60)
    for _, row in ipairs(frame.rows) do
        row:SetWidth(width - 60); row.title:SetWidth(width - 220)
        row.pickup:SetWidth(width - 125); row.state:SetWidth(width - 255)
    end
end
local function createRow(parent)
    local row = CreateFrame("Button", nil, parent, "BackdropTemplate")
    row:SetSize(600, 94); ns.UIPanel(row)
    row.icon = row:CreateTexture(nil, "ARTWORK"); row.icon:SetSize(22, 22); row.icon:SetPoint("TOPLEFT", 12, -12)
    row.title = ns.UILabel(row, "GameFontNormal", 14); row.title:SetPoint("TOPLEFT", 42, -12); row.title:SetWidth(380)
    row.title:SetWordWrap(false)
    row.level = ns.UILabel(row, nil, 11, ns.UIColors.muted); row.level:SetPoint("TOPRIGHT", -12, -13)
    row.level:SetJustifyH("RIGHT")
    row.pickup = ns.UILabel(row, nil, 12); row.pickup:SetPoint("TOPLEFT", 42, -34); row.pickup:SetWidth(535)
    row.pickup:SetWordWrap(false)
    row.state = ns.UILabel(row, nil, 11, ns.UIColors.muted); row.state:SetPoint("BOTTOMLEFT", 42, 14); row.state:SetWidth(405)
    row.state:SetWordWrap(false)
    row.route = ns.UIButton(row, "Route to pickup", 124, function() end)
    row.route:SetPoint("BOTTOMRIGHT", -12, 8)
    return row
end

function ns.RefreshDungeonQuestList()
    local frame = ns.dungeonWindow
    if not frame or not frame.group then return end
    local group, rows, counts = frame.group, {}, {pending = 0, active = 0, completed = 0}
    for _, id in ipairs(group.ids) do
        if ns.DungeonQuestRelevant(id) == true then
            local quest = ns.CatalogueQuest(id)
            local state = ns.Completed(id) == true and not ns.active[id] and "completed" or ns.active[id] and "active" or "pending"
            counts[state] = counts[state] + 1
            if frame.filterKey == "all" or frame.filterKey == state then rows[#rows + 1] = {id = id, quest = quest, state = state} end
        end
    end
    local ranks = {pending = 1, active = 2, completed = 3}
    table.sort(rows, function(a, b)
        if ranks[a.state] ~= ranks[b.state] then return ranks[a.state] < ranks[b.state] end
        if (a.quest.minLevel or 255) ~= (b.quest.minLevel or 255) then return (a.quest.minLevel or 255) < (b.quest.minLevel or 255) end
        return a.id < b.id
    end)
    frame.title:SetText(group.name)
    frame.subtitle:SetText(ns.DungeonOverviewSummary(group))
    frame.summary:SetText(counts.pending .. " to collect  •  " .. counts.active .. " in your log  •  " .. counts.completed .. " completed")
    frame.visibleQuests = rows
    frame.empty:SetShown(#rows == 0); frame.empty:SetText("No quests in this view.")
    frame.content:SetHeight(math.max(100, #rows * 102))
    for index, item in ipairs(rows) do
        local row = frame.rows[index]
        if not row then row = createRow(frame.content); frame.rows[index] = row end
        local id, q, state = item.id, item.quest, item.state
        row.questID = id
        row:SetPoint("TOPLEFT", 0, -(index - 1) * 102)
        row.title:SetText(q.title); row.level:SetText("Lv " .. (q.level or "?"))
        local point = ns.NPCPickupPoint(id) or q.starts and q.starts[1]
        local pickup = point and ((ns.SafeTitle(point.name) or "Quest giver") .. "  •  " .. ns.MapName(point.mapID)) or "Pickup location unavailable"
        row.pickup:SetText(pickup)
        local available, reason = ns.CataloguePickupCheck(id, ns.profile, ns.self)
        local status = state == "completed" and "Completed" or state == "active" and "Already collected"
            or ns.GuideQuestSkipped(id) and "Skipped" or available == true and "Ready to collect" or reason or "Check with the quest giver"
        local class = ns.ClassQuestLabel(id)
        if class then status = class .. " • " .. status end
        row.state:SetText(status)
        row.state:SetTextColor(unpack(state ~= "pending" and ns.UIColors.success or ns.UIColors.muted))
        row.icon:SetTexture(state == "pending" and "Interface\\GossipFrame\\AvailableQuestIcon" or "Interface\\RaidFrame\\ReadyCheck-Ready")
        row.route:SetEnabled(state == "pending" and not ns.GuideQuestSkipped(id)
            and ((q.minLevel or q.level or 255) <= (ns.profile.level or 0) or available == true))
        row.route:SetScript("OnClick", function() ns.ShowDungeonQuests(group, true, id) end)
        row:SetScript("OnClick", function()
            if state == "pending" and not ns.GuideQuestSkipped(id) then ns.ShowDungeonQuests(group, true, id) end
        end)
        ns.UIHelp(row.route, status)
        row:Show()
    end
    for index = #rows + 1, #frame.rows do frame.rows[index]:Hide() end
    frame.collect:SetEnabled(counts.pending + counts.active > 0)
    frame.collect:SetScript("OnClick", function() ns.ShowDungeonQuests(group, true) end)
    layout(frame)
end

function ns.ShowDungeonQuestList(group)
    ns.ReadProfile()
    ns.ReadQuests()
    if not ns.dungeonWindow then
        local frame = CreateFrame("Frame", "WowTogetherDungeonQuests", UIParent, "BackdropTemplate")
        ns.dungeonWindow = frame
        frame:SetSize(660, 560); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG"); frame:SetClampedToScreen(true)
        frame:SetToplevel(true); frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
        frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
        ns.UIPanel(frame, ns.UIColors.background); ns.UIClose(frame)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 20); frame.title:SetPoint("TOPLEFT", 22, -20)
        frame.subtitle = ns.UILabel(frame, nil, 11, ns.UIColors.muted); frame.subtitle:SetPoint("TOPLEFT", 22, -48)
        frame.summary = ns.UILabel(frame, nil, 12); frame.summary:SetPoint("TOPLEFT", 22, -79)
        frame.filterKey, frame.rows = "all", {}
        frame.filter = ns.UIDropdown(frame, {{"all", "All quests"}, {"pending", "To collect"}, {"active", "In your log"}, {"completed", "Completed"}}, 144,
            function(key) frame.filterKey = key; frame.filter:SetChoice(key); frame.scroll:SetVerticalScroll(0); ns.RefreshDungeonQuestList() end)
        frame.filter:SetPoint("TOPRIGHT", -22, -72); frame.filter:SetChoice("all")
        ns.UIDivider(frame, -108)
        frame.scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
        frame.scroll:SetPoint("TOPLEFT", 22, -120); frame.scroll:SetPoint("BOTTOMRIGHT", -38, 68)
        frame.content = CreateFrame("Frame", nil, frame.scroll); frame.content:SetSize(600, 100); frame.scroll:SetScrollChild(frame.content)
        frame.empty = ns.UILabel(frame.content, nil, 13, ns.UIColors.muted); frame.empty:SetPoint("TOPLEFT", 14, -24)
        frame.collect = ns.UIButton(frame, "Start quest route", 156, function() end, true); frame.collect:SetPoint("BOTTOMLEFT", 22, 20)
        frame.hint = ns.UILabel(frame, nil, 11, ns.UIColors.muted); frame.hint:SetPoint("BOTTOMLEFT", 196, 28)
        frame.hint:SetText("Collect quests and prerequisites, then head to the entrance.")
        ns.EnableWindowResize(frame, {key = "dungeon-quests", minWidth = 540, minHeight = 380, maxWidth = 1100, maxHeight = 900, layout = layout})
        if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherDungeonQuests") end
    end
    local frame = ns.dungeonWindow
    frame.group = group; frame.scroll:SetVerticalScroll(0)
    ns.RefreshDungeonQuestList(); frame:Show(); frame:Raise()
end
