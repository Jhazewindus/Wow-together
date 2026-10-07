local addonName, ns = ...

-- Instructions use structured quest facts and matching public progress.
-- They never turn a planning anchor or an unknown objective into a location.
local function text(value) return ns.SafeTitle(value) end
local function count(value)
    return ns.Public(value) and type(value) == "number" and value >= 0 and value <= 1000000
        and value == math.floor(value) and value or nil
end
local function source(stop) return stop.sourceStop or stop end

function ns.GuideStepFacts(stop)
    stop = source(stop)
    local facts = {stop = stop, action = text(stop.action), target = text(stop.itemName)
        or text(stop.objectiveLabel) or text(stop.targetName) or text(stop.npcName),
        npc = text(stop.npcName), item = text(stop.itemName), tool = text(stop.useItemName),
        need = not stop.quantityUnknown and count(stop.quantity) or nil}
    local progress = stop.kind == "q" and ns.ProgressForMember(stop.memberKey or ns.self, stop.id)
    local point = {name = text(stop.targetName) or facts.npc, itemName = facts.item,
        progressName = text(stop.progressName) or text(stop.objectiveLabel)}
    local quest = ns.CatalogueQuest(stop.id)
    if not point.progressName and stop.objectiveKey then
        for _, requirement in ipairs(quest and quest.requirements or {}) do
            local kind = text(requirement.entityType)
            local key = kind and ns.GuideInteger(requirement.entityID) and (kind .. ":" .. requirement.entityID)
            if (requirement.objectiveKey or key) == stop.objectiveKey then
                point.progressName = text(requirement.name)
                break
            end
        end
    end
    for _, objective in ipairs(progress and progress.objectives or {}) do
        if ns.Public(objective) and type(objective) == "table" and ns.ObjectiveMatchesPoint(objective.text, point) then
            facts.objective = objective
            facts.have = count(objective.have)
            facts.finished = ns.Public(objective.finished) and objective.finished == true or nil
            local need = count(objective.need)
            if need and need > 0 then facts.need = need end
            if facts.action ~= "use" and facts.action ~= "heal" and facts.action ~= "interact"
                and facts.action ~= "talk" and facts.action ~= "escort" and facts.action ~= "event" then
                if ns.Public(objective.kind) and objective.kind == "monster" and not facts.item then facts.action = "kill"
                elseif ns.Public(objective.kind) and objective.kind == "item" and not facts.action then facts.action = "collect" end
            end
            break
        end
    end
    local bags = ns.GuideItemProgress(stop, stop.memberKey or ns.self, facts.need)
    if bags then
        facts.inventory = true
        if not facts.have or bags.have > facts.have then facts.have = bags.have end
        facts.need = facts.need or bags.need
        if bags.finished then facts.finished = true end
    end
    if not facts.action and facts.npc and facts.item then facts.action = "collect" end
    if facts.have and facts.need and facts.need > 0 then
        facts.remaining = math.max(0, facts.need - facts.have)
        facts.progress = facts.have .. "/" .. facts.need
    end
    local amount = facts.remaining or facts.need
    facts.amount = amount and amount > 0 and (facts.remaining and facts.have > 0
        and (amount .. " more ") or amount > 1 and (amount .. " × ") or "") or ""
    return facts
end

