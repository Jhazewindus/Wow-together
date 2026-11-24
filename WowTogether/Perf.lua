local addonName, ns = ...

-- A flight recorder for the addon's own cost.
--
-- An outside profiler says how much time the addon took, not what it was
-- doing. So the addon measures itself all the time, cheaply: every entry
-- point the game calls (events, the guide window's update, refreshes, the
-- leveling path's background work) is timed, summed in five-second windows
-- and kept in the saved variables. `/wt perf` prints it in a few chat lines,
-- naming the slowest single calls; `/wt perf clear` starts a new record.
local WINDOW, KEEP = 5, 120            -- seconds per window; windows kept (ten minutes)
local SAFE_SHARE, SAFE_WINDOWS = 0.30, 3
local SPIKE_MS = 50

local clock = type(debugprofilestop) == "function" and debugprofilestop or nil
local depth, current, windowStart = 0, nil, nil
local sections, order = {}, {}   -- entries the game called directly
local inner, innerOrder = {}, {}   -- work measured inside one of those
local total, spikeMs, spikeName = 0, 0, nil
local hot = 0

local function now()
    local value = ns.ReadPublic and ns.ReadPublic(GetTime)
    return type(value) == "number" and value or nil
end

local function section(store, names, name)
    local entry = store[name]
    if not entry then entry = {ms = 0, calls = 0}; store[name] = entry; names[#names + 1] = name end
    return entry
end

-- "name 12ms/3" for the costliest entries of one kind, resetting them.
local function summarise(store, names, limit)
    local top = {}
    for _, name in ipairs(names) do
        local entry = store[name]
        if entry.calls > 0 then top[#top + 1] = {name = name, ms = entry.ms, calls = entry.calls} end
        entry.ms, entry.calls = 0, 0
    end
    table.sort(top, function(a, b) return a.ms > b.ms end)
    local parts = {}
    for index = 1, math.min(limit, #top) do
        parts[index] = top[index].name .. " " .. math.floor(top[index].ms + 0.5) .. "ms/" .. top[index].calls
    end
    return table.concat(parts, ", ")
end

-- This addon's own memory, in MB, measured only when a report asks for it
-- (the client's per-addon accounting is itself costly to update).
local function ownMemory()
    local addons = C_AddOns
    local update = addons and addons.UpdateAddOnMemoryUsage or UpdateAddOnMemoryUsage
    local get = addons and addons.GetAddOnMemoryUsage or GetAddOnMemoryUsage
    if type(update) ~= "function" or type(get) ~= "function" then return nil end
    update()
    local total = 0
    for _, name in ipairs({addonName, "WowTogether_QuestData", "WowTogether_ProfessionData", "WowTogether_DungeonData"}) do
        local value = ns.ReadPublic(get, name)
        if type(value) == "number" then total = total + value end
    end
    return math.floor(total / 1024 + 0.5)
end

local function log()
    if not ns.db then return nil end
    if type(ns.db.perfLog) ~= "table" then ns.db.perfLog = {} end
    return ns.db.perfLog
end

local function closeWindow(time)
    local seconds = windowStart and time - windowStart or 0
    if seconds > 0 then
        local top, parts = summarise(sections, order, 4), summarise(inner, innerOrder, 6)
        local share = total / (seconds * 1000)
        local record = {
            t = math.floor(time), ms = math.floor(total + 0.5), share = math.floor(share * 1000 + 0.5) / 10,
            top = top, parts = parts ~= "" and parts or nil, spike = spikeMs >= SPIKE_MS and (spikeName .. " " .. math.floor(spikeMs + 0.5) .. "ms") or nil,
            -- The whole interface's Lua heap (every addon and the default UI
            -- share it), not this addon's own memory.
            memory = math.floor((collectgarbage("count") or 0) / 1024 + 0.5),
            refreshes = ns.refreshStats and ns.refreshStats.completed or 0,
            sends = ns.syncStats and ns.syncStats.sendAttempts or 0,
            throttled = ns.syncStats and ns.syncStats.throttled or 0,
            safe = ns.safeMode == true or nil,
        }
        local list = log()
        if list then
            list[#list + 1] = record
            while #list > KEEP do table.remove(list, 1) end
        end
        ns.perfLast = record
        hot = share > SAFE_SHARE and hot + 1 or 0
        -- This build records only: nothing is slowed down automatically.
    end
    windowStart, total, spikeMs, spikeName = time, 0, 0, nil
end

-- Wrap an entry point the game calls. Only the outermost call counts
-- towards the total; nested ones are still attributed by name.
function ns.PerfBegin(name, top)
    if not clock then return nil end
    -- `top` marks an entry the game itself calls (an event, a frame update):
    -- nothing of ours can be running above it, so an earlier error that
    -- skipped its PerfEnd cannot leave the depth stuck.
    if top then depth = 0 end
    depth = depth + 1
    return clock()
end

function ns.PerfEnd(name, started)
    if not started then return end
    local elapsed = clock() - started
    depth = math.max(0, depth - 1)
    if depth > 0 then
        -- Measured inside another entry: attributed by name, counted once (in the outer one).
        local entry = section(inner, innerOrder, name)
        entry.ms, entry.calls = entry.ms + elapsed, entry.calls + 1
        return
    end
    local entry = section(sections, order, name)
    entry.ms, entry.calls = entry.ms + elapsed, entry.calls + 1
    total = total + elapsed
    if elapsed > spikeMs then spikeMs, spikeName = elapsed, name end
    local time = now()
    if not time then return end
    if not windowStart then windowStart = time
    elseif time - windowStart >= WINDOW then closeWindow(time) end
end

-- A few chat lines: cheap enough to run on a client that is struggling.
function ns.PerfReport(output)
    output = output or ns.Print
    local list = log() or {}
    if not clock then output("Performance recorder: this client has no high-resolution timer."); return end
    if #list == 0 then output("Performance recorder: no five-second window recorded yet."); return end
    local worst, sum, slow = list[1], 0, {}
    for _, record in ipairs(list) do
        sum = sum + (record.share or 0)
        if (record.share or 0) > (worst.share or 0) then worst = record end
        -- A single call over 16 ms is a dropped frame: collect the slowest by name.
        local name, ms = string.match(record.spike or "", "^(.-) (%d+)ms$")
        ms = tonumber(ms)
        if name and ms and (not slow[name] or ms > slow[name]) then slow[name] = ms end
    end
    local last = list[#list]
    if ns.testBuild then output("Test build: " .. ns.testBuild .. ".") end
    output("Performance: " .. #list .. " windows of " .. WINDOW .. " s; average "
        .. (math.floor(sum / #list * 10 + 0.5) / 10) .. "% of each second, worst " .. (worst.share or 0) .. "%."
        .. (ns.safeMode and " SAFE MODE is on." or ""))
    output("Worst window: " .. (worst.top or "") .. (worst.spike and ("; spike " .. worst.spike) or "") .. "."
        .. (worst.parts and (" Inside those: " .. worst.parts .. ".") or ""))
    output("Latest window: " .. (last.share or 0) .. "% - " .. (last.top or "") .. "."
        .. (last.parts and (" Inside those: " .. last.parts .. ".") or ""))
    local spikes = {}
    for name, ms in pairs(slow) do spikes[#spikes + 1] = {name = name, ms = ms} end
    table.sort(spikes, function(a, b) return a.ms > b.ms end)
    if #spikes > 0 then
        local text = {}
        for index = 1, math.min(5, #spikes) do text[index] = spikes[index].name .. " " .. spikes[index].ms .. " ms" end
        output("Slowest single calls (each is a visible hitch): " .. table.concat(text, ", ") .. ".")
    end
    local own = ownMemory()
    output("Memory: Wow Together " .. (own and (own .. " MB") or "unknown") .. "; whole interface (all addons) "
        .. (last.memory or 0) .. " MB now, " .. (list[1].memory or 0) .. " MB at the start of this record.")
    local kinds = ns.syncStats and ns.syncStats.kinds
    if kinds and next(kinds) then
        local parts = {}
        for kind, count in pairs(kinds) do parts[#parts + 1] = {kind = kind, count = count} end
        table.sort(parts, function(a, b) return a.count > b.count end)
        local text = {}
        for index = 1, math.min(8, #parts) do text[index] = parts[index].kind .. " x" .. parts[index].count end
        output("Party messages queued this session, by kind: " .. table.concat(text, ", ") .. ".")
    end
    if ns.safeModeReason then output("Safe mode reason: " .. ns.safeModeReason) end
end

function ns.PerfCommand(argument)
    argument = string.lower(argument or "")
    if argument == "clear" then
        if ns.db then ns.db.perfLog = {} end
        ns.Print("Performance record cleared.")
    else ns.PerfReport() end
end

-- For tests and for clients without `debugprofilestop`.
function ns.PerfSetClock(fn) clock = fn end
function ns.PerfWindow() return WINDOW end

-- Every timer the addon starts goes through here, so the work it does later
-- is timed under a name ("plan", "path", or "timer:<file>"). Before this,
-- anything run from a timer was invisible to the record: a profile showed
-- the addon at 70% of the game's time while this report said 0.3%.
function ns.After(label, delay, callback)
    if type(callback) ~= "function" then return C_Timer.After(delay, callback) end
    return C_Timer.After(delay, function(...)
        local started = ns.PerfBegin(label, true)
        callback(...)
        if started then ns.PerfEnd(label, started) end
    end)
end
