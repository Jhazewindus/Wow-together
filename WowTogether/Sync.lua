local addonName, ns = ...

local PREFIX = "WowTogetherV1"
local queue, pumping, pending = {}, false, false
local revision = 0
local announced = false
local lastSnapshot, lastCompletion, lastRoster, lastOffers
local lastActiveRevision
local retryCount, sendDelay = 0, 1
local roster = {}
local identities = {}
local labels = {}
local assemblies = {}
local repairs = {}
local MAX_PARTS = 64
ns.syncStats = {sendAttempts = 0, received = 0, accepted = 0, snapshots = 0, titles = 0, ignored = 0, throttled = 0, retries = 0, failures = 0, coalesced = 0, repairs = 0, trace = {}}

function ns.ResultText(value, enumName)
    if not ns.Public(value) then return "restricted" end
    local label = tostring(value)
    local values = Enum and Enum[enumName]
    if type(values) == "table" then
        for key, code in pairs(values) do
            if ns.Public(code) and code == value then return key .. " (" .. label .. ")" end
        end
    end
    return label
end

local function trace(message)
    local history = ns.syncStats.trace
    history[#history + 1] = message
    if #history > 12 then table.remove(history, 1) end
end

local function ignored(reason)
    ns.syncStats.ignored = ns.syncStats.ignored + 1
    trace("Ignored: " .. reason)
end
local function canonical(name, realm)
    if not ns.Public(name) or not ns.Public(realm) or type(name) ~= "string" then return nil end
    if not realm or realm == "" then realm = GetRealmName() end
    if not ns.Public(realm) or type(realm) ~= "string" then return nil end
    return name .. "-" .. string.gsub(realm, "%s", "")
end

function ns.MemberLabel(key)
    return labels[key] or key
end

function ns.UpdateRoster()
    roster = {}
    identities = {}
    labels = {}
    local function addUnit(unit)
        local first, second = UnitFullName(unit)
        local key = canonical(first, second)
        if not key then return nil end
        -- Keep both API values. On the reported Forever build the second value is
        -- a surname, while the message sender includes a separate transport realm.
        local fullCharacterName
        if second and second ~= "" then fullCharacterName = first .. " " .. second end
        identities[#identities + 1] = {unit = unit, key = key, characterName = fullCharacterName}
        labels[key] = fullCharacterName or key
        return key
    end
    ns.self = addUnit("player")
    for index = 1, 4 do
        local key = addUnit("party" .. index)
        if key then roster[key] = true end
    end
    for key in pairs(ns.members) do
        if not roster[key] then ns.members[key] = nil; assemblies[key] = nil; repairs[key] = nil end
    end
    for key in pairs(assemblies) do
        if not roster[key] then assemblies[key] = nil end
    end
    ns.partyNames = {}
    for key in pairs(roster) do ns.partyNames[#ns.partyNames + 1] = key end
    table.sort(ns.partyNames)
    if ns.PrunePartyRoutes then ns.PrunePartyRoutes() end
    local signature = (ns.self or "") .. "|" .. table.concat(ns.partyNames, "|")
    if lastRoster and lastRoster ~= signature then
        -- Old-party transfers must not be delivered into a newly formed party.
        queue = {}
        retryCount = 0
        announced = false
        lastSnapshot, lastCompletion, lastOffers = nil, nil, nil
        if ns.ResetGuideTraffic then ns.ResetGuideTraffic() end
        if ns.ResetCatchupHistory then ns.ResetCatchupHistory() end
    end
    lastRoster = signature
    ns.Refresh()
end

local function resolveSender(sender)
    local characterName, realm = string.match(sender, "^(.+)%-(.+)$")
    local qualified = sender
    if characterName then
        -- Preserve spaces inside the character name; normalize only the realm.
        qualified = characterName .. "-" .. string.gsub(realm, "%s", "")
    else
        characterName = sender
        qualified = canonical(sender)
    end
    local function uniqueMatch(field, value)
        local match, count = nil, 0
        for _, identity in ipairs(identities) do
            if identity[field] and identity[field] == value then
                match = identity
                count = count + 1
            end
        end
        if count > 1 then return nil, "ambiguous party identity" end
        return match
    end
    -- Prefer full name/realm matches for clients that retain the traditional API.
    local match, reason = uniqueMatch("key", qualified)
    if reason then return nil, reason end
    if match then return match, "qualified name" end
    -- Forever surname fallback is an exact match of BOTH game-supplied name parts.
    -- Never use first-name-only matching or accept an unknown/ambiguous sender.
    match, reason = uniqueMatch("characterName", characterName)
    if reason then return nil, reason end
    if match then return match, "full character name" end
    return nil, "sender outside detected roster: " .. sender
end

local function inParty()
    local raid, grouped = IsInRaid(), IsInGroup()
    return ns.Public(raid) and ns.Public(grouped) and not raid and grouped
end

local function pump()
    if #queue == 0 then pumping = false; ns.Refresh(); return end
    if not inParty() then
        queue = {}
        retryCount = 0
        pumping = false
        lastSnapshot, lastCompletion, lastOffers = nil, nil, nil
        if ns.ResetGuideTraffic then ns.ResetGuideTraffic() end
        ns.Refresh()
        return
    end
    -- Keep the head until accepted; dropping throttled snapshot parts loses data.
    local message = queue[1]
    ns.syncStats.sendAttempts = ns.syncStats.sendAttempts + 1
    local result = C_ChatInfo.SendAddonMessage(PREFIX, message, "PARTY")
    ns.syncStats.lastSend = ns.ResultText(result, "SendAddonMessageResult")
    local values = Enum and Enum.SendAddonMessageResult
    local throttle = type(values) == "table" and values.AddonMessageThrottle
    local success = type(values) == "table" and values.Success
    local throttled = ns.Public(result) and ns.Public(throttle)
        and type(throttle) == "number" and result == throttle
    trace("Send " .. (string.sub(message, 1, 3) == "1|H" and "hello" or string.sub(message, 3, 3))
        .. ": " .. ns.syncStats.lastSend)
    if throttled and retryCount < 5 then
        retryCount = retryCount + 1
        ns.syncStats.throttled = ns.syncStats.throttled + 1
        ns.syncStats.retries = ns.syncStats.retries + 1
        sendDelay = math.min(16, sendDelay * 2)
        trace("Keep packet; retry in " .. sendDelay .. " seconds")
    elseif ns.Public(result) and (result == true or result == nil
        or (ns.Public(success) and type(success) == "number" and result == success)) then
        table.remove(queue, 1)
        retryCount = 0
        sendDelay = math.max(1, sendDelay * 0.8)
    else
        -- A failed snapshot invalidates its dependent title transfer as well.
        ns.syncStats.failures = ns.syncStats.failures + 1
        if throttled then ns.syncStats.throttled = ns.syncStats.throttled + 1 end
        trace("Transfer stopped after send failure; manual sync can retry")
        ns.status = "Delivery failed. Check Diagnostics, then retry Sync."
        queue = {}
        retryCount = 0
        pumping = false
        lastSnapshot, lastCompletion, lastOffers = nil, nil, nil
        if ns.ResetGuideTraffic then ns.ResetGuideTraffic() end
        ns.Refresh()
        return
    end
    ns.Refresh()
    C_Timer.After(sendDelay, pump)
end

function ns.TransportState()
    return {queued = #queue, retrying = retryCount > 0, failures = ns.syncStats.failures}
end

function ns.ActiveSnapshotRevision() return lastActiveRevision end

function ns.QueueMessage(message)
    if not ns.syncReady or not inParty() or type(message) ~= "string" or #message > 255 or #queue >= 256 then return false end
    queue[#queue + 1] = message
    if not pumping then pumping = true; C_Timer.After(0, pump) end
    return true
end

local function fingerprint(ids, titles)
    local keys, parts = {}, {}
    for id in pairs(ids) do keys[#keys + 1] = id end
    table.sort(keys)
    for _, id in ipairs(keys) do
        local title = titles and titles[id] or ""
        parts[#parts + 1] = id .. ":" .. #title .. ":" .. title
    end
    return table.concat(parts, ",")
end

local function send(kind, ids, sharedRevision)
    if not ns.syncReady or not inParty() then return end
    local sorted = {}
    for id in pairs(ids) do sorted[#sorted + 1] = id end
    table.sort(sorted)
    local total = math.max(1, math.ceil(#sorted / 18))
    if total > MAX_PARTS or #queue + total > 256 then
        ns.status = "Sync limit reached; try again after the current transfer."
        ns.Refresh()
        return
    end
    local transferRevision = sharedRevision
    if not transferRevision then revision = revision + 1; transferRevision = revision end
    for part = 1, total do
        local chunk = {}
        for i = (part - 1) * 18 + 1, math.min(part * 18, #sorted) do chunk[#chunk + 1] = tostring(sorted[i]) end
        queue[#queue + 1] = "1|" .. kind .. "|" .. transferRevision .. "|" .. part .. "|" .. total .. "|" .. table.concat(chunk, ",")
    end
    if not pumping then pumping = true; C_Timer.After(0, pump) end
    return transferRevision
end

function ns.SendActiveSnapshot(force)
    local signature = fingerprint(ns.active or {}, ns.localTitles)
    if not force and signature == lastSnapshot then
        ns.syncStats.coalesced = ns.syncStats.coalesced + 1
        return lastActiveRevision
    end
    local activeRevision = send("S", ns.active or {})
    if not activeRevision then return end
    lastActiveRevision = activeRevision
    lastSnapshot = signature
    local ids = {}
    for id in pairs(ns.localTitles or {}) do ids[#ids + 1] = id end
    table.sort(ids)
    if #queue + #ids > 256 then
        ns.status = "Quest IDs sent; title queue limit reached. Retry after the current transfer."
        lastSnapshot = nil
        return
    end
    for _, id in ipairs(ids) do
        queue[#queue + 1] = "1|T|" .. activeRevision .. "|" .. id .. "|" .. ns.localTitles[id]
    end
    if not pumping and #queue > 0 then pumping = true; C_Timer.After(0, pump) end
end

function ns.SendCompletion(force)
    local completed, checked = {}, {}
    for id in pairs(ns.QuestIDs()) do
        local result = ns.Completed(id)
        if result ~= nil then checked[id] = true end
        if result == true then completed[id] = true end
    end
    local signature = (lastActiveRevision or 0) .. "|" .. fingerprint(completed) .. "|" .. fingerprint(checked)
    if not force and signature == lastCompletion then
        ns.syncStats.coalesced = ns.syncStats.coalesced + 1
        return
    end
    local historyRevision = send("C", completed)
    -- Both halves use the same revision: absence from a completed list alone is
    -- never interpreted as proof that an ID was actually checked.
    if historyRevision and send("K", checked, historyRevision) then lastCompletion = signature end
end

function ns.SendOffers(force)
    if not ns.offerReady then return end
    local signature = (lastActiveRevision or 0) .. "|" .. fingerprint(ns.offered or {})
    if not force and signature == lastOffers then return end
    if send("O", ns.offered or {}) then lastOffers = signature end
end

function ns.SyncNow(force)
    if force and ns.ResetCatchupRequests then ns.ResetCatchupRequests() end
    if force == nil then force = true end
    if not ns.db then return end
    trace("Manual/event sync requested")
    ns.UpdateRoster()
    if not ns.ReadQuests() then ns.Refresh(); return end
    if ns.ReadGuide then ns.ReadGuide() end
    if not ns.syncReady then ns.status = "Party messaging unavailable. Run /wt probe."
    elseif not inParty() then announced = false; ns.status = "Local quest view ready. Join a party (raids unsupported)."
    else
        if force and #queue > 0 then
            ns.status = "Quest updates are already being sent."
            ns.Refresh()
            return
        end
        ns.status = "Quest progress queued for your party."
        if not announced then
            announced = true
            queue[#queue + 1] = "1|H"
        end
        ns.SendActiveSnapshot(force)
        if ns.SendProgress then ns.SendProgress(force, lastActiveRevision) end
        ns.SendCompletion(force)
        ns.SendOffers(force)
        if ns.SendGuideContext then ns.SendGuideContext(force) end
        if ns.SendRouteLocations then ns.SendRouteLocations(force, lastActiveRevision) end
        if ns.SendCatalogueContext then ns.SendCatalogueContext(force) end
    end
    ns.Refresh()
end

function ns.ScheduleSync()
    if not ns.db or pending or not C_Timer or type(C_Timer.After) ~= "function" then return end
    pending = true
    C_Timer.After(2, function() pending = false; ns.SyncNow(false) end)
end

local function replySnapshot()
    if not ns.ReadQuests() then return end
    if ns.ReadGuide then ns.ReadGuide() end
    ns.SendActiveSnapshot(true)
    if ns.SendProgress then ns.SendProgress(true, lastActiveRevision) end
    ns.SendCompletion(true)
    ns.SendOffers(true)
    if ns.SendGuideContext then ns.SendGuideContext(true) end
    if ns.SendRouteLocations then ns.SendRouteLocations(true, lastActiveRevision) end
    if ns.SendCatalogueContext then ns.SendCatalogueContext(true) end
end

local function repairPeer(sender)
    local member = ns.members[sender]
    if not member or (member.active and not member.syncPending) or repairs[sender] then return end
    local state = {attempts = 0}
    repairs[sender] = state
    local function request()
        if repairs[sender] ~= state or not roster[sender] or not inParty() then return end
        local current = ns.members[sender]
        if current and current.active and not current.syncPending then repairs[sender] = nil; return end
        if state.attempts >= 3 then return end
        state.attempts = state.attempts + 1
        if ns.QueueMessage("1|Q|" .. sender) then
            ns.syncStats.repairs = ns.syncStats.repairs + 1
            trace("Requested missing active snapshot from " .. ns.MemberLabel(sender))
        end
        C_Timer.After(12, request)
    end
    C_Timer.After(4, request)
end

function ns.Receive(prefix, message, channel, sender)
    if not ns.Public(prefix) then return end
    if prefix ~= PREFIX then return end
    ns.syncStats.received = ns.syncStats.received + 1
    if not ns.Public(message) or not ns.Public(channel) or not ns.Public(sender) then
        ignored("restricted message, channel, or sender"); return
    end
    if channel ~= "PARTY" then ignored("channel " .. tostring(channel)); return end
    if type(message) ~= "string" or type(sender) ~= "string" or #message > 255 then
        ignored("invalid envelope"); return
    end
    if not inParty() then ignored("not in a normal party"); return end
    local identity, matchReason = resolveSender(sender)
    if not identity then ignored(matchReason); return end
    if identity.unit == "player" then ignored("self echo (" .. matchReason .. ")"); return end
    local transportSender = sender
    sender = identity.key
    if not roster[sender] then ignored("sender left roster"); return end
    trace("Receive from " .. transportSender .. "; matched " .. matchReason)
    if message == "1|H" then
        ns.syncStats.accepted = ns.syncStats.accepted + 1
        trace("Accepted hello; await refreshed peer snapshot")
        assemblies[sender] = nil
        if ns.ResetPartyRoutePeer then ns.ResetPartyRoutePeer(sender) end
        local member = ns.members[sender] or {}
        ns.members[sender] = member
        member.syncPending, member.activeRevision = true, nil
        member.completionRevision, member.historyRevision, member.routeLocations = nil, nil, nil
        member.progress, member.progressTransfers = nil, nil
        member.offered, member.offerRevision = nil, nil
        repairs[sender] = nil
        replySnapshot()
        repairPeer(sender)
        ns.Refresh()
        return
    end
    if string.sub(message, 1, 4) == "1|Q|" then
        local target = string.sub(message, 5)
        if target == ns.self then ns.syncStats.accepted = ns.syncStats.accepted + 1; replySnapshot() end
        return
    end
    if ns.ReceiveCatchupHistory then
        local handled, accepted, reason = ns.ReceiveCatchupHistory(message, sender)
        if handled then
            if accepted then ns.syncStats.accepted = ns.syncStats.accepted + 1 else ignored(reason) end
            ns.Refresh(); return
        end
    end
    if ns.ReceiveCatalogueMessage then
        local handled, accepted, reason = ns.ReceiveCatalogueMessage(message, sender)
        if handled then
            if accepted then ns.syncStats.accepted = ns.syncStats.accepted + 1 else ignored(reason) end
            ns.Refresh()
            return
        end
    end
    if ns.ReceivePartyRouteMessage then
        local handled, accepted, reason = ns.ReceivePartyRouteMessage(message, sender)
        if handled then
            if accepted then ns.syncStats.accepted = ns.syncStats.accepted + 1 else ignored(reason) end
            ns.Refresh(); return
        end
    end
    if ns.ReceiveRouteMessage then
        local handled, accepted, reason = ns.ReceiveRouteMessage(message, sender)
        if handled then
            if accepted then ns.syncStats.accepted = ns.syncStats.accepted + 1 else ignored(reason) end
            ns.Refresh()
            return
        end
    end
    if ns.ReceiveProgressMessage then
        local handled, accepted, reason = ns.ReceiveProgressMessage(message, sender)
        if handled then
            if accepted then ns.syncStats.accepted = ns.syncStats.accepted + 1 else ignored(reason) end
            ns.Refresh()
            return
        end
    end
    if ns.ReceiveGuideMessage then
        local handled, accepted, reason = ns.ReceiveGuideMessage(message, sender)
        if handled then
            if accepted then ns.syncStats.accepted = ns.syncStats.accepted + 1; ns.Refresh()
            else ignored(reason or "invalid guide metadata") end
            return
        end
    end
    local titleRev, titleID, title = string.match(message, "^1|T|(%d+)|(%d+)|(.*)$")
    if titleRev then
        if #titleRev > 10 or #titleID > 10 or #title > 180 then ignored("invalid title bounds"); return end
        titleRev, titleID = tonumber(titleRev), tonumber(titleID)
        title = ns.SafeTitle(title)
        if not title or titleID < 1 or titleID > 2147483647 then ignored("invalid quest title"); return end
        assemblies[sender] = assemblies[sender] or {}
        local transfer = assemblies[sender]
        local newest = transfer.S and transfer.S.rev or 0
        local member = ns.members[sender]
        if titleRev < newest or (member and member.activeRevision and titleRev < member.activeRevision) then
            ignored("older title revision"); return
        end
        if member and member.activeRevision == titleRev then
            if not member.active[titleID] then ignored("title not in peer active quests"); return end
            member.titles = member.titles or {}
            member.titles[titleID] = title
        else
            -- Hold out-of-order titles until the matching snapshot is complete.
            local pendingTitles = transfer.T
            if pendingTitles and titleRev < pendingTitles.rev then ignored("older pending titles"); return end
            if not pendingTitles or titleRev > pendingTitles.rev then
                pendingTitles = {rev = titleRev, ids = {}, count = 0}
                transfer.T = pendingTitles
            end
            if not pendingTitles.ids[titleID] then
                if pendingTitles.count >= MAX_PARTS * 18 then ignored("title staging limit"); return end
                pendingTitles.count = pendingTitles.count + 1
            end
            pendingTitles.ids[titleID] = title
        end
        ns.syncStats.accepted = ns.syncStats.accepted + 1
        ns.syncStats.titles = ns.syncStats.titles + 1
        ns.Refresh()
        return
    end
    local kind, rev, part, total, payload = string.match(message, "^1|([SCOK])|(%d+)|(%d+)|(%d+)|(.*)$")
    if not kind or #rev > 10 then ignored("invalid protocol/header"); return end
    rev, part, total = tonumber(rev), tonumber(part), tonumber(total)
    if total < 1 or total > MAX_PARTS or part < 1 or part > total then ignored("invalid part bounds"); return end
    local ids, count = {}, 0
    if payload ~= "" then
        if not string.match(payload, "^%d[%d,]*%d$") and not string.match(payload, "^%d+$") then ignored("invalid quest list"); return end
        if string.find(payload, ",,", 1, true) then ignored("empty quest ID"); return end
        for token in string.gmatch(payload, "[^,]+") do
            local id = tonumber(token)
            if not id or id < 1 or id > 2147483647 or #token > 10 then ignored("invalid quest ID"); return end
            count = count + 1
            if count > 18 then ignored("too many quest IDs"); return end
            ids[id] = true
        end
    end
    assemblies[sender] = assemblies[sender] or {}
    local bucket = assemblies[sender][kind]
    -- A new snapshot supersedes incomplete/older transfers of the same kind.
    if bucket and rev < bucket.rev then ignored("older revision"); return end
    if not bucket or rev > bucket.rev then
        bucket = {rev = rev, total = total, parts = {}, count = 0}
        assemblies[sender][kind] = bucket
    end
    if bucket.total ~= total or bucket.parts[part] then ignored("duplicate or inconsistent part"); return end
    ns.syncStats.accepted = ns.syncStats.accepted + 1
    bucket.parts[part] = ids
    bucket.count = bucket.count + 1
    if bucket.count ~= total then return end
    ns.syncStats.snapshots = ns.syncStats.snapshots + 1
    trace("Completed " .. kind .. " snapshot from " .. ns.MemberLabel(sender))
    local result = {}
    for _, chunk in pairs(bucket.parts) do for id in pairs(chunk) do result[id] = true end end
    ns.members[sender] = ns.members[sender] or {}
    if kind == "S" then
        local first = not ns.members[sender].active
        ns.members[sender].active = result
        ns.members[sender].activeRevision = rev
        local retainedTitles = {}
        for id, title in pairs(ns.members[sender].titles or {}) do
            if result[id] then retainedTitles[id] = title end
        end
        ns.members[sender].titles = retainedTitles
        local pendingTitles = assemblies[sender].T
        if pendingTitles and pendingTitles.rev == rev then
            for id, title in pairs(pendingTitles.ids) do
                if result[id] then ns.members[sender].titles[id] = title end
            end
        end
        if pendingTitles and pendingTitles.rev <= rev then assemblies[sender].T = nil end
        if first then ns.SendActiveSnapshot() end
        ns.members[sender].syncPending = nil
        repairs[sender] = nil
        ns.SendCompletion()
    elseif kind == "C" then
        ns.members[sender].completed = result
        ns.members[sender].completionRevision = rev
    elseif kind == "K" then
        ns.members[sender].historyChecked = result
        ns.members[sender].historyRevision = rev
    else
        ns.members[sender].offered = result
        ns.members[sender].offerRevision = rev
    end
    if kind == "C" or kind == "K" then repairPeer(sender) end
    ns.Refresh()
end

function ns.InitializeSync()
    ns.syncReady = C_ChatInfo and type(C_ChatInfo.RegisterAddonMessagePrefix) == "function"
        and type(C_ChatInfo.SendAddonMessage) == "function"
        and C_Timer and type(C_Timer.After) == "function"
    if ns.syncReady then
        local registered = C_ChatInfo.RegisterAddonMessagePrefix(PREFIX)
        ns.syncStats.registration = ns.ResultText(registered, "RegisterAddonMessagePrefixResult")
        -- Modern clients return an enum, older clients may return a boolean.
        -- Confirm actual registration when the query exists; never assume a numeric code.
        if type(C_ChatInfo.IsAddonMessagePrefixRegistered) == "function" then
            local confirmed = C_ChatInfo.IsAddonMessagePrefixRegistered(PREFIX)
            ns.syncReady = ns.Public(confirmed) and confirmed == true
            ns.syncStats.confirmation = ns.ResultText(confirmed, "RegisterAddonMessagePrefixResult")
        else
            local values = Enum and Enum.RegisterAddonMessagePrefixResult
            local success = type(values) == "table" and values.Success
            ns.syncReady = ns.Public(registered) and (registered == true
                or (ns.Public(success) and type(success) == "number" and registered == success))
            ns.syncStats.confirmation = "query unavailable; checked boolean/named Success result"
        end
        trace("Prefix registration: " .. ns.syncStats.registration .. "; ready: " .. tostring(ns.syncReady))
    end
    ns.On("CHAT_MSG_ADDON", ns.Receive)
    ns.UpdateRoster()
end


function ns.SyncDiagnostics(output)
    local function safe(value)
        if not ns.Public(value) then return "restricted" end
        if value == nil then return "unknown" end
        return tostring(value)
    end
    output("")
    output("Sync runtime")
    output("Player name candidates: " .. safe(ns.self) .. " / " .. safe(ns.MemberLabel(ns.self)))
    output("Sender matching: qualified name, or unique exact first-name + surname in the current roster")
    output("Grouped: " .. safe(IsInGroup()) .. "; raid: " .. safe(IsInRaid()))
    output("Detected party peers: " .. tostring(#(ns.partyNames or {})))
    for _, name in ipairs(ns.partyNames or {}) do
        local member = ns.members[name]
        output("  " .. ns.MemberLabel(name) .. ": " .. (member and member.syncPending and "waiting for refreshed quest snapshot; last progress retained"
            or (member and member.active and "quest snapshot received" or "waiting for quest snapshot")))
    end
    output("Quest giver offer API ready: " .. safe(ns.offerReady))
    output("Quest greeting list ready: " .. safe(ns.greetingReady) .. "; " .. (ns.greetingReadStatus or "not read this session"))
    local offered = 0
    for _ in pairs(ns.offered or {}) do offered = offered + 1 end
    output("Quest IDs currently reported by quest giver: " .. offered)
    if ns.PickupDiagnostics then ns.PickupDiagnostics(output) end
    local guideCount = 0
    if ns.GuideQuestIDs then for _ in pairs(ns.GuideQuestIDs()) do guideCount = guideCount + 1 end end
    output("Guide quest records known: " .. guideCount)
    output("Guide read status: " .. (ns.guideReadError or "no read failures recorded"))
    output("Offline catalogue: " .. (ns.catalogue and ns.catalogue.count or 0) .. " quests; captured " .. (ns.catalogue and ns.catalogue.captured or "unknown"))
    output("Route location read status: " .. (ns.routeReadError or "no read failures recorded"))
    local localPoints = 0
    for _ in pairs(ns.routeLocations or {}) do localPoints = localPoints + 1 end
    output("Local quest destinations: " .. localPoints)
    local objectives = 0
    for _, progress in pairs(ns.localProgress or {}) do objectives = objectives + #progress.objectives end
    output("Local objective details: " .. objectives .. "; restricted fields: " .. (ns.restrictedObjectives or 0))
    output("Objective read status: " .. (ns.progressReadError or "no read failures recorded"))
    output("Peer objective snapshots received: " .. (ns.syncStats.objectives or 0))
    output("NPC hints: " .. ns.npcHintCount .. "; " .. ns.npcHintStatus)
    output("Automatic sync: group / quest / objective / level / zone events; updates batched for 2 seconds.")
    output("Current quests first: " .. safe(ns.Option("currentQuestsFirst")) .. "; nearby pickups: " .. safe(ns.Option("nearbyPickups")))
    output("Auto-accept enabled: " .. safe(ns.Option("autoAccept")) .. "; last attempted dialog quest: " .. safe(ns.autoAcceptAttempt))
    output("Auto turn-in enabled: " .. safe(ns.Option("autoTurnIn")) .. "; " .. ns.turnInStatus)
    output("Map preview: " .. (ns.Option("fullRoute") and "full route" or ("current place + " .. ns.Option("routeAhead") .. " ahead")))
    output(ns.guideScanStatus)
    output("Profession guides: " .. ns.professionStatus .. " Personal recipe/material data is not sent to peers.")
    output("Map route: " .. ns.routeStats.status)
    local selection, route = ns.routeSelection, ns.selectedRoute
    if selection then
        output("Selected guide: " .. selection.key .. "; quests in scope: " .. #(selection.records or {}))
        if route and route.fixed then
            output("Fixed zone guide: " .. route.totalSteps .. " total steps; " .. route.remainingSteps .. " remaining; "
                .. route.eligibleMappedQuests .. " eligible quests with mapped steps; " .. route.missing .. " missing-location steps.")
            output("Temporarily deferred pickups: " .. (route.deferredQuests or 0) .. ". Progress and NPC offers recheck them; manual skips remain separate.")
        else
            output("Current trip: " .. (route and route.tripQuests or "legacy") .. " quests; " .. (route and #route.stops or 0)
                .. " stops; pending records: " .. (route and route.missing or 0))
        end
        if selection.batchIDs then output("Trip quest IDs: " .. table.concat(selection.batchIDs, ",")) end
    end
    output("Route generation: " .. (ns.routePlanning and "loading" or ns.routePlanningError or "idle"))
    if ns.routePlanningErrorDetail then output("Route generation error: " .. safe(ns.routePlanningErrorDetail)) end
    output("Route drawing surface: " .. (ns.routeStats.surface or "not drawn") .. "; " .. (ns.routeStats.geometry or "layout unavailable"))
    output("Current quests first: " .. safe(ns.Option("currentQuestsFirst")))
    output("Party route: " .. (ns.partyRouteStatus or "No route started."))
    output("Rendered route pins: " .. ns.routeStats.pins .. "; lines: " .. ns.routeStats.lines)
    for _, person in ipairs(ns.PartyProfiles and ns.PartyProfiles() or {}) do
        local profile = person.profile
        output("Character context for " .. person.name .. ": " .. (profile and ("level " .. profile.level .. ", " .. profile.faction .. ", " .. profile.zone) or "waiting"))
        if profile then output("  UI map " .. profile.mapID .. "; class " .. (profile.classID or 0) .. "; race " .. (profile.raceID or 0)) end
    end
    output("Quest read ready: " .. safe(ns.questReady))
    output("Quest log entries: " .. safe(ns.questEntries))
    local active = 0
    for _ in pairs(ns.active or {}) do active = active + 1 end
    output("Local active quest IDs: " .. active)
    output("Skipped restricted quest entries: " .. safe(ns.restrictedQuests or 0))
    output("Prefix registration result: " .. (ns.syncStats.registration or "not attempted"))
    output("Prefix confirmation: " .. (ns.syncStats.confirmation or "unavailable"))
    output("Sync ready: " .. safe(ns.syncReady))
    output("Send attempts: " .. ns.syncStats.sendAttempts .. "; queued: " .. #queue)
    output("Throttled attempts: " .. ns.syncStats.throttled .. "; retries scheduled: " .. ns.syncStats.retries)
    output("Failed transfers: " .. ns.syncStats.failures .. "; unchanged updates suppressed: " .. ns.syncStats.coalesced)
    output("Missing-snapshot recovery requests: " .. ns.syncStats.repairs)
    output("Last send result: " .. (ns.syncStats.lastSend or "none"))
    output("Our prefix messages received (including self echoes): " .. ns.syncStats.received)
    output("Accepted packets: " .. ns.syncStats.accepted .. "; ignored: " .. ns.syncStats.ignored)
    output("Completed incoming snapshots: " .. ns.syncStats.snapshots)
    output("Accepted quest title packets: " .. ns.syncStats.titles)
    local resolved, total = 0, 0
    for id in pairs(ns.QuestIDs()) do
        total = total + 1
        if not string.find(ns.QuestTitle(id), "(title pending)", 1, true) then resolved = resolved + 1 end
    end
    output("Quest names resolved: " .. resolved .. "/" .. total)
    for _, name in ipairs(ns.partyNames or {}) do
        local member = ns.members[name]
        local checked = 0
        if member and member.historyRevision and member.historyRevision == member.completionRevision then
            for id in pairs(member.historyChecked or {}) do
                if ns.QuestIDs()[id] then checked = checked + 1 end
            end
        end
        output("History checks received for " .. ns.MemberLabel(name) .. ": " .. checked .. "/" .. total)
    end
    output("Status: " .. ns.status)
    output("")
    output("Recent sync activity (this session)")
    for _, message in ipairs(ns.syncStats.trace) do output(message) end
    output("")
    output("Run /wt sync on BOTH clients, let the queue drain (retries may take longer), then Refresh this report.")
    output("Send attempts do not prove delivery. Self echoes do not prove peer delivery.")
end
