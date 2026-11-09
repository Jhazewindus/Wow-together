local addonName, ns = ...

-- Release identity comes only from the TOC metadata.
local function metadata(field)
    local reader = C_AddOns and C_AddOns.GetAddOnMetadata or GetAddOnMetadata
    if type(reader) ~= "function" then return end
    local okay, value = pcall(reader, addonName, field)
    if okay and type(value) == "string" and value ~= "" then return value end
end
ns.VERSION = metadata("Version") or "dev"
if ns.VERSION == "@project-version@" then ns.VERSION = "dev" end
ns.RELEASE_NAME = metadata("X-ReleaseName") or ""
ns.hooks = {
    optionGet = {}, optionSet = {}, uiCreated = {}, settingsCreated = {}, render = {},
    slash = {}, diagnostics = {}, syncReceive = {}, routeBeforeUpdate = {},
    routeAfterUpdate = {}, stopIcon = {}, stopSymbol = {}, destinationDecision = {},
    stepPresentation = {}, researchExport = {}, goldPrice = {}, goldSuggestions = {},
    goldSessionCard = {}, goldFunctionPublished = {},
    hubTabs = {}, hubTabRegistered = {},
}
function ns.HookResults(name, ...)
    local results = {}
    for _, callback in ipairs(ns.hooks[name] or {}) do
        local ok, value = pcall(callback, ...)
        if ok and value ~= nil then results[#results + 1] = value end
    end
    return results
end
function ns.FirstHook(name, ...)
    for _, callback in ipairs(ns.hooks[name] or {}) do
        local ok, handled, value, extra = pcall(callback, ...)
        if ok and handled then return true, value, extra end
    end
    return false
end
function ns.RunHooks(name, ...)
    for _, callback in ipairs(ns.hooks[name] or {}) do pcall(callback, ...) end
end
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

local diagnosticsProbes = {
            {"C_QuestLog.GetNumQuestLogEntries", function() return C_QuestLog and C_QuestLog.GetNumQuestLogEntries end},
            {"C_QuestLog.GetInfo", function() return C_QuestLog and C_QuestLog.GetInfo end},
            {"C_QuestLog.SetSelectedQuest", function() return C_QuestLog and C_QuestLog.SetSelectedQuest end},
            {"C_QuestLog.GetSelectedQuest", function() return C_QuestLog and C_QuestLog.GetSelectedQuest end},
            {"C_QuestLog.GetLogIndexForQuestID", function() return C_QuestLog and C_QuestLog.GetLogIndexForQuestID end},
            {"GetQuestLogSpecialItemInfo", function() return GetQuestLogSpecialItemInfo end},
            {"UseQuestLogSpecialItem", function() return UseQuestLogSpecialItem end},
            {"QuestMapFrame_ShowQuestDetails", function() return QuestMapFrame_ShowQuestDetails end},
            {"C_SuperTrack.SetSuperTrackedQuestID", function() return C_SuperTrack and C_SuperTrack.SetSuperTrackedQuestID end},
            {"C_QuestLog.IsQuestFlaggedCompleted", function() return C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted end},
            {"C_ChatInfo.IsAddonMessagePrefixRegistered", function() return C_ChatInfo and C_ChatInfo.IsAddonMessagePrefixRegistered end},
            {"C_ChatInfo.RegisterAddonMessagePrefix", function() return C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix end},
            {"C_ChatInfo.SendAddonMessage", function() return C_ChatInfo and C_ChatInfo.SendAddonMessage end},
            {"UnitLevel", function() return UnitLevel end},
            {"UnitXP", function() return UnitXP end},
            {"UnitXPMax", function() return UnitXPMax end},
            {"UnitFactionGroup", function() return UnitFactionGroup end},
            {"UnitName", function() return UnitName end},
            {"UnitClass", function() return UnitClass end},
            {"UnitRace", function() return UnitRace end},
            {"GetQuestID", function() return GetQuestID end},
            {"GetTitleText", function() return GetTitleText end},
            {"C_Map.GetBestMapForUnit", function() return C_Map and C_Map.GetBestMapForUnit end},
            {"C_Map.GetPlayerMapPosition", function() return C_Map and C_Map.GetPlayerMapPosition end},
            {"C_Map.GetMapInfo", function() return C_Map and C_Map.GetMapInfo end},
            {"IsInInstance", function() return IsInInstance end},
            {"IsFalling", function() return IsFalling end},
            {"GetBindLocation", function() return GetBindLocation end},
            {"GetItemCooldown / C_Container.GetItemCooldown", function() return GetItemCooldown or C_Container and C_Container.GetItemCooldown end},
            {"IsSpellKnown", function() return IsSpellKnown end},
            {"GetInstanceInfo", function() return GetInstanceInfo end},
            {"EJ_GetInstanceByIndex", function() return EJ_GetInstanceByIndex end},
            {"EJ_GetInstanceInfo", function() return EJ_GetInstanceInfo end},
            {"EJ_GetEncounterInfoByIndex", function() return EJ_GetEncounterInfoByIndex end},
            {"EJ_GetEncounterInfo", function() return EJ_GetEncounterInfo end},
            {"EJ_GetCreatureInfo", function() return EJ_GetCreatureInfo end},
            {"C_EncounterJournal.GetEncountersOnMap", function() return C_EncounterJournal and C_EncounterJournal.GetEncountersOnMap end},
            {"C_Map.GetMapArtLayers", function() return C_Map and C_Map.GetMapArtLayers end},
            {"C_Map.GetMapArtLayerTextures", function() return C_Map and C_Map.GetMapArtLayerTextures end},
            {"C_Map.GetMapGroupID", function() return C_Map and C_Map.GetMapGroupID end},
            {"C_Map.GetMapGroupMembersInfo", function() return C_Map and C_Map.GetMapGroupMembersInfo end},
            {"C_Map.GetMapWorldSize", function() return C_Map and C_Map.GetMapWorldSize end},
            {"GetPlayerFacing", function() return GetPlayerFacing end},
            {"UnitPosition", function() return UnitPosition end},
            {"C_LFGList.GetSearchResults", function() return C_LFGList and C_LFGList.GetSearchResults end},
            {"C_LFGList.GetFilteredSearchResults", function() return C_LFGList and C_LFGList.GetFilteredSearchResults end},
            {"C_LFGList.GetSearchResultPlayerInfo", function() return C_LFGList and C_LFGList.GetSearchResultPlayerInfo end},
            {"C_LFGList.GetSearchResultMemberInfo", function() return C_LFGList and C_LFGList.GetSearchResultMemberInfo end},
            {"C_LFGList.GetApplicants", function() return C_LFGList and C_LFGList.GetApplicants end},
            {"C_LFGList.GetSearchResultInfo", function() return C_LFGList and C_LFGList.GetSearchResultInfo end},
            {"C_LFGList.GetApplicantInfo", function() return C_LFGList and C_LFGList.GetApplicantInfo end},
            {"C_LFGList.GetApplicantMemberInfo", function() return C_LFGList and C_LFGList.GetApplicantMemberInfo end},
            {"C_Map.GetWorldPosFromMapPos", function() return C_Map and C_Map.GetWorldPosFromMapPos end},
            {"C_Map.GetMapLinksForMap", function() return C_Map and C_Map.GetMapLinksForMap end},
            {"CreateVector2D", function() return CreateVector2D end},
            {"C_Map.CanSetUserWaypointOnMap", function() return C_Map and C_Map.CanSetUserWaypointOnMap end},
            {"C_QuestLine.GetAvailableQuestLines", function() return C_QuestLine and C_QuestLine.GetAvailableQuestLines end},
            {"C_QuestLine.GetQuestLineInfo", function() return C_QuestLine and C_QuestLine.GetQuestLineInfo end},
            {"C_QuestLine.GetQuestLineQuests", function() return C_QuestLine and C_QuestLine.GetQuestLineQuests end},
            {"EJ_GetInstanceByIndex", function() return EJ_GetInstanceByIndex end},
            {"EJ_GetInstanceInfo", function() return EJ_GetInstanceInfo end},
            {"C_Texture.GetFilenameFromFileDataID", function() return C_Texture and C_Texture.GetFilenameFromFileDataID end},
            {"C_QuestLine.RequestQuestLinesForMap", function() return C_QuestLine and C_QuestLine.RequestQuestLinesForMap end},
            {"C_QuestLog.GetQuestDifficultyLevel", function() return C_QuestLog and C_QuestLog.GetQuestDifficultyLevel end},
            {"C_QuestLog.GetQuestsOnMap", function() return C_QuestLog and C_QuestLog.GetQuestsOnMap end},
            {"C_QuestLog.GetNextWaypoint", function() return C_QuestLog and C_QuestLog.GetNextWaypoint end},
            {"C_QuestLog.GetTitleForQuestID", function() return C_QuestLog and C_QuestLog.GetTitleForQuestID end},
            {"C_QuestLog.IsComplete", function() return C_QuestLog and C_QuestLog.IsComplete end},
            {"C_QuestLog.GetQuestObjectives", function() return C_QuestLog and C_QuestLog.GetQuestObjectives end},
            {"IsPushableQuest (sharing only; unused by planner)", function() return IsPushableQuest end},
            {"C_QuestLog.IsPushableQuest (sharing only; unused by planner)", function() return C_QuestLog and C_QuestLog.IsPushableQuest end},
            {"C_NamePlate.GetNamePlateForUnit", function() return C_NamePlate and C_NamePlate.GetNamePlateForUnit end},
            {"C_NamePlate.GetNamePlates", function() return C_NamePlate and C_NamePlate.GetNamePlates end},
            {"C_QuestLog.UnitIsRelatedToActiveQuest", function() return C_QuestLog and C_QuestLog.UnitIsRelatedToActiveQuest end},
            {"AcceptQuest", function() return AcceptQuest end},
            {"CanAcceptQuest", function() return CanAcceptQuest end},
            {"IsQuestCompletable (opened turn-in dialog only)", function() return IsQuestCompletable end},
            {"CompleteQuest", function() return CompleteQuest end},
            {"GetNumQuestChoices", function() return GetNumQuestChoices end},
            {"GetQuestReward", function() return GetQuestReward end},
            {"C_Item.GetItemInfo", function() return C_Item and C_Item.GetItemInfo end},
            {"C_Item.GetItemCount", function() return C_Item and C_Item.GetItemCount end},
            {"C_Item.RequestLoadItemDataByID", function() return C_Item and C_Item.RequestLoadItemDataByID end},
            {"C_TradeSkillUI.GetAllRecipeIDs", function() return C_TradeSkillUI and C_TradeSkillUI.GetAllRecipeIDs end},
            {"C_TradeSkillUI.OpenTradeSkill", function() return C_TradeSkillUI and C_TradeSkillUI.OpenTradeSkill end},
            {"GetProfessions", function() return GetProfessions end},
            {"GetProfessionInfo", function() return GetProfessionInfo end},
            {"GetNumTrainerServices", function() return GetNumTrainerServices end},
            {"GetTrainerServiceInfo", function() return GetTrainerServiceInfo end},
            {"GetMerchantNumItems", function() return GetMerchantNumItems end},
            {"GetMerchantItemInfo", function() return GetMerchantItemInfo end},
            {"GetMerchantItemLink", function() return GetMerchantItemLink end},
            {"C_MerchantFrame.GetItemInfo", function() return C_MerchantFrame and C_MerchantFrame.GetItemInfo end},
            {"C_Container.GetContainerNumSlots", function() return C_Container and C_Container.GetContainerNumSlots end},
            {"C_Container.GetContainerNumFreeSlots", function() return C_Container and C_Container.GetContainerNumFreeSlots end},
            {"C_Container.GetContainerItemInfo", function() return C_Container and C_Container.GetContainerItemInfo end},
            {"GetInventoryItemDurability", function() return GetInventoryItemDurability end},
            {"CanMerchantRepair", function() return CanMerchantRepair end},
            {"C_TradeSkillUI.GetRecipeInfo", function() return C_TradeSkillUI and C_TradeSkillUI.GetRecipeInfo end},
            {"C_TradeSkillUI.GetRecipeSchematic", function() return C_TradeSkillUI and C_TradeSkillUI.GetRecipeSchematic end},
            {"C_TradeSkillUI.GetChildProfessionInfo", function() return C_TradeSkillUI and C_TradeSkillUI.GetChildProfessionInfo end},
            {"C_TradeSkillUI.GetBaseProfessionInfo", function() return C_TradeSkillUI and C_TradeSkillUI.GetBaseProfessionInfo end},
            {"C_AuctionHouse.GetCommoditySearchResultInfo", function() return C_AuctionHouse and C_AuctionHouse.GetCommoditySearchResultInfo end},
            {"C_AuctionHouse.GetNumCommoditySearchResults", function() return C_AuctionHouse and C_AuctionHouse.GetNumCommoditySearchResults end},
            {"C_AuctionHouse.MakeItemKey", function() return C_AuctionHouse and C_AuctionHouse.MakeItemKey end},
            {"C_AuctionHouse.SendSearchQuery", function() return C_AuctionHouse and C_AuctionHouse.SendSearchQuery end},
            {"C_AuctionHouse.HasFullCommoditySearchResults", function() return C_AuctionHouse and C_AuctionHouse.HasFullCommoditySearchResults end},
            {"C_AuctionHouse.HasFullItemSearchResults", function() return C_AuctionHouse and C_AuctionHouse.HasFullItemSearchResults end},
            {"C_AuctionHouse.RequestMoreCommoditySearchResults", function() return C_AuctionHouse and C_AuctionHouse.RequestMoreCommoditySearchResults end},
            {"C_AuctionHouse.RequestMoreItemSearchResults", function() return C_AuctionHouse and C_AuctionHouse.RequestMoreItemSearchResults end},
            {"GetServerTime", function() return GetServerTime end},
            {"GetRealmName", function() return GetRealmName end},
            {"C_AuctionHouse.SendBrowseQuery", function() return C_AuctionHouse and C_AuctionHouse.SendBrowseQuery end},
            {"C_AuctionHouse.IsThrottledMessageSystemReady", function() return C_AuctionHouse and C_AuctionHouse.IsThrottledMessageSystemReady end},
            {"C_AuctionHouse.GetNumItemSearchResults", function() return C_AuctionHouse and C_AuctionHouse.GetNumItemSearchResults end},
            {"C_AuctionHouse.GetItemSearchResultInfo", function() return C_AuctionHouse and C_AuctionHouse.GetItemSearchResultInfo end},
            {"QueryAuctionItems", function() return QueryAuctionItems end},
            {"CanSendAuctionQuery", function() return CanSendAuctionQuery end},
            {"GetAuctionItemInfo", function() return GetAuctionItemInfo end},
            {"UnitGUID", function() return UnitGUID end},
            {"C_GossipInfo.GetAvailableQuests", function() return C_GossipInfo and C_GossipInfo.GetAvailableQuests end},
            {"C_GossipInfo.GetActiveQuests", function() return C_GossipInfo and C_GossipInfo.GetActiveQuests end},
            {"C_GossipInfo.SelectAvailableQuest", function() return C_GossipInfo and C_GossipInfo.SelectAvailableQuest end},
            {"C_GossipInfo.SelectActiveQuest", function() return C_GossipInfo and C_GossipInfo.SelectActiveQuest end},
            {"GetNumAvailableQuests", function() return GetNumAvailableQuests end},
            {"GetAvailableQuestInfo", function() return GetAvailableQuestInfo end},
            {"GetAvailableTitle", function() return GetAvailableTitle end}, {"SelectAvailableQuest", function() return SelectAvailableQuest end},
            {"C_TaxiMap.GetAllTaxiNodes", function() return C_TaxiMap and C_TaxiMap.GetAllTaxiNodes end},
            {"GetTaxiMapID", function() return GetTaxiMapID end},
            {"FlightMapFrame.GetMapID", function() return FlightMapFrame and FlightMapFrame.GetMapID end},
            {"C_TaxiMap.GetTaxiNodesForMap", function() return C_TaxiMap and C_TaxiMap.GetTaxiNodesForMap end},
            {"C_Map.GetMapPosFromWorldPos", function() return C_Map and C_Map.GetMapPosFromWorldPos end},
            {"TakeTaxiNode", function() return TakeTaxiNode end}, {"GetNumRoutes", function() return GetNumRoutes end}, {"TaxiGetNodeSlot", function() return TaxiGetNodeSlot end},
            {"UnitOnTaxi", function() return UnitOnTaxi end}, {"GetUnitSpeed", function() return GetUnitSpeed end},
            {"GetTime", function() return GetTime end}, {"UnitIsGhost", function() return UnitIsGhost end}, {"GetBindLocation", function() return GetBindLocation end},
            {"GetSubZoneText", function() return GetSubZoneText end},
            {"C_DeathInfo.GetCorpseMapPosition", function() return C_DeathInfo and C_DeathInfo.GetCorpseMapPosition end},
            {"TooltipDataProcessor.AddTooltipPostCall", function() return TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall end},
            {"C_Map.SetUserWaypoint", function() return C_Map and C_Map.SetUserWaypoint end},
            {"C_Map.GetUserWaypoint", function() return C_Map and C_Map.GetUserWaypoint end},
            {"C_Map.ClearUserWaypoint", function() return C_Map and C_Map.ClearUserWaypoint end},
            {"UiMapPoint.CreateFromCoordinates", function() return UiMapPoint and UiMapPoint.CreateFromCoordinates end},
            {"issecretvalue", function() return issecretvalue end},
            {"loadstring (Lua checks)", function() return loadstring end},
            {"setfenv (Lua checks)", function() return setfenv end},
            {"C_Timer.After", function() return C_Timer and C_Timer.After end},
            {"C_EventUtils.IsEventValid", function() return C_EventUtils and C_EventUtils.IsEventValid end},
            {"WorldMapFrame.GetCanvas", function() return WorldMapFrame and WorldMapFrame.GetCanvas end},
            {"WorldMapFrame.GetCanvasContainer", function() return WorldMapFrame and WorldMapFrame.GetCanvasContainer end},
            {"WorldMapFrame.GetViewRect", function() return WorldMapFrame and WorldMapFrame.GetViewRect end},
            {"WorldMapFrame.AddDataProvider", function() return WorldMapFrame and WorldMapFrame.AddDataProvider end},
            {"WorldMapFrame.GetMapID", function() return WorldMapFrame and WorldMapFrame.GetMapID end},
            {"Frame.CreateLine", function() return ns.frame.CreateLine end},
            {"Frame.SetClipsChildren", function() return ns.frame.SetClipsChildren end},
            {"Frame.SetIgnoreParentAlpha", function() return ns.frame.SetIgnoreParentAlpha end},
        }

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
    for _, probe in ipairs(diagnosticsProbes) do
        output(probe[1] .. ": " .. (type(probe[2]()) == "function" and "present" or "missing"))
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
    output("XP model: " .. (ns.XPDiagnosticsText and ns.XPDiagnosticsText() or "not computed yet"))
    output("Travel: " .. ns.travelStatus)
    ns.TravelDiagnostics(output, true)
    ns.NPCPickupDiagnostics(output)
    ns.GuideQuestFocusDiagnostics(output)
    output("Guide restore: " .. ns.guideResumeStatus)
    if ns.GuideSessionSummaryText then output("Guide session: " .. ns.GuideSessionSummaryText()) end
    output("Party catch-up: " .. ns.partyCatchupStatus)
    ns.ResearchDiagnostics(output)
    ns.MemoryDiagnostics(output)
    ns.ShowDiagnostics(table.concat(lines, "\n"))
end

local CHARACTER_STORES = {"flights", "questHistory", "guideState", "guideModes", "guideSkips", "questResearch", "xpSamples",
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
    if ns.SyncStateInitialize then ns.SyncStateInitialize() end
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

ns.On("PLAYER_LOGOUT", function()
    if ns.SyncStatePersistAll then ns.SyncStatePersistAll() end
end)

ns.On("PLAYER_LOGIN", function()
    ns.ReadProfile(); ns.InitializeAuctionMarket()
    if ns.db and ns.db.config and ns.db.config.soloMode == true
        and ns.db.config.partyMode == "never" and ns.db.config.soloModePartyNotice ~= true then
        ns.db.config.soloModePartyNotice = true
        ns.Print("Your saved Solo mode keeps party features off. Set Settings > Party mode to Ask me if you want party prompts.")
    end
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
ns.On("QUEST_TURNED_IN", function(id, xpReward)
    ns.RememberQuestCompletion(id)
    ns.NoteQuestTurnedIn(id)
    if ns.RecordQuestXPSample then ns.RecordQuestXPSample(id, xpReward) end
    ns.RecordQuestResearch("turn-in", {questID = id, xpReward = xpReward})
    ns.InvalidateNPCOffers()
    ns.activityRevision = (ns.activityRevision or 0) + 1; ns.ScheduleSync()
end)
ns.On("QUEST_REMOVED", function(id) ns.NoteQuestRemoved(id); ns.ScheduleSync() end)
ns.On("UPDATE_FACTION", function()
    ns.RecordQuestResearch("reputation")
    ns.InvalidateNPCOffers(); ns.ScheduleSync()
end)
ns.On("GROUP_ROSTER_UPDATE", function()
    if ns.HandlePartyModeRoster then ns.HandlePartyModeRoster() end
    if not ns.PartyFeaturesEnabled() then return end
    ns.UpdateRoster()
    ns.RenderTracker()
    ns.ScheduleSync()
end)

SLASH_WOWTOGETHER1 = "/wt"
SLASH_WOWTOGETHER2 = "/wowtogether"
SlashCmdList.WOWTOGETHER = function(command)
    command = string.lower(command or "")
    local handled, result = ns.FirstHook("slash", command)
    if handled then return result end
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
