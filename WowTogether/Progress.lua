local addonName, ns = ...

ns.localProgress = {}
local sentProgress, sequence = {}, 0
local MAX_OBJECTIVES = 12

local function smallText(value)
    value = ns.SafeTitle(value) or "Objective"
    value = string.gsub(value, "[,;~]", " ")
    local cut = math.min(#value, 64)
    while cut > 0 and cut < #value do
        local byte = string.byte(value, cut + 1)
        if byte < 128 or byte >= 192 then break end
        cut = cut - 1
    end
    return string.sub(value, 1, cut)
end

local function publicCount(value)
    return ns.GuideInteger(value) and value or nil
end

function ns.ReadProgress()
    local result = {}
    ns.progressReady = C_QuestLog and type(C_QuestLog.GetQuestObjectives) == "function" or false
    ns.restrictedObjectives = 0
    if ns.progressReady then
        for id in pairs(ns.active or {}) do
            local okay, objectives = pcall(C_QuestLog.GetQuestObjectives, id)
            if not okay then ns.progressReadError = "A read-only objective query failed on this build." end
            if okay and ns.Public(objectives) and type(objectives) == "table" then
                local values = {}
                for index, info in ipairs(objectives) do
                    if index > MAX_OBJECTIVES then break end
                    if ns.Public(info) and type(info) == "table" then
                        local kind = ns.Public(info.type) and type(info.type) == "string" and info.type or "other"
                        kind = string.sub(string.gsub(kind, "[^a-z]", ""), 1, 12)
                        if kind == "" then kind = "other" end
                        local done = ns.Public(info.finished) and type(info.finished) == "boolean" and info.finished or nil
                        if ns.Public(info.finished) and info.finished == false then done = false end
                        values[index] = {index = index, text = smallText(info.text), kind = kind,
                            have = publicCount(info.numFulfilled), need = publicCount(info.numRequired), finished = done}
                        if not ns.Public(info.text) or not ns.Public(info.finished) or not ns.Public(info.numFulfilled) or not ns.Public(info.numRequired) then
                            ns.restrictedObjectives = ns.restrictedObjectives + 1
                        end
                    else
                        values[index] = {index = index, text = "Objective " .. index, kind = "other"}
                        ns.restrictedObjectives = ns.restrictedObjectives + 1
                    end
                end
                result[id] = {objectives = values}
            end
        end
    end
    ns.localProgress = result
end

function ns.ResetProgressTraffic() sentProgress = {} end

local function encode(objective)
    return table.concat({objective.index, objective.finished == true and "1" or (objective.finished == false and "0" or "u"),
        objective.have or "-", objective.need or "-", objective.kind, objective.text}, ",")
end

function ns.SendProgress(force, activeRevision)
    if not activeRevision then return end
    local ids = {}
    for id in pairs(ns.localProgress) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do
        local objectives = ns.localProgress[id].objectives
        local encoded = {}
        for _, objective in ipairs(objectives) do encoded[#encoded + 1] = encode(objective) end
        local fingerprint = activeRevision .. "|" .. table.concat(encoded, ";")
        if force or fingerprint ~= sentProgress[id] then
            sequence = sequence + 1
            local parts, success = math.max(1, math.ceil(#encoded / 2)), true
            for part = 1, parts do
                local values = {}
                for index = (part - 1) * 2 + 1, math.min(part * 2, #encoded) do values[#values + 1] = encoded[index] end
                if not ns.QueueMessage(table.concat({"1", "D", activeRevision, id, sequence, part, parts, table.concat(values, ";")}, "|")) then success = false end
            end
            if success then sentProgress[id] = fingerprint end
        end
    end
    for id in pairs(sentProgress) do if not ns.active[id] then sentProgress[id] = nil end end
end

function ns.ReceiveProgressMessage(message, sender)
    if string.sub(message, 1, 4) ~= "1|D|" then return false end
    local activeRev, id, rev, part, total, payload = string.match(message, "^1|D|(%d+)|(%d+)|(%d+)|(%d+)|(%d+)|(.*)$")
    activeRev, id, rev, part, total = tonumber(activeRev), tonumber(id), tonumber(rev), tonumber(part), tonumber(total)
    if not ns.GuideInteger(activeRev) or not ns.GuideInteger(id) or id <= 0 or not ns.GuideInteger(rev)
        or not ns.GuideInteger(part, 6) or not ns.GuideInteger(total, 6) or part < 1 or total < 1 or part > total then
        return true, false, "invalid objective header"
    end
    ns.members[sender] = ns.members[sender] or {}
    local member = ns.members[sender]
    if member.activeRevision and activeRev < member.activeRevision then return true, false, "old objective snapshot" end
    member.progressTransfers, member.progress = member.progressTransfers or {}, member.progress or {}
    local bucket, old = member.progressTransfers[id], member.progress[id]
    if (old and activeRev == old.activeRevision and rev <= old.revision)
        or (bucket and (activeRev < bucket.activeRevision or (activeRev == bucket.activeRevision and rev < bucket.revision))) then
        return true, false, "old objective revision"
    end
    local values = {}
    if payload == "" and (part ~= 1 or total ~= 1) then return true, false, "empty objective part" end
    if string.find(payload, ";;", 1, true) or string.sub(payload, 1, 1) == ";" or string.sub(payload, -1) == ";" then
        return true, false, "empty objective value"
    end
    for encoded in string.gmatch(payload, "[^;]+") do
        local index, flag, have, need, kind, text = string.match(encoded, "^(%d+),([01u]),([%d-]+),([%d-]+),([a-z]+),(.+)$")
        local nHave, nNeed = tonumber(have), tonumber(need)
        index = tonumber(index)
        if not ns.GuideInteger(index, MAX_OBJECTIVES) or index < 1 or not text or #text > 64 or #kind > 12
            or (have ~= "-" and not ns.GuideInteger(nHave)) or (need ~= "-" and not ns.GuideInteger(nNeed)) or values[index] then
            return true, false, "invalid objective value"
        end
        local count = 0
        for _ in pairs(values) do count = count + 1 end
        if count >= 2 then return true, false, "too many objectives in part" end
        values[index] = {index = index, finished = flag == "1" and true or (flag == "0" and false or nil),
            have = nHave, need = nNeed, kind = kind, text = smallText(text)}
        if flag == "0" then values[index].finished = false end
    end
    if not bucket or activeRev > bucket.activeRevision or rev > bucket.revision then
        local count = 0
        for _ in pairs(member.progressTransfers) do count = count + 1 end
        if not bucket and count >= 40 then return true, false, "objective transfer limit" end
        bucket = {activeRevision = activeRev, revision = rev, total = total, parts = {}, count = 0}
        member.progressTransfers[id] = bucket
    end
    if bucket.total ~= total or bucket.parts[part] then return true, false, "duplicate objective part" end
    bucket.parts[part], bucket.count = values, bucket.count + 1
    if bucket.count == total then
        local all, count = {}, 0
        for _, chunk in pairs(bucket.parts) do
            for index, objective in pairs(chunk) do
                if all[index] then return true, false, "duplicate objective index" end
                all[index], count = objective, count + 1
            end
        end
        for index = 1, count do if not all[index] then return true, false, "missing objective index" end end
        member.progress[id] = {activeRevision = activeRev, revision = rev, objectives = all}
        ns.syncStats.objectives = (ns.syncStats.objectives or 0) + 1
    end
    return true, true
end

function ns.ProgressForMember(key, id)
    if key == ns.self then return ns.localProgress[id] end
    local member = ns.members[key]
    local progress = member and member.progress and member.progress[id]
    if member and not member.syncPending and member.active and member.active[id] and progress and progress.activeRevision == member.activeRevision then return progress end
end

function ns.ObjectiveLabel(text)
    return string.gsub(text, "%s*:%s*%d+%s*/%s*%d+%s*$", "")
end

function ns.QuestProgressReady(key, id)
    local progress = ns.ProgressForMember(key, id)
    if not progress or #progress.objectives == 0 then return false end
    for _, objective in ipairs(progress.objectives) do if objective.finished ~= true then return false end end
    return true
end

function ns.TrackerRows()
    local ids, result = {}, {}
    for id in pairs(ns.active or {}) do ids[id] = true end
    for _, member in pairs(ns.members) do for id in pairs(member.active or {}) do ids[id] = true end end
    for id in pairs(ids) do
        local people, objectives = 0, nil
        for _, person in ipairs(ns.PartyProfiles()) do
            local active = person.key == ns.self and ns.active[id] or (ns.members[person.key] and ns.members[person.key].active and ns.members[person.key].active[id])
            if active then people = people + 1 end
            local progress = ns.ProgressForMember(person.key, id)
            if progress and #progress.objectives > 0 and not objectives then objectives = progress.objectives end
        end
        result[#result + 1] = {id = id, title = ns.QuestTitle(id), people = people, objectives = objectives or {}}
    end
    table.sort(result, function(a, b)
        if a.people ~= b.people then return a.people > b.people end
        return a.id < b.id
    end)
    return result
end

function ns.TrackerValue(key, id, index)
    local member = ns.members[key]
    local active = key == ns.self and ns.active[id] or (member and member.active and member.active[id])
    if not active and ns.CatalogueCompletion(key, id) == true then return "Done" end
    if not active and (key == ns.self or (member and member.active and not member.syncPending)) then return "Not in log" end
    local progress = ns.ProgressForMember(key, id)
    local objective = progress and progress.objectives[index]
    if not objective then return "…" end
    if objective.have and objective.need and objective.need > 0 then return objective.have .. "/" .. objective.need end
    if objective.finished == true then return "✓" end
    return objective.finished == false and "In progress" or "…"
end

function ns.ToggleTracker()
    ns.db.trackerVisible = not ns.tracker:IsShown()
    ns.tracker:SetShown(ns.db.trackerVisible)
    ns.RenderTracker()
end

function ns.ScrollTracker(delta)
    local frame = ns.tracker
    frame.scrollOffset = math.max(0, math.min(frame.scrollMaximum or 0, (frame.scrollOffset or 0) - delta * 54))
    frame.scroll:SetVerticalScroll(frame.scrollOffset)
    ns.RenderTracker()
end

function ns.CreateTracker()
    local frame = CreateFrame("Frame", "WowTogetherTracker", UIParent, "BackdropTemplate")
    ns.tracker = frame
    frame:SetSize(360, ns.Option("trackerHeight"))
    frame:SetPoint("TOPRIGHT", UIParent, "TOPRIGHT", -70, -230)
    frame:SetClampedToScreen(true); frame:SetFrameStrata("MEDIUM")
    frame:SetBackdrop({bgFile = "Interface\\Buttons\\WHITE8X8"})
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local point, _, relative, x, y = self:GetPoint()
        if ns.Public(point) and ns.Public(relative) and ns.Public(x) and ns.Public(y)
            and type(point) == "string" and type(relative) == "string" and type(x) == "number" and type(y) == "number" then
            ns.db.trackerPosition = {point = point, relative = relative, x = x, y = y}
        end
    end)
    local saved = ns.db.trackerPosition
    if type(saved) == "table" and type(saved.point) == "string" and type(saved.relative) == "string"
        and type(saved.x) == "number" and type(saved.y) == "number" then
        frame:ClearAllPoints(); frame:SetPoint(saved.point, UIParent, saved.relative, saved.x, saved.y)
    end
    local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", 0, 0); close:SetScript("OnClick", ns.ToggleTracker)
    frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    frame.title:SetPoint("TOPLEFT", 12, -10); frame.title:SetText("Together • party progress")
    frame.scroll = CreateFrame("ScrollFrame", nil, frame)
    frame.scroll:SetPoint("TOPLEFT", 4, -32); frame.scroll:SetPoint("BOTTOMRIGHT", -4, 18)
    frame.scroll:EnableMouseWheel(true)
    frame.scroll:SetScript("OnMouseWheel", function(_, delta) ns.ScrollTracker(delta) end)
    frame.content = CreateFrame("Frame", nil, frame.scroll)
    frame.content:SetSize(348, 100); frame.scroll:SetScrollChild(frame.content)
    frame.footer = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.footer:SetPoint("BOTTOMLEFT", 12, 3)
    frame.lines = {}; frame.scrollOffset = 0
    frame:SetShown(ns.db.trackerVisible ~= false)
end

function ns.TrackerDisplayLines()
    local result, y, rows, profiles = {}, 0, ns.TrackerRows(), ns.PartyProfiles()
    local function add(text, x, width, gold, right)
        result[#result + 1] = {text = text, x = x, width = width, gold = gold, right = right, y = y}
    end
    for _, row in ipairs(rows) do
        add(row.title, 8, 328, true); y = y + 22
        if #row.objectives == 0 then add("Objective details pending", 16, 316); y = y + 20 end
        for index, objective in ipairs(row.objectives) do
            add(ns.ObjectiveLabel(objective.text), 16, 316, true); y = y + 18
            for _, person in ipairs(profiles) do
                local zone = person.profile and person.profile.zone or "zone pending"
                if zone == "" then zone = "zone pending" end
                local value = ns.TrackerValue(person.key, row.id, index)
                if not person.synced then value = "Waiting" end
                add(person.name .. " • " .. zone, 24, 238)
                add(value, 266, 68, false, true); y = y + 17
            end
            y = y + 4
        end
        y = y + 12
    end
    if #rows == 0 then add("Accept a quest to start tracking.", 8, 328); y = 30 end
    return result, y, #rows
end

function ns.RenderTracker()
    if not ns.tracker or not ns.tracker:IsShown() then return end
    local frame, used = ns.tracker, 0
    local height = ns.Option("trackerHeight")
    frame:SetHeight(height)
    frame:SetBackdropColor(0.035, 0.045, 0.06, ns.Option("trackerOpacity"))
    local items, contentHeight, count = ns.TrackerDisplayLines()
    local view = height - 50
    frame.scrollMaximum = math.max(0, contentHeight - view)
    frame.scrollOffset = math.min(frame.scrollOffset or 0, frame.scrollMaximum)
    frame.scroll:SetVerticalScroll(frame.scrollOffset)
    frame.content:SetHeight(math.max(view, contentHeight))
    -- Only create text for the viewport; long party logs stay cheap to scroll.
    for _, item in ipairs(items) do
        if item.y + 18 >= frame.scrollOffset and item.y <= frame.scrollOffset + view then
            used = used + 1
            local font = frame.lines[used]
            if not font then font = frame.content:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall"); frame.lines[used] = font end
            font:ClearAllPoints(); font:SetPoint("TOPLEFT", item.x, -item.y)
            font:SetFont("Fonts\\FRIZQT__.TTF", 11, "OUTLINE")
            font:SetWidth(item.width); font:SetHeight(16); font:SetWordWrap(false)
            font:SetJustifyH(item.right and "RIGHT" or "LEFT")
            font:SetTextColor(item.gold and 1 or 0.91, item.gold and 0.82 or 0.93, item.gold and 0.42 or 0.97, 1)
            font:SetText(item.text); font:Show()
        end
    end
    for index = used + 1, #frame.lines do frame.lines[index]:Hide() end
    frame.footer:SetText(count .. " quests • mouse wheel to scroll")
end

ns.On("QUEST_WATCH_UPDATE", function() if ns.db then ns.ReadProgress(); ns.ScheduleSync(); ns.Refresh() end end)
