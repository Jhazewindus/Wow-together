local addonName, ns = ...

-- Public empty shells keep unrelated guide/runtime features safe before the
-- optional quest reference package is requested.
ns.questEntities = ns.questEntities or {npc = {}, object = {}, item = {}}

-- Optional data add-ons share this private namespace through one temporary
-- global. The payloads remain separate LoadOnDemand add-ons so the client does
-- not parse their large literal tables while loading the main companion.
ns.optionalDataState = ns.optionalDataState or {}
local dataAddons = {
    ["WowTogether_QuestData"] = {field = "catalogue", tableField = "quests"},
    ["WowTogether_ProfessionData"] = {field = "professionGuideData", tableField = "professions"},
    ["WowTogether_DungeonData"] = {field = "dungeonJournalData", tableField = "dungeons",
        extraField = "dungeonMapData", extraTableField = "dungeons"},
}

local function dataReady(definition)
    local primary = ns[definition.field]
    if type(primary) ~= "table" or type(rawget(primary, definition.tableField)) ~= "table" then return false end
    if definition.extraField then
        local extra = ns[definition.extraField]
        if type(extra) ~= "table" or type(rawget(extra, definition.extraTableField)) ~= "table" then return false end
    end
    return true
end

function ns.EnsureOptionalData(addon)
    local definition = dataAddons[addon]
    if not definition then return false end
    local function markLoaded()
        ns.optionalDataState[addon] = "loaded"
        if addon == "WowTogether_QuestData" and ns.ResolveCatalogueMaps then ns.ResolveCatalogueMaps() end
        return true
    end
    if dataReady(definition) then return markLoaded() end
    local state = ns.optionalDataState[addon]
    if state == "loading" or state == "missing" or state == "data missing" or state == "load failed" then return false end
    if type(InCombatLockdown) == "function" then
        local okay, combat = pcall(InCombatLockdown)
        if okay and ns.Public(combat) and combat == true then
            ns.optionalDataState[addon] = "deferred combat"
            return false
        end
    end
    ns.optionalDataState[addon] = "loading"
    local loader = C_AddOns and C_AddOns.LoadAddOn or LoadAddOn
    if type(loader) ~= "function" then
        ns.optionalDataState[addon] = "unavailable"
        return false
    end
    _G.WowTogetherSharedNamespace = ns
    local okay, loadResult = pcall(loader, addon)
    if _G.WowTogetherSharedNamespace == ns then _G.WowTogetherSharedNamespace = nil end
    if okay and ns.Public(loadResult) and loadResult == true and dataReady(definition) then
        return markLoaded()
    end
    -- Missing folders must not cause a retry from every planner field access.
    -- An explicit retry remains possible after clearing this diagnostic state.
    ns.optionalDataState[addon] = okay and "data missing" or "load failed"
    return false
end

local function proxy(field, addon, publicMetadata, safeEmpty)
    local empty = {}
    for key, enabled in pairs(safeEmpty or {}) do if enabled then empty[key] = {} end end
    return setmetatable({}, {__index = function(_, key)
        if publicMetadata and publicMetadata[key] ~= nil then return publicMetadata[key] end
        ns.EnsureOptionalData(addon)
        local value = ns[field]
        local result = type(value) == "table" and rawget(value, key) or nil
        if result ~= nil then return result end
        return empty[key]
    end})
end

-- Keep summary labels available without parsing the 9.5 MiB quest payload.
-- The large quest table is loaded only when a guide/library actually asks for it.
ns.catalogue = proxy("catalogue", "WowTogether_QuestData", {
    count = 5230, captured = "2026-10-10",
    source = "https://forever.warcraftdb.com/list/quests",
    detailSource = "https://www.wowhead.com/forever/quests",
}, {quests = true})
ns.professionGuideData = proxy("professionGuideData", "WowTogether_ProfessionData", nil, {professions = true})
ns.dungeonJournalData = proxy("dungeonJournalData", "WowTogether_DungeonData", nil, {dungeons = true, items = true})
ns.dungeonMapData = proxy("dungeonMapData", "WowTogether_DungeonData", nil, {dungeons = true})

