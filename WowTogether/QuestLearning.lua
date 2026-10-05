local addonName, ns = ...

local LIMIT, baselines, tracking = 512, {}, {}
local ruleIndex, indexData, indexRevision = {}, nil, nil
local function data() return ns.db and ns.db.questLearning end
local function set(list)
    local result = {}
    if type(list) ~= "table" then return result end
    for _, id in ipairs(list) do if ns.GuideInteger(id) and id > 0 then result[id] = true end end
    return result
end
local function scope(record)
    if type(record) ~= "table" or record.interface ~= 16001 or type(record.build) ~= "string"
        or not string.match(record.build, "^%d+$") or #record.build > 12
        or (record.faction ~= "Horde" and record.faction ~= "Alliance")
        or record.classID ~= nil and not ns.GuideInteger(record.classID, 255)
        or record.raceID ~= nil and not ns.GuideInteger(record.raceID, 255) then return end
    return table.concat({record.interface, record.build, record.faction, record.classID or 0, record.raceID or 0}, ":")
end
local function currentContext(profile)
    local _, build, _, interface = ns.ReadPublic(GetBuildInfo)
    return {interface = interface, build = build, faction = profile and profile.faction,
        classID = profile and profile.classID, raceID = profile and profile.raceID}
end

local function restrictions(parent, child)
    local class, race = false, false
    for _, id in ipairs({parent, child}) do
        local quest = ns.CatalogueQuest(id) or {}
        class = class or (quest.classMask or 0) > 0 or string.match(quest.categoryPath or "", "^classes/") ~= nil
        race = race or (quest.raceMask or 0) > 0
    end
    return class, race
end

local function ruleScope(context, parent, child)
    if type(context) ~= "table" or context.interface ~= 16001 or type(context.build) ~= "string"
        or not string.match(context.build, "^%d+$") or #context.build > 12
        or (context.faction ~= "Horde" and context.faction ~= "Alliance") then return end
    local class, race = restrictions(parent, child)
    if class and (not ns.GuideInteger(context.classID, 255) or context.classID == 0)
        or race and (not ns.GuideInteger(context.raceID, 255) or context.raceID == 0) then return end
    return table.concat({context.interface, context.build, context.faction,
        class and context.classID or 0, race and context.raceID or 0}, ":"), class, race
end

