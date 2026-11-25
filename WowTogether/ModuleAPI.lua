local addonName, ns = ...

-- The optional modules load after the core. Keep their integration here so a
-- module never needs the core's saved variables, route internals, or UI frames.
ns.GoldAPIVersion = 2
ns.STEP_SYMBOLS = ns.STEP_SYMBOLS or {}

local modules, names, order, options, syncKinds, exportHooks, stops = {}, {}, {}, {}, {}, {}, {}
local goldFunctions = {}
local moduleLoops, farmSessions = {}, {}
local gatheringObservers = {}
local activeFarmSession, loopFrame = nil, nil
local goldHookNames = {Price = "goldPrice", Suggestions = "goldSuggestions", SessionCard = "goldSessionCard"}
local reservedKinds = {H=true, Q=true, T=true, S=true, C=true, O=true, K=true,
    Y=true, R=true, Z=true, G=true, P=true, D=true, V=true, W=true}
local function validName(name)
    return type(name) == "string" and string.match(name, "^[A-Za-z][A-Za-z0-9_]*$") ~= nil
end
local function safeCardText(value, maximum)
    return ns.Public(value) and type(value) == "string" and value ~= "" and #value <= maximum
        and not string.find(value, "[%z\1-\8\11\12\14-\31\127]")
end
local function safeActionCard(spec, suggestion)
    if type(spec) ~= "table" or not safeCardText(spec.title, 100)
        or not safeCardText(spec.detail, 360) or type(spec.action) ~= "function"
        or type(spec.start) == "function" or type(spec.inspect) == "function" then return end
    for key in pairs(spec) do
        if suggestion and key ~= "key" and key ~= "title" and key ~= "detail"
            and key ~= "priority" and key ~= "action" then return end
        if not suggestion and key ~= "title" and key ~= "detail" and key ~= "action" then return end
    end
    if suggestion then
        if not safeCardText(spec.key, 64) or not string.match(spec.key, "^[%w:_%-]+$")
            or not ns.Public(spec.priority) or not ns.GuideInteger(spec.priority, 1000) or spec.priority < 1 then return end
        return {key = "gold:" .. spec.key, kind = "gold", category = "Gold", title = spec.title,
            detail = spec.detail, priority = spec.priority, action = "Follow", start = spec.action}
    end
    return {kind = "gold", category = "Gold session", title = spec.title,
        detail = spec.detail, action = spec.action}
