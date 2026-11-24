local addonName, ns = ...

-- Sharing quests with the party.
--
-- When the player is in a party, the quests in their log that belong to the
-- zone or dungeon they are in can be shared with the group, using the game's
-- own quest sharing: each member who can take a quest gets the usual offer.
-- By default the addon asks first, once per zone or dungeon: sharing nine
-- quests puts nine offers on every party member's screen, and that is the
-- player's call, not the addon's. A yes holds for that place for the rest of
-- the session (quests accepted there later are shared too); a no is not
-- asked again there. "Always" in the question, or the setting, skips asking.
-- It does not use or need the addon's party sync, and it works with party
-- members who do not have the addon.
--
-- Kept polite: one quest at a time with a pause between, each quest once per
-- group line-up, nothing in raids, nothing in combat. Sharing briefly
-- selects the quest in the log and then puts the selection back.
local PAUSE, SETTLE, LIMIT = 1.5, 4, 25
local shared, queue, running, pendingRun = {}, {}, false, false
local schedule
local announced = {}
ns.questShareStats = {pushed = 0, runs = 0}

-- "ask" (default): ask once per zone or dungeon. "area": share this zone's
-- or dungeon's quests without asking. "all": every quest. "off": never.
local function scope()
    local value = ns.Option and ns.Option("autoShareQuests")
    if value == "all" or value == "off" or value == "area" then return value end
    return "ask"
end

-- The player's answer for each place this session: true shares, false does not.
local consent = {}
local prompt, promptFor

local function inParty()
    return ns.ReadPublic(IsInGroup) == true and ns.ReadPublic(IsInRaid) ~= true and ns.ReadPublic(UnitExists, "party1") == true
end

