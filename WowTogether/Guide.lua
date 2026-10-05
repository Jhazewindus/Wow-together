local addonName, ns = ...

local localRecords, traffic, profileTraffic = {}, {}, nil
local requestedMap
local MAX_RECORDS = 96

local function integer(value, maximum)
    return ns.Public(value) and type(value) == "number" and value >= 0
        and value <= (maximum or 2147483647) and value == math.floor(value)
end
ns.GuideInteger = integer

local function text(value, limit)
    value = ns.SafeTitle(value)
    if not value then return "" end
    -- Preserve UTF-8 by dropping a partial final character after a byte bound.
    if #value <= limit then return value end
    local cut = limit
    while cut > 0 do
        local byte = string.byte(value, cut + 1)
        if not byte or byte < 128 or byte >= 192 then break end
        cut = cut - 1
    end
    return string.sub(value, 1, cut)
end

local function read(fn, ...)
    if type(fn) ~= "function" then return nil end
    local okay, value = pcall(fn, ...)
    if not okay then ns.guideReadError = "A read-only guide query failed; check this beta build."; return nil end
    return ns.Public(value) and value or nil
end

local function count(records)
    local total = 0
    for _ in pairs(records) do total = total + 1 end
    return total
end

function ns.MapName(mapID)
    if C_Map and type(C_Map.GetMapInfo) == "function" and integer(mapID) and mapID > 0 then
        local info = read(C_Map.GetMapInfo, mapID)
        if type(info) == "table" then
            local name = text(info.name, 60)
            if name ~= "" then return name end
        end
    end
    return mapID and mapID > 0 and ("Map " .. mapID) or "Location not learned yet"
end

function ns.ReadProfile()
    local level = read(UnitLevel, "player")
    local faction = read(UnitFactionGroup, "player")
    local map = C_Map and read(C_Map.GetBestMapForUnit, "player")
    local zone = read(GetZoneText)
    local function identity(fn)
        if type(fn) ~= "function" then return 0 end
        local okay, _, _, id = pcall(fn, "player")
        return okay and integer(id, 255) and id or 0
    end
    ns.profile = {level = integer(level, 255) and level or 0,
        faction = (faction == "Horde" or faction == "Alliance" or faction == "Neutral") and faction or "Unknown",
        mapID = integer(map, 1000000) and map or 0, zone = text(zone, 40), classID = identity(UnitClass), raceID = identity(UnitRace)}
end

function ns.InitializeGuide()
    local _, build = GetBuildInfo()
    build = ns.Public(build) and tostring(build) or "unknown"
    ns.db.guideBuilds = type(ns.db.guideBuilds) == "table" and ns.db.guideBuilds or {}
    ns.db.guideBuilds[build] = type(ns.db.guideBuilds[build]) == "table" and ns.db.guideBuilds[build] or {}
    ns.guideObservations = ns.db.guideBuilds[build]
    for id, record in pairs(ns.guideObservations) do
        if integer(id) and id > 0 and type(record) == "table" and record.id == id
            and integer(record.mapID, 1000000) and record.mapID > 0 and type(record.npc) == "string"
            and type(record.title) == "string" and type(record.lineName) == "string" and integer(record.lineID)
            and integer(record.level, 255) and record.source == "n" and type(record.x) == "number"
            and type(record.y) == "number" and record.x >= 0 and record.x <= 1 and record.y >= 0 and record.y <= 1
            and count(localRecords) < MAX_RECORDS then
            localRecords[id] = record
        end
    end
    ns.ReadProfile()
    ns.ReadGuide()
    if C_QuestLine and type(C_QuestLine.GetAvailableQuestLines) == "function" then
        ns.On("QUESTLINE_UPDATE", function() ns.ReadGuide(); ns.ScheduleSync(); ns.Refresh() end)
    end
end

