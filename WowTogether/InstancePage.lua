local addonName, ns = ...

-- The page an instance opens onto.
--
-- It answers three questions, in this order:
--   GETTING IN        what the door needs (an attunement or a key), which
--                     step of its chain the character is on, every step
--   ALSO DONE HERE    steps of another instance's chain that happen inside
--                     this one, so they are done in the same run
--   QUESTS FOR A RUN  the quests to bring, each with what still has to be
--                     done first when it sits at the end of a chain
--
-- It replaces the map, boss and loot viewer as what a card opens: other
-- addons do loot tables better, and none of them knows which chain step the
-- character is on. Nothing here reads the dungeon journal data.

local WIDTH, HEIGHT = 640, 600
local STEP_HEIGHT, QUEST_HEIGHT, HEAD_HEIGHT, REQUIRE_HEIGHT = 26, 48, 30, 62

local function colors() return ns.UIColors end

local function questState(id)
    if ns.active and ns.active[id] ~= nil then
        local ready = ns.readyToTurnIn and ns.readyToTurnIn[id] == true
        return ready and "ready" or "active"
    end
    if ns.CatalogueCompletion and ns.CatalogueCompletion(ns.self, id) == true then return "done" end
    return "open"
end

local function placeOf(id)
    local quest = ns.CatalogueQuest(id)
    local point = ns.NPCPickupPoint and ns.NPCPickupPoint(id) or quest and quest.starts and quest.starts[1]
    if not point then return nil end
    local giver = ns.SafeTitle(point.name)
    local zone = point.mapID and ns.MapName and ns.MapName(point.mapID) or nil
    if giver and zone then return giver .. ", " .. zone end
    return giver or zone
end

-- What still has to be done before a quest can be picked up: its unfinished
-- prerequisites, nearest first, following the chain back.
function ns.QuestLeadIn(id, limit)
    local list, seen, current = {}, {[id] = true}, id
    for _ = 1, limit or 12 do
        local previous
        for _, candidate in ipairs(ns.CataloguePrerequisiteIDs(current)) do
            if not seen[candidate] and ns.CatalogueQuest(candidate)
                and ns.CatalogueIdentityAllowed(candidate, ns.profile) ~= false then previous = candidate; break end
        end
        if not previous then break end
        seen[previous] = true
        if questState(previous) == "done" then break end      -- Everything before a finished step is finished too.
        table.insert(list, 1, previous)
        current = previous
    end
    return list
end