-- Bundled, literal-only data. Keep each nested field packed until it is used.
-- A decoded field becomes an ordinary, stable table: map resolution and other
-- runtime annotations must survive collection and subsequent reads.
local stores, order = {}, {}
local function decode(text, strings)
    local cursor = 1
    local function number()
        local last = assert(string.find(text, ";", cursor, true), "Invalid packed data")
        local value = assert(tonumber(string.sub(text, cursor, last - 1)), "Invalid packed number")
        cursor = last + 1
        return value
    end
    local read
    read = function()
        local tag = string.sub(text, cursor, cursor)
        cursor = cursor + 1
        if tag == "n" then return number() end
        if tag == "s" then return assert(strings[number()], "Invalid packed string") end
        if tag == "y" then return true end
        if tag == "f" then return false end
        local count, value = number(), {}
        assert(tag == "a" or tag == "t", "Invalid packed table")
        for index = 1, count do
            local key = tag == "a" and index or read()
            value[key] = read()
        end
        return value
    end
    local value = read()
    assert(cursor == #text + 1, "Trailing packed data")
    return value
end

function ns.RegisterPackedData(name, rows, columns, strings, packedRows)
    local store = {name = name, rows = rows, columns = columns, strings = strings,
        packedRows = packedRows, total = 0, decoded = 0, packedBytes = 0, totalRows = 0, loadedRows = 0}
    stores[name], order[#order + 1] = store, name
    for _, payload in pairs(packedRows or rows) do
        store.totalRows = store.totalRows + 1
        if packedRows then store.packedBytes = store.packedBytes + #payload end
    end
    for _, column in pairs(columns) do
        for _, payload in pairs(column) do
            store.total, store.packedBytes = store.total + 1, store.packedBytes + #payload
        end
    end
    local function unpackField(row, field)
        local column = columns[field]
        local id = rawget(row, "__packedID")
        local payload = column and column[id]
        if not payload then return end
        local value = decode(payload, strings)
        rawset(row, field, value)
        -- Do not keep both representations after use.
        column[id] = nil
        store.decoded, store.packedBytes = store.decoded + 1, store.packedBytes - #payload
        return value
    end
    local meta = {__index = unpackField, __newindex = function(row, field, value)
        -- An explicit replacement wins over the bundled field, including nil.
        local column, id = columns[field], rawget(row, "__packedID")
        local payload = column and column[id]
        if payload then
            column[id] = nil
            store.decoded, store.packedBytes = store.decoded + 1, store.packedBytes - #payload
        end
        rawset(row, field, value)
    end}
    if packedRows then
        setmetatable(rows, {__index = function(_, id)
            local payload = packedRows[id]
            if not payload then return end
            local row = decode(payload, strings)
            rawset(row, "__packedID", id); setmetatable(row, meta)
            rawset(rows, id, row); packedRows[id] = nil
            store.loadedRows, store.packedBytes = store.loadedRows + 1, store.packedBytes - #payload
            return row
        end, __newindex = function(_, id, row)
            local payload = packedRows[id]
            if payload then
                packedRows[id] = nil
                store.loadedRows, store.packedBytes = store.loadedRows + 1, store.packedBytes - #payload
            end
            rawset(rows, id, row)
        end})
    else
        store.loadedRows = store.totalRows
        for id, row in pairs(rows) do rawset(row, "__packedID", id); setmetatable(row, meta) end
    end
end

-- Source/audit tooling calls this before iterating record fields with pairs.
-- Normal gameplay uses field access and never expands an entire database.
function ns.MaterializePackedData()
    for _, name in ipairs(order) do
        local store = stores[name]
        for id in pairs(store.packedRows or {}) do local row = store.rows[id] end
        for field, column in pairs(store.columns) do
            for id in pairs(column) do local value = store.rows[id][field] end
        end
        for _, row in pairs(store.rows) do rawset(row, "__packedID", nil); setmetatable(row, nil) end
    end
end

function ns.PackedDataStats()
    local result = {}
    for _, name in ipairs(order) do
        local store = stores[name]
        result[#result + 1] = {name = name, total = store.total, decoded = store.decoded, packedBytes = store.packedBytes,
            totalRows = store.totalRows, loadedRows = store.loadedRows}
    end
    return result
end

function ns.OptionalDataDiagnostics(output)
    for _, addon in ipairs({"WowTogether_QuestData", "WowTogether_ProfessionData", "WowTogether_DungeonData"}) do
        output("Optional data " .. addon .. ": " .. (ns.optionalDataState[addon] or "not loaded"))
    end
end

function ns.MemoryDiagnostics(output)
    -- Capability probe only; no garbage-collector manipulation or polling.
    local addons = C_AddOns
    local update = addons and addons.UpdateAddOnMemoryUsage or UpdateAddOnMemoryUsage
    local get = addons and addons.GetAddOnMemoryUsage or GetAddOnMemoryUsage
    output("Addon memory API: " .. (type(update) == "function" and type(get) == "function" and "present" or "unavailable"))
    ns.OptionalDataDiagnostics(output)
    if type(update) == "function" and type(get) == "function" then
        ns.ReadPublic(update)
        local names = {addonName, "WowTogether_QuestData", "WowTogether_ProfessionData", "WowTogether_DungeonData"}
        local total, main, optional = 0, nil, {}
        for index, name in ipairs(names) do
            local used = ns.ReadPublic(get, name)
            if ns.Public(used) and type(used) == "number" and used >= 0 then
                total = total + used
                if index == 1 then main = used else optional[name] = used end
            end
        end
        if main then
            local details = {}
            for _, name in ipairs({"WowTogether_QuestData", "WowTogether_ProfessionData", "WowTogether_DungeonData"}) do
                if optional[name] and optional[name] > 0 then
                    details[#details + 1] = name:gsub("WowTogether_", "") .. " " .. string.format("%.1f MiB", optional[name] / 1024)
                end
            end
            output("Addon Lua memory: " .. string.format("%.1f MiB total", total / 1024)
                .. " (main " .. string.format("%.1f MiB", main / 1024) .. "; data "
                .. (#details > 0 and table.concat(details, ", ") or "none loaded")
                .. "; client attribution includes allocated garbage).")
        end
    end
    for _, stat in ipairs(ns.PackedDataStats()) do
        output(string.format("Data %s: %d/%d records loaded; %d/%d detail fields unpacked; %.2f MiB still packed.",
            stat.name, stat.loadedRows, stat.totalRows, stat.decoded, stat.total, stat.packedBytes / 1048576))
    end
end
