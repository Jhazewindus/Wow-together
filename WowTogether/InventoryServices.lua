local addonName, ns = ...

-- Optional, personal vendor visits. Only actual merchant interactions establish
-- capabilities/locations; inn and trainer locations do not imply a repair shop.
-- No purchase, sale or repair is performed, and the quest plan is never edited.
local RANGE, NEAR, DETOUR = 350 / 0.9144, 150 / 0.9144, 150
local snapshot, cached, displayed, pendingRead, merchantOpen, initialized
local revision, reads = 0, 0
local manaClasses = {[2] = true, [5] = true, [7] = true, [8] = true, [9] = true, [11] = true}
-- Common Classic food/water, including conjured supplies. Names, prices and
-- current stock come from the client. Other consumables are not guessed.
local supplies = {}
for _, row in ipairs({
    {"food", 1, 117, 4540, 4536, 4604, 2070, 787, 5349},
    {"food", 5, 2287, 4541, 4537, 4605, 4145, 4592, 1113},
    {"food", 15, 3770, 4542, 4538, 4606, 422, 4593, 1114},
    {"food", 25, 3771, 4544, 4539, 4607, 1707, 4594, 1487},
    {"food", 35, 4599, 4601, 4602, 4608, 3927, 6887, 8075},
    {"food", 45, 8952, 8950, 8953, 8948, 8932, 8957, 8076},
    {"food", 55, 22895}, {"drink", 1, 159, 5350},
    {"drink", 5, 1179, 2288}, {"drink", 15, 1205, 2136},
    {"drink", 25, 1708, 3772}, {"drink", 35, 1645, 8077},
    {"drink", 45, 8766, 8078}, {"drink", 55, 8079}}) do
    for index = 3, #row do supplies[row[index]] = {kind = row[1], level = row[2]} end
end

local function personal()
    return ns.db and ns.db.inventoryServiceCharacters and ns.db.inventoryServiceCharacters[ns.self]
end
local function scope()
    local _, build = ns.ReadPublic(GetBuildInfo)
    local faction, realm = ns.SafeTitle(ns.profile and ns.profile.faction), ns.SafeTitle(ns.ReadPublic(GetRealmName))
    if not build or not ns.SafeTitle(build) or not realm or faction ~= "Horde" and faction ~= "Alliance" then return end
    return realm .. ":" .. build .. ":" .. faction
end
local function vendors(create)
    local key = scope()
    if not key or not ns.db or not ns.db.inventoryServiceVendors then return end
    local state = ns.db.inventoryServiceVendors[key]
    if not state and create then
        local count, oldest, age = 0, nil, nil
        for id, old in pairs(ns.db.inventoryServiceVendors) do
            count = count + 1
            local sequence = type(old) == "table" and old.sequence or 0
            if not age or sequence < age then oldest, age = id, sequence end
        end
        if count >= 8 then ns.db.inventoryServiceVendors[oldest] = nil end
        state = {places = {}, sequence = 0}; ns.db.inventoryServiceVendors[key] = state
    end
    return state, key
end
local function usable(id)
    local item, level = supplies[id], ns.profile and ns.profile.level
    if not item or not ns.GuideInteger(level, 255) then return end
    -- Do not restock obsolete tiers merely because their food is edible.
    local tier = math.max(1, math.floor((level + 5) / 10) * 10 - 5)
    if item.level <= level and item.level >= tier then return item.kind end
end

