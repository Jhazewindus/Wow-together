local addonName, ns = ...

local scopeCache, scopeSignature, scopeCatalogue

function ns.CatalogueQuest(id)
    return ns.catalogue and ns.catalogue.quests[id]
end

-- Explain a missing pickup with captured item-source facts when available.
-- These facts can identify what starts a quest, but do not imply a map point.
function ns.QuestStartGapReason(id)
    local quest = ns.CatalogueQuest(id)
    if not quest or quest.starts and #quest.starts > 0 then return end
    for _, item in ipairs(quest.providedItems or {}) do
        if item.entityType == "item" and item.entityID then
            local data = ns.questEntities and ns.questEntities.item and ns.questEntities.item[item.entityID]
            local source = data and data.sources and data.sources[1]
            local itemName = ns.SafeTitle(item.name or data and data.name)
            local sourceName = source and ns.SafeTitle(source.name)
            if itemName then
                if sourceName then
                    return "To start " .. quest.title .. ", obtain " .. itemName .. " from " .. sourceName
                        .. ". Its pickup location is not mapped yet."
                end
                return "To start " .. quest.title .. ", obtain " .. itemName
                    .. ". Its pickup location is not mapped yet."
            end
        end
    end
    return "The pickup location for " .. quest.title .. " is not mapped yet."
end

function ns.IsRetiredQuest(id)
    local quest = ns.CatalogueQuest(id)
    local title = quest and quest.title
    if not ns.Public(title) or type(title) ~= "string" then return false end
    title = string.lower(string.match(title, "^%s*(.-)%s*$"))
    return string.find(title, "^<unused>") ~= nil or string.find(title, "^%(unused%)") ~= nil
        or title == "unused" or string.find(title, "^zzold") ~= nil
        or string.find(title, "%(temp disabled%)") ~= nil
        or string.find(title, "<%s*nyi%s*>") ~= nil or string.find(title, "<%s*txt%s*>") ~= nil
end

function ns.IsLevelingExcludedQuest(id)
    if ns.IsRetiredQuest(id) then return true end
    local quest = ns.CatalogueQuest(id)
    -- Explicit zero-level/zero-XP catalogue entries include interactive props
    -- and test quests. They are searchable facts, not leveling work. Missing
    -- rewards and ordinary delivery quests must not be mistaken for these.
    if quest and ns.Public(quest.level) and ns.Public(quest.xp) and quest.level == 0 and quest.xp == 0 then return true end
    local reason = quest and quest.levelingExcluded
    return ns.Public(reason) and (reason == true or type(reason) == "string" and reason ~= "") or false
end

function ns.CatalogueCompletion(key, id, query)
    if key == ns.self then return ns.Completed(id, query) end
    local state = ns.SyncStateForQuest and ns.SyncStateForQuest(key, id)
    if state == 3 then return true end
    if state == 1 or state == 2 then return false end
    if state == 0 then return nil end
    local member = ns.members[key]
    if member and member.completed and member.completed[id] then return true end
    if member and member.historyRevision and member.historyRevision == member.completionRevision
        and member.activeRevision and member.completionRevision >= member.activeRevision and not member.syncPending
        and member.historyChecked and member.historyChecked[id] then return false end
end

local function talkOnly(quest)
    return quest and next(quest.objectives or {}) == nil and next(quest.requirements or {}) == nil
end
local function npcPoint(point)
    return point and point.entityType == "npc" and ns.GuideInteger(point.entityID) and point.entityID > 0 and point.entityID or nil
end

