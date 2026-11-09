local addonName, ns = ...

local alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
local alphabetIndex = {}
for index = 1, #alphabet do alphabetIndex[string.sub(alphabet, index, index)] = index - 1 end
local indexedCatalogue, orderedIDs, indexByID, catalogueHash
local localCodes, fullAssembly, dirtyIDs = {}, {}, {}
local MAX_PEERS, JOURNAL_LIMIT = 40, 1000
local lastPersistAt

local function catalogueIndex()
    local catalogue = ns.catalogue
    if type(catalogue) ~= "table" then return nil end
    local quests = rawget(catalogue, "quests")
    if getmetatable(catalogue) and (not ns.optionalDataState
        or ns.optionalDataState.WowTogether_QuestData ~= "loaded") then return nil end
    if type(quests) ~= "table" then return nil end
    if indexedCatalogue == quests and orderedIDs then return orderedIDs, indexByID, catalogueHash end
    local ids = {}
    for id in pairs(quests) do
        if ns.GuideInteger(id, 2147483647) and id > 0 then ids[#ids + 1] = id end
    end
    table.sort(ids)
    local hash = 0
    local function add(value)
        value = tostring(value)
        for index = 1, #value do hash = (hash * 31 + string.byte(value, index)) % 2147483647 end
        hash = (hash * 31 + 255) % 2147483647
    end
    add(catalogue.captured or "unknown"); add(#ids)
    local indexes = {}
    for index, id in ipairs(ids) do indexes[id] = index; add(id) end
    indexedCatalogue, orderedIDs, indexByID, catalogueHash = quests, ids, indexes, tostring(hash)
    return ids, indexes, catalogueHash
end

local function encodeBytes(bytes)
    local output = {}
    for index = 1, #bytes, 3 do
        local a, b, c = string.byte(bytes, index, index + 2)
        b, c = b or 0, c or 0
        local value = a * 65536 + b * 256 + c
        output[#output + 1] = string.sub(alphabet, math.floor(value / 262144) % 64 + 1, math.floor(value / 262144) % 64 + 1)
        output[#output + 1] = string.sub(alphabet, math.floor(value / 4096) % 64 + 1, math.floor(value / 4096) % 64 + 1)
        output[#output + 1] = index + 1 <= #bytes and string.sub(alphabet, math.floor(value / 64) % 64 + 1, math.floor(value / 64) % 64 + 1) or "="
        output[#output + 1] = index + 2 <= #bytes and string.sub(alphabet, value % 64 + 1, value % 64 + 1) or "="
    end
    return table.concat(output)
end

local function decodeBytes(payload)
    if type(payload) ~= "string" or #payload % 4 ~= 0 or not string.match(payload, "^[A-Za-z0-9+/]*=?=?$") then return nil end
    local output = {}
    for index = 1, #payload, 4 do
        local a, b = alphabetIndex[string.sub(payload, index, index)], alphabetIndex[string.sub(payload, index + 1, index + 1)]
        local cchar, dchar = string.sub(payload, index + 2, index + 2), string.sub(payload, index + 3, index + 3)
        local c, d = cchar == "=" and 0 or alphabetIndex[cchar], dchar == "=" and 0 or alphabetIndex[dchar]
        if a == nil or b == nil or c == nil or d == nil then return nil end
        local value = a * 262144 + b * 4096 + c * 64 + d
        output[#output + 1] = string.char(math.floor(value / 65536) % 256)
        if cchar ~= "=" then output[#output + 1] = string.char(math.floor(value / 256) % 256) end
        if dchar ~= "=" then output[#output + 1] = string.char(value % 256) end
        if cchar == "=" and dchar ~= "=" or index + 3 < #payload and (cchar == "=" or dchar == "=") then return nil end
    end
    return table.concat(output)
end

local function encodeCodes(codes)
    local bytes, buffer, bits = {}, 0, 0
    for _, code in ipairs(codes) do
        if not ns.GuideInteger(code, 3) then return nil end
        buffer, bits = buffer + code * 2 ^ bits, bits + 2
        if bits == 8 then bytes[#bytes + 1] = string.char(buffer); buffer, bits = 0, 0 end
    end
    if bits > 0 then bytes[#bytes + 1] = string.char(buffer) end
    return encodeBytes(table.concat(bytes))
end

local function decodeCodes(payload, count)
    if not ns.GuideInteger(count, 100000) then return nil end
    local bytes = decodeBytes(payload)
    if not bytes or #bytes ~= math.ceil(count * 2 / 8) then return nil end
    local codes, buffer, bits, index = {}, 0, 0, 1
    for offset = 1, #bytes do
        buffer, bits = buffer + string.byte(bytes, offset) * 2 ^ bits, bits + 8
        while bits >= 2 and index <= count do
            codes[index], buffer, bits = buffer % 4, math.floor(buffer / 4), bits - 2
            index = index + 1
        end
    end
    return codes
end

local function currentCode(id)
    if ns.questHistory and ns.questHistory[id] then return 3 end
    local completed = ns.Completed and ns.Completed(id)
    if completed == true then return 3 end
    if ns.active and ns.active[id] then return 2 end
    if completed == false then return 1 end
    return 0
end

local function stateStore()
    if not ns.char then return nil end
    local saved = ns.char.syncState
    if type(saved) ~= "table" then saved = {}; ns.char.syncState = saved end
    local journal = type(ns.char.stateJournal) == "table" and ns.char.stateJournal
        or type(saved.journal) == "table" and saved.journal or {}
    ns.char.stateJournal, saved.journal = journal, journal
    saved.revision = ns.GuideInteger(saved.revision, 2147483647) and saved.revision or 0
    saved.minRev = ns.GuideInteger(saved.minRev, 2147483647) and saved.minRev or 0
    return saved
end

local function peerStore()
    if not ns.db then return nil end
    ns.db.peers = type(ns.db.peers) == "table" and ns.db.peers or {}
    local peers, keys = ns.db.peers, {}
    for key, record in pairs(peers) do
        if type(key) ~= "string" or type(record) ~= "table" then peers[key] = nil
        else keys[#keys + 1] = key end
    end
    if #keys > MAX_PEERS then
        table.sort(keys, function(a, b)
            local left, right = peers[a]._use or 0, peers[b]._use or 0
            return left == right and a < b or left < right
        end)
        for index = 1, #keys - MAX_PEERS do peers[keys[index]] = nil end
    end
    return ns.db.peers
end

local function peerRecord(key)
    local peers = peerStore()
    return peers and peers[key]
end

local function persistPeer(key, member)
    local peers = peerStore()
    if not peers then return end
    local record = peers[key] or {}
    peers[key] = record
    if member and member.profile then
        record.level, record.classID = member.profile.level, member.profile.classID
        record.faction = member.profile.faction
    end
    if member and member.state then
        record.state, record.stateHash, record.receivedRev = member.state, member.stateHash, member.receivedRev or 0
    end
    if member then
        record.sentRev, record.sentHash = member.sentRev, member.sentHash
        record.peerAck = member.stateAck
    end
    record.updatedAt = type(GetTime) == "function" and GetTime() or 0
    record._use = (ns.db.peerUse or 0) + 1; ns.db.peerUse = record._use
    local keys = {}
    for name in pairs(peers) do keys[#keys + 1] = name end
    if #keys > MAX_PEERS then
        table.sort(keys, function(a, b)
            local left, right = peers[a]._use or 0, peers[b]._use or 0
            return left == right and a < b or left < right
        end)
        for index = 1, #keys - MAX_PEERS do peers[keys[index]] = nil end
    end
end

local function applyPeerState(key, record)
    if type(record) ~= "table" or not record.state or record.stateHash ~= select(3, catalogueIndex()) then return end
    local ids = catalogueIndex()
    local codes = decodeCodes(record.state, #ids)
    if not codes then return end
    local member = ns.members[key] or {}; ns.members[key] = member
    member.state, member.stateHash, member.receivedRev = record.state, record.stateHash, record.receivedRev or 0
    member.sentRev, member.sentHash = record.sentRev, record.sentHash
    member.active, member.completed, member.historyChecked = {}, {}, {}
    for index, id in ipairs(ids) do
        local code = codes[index]
        if code == 2 then member.active[id] = true end
        if code == 3 then member.completed[id] = true end
        if code == 1 or code == 2 or code == 3 then member.historyChecked[id] = true end
    end
    member.activeRevision = member.receivedRev
    member.completionRevision, member.historyRevision = member.receivedRev, member.receivedRev
    member.syncPending, member.stateReady = nil, true
    if ns.GuideInteger(record.level, 255) and ns.GuideInteger(record.classID, 255) then
        member.profile = {level = record.level, classID = record.classID, faction = record.faction or "Unknown"}
    end
end

function ns.SyncStateInitialize()
    local ids, _, hash = catalogueIndex()
    local saved = stateStore()
    peerStore()
    if not ids or not saved then return false end
    local old = saved.catalogueHash == hash and saved.snapshot and decodeCodes(saved.snapshot, #ids)
    if old then
        localCodes = old
        dirtyIDs = {}
        for _, id in ipairs(ids) do dirtyIDs[id] = true end
    else
        if saved.catalogueHash and saved.catalogueHash ~= hash then
            saved.journal, ns.char.stateJournal, saved.revision, saved.minRev = {}, {}, 0, 0
        end
        localCodes = {}
        for index, id in ipairs(ids) do localCodes[index] = currentCode(id) end
        saved.snapshot = encodeCodes(localCodes)
        saved.catalogueHash = hash
        dirtyIDs = {}
    end
    for key, record in pairs(peerStore() or {}) do applyPeerState(key, record) end
    return true
end

function ns.SyncStateCatalogueHash()
    local _, _, hash = catalogueIndex()
    return hash
end

function ns.SyncStateEncode(codes) return encodeCodes(codes) end
function ns.SyncStateDecode(payload, count) return decodeCodes(payload, count) end

function ns.SyncStateScan()
    local ids, _, hash = catalogueIndex()
    local saved = stateStore()
    if not ids or not saved then return {} end
    if not localCodes or #localCodes ~= #ids then ns.SyncStateInitialize(); localCodes = localCodes or {} end
    local changed = {}
    local _, indexes = catalogueIndex()
    for id in pairs(dirtyIDs) do
        local index = indexes[id]
        local code = index and currentCode(id)
        if code ~= nil and code ~= localCodes[index] then
            saved.revision = saved.revision + 1
            local row = {rev = saved.revision, id = id, state = code}
            saved.journal[#saved.journal + 1] = row
            changed[#changed + 1] = row
            localCodes[index] = code
        end
    end
    dirtyIDs = {}
    while #saved.journal > JOURNAL_LIMIT do
        local removed = table.remove(saved.journal, 1)
        saved.minRev = math.max(saved.minRev, removed.rev)
    end
    saved.snapshot, saved.catalogueHash = encodeCodes(localCodes), hash
    return changed
end

function ns.SyncStateMarkDirty(id)
    if ns.GuideInteger(id, 2147483647) and id > 0 then dirtyIDs[id] = true end
end

function ns.SyncStateRefreshActive(previous, current)
    for id in pairs(previous or {}) do ns.SyncStateMarkDirty(id) end
    for id in pairs(current or {}) do ns.SyncStateMarkDirty(id) end
end

function ns.SyncStateRecord(id)
    ns.SyncStateMarkDirty(id)
end

function ns.SyncStateRevision()
    local saved = stateStore()
    return saved and saved.revision or 0
end

function ns.SyncStateJournalSince(revision)
    local saved = stateStore()
    if not saved then return nil end
    if not ns.GuideInteger(revision, 2147483647) or revision < saved.minRev then return nil end
    local rows = {}
    for _, row in ipairs(saved.journal) do if row.rev > revision then rows[#rows + 1] = row end end
    return rows
end

function ns.SyncStateCurrentCodes(ids)
    ids = ids or catalogueIndex()
    local codes = {}
    for index, id in ipairs(ids) do codes[index] = currentCode(id) end
    return codes
end

function ns.SyncStateEncodeScope(ids)
    return encodeCodes(ns.SyncStateCurrentCodes(ids))
end

function ns.SyncStateScopeHash(ids)
    local hash = 0
    for _, id in ipairs(ids or {}) do
        local value = tostring(id) .. ","
        for index = 1, #value do hash = (hash * 31 + string.byte(value, index)) % 2147483647 end
    end
    return tostring(hash)
end

function ns.SyncStatePeer(key)
    return peerRecord(key)
end

function ns.SyncStateAttachPeer(key)
    applyPeerState(key, peerRecord(key))
end

function ns.SyncStateSavePeer(key)
    persistPeer(key, ns.members and ns.members[key])
end

function ns.SyncStateApplyFull(key, revision, payload)
    local ids, _, hash = catalogueIndex()
    local codes = ids and decodeCodes(payload, #ids)
    if not codes or not ns.GuideInteger(revision, 2147483647) then return false, "invalid full state" end
    local member = ns.members[key] or {}; ns.members[key] = member
    if revision < (member.receivedRev or 0) then return false, "old full state" end
    member.state, member.stateHash, member.receivedRev = payload, hash, revision
    persistPeer(key, member)
    applyPeerState(key, peerRecord(key))
    if member.scopeState and revision >= (member.scopeState.revision or 0) then member.scopeState = nil end
    return true
end

function ns.SyncStateApplyDelta(key, revision, updates)
    local ids, indexes, hash = catalogueIndex()
    local member = ns.members[key] or {}; ns.members[key] = member
    if member.stateHash ~= hash or not member.state then return false, "delta without matching baseline" end
    -- A large journal tail may span several U packets with the same revision.
    -- Accept each packet until the sender's hello acknowledges the revision.
    if revision < (member.receivedRev or 0) then return false, "old state delta" end
    local codes = decodeCodes(member.state, #ids)
    if not codes then return false, "invalid saved state" end
    for _, update in ipairs(updates) do
        local index = indexes[update.id]
        if not index or not ns.GuideInteger(update.state, 3) then return false, "invalid state delta entry" end
        codes[index] = update.state
    end
    member.state, member.stateHash, member.receivedRev = encodeCodes(codes), hash, revision
    persistPeer(key, member)
    applyPeerState(key, peerRecord(key))
    if member.scopeState and revision >= (member.scopeState.revision or 0) then member.scopeState = nil end
    return true
end

function ns.SyncStateApplyScope(key, revision, hash, ids, payload)
    if ns.SyncStateScopeHash(ids) ~= tostring(hash) then return false, "scope hash mismatch" end
    local codes = decodeCodes(payload, #ids)
    if not codes then return false, "invalid scope state" end
    local member = ns.members[key] or {}; ns.members[key] = member
    local states = {}
    for index, id in ipairs(ids) do states[id] = codes[index] end
    member.scopeState = {revision = revision, hash = tostring(hash), ids = ids, states = states}
    ns.SyncStateSavePeer(key)
    return true
end

function ns.SyncStateForQuest(key, id)
    local member = ns.members and ns.members[key]
    local scope = member and member.scopeState
    if scope and scope.states and scope.states[id] ~= nil then return scope.states[id] end
    local ids, indexes, hash = catalogueIndex()
    if not ids or not member or member.stateHash ~= hash or not member.state then return nil end
    local codes = decodeCodes(member.state, #ids)
    return codes and indexes[id] and codes[indexes[id]] or nil
end

function ns.SyncStatePeerHello(key, hash, revision, acknowledged, level, classID, scopeHash)
    local member = ns.members[key] or {}; ns.members[key] = member
    if not member.state and ns.SyncStateAttachPeer then ns.SyncStateAttachPeer(key); member = ns.members[key] or member end
    member.stateHashFromPeer = hash
    member.stateRevisionFromPeer = revision
    member.stateAck = acknowledged
    member.stateScopeHashFromPeer = scopeHash
    member.catalogueMismatch = hash ~= ns.SyncStateCatalogueHash()
    if acknowledged and member.sentRev and acknowledged >= member.sentRev and member.sentHash == hash then
        member._stateQueuePending = nil
    end
    if ns.GuideInteger(level, 255) and level > 0 then
        member.profile = member.profile or {}
        member.profile.level, member.profile.classID = level, ns.GuideInteger(classID, 255) and classID or 0
    end
    ns.SyncStateSavePeer(key)
end

local function queueMessage(message, lane)
    return ns.QueueMessage and ns.QueueMessage(message, lane) == true
end

function ns.SyncStateSendScope(ids)
    if type(ids) ~= "table" or #ids == 0 or #ids > 512 then return false end
    local payload = ns.SyncStateEncodeScope(ids)
    if not payload then return false end
    local message = table.concat({"1", "Z", ns.SyncStateRevision(), ns.SyncStateScopeHash(ids), payload}, "|")
    if #message > 255 then return false end
    return queueMessage(message, "now")
end

function ns.SyncStateSendPeer(key)
    local ids, _, hash = catalogueIndex()
    local member = ns.members and ns.members[key]
    local saved = stateStore()
    if not ids or not member or not saved or member.catalogueMismatch or member.stateHashFromPeer ~= hash then return false end
    local scope = ns.PartyPlanCurrentScope and ns.PartyPlanCurrentScope() or {}
    if #scope > 512 then local bounded = {}; for index = 1, 512 do bounded[index] = scope[index] end; scope = bounded end
    if #scope > 0 then ns.SyncStateSendScope(scope) end
    local acknowledged = member.stateAck
    if acknowledged and acknowledged >= saved.revision and member.sentHash == hash then return true end
    if member._stateQueuePending and member.sentHash == hash then return true end
    local updates = ns.SyncStateJournalSince(acknowledged)
    if updates == nil or not member.sentHash or member.sentHash ~= hash then
        local payload = saved.snapshot or encodeCodes(localCodes)
        if not payload then return false end
        local chunkSize, total = 225, math.ceil(#payload / 225)
        local messages = {}
        for part = 1, total do
            local chunk = string.sub(payload, (part - 1) * chunkSize + 1, part * chunkSize)
            local message = table.concat({"1", "B", saved.revision, part, total, chunk}, "|")
            if #message > 255 then return false end
            messages[#messages + 1] = message
        end
        if not ns.QueueMessages or not ns.QueueMessages(messages, "background") then return false end
        member.sentRev, member.sentHash = saved.revision, hash
        member._stateQueuePending = true
        ns.syncStats.lastFullSendMessages = total
        ns.syncStats.lastFullSendRevision = saved.revision
        ns.SyncStateSavePeer(key)
        return true
    end
    if #updates == 0 then return true end
    local latest = {}
    for _, row in ipairs(updates) do latest[row.id] = row.state end
    local changedIDs = {}
    for id in pairs(latest) do changedIDs[#changedIDs + 1] = id end
    table.sort(changedIDs)
    local header = "1|U|" .. saved.revision .. "|"
    local payload, messages, count = {}, {}, 0
    local function flush()
        if #payload == 0 then return true end
        local message = header .. table.concat(payload, ",")
        if #message > 255 then return false end
        messages[#messages + 1] = message
        payload, count = {}, 0
        return true
    end
    for _, id in ipairs(changedIDs) do
        local item = tostring(id) .. ":" .. latest[id]
        local size = #item + (#payload > 0 and 1 or 0)
        if count >= 25 or #header + #table.concat(payload, ",") + size > 255 then
            if not flush() then return false end
        end
        payload[#payload + 1], count = item, count + 1
    end
    if not flush() then return false end
    if not ns.QueueMessages or not ns.QueueMessages(messages, "now") then return false end
    member.sentRev, member.sentHash = saved.revision, hash
    member._stateQueuePending = true
    ns.SyncStateSavePeer(key)
    return true
end

function ns.SyncStateSendCurrent()
    ns.SyncStateScan()
    for _, key in ipairs(ns.partyNames or {}) do ns.SyncStateSendPeer(key) end
    local saved = stateStore()
    if saved then
        local now = type(GetTime) == "function" and GetTime() or 0
        if not lastPersistAt or now - lastPersistAt >= 60 then
            ns.SyncStatePersistAll()
            lastPersistAt = now
        end
    end
end

function ns.ReceiveSyncStateMessage(message, sender)
    local revision, part, total, payload = string.match(message, "^1|B|(%d+)|(%d+)|(%d+)|(.*)$")
    if revision then
        revision, part, total = tonumber(revision), tonumber(part), tonumber(total)
        if #tostring(revision) > 10 or not ns.GuideInteger(revision, 2147483647)
            or not ns.GuideInteger(part, 16) or not ns.GuideInteger(total, 16)
            or part < 1 or total < 1 or part > total or #payload > 225
            or not string.match(payload, "^[A-Za-z0-9+/]*=?=?$") then return true, false, "invalid full state header" end
        local member = ns.members[sender]
        if not member or member.catalogueMismatch then return true, false, "full state catalogue mismatch" end
        local accepted, complete, reason = ns.SyncStateAssembly(sender, revision, part, total, payload)
        if not accepted then return true, false, reason end
        return true, true, nil, complete
    end
    revision, payload = string.match(message, "^1|U|(%d+)|(.*)$")
    if revision then
        revision = tonumber(revision)
        if not ns.GuideInteger(revision, 2147483647) or #payload == 0 then return true, false, "invalid state delta header" end
        local updates, seen = {}, {}
        for row in string.gmatch(payload .. ",", "(.-),") do
            local id, state = string.match(row, "^(%d+):([0-3])$")
            id, state = tonumber(id), tonumber(state)
            if not ns.GuideInteger(id, 2147483647) or id <= 0 or not state or state > 3 or seen[id]
                or #updates >= 25 then return true, false, "invalid state delta entry" end
            updates[#updates + 1], seen[id] = {id = id, state = state}, true
        end
        if table.concat((function() local rows = {}; for _, row in ipairs(updates) do rows[#rows + 1] = row.id .. ":" .. row.state end; return rows end)(), ",") ~= payload then
            return true, false, "noncanonical state delta"
        end
        local accepted, reason = ns.SyncStateApplyDelta(sender, revision, updates)
        return true, accepted, reason
    end
    local scopeRevision, scopeHash, scopePayload = string.match(message, "^1|Z|(%d+)|(%d+)|(.*)$")
    if scopeRevision then
        scopeRevision = tonumber(scopeRevision)
        if not ns.GuideInteger(scopeRevision, 2147483647) or #scopeHash > 10 or #scopePayload > 180
            or not string.match(scopeHash, "^%d+$") or not string.match(scopePayload, "^[A-Za-z0-9+/]*=?=?$") then
            return true, false, "invalid scoped state header"
        end
        local member = ns.members[sender] or {}; ns.members[sender] = member
        local scope = member and member.partyPlanScope
        if not scope and ns.PartyPlanCurrentScope then
            local localIDs = ns.PartyPlanCurrentScope()
            if ns.SyncStateScopeHash(localIDs) == scopeHash then
                scope = {hash = scopeHash, revision = scopeRevision, ids = localIDs}
                member.partyPlanScope = scope
            end
        end
        if not scope or tostring(scope.hash) ~= scopeHash then
            member.pendingScopeState = {revision = scopeRevision, hash = scopeHash, payload = scopePayload}
            return true, true
        end
        local accepted, reason = ns.SyncStateApplyScope(sender, scopeRevision, scopeHash, scope.ids, scopePayload)
        return true, accepted, reason
    end
    return false
end

function ns.SyncStateApplyPendingScope(key, ids, hash)
    local member = ns.members and ns.members[key]
    local pending = member and member.pendingScopeState
    if not pending or tostring(hash) ~= pending.hash then return false end
    member.pendingScopeState = nil
    return ns.SyncStateApplyScope(key, pending.revision, pending.hash, ids, pending.payload)
end

function ns.SyncStateAssembly(key, revision, part, total, payload)
    local bucket = fullAssembly[key]
    if bucket and revision < bucket.revision then return false, "old full state" end
    if not bucket or revision > bucket.revision then bucket = {revision = revision, total = total, parts = {}, count = 0}; fullAssembly[key] = bucket end
    if bucket.total ~= total then return false, "inconsistent full state part count" end
    if bucket.parts[part] then
        if bucket.parts[part] == payload then return true, false end
        return false, "conflicting duplicate full state part"
    end
    bucket.parts[part], bucket.count = payload, bucket.count + 1
    if bucket.count < total then return true, false end
    local chunks = {}
    for index = 1, total do if not bucket.parts[index] then return false, "missing full state part" end; chunks[index] = bucket.parts[index] end
    fullAssembly[key] = nil
    local accepted, reason = ns.SyncStateApplyFull(key, revision, table.concat(chunks))
    return accepted, accepted, reason
end

function ns.SyncStatePersistAll()
    for key, member in pairs(ns.members or {}) do persistPeer(key, member) end
    return true
end

function ns.ResetSyncStateTraffic()
    for _, member in pairs(ns.members or {}) do
        member._stateQueuePending, member.sentRev, member.sentHash = nil, nil, nil
    end
end
