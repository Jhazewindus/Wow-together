local addonName, ns = ...

local scopeCache, scopeSignature, scopeCatalogue

function ns.CatalogueQuest(id)
    return ns.catalogue and ns.catalogue.quests[id]
end

function ns.CatalogueCompletion(key, id)
    if key == ns.self then return ns.Completed(id) end
    local member = ns.members[key]
    if member and member.completed and member.completed[id] then return true end
    if member and member.historyRevision and member.historyRevision == member.completionRevision
        and member.activeRevision and member.completionRevision >= member.activeRevision and not member.syncPending
        and member.historyChecked and member.historyChecked[id] then return false end
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
        if mask and mask > 0 then
            local value = profile[requirement[2]]
            if not value or value <= 0 or value > 32 or not bit or type(bit.band) ~= "function" or type(bit.lshift) ~= "function" then
                return nil, "This quest's " .. requirement[3] .. " restriction still needs checking."
            end
            if bit.band(mask, bit.lshift(1, value - 1)) == 0 then return false, "This quest has a different " .. requirement[3] .. " requirement." end
        end
    end
    return true
end

function ns.CatalogueAllowed(id, profile, key)
    local quest = ns.CatalogueQuest(id)
    if not quest then return true end
    if not profile or not profile.level or profile.level <= 0 then return nil, "Waiting for player level." end
    if quest.minLevel and profile.level < quest.minLevel then return false, "Requires level " .. quest.minLevel .. "." end
    local identity, reason = ns.CatalogueIdentityAllowed(id, profile)
    if identity ~= true then return identity, reason end
    key = key or ns.self
    if key == ns.self and ns.ObservedPickupAvailable then
        local observed = ns.ObservedPickupAvailable(id)
        if observed == false then return false, "This quest giver did not offer this quest at your current progress. Recheck after progressing." end
        if observed == true then return true end
    end
    if ns.catalogue.detailSource and quest.prerequisitesRead ~= true then
        return nil, "Pickup requirements are missing from the detailed data. Talk to the quest giver to check its offer."
    end
    if quest.prerequisitesUnverified then
        return nil, "This quest has a branching prerequisite that still needs quest-giver confirmation."
    end
    if quest.prerequisiteAny then
        local unknown, titles = false, {}
        for _, previous in ipairs(quest.prerequisiteAny) do
            local complete = ns.CatalogueCompletion(key, previous)
            if complete == true then return true end
            if complete == nil then unknown = true end
            titles[#titles + 1] = ns.QuestTitle(previous)
        end
        local reason = (unknown and "Checking prerequisite history: " or "Finish a prerequisite first: ") .. table.concat(titles, " / ") .. "."
        if unknown then return nil, reason end
        return false, reason
    end
    if quest.previousQuest then
        local complete = ns.CatalogueCompletion(key or ns.self, quest.previousQuest)
        if complete == nil then return nil, "Checking history for " .. ns.QuestTitle(quest.previousQuest) .. "." end
        if not complete then return false, "Finish " .. ns.QuestTitle(quest.previousQuest) .. " first." end
    end
    return true
end

function ns.CataloguePrerequisiteIDs(id)
    local quest, ids = ns.CatalogueQuest(id), {}
    if quest then
        if quest.previousQuest then ids[#ids + 1] = quest.previousQuest end
        for _, previous in ipairs(quest.prerequisiteAny or quest.prerequisiteCandidates or {}) do ids[#ids + 1] = previous end
    end
    return ids
end

function ns.CatalogueScopeIDs()
    local maps, ids = {}, {}
    if ns.profile and ns.profile.mapID > 0 then maps[ns.profile.mapID] = true end
    for _, person in ipairs(ns.PartyProfiles and ns.PartyProfiles() or {}) do
        if person.profile and person.profile.mapID > 0 then maps[person.profile.mapID] = true end
        local member = ns.members[person.key]
        if member and member.catalogueMapID and member.catalogueMapID > 0 then maps[member.catalogueMapID] = true end
    end
    if ns.libraryMapID then maps[ns.libraryMapID] = true end
    if ns.NearbyZoneMaps then
        for mapID in pairs(ns.NearbyZoneMaps(ns.profile and ns.profile.mapID or 0)) do maps[mapID] = true end
    end
    local keys = {}
    for mapID in pairs(maps) do keys[#keys + 1] = mapID end
    table.sort(keys)
    local signature = table.concat(keys, ",")
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
    return category and string.gsub(category, "-", " ") or "Other quests"
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
            libraryIndex[#libraryIndex + 1] = {id = id, quest = quest, zone = zone,
                zoneKey = quest.mapID and ("map:" .. quest.mapID) or ("zone:" .. zone), search = string.lower(quest.title .. " " .. zone)}
        end
        table.sort(libraryIndex, function(a, b)
            if (a.quest.level or 0) ~= (b.quest.level or 0) then return (a.quest.level or 0) < (b.quest.level or 0) end
            return a.id < b.id
        end)
    end
    local query = string.lower(ns.librarySearch or "")
    local quests, zones = {}, {}
    local low, high = ns.LibraryLevelRange()
    for _, item in ipairs(libraryIndex) do
        local quest, zone, zoneKey = item.quest, item.zone, item.zoneKey
        local level = quest.level
        if ns.CatalogueIdentityAllowed(item.id, ns.profile) ~= false and (not low or (level and level >= low and level <= high)) then
          if query ~= "" then
            if string.find(item.search, query, 1, true) then quests[#quests + 1] = item end
          elseif ns.libraryZone == zoneKey then quests[#quests + 1] = item
          elseif not ns.libraryZone then
            local group = zones[zoneKey]
            if not group then group = {zoneKey = zoneKey, zone = zone, mapID = quest.mapID, count = 0, mapped = 0}; zones[zoneKey] = group end
            group.count = group.count + 1
            if quest.starts then group.mapped = group.mapped + 1 end
          end
        end
    end
    if not ns.libraryZone and query == "" then
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
        window:SetBackdrop({bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1})
        window:SetBackdropColor(0.035, 0.045, 0.06, 0.98)
        window:SetBackdropBorderColor(0.93, 0.73, 0.39, 1)
        local close = CreateFrame("Button", nil, window, "UIPanelCloseButton")
        close:SetPoint("TOPRIGHT", -4, -4)
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
        for _, item in ipairs(quest.requiredItems or {}) do
            lines[#lines + 1] = "Bring " .. item.quantity .. " × " .. item.name .. (item.buyable and " • vendor-listed; check current availability" or " • item source not verified as buyable")
        end
        if quest.starts and quest.starts[1] then lines[#lines + 1] = "Start: " .. quest.starts[1].name end
        if quest.ends and quest.ends[1] then lines[#lines + 1] = "Return to: " .. quest.ends[1].name end
        if quest.objectiveLocationsIncomplete then lines[#lines + 1] = "Some objective locations are missing or have several possible item-drop sources. Only clear destinations are routed." end
        local _, reason = ns.CatalogueAllowed(id, ns.profile, ns.self)
        if reason then lines[#lines + 1] = reason end
        if quest.previousQuest then lines[#lines + 1] = "Published previous step: " .. ns.QuestTitle(quest.previousQuest) end
        if quest.prerequisiteAny then
            local titles = {}; for _, previous in ipairs(quest.prerequisiteAny) do titles[#titles + 1] = ns.QuestTitle(previous) end
            lines[#lines + 1] = "Finish one published prerequisite variant: " .. table.concat(titles, " / ")
        end
        lines[#lines + 1] = ""
        lines[#lines + 1] = quest.starts and "Published map points come from Wowhead's Forever pages. Check them against this beta build."
            or "The source has no quest-giver coordinates for this quest. A client marker or an NPC encounter can add a map destination."
    else lines[#lines + 1] = "This quest is not in the imported catalogue yet. Live party quest data is still available." end
    lines[#lines + 1] = "History and known requirements guide suggestions; the quest giver confirms pickup availability."
    ns.questDetails.title:SetText(ns.QuestTitle(id))
    ns.questDetails.body:SetText(table.concat(lines, "\n\n"))
    ns.questDetails:SetHeight(math.min(700, math.max(330, ns.questDetails.body:GetStringHeight() + 96)))
    ns.questDetails:Show()
end
