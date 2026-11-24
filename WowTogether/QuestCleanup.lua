local addonName, ns = ...

-- Cleaning the quest log of quests that are no longer worth doing.
--
-- A quest is offered for abandoning only when all of this holds:
--   * its reward at the character's level is under 30% of a typical quest's
--     (the same line the leveling path draws), and the guide knows no
--     worthwhile quest it leads to;
--   * it is not finished, and not nearly finished (the "finish nearly done
--     quests" setting), so no work that is as good as done is thrown away;
--   * it is not a dungeon, class, profession or repeatable quest, and the
--     player has not chosen to keep it;
--   * the catalogue knows the quest and its reward. An unknown quest is
--     never touched.
-- Abandoning cannot be undone, so by default the addon asks, with the list,
-- after a level-up or on `/wt clean`. The setting can make it automatic or
-- turn it off. Nothing is abandoned in combat.
local WORTH, PACE, SHOWN = 0.3, 0.4, 8
local declined = {}      -- quests the player said to keep, this session
local prompt, offered
local busy = false

local function mode()
    local value = ns.Option and ns.Option("questCleanup")
    if value == "auto" or value == "off" then return value end
    return "ask"
end

-- The quests that could go, lowest level first: {id, title, level, xp}.
function ns.UselessQuests()
    local result = {}
    local state = ns.XPState and ns.XPState()
    local level = state and state.level or ns.profile and ns.profile.level
    if not ns.GuideInteger(level) or level < 1 then return result end
    local reference = ns.CatalogueXPReference and ns.CatalogueXPReference(level)
    if not reference or reference <= 0 then return result end
    local ids = {}
    for id in pairs(ns.active or {}) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do
        local quest = ns.CatalogueQuest(id)
        local reward = quest and ns.QuestXP(id, level)
        if quest and reward and reward < reference * WORTH
            and not declined[id] and not (ns.LowValueQuestKept and ns.LowValueQuestKept(id))
            and not (ns.readyToTurnIn and ns.readyToTurnIn[id] == true) and ns.QuestProgressReady(ns.self, id) ~= true
            and not ns.QuestNearlyDone(id)
            and not ns.IsDungeonQuest(id) and not ns.IsProfessionQuest(id) and not ns.IsRepeatableQuest(id)
            and not ns.IsClassQuest(id)
            and ns.LevelingValue(id) == false then
            result[#result + 1] = {id = id, title = ns.QuestTitle(id) or quest.title or ("quest " .. id),
                level = quest.level or 0, xp = reward}
        end
    end
    table.sort(result, function(a, b) if a.level ~= b.level then return a.level < b.level end return a.id < b.id end)
    return result
end

-- How many quests could go, for the link on the guide window. Looking is
-- not free (it weighs every quest in the log), so the answer is kept until
-- the log or the level changes, and for at least twenty seconds.
local counted, countedFor, countedAt
function ns.UselessQuestCount()
    if mode() == "off" then return 0 end
    local time = ns.ReadPublic(GetTime)
    local entries, sum = 0, 0
    for id in pairs(ns.active or {}) do entries, sum = entries + 1, sum + id end
    local key = entries .. ":" .. sum .. ":" .. tostring(ns.profile and ns.profile.level)
    if counted and countedFor == key and (type(time) ~= "number" or not countedAt or time - countedAt < 20) then return counted end
    if counted and type(time) == "number" and countedAt and time - countedAt < 20 then return counted end
    counted, countedFor, countedAt = #ns.UselessQuests(), key, type(time) == "number" and time or nil
    return counted
end
function ns.ForgetUselessQuestCount() counted, countedFor, countedAt = nil, nil, nil end

local function abandon(id)
    local log = C_QuestLog
    if not log or not ns.active[id] or not ns.ReadPublic(log.GetLogIndexForQuestID, id) then return false end
    if type(log.SetSelectedQuest) ~= "function" or type(log.AbandonQuest) ~= "function" then return false end
    local previous = ns.ReadPublic(log.GetSelectedQuest)
    log.SetSelectedQuest(id)
    -- The game abandons the quest marked for abandoning, which is set from the selected one.
    if type(log.SetAbandonQuest) == "function" then log.SetAbandonQuest() end
    local okay = pcall(log.AbandonQuest)
    if ns.GuideInteger(previous) and previous > 0 and previous ~= id then log.SetSelectedQuest(previous) end
    return okay
end

-- Abandons the given quests one at a time, then refreshes once and says what went.
function ns.AbandonQuests(list)
    if busy or #list == 0 then return false end
    if ns.RouteInCombat() then ns.Print("Leave combat before cleaning your quest log."); return false end
    busy = true
    local queue, gone = {}, {}
    for _, quest in ipairs(list) do queue[#queue + 1] = quest end
    local function finish()
        busy = false
        ns.ForgetUselessQuestCount()
        if ns.ReadQuests then ns.ReadQuests() end
        if ns.ScheduleRefresh then ns.ScheduleRefresh(true) end
        if #gone > 0 then
            local names = {}
            for index = 1, math.min(4, #gone) do names[index] = gone[index] end
            ns.Print("Abandoned " .. #gone .. (#gone == 1 and " quest" or " quests") .. " no longer worth doing: "
                .. table.concat(names, ", ") .. (#gone > 4 and (" and " .. (#gone - 4) .. " more") or "") .. ".")
        end
        ns.questCleanupStatus = "Abandoned " .. #gone .. " of " .. #list .. "."
    end
    local function step()
        local quest = table.remove(queue, 1)
        if not quest then finish(); return end
        if ns.RouteInCombat() then queue = {}; finish(); return end   -- A fight started: stop here.
        if abandon(quest.id) then gone[#gone + 1] = quest.title end
        if C_Timer and type(C_Timer.After) == "function" then ns.After("timer:QuestCleanup", PACE, step) else step() end
    end
    step()
    return true
end

local function closePrompt() if prompt then prompt:Hide() end; offered = nil end

local function ask(list)
    if not prompt then
        local colors = ns.UIColors
        prompt = CreateFrame("Frame", "WowTogetherCleanupPrompt", UIParent, "BackdropTemplate")
        ns.questCleanupPrompt = prompt
        prompt:SetSize(440, 250); prompt:SetPoint("TOP", UIParent, "TOP", 0, -140); prompt:SetFrameStrata("DIALOG")
        prompt:SetClampedToScreen(true); ns.UIPanel(prompt); ns.UIClose(prompt)
        prompt.title = ns.UILabel(prompt, "GameFontNormalLarge", 15, colors.gold)
        prompt.title:SetPoint("TOPLEFT", 16, -14); prompt.title:SetWidth(380)
        prompt.body = ns.UILabel(prompt, nil, 12, colors.text)
        prompt.body:SetPoint("TOPLEFT", 16, -42); prompt.body:SetSize(408, 150)
        prompt.body:SetJustifyH("LEFT"); prompt.body:SetJustifyV("TOP"); prompt.body:SetWordWrap(true)
        prompt.yes = ns.UIButton(prompt, "Abandon them", 130, function()
            local list = offered; closePrompt()
            if list then ns.AbandonQuests(list) end
        end, true)
        prompt.yes:SetPoint("BOTTOMLEFT", 16, 12)
        prompt.no = ns.UIButton(prompt, "Keep them", 110, function()
            for _, quest in ipairs(offered or {}) do declined[quest.id] = true end
            ns.ForgetUselessQuestCount()
            closePrompt()
        end)
        prompt.no:SetPoint("LEFT", prompt.yes, "RIGHT", 8, 0)
        prompt.always = ns.UIButton(prompt, "Always clean", 130, function()
            local list = offered; closePrompt()
            ns.SetOption("questCleanup", "auto")
            ns.Print("Quests no longer worth doing are now abandoned without asking after each level-up. Settings change this.")
            if list then ns.AbandonQuests(list) end
        end)
        prompt.always:SetPoint("LEFT", prompt.no, "RIGHT", 8, 0)
        ns.UIHelp(prompt.no, "Keep these quests and do not ask about them again this session.")
        ns.UIHelp(prompt.always, "Never ask: abandon such quests after each level-up. Abandoning cannot be undone.")
    end
    offered = list
    local lines = {}
    for index, quest in ipairs(list) do
        if index > SHOWN then lines[#lines + 1] = "…and " .. (#list - SHOWN) .. " more"; break end
        lines[#lines + 1] = "Lv " .. quest.level .. "  " .. quest.title .. "  •  " .. quest.xp .. " XP now"
    end
    prompt.title:SetText("Abandon " .. #list .. (#list == 1 and " quest" or " quests") .. " no longer worth doing?")
    prompt.body:SetText(table.concat(lines, "\n") .. "\n\nNone is finished or nearly finished. Abandoning cannot be undone.")
    prompt:SetHeight(110 + math.min(#list, SHOWN + 1) * 15 + 30)
    prompt:Show()
end

-- Looks at the log and acts as the setting says. `byHand` is the /wt clean command.
function ns.QuestLogCleanup(byHand)
    local how = mode()
    if how == "off" and not byHand then return 0 end
    if busy then return 0 end
    if ns.RouteInCombat() then
        if byHand then ns.Print("Leave combat before cleaning your quest log.") end
        return 0
    end
    if byHand then declined = {} end
    local list = ns.UselessQuests()
    ns.questCleanupStatus = #list .. " quest(s) no longer worth doing."
    if #list == 0 then
        if byHand then ns.Print("Nothing to clean: every quest in your log is still worth doing, finished or nearly finished.") end
        return 0
    end
    if how == "auto" and not byHand then ns.AbandonQuests(list) else ask(list) end
    return #list
end

-- A level gained is when quests turn worthless: look a few seconds later.
ns.On("PLAYER_LEVEL_UP", function()
    if mode() == "off" or not C_Timer or type(C_Timer.After) ~= "function" then return end
    ns.After("timer:QuestCleanup", 6, function() ns.QuestLogCleanup(false) end)
end)

function ns.QuestCleanupDiagnostics(output)
    output("Quest log clean-up: " .. mode() .. "; " .. (ns.questCleanupStatus or "not looked at yet")
        .. " Offered after a level-up or with /wt clean; never in combat.")
end
