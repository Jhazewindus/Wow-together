local addonName, ns = ...

local LIMIT, HISTORY_LIMIT = 300, 128
local function json(value)
    if not ns.Public(value) then return "null" end
    local kind = type(value)
    if kind == "boolean" then return value and "true" or "false" end
    if kind == "number" then
        if value ~= value or value == math.huge or value == -math.huge then return "null" end
        return tostring(value)
    end
    if kind == "string" then
        value = string.gsub(value, "\\", "\\\\")
        value = string.gsub(value, '"', '\\"')
        value = string.gsub(value, "%c", function(c) return string.format("\\u%04x", string.byte(c)) end)
        return '"' .. value .. '"'
    end
    if kind ~= "table" then return "null" end
    local keys, parts = {}, {}
    for key in pairs(value) do keys[#keys + 1] = key end
    if #keys == #value then
        for _, item in ipairs(value) do parts[#parts + 1] = json(item) end
        return "[" .. table.concat(parts, ",") .. "]"
    end
    table.sort(keys)
    for _, key in ipairs(keys) do parts[#parts + 1] = json(key) .. ":" .. json(value[key]) end
    return "{" .. table.concat(parts, ",") .. "}"
end

local function state()
    return ns.db and ns.db.questResearch and ns.db.questResearch[ns.self]
end

function ns.ResearchCaptureBoundary()
    local saved = state()
    if saved then saved.session = saved.session + 1 end
    ns.researchSignature = nil
    if ns.ResetLearningContext then ns.ResetLearningContext() end
end

function ns.InitializeQuestResearch()
    if type(ns.db.questResearch) ~= "table" then ns.db.questResearch = {} end
    local saved = state()
    if type(saved) ~= "table" or saved.schema ~= 1 or type(saved.events) ~= "table" then
        saved = {schema = 1, events = {}, sequence = 0, dropped = 0, session = 0, reputationRevision = 0}
        ns.db.questResearch[ns.self] = saved
    end
    for _, key in ipairs({"sequence", "dropped", "session", "reputationRevision"}) do
        if not ns.GuideInteger(saved[key]) then saved[key] = 0 end
    end
    while #saved.events > LIMIT do table.remove(saved.events, 1); saved.dropped = saved.dropped + 1 end
    ns.ResearchCaptureBoundary()
end

local function snapshot(kind, facts, saved)
    ns.ReadProfile()
    local profile = ns.profile or {}
    local version, build, _, interface = ns.ReadPublic(GetBuildInfo)
    local result = {event = kind, addon = ns.VERSION, session = saved.session,
        client = version, build = build, interface = interface,
        level = profile.level, faction = profile.faction, classID = profile.classID,
        raceID = profile.raceID, mapID = profile.mapID, reputationRevision = saved.reputationRevision,
        questID = facts.questID, npcID = facts.npcID, completeList = facts.complete,
        offered = {}, active = {}, completed = {}, notCompleted = {}, historyUnknown = {}}
    if kind == "skip-step" or kind == "skip-quest" or kind == "defer-pickup" or kind == "restore-pickup" then
        result.guideKey, result.stepKey = ns.SafeTitle(facts.guideKey), ns.SafeTitle(facts.stepKey)
        -- Invited trip keys contain the sender's character name. Raw research
        -- exports stay anonymous; stable catalogue guide keys remain intact.
        if result.guideKey and string.find(result.guideKey, "party:", 1, true) then result.guideKey = "party-route" end
        result.stepKind = ns.SafeTitle(facts.stepKind)
        if ns.GuideInteger(facts.guideStep) then result.guideStep = facts.guideStep end
    end
    if kind == "level" and ns.GuideInteger(facts.level, 255) then result.level = facts.level end
    local ids, count = {}, 0
    local function add(id)
        if ns.GuideInteger(id) and id > 0 and not ids[id] then
            if count < HISTORY_LIMIT then ids[id], count = true, count + 1
            else result.historyTruncated = true end
        end
    end
    local function addWithPrerequisites(id)
        add(id)
        for _, previous in ipairs(ns.CataloguePrerequisiteIDs(id)) do add(previous) end
    end
    addWithPrerequisites(facts.questID)
    for id in pairs(facts.offered or {}) do result.offered[#result.offered + 1] = id; addWithPrerequisites(id) end
    for id in pairs(ns.active or {}) do
        if kind ~= "turn-in" or id ~= facts.questID then result.active[#result.active + 1] = id end
        addWithPrerequisites(id)
    end
    if kind == "accept" and facts.questID and not ns.active[facts.questID] then result.active[#result.active + 1] = facts.questID end
    local related = {}
    for id, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
        for _, point in ipairs(quest.starts or {}) do
            if facts.npcID and point.npc and point.entityID == facts.npcID then related[#related + 1] = id; break end
        end
    end
    table.sort(related)
    for _, id in ipairs(related) do addWithPrerequisites(id) end
    if kind == "offers" then
        local atNPC = {}; for _, id in ipairs(related) do atNPC[id] = true end
        result.plannedPickups, result.missingPlannedPickups = {}, {}
        for _, stop in ipairs(ns.selectedRoute and ns.selectedRoute.stops or {}) do
            if stop.kind == "a" and atNPC[stop.id] and (not stop.memberKey or stop.memberKey == ns.self) then
                result.plannedPickups[#result.plannedPickups + 1] = stop.id
                if facts.complete and not facts.offered[stop.id] then result.missingPlannedPickups[#result.missingPlannedPickups + 1] = stop.id end
            end
        end
        table.sort(result.plannedPickups); table.sort(result.missingPlannedPickups)
    end
    for _, record in ipairs(ns.routeSelection and ns.routeSelection.records or {}) do addWithPrerequisites(record.id) end
    for id in pairs(ids) do
        local done = C_QuestLog and ns.ReadPublic(C_QuestLog.IsQuestFlaggedCompleted, id)
        if kind == "turn-in" and id == facts.questID then done = true end -- Native hand-in event is direct evidence.
        local target = done == true and result.completed or (done == false and result.notCompleted or result.historyUnknown)
        target[#target + 1] = id
    end
    for _, key in ipairs({"offered", "active", "completed", "notCompleted", "historyUnknown"}) do table.sort(result[key]) end
    return result
end

function ns.RecordQuestResearch(kind, facts)
    local saved = state()
    if not saved or not ns.Option("recordQuestData") then return end
    facts = facts or {}
    if (kind == "accept" or kind == "turn-in") and (not ns.GuideInteger(facts.questID) or facts.questID <= 0) then return end
    if facts.questID ~= nil and (not ns.GuideInteger(facts.questID) or facts.questID <= 0) then return end
    if kind == "reputation" then saved.reputationRevision = saved.reputationRevision + 1 end
    local record = snapshot(kind, facts, saved)
    local signature = json(record)
    if signature == ns.researchSignature then return end
    ns.researchSignature = signature
    saved.sequence = saved.sequence + 1
    record.sequence = saved.sequence
    saved.events[#saved.events + 1] = record
    if ns.ObserveQuestLearning then ns.ObserveQuestLearning(record, ns.self) end
    if #saved.events > LIMIT then table.remove(saved.events, 1); saved.dropped = saved.dropped + 1 end
end

function ns.ExportQuestResearch()
    local saved, lines = state(), {}
    local header = {format = "wow-together-quest-research", schema = 1, addon = ns.VERSION,
        capacity = LIMIT, dropped = saved and saved.dropped or 0}
    local encoded = json(header)
    lines[#lines + 1] = string.sub(encoded, 1, -2) .. ',"events":['
    for index, record in ipairs(saved and saved.events or {}) do
        lines[#lines + 1] = json(record) .. (index < #saved.events and "," or "")
    end
    lines[#lines + 1] = "]}"
    return table.concat(lines, "\n")
end

function ns.ShowQuestResearch()
    ns.ShowDiagnostics(ns.ExportQuestResearch(), "Wow Together — Quest data export", ns.ShowQuestResearch)
end

function ns.ExportGuideFindings()
    local saved = state()
    return json({format = "wow-together-guide-findings", schema = 1, addon = ns.VERSION,
        capacity = LIMIT, dropped = saved and saved.dropped or 0,
        findings = ns.ExportLearnedFindings(), events = saved and saved.events or {}})
end

function ns.ShowGuideFindings()
    ns.ShowDiagnostics(ns.ExportGuideFindings(), "Wow Together — Guide findings export", ns.ShowGuideFindings)
end

function ns.ResearchDiagnostics(output)
    local saved = state()
    output("Quest data recording: " .. (ns.Option("recordQuestData") and "on" or "off") .. "; "
        .. (saved and #saved.events or 0) .. "/" .. LIMIT .. " observations; "
        .. (saved and saved.dropped or 0) .. " older observations replaced. Export: /wt research.")
    ns.LearningDiagnostics(output)
end
