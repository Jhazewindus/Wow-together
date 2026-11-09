local addonName, namespace = ...
local ns = _G.WowTogetherModuleAPI
if not namespace.enabled then return end

local observations = {}
namespace.GoldObservations = observations
local db = namespace.db
if type(db.observations) ~= "table" then db.observations = {} end
if type(db.observerID) ~= "string" or not string.match(db.observerID, "^%x%x%x%x%x%x%x%x$") then
    db.observerID = string.format("%08x", math.random(0, 2147483646))
end

local MAX_MOBS, MAX_DROPS, MAX_NODES, MAX_RUNS = 2000, 60, 3000, 50
local MAX_SEEN, MAX_PEERS = 4000, 40
local seenDeaths, seenLooted, seenItems, recentDeaths = {}, {}, {}, {}
local knownGUIDs, seenOrder, seenNext = {}, {}, 1
local lastKill, pendingGather, currentRun = {}, nil, nil
local function trackGUID(guid)
    if knownGUIDs[guid] then return end
    local old = seenOrder[seenNext]
    if old then
        knownGUIDs[old], seenDeaths[old], seenLooted[old], seenItems[old] = nil, nil, nil, nil
    end
    knownGUIDs[guid], seenOrder[seenNext] = true, guid
    seenNext = seenNext % MAX_SEEN + 1
end
local function clock()
    local value = ns.ReadPublic(GetTime)
    return type(value) == "number" and value == value and value or nil
end
local function wallTime()
    local value = ns.ReadPublic(GetServerTime)
    return ns.GuideInteger(value, 9000000000) and value or nil
end
local function buildKey()
    local build = ns.ReadPublic(function() local _, number = GetBuildInfo(); return number end)
    return type(build) == "string" and build or "unknown"
end
local build = buildKey()
if type(db.observations[build]) ~= "table" then
    db.observations[build] = {mobs = {}, nodes = {}, runs = {}, peers = {}}
end
local state = db.observations[build]
for _, key in ipairs({"mobs", "nodes", "runs", "peers"}) do
    if type(state[key]) ~= "table" then state[key] = {} end
end
local mobCount = 0
for _ in pairs(state.mobs) do mobCount = mobCount + 1 end

local function validID(id)
    return ns.GuideInteger(id, 2147483647) and id > 0
end
local function npcID(guid)
    if type(guid) ~= "string" then return nil end
    local id = string.match(guid, "^Creature%-%d+%-%d+%-%d+%-%d+%-(%d+)%-[%x]+$")
    id = tonumber(id)
    return validID(id) and id or nil
end
local function objectID(guid)
    if type(guid) ~= "string" then return nil end
    local id = string.match(guid, "^GameObject%-%d+%-%d+%-%d+%-%d+%-(%d+)%-[%x]+$")
    id = tonumber(id)
    return validID(id) and id or nil
end
local function itemID(link)
    local id = type(link) == "string" and tonumber(string.match(link, "item:(%d+)"))
    return validID(id) and id or nil
end
local function partySize()
    local count = ns.ReadPublic(GetNumGroupMembers)
    return ns.GuideInteger(count, 40) and math.max(1, count) or 1
end
local function point()
    local map = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not validID(map) then return nil end
    local position = C_Map and ns.ReadPublic(C_Map.GetPlayerMapPosition, map, "player")
    if not position then return nil end
    local x, y
    if type(position.GetXY) == "function" then x, y = ns.ReadPublic(position.GetXY, position)
    else x, y = position.x, position.y end
    if not ns.Public(x) or not ns.Public(y) or type(x) ~= "number" or type(y) ~= "number"
        or x < 0 or x > 1 or y < 0 or y > 1 then return nil end
    return {mapID = map, x = x, y = y}
end
local function mob(id)
    if not validID(id) then return nil end
    local record = state.mobs[id]
    if record then return record end
    if mobCount >= MAX_MOBS then return nil end
    record = {looted = 0, drops = {}, pace = {}, source = "local observation", sampleSize = 0}
    state.mobs[id] = record; mobCount = mobCount + 1
    return record
