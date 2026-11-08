local addonName, ns = ...

-- The TOC is the only place a version is typed. The literal fallback exists
-- for builds whose metadata API is unavailable; keep it equal to the TOC.
local function metadata(field)
    local reader = C_AddOns and C_AddOns.GetAddOnMetadata or GetAddOnMetadata
    if type(reader) ~= "function" then return end
    local okay, value = pcall(reader, addonName, field)
    if okay and type(value) == "string" and value ~= "" then return value end
end
ns.VERSION = metadata("Version") or "0.8.104"
ns.RELEASE_NAME = metadata("X-ReleaseName") or "PARTY QUEST DIGEST"
ns.handlers = {}
ns.eventFailures = {}
ns.members = {}
ns.status = "Waiting for addon initialization."
ns.frame = CreateFrame("Frame")

function ns.Public(value)
    return not issecretvalue or not issecretvalue(value)
end

function ns.Print(message)
    if ns.Public(message) then
        DEFAULT_CHAT_FRAME:AddMessage("|cff66ccffWow Together:|r " .. message)
    end
end

function ns.Refresh(background)
    ns.objectiveDisplayRevision = (ns.objectiveDisplayRevision or 0) + 1
    local query = ns.NewQuestQuery and ns.NewQuestQuery()
    -- Guide progress belongs to the guide, not to dashboard rendering. Keep it
    -- current with a hidden/resizing window, and share this read pass with UI.
    if ns.UpdateSelectedRoute then ns.UpdateSelectedRoute(nil, query) end
    if ns.UpdateGuideQuestFocus then ns.UpdateGuideQuestFocus() end
    if ns.UpdateGuideQuestItem then ns.UpdateGuideQuestItem() end
    if ns.ui and ns.ui.resizing then ns.ui.resizeDirty = true
    elseif ns.Render and (not background or ns.window and ns.window:IsShown()) then
        if background and ns.QueueBackgroundRender then ns.QueueBackgroundRender()
        else ns.Render(query, true) end
    end
    if ns.RenderTracker then ns.RenderTracker() end
    if ns.RenderGuideQuestList then ns.RenderGuideQuestList() end
    if ns.UpdateNavigation then ns.UpdateNavigation() end
    if ns.ScheduleActivitySuggestions then ns.ScheduleActivitySuggestions() end
    if ns.QueuePartyRouteFollow then ns.QueuePartyRouteFollow() end
    if ns.SchedulePartyCatchup then ns.SchedulePartyCatchup() end
    if ns.SaveSelectedGuide then ns.SaveSelectedGuide() end
    if ns.CaptureSessionCheckpoint then ns.CaptureSessionCheckpoint() end
end

-- Event storms often request the same route, tracker and dashboard refresh in
-- one frame. Coalesce background invalidations, while keeping explicit UI
-- actions on the synchronous Refresh path.
ns.refreshStats = {requested = 0, coalesced = 0, completed = 0}
local refreshPending, refreshQueued, refreshBackground = false, false, true
function ns.ScheduleRefresh(background)
    ns.refreshStats.requested = ns.refreshStats.requested + 1
    if refreshPending then
        ns.refreshStats.coalesced = ns.refreshStats.coalesced + 1
        refreshQueued = true
        refreshBackground = refreshBackground and background == true
        return
    end
    refreshPending, refreshQueued, refreshBackground = true, false, background == true
    ns.refreshStats.completed = ns.refreshStats.completed + 1
    ns.Refresh(background == true)
    local function finishBurst()
        local useBackground, queued = refreshBackground, refreshQueued
        refreshPending, refreshQueued, refreshBackground = false, false, true
        if not queued then return end
        ns.refreshStats.completed = ns.refreshStats.completed + 1
        ns.Refresh(useBackground)
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0.04, finishBurst)
    else finishBurst() end
end

local progressPending = false
ns.guideProgressStats = {updates = 0, coalesced = 0, retries = 0}
function ns.ScheduleGuideProgress()
    if not ns.db or not C_Timer or type(C_Timer.After) ~= "function" then return end
    ns.guideProgressRevision = (ns.guideProgressRevision or 0) + 1
    if progressPending then ns.guideProgressStats.coalesced = ns.guideProgressStats.coalesced + 1; return end
    progressPending = true
    local attempts = 0
    local function update()
        -- Clear before running reads/handlers so a surfaced Lua error cannot
        -- permanently suppress subsequent events. A new event takes precedence
        -- over this callback's bounded retry.
        progressPending = false
        if ns.guideScanning then return end
        attempts = attempts + 1
        local ready = ns.ReadQuests()
        -- Read objectives/destinations only after a complete quest-log snapshot.
        if ready then ns.ReadGuide() end
        ns.guideProgressStats.updates = ns.guideProgressStats.updates + 1
        ns.ScheduleRefresh(true)
        if not ready and attempts < 3 and not progressPending then
            progressPending = true
            ns.guideProgressStats.retries = ns.guideProgressStats.retries + 1
            C_Timer.After(0.25 * attempts, update)
        end
    end
    C_Timer.After(0.1, update)
