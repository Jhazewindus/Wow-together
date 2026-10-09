local addonName, ns = ...

-- Explain the selected plan from facts, without changing it. An explanation
-- is not proof of an NPC offer, a walkable road or globally optimal XP/time.
local cached
local goalFields = {"id", "kind", "mapID", "x", "y", "title", "npcName", "action", "itemName", "targetName",
    "unknownLocation", "planNeedsReview", "travelReason", "confirmation", "dungeonEntrance", "professionStep",
    "memberKey", "objectiveKey", "quantity", "quantityUnknown", "useItemName", "flowWithQuestID", "flowUnlockQuestID",
    "flowRewardFirst", "flowLogSpace", "flowEarlyReward"}
local function unchanged(decision, goal)
    for _, field in ipairs(goalFields) do
        if not ns.Public(goal[field]) or decision.goalFacts[field] ~= goal[field] then return false end
    end
    return true
end
local function text(value) return ns.SafeTitle(value) end
local function contains(values, id)
    for _, value in ipairs(values or {}) do if value == id then return true end end
    return false
end

function ns.GuideDestination(stop)
    local goal = stop or {}
    for _ = 1, 8 do
        if goal.goal then goal = goal.goal elseif goal.sourceStop then goal = goal.sourceStop else break end
    end
    return goal
end

local function context(guide, route)
    local profile = ns.profile or {}
    local learning = ns.db and ns.db.questLearning
    if not cached or cached.guide ~= guide or cached.route ~= route or cached.catalogue ~= ns.catalogue
        or cached.progress ~= ns.localProgress or cached.active ~= ns.active
        or cached.revision ~= ns.objectiveDisplayRevision or cached.learning ~= (learning and learning.revision)
        or cached.guideRevision ~= ns.guideProgressRevision or cached.useLearned ~= ns.Option("useLearnedQuests")
        or cached.level ~= profile.level or cached.class ~= profile.classID or cached.race ~= profile.raceID
        or cached.faction ~= profile.faction or cached.classQuests ~= ns.Option("classQuests") then
        cached = {guide = guide, route = route, catalogue = ns.catalogue, progress = ns.localProgress,
            active = ns.active, revision = ns.objectiveDisplayRevision, learning = learning and learning.revision,
            guideRevision = ns.guideProgressRevision, useLearned = ns.Option("useLearnedQuests"),
            level = profile.level, class = profile.classID, race = profile.raceID, faction = profile.faction,
            classQuests = ns.Option("classQuests"), query = ns.NewQuestQuery(), decisions = {}}
    end
    return cached
end

local function result(code, why, specific, related)
    return {code = code, why = why, specificBenefit = specific == true, relatedQuestIDs = related or {}}
end

local function unfinished(id, key, ctx)
    local member = key ~= ns.self and ns.members[key]
    local active = key == ns.self and ns.active or member and member.active
    local profile = key == ns.self and ns.profile or member and member.profile
    return not (active and active[id]) and not ns.GuideQuestSkipped(id) and ns.ClassQuestEnabled(id)
        and ns.CatalogueIdentityAllowed(id, profile) == true
        and ns.CatalogueCompletion(key, id, ctx.query) ~= true
end

local function continuation(goal, ctx)
    local guide, key = ctx.guide, goal.memberKey or ns.self
    for _, record in ipairs(guide and guide.records or {}) do
        local quest = ns.CatalogueQuest(record.id)
        if quest and record.id ~= goal.id then
            local required = quest.previousQuest == goal.id or contains(quest.prerequisiteAll, goal.id)
            local learned = key == ns.self and contains(ns.LearnedPrerequisiteIDs(record.id), goal.id)
            local alternatives = contains(quest.prerequisiteAny, goal.id)
            local chosen = contains(guide.collectionDependencies and guide.collectionDependencies[record.id], goal.id)
            -- Check history only for an actual relation, not every guide record
            -- on each progress refresh.
            if (required or learned or alternatives and chosen) and not quest.prerequisitesUnverified
                and unfinished(record.id, key, ctx) then
                return record.id, text(quest.title) or text(record.title), learned, alternatives and not required
            end
        end
    end