function ns.GuideStepAction(stop, facts)
    facts = facts or ns.GuideStepFacts(stop); stop = facts.stop
    if stop.professionStep then return stop.label end
    if stop.dungeonEntrance then return text(stop.label) or "Go to the dungeon entrance" end
    if stop.kind == "trainer" then return text(stop.label) or "Check your class trainer" end
    local title, target = text(stop.title) or "this quest", facts.target
    if stop.confirmation then return "Talk to " .. (facts.npc or "the quest giver") end
    if stop.kind == "travel" or stop.kind == "f" then return text(stop.label) or "Travel to the next stop" end
    if stop.kind == "corpse" then return "Return to your corpse" end
    if stop.kind == "loading" then return stop.action == "scan" and "Scanning guide…" or "Loading route…" end
    if stop.kind == "notice" then return text(stop.label) or "Waiting for the next guide step" end
    if facts.action == "start-item" then
        local verb = stop.sourceAction == "buy" and "Buy " or stop.sourceAction == "loot" and "Loot " or "Find "
        return verb .. (facts.item or target or title)
    end
    if stop.kind == "a" then
        if facts.npc then return "Accept from " .. facts.npc end
        if target then return "Accept at " .. target end
        return "Accept " .. title
    end
    if stop.kind == "t" then return facts.npc and ("Turn in to " .. facts.npc) or ("Turn in " .. title) end
    if facts.finished or facts.remaining == 0 then return "Objective complete: " .. (target or title) end
    local amount, action = facts.amount, facts.action
    if action == "use" then
        return "Use " .. (facts.tool or "the quest item") .. (stop.sourceAction == "use-at" and " at " or " on ")
            .. (text(stop.npcName) or text(stop.targetName) or target or title)
    end
    if action == "escort" then return "Escort " .. (target or title) end
    if action == "event" then return "Complete " .. (target or title) end
    if action == "heal" then return "Heal " .. amount .. (target or title) end
    if action == "kill" then return "Kill " .. amount .. (target or title) end
    if action == "buy" then return "Buy " .. amount .. (target or title) end
    if action == "talk" then return "Speak to " .. (facts.npc or target or title) end
    if action == "interact" then return "Interact with " .. (target or title) end
    if action == "collect" or action == "loot" or action == "item" or action == "gather" then
        local verb = facts.npc and facts.item and "Loot " or action == "gather" and "Gather " or "Collect "
        return verb .. amount .. (target or title)
    end
    return target and ("Complete the " .. target .. " objective") or (text(stop.label) or ("Work on " .. title))
end

function ns.GuideStepHint(stop, facts)
    facts = facts or ns.GuideStepFacts(stop); stop = facts.stop
    if stop.professionStep then return stop.description end
    if stop.dungeonEntrance then return stop.published and "Entrance area; follow the approach to the portal."
        or "Collect your dungeon quests before entering." end
    local action = facts.action
    if stop.kind == "trainer" then return "Optional training check; buy useful class skills manually. Done training or Skip training resumes quests." end
    if stop.confirmation then return stop.confirmationReason or "Check the quest giver's offers before picking this quest up." end
    if stop.kind == "travel" or stop.kind == "f" then return "Follow the travel instructions for this leg." end
    if stop.kind == "corpse" then return "Recover your body to resume the guide." end
    if stop.kind == "loading" then return "Checking quest progress and route information." end
    if stop.kind == "notice" then return "Check the guide status below." end
    if facts.finished or facts.remaining == 0 then return "This objective is finished." end
    if action == "start-item" then
        return (facts.npc and ((stop.sourceAction == "buy" and "Buy from " or "Loot from ") .. facts.npc .. "; ") or "")
            .. "use the item to start the quest."
    end
    if stop.kind == "a" or stop.kind == "t" then
        local entity = facts.npc and ns.questEntities and ns.questEntities.npc and ns.questEntities.npc[stop.entityID]
        if entity and entity.patrols and #entity.patrols > 0 then return "This quest giver patrols; search nearby." end
        if stop.npcVisitPickup then return "Collect the other guide quests offered here too." end
        if stop.kind == "a" then return facts.npc and "Choose this quest in the NPC's offer list." or "Interact with the quest starter." end
        return "Hand in the completed quest."
    end
    if (action == "collect" or action == "loot" or action == "item") and facts.npc and facts.item then
        return "Kill and loot " .. facts.npc .. "."
    end
    if action == "gather" or action == "collect" or action == "item" then
        local target = text(stop.targetName)
        if target and target ~= facts.item then return "Collect from " .. target .. "." end
        return (action == "gather" or stop.entityType == "object") and "Collect the marked ground objects."
            or "Collect the required quest items."
    end
    if action == "use" then return facts.need and facts.need > 1 and ("Use the item on " .. facts.need .. " targets in total.")
        or "Use the item at the marked target." end
    if action == "heal" then return facts.tool and ("Use " .. facts.tool .. " on the injured targets.") or "Heal the marked injured targets." end
    if action == "escort" then return "Stay with the NPC until the escort completes." end
    if action == "talk" then return "Speak to the NPC for this quest objective." end
    if action == "buy" then return "Buy the required items from this vendor." end
    if action == "interact" then return "Interact with the marked quest target." end
    if action == "event" then return "Complete the quest event at this location." end
    return "Finish this quest objective in the marked area."
