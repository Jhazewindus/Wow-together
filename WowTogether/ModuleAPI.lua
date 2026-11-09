local addonName, ns = ...

-- The optional modules load after the core. Keep their integration here so a
-- module never needs the core's saved variables, route internals, or UI frames.
ns.GoldAPIVersion = 1
ns.STEP_SYMBOLS = ns.STEP_SYMBOLS or {}
ns.STEP_SYMBOLS.farm = "Interface\\Icons\\INV_Misc_Coin_01"

local modules, names, order, options, syncKinds, exportHooks, stops = {}, {}, {}, {}, {}, {}, {}
local reservedKinds = {H=true, Q=true, T=true, S=true, C=true, O=true, K=true,
    Y=true, R=true, Z=true, G=true, P=true, D=true, V=true, W=true}
local function validName(name)
    return type(name) == "string" and string.match(name, "^[A-Za-z][A-Za-z0-9_]*$") ~= nil
end
local function optionKey(name, key)
    return type(key) == "string" and #key > #name + 1
        and string.sub(key, 1, #name + 1) == string.lower(name) .. "."
end

local oldOption, oldSetOption = ns.Option, ns.SetOption
function ns.Option(key)
    local item = options[key]
    if item then
        local value = item.group.get(key)
        if value == nil then return item.default end
        return value
    end
    return oldOption(key)
end
function ns.SetOption(key, value)
    local item = options[key]
    if not item then return oldSetOption(key, value) end
    if type(value) ~= type(item.default) then return false end
    item.group.set(key, value)
    if ns.RenderSettings then ns.RenderSettings() end
    return true
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
    return true
end

local createUI, createSettings, render = ns.CreateUI, ns.CreateSettings, ns.Render
function ns.CreateUI(...)
    local result = createUI(...)
    for _, name in ipairs(order) do addTab(name) end
    return result
end
function ns.CreateSettings(...)
    local result = createSettings(...)
    for _, name in ipairs(order) do addSettings(name) end
    return result
end
function ns.Render(...)
    local result = render(...)
    if not ns.ui then return result end
    for _, name in ipairs(order) do
        local entry = modules[name]
        if entry.page then
            local selected = ns.filter == "module:" .. string.lower(name)
            entry.page:SetShown(selected)
            if selected then
                ns.ui.empty:Hide()
                ns.ui.viewDescription:SetText(entry.tab.title)
                ns.ui.hint:SetText("")
                entry.tab.render(entry.page)
                ns.ui.content:SetHeight(math.max(250, entry.page:GetHeight() or 250))
            end
        end
    end
    return result
end

local slash = SlashCmdList.WOWTOGETHER
SlashCmdList.WOWTOGETHER = function(command)
    local word, rest = string.match(command or "", "^%s*([%w_]+)%s*(.-)%s*$")
    local entry = word and modules[word] or nil
    if not entry and word then
        for name, spec in pairs(modules) do
            if string.lower(name) == string.lower(word) then entry = spec; break end
        end
    end
    if entry and entry.slash then return entry.slash(rest) end
    return slash(command)
end

local showDiagnostics = ns.ShowDiagnostics
function ns.ShowDiagnostics(report, caption, onRefresh)
    if caption == nil and type(report) == "string" then
        local lines = {report}
        for _, name in ipairs(order) do
            local probe = modules[name].probe
            if probe then
                lines[#lines + 1] = "\n" .. name .. ":"
                probe(function(line) lines[#lines + 1] = tostring(line) end)
            end
        end
        report = table.concat(lines, "\n")
    end
    return showDiagnostics(report, caption, onRefresh)
end

-- The core's Receive function has already checked prefix, party membership,
-- sender identity and packet size when it reaches this extension point.
local receivePartyPlan = ns.ReceivePartyPlanMessage
function ns.RegisterSyncKind(letter, handler)
    assert(type(letter) == "string" and string.match(letter, "^[A-Z]$")
        and type(handler) == "function", "Invalid sync registration")
    assert(not reservedKinds[letter] and not syncKinds[letter], "Duplicate sync kind: " .. letter)
    syncKinds[letter] = handler
    return true
end
ns.ReceivePartyPlanMessage = function(message, sender)
    local letter = type(message) == "string" and string.match(message, "^1|([A-Z])|")
    local handler = letter and syncKinds[letter]
    if handler then
        local ok, accepted, reason = pcall(handler, message, sender)
        return true, ok and accepted == true, ok and reason or "module handler failed"
    end
    return receivePartyPlan(message, sender)
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
    local paths, costs = {}, {}
    for i = 1, count do
        paths[i], costs[i] = {}, {}
        for j = 1, count do
            if i ~= j then
                local path = ns.FindTravelPath(points[i], points[j], false)
                local valid = path and finite(path.seconds) and path.seconds >= 0
                for _, leg in ipairs(path and path.legs or {}) do
                    if leg.method ~= "walk" then valid = false; break end
                end
                if valid then paths[i][j], costs[i][j] = path, path.seconds end
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
    sequence[#sequence + 1] = 1
    local loop = {points = {}, legs = {}, seconds = 0}
    for index, pointIndex in ipairs(sequence) do
        loop.points[index] = points[pointIndex]
        if index > 1 then
            local path = paths[sequence[index - 1]][pointIndex]
            if not path then return nil end
            loop.legs[#loop.legs + 1] = path
            loop.seconds = loop.seconds + path.seconds
        end
    end
    return loop
end

local function removeStops(route)
    if not route or type(route.stops) ~= "table" then return end
    for index = #route.stops, 1, -1 do
        if route.stops[index].moduleStop then table.remove(route.stops, index) end
    end
end
local function applyStops()
    local route = ns.selectedRoute
    if not route or type(route.stops) ~= "table" then return end
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
local updateRoute, stopIcon, stopSymbol = ns.UpdateSelectedRoute, ns.StopIcon, ns.StopSymbol
function ns.UpdateSelectedRoute(...)
    removeStops(ns.selectedRoute)
    local result = updateRoute(...)
    applyStops()
    return result
end
function ns.StopIcon(stop)
    if stop and stop.kind == "farm" and stop.moduleStop then return ns.STEP_SYMBOLS.farm end
    return stopIcon(stop)
end
function ns.StopSymbol(stop)
    if stop and stop.kind == "farm" and stop.moduleStop then return "G" end
    return stopSymbol(stop)
end

local destinationDecision = ns.GuideDestinationDecision
function ns.GuideDestinationDecision(stop, guide, route)
    if stop and stop.kind == "farm" and stop.moduleStop then
        return {code = "module-farm", why = stop.reason, specificBenefit = true, confidence = "module-provided"}
    end
    return destinationDecision(stop, guide, route)
end

-- Give module-provided farm work the same structured player-facing fields as
-- native steps. The module supplies its actionable instruction and reason;
-- the core does not invent Gold-specific farming advice.
local presentGuideStep = ns.GuideStepPresentation
function ns.GuideStepPresentation(stop, facts, guide, route, state)
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
        return {kind = "farm", icon = ns.STEP_SYMBOLS.farm, title = stop.title or stop.label,
            stepLine = "Optional module task", what = stop.label, why = why,
            status = "Optional, on the way", statusColor = "text",
            time = distance and timing and (distance .. ", " .. timing) or distance or timing,
            location = location, details = {}, decision = ns.GuideDestinationDecision(stop, guide, route),
            stop = stop, goal = stop, facts = facts or {stop = stop}}
    end
    return presentGuideStep(stop, facts, guide, route, state)
end

local function encode(value, depth)
    if not ns.Public(value) or depth > 8 then return "null" end
    local kind = type(value)
    if kind == "nil" then return "null" end
    if kind == "boolean" then return value and "true" or "false" end
    if kind == "number" then return finite(value) and tostring(value) or "null" end
    if kind == "string" then
        local escaped = string.gsub(string.gsub(value, "\\", "\\\\"), '"', '\\"')
        escaped = string.gsub(escaped, "%c", function(c) return string.format("\\u%04x", string.byte(c)) end)
        return '"' .. escaped .. '"'
    end
    if kind ~= "table" then return "null" end
    local keys, values = {}, {}
    for key in pairs(value) do keys[#keys + 1] = key end
    if #keys == #value then
        for _, item in ipairs(value) do values[#values + 1] = encode(item, depth + 1) end
        return "[" .. table.concat(values, ",") .. "]"
    end
    table.sort(keys)
    for _, key in ipairs(keys) do
        values[#values + 1] = encode(key, depth + 1) .. ":" .. encode(value[key], depth + 1)
    end
    return "{" .. table.concat(values, ",") .. "}"
end
-- Hooks return an array of observation event tables. They are appended to the
-- existing /wt research JSON events array without exposing core research state.
function ns.ResearchExportHook(fn)
    assert(type(fn) == "function", "Invalid research export hook")
    exportHooks[#exportHooks + 1] = fn
    return true
end
local exportResearch = ns.ExportQuestResearch
function ns.ExportQuestResearch(...)
    local result = exportResearch(...)
    if #exportHooks == 0 then return result end
    local events = {}
    for _, hook in ipairs(exportHooks) do
        local rows = hook()
        assert(type(rows) == "table", "Research hook must return event array")
        for _, row in ipairs(rows) do
            assert(type(row) == "table" and type(row.event) == "string", "Invalid research event")
            events[#events + 1] = encode(row, 0)
        end
    end
    if #events == 0 then return result end
    local start, finish = string.find(result, "%]%}%s*$")
    assert(start, "Unexpected research export format")
    local prefix = string.sub(result, 1, start - 1)
    local hasEvents = string.match(prefix, "%[%s*$") == nil
    return prefix .. (hasEvents and "," or "") .. table.concat(events, ",") .. string.sub(result, start, finish)
end

-- A separately loaded optional addon has a different private namespace. Give
-- it a deliberately limited public table instead of exposing core `ns`.
local publicAPI = {
    version = ns.GoldAPIVersion,
    STEP_SYMBOLS = {farm = ns.STEP_SYMBOLS.farm},
}
for _, name in ipairs({"RegisterModule", "FindTravelPath", "TravelPointDistance", "PlayerPoint",
    "TrailLoop", "RouteCostModel", "PushGuideStop", "ClearModuleStops", "RegisterSyncKind",
    "CatalogueQuest", "ReadPublic", "Public", "GuideInteger", "SafeTitle",
    "Option", "SetOption", "Print", "On", "ResearchExportHook"}) do
    publicAPI[name] = ns[name]
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
