local addonName, ns = ...

-- Use the game's status-text preferences; never read or hook unit bars/auras.
local wanted = {statusText = "1", statusTextDisplay = "NUMERIC"}
ns.unitNumbersStatus = "Using game display settings."

local function api(name)
    return C_CVar and type(C_CVar[name]) == "function" and C_CVar[name] or _G[name]
end
local function read(key)
    local value = ns.ReadPublic(api("GetCVar"), key)
    if type(value) == "string" and value ~= "" then return value end
end
local function write(key, value)
    local setter = api("SetCVar")
    if type(setter) ~= "function" then return false end
    local ok = pcall(setter, key, value)
    return ok and read(key) == value
end

function ns.ApplyUnitNumbers()
    if not ns.db then return end
    if ns.RouteInCombat() then ns.unitNumbersStatus = "Display change queued until combat ends."; return end
    local restore = ns.db.unitNumberRestore
    if ns.Option("unitNumbers") then
        local previous = {}
        for key in pairs(wanted) do
            previous[key] = read(key)
            if not previous[key] then ns.unitNumbersStatus = "Native status-text settings unavailable."; return end
        end
        if type(restore) ~= "table" then restore = {}; ns.db.unitNumberRestore = restore end
        local applied = true
        for key, value in pairs(wanted) do
            if type(restore[key]) ~= "string" then restore[key] = previous[key] end
            if previous[key] ~= value and not write(key, value) then applied = false end
        end
        ns.unitNumbersStatus = applied and "Numeric health/resource text enabled." or "Native display change could not be applied."
    elseif type(restore) == "table" then
        for key, value in pairs(wanted) do
            local current = read(key)
            -- Preserve changes made later in the game's own settings.
            if current and (current ~= value or restore[key] == nil or write(key, restore[key])) then restore[key] = nil end
        end
        if next(restore) == nil then ns.db.unitNumberRestore = nil end
        ns.unitNumbersStatus = ns.db.unitNumberRestore and "Native display restoration pending." or "Using game display settings."
    end
end

function ns.InitializeUnitNumbers()
    ns.ApplyUnitNumbers()
    for _, event in ipairs({"PLAYER_LOGIN", "PLAYER_REGEN_ENABLED"}) do
        local previous = ns.handlers[event]
        ns.On(event, function(...) if previous then previous(...) end; ns.ApplyUnitNumbers() end)
    end
end