-- Who is in the party, as one string: a quest is shared once per line-up.
local function roster()
    local names = {}
    for index = 1, 4 do
        local name = ns.ReadPublic(UnitName, "party" .. index)
        if type(name) == "string" and name ~= "" then names[#names + 1] = name end
    end
    table.sort(names)
    return table.concat(names, ",")
end

-- Names the quest log may file this place's quests under.
local function areaNames()
    local names = {}
    for _, reader in ipairs({GetRealZoneText, GetZoneText}) do
        local name = ns.ReadPublic(reader)
        if type(name) == "string" and name ~= "" then names[name] = true end
    end
    if ns.ReadPublic(IsInInstance) == true then
        local name = ns.ReadPublic(GetInstanceInfo)
        if type(name) == "string" and name ~= "" then names[name] = true end
    end
    return names
end

-- Quests with something to do on the map the player is on.
local function questsHere()
    local here = {}
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local list = ns.GuideInteger(mapID) and mapID > 0 and C_QuestLog and ns.ReadPublic(C_QuestLog.GetQuestsOnMap, mapID)
    for _, entry in ipairs(type(list) == "table" and list or {}) do
        if type(entry) == "table" and ns.Public(entry.questID) and ns.GuideInteger(entry.questID) then here[entry.questID] = true end
    end
    return here
end

-- The quests this would share now: {id, title}, in quest-log order.
function ns.ShareableQuests(wanted)
    wanted = wanted or scope()
    if wanted == "ask" then wanted = "area" end
    local result = {}
    if wanted == "off" or not C_QuestLog or type(C_QuestLog.GetNumQuestLogEntries) ~= "function"
        or type(C_QuestLog.GetInfo) ~= "function" or type(C_QuestLog.IsPushableQuest) ~= "function" then return result end
    local count = ns.ReadPublic(C_QuestLog.GetNumQuestLogEntries)
    if not ns.GuideInteger(count) then return result end
    local names, here, header = areaNames(), questsHere(), nil
    for index = 1, math.min(count, 200) do
        local info = ns.ReadPublic(C_QuestLog.GetInfo, index)
        if type(info) == "table" and ns.Public(info.isHeader) then
            if info.isHeader then
                header = ns.Public(info.title) and type(info.title) == "string" and info.title or nil
            elseif ns.Public(info.questID) and ns.GuideInteger(info.questID) and info.questID > 0
                and not (ns.Public(info.isHidden) and info.isHidden == true) then
                local id = info.questID
                local belongs = wanted == "all" or header and names[header] or here[id]
                if belongs and ns.ReadPublic(C_QuestLog.IsPushableQuest, id) == true then
                    local title = ns.Public(info.title) and type(info.title) == "string" and info.title or ("quest " .. id)
                    result[#result + 1] = {id = id, title = title}
                end
            end
        end
    end
    return result
end

local function push(quest)
    if type(QuestLogPushQuest) ~= "function" or type(C_QuestLog.SetSelectedQuest) ~= "function" then
        ns.questShareStatus = "The client does not offer quest sharing to addons."
        return false
    end
    -- Sharing acts on the selected quest. Select it, share, put the selection back.
    local previous = ns.ReadPublic(C_QuestLog.GetSelectedQuest)
    C_QuestLog.SetSelectedQuest(quest.id)
    QuestLogPushQuest()
    if ns.GuideInteger(previous) and previous > 0 and previous ~= quest.id then C_QuestLog.SetSelectedQuest(previous) end
    ns.questShareStats.pushed = ns.questShareStats.pushed + 1
    return true
end

local function finish()
    running = false
    if #announced > 0 then
        local names = {}
        for index = 1, math.min(3, #announced) do names[index] = announced[index] end
        ns.Print("Shared " .. #announced .. (#announced == 1 and " quest" or " quests") .. " with your party: "
            .. table.concat(names, ", ") .. (#announced > 3 and (" and " .. (#announced - 3) .. " more") or "") .. ".")
        ns.questShareStatus = "Shared " .. #announced .. " quest(s) with " .. roster() .. "."
    end
    announced = {}
end

local function step()
    if #queue == 0 then finish(); return end
    if not inParty() then queue = {}; finish(); return end
    if ns.RouteInCombat() then
        -- Not during a fight: try again shortly, keeping the queue.
        ns.After("timer:QuestShare", PAUSE * 2, step)
        return
    end
    local quest = table.remove(queue, 1)
    if push(quest) then announced[#announced + 1] = quest.title end
    ns.After("timer:QuestShare", PAUSE, step)
end

-- The place the player is in, as the question names it and as the answer is kept.
local function place()
    if ns.ReadPublic(IsInInstance) == true then
        local name = ns.ReadPublic(GetInstanceInfo)
        if type(name) == "string" and name ~= "" then return name end
    end
    local name = ns.ReadPublic(GetRealZoneText)
    return type(name) == "string" and name ~= "" and name or "this zone"
end

-- The quests that would go out now: not yet offered to this line-up.
local function unshared(wanted)
    local line, list = roster(), {}
    for _, quest in ipairs(ns.ShareableQuests(wanted)) do
        if shared[quest.id] ~= line then list[#list + 1] = quest end
    end
    return list
end

local function closePrompt() if prompt then prompt:Hide() end; promptFor = nil end

-- "Share 9 quests for Hillsbrad Foothills with your party?"
local function ask(where, count)
    if promptFor == where and prompt and prompt:IsShown() then return end
    if not prompt then
        local colors = ns.UIColors
        prompt = CreateFrame("Frame", "WowTogetherSharePrompt", UIParent, "BackdropTemplate")
        ns.questSharePrompt = prompt
        prompt:SetSize(430, 96); prompt:SetPoint("TOP", UIParent, "TOP", 0, -140); prompt:SetFrameStrata("DIALOG")
        prompt:SetClampedToScreen(true); ns.UIPanel(prompt)
        prompt.text = ns.UILabel(prompt, nil, 13, colors.text)
        prompt.text:SetPoint("TOPLEFT", 16, -14); prompt.text:SetSize(398, 34); prompt.text:SetWordWrap(true); prompt.text:SetJustifyV("TOP")
        prompt.yes = ns.UIButton(prompt, "Share", 110, function()
            local where = promptFor; closePrompt()
            if where then consent[where] = true; ns.ShareQuestsNow(false, "area", true) end
        end, true)
        prompt.yes:SetPoint("BOTTOMLEFT", 16, 12)
        prompt.no = ns.UIButton(prompt, "Not here", 110, function()
            local where = promptFor; closePrompt()
            if where then consent[where] = false; ns.questShareStatus = "Not sharing in " .. where .. " this session." end
        end)
        prompt.no:SetPoint("LEFT", prompt.yes, "RIGHT", 8, 0)
        prompt.always = ns.UIButton(prompt, "Always share", 130, function()
            closePrompt()
            ns.SetOption("autoShareQuests", "area")
            ns.Print("Quests for the zone or dungeon you are in are now shared without asking. Party settings change this.")
            ns.ShareQuestsNow(false, "area", true)
        end)
        prompt.always:SetPoint("LEFT", prompt.no, "RIGHT", 8, 0)
        ns.UIHelp(prompt.yes, "Share them now, and anything you accept here later this session.")
        ns.UIHelp(prompt.no, "Do not share here, and do not ask again for this place this session.")
        ns.UIHelp(prompt.always, "Never ask: always share the quests of the zone or dungeon you are in.")
    end
    promptFor = where
    prompt.text:SetText("Share " .. count .. (count == 1 and " quest" or " quests") .. " for " .. where
        .. " with your party? Each member who can take one gets the usual offer.")
    prompt:Show()
    ns.questShareStatus = "Asked about " .. where .. "."
end

-- Share what belongs here and has not been offered to this line-up yet.
-- `force` shares again whatever was shared before (the /wt share command).
-- `agreed` marks a run the player has just said yes to.
function ns.ShareQuestsNow(force, wanted, agreed)
    pendingRun = false
    wanted = wanted or scope()
    if wanted == "off" and not force then ns.questShareStatus = "Off in settings."; return 0 end
    if not inParty() then closePrompt(); ns.questShareStatus = "Not in a party."; return 0 end
    if not C_Timer or type(C_Timer.After) ~= "function" then return 0 end
    if wanted == "ask" and not force and not agreed then
        -- Ask once per place; a yes covers what is accepted there later.
        local where = place()
        if consent[where] == false then return 0 end
        if consent[where] ~= true then
            if ns.RouteInCombat() then schedule(SETTLE); return 0 end
            local waiting = unshared("area")
            if #waiting > 0 then ask(where, #waiting) end
            return 0
        end
        wanted = "area"
    end
    if wanted == "ask" then wanted = "area" end
    local line, added = roster(), 0
    local waiting = {}
    for _, quest in ipairs(queue) do waiting[quest.id] = true end
    for _, quest in ipairs(ns.ShareableQuests(wanted == "off" and "area" or wanted)) do
        if added >= LIMIT then break end
        if (force or shared[quest.id] ~= line) and not waiting[quest.id] then
            shared[quest.id] = line
            queue[#queue + 1] = quest
            added = added + 1
        end
    end
    ns.questShareStats.runs = ns.questShareStats.runs + 1
    if added == 0 then
        if force then ns.Print("No quest from this zone or dungeon can be shared right now.") end
        return 0
    end
    if not running then running = true; step() end
    return added
end

-- Several events arrive together when a group forms or a zone loads: one run, a moment later.
function schedule(delay)
    if scope() == "off" or pendingRun then return end
    if not C_Timer or type(C_Timer.After) ~= "function" then return end
    -- Nothing to wait for on a client without quest sharing, or outside a party.
    if type(QuestLogPushQuest) ~= "function" or not C_QuestLog or type(C_QuestLog.IsPushableQuest) ~= "function" then return end
    if not inParty() then return end
    pendingRun = true
    ns.After("timer:QuestShare", delay or SETTLE, function() if pendingRun then ns.ShareQuestsNow(false) end end)
end
ns.ScheduleQuestShare = schedule

ns.On("GROUP_ROSTER_UPDATE", function() if not inParty() then closePrompt() end; schedule(SETTLE) end)
ns.On("ZONE_CHANGED_NEW_AREA", function() closePrompt(); schedule(SETTLE + 2) end)
ns.On("PLAYER_ENTERING_WORLD", function() schedule(SETTLE + 4) end)
ns.On("QUEST_ACCEPTED", function() schedule(2) end)

-- /wt share        share this zone's or dungeon's quests again now
-- /wt share all    share every shareable quest in the log now
function ns.ShareQuestsCommand(argument)
    argument = string.lower(argument or "")
    if not inParty() then ns.Print("Join a party to share quests."); return end
    closePrompt()
    ns.ShareQuestsNow(true, string.find(argument, "all", 1, true) and "all" or "area")
end

function ns.QuestShareDiagnostics(output)
    local answers = {}
    for where, answer in pairs(consent) do answers[#answers + 1] = where .. (answer and " yes" or " no") end
    table.sort(answers)
    output("Quest sharing: " .. scope() .. (#answers > 0 and (" (" .. table.concat(answers, ", ") .. ")") or "") .. "; " .. ns.questShareStats.pushed .. " shared this session in "
        .. ns.questShareStats.runs .. " run(s). " .. (ns.questShareStatus or "Nothing shared yet.")
        .. " QuestLogPushQuest " .. (type(QuestLogPushQuest) == "function" and "present" or "missing") .. ".")
end
