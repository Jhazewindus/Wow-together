local addonName, namespace = ...
local ns = _G.WowTogetherModuleAPI
if not namespace.enabled then return end

local farms = {}
namespace.GoldFarms = farms
local prices, observations = namespace.GoldPrices, namespace.GoldObservations
local db = namespace.db
if type(db.gathering) ~= "table" then db.gathering = {} end
if type(db.farmSession) ~= "table" then db.farmSession = nil end

local LIMIT, MAX_POINTS, GATHER_POINTS_REQUIRED = 50, 24, 3
local DEFAULT_KILLS_PER_HOUR, DEFAULT_NODES_PER_HOUR = 120, 30
local candidates, candidateCount, lastError = {}, 0, nil
local refreshGeneration = 0
local activeSession, pendingSession = nil, nil

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end
local function positive(value)
    return ns.GuideInteger(value, 2147483647) and value > 0
end
local function safeText(value, max)
    return ns.Public(value) and type(value) == "string" and value ~= "" and #value <= max
end
local function clipped(value, max)
    value = tostring(value or "")
    return #value <= max and value or string.sub(value, 1, max - 1) .. "…"
end
local function now()
    local value = ns.ReadPublic(GetTime)
    return finite(value) and value or nil
end
local function level()
    local value = ns.ReadPublic(UnitLevel, "player")
    return ns.GuideInteger(value, 255) and math.max(1, value) or 1
end
local function profileMap()
    local map = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    return positive(map) and map or nil
end
local function price(itemID)
    if not prices or type(prices.Price) ~= "function" then return nil end
    local quote = prices.Price(itemID)
    if type(quote) ~= "table" or not positive(quote.copper) or not safeText(quote.source, 80) then return nil end
    return quote.copper, quote.source, quote.age
end
local function itemPrice(itemID)
    if not positive(itemID) then return nil end
    local copper, source = price(itemID)
    if not copper or not source then return nil end
    return copper, source
end
local function cleanSource(record, key)
    local source = record and record.sources and record.sources[key]
    return safeText(source, 180) and source or "source not supplied"
end
local function quantityValue(item)
    if not item then return nil end
    local low = item.minYield or item.minimumYield or item.minQuantity or item.minCount
    local high = item.maxYield or item.maximumYield or item.maxQuantity or item.maxCount
    local average = item.averageYield or item.expectedYield or item.expectedQuantity
    if finite(average) and average > 0 then return average, "sourced average yield" end
    if finite(low) and low > 0 and finite(high) and high >= low then
        return (low + high) / 2, "midpoint of sourced yield range"
    end
    if finite(item.quantity) and item.quantity > 0 then
        local source = type(item.source) == "string" and string.lower(item.source) or ""
        if string.find(source, "legacy", 1, true) or string.find(source, "cmangos", 1, true) then
            return item.quantity, "legacy minimum count (lower bound)"
        end
        return item.quantity, "sourced item quantity"
    end
    return nil
end
local function chanceValue(item)
    if not item then return nil end
    if finite(item.chance) and item.chance > 0 and item.chance <= 100 then
        return item.chance / 100, item.chanceSource or item.source or "sourced percent chance"
    end
    if finite(item.probability) and item.probability > 0 and item.probability <= 1 then
        return item.probability, item.chanceSource or item.source or "sourced probability"
    end
    return nil
end
local function estimateLoot(loot)
    local expected, assumptions, seen = 0, {}, 0
    for _, item in ipairs(loot or {}) do
        local itemID = item.itemID
        local unitPrice, source = itemPrice(itemID)
        local yield, yieldBasis = quantityValue(item)
        local chance, chanceBasis = chanceValue(item)
        if unitPrice and yield and chance then
            expected = expected + unitPrice * yield * chance
            assumptions[#assumptions + 1] = string.format("%g%% (%s) × %g (%s) × %dc (%s)",
                chance * 100, clipped(chanceBasis, 50), yield, clipped(yieldBasis, 50), unitPrice, clipped(source, 50))
            seen = seen + 1
        end
    end
    if seen == 0 then return nil end
    return expected, table.concat(assumptions, "; ")
