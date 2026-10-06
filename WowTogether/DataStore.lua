local addonName, ns = ...

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

function ns.MemoryDiagnostics(output)
    -- Capability probe only; no garbage-collector manipulation or polling.
    local addons = C_AddOns
    local update = addons and addons.UpdateAddOnMemoryUsage or UpdateAddOnMemoryUsage
    local get = addons and addons.GetAddOnMemoryUsage or GetAddOnMemoryUsage
    output("Addon memory API: " .. (type(update) == "function" and type(get) == "function" and "present" or "unavailable"))
    if type(update) == "function" and type(get) == "function" then
        ns.ReadPublic(update)
        local used = ns.ReadPublic(get, addonName)
        if ns.Public(used) and type(used) == "number" then output(string.format("Addon Lua memory: %.1f MiB (client attribution; includes allocated garbage).", used / 1024)) end
    end
    for _, stat in ipairs(ns.PackedDataStats()) do
        output(string.format("Data %s: %d/%d records loaded; %d/%d detail fields unpacked; %.2f MiB still packed.",
            stat.name, stat.loadedRows, stat.totalRows, stat.decoded, stat.total, stat.packedBytes / 1048576))
    end
end