local function indexedRules(id)
    local saved = data()
    if saved ~= indexData or saved.revision ~= indexRevision then
        ruleIndex, indexData, indexRevision = {}, saved, saved.revision
        local keys = {}; for key in pairs(saved.rules) do keys[#keys + 1] = key end; table.sort(keys)
        for _, key in ipairs(keys) do
            local rule = saved.rules[key]
            ruleIndex[rule.questID] = ruleIndex[rule.questID] or {}
            table.insert(ruleIndex[rule.questID], rule)
        end
    end
    return ruleIndex[id] or {}
end
local function changed()
    local saved = data()
    saved.revision = saved.revision + 1
    ns.forceRouteReplan, ns.routeSignature = true, nil
end

function ns.ResetLearningContext()
    baselines, tracking = {}, {}
end

local function singleGiver(id, npcID)
    local quest, seen = ns.CatalogueQuest(id), {}
    if not quest then return false end
    for _, point in ipairs(quest.starts or {}) do
        if not point.npc or not point.entityID then return false end
        seen[point.entityID] = true
    end
    local count = 0; for giver in pairs(seen) do count = count + 1; if giver ~= npcID then return false end end
    return count == 1
end

local function usable(rule, context)
    return rule.scope == ruleScope(context, rule.previousQuest, rule.questID)
        and rule.disabled ~= true and not rule.ambiguous
        and not ns.IsRepeatableQuest(rule.questID) and not ns.IsRepeatableQuest(rule.previousQuest)
        and not ns.IsProfessionQuest(rule.questID) and not ns.IsProfessionQuest(rule.previousQuest)
        and singleGiver(rule.questID, rule.npcID)
end

local function matchingRule(id, context)
    local found
    for _, rule in ipairs(indexedRules(id)) do
        if usable(rule, context) then
            if found and found.previousQuest ~= rule.previousQuest then return end
            found = rule
        end
    end
    return found
end

function ns.LearnedQuestRule(id, profile, key)
    if not ns.GuideInteger(id) or id <= 0 or key and key ~= ns.self
        or not ns.Option("useLearnedQuests") or not data() then return end
    return matchingRule(id, currentContext(profile or ns.profile))
end

function ns.LearnedPrerequisiteIDs(id)
    local rule = ns.LearnedQuestRule(id)
    local quest = ns.CatalogueQuest(id)
    if quest and (quest.previousQuest or quest.prerequisiteAny) then return {} end
    return rule and {rule.previousQuest} or {}
end

function ns.LearnedFollowers(id, key)
    local result, context, seen = {}, currentContext(ns.profile), {}
    if key and key ~= ns.self or not ns.Option("useLearnedQuests") or not data() then return result end
    for _, rule in pairs(data().rules) do
        if rule.previousQuest == id and usable(rule, context) and not seen[rule.questID]
            and matchingRule(rule.questID, context) then
            result[#result + 1], seen[rule.questID] = rule.questID, true
        end
    end
    table.sort(result); return result
end

function ns.LearnedPrerequisiteAllowed(id, profile, key)
    local quest = ns.CatalogueQuest(id)
    -- Published alternatives must not be narrowed to a single observed branch.
    if quest and (quest.previousQuest or quest.prerequisiteAny) then return true end
    local rule = ns.LearnedQuestRule(id, profile, key)
    if not rule then return true end
    local completed = ns.CatalogueCompletion(key or ns.self, rule.previousQuest)
    if completed == true then return true end
    local reason = "Observed by " .. rule.sourceCharacter .. " (tentative): "
        .. (completed == false and "finish " or "check history for ") .. ns.QuestTitle(rule.previousQuest) .. " first."
    return completed, reason
end

function ns.LearnedStepSource(id, profile, key)
    local rule = ns.LearnedQuestRule(id, profile, key)
    if rule then return rule.sourceCharacter end
    for _, follower in ipairs(ns.LearnedFollowers(id, key)) do
        if ns.CatalogueCompletion(key or ns.self, follower) ~= true then
            rule = ns.LearnedQuestRule(follower, profile, key)
            if rule then return rule.sourceCharacter end
        end
    end
end

local function hasAncestor(id, wanted, seen, depth, context)
    if id == wanted then return true end
    if depth > 24 or seen[id] then return false end
    seen[id] = true
    local quest, ids = ns.CatalogueQuest(id) or {}, {}
    if quest.previousQuest then ids[#ids + 1] = quest.previousQuest end
    for _, previous in ipairs(quest.prerequisiteAny or {}) do ids[#ids + 1] = previous end
    local learned = matchingRule(id, context)
    if learned and not learned.disabled and not learned.ambiguous then ids[#ids + 1] = learned.previousQuest end
    for _, previous in ipairs(ids) do
        if hasAncestor(previous, wanted, seen, depth + 1, context) then return true end
    end
    return false
end

local function evidence(before, after, sourceID)
    local function publicCopy(record)
        local copy = {}
        for _, key in ipairs({"event", "sequence", "session", "level", "npcID", "offered", "active",
            "completed", "notCompleted", "historyUnknown", "reputationRevision", "completeList", "historyTruncated"}) do
            copy[key] = record[key]
        end
        return copy
    end
    return {sourceID = sourceID, before = publicCopy(before), after = publicCopy(after)}
end

local function remember(before, after, parent, child, source)
    if parent == child or ns.IsRepeatableQuest(parent) or ns.IsRepeatableQuest(child)
        or ns.IsProfessionQuest(parent) or ns.IsProfessionQuest(child) then return end
    local wanted, class, race = ruleScope(after, parent, child)
    if not wanted then return end
    local saved, key = data(), wanted .. ":" .. child
    local rule = saved.rules[key]
    if not rule then
        local count = 0; for _ in pairs(saved.rules) do count = count + 1 end
        if count >= LIMIT then ns.learningStatus = "Learning storage is full; export findings for review."; return end
        rule = {scope = wanted, interface = after.interface, build = after.build, faction = after.faction,
            classID = after.classID, raceID = after.raceID, npcID = after.npcID, questID = child,
            previousQuest = parent, sourceCharacter = ns.SafeTitle(ns.MemberLabel(source)) or "Unknown character",
            characters = {}, proofs = {}, level = after.level, tentative = true,
            classRestricted = class, raceRestricted = race}
        saved.rules[key] = rule
        indexData = nil
        if hasAncestor(parent, child, {}, 0, after) then rule.disabled, rule.reason = true, "Would create a prerequisite cycle." end
    elseif rule.previousQuest ~= parent then
        rule.disabled, rule.reason, rule.alternativeParent = true, "Another predecessor was observed; possible branching.", parent
        changed()
    end
    if not rule.characters[source] then
        rule.characters[source] = true
        if #rule.proofs < 4 then rule.proofs[#rule.proofs + 1] = evidence(before, after, saved.sources[source]) end
        changed()
    end
    if before.reputationRevision ~= after.reputationRevision and not rule.reputationNotification then
        rule.reputationNotification = true; changed()
    end
    if before.level ~= after.level then
        rule.ambiguous, rule.reason = true, "Level changed during the observed unlock; needs review."
        changed()
    end
end

function ns.ObserveQuestLearning(record, source)
    local saved, wanted = data(), scope(record)
    if not saved or not wanted or not ns.GuideInteger(record.session) or not ns.GuideInteger(record.sequence)
        or not ns.GuideInteger(record.level, 255) or record.level <= 0 then return end
    if not saved.sources[source] then saved.sourceSequence = saved.sourceSequence + 1; saved.sources[source] = saved.sourceSequence end
    local tag = source .. ":" .. record.session .. ":" .. wanted
    local state = tracking[source]
    if not state or state.tag ~= tag or record.sequence <= state.sequence then
        state = {tag = tag, sequence = 0, turnIns = {}, ordinal = 0}; tracking[source] = state
        baselines[source] = {}
    end
    state.sequence = record.sequence
    if record.event == "turn-in" and ns.GuideInteger(record.questID) and record.questID > 0 then
        state.ordinal = state.ordinal + 1
        state.turnIns[state.ordinal] = record.questID
        return
    end
    if record.event ~= "offers" or not ns.GuideInteger(record.npcID) or record.npcID <= 0 then return end
    local offered, undone, completed = set(record.offered), set(record.notCompleted), set(record.completed)
    -- Positive offers contradict a tentative dependency even in a partial list.
    for _, rule in pairs(saved.rules) do
        if rule.scope == ruleScope(record, rule.previousQuest, rule.questID) and rule.npcID == record.npcID and not rule.disabled
            and offered[rule.questID] and undone[rule.previousQuest] then
            rule.disabled, rule.reason = true, "NPC offered the quest before the learned prerequisite was completed."
            changed()
        end
    end
    local last = baselines[source][record.npcID]
    if last and state.ordinal - last.ordinal == 1 and not last.record.historyTruncated and not record.historyTruncated
        and last.record.mapID == record.mapID then
        local before, parent = last.record, state.turnIns[state.ordinal]
        local beforeDone, beforeUndone = set(before.completed), set(before.notCompleted)
        local beforeOffered, beforeActive = set(before.offered), set(before.active)
        local afterActive, deltas, additions = set(record.active), 0, 0
        for id in pairs(completed) do if beforeUndone[id] then deltas = deltas + 1 end end
        for id in pairs(afterActive) do if not beforeActive[id] then additions = additions + 1 end end
        if parent and beforeActive[parent] and beforeUndone[parent] and completed[parent] and deltas == 1 and additions == 0 then
            for child in pairs(offered) do
                if not beforeOffered[child] and not beforeActive[child] and beforeUndone[child]
                    and not beforeDone[child] and undone[child] and not afterActive[child]
                    and not completed[child] then remember(before, record, parent, child, source) end
            end
        end
    end
    if record.completeList == true then
        local count = 0; for _ in pairs(baselines[source]) do count = count + 1 end
        if not baselines[source][record.npcID] and count >= 64 then baselines[source] = {} end
        baselines[source][record.npcID] = {record = record, ordinal = state.ordinal}
    end
    -- Keep a bounded turn-in journal; older baselines cannot imply a clean pair.
    if state.ordinal >= 128 then tracking[source], baselines[source] = nil, nil end
end

function ns.InitializeQuestLearning()
    local saved = data()
    if type(saved) ~= "table" or (saved.schema ~= 1 and saved.schema ~= 2)
        or type(saved.rules) ~= "table" or type(saved.sources) ~= "table" then
        saved = {schema = 2, rules = {}, sources = {}, sourceSequence = 0, revision = 0}; ns.db.questLearning = saved
    end
    if not ns.GuideInteger(saved.sourceSequence) then saved.sourceSequence = 0 end
    if not ns.GuideInteger(saved.revision) then saved.revision = 0 end
    -- Preserve existing observations while broadening ordinary rules. Conflicting
    -- predecessors from formerly separate classes/races require review.
    local keys, migrated = {}, {}
    for key in pairs(saved.rules) do keys[#keys + 1] = key end; table.sort(keys)
    for _, key in ipairs(keys) do
        local rule = saved.rules[key]
        if type(rule) ~= "table" or not ns.GuideInteger(rule.questID) or not ns.GuideInteger(rule.previousQuest)
            or not ns.GuideInteger(rule.npcID) or type(rule.scope) ~= "string" or type(rule.sourceCharacter) ~= "string"
            or type(rule.characters) ~= "table" or type(rule.proofs) ~= "table" then rule = nil end
        local wanted, class, race
        if rule then wanted, class, race = ruleScope(rule, rule.previousQuest, rule.questID) end
        if wanted then
            rule.scope, rule.classRestricted, rule.raceRestricted = wanted, class, race
            local destination = wanted .. ":" .. rule.questID
            local existing = migrated[destination]
            if not existing then migrated[destination] = rule
            else
                if existing.previousQuest ~= rule.previousQuest or existing.npcID ~= rule.npcID then
                    existing.disabled, existing.alternativeParent = true, rule.previousQuest
                    existing.reason = "Conflicting observations merged across classes/races; needs review."
                end
                existing.disabled = existing.disabled or rule.disabled
                existing.ambiguous = existing.ambiguous or rule.ambiguous
                existing.reason = existing.reason or rule.reason
                existing.reputationNotification = existing.reputationNotification or rule.reputationNotification
                for character in pairs(rule.characters) do existing.characters[character] = true end
                for _, proof in ipairs(rule.proofs) do
                    if #existing.proofs < 4 then existing.proofs[#existing.proofs + 1] = proof end
                end
            end
        end
    end
    saved.rules, saved.schema, saved.revision = migrated, 2, saved.revision + 1
    indexData = nil
    ns.ResetLearningContext()
    local names = {}; for name in pairs(ns.db.questResearch or {}) do names[#names + 1] = name end; table.sort(names)
    for _, name in ipairs(names) do
        local research = ns.db.questResearch[name]
        if type(research) == "table" and type(research.events) == "table" then
            for _, record in ipairs(research.events) do ns.ObserveQuestLearning(record, name) end
        end
    end
    ns.ResetLearningContext() -- A reload/pause is an observation gap.
end

function ns.ExportLearnedFindings()
    local result, saved = {}, data()
    if not saved then return result end
    local keys = {}; for key in pairs(saved.rules) do keys[#keys + 1] = key end; table.sort(keys)
    for _, key in ipairs(keys) do
        local rule, copy = saved.rules[key], {}
        for _, field in ipairs({"questID", "previousQuest", "npcID", "interface", "build", "faction", "classID",
            "raceID", "level", "tentative", "disabled", "reason", "ambiguous", "alternativeParent",
            "reputationNotification", "proofs", "classRestricted", "raceRestricted"}) do copy[field] = rule[field] end
        local count = 0; for _ in pairs(rule.characters) do count = count + 1 end; copy.sourceCount = count
        if ns.Option("exportCharacterNames") then copy.sourceCharacter = rule.sourceCharacter end
        result[#result + 1] = copy
    end
    return result
end

function ns.LearningDiagnostics(output)
    local active, disabled, ambiguous = 0, 0, 0
    for _, rule in pairs(data() and data().rules or {}) do
        if rule.disabled then disabled = disabled + 1 elseif rule.ambiguous then ambiguous = ambiguous + 1 else active = active + 1 end
    end
    output("Observed quest learning: " .. (ns.Option("useLearnedQuests") and "on" or "off") .. "; "
        .. active .. " patterns; " .. disabled .. " contradicted/disabled; " .. ambiguous .. " need review.")
    output("Ordinary patterns match build/faction; class/race are required only for restricted quests or prerequisites.")
    output("A skip is saved for this character; it does not learn an unlock or confirm a missing NPC offer.")
    if ns.learningStatus then output(ns.learningStatus) end
end
