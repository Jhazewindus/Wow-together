local addonName, ns = ...

local BUCKETS = 61
local SECTIONS = {
    [1] = "minimap", [2] = "navigation", [3] = "arrow",
    [4] = "travel", [5] = "recorders", [6] = "probe",
}
local ledger, lastHeapKB, peakHeapKB = {}, nil, nil
for id = 1, #SECTIONS do
    local values, seconds = {}, {}
    for slot = 1, BUCKETS do values[slot], seconds[slot] = 0, -1 end
    ledger[id] = {values = values, seconds = seconds}
end

ns.MemorySampleSection = {minimap = 1, navigation = 2, arrow = 3, travel = 4, recorders = 5, probe = 6}

local function numeric(value)
    return ns.Public(value) and type(value) == "number" and value == value and value >= 0 and value < math.huge
end

local function heapKB()
    if type(collectgarbage) ~= "function" then return end
    local value = ns.ReadPublic(collectgarbage, "count")
    if not numeric(value) then return end
    if not lastHeapKB or value < lastHeapKB then peakHeapKB = value
    elseif not peakHeapKB or value > peakHeapKB then peakHeapKB = value end
    lastHeapKB = value
    return value
end

function ns.StartMemorySample(section)
    if not ledger[section] then return end
    return heapKB()
end

function ns.EndMemorySample(section, before)
    local stats = ledger[section]
    if not stats or not numeric(before) then heapKB(); return end
    local after = heapKB()
    local now = ns.ReadPublic(GetTime)
    if not numeric(after) or not numeric(now) then return end
    local second = math.floor(now)
    local slot = second % BUCKETS + 1
    if stats.seconds[slot] ~= second then stats.seconds[slot], stats.values[slot] = second, 0 end
    local delta = after - before
    if delta > 0 then stats.values[slot] = stats.values[slot] + delta end
    if section == 6 then ns.lastProbeAllocationKB = math.max(0, delta) end
end

function ns.AllocationDiagnostics(output)
    local now = ns.ReadPublic(GetTime)
    local current = heapKB()
    local second = numeric(now) and math.floor(now) or 0
    local total, sums = 0, {0, 0, 0, 0, 0, 0}
    for id = 1, #SECTIONS do
        local stats = ledger[id]
        local sum = 0
        for slot = 1, BUCKETS do
            local age = second - stats.seconds[slot]
            if age >= 0 and age < 60 then sum = sum + stats.values[slot] end
        end
        sums[id] = sum
        if id < 6 then total = total + sum end
    end
    output(string.format("Heap increases observed (last 60 s): %.1f MiB total — minimap %.1f · navigation %.1f · arrow %.1f · travel %.1f · recorders %.1f",
        total / 1024, sums[1] / 1024, sums[2] / 1024, sums[3] / 1024, sums[4] / 1024, sums[5] / 1024))
    output("Lua heap: " .. (current and string.format("%.1f MiB now", current / 1024) or "unavailable")
        .. (peakHeapKB and string.format("; sampled peak since last observed reduction %.1f MiB", peakHeapKB / 1024) or "")
        .. ". These are sampled increases; collection between samples can hide churn. Compare after a manual full collection to check retained memory.")
    output(string.format("Last /wt probe allocation: %.1f KiB (probe section allocated during the previous report).",
        ns.lastProbeAllocationKB or 0))
end