end
local function mobPace(npcID)
    local state = db.observations
    local build = type(state) == "table" and ns.ReadPublic(function() local _, number = GetBuildInfo(); return number end)
    local mobs = build and state[build] and state[build].mobs
    local record = mobs and mobs[npcID]
    local size = ns.ReadPublic(GetNumGroupMembers)
    size = ns.GuideInteger(size, 40) and math.max(1, size) or 1
    local pace = record and record.pace and record.pace[size]
    if pace and finite(pace.seconds) and pace.seconds > 0 and ns.GuideInteger(pace.sampleSize, 100) and pace.sampleSize >= 2 then
        return 3600 / pace.seconds, string.format("%g kills/hour from %d observed intervals", 3600 / pace.seconds, pace.sampleSize)
    end
    return DEFAULT_KILLS_PER_HOUR, DEFAULT_KILLS_PER_HOUR .. " kills/hour assumed (one kill per 30 seconds)"
end
local function copyPoint(point, label, reason)
    if type(point) ~= "table" or not ns.GuideInteger(point.mapID, 1000000) or point.mapID < 1
        or not finite(point.x) or point.x < 0 or point.x > 1
        or not finite(point.y) or point.y < 0 or point.y > 1 then return nil end
    return {mapID = point.mapID, x = point.x, y = point.y,
        label = label or point.label or "Farm spot", reason = reason or point.reason or "Sourced or observed farm location."}
end
local function routePoints(candidate)
    local result = {}
    local function add(point, label, reason)
        local item = copyPoint(point, label, reason)
        if not item then return end
        for _, existing in ipairs(result) do
            if existing.mapID == item.mapID and math.abs(existing.x - item.x) < 0.001 and math.abs(existing.y - item.y) < 0.001 then return end
        end
        if #result < MAX_POINTS then result[#result + 1] = item end
    end
    for _, point in ipairs(candidate.points or {}) do
        add(point, point.label or candidate.name, point.reason or candidate.pointSource)
    end
    if candidate.kind == "gathering" and #result < GATHER_POINTS_REQUIRED then
        local sourceKind = candidate.sourceKind
        if not sourceKind and (candidate.profession == "Mining" or candidate.profession == "Herbalism") then
            sourceKind = "gather-node"
        elseif not sourceKind and candidate.profession == "Skinning" then sourceKind = "skinning" end
        local learned = sourceKind and db.gathering[candidate.profession .. ":" .. candidate.mapID .. ":" .. sourceKind]
        for _, point in ipairs(learned and learned.points or {}) do
            local matches = #candidate.loot == 0
            for _, yield in ipairs(candidate.loot or {}) do
                if point.items and point.items[yield.itemID] then matches = true; break end
            end
            if matches and point.count and point.count >= 1 then
                add(point, candidate.name, "Observed during your own gathering play.")
            end
        end
    end
    return result
end
local function rate(copper, seconds)
    if not finite(copper) or copper < 0 or not finite(seconds) or seconds <= 0 then return 0 end
    return copper * 3600 / seconds