local function merge(record)
    if not integer(record.id) or record.id <= 0 then return end
    local previous = localRecords[record.id]
    if not previous and count(localRecords) >= MAX_RECORDS then return end
    if previous then
        for _, key in ipairs({"npc", "title", "lineName"}) do
            if not record[key] or record[key] == "" then record[key] = previous[key] end
        end
        if not record.level or record.level <= 0 then record.level = previous.level end
        if not record.lineID or record.lineID == 0 then record.lineID = previous.lineID end
        if (previous.source == "n" and record.source ~= "n") or (previous.source == "l" and record.source == "p") then
            record.mapID, record.x, record.y, record.source = previous.mapID, previous.x, previous.y, previous.source
        end
    end
    localRecords[record.id] = record
end

local function lineRecord(info, mapID)
    if not ns.Public(info) or type(info) ~= "table" then return end
    local id, lineID = info.questID, info.questLineID
    if not integer(id) or id <= 0 or not integer(lineID) then return end
    if not ns.Public(info.isHidden) or info.isHidden == true then return end
    local x, y = info.x, info.y
    local source = "p"
    -- x/y belong to the map used for this query. A startMapID can refer to
    -- another map and must not be paired with coordinates from this one.
    local targetMap = integer(mapID, 1000000) and mapID or 0
    if ns.Public(x) and ns.Public(y) and type(x) == "number" and type(y) == "number"
        and x >= 0 and x <= 1 and y >= 0 and y <= 1 then source = "l" else x, y = 0, 0 end
    local level = C_QuestLog and read(C_QuestLog.GetQuestDifficultyLevel, id)
    merge({id = id, title = text(info.questName, 60), lineID = lineID,
        lineName = text(info.questLineName, 50), mapID = targetMap, x = x, y = y,
        level = integer(level, 255) and level or 0, npc = "", source = source})
end

function ns.ReadGuide()
    ns.ReadProfile()
    local mapID = ns.profile.mapID
    if C_QuestLine and mapID > 0 then
        if type(C_QuestLine.RequestQuestLinesForMap) == "function" and requestedMap ~= mapID then
            requestedMap = mapID
            read(C_QuestLine.RequestQuestLinesForMap, mapID)
        end
        local lines = read(C_QuestLine.GetAvailableQuestLines, mapID)
        if type(lines) == "table" then
            for index, info in ipairs(lines) do
                if index > 32 then break end
                lineRecord(info, mapID)
            end
        end
    end
    for id, title in pairs(ns.active or {}) do
        local info = C_QuestLine and read(C_QuestLine.GetQuestLineInfo, id, mapID > 0 and mapID or nil)
        if type(info) == "table" then lineRecord(info, mapID) end
        local level = ns.questLevels and ns.questLevels[id] or 0
        merge({id = id, title = text(title, 60), lineID = type(info) == "table" and integer(info.questLineID) and info.questLineID or 0,
            lineName = type(info) == "table" and text(info.questLineName, 50) or "", mapID = 0,
            x = 0, y = 0, level = level, npc = "", source = "p"})
    end
    if ns.ReadRouteLocations then ns.ReadRouteLocations() end
    if ns.ReadProgress then ns.ReadProgress() end
    if ns.UpdateNPCHints then ns.UpdateNPCHints() end
end

function ns.ObserveQuestGiver(quests)
    if not ns.profile then ns.ReadProfile() end
    local name, surname
    if type(UnitName) == "function" then name, surname = UnitName("npc") end
    if not ns.Public(name) or not ns.Public(surname) or type(name) ~= "string" then return end
    local npc = text(name .. (type(surname) == "string" and surname ~= "" and (" " .. surname) or ""), 40)
    if npc == "" then return end
    ns.ReadProfile()
    local mapID = ns.profile.mapID
    local point = C_Map and mapID > 0 and read(C_Map.GetPlayerMapPosition, mapID, "player")
    if not point or not ns.Public(point) or type(point.GetXY) ~= "function" then return end
    local x, y = point:GetXY()
    if not ns.Public(x) or not ns.Public(y) or type(x) ~= "number" or type(y) ~= "number"
        or x < 0 or x > 1 or y < 0 or y > 1 then return end
    for _, quest in ipairs(quests) do
        if ns.Public(quest) and type(quest) == "table" then
            local id = quest.questID
            if integer(id) and id > 0 then
                local info = C_QuestLine and read(C_QuestLine.GetQuestLineInfo, id, mapID)
                if type(info) == "table" then lineRecord(info, mapID) end
                local level = quest.questLevel
                if not integer(level, 255) then level = C_QuestLog and read(C_QuestLog.GetQuestDifficultyLevel, id) end
                merge({id = id, title = text(quest.title, 60), lineID = 0, lineName = "", mapID = mapID,
                    x = x, y = y, npc = npc, source = "n", level = integer(level, 255) and level or 0})
                ns.guideObservations[id] = localRecords[id]
            end
        end
    end
    ns.SendGuideContext()
    ns.SendCompletion()
    ns.Refresh()
