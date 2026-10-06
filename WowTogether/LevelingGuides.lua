local addonName, ns = ...

ns.guideLevel, ns.guideSearch, ns.guidePage = "party", "", 1
local indexed, indexRevision, entries, resolved, resolvedMap

local function normalize(value)
    return string.lower(string.gsub(value or "", "[^%w]", ""))
end

function ns.ResolveCatalogueMaps()
    local current = ns.profile and ns.profile.mapID or 0
    if resolved == ns.catalogue and resolvedMap == current then return end
    resolved, resolvedMap = ns.catalogue, current
    local names, ambiguous = {}, {}
    local function remember(name, id)
        local key = normalize(name)
        if key == "" then return end
        if names[key] and names[key] ~= id then ambiguous[key] = true end
        names[key] = id
    end
    for id in pairs(ns.KnownZoneMaps()) do
        local info = C_Map and ns.ReadPublic(C_Map.GetMapInfo, id)
        if type(info) == "table" then
            local name = ns.SafeTitle(info.name)
            if name then remember(name, id) end
        end
    end
    local fields = {a = "starts", q = "objectives", t = "ends"}
    local changed = false
    for _, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
        local zoneKey = normalize(quest.zone and quest.zone ~= "" and quest.zone or ns.CatalogueZone(quest))
        if (quest.mapID or 0) == 0 and names[zoneKey] and not ambiguous[zoneKey] then
            quest.mapID, changed = names[zoneKey], true
        end
        local unresolved = 0
        for _, location in ipairs(quest.unmappedLocations or {}) do
            local key, field = normalize(location.sourceZone), fields[location.kind]
            local id = not ambiguous[key] and names[key]
            if field and id and not location.resolved then
                local point = {}; for k, value in pairs(location) do point[k] = value end
                point.mapID, point.sourceZone, point.sourceAreaID, point.kind, point.resolved = id, nil, nil, nil, nil
                quest[field] = quest[field] or {}; quest[field][#quest[field] + 1] = point
                location.resolved, changed = true, true
            elseif not location.resolved then unresolved = unresolved + 1 end
        end
        if quest.unmappedLocations and unresolved == 0 and quest.otherLocationsIncomplete == false then
            quest.objectiveLocationsIncomplete = nil
        end
    end
    if changed then ns.catalogueLocationRevision = (ns.catalogueLocationRevision or 0) + 1 end
end

function ns.GuideLevelRange(value, query)
    value = value or ns.guideLevel
    if value == "all" then return 1, 255 end
    if value == "party" then
        local level = ns.PartyLevelFloor(query) or 1
        local low = math.floor((math.max(1, level) - 1) / 10) * 10 + 1
        return low, low + 9
    end
    if value == "51+" then return 51, 255 end
    local low, high = string.match(value, "^(%d+)%-(%d+)$")
    return tonumber(low) or 1, tonumber(high) or 10
end

function ns.SetGuideLevel(value)
    ns.guideLevel, ns.guidePage = value, 1
    ns.ui.scroll:SetVerticalScroll(0); ns.Refresh()
end

function ns.ApplyGuideSearch()
    ns.guideSearchGeneration = (ns.guideSearchGeneration or 0) + 1
    ns.guideSearch, ns.guidePage = ns.guideSearchDraft or "", 1
    ns.ui.scroll:SetVerticalScroll(0); ns.Refresh()
end

function ns.QueueGuideSearch(value)
    ns.guideSearchDraft = string.sub(value, 1, 100)
    ns.guideSearchGeneration = (ns.guideSearchGeneration or 0) + 1
    local generation = ns.guideSearchGeneration
    if C_Timer and type(C_Timer.After) == "function" then
        C_Timer.After(0.4, function()
            if generation == ns.guideSearchGeneration and ns.filter == "guides" then ns.ApplyGuideSearch() end
        end)
    end
end

local function geographic(quest)
    local category = quest.categoryPath or ""
    return string.find(category, "^kalimdor/") or string.find(category, "^eastern%-kingdoms/")
        or (category == "" or category == "uncategorized") and ((quest.mapID or 0) > 0 or (quest.areaID or 0) > 0)
end

local function recordEnabled(id)
    return not ns.IsLevelingExcludedQuest(id) and not ns.IsProfessionQuest(id) and not ns.IsDungeonQuest(id) and not ns.IsRepeatableQuest(id)
        and ns.CatalogueIdentityAllowed(id, ns.profile) ~= false
end

local function browseEnabled(id)
    return recordEnabled(id) and ns.ClassQuestEnabled(id)
end

local function rebuildIndex()
    if indexed == ns.catalogue and indexRevision == ns.catalogueLocationRevision then return end
    indexed, indexRevision, entries = ns.catalogue, ns.catalogueLocationRevision, {}
    local canonical, ambiguous = {}, {}
    for _, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
        local path = quest.categoryPath
        if geographic(quest) and path and path ~= "" and path ~= "uncategorized" and (quest.mapID or 0) > 0 then
            if canonical[quest.mapID] and canonical[quest.mapID] ~= path then ambiguous[quest.mapID] = true end
            canonical[quest.mapID] = path
        end
    end
    local function add(key, kind, title, zone, mapID, id)
        local entry = entries[key]
        if not entry then
            entry = {key = key, mode = kind, title = title, zone = zone, mapID = mapID or 0, ids = {}, seen = {}}
            entries[key] = entry
        end
        if entry.mapID == 0 and (mapID or 0) > 0 then entry.mapID = mapID end
        if not entry.seen[id] then entry.ids[#entry.ids + 1], entry.seen[id] = id, true end
    end
    for id, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
        if geographic(quest) and ((quest.areaID or 0) > 0 or (quest.mapID or 0) > 0 or quest.zone and quest.zone ~= "") then
            local zone = ns.CatalogueZone(quest)
            local path = quest.categoryPath ~= "uncategorized" and quest.categoryPath
                or not ambiguous[quest.mapID] and canonical[quest.mapID]
            if quest.categoryPath == "uncategorized" and zone == "Uncategorized" and (quest.mapID or 0) > 0 then zone = ns.MapName(quest.mapID) end
            local key = path and path ~= "" and path
                or ((quest.mapID or 0) > 0 and ("map:" .. quest.mapID) or "zone:" .. normalize(zone))
            add("level-zone:" .. key, "zone", zone .. " leveling guide", zone, quest.mapID, id)
            if quest.seriesRoot then
                local root = ns.CatalogueQuest(quest.seriesRoot)
                local title = quest.seriesName or root and root.title or quest.title
                local chainZone, chainMap = root and ns.CatalogueZone(root) or zone, root and root.mapID or quest.mapID
                add("level-chain:" .. quest.seriesRoot, "chain", title, chainZone, chainMap, id)
                for _, nextID in ipairs(quest.series or {}) do
                    if ns.CatalogueQuest(nextID) then add("level-chain:" .. quest.seriesRoot, "chain", title, chainZone, chainMap, nextID) end
                end
            end
        end
    end
    -- A class category is not a separate leveling zone. Join its primary
    -- published pickup to an existing, unambiguous zone; never guess a zone
    -- from the class name or substitute an alternative starter for the compiler.
    local byMap, ambiguousMap = {}, {}
    for _, entry in pairs(entries) do
        if entry.mode == "zone" and entry.mapID > 0 then
            if byMap[entry.mapID] and byMap[entry.mapID] ~= entry then ambiguousMap[entry.mapID] = true end
            byMap[entry.mapID] = entry
        end
    end
    for id, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
        if ns.IsClassQuest(id) and not geographic(quest) then
            local point = quest.starts and quest.starts[1]
            local mapID = point and point.mapID
            local entry = mapID and not ambiguousMap[mapID] and byMap[mapID]
            if entry then add(entry.key, "zone", entry.title, entry.zone, entry.mapID, id) end
        end
    end
    for _, entry in pairs(entries) do table.sort(entry.ids) end
end

local function addPrerequisites(records, seen, id, depth)
    if depth > 24 or #records >= 512 then return end
    for _, previous in ipairs(ns.CataloguePrerequisiteIDs(id)) do
        if not seen[previous] and ns.CatalogueQuest(previous) and recordEnabled(previous) then
            seen[previous] = true
            addPrerequisites(records, seen, previous, depth + 1)
            records[#records + 1] = ns.CatalogueRecord(previous)
        end
    end
end

local function addChain(records, seen, id)
    if #records >= 512 or seen[id] or not ns.CatalogueQuest(id) or not recordEnabled(id) then return end
    addPrerequisites(records, seen, id, 0)
    records[#records + 1], seen[id] = ns.CatalogueRecord(id), true
    local quest, after = ns.CatalogueQuest(id), false
    for _, nextID in ipairs(quest.series or {}) do
        if after then addChain(records, seen, nextID) end
        if nextID == id then after = true end
    end
end

local function entryRecords(entry)
    local records, seen = {}, {}
    for _, id in ipairs(entry.ids) do addChain(records, seen, id) end
    return records
end

-- The saved zone scope includes optional class work. The checkbox filters its
-- presentation/progress later, rather than deleting instructions at discovery.
function ns.LevelingGuideRecords(key)
    rebuildIndex()
    local entry = entries[key]
    return entry and entryRecords(entry)
end

local function localWork(quest, mapID)
    local mapped = false
    for _, point in ipairs(quest.objectives or {}) do
        if (point.mapID or 0) > 0 then
            mapped = true
            if point.mapID == mapID then return true end
        end
    end
    -- Unknown geography cannot establish a remote objective. Use the published
    -- zone category until detailed locations exist; known remote-only work does
    -- not qualify its pickup zone as a leveling area.
    return not mapped
end

local function coreRange(entry)
    local levels = {}
    for _, id in ipairs(entry.ids) do
        local quest = ns.CatalogueQuest(id)
        if browseEnabled(id) and (quest.level or 0) > 0 and localWork(quest, entry.mapID) then levels[#levels + 1] = quest.level end
    end
    table.sort(levels)
    if #levels == 0 then return end
    -- Large catalogues can contain a handful of high-level handoffs. The middle
    -- 80% describes the main quest band; small/new-zone catalogues keep all data.
    local trim = #levels >= 10 and math.floor(#levels * 0.1) or 0
    return levels[1 + trim], levels[#levels - trim]
end

local function buildChoice(entry, low, high, query)
    query = query or ns.NewQuestQuery()
    local relevant, search = 0, {entry.title, entry.zone}
    local minimum, maximum, located = 255, 0, 0
    for _, id in ipairs(entry.ids) do
        local quest = ns.CatalogueQuest(id)
        if browseEnabled(id) then
            local level = quest.level or 0
            if level > 0 then minimum, maximum = math.min(minimum, level), math.max(maximum, level) end
            search[#search + 1] = quest.title
            for _, point in ipairs(quest.starts or {}) do search[#search + 1] = point.name or "" end
            -- Brackets filter guide discovery, not its lifetime. Preserve the
            -- full chain, including later levels and published cross-zone work.
            if level >= low and level <= high then
                relevant = relevant + 1
            end
            if quest.starts and #quest.starts > 0 then located = located + 1 end
        end
    end
    -- A single observed/isolated quest is not a leveling guide. Completed
    -- earlier stages still count as evidence that a real multi-quest plan exists.
    if relevant == 0 then return end
    local records, enabled = entryRecords(entry), {}
    for _, record in ipairs(records) do
        if ns.ClassQuestEnabled(record.id) then enabled[#enabled + 1] = record end
    end
    if #enabled < 2 then return end
    local focus = ns.GuideFocus(enabled, query)
    local pending, completed = 0, 0
    for _, record in ipairs(enabled) do
        if ns.PartyQuestFinished(record.id, query) then completed = completed + 1 else pending = pending + 1 end
    end
    local level, _, name = ns.PartyLevelFloor(query)
    local mapID = entry.mapID
    if mapID == 0 then
        for _, id in ipairs(entry.ids) do
            local record = ns.CatalogueRecord(id)
            if record.mapID > 0 then mapID = record.mapID; break end
        end
    end
    local guide = {key = entry.key, mode = entry.mode, title = entry.title, zone = entry.zone,
        kind = entry.mode == "zone" and "Zone guide" or "Questline", records = records, target = records[1],
        mapID = mapID, homeMapID = mapID, focusKey = focus, profilesReady = true, level = level, minLevel = minimum, maxLevel = maximum,
        rangeLow = low, rangeHigh = high, relevant = relevant, completed = completed, pending = pending,
        knownStops = located, hasPoint = located > 0, fullGuide = true, classQuestScope = true,
        search = string.lower(table.concat(search, " ")),
        priority = ns.ZonePreference(mapID) + (entry.mode == "zone" and 30 or 0) + (located > 0 and 10 or 0)}
    guide.mainLevelLow, guide.mainLevelHigh = coreRange(entry)
    guide.fixedRoute = ns.Option("fixedZoneGuides")
    guide.coverage = ns.GuideLocationCoverage(enabled)
    guide.knownStops, guide.hasPoint = guide.coverage.pickups, guide.coverage.pickups > 0
    guide.reason = relevant .. " quest(s) in levels " .. low .. "–" .. high .. "; " .. #enabled .. " in the full guide. "
        .. (guide.fixedRoute and "Fixed order; progress advances steps without replanning."
            or ("Optimize pickups, nearby objectives and returns for " .. (name or "your character") .. "."))
    if located < #enabled then guide.reason = guide.reason .. " Some NPC/objective locations remain unknown." end
    guide.destination = "Generate the route to its first useful, unlocked step."
    return guide
end

local function levelPath(id, level, seen, depth, query)
    if depth > 24 or seen[id] then return false end
    local quest = ns.CatalogueQuest(id)
    if not quest then return true end -- Missing requirements remain an NPC check.
    if quest.minLevel and quest.minLevel > level then return false end
    if (quest.level or 0) > level + 3 then return false end
    if ns.CatalogueIdentityAllowed(id, ns.profile) == false then return false end
    local visited = {}; for key, value in pairs(seen) do visited[key] = value end; visited[id] = true
    if quest.previousQuest and not ns.PartyQuestFinished(quest.previousQuest, query)
        and not levelPath(quest.previousQuest, level, visited, depth + 1, query) then return false end
    for _, previous in ipairs(quest.prerequisiteAll or {}) do
        if not ns.PartyQuestFinished(previous, query) and not levelPath(previous, level, visited, depth + 1, query) then return false end
    end
    if quest.prerequisiteAny then
        for _, previous in ipairs(quest.prerequisiteAny) do
            if ns.PartyQuestFinished(previous, query) or levelPath(previous, level, visited, depth + 1, query) then return true end
        end
        return false
    end
    return true
end

local function guideAreaMatches(guide)
    if ns.IsCapitalMap(guide.homeMapID) then return false end
    -- Keep useful entry quests just below the main band: the same three-level
    -- difficulty allowance used below still permits a zone transition.
    if guide.mainLevelHigh and (guide.mainLevelHigh + 3 < (guide.rangeLow or 1) or guide.mainLevelLow > (guide.rangeHigh or 255) + 3) then return false end
    return true
end

local function guideRecordMatches(guide, record)
    local quest = ns.CatalogueQuest(record.id)
    local knownLevel = quest and ((quest.level or 0) > 0 or (quest.minLevel or 0) > 0)
    local inBracket = quest and (quest.level or 0) >= (guide.rangeLow or 1) and (quest.level or 0) <= (guide.rangeHigh or 255)
    return ns.ClassQuestEnabled(record.id) and inBracket and knownLevel and localWork(quest, guide.homeMapID)
        and record.mapID == guide.homeMapID and ns.CatalogueIdentityAllowed(record.id, ns.profile) == true
end

function ns.GuideBracketMatches(guide)
    if not guideAreaMatches(guide) then return false end
    for _, record in ipairs(guide.records or {}) do
        if guideRecordMatches(guide, record) then return true end
    end
    return false
end

function ns.GuideLevelSuitable(guide, query, unfinishedOnly)
    query = query or ns.NewQuestQuery()
    local level = ns.PartyLevelFloor(query)
    if not level or not guideAreaMatches(guide) then return false end
    for _, record in ipairs(guide.records or {}) do
        if guideRecordMatches(guide, record)
            and (not unfinishedOnly or not ns.PartyQuestFinished(record.id, query) and not ns.GuideQuestSkipped(record.id))
            and ns.LevelingValue(record.id, query) == true and levelPath(record.id, level, {}, 0, query) then return true end
    end
    return false
end

function ns.LevelingGuideChoices(ignoreSearch, queryContext, levelFilter)
    ns.ResolveCatalogueMaps(); rebuildIndex()
    queryContext = queryContext or ns.NewQuestQuery()
    levelFilter = levelFilter or ns.guideLevel
    local choices, low, high = {}, ns.GuideLevelRange(levelFilter, queryContext)
    local query = ignoreSearch and "" or string.lower(ns.guideSearch or "")
    for _, entry in pairs(entries) do
        -- Chains remain part of zone planning and saved/shared guides. The
        -- browser offers whole zones rather than duplicate partial-chain cards.
        local choice = entry.mode == "zone" and buildChoice(entry, low, high, queryContext)
        if choice and ns.GuideBracketMatches(choice)
            and (query == "" or string.find(choice.search, query, 1, true)) then choices[#choices + 1] = choice end
    end
    local level = ns.PartyLevelFloor(queryContext)
    local visible = {}
    for _, choice in ipairs(choices) do
        choice.levelReady = ns.GuideLevelSuitable(choice, queryContext)
        if levelFilter ~= "party" or choice.levelReady then
            choice.upcoming = false
            if not choice.levelReady and level then
                for _, record in ipairs(choice.records) do
                    local quest = ns.CatalogueQuest(record.id)
                    if guideRecordMatches(choice, record) and ((quest.level or 0) > level + 3 or (quest.minLevel or 0) > level) then
                        choice.upcoming = true; break
                    end
                end
            end
            visible[#visible + 1] = choice
        end
    end
    choices = visible
    table.sort(choices, function(a, b)
        if a.levelReady ~= b.levelReady then return a.levelReady end
        if a.priority ~= b.priority then return a.priority > b.priority end
        if a.zone ~= b.zone then return a.zone < b.zone end
        return a.key < b.key
    end)
    return choices
end

-- Evaluate future difficulty only on Start, not on each browser/arrow refresh.
-- The hypothetical level belongs to this private query; it grants no pickup,
-- completion or routing credit to the actual character or party.
function ns.GuideEarlyStartAdvice(guide, query)
    if not guide or not guide.fullGuide or not ns.GuideBracketMatches(guide) then return end
    query = query or ns.NewQuestQuery()
    local level, key, name = ns.PartyLevelFloor(query)
    if not level or ns.GuideLevelSuitable(guide, query) then return end
    local future = ns.NewQuestQuery()
    local nextLevel
    for candidate = level + 1, 60 do
        future.floor, future.values = {candidate, key, name}, {}
        if ns.GuideLevelSuitable(guide, future) then nextLevel = candidate; break end
    end
    if not nextLevel then return end
    local recommendation
    for _, choice in ipairs(ns.LevelingGuideChoices(true, query, "party")) do
        if choice.key ~= guide.key and ns.GuideLevelSuitable(choice, query, true) then recommendation = choice; break end
    end
    return {level = level, recommendedLevel = nextLevel, name = name or "You", recommendation = recommendation}
end

function ns.RebuildLevelingGuide(guide)
    rebuildIndex()
    local low, high = ns.GuideLevelRange()
    local entry = entries[guide.key]
    return entry and buildChoice(entry, low, high) or guide
end

function ns.InvitedLevelingGuide(invite)
    rebuildIndex()
    if invite.guideKey then
        local entry = entries[invite.guideKey]
        if not entry or entry.mode ~= invite.mode then return end
        local guide = buildChoice(entry, invite.rangeLow, invite.rangeHigh)
        if guide then guide.sharedBy, guide.fixedRoute = invite.sender, invite.fixedRoute == true; return guide end
    end
    for _, entry in pairs(entries) do
        if entry.mode == invite.mode and entry.seen[invite.target] then
            local low, high = ns.GuideLevelRange("party")
            local guide = buildChoice(entry, low, high)
            if guide then guide.sharedBy = invite.sender; return guide end
        end
    end
end

function ns.ZoneGuideForMap(mapID, allLevels, query)
    ns.ResolveCatalogueMaps(); rebuildIndex()
    local low, high = ns.GuideLevelRange("party")
    if allLevels then low, high = 1, 255 end
    for _, entry in pairs(entries) do
        if entry.mode == "zone" and (entry.mapID == mapID or entry.mapID == 0) then
            local choice = buildChoice(entry, low, high, query)
            if choice and choice.homeMapID == mapID then return choice end
        end
    end
end

local function levelReadyNeighbour(guide, route, current)
    -- A level milestone is a suggestion, never permission to replace useful
    -- current work, an NPC confirmation, or a missing-location step.
    if not route or #route.stops > 0 or route.pendingStop
        or not (route.complete or (route.filteredSteps or 0) > 0) then return end
    local query, best, score = ns.NewQuestQuery(), nil, nil
    local level = ns.PartyLevelFloor(query)
    if not level then return end
    for _, person in ipairs(query.profiles) do if not person.synced then return end end
    for mapID in pairs(ns.NearbyZoneMaps(current)) do
        if mapID ~= current and mapID ~= (guide.homeMapID or guide.mapID) and not ns.IsCapitalMap(mapID) then
            local candidate = ns.ZoneGuideForMap(mapID, false, query)
            if candidate and ns.GuideLevelSuitable(candidate, query, true) then
                for _, record in ipairs(candidate.records) do
                    if ns.ClassQuestEnabled(record.id) and not ns.GuideQuestSkipped(record.id)
                        and ns.LevelingValue(record.id, query) == true and not ns.PartyQuestFinished(record.id, query)
                        and ns.FocusCanStartRecord(record, candidate.focusKey)
                        and ns.CatalogueAllowed(record.id, ns.profile, ns.self, query) == true then
                        local quest = ns.CatalogueQuest(record.id)
                        local point = quest and quest.starts and quest.starts[1]
                        if point and point.mapID == mapID and ns.DiscoveryZoneAllowed(mapID, point) then
                            local value = math.abs((record.level or level) - level)
                            if not score or value < score or value == score and candidate.key < best.key then
                                best, score = candidate, value
                            end
                        end
                    end
                end
            end
        end
    end
    if best then
        best.transition = true
        best.noticeKey = "level-ready:" .. guide.key .. ":" .. best.key .. ":" .. best.rangeLow
        best.reason = "At level " .. level .. ", " .. best.zone .. " has useful quests in your leveling range. "
            .. "Your current guide has no suitable work ready now. Start this nearby zone, or keep your guide."
    end
    return best
end

function ns.LevelingZoneTransition()
    local guide, route = ns.routeSelection, ns.selectedRoute
    if not guide or not guide.fullGuide then return end
    local home, current = guide.homeMapID or guide.mapID, ns.profile and ns.profile.mapID or 0
    local levelReady = levelReadyNeighbour(guide, route, current)
    if levelReady then return levelReady end
    local nextMap = route and route.stops[1] and route.stops[1].mapID
    if current ~= home and nextMap == home then return end
    local destination = nextMap and nextMap ~= home and nextMap or current ~= home and current
    if not destination or not ns.NearbyZoneMaps(current)[destination] then return end
    if current ~= home and not ns.NearbyZoneMaps(home)[current] and nextMap ~= destination then return end
    local nextGuide = ns.ZoneGuideForMap(destination)
    if not nextGuide or nextGuide.key == guide.key then return end
    local ready = false
    for _, person in ipairs(ns.PartyProfiles()) do if not person.synced then return end end
    for _, record in ipairs(nextGuide.records) do
        if ns.LevelingValue(record.id) == true and ns.FocusCanStartRecord(record, nextGuide.focusKey)
            and not ns.PartyQuestFinished(record.id) then
            local stages = ns.PartyRouteStages(record, nextGuide.focusKey)
            if stages[1] and stages[1].mapID == destination then ready = true; break end
        end
    end
    if not ready then return end
    nextGuide.transition = true
    nextGuide.noticeKey = "transition:" .. guide.key .. ":" .. nextGuide.key .. ":" .. nextGuide.rangeLow
    nextGuide.reason = "Your guide continues toward " .. nextGuide.zone .. ". Your party's level and known quest progress fit its full zone guide. Keep this guide, or start that zone's plan."
    return nextGuide
end
