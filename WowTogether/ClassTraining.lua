local addonName, ns = ...

-- Personal, optional service stops. The quest route and its fixed plan are
-- never edited. An even level is a reminder, not proof of learnable spells.
local RANGE, DETOUR = 150 / 0.9144, 150
local indexed, byClass, byID, cached, displayed = nil, {}, {}, nil, nil
local function saved() return ns.db and ns.db.classTraining and ns.db.classTraining[ns.self] end
local function index()
    if indexed == ns.guideServiceData then return end
    indexed, byClass, byID = ns.guideServiceData, {}, {}
    for _, place in ipairs(ns.guideServiceData and ns.guideServiceData.trainers or {}) do
        if ns.SafeTitle(place.id) and ns.SafeTitle(place.name) and ns.GuideInteger(place.classID)
            and place.classID > 0 and ns.ValidTravelPoint(place) then
            byID[place.id] = place
            byClass[place.classID] = byClass[place.classID] or {}
            table.insert(byClass[place.classID], place)
        end
    end
end
local function friendly(place)
    local owner, faction = ns.SafeTitle(place.faction), ns.SafeTitle(ns.profile and ns.profile.faction)
    return (faction == "Horde" or faction == "Alliance") and (owner == faction or owner == "Both")
end
local function band()
    local level = ns.profile and ns.profile.level
    return ns.GuideInteger(level, 255) and level >= 2 and math.floor(level / 2) * 2 or nil
end
local function enabled()
    return ns.Option("classTraining") and ns.routeSelection and ns.routeSelection.mode == "zone"
        and ns.SafeTitle(ns.routeSelection.key) ~= nil
end

function ns.InitializeClassTraining()
    if type(ns.db.classTraining) ~= "table" then ns.db.classTraining = {} end
    local state = saved()
    if type(state) ~= "table" then state = {}; ns.db.classTraining[ns.self] = state end
    for _, key in ipairs({"checked", "declined"}) do
        if not ns.GuideInteger(state[key], 255) then state[key] = 0 end
    end
    if type(state.pending) ~= "table" or not ns.SafeTitle(state.pending.id)
        or not ns.SafeTitle(state.pending.guideKey) then state.pending = nil end
    state.revision, cached, displayed = 0, nil, nil
end

local function trainerName(place)
    for _, id in ipairs(place.npcIDs or {}) do
        local npc = ns.questEntities and ns.questEntities.npc and ns.questEntities.npc[id]
        local name = npc and ns.SafeTitle(npc.name)
        if name then return name end
    end
    return place.name
end

function ns.CurrentClassTrainingStop()
    local state, level = saved(), band()
    if not enabled() or not state or not state.pending or not level
        or level <= math.max(state.checked, state.declined)
        or state.pending.guideKey ~= ns.routeSelection.key then return end
    index()
    local place = byID[state.pending.id]
    local class = ns.profile and ns.profile.classID
    if not place or not ns.GuideInteger(class) or class ~= place.classID or not friendly(place) then return end
    if not displayed or displayed.place ~= place or displayed.trainingLevel ~= level then
        local name = trainerName(place)
        displayed = {id = 0, kind = "trainer", action = "train", title = "Class training",
            label = "Check training with " .. name, npcName = name, targetName = name,
            mapID = place.mapID, x = place.x, y = place.y, sourceZone = place.hub,
            trainingLevel = level, place = place, optional = true}
    end
    return displayed
end

function ns.IsClassTrainingStep(stop)
    return stop and (stop.kind == "trainer" or stop.goal and stop.goal.kind == "trainer") or false
end