function ns.ReadServiceInventory()
    if not initialized or not ns.Option("inventoryServices") then return end
    local result = {food = 0, drink = 0, free = 0, slots = 0}
    local container = C_Container or {}
    local slotsFn = container.GetContainerNumSlots or GetContainerNumSlots
    local freeFn = container.GetContainerNumFreeSlots or GetContainerNumFreeSlots
    local itemFn = container.GetContainerItemInfo
    local itemIDFn = container.GetContainerItemID or GetContainerItemID
    local bagKnown = type(slotsFn) == "function" and type(freeFn) == "function"
    local supplyKnown = ns.GuideInteger(ns.profile and ns.profile.level, 255) and ns.profile.level > 0
    if type(slotsFn) ~= "function" then supplyKnown = false end
    for bag = 0, 4 do -- Backpack + equipped ordinary/specialty bags; no bank/reagent bag.
        local count = ns.ReadPublic(slotsFn, bag)
        if not ns.GuideInteger(count, 200) then bagKnown, supplyKnown = false, false
        elseif count > 0 then
            local free, family = ns.ReadPublic(freeFn, bag)
            if not ns.GuideInteger(free, count) or not ns.GuideInteger(family) then bagKnown = false
            elseif family == 0 then result.free, result.slots = result.free + free, result.slots + count end
            if type(itemFn) ~= "function" and type(GetContainerItemInfo) ~= "function" then supplyKnown = false end
            for slot = 1, count do
                local id, amount
                if type(itemFn) == "function" then
                    local okay, info = pcall(itemFn, bag, slot)
                    if not okay or not ns.Public(info) then supplyKnown = false
                    elseif info ~= nil then
                        if type(info) ~= "table" or not ns.GuideInteger(info.itemID) or not ns.GuideInteger(info.stackCount, 100000) then supplyKnown = false
                        else id, amount = info.itemID, info.stackCount end
                    elseif type(itemIDFn) == "function" then
                        local valid, itemID = pcall(itemIDFn, bag, slot)
                        if not valid or not ns.Public(itemID) or itemID ~= nil then supplyKnown = false end
                    end
                elseif type(GetContainerItemInfo) == "function" then
                    local okay, _, stack = pcall(GetContainerItemInfo, bag, slot)
                    local known, itemID = false, nil
                    if type(itemIDFn) == "function" then known, itemID = pcall(itemIDFn, bag, slot) end
                    if not okay or not known or not ns.Public(stack) or not ns.Public(itemID) then supplyKnown = false
                    else id, amount = itemID, stack end
                end
                if id ~= nil then
                    if not ns.GuideInteger(id) or not ns.GuideInteger(amount, 100000) then supplyKnown = false
                    else
                        local kind = usable(id)
                        if kind then result[kind] = result[kind] + amount end
                    end
                end
            end
        end
    end
    if not bagKnown or result.slots == 0 then result.free, result.slots = nil, nil end
    if not supplyKnown then result.food, result.drink = nil, nil end
    local durability, private = nil, false
    for slot = 1, 18 do
        local okay, current, maximum = false, nil, nil
        if type(GetInventoryItemDurability) == "function" then okay, current, maximum = pcall(GetInventoryItemDurability, slot) end
        if not okay or not ns.Public(current) or not ns.Public(maximum) then private = true
        elseif current ~= nil or maximum ~= nil then
            if ns.GuideInteger(current, 100000) and ns.GuideInteger(maximum, 100000) and maximum > 0 and current <= maximum then
                durability = math.min(durability or 1, current / maximum)
            else private = true end
        end
    end
    result.durability = not private and durability or nil
    snapshot, cached, revision, reads = result, nil, revision + 1, reads + 1
    local state = personal()
    if state then
        if result.free and result.free > 4 then state.dismissed.bags = nil end
        if result.durability and result.durability > 0.25 then state.dismissed.repair = nil end
        for _, kind in ipairs({"food", "drink"}) do
            if result[kind] and result[kind] > 5 then state.dismissed[kind] = nil end
        end
    end
    ns.serviceInventory = result -- Diagnostic snapshot; no peer packets.
end

function ns.QueueServiceInventory()
    if not initialized or not ns.Option("inventoryServices") or pendingRead then return end
    pendingRead = true
    local function update()
        pendingRead = false
        if not ns.Option("inventoryServices") then return end
        local hadPending = personal() and personal().pending
        ns.ReadServiceInventory()
        if merchantOpen then ns.RecordServiceVendor() end
        if ns.navigation then ns.UpdateNavigation() end
        if hadPending and ns.DrawRoute then ns.DrawRoute(nil, true) end
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0.2, update) else update() end
end