end

local function visit(goal, ctx)
    if not ns.ValidTravelPoint(goal) or goal.unknownLocation then return end
    local found, ids, seen = false, {}, {}
    for _, point in ipairs(ctx.route and ctx.route.stops or {}) do
        if not found and point.id == goal.id and point.kind == goal.kind then found = true end
        if found then
            if point.kind ~= goal.kind or point.mapID ~= goal.mapID or point.unknownLocation
                or not ns.ValidTravelPoint(point) then break end
            local yards = point.x == goal.x and point.y == goal.y and 0 or ns.WalkingDistance(goal.mapID, goal, point)
            if not yards or yards > 100 then break end
            local key = point.memberKey or ns.self
            local member = key ~= ns.self and ns.members[key]
            local profile = key == ns.self and ns.profile or member and member.profile
            local eligible = goal.kind ~= "a" or unfinished(point.id, key, ctx)
                and ns.CatalogueAllowed(point.id, profile, key, ctx.query) == true
            if not seen[point.id] and not ns.GuideQuestSkipped(point.id) and #ns.FilterGuideStages({point}) > 0
                and eligible then
                seen[point.id], ids[#ids + 1] = true, point.id
            end
        end
    end
    return #ids > 1 and ids or nil
end

local function objectiveVisit(goal, ctx)
    if not ns.ValidTravelPoint(goal) or goal.unknownLocation then return end
    local found, ids, seen = false, {}, {}
    for _, point in ipairs(ctx.route and ctx.route.stops or {}) do
        if not found and point.id == goal.id and point.kind == "q"
            and (not goal.objectiveKey or point.objectiveKey == goal.objectiveKey) then found = true end
        if found then
            if point.kind ~= "q" or point.mapID ~= goal.mapID or point.unknownLocation
                or not ns.ValidTravelPoint(point) then break end
            local yards = point.x == goal.x and point.y == goal.y and 0 or ns.WalkingDistance(goal.mapID, goal, point)
            if not yards or yards > 250 / 0.9144 then break end
            local key = point.memberKey or ns.self
            local member = key ~= ns.self and ns.members[key]
            local active = key == ns.self and ns.active or member and not member.syncPending and member.active
            local facts = ns.GuideStepFacts(point)
            local action = facts.action
            if action ~= "kill" and action ~= "loot" and action ~= "collect" and action ~= "gather" then break end
            if active and active[point.id] and not seen[point.id] and not facts.finished and facts.remaining ~= 0
                and not ns.GuideQuestSkipped(point.id) and #ns.FilterGuideStages({point}) > 0 then
                seen[point.id], ids[#ids + 1] = true, point.id
            end
        end
    end
    return #ids > 1 and ids or nil
end

local function flowReason(goal, ctx)
    local other = ns.CatalogueQuest(goal.flowWithQuestID)
    local key = goal.memberKey or ns.self
    local member = key ~= ns.self and ns.members[key]
    local profile = key == ns.self and ns.profile or member and member.profile
    if not other or ns.GuideQuestSkipped(goal.flowWithQuestID) or not ns.ClassQuestEnabled(goal.flowWithQuestID)
        or ns.CatalogueIdentityAllowed(goal.flowWithQuestID, profile) ~= true
        or ns.CatalogueCompletion(key, goal.flowWithQuestID, ctx.query) == true then return end
    local title = text(other.title)
    if not title then return end
    local child = ns.CatalogueQuest(goal.flowUnlockQuestID)
    if goal.kind == "t" and child and unfinished(goal.flowUnlockQuestID, key, ctx) then
        return result("unlock-loop", "This hand-in progresses toward " .. child.title
            .. "; its work can join " .. title .. " in the same area.", true, {goal.flowUnlockQuestID, goal.flowWithQuestID})
    end
    local active = key == ns.self and ns.active or member and member.active
    if active and active[goal.flowWithQuestID] and ns.QuestProgressReady(key, goal.flowWithQuestID) ~= true then
        if goal.kind == "a" then return result("pickup-loop", "Pick this up before leaving; its work joins " .. title
            .. " in the same area.", true, {goal.flowWithQuestID}) end
        if goal.kind == "q" then return result("shared-loop", "Do this area together with " .. title
            .. " to avoid a separate trip.", true, {goal.flowWithQuestID}) end
    end
end

local function explain(goal, ctx)
    local title, quest, guide = text(goal.title) or "this quest", ns.CatalogueQuest(goal.id), ctx.guide
    if text(goal.travelReason) then return result("planned-purpose", text(goal.travelReason), true) end
    if goal.dungeonEntrance then
        return result("dungeon-run", "The dungeon quest objectives require a run through " .. title .. ".", true)
    end
    if goal.kind == "trainer" then
        return result("class-training", "Optional training check near your quest route; new class skills may be available.", true)
    end
    if goal.confirmation then
        return result("confirm-offer", "Talk to " .. (text(goal.npcName) or "the quest giver")
            .. " to check this quest's pickup requirements before continuing.", true)
    end
    if goal.kind == "corpse" then return result("corpse", "Recover your body to resume the selected guide.", true) end
    if guide and guide.mode == "travel" then
        return result("selected-travel", "You selected the quickest known journey to " .. (text(guide.zone) or title) .. ".", true)
    end
    if goal.professionStep then
        return result("profession-work", text(goal.description) or "Progress toward the skill goal you selected.", true)
    end
    if goal.kind ~= "a" and goal.kind ~= "q" and goal.kind ~= "t" then
        return result("guide-status", text(goal.label) or "Waiting for the next step of your selected guide.", false)
    end
    local useful, exception = ns.LevelingValue(goal.id, ctx.query)
    if guide and guide.catchupRequired and guide.catchupRequired[goal.id] then
        return result("party-prerequisite", "This prerequisite helps your party catch up through the quest chain.", true)
    end
    if useful == true and exception and not ns.IsClassQuest(goal.id) then
        return result("useful-prerequisite", "Lower-level step: " .. exception, true)
    end
    if goal.kind == "t" and goal.flowRewardFirst then
        return result("reward-first", "Collect this reward before the next work; its XP helps with the levels needed later in this guide.", true)
    end
    if goal.kind == "t" and goal.flowEarlyReward then
        return result("early-reward", "Hand this in while you're here to collect XP before your next quest work.", true)
    end
    if goal.kind == "t" and goal.flowLogSpace then
        return result("quest-log-space", "Hand this in during this visit to leave more room for the next quest pickups.", true)
    end
    local flow = flowReason(goal, ctx)
    if flow then return flow end
    local nextID, nextTitle, learned, alternative = continuation(goal, ctx)
    if nextID then
        if alternative then return result("chosen-branch", "Chosen branch toward " .. nextTitle .. "; other prerequisites may also work.", true, {nextID}) end
        return result(learned and "learned-prerequisite" or "prerequisite", "Required for " .. nextTitle
            .. " later in this guide; finish and turn in " .. title .. " first.", true, {nextID})
    end
    if guide and guide.mode == "dungeon" and guide.collectionGoals and guide.collectionGoals[goal.id] and goal.kind == "a" then
        return result("dungeon-pickup", "Collect " .. title .. " before entering " .. (text(guide.zone) or "the dungeon") .. ".", true)
    end
    local ids = (goal.kind == "a" or goal.kind == "t") and visit(goal, ctx)
    if ids then
        return result(goal.kind == "a" and "pickup-hub" or "return-hub", "This visit groups " .. #ids
            .. (goal.kind == "a" and " nearby quest pickups before heading out." or " nearby hand-ins to collect their rewards together."), true, ids)
    end
    if goal.kind == "t" then
        return result("quest-reward", "Return here to collect the reward for " .. title .. ".", true)
    end
    if ns.IsClassQuest(goal.id) then
        return result("class-progression", "Optional class progression; follow it for your class, or use Skip quest.", true)
    end
    if useful == false and not (guide and guide.mode == "dungeon") then
        if ns.GuideDifficultyOverride(guide) then
            return result("chosen-level-range", "Outside the recommended level range; included because you chose Continue anyway.", true)
        end
        return result("outside-level-range", "Outside your useful leveling range; this saved or previewed step can be skipped.", false)
    end
    if goal.kind == "q" then
        ids = objectiveVisit(goal, ctx)
        if ids then return result("objective-area", "This area advances " .. #ids .. " accepted quests in one visit.", true, ids) end
        local facts = ns.GuideStepFacts(goal)
        local target = text(facts.item) or text(facts.target)
        return result("quest-objective", target and (target .. " is needed to finish " .. title .. ".")
            or ("Finish " .. title .. " before collecting its reward."), true)
    end
    local level = quest and quest.level
    if ns.GuideInteger(level) and level > 0 then
        return result("level-work", "This level " .. level .. " quest adds leveling work to your selected guide.", false)
    end
    return result("selected-guide", "Included in your selected guide; no extra unlock benefit is recorded for " .. title .. ".", false)
end

function ns.GuideDestinationDecision(stop, guide, route)
    if stop and stop.flightDiscovery then
        local decision = result("flight-check", ns.TravelPathSummary(stop) or "Check the nearer flight master's connections.", true)
        decision.estimated = true; return decision
    end
    local goal = ns.GuideDestination(stop)
    if goal.inventoryService then return result("service", goal.serviceReason, true) end
    local ctx = context(guide or ns.routeSelection, route or ns.selectedRoute)
    if ctx.decisions[goal] and unchanged(ctx.decisions[goal], goal) then return ctx.decisions[goal] end
    local decision = explain(goal, ctx)
    local quest = ns.CatalogueQuest(goal.id)
    decision.questID, decision.stage = goal.id, goal.kind
    decision.goalFacts = {}; for _, field in ipairs(goalFields) do
        if ns.Public(goal[field]) then decision.goalFacts[field] = goal[field] end
    end
    decision.needsReview = not decision.specificBenefit or goal.unknownLocation == true or goal.planNeedsReview == true
        or quest and quest.prerequisitesUnverified == true or false
    if goal.unknownLocation and not goal.professionStep then decision.caution = "Exact destination not mapped; check the quest tracker."
    elseif goal.kind == "a" and quest and (not quest.prerequisitesRead or quest.prerequisitesUnverified or goal.planNeedsReview)
        and ns.PickupOfferEvidence(goal.memberKey or ns.self, goal.id) ~= true then
        decision.caution = "Confirm availability with " .. (text(goal.npcName) or "the quest giver") .. "."
    end
    ctx.decisions[goal] = decision
    return decision
end

function ns.GuideDestinationReason(stop, guide, route)
    return ns.GuideDestinationDecision(stop, guide, route).why
end

function ns.GuideVisibleReason(stop, mapID, distance, guide, route)
    local decision = ns.GuideDestinationDecision(stop, guide, route)
    local goal = ns.GuideDestination(stop)
    local long = ns.GuideInteger(mapID) and mapID > 0 and ns.GuideInteger(goal.mapID) and goal.mapID > 0 and mapID ~= goal.mapID
        or ns.Public(distance) and type(distance) == "number" and distance >= 1000
    local why = decision.why
    if long and (decision.code == "level-work" or decision.code == "selected-guide") then
        why = why .. " No special unlock is known; use Skip quest if this detour isn't worth it."
    end
    if decision.caution then why = why .. " " .. decision.caution end
    local hint = ns.GuideStepHint(goal)
    if goal.kind == "q" or goal.action == "start-item" or hint == "This quest giver patrols; search nearby." then
        why = why .. " " .. hint
    end
    return why
end

function ns.GuideReasonDiagnostics(output)
    local stop = ns.navigation and ns.navigation.state and ns.navigation.state.stop
    if not stop then output("Destination reason: no current guide step."); return end
    local decision = ns.GuideDestinationDecision(stop)
    output("Destination reason: " .. decision.code .. "; " .. decision.why)
    output("Reason evidence: " .. (decision.specificBenefit and "specific quest/plan benefit" or "selected guide only")
        .. "; review " .. (decision.needsReview and "needed" or "not flagged") .. ".")
end