end
local function safeSuggestions(value)
    if type(value) ~= "table" then return end
    local count = #value
    if count > 5 then return end
    for key in pairs(value) do
        if not ns.Public(key) or not ns.GuideInteger(key, 5) or key < 1 or key > count then return end
    end
    local result, keys = {}, {}
    for index = 1, count do
        local card = safeActionCard(value[index], true)
        if not card or keys[card.key] then return end
        keys[card.key] = true; result[#result + 1] = card
    end
    return result
end
local function copySessionSummary(summary)
    if type(summary) ~= "table" or not safeCardText(summary.title, 120)
        or not ns.Public(summary.quests) or not ns.Public(summary.xp)
        or not ns.GuideInteger(summary.quests, 4096)
        or not ns.GuideInteger(summary.xp, 10000000000)
        or not ns.Public(summary.seconds) or type(summary.seconds) ~= "number"
        or summary.seconds ~= summary.seconds or summary.seconds < 0 or summary.seconds > 100000000 then return end
    return {title = summary.title, quests = summary.quests, xp = summary.xp, seconds = summary.seconds,
        xpKnown = summary.xpKnown == true, xpPartial = summary.xpPartial == true,
        timePartial = summary.timePartial == true,
        startLevel = ns.GuideInteger(summary.startLevel, 60) and summary.startLevel or nil,
        endLevel = ns.GuideInteger(summary.endLevel, 60) and summary.endLevel or nil}
end

local function moduleRecord(name)
    if not validName(name) or not names[string.lower(name)] then return nil end
    for _, registered in ipairs(order) do
        if string.lower(registered) == string.lower(name) then return registered, modules[registered] end
    end
end

function ns.PublishGoldFunction(name, callback)
    if not goldHookNames[name] then return false, "Unsupported Gold function name." end
    if type(callback) ~= "function" then return false, "Gold function must be callable." end
    goldFunctions[name] = callback
    ns.RunHooks("goldFunctionPublished", name)
    if name == "Suggestions" and ns.ScheduleSync then ns.ScheduleSync() end
    return true, nil
end

ns.hooks.goldPrice[#ns.hooks.goldPrice + 1] = function(itemID, quantity)
    local callback = goldFunctions.Price
    if not callback then return false end
    return true, callback(itemID, quantity)
end
ns.hooks.goldSuggestions[#ns.hooks.goldSuggestions + 1] = function()
    local callback = goldFunctions.Suggestions
    if not callback then return false end
    local cards = safeSuggestions(callback())
    if not cards then return false end
    return true, cards
end
ns.hooks.goldSessionCard[#ns.hooks.goldSessionCard + 1] = function(summary)
    local callback = goldFunctions.SessionCard
    local copy = copySessionSummary(summary)
    if not callback or not copy then return false end
    local card = safeActionCard(callback(copy), false)
    if not card then return false end
    return true, card
end
local function optionKey(name, key)
    return type(key) == "string" and #key > #name + 1
        and string.sub(key, 1, #name + 1) == string.lower(name) .. "."
end

local function addDropdownEntry(control, key, title, callback)
    if not control or control.options[key] then return end
    local index = #control.entries + 1
    control.entries[index] = {key, title}
    local row = ns.UIButton(control.menu, title, control:GetWidth() - 8, function()
        control.menu:Hide(); callback(key)
    end)
    row:SetHeight(26); row:SetPoint("TOPLEFT", 4, -4 - (index - 1) * 28)
    row.caption:SetJustifyH("LEFT")
    control.options[key] = row
    control.menu:SetHeight(index * 28 + 8)
end

local function addTab(name)
    if not ns.ui or not modules[name].tab then return end
    local entry = modules[name]
    local key = "module:" .. string.lower(name)
    addDropdownEntry(ns.ui.viewChoice, key, entry.tab.title, ns.SetFilter)
    local page = CreateFrame("Frame", nil, ns.ui.content)
    page:SetPoint("TOPLEFT", 0, 0)
    page:SetSize(ns.ui.contentWidth or 760, 250)
    page:Hide()
    entry.page = page
end

local function addSettings(name)
    if not ns.settings then return end
    local group = modules[name].settingsGroup
    if not group then return end
    local frame, key = ns.settings, "module:" .. string.lower(name)
    if frame.pages[key] then return end
    local page = CreateFrame("Frame", nil, frame)
    page:SetPoint("TOPLEFT", 22, -104); page:SetSize(576, 374)
    frame.pages[key] = page
    page.heading = ns.UILabel(page, "GameFontNormal", 13)
    page.heading:SetPoint("TOPLEFT", 32, -2); page.heading:SetText(group.title)
    page.description = ns.UILabel(page, nil, 10)
    page.description:SetPoint("TOPLEFT", 32, -22)
    page.description:SetSize(540, 28); page.description:SetWordWrap(true)
    page.description:SetText(group.description or "")
    local cursor = 54
    for _, item in ipairs(group.entries or {}) do
        local label = ns.UILabel(page, "GameFontNormal", 12)
        label:SetPoint("TOPLEFT", 32, -cursor); label:SetSize(500, 16)
        label:SetText(item.label)
        local help = ns.UILabel(page, nil, 10)
        help:SetPoint("TOPLEFT", 32, -cursor - 18)
        help:SetSize(500, 30); help:SetWordWrap(true)
        help:SetText(item.help or "")
        if item.choices then
            local choice = ns.UIDropdown(page, item.choices, 200, function(value) ns.SetOption(item.key, value) end)
            choice:SetPoint("TOPRIGHT", -4, -cursor + 4)
            frame.dropdowns[item.key] = choice
        else
            local check = CreateFrame("CheckButton", nil, page, "UICheckButtonTemplate")
            check:SetSize(24, 24); check:SetPoint("TOPLEFT", 0, -cursor + 2)
            check:SetScript("OnClick", function(self) ns.SetOption(item.key, self:GetChecked() == true) end)
            frame.checks[item.key] = check
        end
        cursor = cursor + 65
    end
    page.contentHeight = cursor
    page:Hide()
    addDropdownEntry(frame.section, key, group.title, function(section)
        frame.sectionKey = section; ns.RenderSettings()
    end)
end

ns.hooks.optionGet[#ns.hooks.optionGet + 1] = function(key)
    local item = options[key]
    if not item then return false end
    local value = item.group.get(key)
    if value == nil then value = item.default end
    return true, value
end
ns.hooks.optionSet[#ns.hooks.optionSet + 1] = function(key, value)
    local item = options[key]
    if not item then return false end
    if type(value) ~= type(item.default) then return true, false end
    item.group.set(key, value)
    if ns.RenderSettings then ns.RenderSettings() end
    return true, true
end
ns.hooks.uiCreated[#ns.hooks.uiCreated + 1] = function()
    for _, name in ipairs(order) do addTab(name) end
end
ns.hooks.hubTabs[#ns.hooks.hubTabs + 1] = function()
    local tabs = {}
    for _, name in ipairs(order) do
        local entry = modules[name]
        if entry.tab then
            tabs[#tabs + 1] = {key = "module:" .. string.lower(name), name = name,
                title = entry.tab.title, render = entry.tab.render}
        end
    end
    return tabs
end
ns.hooks.settingsCreated[#ns.hooks.settingsCreated + 1] = function()
    for _, name in ipairs(order) do addSettings(name) end
end
ns.hooks.render[#ns.hooks.render + 1] = function()
    if not ns.ui then return end
    for _, name in ipairs(order) do
        local entry = modules[name]
        if entry.page then
            local selected = entry.tab and ns.filter == "module:" .. string.lower(name)
            entry.page:SetShown(selected == true)
            if selected then
                ns.ui.empty:Hide()
                ns.ui.viewDescription:SetText(entry.tab.title)
                ns.ui.hint:SetText("")
                entry.tab.render(entry.page)
                ns.ui.content:SetHeight(math.max(250, entry.page:GetHeight() or 250))
            end
        end
    end
end
ns.hooks.slash[#ns.hooks.slash + 1] = function(command)
    local word, rest = string.match(command or "", "^%s*([%w_]+)%s*(.-)%s*$")
    local entry = word and modules[word] or nil
    if not entry and word then
        for name, spec in pairs(modules) do
            if string.lower(name) == string.lower(word) then entry = spec; break end
        end
    end
    if entry and entry.slash then return true, entry.slash(rest) end
    return false
end
ns.hooks.diagnostics[#ns.hooks.diagnostics + 1] = function()
    local lines = {}
    for _, name in ipairs(order) do
        local probe = modules[name].probe
        if probe then
            lines[#lines + 1] = "\n" .. name .. ":"
            probe(function(line) lines[#lines + 1] = tostring(line) end)
        end
    end
    return table.concat(lines, "\n")
end

-- tab.render(page) owns only its page. settingsGroup entries are
-- {key, label, help, default, choices?}; get/set use the module's own store.
function ns.RegisterModule(name, spec)
    assert(validName(name) and type(spec) == "table", "Invalid module registration")
    assert(not names[string.lower(name)], "Duplicate module: " .. name)
    if spec.tab then
        assert(type(spec.tab) == "table" and type(spec.tab.title) == "string"
            and type(spec.tab.render) == "function", "Invalid module tab")
    end
    if spec.slash then assert(type(spec.slash) == "function", "Invalid module slash handler") end
    if spec.probe then assert(type(spec.probe) == "function", "Invalid module probe") end
    local group = spec.settingsGroup
    if group then
        assert(type(group) == "table" and type(group.title) == "string"
            and type(group.entries) == "table", "Invalid module settings")
        if #group.entries > 0 then
            assert(type(group.get) == "function" and type(group.set) == "function", "Missing module settings store")
        end
        for _, item in ipairs(group.entries) do
            assert(optionKey(name, item.key) and type(item.label) == "string"
                and item.default ~= nil and not options[item.key], "Invalid module setting")
            if item.choices then
                assert(type(item.choices) == "table", "Invalid module choices")
            else assert(type(item.default) == "boolean", "Checkbox default must be boolean") end
        end
    end
    modules[name], names[string.lower(name)], order[#order + 1] = spec, true, name
    for _, item in ipairs(group and group.entries or {}) do
        options[item.key] = {group = group, default = item.default}
    end
    addTab(name); addSettings(name)
    if spec.tab then ns.RunHooks("hubTabRegistered", name, spec.tab) end
    return true
end

function ns.RegisterSyncKind(letter, handler)
    assert(type(letter) == "string" and string.match(letter, "^[A-Z]$")
        and type(handler) == "function", "Invalid sync registration")
    assert(not reservedKinds[letter] and not syncKinds[letter], "Duplicate sync kind: " .. letter)
    syncKinds[letter] = handler
    return true
end

-- Module packets use the same validated party transport as core traffic.
-- Keep module payloads behind a registered kind and in the background lane
-- unless the caller explicitly asks for normal-priority delivery.
function ns.QueueModuleSync(letter, payload, priority)
    if type(letter) ~= "string" or not string.match(letter, "^[A-Z]$")
        or not syncKinds[letter] or type(payload) ~= "string" or payload == ""
        or string.find(payload, "[\r\n%z]") then return false end
    priority = priority or "background"
    if priority ~= "background" and priority ~= "now" then return false end
    local message = "1|" .. letter .. "|" .. payload
    if #message > 255 or type(ns.QueueMessage) ~= "function" then return false end
    return ns.QueueMessage(message, priority) == true
end
ns.hooks.syncReceive[#ns.hooks.syncReceive + 1] = function(message, sender)
    local letter = type(message) == "string" and string.match(message, "^1|([A-Z])|")
    local handler = letter and syncKinds[letter]
    if not handler then return false end
    local ok, accepted, reason = pcall(handler, message, sender)
    return true, ok and accepted == true, ok and reason or "module handler failed"
end

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end
-- Return a closed route with ordered points, routed legs and total seconds.
-- Exact Held-Karp search is bounded to ten nodes; larger loops use a bounded
-- nearest-neighbour search over the same proven walking paths.
function ns.TrailLoop(points)
    if type(points) ~= "table" or #points > 24 then return nil end
    local count = #points
    if count == 0 then return {points = {}, legs = {}, seconds = 0} end
    for _, point in ipairs(points) do if not ns.ValidTravelPoint(point) then return nil end end
    if count == 1 then return {points = {points[1], points[1]}, legs = {}, seconds = 0} end
    -- Legs are costed by straight-line distance at running speed.
    --
    -- This used to search for a walking path between every pair of points:
    -- 552 searches for 24 points, all in one go. Starting a farm froze the
    -- game for minutes (18 seconds in the host, which is roughly ten times
    -- faster than the client). An addon cannot see terrain anyway; the order
    -- of a loop through one creature's spawn points is decided well enough by
    -- distance, and a module that wants the real path for a leg can still
    -- ask for it, one leg at a time.
    local RUN_YARDS_PER_SECOND = 7
    local costs, scaleCache = {}, {}
    for i = 1, count do
        costs[i] = {}
        for j = 1, count do
            if i ~= j then
                local distance = ns.TravelPointDistance(points[i], points[j], scaleCache)
                if finite(distance) and distance >= 0 then costs[i][j] = distance / RUN_YARDS_PER_SECOND end
            end
        end
    end
    local sequence = {1}
    if count <= 10 then
        local size, dp = 2 ^ (count - 1), {}
        local function bit(mask, index) return math.floor(mask / 2 ^ (index - 2)) % 2 == 1 end
        for mask = 1, size - 1 do
            dp[mask] = {}
            for last = 2, count do
                if bit(mask, last) then
                    local previous = mask - 2 ^ (last - 2)
                    if previous == 0 then
                        if costs[1][last] then dp[mask][last] = {costs[1][last], 1} end
                    else
                        for prior = 2, count do
                            local row = dp[previous] and dp[previous][prior]
                            if row and costs[prior][last] then
                                local cost = row[1] + costs[prior][last]
                                if not dp[mask][last] or cost < dp[mask][last][1] then
                                    dp[mask][last] = {cost, prior}
                                end
                            end
                        end
                    end
                end
            end
        end
        local mask, last, best = size - 1, nil, nil
        for index = 2, count do
            local row = dp[mask][index]
            if row and costs[index][1] and (not best or row[1] + costs[index][1] < best) then
                best, last = row[1] + costs[index][1], index
            end
        end
        if not last then return nil end
        local reversed = {}
        while last ~= 1 do
            reversed[#reversed + 1] = last
            local previous = dp[mask][last][2]
            mask = mask - 2 ^ (last - 2)
            last = previous
        end
        for index = #reversed, 1, -1 do sequence[#sequence + 1] = reversed[index] end
    else
        local used = {[1] = true}
        for _ = 2, count do
            local current, nextIndex, best = sequence[#sequence], nil, nil
            for index = 2, count do
                if not used[index] and costs[current][index]
                    and (not best or costs[current][index] < best) then
                    nextIndex, best = index, costs[current][index]
                end
            end
            if not nextIndex then return nil end
            used[nextIndex] = true; sequence[#sequence + 1] = nextIndex
        end
    end
    -- Nearest-neighbour order crosses itself; uncross it. Each pass looks at
    -- every pair of legs and reverses the stretch between them when that is
    -- shorter. A few passes settle two dozen points.
    if count > 10 then
        for _ = 1, 8 do
            local improved = false
            for i = 2, count - 1 do
                for j = i + 1, count do
                    local a, b = sequence[i - 1], sequence[i]
                    local c, d = sequence[j], sequence[j + 1] or sequence[1]
                    local now = (costs[a][b] or math.huge) + (costs[c][d] or math.huge)
                    local swapped = (costs[a][c] or math.huge) + (costs[b][d] or math.huge)
                    if swapped + 0.001 < now then
                        local low, high = i, j
                        while low < high do sequence[low], sequence[high] = sequence[high], sequence[low]; low, high = low + 1, high - 1 end
                        improved = true
                    end
                end
            end
            if not improved then break end
        end
    end
    sequence[#sequence + 1] = 1
    local loop = {points = {}, legs = {}, seconds = 0}
    for index, pointIndex in ipairs(sequence) do
        loop.points[index] = points[pointIndex]
        if index > 1 then
            local seconds = costs[sequence[index - 1]][pointIndex]
            if not seconds then return nil end
            loop.legs[#loop.legs + 1] = {seconds = seconds, estimated = true, legs = {}}
            loop.seconds = loop.seconds + seconds
        end
    end
    return loop
end

local function removeStops(route)
    if not route or route.moduleLoop or type(route.stops) ~= "table" then return end
    for index = #route.stops, 1, -1 do
        if route.stops[index].moduleStop then table.remove(route.stops, index) end
    end
end
local function applyStops()
    local route = ns.selectedRoute
    if not route or route.moduleLoop or type(route.stops) ~= "table" then return end
    removeStops(route)
    local before = {}
    for _, name in ipairs(order) do
        for _, stop in ipairs(stops[name] or {}) do before[#before + 1] = stop end
    end
    for index = #before, 1, -1 do table.insert(route.stops, 1, before[index]) end
end
function ns.PushGuideStop(stop)
    assert(type(stop) == "table" and validName(stop.module) and modules[stop.module]
        and stop.kind == "farm" and ns.ValidTravelPoint(stop)
        and type(stop.label) == "string" and stop.label ~= ""
        and type(stop.reason) == "string" and stop.reason ~= "", "Invalid module farm stop")
    local copy = {}
    for key, value in pairs(stop) do copy[key] = value end
    copy.id = copy.id or 0
    copy.title = copy.title or copy.label or "Farm"
    copy.label = copy.label or copy.title
    copy.moduleStop = true
    stops[stop.module] = stops[stop.module] or {}
    stops[stop.module][#stops[stop.module] + 1] = copy
    applyStops()
    if ns.ScheduleRefresh then ns.ScheduleRefresh(true) end
    return true
end
function ns.ClearModuleStops(name)
    assert(validName(name), "Invalid module name")
    stops[name] = nil
    applyStops()
    if ns.ScheduleRefresh then ns.ScheduleRefresh(true) end
end
ns.hooks.routeBeforeUpdate[#ns.hooks.routeBeforeUpdate + 1] = function()
    if not (ns.selectedRoute and ns.selectedRoute.moduleLoop) then removeStops(ns.selectedRoute) end
end
ns.hooks.routeAfterUpdate[#ns.hooks.routeAfterUpdate + 1] = function()
    applyStops()
end
ns.hooks.stopIcon[#ns.hooks.stopIcon + 1] = function(stop)
    if stop and stop.kind == "farm" and stop.moduleStop then return true, ns.StepIconTexture("farm") end
    return false
end
ns.hooks.stopSymbol[#ns.hooks.stopSymbol + 1] = function(stop)
    if stop and stop.kind == "farm" and stop.moduleStop then return true, "G" end
    return false
end
ns.hooks.destinationDecision[#ns.hooks.destinationDecision + 1] = function(stop, guide, route)
    if stop and stop.kind == "farm" and stop.moduleStop then
        return true, {code = "module-farm", why = stop.reason, specificBenefit = true, confidence = "module-provided"}
    end
    return false
end

-- Give module-provided farm work the same structured player-facing fields as
-- native steps. The module supplies its actionable instruction and reason;
-- the core does not invent Gold-specific farming advice.
ns.hooks.stepPresentation[#ns.hooks.stepPresentation + 1] = function(stop, facts, guide, route, state)
    if stop and stop.kind == "farm" and stop.moduleStop then
        local why = string.gsub(string.gsub(stop.reason, "%s+$", ""), "[%.!]+$", "")
        local distance = state and ns.Public(state.distance) and type(state.distance) == "number"
            and ns.FormatDistance(state.distance) or nil
        local seconds = state and (state.walkSeconds or state.flight and (state.flight.remaining or state.flight.elapsed))
        local timing = ns.Public(seconds) and type(seconds) == "number" and seconds > 0
            and (seconds < 60 and ("~" .. math.floor(seconds) .. " s")
                or ("~" .. math.floor(seconds / 60) .. " min " .. string.format("%02d", math.floor(seconds % 60)) .. " s"))
            or nil
        local location = ns.StopLocationText(stop)
        return true, {kind = "farm", icon = ns.StepIconTexture("farm"), title = stop.title or stop.label,
            stepLine = "Optional module task", what = stop.label, why = why,
            status = "Optional, on the way", statusColor = "text",
            time = distance and timing and (distance .. ", " .. timing) or distance or timing,
            location = location, details = {}, decision = ns.GuideDestinationDecision(stop, guide, route),
            stop = stop, goal = stop, facts = facts or {stop = stop}}
    end
    return false
end

-- Hooks return an array of observation event tables. They are appended to the
-- existing /wt research JSON events array without exposing core research state.
function ns.ResearchExportHook(fn)
    assert(type(fn) == "function", "Invalid research export hook")
    exportHooks[#exportHooks + 1] = fn
    return true
end

local function safeDenseArray(value, maximum)
    if type(value) ~= "table" or not ns.Public(value) or #value > maximum then return false end
    local count = 0
    for key in pairs(value) do
        if not ns.Public(key) or not ns.GuideInteger(key, maximum) or key < 1 or key > #value then return false end
        count = count + 1
    end
    return count == #value
end

local function safeSource(value)
    return ns.Public(value) and type(value) == "string" and #value > 0 and #value <= 240
        and not string.find(value, "[%z\1-\8\11\12\14-\31\127]")
end

local function prepareFarmPrior(record, mapID)
    if type(record) ~= "table" or not ns.Public(record)
        or not ns.GuideInteger(record.npcID, 2147483647) or record.npcID < 1
        or not safeCardText(record.name, 100)
        or not ns.GuideInteger(record.minLevel, 255) or record.minLevel < 1
        or not ns.GuideInteger(record.maxLevel, 255) or record.maxLevel < record.minLevel
        or record.confidence ~= "legacy, unconfirmed"
        or not ns.GuideInteger(record.mapID, 1000000) or record.mapID < 1
        or mapID and record.mapID ~= mapID or not safeCardText(record.zoneName, 100)
        or type(record.spawnPoints) ~= "table" or #record.spawnPoints > 24
        or type(record.loot) ~= "table" or #record.loot > 200
        or type(record.sources) ~= "table" then return nil end
    local sources = record.sources
    for _, key in ipairs({"npcID", "name", "level", "mapID", "zoneName", "spawnPoints", "loot"}) do
        if not safeSource(sources[key]) then return nil end
    end
    local copy = {npcID = record.npcID, name = record.name, minLevel = record.minLevel,
        maxLevel = record.maxLevel, confidence = record.confidence, mapID = record.mapID, zoneName = record.zoneName,
        spawnPoints = {}, loot = {}, sources = {}}
    for _, key in ipairs({"npcID", "name", "level", "mapID", "zoneName", "spawnPoints", "loot"}) do
        copy.sources[key] = sources[key]
    end
    return copy
end

local function clockMilliseconds()
    if type(debugprofilestop) ~= "function" then return nil end
    local value = ns.ReadPublic(debugprofilestop)
    return finite(value) and value or nil
end

local function queueNext(callback)
    if type(ns.After) == "function" then
        local okay = pcall(ns.After, "timer:ModuleAPI", 0, callback)
        return okay
    end
    return false
end

local function searchFarmPriors(filter, onDone, ...)
    if type(filter) ~= "table" or not ns.Public(filter)
        or not ns.GuideInteger(filter.minLevel, 255) or filter.minLevel < 1
        or not ns.GuideInteger(filter.maxLevel, 255) or filter.maxLevel < filter.minLevel
        or filter.mapID ~= nil and (not ns.GuideInteger(filter.mapID, 1000000) or filter.mapID < 1)
        or not ns.GuideInteger(filter.limit, 50) or filter.limit < 1
        or type(onDone) ~= "function" or select("#", ...) > 0 then
        return false, "Invalid farm-prior search arguments."
    end
    for key in pairs(filter) do
        if key ~= "minLevel" and key ~= "maxLevel" and key ~= "mapID" and key ~= "limit" then
            return false, "Unknown farm-prior filter field."
        end
    end
    if type(ns.EnsureOptionalData) == "function" then ns.EnsureOptionalData("WowTogether_GoldData") end
    local data = ns.farmPriorData
    local recordCount = type(data) == "table" and (data.count or #data.records) or 0
    if type(data) ~= "table" or type(data.records) ~= "table" or not ns.GuideInteger(recordCount, 1000000) or recordCount == 0 then
        return false, "Current-game farm-prior data is unavailable."
    end
    if not clockMilliseconds() or not C_Timer or type(C_Timer.After) ~= "function" then
        return false, "Farm-prior search needs a frame clock and timer."
    end
    local index, result, pending, done = 1, {}, nil, false
    local function finish()
        if done then return end
        done = true
        local okay = pcall(onDone, result)
        if not okay then ns.moduleFarmPriorCallbackError = true end
    end
    local function step()
        if done then return end
        local began = clockMilliseconds()
        if not began then finish(); return end
        while pending or index <= recordCount do
            if pending then
                local record, copy = pending.source, pending.copy
                local point = record.spawnPoints[pending.spawnIndex]
                local item = not point and record.loot[pending.lootIndex]
                if point then
                    if type(point) ~= "table" or not ns.Public(point) or point.mapID ~= record.mapID
                        or not ns.ValidTravelPoint(point) then pending.valid = false
                    else
                        copy.spawnPoints[pending.spawnIndex] = {mapID = point.mapID, x = point.x, y = point.y,
                            source = safeSource(point.source) and point.source or copy.sources.spawnPoints}
                    end
                    pending.spawnIndex = pending.spawnIndex + 1
                elseif item then
                    if type(item) ~= "table" or not ns.Public(item)
                        or not ns.GuideInteger(item.itemID, 2147483647) or item.itemID < 1
                        or not finite(item.chance) or item.chance <= 0 or item.chance > 100
                        or not ns.GuideInteger(item.quantity, 10000) or item.quantity < 1 then pending.valid = false
                    else
                        copy.loot[pending.lootIndex] = {itemID = item.itemID, chance = item.chance, quantity = item.quantity,
                            source = safeSource(item.source) and item.source or copy.sources.loot}
                    end
                    pending.lootIndex = pending.lootIndex + 1
                else
                    if pending.valid then
                        result[#result + 1] = copy
                        if #result >= filter.limit then finish(); return end
                    end
                    pending = nil
                end
            else
                local record = data.records[index]
                index = index + 1
                if type(record) == "table" and ns.GuideInteger(record.minLevel, 255)
                    and ns.GuideInteger(record.maxLevel, 255) and record.minLevel <= filter.maxLevel
                    and record.maxLevel >= filter.minLevel and (not filter.mapID or record.mapID == filter.mapID) then
                    local copy = prepareFarmPrior(record, filter.mapID)
                    if copy then pending = {source = record, copy = copy,
                        spawnIndex = 1, lootIndex = 1, valid = true} end
                end
            end
            local current = clockMilliseconds()
            if not current or current - began >= 2 then
                if not queueNext(step) then finish() end
                return
            end
        end
        finish()
    end
    if not queueNext(step) then return false, "Farm-prior search timer is unavailable." end
    return true
end

local function prepareGatheringFact(fact)
    if type(fact) ~= "table" or not ns.Public(fact)
        or not ns.GuideInteger(fact.professionID, 1000)
        or not safeCardText(fact.profession, 40) or not safeCardText(fact.node, 100)
        or not ns.GuideInteger(fact.requiredSkill, 1000)
        or not ns.GuideInteger(fact.ownSkill, 1000) or fact.ownSkill < fact.requiredSkill
        or not safeCardText(fact.zone, 100)
        or not ns.GuideInteger(fact.zoneMinLevel, 255) or not ns.GuideInteger(fact.zoneMaxLevel, 255)
        or fact.zoneMinLevel > fact.zoneMaxLevel
        or fact.zoneFaction ~= nil and fact.zoneFaction ~= "Alliance" and fact.zoneFaction ~= "Horde"
        or type(fact.loot) ~= "table" or #fact.loot > 100 or type(fact.sources) ~= "table" then return nil end
    local sources = {}
    for _, key in ipairs({"profession", "node", "skill", "zone", "mapID", "yield"}) do
        if not safeSource(fact.sources[key]) then return nil end
        sources[key] = fact.sources[key]
    end
    local loot = {}
    for index, item in ipairs(fact.loot) do
        if type(item) ~= "table" or not ns.Public(item)
            or not ns.GuideInteger(item.itemID, 2147483647) or item.itemID < 1
            or not safeSource(item.source) then return nil end
        loot[index] = {itemID = item.itemID, source = item.source}
        if item.chance ~= nil or item.quantity ~= nil then
            if not finite(item.chance) or item.chance <= 0 or item.chance > 100
                or not ns.GuideInteger(item.quantity, 10000) or item.quantity < 1 then return nil end
            loot[index].chance, loot[index].quantity = item.chance, item.quantity
        end
    end
    return {professionID = fact.professionID, profession = fact.profession, node = fact.node,
        requiredSkill = fact.requiredSkill, ownSkill = fact.ownSkill,
        zone = fact.zone, zoneMinLevel = fact.zoneMinLevel, zoneMaxLevel = fact.zoneMaxLevel,
        zoneFaction = fact.zoneFaction, loot = loot, sources = sources}
end

local function searchGatheringFarms(filter, onDone, ...)
    if type(filter) ~= "table" or not ns.Public(filter)
        or filter.profession ~= nil and (not ns.Public(filter.profession) or filter.profession ~= "Mining" and filter.profession ~= "Herbalism"
            and filter.profession ~= "Skinning" and filter.profession ~= "Fishing"
        )
        or filter.mapID ~= nil and (not ns.GuideInteger(filter.mapID, 1000000) or filter.mapID < 1)
        or not ns.GuideInteger(filter.limit, 50) or filter.limit < 1
        or type(onDone) ~= "function" or select("#", ...) > 0 then
        return false, "Invalid gathering-farm search arguments."
    end
    for key in pairs(filter) do
        if key ~= "profession" and key ~= "mapID" and key ~= "limit" then
            return false, "Unknown gathering-farm filter field."
        end
    end
    if type(ns.EnsureOptionalData) == "function" then ns.EnsureOptionalData("WowTogether_GoldData") end
    if type(ns.GatheringFarmFactCount) ~= "function" or type(ns.GatheringFarmFact) ~= "function"
        or ns.GatheringFarmFactCount() < 1 then
        return false, "Gathering-farm data is unavailable."
    end
    if not clockMilliseconds() or type(ns.After) ~= "function"
        or type(ns.KnownZoneMaps) ~= "function" or type(ns.MapName) ~= "function" then
        return false, "Gathering-farm search needs public map data, a frame clock, and a timer."
    end
    local knownMaps = ns.KnownZoneMaps()
    if type(knownMaps) ~= "table" then return false, "Gathering-farm map data is unavailable." end
    local mapByName = {}
    local factCount = ns.GatheringFarmFactCount()
    local mapKey = next(knownMaps)
    local index, result, grouped, done, mapsReady = 1, {}, {}, false, false
    local function finish()
        if done then return end
        done = true
        local okay = pcall(onDone, result)
        if not okay then ns.moduleGatheringFarmCallbackError = true end
    end
    local function step()
        if done then return end
        local began = clockMilliseconds()
        if not began then finish(); return end
        while not mapsReady do
            if mapKey == nil then mapsReady = true; break end
            local currentID = mapKey
            mapKey = next(knownMaps, mapKey)
            if ns.GuideInteger(currentID, 1000000) and currentID > 0 then
                local zone = ns.MapName(currentID)
                if safeCardText(zone, 100) and zone ~= ("Map " .. currentID) then mapByName[zone] = currentID end
            end
            local current = clockMilliseconds()
            if not current or current - began >= 2 then
                if not queueNext(step) then finish() end
                return
            end
        end
        while index <= factCount do
            local fact = prepareGatheringFact(ns.GatheringFarmFact(index))
            index = index + 1
            if fact and (not filter.profession or fact.profession == filter.profession) then
                local mapID = mapByName[fact.zone]
                local profile = ns.profile or {}
                if not mapID and profile.zone == fact.zone and ns.GuideInteger(profile.mapID, 1000000) then
                    mapID = profile.mapID
                end
                if mapID and (not filter.mapID or mapID == filter.mapID)
                    and (not fact.zoneFaction or profile.faction == fact.zoneFaction)
                    and profile.level >= fact.zoneMinLevel - 5 and profile.level <= 255 then
                    local key = fact.profession .. "\0" .. fact.node
                    local candidate = grouped[key]
                    if not candidate and #result < filter.limit then
                        candidate = {profession = fact.profession, professionID = fact.professionID,
                            node = fact.node, requiredSkill = fact.requiredSkill, ownSkill = fact.ownSkill,
                            zones = {}, loot = {}, sources = fact.sources}
                        grouped[key] = candidate; result[#result + 1] = candidate
                    end
                    if candidate then
                        local zoneRecord
                        for _, item in ipairs(candidate.zones) do if item.mapID == mapID then zoneRecord = item; break end end
                        if not zoneRecord then
                            zoneRecord = {mapID = mapID, name = fact.zone, points = {}}
                            if type(ns.GatheringFarmPoints) == "function" then
                                local externalPoints = ns.GatheringFarmPoints(fact.profession, fact.node, mapID)
                                if type(externalPoints) == "table" then
                                    for _, point in ipairs(externalPoints) do
                                        if type(point) == "table" and ns.Public(point) and point.mapID == mapID
                                            and ns.ValidTravelPoint(point) and safeSource(point.source) and #zoneRecord.points < 24 then
                                            zoneRecord.points[#zoneRecord.points + 1] = {mapID = mapID,
                                                x = point.x, y = point.y, source = point.source}
                                        end
                                    end
                                end
                            end
                            zoneRecord.loot = {}
                            for _, loot in ipairs(fact.loot) do zoneRecord.loot[#zoneRecord.loot + 1] = loot end
                            if type(ns.GatheringFarmYield) == "function" then
                                local seeded = ns.GatheringFarmYield(fact.profession, fact.node, fact.zone, mapID)
                                if type(seeded) == "table" then
                                    for _, item in ipairs(seeded) do
                                        if type(item) ~= "table" or not ns.Public(item)
                                            or not ns.GuideInteger(item.itemID, 2147483647) or item.itemID < 1
                                            or not finite(item.chance) or item.chance <= 0 or item.chance > 100
                                            or not ns.GuideInteger(item.quantity, 10000) or item.quantity < 1
                                            or not safeSource(item.source) then
                                            item = nil
                                        end
                                        if item then
                                        local present
                                        for _, existing in ipairs(zoneRecord.loot) do
                                            if existing.itemID == item.itemID then present = existing; break end
                                        end
                                        if present and not present.chance and item.chance then
                                            for key, value in pairs(item) do present[key] = value end
                                        elseif not present and #zoneRecord.loot < 100 then
                                            zoneRecord.loot[#zoneRecord.loot + 1] = item
                                        end
                                        end
                                    end
                                end
                            end
                            candidate.zones[#candidate.zones + 1] = zoneRecord
                        end
                        for _, loot in ipairs(zoneRecord.loot) do
                            local foundItem = false
                            for _, item in ipairs(candidate.loot) do if item.itemID == loot.itemID then foundItem = true; break end end
                            if not foundItem and #candidate.loot < 100 then candidate.loot[#candidate.loot + 1] = loot end
                        end
                        for _, loot in ipairs(fact.loot) do
                            local foundItem = false
                            for _, item in ipairs(candidate.loot) do if item.itemID == loot.itemID then foundItem = true; break end end
                            if not foundItem then candidate.loot[#candidate.loot + 1] = loot end
                        end
                    end
                end
            end
            local current = clockMilliseconds()
            if not current or current - began >= 2 then
                if not queueNext(step) then finish() end
                return
            end
        end
        finish()
    end
    if not queueNext(step) then return false, "Gathering-farm search timer is unavailable." end
    return true
end

local function registerGatheringObserver(module, callback, ...)
    if not ns.Public(module) then return false, "Invalid gathering observer arguments." end
    local registered = moduleRecord(module)
    if not registered or not ns.Public(callback) or type(callback) ~= "function" or select("#", ...) > 0 then
        return false, "Invalid gathering observer arguments."
    end
    local list = gatheringObservers[registered] or {}
    gatheringObservers[registered] = list
    list[#list + 1] = callback
    local active = true
    return true, function()
        if not active then return false end
        active = false
        for index = #list, 1, -1 do if list[index] == callback then table.remove(list, index) end end
        return true
    end
end

ns.hooks.gatheringObserved[#ns.hooks.gatheringObserved + 1] = function(event)
    if type(event) ~= "table" or not ns.Public(event)
        or not ns.GuideInteger(event.professionID, 1000)
        or not ns.GuideInteger(event.mapID, 1000000) or event.mapID < 1
        or not finite(event.x) or event.x < 0 or event.x > 1
        or not finite(event.y) or event.y < 0 or event.y > 1
        or not ns.GuideInteger(event.itemID, 2147483647) or event.itemID < 1
        or not ns.GuideInteger(event.quantity, 10000) or event.quantity < 1
        or not safeSource(event.source) then return end
    local professions = {[186] = "Mining", [182] = "Herbalism", [393] = "Skinning", [356] = "Fishing"}
    if event.profession ~= professions[event.professionID] then return end
    for _, list in pairs(gatheringObservers) do
        for _, callback in ipairs(list) do
            local copy = {professionID = event.professionID, profession = event.profession,
                mapID = event.mapID, x = event.x, y = event.y, itemID = event.itemID,
                quantity = event.quantity, source = event.source, observedAt = finite(event.observedAt) and event.observedAt or nil}
            pcall(callback, copy)
        end
    end
end

local function formatGoldRate(copper)
    return string.format("%.1f gold/hour", copper / 10000)
end

local function activeFarmCard()
    return activeFarmSession
end

local function setFarmSession(module, data, ...)
    if select("#", ...) > 0 then return false, "Unexpected farm-session arguments." end
    local registered = moduleRecord(module)
    if not registered then return false, "Module is not registered." end
    if data == nil then
        farmSessions[registered] = nil
        if activeFarmSession and activeFarmSession.module == registered then activeFarmSession = nil end
        return true
    end
    if type(data) ~= "table" or not ns.Public(data)
        or not safeCardText(data.label, 100)
        or not finite(data.estimatedCopperPerHour) or data.estimatedCopperPerHour < 0 or data.estimatedCopperPerHour > 9000000000000
        or not finite(data.actualCopperPerHour) or data.actualCopperPerHour < 0 or data.actualCopperPerHour > 9000000000000
        or not finite(data.startTime) or data.startTime <= 0
        or not safeCardText(data.estimatedBasis, 100) or not safeCardText(data.actualBasis, 100) then
        return false, "Invalid farm-session data."
    end
    for key in pairs(data) do
        if key ~= "label" and key ~= "estimatedCopperPerHour" and key ~= "actualCopperPerHour"
            and key ~= "startTime" and key ~= "estimatedBasis" and key ~= "actualBasis" then
            return false, "Unknown farm-session field."
        end
    end
    local copy = {module = registered, label = data.label,
        estimatedCopperPerHour = data.estimatedCopperPerHour,
        actualCopperPerHour = data.actualCopperPerHour, startTime = data.startTime,
        estimatedBasis = data.estimatedBasis, actualBasis = data.actualBasis}
    farmSessions[registered], activeFarmSession = copy, copy
    return true
end

local refreshTimes = {}
local function requestFarmSessionRefresh(module, ...)
    if select("#", ...) > 0 then return false, "Unexpected farm-session refresh arguments." end
    local registered = moduleRecord(module)
    if not registered then return false, "Module is not registered." end
    if not activeFarmSession or activeFarmSession.module ~= registered then return false, "No farm session is active." end
    if ns.RouteInCombat and ns.RouteInCombat() then return false, "Refresh after combat." end
    local now = ns.ReadPublic(GetTime)
    if not finite(now) then return false, "Frame clock is unavailable." end
    if refreshTimes[registered] and now - refreshTimes[registered] < 1 then
        return false, "Farm-session refresh is rate limited."
    end
    if type(ns.RedrawGoldSessionCard) ~= "function" then return false, "Gold session card is unavailable." end
    if ns.RedrawGoldSessionCard() ~= true then return false, "Open the Hub before refreshing its session card." end
    refreshTimes[registered] = now
    return true
end

local function moduleLoopStops(state, index)
    local loop = state and state.route
    if not loop then return {} end
    local stops, count = {}, #loop.loopStops
    for offset = 0, count do
        local at = ((index + offset - 1) % count) + 1
        local point = loop.loopStops[at]
        local copy = {}
        for key, value in pairs(point) do copy[key] = value end
        stops[#stops + 1] = copy
    end
    return stops
end

local function notifyLoopStopped(state, reason)
    if not state or state.notified then return end
    state.notified = true
    if type(state.onStop) == "function" then pcall(state.onStop, reason) end
end

local function endModuleLoop(module, reason)
    local registered = moduleRecord(module)
    if not registered then return false, "Module is not registered." end
    local state = moduleLoops[registered]
    if not state then return false, "Module loop is not running." end
    moduleLoops[registered] = nil
    notifyLoopStopped(state, safeCardText(reason, 120) and reason or "stopped")
    if loopFrame and not next(moduleLoops) then loopFrame:SetScript("OnUpdate", nil); loopFrame = nil end
    if ns.routeSelection == state.guide then
        ns.ClearRoute()
        if ns.UpdateNavigation then ns.UpdateNavigation() end
    end
    return true
end

local function stopModuleLoop(module, ...)
    if select("#", ...) > 0 then return false, "Unexpected module-loop stop arguments." end
    return endModuleLoop(module, "stopped by module")
end

local function advanceModuleLoop(state)
    if not state or moduleLoops[state.module] ~= state or ns.RouteInCombat and ns.RouteInCombat() then return false end
    local stop = state.route.stops[1]
    if not stop then return false end
    local player = ns.PlayerPoint(stop.mapID)
    local distance = player and ns.TravelPointDistance(player, stop)
    if not finite(distance) or distance > 18 then return false end
    state.index = state.index % #state.route.loopStops + 1
    state.route.stops = moduleLoopStops(state, state.index)
    ns.routeSignature = nil
    if ns.DrawRoute then ns.DrawRoute() end
    if ns.UpdateNavigation then ns.UpdateNavigation() end
    return true
end

local function activateModuleLoop(request)
    if not request or request.started then return false end
    request.started = true
    if moduleLoops[request.module] then endModuleLoop(request.module, "replaced by a new module loop") end
    if ns.RouteInCombat and ns.RouteInCombat() then return false end
    if ns.routeSelection and ns.StopGuide then ns.StopGuide(false) end
    local stops = {}
    for index, point in ipairs(request.loop.points) do
        if index < #request.loop.points then
            local source = request.points[point.index]
            stops[#stops + 1] = {id = 0, kind = "farm", module = request.module,
                moduleStop = true, mapID = point.mapID, x = point.x, y = point.y,
                title = source.label, label = source.label, reason = source.reason}
        end
    end
    if #stops == 0 then return false end
    local guide = {key = "module:" .. string.lower(request.module) .. ":loop",
        mode = "module", module = request.module, title = request.title,
        focusKey = ns.self, personal = true, mapID = stops[1].mapID}
    local route = {key = guide.key, title = request.title, mapID = stops[1].mapID,
        stops = {}, loopStops = stops, complete = false, moduleLoop = true}
    local state = {module = request.module, title = request.title, guide = guide,
        route = route, loop = request.loop, index = 1, onStop = request.onStop}
    route.stops = moduleLoopStops(state, state.index)
    moduleLoops[request.module] = state
    ns.routeSelection, ns.selectedRoute, ns.routeSignature, ns.routePaused = guide, route, nil, nil
    ns.guideStopped, ns.guideWindowIdle = nil, nil
    if ns.AttachRouteProvider then ns.AttachRouteProvider() end
    if ns.DrawRoute then ns.DrawRoute() end
    if not loopFrame then loopFrame = CreateFrame("Frame") end
    loopFrame:SetScript("OnUpdate", function(self, elapsed)
        local started = ns.PerfBegin and ns.PerfBegin("moduleLoop", true)
        if finite(elapsed) and elapsed >= 0 then
            self.elapsed = (self.elapsed or 0) + elapsed
            if self.elapsed >= 0.2 then
                self.elapsed = 0
                local active = ns.routeSelection and moduleLoops[ns.routeSelection.module]
                if active then advanceModuleLoop(active) end
            end
        end
        if started then ns.PerfEnd("moduleLoop", started) end
    end)
    if ns.OpenGuideWindow then ns.OpenGuideWindow() end
    if type(request.onStart) == "function" then pcall(request.onStart) end
    return true
end

local function startModuleLoop(module, spec, ...)
    local registered = moduleRecord(module)
    if not registered or type(spec) ~= "table" or not ns.Public(spec)
        or not safeCardText(spec.title, 100) or not safeDenseArray(spec.points, 24) or #spec.points == 0
        or type(spec.onStop) ~= "function" or spec.onStart ~= nil and type(spec.onStart) ~= "function"
        or select("#", ...) > 0 then
        return false, "Invalid module loop arguments."
    end
    for key in pairs(spec) do
        if key ~= "title" and key ~= "points" and key ~= "onStop" and key ~= "onStart" then return false, "Unknown module loop field." end
    end
    if ns.RouteInCombat and ns.RouteInCombat() then return false, "Start the loop after combat." end
    local points = {}
    for index, point in ipairs(spec.points) do
        if type(point) ~= "table" or not ns.Public(point) or not ns.ValidTravelPoint(point)
            or not safeCardText(point.label, 100) or not safeCardText(point.reason, 240) then
            return false, "Each loop point needs a valid location, label, and reason."
        end
        for key in pairs(point) do
            if key ~= "mapID" and key ~= "x" and key ~= "y" and key ~= "label" and key ~= "reason" then
                return false, "Unknown module loop point field."
            end
        end
        points[index] = {mapID = point.mapID, x = point.x, y = point.y,
            label = point.label, reason = point.reason, index = index}
    end
    local walkPoints = {}
    for index, point in ipairs(points) do walkPoints[index] = {mapID = point.mapID, x = point.x, y = point.y, index = index} end
    local loop = ns.TrailLoop(walkPoints)
    if not loop or #loop.points < 2 then return false, "No walking loop is available for these points." end
    if #loop.points == 2 and #points > 1 then return false, "No walking loop is available for these points." end
    local request = {module = registered, title = spec.title, points = points, loop = loop,
        onStop = spec.onStop, onStart = spec.onStart}
    if ns.routeSelection then
        if not StaticPopup_Show or type(StaticPopup_Show) ~= "function" then
            return false, "Guide replacement needs a confirmation dialog."
        end
        StaticPopupDialogs = StaticPopupDialogs or {}
        StaticPopupDialogs.WOWTOGETHER_MODULE_LOOP_CONFIRM = {
            text = "Starting %s will stop your current guide. Start the loop?",
            button1 = YES, button2 = NO, timeout = 0, whileDead = 1, hideOnEscape = 1,
            preferredIndex = 3,
            OnAccept = function(_, data)
                if ns.RouteInCombat and ns.RouteInCombat() then
                    notifyLoopStopped(data, "guide replacement accepted during combat")
                    return
                end
                if not activateModuleLoop(data) then
                    notifyLoopStopped(data, "could not start after guide replacement was accepted")
                end
            end,
            OnCancel = function(_, data)
                notifyLoopStopped(data, "player declined guide replacement")
            end,
        }
        local okay, shown = pcall(StaticPopup_Show, "WOWTOGETHER_MODULE_LOOP_CONFIRM", request.title, nil, request)
        if not okay or not shown then return false, "Could not show the guide-replacement confirmation." end
        return true, "Waiting for confirmation."
    end
    if not activateModuleLoop(request) then return false, "Could not start the module loop." end
    return true
end

local function readAuctionQuote(itemID, ...)
    if select("#", ...) > 0 then return nil end
    if not ns.GuideInteger(itemID, 2147483647) or itemID < 1 or type(ns.AuctionQuote) ~= "function" then return nil end
    local quote = ns.AuctionQuote(itemID)
    local now = ns.ReadPublic(GetServerTime)
    if type(quote) ~= "table" or quote.unavailable or not finite(quote.unitPrice)
        or quote.unitPrice <= 0 or not ns.GuideInteger(quote.time, 9000000000)
        or not ns.GuideInteger(now, 9000000000) or quote.time > now then return nil end
    return quote.unitPrice, now - quote.time
end

ns.hooks.routeCleared = ns.hooks.routeCleared or {}
ns.hooks.routeCleared[#ns.hooks.routeCleared + 1] = function(selection)
    local state = selection and selection.mode == "module" and moduleLoops[selection.module]
    if state then endModuleLoop(state.module, "guide route cleared") end
end
ns.hooks.routeWillActivate = ns.hooks.routeWillActivate or {}
ns.hooks.routeWillActivate[#ns.hooks.routeWillActivate + 1] = function(nextGuide)
    local current = ns.routeSelection
    local state = current and current.mode == "module" and moduleLoops[current.module]
    if state and nextGuide ~= state.guide then
        moduleLoops[state.module] = nil
        notifyLoopStopped(state, "replaced by another guide")
        if loopFrame and not next(moduleLoops) then loopFrame:SetScript("OnUpdate", nil); loopFrame = nil end
    end
end

ns.ModuleLoopRoute = function(module)
    local state = moduleLoops[module]
    return state and state.route or nil
end

ns.ModuleFarmSessionForCard = function()
    local data = activeFarmCard()
    if not data then return nil end
    return {title = data.label,
        detail = "Estimated " .. formatGoldRate(data.estimatedCopperPerHour)
            .. " • Actual " .. formatGoldRate(data.actualCopperPerHour)
            .. "\nEstimate: " .. data.estimatedBasis .. "\nActual: " .. data.actualBasis,
        action = function() ns.SetFilter("module:" .. string.lower(data.module)) end}
end
ns.hooks.researchExport[#ns.hooks.researchExport + 1] = function()
    local events = {}
    for _, hook in ipairs(exportHooks) do
        local rows = hook()
        assert(type(rows) == "table", "Research hook must return event array")
        for _, row in ipairs(rows) do
            assert(type(row) == "table" and type(row.event) == "string", "Invalid research event")
            events[#events + 1] = row
        end
    end
    return events
end

-- A separately loaded optional addon has a different private namespace. Give
-- it a deliberately limited public table instead of exposing core `ns`.
-- Opens the main window on a module's own page: what a module's buttons use
-- to say "see the rest here", so nothing needs a typed command.
function ns.OpenModulePage(name)
    local entry = type(name) == "string" and ns.Public(name) and modules[name]
    if not entry or not entry.tab or not ns.window or type(ns.SetFilter) ~= "function" then return false end
    if ns.RouteInCombat and ns.RouteInCombat() and not ns.window:IsShown() then return false end
    if not ns.window:IsShown() then ns.window:Show() end
    ns.SetFilter("module:" .. string.lower(name))
    return true
end

local publicAPI = {
    version = ns.GoldAPIVersion,
    STEP_SYMBOLS = {farm = ns.STEP_ICON_TEXTURES.farm},
    AuctionQuote = readAuctionQuote,
    FarmPriorSearch = searchFarmPriors,
    GatheringFarmSearch = searchGatheringFarms,
    RegisterGatheringObserver = registerGatheringObserver,
    StartModuleLoop = startModuleLoop,
    StopModuleLoop = stopModuleLoop,
    SetFarmSession = setFarmSession,
    RequestFarmSessionRefresh = requestFarmSessionRefresh,
}
for _, name in ipairs({"RegisterModule", "FindTravelPath", "TravelPointDistance", "PlayerPoint",
    "TrailLoop", "RouteCostModel", "PushGuideStop", "ClearModuleStops", "RegisterSyncKind",
    "QueueModuleSync",
    "CatalogueQuest", "ReadPublic", "Public", "GuideInteger", "SafeTitle",
    "Option", "SetOption", "Print", "On", "ResearchExportHook",
    "StartFarmCandidateScan", "PublishGoldFunction",
    -- Drawing in the addon's own style, so a module's windows look like the
    -- core's. These only build and colour frames the module owns.
    "UIPanel", "UILabel", "UIButton", "UIButtonTone", "UIClose", "UIHelp", "UIDivider",
    "AuctionHouseVisible", "AuctionHouseAnchor", "RouteInCombat", "After", "OpenModulePage"}) do
    publicAPI[name] = ns[name]
end
-- A copy: a module can read the palette, not change the core's.
publicAPI.UIColors = {}
for key, color in pairs(ns.UIColors or {}) do
    publicAPI.UIColors[key] = {color[1], color[2], color[3], color[4]}
end
setmetatable(publicAPI, {__index = function(_, name)
    if name == "catalogue" then return ns.catalogue end
end})
_G.WowTogetherModuleAPI = publicAPI

-- Gold is packaged as a separate LoadOnDemand addon. Load it only when it is
-- installed and enabled; its TOC dependency guarantees the core is ready.
ns.On("PLAYER_LOGIN", function()
    local isLoaded = C_AddOns and C_AddOns.IsAddOnLoaded or IsAddOnLoaded
    if type(isLoaded) == "function" then
        local ok, loaded = pcall(isLoaded, "WowTogether_Gold")
        if ok and loaded == true then return end
    end
    local load = C_AddOns and C_AddOns.LoadAddOn or LoadAddOn
    if type(load) == "function" then
        local ok, loaded, reason = pcall(load, "WowTogether_Gold")
        ns.optionalGoldStatus = ok and loaded == true and "loaded" or tostring(reason or "unavailable")
    else
        ns.optionalGoldStatus = "loader unavailable"
    end
end)
