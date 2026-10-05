local addonName, ns = ...

ns.VERSION = "0.7.4"
ns.handlers = {}
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

function ns.Refresh()
    if ns.ui and ns.ui.resizing then ns.ui.resizeDirty = true
    elseif ns.Render then ns.Render() end
    if ns.RenderTracker then ns.RenderTracker() end
    if ns.RenderGuideQuestList then ns.RenderGuideQuestList() end
    if ns.UpdateNavigation then ns.UpdateNavigation() end
    if ns.ScheduleActivitySuggestions then ns.ScheduleActivitySuggestions() end
    if ns.QueuePartyRouteFollow then ns.QueuePartyRouteFollow() end
    if ns.SchedulePartyCatchup then ns.SchedulePartyCatchup() end
    if ns.SaveSelectedGuide then ns.SaveSelectedGuide() end
end

function ns.On(event, handler)
    ns.handlers[event] = handler
    ns.frame:RegisterEvent(event)
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
        {"C_QuestLog.IsQuestFlaggedCompleted", C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted},
        {"C_ChatInfo.IsAddonMessagePrefixRegistered", C_ChatInfo and C_ChatInfo.IsAddonMessagePrefixRegistered},
        {"C_ChatInfo.RegisterAddonMessagePrefix", C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix},
        {"C_ChatInfo.SendAddonMessage", C_ChatInfo and C_ChatInfo.SendAddonMessage},
        {"UnitLevel", UnitLevel},
        {"UnitFactionGroup", UnitFactionGroup},
        {"UnitName", UnitName},
        {"UnitClass", UnitClass},
        {"UnitRace", UnitRace},
        {"GetQuestID", GetQuestID},
        {"GetTitleText", GetTitleText},
        {"C_Map.GetBestMapForUnit", C_Map and C_Map.GetBestMapForUnit},
        {"C_Map.GetPlayerMapPosition", C_Map and C_Map.GetPlayerMapPosition},
        {"C_Map.GetMapInfo", C_Map and C_Map.GetMapInfo},
        {"C_Map.GetMapWorldSize", C_Map and C_Map.GetMapWorldSize},
        {"GetPlayerFacing", GetPlayerFacing},
        {"C_Map.GetWorldPosFromMapPos", C_Map and C_Map.GetWorldPosFromMapPos},
        {"C_Map.GetMapLinksForMap", C_Map and C_Map.GetMapLinksForMap},
        {"CreateVector2D", CreateVector2D},
        {"C_Map.CanSetUserWaypointOnMap", C_Map and C_Map.CanSetUserWaypointOnMap},
        {"C_QuestLine.GetAvailableQuestLines", C_QuestLine and C_QuestLine.GetAvailableQuestLines},
        {"C_QuestLine.GetQuestLineInfo", C_QuestLine and C_QuestLine.GetQuestLineInfo},
        {"C_QuestLine.GetQuestLineQuests", C_QuestLine and C_QuestLine.GetQuestLineQuests},
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
        {"C_TradeSkillUI.GetRecipeInfo", C_TradeSkillUI and C_TradeSkillUI.GetRecipeInfo},
        {"C_TradeSkillUI.GetRecipeSchematic", C_TradeSkillUI and C_TradeSkillUI.GetRecipeSchematic},
        {"C_TradeSkillUI.GetChildProfessionInfo", C_TradeSkillUI and C_TradeSkillUI.GetChildProfessionInfo},
        {"C_TradeSkillUI.GetBaseProfessionInfo", C_TradeSkillUI and C_TradeSkillUI.GetBaseProfessionInfo},
        {"C_AuctionHouse.GetCommoditySearchResultInfo", C_AuctionHouse and C_AuctionHouse.GetCommoditySearchResultInfo},
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
        {"TakeTaxiNode", TakeTaxiNode}, {"UnitOnTaxi", UnitOnTaxi}, {"GetUnitSpeed", GetUnitSpeed},
        {"GetTime", GetTime}, {"UnitIsGhost", UnitIsGhost},
        {"C_DeathInfo.GetCorpseMapPosition", C_DeathInfo and C_DeathInfo.GetCorpseMapPosition},
        {"TooltipDataProcessor.AddTooltipPostCall", TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall},
        {"C_Map.SetUserWaypoint", C_Map and C_Map.SetUserWaypoint},
        {"UiMapPoint.CreateFromCoordinates", UiMapPoint and UiMapPoint.CreateFromCoordinates},
        {"issecretvalue", issecretvalue},
        {"C_Timer.After", C_Timer and C_Timer.After},
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
    ns.SyncDiagnostics(output)
    ns.NavigationDiagnostics(output)
    local low, high = ns.PreferredQuestLevels()
    if low then
        local level, _, name = ns.PartyLevelFloor()
        output("Leveling quest band: " .. low .. "–" .. high .. "; lowest synced player: " .. name .. " (level " .. level .. ").")
    else output("Leveling quest band: waiting for public character level.") end
    output("Travel: " .. ns.travelStatus)
    ns.TravelDiagnostics(output)
    output("Guide restore: " .. ns.guideResumeStatus)
    output("Party catch-up: " .. ns.partyCatchupStatus)
    ns.ResearchDiagnostics(output)
    ns.ShowDiagnostics(table.concat(lines, "\n"))