local function stockAt(slot)
    local link = ns.SafeTitle(ns.ReadPublic(GetMerchantItemLink, slot))
    local id = link and tonumber(string.match(link, "item:(%d+)"))
    if not id or not supplies[id] then return end
    local info = C_MerchantFrame and ns.ReadPublic(C_MerchantFrame.GetItemInfo, slot)
    if type(info) == "table" then
        local extended = info.hasExtendedCost
        if not ns.Public(extended) then return id end
        if extended == nil then extended = info.extendedCost end
        if not ns.Public(info.numAvailable) or not ns.Public(extended) or type(extended) ~= "boolean"
            or not ns.Public(info.isPurchasable) or type(info.numAvailable) ~= "number" then return id end
        return id, info.numAvailable ~= 0 and not extended and info.isPurchasable ~= false
    end
    if type(GetMerchantItemInfo) ~= "function" then return end
    local okay, _, _, _, _, available, _, extended = pcall(GetMerchantItemInfo, slot)
    if okay and ns.Public(available) and ns.Public(extended) and type(available) == "number"
        and type(extended) == "boolean" then return id, available ~= 0 and extended == false end
    return id
end

function ns.RecordServiceVendor()
    if not initialized or not ns.Option("inventoryServices") or not merchantOpen or ns.RouteInCombat() then return end
    local guid, name = ns.SafeTitle(ns.ReadPublic(UnitGUID, "npc")), ns.SafeTitle(ns.ReadPublic(UnitName, "npc"))
    local id = guid and tonumber(string.match(guid, "^Creature%-%d+%-%d+%-%d+%-%d+%-(%d+)%-"))
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local position = ns.GuideInteger(mapID) and ns.PlayerPoint(mapID)
    if not id or not name or not ns.ValidTravelPoint(position) then return end
    local state = vendors(true)
    if not state then return end
    local key = mapID .. ":" .. id
    local old, count = state.places[key], 0
    for _ in pairs(state.places) do count = count + 1 end
    if not old and count >= 256 then
        local oldest, age
        for k, value in pairs(state.places) do
            if not age or value.sequence < age then oldest, age = k, value.sequence end
        end
        state.places[oldest] = nil
    end
    local place = {key = key, npcID = id, name = name, mapID = mapID, x = position.x, y = position.y,
        items = old and old.items or {}, repair = old and old.repair}
    local repair = ns.ReadPublic(CanMerchantRepair)
    if type(repair) == "boolean" then place.repair = repair end
    local stock = ns.ReadPublic(GetMerchantNumItems)
    if ns.GuideInteger(stock, 200) then
        -- Unresolved item links retain earlier confirmed stock until it loads.
        for slot = 1, stock do
            local itemID, sold = stockAt(slot)
            if itemID and type(sold) == "boolean" then place.items[itemID] = sold or nil end
        end
        if stock == 0 then place.items = {} end
    end
    ns.db.inventoryServiceSequence = (ns.db.inventoryServiceSequence or 0) + 1
    place.sequence, state.sequence = ns.db.inventoryServiceSequence, ns.db.inventoryServiceSequence
    state.places[key], cached = place, nil
end

local function enabled()
    return ns.Option("inventoryServices") and ns.routeSelection and ns.routeSelection.mode ~= "profession"
        and ns.SafeTitle(ns.routeSelection.key) and snapshot ~= nil
end
local function safeTime()
    return not ns.routePaused and not ns.guideScanning and not ns.routePlanning and not ns.navigationPreview
        and not ns.RouteInCombat() and ns.ReadPublic(UnitOnTaxi, "player") == false and ns.ReadPublic(UnitIsGhost, "player") == false
