local addonName, ns = ...

local catalogue, dungeons
local function titleCase(value) return string.gsub(string.gsub(value, "-", " "), "%f[%a]%l", string.upper) end
local function dungeonName(value)
    value = ns.SafeTitle(value)
    return value and string.gsub(string.lower(value), "[^%w]", "") or ""
end

function ns.DungeonGroups()
    if catalogue ~= ns.catalogue then
        catalogue, dungeons = ns.catalogue, {}
        local definitions = ns.dungeonData and ns.dungeonData.dungeons or {}
        local membership, names, areas = {}, {}, {}
        ns.dungeonUnassigned = 0
        for key, info in pairs(definitions) do
            dungeons[key] = {key = key, name = info.name, ids = {}, minLevel = 255,
                level = info.runLevelLow, maxLevel = info.runLevelHigh, definition = info}
            names[dungeonName(info.name)] = key
            for _, name in ipairs(info.aliases) do names[dungeonName(name)] = key end
            for _, area in ipairs(info.areaIDs) do areas[area] = key end
            for _, id in ipairs(info.questIDs) do
                membership[id] = membership[id] or {}; membership[id][key] = true
            end
        end
        for id, quest in pairs(ns.catalogue.quests) do
            local assigned = membership[id] or {}
            if ns.IsDungeonQuest(id) then
                local slug = quest.categoryPath and string.match(quest.categoryPath, "^dungeons/(.+)$")
                local key = slug or areas[quest.areaID] or names[dungeonName(ns.CatalogueZone(quest))]
                if not key and not ns.dungeonData then key = string.lower(ns.CatalogueZone(quest)) end
                if key then assigned[key] = true end
                if not next(assigned) then ns.dungeonUnassigned = ns.dungeonUnassigned + 1 end
            end
            for key in pairs(assigned) do
                local group = dungeons[key]
                if not group then
                    group = {key = key, name = titleCase(key), ids = {}, minLevel = 255, level = 255, maxLevel = 0}
                    dungeons[key] = group
                end
                group.ids[#group.ids + 1] = id
                group.minLevel = math.min(group.minLevel, quest.minLevel or quest.level or 255)
                if not group.definition then
                    group.level = math.min(group.level, quest.level or 255)
                    group.maxLevel = math.max(group.maxLevel, quest.level or 0)
                end
            end
        end
        for _, group in pairs(dungeons) do table.sort(group.ids) end
    end
    local result = {}
    for _, group in pairs(dungeons) do result[#result + 1] = group end
    table.sort(result, function(a, b) if a.level ~= b.level then return a.level < b.level end; return a.key < b.key end)
    return result
end

function ns.DungeonQuestRelevant(id)
    if ns.IsRepeatableQuest(id) or ns.IsProfessionQuest(id)
        or ns.IsClassQuest(id) and not ns.Option("classQuests") then return false end
    return ns.CatalogueIdentityAllowed(id, ns.profile)
end

function ns.DungeonCollectionReadiness(group)
    local result = {count = 0, pickupLevel = 0, maxLevel = 0, unknown = 0, unfinished = 0}
    for _, id in ipairs(group.ids) do
        local relevant, quest = ns.DungeonQuestRelevant(id), ns.CatalogueQuest(id)
        if relevant == nil then result.unknown = result.unknown + 1
        elseif relevant then
            result.count = result.count + 1
            if ns.GuideInteger(quest.minLevel, 255) then
                result.pickupLevel = math.max(result.pickupLevel, quest.minLevel)
            else result.unknown = result.unknown + 1 end
            result.maxLevel = math.max(result.maxLevel, quest.level or 0, quest.minLevel or 0)
            if ns.Completed(id) ~= true and not ns.GuideQuestSkipped(id) then result.unfinished = result.unfinished + 1 end
        end
    end
    local level = ns.profile and ns.profile.level
    result.levelReady = result.count > 0 and result.unknown == 0
        and ns.GuideInteger(level, 255) and level >= result.pickupLevel
    result.noticeKey = "dungeon-all-levels:" .. group.key .. ":" .. result.pickupLevel
    return result
end

function ns.DungeonCollectionSummary(group, readiness)
    if group.definition and #group.ids == 0 then return "Quest data not captured for this dungeon yet." end
    local result = readiness or ns.DungeonCollectionReadiness(group)
    if result.count == 0 then return "No matching regular quests for your character and settings." end
    if result.unknown > 0 then return "The full collection level is unknown; " .. result.unknown .. " pickup level or identity requirements need checking." end
    return "Full collection pickup level: " .. result.pickupLevel .. " • " .. result.count .. " regular quests for your character."
        .. (result.levelReady and " All known pickup-level requirements are met." or " Reach this level before collecting the full set.")
        .. " Prerequisite hand-ins and NPC offers still need checking."
end

function ns.DungeonOverviewSummary(group)
    local info = group.definition
    if not info then return "" end
    local place = info.locationHint
    if info.entrances[1] then place = ns.MapName(info.entrances[1].mapID) end
    return "Dungeon levels " .. info.runLevelLow .. "–" .. info.runLevelHigh
        .. (place and (" • " .. place) or "") .. "."
end

function ns.CrossMapDistance(a, b)
    if not C_Map or type(C_Map.GetWorldPosFromMapPos) ~= "function" or type(CreateVector2D) ~= "function" then return end
    local ac, ap = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, a.mapID, CreateVector2D(a.x, a.y))
    local bc, bp = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, b.mapID, CreateVector2D(b.x, b.y))
    if not ns.GuideInteger(ac) or ac ~= bc or not ap or not bp then return end
    local ax, ay = ns.ReadPublic(ap.GetXY, ap)
    local bx, by = ns.ReadPublic(bp.GetXY, bp)
    if type(ax) == "number" and type(ay) == "number" and type(bx) == "number" and type(by) == "number" then
        return math.sqrt((ax - bx)^2 + (ay - by)^2)
    end
