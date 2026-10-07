local addonName, ns = ...

-- Optional advice, separate from quest steps and travel decisions. Flight tips
-- allow a nearby visit or a short detour; inns retain their 150-metre range.
-- All physical distance calculations use game yards.
local RANGE, HUB = 150 / 0.9144, 400 / 0.9144
local FLIGHT_NEAR, FLIGHT_AHEAD, FLIGHT_EXTRA = 350 / 0.9144, 750 / 0.9144, 200 / 0.9144
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

local function findTip(route, guide, position, navigation)
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
        local seen, safety, nearest = {}, ns.TravelSafetyContext(), nil
        local nextStop = navigation and navigation.stop or route.stops[1]
        local direct = ns.ValidTravelPoint(nextStop) and not nextStop.unknownLocation and not nextStop.planningAnchor
            and nextStop.mapID == mapID and ns.TravelPointDistance(position, nextStop, metrics)
        local function check(id, place, node)
            if seen[id] or not ns.ValidTravelPoint(place) or not friendly(place) or not ns.SafeTitle(place.name) then return end
            seen[id] = true
            if node and ns.Public(node.known) and node.known == true
                or ns.checkedFlightNodes and ns.checkedFlightNodes[id] then return end
            local yards = place.mapID == mapID and ns.TravelPointDistance(position, place, metrics)
            if not yards then return end
            if not nearest or yards < nearest.distance then nearest = {name = place.name, distance = yards} end
            if yards > FLIGHT_AHEAD or ns.HostileTravelArea(place, safety)
                or ns.HostileWalkCrossing(position, place, safety, true, false) then return end
            local extra
            if direct then
                local onward = ns.TravelPointDistance(place, nextStop, metrics)
                if onward and not ns.HostileWalkCrossing(place, nextStop, safety, true, true) then
                    extra = math.max(0, yards + onward - direct)
                end
            end
            if yards > FLIGHT_NEAR and (not extra or extra > FLIGHT_EXTRA) then return end
            local confirmed = node and ns.Public(node.known) and node.known == false
                and ns.Public(node.unlockConfirmed) and node.unlockConfirmed == true
            local value = tip(confirmed and "flight" or "flight-check", place, yards,
                "Unlock this stop for easier future trips through " .. place.name .. "."
                    .. (confirmed and " Talk to the flight master to learn it."
                        or " Talk to the flight master and check whether you still need to learn it.")
                    .. (yards > FLIGHT_NEAR and ("\nOn your way: ~" .. ns.FormatDistance(extra) .. " extra walking (estimate).") or ""),
                "taxi:" .. id)
            value.text = (confirmed and "Get flight path" or "Check flight path") .. " — " .. place.name
                .. "\n" .. ns.FormatDistance(yards) .. (yards > FLIGHT_NEAR and " • Short detour for future trips" or " • Unlock for future trips")
            value.extraWalking, value.taxiID = extra, id
            consider(value, confirmed and 1 or 3)
        end
        local data = ns.travelData and ns.travelData.nodes or {}
        local labels = ns.guideServiceData and ns.guideServiceData.taxis or {}
        local function location(id, published)
            local node = flights and flights.nodes[id]
            local label = labels[id] or {}
            if seen[id] or node and ns.Public(node.known) and node.known == true
                or ns.checkedFlightNodes and ns.checkedFlightNodes[id] then return end
            local owner = ns.SafeTitle(node and node.faction) or published and ns.SafeTitle(published.faction) or ns.SafeTitle(label.faction)
            if not friendly({faction = owner}) then return end
            local p = node and node.point or published
            if not ns.ValidTravelPoint(p) then p = published end
            if not ns.ValidTravelPoint(p) then return end
            if p.mapID ~= mapID then
                -- New observations can use continent flight-map coordinates.
                -- Project publicly; never reuse their normalized x/y locally.
                local projected = node and ns.ProjectMapPoint(p, mapID, metrics)
                p = ns.ValidTravelPoint(projected) and projected or published
            end
            if not ns.ValidTravelPoint(p) or p.mapID ~= mapID then return end
            check(id, {mapID = p.mapID, x = p.x, y = p.y,
                name = ns.SafeTitle(node and node.name) or ns.SafeTitle(label.name) or published and ns.SafeTitle(published.name),
                faction = owner}, node)
        end
        -- Settlement labels cover only part of the published catalogue.
        for key, place in pairs(data) do
            local id = tonumber(string.match(key, "^TAXI_(%d+)$"))
            if id then location(id, place) end
        end
        for id in pairs(labels) do if not seen[id] then location(id, data["TAXI_" .. id]) end end
        for id in pairs(flights and flights.nodes or {}) do if not seen[id] then location(id, data["TAXI_" .. id]) end end
        ns.nearbyFlightStatus = nearest and (nearest.name .. ": " .. ns.FormatDistance(nearest.distance)
            .. (best and " • advice available" or " • outside range, dismissed or crossing blocked"))
            or "No friendly unlearned flight master located on the current map."
    else
        ns.nearbyFlightStatus = "Disabled in settings."
    end
    if guide.mode ~= "travel" and ns.Option("hearthstoneTips") then
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
    if not saved() or not guide or not route or not route.stops or not route.stops[1]
        or ns.navigationPreview or ns.routePaused or ns.guideScanning or ns.routePlanning or ns.RouteInCombat()
        or state and (state.flight or state.stop.kind == "corpse")
        or state and ns.IsClassTrainingStep(state.stop)
        or ns.ReadPublic(UnitOnTaxi, "player") == true or ns.ReadPublic(UnitIsGhost, "player") == true then return end
    if state and state.stop.flightDiscovery then
        if ns.Option("routeArrow") then return end
        local plan = state.stop.flightDiscovery
        return {key = plan.key, flightDiscovery = state.stop,
            text = "Check " .. plan.source.name .. " flights\nPotential saving ~" .. ns.FormatTravelDuration(plan.savedSeconds),
            detail = ns.TravelPathSummary(state.stop) .. "\n× keeps the known route; no quest is skipped."}
    end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) then return end
    local now = ns.ReadPublic(GetTime)
    local nextStop = state and state.stop or route.stops[1]
    local leg = ns.ValidTravelPoint(nextStop) and table.concat({nextStop.mapID, nextStop.x, nextStop.y}, ",") or ""
    local signature = table.concat({tostring(route), guide.key, mapID, ns.travelRevision or 0,
        saved().revision, tostring(ns.Option("nearbyFlights")), tostring(ns.Option("hearthstoneTips")),
        ns.SafeTitle(ns.profile and ns.profile.faction) or "", ns.Option("distanceUnits"), leg}, ":")
    if cached and cached.signature == signature and ns.Public(now) and type(now) == "number"
        and now >= cached.time and now - cached.time < 1 then return cached.tip end
    local result = findTip(route, guide, ns.PlayerPoint(mapID), state)
    cached = ns.Public(now) and type(now) == "number" and now == now and {signature = signature, time = now, tip = result} or nil
    return result
