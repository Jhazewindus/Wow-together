local addonName, ns = ...

function ns.SafeTitle(title)
    if not ns.Public(title) or type(title) ~= "string" then return nil end
    title = string.gsub(title, "[%c|]", " ")
    if not string.find(title, "%S") then return nil end
    if #title > 180 then
        -- Bound packet size without cutting a UTF-8 character in half.
        local limit, first = 177, 177
        while first > 0 do
            local byte = string.byte(title, first)
            if byte < 128 or byte >= 192 then break end
            first = first - 1
        end
        if first > 0 then
            local byte = string.byte(title, first)
            local width = byte >= 240 and 4 or (byte >= 224 and 3 or (byte >= 192 and 2 or 1))
            if first + width - 1 > limit then limit = first - 1 end
        else limit = 0 end
        title = string.sub(title, 1, limit) .. "..."
    end
    return title
end

function ns.QuestTitle(id)
    if ns.localTitles and ns.localTitles[id] then return ns.localTitles[id] end
    -- Stable peer ordering keeps conflicting locales deterministic.
    local names = {}
    for name in pairs(ns.members) do names[#names + 1] = name end
    table.sort(names)
    for _, name in ipairs(names) do
        local member = ns.members[name]
        if member.active and member.active[id] and member.titles and member.titles[id] then
            return member.titles[id]
        end
    end
    local quest = ns.CatalogueQuest and ns.CatalogueQuest(id)
    if quest and quest.title ~= "" then return quest.title end
    if ns.GuideTitle then
        local title = ns.GuideTitle(id)
        if title then return title end
    end
    return "Quest " .. id .. " (title pending)"
end

function ns.ReadQuests()
    ns.active = {}
    ns.localTitles = {}
    ns.questLevels = {}
    ns.questEntries = nil
    ns.restrictedQuests = 0
    if not C_QuestLog or type(C_QuestLog.GetNumQuestLogEntries) ~= "function"
        or type(C_QuestLog.GetInfo) ~= "function" then
        ns.questReady = false
        ns.status = "Quest log API missing. Run /wt probe."
        return false
    end
    local count = C_QuestLog.GetNumQuestLogEntries()
    if not ns.Public(count) or type(count) ~= "number" then
        ns.questReady = false
        ns.status = "Quest log count unavailable or restricted."
        return false
    end
    ns.questEntries = count
    for index = 1, count do
        local info = C_QuestLog.GetInfo(index)
        if ns.Public(info) and type(info) == "table" then
            local id, header = info.questID, info.isHeader
            if ns.Public(id) and ns.Public(header) and not header
                and type(id) == "number" and id > 0 then
                local level = info.level
                if ns.Public(level) and type(level) == "number" and level > 0 and level <= 255 and level == math.floor(level) then ns.questLevels[id] = level end
                local title = ns.SafeTitle(info.title)
                ns.localTitles[id] = title
                ns.active[id] = title or ("Quest " .. id)
            elseif not ns.Public(id) or not ns.Public(header) then
                ns.restrictedQuests = ns.restrictedQuests + 1
            end
        elseif not ns.Public(info) then
            ns.restrictedQuests = ns.restrictedQuests + 1
        end
    end
    ns.questReady = true
    return true
end

function ns.Completed(id)
    if not C_QuestLog or type(C_QuestLog.IsQuestFlaggedCompleted) ~= "function" then return nil end
    local value = C_QuestLog.IsQuestFlaggedCompleted(id)
    if not ns.Public(value) or type(value) ~= "boolean" then return nil end
    return value
end

function ns.QuestIDs()
    local ids = {}
    for id in pairs(ns.active or {}) do ids[id] = true end
    for _, member in pairs(ns.members) do
        for id in pairs(member.active or {}) do ids[id] = true end
    end
    if ns.GuideQuestIDs then for id in pairs(ns.GuideQuestIDs()) do ids[id] = true end end
    if ns.CatalogueScopeIDs then for id in pairs(ns.CatalogueScopeIDs()) do ids[id] = true end end
    for id in pairs(ns.dungeonHistoryScope or {}) do ids[id] = true end
    for id in pairs(ns.partyRouteHistoryScope or {}) do ids[id] = true end
    return ids
end

function ns.MemberStates(id)
    local states = {}
    local function add(name, active, completed, checked, offered, ready, pending)
        local status, history
        if completed then history = "completed"
        elseif checked then history = "not_completed"
        else history = "unknown" end
        if pending then status = "Refreshing snapshot"
        elseif active and ready then status = "Ready to turn in"
        elseif active then status = "Active"
        elseif offered then status = "Offered by quest giver"
        elseif completed then status = "Reported completed"
        elseif checked then status = "Not in log; history unfinished"
        else status = "Not in log; history pending" end
        states[#states + 1] = {name = name, status = status, history = history,
            active = active and true or false, offered = offered and true or false, ready = ready and true or false}
    end
    local localCompleted = ns.Completed(id)
    add("You", ns.active and ns.active[id], localCompleted == true, localCompleted ~= nil, ns.offered and ns.offered[id], ns.readyToTurnIn and ns.readyToTurnIn[id])
    local names = {}
    for name, member in pairs(ns.members) do
        if member.active then names[#names + 1] = name end
    end
    table.sort(names)
    for _, name in ipairs(names) do
        local member = ns.members[name]
        local checked = ns.CatalogueCompletion(name, id) ~= nil
        local point = ns.RoutePointForMember and ns.RoutePointForMember(name, id)
        add(ns.MemberLabel(name), member.active[id], member.completed and member.completed[id], checked,
            member.offered and member.offered[id], (point and point.kind == "t") or (ns.QuestProgressReady and ns.QuestProgressReady(name, id)), member.syncPending)
    end
    return states
end

function ns.Rows()
    local rows = {}
    local people = 1
    for _, member in pairs(ns.members) do if member.active then people = people + 1 end end
    for id in pairs(ns.QuestIDs()) do
        local active, completed = 0, 0
        if ns.active[id] then active = active + 1 end
        if ns.Completed(id) == true then completed = completed + 1 end
        for _, member in pairs(ns.members) do
            if member.active and member.active[id] then active = active + 1 end
            if member.completed and member.completed[id] then completed = completed + 1 end
        end
        if active > 0 then
            rows[#rows + 1] = {id = id, title = ns.QuestTitle(id), active = active,
                completed = completed, people = people, members = ns.MemberStates(id)}
        end
    end
    table.sort(rows, function(a, b)
        if a.active ~= b.active then return a.active > b.active end
        return a.id < b.id
    end)
    return rows
end
