local addonName, ns = ...

-- Personal transports this character owns: the Hearthstone and class
-- teleports. The live router adds them as one-way edges from the current
-- position, priced with cast time, a hassle allowance and any remaining
-- cooldown, so "deliver X in Stormwind" becomes "Use your Hearthstone" when
-- that is quicker than walking or flying. Generic fixed-guide comparisons
-- still exclude them (a shared guide cannot assume where you are bound).
-- HASSLE values the cooldown you give up: a Hearthstone is only suggested
-- when it beats walking/flying by more than ~2.5 minutes; a class teleport
-- (short cooldown, a reagent) by more than a minute. MAX_WAIT caps how long
-- a route may ask you to wait for the cooldown.
local HEARTHSTONE, CAST, HASSLE, TELEPORT_HASSLE, MAX_WAIT = 6948, 10, 150, 60, 180

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value and value > -math.huge and value < math.huge
end
local function number(value) return finite(value) and value or nil end

-- Classic teleport spells and approximate landing points. Landings use the
-- published city node nearest to the mage/druid tower; after the teleport the
-- router re-plans from the real position, so these only price the estimate.
ns.personalTeleports = {
    {spell = 3561, name = "Teleport: Stormwind", mapID = 1453, x = 0.4987, y = 0.8667, faction = "Alliance"},
    {spell = 3562, name = "Teleport: Ironforge", mapID = 1455, x = 0.2700, y = 0.0850, faction = "Alliance"},
    {spell = 3565, name = "Teleport: Darnassus", mapID = 1457, x = 0.4400, y = 0.7800, faction = "Alliance"},
    {spell = 3567, name = "Teleport: Orgrimmar", mapID = 1454, x = 0.3860, y = 0.8590, faction = "Horde"},
    {spell = 3563, name = "Teleport: Undercity", mapID = 1458, x = 0.8500, y = 0.1300, faction = "Horde"},
    {spell = 3566, name = "Teleport: Thunder Bluff", mapID = 1456, x = 0.2500, y = 0.2200, faction = "Horde"},
    {spell = 18960, name = "Teleport: Moonglade", mapID = 1450, x = 0.5200, y = 0.4100, faction = "Both"},
}

local function itemCount(id)
    local count
    if C_Item and type(C_Item.GetItemCount) == "function" then count = ns.ReadPublic(C_Item.GetItemCount, id) end
    if count == nil and type(GetItemCount) == "function" then count = ns.ReadPublic(GetItemCount, id) end
    return number(count) or 0
end

local function itemCooldown(id)
    local start, duration
    if C_Container and type(C_Container.GetItemCooldown) == "function" then start, duration = ns.ReadPublic(C_Container.GetItemCooldown, id) end
    if start == nil and C_Item and type(C_Item.GetItemCooldown) == "function" then start, duration = ns.ReadPublic(C_Item.GetItemCooldown, id) end
    if start == nil and type(GetItemCooldown) == "function" then start, duration = ns.ReadPublic(GetItemCooldown, id) end
    local now = ns.ReadPublic(GetTime)
    if not number(start) or not number(duration) or not number(now) or duration <= 0 or start <= 0 then return 0 end
    return math.max(0, start + duration - now)
end

local function spellKnown(id)
    if type(IsSpellKnown) == "function" then
        local known = ns.ReadPublic(IsSpellKnown, id)
        if known == true then return true end
    end
    if type(IsPlayerSpell) == "function" then return ns.ReadPublic(IsPlayerSpell, id) == true end
    return false
end

local function spellCooldown(id)
    local start, duration
    if C_Spell and type(C_Spell.GetSpellCooldown) == "function" then
        local info = ns.ReadPublic(C_Spell.GetSpellCooldown, id)
        if type(info) == "table" then start, duration = info.startTime, info.duration end
    end
    if start == nil and type(GetSpellCooldown) == "function" then start, duration = ns.ReadPublic(GetSpellCooldown, id) end
    local now = ns.ReadPublic(GetTime)
    if not number(start) or not number(duration) or not number(now) or duration <= 1.6 or start <= 0 then return 0 end
    return math.max(0, start + duration - now)
end