end

function ns.DismissGuideTip()
    local value = ns.navigation and ns.navigation.tip and ns.navigation.tip.value
    local state = saved()
    if value and value.flightDiscovery then ns.DismissFlightCheck(value.flightDiscovery); return end
    if state and value then state.dismissed[value.key] = true; cached = nil; ns.UpdateNavigation() end
end

function ns.UpdateGuideTip(state)
    local frame = ns.navigation and ns.navigation.tip
    if not frame then return end
    local value = state.visible and ns.CurrentGuideTip(state) or nil
    frame.value = value
    frame:SetShown(value ~= nil and ns.Option("routeArrow"))
    if value then frame.text:SetText(value.text) end
    local standalone = ns.standaloneNavigation
    if standalone then
        standalone.guideTip = value
        standalone.tip:SetShown(value ~= nil and standalone:IsShown() and not ns.Option("routeArrow"))
        if value then standalone.tip.text:SetText(value.text) end
        ns.LayoutStandaloneDetails(standalone)
    end
end

function ns.GuideTipDiagnostics(output)
    output("Guide tips: flight paths " .. (ns.Option("nearbyFlights") and "on" or "off")
        .. "; hearthstone " .. (ns.Option("hearthstoneTips") and "on" or "off")
        .. "; flight range 350 metres, or 750 metres with at most 200 metres estimated extra walking; inn range 150 metres.")
    local count = 0
    for key in pairs(ns.travelData and ns.travelData.nodes or {}) do if string.match(key, "^TAXI_%d+$") then count = count + 1 end end
    output("Flight discovery advice: " .. count .. " bundled taxi locations; " .. (ns.nearbyFlightStatus or "not checked yet"))
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
