local addonName, ns = ...

-- First party-plan stage: exchange bounded quest-history digests and show
-- differences in the existing party tracker. Plan routing stays local until
-- all members have a matching, validated scope and digest.
local alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
local alphabetIndex = {}
for index = 1, #alphabet do alphabetIndex[string.sub(alphabet, index, index)] = index - 1 end
local scopeRevision, digestRevision = 0, 0
local lastScopeHash, lastDigestSignature
local scopeAssemblies, digestAssemblies = {}, {}
local cachedScopeSource, cachedScope = nil, nil
local cachedLocalSnapshot

local function hashIDs(ids)
    local hash = 0
    for _, id in ipairs(ids) do
        local value = tostring(id) .. ","
        for index = 1, #value do hash = (hash * 31 + string.byte(value, index)) % 2147483647 end
    end
    return tostring(hash)
end

local function catalogueLoaded()
    return type(ns.catalogue) == "table" and type(rawget(ns.catalogue, "quests")) == "table"
end

local function currentScope()
    local roots = {}
    local guide = ns.routeSelection
    if guide and guide.records then
        for _, record in ipairs(guide.records) do if ns.GuideInteger(record.id) and record.id > 0 then roots[#roots + 1] = record.id end end
    else
        for id in pairs(ns.active or {}) do if ns.GuideInteger(id) and id > 0 then roots[#roots + 1] = id end end
    end
    table.sort(roots)
    local learningRevision = ns.char and ns.char.questLearning and ns.char.questLearning.revision or 0
    local signature = table.concat(roots, ",") .. ":" .. tostring(catalogueLoaded()) .. ":" .. tostring(learningRevision)
    if signature == cachedScopeSource and cachedScope then return cachedScope end
    local ids, seen, ordered = {}, {}, {}
    local function add(id, depth)
        if not ns.GuideInteger(id) or id <= 0 or seen[id] or #ordered >= 512 then return end
        seen[id], ids[id] = true, true
        ordered[#ordered + 1] = id
        if catalogueLoaded() and (depth or 0) < 24 and ns.CataloguePrerequisiteIDs then
            for _, previous in ipairs(ns.CataloguePrerequisiteIDs(id)) do add(previous, (depth or 0) + 1) end
        end
        local quest = catalogueLoaded() and ns.CatalogueQuest and ns.CatalogueQuest(id)
        for _, previous in ipairs(quest and quest.series or {}) do add(previous, (depth or 0) + 1) end
    end
    if guide and guide.records then
        for _, id in ipairs(roots) do add(id, 0) end
    else
        for _, id in ipairs(roots) do add(id, 0) end
    end
    table.sort(ordered)
    cachedScopeSource, cachedScope = signature, ordered
    return ordered
end

local function questState(id)
    if ns.active and ns.active[id] then return 2 end
    local completed = ns.Completed and ns.Completed(id)
    if completed == true then return 3 end
    if completed == false then return 1 end
    return 0
end

local function packStates(states, offers, skipped, pins)
    local out, buffer, bitCount = {}, 0, 0
    for index, state in ipairs(states) do
        local value = state + (offers[index] and 4 or 0) + (skipped[index] and 8 or 0) + (pins[index] and 16 or 0)
        buffer, bitCount = buffer + value * (2 ^ bitCount), bitCount + 5
        while bitCount >= 6 do
            local digit = buffer % 64
            out[#out + 1] = string.sub(alphabet, digit + 1, digit + 1)
            buffer, bitCount = math.floor(buffer / 64), bitCount - 6
        end
    end
    if bitCount > 0 then out[#out + 1] = string.sub(alphabet, buffer + 1, buffer + 1) end
    return table.concat(out)
end

local function captureStates(ids)
    local states, offers, skipped, pins = {}, {}, {}, {}
    for index, id in ipairs(ids) do
        states[index] = questState(id)
        local quest = catalogueLoaded() and ns.CatalogueQuest and ns.CatalogueQuest(id)
        offers[index] = quest and quest.prerequisitesUnverified == true
            and ns.ObservedPickupAvailable and ns.ObservedPickupAvailable(id) == true or false
        skipped[index] = ns.GuideQuestSkipped and ns.GuideQuestSkipped(id) or false
        pins[index] = ns.PartyPlanPinned and ns.PartyPlanPinned(id) or false
    end
    return states, offers, skipped, pins
end

local function encodeStates(ids)
    return packStates(captureStates(ids))
end

local function localSnapshot(ids)
    local states, offers, skipped, pins = captureStates(ids)
    return {hash = hashIDs(ids), ids = ids, states = states, offers = offers, skipped = skipped, pins = pins,
        payload = packStates(states, offers, skipped, pins)}
end

local function decodeStates(payload, count)
    if type(payload) ~= "string" or #payload ~= math.ceil(count * 5 / 6) then return nil end
    local states, offers, skipped, pins = {}, {}, {}, {}
    local buffer, bitCount, index = 0, 0, 1
    for offset = 1, #payload do
        local digit = alphabetIndex[string.sub(payload, offset, offset)]
        if digit == nil then return nil end
        buffer, bitCount = buffer + digit * (2 ^ bitCount), bitCount + 6
        while bitCount >= 5 and index <= count do
            local value = buffer % 32
            buffer, bitCount = math.floor(buffer / 32), bitCount - 5
            states[index], offers[index] = value % 4, math.floor(value / 4) % 2 == 1
            skipped[index], pins[index] = math.floor(value / 8) % 2 == 1, math.floor(value / 16) % 2 == 1
            index = index + 1
        end
    end
    return states, offers, skipped, pins
end

local function scopeForGuide()
    return currentScope()
end

function ns.ResetPartyPlanTraffic()
    lastScopeHash, lastDigestSignature = nil, nil
    scopeAssemblies, digestAssemblies = {}, {}
    cachedScopeSource, cachedScope, cachedLocalSnapshot = nil, nil, nil
    for _, member in pairs(ns.members or {}) do member.partyPlan = nil end
end

function ns.ResetPartyPlanPeer(sender)
    scopeAssemblies[sender], digestAssemblies[sender] = nil, nil
    local member = ns.members and ns.members[sender]
    if member then member.partyPlan, member.partyPlanScope = nil, nil end
end

function ns.PartyPlanScopeHash(ids)
    return hashIDs(ids)
end

function ns.PartyPlanEncodeStates(ids)
    return encodeStates(ids)
end

function ns.PartyPlanDecodeStates(payload, count)
    return decodeStates(payload, count)
end

function ns.PartyPlanPinned(id)
    local pins = ns.char and ns.char.partyPlanPins
    return type(pins) == "table" and pins[id] == true or false
end

function ns.SetPartyPlanPinned(id, value)
    if not ns.GuideInteger(id) or id <= 0 or not ns.char then return false end
    ns.char.partyPlanPins = type(ns.char.partyPlanPins) == "table" and ns.char.partyPlanPins or {}
    ns.char.partyPlanPins[id] = value == true and true or nil
    if ns.ScheduleSync then ns.ScheduleSync() end
    return true
end

function ns.SendPartyPlanDigest(force)
    if not ns.PartyFeaturesEnabled or not ns.PartyFeaturesEnabled() or not ns.QueueMessage
        or not ns.syncReady or not ns.partyNames or #ns.partyNames == 0 then return false end
    local ids = scopeForGuide()
    if #ids == 0 then return false end
    local hash = hashIDs(ids)
    cachedLocalSnapshot = localSnapshot(ids)
    if hash ~= lastScopeHash or force then
        scopeRevision = scopeRevision + 1
        local total = math.max(1, math.ceil(#ids / 18))
        for part = 1, total do
            local chunk = {}
            for index = (part - 1) * 18 + 1, math.min(part * 18, #ids) do chunk[#chunk + 1] = tostring(ids[index]) end
            if not ns.QueueMessage(table.concat({"2", "C", scopeRevision, hash, part, total, table.concat(chunk, ",")}, "|")) then
                lastScopeHash = nil
                return false
            end
        end
        lastScopeHash = hash
    end
    local level = ns.profile and ns.GuideInteger(ns.profile.level, 255) and ns.profile.level or 0
    local payload = cachedLocalSnapshot.payload
    local signature = table.concat({hash, level, payload}, "|")
    if not force and signature == lastDigestSignature then return true end
    digestRevision = digestRevision + 1
    local total = math.max(1, math.ceil(#payload / 200))
    for part = 1, total do
        local chunk = string.sub(payload, (part - 1) * 200 + 1, part * 200)
        if not ns.QueueMessage(table.concat({"2", "S", digestRevision, hash, level, part, total, chunk}, "|")) then
            return false
        end
    end
    lastDigestSignature = signature
    return true
end

local function receiveScope(message, sender)
    local rev, hash, part, total, payload = string.match(message, "^2|C|(%d+)|(%d+)|(%d+)|(%d+)|(.*)$")
    rev, part, total = tonumber(rev), tonumber(part), tonumber(total)
    if not ns.GuideInteger(rev) or #tostring(rev) > 10 or not ns.GuideInteger(part, 32) or not ns.GuideInteger(total, 32)
        or part < 1 or total < 1 or part > total or not hash or #hash > 10 or not string.match(hash, "^%d+$") or #payload > 220 then
        return true, false, "invalid party-plan scope header"
    end
    local ids, seen = {}, {}
    if payload ~= "" and (not string.match(payload, "^%d[%d,]*%d$") or string.find(payload, ",,", 1, true)
        or string.sub(payload, 1, 1) == "," or string.sub(payload, -1) == ",") then
        return true, false, "invalid party-plan scope list"
    end
    for token in string.gmatch(payload, "[^,]+") do
        if not string.match(token, "^%d+$") or #token > 10 then return true, false, "invalid party-plan scope ID" end
        local id = tonumber(token)
        if not ns.GuideInteger(id) or id < 1 or id > 2147483647 or seen[id] then return true, false, "duplicate/invalid party-plan scope ID" end
        ids[#ids + 1], seen[id] = id, true
    end
    if #ids > 18 or (#payload == 0 and (part ~= 1 or total ~= 1)) then return true, false, "party-plan scope chunk bounds" end
    scopeAssemblies[sender] = scopeAssemblies[sender] or {}
    local bucket = scopeAssemblies[sender]
    if bucket.revision and rev < bucket.revision then return true, false, "old party-plan scope" end
    if not bucket.revision or rev > bucket.revision then bucket = {revision = rev, hash = hash, total = total, parts = {}, count = 0}; scopeAssemblies[sender] = bucket end
    if bucket.hash ~= hash or bucket.total ~= total or bucket.parts[part] then return true, false, "duplicate/inconsistent party-plan scope" end
    bucket.parts[part], bucket.count = ids, bucket.count + 1
    if bucket.count == total then
        local all, allSeen = {}, {}
        for index = 1, total do
            if not bucket.parts[index] then return true, false, "missing party-plan scope chunk" end
            for _, id in ipairs(bucket.parts[index]) do
                if allSeen[id] or #all >= 512 then return true, false, "party-plan scope limit" end
                allSeen[id] = true; all[#all + 1] = id
            end
        end
        table.sort(all)
        if hashIDs(all) ~= hash then return true, false, "party-plan scope hash mismatch" end
        ns.members[sender] = ns.members[sender] or {}
        ns.members[sender].partyPlanScope = {hash = hash, revision = rev, ids = all}
        ns.Refresh(true)
    end
    return true, true
end

local function receiveDigest(message, sender)
    local rev, hash, level, part, total, payload = string.match(message, "^2|S|(%d+)|(%d+)|(%d+)|(%d+)|(%d+)|(.*)$")
    rev, level, part, total = tonumber(rev), tonumber(level), tonumber(part), tonumber(total)
    if not ns.GuideInteger(rev) or #tostring(rev) > 10 or not ns.GuideInteger(level, 255) or not ns.GuideInteger(part, 4)
        or not ns.GuideInteger(total, 4) or part < 1 or total < 1 or part > total
        or not hash or #hash > 10 or not string.match(hash, "^%d+$") or #payload > 200
        or not string.match(payload, "^[A-Za-z0-9_%-]*$") then
        return true, false, "invalid party-plan digest header"
    end
    local scope = scopeAssemblies[sender]
    if not scope or not scope.revision or not ns.members[sender] or not ns.members[sender].partyPlanScope
        or ns.members[sender].partyPlanScope.hash ~= hash then return true, false, "party-plan digest before matching scope" end
    digestAssemblies[sender] = digestAssemblies[sender] or {}
    local bucket = digestAssemblies[sender]
    if bucket.revision and rev < bucket.revision then return true, false, "old party-plan digest" end
    if not bucket.revision or rev > bucket.revision then bucket = {revision = rev, hash = hash, level = level, total = total, parts = {}, count = 0}; digestAssemblies[sender] = bucket end
    if bucket.hash ~= hash or bucket.level ~= level or bucket.total ~= total or bucket.parts[part] then return true, false, "duplicate/inconsistent party-plan digest" end
    bucket.parts[part], bucket.count = payload, bucket.count + 1
    if bucket.count == total then
        local parts = {}
        for index = 1, total do if not bucket.parts[index] then return true, false, "missing party-plan digest chunk" end; parts[index] = bucket.parts[index] end
        local states, offers, skipped, pins = decodeStates(table.concat(parts), #ns.members[sender].partyPlanScope.ids)
        if not states then return true, false, "invalid party-plan state bits" end
        ns.members[sender].partyPlan = {hash = hash, revision = rev, level = level, states = states, offers = offers,
            skipped = skipped, pins = pins,
            ids = ns.members[sender].partyPlanScope.ids, receivedAt = ns.ReadPublic and ns.ReadPublic(GetTime) or 0}
        ns.Refresh(true)
    end
    return true, true
end

function ns.ReceivePartyPlanMessage(message, sender)
    if string.sub(message, 1, 4) == "2|C|" then return receiveScope(message, sender) end
    if string.sub(message, 1, 4) == "2|S|" then return receiveDigest(message, sender) end
    return false
end

local function partyPlanTitle(id)
    if ns.localTitles and ns.localTitles[id] then return ns.localTitles[id] end
    for _, record in ipairs(ns.routeSelection and ns.routeSelection.records or {}) do
        if record.id == id and record.title and record.title ~= "" then return record.title end
    end
    for _, name in ipairs(ns.partyNames or {}) do
        local member = ns.members[name]
        if member and member.titles and member.titles[id] then return member.titles[id] end
    end
    return "quest " .. tostring(id)
end

function ns.PartyPlanMissingLine()
    if not ns.PartyFeaturesEnabled or not ns.PartyFeaturesEnabled() or not ns.partyNames or #ns.partyNames == 0 then return nil end
    local ids = scopeForGuide()
    if #ids == 0 then return "Missing vs party: choose a guide to compare quest gaps." end
    local hash = hashIDs(ids)
    if not cachedLocalSnapshot or cachedLocalSnapshot.hash ~= hash then cachedLocalSnapshot = localSnapshot(ids) end
    local own = {}; for index, id in ipairs(ids) do own[id] = cachedLocalSnapshot.states[index] end
    local gaps, waiting, oldVersion = {}, false, false
    for _, name in ipairs(ns.partyNames) do
        local member = ns.members[name]
        local digest = member and member.partyPlan
        if member and member.planSupport == false then oldVersion, waiting = true, true
        elseif not digest or digest.hash ~= hash then waiting = true
        else
            for index, id in ipairs(ids) do
                local mine, theirs = own[id], digest.states[index]
                local mineSkipped = cachedLocalSnapshot.skipped[index]
                local theirsSkipped = digest.skipped and digest.skipped[index]
                if mine == 0 or theirs == 0 then waiting = true end
                if not mineSkipped and not theirsSkipped and mine == 2 and theirs == 1 then
                    gaps[#gaps + 1] = ns.MemberLabel(name) .. " lacks " .. partyPlanTitle(id)
                elseif not mineSkipped and not theirsSkipped and mine == 1 and theirs == 2 then
                    gaps[#gaps + 1] = "You lack " .. partyPlanTitle(id) .. " (" .. ns.MemberLabel(name) .. " has it)"
                end
                if #gaps >= 2 then break end
            end
        end
        if #gaps >= 2 then break end
    end
    if #gaps > 0 then return "Missing vs party: " .. table.concat(gaps, " · ") end
    if oldVersion then return "Missing vs party: update party addons to compare quest gaps." end
    if waiting then return "Missing vs party: waiting for matching quest data." end
    return "Missing vs party: no quest-log gaps in this guide."
end

function ns.PartyPlanDiagnostics(output)
    local scopes, digests = 0, 0
    for _, name in ipairs(ns.partyNames or {}) do
        local member = ns.members[name]
        if member and member.partyPlanScope then scopes = scopes + 1 end
        if member and member.partyPlan then digests = digests + 1 end
    end
    output("Party digest: " .. digests .. "/" .. tostring(#(ns.partyNames or {})) .. " fresh; " .. scopes .. " matching scopes received")
    output("Party digest scope size: " .. tostring(#scopeForGuide()) .. "/512 quests")
end
