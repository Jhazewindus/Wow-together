local addonName, ns = ...

local indexed, followups

function ns.PartyLevelFloor()
    local level, key, name
    for _, person in ipairs(ns.PartyProfiles()) do
        local value = person.profile and person.profile.level
        if ns.GuideInteger(value) and value > 0 and
            (not level or value < level or value == level and person.key < key) then
            level, key, name = value, person.key, person.name
        end
    end
    return level, key or ns.self, name or "You"
end

function ns.GuideFocus(records)
    local _, fallback = ns.PartyLevelFloor()
    local chosen, progress
    for _, person in ipairs(ns.PartyProfiles()) do
        if person.synced then
            local done, checked, total = 0, 0, 0
            local active = person.key == ns.self and ns.active or ns.members[person.key].active
            for _, record in ipairs(records or {}) do
                if ns.CatalogueIdentityAllowed(record.id, person.profile) ~= false then
                    total = total + 1
                    local completed = ns.CatalogueCompletion(person.key, record.id)
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
    if quest.previousQuest or quest.prerequisiteAny then
        return ns.CatalogueAllowed(record.id, profile, key) == true
    end
    return true
end

function ns.QuestDifficultyLabel(id)
    if ns.IsDungeonQuest(id) then return "Dungeon / group" end
    if ns.IsGroupQuest(id) then return "Group / elite" end
    return "Normal quest"
end

local function nextQuests(id)
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
            for _, previous in ipairs(quest.prerequisiteAny or {}) do add(previous, nextID) end
            for position, current in ipairs(quest.series or {}) do
                if quest.series[position + 1] then add(current, quest.series[position + 1]) end
            end
        end
    end
    return followups[id] or {}
end

function ns.UsefulQuestReason(id, key, level)
    local queue, seen, cursor = {id}, {[id] = true}, 1
    local lower = math.max(1, level - math.max(5, math.floor(level * 0.2)))
    while queue[cursor] and cursor <= 128 do
        local previous = queue[cursor]; cursor = cursor + 1
        for nextID in pairs(nextQuests(previous)) do
            if not seen[nextID] then
                seen[nextID] = true
                local quest = ns.CatalogueQuest(nextID)
                local profile = key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
                if quest and not quest.repeatable and not ns.IsProfessionQuest(nextID)
                    and ns.CatalogueIdentityAllowed(nextID, profile) == true
                    and ns.CatalogueCompletion(key, nextID) ~= true then
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

function ns.LevelingValue(id)
    local quest = ns.CatalogueQuest(id)
    if not quest then return true end
    local level, key = ns.PartyLevelFloor()
    if not level then return nil end
    if ns.IsGroupQuest(id) and #(ns.partyNames or {}) == 0 then return false, "Group / elite: bring a party." end
    local value = quest.level or 0
    if value == 0 then return true end
    if value > level + 3 then return false, "Above the lowest player's level range." end
    if value >= math.max(1, level - math.max(5, math.floor(level * 0.2))) then return true end
    local reason = ns.UsefulQuestReason(id, key, level)
    if not reason then
        for _, person in ipairs(ns.PartyProfiles()) do
            if person.synced then reason = ns.UsefulQuestReason(id, person.key, level) end
            if reason then break end
        end
    end
    if reason then return true, reason end
    return false, "Below the useful level range; no worthwhile follow-up is known."
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
