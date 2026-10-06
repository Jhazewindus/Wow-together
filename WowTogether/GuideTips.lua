local addonName, ns = ...

-- Optional advice, separate from quest steps and travel decisions. Physical
-- distance is in game yards; 150 metres is 150 / 0.9144 yards on every map.
local RANGE, HUB = 150 / 0.9144, 400 / 0.9144
local indexed, innsByMap, cached = nil, {}, nil

local function saved()
    return ns.db and ns.db.guideServices and ns.db.guideServices[ns.self]
end

local function friendly(place)
    local faction = ns.profile and ns.SafeTitle(ns.profile.faction)
    local owner = ns.SafeTitle(place.faction)
    return faction and (owner == faction or owner == "Both")
end

local function indexInns()
    local state = saved()
    local signature = tostring(ns.guideServiceData) .. ":" .. tostring(state and state.revision or 0)
    if indexed == signature then return end
    indexed, innsByMap = signature, {}
    local seen = {}
    local function add(inn)
        if type(inn) ~= "table" or not ns.SafeTitle(inn.id) or not ns.SafeTitle(inn.name)
            or not ns.ValidTravelPoint(inn) or seen[inn.id] then return end
        seen[inn.id] = true
        innsByMap[inn.mapID] = innsByMap[inn.mapID] or {}
        table.insert(innsByMap[inn.mapID], inn)
    end
    -- An actual inn interaction can update an older published location.
    for _, inn in pairs(state and state.inns or {}) do add(inn) end
    for _, inn in ipairs(ns.guideServiceData and ns.guideServiceData.inns or {}) do add(inn) end
end

function ns.InitializeGuideTips()
    ns.db.guideServices = type(ns.db.guideServices) == "table" and ns.db.guideServices or {}
    local state = ns.db.guideServices[ns.self]
    if type(state) ~= "table" then state = {}; ns.db.guideServices[ns.self] = state end
    if type(state.inns) ~= "table" then state.inns = {} end
    if type(state.dismissed) ~= "table" then state.dismissed = {} end
    state.revision = 0
    if not ns.SafeTitle(state.boundInnID) then state.boundInnID = nil end
    indexed, cached, ns.pendingGuideInn = nil, nil, nil
end

local function usefulReturn(inn, route, metrics)
    local returns, away = {}, false
    for index, stop in ipairs(route.stops or {}) do
        if index > 48 then break end
        if ns.ValidTravelPoint(stop) and not stop.unknownLocation and not stop.planningAnchor then
            local yards = ns.TravelPointDistance(inn, stop, metrics)
            if yards and yards > HUB and stop.kind == "q" then away = true end
            if away and stop.kind == "t" and yards and yards <= HUB then returns[stop.id] = true end
        end
    end
    local count = 0; for _ in pairs(returns) do count = count + 1 end
    return count >= 2 and count or nil
end

local function tip(kind, place, yards, detail, key)
    local verb = kind == "hearth" and "Set hearthstone" or kind == "flight" and "Get flight path" or "Check flight path"
    return {kind = kind, key = key, place = place, distance = yards,
        text = "Tip: " .. verb .. " — " .. place.name .. " • " .. ns.FormatDistance(yards),
        detail = verb .. " at " .. place.name .. ".\n" .. detail .. "\n"
            .. ns.MapName(place.mapID) .. string.format(" • %.1f, %.1f", place.x * 100, place.y * 100)
            .. "\nOptional: keep following your guide. Dismiss with ×."}
end

