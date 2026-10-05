local addonName, ns = ...

-- A separate, read-only inspection environment. No addon state, frames,
-- mutation APIs, loaders, or chat actions are exposed to pasted snippets.
local CODE_LIMIT, OUTPUT_LIMIT = 8192, 24000
local backing = setmetatable({}, {__mode = "k"})
local globals = {"GetBuildInfo", "GetZoneText", "GetTime", "GetPlayerFacing", "InCombatLockdown", "IsInGroup", "IsInRaid",
    "UnitLevel", "UnitName", "UnitFullName", "UnitGUID", "UnitFactionGroup", "UnitClass", "UnitRace", "UnitHealth",
    "UnitHealthMax", "UnitExists", "UnitCanAttack", "UnitIsGhost", "UnitOnTaxi", "GetQuestID", "GetTitleText",
    "GetNumAvailableQuests", "GetAvailableQuestInfo", "GetAvailableTitle", "GetNumGossipAvailableQuests",
    "GetNumQuestChoices", "IsQuestCompletable", "IsPushableQuest", "GetTaxiMapID", "issecretvalue"}
local namespaces = {
    C_QuestLog = {"GetNumQuestLogEntries", "GetInfo", "IsQuestFlaggedCompleted", "GetQuestDifficultyLevel", "GetQuestObjectives",
        "GetTitleForQuestID", "IsComplete", "GetQuestsOnMap", "GetNextWaypoint", "IsPushableQuest", "UnitIsRelatedToActiveQuest"},
    C_GossipInfo = {"GetAvailableQuests", "GetActiveQuests"},
    C_QuestLine = {"GetAvailableQuestLines", "GetQuestLineInfo", "GetQuestLineQuests"},
    C_Map = {"GetBestMapForUnit", "GetPlayerMapPosition", "GetMapInfo", "GetMapWorldSize", "GetMapLinksForMap",
        "GetWorldPosFromMapPos", "GetMapPosFromWorldPos", "CanSetUserWaypointOnMap"},
    C_TaxiMap = {"GetAllTaxiNodes", "GetTaxiNodesForMap"},
    C_DeathInfo = {"GetCorpseMapPosition"},
    C_Spell = {"GetSpellInfo", "IsSpellDataCached"},
    C_Item = {"GetItemInfo", "GetItemCount", "IsItemDataCachedByID"},
    C_ChatInfo = {"IsAddonMessagePrefixRegistered"},
}

local function pack(...) return {n = select("#", ...), ...} end

