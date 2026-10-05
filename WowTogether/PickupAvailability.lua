local addonName, ns = ...

-- User-tested Forever beta interpretation. This is an optional compatibility
-- gate, not a claim about the meaning of IsPushableQuest on other WoW clients.
local readings, sent, sequence = {}, nil, 0
local MAX_QUESTS, PER_PART, MAX_PARTS = 512, 18, 29

local function api()
    if type(IsPushableQuest) == "function" then return IsPushableQuest, "IsPushableQuest" end
    if C_QuestLog and type(C_QuestLog.IsPushableQuest) == "function" then
        return C_QuestLog.IsPushableQuest, "C_QuestLog.IsPushableQuest"
    end
end

function ns.InvalidatePickupAvailability()
    if ns.RouteInCombat() then ns.pickupDirty = true; return end
    readings = {}
    ns.pickupDirty = nil
    ns.pickupRevision = (ns.pickupRevision or 0) + 1
end

function ns.ResetPickupTraffic() sent = nil end

function ns.PickupAvailability(key, id)
    if not ns.Option("betaPickupCheck") then return nil, false end
    if key ~= ns.self then
        local member = ns.members[key]
        local snapshot = member and member.pickupAvailability
        if not snapshot then return nil, false end -- Older addons use the existing evidence gates.
        if not snapshot.supported then return nil, false end
        if member.syncPending or not member.active or snapshot.activeRevision ~= member.activeRevision then return nil, true end
        return snapshot.values[id], true
    end
    local fn = api()
    if not fn then return nil, false end
    if ns.RouteInCombat() then
        if type(readings[id]) == "boolean" then return readings[id], true end
        return nil, true
    end
    if readings[id] == nil then
        local result = ns.ReadPublic(fn, id)
        readings[id] = type(result) == "boolean" and result or "unknown"
        if result == false then readings[id] = false end
    end
    if type(readings[id]) == "boolean" then return readings[id], true end
    return nil, true
end