local function findTip(route, guide, position)
    local state, best, rank, bestDistance = saved(), nil, nil, nil
    if not state or not ns.ValidTravelPoint(position) then return end
    local metrics, mapID = {}, position.mapID
    local function consider(value, priority)
        if not state.dismissed[value.key] and (not rank or priority < rank
            or priority == rank and (value.distance < bestDistance
            or value.distance == bestDistance and value.key < best.key)) then
            best, rank, bestDistance = value, priority, value.distance
        end
    end
    if ns.Option("nearbyFlights") then
        local flights = ns.db.flights and ns.db.flights[ns.self]
        local seen = {}
        local function check(id, place, node)
            if seen[id] or not ns.ValidTravelPoint(place) or not friendly(place) then return end
            seen[id] = true
            if node and node.known == true or ns.checkedFlightNodes and ns.checkedFlightNodes[id] then return end
            local yards = place.mapID == mapID and ns.TravelPointDistance(position, place, metrics)
            if not yards or yards > RANGE then return end
            local confirmed = node and node.known == false and node.unlockConfirmed == true
            consider(tip(confirmed and "flight" or "flight-check", place, yards,
                confirmed and "This character's map reports this flight path as undiscovered. Talk to the flight master to unlock it."
                    or "Unlock status is unknown. Talk to the flight master and learn it if needed; location data alone does not confirm an unlock.",
                "taxi:" .. id), confirmed and 1 or 3)
        end
        local data = ns.travelData and ns.travelData.nodes or {}
        for id, metadata in pairs(ns.guideServiceData and ns.guideServiceData.taxis or {}) do
            local node = flights and flights.nodes[id]
            local location = node and node.point or data["TAXI_" .. id]
            if ns.ValidTravelPoint(location) then
                check(id, {mapID = location.mapID, x = location.x, y = location.y,
                    name = ns.SafeTitle(node and node.name) or metadata.name,
                    faction = ns.SafeTitle(node and node.faction) or metadata.faction}, node)
            end
        end
        for id, node in pairs(flights and flights.nodes or {}) do
            if node.point and ns.SafeTitle(node.name) then
                local p = node.point
                check(id, {mapID = p.mapID, x = p.x, y = p.y, name = node.name, faction = node.faction}, node)
            end
        end
    end
    if ns.Option("hearthstoneTips") then
        indexInns()
        local bind = ns.SafeTitle(ns.ReadPublic(GetBindLocation))
        for _, inn in ipairs(innsByMap[mapID] or {}) do
            if friendly(inn) and state.boundInnID ~= inn.id and (not bind or string.lower(bind) ~= string.lower(inn.name)) then
                local yards = ns.TravelPointDistance(position, inn, metrics)
                if yards and yards <= RANGE then
                    local count = usefulReturn(inn, route, metrics)
                    if count then consider(tip("hearth", inn, yards,
                        "Your upcoming guide work returns here for " .. count .. " quest turn-ins after objectives away from this hub. Set your home at the innkeeper manually.",
                        "hearth:" .. guide.key .. ":" .. inn.id), 2) end
                end
            end
        end
    end
    return best
end

function ns.CurrentGuideTip(state)
    local guide, route = ns.routeSelection, ns.selectedRoute
    if not saved() or not guide or guide.mode == "travel" or not route or not route.stops or not route.stops[1]
        or ns.navigationPreview or ns.routePaused or ns.guideScanning or ns.routePlanning or ns.RouteInCombat()
        or state and (state.flight or state.stop.kind == "corpse")
        or state and ns.IsClassTrainingStep(state.stop)
        or ns.ReadPublic(UnitOnTaxi, "player") == true or ns.ReadPublic(UnitIsGhost, "player") == true then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) then return end
    local now = ns.ReadPublic(GetTime)
    local signature = table.concat({tostring(route), guide.key, mapID, ns.travelRevision or 0,
        saved().revision, tostring(ns.Option("nearbyFlights")), tostring(ns.Option("hearthstoneTips")),
        ns.SafeTitle(ns.profile and ns.profile.faction) or "", ns.Option("distanceUnits")}, ":")
    if cached and cached.signature == signature and ns.Public(now) and type(now) == "number"
        and now >= cached.time and now - cached.time < 1 then return cached.tip end
    local result = findTip(route, guide, ns.PlayerPoint(mapID))
    cached = ns.Public(now) and type(now) == "number" and now == now and {signature = signature, time = now, tip = result} or nil
    return result