-- Breadcrumb targets: the quests a "Speak with X" / "Report to X" errand
-- exists to lead into. The server refuses such an errand once its
-- continuation is accepted or done (SatisfyQuestNextChain), so the guide must
-- not route to it either. Published `nextInChain` data wins; without it, a
-- class-category errand with no objectives is inferred to lead into the
-- same-class quests its end NPC starts, excluding round trips back to its
-- own start NPC, quests it is a recorded prerequisite of, and quests outside
-- a -5/+10 level band. Skipping an errand too eagerly costs a few XP; routing
-- to one the server no longer offers costs a trip to another city. Zone quests are never inferred: a
-- delivery to a hub NPC is not an errand.
local breadcrumbCache, breadcrumbSignature, startIndex = {}, nil, nil
local function indexCatalogue()
    local quests = ns.catalogue and ns.catalogue.quests
    if not quests then return end
    local signature = tostring(quests)
    if breadcrumbSignature == signature then return end
    breadcrumbSignature, breadcrumbCache, startIndex = signature, {}, {}
    -- Only class-category quests are indexed: inference is limited to them,
    -- and this keeps the one-time unpacking to a few hundred records.
    for id, quest in pairs(quests) do
        local path = quest.categoryPath
        if type(path) == "string" and string.find(path, "^classes/") then
            local starter = npcPoint(quest.starts and quest.starts[1])
            if starter then startIndex[starter] = startIndex[starter] or {}; table.insert(startIndex[starter], id) end
        end
    end
end

