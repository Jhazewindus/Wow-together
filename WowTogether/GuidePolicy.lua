local addonName, ns = ...

local indexed, followups

-- Prefer worthwhile leveling work, rather than the entire green difficulty
-- band. Lower quests can still qualify through their useful continuations.
local function preferredFloor(level)
    return math.max(1, level - 3)
end

function ns.PreferredQuestLevels(query)
    local level = ns.PartyLevelFloor(query)
    if level then return preferredFloor(level), level + 3 end
end

function ns.PartyLevelFloor(query)
    if query and query.floor then return query.floor[1], query.floor[2], query.floor[3] end
    local level, key, name
    for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
        local value = person.profile and person.profile.level
        if person.synced and ns.GuideInteger(value) and value > 0 and
            (not level or value < level or value == level and person.key < key) then
            level, key, name = value, person.key, person.name
        end
    end
    key, name = key or ns.self, name or "You"
    if query then query.floor = {level, key, name} end
    return level, key, name
end

function ns.GuideFocus(records, query)
    local _, fallback = ns.PartyLevelFloor(query)
    local chosen, progress
    for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
        if person.synced then
            local done, checked, total = 0, 0, 0
            local active = person.key == ns.self and ns.active or ns.members[person.key].active
            for _, record in ipairs(records or {}) do
                if ns.CatalogueIdentityAllowed(record.id, person.profile) ~= false then
                    total = total + 1
                    local completed = ns.CatalogueCompletion(person.key, record.id, query)
                    if completed ~= nil or active and active[record.id] then checked = checked + 1 end
                    if completed == true and not (active and active[record.id]) then done = done + 1 end
                end
            end
            -- Unknown history cannot establish that someone is behind.
            if total > 0 and checked == total then
                local value = done / total
                if not chosen or value < progress or value == progress and person.key < chosen then
                    chosen, progress = person.key, value
                end
            end
        end
    end
    return chosen or fallback
end

function ns.IsGroupQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and (quest.questType == "Elite" or quest.questType == "Raid") or false
end

function ns.FocusCanStartRecord(record, key)
    local quest = ns.CatalogueQuest(record.id)
    if not quest then return true end
    local active = key == ns.self and ns.active or ns.members[key] and ns.members[key].active
    local profile = key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
    if active and active[record.id] or ns.CatalogueCompletion(key, record.id) == true
        or ns.CatalogueIdentityAllowed(record.id, profile) == false then return true end
    if quest.previousQuest or quest.prerequisiteAny or quest.prerequisiteAll then
        return ns.CatalogueAllowed(record.id, profile, key) == true
    end
    return true
end

function ns.QuestDifficultyLabel(id)
    if ns.IsDungeonQuest(id) then return "Dungeon / group" end
    if ns.IsGroupQuest(id) then return "Group / elite" end
    return "Normal quest"
end

local function nextQuests(id, key)
    if indexed ~= ns.catalogue then
        indexed, followups = ns.catalogue, {}
        local function add(previous, nextID)
            if previous and previous ~= nextID then
                followups[previous] = followups[previous] or {}
                followups[previous][nextID] = true
            end
        end
        for nextID, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
            add(quest.previousQuest, nextID)
            for _, previous in ipairs(quest.prerequisiteAll or {}) do add(previous, nextID) end
            for _, previous in ipairs(quest.prerequisiteAny or {}) do add(previous, nextID) end
            for position, current in ipairs(quest.series or {}) do
                if quest.series[position + 1] then add(current, quest.series[position + 1]) end
            end
        end
    end
    local result = {}; for nextID in pairs(followups[id] or {}) do result[nextID] = true end
    for _, nextID in ipairs(ns.LearnedFollowers and ns.LearnedFollowers(id, key) or {}) do result[nextID] = true end
    return result
end

function ns.UsefulQuestReason(id, key, level, query)
    local queue, seen, cursor = {id}, {[id] = true}, 1
    local lower = preferredFloor(level)
    while queue[cursor] and cursor <= 128 do
        local previous = queue[cursor]; cursor = cursor + 1
        for nextID in pairs(nextQuests(previous, key)) do
            if not seen[nextID] then
                seen[nextID] = true
                local quest = ns.CatalogueQuest(nextID)
                local profile = key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
                if quest and not ns.IsLevelingExcludedQuest(nextID) and not quest.repeatable and not ns.IsProfessionQuest(nextID)
                    and ns.CatalogueIdentityAllowed(nextID, profile) == true
                    and ns.CatalogueCompletion(key, nextID, query) ~= true then
                    local value = quest.level or 0
                    local dungeon = ns.IsDungeonQuest(nextID) and (quest.minLevel or value) <= level + 5 and value <= level + 8
                    if dungeon or value >= lower and value <= level + 3 then
                        return "Unlocks " .. quest.title .. (ns.IsDungeonQuest(nextID) and " (dungeon quest)." or " (level " .. value .. ").")
                    end
                    if #queue < 128 then queue[#queue + 1] = nextID end
                end
            end
        end
    end
end

local function levelingValue(id, query)
    local quest = ns.CatalogueQuest(id)
    if not quest then return true end
    local level, key = ns.PartyLevelFloor(query)
    if not level then return nil end
    if ns.IsGroupQuest(id) and #(ns.partyNames or {}) == 0 then return false, "Group / elite: bring a party." end
    local value = quest.level or 0
    if value == 0 then return true end
    if value > level + 3 then return false, "Above the lowest player's level range." end
    if ns.IsClassQuest(id) then return true, "Class progression." end
    if value >= preferredFloor(level) then return true end
    local reason = ns.UsefulQuestReason(id, key, level, query)
    if not reason then
        for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
            if person.synced then reason = ns.UsefulQuestReason(id, person.key, level, query) end
            if reason then break end
        end
    end
    if reason then return true, reason end
    return false, "Below preferred quest levels " .. preferredFloor(level) .. "–" .. (level + 3) .. "; no worthwhile follow-up is known."
end

function ns.LevelingValue(id, query)
    if not query then return levelingValue(id) end
    query.values = query.values or {}
    local cached = query.values[id]
    if cached then return cached[1], cached[2] end
    local value, reason = levelingValue(id, query)
    query.values[id] = {value, reason}
    return value, reason
end

-- Being in a quest log is not a reason to bypass the leveling band. Retain a
-- ready hand-in for that character without sending others to finish old work.
function ns.LevelingWorkAllowed(id, key, query)
    if ns.LevelingValue(id, query) ~= false then return true end
    local active = key == ns.self and ns.active or ns.members[key] and ns.members[key].active
    return active and active[id] ~= nil and (ns.QuestProgressReady(key, id) == true
        or key == ns.self and ns.readyToTurnIn[id] == true) or false
end

function ns.QuestLogReview()
    local result = {}
    for id in pairs(ns.active or {}) do
        local useful, reason = ns.LevelingValue(id)
        if ns.IsRepeatableQuest(id) then reason = "Repeatable; outside the leveling plan."; useful = false end
        if useful == false and not ns.readyToTurnIn[id] and not ns.IsProfessionQuest(id) and not ns.IsClassQuest(id) then
            result[#result + 1] = {id = id, title = ns.QuestTitle(id), reason = reason}
        end
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end