-- The page as a flat list of rows.
local function build(instance)
    local items, key = {}, instance.key
    local access = ns.InstanceAccess(key)
    local needs = {}
    for _, status in ipairs(access) do if status.state ~= "open" then needs[#needs + 1] = status end end
    if #access > 0 then
        items[#items + 1] = {kind = "head", text = "GETTING IN"}
        for _, status in ipairs(access) do
            items[#items + 1] = {kind = "require", status = status}
            for index, id in ipairs(status.chain or {}) do
                local state = questState(id)
                if status.state == "have" then state = "done" end
                items[#items + 1] = {kind = "step", id = id, index = index, state = state,
                    current = id == status.nextID and status.state ~= "have"}
            end
        end
    end
    local also = ns.InstanceAlsoHere(key)
    local shown = false
    for _, entry in ipairs(also) do
        if entry.owner ~= key then
            if not shown then items[#items + 1] = {kind = "head", text = "ALSO DONE IN HERE"}; shown = true end
            for _, id in ipairs(entry.steps) do
                items[#items + 1] = {kind = "step", id = id, state = questState(id), note = entry.title}
            end
        end
    end
    -- A quest already listed above as a step is not listed again below.
    local listed = {}
    for _, item in ipairs(items) do if item.kind == "step" then listed[item.id] = true end end
    local quests = {}
    for _, id in ipairs(instance.ids or {}) do
        if not listed[id] and ns.DungeonQuestRelevant(id) == true then
            quests[#quests + 1] = {kind = "quest", id = id, state = questState(id), lead = ns.QuestLeadIn(id)}
        end
    end
    local rank = {ready = 1, active = 2, open = 3, done = 4}
    table.sort(quests, function(a, b)
        if rank[a.state] ~= rank[b.state] then return rank[a.state] < rank[b.state] end
        if #a.lead ~= #b.lead then return #a.lead < #b.lead end      -- Ones you can pick up now before ones with a chain ahead.
        return a.id < b.id
    end)
    if #quests > 0 then
        items[#items + 1] = {kind = "head", text = "QUESTS FOR A RUN"}
        for _, quest in ipairs(quests) do items[#items + 1] = quest end
    end
    local counts = {open = 0, active = 0, ready = 0, done = 0}
    for _, quest in ipairs(quests) do counts[quest.state] = counts[quest.state] + 1 end
    return items, counts, needs
end

local STATE_TEXT = {done = "Done", active = "In your log", ready = "Ready to hand in", open = ""}
local STATE_ICON = {done = "Interface\\RaidFrame\\ReadyCheck-Ready", ready = "Interface\\GossipFrame\\ActiveQuestIcon",
    active = "Interface\\GossipFrame\\ActiveQuestIcon", open = "Interface\\GossipFrame\\AvailableQuestIcon"}

local function makeRow(parent)
    local row = CreateFrame("Button", nil, parent, "BackdropTemplate")
    row.icon = row:CreateTexture(nil, "ARTWORK"); row.icon:SetSize(16, 16)
    row.title = ns.UILabel(row, nil, 12); row.title:SetWordWrap(false)
    row.right = ns.UILabel(row, nil, 11, colors().muted); row.right:SetJustifyH("RIGHT"); row.right:SetWordWrap(false)
    row.line = ns.UILabel(row, nil, 11, colors().muted); row.line:SetWordWrap(false)
    row.second = ns.UILabel(row, nil, 11, colors().muted); row.second:SetWordWrap(false)
    row.go = ns.UIButton(row, "Show", 78, function() end); row.go:SetHeight(22)
    return row
end

local function showQuest(id)
    if type(ns.ShowQuestDetails) == "function" then ns.ShowQuestDetails(id) end
end

local function draw(frame)
    local instance = frame.instance
    if not instance then return end
    local items, counts, needs = build(instance)
    local width = (frame.content:GetWidth() or 580)
    frame.title:SetText(instance.name)
    frame.subtitle:SetText(instance.subtitle or "")
    local pending = {}
    for _, status in ipairs(needs) do
        if status.state ~= "have" then pending[#pending + 1] = status.title end
    end
    frame.summary:SetText((#pending > 0 and ("Still needed: " .. table.concat(pending, ", ") .. "  •  ") or (#needs > 0 and "You can get in  •  " or ""))
        .. (counts.open + counts.active + counts.ready + counts.done > 0
            and (counts.open .. " to collect  •  " .. (counts.active + counts.ready) .. " in your log  •  " .. counts.done .. " done") or "No quests listed"))
    local y, gold, text, muted = 0, colors().gold, colors().text, colors().muted
    -- Rows are kept per kind: a boxed row is never reused as a plain one.
    local used = {}
    for _, pool in pairs(frame.pools) do for _, row in ipairs(pool) do row:Hide() end end
    for index, item in ipairs(items) do
        local kind = (item.kind == "require" or item.kind == "quest") and "boxed" or "plain"
        local pool = frame.pools[kind]
        used[kind] = (used[kind] or 0) + 1
        local row = pool[used[kind]]
        if not row then
            row = makeRow(frame.content); pool[used[kind]] = row
            if kind == "boxed" then ns.UIPanel(row) end
        end
        frame.rows[index] = row
        row:ClearAllPoints(); row:SetPoint("TOPLEFT", 0, -y); row:SetWidth(width)
        row.icon:Hide(); row.right:SetText(""); row.line:SetText(""); row.second:SetText(""); row.go:Hide()
        row.title:ClearAllPoints(); row.right:ClearAllPoints(); row.line:ClearAllPoints(); row.second:ClearAllPoints(); row.icon:ClearAllPoints(); row.go:ClearAllPoints()
        row:SetScript("OnClick", nil)
        if item.kind == "head" then
            row:SetHeight(HEAD_HEIGHT)
            row.title:SetPoint("BOTTOMLEFT", 2, 6); row.title:SetWidth(width - 4)
            row.title:SetText(item.text); row.title:SetTextColor(unpack(gold))
            y = y + HEAD_HEIGHT
        elseif item.kind == "require" then
            local status, entry = item.status, item.status.entry
            row:SetHeight(REQUIRE_HEIGHT)
            row.title:SetPoint("TOPLEFT", 12, -9); row.title:SetWidth(width - 220)
            row.title:SetText(entry.title); row.title:SetTextColor(unpack(text))
            row.right:SetPoint("TOPRIGHT", -12, -10); row.right:SetWidth(190)
            local done = status.state == "have" or status.state == "open"
            row.right:SetText(status.state == "open" and "Nothing needed" or status.state == "have" and "You have it"
                or status.total and (status.done .. " of " .. status.total .. " steps") or "Not yet")
            row.right:SetTextColor(unpack(done and colors().success or gold))
            row.line:SetPoint("TOPLEFT", 12, -27); row.line:SetWidth(width - 24)
            row.line:SetText(status.state == "open" and (entry.note or "")
                or ((entry.everyone and "Everyone in the group needs it" or "One member of the group needs it")
                    .. (entry.scope and (", for " .. entry.scope) or "") .. ". " .. (entry.drop or entry.note or "")))
            row.second:SetPoint("TOPLEFT", 12, -42); row.second:SetWidth(width - 24)
            row.second:SetText(entry.uncertain or "")
            row.second:SetTextColor(1, 0.6, 0.3)
            y = y + REQUIRE_HEIGHT + 4
        elseif item.kind == "step" then
            local quest = ns.CatalogueQuest(item.id)
            row:SetHeight(STEP_HEIGHT)
            row.icon:Show(); row.icon:SetPoint("LEFT", 14, 0); row.icon:SetTexture(STATE_ICON[item.state])
            row.title:SetPoint("LEFT", 38, 0); row.title:SetWidth(width * 0.42)
            row.title:SetText((item.index and (item.index .. ". ") or "") .. (quest and quest.title or ("Quest " .. item.id)))
            row.title:SetTextColor(unpack(item.state == "done" and muted or (item.current and gold or text)))
            local state = item.current and (item.state == "open" and "Next" or STATE_TEXT[item.state]) or STATE_TEXT[item.state]
            row.right:SetPoint("RIGHT", item.current and -96 or -12, 0); row.right:SetWidth(width * 0.42)
            row.right:SetText(item.state == "done" and "Done" or ((item.note and (item.note .. "  •  ") or "")
                .. (state ~= "" and (state .. "  •  ") or "") .. (placeOf(item.id) or "")))
            row.right:SetTextColor(unpack(item.state == "done" and colors().success or muted))
            if item.current then
                row.go:Show(); row.go:SetPoint("RIGHT", -8, 0); row.go.caption:SetText("Show")
                row.go:SetScript("OnClick", function() showQuest(item.id) end)
            end
            row:SetScript("OnClick", function() showQuest(item.id) end)
            y = y + STEP_HEIGHT
        else
            local quest = ns.CatalogueQuest(item.id)
            row:SetHeight(QUEST_HEIGHT)
            row.icon:Show(); row.icon:SetPoint("TOPLEFT", 12, -8); row.icon:SetTexture(STATE_ICON[item.state])
            row.title:SetPoint("TOPLEFT", 36, -8); row.title:SetWidth(width - 220)
            row.title:SetText(quest.title); row.title:SetTextColor(unpack(item.state == "done" and muted or text))
            row.right:SetPoint("TOPRIGHT", -12, -9); row.right:SetWidth(170)
            row.right:SetText((STATE_TEXT[item.state] ~= "" and (STATE_TEXT[item.state] .. "  •  ") or "") .. "Lv " .. (quest.level or "?"))
            row.right:SetTextColor(unpack(item.state == "done" and colors().success or muted))
            row.line:SetPoint("TOPLEFT", 36, -27); row.line:SetWidth(width - 140)
            local leadCount = #item.lead
            if item.state ~= "open" then
                row.line:SetText(item.state == "done" and "" or (placeOf(item.id) and ("From " .. placeOf(item.id)) or ""))
            elseif leadCount > 0 then
                local first = ns.CatalogueQuest(item.lead[1])
                row.line:SetText(leadCount .. (leadCount == 1 and " quest" or " quests") .. " first, starting with "
                    .. (first and first.title or "a quest") .. (placeOf(item.lead[1]) and (" (" .. placeOf(item.lead[1]) .. ")") or ""))
                row.line:SetTextColor(unpack(gold))
            else
                row.line:SetText(placeOf(item.id) and ("Pick up from " .. placeOf(item.id)) or "Pickup location not known")
                row.line:SetTextColor(unpack(muted))
            end
            if item.state == "open" then
                local target = item.lead[1] or item.id
                row.go:Show(); row.go:SetPoint("BOTTOMRIGHT", -8, 6); row.go.caption:SetText(leadCount > 0 and "First step" or "Show")
                row.go:SetScript("OnClick", function() showQuest(target) end)
            end
            row:SetScript("OnClick", function() showQuest(item.id) end)
            y = y + QUEST_HEIGHT + 4
        end
        row:Show()
    end
    for index = #items + 1, #frame.rows do frame.rows[index] = nil end
    frame.empty:SetShown(#items == 0)
    frame.content:SetHeight(math.max(80, y + 8))
    local group = instance.group
    frame.collect:SetShown(group ~= nil)
    if group then
        frame.collect:SetEnabled(counts.open + counts.active + counts.ready > 0)
        frame.collect:SetScript("OnClick", function() ns.ShowDungeonQuests(group, true) end)
    end
    frame.hint:SetText(group and "Leads you to every pickup and prerequisite, then to the entrance."
        or "Press Show on the next step to see where it starts.")
end

function ns.RefreshInstancePage()
    local frame = ns.instancePage
    if frame and frame:IsShown() then draw(frame) end
end

-- `instance`: a dungeon group from ns.DungeonGroups(), or a raid from ns.instanceRaids.
function ns.ShowInstancePage(instance)
    if type(instance) ~= "table" then return false end
    ns.ReadProfile(); ns.ReadQuests()
    if not ns.instancePage then
        local frame = CreateFrame("Frame", "WowTogetherInstancePage", UIParent, "BackdropTemplate")
        ns.instancePage = frame
        frame:SetSize(WIDTH, HEIGHT); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG"); frame:SetClampedToScreen(true)
        frame:SetToplevel(true); frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
        frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
        ns.UIPanel(frame, colors().background); ns.UIClose(frame)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 20); frame.title:SetPoint("TOPLEFT", 22, -20)
        frame.subtitle = ns.UILabel(frame, nil, 11, colors().muted); frame.subtitle:SetPoint("TOPLEFT", 22, -48)
        frame.subtitle:SetWidth(WIDTH - 70); frame.subtitle:SetWordWrap(false)
        frame.summary = ns.UILabel(frame, nil, 12); frame.summary:SetPoint("TOPLEFT", 22, -70)
        frame.summary:SetWidth(WIDTH - 44); frame.summary:SetWordWrap(false)
        ns.UIDivider(frame, -94)
        frame.scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
        frame.scroll:SetPoint("TOPLEFT", 22, -100); frame.scroll:SetPoint("BOTTOMRIGHT", -38, 62)
        frame.content = CreateFrame("Frame", nil, frame.scroll); frame.content:SetSize(WIDTH - 60, 100); frame.scroll:SetScrollChild(frame.content)
        frame.rows, frame.pools = {}, {boxed = {}, plain = {}}
        frame.empty = ns.UILabel(frame.content, nil, 13, colors().muted); frame.empty:SetPoint("TOPLEFT", 14, -24)
        frame.empty:SetText("Nothing is known about this instance yet.")
        frame.collect = ns.UIButton(frame, "Start quest route", 156, function() end, true); frame.collect:SetPoint("BOTTOMLEFT", 22, 18)
        frame.hint = ns.UILabel(frame, nil, 11, colors().muted); frame.hint:SetPoint("BOTTOMLEFT", 190, 24)
        frame.hint:SetWidth(WIDTH - 220); frame.hint:SetWordWrap(false)
        if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherInstancePage") end
    end
    local frame = ns.instancePage
    local group = instance.ids and instance.definition ~= nil and instance or (instance.ids and instance) or nil
    frame.instance = {key = instance.key, name = instance.name, ids = instance.ids or {}, group = group,
        subtitle = group and ns.DungeonOverviewSummary(group) ~= "" and ns.DungeonOverviewSummary(group)
            or ("Level " .. tostring(instance.level or "?") .. (instance.where and (" • " .. instance.where) or "") .. (instance.note and (". " .. instance.note) or ""))}
    frame.scroll:SetVerticalScroll(0)
    draw(frame); frame:Show(); frame:Raise()
    return true
end

-- Keep the page current while it is open.
for _, event in ipairs({"QUEST_ACCEPTED", "QUEST_TURNED_IN", "QUEST_REMOVED", "BAG_UPDATE_DELAYED"}) do
    ns.On(event, function()
        if ns.instancePage and ns.instancePage:IsShown() and not ns.instancePageQueued then
            ns.instancePageQueued = true
            ns.After("timer:InstancePage", 0.5, function() ns.instancePageQueued = nil; ns.RefreshInstancePage() end)
        end
    end)
end