end
local function median(samples)
    if #samples == 0 then return nil end
    local sorted = {}
    for index, value in ipairs(samples) do sorted[index] = value end
    table.sort(sorted)
    local middle = math.floor((#sorted + 1) / 2)
    return #sorted % 2 == 1 and sorted[middle] or (sorted[middle] + sorted[middle + 1]) / 2
end

function observations.RecordKill(guid, at)
    local id = npcID(guid)
    at = at or clock()
    if ns.Option("gold.recordLoot") ~= true or not id or not at or seenDeaths[guid] then return false end
    trackGUID(guid)
    seenDeaths[guid] = at
    recentDeaths[#recentDeaths + 1] = {guid = guid, npcID = id, time = at}
    while #recentDeaths > 20 or recentDeaths[1] and at - recentDeaths[1].time > 10 do
        table.remove(recentDeaths, 1)
    end
    local record = mob(id)
    if not record then return false end
    local size = partySize()
    local pace = record.pace[size]
    if not pace then pace = {intervals = {}, source = "local observation", sampleSize = 0}; record.pace[size] = pace end
    local previous = lastKill[id .. ":" .. size]
    if previous and at > previous and at - previous <= 300 then
        local intervals = pace.intervals
        intervals[#intervals + 1] = at - previous
        if #intervals > 20 then table.remove(intervals, 1) end
        pace.seconds = median(intervals)
        pace.sampleSize = #intervals
    end
    lastKill[id .. ":" .. size] = at
    return true
end

local function recordDrop(guid, id, count, source)
    local npc = npcID(guid)
    local record = npc and mob(npc)
    if not record then return false end
    trackGUID(guid)
    if not seenLooted[guid] then
        seenLooted[guid] = true
        record.looted = record.looted + 1
        record.sampleSize = record.looted
        local location = point()
        if location then
            record.mapID, record.x, record.y = location.mapID, location.x, location.y
        end
        record.partySize = partySize()
        for _, drop in pairs(record.drops) do drop.sampleSize = record.looted end
    end
    if not validID(id) or not ns.GuideInteger(count, 1000000) or count <= 0 then return true end
    local drop = record.drops[id]
    if not drop then
        local distinct = 0
        for _ in pairs(record.drops) do distinct = distinct + 1 end
        if distinct >= MAX_DROPS then return false end
        drop = {n = 0, total = 0, source = source, sampleSize = record.looted}
        record.drops[id] = drop
    end
    seenItems[guid] = seenItems[guid] or {}
    local previous = seenItems[guid][id] or 0
    if count <= previous then return true, false end
    if previous == 0 then drop.n = drop.n + 1 end
    drop.total = drop.total + count - previous
    seenItems[guid][id] = count
    drop.sampleSize = record.looted
    record.revision = (record.revision or 0) + 1
    return true, true
end

local function gatherKind(spellID)
    local info = C_Spell and ns.ReadPublic(C_Spell.GetSpellInfo, spellID)
    local name = type(info) == "table" and info.name or ns.ReadPublic(GetSpellInfo, spellID)
    if not ns.Public(name) or type(name) ~= "string" then return nil end
    name = string.lower(name)
    if string.find(name, "mining", 1, true) then return "mining" end
    if string.find(name, "herbalism", 1, true) or string.find(name, "herb gathering", 1, true) then return "herbalism" end
    if string.find(name, "skinning", 1, true) then return "skinning" end
end
function observations.RecordGatherCast(unit, _, spellID)
    if unit ~= "player" or not validID(spellID) or ns.Option("gold.recordLoot") ~= true then return end
    local kind = gatherKind(spellID)
    if not kind then return end
    pendingGather = {kind = kind, spellID = spellID, at = clock(), point = point()}
end
local function recordNode(guid, id, count)
    local pending, now = pendingGather, clock()
    if not pending or not pending.at or not now or now - pending.at > 12 or not pending.point then return false end
    local location = pending.point
    local nodeID = objectID(guid)
    if not nodeID and pending.kind ~= "skinning" then return false end
    if pending.sourceGUID == guid and pending.node then
        local node = pending.node
        local item = node.items[id] or {total = 0, source = "local observation", sampleSize = node.visits}
        node.items[id] = item; item.total = item.total + count
        return true
    end
    local map = state.nodes[location.mapID]
    if not map then map = {}; state.nodes[location.mapID] = map end
    local node
    for _, candidate in ipairs(map) do
        if candidate.objectID == nodeID and candidate.kind == pending.kind
            and math.abs(candidate.x - location.x) <= 0.02 and math.abs(candidate.y - location.y) <= 0.02 then
            node = candidate; break
        end
    end
    if not node then
        if #map >= MAX_NODES then return false end
        node = {objectID = nodeID, spellID = pending.spellID, kind = pending.kind,
            x = location.x, y = location.y, mapID = location.mapID,
            visits = 0, items = {}, source = "local observation", sampleSize = 0}
        map[#map + 1] = node
    end
    node.visits = node.visits + 1
    node.sampleSize = node.visits
    for _, item in pairs(node.items) do item.sampleSize = node.visits end
    node.items[id] = node.items[id] or {total = 0, source = "local observation", sampleSize = node.visits}
    node.items[id].total = node.items[id].total + count
    pending.sourceGUID, pending.node = guid, node
    return true
end

local function finishRun(now)
    local run = currentRun
    currentRun = nil
    if not run or not now or now <= run.start then return end
    local saved = state.runs[run.id]
    if not saved then saved = {}; state.runs[run.id] = saved end
    saved[#saved + 1] = {durationSeconds = now - run.start,
        lootCopper = run.lootCopper, pricedItems = run.pricedItems, totalItems = run.totalItems,
        memberCount = run.memberCount, source = "local observation", sampleSize = 1,
        observedAt = wallTime()}
    if #saved > MAX_RUNS then table.remove(saved, 1) end
end
function observations.CheckInstance()
    local inside, kind = ns.ReadPublic(IsInInstance)
    local id = inside == true and kind == "party" and ns.ReadPublic(function()
        local _, _, _, _, _, _, _, instanceID = GetInstanceInfo()
        return instanceID
    end) or nil
    if not validID(id) then id = nil end
    local now = clock()
    if currentRun and currentRun.id ~= id then finishRun(now) end
    if id and not currentRun and now then
        currentRun = {id = id, start = now, lootCopper = 0,
            pricedItems = 0, totalItems = 0, memberCount = partySize()}
    end
end
local function valueRunItem(id, count)
    if not currentRun then return end
    currentRun.totalItems = currentRun.totalItems + count
    local prices = namespace.GoldPrices
    local quote = prices and prices.Price and prices.Price(id)
    if quote then
        currentRun.lootCopper = currentRun.lootCopper + quote.copper * count
        currentRun.pricedItems = currentRun.pricedItems + count
    end
end
function observations.RecordLoot(guid, id, count, source)
    if ns.Option("gold.recordLoot") ~= true or not validID(id)
        or not ns.GuideInteger(count, 1000000) or count <= 0 then return false end
    local node = recordNode(guid, id, count)
    local drop, credited
    if not node then drop, credited = recordDrop(guid, id, count, source or "local observation") end
    if node or credited then valueRunItem(id, count) end
    return node or drop or false
end
function observations.LootOpened()
    if ns.Option("gold.recordLoot") ~= true then return end
    local slots = ns.ReadPublic(GetNumLootItems)
    if not ns.GuideInteger(slots, 100) then return end
    if slots == 0 then
        local guid = ns.ReadPublic(GetLootSourceInfo, 1)
        if npcID(guid) then recordDrop(guid, nil, nil, "local observation") end
        return
    end
    for slot = 1, slots do
        local guid = ns.ReadPublic(GetLootSourceInfo, slot)
        local link = ns.ReadPublic(GetLootSlotLink, slot)
        local id = itemID(link)
        local count = ns.ReadPublic(function(index)
            local _, _, amount = GetLootSlotInfo(index)
            return amount
        end, slot)
        if id and guid then observations.RecordLoot(guid, id, count or 1, "local observation") end
    end
end
function observations.PartyLoot(message)
    if ns.Option("gold.recordLoot") ~= true or not ns.Public(message) or type(message) ~= "string" then return end
    local id = itemID(message)
    if not id then return end
    local count = tonumber(string.match(message, "|h|r%s*[xX](%d+)")) or 1
    local now = clock()
    for index = #recentDeaths, 1, -1 do
        local death = recentDeaths[index]
        if now and now - death.time <= 5 then
            observations.RecordLoot(death.guid, id, count, "party-attributed observation")
            return
        end
    end
end
function observations.CombatLog()
    local subevent, guid = ns.ReadPublic(function()
        local _, event, _, _, _, _, _, destGUID = CombatLogGetCurrentEventInfo()
        return event, destGUID
    end)
    if subevent ~= "UNIT_DIED" and subevent ~= "PARTY_KILL" then return end
    observations.RecordKill(guid)
end

-- M packets contain only an anonymous observer token and aggregate counts.
-- Core validates the addon prefix, normal party, and sender before dispatch.
function observations.DropPacket(npc, item)
    local record = state.mobs[npc]
    local drop = record and record.drops[item]
    if not drop then return nil end
    local packet = table.concat({"1", "M", "D", db.observerID, npc, item,
        record.looted, drop.n, drop.total, record.revision or 0}, "|")
    return #packet <= 255 and packet or nil
end
function observations.ReceiveM(message)
    if ns.Option("gold.shareObservations") ~= true or type(message) ~= "string" or #message > 255 then
        return false, "Gold sharing disabled or packet too long"
    end
    local observer, npc, item, looted, n, total, revision = string.match(message,
        "^1|M|D|(%x%x%x%x%x%x%x%x)|(%d+)|(%d+)|(%d+)|(%d+)|(%d+)|(%d+)$")
    npc, item, looted, n, total, revision = tonumber(npc), tonumber(item), tonumber(looted),
        tonumber(n), tonumber(total), tonumber(revision)
    if not observer or observer == db.observerID or not validID(npc) or not validID(item)
        or not ns.GuideInteger(looted, 10000000) or looted < 1
        or not ns.GuideInteger(n, looted) or n < 1
        or not ns.GuideInteger(total, 10000000) or total < n
        or not ns.GuideInteger(revision, 10000000) then return false, "Invalid Gold drop packet" end
    local peer = state.peers[observer]
    if not peer then
        local count = 0
        for _ in pairs(state.peers) do count = count + 1 end
        if count >= MAX_PEERS then return false, "Gold peer cap reached" end
        peer = {}; state.peers[observer] = peer
    end
    local mob = peer[npc]
    if not mob then
        local count = 0
        for _ in pairs(peer) do count = count + 1 end
        if count >= MAX_MOBS then return false, "Gold NPC cap reached" end
        mob = {drops = {}, source = "party observation"}; peer[npc] = mob
    end
    local previous = mob.drops[item]
    if previous and previous.revision >= revision then return false, "Old Gold drop packet" end
    if not previous then
        local count = 0
        for _ in pairs(mob.drops) do count = count + 1 end
        if count >= MAX_DROPS then return false, "Gold drop cap reached" end
    end
    mob.looted, mob.sampleSize = looted, looted
    mob.drops[item] = {n = n, total = total, revision = revision,
        source = "party observation", sampleSize = looted, observerCount = 1}
    return true
end

function observations.ExportEvents()
    local events = {}
    local function add(event)
        if #events < 500 then events[#events + 1] = event end
    end
    for npc, record in pairs(state.mobs) do
        local pace = {}
        for size, sample in pairs(record.pace) do
            if sample.seconds then
                pace[#pace + 1] = {partySize = size, seconds = sample.seconds,
                    sampleSize = sample.sampleSize, provenance = sample.source}
            end
        end
        for item, drop in pairs(record.drops) do
            add({event = "gold-drop", build = build, npcID = npc, itemID = item,
                looted = record.looted, n = drop.n, total = drop.total,
                mapID = record.mapID, x = record.x, y = record.y,
                partySize = record.partySize, pace = pace,
                observerID = db.observerID, sampleSize = record.looted,
                provenance = drop.source})
        end
    end
    for mapID, nodes in pairs(state.nodes) do
        for _, node in ipairs(nodes) do
            local items = {}
            for itemID, item in pairs(node.items) do
                items[#items + 1] = {itemID = itemID, total = item.total,
                    sampleSize = item.sampleSize, provenance = item.source}
            end
            add({event = "gold-node", build = build, mapID = mapID, objectID = node.objectID,
                spellID = node.spellID, kind = node.kind, x = node.x, y = node.y,
                items = items, observerID = db.observerID,
                sampleSize = node.visits, provenance = node.source})
        end
    end
    for dungeon, runs in pairs(state.runs) do
        for index, run in ipairs(runs) do
            add({event = "gold-run", build = build, dungeonID = dungeon,
                runIndex = index, observedAt = run.observedAt,
                durationSeconds = run.durationSeconds, lootCopper = run.lootCopper,
                pricedItems = run.pricedItems, totalItems = run.totalItems,
                memberCount = run.memberCount, observerID = db.observerID,
                sampleSize = 1, provenance = run.source})
        end
    end
    return events
end
function observations.Probe(output)
    local nodes, runs = 0, 0
    for _, map in pairs(state.nodes) do nodes = nodes + #map end
    for _, group in pairs(state.runs) do runs = runs + #group end
    output("Gold observations: " .. mobCount .. " NPCs, " .. nodes .. " nodes, " .. runs
        .. " dungeon runs; M receive ready; outgoing background lane unavailable.")
end

ns.On("COMBAT_LOG_EVENT_UNFILTERED", observations.CombatLog)
ns.On("LOOT_OPENED", observations.LootOpened)
ns.On("CHAT_MSG_LOOT", observations.PartyLoot)
ns.On("UNIT_SPELLCAST_SUCCEEDED", observations.RecordGatherCast)
ns.On("PLAYER_ENTERING_WORLD", observations.CheckInstance)
ns.On("ZONE_CHANGED_NEW_AREA", observations.CheckInstance)
ns.RegisterSyncKind("M", observations.ReceiveM)
ns.ResearchExportHook(observations.ExportEvents)
observations.CheckInstance()
