local addonName, ns = ...

local catalogue, dungeons
local function titleCase(value) return string.gsub(string.gsub(value, "-", " "), "%f[%a]%l", string.upper) end

function ns.DungeonGroups()
    if catalogue ~= ns.catalogue then
        catalogue, dungeons = ns.catalogue, {}
        for id, quest in pairs(ns.catalogue.quests) do
            if ns.IsDungeonQuest(id) then
                local slug = quest.categoryPath and string.match(quest.categoryPath, "^dungeons/(.+)$")
                local name = slug and titleCase(slug) or ns.CatalogueZone(quest)
                local key = slug or string.lower(name)
                local group = dungeons[key]
                if not group then group = {key = key, name = name, ids = {}, minLevel = 255, level = 255, maxLevel = 0}; dungeons[key] = group end
                group.ids[#group.ids + 1] = id
                group.minLevel = math.min(group.minLevel, quest.minLevel or quest.level or 255)
                group.level = math.min(group.level, quest.level or 255)
                group.maxLevel = math.max(group.maxLevel, quest.level or 0)
            end
        end
        for _, group in pairs(dungeons) do table.sort(group.ids) end
    end
    local result = {}
    for _, group in pairs(dungeons) do result[#result + 1] = group end
    table.sort(result, function(a, b) if a.level ~= b.level then return a.level < b.level end; return a.key < b.key end)
    return result
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
    if recorded and ns.GuideInteger(recorded.mapID) and recorded.mapID > 0 and type(recorded.x) == "number" and type(recorded.y) == "number"
        and recorded.x >= 0 and recorded.x <= 1 and recorded.y >= 0 and recorded.y <= 1 then return recorded end
    if not C_Map or type(C_Map.GetMapLinksForMap) ~= "function" then return end
    local maps = {[ns.profile and ns.profile.mapID or 0] = true}
    for _, id in ipairs(group.ids) do
        local quest = ns.CatalogueQuest(id)
        for _, point in ipairs(quest.starts or {}) do maps[point.mapID] = true end
    end
    local ordered = {}; for id in pairs(maps) do if id > 0 then ordered[#ordered + 1] = id end end; table.sort(ordered)
    for _, id in ipairs(ordered) do
        local links = ns.ReadPublic(C_Map.GetMapLinksForMap, id)
        if type(links) == "table" then
            for index, link in ipairs(links) do
                if index > 100 then break end
                if ns.Public(link) and type(link) == "table" then
                    local name, position = ns.SafeTitle(link.name), ns.Public(link.position) and link.position
                    if name and string.lower(name) == string.lower(group.name) and position then
                        local x, y = ns.ReadPublic(position.GetXY, position)
                        if type(x) == "number" and type(y) == "number" and x >= 0 and x <= 1 and y >= 0 and y <= 1 then
                            return {mapID = id, x = x, y = y, name = group.name, source = "Client map entrance link"}
                        end
                    end
                end
            end
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

function ns.DungeonGuide(group)
    local records, unlock, level = {}, group.minLevel, ns.profile and ns.profile.level or 0
    for _, id in ipairs(group.ids) do
        local quest = ns.CatalogueQuest(id)
        if (quest.minLevel or quest.level or 255) <= level
            and ns.CatalogueIdentityAllowed(id, ns.profile) ~= false
            and (not ns.IsClassQuest(id) or ns.Option("classQuests"))
            and not ns.PartyQuestFinished(id) then records[#records + 1] = ns.CatalogueRecord(id) end
    end
    if #records == 0 then return end
    local entrance = ns.DungeonEntrance(group)
    local guide = {key = "dungeon:" .. group.key, dungeon = group, mode = "dungeon", title = group.name .. " quest collection",
        kind = "Dungeon quests", records = records, target = records[1], focusKey = ns.self, mapID = ns.profile.mapID,
        level = group.level, zone = group.name, profilesReady = true, entrance = entrance,
        reason = "Quest pickup levels start at " .. unlock .. "; listed quest levels " .. group.level .. "–" .. group.maxLevel .. ". Collect local pickups before entering.",
        destination = "Collect first, then go to the dungeon entrance."}
    local route = ns.BuildDungeonRoute(guide, true)
    guide.hasPoint, guide.knownStops, guide.missingStops = #route.stops > 0, #route.stops, route.missing
    guide.nextStop = route.stops[1]
    if not entrance then guide.reason = guide.reason .. " Entrance not located yet; stand outside it and use Record entrance here." end
    if route.remote > 0 then guide.reason = guide.reason .. " " .. route.remote .. " distant pickups excluded to avoid a long detour." end
    if route.missing > 0 then guide.reason = guide.reason .. " " .. route.missing .. " pickups need location/prerequisite checks." end
    return guide
end

function ns.BuildDungeonRoute(guide, includeOrigin)
    local currentMap, stops, missing, remote = ns.profile.mapID, {}, 0, 0
    local current = ns.PlayerPoint(currentMap)
    local entrance = guide.entrance
    local mapID = currentMap
    local allPickups, localPickups = {}, 0
    for _, record in ipairs(guide.records) do
        local stages = ns.PartyRouteStages(record, guide.focusKey)
        local first = stages[1]
        if first and first.kind == "a" then
            allPickups[#allPickups + 1] = first
            if first.mapID == currentMap then localPickups = localPickups + 1 end
        elseif #stages == 0 and not ns.PartyQuestFinished(record.id) then missing = missing + 1 end
    end
    -- Finish pickups in the current zone before drawing a nearby entrance map.
    if localPickups == 0 and entrance and entrance.mapID ~= currentMap then
        local distance = current and ns.CrossMapDistance(current, entrance)
        if distance and distance <= 2500 then mapID = entrance.mapID end
    end
    local pickups = {}
    for _, point in ipairs(allPickups) do
        if point.mapID == mapID then pickups[#pickups + 1] = point else remote = remote + 1 end
    end
    local position = includeOrigin and ns.PlayerPoint(mapID) or nil
    local last = position
    while #pickups > 0 and #stops < 19 do
        local best, score = 1, math.huge
        for index, point in ipairs(pickups) do
            local value = last and ns.NormalizedDistance(last, point) or index
            if value < score then best, score = index, value end
        end
        last = table.remove(pickups, best); stops[#stops + 1] = last
    end
    if entrance and entrance.mapID == mapID then
        stops[#stops + 1] = {id = guide.target.id, mapID = mapID, x = entrance.x, y = entrance.y, kind = "q",
            label = "After collecting quests: " .. guide.dungeon.name .. " entrance", title = guide.dungeon.name, planned = #stops > 0}
    end
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops, origin = position, focusKey = guide.focusKey,
        missing = missing, remote = remote, limited = #pickups, otherMaps = remote,
        partial = missing > 0 or remote > 0 or not entrance or entrance.mapID ~= mapID}
end

function ns.ShowDungeonQuests(group)
    ns.dungeonHistoryScope = {}
    for index, id in ipairs(group.ids) do
        if index > 96 then break end
        ns.dungeonHistoryScope[id] = true
        local quest = ns.CatalogueQuest(id)
        if quest.previousQuest then ns.dungeonHistoryScope[quest.previousQuest] = true end
    end
    ns.ScheduleSync()
    local guide = ns.DungeonGuide(group)
    if guide and guide.hasPoint then ns.ShowGuideOnMap(guide)
    elseif guide then ns.ShowQuestDetails(guide.target.id)
    else ns.guideAction = "No unfinished quests in this dungeon match your current level and faction."; ns.Refresh() end
end

function ns.ShowDungeonQuestList(group)
    if not ns.dungeonWindow then
        local frame = CreateFrame("Frame", "WowTogetherDungeonQuests", UIParent, "BackdropTemplate")
        ns.dungeonWindow = frame
        frame:SetSize(660, 500); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG"); frame:SetClampedToScreen(true); ns.UIPanel(frame)
        local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton"); close:SetPoint("TOPRIGHT", -4, -4)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 20); frame.title:SetPoint("TOPLEFT", 22, -20)
        local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
        scroll:SetPoint("TOPLEFT", 22, -58); scroll:SetPoint("BOTTOMRIGHT", -38, 68)
        frame.content = CreateFrame("Frame", nil, scroll); frame.content:SetSize(596, 100); scroll:SetScrollChild(frame.content)
        frame.text = ns.UILabel(frame.content, nil, 12); frame.text:SetPoint("TOPLEFT"); frame.text:SetWidth(590)
        frame.collect = ns.UIButton(frame, "Map nearby pickups, then entrance", 280, function() end, true); frame.collect:SetPoint("BOTTOMLEFT", 22, 20)
        frame.record = ns.UIButton(frame, "Record entrance here", 190, function() end); frame.record:SetPoint("BOTTOMRIGHT", -22, 20)
    end
    local lines = {"Collect quests locally before entering. Distant city pickups are optional; earlier quest steps may be required.", ""}
    for _, id in ipairs(group.ids) do
        local quest = ns.CatalogueQuest(id)
        local start = quest.starts and quest.starts[1]
        lines[#lines + 1] = quest.title .. " • quest Lv " .. (quest.level or "?") .. " • pickup Lv " .. (quest.minLevel or "?")
        lines[#lines + 1] = "  " .. (ns.ClassQuestLabel(id) or quest.side or "Faction unknown")
            .. " • " .. (ns.Completed(id) == true and "Completed" or (ns.active[id] and "In your log" or "Not in your log"))
        if start then lines[#lines + 1] = "  Pickup: " .. start.name .. " • " .. ns.MapName(start.mapID)
        else lines[#lines + 1] = "  Pickup location not known yet." end
        if quest.previousQuest then lines[#lines + 1] = "  Previous step: " .. ns.QuestTitle(quest.previousQuest) end
        lines[#lines + 1] = ""
    end
    lines[#lines + 1] = "For Record entrance here, stand outside the dungeon entrance first. This stores your current position."
    ns.dungeonWindow.title:SetText(group.name .. " quests")
    ns.dungeonWindow.text:SetText(table.concat(lines, "\n"))
    local height = ns.dungeonWindow.text:GetStringHeight()
    if ns.Public(height) and type(height) == "number" then ns.dungeonWindow.content:SetHeight(math.max(100, height + 12)) end
    ns.dungeonWindow.collect:SetScript("OnClick", function() ns.ShowDungeonQuests(group) end)
    ns.dungeonWindow.record:SetScript("OnClick", function() ns.RecordDungeonEntrance(group) end)
    ns.dungeonWindow:Show()
end

function ns.ZoneTransition()
    if ns.routeSelection and ns.routeSelection.fullGuide then return ns.LevelingZoneTransition() end
    local currentMap = ns.profile and ns.profile.mapID or 0
    local position = ns.PlayerPoint(currentMap)
    if not position then return end
    local best, score
    for id, quest in pairs(ns.catalogue.quests) do
        local point = quest.starts and quest.starts[1]
        if ns.LevelingQuestEnabled(id) and (quest.previousQuest or quest.prerequisiteAny) and point
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
        if ns.RouteInCombat() or ns.routePlanning or (ns.activityPrompt and ns.activityPrompt:IsShown()) then return end
        lastContext = context
        local selection = ns.routeSelection
        if selection and (selection.mode == "current" or selection.mode == "bundle") and ns.HasCurrentPartyQuests() then return end
        local lowest
        for _, person in ipairs(ns.PartyProfiles()) do
            if not person.synced or not person.profile or person.profile.level <= 0 then return end
            lowest = math.min(lowest or person.profile.level, person.profile.level)
        end
        if ns.Option("dungeonPrompts") then
            for _, group in ipairs(ns.DungeonGroups()) do
                if lowest >= group.minLevel and lowest <= group.maxLevel + 3 then
                    local guide = ns.DungeonGuide(group)
                    local first = guide and guide.nextStop
                    if first and (first.mapID == ns.profile.mapID or (ns.PlayerPoint(ns.profile.mapID) and ns.CrossMapDistance(ns.PlayerPoint(ns.profile.mapID), first) or math.huge) <= 2500)
                        and not (ns.db.activityNotices and ns.db.activityNotices[ns.ActivityNoticeKey(guide.key)]) then
                        ns.ShowActivityPrompt(guide.key, "Collect " .. group.name .. " quests?", guide.reason, function() ns.SetFilter("dungeons"); ns.ShowDungeonQuests(group) end)
                        return
                    end
                end
            end
        end
        if ns.Option("zonePrompts") then
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
