local addonName, ns = ...

local requested, requestCount, sentRequests, pending = {}, 0, {}, false
ns.partyCatchupStatus = "Join a synced party to compare zone progress."

local function inParty()
    return ns.PartyFeaturesEnabled() and ns.ReadPublic(IsInGroup) == true and ns.ReadPublic(IsInRaid) ~= true and #(ns.partyNames or {}) > 0
end

function ns.ResetCatchupHistory()
    requested, requestCount, sentRequests = {}, 0, {}
end

function ns.ResetCatchupRequests() sentRequests = {} end

function ns.RequestedCatchupHistory() return requested end

function ns.ReceiveCatchupHistory(message)
    if string.sub(message, 1, 4) ~= "1|Y|" then return false end
    local payload, values, canonical, added = string.sub(message, 5), {}, {}, 0
    for value in string.gmatch(payload, "[^,]+") do
        local id = tonumber(value)
        if not ns.GuideInteger(id, 2147483647) or id < 1 or not ns.CatalogueQuest(id) or values[id]
            or #canonical >= 18 then return true, false, "invalid catch-up history request" end
        values[id], canonical[#canonical + 1] = true, tostring(id)
        if not requested[id] then added = added + 1 end
    end
    if #canonical == 0 or table.concat(canonical, ",") ~= payload or requestCount + added > 512 then
        return true, false, "catch-up history request limit"
    end
    for id in pairs(values) do requested[id] = true end
    requestCount = requestCount + added
    if added > 0 then ns.ScheduleSync() end
    return true, true
end

local function historyReady(person)
    if person.key == ns.self then return ns.questReady == true end
    local peer = ns.members[person.key]
    return person.synced and peer and peer.activeRevision and peer.completionRevision and peer.historyRevision
        and peer.historyRevision == peer.completionRevision and peer.completionRevision >= peer.activeRevision
        and not peer.syncPending
end

local function active(id)
    for _, person in ipairs(ns.PartyProfiles()) do
        local quests = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
        if quests and quests[id] then return true end
    end
    return false
end

function ns.RequestCatchupHistory(records)
    local scope, missing = {}, {}
    local function add(id, depth)
        if depth > 24 or scope[id] or not ns.CatalogueQuest(id) then return end
        scope[id] = true
        for _, previous in ipairs(ns.CataloguePrerequisiteIDs(id)) do add(previous, depth + 1) end
    end
    for _, record in ipairs(records) do add(record.id, 0) end
    for _, person in ipairs(ns.PartyProfiles()) do
        if person.key ~= ns.self then
            local peer = ns.members[person.key]
            local revision = peer and peer.activeRevision or 0
            if not sentRequests[person.key] or sentRequests[person.key].revision ~= revision then
                sentRequests[person.key] = {revision = revision, ids = {}}
            end
            for id in pairs(scope) do
                if (not historyReady(person) or ns.CatalogueCompletion(person.key, id) == nil)
                    and not sentRequests[person.key].ids[id] then missing[id] = true end
            end
        end
    end
    local ids = {}; for id in pairs(missing) do ids[#ids + 1] = id end; table.sort(ids)
    for first = 1, math.min(#ids, 512), 18 do
        local chunk = {}; for index = first, math.min(first + 17, #ids, 512) do chunk[#chunk + 1] = tostring(ids[index]) end
        if ns.QueueMessage("1|Y|" .. table.concat(chunk, ",")) then
            for _, person in ipairs(ns.PartyProfiles()) do
                if person.key ~= ns.self then
                    for _, value in ipairs(chunk) do sentRequests[person.key].ids[tonumber(value)] = true end
                end
            end
        end
    end
end

function ns.PartyCatchupGuide(base)
    if not inParty() then return nil, "Join a normal party to compare zone progress." end
    base = base or ns.ZoneGuideForMap(ns.profile and ns.profile.mapID or 0, true)
    if not base or base.mode ~= "zone" then return nil, "No zone guide is available for this map." end
    ns.RequestCatchupHistory(base.records)
    local people, targets, selected, required, waiting = ns.PartyProfiles(), {}, {}, {}, false
    for _, person in ipairs(people) do if not historyReady(person) then waiting = true end end
    for _, record in ipairs(base.records) do
        local complete, behind, eligible = 0, 0, 0
        for _, person in ipairs(people) do
            local allowed = ns.CatalogueIdentityAllowed(record.id, person.profile)
            if allowed == nil then waiting = true
            elseif allowed then
                eligible = eligible + 1
                local done = historyReady(person) and ns.CatalogueCompletion(person.key, record.id)
                if done == true then complete = complete + 1
                elseif done == false then behind = behind + 1 else waiting = true end
            end
        end
        if eligible >= 2 and complete > 0 and behind > 0 and not ns.GuideQuestSkipped(record.id)
            and not ns.IsLevelingExcludedQuest(record.id) and not ns.IsRepeatableQuest(record.id) and not ns.IsProfessionQuest(record.id)
            and (ns.LevelingValue(record.id) == true or active(record.id))
            and record.mapID == base.homeMapID then targets[record.id] = true end
    end
    if waiting then return nil, "Waiting for confirmed party quest history and character details." end
    local function add(id, key, depth)
        if depth > 24 or ns.CatalogueCompletion(key, id) == true or not ns.CatalogueQuest(id) then return end
        local profile
        for _, person in ipairs(people) do if person.key == key then profile = person.profile end end
        if ns.CatalogueIdentityAllowed(id, profile) ~= true or ns.IsLevelingExcludedQuest(id) or ns.IsRepeatableQuest(id) or ns.IsProfessionQuest(id) then return end
        selected[id], required[id] = true, not targets[id]
        local quest = ns.CatalogueQuest(id)
        if quest.previousQuest then add(quest.previousQuest, key, depth + 1) end
        for _, previous in ipairs(quest.prerequisiteAll or {}) do add(previous, key, depth + 1) end
        if quest.prerequisiteAny then
            for _, previous in ipairs(quest.prerequisiteAny) do if ns.CatalogueCompletion(key, previous) == true then return end end
            local alternatives = {}; for _, previous in ipairs(quest.prerequisiteAny) do alternatives[#alternatives + 1] = previous end
            table.sort(alternatives)
            for _, previous in ipairs(alternatives) do
                if ns.CatalogueIdentityAllowed(previous, profile) == true and ns.CatalogueQuest(previous) then
                    add(previous, key, depth + 1); break
                end
            end
        elseif not quest.previousQuest and not quest.prerequisiteAll and key == ns.self then
            for _, previous in ipairs(ns.LearnedPrerequisiteIDs(id)) do add(previous, key, depth + 1) end
        end
    end
    local count = 0
    for id in pairs(targets) do
        count = count + 1
        for _, person in ipairs(people) do if ns.CatalogueCompletion(person.key, id) == false then add(id, person.key, 0) end end
    end
    if count == 0 then return nil, "No useful zone progression gaps were found in the synced party." end
    local ids, records = {}, {}; for id in pairs(selected) do ids[#ids + 1] = id end; table.sort(ids)
    for _, id in ipairs(ids) do records[#records + 1] = ns.CatalogueRecord(id) end
    return {key = "catchup:" .. base.key, guideKey = base.key, title = base.zone .. " • Catch up party", zone = base.zone,
        mode = "zone", kind = "Party catch-up", fullGuide = true, fixedRoute = false, catchup = true,
        homeMapID = base.homeMapID, mapID = base.homeMapID, rangeLow = base.rangeLow, rangeHigh = base.rangeHigh,
        records = records, target = records[1], focusKey = ns.GuideFocus(records), profilesReady = true,
        catchupTargets = targets, catchupRequired = required,
        reason = count .. " useful quest(s) separate your party's progress. Finish missing prerequisites and nearby objectives together."}
end

function ns.ShowPartyCatchup(base, manual)
    if not ns.PartyFeaturesEnabled() then ns.partyCatchupStatus = "Party catch-up is disabled in solo leveling mode."; return false end
    local guide, reason = ns.PartyCatchupGuide(base)
    ns.partyCatchupStatus = reason or guide.reason
    if not guide then ns.guideAction = reason; return false end
    if ns.activityPrompt and ns.activityPrompt:IsShown() or ns.partyRoutePrompt and ns.partyRoutePrompt:IsShown() then return false end
    local key = "catchup:" .. guide.homeMapID .. ":" .. table.concat(ns.partyNames, ",")
    if manual and ns.db.activityNotices then ns.db.activityNotices[ns.ActivityNoticeKey(key)] = nil end
    ns.ShowActivityPrompt(key, "Catch up party in " .. guide.zone .. "?", guide.reason .. "\n\nYour current guide stays selected until you start this route.",
        function()
            local current, message = ns.PartyCatchupGuide(base)
            if current then ns.StartPartyRoute(current) else ns.guideAction = message; ns.Refresh() end
        end, "Catch up party", "Keep my guide")
    return true
end

function ns.SchedulePartyCatchup()
    if pending or not ns.db or not inParty() or ns.routeSelection and ns.routeSelection.catchup
        or not ns.profile or ns.profile.level <= 0 or ns.profile.mapID <= 0
        or not C_Timer or type(C_Timer.After) ~= "function" then return end
    pending = true
    C_Timer.After(1.5, function()
        pending = false
        if not ns.RouteInCombat() and not ns.routePlanning then ns.ShowPartyCatchup(nil, false) end
    end)
end