local function scope()
    local ids, count = {}, 0
    local function add(id)
        if ns.GuideInteger(id) and id > 0 and not ids[id] and count < MAX_QUESTS then
            ids[id], count = true, count + 1
        end
    end
    for _, record in ipairs(ns.routeSelection and ns.routeSelection.records or {}) do add(record.id) end
    for _, source in ipairs({ns.partyRouteHistoryScope or {}, ns.QuestIDs()}) do
        local ordered = {}; for id in pairs(source) do ordered[#ordered + 1] = id end; table.sort(ordered)
        for _, id in ipairs(ordered) do add(id) end
    end
    local ordered = {}; for id in pairs(ids) do ordered[#ordered + 1] = id end; table.sort(ordered)
    return ordered
end

function ns.ReadPickupAvailability()
    local fn, source = api()
    local supported = ns.Option("betaPickupCheck") and fn ~= nil
    local values, yes, no, unknown = {}, 0, 0, 0
    for _, id in ipairs(scope()) do
        local result = ns.PickupAvailability(ns.self, id)
        if result == true then yes = yes + 1; values[id] = true
        elseif result == false then no = no + 1; values[id] = false
        else unknown = unknown + 1 end
    end
    ns.localPickupAvailability = {supported = supported, source = source or "missing", values = values,
        yes = yes, no = no, unknown = unknown}
    return ns.localPickupAvailability
end

function ns.SendPickupAvailability(force, activeRevision)
    if not activeRevision or ns.RouteInCombat() then return end
    local snapshot, encoded = ns.ReadPickupAvailability(), {}
    local ids = {}; for id in pairs(snapshot.values) do ids[#ids + 1] = id end; table.sort(ids)
    for _, id in ipairs(ids) do encoded[#encoded + 1] = id .. ":" .. (snapshot.values[id] and "1" or "0") end
    local supported = snapshot.supported and "1" or "0"
    local signature = activeRevision .. "|" .. supported .. "|" .. table.concat(encoded, ",")
    if not force and signature == sent then return end
    sequence = sequence + 1
    local parts, success = math.max(1, math.ceil(#encoded / PER_PART)), true
    for part = 1, parts do
        local chunk = {}
        for index = (part - 1) * PER_PART + 1, math.min(part * PER_PART, #encoded) do chunk[#chunk + 1] = encoded[index] end
        if not ns.QueueMessage(table.concat({"1", "E", activeRevision, sequence, part, parts, supported, table.concat(chunk, ",")}, "|")) then success = false end
    end
    if success then sent = signature end
end

function ns.ReceivePickupAvailabilityMessage(message, sender)
    if string.sub(message, 1, 4) ~= "1|E|" then return false end
    local active, rev, part, total, supported, payload = string.match(message, "^1|E|(%d+)|(%d+)|(%d+)|(%d+)|([01])|(.*)$")
    active, rev, part, total = tonumber(active), tonumber(rev), tonumber(part), tonumber(total)
    if #message > 255 or not ns.GuideInteger(active) or active < 1 or not ns.GuideInteger(rev) or rev < 1
        or not ns.GuideInteger(part, MAX_PARTS) or not ns.GuideInteger(total, MAX_PARTS)
        or part < 1 or total < 1 or part > total then return true, false, "invalid pickup-check header" end
    local member = ns.members[sender]
    if not member then
        local inRoster = false
        for _, name in ipairs(ns.partyNames or {}) do if name == sender then inRoster = true end end
        if not inRoster then return true, false, "pickup check outside roster" end
        member = {}; ns.members[sender] = member
    end
    local old, bucket = member.pickupAvailability, member.pickupTransfer
    if member.activeRevision and active < member.activeRevision
        or old and (active < old.activeRevision or active == old.activeRevision and rev <= old.revision)
        or bucket and (active < bucket.activeRevision or active == bucket.activeRevision and rev < bucket.revision) then
        return true, false, "old pickup check"
    end
    if payload == "" and (part ~= 1 or total ~= 1) or supported == "0" and payload ~= ""
        or string.find(payload, ",,", 1, true) or string.sub(payload, 1, 1) == "," or string.sub(payload, -1) == "," then
        return true, false, "invalid pickup-check payload"
    end
    local values, count = {}, 0
    for encoded in string.gmatch(payload, "[^,]+") do
        local id, flag = string.match(encoded, "^(%d+):([01])$"); id = tonumber(id)
        if not ns.GuideInteger(id) or id < 1 or values[id] ~= nil or count >= PER_PART then
            return true, false, "invalid pickup-check value"
        end
        values[id], count = flag == "1", count + 1
    end
    if not bucket or active > bucket.activeRevision or rev > bucket.revision then
        bucket = {activeRevision = active, revision = rev, total = total, supported = supported == "1", parts = {}, count = 0}
        member.pickupTransfer = bucket
    end
    if bucket.total ~= total or bucket.supported ~= (supported == "1") or bucket.parts[part] then
        return true, false, "inconsistent pickup-check part"
    end
    bucket.parts[part], bucket.count = values, bucket.count + 1
    if bucket.count == total then
        local all, size = {}, 0
        for _, chunk in pairs(bucket.parts) do
            for id, value in pairs(chunk) do
                if all[id] ~= nil then member.pickupTransfer = nil; return true, false, "duplicate pickup-check quest" end
                all[id], size = value, size + 1
                if size > MAX_QUESTS then member.pickupTransfer = nil; return true, false, "pickup-check scope limit" end
            end
        end
        member.pickupAvailability = {activeRevision = active, revision = rev, supported = bucket.supported, values = all}
        member.pickupTransfer = nil
        ns.syncStats.pickups = (ns.syncStats.pickups or 0) + 1
    end
    return true, true
end

function ns.PickupDiagnostics(output)
    local snapshot = ns.ReadPickupAvailability()
    output("Tested beta pickup check: " .. (ns.Option("betaPickupCheck") and "enabled" or "disabled") .. "; API: " .. snapshot.source)
    output("Own pickup results: " .. snapshot.yes .. " true; " .. snapshot.no .. " false; " .. snapshot.unknown .. " unknown")
    output("Peer pickup snapshots received: " .. (ns.syncStats.pickups or 0))
    for _, name in ipairs(ns.partyNames or {}) do
        local member, count = ns.members[name], 0
        local received = member and member.pickupAvailability
        if received then for _ in pairs(received.values) do count = count + 1 end end
        output("  Pickup checks for " .. ns.MemberLabel(name) .. ": " .. count .. "; " .. (received and received.supported
            and (not member.syncPending and received.activeRevision == member.activeRevision and "current" or "waiting for matching quest snapshot")
            or "compatibility check unavailable/off"))
    end
end
