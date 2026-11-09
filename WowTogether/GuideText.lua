local addonName, ns = ...

local ICON_NAMES = {
    "kill", "collect", "use", "talk", "accept", "turnin", "turnin-pending",
    "travel", "fly", "hearth", "teleport", "ship", "party", "wait", "farm",
    "dungeon", "pause", "menu", "close", "scan",
}
local ICON_TEXTURES = {}
for _, name in ipairs(ICON_NAMES) do
    ICON_TEXTURES[name] = "Interface\\AddOns\\WowTogether\\Media\\Icons\\" .. name
end
ns.STEP_ICON_TEXTURES = ICON_TEXTURES

local STEP_SYMBOLS = {
    accept = {icon = "accept", glyph = "!"},
    turnin = {icon = "turnin", glyph = "?"},
    turninIncomplete = {icon = "turnin-pending", glyph = "?"},
    kill = {icon = "kill", glyph = "x"},
    collect = {icon = "collect", glyph = "+"},
    use = {icon = "use", glyph = "u"},
    talk = {icon = "talk", glyph = "..."},
    travel = {icon = "travel", glyph = ">"},
    fly = {icon = "fly", glyph = "f"},
    hearth = {icon = "hearth", glyph = "h"},
    teleport = {icon = "teleport", glyph = "t"},
    ship = {icon = "ship", glyph = "s"},
    party = {icon = "party", glyph = "&"},
    wait = {icon = "wait", glyph = "w"},
    farm = {icon = "farm", glyph = "$"},
    dungeon = {icon = "dungeon", glyph = "D"},
}
ns.STEP_SYMBOLS = STEP_SYMBOLS

local STEP_KIND_ALIASES = {
    ["travel-walk"] = "travel", ["travel-fly"] = "fly", ["travel-hearth"] = "hearth",
    ["travel-teleport"] = "teleport", ["travel-ship"] = "ship",
    trainer = "talk", vendor = "use", corpse = "travel",
}
local ICON_AVAILABLE = {}