function ns.LuaInspectionFormat(value)
    local seen, nodes = {}, 0
    local function render(item, depth)
        if not ns.Public(item) then return "<restricted>" end
        local kind = type(item)
        if kind == "nil" or kind == "boolean" or kind == "number" then return tostring(item) end
        if kind == "string" then
            local text = string.sub(item, 1, 1000)
            return string.format("%q", text) .. (#item > 1000 and " <truncated>" or "")
        end
        if kind ~= "table" then return "<" .. kind .. ">" end
        item = backing[item] or item
        if seen[item] then return "<cycle>" end
        if depth >= 5 or nodes >= 300 then return "<table limit>" end
        seen[item] = true
        local entries, count = {}, 0
        for key, field in pairs(item) do
            count, nodes = count + 1, nodes + 1
            if count > 40 or nodes > 300 then entries[#entries + 1] = "…"; break end
            entries[#entries + 1] = "[" .. render(key, depth + 1) .. "] = " .. render(field, depth + 1)
        end
        table.sort(entries)
        seen[item] = nil
        if #entries == 0 then return "{}" end
        local indent = string.rep("  ", depth + 1)
        return "{\n" .. indent .. table.concat(entries, ",\n" .. indent) .. "\n" .. string.rep("  ", depth) .. "}"
    end
    return string.sub(render(value, 0), 1, OUTPUT_LIMIT)
end

local function readonly(source)
    if not ns.Public(source) then return source end
    if type(source) ~= "table" then return source end
    local proxy = {}
    backing[proxy] = source
    return setmetatable(proxy, {__index = function(_, key) return readonly(source[key]) end,
        __newindex = function() error("Read-only API table", 2) end})
end

local function environment(append)
    local env = {type = type, tonumber = function(value, base) if ns.Public(value) then return tonumber(value, base) end end,
        tostring = function(value) return ns.Public(value) and tostring(value) or "<restricted>" end,
        select = select, unpack = unpack, pcall = pcall, assert = assert, error = error}
    env.next = function(value, key)
        if not ns.Public(value) then error("Restricted table", 2) end
        local k, v = next(backing[value] or value, key)
        return k, readonly(v)
    end
    env.pairs = function(value) return env.next, value, nil end
    env.ipairs = function(value)
        if not ns.Public(value) then error("Restricted table", 2) end
        return ipairs(value)
    end
    env.print = function(...)
        local values, parts = pack(...), {}
        for index = 1, values.n do parts[#parts + 1] = ns.LuaInspectionFormat(values[index]) end
        append(table.concat(parts, "\t"))
    end
    env.apiType = function(path)
        if not ns.Public(path) or type(path) ~= "string" then return "invalid path" end
        local parent, key = string.match(path, "^([%w_]+)%.([%w_]+)$")
        local value
        if parent then
            local api = _G[parent]
            if ns.Public(api) and type(api) == "table" then value = api[key] end
        elseif string.match(path, "^[%w_]+$") then value = _G[path]
        else return "invalid path" end
        return ns.Public(value) and type(value) or "restricted"
    end
    env.math, env.string, env.table = readonly(math), readonly(string), readonly(table)
    -- Bound the common accidentally enormous string allocation.
    local strings = {}; for key, value in pairs(string) do if key ~= "dump" then strings[key] = value end end
    strings.rep = function(value, count)
        if not ns.Public(value) or not ns.Public(count) or type(value) ~= "string" or type(count) ~= "number"
            or count < 0 or count > CODE_LIMIT or #value * count > OUTPUT_LIMIT then error("String size limit", 2) end
        return string.rep(value, count)
    end
    env.string = readonly(strings)
    for _, name in ipairs(globals) do if type(_G[name]) == "function" then env[name] = _G[name] end end
    for name, allowed in pairs(namespaces) do
        local api = _G[name]
        if ns.Public(api) and type(api) == "table" then
            local entries = {}
            for _, method in ipairs(allowed) do if type(api[method]) == "function" then entries[method] = api[method] end end
            env[name] = readonly(entries)
        end
    end
    if type(Enum) == "table" then env.Enum = readonly(Enum) end
    if ns.Public(WOW_PROJECT_ID) then env.WOW_PROJECT_ID = WOW_PROJECT_ID end
    if ns.Public(LE_EXPANSION_LEVEL_CURRENT) then env.LE_EXPANSION_LEVEL_CURRENT = LE_EXPANSION_LEVEL_CURRENT end
    return env
end

-- Straight-line checks can use locals, conditionals, print and return. Tables
-- are formatted automatically, so loops and function definitions aren't needed.
local function unsupportedToken(code)
    local index = 1
    local function longEnd(at)
        local equals = string.match(string.sub(code, at), "^%[(=*)%[")
        if not equals then return end
        local finish = string.find(code, "]" .. equals .. "]", at + #equals + 2, true)
        return finish and finish + #equals + 2 or #code + 1
    end
    while index <= #code do
        local char = string.sub(code, index, index)
        if string.sub(code, index, index + 1) == "--" then
            index = longEnd(index + 2) or (string.find(code, "\n", index + 2, true) or #code + 1)
        elseif char == "'" or char == '"' then
            index = index + 1
            while index <= #code do
                local c = string.sub(code, index, index)
                if c == "\\" then index = index + 2
                elseif c == char then index = index + 1; break
                else index = index + 1 end
            end
        elseif char == "[" and longEnd(index) then index = longEnd(index)
        elseif string.match(char, "[%a_]") then
            local token = string.match(string.sub(code, index), "^[%w_]+")
            if token == "for" or token == "while" or token == "repeat" or token == "function" then return token end
            index = index + #token
        else index = index + 1 end
    end
end

function ns.RunLuaInspection(code)
    if not ns.Public(code) or type(code) ~= "string" or #code > CODE_LIMIT then return "Input must be at most 8 KB." end
    if ns.RouteInCombat() then return "Run Lua checks outside combat." end
    if type(loadstring) ~= "function" or type(setfenv) ~= "function" then return "Lua compilation is unavailable on this build (loadstring/setfenv)." end
    local token = unsupportedToken(code)
    if token then return "Use a straight-line check: loops and function definitions are unavailable. Return a table to inspect its fields." end
    if not string.find(code, "%S") then return "Paste a check, then press Run." end
    local fn, compileError = loadstring(code, "WowTogether Lua check")
    if not fn then return "Syntax error: " .. ns.LuaInspectionFormat(compileError) end
    local lines, bytes = {}, 0
    local function append(line)
        if bytes >= OUTPUT_LIMIT then return end
        local part = string.sub(line, 1, OUTPUT_LIMIT - bytes)
        lines[#lines + 1], bytes = part, bytes + #part + 1
    end
    setfenv(fn, environment(append))
    local results = pack(pcall(fn))
    if results[1] ~= true then append("Lua error: " .. ns.LuaInspectionFormat(results[2]))
    else
        for index = 2, results.n do append("Return " .. (index - 1) .. ": " .. ns.LuaInspectionFormat(results[index])) end
        if results.n == 1 and #lines == 0 then append("Completed; no values returned.") end
    end
    if bytes >= OUTPUT_LIMIT then lines[#lines + 1] = "<output truncated>" end
    return table.concat(lines, "\n")
end

function ns.ShowLuaConsole()
    if ns.luaConsole then ns.luaConsole:Show(); return end
    local frame = CreateFrame("Frame", "WowTogetherLuaConsole", UIParent, "BackdropTemplate")
    ns.luaConsole = frame
    frame:SetSize(780, 660); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
    frame:SetClampedToScreen(true); ns.UIPanel(frame)
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherLuaConsole") end
    local title = ns.UILabel(frame, "GameFontNormalLarge", 18)
    title:SetPoint("TOPLEFT", 22, -18); title:SetText("Lua checks")
    local help = ns.UILabel(frame, nil, 11)
    help:SetPoint("TOPLEFT", 22, -46); help:SetWidth(730)
    help:SetText("Read-only API subset • locals, print, return • apiType(\"C_API.Method\") checks actual presence • outside combat")
    local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton"); close:SetPoint("TOPRIGHT", -4, -4)
    local function editor(y, height)
        local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
        scroll:SetPoint("TOPLEFT", 24, y); scroll:SetSize(710, height)
        local box = CreateFrame("EditBox", nil, scroll)
        box:SetMultiLine(true); box:SetAutoFocus(false); box:SetFontObject("ChatFontNormal")
        box:SetSize(704, height); box:SetTextInsets(6, 6, 6, 6); scroll:SetScrollChild(box)
        box:SetScript("OnEscapePressed", box.ClearFocus)
        box:SetScript("OnTextChanged", function(self) self:SetHeight(math.max(height, (self:GetStringHeight() or height) + 12)) end)
        return box, scroll
    end
    frame.input = editor(-80, 180); frame.input:SetMaxLetters(CODE_LIMIT)
    frame.input:SetText("return GetBuildInfo()")
    local outputLabel = ns.UILabel(frame, "GameFontNormal", 12)
    outputLabel:SetPoint("TOPLEFT", 24, -312); outputLabel:SetText("Output • Copy with Ctrl+C")
    frame.output = editor(-338, 272)
    frame.output:SetText("Paste your check above, then Run. Results stay here; nothing is sent to chat or peers.")
    local run = ns.UIButton(frame, "Run", 110, function()
        frame.input:ClearFocus()
        frame.output:SetText(string.gsub(ns.RunLuaInspection(frame.input:GetText()), "|", "||"))
    end, true); run:SetPoint("TOPLEFT", 24, -270)
    frame.run = run
    local example = ns.UIButton(frame, "NPC offers", 130, function() frame.input:SetText("return C_GossipInfo.GetAvailableQuests()") end)
    example:SetPoint("LEFT", run, "RIGHT", 10, 0)
    local quests = ns.UIButton(frame, "Quest objectives", 150, function() frame.input:SetText("local questID = 780\nreturn C_QuestLog.GetQuestObjectives(questID)") end)
    quests:SetPoint("LEFT", example, "RIGHT", 10, 0)
    local copy = ns.UIButton(frame, "Select output", 140, function() frame.output:SetFocus(); frame.output:HighlightText() end)
    copy:SetPoint("BOTTOMLEFT", 24, 16)
    local clear = ns.UIButton(frame, "Clear", 90, function() frame.output:SetText("") end)
    clear:SetPoint("LEFT", copy, "RIGHT", 10, 0)
end