end

function ns.DungeonEntrance(group)
    local recorded = ns.db.dungeonEntrances and ns.db.dungeonEntrances[group.key]
    if ns.ValidTravelPoint(recorded) then return recorded end
    local published = group.definition and group.definition.entrances or {}
    local maps = {[ns.profile and ns.profile.mapID or 0] = true}
    for _, point in ipairs(published) do if ns.ValidTravelPoint(point) then maps[point.mapID] = true end end
    for _, id in ipairs(group.ids) do
        local quest = ns.CatalogueQuest(id)
        for _, point in ipairs(quest.starts or {}) do maps[point.mapID] = true end
    end
    local ordered = {}; for id in pairs(maps) do if id > 0 then ordered[#ordered + 1] = id end end; table.sort(ordered)
    for _, id in ipairs(C_Map and type(C_Map.GetMapLinksForMap) == "function" and ordered or {}) do
        local links = ns.ReadPublic(C_Map.GetMapLinksForMap, id)
        if type(links) == "table" then
            for index, link in ipairs(links) do
                if index > 100 then break end
                if ns.Public(link) and type(link) == "table" then
                    local name, position = ns.SafeTitle(link.name), ns.Public(link.position) and link.position
                    local matches = name and dungeonName(name) == dungeonName(group.name)
                    for _, alias in ipairs(group.definition and group.definition.aliases or {}) do
                        if name and dungeonName(name) == dungeonName(alias) then matches = true end
                    end
                    if matches and position then
                        local x, y = ns.ReadPublic(position.GetXY, position)
                        if ns.ValidTravelPoint({mapID = id, x = x, y = y}) then
                            return {mapID = id, x = x, y = y, name = group.name, source = "Client map entrance link"}
                        end
                    end
                end
            end
        end
    end
    -- A captured entrance area remains usable when the beta has no public map
    -- link. Return a copy; character recording must not mutate shipped facts.
    for _, point in ipairs(published) do
        if ns.ValidTravelPoint(point) then
            local result = {}; for key, value in pairs(point) do result[key] = value end
            return result
        end
    end
end

function ns.RecordDungeonEntrance(group)
    local point = ns.PlayerPoint(ns.profile.mapID)
    if not point then ns.guideAction = "Your map position is unavailable."; ns.Refresh(); return end
    ns.db.dungeonEntrances = ns.db.dungeonEntrances or {}
    point.name, point.source = group.name, "Player-recorded entrance"
    ns.db.dungeonEntrances[group.key] = point
    ns.activityRevision = (ns.activityRevision or 0) + 1
    ns.guideAction = "Recorded " .. group.name .. " entrance here. Stand outside the entrance when recording."
    ns.Refresh()
end

function ns.ZoneTransition()
    if ns.routeSelection and ns.routeSelection.fullGuide then return ns.LevelingZoneTransition() end
    local currentMap = ns.profile and ns.profile.mapID or 0
    local position = ns.PlayerPoint(currentMap)
    if not position then return end
    local best, score
    for id, quest in pairs(ns.catalogue.quests) do
        local point = quest.starts and quest.starts[1]
        if ns.LevelingQuestEnabled(id) and (quest.previousQuest or quest.prerequisiteAny or quest.prerequisiteAll) and point
            and point.mapID ~= currentMap and ns.DiscoveryZoneAllowed(point.mapID, point) then
            local eligible = true
            for _, person in ipairs(ns.PartyProfiles()) do
                if not person.synced or ns.CatalogueAllowed(id, person.profile, person.key) ~= true
                    or ns.CatalogueCompletion(person.key, id) == true then eligible = false; break end
            end
            if eligible then
                local distance = ns.CrossMapDistance(position, point)
                if distance and distance <= 2500 then
                    local value = (quest.xp or 300) / (100 + distance)
                    if not score or value > score then best, score = id, value end
                end
            end
        end
    end
    if best then
        local record = ns.CatalogueRecord(best)
        return {key = "transition:" .. best, title = record.seriesName or record.title, kind = "Next leveling zone",
            records = {record}, target = record, focusKey = ns.self, hasPoint = true, mapID = record.mapID, zone = ns.MapName(record.mapID),
            reason = "Your party completed the previous step. This known questline continues in nearby " .. ns.MapName(record.mapID) .. "."}
    end
end

function ns.ShowActivityPrompt(key, title, text, callback, acceptLabel, declineLabel)
    if ns.activityPrompt and ns.activityPrompt:IsShown() then return end
    ns.db.activityNotices = ns.db.activityNotices or {}
    key = ns.ActivityNoticeKey(key)
    if ns.db.activityNotices[key] then return end
    if not ns.activityPrompt then
        local frame = CreateFrame("Frame", "WowTogetherActivityPrompt", UIParent, "BackdropTemplate")
        ns.activityPrompt = frame
        frame:SetSize(480, 210); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG"); frame:SetClampedToScreen(true); ns.UIPanel(frame)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 18); frame.title:SetPoint("TOPLEFT", 22, -22); frame.title:SetWidth(436)
        frame.text = ns.UILabel(frame, nil, 12); frame.text:SetPoint("TOPLEFT", 22, -52); frame.text:SetWidth(436); frame.text:SetHeight(100)
        frame.accept = ns.UIButton(frame, "Show collection plan", 200, function() end, true); frame.accept:SetPoint("BOTTOMLEFT", 22, 18)
        frame.later = ns.UIButton(frame, "Later", 130, function() frame:Hide() end); frame.later:SetPoint("BOTTOMRIGHT", -22, 18)
    end
    ns.db.activityNotices[key] = true
    ns.activityPrompt.noticeKey = key
    ns.activityPrompt.title:SetText(title); ns.activityPrompt.text:SetText(text)
    ns.activityPrompt.accept.caption:SetText(acceptLabel or (string.find(key, "transition:", 1, true) and "Show next zone route" or "Show collection plan"))
    ns.activityPrompt.later.caption:SetText(declineLabel or "Later")
    ns.activityPrompt.accept:SetScript("OnClick", function() ns.activityPrompt:Hide(); callback() end)
    ns.activityPrompt:Show()
end

function ns.ActivityNoticeKey(key) return (ns.self or "player") .. ":" .. key end

local pending, lastContext
function ns.ScheduleActivitySuggestions()
    if pending or not ns.db or not C_Timer or type(C_Timer.After) ~= "function" then return end
    if not ns.Option("dungeonPrompts") and not ns.Option("zonePrompts") then return end
    local parts = {ns.profile and ns.profile.level or 0, ns.profile and ns.profile.mapID or 0, ns.activityRevision or 0,
        tostring(ns.Option("dungeonPrompts")), tostring(ns.Option("zonePrompts")),
        tostring(ns.Option("classQuests")), tostring(ns.questReady), tostring(ns.catalogue),
        tostring(ns.profile and ns.profile.faction), tostring(ns.profile and ns.profile.classID), tostring(ns.profile and ns.profile.raceID),
        tostring(ns.routeSelection and ns.routeSelection.mode), tostring(ns.HasCurrentPartyQuests()),
        ns.routeSelection and ns.routeSelection.key or "", ns.selectedRoute and ns.selectedRoute.mapID or 0}
    for _, person in ipairs(ns.PartyProfiles()) do
        local member = ns.members[person.key]
        parts[#parts + 1] = person.key .. ":" .. tostring(person.synced) .. ":" .. (member and member.completionRevision or 0)
            .. ":" .. (person.profile and person.profile.level or 0) .. ":" .. (person.profile and person.profile.mapID or 0)
    end
    local context = table.concat(parts, "|")
    if context == lastContext then return end
    pending = true
    C_Timer.After(1, function()
        pending = false
        if ns.RouteInCombat() or ns.routePlanning or ns.guideScanning or (ns.activityPrompt and ns.activityPrompt:IsShown()) then return end
        lastContext = context
        local selection = ns.routeSelection
        if ns.Option("dungeonPrompts") and ns.questReady then
            for _, group in ipairs(ns.DungeonGroups()) do
                local readiness = ns.DungeonCollectionReadiness(group)
                if readiness.levelReady and ns.profile.level <= readiness.maxLevel + 3 and readiness.unfinished > 0
                    and not (ns.db.activityNotices and ns.db.activityNotices[ns.ActivityNoticeKey(readiness.noticeKey)]) then
                    ns.ShowActivityPrompt(readiness.noticeKey, "Collect " .. group.name .. " quests?", ns.DungeonCollectionSummary(group, readiness)
                        .. " Review the collection plan; distant pickups and missing locations are shown before travelling.",
                        function() ns.SetFilter("dungeons"); ns.ShowDungeonQuests(group) end)
                    return
                end
            end
        end
        if ns.Option("zonePrompts") then
            if selection and (selection.mode == "current" or selection.mode == "bundle") and ns.HasCurrentPartyQuests() then return end
            for _, person in ipairs(ns.PartyProfiles()) do
                if not person.synced or not person.profile or person.profile.level <= 0 then return end
            end
            local transition = ns.ZoneTransition()
            if transition and transition.fullGuide then
                ns.ShowActivityPrompt(transition.noticeKey, "Start " .. transition.zone .. " guide?", transition.reason,
                    function() ns.RequestStartRoute(transition) end, "Start zone guide", "Keep my guide")
                return
            end
            local circuits = ns.LocalCircuitChoices()
            if transition and (#circuits == 0 or #circuits[1].records <= 1) then
                ns.ShowActivityPrompt(transition.key, "Continue into " .. transition.zone .. "?", transition.reason .. " Local quest options are running low.", function() ns.ShowGuideOnMap(transition) end)
            end
        end
    end)
end