end
local function needs(pending)
    local state, result = personal(), {}
    if not state or not snapshot then return result end
    local permitted = pending or {bags = true, repair = true, food = true, drink = true}
    if permitted.bags and not state.dismissed.bags and (snapshot.free and snapshot.free <= 4 or pending and snapshot.free == nil) then result.bags = true end
    if permitted.repair and not state.dismissed.repair and (snapshot.durability and snapshot.durability <= 0.25 or pending and snapshot.durability == nil) then result.repair = true end
    if ns.Option("restockSupplies") then
        local threshold = pending and ns.Option("supplyTarget") - 1 or 5
        if permitted.food and not state.dismissed.food and (snapshot.food and snapshot.food <= threshold or pending and snapshot.food == nil) then result.food = true end
        if permitted.drink and not state.dismissed.drink and manaClasses[ns.profile and ns.profile.classID]
            and (snapshot.drink and snapshot.drink <= threshold or pending and snapshot.drink == nil) then result.drink = true end
    end
    return result
end
local function matching(place, needed)
    local matched, weight = {}, 0
    if needed.repair and place.repair == true then matched.repair, weight = true, weight + 4 end
    if needed.bags then matched.bags, weight = true, weight + 3 end
    for id in pairs(place.items or {}) do
        local kind = usable(id)
        if kind and needed[kind] and not matched[kind] then matched[kind], weight = true, weight + 1 end
    end
    return matched, weight