end

function ns.StopInstruction(stop, facts)
    facts = facts or ns.GuideStepFacts(stop); stop = facts.stop
    local title = text(stop.title) or "this quest"
    if stop.confirmation then return "Talk to " .. (facts.npc or "the quest giver") .. " to confirm " .. title end
    if stop.kind == "a" and facts.action ~= "start-item" then
        return "Accept " .. title .. (facts.npc and (" from " .. facts.npc) or facts.target and (" at " .. facts.target) or "")
    end
    if stop.kind == "t" then return "Turn in " .. title .. (facts.npc and (" to " .. facts.npc) or "") end
    if facts.action == "start-item" then return ns.GuideStepAction(stop, facts)
        .. (facts.npc and (" from " .. facts.npc) or "") .. "; use it to start the quest" end
    if facts.action == "use" and not facts.finished and facts.remaining ~= 0 then
        return "Use " .. (facts.tool or "the quest item") .. (stop.sourceAction == "use-at" and " at " or " on ")
            .. facts.amount .. (facts.npc or text(stop.targetName) or facts.target or title)
    end
    local instruction = ns.GuideStepAction(stop, facts)
    if facts.npc and facts.item and (facts.action == "collect" or facts.action == "loot" or facts.action == "item") then
        instruction = instruction .. " from " .. facts.npc
    end
    return instruction
end

local function destination(stop)
    local goal = stop
    for _ = 1, 4 do
        if goal.goal then goal = goal.goal elseif goal.sourceStop then goal = goal.sourceStop else break end
    end
    return goal
end

-- Reasons use the selected guide's real dependencies/visits. Cache per route
-- and destination so arrow ticks do not rescan a full guide's remaining steps.
local reasonRoute, reasonGuide, reasonCatalogue
local reasons = {}
function ns.GuideDestinationReason(stop)
    local goal = destination(stop)
    if text(goal.travelReason) then return text(goal.travelReason) end
    local route, guide = ns.selectedRoute, ns.routeSelection
    if route ~= reasonRoute or guide ~= reasonGuide or ns.catalogue ~= reasonCatalogue then
        reasonRoute, reasonGuide, reasonCatalogue, reasons = route, guide, ns.catalogue, {}
    end
    if reasons[goal] ~= nil then return reasons[goal] or nil end
    local reason
    if goal.dungeonEntrance then
        reason = "The dungeon quest objectives require a run through " .. (text(goal.title) or "this dungeon") .. "."
    elseif goal.kind == "trainer" then
        reason = "Optional training check near your quest route; new class skills may be available."
    elseif goal.confirmation then
        reason = "Talk to " .. (text(goal.npcName) or "the quest giver") .. " to check this quest's pickup requirements before continuing."
    elseif goal.kind == "a" or goal.kind == "q" or goal.kind == "t" then
        local useful, exception = ns.LevelingValue(goal.id)
        if guide and guide.catchupRequired and guide.catchupRequired[goal.id] then
            reason = "This prerequisite helps your party catch up through the quest chain."
        elseif useful == true and exception then reason = exception end
        local followup
        if not reason then
            local key = goal.memberKey or ns.self
            local profile = key == ns.self and ns.profile or ns.members[key] and ns.members[key].profile
            for _, record in ipairs(guide and guide.records or {}) do
                local quest = ns.CatalogueQuest(record.id)
                local required = quest and quest.previousQuest == goal.id
                for _, parent in ipairs(quest and quest.prerequisiteAll or {}) do
                    if parent == goal.id then required = true end
                end
                if required and not ns.GuideQuestSkipped(record.id) and ns.ClassQuestEnabled(record.id)
                    and ns.CatalogueIdentityAllowed(record.id, profile) ~= false
                    and ns.CatalogueCompletion(key, record.id) ~= true then
                    followup = text(quest.title) or text(record.title); break
                end
            end
            if followup then reason = "Required for " .. followup .. " later in this guide." end
        end
        if not reason and (goal.kind == "a" or goal.kind == "t") then
            local found, count, seen = false, 0, {}
            for _, point in ipairs(route and route.stops or {}) do
                if not found and point.id == goal.id and point.kind == goal.kind then found = true end
                if found then
                    if point.kind ~= goal.kind or point.mapID ~= goal.mapID or point.unknownLocation or goal.unknownLocation then break end
                    local yards = point.x == goal.x and point.y == goal.y and 0
                        or ns.WalkingDistance(goal.mapID, goal, point)
                    if not yards or yards > 100 then break end
                    if not seen[point.id] then seen[point.id] = true; count = count + 1 end
                end
            end
            if count > 1 then reason = "This visit groups " .. count .. (goal.kind == "a" and " nearby quest pickups before heading out." or " nearby hand-ins to collect their rewards together.") end
        end
        if not reason then
            if goal.kind == "t" then reason = "Return here to collect the reward for " .. (text(goal.title) or "this quest") .. "."
            elseif goal.kind == "a" then reason = "This pickup is part of your selected guide's fixed quest order."
            else reason = "The objectives for " .. (text(goal.title) or "this quest") .. " are at this destination." end
        end
    end
    reasons[goal] = reason or false
    return reason