end

function ns.DismissGuideTip()
    local value = ns.navigation and ns.navigation.tip and ns.navigation.tip.value
    local state = saved()
    if state and value then state.dismissed[value.key] = true; cached = nil; ns.UpdateNavigation() end
end

function ns.UpdateGuideTip(state)
    local frame = ns.navigation and ns.navigation.tip
    if not frame then return end
    local value = state.visible and ns.CurrentGuideTip(state) or nil
    frame.value = value
    frame:SetShown(value ~= nil and ns.Option("routeArrow"))
    if value then frame.text:SetText(value.text) end
    if ns.standaloneNavigation then ns.standaloneNavigation.guideTip = value end
end

function ns.GuideTipDiagnostics(output)
    output("Guide tips: flight paths " .. (ns.Option("nearbyFlights") and "on" or "off")
        .. "; hearthstone " .. (ns.Option("hearthstoneTips") and "on" or "off") .. "; nearby range 150 metres.")
    local value = ns.navigation and ns.navigation.tip and ns.navigation.tip.value
    output("Current optional tip: " .. (value and value.text or "none"))
    local interaction = ns.handlers.PLAYER_INTERACTION_MANAGER_FRAME_SHOW and "modern binder interaction"
        or ns.handlers.CONFIRM_BINDER and "binder confirmation" or "unavailable"
    output("Inn recording: " .. interaction .. "; binding event " .. (ns.handlers.HEARTHSTONE_BOUND and "registered" or "unavailable") .. ".")
end

function ns.RecordGuideInn()
    ns.pendingGuideInn = nil
    local state = saved()
    if not state or ns.RouteInCombat() then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local location = ns.GuideInteger(mapID) and ns.PlayerPoint(mapID)
    if not ns.ValidTravelPoint(location) then return end
    local guid = ns.SafeTitle(ns.ReadPublic(UnitGUID, "npc"))
    local npcID = guid and tonumber(string.match(guid, "^Creature%-%d+%-%d+%-%d+%-%d+%-(%d+)%-"))
    indexInns()
    local published
    for _, inn in ipairs(innsByMap[mapID] or {}) do
        if npcID and inn.npcID == npcID then published = inn; break end
    end
    local name = published and published.name or ns.SafeTitle(ns.ReadPublic(GetSubZoneText)) or ns.SafeTitle(ns.ReadPublic(GetZoneText))
    local faction = ns.SafeTitle(ns.profile and ns.profile.faction)
    if not name or not faction then return end
    local id = published and published.id or "observed:" .. mapID .. ":" .. (npcID or name)
    state.inns[id] = {id = id, mapID = mapID, x = location.x, y = location.y, name = name, faction = faction, npcID = npcID}
    state.revision, ns.pendingGuideInn, cached = state.revision + 1, id, nil
end

-- INN_INFO is not a valid event on the tested Forever client. Modern UI
-- interaction events identify the binder by enum; use the older confirmation
-- event only where registration succeeds. Neither binds a hearthstone.
local interactions = Enum and Enum.PlayerInteractionType
local binder = interactions and interactions.Binder
if ns.Public(binder) and type(binder) == "number" then
    ns.On("PLAYER_INTERACTION_MANAGER_FRAME_SHOW", function(interaction)
        if ns.Public(interaction) and interaction == binder then ns.RecordGuideInn() end
    end)
end
ns.On("CONFIRM_BINDER", ns.RecordGuideInn)
ns.On("HEARTHSTONE_BOUND", function()
    local state = saved()
    if not state then return end
    local inn = state.inns[ns.pendingGuideInn]
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local position = ns.GuideInteger(mapID) and ns.PlayerPoint(mapID)
    local yards = inn and position and ns.TravelPointDistance(inn, position)
    state.boundInnID = yards and yards <= 30 and ns.pendingGuideInn or nil
    ns.pendingGuideInn = nil
    state.revision, cached = state.revision + 1, nil
    ns.UpdateNavigation()
end)
