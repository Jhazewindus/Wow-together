local addonName, ns = ...

ns.routeLocations = {}
ns.readyToTurnIn = {}
local sentLocations = {}
local MAX_STOPS = 20
ns.routeStats = {pins = 0, lines = 0, status = "No route selected."}

local function validPoint(mapID, x, y)
    return ns.GuideInteger(mapID, 1000000) and mapID > 0 and ns.Public(x) and ns.Public(y)
        and type(x) == "number" and type(y) == "number" and x >= 0 and x <= 1 and y >= 0 and y <= 1
end

local function query(fn, ...)
    if type(fn) ~= "function" then return end
    local okay, a, b, c = pcall(fn, ...)
    if not okay then ns.routeReadError = "A read-only quest-location query failed on this build."; return end
    if ns.Public(a) and ns.Public(b) and ns.Public(c) then return a, b, c end
end

function ns.ReadRouteLocations()
    local points = {}
    ns.readyToTurnIn = {}
    local mapID = ns.profile and ns.profile.mapID or 0
    if C_QuestLog and mapID > 0 then
        local pois = query(C_QuestLog.GetQuestsOnMap, mapID)
        if type(pois) == "table" then
            for index, poi in ipairs(pois) do
                if index > 96 then break end
                if ns.Public(poi) and type(poi) == "table" and ns.GuideInteger(poi.questID) and poi.questID > 0
                    and validPoint(mapID, poi.x, poi.y) and ns.Public(poi.isQuestStart) then
                    if ns.active[poi.questID] or poi.isQuestStart == true then
                        points[poi.questID] = {id = poi.questID, mapID = mapID, x = poi.x, y = poi.y,
                            kind = poi.isQuestStart == true and "a" or "q"}
                    end
                end
            end
        end
    end
    for id in pairs(ns.active or {}) do
        if C_QuestLog then
            local targetMap, x, y = query(C_QuestLog.GetNextWaypoint, id)
            if validPoint(targetMap, x, y) then points[id] = {id = id, mapID = targetMap, x = x, y = y, kind = "q"} end
            local complete = query(C_QuestLog.IsComplete, id)
            ns.readyToTurnIn[id] = complete == true
            local quest = ns.CatalogueQuest(id)
            local finish = complete == true and quest and quest.ends and quest.ends[1]
            if finish and validPoint(finish.mapID, finish.x, finish.y) then
                -- IsComplete can arrive before GetNextWaypoint stops pointing
                -- at the objective. A known receiver is the correct next step.
                points[id] = {id = id, mapID = finish.mapID, x = finish.x, y = finish.y, kind = "t", published = true,
                    name = finish.name, npc = finish.npc, entityID = finish.entityID}
            end
            if not points[id] then
                local list
                if quest then
                    if complete == true then list = quest.ends else list = quest.objectives end
                    if complete ~= true and (not list or #list == 0) and not quest.objectiveLocationsIncomplete then list = quest.ends end
                end
                local p = list and list[1]
                if p and validPoint(p.mapID, p.x, p.y) then points[id] = {id = id, mapID = p.mapID, x = p.x, y = p.y,
                    kind = complete == true and "t" or "q", published = true, name = p.name,
                    entityID = p.entityID, action = p.action, itemName = p.itemName, npc = p.npc} end
            end
            if points[id] then
                if complete == true then points[id].kind = "t" end
            end
        end
    end
    ns.routeLocations = points
end

function ns.ResetRouteTraffic() sentLocations = {} end

function ns.SendRouteLocations(force, revision)
    if not revision then return end
    local ids = {}
    for id in pairs(ns.routeLocations) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do
        local p = ns.routeLocations[id]
        local message = table.concat({"1", "R", revision, id, p.mapID,
            math.floor(p.x * 100000), math.floor(p.y * 100000), p.kind}, "|")
        if (force or sentLocations[id] ~= message) and ns.QueueMessage(message) then sentLocations[id] = message end
    end
    for id in pairs(sentLocations) do
        if not ns.routeLocations[id] and ns.QueueMessage("1|R|" .. revision .. "|" .. id .. "|0|0|0|x") then sentLocations[id] = nil end
    end
end

function ns.ReceiveRouteMessage(message, sender)
    if string.sub(message, 1, 4) ~= "1|R|" then return false end
    local revision, id, mapID, x, y, kind = string.match(message, "^1|R|(%d+)|(%d+)|(%d+)|(%d+)|(%d+)|([aqtx])$")
    revision, id, mapID, x, y = tonumber(revision), tonumber(id), tonumber(mapID), tonumber(x), tonumber(y)
    if not ns.GuideInteger(revision) or not ns.GuideInteger(id) or id <= 0 or not ns.GuideInteger(x, 100000)
        or not ns.GuideInteger(y, 100000) or not ns.GuideInteger(mapID, 1000000)
        or (kind ~= "x" and mapID <= 0) or (kind == "x" and (mapID ~= 0 or x ~= 0 or y ~= 0)) then
        return true, false, "invalid quest destination"
    end
    ns.members[sender] = ns.members[sender] or {}
    local member = ns.members[sender]
    if member.activeRevision and revision < member.activeRevision then return true, false, "old quest destination" end
    member.routeLocations = member.routeLocations or {}
    if kind == "x" then member.routeLocations[id] = nil; return true, true end
    local count = 0
    for _ in pairs(member.routeLocations) do count = count + 1 end
    if not member.routeLocations[id] and count >= 96 then return true, false, "quest destination limit" end
    member.routeLocations[id] = {id = id, revision = revision, mapID = mapID, x = x / 100000, y = y / 100000, kind = kind}
    return true, true
end

function ns.RoutePointForMember(key, id)
    if key == ns.self then return ns.routeLocations[id] end
    local member = ns.members[key]
    if member and member.syncPending then return end
    local point = member and member.routeLocations and member.routeLocations[id]
    if point and point.revision == member.activeRevision and (point.kind == "a" or (member.active and member.active[id])) then return point end
end

function ns.RouteRecords()
    local records = {}
    local function add(key, points)
        for id in pairs(points or {}) do
            local point = ns.RoutePointForMember(key, id)
            if point then
                local title = ns.localTitles and ns.localTitles[id]
                if not title and C_QuestLog then title = ns.SafeTitle(query(C_QuestLog.GetTitleForQuestID, id)) end
                local catalog = ns.catalogue and ns.catalogue.quests[id]
                if not title then title = catalog and catalog.title or "Quest " .. id end
                records[id] = records[id] or {id = id, title = title, lineID = 0, lineName = "", npc = "",
                    level = ns.questLevels[id] or (catalog and catalog.level) or 0,
                    mapID = point.mapID, x = point.x, y = point.y, source = "p"}
            end
        end
    end
    add(ns.self, ns.routeLocations)
    for _, name in ipairs(ns.partyNames or {}) do add(name, ns.members[name] and ns.members[name].routeLocations) end
    return records
end

local function focusStatus(key, id, query)
    if key == ns.self then return ns.active[id], ns.Completed(id, query), ns.offered[id] end
    local member = ns.members[key]
    return member and member.active and member.active[id], member and member.completed and member.completed[id], member and member.offered and member.offered[id]
end

function ns.RouteStop(record, focusKey)
    focusKey = focusKey or ns.self
    local active, completed, offered = focusStatus(focusKey, record.id)
    if completed and not active and not offered then return end
    local catalog = ns.catalogue and ns.catalogue.quests[record.id]
    local profile = focusKey == ns.self and ns.profile or (ns.members[focusKey] and ns.members[focusKey].profile)
    if not active then
        if ns.CatalogueAllowed(record.id, profile, focusKey) ~= true then return end
        if catalog and ns.CatalogueCompletion(focusKey, record.id) ~= false
            and ns.PickupOfferEvidence(focusKey, record.id) ~= true then return end
    end
    local p = ns.RoutePointForMember(focusKey, record.id)
    if active then
        local ready = (focusKey == ns.self and ns.readyToTurnIn[record.id])
            or (ns.QuestProgressReady and ns.QuestProgressReady(focusKey, record.id))
        if ready and p and p.kind ~= "t" then
            -- Public objective completion can precede a native waypoint refresh.
            local finish = catalog and catalog.ends and catalog.ends[1]
            if finish and validPoint(finish.mapID, finish.x, finish.y) then
                p = {mapID = finish.mapID, x = finish.x, y = finish.y, kind = "t", published = true,
                    name = finish.name, entityID = finish.entityID, npc = finish.npc}
            else p = nil end
        end
        -- A pickup location is not an objective or a turn-in. Keep those stages
        -- separate rather than sending a player with an active quest to its giver.
        if not p and catalog then
            local point
            if ready then point = catalog.ends and catalog.ends[1]
            else point = catalog.objectives and catalog.objectives[1] end
            if point and validPoint(point.mapID, point.x, point.y) then
                p = {mapID = point.mapID, x = point.x, y = point.y, kind = ready and "t" or "q",
                    entityID = point.entityID, action = point.action, name = point.name, published = true, npc = point.npc}
            end
        end
        if not p or p.kind == "a" then return end
    elseif not p then
        if (record.source == "n" or record.source == "l") and validPoint(record.mapID, record.x, record.y) then
            p = {mapID = record.mapID, x = record.x, y = record.y, kind = "a"}
        elseif catalog and catalog.starts and catalog.starts[1] then
            local start = catalog.starts[1]
            if validPoint(start.mapID, start.x, start.y) then p = {mapID = start.mapID, x = start.x, y = start.y,
                kind = "a", published = true, name = start.name, entityID = start.entityID} end
        end
    end
    if not p then return end
    local title = ns.QuestTitle(record.id)
    if string.find(title, "(title pending)", 1, true) and record.title ~= "" then title = record.title end
    local npc = record.npc ~= "" and record.npc or (p.name or "")
    local entityID, action, itemName, npcName = p.entityID, p.action, p.itemName, p.npc and p.name or nil
    local facts = p
    local matched, bestIdentity, bestDistance
    local candidates = catalog and (p.kind == "a" and catalog.starts or (p.kind == "t" and catalog.ends or catalog.objectives))
    for _, candidate in ipairs(candidates or {}) do
        if candidate.mapID == p.mapID and math.abs(candidate.x - p.x) < 0.04 and math.abs(candidate.y - p.y) < 0.04 then
            local compatible = not (p.objectiveKey and candidate.objectiveKey and p.objectiveKey ~= candidate.objectiveKey)
                and not (p.itemID and candidate.itemID and p.itemID ~= candidate.itemID)
            local identity = (p.objectiveKey and p.objectiveKey == candidate.objectiveKey)
                or (p.itemID and p.itemID == candidate.itemID)
                or (p.entityID and p.entityID == candidate.entityID)
                or (p.name and p.name ~= "" and p.name == candidate.name)
            identity = identity and 0 or 1
            local distance = (candidate.x - p.x) ^ 2 + (candidate.y - p.y) ^ 2
            if compatible and (not matched or identity < bestIdentity or (identity == bestIdentity and distance < bestDistance)) then
                matched, bestIdentity, bestDistance = candidate, identity, distance
            end
        end
    end
    if matched then
        facts = matched
        entityID, action = entityID or matched.entityID, action or matched.action
        itemName = itemName or matched.itemName
        if matched.npc then npcName = npcName or matched.name end
    end
    local result = {id = record.id, mapID = p.mapID, x = p.x, y = p.y, kind = p.kind, title = title, published = p.published,
        learnedSource = ns.LearnedStepSource(record.id, profile, focusKey),
        entityID = entityID, action = action, itemName = itemName, targetName = p.name or npcName,
        npcName = npcName or ((p.kind == "a" or p.kind == "t") and npc ~= "" and npc or nil),
        label = p.kind == "t" and ("Turn in " .. title) or (p.kind == "q" and ("Work on " .. title)
            or (npc ~= "" and ("Talk to " .. npc) or ("Check pickup: " .. title))),
        approximate = p.kind == "a" and record.source == "n"}
    for _, key in ipairs({"quantity", "itemID", "objectiveKey", "useItemName", "spellID", "entityType",
        "legacyStepKey", "sourceAction", "alternativeEntityIDs", "progressName", "objectiveLabel", "quantityUnknown"}) do
        result[key] = p[key]
        if result[key] == nil then result[key] = facts[key] end
    end
    if result.quantityUnknown then result.quantity = nil end
    return result
end

function ns.PublishedGuideStop(record, point, kind)
    if not point or not validPoint(point.mapID, point.x, point.y) then return end
    return {id = record.id, mapID = point.mapID, x = point.x, y = point.y, kind = kind,
        title = ns.QuestTitle(record.id), label = point.name or record.title, published = true,
        entityID = point.entityID, action = point.action, itemName = point.itemName,
        targetName = point.name, npcName = point.npc and point.name or nil,
        alternativeCount = point.alternativeCount, quantity = point.quantity, itemID = point.itemID,
        objectiveKey = point.objectiveKey, useItemName = point.useItemName, spellID = point.spellID,
        entityType = point.entityType, worldFallback = point.worldFallback, legacyStepKey = point.legacyStepKey,
        sourceAction = point.sourceAction, alternativeEntityIDs = point.alternativeEntityIDs,
        progressName = point.progressName, objectiveLabel = point.objectiveLabel, quantityUnknown = point.quantityUnknown}
end

function ns.ClientObjectiveStop(stop, key)
    -- Peer packets do not distinguish native coordinates from a catalogue
    -- fallback, so only our own native read can fill this missing stage.
    if key ~= ns.self or not stop.unknownLocation or stop.kind ~= "q" then return end
    local active = key == ns.self and ns.active or ns.members[key] and ns.members[key].active
    if not active or not active[stop.id] then return end
    local point = ns.RoutePointForMember(key, stop.id)
    -- Published fallback points cannot fill a genuinely missing objective:
    -- otherwise the same known drop area would be mislabeled as the missing one.
    if not point or point.kind ~= "q" or point.published
        or not validPoint(point.mapID, point.x, point.y) then return end
    local result = {}; for name, value in pairs(stop) do result[name] = value end
    result.fixedStepKey = ns.GuideStepKey(stop)
    result.mapID, result.x, result.y = point.mapID, point.x, point.y
    result.unknownLocation, result.clientLocation = nil, true
    result.label = "Finish remaining objectives for " .. stop.title
    return result
end

function ns.QuestRouteStages(record, focusKey)
    local first = ns.RouteStop(record, focusKey)
    if not first then return {} end
    local result, quest = {first}, ns.CatalogueQuest(record.id)
    if not quest or first.kind == "t" then return result end
    local function add(point, kind, prefix)
        if not point or not validPoint(point.mapID, point.x, point.y) then return end
        local previous = result[#result]
        if previous.mapID == point.mapID and math.abs(previous.x - point.x) < 0.00001 and math.abs(previous.y - point.y) < 0.00001 then return end
        local stop = ns.PublishedGuideStop(record, point, kind)
        stop.label, stop.planned = prefix .. point.name, true
        result[#result + 1] = stop
        result[#result].learnedSource = first.learnedSource
    end
    if first.kind == "a" then
        for _, point in ipairs(quest.objectives or {}) do add(point, "q", "Objective area: ") end
        if quest.objectiveLocationsIncomplete then return result end
    elseif first.kind == "q" and first.published then
        for _, point in ipairs(quest.objectives or {}) do
            if point.mapID ~= first.mapID or math.abs(point.x - first.x) >= 0.00001 or math.abs(point.y - first.y) >= 0.00001 then
                add(point, "q", "Objective area: ")
            end
        end
        if quest.objectiveLocationsIncomplete then return result end
    end
    add(quest.ends and quest.ends[1], "t", "After objectives, return to ")
    return result
end

function ns.RouteStages(record, focusKey)
    if ns.GuideQuestSkipped(record.id) then return {} end
    return ns.FilterGuideStages(ns.QuestRouteStages(record, focusKey))
end

function ns.PartyRouteStages(record, preferred, leveling)
    local chosen, chosenPerson, chosenRank, chosenPreference
    local stageOrder = {a = 1, q = 2, t = 3}
    for _, person in ipairs(ns.PartyProfiles()) do
        if person.synced and (not leveling or ns.LevelingWorkAllowed(record.id, person.key)) then
            local stages = ns.RouteStages(record, person.key)
            if #stages > 0 then
                local rank, preference = stageOrder[stages[1].kind], person.key == preferred and 0 or 1
                if not chosen or rank < chosenRank or (rank == chosenRank and preference < chosenPreference)
                    or (rank == chosenRank and preference == chosenPreference and person.key < chosenPerson.key) then
                    chosen, chosenPerson, chosenRank, chosenPreference = stages, person, rank, preference
                end
            end
        end
    end
    if chosen then
        for _, stage in ipairs(chosen) do stage.memberKey = chosenPerson.key; stage.forPlayer = chosenPerson.name end
    end
    return chosen or {}
end

function ns.LevelingRouteStages(record, preferred, personal)
    if not personal then return ns.PartyRouteStages(record, preferred, true) end
    if ns.IsProfessionQuest(record.id) or ns.LevelingWorkAllowed(record.id, ns.self) then
        return ns.RouteStages(record, ns.self)
    end
    return {}
end

function ns.PartyQuestFinished(id, query)
    if query and query.finished[id] ~= nil then return query.finished[id] end
    for _, person in ipairs(query and query.profiles or ns.PartyProfiles()) do
        local active, complete, offered = focusStatus(person.key, id, query)
        if not person.synced or active or offered then
            if query then query.finished[id] = false end
            return false
        end
        local allowed = ns.CatalogueIdentityAllowed(id, person.profile)
        if allowed ~= false and complete ~= true then
            if query then query.finished[id] = false end
            return false
        end
    end
    if query then query.finished[id] = true end
    return true
end

local function origin(mapID)
    if not ns.profile or ns.profile.mapID ~= mapID or not C_Map then return end
    local point = query(C_Map.GetPlayerMapPosition, mapID, "player")
    if point and type(point.GetXY) == "function" then
        local x, y = query(point.GetXY, point)
        if validPoint(mapID, x, y) then return {mapID = mapID, x = x, y = y, label = "Route start"} end
    end
end

function ns.BuildGuideRoute(guide, includeOrigin, cooperative)
    if guide.mode == "travel" then return ns.BuildTravelGuideRoute(guide) end
    if guide.fixedRoute then return ns.BuildFixedGuideRoute(guide, includeOrigin, cooperative) end
    if guide.fullGuide and (guide.mode == "zone" or guide.mode == "chain") then return ns.BuildLevelingRoute(guide, includeOrigin, cooperative) end
    if (guide.mode == "current" or guide.mode == "bundle") and ns.BuildCurrentQuestRoute then return ns.BuildCurrentQuestRoute(guide, includeOrigin) end
    if guide.mode == "dungeon" and ns.BuildDungeonRoute then return ns.BuildDungeonRoute(guide, includeOrigin) end
    if guide.mode == "circuit" and ns.BuildCircuitRoute then return ns.BuildCircuitRoute(guide, includeOrigin) end
    local blocks, missing, focusKey = {}, 0, guide.focusKey or ns.self
    local partial = false
    for _, record in ipairs(guide.records or {guide.target}) do
        local stages = {}
        if guide.personal or ns.FocusCanStartRecord(record, focusKey) then
            stages = ns.LevelingRouteStages(record, focusKey, guide.personal)
        end
        if #stages > 0 then
            blocks[#blocks + 1] = stages
            local quest = ns.CatalogueQuest(record.id)
            if quest and quest.objectiveLocationsIncomplete then partial = true end
        else missing = missing + 1 end
    end
    local mapID = blocks[1] and blocks[1][1].mapID or 0
    local otherMaps = 0
    local start = includeOrigin and origin(mapID) or nil
    local planningOrigin = origin(mapID)
    local tasks = {}
    for _, block in ipairs(blocks) do
        if block[1].mapID ~= mapID then otherMaps = otherMaps + #block
        else
            local localStages = {}
            for index, p in ipairs(block) do
                if p.mapID ~= mapID then otherMaps = otherMaps + #block - index + 1; break end
                localStages[#localStages + 1] = p
            end
            if #localStages > 0 then tasks[#tasks + 1] = {stages = localStages, next = 1} end
        end
    end
    local ordered, remaining = {}, 0
    -- Choose among dependency-ready stages. This collects nearby pickups first,
    -- groups objectives, and delays each return until its earlier stages finish.
    while #ordered < MAX_STOPS do
        local previous, best, cost = ordered[#ordered] or planningOrigin, nil, nil
        for index, task in ipairs(tasks) do
            local p = task.stages[task.next]
            if p then
                local distance = previous and (((p.x - previous.x) * 1.5)^2 + (p.y - previous.y)^2) or index
                if p.kind == "a" and previous and distance < 0.0064 then distance = distance * 0.65 end
                if not cost or distance < cost or (distance == cost and p.id < tasks[best].stages[tasks[best].next].id) then best, cost = index, distance end
            end
        end
        if not best then break end
        local task = tasks[best]
        ordered[#ordered + 1] = task.stages[task.next]
        task.next = task.next + 1
    end
    for _, task in ipairs(tasks) do remaining = remaining + math.max(0, #task.stages - task.next + 1) end
    return {key = guide.key, title = guide.title, mapID = mapID, stops = ordered, origin = start,
        missing = missing, otherMaps = otherMaps, limited = remaining, focusKey = focusKey, partial = partial}
end

local function inCombat()
    local value = type(InCombatLockdown) == "function" and InCombatLockdown()
    return not ns.Public(value) or value == true
end
ns.RouteInCombat = inCombat

function ns.StopIcon(stop)
    if stop.kind == "a" then return "Interface\\GossipFrame\\AvailableQuestIcon" end
    if stop.kind == "t" then return "Interface\\GossipFrame\\ActiveQuestIcon" end
    if stop.kind == "f" then return "Interface\\Icons\\Ability_Mount_Wyvern_01" end
    if stop.kind == "corpse" then return "Interface\\TargetingFrame\\UI-RaidTargetingIcon_8" end
    if stop.kind == "q" and ns.Option("npcMarker") == "cross" then return "Interface\\RaidFrame\\ReadyCheck-NotReady" end
    if stop.action == "kill" then return "Interface\\TargetingFrame\\UI-RaidTargetingIcon_8" end
    return nil
end

function ns.StopSymbol(stop) return stop.kind == "travel" and "›" or stop.action == "collect" and "*" or "+" end

local function hideDrawing(provider)
    for _, pin in ipairs(provider.pins or {}) do pin:Hide() end
    for _, line in ipairs(provider.lines or {}) do line:Hide() end
    for _, line in ipairs(provider.shadowLines or {}) do line:Hide() end
    if provider.legend then provider.legend:Hide() end
    ns.routeStats.pins, ns.routeStats.lines = 0, 0
end

function ns.RouteSurface(map)
    local function finite(value) return type(value) == "number" and value == value and value > -math.huge and value < math.huge end
    local canvas = query(map.GetCanvas, map)
    if not canvas then return nil, "Map canvas unavailable." end
    local parent = canvas
    local left, top, spanX, spanY, mode = 0, 0, 1, 1, "Canvas fallback"
    local viewport = query(map.GetCanvasContainer, map)
    if viewport and type(map.GetViewRect) == "function" then
        local rect = query(map.GetViewRect, map)
        if not rect then return nil, "Waiting for map view rectangle." end
        local right, bottom
        left, right = query(rect.GetLeft, rect), query(rect.GetRight, rect)
        top, bottom = query(rect.GetTop, rect), query(rect.GetBottom, rect)
        if not finite(left) or not finite(right) or not finite(top) or not finite(bottom)
            or right <= left or bottom <= top or right - left < 0.000001 or bottom - top < 0.000001 then
            return nil, "Map view rectangle unavailable or restricted."
        end
        spanX, spanY, parent, mode = right - left, bottom - top, viewport, "Viewport projection"
    end
    local width, height = query(parent.GetWidth, parent), query(parent.GetHeight, parent)
    if not finite(width) or not finite(height) or width <= 0 or height <= 0 then return nil, "Waiting for map layout." end
    return {parent = parent, width = width, height = height, left = left, top = top, spanX = spanX, spanY = spanY, mode = mode}
end

function ns.RouteProject(surface, point)
    return (point.x - surface.left) / surface.spanX * surface.width,
        (point.y - surface.top) / surface.spanY * surface.height
end

function ns.ClipRouteSegment(x1, y1, x2, y2, width, height)
    local dx, dy, start, finish = x2 - x1, y2 - y1, 0, 1
    for _, bound in ipairs({{-dx, x1}, {dx, width - x1}, {-dy, y1}, {dy, height - y1}}) do
        local p, q = bound[1], bound[2]
        if p == 0 then if q < 0 then return end
        else
            local t = q / p
            if p < 0 then start = math.max(start, t) else finish = math.min(finish, t) end
            if start > finish then return end
        end
    end
    return x1 + start * dx, y1 + start * dy, x1 + finish * dx, y1 + finish * dy
end

function ns.RouteDisplayStops(route)
    if ns.Option("fullRoute") then return route.previewStops or route.stops end
    local stops, places, previous = {}, 0, nil
    for _, stop in ipairs(route.stops) do
        local key = stop.mapID .. ":" .. math.floor(stop.x * 100000) .. ":" .. math.floor(stop.y * 100000)
        if key ~= previous then places = places + 1 end
        if places > 1 + ns.Option("routeAhead") then break end
        stops[#stops + 1], previous = stop, key
    end
    return stops
end

function ns.ViewRouteZone(provider)
    local route = ns.RouteForDisplay()
    provider = provider or ns.routeProvider
    if not route or not provider or not provider.owningMap then return end
    if inCombat() then ns.routeZoneViewPending = true; return end
    provider.owningMap:SetMapID(route.mapID); provider.owningMap:Show(); ns.DrawRoute(provider)
end

local function routeLegend(provider, map)
    if provider.legend then return provider.legend end
    local parent = map
    local viewport = query(map.GetCanvasContainer, map) or query(map.GetCanvas, map) or map
    local legend = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    legend:SetPoint("TOPLEFT", viewport, "BOTTOMLEFT", 0, -6)
    legend:SetBackdrop({bgFile = "Interface\\Buttons\\WHITE8X8"})
    legend:SetBackdropColor(0.035, 0.045, 0.06, 0.45)
    local level = query(parent.GetFrameLevel, parent)
    if type(level) == "number" then legend:SetFrameLevel(level + 40) end
    legend.caption = legend:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    legend.caption:SetPoint("TOPLEFT", 10, -6); legend.caption:SetSize(308, 34); legend.caption:SetJustifyH("LEFT")
    legend.full = ns.UIButton(legend, "Show full route", 120, function() ns.SetOption("fullRoute", not ns.Option("fullRoute")) end)
    legend.full:SetPoint("BOTTOMLEFT", 8, 5)
    legend.ahead = ns.UIButton(legend, "2 ahead", 90, function() ns.SetOption("routeAhead", (ns.Option("routeAhead") + 1) % 3) end)
    legend.ahead:SetPoint("BOTTOMLEFT", 134, 5)
    legend.zone = ns.UIButton(legend, "View route zone", 120, function() ns.ViewRouteZone(provider) end)
    legend.zone:SetPoint("BOTTOMLEFT", 230, 5)
    local close = CreateFrame("Button", nil, legend, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", 0, 0); close:SetScript("OnClick", function() ns.ClearRoute(); ns.Refresh() end)
    -- There is no continuous position event. Only redraw map geometry at 1 Hz
    -- while this owned overlay is visible; do not rescan quests or replan.
    legend.elapsed = 0
    legend:SetScript("OnUpdate", function(self, elapsed)
        if not ns.Public(elapsed) or type(elapsed) ~= "number" or elapsed < 0 or elapsed ~= elapsed or elapsed > 1000 then return end
        self.elapsed = self.elapsed + elapsed
        if self.elapsed < 1 then return end
        self.elapsed = 0
        local route = ns.RouteForDisplay()
        local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
        if not route then return end
        local point = ns.GuideInteger(mapID) and mapID > 0 and ns.PlayerPoint(mapID) or nil
        local old = provider.playerOrigin
        if old and not point or point and (not old or point.mapID ~= old.mapID
            or math.abs(point.x - old.x) + math.abs(point.y - old.y) > 0.0001) then ns.DrawRoute(provider, true) end
    end)
    provider.legend = legend
    return legend
end

local function updateLegend(legend, text)
    legend.caption:SetText(text); legend.caption:SetShown(ns.Option("mapLegend"))
    legend:SetSize(360, ns.Option("mapLegend") and 78 or 37)
    legend.full.caption:SetText(ns.Option("fullRoute") and "Focus next steps" or "Show full route")
    legend.ahead.caption:SetText(ns.Option("routeAhead") .. " ahead")
    legend.ahead:SetEnabled(not ns.Option("fullRoute"))
    legend:Show()
end

local function publicOwnedDrawing(provider)
    if not provider.overlay or not provider.legend then return false end
    local frames = {provider.overlay, provider.legend}
    for _, pin in ipairs(provider.pins or {}) do frames[#frames + 1] = pin end
    for _, frame in ipairs(frames) do
        if ns.ReadPublic(frame.IsProtected, frame) ~= false then return false end
    end
    return true
end

function ns.DrawRoute(provider, geometryOnly)
    provider = provider or ns.routeProvider
    if not provider then return end
    if inCombat() and (not geometryOnly or not publicOwnedDrawing(provider)) then ns.routeRedrawPending = true; return end
    hideDrawing(provider)
    ns.routeStats.surface, ns.routeStats.geometry = nil, nil
    local map, route = provider.owningMap, ns.RouteForDisplay()
    if not map or not route then
        if ns.routePaused then ns.routeStats.status = ns.routePaused end
        return
    end
    local mapID = map:GetMapID()
    if not ns.GuideInteger(mapID) or mapID <= 0 then ns.routeStats.status = "Map view unavailable."; return end
    local legend = routeLegend(provider, map)
    local strata = query(map.GetFrameStrata, map)
    local upper = {DIALOG = true, FULLSCREEN = true, FULLSCREEN_DIALOG = true, TOOLTIP = true}
    legend:SetFrameStrata(upper[strata] and strata or "HIGH")
    local displayed = ns.RouteDisplayStops(route)
    local playerMap = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local origin = ns.GuideInteger(playerMap) and playerMap > 0 and ns.PlayerPoint(playerMap) or nil
    local projected, projectionContext, hasDisplayedMap = {}, {}, playerMap == mapID
    for index, stop in ipairs(displayed) do
        projected[index] = ns.ProjectMapPoint(stop, mapID, projectionContext)
        if projected[index] then hasDisplayedMap = true end
    end
    if mapID ~= route.mapID and not hasDisplayedMap then
        updateLegend(legend, "Next steps are in " .. ns.MapName(route.mapID) .. ".\nTravel coordinates are unavailable here. Use View route zone.")
        ns.routeStats.status = "Viewing another map; next route steps are in " .. ns.MapName(route.mapID) .. "."
        return
    end
    local surface, unavailable = ns.RouteSurface(map)
    if not surface then ns.routeStats.status = unavailable; updateLegend(legend, unavailable .. "\nThe selected route is retained."); return end
    if inCombat() and ns.ReadPublic(provider.overlay.GetParent, provider.overlay) ~= surface.parent then
        ns.routeRedrawPending = true; return
    end
    local width, height = surface.width, surface.height
    if not provider.overlay then
        provider.overlay = CreateFrame("Frame", nil, surface.parent)
        provider.overlay:EnableMouse(false)
        if type(provider.overlay.SetClipsChildren) == "function" then provider.overlay:SetClipsChildren(true) end
        if type(provider.overlay.SetIgnoreParentAlpha) == "function" then provider.overlay:SetIgnoreParentAlpha(true) end
    end
    local overlay = provider.overlay
    if not inCombat() then overlay:SetParent(surface.parent) end
    overlay:ClearAllPoints(); overlay:SetAllPoints(surface.parent)
    overlay:Show()
    overlay:SetFrameStrata(upper[strata] and strata or "HIGH")
    local level = query(surface.parent.GetFrameLevel, surface.parent)
    if type(level) == "number" then overlay:SetFrameLevel(level + 30) end
    if type(overlay.CreateLine) ~= "function" then ns.routeStats.status = "Route line drawing unavailable."; return end
    ns.routeStats.surface = surface.mode
    ns.routeStats.geometry = string.format("%.0f x %.0f; view %.4f,%.4f / %.4f,%.4f", width, height,
        surface.left, surface.top, surface.spanX, surface.spanY)
    local points = {}
    provider.playerOrigin = origin
    local travel = not route.flying and origin and displayed[1] and ns.TravelLinePoints(origin, displayed[1])
    if route.flying then
        -- The flight's terrain path is unknown. Do not draw ground directions
        -- from the moving gryphon/wyvern to quest objectives.
    elseif travel then
        for _, point in ipairs(travel) do points[#points + 1] = point and ns.ProjectMapPoint(point, mapID, projectionContext) or false end
        for index = 2, #displayed do points[#points + 1] = projected[index] or false end
    else
        if origin then points[#points + 1] = ns.ProjectMapPoint(origin, mapID, projectionContext) or false end
        for index in ipairs(displayed) do points[#points + 1] = projected[index] or false end
    end
    local visibleLines = 0
    for index = 2, #points do
      if points[index - 1] and points[index] then
        local x1, y1 = ns.RouteProject(surface, points[index - 1])
        local x2, y2 = ns.RouteProject(surface, points[index])
        x1, y1, x2, y2 = ns.ClipRouteSegment(x1, y1, x2, y2, width, height)
        if x1 and math.abs(x2 - x1) + math.abs(y2 - y1) >= 0.5 then
            visibleLines = visibleLines + 1
            provider.shadowLines = provider.shadowLines or {}
            local shadow = provider.shadowLines[visibleLines]
            if not shadow then shadow = overlay:CreateLine(nil, "OVERLAY", nil, 6); provider.shadowLines[visibleLines] = shadow end
            shadow:SetThickness(4); shadow:SetColorTexture(0.12, 0.085, 0.025, ns.routePaused and 0.45 or 0.85)
            shadow:SetStartPoint("TOPLEFT", overlay, x1, -y1)
            shadow:SetEndPoint("TOPLEFT", overlay, x2, -y2); shadow:Show()
            local line = provider.lines[visibleLines]
            if not line then line = overlay:CreateLine(nil, "OVERLAY", nil, 7); provider.lines[visibleLines] = line end
            line:SetThickness(2)
            line:SetColorTexture(1, 0.82, 0.30, ns.routePaused and 0.45 or 1)
            line:SetStartPoint("TOPLEFT", overlay, x1, -y1)
            line:SetEndPoint("TOPLEFT", overlay, x2, -y2)
            line:Show()
        end
      end
    end
    local groups, locations = {}, {}
    local waypoint = ns.travelWaypoint
    if waypoint and waypoint.kind == "travel" then
        local location = ns.ProjectMapPoint(waypoint, mapID, projectionContext)
        local x, y
        if location then x, y = ns.RouteProject(surface, location) end
        if x and x >= 0 and x <= width and y >= 0 and y <= height then
            groups[#groups + 1] = {point = waypoint, x = x, y = y, stops = {waypoint}, numbers = {"›"}}
        end
    end
    for index, p in ipairs(displayed) do
        local location = projected[index]
        local x, y
        if location then x, y = ns.RouteProject(surface, location) end
        if x and x >= 0 and x <= width and y >= 0 and y <= height then
            local key = math.floor(location.x * 100000) .. ":" .. math.floor(location.y * 100000)
            local group = locations[key]
            if not group then
                for _, nearby in ipairs(groups) do if math.abs(nearby.x - x) <= 6 and math.abs(nearby.y - y) <= 6 then group = nearby; break end end
            end
            if not group then group = {point = p, x = x, y = y, stops = {}, numbers = {}}; groups[#groups + 1] = group end
            locations[key] = group
            group.stops[#group.stops + 1], group.numbers[#group.numbers + 1] = p, tostring(p.guideStep or index)
        end
    end
    for index, group in ipairs(groups) do
        local p = group.point
        local pin = provider.pins[index]
        if not pin then
            pin = CreateFrame("Button", nil, overlay)
            pin:SetSize(18, 18)
            pin.icon = pin:CreateTexture(nil, "ARTWORK")
            pin.icon:SetSize(16, 16)
            pin.icon:SetPoint("CENTER")
            pin.symbol = pin:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
            pin.symbol:SetFont("Fonts\\FRIZQT__.TTF", 18, "OUTLINE")
            pin.symbol:SetPoint("CENTER"); pin.symbol:SetTextColor(1, 0.85, 0.3, 1)
            pin.number = pin:CreateFontString(nil, "OVERLAY", "GameFontNormal")
            pin.number:SetFont("Fonts\\FRIZQT__.TTF", 11, "OUTLINE")
            pin.number:SetTextColor(1, 0.94, 0.76, 1)
            pin.number:SetPoint("TOPLEFT", pin, "BOTTOMRIGHT", -3, 4)
            pin:SetScript("OnEnter", function(self)
                if not GameTooltip then return end
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                for step, stop in ipairs(self.group.stops) do
                    GameTooltip:AddLine(self.group.numbers[step] .. ". " .. stop.label, 0.96, 0.76, 0.36, true)
                    GameTooltip:AddLine(stop.title, 1, 1, 1, true)
                    if stop.forPlayer then GameTooltip:AddLine("For " .. stop.forPlayer, 0.7, 0.85, 0.9, true) end
                    if stop.approximate then GameTooltip:AddLine("Approximate NPC encounter location.", 0.7, 0.75, 0.8, true) end
                    if stop.published then GameTooltip:AddLine("Published Forever location; check against this beta build.", 0.7, 0.75, 0.8, true) end
                    if stop.planned then GameTooltip:AddLine("Planned stage after the previous step.", 0.7, 0.75, 0.8, true) end
                end
                GameTooltip:Show()
            end)
            pin:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
            provider.pins[index] = pin
        end
        pin.stop, pin.group = p, group
        local numbers = #group.numbers <= 3 and table.concat(group.numbers, "/")
            or (group.numbers[1] .. "/" .. group.numbers[2] .. "/+" .. (#group.numbers - 2))
        local icon = ns.StopIcon(p)
        pin.icon:SetTexture(icon); pin.icon:SetShown(icon ~= nil)
        pin.symbol:SetText(ns.StopSymbol(p)); pin.symbol:SetShown(icon == nil)
        pin:SetAlpha(ns.routePaused and 0.65 or 1)
        pin.number:SetText(numbers)
        pin:ClearAllPoints()
        pin:SetPoint("CENTER", overlay, "TOPLEFT", group.x, -group.y)
        pin:Show()
    end
    local missingTravel = displayed[1] and displayed[1].mapID ~= mapID and not projected[1]
    updateLegend(legend, route.flying and "Wow Together • Flying • Ground directions resume after landing" or
        "Wow Together • " .. #displayed .. " stops • " .. #groups .. " visible " .. (#groups == 1 and "place" or "places")
        .. (ns.Option("fullRoute") and " • All eligible mapped quests" or " • Next steps")
        .. (ns.routePaused and " • Waiting for party updates" or "")
        .. (route.partial and " • Partial route" or "")
        .. ((route.otherMaps or 0) > 0 and " • Other zones" or "")
        .. (missingTravel and ("\nTravel to " .. ns.MapName(displayed[1].mapID) .. "; travel coordinates unavailable here.") or ""))
    ns.routeStats.pins, ns.routeStats.lines = #groups, visibleLines
    ns.routeStats.status = route.flying and "Flying; ground route lines hidden until landing."
        or ns.routePaused and (ns.routePaused .. " Showing the last confirmed route.")
        or missingTravel and ("Cross-zone travel coordinates unavailable on map " .. mapID .. ".")
        or ("Route drawn on map " .. mapID .. ".")
end

function ns.AttachRouteProvider()
    if ns.routeProvider then return true end
    local map = WorldMapFrame
    if not map or type(map.AddDataProvider) ~= "function" or type(map.GetCanvas) ~= "function"
        or type(map.GetMapID) ~= "function" or type(MapCanvasDataProviderMixin) ~= "table" then
        ns.routeStats.status = "Map route canvas unavailable; the navigation arrow remains available."; return false
    end
    local provider = {pins = {}, lines = {}}
    for key, method in pairs(MapCanvasDataProviderMixin) do provider[key] = method end
    provider.RefreshAllData = function(self) ns.DrawRoute(self, true) end
    local function afterLayout(self)
        if not C_Timer or type(C_Timer.After) ~= "function" then ns.DrawRoute(self, true); return end
        if self.redrawQueued then return end
        self.redrawQueued = true
        C_Timer.After(0, function() self.redrawQueued = nil; ns.DrawRoute(self, true) end)
    end
    provider.OnCanvasSizeChanged = afterLayout
    provider.OnCanvasScaleChanged = afterLayout
    provider.OnCanvasPanChanged = provider.RefreshAllData
    provider.OnShow = provider.RefreshAllData
    ns.routeProvider = provider
    map:AddDataProvider(provider)
    return true
end

function ns.ActivateRoute(guide, route)
    ns.CancelGuideScan()
    ns.ResetTravelPath()
    ns.guideStepHistory, ns.navigationPreview, ns.forceRouteReplan = {}, nil, nil
    ns.routePaused = nil
    ns.routeSelection = guide
    ns.selectedRoute = route or ns.BuildGuideRoute(guide, true)
    ns.selectedRoute = ns.AddNPCVisitPickups(guide, ns.selectedRoute)
    if guide.mode == "travel" then ns.routePaused = ns.selectedRoute.pendingReason or ns.selectedRoute.complete and "Arrived in Orgrimmar." end
    ns.InitializeGuideStepHistory(guide, ns.selectedRoute)
    ns.routeSignature = nil
    ns.AttachRouteProvider()
    ns.DrawRoute()
    if ns.UpdateNPCHints then ns.UpdateNPCHints() end
    if ns.SaveSelectedGuide then ns.SaveSelectedGuide() end
end

function ns.CompleteSelectedGuide(guide, message)
    ns.routeSelection, ns.navigationPreview = guide, nil
    ns.selectedRoute = {key = guide.key, title = guide.title, mapID = guide.homeMapID or guide.mapID or 0,
        stops = {}, previewStops = {}, complete = true, remainingSteps = 0}
    ns.routePaused, ns.routeSignature = message or "Guide complete. Choose another guide when ready.", nil
    ns.guideAction = ns.routePaused
    ns.DrawRoute()
    if ns.SaveSelectedGuide then ns.SaveSelectedGuide() end
end

local function routeSignature(route)
    local parts = {tostring(route.mapID)}
    for _, p in ipairs(route.stops) do
        parts[#parts + 1] = table.concat({p.id, p.kind, p.mapID, p.x, p.y, p.label}, ":")
    end
    return table.concat(parts, "|")
end

function ns.UpdateSelectedRoute(choices, query)
    local selection = ns.routeSelection
    if not selection then return end
    if selection.mode == "travel" then ns.UpdateTravelGuide(selection); return end
    if selection.fixedRoute then ns.UpdateFixedGuideRoute(selection, query); return end
    if selection.mode == "current" and not selection.sharedBy and ns.Option("nearbyPickups") then
        for _, choice in ipairs(ns.CurrentQuestChoices() or {}) do
            if choice.mode == "bundle" and choice.mapID == selection.mapID then
                selection = choice; ns.routeSelection, ns.routeSignature = choice, nil; break
            end
        end
    elseif selection.mode == "bundle" and not selection.sharedBy and not selection.baseGuide and not ns.Option("nearbyPickups") then
        -- Turning the setting off also removes planned pickups from an open route.
        local copy = {}
        for key, value in pairs(selection) do copy[key] = value end
        copy.mode, copy.pickupIDs, copy.key = "current", nil, "current:" .. selection.mapID
        selection = copy; ns.routeSelection, ns.routeSignature = copy, nil
    end
    if selection.mode == "dungeon" then
        local finished = true
        for _, record in ipairs(selection.records) do
            local complete
            if selection.personal then complete = ns.Completed(record.id) == true and not ns.active[record.id]
            else complete = ns.PartyQuestFinished(record.id) end
            if not complete then finished = false; break end
        end
        if finished then
            ns.CompleteSelectedGuide(selection)
            return
        end
    end
    -- Keep the selected quest set on normal progress/zone updates. A manual
    -- Scan guide is the explicit place to choose a freshly optimized selection.
    local guide = selection
    if selection.mode == "dungeon" and selection.dungeon then guide = ns.DungeonGuide(selection.dungeon) end
    local id = tonumber(string.match(selection.key, "^quest:(%d+)$"))
    if id then
        local record = ns.CatalogueRecord(id)
        if record then guide = {key = selection.key, title = selection.title, records = {record}, focusKey = ns.self, personal = selection.personal} end
    end
    if not guide.personal then
        local copy = {}; for key, value in pairs(guide) do copy[key] = value end
        copy.focusKey = ns.GuideFocus(guide.records); guide = copy
    end
    local old = ns.selectedRoute
    local focus = guide and guide.focusKey or selection.focusKey
    local member = focus ~= ns.self and ns.members[focus]
    local waiting = focus ~= ns.self and (not member or not member.active or member.syncPending)
    if not guide.personal then
        for _, person in ipairs(ns.PartyProfiles()) do
            local peer = ns.members[person.key]
            if person.key ~= ns.self and peer and peer.active and not person.synced then waiting = true; break end
        end
    end
    if selection.mode == "current" or selection.mode == "bundle" then
        for _, record in ipairs(selection.records) do if ns.CurrentQuestPending(record.id) then waiting = true; break end end
        if selection.mode == "bundle" then
            for _, person in ipairs(ns.PartyProfiles()) do if not person.synced then waiting = true; break end end
        end
    end
    local route = guide and ns.BuildGuideRoute(guide, false)
    if route and old then route = ns.PinCurrentDestination(old, route) end
    if route then route = ns.AddNPCVisitPickups(guide, route, query) end
    if route and guide and route.mapID ~= guide.mapID then
        local copy = {}; for key, value in pairs(guide) do copy[key] = value end
        copy.mapID, copy.zone = route.mapID, ns.MapName(route.mapID); guide = copy
    end
    if waiting or not route or #route.stops == 0 then
        if not waiting and route and #route.stops == 0 and ns.GuideSelectionHasSkips(selection) then
            local actualDone = true
            for _, record in ipairs(selection.records or {}) do
                if not ns.PartyQuestFinished(record.id) then actualDone = false; break end
            end
            if not actualDone then
                route.mapID = old and old.mapID or selection.mapID or route.mapID
                ns.selectedRoute, ns.routeSignature = route, nil
                ns.routePaused = "Remaining guide steps are skipped."
                ns.guideAction = "All mapped remaining steps were skipped. Scan with Reconsider skips enabled, or reset skips in settings."
                ns.DrawRoute(); return
            end
        end
        local finished = not waiting
        for _, record in ipairs(selection.records or {selection.target}) do
            local complete
            if ns.GuideQuestSkipped(record.id) then complete = true
            elseif selection.mode == "bundle" then complete = ns.BundleQuestFinished(selection, record.id)
            elseif selection.mode == "current" then complete = ns.CurrentQuestFinished(record.id)
            elseif selection.personal then complete = ns.Completed(record.id) == true and not ns.active[record.id]
            else complete = ns.PartyQuestFinished(record.id) end
            if not complete then finished = false; break end
        end
        if finished then ns.CompleteSelectedGuide(selection, selection.mode == "current" and "No selected quests remain in party logs." or nil)
        else
            if not waiting and route then
                ns.routeSelection, ns.selectedRoute = guide, route
            end
            ns.routePaused = waiting and "Waiting for refreshed party quest snapshots."
                or guide.pendingReason or "Waiting for the next quest destination or prerequisite history."
            ns.routeSignature = nil
            ns.DrawRoute()
            ns.guideAction = ns.routePaused
        end
        return
    end
    route.origin = ns.profile and ns.profile.mapID == route.mapID and ns.PlayerPoint(route.mapID) or nil
    local signature = routeSignature(route)
    if signature == ns.routeSignature then return end
    local before, after = old and old.stops[1], route.stops[1]
    if before and ns.RememberGuideStep then ns.RememberGuideStep(before, after) end
    ns.routeSelection, ns.selectedRoute, ns.routeSignature, ns.routePaused = guide, route, signature, nil
    ns.DrawRoute()
    ns.guideAction = #route.stops .. " route stop(s): " .. after.label .. "."
    if ns.UpdateNPCHints then ns.UpdateNPCHints() end
end

function ns.ClearRoute()
    ns.CancelGuideScan()
    ns.ResetTravelPath()
    if ns.ClearSavedGuide then ns.ClearSavedGuide() end
    if ns.CancelGuidePlanning then ns.CancelGuidePlanning() end
    ns.routeSelection = nil
    ns.routeZoneViewPending = nil
    if inCombat() then ns.routeClearPending = true; return end
    ns.selectedRoute, ns.routeSelection, ns.routeSignature, ns.routeWaypointPending, ns.routePaused = nil, nil, nil, nil, nil
    if ns.routeProvider then hideDrawing(ns.routeProvider) end
    ns.routeStats.status = "Route cleared."
    ns.guideAction = ns.routeStats.status
    if ns.UpdateNPCHints then ns.UpdateNPCHints() end
end

function ns.FlushRouteUpdates()
    if ns.routeClearPending then ns.routeClearPending = nil; ns.ClearRoute() end
    if ns.routeRedrawPending then ns.routeRedrawPending = nil; ns.DrawRoute() end
    ns.routeWaypointPending = nil
    if ns.routeZoneViewPending and ns.selectedRoute then
        ns.routeZoneViewPending = nil
        ns.ViewRouteZone()
    end
end

ns.On("QUEST_POI_UPDATE", function() if ns.db then ns.ReadRouteLocations(); ns.ScheduleSync(); ns.Refresh() end end)