end
local function reason(matched)
    local parts = {}
    if matched.bags then parts[#parts + 1] = snapshot.free and (snapshot.free .. " bag slots free") or "Check bag space" end
    if matched.repair then parts[#parts + 1] = snapshot.durability and ("Gear at " .. math.floor(snapshot.durability * 100 + 0.5) .. "%") or "Check repairs" end
    if matched.food then parts[#parts + 1] = snapshot.food and (snapshot.food .. " food left") or "Check food" end
    if matched.drink then parts[#parts + 1] = snapshot.drink and (snapshot.drink .. " drink left") or "Check drink" end
    return table.concat(parts, " • ")
end
local function instructions(place, matched)
    local parts, chosen = {}, {}
    if matched.bags then parts[#parts + 1] = "Sell items you no longer need." end
    if matched.repair then parts[#parts + 1] = "Repair your equipment." end
    for id in pairs(place.items or {}) do
        local kind = usable(id)
        if kind and matched[kind] and (not chosen[kind] or id < chosen[kind]) then chosen[kind] = id end
    end
    for _, kind in ipairs({"food", "drink"}) do
        local id = chosen[kind]
        if id then
            local name = C_Item and ns.SafeTitle(ns.ReadPublic(C_Item.GetItemInfo, id)) or ns.SafeTitle(ns.ReadPublic(GetItemInfo, id))
            parts[#parts + 1] = snapshot[kind] and ("Buy ~" .. math.max(0, ns.Option("supplyTarget") - snapshot[kind]) .. " " .. (name or kind) .. ".")
                or ("Check your " .. kind .. " supplies.")
        end
    end
    return table.concat(parts, " ")
end

function ns.CurrentInventoryServiceStop()
    local state, collection, key = personal(), vendors()
    local pending = state and state.pending
    if not enabled() or not pending then return end
    if pending.guideKey ~= ns.routeSelection.key or pending.scope ~= key then state.pending = nil; return end
    local place = collection and collection.places[pending.vendor]
    if not place or not ns.ValidTravelPoint(place) then state.pending = nil; return end
    local signature = table.concat({revision, place.sequence, ns.Option("supplyTarget"), tostring(ns.Option("restockSupplies"))}, ":")
    if displayed and displayed.pending == pending and displayed.signature == signature then return displayed.stop end
    local matched, weight = matching(place, needs(pending.needs))
    if weight == 0 then state.pending = nil; cached, displayed = nil, nil; ns.ResetTravelPath(); return end
    local why = reason(matched)
    local stop = {id = 0, kind = "service", inventoryService = true, title = "Visit " .. place.name,
        label = "Talk to " .. place.name, npcName = place.name, mapID = place.mapID, x = place.x, y = place.y,
        serviceReason = why, serviceInstructions = instructions(place, matched), optional = true}
    displayed = {pending = pending, signature = signature, stop = stop}
    return stop
end

function ns.IsInventoryServiceStep(stop)
    return stop and ns.GuideDestination(stop).inventoryService == true or false
end
function ns.InventoryServiceDestination(stop)
    if not safeTime() then return stop end
    return ns.CurrentInventoryServiceStop() or stop
end

function ns.CurrentInventoryServiceTip(stop)
    if not enabled() or not safeTime() or merchantOpen or ns.CurrentInventoryServiceStop()
        or ns.IsClassTrainingStep(stop) then return end
    local collection, key = vendors()
    if not collection then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) then return end
    local now = ns.ReadPublic(GetTime)
    local signature = table.concat({key, ns.routeSelection.key, tostring(ns.selectedRoute), revision, collection.sequence,
        mapID, tostring(ns.Option("restockSupplies")), ns.Option("supplyTarget"), ns.profile.level or 0,
        ns.profile.classID or 0, stop and ns.GuideStepKey(stop) or "", ns.Option("distanceUnits")}, ":")
    if cached and cached.signature == signature and type(now) == "number" and now >= cached.time and now - cached.time < 1 then return cached.value end
    local position, required = ns.PlayerPoint(mapID), needs()
    if not ns.ValidTravelPoint(position) or not next(required) then return end
    local metrics, safety, terrain, best, bestWeight = {}, ns.TravelSafetyContext(), ns.TravelTerrainContext(), nil, 0
    local direct = ns.ValidTravelPoint(stop) and not stop.unknownLocation and stop.mapID == mapID
        and ns.TravelPointDistance(position, stop, metrics)
    for _, place in pairs(collection.places) do
        if ns.ValidTravelPoint(place) and place.mapID == mapID then
            local matched, weight = matching(place, required)
            local distance = weight > 0 and ns.TravelPointDistance(position, place, metrics)
            local onward = direct and ns.TravelPointDistance(place, stop, metrics)
            local extra = distance and onward and math.max(0, distance + onward - direct)
            if distance and distance <= RANGE and (extra and extra <= DETOUR or not direct and distance <= NEAR)
                and not ns.HostileTravelArea(place, safety) and not ns.HostileWalkCrossing(position, place, safety, true, false)
                and not ns.TerrainWalkCrossing(position, place, terrain)
                and (not direct or not ns.HostileWalkCrossing(place, stop, safety, true, true))
                and (not direct or not ns.TerrainWalkCrossing(place, stop, terrain))
                and (weight > bestWeight or weight == bestWeight and (not best or distance < best.distance
                    or distance == best.distance and place.key < best.place.key)) then
                bestWeight = weight
                best = {kind = "service", key = "service:" .. place.key, place = place, distance = distance, needs = matched,
                    scope = key, guideKey = ns.routeSelection.key,
                    text = "Visit " .. place.name .. " • " .. ns.FormatDistance(distance) .. "\n" .. reason(matched),
                    detail = reason(matched) .. ".\n" .. instructions(place, matched)
                        .. "\nClick to visit; Done resumes your guide. × dismisses this advice until the need is resolved."}
            end
        end
    end
    cached = type(now) == "number" and now == now and {signature = signature, time = now, value = best} or nil
    return best
end

function ns.AcceptInventoryServiceTip(value)
    if not value or value.kind ~= "service" or not safeTime() then return false end
    cached = nil -- Validate the current position again on this hardware click.
    local current = ns.CurrentInventoryServiceTip(ns.navigation and ns.navigation.state and ns.navigation.state.stop)
    local state = personal()
    if not current or not state or current.key ~= value.key then return false end
    state.pending = {guideKey = current.guideKey, scope = current.scope, vendor = current.place.key, needs = current.needs}
    cached = nil; ns.ResetTravelPath(); ns.flightPlanCache = nil
    ns.UpdateNavigation(); ns.DrawRoute(nil, true)
    return true
end
function ns.DismissInventoryServiceTip(value)
    local state = personal()
    if not state or not value or value.kind ~= "service" then return end
    for kind in pairs(value.needs or {}) do state.dismissed[kind] = true end
    cached = nil; ns.UpdateNavigation()
end
function ns.FinishInventoryService()
    local state = personal()
    if not state or not state.pending or not safeTime() then return false end
    for kind in pairs(state.pending.needs or {}) do state.dismissed[kind] = true end
    state.pending, cached, displayed = nil, nil, nil
    ns.ResetTravelPath(); ns.flightPlanCache = nil
    ns.UpdateNavigation(); ns.DrawRoute(nil, true)
    return true
end

function ns.ClearInventoryService()
    local state = personal()
    if state then state.pending = nil end
    cached, displayed = nil, nil
end

function ns.InitializeInventoryServices()
    if initialized then return end
    ns.db.inventoryServiceCharacters = type(ns.db.inventoryServiceCharacters) == "table" and ns.db.inventoryServiceCharacters or {}
    ns.db.inventoryServiceVendors = type(ns.db.inventoryServiceVendors) == "table" and ns.db.inventoryServiceVendors or {}
    local state = personal()
    if type(state) ~= "table" then state = {}; ns.db.inventoryServiceCharacters[ns.self] = state end
    state.dismissed = type(state.dismissed) == "table" and state.dismissed or {}
    if type(state.pending) ~= "table" or type(state.pending.needs) ~= "table" then state.pending = nil end
    initialized = true
    -- Register last, chaining the profession/travel handlers instead of replacing them.
    local function chain(event, action)
        local before = ns.handlers[event]
        ns.On(event, function(...) if before then before(...) end; action(...) end)
    end
    for _, event in ipairs({"BAG_UPDATE_DELAYED", "UPDATE_INVENTORY_DURABILITY", "PLAYER_EQUIPMENT_CHANGED", "PLAYER_LEVEL_UP", "PLAYER_LOGIN"}) do
        chain(event, ns.QueueServiceInventory)
    end
    chain("MERCHANT_SHOW", function() merchantOpen = true; ns.RecordServiceVendor(); ns.QueueServiceInventory() end)
    chain("MERCHANT_UPDATE", ns.QueueServiceInventory)
    chain("MERCHANT_CLOSED", function() merchantOpen = false; ns.QueueServiceInventory() end)
    chain("GET_ITEM_INFO_RECEIVED", function() if merchantOpen then ns.QueueServiceInventory() end end)
    ns.ReadServiceInventory()
end

function ns.InventoryServiceDiagnostics(output)
    local collection, count = vendors(), 0
    for _ in pairs(collection and collection.places or {}) do count = count + 1 end
    output("Inventory services: " .. (ns.Option("inventoryServices") and "on" or "off") .. "; " .. count
        .. " visited vendors known for this realm/build/faction; " .. reads .. " event-batched reads.")
    output("Inventory needs: " .. (snapshot and snapshot.free and (snapshot.free .. " free regular slots") or "bags unknown")
        .. "; " .. (snapshot and snapshot.durability and (math.floor(snapshot.durability * 100) .. "% lowest durability") or "durability unknown")
        .. "; food " .. (snapshot and snapshot.food or "unknown") .. "; drink " .. (snapshot and snapshot.drink or "unknown")
        .. ". Common usable supplies only; target " .. ns.Option("supplyTarget") .. ".")
    output("Service stop: " .. (personal() and personal().pending and personal().pending.vendor or "none")
        .. ". Optional click; max 350 metres nearby / 150 yards extra estimated walking; manual transactions.")
end