end
local function setSessionCard()
    local session = activeSession
    if not session or type(ns.SetFarmSession) ~= "function" then return end
    local elapsed = math.max(1, (now() or session.startTime) - session.startTime)
    local actual = rate(session.copper, elapsed)
    local label = session.label
    if session.items > 0 then label = label .. " • " .. session.items .. " measured items" end
    local sources = {}
    for source, count in pairs(session.priceSources or {}) do sources[#sources + 1] = {source = source, count = count} end
    table.sort(sources, function(a,b) return a.source < b.source end)
    local sourceText = {}
    for _, item in ipairs(sources) do sourceText[#sourceText + 1] = item.count .. " at " .. item.source end
    local actualBasis = session.items > 0
        and (session.items .. " locally looted/gathered items over " .. math.floor(session.elapsed) .. " s; " .. table.concat(sourceText, ", "))
        or "No priced loot observed yet"
    local data = {label = clipped(label, 100), estimatedCopperPerHour = session.estimate,
        actualCopperPerHour = actual, startTime = session.startTime,
        estimatedBasis = clipped(session.estimateBasis, 100), actualBasis = clipped(actualBasis, 100)}
    local okay = ns.SetFarmSession("Gold", data)
    if okay and ns.RequestFarmSessionRefresh then ns.RequestFarmSessionRefresh("Gold") end
end
local function candidateHasItem(candidate, itemID)
    if not candidate.loot or #candidate.loot == 0 then return true end
    for _, item in ipairs(candidate.loot) do if item.itemID == itemID then return true end end
    return false
end
local function eventSourceKind(event)
    if event.profession == "Fishing" then return event.source == "fishing-pool" and "fishing-pool" or "open-water" end
    if event.profession == "Skinning" then return "skinning" end
    return "gather-node"
end
local function recordMeasured(itemID, quantity, kind, detail)
    if not activeSession or not positive(itemID) or not ns.GuideInteger(quantity, 1000000) or quantity < 1 then return end
    local candidate = activeSession.candidate
    if candidate.kind == "mob" then
        if kind ~= "mob" or detail ~= candidate.npcID or not candidateHasItem(candidate, itemID) then return end
    else
        if kind ~= "gathering" or detail.profession ~= candidate.profession
            or detail.mapID ~= candidate.mapID or not candidateHasItem(candidate, itemID)
            or candidate.sourceKind and eventSourceKind(detail) ~= candidate.sourceKind then return end
    end
    local stamp = now()
    if not stamp then return end
    local unitPrice, priceSource = itemPrice(itemID)
    if not unitPrice then activeSession.unpriced = activeSession.unpriced + quantity; return end
    activeSession.copper = activeSession.copper + unitPrice * quantity
    activeSession.items = activeSession.items + quantity
    activeSession.priceSources[priceSource] = (activeSession.priceSources[priceSource] or 0) + quantity
    activeSession.elapsed = math.max(0, stamp - activeSession.startTime)
    db.farmSession.copper = activeSession.copper
    db.farmSession.items = activeSession.items
    db.farmSession.elapsed = activeSession.elapsed
    setSessionCard()
end
function farms.RecordLoot(itemID, quantity, npcID)
    recordMeasured(itemID, quantity, "mob", npcID)
end

local function addLearnedPoint(event)
    if ns.Option("gold.recordLoot") ~= true or type(event) ~= "table"
        or not safeText(event.profession, 40) or not positive(event.mapID)
        or not finite(event.x) or event.x < 0 or event.x > 1 or not finite(event.y) or event.y < 0 or event.y > 1 then return end
    local sourceKind = event.source
    if event.profession == "Fishing" then
        sourceKind = sourceKind == "fishing-pool" and "fishing-pool" or "open-water"
    elseif event.profession == "Skinning" then sourceKind = "skinning"
    else sourceKind = "gather-node" end
    local key = event.profession .. ":" .. event.mapID .. ":" .. sourceKind
    local row = db.gathering[key]
    if not row then row = {points = {}, items = {}}; db.gathering[key] = row end
    local at = now() or 0
    local point
    for _, existing in ipairs(row.points) do
        if math.abs(existing.x - event.x) <= 0.015 and math.abs(existing.y - event.y) <= 0.015 then point = existing; break end
    end
    if not point then
        if #row.points >= 300 then table.remove(row.points, 1) end
        point = {mapID = event.mapID, x = event.x, y = event.y, count = 0, items = {}, firstSeen = at}
        row.points[#row.points + 1] = point
    end
    if not point.lastVisit or at - point.lastVisit >= 10 then point.count = point.count + 1; point.lastVisit = at end
    point.lastSeen = at
    local data = point.items[event.itemID] or {total = 0, count = 0}
    data.total = data.total + event.quantity; data.count = data.count + 1
    point.items[event.itemID] = data
    local itemData = row.items[event.itemID] or {total = 0, count = 0}
    itemData.total = itemData.total + event.quantity; itemData.count = itemData.count + 1
    row.items[event.itemID] = itemData
    if not row.lastHarvestAt or at - row.lastHarvestAt >= 5 then
        if row.lastHarvestAt and at > row.lastHarvestAt and at - row.lastHarvestAt <= 600 then
            row.harvestIntervals = row.harvestIntervals or {}
            row.harvestIntervals[#row.harvestIntervals + 1] = at - row.lastHarvestAt
            if #row.harvestIntervals > 20 then table.remove(row.harvestIntervals, 1) end
            if #row.harvestIntervals >= 3 then
                local sorted = {}
                for i, interval in ipairs(row.harvestIntervals) do sorted[i] = interval end
                table.sort(sorted)
                local middle = math.floor((#sorted + 1) / 2)
                row.harvestsPerHour = 3600 / sorted[middle]
                row.harvestSample = #sorted
            end
        end
        row.lastHarvestAt = at
    end
end
local observerRegistered = false
local function onGathered(event)
    addLearnedPoint(event)
    recordMeasured(event.itemID, event.quantity, "gathering", event)
end
if type(ns.RegisterGatheringObserver) == "function" then
    local okay = ns.RegisterGatheringObserver("Gold", onGathered)
    observerRegistered = okay == true
end

local function makeMob(record)
    local expectedPerKill, lootBasis = estimateLoot(record.loot)
    if not expectedPerKill or not positive(record.npcID) then return nil end
    local kills, paceBasis = mobPace(record.npcID)
    -- An assumed pace cannot outrun the spawns: a creature that stands in one
    -- place gives one kill per respawn, not one every thirty seconds. Without
    -- this a single named guard with a sure drop tops every list. Six minutes
    -- per spawn point is assumed; the player's own measured pace is not capped.
    local spawns = type(record.spawnPoints) == "table" and #record.spawnPoints or 0
    if string.find(paceBasis, "assumed", 1, true) then
        local cap = math.max(1, spawns) * 10
        if kills > cap then
            kills = cap
            paceBasis = cap .. " kills/hour assumed (" .. math.max(1, spawns) .. " spawn point" .. (spawns == 1 and "" or "s") .. ", one kill each per six minutes)"
        end
    end
    local copperPerHour = expectedPerKill * kills
    local name = safeText(record.name, 100) and record.name or ("NPC " .. record.npcID)
    local candidate = {kind = "mob", id = "mob:" .. record.npcID .. ":" .. record.mapID, name = name,
        zone = record.zoneName or record.zone or "Unknown zone", mapID = record.mapID,
        npcID = record.npcID, estimate = copperPerHour, expectedPerKill = expectedPerKill, pace = kills,
        paceAssumed = string.find(paceBasis, "assumed", 1, true) ~= nil,
        basis = "Legacy, unconfirmed; " .. paceBasis .. "; " .. lootBasis .. "; data: " .. cleanSource(record, "loot"),
        points = record.spawnPoints or {}, pointSource = cleanSource(record, "spawnPoints"),
        loot = record.loot, source = "farm prior", sample = 0}
    return candidate
end
local function gatheringYield(item, mapID, profession, sourceKind)
    local seededYield = quantityValue(item)
    local seededChance = chanceValue(item)
    local learned = sourceKind and db.gathering[profession .. ":" .. mapID .. ":" .. sourceKind]
    local sample = learned and learned.items and learned.items[item.itemID]
    if sample and sample.count and sample.count >= 3 and finite(sample.total) and sample.total > 0 then
        return sample.total / sample.count, seededChance or 1, "your " .. sample.count .. " observed yields"
    end
    if not seededYield or not seededChance then return nil end
    return seededYield, seededChance, "seeded " .. tostring(item.source or "yield source")
end
local function makeGathering(row, zone)
    local sourceKind = zone.sourceKind or zone.waterKind or row.sourceKind or row.waterKind
    if row.profession == "Mining" or row.profession == "Herbalism" then sourceKind = "gather-node" end
    if row.profession == "Skinning" then sourceKind = "skinning" end
    local expected, basis, hasData = 0, {}, false
    local loot = type(zone.loot) == "table" and #zone.loot > 0 and zone.loot or row.loot or {}
    for _, item in ipairs(loot) do
        local unitPrice, source = itemPrice(item.itemID)
        local yield, chance, yieldBasis = gatheringYield(item, zone.mapID, row.profession, sourceKind)
        if unitPrice and yield and chance then
            expected = expected + unitPrice * yield * chance
            basis[#basis + 1] = string.format("%g × %g%% × %dc (%s; %s; %s)", yield, chance * 100,
                unitPrice, clipped(source, 40), clipped(yieldBasis, 50), clipped(tostring(item.source or "source unavailable"), 50))
            hasData = true
        end
    end
    if not hasData then return nil end
    local candidatesPerHour, rateBasis = DEFAULT_NODES_PER_HOUR, DEFAULT_NODES_PER_HOUR .. " harvests/hour assumed (one every 2 minutes)"
    local localSamples = 0
    local learned = sourceKind and db.gathering[row.profession .. ":" .. zone.mapID .. ":" .. sourceKind]
    localSamples = learned and #learned.points or 0
    if learned and learned.harvestsPerHour and learned.harvestSample >= 3 then
        candidatesPerHour = learned.harvestsPerHour
        rateBasis = string.format("%g harvests/hour from %d observed intervals", candidatesPerHour, learned.harvestSample)
    end
    -- Third-party seed coordinates can help identify known zones, but a
    -- gathering loop is offered only after this character has observed enough
    -- real node/catch positions in play.
    local points = {}
    local zoneName = zone.name or ("Map " .. zone.mapID)
    local nodeKey = string.gsub(row.node, "[^%w:_%-]", "_")
    return {kind = "gathering", id = "gather:" .. row.professionID .. ":" .. zone.mapID .. ":" .. nodeKey,
        name = row.node, profession = row.profession, professionID = row.professionID,
        zone = zoneName, mapID = zone.mapID, estimate = expected * candidatesPerHour,
        basis = rateBasis .. "; " .. table.concat(basis, "; "), points = points,
        pointSource = zone.pointsSource or row.pointsSource or "No coordinates supplied", sourceKind = sourceKind,
        loot = row.loot, source = "gathering data", sample = localSamples}
end
local function sortCandidates()
    table.sort(candidates, function(a,b)
        if a.estimate ~= b.estimate then return a.estimate > b.estimate end
        return a.id < b.id
    end)
    candidateCount = #candidates
    local cards = {}
    for index = 1, math.min(3, #candidates) do
        local row = candidates[index]
        local key = row.id
        local pointRows = routePoints(row)
        local routeText = #pointRows >= 3 and "Start a measured walking loop." or "Zone-level suggestion; no route coordinates yet."
        cards[#cards + 1] = {key = clipped(row.id, 64), title = clipped(row.name .. " — " .. row.zone, 100),
            detail = clipped(string.format("Estimate %.1fg/hour. Basis: %s. %s", row.estimate / 10000, row.basis, routeText), 350),
            priority = math.max(1, 100 - index), action = function() farms.Start(key) end}
    end
    if type(ns.PublishGoldFunction) == "function" then ns.PublishGoldFunction("Suggestions", function() return cards end) end
end
local function acceptMobRows(rows)
    for _, record in ipairs(rows or {}) do
        local candidate = makeMob(record)
        if candidate then candidates[#candidates + 1] = candidate end
    end
    sortCandidates()
end
local function acceptGatherRows(rows)
    for _, row in ipairs(rows or {}) do
        for _, zone in ipairs(row.zones or {}) do
            if positive(zone.mapID) then
                local candidate = makeGathering(row, zone)
                if candidate then candidates[#candidates + 1] = candidate end
            end
        end
    end
    sortCandidates()
end
function farms.RefreshSearches()
    refreshGeneration = refreshGeneration + 1
    local generation = refreshGeneration
    candidates, candidateCount = {}, 0
    lastError = nil
    local current = level()
    local prior, priorReason
    if type(ns.FarmPriorSearch) == "function" then
        prior, priorReason = ns.FarmPriorSearch({minLevel = math.max(1, current - 5),
            maxLevel = math.min(255, current + 5), limit = LIMIT}, function(rows)
                if generation == refreshGeneration then acceptMobRows(rows) end
            end)
    else priorReason = "FarmPriorSearch unavailable" end
    if not prior then lastError = tostring(priorReason or "FarmPriorSearch failed") end
    local gathering, gatheringReason
    if type(ns.GatheringFarmSearch) == "function" then
        gathering, gatheringReason = ns.GatheringFarmSearch({limit = LIMIT}, function(rows)
            if generation == refreshGeneration then acceptGatherRows(rows) end
        end)
    else gatheringReason = "GatheringFarmSearch unavailable" end
    if not gathering then lastError = lastError and (lastError .. "; " .. tostring(gatheringReason or "gathering search failed"))
        or tostring(gatheringReason or "GatheringFarmSearch failed") end
    return prior == true or gathering == true
end
if type(ns.On) == "function" then
    ns.On("PLAYER_LEVEL_UP", farms.RefreshSearches)
    ns.On("SKILL_LINES_CHANGED", farms.RefreshSearches)
    ns.On("ZONE_CHANGED_NEW_AREA", farms.RefreshSearches)
end
local function beginSession(candidate, start)
    activeSession = {id = candidate.id, label = candidate.name .. " in " .. candidate.zone,
        estimate = candidate.estimate, estimateBasis = candidate.basis,
        startTime = start, copper = 0, items = 0, unpriced = 0, elapsed = 0,
        candidate = candidate, priceSources = {}}
    db.farmSession = {id = candidate.id, label = activeSession.label, estimate = activeSession.estimate,
        estimateBasis = activeSession.estimateBasis, startTime = activeSession.startTime,
        copper = 0, items = 0}
    local accepted, reason = ns.SetFarmSession("Gold", {label = activeSession.label,
        estimatedCopperPerHour = activeSession.estimate, actualCopperPerHour = 0,
        startTime = activeSession.startTime, estimatedBasis = activeSession.estimateBasis,
        actualBasis = "No priced loot observed yet"})
    if not accepted then
        activeSession = nil; db.farmSession = nil
        ns.Print("Gold: cannot open the session card: " .. tostring(reason))
        if type(ns.StopModuleLoop) == "function" then ns.StopModuleLoop("Gold") end
        return false
    end
    setSessionCard()
    return true
end
function farms.Start(key)
    local candidate
    for _, row in ipairs(candidates) do if row.id == key then candidate = row; break end end
    if not candidate then return false, "Farm suggestion expired; refresh suggestions." end
    local start = now()
    if not start then return false, "Game clock unavailable." end
    local function stopThis(reason)
        if pendingSession and pendingSession.id == key then pendingSession = nil end
        if activeSession and activeSession.id == key then farms.Stop(reason) end
    end
    if candidate.kind == "gathering" then
        local pointRows = routePoints(candidate)
        if #pointRows >= GATHER_POINTS_REQUIRED then
            pendingSession = {id = key, candidate = candidate, start = start}
            local ok, reason = ns.StartModuleLoop("Gold", {title = candidate.name .. " in " .. candidate.zone,
                points = pointRows, onStop = stopThis, onStart = function() beginSession(candidate, now() or start); pendingSession = nil end})
            if not ok then pendingSession = nil; ns.Print("Gold: " .. tostring(reason)); return false end
        else
            ns.Print("Gold: gathering session started in " .. candidate.zone .. "; follow the zone suggestion and keep moving between nodes.")
            return beginSession(candidate, start)
        end
    else
        local pointRows = routePoints(candidate)
        if #pointRows < 3 then ns.Print("Gold: no sourced route points are available for " .. candidate.name .. "."); return false end
        pendingSession = {id = key, candidate = candidate, start = start}
        local ok, reason = ns.StartModuleLoop("Gold", {title = candidate.name .. " — " .. candidate.zone,
            points = pointRows, onStop = stopThis, onStart = function() beginSession(candidate, now() or start); pendingSession = nil end})
        if not ok then pendingSession = nil; ns.Print("Gold: " .. tostring(reason)); return false end
    end
    return pendingSession == nil and activeSession ~= nil
end
function farms.Stop(reason)
    if not activeSession then return false end
    activeSession.stopReason = safeText(reason, 120) and reason or "stopped"
    db.farmSession, pendingSession = nil, nil
    activeSession = nil
    if type(ns.SetFarmSession) == "function" then ns.SetFarmSession("Gold", nil) end
    if type(ns.StopModuleLoop) == "function" then ns.StopModuleLoop("Gold") end
    return true
end
-- What the farm tracker shows beside its own figures: the suggested farm in
-- progress and what it was estimated to pay.
function farms.ActiveSession()
    if not activeSession then return nil end
    return {label = activeSession.label, estimate = activeSession.estimate, estimateBasis = activeSession.estimateBasis}
end
-- How often a farm pays out: kills or harvests an hour, and whether that is
-- the player's own measured pace or an assumption.
local function paceOf(row)
    if row.kind == "mob" then
        if row.pace then return row.pace, row.paceAssumed == true, "kills" end
        local rate, basis = mobPace(row.npcID)
        return rate, string.find(basis, "assumed", 1, true) ~= nil, "kills"
    end
    local learned = row.sourceKind and db.gathering[row.profession .. ":" .. row.mapID .. ":" .. row.sourceKind]
    if learned and learned.harvestsPerHour and (learned.harvestSample or 0) >= 3 then return learned.harvestsPerHour, false, "harvests" end
    return DEFAULT_NODES_PER_HOUR, true, "harvests"
end

-- What a farm's estimate is made of, item by item: the chance, the count and
-- the price of each, biggest earner first.
local function breakdown(row)
    local items, total = {}, 0
    for _, item in ipairs(row.loot or {}) do
        local unitPrice, source = itemPrice(item.itemID)
        local yield, chance
        if row.kind == "mob" then yield, chance = quantityValue(item), chanceValue(item)
        else yield, chance = gatheringYield(item, row.mapID, row.profession, row.sourceKind) end
        if yield and chance then
            local each = unitPrice or 0
            local worth = each * yield * chance
            total = total + worth
            items[#items + 1] = {itemID = item.itemID, chance = chance, yield = yield, each = unitPrice,
                auction = source == "core auction quote", worth = worth}
        end
    end
    table.sort(items, function(a, b)
        if a.worth ~= b.worth then return a.worth > b.worth end
        return a.itemID < b.itemID
    end)
    return items, total
end

-- The best suggestions, for the gold page: one per creature or node (the
-- data lists some in several zones), each with what its estimate rests on.
-- The kinds of farm, in the order they are offered: killing first, then the
-- gathering professions.
farms.CATEGORIES = {"Killing", "Mining", "Herbalism", "Skinning", "Fishing"}
local function categoryOf(row)
    if row.kind == "mob" then return "Killing" end
    return row.profession
end

-- How many different farms there are of each kind.
function farms.Categories()
    local counts, seen = {}, {}
    for _, name in ipairs(farms.CATEGORIES) do counts[name] = 0 end
    for _, row in ipairs(candidates) do
        local category = categoryOf(row)
        local key = tostring(category) .. "\0" .. tostring(row.name)
        if category and counts[category] and not seen[key] then seen[key] = true; counts[category] = counts[category] + 1 end
    end
    return counts
end

-- `category` narrows the list to one kind ("Killing", "Mining", ...); nil is the best of everything.
function farms.Suggestions(limit, category)
    -- The data places a creature in every zone its spawn points touch, so one
    -- that lives on a border is listed two or three times. Its home is the
    -- zone with the most of its spawn points.
    local home, pool = {}, {}
    for _, row in ipairs(candidates) do
        if category == nil or categoryOf(row) == category then pool[#pool + 1] = row end
    end
    for _, row in ipairs(pool) do
        local known = home[row.name]
        local points = type(row.points) == "table" and #row.points or 0
        if not known or points > known.points or (points == known.points and row.estimate > known.row.estimate) then
            home[row.name] = {row = row, points = points}
        end
    end
    local list, taken = {}, {}
    for _, row in ipairs(pool) do
        if #list >= (limit or 3) then break end
        if not taken[row.name] and home[row.name].row == row then
            taken[row.name] = true
            local items, total = breakdown(row)
            local rate, assumed, unit = paceOf(row)
            local top, auction, vendor = {}, 0, 0
            for index, item in ipairs(items) do
                if item.each then if item.auction then auction = auction + 1 else vendor = vendor + 1 end end
                if index <= 4 and item.worth > 0 then
                    top[#top + 1] = {itemID = item.itemID, chance = item.chance, each = item.each, auction = item.auction,
                        share = total > 0 and item.worth / total or 0}
                end
            end
            list[#list + 1] = {key = row.id, name = row.name, zone = row.zone, kind = row.kind, profession = row.profession,
                category = categoryOf(row),
                estimate = row.estimate, routable = #routePoints(row) >= 3,
                active = activeSession ~= nil and activeSession.id == row.id,
                pace = rate, paceAssumed = assumed, paceUnit = unit, measured = (row.sample or 0) > 0 or not assumed,
                top = top, others = math.max(0, #items - #top), auctionPriced = auction, vendorPriced = vendor}
        end
    end
    return list, lastError
end

-- The items whose price decides which farm is best: what the farms near the
-- player drop, weighted by how much of it an hour of farming would bring.
-- Rare world drops (a fiftieth of a percent each) are left out: they do not
-- move an estimate and there are hundreds of them.
function farms.ScanItems(limit)
    local weight = {}
    for _, row in ipairs(candidates) do
        local rate = paceOf(row)
        for _, item in ipairs((breakdown(row))) do
            local perHour = item.chance * item.yield * rate
            if perHour >= 0.5 and (not weight[item.itemID] or perHour > weight[item.itemID]) then weight[item.itemID] = perHour end
        end
    end
    local ids = {}
    for itemID in pairs(weight) do ids[#ids + 1] = itemID end
    table.sort(ids, function(a, b)
        if weight[a] ~= weight[b] then return weight[a] > weight[b] end
        return a < b
    end)
    while #ids > (limit or 300) do table.remove(ids) end
    return ids
end

-- Re-rank after new prices came in.
function farms.PricesChanged() farms.RefreshSearches() end

function farms.Probe(output)
    output("Gold farms: " .. candidateCount .. " candidates; " .. (observerRegistered and "gathering observer available" or "gathering observer unavailable")
        .. "; last error " .. clipped(lastError or "none", 180) .. ".")
end

function farms.Render(page)
    local tracker = namespace.GoldTracker
    if tracker and type(tracker.RenderPage) == "function" then
        if page.goldStatus then page.goldStatus:Hide() end
        return tracker.RenderPage(page)
    end
    page.goldStatus = page.goldStatus or page:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    page.goldStatus:ClearAllPoints()
    page.goldStatus:SetPoint("TOPLEFT", 16, -16)
    page.goldStatus:SetWidth(480)
    page.goldStatus:SetJustifyH("LEFT")
    local lines = {"Gold farm suggestions are on the Play page.",
        "Candidates: " .. candidateCount .. "; saved auction quotes are preferred over vendor price.",
        "No item is bought or sold automatically."}
    if activeSession then
        lines[#lines + 1] = "Active: " .. activeSession.label
        lines[#lines + 1] = string.format("Estimate %.1fg/hour; measured %.1fg/hour from %d priced items.",
            activeSession.estimate / 10000, rate(activeSession.copper, math.max(1, activeSession.elapsed)) / 10000, activeSession.items)
        lines[#lines + 1] = activeSession.estimateBasis
    end
    if lastError then lines[#lines + 1] = "Search: " .. clipped(lastError, 200) end
    page.goldStatus:SetText(table.concat(lines, "\n"))
    page:SetHeight(math.max(250, 42 + #lines * 18))
end

if type(ns.PublishGoldFunction) == "function" then
    ns.PublishGoldFunction("Price", function(itemID)
        local quote = prices and prices.Price and prices.Price(itemID)
        if quote then return quote.copper, quote.source == "core auction quote" end
    end)
end
farms.RefreshSearches()