local function convenient(stop, position, class)
    if not ns.ValidTravelPoint(stop) or stop.unknownLocation or stop.planningAnchor then return end
    local metrics = {}
    local direct = ns.TravelPointDistance(position, stop, metrics)
    if not direct then return end
    -- Visit near pickups/returns. Also allow training just before leaving a
    -- known hub for distant work; never interrupt an objective nearby.
    local visit = (stop.kind == "a" or stop.kind == "t") and direct <= RANGE
    if not visit and (stop.kind ~= "q" or direct <= RANGE * 2) then return end
    local safety, best, extra, approach = ns.TravelSafetyContext(), nil, nil, nil
    for _, place in ipairs(byClass[class] or {}) do
        if friendly(place) and (visit or place.hub) and not ns.HostileTravelArea(place, safety) then
            local near = ns.TravelPointDistance(position, place, metrics)
            local onward = near and near <= RANGE and ns.TravelPointDistance(place, stop, metrics)
            local detour = onward and math.max(0, near + onward - direct)
            if detour and detour <= DETOUR and (not visit or onward <= RANGE)
                and not ns.HostileWalkCrossing(position, place, safety, true, false)
                and not ns.HostileWalkCrossing(place, stop, safety, false, true)
                and (not best or detour < extra or detour == extra and (near < approach
                    or near == approach and place.id < best.id)) then
                best, extra, approach = place, detour, near
            end
        end
    end
    return best
end

function ns.ClassTrainingDestination(stop)
    if ns.routeSelection and ns.routeSelection.mode == "profession" then return stop end
    if not enabled() or ns.guideScanning or ns.routePlanning or ns.routePaused
        or ns.navigationPreview or ns.ReadPublic(UnitOnTaxi, "player") ~= false
        or ns.ReadPublic(UnitIsGhost, "player") ~= false then return stop end
    local current = ns.CurrentClassTrainingStop()
    if current then return current end
    if not stop then return end
    local state, level, class = saved(), band(), ns.profile and ns.profile.classID
    if not state or not level or not ns.GuideInteger(class) or class <= 0
        or level <= math.max(state.checked, state.declined) or ns.RouteInCombat() then return stop end
    index()
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) or mapID <= 0 then return stop end
    local now = ns.ReadPublic(GetTime)
    local signature = table.concat({ns.routeSelection.key, tostring(ns.selectedRoute), tostring(indexed), ns.GuideStepKey(stop),
        mapID, level, class, ns.SafeTitle(ns.profile.faction) or "", state.revision}, ":")
    if cached and cached.signature == signature and ns.Public(now) and type(now) == "number"
        and now >= cached.time and now - cached.time < 1 then return stop end
    cached = ns.Public(now) and type(now) == "number" and now == now
        and {signature = signature, time = now} or nil
    local position = ns.PlayerPoint(mapID)
    local place = ns.ValidTravelPoint(position) and convenient(stop, position, class)
    if place then
        state.pending = {id = place.id, guideKey = ns.routeSelection.key}
        displayed = nil
        ns.ResetTravelPath()
        ns.flightPlanCache = nil
        return ns.CurrentClassTrainingStop() or stop
    end
    return stop
end

function ns.FinishClassTraining(checked)
    if ns.guideScanning or ns.routePlanning or ns.navigationPreview
        or ns.ReadPublic(UnitIsGhost, "player") ~= false or ns.ReadPublic(UnitOnTaxi, "player") ~= false then return false end
    local current, state = ns.CurrentClassTrainingStop(), saved()
    if not current or not state then return false end
    local key = checked and "checked" or "declined"
    state[key] = math.max(state[key], current.trainingLevel)
    state.pending, state.revision, cached, displayed = nil, state.revision + 1, nil, nil
    ns.flightPlanCache = nil
    ns.ResetTravelPath()
    ns.UpdateNavigation()
    ns.DrawRoute(nil, true)
    return true
end

function ns.ClassTrainingDiagnostics(output)
    local state, level = saved(), band()
    output("Class training: " .. (ns.Option("classTraining") and "on" or "off")
        .. "; reminder level " .. (level or "unknown") .. "; checked " .. (state and state.checked or 0)
        .. "; skipped " .. (state and state.declined or 0) .. ". Personal; even levels are training checks.")
    local current = ns.CurrentClassTrainingStop()
    output("Training stop: " .. (current and current.label or "none")
        .. "; range 150 metres, estimated added walk at most 150 yards. Spell availability is not inferred.")
end