end

local function allRecords()
    local records = {}
    for id, record in pairs(localRecords) do records[id] = record end
    local names = {}
    for name in pairs(ns.members) do names[#names + 1] = name end
    table.sort(names)
    for _, name in ipairs(names) do
        local member = ns.members[name]
        for id, record in pairs(member.guideRecords or {}) do
            local old = records[id]
            if not old or (old.source ~= "n" and record.source == "n") then records[id] = record end
        end
    end
    if ns.RouteRecords then
        for id, record in pairs(ns.RouteRecords()) do
            local old = records[id]
            if not old then records[id] = record
            elseif old.mapID == 0 then
                local copy = {}
                for key, value in pairs(old) do copy[key] = value end
                copy.mapID, copy.x, copy.y = record.mapID, record.x, record.y
                records[id] = copy
            end
        end
    end
    if ns.CatalogueGuideRecords then
        for id, record in pairs(ns.CatalogueGuideRecords()) do
            local old = records[id]
            if not old then records[id] = record
            else
                local copy = {}
                for key, value in pairs(old) do copy[key] = value end
                copy.seriesRoot, copy.seriesName, copy.seriesPosition = record.seriesRoot, record.seriesName, record.seriesPosition
                if copy.mapID == 0 then copy.mapID = record.mapID end
                records[id] = copy
            end
        end
    end
    if ns.LevelingQuestEnabled then for id in pairs(records) do if not ns.LevelingQuestEnabled(id) then records[id] = nil end end end
    return records
end

function ns.GuideQuestIDs()
    local ids = {}
    for id in pairs(allRecords()) do ids[id] = true end
    return ids
end

function ns.GuideTitle(id)
    local record = allRecords()[id]
    return record and record.title ~= "" and record.title or nil
end

function ns.ResetGuideTraffic()
    traffic, profileTraffic = {}, nil
    if ns.ResetRouteTraffic then ns.ResetRouteTraffic() end
    if ns.ResetCatalogueTraffic then ns.ResetCatalogueTraffic() end
    if ns.ResetProgressTraffic then ns.ResetProgressTraffic() end
end

function ns.SendGuideContext(force)
    if not ns.QueueMessage then return end
    ns.ReadProfile()
    local faction = ns.profile.faction == "Horde" and 2 or (ns.profile.faction == "Alliance" and 1 or 0)
    local payload = "1|P|" .. ns.profile.level .. "|" .. faction .. "|" .. ns.profile.mapID .. "|" .. ns.profile.zone
    if ns.profile.classID > 0 or ns.profile.raceID > 0 then payload = payload .. "|" .. ns.profile.classID .. "|" .. ns.profile.raceID end
    if (force or payload ~= profileTraffic) and ns.QueueMessage(payload) then profileTraffic = payload end
    local ids = {}
    for id in pairs(localRecords) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do
        local record = localRecords[id]
        local message = table.concat({"1", "G", id, record.lineID or 0, record.mapID or 0,
            math.floor((record.x or 0) * 100000), math.floor((record.y or 0) * 100000), record.level or 0,
            record.source or "p", text(record.title, 60), text(record.lineName, 50), text(record.npc, 40)}, "|")
        if (force or traffic[id] ~= message) and ns.QueueMessage(message) then traffic[id] = message end
    end
end

function ns.ReceiveGuideMessage(message, sender)
    local level, faction, mapID, zone, classID, raceID = string.match(message, "^1|P|(%d+)|(%d+)|(%d+)|([^|]*)|(%d+)|(%d+)$")
    if not level then level, faction, mapID, zone = string.match(message, "^1|P|(%d+)|(%d+)|(%d+)|([^|]*)$") end
    if string.sub(message, 1, 4) == "1|P|" then
        level, faction, mapID = tonumber(level), tonumber(faction), tonumber(mapID)
        classID, raceID = tonumber(classID) or 0, tonumber(raceID) or 0
        if not integer(level, 255) or not integer(faction, 2) or not integer(mapID, 1000000)
            or not integer(classID, 255) or not integer(raceID, 255) or not zone or #zone > 40 then return true, false, "invalid character context" end
        ns.members[sender] = ns.members[sender] or {}
        ns.members[sender].profile = {level = level, faction = faction == 2 and "Horde" or (faction == 1 and "Alliance" or "Unknown"),
            mapID = mapID, zone = text(zone, 40), classID = classID, raceID = raceID}
        return true, true
    end
    if string.sub(message, 1, 4) ~= "1|G|" then return false end
    local id, lineID, targetMap, x, y, questLevel, source, title, lineName, npc =
        string.match(message, "^1|G|(%d+)|(%d+)|(%d+)|(%d+)|(%d+)|(%d+)|([nlp])|([^|]*)|([^|]*)|([^|]*)$")
    id, lineID, targetMap, x, y, questLevel = tonumber(id), tonumber(lineID), tonumber(targetMap), tonumber(x), tonumber(y), tonumber(questLevel)
    if not integer(id) or id <= 0 or not integer(lineID) or not integer(targetMap, 1000000)
        or not integer(x, 100000) or not integer(y, 100000) or not integer(questLevel, 255)
        or not title or #title > 60 or #lineName > 50 or #npc > 40 then return true, false, "invalid guide record" end
    ns.members[sender] = ns.members[sender] or {}
    local records = ns.members[sender].guideRecords or {}
    if not records[id] and count(records) >= MAX_RECORDS then return true, false, "guide record limit" end
    records[id] = {id = id, lineID = lineID, mapID = targetMap, x = x / 100000, y = y / 100000,
        level = questLevel, source = source, title = text(title, 60), lineName = text(lineName, 50), npc = text(npc, 40)}
    ns.members[sender].guideRecords = records
    ns.ScheduleSync()
    return true, true
end

function ns.PartyProfiles()
    local profiles = {{name = "You", key = ns.self, profile = ns.profile, synced = ns.questReady}}
    for _, name in ipairs(ns.partyNames or {}) do
        local member = ns.members[name]
        profiles[#profiles + 1] = {name = ns.MemberLabel(name), key = name,
            profile = member and member.profile, synced = member and member.active ~= nil and not member.syncPending}
    end
    return profiles
end

function ns.GuideChoices()
    ns.currentGuideStatus = nil
    if ns.Option("currentQuestsFirst") and ns.CurrentQuestChoices then
        local current = ns.CurrentQuestChoices()
        if current then return current end
    end
    local groups, profiles = {}, ns.PartyProfiles()
    local lowest, highest, lowName, lowKey, ready = nil, nil, nil, ns.self, true
    local factions = {}
    for _, person in ipairs(profiles) do
        local profile = person.profile
        if not person.synced or not profile or not profile.level or profile.level <= 0 then ready = false
        else
            if not lowest or profile.level < lowest or (profile.level == lowest and person.key < lowKey) then
                lowest, lowName, lowKey = profile.level, person.name, person.key
            end
            highest = math.max(highest or 0, profile.level)
            if profile.faction ~= "Unknown" then factions[profile.faction] = true end
        end
    end
    for _, record in pairs(allRecords()) do
        local key, kind, title
        if record.seriesRoot then key, kind, title = "series:" .. record.seriesRoot, "Questline", record.seriesName
        elseif record.lineID > 0 and record.lineName ~= "" then key, kind, title = "line:" .. record.lineID, "Questline", record.lineName
        elseif record.npc ~= "" and record.mapID > 0 then key, kind, title = "npc:" .. record.mapID .. ":" .. record.npc, "Quest hub", record.npc
        else key, kind, title = "progress:" .. (record.mapID or 0), "Current progress", "Current quest progress" end
        local group = groups[key]
        if not group then group = {key = key, title = title, kind = kind, records = {}}; groups[key] = group end
        group.records[#group.records + 1] = record
        local stages = ns.PartyRouteStages and ns.PartyRouteStages(record, lowKey)
        local stop = stages and stages[1]
        local focusProfile = lowKey == ns.self and ns.profile or (ns.members[lowKey] and ns.members[lowKey].profile)
        if stop and (not focusProfile or record.level == 0 or record.level <= focusProfile.level + 3) then
            local routeKey = "zone-route:" .. stop.mapID
            local routeGroup = groups[routeKey]
            if not routeGroup then
                routeGroup = {key = routeKey, title = ns.MapName(stop.mapID) .. " quest route", kind = "Zone route", records = {}}
                groups[routeKey] = routeGroup
            end
            routeGroup.records[#routeGroup.records + 1] = record
        end
    end
    local choices = ns.LocalCircuitChoices and ns.LocalCircuitChoices() or {}
    for _, group in pairs(groups) do
        table.sort(group.records, function(a, b)
            local function score(record)
                local active, completed, offered = 0, 0, 0
                for _, state in ipairs(ns.MemberStates(record.id)) do
                    if state.active then active = active + 1 end
                    if state.history == "completed" and not state.active and not state.offered then completed = completed + 1 end
                    if state.offered then offered = offered + 1 end
                end
                local result = active * 15 + offered * 12 - completed * 8
                if record.source == "n" then result = result + 8 elseif record.source == "l" then result = result + 4 end
                if lowest and record.level > 0 then
                    result = result - math.abs(record.level - lowest) * 3
                    if record.level > lowest + 2 then result = result - 60 end
                end
                return result
            end
            local as, bs = score(a), score(b)
            if as ~= bs then return as > bs end
            return a.id < b.id
        end)
        group.focusKey = lowKey
        local plan = ns.BuildGuideRoute and ns.BuildGuideRoute(group, false)
        if plan and #plan.stops > 0 then
            local nextID = plan.stops[1].id
            for _, record in ipairs(group.records) do if record.id == nextID then group.target = record; break end end
        end
        local target = group.target or group.records[1]
        local shared, finished = 0, 0
        for _, state in ipairs(ns.MemberStates(target.id)) do
            if state.active then shared = shared + 1 end
            if state.history == "completed" and not state.active and not state.offered then finished = finished + 1 end
        end
        local gap = ready and highest - lowest or nil
        local priority = shared * 20 + (target.source == "n" and 50 or (target.source == "l" and 35 or 0))
        local knownStops = plan and #plan.stops or 0
        priority = priority + (knownStops > 0 and 90 or -100) + math.min(6, knownStops) * 6
        if group.kind == "Questline" then priority = priority + 30 end
        if lowest and target.level > 0 then
            priority = priority - math.abs(target.level - lowest) * 4
            if target.level > lowest + 2 then priority = priority - 100 end
        end
        group.finished = finished == #profiles
        if group.finished then priority = priority - 200 end
        group.target, group.priority, group.mapID = target, priority, target.mapID
        if knownStops > 0 then group.mapID = plan.mapID end
        group.zone = ns.MapName(group.mapID)
        group.level = target.level > 0 and target.level or nil
        group.shared, group.profilesReady = shared, ready
        group.lowest, group.highest, group.lowName = lowest, highest, lowName
        group.catchup = ready and gap > math.max(4, math.floor(lowest * 0.4)) and shared < #profiles
        if group.finished then group.reason = "Every synced player completed this step."
        elseif not ready then group.reason = "Waiting for every party member's level and quest snapshot."
        elseif factions.Horde and factions.Alliance then group.reason = "Faction differences need checking before choosing a shared questline."
        elseif group.catchup then group.reason = "Party levels " .. lowest .. "–" .. highest .. ". Help the lower-level player " .. lowName .. " progress first."
        else group.reason = "Party levels " .. lowest .. "–" .. highest .. ". " .. shared .. " player(s) already have the next quest active." end
        if group.level and lowest and group.level > lowest + 2 then
            group.reason = group.reason .. " Quest level " .. group.level .. " is above their range."
        end
        group.destination = target.npc ~= "" and ("Talk to " .. target.npc)
            or (target.source == "l" and "Visit the client questline marker" or "Quest giver not learned yet")
        group.hasPoint = knownStops > 0
        group.knownStops, group.missingStops = knownStops, plan and plan.missing or #group.records
        group.nextStop = plan and plan.stops[1]
        if group.nextStop and group.nextStop.kind ~= "a" then group.destination = group.nextStop.label end
        local liveOnly = false
        for _, record in ipairs(group.records) do if not ns.CatalogueQuest(record.id) then liveOnly = true; break end end
        if knownStops > 0 or liveOnly then choices[#choices + 1] = group end
    end
    table.sort(choices, function(a, b)
        if a.priority ~= b.priority then return a.priority > b.priority end
        return a.key < b.key
    end)
    return choices
end

function ns.ShowGuideOnMap(guide)
    local route = guide and ns.BuildGuideRoute(guide, true)
    local first = route and route.stops[1]
    if not first then ns.guideAction = "This quest has no NPC or objective coordinates yet. View its details in the Quest library."; ns.Refresh(); return false end
    local blocked = type(InCombatLockdown) == "function" and InCombatLockdown()
    if not ns.Public(blocked) then return false end
    if blocked then
        ns.pendingGuideMap = guide
        ns.guideAction = "The map destination will open after combat."
        ns.Refresh()
        return false
    end
    if not C_Map or type(C_Map.SetUserWaypoint) ~= "function" or not UiMapPoint or type(UiMapPoint.CreateFromCoordinates) ~= "function" then
        ns.guideAction = "Map waypoint API missing on this build."; ns.Refresh(); return false
    end
    if type(C_Map.CanSetUserWaypointOnMap) == "function" then
        local allowed = C_Map.CanSetUserWaypointOnMap(first.mapID)
        if not ns.Public(allowed) or allowed ~= true then ns.guideAction = "This map does not support a user waypoint."; ns.Refresh(); return false end
    end
    local point = UiMapPoint.CreateFromCoordinates(first.mapID, first.x, first.y)
    local success = C_Map.SetUserWaypoint(point)
    if not ns.Public(success) or success ~= true then ns.guideAction = "The client did not accept the waypoint."; ns.Refresh(); return false end
    if not WorldMapFrame and C_AddOns and type(C_AddOns.LoadAddOn) == "function" then C_AddOns.LoadAddOn("Blizzard_WorldMap") end
    if WorldMapFrame and type(WorldMapFrame.SetMapID) == "function" and type(WorldMapFrame.Show) == "function" then
        WorldMapFrame:SetMapID(first.mapID)
        WorldMapFrame:Show()
        ns.ActivateRoute(guide, route)
        if ns.window then ns.window:Hide() end
    else ns.routeStats.status = "World map frame unavailable; the destination waypoint was set."
    end
    ns.guideAction = #route.stops .. " route stop(s): " .. first.label .. "."
    if ns.routeStats.lines == 0 then ns.guideAction = ns.guideAction .. " " .. ns.routeStats.status end
    ns.Refresh()
    return true
end

ns.On("PLAYER_REGEN_ENABLED", function()
    if ns.ReadProgress then ns.ReadProgress() end
    if ns.db then ns.ScheduleSync() end
    if ns.FlushRouteUpdates then ns.FlushRouteUpdates() end
    if ns.pendingGuideMap then local guide = ns.pendingGuideMap; ns.pendingGuideMap = nil; ns.ShowGuideOnMap(guide) end
    if ns.UpdateNPCHints then ns.UpdateNPCHints() end
end)