end

-- Put the reason for a journey first; the action/giver remain in the tooltip.
-- Crossing waypoints are directions, never substitute quest objectives.
function ns.GuideDestinationPurpose(stop)
    local goal, reason = destination(stop), ns.GuideDestinationReason(stop)
    if goal.professionStep then return reason and (reason .. "\n" .. (text(goal.description) or "")) or text(goal.description) end
    if goal.dungeonEntrance or goal.kind == "trainer" then return reason end
    if goal.kind ~= "a" and goal.kind ~= "q" and goal.kind ~= "t" then return end
    local instruction = ns.StopInstruction(goal)
    if goal.kind == "q" then instruction = instruction .. " for " .. (text(goal.title) or "this quest") end
    return reason and (reason .. "\n" .. instruction) or instruction
end

function ns.StopLocationText(stop, mapID)
    stop = source(stop)
    if not ns.GuideInteger(stop.mapID) or stop.mapID <= 0 then return "Location not mapped" end
    local zone = ns.MapName(stop.mapID)
    local place = text(stop.sourceZone)
    if place and place ~= zone then zone = place .. " • " .. zone end
    if ns.GuideInteger(mapID) and mapID > 0 and mapID ~= stop.mapID then zone = "Travel to " .. zone end
    local mapped = not stop.unknownLocation and ns.Public(stop.x) and ns.Public(stop.y)
        and type(stop.x) == "number" and type(stop.y) == "number"
        and stop.x >= 0 and stop.x <= 1 and stop.y >= 0 and stop.y <= 1
        and stop.kind ~= "notice" and stop.kind ~= "loading"
    if mapped then return zone .. string.format(" • %.1f, %.1f", stop.x * 100, stop.y * 100) end
    return zone .. " • location not mapped"
end

function ns.GuideStepDescription(stop, facts)
    facts = facts or ns.GuideStepFacts(stop)
    local parts = {text(facts.stop.title) or "Guide step", ns.StopInstruction(stop, facts)}
    local groupWarning = ns.QuestGroupWarning(facts.stop.id)
    if groupWarning then parts[#parts + 1] = groupWarning end
    if facts.progress then parts[#parts + 1] = "Progress: " .. facts.progress end
    if text(facts.stop.forPlayer) then parts[#parts + 1] = "For " .. text(facts.stop.forPlayer) end
    parts[#parts + 1] = ns.GuideStepHint(stop, facts)
    if stop.goal then
        local purpose = ns.GuideDestinationPurpose(stop)
        if purpose then parts[#parts + 1] = purpose end
    else
        local reason = ns.GuideDestinationReason(stop)
        if reason then parts[#parts + 1] = reason end
    end
    parts[#parts + 1] = ns.StopLocationText(stop)
    local quest = ns.CatalogueQuest(facts.stop.id)
    if quest then
        for _, item in ipairs(quest.providedItems or {}) do
            local name = text(item.name)
            if name then parts[#parts + 1] = "Quest item: " .. name .. " (provided)" end
        end
    end
    return table.concat(parts, "\n")
end