-- Where the Hearthstone lands: the inn confirmed by the bind event, else the
-- published inn whose name matches the client's bind location.
function ns.HearthstonePoint()
    local state = ns.char and ns.char.guideServices
    local inns = ns.db and ns.db.innLocations and ns.db.innLocations[ns.worldBuild]
    local inn = state and state.boundInnID and inns and inns[state.boundInnID]
    if inn and ns.ValidTravelPoint(inn) then return {mapID = inn.mapID, x = inn.x, y = inn.y}, ns.SafeTitle(inn.name) or "your inn", "confirmed" end
    local bind = ns.SafeTitle(ns.ReadPublic(GetBindLocation))
    if not bind then return nil, nil, "bind location unavailable" end
    local wanted = string.lower(bind)
    for _, candidate in pairs(inns or {}) do
        if ns.ValidTravelPoint(candidate) and ns.SafeTitle(candidate.name) and string.lower(candidate.name) == wanted then
            return {mapID = candidate.mapID, x = candidate.x, y = candidate.y}, candidate.name, "recorded inn"
        end
    end
    for _, candidate in ipairs(ns.guideServiceData and ns.guideServiceData.inns or {}) do
        if ns.ValidTravelPoint(candidate) and ns.SafeTitle(candidate.name) and string.lower(candidate.name) == wanted then
            return {mapID = candidate.mapID, x = candidate.x, y = candidate.y}, candidate.name, "published inn"
        end
    end
    return nil, bind, "no inn location for " .. bind
end

-- Transports usable right now, as {id, point, name, method, seconds, remaining}.
function ns.PersonalTransports()
    local result = {}
    if ns.Option("useHearthstone") and itemCount(HEARTHSTONE) > 0 then
        local point, name, basis = ns.HearthstonePoint()
        local remaining = itemCooldown(HEARTHSTONE)
        if point and remaining <= MAX_WAIT then
            result[#result + 1] = {id = "HEARTH", point = point, name = name, method = "hearth",
                seconds = CAST + HASSLE + remaining, remaining = remaining, basis = basis}
        end
        ns.hearthstoneStatus = point and (name .. " (" .. basis .. "; cooldown " .. ns.FormatTravelDuration(remaining) .. ")") or basis
    else
        ns.hearthstoneStatus = ns.Option("useHearthstone") and "no Hearthstone in bags" or "disabled in settings"
    end
    if ns.Option("useHearthstone") then
        local faction = ns.profile and ns.SafeTitle(ns.profile.faction)
        for _, teleport in ipairs(ns.personalTeleports) do
            if (teleport.faction == "Both" or teleport.faction == faction) and spellKnown(teleport.spell) then
                local remaining = spellCooldown(teleport.spell)
                if remaining <= MAX_WAIT then
                    result[#result + 1] = {id = "TELEPORT_" .. teleport.spell, point = {mapID = teleport.mapID, x = teleport.x, y = teleport.y},
                        name = teleport.name, method = "teleport", seconds = CAST + TELEPORT_HASSLE + remaining, remaining = remaining,
                        basis = "approximate landing", approximate = true}
                end
            end
        end
    end
    return result
end

-- Cheap state key so a route re-plans when the bind point or the Hearthstone
-- cooldown minute changes, without rebuilding the graph every frame.
local personalSignature, personalEnabled, personalBind, personalMinute
function ns.PersonalTransportSignature()
    local enabled = ns.Option("useHearthstone") == true
    local bind, minute
    if enabled then
        bind = ns.SafeTitle(ns.ReadPublic(GetBindLocation)) or ""
        local remaining = itemCount(HEARTHSTONE) > 0 and itemCooldown(HEARTHSTONE) or -60
        minute = math.floor(remaining / 60)
    else
        bind, minute = "", -60
    end
    if personalSignature == nil or enabled ~= personalEnabled or bind ~= personalBind or minute ~= personalMinute then
        personalEnabled, personalBind, personalMinute = enabled, bind, minute
        personalSignature = enabled and ("p:" .. bind .. ":" .. minute) or "p:off"
    end
    return personalSignature
end

function ns.PersonalTransportLabel(leg)
    local transport = leg.to and leg.to.personal
    local name = transport and transport.name or leg.name
    local remaining = transport and transport.remaining or 0
    local wait = remaining > 0 and (" (ready in " .. ns.FormatTravelDuration(remaining) .. ")") or ""
    if leg.method == "hearth" then return "Use your Hearthstone to " .. name .. wait end
    return "Cast " .. name .. wait
end

function ns.PersonalTransportDiagnostics(output)
    local transports = ns.PersonalTransports()
    output("Hearthstone: " .. (ns.hearthstoneStatus or "not checked") .. ".")
    local names = {}
    for _, transport in ipairs(transports) do
        if transport.method == "teleport" then names[#names + 1] = transport.name end
    end
    output("Teleports known: " .. (#names > 0 and table.concat(names, ", ") or "none") .. ".")
end