end

ns.On("ADDON_LOADED", function(name)
    if name ~= addonName then return end
    if type(WowTogetherDB) ~= "table" then WowTogetherDB = {} end
    WowTogetherDB.version = 1
    ns.db = WowTogetherDB
    ns.InitializeConfig()
    ns.CreateUI()
    ns.CreateSettings()
    ns.CreateMinimap()
    ns.ReadQuests()
    ns.InitializeSync()
    ns.InitializeGuideControls()
    ns.InitializeTravel()
    ns.InitializeItemHints()
    ns.InitializeOffers()
    ns.InitializeQuestResearch()
    ns.InitializeQuestLearning()
    ns.InitializeGuide()
    ns.ReadProgress()
    ns.CreateTracker()
    ns.CreateNavigation()
    ns.InitializeGuidePersistence()
    if ns.InitializeProfessionGuides then ns.InitializeProfessionGuides() end
    ns.Refresh()
    ns.Print("Loaded. /wt opens the quest view; /wt probe opens diagnostics.")
end)

ns.On("PLAYER_LOGIN", function() ns.RestoreSavedGuide(); ns.ScheduleFlightDiscovery(); ns.ScheduleSync() end)
ns.On("QUEST_LOG_UPDATE", function()
    if ns.db then ns.ReadProgress(); ns.UpdateNPCHints(); ns.Refresh() end
    ns.ScheduleSync()
end)
ns.On("ZONE_CHANGED_NEW_AREA", function()
    ns.ResetZoneConnections(); ns.ReadGuide(); ns.ScheduleFlightDiscovery(); ns.ScheduleSync(); ns.Refresh()
end)
ns.On("PLAYER_LEVEL_UP", function(level) ns.RecordQuestResearch("level", {level = level}); ns.ScheduleSync() end)
ns.On("QUEST_ACCEPTED", function(_, id) ns.RecordQuestResearch("accept", {questID = id}); ns.ScheduleSync() end)
ns.On("QUEST_TURNED_IN", function(id)
    ns.RecordQuestResearch("turn-in", {questID = id})
    ns.InvalidateNPCOffers()
    ns.activityRevision = (ns.activityRevision or 0) + 1; ns.ScheduleSync()
end)
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
    elseif command == "minimap" then ns.ToggleMinimap()
    elseif command == "tracker" then ns.ToggleTracker()
    elseif command == "arrow" then ns.ToggleNavigation()
    elseif command == "config" then ns.ToggleSettings()
    elseif command == "route clear" then ns.ClearRoute(); ns.Refresh()
    elseif command == "guide reset" then ns.ResetGuideSkips()
    elseif command == "guide scan" then ns.ScanGuideProgress()
    elseif command == "catchup" then ns.ShowPartyCatchup(nil, true)
    elseif command == "research" then ns.ShowQuestResearch()
    elseif command == "findings" then ns.ShowGuideFindings()
    elseif command == "questlines" then ns.ShowQuestLineReport()
    else ns.ToggleWindow() end
end
