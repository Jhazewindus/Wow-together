local addonName, ns = ...

ns.VERSION = "0.8.55"
ns.RELEASE_NAME = "SMALL CRAFTING STEPS"
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
        ns.Refresh(true)
        if not ready and attempts < 3 and not progressPending then
            progressPending = true
            ns.guideProgressStats.retries = ns.guideProgressStats.retries + 1
            C_Timer.After(0.25 * attempts, update)
        end
    end
    C_Timer.After(0.1, update)
end

function ns.On(event, handler)
    -- A successful subscription belongs to this one dispatch frame. Updating
    -- its handler must not register it again: some builds return false for an
    -- already registered event. Explicit unsubscription clears the handler.
    if ns.handlers[event] then
        ns.handlers[event], ns.eventFailures[event] = handler, nil
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
    ns.handlers[event] = handler
    return true
end

ns.frame:SetScript("OnEvent", function(_, event, ...)
    local handler = ns.handlers[event]
    if handler then handler(...) end
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
    output("Scan guide: fresh quest log, objectives and history; fixed order retained. Useful lower-level prerequisites explain their unlock.")
    ns.NavigationDiagnostics(output)
    ns.GuideReasonDiagnostics(output)
    ns.QuestItemDiagnostics(output)
    ns.GuideTipDiagnostics(output)
    ns.ClassTrainingDiagnostics(output)
    ns.DungeonArtworkDiagnostics(output)
    ns.DungeonViewerDiagnostics(output)
    local low, high = ns.PreferredQuestLevels()
    if low then
        local level, _, name = ns.PartyLevelFloor()
        output("Leveling quest band: " .. low .. "–" .. high .. "; lowest synced player: " .. name .. " (level " .. level .. ").")
    else output("Leveling quest band: waiting for public character level.") end
    output("Travel: " .. ns.travelStatus)
    ns.TravelDiagnostics(output)
    ns.NPCPickupDiagnostics(output)
    ns.GuideQuestFocusDiagnostics(output)
    output("Guide restore: " .. ns.guideResumeStatus)
    output("Party catch-up: " .. ns.partyCatchupStatus)
    ns.ResearchDiagnostics(output)
    ns.MemoryDiagnostics(output)
    ns.ShowDiagnostics(table.concat(lines, "\n"))
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
    ns.CreateUI()
    ns.CreateSettings()
    ns.CreateMinimap()
    ns.ReadQuests()
    ns.InitializeSync()
    ns.InitializeQuestHistory()
    ns.InitializeGuideXP()
    ns.InitializeGuideControls()
    ns.InitializeTravel()
    ns.InitializeGuideTips()
    ns.InitializeClassTraining()
    ns.InitializeItemHints()
    ns.InitializeOffers()
    ns.InitializeNPCPickups()
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
    ns.ResetZoneConnections(); ns.ReadGuide(); ns.ScheduleFlightDiscovery(); ns.ScheduleSync(); ns.Refresh(true)
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
    else ns.ToggleWindow() end
end
