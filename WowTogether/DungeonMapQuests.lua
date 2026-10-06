local addonName, ns = ...

local phases = {a = "Pick up", q = "Objectives", t = "Turn in"}
local function close(left, right)
    return (left.x - right.x) ^ 2 + (left.y - right.y) ^ 2 < .03 ^ 2
end

function ns.DungeonMapQuestGroups(map)
    local groups, query = {}, ns.NewQuestQuery()
    for _, point in ipairs(map and map.quests or {}) do
        if ns.DungeonMapQuestVisible(point, query) then
            local group
            for _, candidate in ipairs(groups) do
                if candidate.entityID == point.entityID and candidate.entityType == point.entityType and close(candidate, point) then group = candidate; break end
            end
            if not group then
                group = {x = point.x, y = point.y, kind = point.kind, name = point.name, entityID = point.entityID,
                    entityType = point.entityType, quests = {}, seen = {}}
                groups[#groups + 1] = group
            end
            local key = point.id .. ":" .. point.kind .. ":" .. (point.instruction or "")
            if not group.seen[key] then group.quests[#group.quests + 1] = point; group.seen[key] = true end
            if point.kind == "a" then group.kind = "a" end
            if point.kind == "t" and ns.readyToTurnIn and ns.readyToTurnIn[point.id] then group.kind = "t" end
        end
    end
    return groups
end

function ns.DungeonMapQuestTooltip(group)
    local lines = {group.name}
    for index, point in ipairs(group.quests) do
        if index > 5 then lines[#lines + 1] = "View all quests"; break end
        lines[#lines + 1] = (phases[point.kind] or "Quest") .. " • " .. ns.QuestTitle(point.id)
    end
    return table.concat(lines, "\n")
end

local function render()
    local frame = ns.dungeonMapQuestWindow
    if not frame or not frame:IsShown() or not frame.group then return end
    local points = {}
    for _, point in ipairs(frame.group.quests) do if ns.DungeonMapQuestVisible(point) then points[#points + 1] = point end end
    frame.page = math.max(1, math.min(math.max(1, math.ceil(#points / 4)), frame.page))
    frame.title:SetText(frame.group.name)
    frame.summary:SetText(ns.dungeonData.dungeons[frame.key].name)
    for index, row in ipairs(frame.rows) do
        local point = points[(frame.page - 1) * 4 + index]
        row:SetShown(point ~= nil)
        if point then
            row.title:SetText(ns.QuestTitle(point.id))
            row.action:SetText(point.instruction or phases[point.kind])
            local state = ns.active and ns.active[point.id] and "In your log" or ""
            if point.kind == "t" and ns.readyToTurnIn and ns.readyToTurnIn[point.id] then state = "Ready to turn in" end
            row.state:SetText(state)
        end
    end
    local pages = math.max(1, math.ceil(#points / 4))
    frame:SetHeight(104 + math.max(1, math.min(4, #points)) * 64 + (pages > 1 and 36 or 0))
    frame.previous:SetEnabled(frame.page > 1); frame.next:SetEnabled(frame.page < pages)
    frame.previous:SetShown(pages > 1); frame.next:SetShown(pages > 1); frame.pageText:SetShown(pages > 1)
    frame.pageText:SetText(frame.page .. " / " .. pages)
    frame.empty:SetShown(#points == 0)
end

function ns.RefreshDungeonMapQuests()
    render()
end

function ns.ShowDungeonMapQuests(group, key)
    if not group or not ns.dungeonData.dungeons[key] then return end
    if not ns.dungeonMapQuestWindow then
        local frame = CreateFrame("Frame", "WowTogetherDungeonMapQuests", UIParent, "BackdropTemplate")
        ns.dungeonMapQuestWindow = frame
        frame:SetSize(380, 388); frame:SetPoint("CENTER", 200, 0)
        frame:SetClampedToScreen(true); frame:SetFrameStrata("DIALOG"); ns.UIPanel(frame, ns.UIColors.background)
        frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
        frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
        ns.UIClose(frame)
        frame.title = ns.UILabel(frame, "GameFontNormal", 16); frame.title:SetPoint("TOPLEFT", 18, -18); frame.title:SetSize(322, 28)
        frame.summary = ns.UILabel(frame, nil, 10, ns.UIColors.muted); frame.summary:SetPoint("TOPLEFT", 18, -48); frame.summary:SetSize(340, 20)
        ns.UIDivider(frame, -77)
        frame.rows = {}
        for index = 1, 4 do
            local row = CreateFrame("Frame", nil, frame); row:SetPoint("TOPLEFT", 18, -88 - (index - 1) * 64); row:SetSize(344, 60)
            row.title = ns.UILabel(row, "GameFontNormal", 12); row.title:SetPoint("TOPLEFT"); row.title:SetSize(344, 18); row.title:SetWordWrap(false)
            row.action = ns.UILabel(row, nil, 11); row.action:SetPoint("TOPLEFT", 0, -20); row.action:SetSize(344, 26)
            row.state = ns.UILabel(row, nil, 9, ns.UIColors.muted); row.state:SetPoint("TOPLEFT", 0, -47); row.state:SetSize(344, 12)
            frame.rows[index] = row
        end
        frame.previous = ns.UIButton(frame, "‹", 28, function() frame.page = frame.page - 1; render() end); frame.previous:SetPoint("BOTTOMLEFT", 18, 14)
        frame.next = ns.UIButton(frame, "›", 28, function() frame.page = frame.page + 1; render() end); frame.next:SetPoint("BOTTOMRIGHT", -18, 14)
        frame.pageText = ns.UILabel(frame, nil, 10, ns.UIColors.muted); frame.pageText:SetPoint("BOTTOM", 0, 22)
        frame.empty = ns.UILabel(frame, nil, 12, ns.UIColors.muted); frame.empty:SetPoint("TOPLEFT", 18, -92); frame.empty:SetText("No unfinished quests here.")
        if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherDungeonMapQuests") end
    end
    local frame = ns.dungeonMapQuestWindow
    frame.group, frame.key, frame.page = group, key, 1; frame:Show(); render()
end