local function probeStepSymbols()
    local total, available = 0, 0
    for _, name in ipairs(ICON_NAMES) do
        total = total + 1
        local ok = false
        if type(GetFileIDFromPath) == "function" then
            local success, fileID = pcall(GetFileIDFromPath, ICON_TEXTURES[name] .. ".tga")
            ok = success and type(fileID) == "number" and fileID > 0
        end
        if not ok and CreateFrame then
            local probe = CreateFrame("Frame")
            local texture = probe:CreateTexture(nil, "ARTWORK")
            if texture and type(texture.SetTexture) == "function" and type(texture.GetTexture) == "function" then
                local asset = ICON_TEXTURES[name] .. ".tga"
                local success = pcall(texture.SetTexture, texture, asset)
                local valid, found = false, nil
                if success then valid, found = pcall(texture.GetTexture, texture) end
                ok = valid and (found == asset or type(found) == "number")
            end
            if probe.Hide then probe:Hide() end
        end
        ICON_AVAILABLE[name] = ok
        if ok then available = available + 1 end
    end
    local fallback = {}
    for key, symbol in pairs(STEP_SYMBOLS) do
        symbol.texture = ICON_TEXTURES[symbol.icon]
        symbol.available = ICON_AVAILABLE[symbol.icon] == true
    end
    for _, name in ipairs(ICON_NAMES) do
        if not ICON_AVAILABLE[name] then fallback[#fallback + 1] = name end
    end
    table.sort(fallback)
    ns.stepIconStatus = "Step icons: " .. available .. "/" .. total .. " addon textures"
        .. (#fallback > 0 and (", missing " .. table.concat(fallback, ", ")) or "")
end
probeStepSymbols()

function ns.StepSymbolFor(kind)
    local symbol = STEP_SYMBOLS[kind] or STEP_SYMBOLS[STEP_KIND_ALIASES[kind]] or STEP_SYMBOLS.travel
    if type(symbol) == "string" then return nil, symbol end
    return symbol.glyph, symbol.available and symbol.texture or nil
end

function ns.StepIconTexture(name)
    return ICON_AVAILABLE[name] == true and ICON_TEXTURES[name] or nil
end

function ns.StepSymbolKind(stop, facts)
    if stop.kind == "a" then return "accept" end
    if stop.kind == "t" then return facts and facts.finished and "turninIncomplete" or "turnin" end
    if stop.kind == "party" or stop.memberKey then return "party" end
    if stop.kind == "wait" then return "wait" end
    if stop.kind == "farm" then return "farm" end
    if stop.dungeonEntrance then return "dungeon" end
    if stop.kind == "trainer" then return "talk" end
    if stop.kind == "travel" or stop.kind == "f" or stop.kind == "corpse" then
        local method = stop.flightPlan and "taxi" or stop.travelLeg and stop.travelLeg.method
        if method == "taxi" then return "fly" end
        if method == "hearth" then return "hearth" end
        if method == "teleport" then return "teleport" end
        if method == "ship" or method == "zeppelin" or method == "tram" then return "ship" end
        return "travel"
    end
    local action = facts and facts.action or stop.action
    if action == "kill" then return "kill" end
    if action == "talk" or action == "escort" then return "talk" end
    if action == "use" or action == "heal" or action == "interact" or action == "event" then return "use" end
    if action == "collect" or action == "interact" or stop.itemID then return "collect" end
    return "collect"
end

-- Instructions use structured quest facts and matching public progress.
-- They never turn a planning anchor or an unknown objective into a location.
local function text(value) return ns.SafeTitle(value) end
local function characterCount(value) return select(2, string.gsub(value, "[^\128-\191]", "")) end
local function characterPrefix(value, limit)
    local index, count = 1, 0
    while index <= #value and count < limit do
        local byte = string.byte(value, index)
        index = index + (byte >= 240 and 4 or byte >= 224 and 3 or byte >= 192 and 2 or 1)
        count = count + 1
    end
    return string.sub(value, 1, index - 1)
end
local function compactTooltipText(...)
    local output, seen = {}, {}
    for index = 1, select("#", ...) do
        local value = select(index, ...)
        if type(value) == "string" then
            for line in string.gmatch(value .. "\n", "([^\n]*)\n") do
                line = string.gsub(line, "^%s*(.-)%s*$", "%1")
                if line ~= "" and not seen[line] then
                    seen[line] = true
                    output[#output + 1] = line
                end
            end
        end
    end
    return table.concat(output, "\n")
end
ns.CompactGuideTooltip = compactTooltipText

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
                point.progressName = text(requirement.progressName) or text(requirement.name)
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
    if facts.action == "start-item" and ns.GuideInteger(stop.itemID) and stop.itemID > 0 then
        local owned = ns.ItemOwned(stop.itemID)
        facts.startItem = {itemID = stop.itemID, name = facts.item or ns.ItemName(stop.itemID),
            inBags = ns.GuideInteger(owned) and owned > 0 or false, count = owned or 0}
    end
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
    if stop.inventoryService then return text(stop.label) or "Visit the vendor" end
    local title, target = text(stop.title) or "this quest", facts.target
    if stop.confirmation then return "Talk to " .. (facts.npc or "the quest giver") end
    if stop.kind == "travel" or stop.kind == "f" then return text(stop.label) or "Travel to the next stop" end
    if stop.kind == "corpse" then return "Return to your corpse" end
    if stop.kind == "loading" then return stop.action == "scan" and "Scanning guide…" or "Loading route…" end
    if stop.kind == "notice" then return text(stop.label) or "Waiting for the next guide step" end
    if facts.action == "start-item" then
        if facts.startItem and facts.startItem.inBags then
            return "Use " .. (facts.startItem.name or facts.item or "the item") .. " to start " .. title
        end
        if facts.npc then return "Kill " .. facts.npc .. " for " .. (facts.item or "the quest item") end
        local verb = stop.sourceAction == "buy" and "Buy " or stop.sourceAction == "loot" and "Loot " or "Find "
        return verb .. (facts.item or target or title)
    end
    if stop.kind == "a" then
        if stop.entityType == "object" then
            local object = facts.npc or target or "object"
            local full = "Read the " .. object .. " (ground object) to start " .. title
            if characterCount(full) <= 70 then return full end
            local compact = "Read " .. object .. " (object) to start " .. title
            if characterCount(compact) <= 70 then return compact end
            return "Read " .. object .. " to start " .. title
        end
        if facts.npc then return "Accept from " .. facts.npc end
        if target then return "Accept at " .. target end
        return "Accept " .. title
    end
    if stop.kind == "t" then return facts.npc and ("Turn in to " .. facts.npc) or ("Turn in " .. title) end
    if facts.finished or facts.remaining == 0 then return "Objective complete: " .. (target or title) end
    if text(stop.dungeonBossName) then
        return "Kill " .. text(stop.dungeonBossName) .. " — also completes " .. title
    end
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

local function guideStepHintSource(stop, facts)
    facts = facts or ns.GuideStepFacts(stop); stop = facts.stop
    if stop.professionStep then return stop.description end
    if stop.dungeonEntrance then return stop.published and "Entrance area; follow the approach to the portal."
        or "Collect your dungeon quests before entering." end
    local action = facts.action
    if stop.kind == "trainer" then return "Optional training check; buy useful class skills manually. Done training or Skip training resumes quests." end
    if stop.confirmation then return stop.confirmationReason or "Check the quest giver's offers before picking this quest up." end
    if stop.kind == "travel" or stop.kind == "f" then return nil end
    if stop.kind == "corpse" then return "Recover your body to resume the guide." end
    if stop.kind == "loading" then return "Checking quest progress and route information." end
    if stop.kind == "notice" then return text(stop.label) end
    if facts.finished or facts.remaining == 0 then return "This objective is finished." end
    if action == "start-item" then
        if facts.startItem and facts.startItem.inBags then return "Use the item to start the quest." end
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
ns.GuideStepHintSource = guideStepHintSource

function ns.StopInstruction(stop, facts)
    facts = facts or ns.GuideStepFacts(stop); stop = facts.stop
    local title = text(stop.title) or "this quest"
    if stop.confirmation then return "Talk to " .. (facts.npc or "the quest giver") .. " to confirm " .. title end
    if stop.kind == "a" and facts.action ~= "start-item" then
        if stop.entityType == "object" then return ns.GuideStepAction(stop, facts) end
        return "Accept " .. title .. (facts.npc and (" from " .. facts.npc) or facts.target and (" at " .. facts.target) or "")
    end
    if stop.kind == "t" then return "Turn in " .. title .. (facts.npc and (" to " .. facts.npc) or "") end
    if facts.action == "start-item" then return ns.GuideStepAction(stop, facts) end
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

-- Put the reason for a journey first; the action/giver remain in the tooltip.
-- Crossing waypoints are directions, never substitute quest objectives.
function ns.GuideDestinationPurpose(stop, mapID, distance, guide, route)
    local goal = ns.GuideDestination(stop)
    if goal.professionStep then return text(goal.travelReason) or goal.description end
    if goal.inventoryService then return goal.serviceReason .. "\n" .. goal.serviceInstructions end
    local reason = ns.GuideVisibleReason(stop, mapID or ns.profile and ns.profile.mapID, distance, guide, route)
    if goal.dungeonEntrance or goal.kind == "trainer" then return reason end
    if goal.kind ~= "a" and goal.kind ~= "q" and goal.kind ~= "t" then return end
    if goal.kind == "t" and reason and text(goal.npcName) then
        return string.gsub(reason, "%.$", "") .. " from " .. text(goal.npcName) .. "."
    end
    -- The arrow status already gives the current action. Keep the context line
    -- for the reason to travel, rather than repeating that action a second time.
    return reason
end

function ns.GuideStepRequirement(stop, mapID, distance, guide, route)
    local decision = ns.GuideDestinationDecision(stop, guide, route)
    local current = ns.GuideReasonCanBeCurrent(stop, guide, route)
    if not current then return "Later" end
    if not decision.specificBenefit then return end
    if decision.code == "prerequisite" or decision.code == "learned-prerequisite"
        or decision.code == "chosen-branch" or decision.code == "party-prerequisite" then
        return "Required now for this quest chain"
    end
    if decision.code == "quest-objective" or decision.code == "quest-reward" then
        return "Required now to finish " .. (text(ns.GuideDestination(stop).title) or "this quest")
    end
    local goal = ns.GuideDestination(stop)
    local otherMap = ns.GuideInteger(mapID) and mapID > 0 and goal.mapID ~= mapID
    if not otherMap and ns.Public(distance) and type(distance) == "number" and distance <= 1000 then
        return "Optional • on your way"
    end
    return "Optional • current route"
end

local function compactStepHint(stop, facts)
    local hint = guideStepHintSource(stop, facts)
    local action = facts.action
    if stop.professionStep or stop.inventoryService or stop.dungeonEntrance
        or stop.kind == "trainer" or stop.kind == "travel" or stop.kind == "f"
        or stop.kind == "corpse" or stop.kind == "loading" or stop.kind == "notice"
        or stop.confirmation or action == "start-item" then return hint end
    if stop.kind == "a" or stop.kind == "t" then
        if hint == "Hand in the completed quest." or hint == "Interact with the quest starter."
            or hint == "Choose this quest in the NPC's offer list." then return end
        return hint
    end
    if action == "escort" or action == "heal" then return hint end
    if (action == "collect" or action == "loot" or action == "item" or action == "gather")
        and text(stop.targetName) and text(stop.targetName) ~= facts.item
        and hint == ("Collect from " .. text(stop.targetName) .. ".") then return hint end
    return
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

local function withoutFinalPeriod(value)
    if type(value) ~= "string" then return nil end
    return string.gsub(string.gsub(value, "%s+$", ""), "[%.!]+$", "")
end

local function capped(value, maximum)
    value = withoutFinalPeriod(value)
    if not value then return nil end
    if characterCount(value) > maximum then return characterPrefix(value, maximum - 1) .. "…" end
    return value
end

local function sentence(value, maximum)
    value = capped(value, maximum)
    if value and not string.find(value, "[.!?]$") then return value .. "." end
    return value
end

local function actionKind(action)
    if action == "kill" or action == "escort" then return "kill" end
    if action == "collect" or action == "loot" or action == "item" or action == "gather" or action == "buy" then return "collect" end
    if action == "use" or action == "heal" or action == "interact" or action == "event" then return "use" end
    if action == "talk" then return "talk" end
    return "explore"
end

local function presentationKind(stop, facts)
    if stop.kind == "a" then return "accept" end
    if stop.kind == "t" then return "turnin" end
    if stop.kind == "party" or stop.memberKey then return "party" end
    if stop.kind == "wait" then return "wait" end
    if stop.kind == "farm" then return "farm" end
    if stop.kind == "trainer" then return "trainer" end
    if stop.inventoryService then return "vendor" end
    if stop.professionStep then return "vendor" end
    if stop.confirmation then return "notice" end
    if stop.dungeonEntrance then return "dungeon" end
    if stop.kind == "corpse" then return "corpse" end
    if stop.kind == "notice" or stop.kind == "loading" then return "notice" end
    if stop.kind == "travel" or stop.kind == "f" then
        local method = stop.flightPlan and "taxi" or stop.travelLeg and stop.travelLeg.method
        if method == "taxi" then return "travel-fly" end
        if method == "ship" or method == "zeppelin" or method == "tram" then return "travel-ship" end
        if method == "hearth" then return "travel-hearth" end
        if method == "teleport" then return "travel-teleport" end
        return "travel-walk"
    end
    return actionKind(facts.action)
end

local function presentationTravelAction(stop, goal)
    if stop.flightDiscovery then
        local plan = stop.flightDiscovery
        return "Visit " .. (text(plan.source and plan.source.name) or "the flight master")
    end
    local leg = stop.travelLeg
    if stop.flightPlan then
        local instruction = text(stop.label)
        if instruction then return instruction end
        return "Fly to " .. (stop.flightPlan.destination.name or ns.MapName(stop.flightPlan.destination.mapID))
    end
    if not leg then return text(stop.label) or text(stop.status) or "Travel to the next stop" end
    if leg.method == "hearth" or leg.method == "teleport" then
        return ns.PersonalTransportLabel(leg)
    end
    if leg.method == "taxi" then return "Fly to " .. (text(leg.name) or ns.MapName(leg.to.mapID)) end
    if leg.method == "ship" or leg.method == "zeppelin" or leg.method == "tram" then
        if leg.from and (text(leg.from.name) or text(leg.from.label)) then
            return "Board at " .. (text(leg.from.name) or text(leg.from.label))
        end
        local transport = leg.method == "ship" and "ship" or leg.method == "zeppelin" and "zeppelin" or "tram"
        return "Take the " .. transport .. " to " .. (text(leg.name) or ns.MapName(leg.to.mapID))
    end
    if leg.to and leg.to.terrain then return "Follow the road around " .. (text(leg.to.terrain.name) or "the terrain") end
    if leg.to and leg.to.trail then return "Follow the road towards " .. (text(leg.to.name) or ns.MapName(leg.to.mapID)) end
    if leg.waypoint or leg.toID and string.find(leg.toID, "^BORDER_") then
        return "Walk to " .. (text(leg.name) or text(leg.to.name) or ns.MapName(leg.to.mapID))
    end
    return text(stop.label) or ("Walk to " .. (text(leg.name) or ns.MapName(leg.to.mapID)))
end

local function presentationStatus(decision, stop, facts, guide)
    if stop.confirmation then return "Confirm at the giver", "gold" end
    if facts.finished or facts.remaining == 0 or stop.id and stop.id > 0
        and ns.CatalogueCompletion(stop.memberKey or ns.self, stop.id) == true then
        return "Done", "green"
    end
    if decision and decision.specificBenefit ~= true then
        local quest = ns.CatalogueQuest(stop.id)
        local level = quest and (quest.minLevel or quest.level)
        return "Later" .. (level and (" (level " .. level .. ")") or ""), "muted"
    end
    local optional = { ["pickup-hub"] = true, ["return-hub"] = true, ["objective-area"] = true,
        ["early-reward"] = true, ["quest-log-space"] = true, ["dungeon-pickup"] = true,
        ["class-training"] = true, vendor = true, ["class-progression"] = true,
        ["profession-work"] = true, service = true }
    if stop.kind == "trainer" or stop.inventoryService or stop.professionStep
        or decision and optional[decision.code] then return "Optional, on the way", "text" end
    if guide and decision and decision.specificBenefit then return "Required", "gold" end
    return "Optional, on the way", "text"
end

local function statusLineForGuide(guide, route, stop, status)
    if status == "Optional, on the way" and ns.IsClassTrainingStep and ns.IsClassTrainingStep(stop) then return "Optional class training" end
    if status == "Optional, on the way" and ns.IsInventoryServiceStep and ns.IsInventoryServiceStep(stop) then return "Optional vendor visit" end
    if not guide then return "Current step" end
    local countStops = route and route.stops and #route.stops or guide.classQuestStepCount or guide.classQuestCount
    local index = stop.guideStep
    local prefix
    if stop.historyPreview then prefix = "Previous step"
    elseif index and countStops then prefix = "Step " .. index .. " of " .. countStops
    elseif index then prefix = "Step " .. index
    else prefix = "Current step" end
    local label = guide.zone or guide.title or guide.name
    if guide.mode == "zone" and ns.profile and ns.profile.faction and label then label = ns.profile.faction .. " / " .. label end
    if label then return prefix .. " • " .. label end
    return prefix
end

local function presentationTime(state)
    if not state then return nil end
    if state.arrived then return "Here" end
    local distance = state.distance and ns.FormatDistance(state.distance) or nil
    local seconds
    if state.flight then
        seconds = state.flight.remaining or state.flight.elapsed
    else
        seconds = state.walkSeconds
    end
    local timing
    if seconds and seconds > 0 then
        timing = seconds < 60 and ("~" .. math.floor(seconds) .. " s")
            or ("~" .. math.floor(seconds / 60) .. " min " .. string.format("%02d", math.floor(seconds % 60)) .. " s")
    end
    if distance and timing then return distance .. ", " .. timing end
    return distance or timing
end

local function presentationTravelSummary(stop, fallback)
    local path = ns.travelPath
    if (stop.travelLeg or stop.flightPlan) and not stop.flightPlan
        and type(path) == "table" and type(path.legs) == "table" then
        local parts, landing = {}, nil
        local cursor = math.max(1, path.cursor or 1)
        for index = cursor, #path.legs do
            local leg = path.legs[index]
            local method, label = leg.method, text(leg.name)
            local action
            if method == "teleport" then action, landing = "Teleport", leg.name
            elseif method == "hearth" then action, landing = "Hearthstone", leg.name
            elseif method == "taxi" then
                local flight = type(leg.flight) == "table" and leg.flight
                local seconds = flight and (flight.flightSeconds or flight.seconds) or leg.seconds
                action = "Fly to " .. (label or "the next flight point")
                    .. (seconds and (" (~" .. ns.FormatTravelDuration(seconds) .. ")") or "")
            elseif method == "ship" or method == "zeppelin" or method == "tram" then
                action = "Take the " .. method .. (label and (" to " .. label) or "")
            elseif method == "walk" then
                action = "walk" .. (leg.seconds and (" ~" .. ns.FormatTravelDuration(leg.seconds)) or "")
            end
            if action then parts[#parts + 1] = action end
        end
        if #parts > 0 then
            local result = table.concat(parts, ", then ")
            if landing then result = result .. ". Lands in " .. landing end
            return sentence(result, 180)
        end
    end
    -- Keep the authored summary intact. Core prose is already composed at its
    -- source and must not be rewritten here with string substitutions.
    return fallback and sentence(fallback, 180) or nil
end

function ns.GuideStepPresentation(stop, facts, guide, route, state)
    if not stop then return nil end
    local handled, presentation = ns.FirstHook("stepPresentation", stop, facts, guide, route, state)
    if handled then return presentation end
    guide, route = guide or ns.routeSelection, route or ns.selectedRoute
    local goal = ns.GuideDestination(stop)
    facts = facts and facts.stop == goal and facts or ns.GuideStepFacts(goal)
    local decision = ns.GuideDestinationDecision(stop, guide, route)
    local status, statusColor = presentationStatus(decision, goal, facts, guide)
    local complete = stop.kind == "notice" and route and route.complete == true
    if complete then status, statusColor = "Done", "green" end
    local isTravel = stop.kind == "travel" or stop.kind == "f" or stop.travelLeg or stop.flightPlan or state and state.flight
    local what = complete and "Guide complete"
        or state and state.flight and ("Fly to " .. (text(state.flight.name) or "your destination"))
        or isTravel and presentationTravelAction(stop, goal) or ns.StopInstruction(goal, facts)
    local title = text(goal.title) or text(stop.title) or "Current task"
    local why = decision and decision.specificBenefit and decision.why or nil
    local departure = stop.travelLeg and (stop.travelLeg.method == "ship" or stop.travelLeg.method == "zeppelin"
        or stop.travelLeg.method == "tram" or stop.travelLeg.method == "taxi")
    local locationStop = isTravel and stop.travelLeg and (departure and stop.travelLeg.from or stop.travelLeg.to) or goal
    local location = locationStop and locationStop.mapID and not (goal.professionStep and goal.unknownLocation)
        and ns.StopLocationText(locationStop) or nil
    local rawHint = guideStepHintSource(goal, facts)
    local hint = compactStepHint(goal, facts)
    local details, seen = {}, {}
    local function addDetail(value)
        value = text(value)
        local lowered = value and string.lower(value)
        local repeats = lowered and (what and (string.find(lowered, string.lower(what), 1, true)
            or string.find(string.lower(what), lowered, 1, true))
            or why and (string.find(lowered, string.lower(why), 1, true)
                or string.find(string.lower(why), lowered, 1, true)))
        if value and value ~= "" and not repeats and not seen[value] and #details < 3 then
            details[#details + 1], seen[value] = sentence(value, 110), true
        end
    end
    if goal.inventoryService then
        addDetail(goal.serviceReason)
        addDetail(goal.serviceInstructions)
        addDetail("Done resumes your guide")
    else
        for _, watch in ipairs(goal.dungeonLootWatch or {}) do
            addDetail("Watch for: " .. watch.name .. " (" .. watch.members .. ")")
        end
        addDetail(ns.QuestGroupWarning(goal.id))
        addDetail(goal.forPlayer and ("For " .. text(goal.forPlayer)))
        if goal.clientLocation then addDetail("Quest tracker marked area") end
        local quest = ns.CatalogueQuest(goal.id)
        for _, item in ipairs(quest and quest.providedItems or {}) do
            if item.name then addDetail("Quest item: " .. text(item.name) .. " (provided)") end
        end
        if goal.unsafeTransit then addDetail("No mapped bypass is known. Follow roads around the town") end
        if goal.unsafeTerrain then
            addDetail(goal.terrainApproach and "Reach the mesa using its lift or ramp" or "Use the entrance or a path around the pinnacle")
        end
        addDetail(decision and decision.caution)
        if hint and not goal.professionStep
            and not string.find(string.lower(what), string.lower(hint), 1, true) then addDetail(hint) end
    end
    if goal.professionStep and not why then
        addDetail(goal.description)
    end
    local kind = presentationKind(stop, facts)
    local icon = ns.StopIcon(stop) or ns.StopIcon(goal) or (facts.action == "kill" and "Interface\\TargetingFrame\\UI-RaidTargetingIcon_8")
        or "Interface\\Icons\\INV_Misc_Map_01"
    local thenText
    if isTravel then thenText = "Then: " .. ns.StopInstruction(goal, facts)
        .. (location and (" (" .. location .. ")") or "") .. "." end
    local travel = presentationTravelSummary(stop, ns.TravelPathSummary(stop))
    local evidence = decision and decision.code and ("Reason: " .. decision.code
        .. (decision.confidence and (" • " .. decision.confidence) or "")
        .. (decision.estimated and " • estimated" or "") .. ".")
    return {kind = kind, icon = icon, title = title, stepLine = capped(statusLineForGuide(guide, route, goal, status), 110),
        what = capped(what, 70), progress = facts.progress, why = capped(why, 110), status = status,
        statusColor = statusColor, time = presentationTime(state), location = location, then_ = thenText,
        travel = travel and string.gsub(string.gsub(travel, "^%s+", ""), "%s+$", "") or nil,
        hint = rawHint,
        details = details, evidence = evidence, decision = decision, stop = stop, goal = goal, facts = facts}
end

function ns.GuidePresentationTooltip(presentation, includeCard)
    if not presentation then return "" end
    return table.concat(ns.GuidePresentationTooltipLines(presentation, includeCard), "\n")
end

function ns.GuidePresentationTooltipLines(presentation, includeCard)
    if not presentation then return {} end
    local output, seen = {}, {}
    local function keyFor(value)
        value = text(value)
        return value and string.lower(string.gsub(value, "[%.!]+$", "")) or nil
    end
    local function add(value)
        value = text(value)
        if not value then return end
        local key = keyFor(value)
        if key == "" or seen[key] or #output >= 5 then return end
        seen[key], output[#output + 1] = true, value
    end
    local function mark(value)
        local key = keyFor(value)
        if key then seen[key] = true end
    end
    if includeCard == true then
        add(presentation.what); add(presentation.why); add(presentation.status)
    else
        mark(presentation.what)
        if includeCard ~= "arrow" then
            mark(presentation.why); mark(presentation.status)
        else add(presentation.why); add(presentation.status) end
    end
    add(presentation.then_)
    if not (presentation.then_ and presentation.location
        and string.find(presentation.then_, presentation.location, 1, true)) then add(presentation.location) end
    add(presentation.travel)
    for _, detail in ipairs(presentation.details or {}) do add(detail) end
    add(presentation.evidence)
    return output
end

function ns.GuideStepDescription(stop, facts, guide, route)
    local presentation = ns.GuideStepPresentation(stop, facts, guide, route)
    return compactTooltipText(presentation and presentation.title,
        ns.GuidePresentationTooltip(presentation, true))
end

function ns.GuideStepHint(stop, facts, guide, route)
    local presentation = ns.GuideStepPresentation(stop, facts, guide, route)
    return presentation and presentation.hint
end