function ns.CatalogueBreadcrumbTargets(id)
    local quest = ns.CatalogueQuest(id)
    if not quest then return {} end
    indexCatalogue()
    if breadcrumbCache[id] then return breadcrumbCache[id] end
    local targets = {}
    local published = quest.nextInChain
    if type(published) == "number" then targets[1] = published
    elseif type(published) == "table" then for _, other in ipairs(published) do targets[#targets + 1] = other end end
    local path = quest.categoryPath
    local starter, finisher = npcPoint(quest.starts and quest.starts[1]), npcPoint(quest.ends and quest.ends[1])
    if #targets == 0 and type(path) == "string" and string.find(path, "^classes/") and talkOnly(quest)
        and starter and finisher and starter ~= finisher then
        local level = quest.level or quest.minLevel or 0
        for _, other in ipairs(startIndex and startIndex[finisher] or {}) do
            local candidate = ns.CatalogueQuest(other)
            local otherLevel = candidate and (candidate.level or candidate.minLevel or 0) or 0
            if other ~= id and candidate and candidate.categoryPath == path and not ns.IsRetiredQuest(other)
                and npcPoint(candidate.ends and candidate.ends[1]) ~= starter
                and otherLevel >= level - 5 and otherLevel <= level + 10 then
                local dependent = false
                for _, previous in ipairs(ns.CataloguePrerequisiteIDs(other)) do if previous == id then dependent = true end end
                if not dependent then targets[#targets + 1] = other end
            end
        end
        table.sort(targets)
    end
    breadcrumbCache[id] = targets
    return targets
end

-- Only explicitly documented alternatives qualify. Matching titles alone must
-- never suppress separate chain quests, repeatables or accepted work. The
-- second result names the relation: "exclusive" or "breadcrumb".
local function alternativeTaken(id, key, query)
    local quest = ns.CatalogueQuest(id)
    if not quest then return end
    key = key or ns.self
    local member = key ~= ns.self and ns.members[key]
    local active = key == ns.self and ns.active or member and member.active
    if active and active[id] then return end
    if key ~= ns.self and (not member or member.syncPending or not member.activeRevision) then return end
    for _, other in ipairs(quest.exclusiveQuests or {}) do
        if active and active[other] or ns.CatalogueCompletion(key, other, query) == true then return other, "exclusive" end
    end
    local targets = ns.CatalogueBreadcrumbTargets(id)
    if #targets == 0 or ns.CatalogueCompletion(key, id, query) == true then return end
    for _, other in ipairs(targets) do
        if active and active[other] or ns.CatalogueCompletion(key, other, query) == true then return other, "breadcrumb" end
    end
end

-- Keep the public contract compatible with callers that expect one value.
function ns.CatalogueAlternativeTaken(id, key, query)
    local alternative = alternativeTaken(id, key, query)
    return alternative
end

local classCategoryIDs = {warrior = 1, paladin = 2, hunter = 3, rogue = 4, priest = 5,
    ["death-knight"] = 6, shaman = 7, mage = 8, warlock = 9, monk = 10, druid = 11,
    ["demon-hunter"] = 12, evoker = 13}

function ns.CatalogueClassCategoryID(id)
    local quest = ns.CatalogueQuest(id)
    local path = quest and quest.categoryPath
    local slug = type(path) == "string" and string.match(path, "^classes/([%w%-]+)$")
    return slug and classCategoryIDs[slug]
end

function ns.CatalogueClassCategoryAllowed(id, profile)
    local categoryClass = ns.CatalogueClassCategoryID(id)
    if not categoryClass then return true end
    local classID = profile and profile.classID
    if not ns.GuideInteger(classID, 255) or classID <= 0 then return nil, "Waiting for class." end
    if classID == categoryClass then return true end
    local names = {[1] = "Warrior", [2] = "Paladin", [3] = "Hunter", [4] = "Rogue", [5] = "Priest",
        [6] = "Death Knight", [7] = "Shaman", [8] = "Mage", [9] = "Warlock", [10] = "Monk",
        [11] = "Druid", [12] = "Demon Hunter", [13] = "Evoker"}
    return false, "A " .. (names[categoryClass] or "class") .. " class requirement."
end

function ns.CatalogueIdentityAllowed(id, profile)
    local quest = ns.CatalogueQuest(id)
    if not quest then return true end
    if not profile then return nil, "Waiting for player details." end
    if quest.side == "Alliance" or quest.side == "Horde" then
        if not profile.faction or profile.faction == "Unknown" then return nil, "Waiting for faction." end
        if profile.faction ~= quest.side then return false, "A " .. quest.side .. " quest." end
    elseif quest.side ~= "Both" and quest.side ~= "Neutral" then
        return nil, "Faction availability has not been verified."
    end
    for _, requirement in ipairs({{"classMask", "classID", "class"}, {"raceMask", "raceID", "race"}}) do
        local mask = quest[requirement[1]]
        if requirement[1] == "raceMask" and quest.allowedRaceIDs and #quest.allowedRaceIDs > 0 then
            local value, allowed = profile.raceID, false
            if not value or value <= 0 then return nil, "Waiting for race." end
            for _, race in ipairs(quest.allowedRaceIDs) do if race == value then allowed = true; break end end
            if not allowed then return false, "This quest has a different race requirement." end
        elseif mask and mask > 0 then
            local value = profile[requirement[2]]
            if not value or value <= 0 or value > 32 or not bit or type(bit.band) ~= "function" or type(bit.lshift) ~= "function" then
                return nil, "This quest's " .. requirement[3] .. " restriction still needs checking."
            end
            if bit.band(mask, bit.lshift(1, value - 1)) == 0 then return false, "This quest has a different " .. requirement[3] .. " requirement." end
        end
    end
    return true
end

function ns.CataloguePrerequisitesAllowed(id, key, query)
    local quest = ns.CatalogueQuest(id)
    if not quest then return true end
    key = key or ns.self
    for _, previous in ipairs(quest.prerequisiteAll or {}) do
        local complete = ns.CatalogueCompletion(key, previous, query)
        if complete == nil then return nil, "Checking history for " .. ns.QuestTitle(previous) .. "." end
        if not complete then return false, "Finish " .. ns.QuestTitle(previous) .. " first." end
    end
    if quest.prerequisiteAny then
        local met, unknown, titles = false, false, {}
        for _, previous in ipairs(quest.prerequisiteAny) do
            local complete = ns.CatalogueCompletion(key, previous, query)
            if complete == true then met = true end
            if complete == nil then unknown = true end
            titles[#titles + 1] = ns.QuestTitle(previous)
        end
        if not met then
            local reason = (unknown and "Checking prerequisite history: " or "Finish a prerequisite first: ") .. table.concat(titles, " / ") .. "."
            if unknown then return nil, reason end
            return false, reason
        end
    end
    if quest.previousQuest then
        local complete = ns.CatalogueCompletion(key or ns.self, quest.previousQuest, query)
        if complete == nil then return nil, "Checking history for " .. ns.QuestTitle(quest.previousQuest) .. "." end
        if not complete then return false, "Finish " .. ns.QuestTitle(quest.previousQuest) .. " first." end
    end
    return true
end

function ns.PickupOfferEvidence(key, id)
    if key == ns.self then
        local observed = ns.ObservedPickupAvailable and ns.ObservedPickupAvailable(id)
        if observed ~= nil then return observed end
        if ns.offered[id] == true then return true end
    else
        local member = ns.members[key]
        if member and not member.syncPending and member.activeRevision and member.offerRevision
            and member.offerRevision >= member.activeRevision and member.offered and member.offered[id] == true then return true end
        -- An empty peer list only describes their current NPC, not every giver.
    end
end

function ns.QuestGiverName(id)
    local quest, names, seen = ns.CatalogueQuest(id), {}, {}
    local observed = ns.NPCPickupPoint and ns.NPCPickupPoint(id)
    local function add(point)
        local name = point and ns.SafeTitle(point.name)
        if name and point.action ~= "start-item" and (point.npc or point.entityType == "npc") and not seen[name] then
            names[#names + 1], seen[name] = name, true
        end
    end
    add(observed)
    if #names == 0 then
        for _, point in ipairs(quest and quest.starts or {}) do add(point) end
        for _, point in ipairs(quest and quest.startRefs or {}) do add(point) end
    end
    if #names > 0 then return table.concat(names, " or ") end
end

-- The third result is a machine-readable reason for the confirmation UI.
-- Existing callers keep the two-result eligibility contract below.
function ns.CataloguePickupCheck(id, profile, key, query)
    local quest = ns.CatalogueQuest(id)
    if quest and (not profile or not profile.level or profile.level <= 0) then return nil, "Waiting for player level." end
    if quest and quest.minLevel and profile.level < quest.minLevel then return false, "Requires level " .. quest.minLevel .. "." end
    local identity, reason = ns.CatalogueIdentityAllowed(id, profile)
    if identity == false then return false, reason end
    key = key or ns.self
    local alternative, relation = alternativeTaken(id, key, query)
    if alternative and relation == "breadcrumb" then
        return false, "No longer offered: it only leads into " .. ns.QuestTitle(alternative) .. ", which is already underway or done.", "breadcrumb-superseded"
    elseif alternative then return false, "Already following the alternative " .. ns.QuestTitle(alternative) .. "." end
    -- Neither shareability nor an opened turn-in dialog proves remote pickup.
    -- Actual beta offers can contradict an explicitly marked older-world
    -- fallback gate. Published beta and tester prerequisites remain strict.
    local prerequisites, prerequisiteReason = ns.CataloguePrerequisitesAllowed(id, key, query)
    local offered = ns.PickupOfferEvidence(key, id)
    if offered == true and quest and quest.prerequisiteSource
        and (string.find(quest.prerequisiteSource, "^Identity%-matched unchanged quest:")
            or quest.prerequisiteSource == "Published converted-baseline prerequisites") then return true end
    if prerequisites ~= true then return prerequisites, prerequisiteReason end
    if offered == true then return true end
    if ns.LearnedPrerequisiteAllowed then
        local learned, learnedReason = ns.LearnedPrerequisiteAllowed(id, profile, key, query)
        if learned ~= true then return learned, learnedReason end
    end
    if offered == false then return false, "This quest giver did not offer this quest at your current progress. Recheck after progressing." end
    if quest and quest.pickupRequiresOffer then return false, "Confirm this quest at its NPC; its published eligibility is under review." end
    if identity ~= true then return identity, reason end
    if not quest then return true end
    if ns.catalogue.detailSource and quest.prerequisitesRead ~= true then
        return nil, "Pickup requirements are missing from the detailed data. Talk to the quest giver to check its offer."
    end
    if quest.prerequisitesUnverified then
        local giver = ns.QuestGiverName(id)
        return nil, "This quest has a branching prerequisite that still needs quest-giver confirmation. "
            .. (giver and ("Talk to " .. giver .. ".") or "The quest giver's name is not recorded."), "branching-prerequisite"
    end
    return true
end

function ns.CatalogueAllowed(id, profile, key, query)
    local allowed, reason = ns.CataloguePickupCheck(id, profile, key, query)
    if reason then return allowed, reason end
    return allowed
end

function ns.CataloguePrerequisiteIDs(id)
    local quest, ids, seen = ns.CatalogueQuest(id), {}, {}
    local function add(previous)
        if previous and not seen[previous] then ids[#ids + 1], seen[previous] = previous, true end
    end
    if quest then
        add(quest.previousQuest)
        for _, previous in ipairs(quest.prerequisiteAll or {}) do add(previous) end
        for _, previous in ipairs(quest.prerequisiteAny or quest.prerequisiteCandidates or {}) do add(previous) end
    end
    if ns.LearnedPrerequisiteIDs then
        for _, previous in ipairs(ns.LearnedPrerequisiteIDs(id)) do
            add(previous)
        end
    end
    return ids
end

function ns.CatalogueScopeIDs()
    local maps, ids = {}, {}
    if ns.profile and type(ns.profile.mapID) == "number" and ns.profile.mapID > 0 then maps[ns.profile.mapID] = true end
    for _, person in ipairs(ns.PartyProfiles and ns.PartyProfiles() or {}) do
        if person.profile and type(person.profile.mapID) == "number" and person.profile.mapID > 0 then maps[person.profile.mapID] = true end
        local member = ns.members[person.key]
        if member and type(member.catalogueMapID) == "number" and member.catalogueMapID > 0 then maps[member.catalogueMapID] = true end
    end
    if ns.libraryMapID then maps[ns.libraryMapID] = true end
    if ns.NearbyZoneMaps then
        for mapID in pairs(ns.NearbyZoneMaps(ns.profile and ns.profile.mapID or 0)) do maps[mapID] = true end
    end
    local keys = {}
    for mapID in pairs(maps) do keys[#keys + 1] = mapID end
    table.sort(keys)
    local signature = table.concat(keys, ",") .. ":" .. tostring(ns.char and ns.char.questLearning and ns.char.questLearning.revision or 0)
        .. ":" .. tostring(ns.Option("useLearnedQuests"))
    if signature == scopeSignature and scopeCatalogue == ns.catalogue then return scopeCache end
    local ordered = {}
    for id, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
        if quest.mapID and maps[quest.mapID] then ordered[#ordered + 1] = id end
    end
    table.sort(ordered)
    local count = 0
    local function add(id)
        if not ids[id] and count < 512 then ids[id] = true; count = count + 1 end
    end
    for index, id in ipairs(ordered) do
        if index > 400 then break end
        add(id)
        local quest = ns.CatalogueQuest(id)
        for _, previous in ipairs(quest.series or {}) do add(previous) end
        for _, previous in ipairs(ns.CataloguePrerequisiteIDs(id)) do add(previous) end
    end
    scopeCache, scopeSignature, scopeCatalogue = ids, signature, ns.catalogue
    return ids
end

function ns.CatalogueRecord(id)
    local quest = ns.CatalogueQuest(id)
    if not quest then return end
    local start = quest.starts and quest.starts[1]
    return {id = id, title = quest.title, level = quest.level or 0,
        mapID = start and start.mapID or quest.mapID or 0,
        x = start and start.x or 0, y = start and start.y or 0,
        npc = start and start.npc and start.name or "", source = "d", lineID = 0, lineName = "",
        difficulty = ns.QuestDifficultyLabel and ns.QuestDifficultyLabel(id),
        seriesRoot = quest.seriesRoot, seriesName = quest.seriesName, seriesPosition = quest.seriesPosition}
end

function ns.CatalogueGuideRecords()
    local records = {}
    for id in pairs(ns.CatalogueScopeIDs()) do
        local quest = ns.CatalogueQuest(id)
        if quest and quest.starts and #quest.starts > 0 and (not ns.LevelingQuestEnabled or ns.LevelingQuestEnabled(id)) then records[id] = ns.CatalogueRecord(id) end
    end
    return records
end

function ns.CatalogueZone(quest)
    if type(quest.zone) == "string" and quest.zone ~= "" then return quest.zone end
    local category = quest.categoryPath and string.match(quest.categoryPath, "([^/]+)$")
    if not category then return "Other quests" end
    local name = string.gsub(category, "-", " ")
    name = string.gsub(name, "(%a)([%w']*)", function(first, rest) return string.upper(first) .. rest end)
    return name
end

ns.libraryLevel = "all"
ns.LIBRARY_PAGE_SIZE = 24
function ns.LibraryLevelRange()
    if ns.libraryLevel == "party" then
        local lowest
        for _, person in ipairs(ns.PartyProfiles()) do
            local level = person.profile and person.profile.level
            if level and level > 0 then lowest = math.min(lowest or level, level) end
        end
        if lowest then return math.max(1, lowest - 3), lowest + 3 end
        return 0, 0
    end
    if ns.libraryLevel == "51+" then return 51, 255 end
    local low, high = string.match(ns.libraryLevel, "^(%d+)%-(%d+)$")
    return tonumber(low), tonumber(high)
end

function ns.SetLibraryLevel(value)
    ns.libraryLevel, ns.libraryPage = value, 1
    ns.ui.scroll:SetVerticalScroll(0)
    ns.Refresh()
end

function ns.ApplyLibrarySearch()
    ns.librarySearchGeneration = (ns.librarySearchGeneration or 0) + 1
    ns.librarySearch = ns.librarySearchDraft or ""
    ns.libraryPage = 1
    ns.ui.scroll:SetVerticalScroll(0)
    ns.Refresh()
end

function ns.QueueLibrarySearch(value)
    ns.librarySearchDraft = string.sub(value, 1, 100)
    ns.librarySearchGeneration = (ns.librarySearchGeneration or 0) + 1
    local generation = ns.librarySearchGeneration
    if C_Timer and type(C_Timer.After) == "function" then
        C_Timer.After(0.4, function()
            if generation == ns.librarySearchGeneration and ns.filter == "library" then ns.ApplyLibrarySearch() end
        end)
    end
end

local libraryIndex, indexedCatalogue
function ns.LibraryItems()
    if indexedCatalogue ~= ns.catalogue then
        libraryIndex, indexedCatalogue = {}, ns.catalogue
        for id, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do
            local zone = ns.CatalogueZone(quest)
            local class = ns.ClassQuestLabel(id) or ""
            libraryIndex[#libraryIndex + 1] = {id = id, quest = quest, zone = zone,
                zoneKey = quest.mapID and ("map:" .. quest.mapID) or ("zone:" .. zone),
                search = string.lower(quest.title .. " " .. zone .. " " .. class)}
        end
        table.sort(libraryIndex, function(a, b)
            if (a.quest.level or 0) ~= (b.quest.level or 0) then return (a.quest.level or 0) < (b.quest.level or 0) end
            return a.id < b.id
        end)
    end
    local query = string.lower(ns.librarySearch or "")
    local quests, zones = {}, {}
    local low, high = ns.LibraryLevelRange()
    local classOnly = ns.filter == "classquests"
    for _, item in ipairs(libraryIndex) do
        local quest, zone, zoneKey = item.quest, item.zone, item.zoneKey
        local level = quest.level
        local identity = ns.CatalogueIdentityAllowed(item.id, ns.profile)
        local classCategoryAllowed = not classOnly or ns.CatalogueClassCategoryAllowed(item.id, ns.profile) == true
        if (classOnly and ns.IsClassQuest(item.id) and identity == true and classCategoryAllowed
            or not classOnly and identity ~= false)
            and (not low or (level and level >= low and level <= high)) then
          if classOnly then item.availableNow = ns.CatalogueAllowed(item.id, ns.profile, ns.self) == true end
          if query ~= "" then
            if string.find(item.search, query, 1, true) then quests[#quests + 1] = item end
          elseif classOnly then quests[#quests + 1] = item
          elseif ns.libraryZone == zoneKey then quests[#quests + 1] = item
          elseif not ns.libraryZone then
            local group = zones[zoneKey]
            if not group then group = {zoneKey = zoneKey, zone = zone, mapID = quest.mapID, count = 0, mapped = 0}; zones[zoneKey] = group end
            group.count = group.count + 1
            if quest.starts then group.mapped = group.mapped + 1 end
          end
        end
    end
    if classOnly then
        table.sort(quests, function(a, b)
            if a.availableNow ~= b.availableNow then return a.availableNow end
            if (a.quest.level or 0) ~= (b.quest.level or 0) then return (a.quest.level or 0) < (b.quest.level or 0) end
            return a.id < b.id
        end)
    end
    if not classOnly and not ns.libraryZone and query == "" then
        local result = {}
        for _, zone in pairs(zones) do result[#result + 1] = zone end
        table.sort(result, function(a, b)
            local current = ns.profile and ns.profile.mapID
            if (a.mapID == current) ~= (b.mapID == current) then return a.mapID == current end
            if a.mapped ~= b.mapped then return a.mapped > b.mapped end
            return a.zone < b.zone
        end)
        return result
    end
    return quests
end

function ns.LibraryPageItems()
    local all, page = ns.LibraryItems(), ns.libraryPage or 1
    local pages = math.max(1, math.ceil(#all / ns.LIBRARY_PAGE_SIZE))
    ns.libraryPage = math.max(1, math.min(page, pages))
    local result = {}
    for index = (ns.libraryPage - 1) * ns.LIBRARY_PAGE_SIZE + 1, math.min(#all, ns.libraryPage * ns.LIBRARY_PAGE_SIZE) do result[#result + 1] = all[index] end
    return result, #all, pages
end

function ns.OpenLibraryZone(key, mapID)
    ns.libraryZone, ns.libraryMapID = key, mapID
    ns.librarySearch, ns.librarySearchDraft, ns.libraryPage = "", "", 1
    ns.librarySearchGeneration = (ns.librarySearchGeneration or 0) + 1
    if ns.ui.librarySearch then ns.ui.librarySearch:SetText("") end
    ns.SetFilter("library")
    ns.ScheduleSync()
end

local lastCatalogueMap
function ns.ResetCatalogueTraffic() lastCatalogueMap = nil end
function ns.SendCatalogueContext(force)
    local mapID = ns.libraryMapID or 0
    if (force or mapID ~= lastCatalogueMap) and ns.QueueMessage("1|Z|" .. mapID) then lastCatalogueMap = mapID end
end

function ns.ReceiveCatalogueMessage(message, sender)
    if string.sub(message, 1, 4) ~= "1|Z|" then return false end
    local mapID = tonumber(string.match(message, "^1|Z|(%d+)$"))
    if not ns.GuideInteger(mapID, 1000000) then return true, false, "invalid catalogue map" end
    local known = mapID == 0
    for _, quest in pairs(ns.catalogue and ns.catalogue.quests or {}) do if quest.mapID == mapID then known = true; break end end
    if not known then return true, false, "catalogue map not present" end
    ns.members[sender] = ns.members[sender] or {}
    ns.members[sender].catalogueMapID = mapID
    ns.ScheduleSync()
    return true, true
end

function ns.ShowQuestDetails(id)
    local quest = ns.CatalogueQuest(id)
    if not ns.questDetails then
        local window = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
        window:SetSize(570, 330)
        window:SetPoint("CENTER")
        window:SetClampedToScreen(true)
        window:SetFrameStrata("DIALOG")
        ns.UIPanel(window, ns.UIColors.background)
        ns.UIClose(window)
        window.title = window:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        window.title:SetPoint("TOPLEFT", 20, -22)
        window.title:SetWidth(510)
        window.title:SetJustifyH("LEFT")
        window.body = window:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
        window.body:SetPoint("TOPLEFT", 20, -66)
        window.body:SetWidth(520)
        window.body:SetJustifyH("LEFT")
        window.body:SetJustifyV("TOP")
        ns.questDetails = window
    end
    local lines = {}
    if quest then
        lines[#lines + 1] = ns.CatalogueZone(quest) .. " • Quest level " .. (quest.level or "unknown")
        lines[#lines + 1] = "Minimum level: " .. (quest.minLevel or "not supplied") .. " • Faction: " .. (quest.side or "not supplied")
        if ns.ClassQuestLabel(id) then lines[#lines + 1] = ns.ClassQuestLabel(id) end
        if ns.IsRepeatableQuest(id) then lines[#lines + 1] = "Repeatable quest; excluded from automatic leveling guides." end
        if quest.xp then lines[#lines + 1] = "Published base quest XP: " .. quest.xp .. "; actual reward varies by player level." end
        local low, high = ns.PreferredQuestLevels()
        if low then
            local _, reason = ns.LevelingValue(id)
            lines[#lines + 1] = "Preferred leveling quest levels: " .. low .. "–" .. high .. "."
            if reason then lines[#lines + 1] = reason end
        end
        for _, item in ipairs(quest.requiredItems or {}) do
            lines[#lines + 1] = "Bring " .. item.quantity .. " × " .. item.name .. (item.buyable and " • vendor-listed; check current availability" or " • item source not verified as buyable")
        end
        if quest.starts and quest.starts[1] then lines[#lines + 1] = "Start: " .. quest.starts[1].name end
        if quest.ends and quest.ends[1] then lines[#lines + 1] = "Return to: " .. quest.ends[1].name end
        if quest.objectiveAlternatives then lines[#lines + 1] = "Alternative farming locations are known; the guide chooses one per objective." end
        if quest.objectiveLocationsIncomplete then lines[#lines + 1] = "Some objective locations are still missing. Known areas and public quest-tracker locations are used when available." end
        local _, reason = ns.CatalogueAllowed(id, ns.profile, ns.self)
        if reason then lines[#lines + 1] = reason end
        if quest.previousQuest then
            lines[#lines + 1] = (quest.prerequisiteSource and "Reported prerequisite: " or "Published previous step: ") .. ns.QuestTitle(quest.previousQuest)
            if quest.prerequisiteSource then lines[#lines + 1] = quest.prerequisiteSource end
        end
        if quest.prerequisiteAny then
            local titles = {}; for _, previous in ipairs(quest.prerequisiteAny) do titles[#titles + 1] = ns.QuestTitle(previous) end
            lines[#lines + 1] = "Finish one published prerequisite variant: " .. table.concat(titles, " / ")
        end
        if quest.prerequisiteAll then
            local titles = {}; for _, previous in ipairs(quest.prerequisiteAll) do titles[#titles + 1] = ns.QuestTitle(previous) end
            lines[#lines + 1] = "Finish all prerequisites: " .. table.concat(titles, ", ")
        end
        lines[#lines + 1] = ""
        lines[#lines + 1] = quest.starts and "Published map points come from the captured Forever sources and marked fallbacks. Check them against this beta build."
            or "The source has no quest-giver coordinates for this quest. A client marker or an NPC encounter can add a map destination."
    else lines[#lines + 1] = "This quest is not in the imported catalogue yet. Live party quest data is still available." end
    lines[#lines + 1] = "History and known requirements guide suggestions; the quest giver confirms pickup availability."
    ns.questDetails.title:SetText(ns.QuestTitle(id))
    ns.questDetails.body:SetText(table.concat(lines, "\n\n"))
    ns.questDetails:SetHeight(math.min(700, math.max(330, ns.questDetails.body:GetStringHeight() + 96)))
    ns.questDetails:Show()
end
