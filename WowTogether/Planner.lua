local addonName, ns = ...

function ns.ReadPublic(fn, ...)
    if type(fn) ~= "function" then return end
    local okay, a, b, c, d, e = pcall(fn, ...)
    if okay and ns.Public(a) and ns.Public(b) and ns.Public(c) and ns.Public(d) and ns.Public(e) then return a, b, c, d, e end
end

local function currentPeople(id)
    local result = {}
    for _, person in ipairs(ns.PartyProfiles()) do
        local active = person.key == ns.self and ns.active or (ns.members[person.key] and ns.members[person.key].active)
        if person.synced and active and active[id] then result[#result + 1] = person end
    end
    return result
end

function ns.CurrentQuestPending(id)
    for _, name in ipairs(ns.partyNames or {}) do
        local member = ns.members[name]
        if member and member.syncPending and member.active and member.active[id] then return true end
    end
    return false
end

function ns.CurrentQuestFinished(id)
    return #currentPeople(id) == 0 and not ns.CurrentQuestPending(id)
end

function ns.HasCurrentPartyQuests()
    for _, person in ipairs(ns.PartyProfiles()) do
        local active = person.key == ns.self and ns.active or (ns.members[person.key] and ns.members[person.key].active)
        for id in pairs(active or {}) do
            if not ns.IsProfessionQuest(id) and not ns.IsRepeatableQuest(id) and not ns.GuideQuestSkipped(id) then return true end
        end
    end
    return false
end

local function routePeople(guide, id)
    if guide.mode == "bundle" and guide.pickupIDs and guide.pickupIDs[id] then return ns.PartyProfiles() end
    return currentPeople(id)
end

function ns.CurrentRouteMap(guide)
    local points, counts = {}, {}
    for _, record in ipairs(guide.records) do
        for _, person in ipairs(routePeople(guide, record.id)) do
            local first = person.synced and ns.RouteStages(record, person.key)[1]
            if first then
                points[first.mapID] = points[first.mapID] or first
                counts[first.mapID] = (counts[first.mapID] or 0) + 1
            end
        end
    end
    if points[guide.mapID] then return guide.mapID end
    local current = ns.profile and ns.profile.mapID or 0
    if points[current] then return current end
    local position = ns.PlayerPoint(current)
    local best, distance
    for mapID, point in pairs(points) do
        local value = position and ns.CrossMapDistance and ns.CrossMapDistance(position, point) or math.huge
        if not best or value < distance or (value == distance and (counts[mapID] > counts[best]
            or counts[mapID] == counts[best] and mapID < best)) then best, distance = mapID, value end
    end
    return best or guide.mapID
end

local function routeMetric(mapID)
    local width, height
    if C_Map then width, height = ns.ReadPublic(C_Map.GetMapWorldSize, mapID) end
    local physical = type(width) == "number" and type(height) == "number" and width > 0 and height > 0
        and width < 1000000 and height < 1000000
    width, height = physical and width or 1.5, physical and height or 1
    return function(a, b)
        if not a or not b then return 0 end
        return math.sqrt(((a.x - b.x) * width)^2 + ((a.y - b.y) * height)^2)
    end, physical
end

local function improveObjectiveRuns(stops, position, distance)
    local first = 1
    while first <= #stops do
        if stops[first].kind ~= "q" then first = first + 1
        else
            local last = first
            while stops[last + 1] and stops[last + 1].kind == "q" do last = last + 1 end
            -- Bounded two-edge swaps improve the nearest-neighbour loop while
            -- keeping pickups and ready/future returns in their chosen order.
            for pass = 1, 3 do
                local changed = false
                for a = first, last - 1 do
                    for b = a + 1, last do
                        local before, after = stops[a - 1] or position, stops[b + 1]
                        local old = distance(before, stops[a]) + distance(stops[b], after)
                        local new = distance(before, stops[b]) + distance(stops[a], after)
                        if new + 0.000001 < old then
                            local left, right = a, b
                            while left < right do stops[left], stops[right] = stops[right], stops[left]; left, right = left + 1, right - 1 end
                            changed = true
                        end
                    end
                end
                if not changed then break end
            end
            first = last + 1
        end
    end
end

function ns.BuildCurrentQuestRoute(guide, includeOrigin)
    local mapID, phases, missing, otherMaps, partial = ns.CurrentRouteMap(guide), {{}, {}, {}, {}}, 0, 0, false
    local seen, unknownObjectives = {{}, {}, {}, {}}, 0
    for _, record in ipairs(guide.records) do
        local found, unavailable = false, false
        local people = routePeople(guide, record.id)
        local pickup = guide.mode == "bundle" and guide.pickupIDs and guide.pickupIDs[record.id]
        for _, person in ipairs(people) do
            if person.synced then
                local stages = ns.RouteStages(record, person.key)
                -- Only explicitly selected nearby quests may add pickup stages.
                -- Completed or ineligible players contribute no stages.
                if #stages > 0 then
                    found = true
                    local immediate = stages[1].kind == "t"
                    for index, stop in ipairs(stages) do
                        if stop.mapID ~= mapID then otherMaps = otherMaps + #stages - index + 1; break end
                        local phase = immediate and 1 or (stop.kind == "a" and 2 or (stop.kind == "q" and 3 or 4))
                        if stop.kind ~= "a" or pickup then
                            local key = record.id .. ":" .. stop.kind .. ":" .. math.floor(stop.x * 100000) .. ":" .. math.floor(stop.y * 100000)
                            local old = seen[phase][key]
                            if not old then
                                stop.memberKey, stop.forPlayer = person.key, person.name
                                seen[phase][key] = stop; phases[phase][#phases[phase] + 1] = stop
                            else old.forPlayer = old.forPlayer .. ", " .. person.name end
                        end
                    end
                elseif person.key == ns.self and ns.active[record.id]
                    or ns.members[person.key] and ns.members[person.key].active and ns.members[person.key].active[record.id] then
                    unavailable = true
                end
            end
        end
        if unavailable then missing = missing + 1 end
        if not found and ns.CurrentQuestPending(record.id) then partial = true end
        local quest = ns.CatalogueQuest(record.id)
        if quest and quest.objectiveLocationsIncomplete and found then
            partial = true; unknownObjectives = unknownObjectives + 1
        end
    end
    local position = ns.PlayerPoint(mapID)
    if not ns.profile or ns.profile.mapID ~= mapID then position = nil end
    local stops, last, ready = {}, position, #phases[1]
    local distance, physical = routeMetric(mapID)
    local function closest(remaining)
        local best, cost = 1, math.huge
        for index, stop in ipairs(remaining) do
            local value = last and distance(last, stop) or index
            if value < cost then best, cost = index, value end
        end
        return best, cost
    end
    for phase = 2, 4 do
        local remaining = phases[phase]
        while (#remaining > 0 or #phases[1] > 0) and #stops < 20 do
            local best, nextDistance = closest(remaining)
            local readyIndex, readyDistance = closest(phases[1])
            local nearbyReady = phases[1][readyIndex] and (not last
                or ns.NormalizedDistance(last, phases[1][readyIndex]) <= ns.Option("circuitRadius") * 0.45)
            if #phases[1] > 0 and (#remaining == 0 and phase == 4 or nearbyReady or readyDistance <= nextDistance and #remaining > 0) then
                last = table.remove(phases[1], readyIndex)
            elseif #remaining > 0 then last = table.remove(remaining, best)
            else break
            end
            stops[#stops + 1] = last
        end
    end
    improveObjectiveRuns(stops, position, distance)
    local yards, previous = physical and 0 or nil, position
    for _, stop in ipairs(stops) do if previous and yards then yards = yards + distance(previous, stop) end; previous = stop end
    local limited = #phases[1] + #phases[2] + #phases[3] + #phases[4]
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops, origin = includeOrigin and position or nil,
        focusKey = ns.self, ready = ready, missing = missing, otherMaps = otherMaps, limited = limited, unknownObjectives = unknownObjectives,
        walkingYards = yards,
        partial = partial or missing > 0 or otherMaps > 0 or limited > 0}
end

function ns.BundleQuestFinished(guide, id)
    if not guide.pickupIDs or not guide.pickupIDs[id] then return ns.CurrentQuestFinished(id) end
    for _, person in ipairs(ns.PartyProfiles()) do
        if not person.synced then return false end
        local active = person.key == ns.self and ns.active or (ns.members[person.key] and ns.members[person.key].active)
        if active and active[id] then return false end
        if ns.CatalogueCompletion(person.key, id) ~= true
            and ns.CatalogueAllowed(id, person.profile, person.key) ~= false then return false end
    end
    return true
end

function ns.CurrentQuestChoices()
    local ids, waiting = {}, 0
    for _, person in ipairs(ns.PartyProfiles()) do
        if not person.synced then waiting = waiting + 1
        else
            local active = person.key == ns.self and ns.active or (ns.members[person.key] and ns.members[person.key].active)
            for id in pairs(active or {}) do
                if not ns.IsProfessionQuest(id) and not ns.IsRepeatableQuest(id) and not ns.GuideQuestSkipped(id) then ids[id] = true end
            end
        end
    end
    local ordered = {}; for id in pairs(ids) do ordered[#ordered + 1] = id end; table.sort(ordered)
    if #ordered == 0 then
        ns.currentGuideStatus = waiting > 0 and "Waiting for friends' quest logs before suggesting new pickups." or nil
        return waiting > 0 and {} or nil
    end
    local groups, choices = {}, {}
    local currentMap = ns.profile and ns.profile.mapID or 0
    local liveRecords = ns.RouteRecords()
    for _, id in ipairs(ordered) do
        local record = ns.CatalogueRecord(id) or liveRecords[id] or {id = id, title = ns.QuestTitle(id),
            level = ns.questLevels[id] or 0, source = "p", lineID = 0, lineName = "", npc = "", mapID = currentMap}
        local maps = {}
        for _, person in ipairs(currentPeople(id)) do
            local stages = ns.RouteStages(record, person.key)
            maps[stages[1] and stages[1].mapID or currentMap] = true
        end
        for mapID in pairs(maps) do
            local group = groups[mapID]
            if not group then
                group = {key = "current:" .. mapID, mode = "current", mapID = mapID, records = {}, focusKey = ns.self,
                    kind = "Current party quests", zone = ns.MapName(mapID), profilesReady = waiting == 0}
                groups[mapID] = group
            end
            group.records[#group.records + 1] = record
        end
    end
    for _, group in pairs(groups) do
        local route = ns.BuildCurrentQuestRoute(group, true)
        if ns.Option("nearbyPickups") and group.profilesReady and group.mapID == currentMap then
            ns.AddNearbyPickups(group, route)
            if group.mode == "bundle" then route = ns.BuildCurrentQuestRoute(group, true) end
        end
        group.nextStop, group.knownStops, group.missingStops = route.stops[1], #route.stops, route.missing
        group.hasPoint, group.ready = #route.stops > 0, route.ready
        group.title = route.ready > 0 and route.stops[1] and route.stops[1].kind == "t"
            and ("Turn in " .. route.ready .. " ready quest" .. (route.ready == 1 and "" or "s")) or "Finish our current quests"
        group.target = group.records[1]
        for _, record in ipairs(group.records) do if group.nextStop and record.id == group.nextStop.id then group.target = record; break end end
        group.level = group.target.level > 0 and group.target.level or nil
        group.priority = (group.mapID == currentMap and 10000 or 0) + (group.hasPoint and 2000 or 0) + route.ready * 100
        group.reason = "From your party's quest logs. Nearby ready turn-ins first; finish local work before long delivery detours. No new quest pickups."
        if group.mode == "bundle" then
            group.kind = "Current quests + nearby pickups"
            if route.ready == 0 or not route.stops[1] or route.stops[1].kind ~= "t" then group.title = "Current quests + nearby pickups" end
            local names = {}
            for _, record in ipairs(group.records) do
                if group.pickupIDs[record.id] then names[#names + 1] = record.title .. (record.npc ~= "" and (" at " .. record.npc) or "") end
            end
            group.reason = "Nearby ready turn-ins first. Nearby pickups: " .. table.concat(names, "; ")
                .. ". Combine mapped objectives, then group later turn-ins."
        end
        if route.unknownObjectives > 0 then group.reason = group.reason .. " " .. route.unknownObjectives .. " quest(s) have incomplete objective locations; those steps need the game tracker." end
        if waiting > 0 then group.reason = group.reason .. " " .. waiting .. " friend(s) still need a refreshed quest snapshot." end
        if route.missing > 0 then group.reason = group.reason .. " " .. route.missing .. " active quest(s) have no verified destination yet." end
        if group.mapID ~= currentMap then group.reason = group.reason .. " Travel to " .. group.zone .. " for accepted party quests after the current-zone work." end
        group.destination = group.nextStop and group.nextStop.label or "Check active quest destinations"
        choices[#choices + 1] = group
    end
    table.sort(choices, function(a, b) if a.priority ~= b.priority then return a.priority > b.priority end; return a.key < b.key end)
    ns.currentGuideStatus = ns.Option("nearbyPickups") and "Quest-log routes include useful nearby pickups." or "Quest-log routes use accepted quests only."
    return choices
end

function ns.IsProfessionQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and quest.categoryPath and string.sub(quest.categoryPath, 1, 12) == "professions/" or false
end

function ns.IsDungeonQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and (quest.questType == "Dungeon" or (quest.categoryPath and string.sub(quest.categoryPath, 1, 9) == "dungeons/")) or false
end

function ns.IsClassQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and ((quest.classMask and quest.classMask > 0)
        or (quest.categoryPath and string.sub(quest.categoryPath, 1, 8) == "classes/")) or false
end

function ns.ClassQuestLabel(id)
    if not ns.IsClassQuest(id) then return nil end
    local quest = ns.CatalogueQuest(id)
    if quest.categoryPath and string.sub(quest.categoryPath, 1, 8) == "classes/" then
        return "Class quest: " .. string.gsub(string.sub(quest.categoryPath, 9), "^%l", string.upper)
    end
    local classes, names = {}, {[1] = "Warrior", [2] = "Paladin", [3] = "Hunter", [4] = "Rogue", [5] = "Priest",
        [6] = "Death Knight", [7] = "Shaman", [8] = "Mage", [9] = "Warlock", [10] = "Monk", [11] = "Druid", [12] = "Demon Hunter", [13] = "Evoker"}
    if bit and type(bit.band) == "function" and type(bit.lshift) == "function" then
        for id, name in pairs(names) do if bit.band(quest.classMask or 0, bit.lshift(1, id - 1)) ~= 0 then classes[#classes + 1] = name end end
    end
    table.sort(classes)
    return #classes > 0 and ("Class quest: " .. table.concat(classes, ", ")) or "Class quest • restriction needs checking"
end

function ns.LevelingQuestEnabled(id)
    return not ns.IsProfessionQuest(id) and not ns.IsDungeonQuest(id) and not ns.IsRepeatableQuest(id) and not ns.GuideQuestSkipped(id)
        and (not ns.IsClassQuest(id) or ns.Option("classQuests"))
        and ns.LevelingValue(id) ~= false
end

function ns.IsRepeatableQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and quest.repeatable == true or false
end

function ns.PlayerPoint(mapID)
    local point = C_Map and ns.ReadPublic(C_Map.GetPlayerMapPosition, mapID, "player")
    local x, y
    if point then x, y = ns.ReadPublic(point.GetXY, point) end
    if type(x) == "number" and type(y) == "number" and x >= 0 and x <= 1 and y >= 0 and y <= 1 then
        return {mapID = mapID, x = x, y = y}
    end
end

function ns.NormalizedDistance(a, b)
    if not a or not b or a.mapID ~= b.mapID then return math.huge end
    return math.sqrt(((a.x - b.x) * 1.5)^2 + (a.y - b.y)^2)
end

function ns.WalkingDistance(mapID, a, b, metrics)
    local width, height
    local cached = metrics and metrics[mapID]
    if cached then width, height = cached[1], cached[2]
    else
        if C_Map then width, height = ns.ReadPublic(C_Map.GetMapWorldSize, mapID) end
        if metrics then metrics[mapID] = {width, height} end
    end
    if type(width) == "number" and type(height) == "number" and width > 0 and height > 0
        and width < 1000000 and height < 1000000 then
        return math.sqrt(((a.x - b.x) * width)^2 + ((a.y - b.y) * height)^2)
    end
end

local indexedCatalogue, maps
local function mapRecords(mapID)
    if ns.catalogue ~= indexedCatalogue then
        maps, indexedCatalogue = {}, ns.catalogue
        for id, quest in pairs(ns.catalogue.quests) do
            local start = quest.starts and quest.starts[1]
            local finish = quest.ends and quest.ends[1]
            local map = finish and finish.mapID or (start and start.mapID)
            if map then maps[map] = maps[map] or {}; maps[map][#maps[map] + 1] = id end
        end
        for _, ids in pairs(maps) do table.sort(ids) end
    end
    return maps[mapID] or {}
end

local function focusPlayer()
    local key, level, ready = ns.self, ns.profile and ns.profile.level, true
    for _, person in ipairs(ns.PartyProfiles()) do
        local p = person.profile
        if not person.synced or not p or not p.level or p.level <= 0 then ready = false
        elseif not level or level <= 0 or p.level < level or (p.level == level and person.key < key) then key, level = person.key, p.level end
    end
    return key, level or 0, ready
end

local function distanceToTrip(point, route)
    local best, last = math.huge, route.origin
    for _, stop in ipairs(route.stops) do
        best = math.min(best, ns.NormalizedDistance(point, stop))
        if last and last.mapID == point.mapID and stop.mapID == point.mapID then
            local dx, dy = (stop.x - last.x) * 1.5, stop.y - last.y
            local length = dx * dx + dy * dy
            if length > 0 then
                local t = math.max(0, math.min(1, (((point.x - last.x) * 1.5) * dx + (point.y - last.y) * dy) / length))
                best = math.min(best, ns.NormalizedDistance(point, {mapID = point.mapID,
                    x = last.x + (stop.x - last.x) * t, y = last.y + dy * t}))
            end
        end
        last = stop
    end
    return best
end

function ns.AddNearbyPickups(group, route)
    local key, level, ready = focusPlayer()
    if not ready or level <= 0 or #route.stops == 0 or #route.stops >= 20 then return end
    local selected, candidates, radius = {}, {}, ns.Option("circuitRadius")
    for _, record in ipairs(group.records) do selected[record.id] = true end
    for _, id in ipairs(mapRecords(group.mapID)) do
        local quest = ns.CatalogueQuest(id)
        if not selected[id] and ns.LevelingQuestEnabled(id) and (quest.level or 0) <= level + 2
            and (quest.minLevel or 0) <= level then
            local record = ns.CatalogueRecord(id)
            local stages = ns.PartyRouteStages(record, key)
            local first, finish = stages[1], quest.ends and quest.ends[1]
            local valid = first and first.kind == "a" and first.mapID == group.mapID
                and finish and finish.mapID == group.mapID
                and distanceToTrip(first, route) <= radius * 0.45
                and distanceToTrip(finish, route) <= radius * 0.45
            local detour = valid and distanceToTrip(first, route) or math.huge
            for _, stop in ipairs(stages) do
                local distance = distanceToTrip(stop, route)
                if stop.mapID ~= group.mapID or distance > radius then valid = false end
                detour = math.max(detour, distance)
            end
            if valid then candidates[#candidates + 1] = {record = record, stages = #stages, detour = detour,
                incomplete = quest.objectiveLocationsIncomplete == true} end
        end
    end
    table.sort(candidates, function(a, b)
        -- Prefer complete location data, then shorter detours. XP cannot
        -- justify a distant pickup or objective area.
        if a.incomplete ~= b.incomplete then return not a.incomplete end
        if a.detour ~= b.detour then return a.detour < b.detour end
        return a.record.id < b.record.id
    end)
    local added, stops, incomplete = {}, #route.stops, 0
    for _, candidate in ipairs(candidates) do
        if #added < ns.Option("circuitLimit") and #group.records < 20 and stops + candidate.stages <= 20
            and (not candidate.incomplete or incomplete < 2) then
            group.records[#group.records + 1] = candidate.record
            group.pickupIDs = group.pickupIDs or {}; group.pickupIDs[candidate.record.id] = true
            added[#added + 1], stops = candidate.record.id, stops + candidate.stages
            if candidate.incomplete then incomplete = incomplete + 1 end
        end
    end
    if #added > 0 then
        group.mode = "bundle"
        local ids = {}; for _, record in ipairs(group.records) do ids[#ids + 1] = record.id end; table.sort(ids)
        table.sort(added)
        -- An accepted pickup changes its role in new recommendations. Keep an
        -- explicitly selected bundle stable so other friends still get pickups.
        group.key = "bundle:" .. group.mapID .. ":" .. table.concat(ids, ",") .. ":" .. table.concat(added, ",")
    end
end

function ns.LocalCircuitChoices()
    local mapID = ns.profile and ns.profile.mapID or 0
    local key, level, ready = focusPlayer()
    if mapID <= 0 or level <= 0 or not ready then return {} end
    local position, candidates = ns.PlayerPoint(mapID), {}
    local radius = ns.Option("circuitRadius")
    for _, id in ipairs(mapRecords(mapID)) do
        local quest = ns.CatalogueQuest(id)
        if ns.LevelingQuestEnabled(id) and not quest.objectiveLocationsIncomplete
            and (quest.level or 0) <= level + 2 then
            local record = ns.CatalogueRecord(id)
            local stages = ns.PartyRouteStages(record, key)
            local hasObjective, valid = false, #stages > 0
            local finish = quest.ends and quest.ends[1]
            for _, stop in ipairs(stages) do
                if stop.mapID ~= mapID or ns.NormalizedDistance(stop, finish) > radius * 2 then valid = false end
                if stop.kind == "q" then hasObjective = true end
            end
            if valid and finish and (hasObjective or stages[1].kind == "t") then
                local first = quest.starts and quest.starts[1] or stages[1]
                if first.mapID == mapID then
                    local nearby = not position or ns.NormalizedDistance(position, first) <= radius * 1.8
                    if nearby then candidates[#candidates + 1] = {record = record, first = first, finish = finish, stages = stages,
                        value = math.max(100, quest.xp or 300) / (1 + math.max(0, level - (quest.level or level) - 3)), xp = quest.xp} end
                end
            end
        end
    end
    table.sort(candidates, function(a, b)
        local da = position and ns.NormalizedDistance(position, a.first) or 0
        local db = position and ns.NormalizedDistance(position, b.first) or 0
        if da ~= db then return da < db end
        return a.record.id < b.record.id
    end)
    local choices, signatures = {}, {}
    -- Bound the search by local candidates, independent of global catalogue size.
    for anchorIndex = 1, math.min(40, #candidates) do
        local anchor, available = candidates[anchorIndex], {}
        for index = 1, math.min(80, #candidates) do
            local candidate = candidates[index]
            if ns.NormalizedDistance(candidate.finish, anchor.finish) <= radius * 0.45
                and ns.NormalizedDistance(candidate.first, anchor.first) <= radius then
                local walking = ns.NormalizedDistance(candidate.stages[1], anchor.finish)
                available[#available + 1] = {candidate = candidate, priority = candidate.value / (0.04 + walking)}
            end
        end
        table.sort(available, function(a, b)
            if a.priority ~= b.priority then return a.priority > b.priority end
            return a.candidate.record.id < b.candidate.record.id
        end)
        local records, ids, xp, unknown, score, stopCount = {}, {}, 0, 0, 0, 0
        for index = 1, #available do
            local c = available[index].candidate
            if #records < ns.Option("circuitLimit") and stopCount + #c.stages <= 20 then
                records[#records + 1], ids[#ids + 1] = c.record, c.record.id
                if c.xp then xp = xp + c.xp else unknown = unknown + 1 end
                score, stopCount = score + c.value, stopCount + #c.stages
            end
        end
        table.sort(ids)
        local signature = table.concat(ids, ",")
        if #records > 0 and not signatures[signature] then
            signatures[signature] = true
            local title = "Local circuit • " .. #records .. " quest" .. (#records > 1 and "s" or "")
            local hub = anchor.finish.name or ns.MapName(mapID)
            local group = {key = "circuit:" .. mapID .. ":" .. signature, title = title, kind = "Local XP circuit", mode = "circuit",
                mapID = mapID, records = records, target = records[1], focusKey = key, zone = ns.MapName(mapID), profilesReady = true,
                lowest = level, highest = level, xp = xp, xpUnknown = unknown, hasPoint = true, level = level, shared = 0,
                priority = 1000 + score / 50 - (position and ns.NormalizedDistance(position, anchor.first) * 400 or 0),
                reason = "Collect nearby quests, work their objectives, then return together around " .. hub .. ".",
                destination = "Finish in one local turn-in circuit."}
            local plan = ns.BuildCircuitRoute(group, true)
            group.nextStop, group.knownStops, group.missingStops = plan.stops[1], #plan.stops, plan.missing
            group.reason = group.reason .. " Listed quest XP: " .. xp .. (unknown > 0 and (" + " .. unknown .. " unknown rewards") or "") .. "; actual XP varies by level."
            if plan.walkingYards then group.reason = group.reason .. " Approx. " .. math.ceil(plan.walkingYards / 7 / 60) .. " walking minutes before terrain/combat." end
            choices[#choices + 1] = group
        end
    end
    table.sort(choices, function(a, b) if a.priority ~= b.priority then return a.priority > b.priority end; return a.key < b.key end)
    local result = {}
    for index = 1, math.min(3, #choices) do result[#result + 1] = choices[index] end
    return result
end

function ns.BuildCircuitRoute(guide, includeOrigin)
    local phases, missing, partial = {a = {}, q = {}, t = {}}, 0, false
    local mapID = guide.mapID or (guide.target and guide.target.mapID) or 0
    for _, record in ipairs(guide.records) do
        local stages = guide.personal and ns.RouteStages(record, ns.self) or ns.PartyRouteStages(record, guide.focusKey)
        if #stages == 0 then missing = missing + 1 end
        for _, stop in ipairs(stages) do
            if stop.mapID == mapID then phases[stop.kind][#phases[stop.kind] + 1] = stop else partial = true end
        end
    end
    local position = includeOrigin and ns.PlayerPoint(mapID) or nil
    local stops, last, yards = {}, position, position and 0 or nil
    for _, kind in ipairs({"a", "q", "t"}) do
        local remaining = phases[kind]
        while #remaining > 0 and #stops < 20 do
            local best, distance = 1, math.huge
            for index, stop in ipairs(remaining) do
                local d = last and ns.NormalizedDistance(last, stop) or index
                if d < distance then best, distance = index, d end
            end
            local stop = table.remove(remaining, best)
            if last then
                local length = ns.WalkingDistance(mapID, last, stop)
                if length and yards ~= nil then yards = yards + length else yards = nil end
            end
            stops[#stops + 1], last = stop, stop
        end
    end
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops, origin = position, focusKey = guide.focusKey,
        missing = missing, otherMaps = 0, limited = #phases.a + #phases.q + #phases.t, partial = partial, walkingYards = yards}
end