end

-- Every module may subscribe to the same event; handlers run in
-- registration order. Registering the same function twice is a no-op, so an
-- initializer that runs again does not double-subscribe. The frame itself
-- registers each event once: some builds return false for a repeat.
function ns.On(event, handler)
    if type(handler) ~= "function" then return false end
    local list = ns.handlers[event]
    if list then
        for _, existing in ipairs(list) do if existing == handler then return true end end
        list[#list + 1] = handler
        ns.eventFailures[event] = nil
        return true
    end
    -- Beta builds may omit otherwise documented events. This only catches
    -- event-registration errors; it does not wrap handlers or protected actions.
    local validate = C_EventUtils and C_EventUtils.IsEventValid
    if type(validate) == "function" then
        local ok, valid = pcall(validate, event)
        if ok and ns.Public(valid) and valid == false then
            ns.eventFailures[event] = "unsupported"
            return false
        end
    end
    local ok, registered = pcall(ns.frame.RegisterEvent, ns.frame, event)
    if not ok or not ns.Public(registered) or registered ~= true then
        ns.eventFailures[event] = "registration rejected"
        return false
    end
    ns.eventFailures[event] = nil
    ns.handlers[event] = {handler}
    return true
end

ns.frame:SetScript("OnEvent", function(_, event, ...)
    local list = ns.handlers[event]
    if not list then return end
    for index = 1, #list do list[index](...) end
end)

function ns.Diagnostics()
    local lines = {"Wow Together " .. ns.VERSION .. " — beta capability and sync report", ""}
    local function output(line) lines[#lines + 1] = line end
    local version, build, _, interface = GetBuildInfo()
    local function readable(value)
        if not ns.Public(value) then return "restricted" end
        return tostring(value or "unknown")
    end
    output("Client " .. readable(version) .. ", build " .. readable(build)
        .. ", interface " .. readable(interface) .. ". Expected beta interface: 16001.")
    output("Project " .. readable(WOW_PROJECT_ID) .. ", expansion "
        .. readable(LE_EXPANSION_LEVEL_CURRENT) .. "; neither alone selects compatibility.")
    local probes = {
        {"C_QuestLog.GetNumQuestLogEntries", C_QuestLog and C_QuestLog.GetNumQuestLogEntries},
        {"C_QuestLog.GetInfo", C_QuestLog and C_QuestLog.GetInfo},
        {"C_QuestLog.SetSelectedQuest", C_QuestLog and C_QuestLog.SetSelectedQuest},
        {"C_QuestLog.GetSelectedQuest", C_QuestLog and C_QuestLog.GetSelectedQuest},
        {"C_QuestLog.GetLogIndexForQuestID", C_QuestLog and C_QuestLog.GetLogIndexForQuestID},
        {"GetQuestLogSpecialItemInfo", GetQuestLogSpecialItemInfo},
        {"UseQuestLogSpecialItem", UseQuestLogSpecialItem},
        {"QuestMapFrame_ShowQuestDetails", QuestMapFrame_ShowQuestDetails},
        {"C_SuperTrack.SetSuperTrackedQuestID", C_SuperTrack and C_SuperTrack.SetSuperTrackedQuestID},
        {"C_QuestLog.IsQuestFlaggedCompleted", C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted},
        {"C_ChatInfo.IsAddonMessagePrefixRegistered", C_ChatInfo and C_ChatInfo.IsAddonMessagePrefixRegistered},
        {"C_ChatInfo.RegisterAddonMessagePrefix", C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix},
        {"C_ChatInfo.SendAddonMessage", C_ChatInfo and C_ChatInfo.SendAddonMessage},
        {"UnitLevel", UnitLevel},
        {"UnitXP", UnitXP},
        {"UnitXPMax", UnitXPMax},
        {"UnitFactionGroup", UnitFactionGroup},
        {"UnitName", UnitName},
        {"UnitClass", UnitClass},
        {"UnitRace", UnitRace},
        {"GetQuestID", GetQuestID},
        {"GetTitleText", GetTitleText},
        {"C_Map.GetBestMapForUnit", C_Map and C_Map.GetBestMapForUnit},
        {"C_Map.GetPlayerMapPosition", C_Map and C_Map.GetPlayerMapPosition},
        {"C_Map.GetMapInfo", C_Map and C_Map.GetMapInfo},
        {"IsInInstance", IsInInstance},
        {"IsFalling", IsFalling},
        {"GetBindLocation", GetBindLocation},
        {"GetItemCooldown / C_Container.GetItemCooldown", GetItemCooldown or C_Container and C_Container.GetItemCooldown},
        {"IsSpellKnown", IsSpellKnown},
        {"GetInstanceInfo", GetInstanceInfo},
        {"EJ_GetInstanceByIndex", EJ_GetInstanceByIndex},
        {"EJ_GetInstanceInfo", EJ_GetInstanceInfo},
        {"EJ_GetEncounterInfoByIndex", EJ_GetEncounterInfoByIndex},
        {"EJ_GetEncounterInfo", EJ_GetEncounterInfo},
        {"EJ_GetCreatureInfo", EJ_GetCreatureInfo},
        {"C_EncounterJournal.GetEncountersOnMap", C_EncounterJournal and C_EncounterJournal.GetEncountersOnMap},
        {"C_Map.GetMapArtLayers", C_Map and C_Map.GetMapArtLayers},
        {"C_Map.GetMapArtLayerTextures", C_Map and C_Map.GetMapArtLayerTextures},
        {"C_Map.GetMapGroupID", C_Map and C_Map.GetMapGroupID},
        {"C_Map.GetMapGroupMembersInfo", C_Map and C_Map.GetMapGroupMembersInfo},
        {"C_Map.GetMapWorldSize", C_Map and C_Map.GetMapWorldSize},
        {"GetPlayerFacing", GetPlayerFacing},
        {"UnitPosition", UnitPosition},
        {"C_LFGList.GetSearchResults", C_LFGList and C_LFGList.GetSearchResults},
        {"C_LFGList.GetFilteredSearchResults", C_LFGList and C_LFGList.GetFilteredSearchResults},
        {"C_LFGList.GetSearchResultPlayerInfo", C_LFGList and C_LFGList.GetSearchResultPlayerInfo},
        {"C_LFGList.GetSearchResultMemberInfo", C_LFGList and C_LFGList.GetSearchResultMemberInfo},
        {"C_LFGList.GetApplicants", C_LFGList and C_LFGList.GetApplicants},
        {"C_LFGList.GetSearchResultInfo", C_LFGList and C_LFGList.GetSearchResultInfo},
        {"C_LFGList.GetApplicantInfo", C_LFGList and C_LFGList.GetApplicantInfo},
        {"C_LFGList.GetApplicantMemberInfo", C_LFGList and C_LFGList.GetApplicantMemberInfo},
        {"C_Map.GetWorldPosFromMapPos", C_Map and C_Map.GetWorldPosFromMapPos},
        {"C_Map.GetMapLinksForMap", C_Map and C_Map.GetMapLinksForMap},
        {"CreateVector2D", CreateVector2D},
        {"C_Map.CanSetUserWaypointOnMap", C_Map and C_Map.CanSetUserWaypointOnMap},
        {"C_QuestLine.GetAvailableQuestLines", C_QuestLine and C_QuestLine.GetAvailableQuestLines},
        {"C_QuestLine.GetQuestLineInfo", C_QuestLine and C_QuestLine.GetQuestLineInfo},
        {"C_QuestLine.GetQuestLineQuests", C_QuestLine and C_QuestLine.GetQuestLineQuests},
        {"EJ_GetInstanceByIndex", EJ_GetInstanceByIndex},
        {"EJ_GetInstanceInfo", EJ_GetInstanceInfo},
        {"C_Texture.GetFilenameFromFileDataID", C_Texture and C_Texture.GetFilenameFromFileDataID},
        {"C_QuestLine.RequestQuestLinesForMap", C_QuestLine and C_QuestLine.RequestQuestLinesForMap},
        {"C_QuestLog.GetQuestDifficultyLevel", C_QuestLog and C_QuestLog.GetQuestDifficultyLevel},
        {"C_QuestLog.GetQuestsOnMap", C_QuestLog and C_QuestLog.GetQuestsOnMap},
        {"C_QuestLog.GetNextWaypoint", C_QuestLog and C_QuestLog.GetNextWaypoint},
        {"C_QuestLog.GetTitleForQuestID", C_QuestLog and C_QuestLog.GetTitleForQuestID},
        {"C_QuestLog.IsComplete", C_QuestLog and C_QuestLog.IsComplete},
        {"C_QuestLog.GetQuestObjectives", C_QuestLog and C_QuestLog.GetQuestObjectives},
        {"IsPushableQuest (sharing only; unused by planner)", IsPushableQuest},
        {"C_QuestLog.IsPushableQuest (sharing only; unused by planner)", C_QuestLog and C_QuestLog.IsPushableQuest},
        {"C_NamePlate.GetNamePlateForUnit", C_NamePlate and C_NamePlate.GetNamePlateForUnit},
        {"C_NamePlate.GetNamePlates", C_NamePlate and C_NamePlate.GetNamePlates},
        {"C_QuestLog.UnitIsRelatedToActiveQuest", C_QuestLog and C_QuestLog.UnitIsRelatedToActiveQuest},
        {"AcceptQuest", AcceptQuest},
        {"CanAcceptQuest", CanAcceptQuest},
        {"IsQuestCompletable (opened turn-in dialog only)", IsQuestCompletable},
        {"CompleteQuest", CompleteQuest},
        {"GetNumQuestChoices", GetNumQuestChoices},
        {"GetQuestReward", GetQuestReward},
        {"C_Item.GetItemInfo", C_Item and C_Item.GetItemInfo},
        {"C_Item.GetItemCount", C_Item and C_Item.GetItemCount},
        {"C_Item.RequestLoadItemDataByID", C_Item and C_Item.RequestLoadItemDataByID},
        {"C_TradeSkillUI.GetAllRecipeIDs", C_TradeSkillUI and C_TradeSkillUI.GetAllRecipeIDs},
        {"C_TradeSkillUI.OpenTradeSkill", C_TradeSkillUI and C_TradeSkillUI.OpenTradeSkill},
        {"GetProfessions", GetProfessions},
        {"GetProfessionInfo", GetProfessionInfo},
        {"GetNumTrainerServices", GetNumTrainerServices},
        {"GetTrainerServiceInfo", GetTrainerServiceInfo},
        {"GetMerchantNumItems", GetMerchantNumItems},
        {"GetMerchantItemInfo", GetMerchantItemInfo},
        {"GetMerchantItemLink", GetMerchantItemLink},
        {"C_MerchantFrame.GetItemInfo", C_MerchantFrame and C_MerchantFrame.GetItemInfo},
        {"C_Container.GetContainerNumSlots", C_Container and C_Container.GetContainerNumSlots},
        {"C_Container.GetContainerNumFreeSlots", C_Container and C_Container.GetContainerNumFreeSlots},
        {"C_Container.GetContainerItemInfo", C_Container and C_Container.GetContainerItemInfo},
        {"GetInventoryItemDurability", GetInventoryItemDurability},
        {"CanMerchantRepair", CanMerchantRepair},
        {"C_TradeSkillUI.GetRecipeInfo", C_TradeSkillUI and C_TradeSkillUI.GetRecipeInfo},
        {"C_TradeSkillUI.GetRecipeSchematic", C_TradeSkillUI and C_TradeSkillUI.GetRecipeSchematic},
        {"C_TradeSkillUI.GetChildProfessionInfo", C_TradeSkillUI and C_TradeSkillUI.GetChildProfessionInfo},
        {"C_TradeSkillUI.GetBaseProfessionInfo", C_TradeSkillUI and C_TradeSkillUI.GetBaseProfessionInfo},
        {"C_AuctionHouse.GetCommoditySearchResultInfo", C_AuctionHouse and C_AuctionHouse.GetCommoditySearchResultInfo},
        {"C_AuctionHouse.GetNumCommoditySearchResults", C_AuctionHouse and C_AuctionHouse.GetNumCommoditySearchResults},
        {"C_AuctionHouse.MakeItemKey", C_AuctionHouse and C_AuctionHouse.MakeItemKey},
        {"C_AuctionHouse.SendSearchQuery", C_AuctionHouse and C_AuctionHouse.SendSearchQuery},
        {"C_AuctionHouse.HasFullCommoditySearchResults", C_AuctionHouse and C_AuctionHouse.HasFullCommoditySearchResults},
        {"C_AuctionHouse.HasFullItemSearchResults", C_AuctionHouse and C_AuctionHouse.HasFullItemSearchResults},
        {"C_AuctionHouse.RequestMoreCommoditySearchResults", C_AuctionHouse and C_AuctionHouse.RequestMoreCommoditySearchResults},
        {"C_AuctionHouse.RequestMoreItemSearchResults", C_AuctionHouse and C_AuctionHouse.RequestMoreItemSearchResults},
        {"GetServerTime", GetServerTime},
        {"GetRealmName", GetRealmName},
        {"C_AuctionHouse.SendBrowseQuery", C_AuctionHouse and C_AuctionHouse.SendBrowseQuery},
        {"C_AuctionHouse.IsThrottledMessageSystemReady", C_AuctionHouse and C_AuctionHouse.IsThrottledMessageSystemReady},
        {"C_AuctionHouse.GetNumItemSearchResults", C_AuctionHouse and C_AuctionHouse.GetNumItemSearchResults},
        {"C_AuctionHouse.GetItemSearchResultInfo", C_AuctionHouse and C_AuctionHouse.GetItemSearchResultInfo},
        {"QueryAuctionItems", QueryAuctionItems},
        {"CanSendAuctionQuery", CanSendAuctionQuery},
        {"GetAuctionItemInfo", GetAuctionItemInfo},
        {"UnitGUID", UnitGUID},
        {"C_GossipInfo.GetAvailableQuests", C_GossipInfo and C_GossipInfo.GetAvailableQuests},
        {"C_GossipInfo.GetActiveQuests", C_GossipInfo and C_GossipInfo.GetActiveQuests},
        {"C_GossipInfo.SelectAvailableQuest", C_GossipInfo and C_GossipInfo.SelectAvailableQuest},
        {"C_GossipInfo.SelectActiveQuest", C_GossipInfo and C_GossipInfo.SelectActiveQuest},
        {"GetNumAvailableQuests", GetNumAvailableQuests},
        {"GetAvailableQuestInfo", GetAvailableQuestInfo},
        {"GetAvailableTitle", GetAvailableTitle}, {"SelectAvailableQuest", SelectAvailableQuest},
        {"C_TaxiMap.GetAllTaxiNodes", C_TaxiMap and C_TaxiMap.GetAllTaxiNodes},
        {"GetTaxiMapID", GetTaxiMapID},
        {"FlightMapFrame.GetMapID", FlightMapFrame and FlightMapFrame.GetMapID},
        {"C_TaxiMap.GetTaxiNodesForMap", C_TaxiMap and C_TaxiMap.GetTaxiNodesForMap},
        {"C_Map.GetMapPosFromWorldPos", C_Map and C_Map.GetMapPosFromWorldPos},
        {"TakeTaxiNode", TakeTaxiNode}, {"GetNumRoutes", GetNumRoutes}, {"TaxiGetNodeSlot", TaxiGetNodeSlot},
        {"UnitOnTaxi", UnitOnTaxi}, {"GetUnitSpeed", GetUnitSpeed},
        {"GetTime", GetTime}, {"UnitIsGhost", UnitIsGhost}, {"GetBindLocation", GetBindLocation},
        {"GetSubZoneText", GetSubZoneText},
        {"C_DeathInfo.GetCorpseMapPosition", C_DeathInfo and C_DeathInfo.GetCorpseMapPosition},
        {"TooltipDataProcessor.AddTooltipPostCall", TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall},
        {"C_Map.SetUserWaypoint", C_Map and C_Map.SetUserWaypoint},
        {"C_Map.GetUserWaypoint", C_Map and C_Map.GetUserWaypoint},
        {"C_Map.ClearUserWaypoint", C_Map and C_Map.ClearUserWaypoint},
        {"UiMapPoint.CreateFromCoordinates", UiMapPoint and UiMapPoint.CreateFromCoordinates},
        {"issecretvalue", issecretvalue},
        {"loadstring (Lua checks)", loadstring},
        {"setfenv (Lua checks)", setfenv},
        {"C_Timer.After", C_Timer and C_Timer.After},
        {"C_EventUtils.IsEventValid", C_EventUtils and C_EventUtils.IsEventValid},
        {"WorldMapFrame.GetCanvas", WorldMapFrame and WorldMapFrame.GetCanvas},
        {"WorldMapFrame.GetCanvasContainer", WorldMapFrame and WorldMapFrame.GetCanvasContainer},
        {"WorldMapFrame.GetViewRect", WorldMapFrame and WorldMapFrame.GetViewRect},
        {"WorldMapFrame.AddDataProvider", WorldMapFrame and WorldMapFrame.AddDataProvider},
        {"WorldMapFrame.GetMapID", WorldMapFrame and WorldMapFrame.GetMapID},
        {"Frame.CreateLine", ns.frame.CreateLine},
        {"Frame.SetClipsChildren", ns.frame.SetClipsChildren},
        {"Frame.SetIgnoreParentAlpha", ns.frame.SetIgnoreParentAlpha},
    }
    for _, probe in ipairs(probes) do
        output(probe[1] .. ": " .. (type(probe[2]) == "function" and "present" or "missing"))
    end
    output("MapCanvasDataProviderMixin: " .. (type(MapCanvasDataProviderMixin) == "table" and "present" or "missing"))
    output("Presence is not proof of working behavior. No waypoint or protected action was called.")
    local unavailable = {}
    for event, reason in pairs(ns.eventFailures) do unavailable[#unavailable + 1] = event .. " (" .. reason .. ")" end
    table.sort(unavailable)
    output("Unavailable event registrations: " .. (#unavailable > 0 and table.concat(unavailable, ", ") or "none"))
    ns.SyncDiagnostics(output)
    output("Personal guide updates: " .. ns.guideProgressStats.updates .. " refreshes; "
        .. ns.guideProgressStats.coalesced .. " overlapping events batched; "
        .. ns.guideProgressStats.retries .. " quest-log retries. Dashboard work is deferred while hidden/resizing.")
    output("Refresh scheduler: " .. ns.refreshStats.requested .. " requests; " .. ns.refreshStats.coalesced
        .. " coalesced; " .. ns.refreshStats.completed .. " passes.")
    output("Scan guide: fresh quest log, objectives and history; fixed order retained. Useful lower-level prerequisites explain their unlock.")
    ns.NavigationDiagnostics(output)
    if ns.MinimapRouteDiagnostics then ns.MinimapRouteDiagnostics(output) end
    ns.GuideReasonDiagnostics(output)
    ns.QuestItemDiagnostics(output)
    if ns.ObjectiveLearningDiagnostics then ns.ObjectiveLearningDiagnostics(output) end
    ns.GuideTipDiagnostics(output)
    ns.ClassTrainingDiagnostics(output)
    ns.InventoryServiceDiagnostics(output)
    ns.DungeonArtworkDiagnostics(output)
    ns.DungeonViewerDiagnostics(output)
    ns.GroupFinderRoleDiagnostics(output)
    ns.ApproachMapDiagnostics(output)
    output("Unit numbers: " .. ns.unitNumbersStatus)
    local low, high = ns.PreferredQuestLevels()
    if low then
        local level, _, name = ns.PartyLevelFloor()
        output("Leveling quest band: " .. low .. "–" .. high .. "; lowest synced player: " .. name .. " (level " .. level .. ").")
    else output("Leveling quest band: waiting for public character level.") end
    local xpState = ns.XPState and ns.XPState()
    if xpState then
        local guide = ns.routeSelection or ns.routeSelectionCandidate
        local remaining = guide and ns.ZoneXPRemaining and ns.ZoneXPRemaining(guide, ns.profile)
        local projection = guide and ns.ZoneExitProjection and ns.ZoneExitProjection(guide, ns.profile)
        output("XP model: level " .. xpState.level .. " (" .. math.floor(xpState.xp / xpState.xpMax * 100) .. "%), rested "
            .. xpState.rested .. "; zone remaining " .. tostring(remaining or "unknown")
            .. ", projected exit " .. tostring(projection and projection.level or "unknown")
            .. (projection and projection.percent and (" (" .. math.floor(projection.percent * 100) .. "%)") or ""))
    end
    output("Travel: " .. ns.travelStatus)
    ns.TravelDiagnostics(output)
    ns.NPCPickupDiagnostics(output)
    ns.GuideQuestFocusDiagnostics(output)
    output("Guide restore: " .. ns.guideResumeStatus)
    if ns.GuideSessionSummaryText then output("Guide session: " .. ns.GuideSessionSummaryText()) end
    output("Party catch-up: " .. ns.partyCatchupStatus)
    ns.ResearchDiagnostics(output)
    ns.MemoryDiagnostics(output)
    ns.ShowDiagnostics(table.concat(lines, "\n"))
end

local CHARACTER_STORES = {"flights", "questHistory", "guideState", "guideSkips", "questResearch",
    "questResearchObserverIDs", "questLearning", "guideSessions", "classTraining", "professions",
    "inventoryServiceCharacters", "pickupRechecks", "confirmationWaypoints"}

local function copySaved(value, depth)
    if type(value) ~= "table" then return value end
    depth = (depth or 0) + 1
    if depth > 24 then return nil end
    local result = {}
    for key, child in pairs(value) do
        if type(key) == "string" or type(key) == "number" then
            local copied = copySaved(child, depth)
            if copied ~= nil then result[key] = copied end
        end
    end
    return result
end

local function hasSavedValue(value, depth)
    if type(value) ~= "table" then return value ~= nil end
    depth = (depth or 0) + 1
    if depth > 24 then return false end
    for _, child in pairs(value) do if hasSavedValue(child, depth) then return true end end
    return false
end

local function currentBuildFaction()
    local _, build = ns.ReadPublic(GetBuildInfo)
    local faction = ns.ReadPublic(UnitFactionGroup, "player")
    if type(build) ~= "string" and type(build) ~= "number" then build = "unknown" end
    if faction ~= "Horde" and faction ~= "Alliance" then faction = "unknown" end
    return tostring(build), faction
end

function ns.MigrateCharacterStorage()
    if type(WowTogetherCharDB) ~= "table" then WowTogetherCharDB = {} end
    ns.char = WowTogetherCharDB
    if ns.char.schema ~= 2 then
        for _, store in ipairs(CHARACTER_STORES) do
            local old = ns.db[store]
            local empty = type(ns.char[store]) ~= "table" or not hasSavedValue(ns.char[store])
            if type(old) == "table" and type(old[ns.self]) == "table" and empty then
                ns.char[store] = copySaved(old[ns.self])
            end
        end
        local oldServices = ns.db.guideServices and ns.db.guideServices[ns.self]
        if type(oldServices) == "table" then
            ns.char.guideServices = type(ns.char.guideServices) == "table" and ns.char.guideServices or {}
            if ns.char.guideServices.boundInnID == nil then ns.char.guideServices.boundInnID = oldServices.boundInnID end
            ns.char.guideServices.dismissed = type(ns.char.guideServices.dismissed) == "table"
                and ns.char.guideServices.dismissed or copySaved(oldServices.dismissed or {})
        end
        ns.char.schema = 2
    end

    local build, faction = currentBuildFaction()
    local migrateWorld = ns.db.schema ~= 2
    ns.db.innLocations = type(ns.db.innLocations) == "table" and ns.db.innLocations or {}
    local inns = ns.db.innLocations[build]
    if type(inns) ~= "table" then inns = {}; ns.db.innLocations[build] = inns end
    if migrateWorld then
        for _, services in pairs(type(ns.db.guideServices) == "table" and ns.db.guideServices or {}) do
            for id, inn in pairs(type(services) == "table" and type(services.inns) == "table" and services.inns or {}) do
                if type(inn) == "table" and type(id) == "string" and type(inn.mapID) == "number"
                    and type(inn.x) == "number" and type(inn.y) == "number" and inns[id] == nil then
                    inns[id] = copySaved(inn)
                end
            end
        end

        -- Preserve old positive offer observations under the current build while
        -- isolating their unknown faction and old offer context. They are not
        -- actionable on a character until that context is observed anew.
        ns.db.offerKnowledgeBuilds = type(ns.db.offerKnowledgeBuilds) == "table" and ns.db.offerKnowledgeBuilds or {}
        for _, knowledge in pairs(type(ns.db.offerKnowledge) == "table" and ns.db.offerKnowledge or {}) do
            local byFaction = ns.db.offerKnowledgeBuilds[build]
            if type(byFaction) ~= "table" then byFaction = {}; ns.db.offerKnowledgeBuilds[build] = byFaction end
            local byHash = byFaction.unknown
            if type(byHash) ~= "table" then byHash = {}; byFaction.unknown = byHash end
            for npcID, fact in pairs(type(knowledge) == "table" and knowledge or {}) do
                if type(fact) == "table" and type(fact.offered) == "table" then
                    local hash = "legacy:" .. tostring(fact.context or "unknown")
                    local byQuest = byHash[hash]
                    if type(byQuest) ~= "table" then byQuest = {}; byHash[hash] = byQuest end
                    for questID in pairs(fact.offered) do
                        if ns.GuideInteger(tonumber(questID)) and tonumber(questID) > 0 then
                            byQuest[tonumber(questID)] = byQuest[tonumber(questID)] or {}
                            if ns.GuideInteger(tonumber(npcID)) then
                                byQuest[tonumber(questID)][tonumber(npcID)] = {offered = true, observers = 1, legacy = true}
                            end
                        end
                    end
                end
            end
        end
    end
    ns.worldBuild, ns.worldFaction = build, faction
    ns.db.schema = 2
end

ns.On("ADDON_LOADED", function(name)
    if name ~= addonName then
        if name == "Blizzard_EncounterJournal" and ns.db then ns.RefreshDungeonArtwork() end
        return
    end
    if type(WowTogetherDB) ~= "table" then WowTogetherDB = {} end
    WowTogetherDB.version = 1
    ns.db = WowTogetherDB
    ns.InitializeConfig()
    ns.InitializeUnitNumbers()
    ns.CreateUI()
    ns.CreateSettings()
    ns.CreateMinimap()
    ns.CreateMinimapRoute()
    ns.ReadQuests()
    ns.InitializeSync()
    ns.MigrateCharacterStorage()
    ns.InitializeQuestHistory()
    ns.InitializeGuideXP()
    ns.InitializeGuideControls()
    ns.InitializeTravel()
    ns.InitializeTravelTrails()
    ns.InitializeGuideTips()
    ns.InitializeClassTraining()
    ns.InitializeItemHints()
    ns.InitializeOffers()
    ns.InitializeNPCPickups()
    ns.InitializeObjectiveLearning()
    ns.InitializeQuestResearch()
    ns.InitializeQuestLearning()
    ns.InitializeGuide()
    ns.ReadProgress()
    ns.CreateTracker()
    ns.CreateNavigation()
    ns.InitializeGuidePersistence()
    if ns.InitializeProfessionGuides then ns.InitializeProfessionGuides() end
    ns.InitializeAuctionMarket()
    ns.InitializeDungeonViewer()
    ns.InitializeApproachMaps()
    ns.InitializeGroupFinderRoles()
    ns.InitializeInventoryServices()
    ns.InitializeSessionCheckpoints()
    ns.Refresh()
    ns.Print("Loaded. /wt opens the quest view; /wt probe opens diagnostics.")
end)

ns.On("PLAYER_LOGIN", function()
    ns.ReadProfile(); ns.InitializeAuctionMarket()
    ns.RestoreSavedGuide(); ns.RefreshDungeonArtwork(); ns.ScheduleFlightDiscovery(); ns.ScheduleSync()
end)
ns.On("QUEST_LOG_UPDATE", function()
    ns.ScheduleSync()
end)
ns.On("ZONE_CHANGED_NEW_AREA", function()
    ns.ResetZoneConnections(); ns.ReadGuide(); ns.ScheduleFlightDiscovery(); ns.ScheduleSync(); ns.ScheduleRefresh(true)
end)
ns.On("PLAYER_LEVEL_UP", function(level)
    ns.ReadGuideXP(); ns.RecordQuestResearch("level", {level = level}); ns.ScheduleSync()
    if ns.QueueProfessionUpdate then ns.QueueProfessionUpdate() end
end)
ns.On("QUEST_ACCEPTED", function(_, id)
    ns.ForgetQuestCompletion(id)
    ns.NoteQuestAccepted(id)
    ns.RecordQuestResearch("accept", {questID = id})
    if ns.GuideInteger(id) then ns.offered[id] = nil end
    ns.autoGossipAttempt, ns.autoAcceptAttempt = nil, nil
    ns.ScheduleSync()
end)
ns.On("QUEST_TURNED_IN", function(id)
    ns.RememberQuestCompletion(id)
    ns.NoteQuestTurnedIn(id)
    ns.RecordQuestResearch("turn-in", {questID = id})
    ns.InvalidateNPCOffers()
    ns.activityRevision = (ns.activityRevision or 0) + 1; ns.ScheduleSync()
end)
ns.On("QUEST_REMOVED", function(id) ns.NoteQuestRemoved(id); ns.ScheduleSync() end)
ns.On("UPDATE_FACTION", function()
    ns.RecordQuestResearch("reputation")
    ns.InvalidateNPCOffers(); ns.ScheduleSync()
end)
ns.On("GROUP_ROSTER_UPDATE", function()
    if not ns.PartyFeaturesEnabled() then return end
    ns.UpdateRoster()
    ns.RenderTracker()
    ns.ScheduleSync()
end)

SLASH_WOWTOGETHER1 = "/wt"
SLASH_WOWTOGETHER2 = "/wowtogether"
SlashCmdList.WOWTOGETHER = function(command)
    command = string.lower(command or "")
    if command == "probe" then ns.Diagnostics()
    elseif command == "sync" then ns.SyncNow(true)
    elseif command == "lua" then ns.ShowLuaConsole()
    elseif command == "minimap" then ns.ToggleMinimap()
    elseif command == "tracker" then ns.ToggleTracker()
    elseif command == "arrow" then ns.ToggleNavigation()
    elseif command == "config" then ns.ToggleSettings()
    elseif command == "route clear" then ns.ClearRoute(); ns.Refresh()
    elseif command == "guide reset" then ns.ResetGuideSkips()
    elseif command == "guide scan" then ns.ScanGuideProgress()
    elseif command == "train done" then ns.FinishClassTraining(true)
    elseif command == "train skip" then ns.FinishClassTraining(false)
    elseif command == "catchup" then ns.ShowPartyCatchup(nil, true)
    elseif command == "research" then ns.ShowQuestResearch()
    elseif command == "findings" then ns.ShowGuideFindings()
    elseif command == "questlines" then ns.ShowQuestLineReport()
    elseif command == "roads" or string.sub(command, 1, 6) == "roads " then ns.TravelTrailCommand(string.sub(command, 7))
    else ns.ToggleWindow() end
end
