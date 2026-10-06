local addonName, ns = ...

-- Selection is driven by guide progress, not movement/arrow repainting. Native
-- helpers are capability-probed; their behavior still needs beta testing.
function ns.UpdateGuideQuestFocus()
    if not ns.Option("highlightGuideQuest") then
        ns.guideQuestFocusTarget = nil
        ns.guideQuestFocusPending = nil
        ns.guideQuestFocusStatus = "Off in settings."
        return
    end
    local route = ns.routeSelection and ns.selectedRoute
    local stop = route and (route.stops and route.stops[1] or route.pendingStop)
    local id = stop and stop.id
    if ns.guideScanning or ns.routePlanning or ns.routePaused or not ns.questReady
        or not ns.GuideInteger(id) or id <= 0 or not ns.active[id] then
        ns.guideQuestFocusTarget = nil
        ns.guideQuestFocusPending = nil
        ns.guideQuestFocusStatus = "Waiting for an accepted current guide quest."
        return
    end
    local selectQuest = C_QuestLog and C_QuestLog.SetSelectedQuest
    local showDetails = QuestMapFrame_ShowQuestDetails
    local trackQuest = C_SuperTrack and C_SuperTrack.SetSuperTrackedQuestID
    if type(selectQuest) ~= "function" and type(trackQuest) ~= "function" then
        ns.guideQuestFocusStatus = "Quest selection/tracking APIs unavailable on this build."
        return
    end
    if ns.RouteInCombat() then
        -- PLAYER_REGEN_ENABLED recomputes the target rather than replaying an
        -- obsolete closure if the player skipped/switched steps in combat.
        ns.guideQuestFocusPending = true
        ns.guideQuestFocusStatus = "Waiting until combat ends."
        return
    end
    ns.guideQuestFocusPending = nil
    local previous = ns.guideQuestFocusTarget
    local status = "Current guide quest: " .. ns.QuestTitle(id) .. " (" .. id .. ")."
    if previous and previous.id == id and previous.selectQuest == selectQuest
        and previous.trackQuest == trackQuest and previous.showDetails == showDetails then
        ns.guideQuestFocusStatus = status
        return
    end
    -- Set before calling native actions: synchronous quest events must not
    -- select recursively. Do not retry failed protected actions with pcall.
    ns.guideQuestFocusTarget = {id = id, selectQuest = selectQuest, trackQuest = trackQuest, showDetails = showDetails}
    if type(selectQuest) == "function" then
        -- Match a native log click, including its displayed details. Calling
        -- this helper does not open the map/log window. Direct selection is
        -- the fallback when the UI helper isn't exposed by the beta.
        if type(showDetails) == "function" then showDetails(id)
        else selectQuest(id) end
    end
    if type(trackQuest) == "function" then trackQuest(id) end
    ns.guideQuestFocusStatus = status
end

function ns.GuideQuestFocusDiagnostics(output)
    output("Native quest highlights: " .. (ns.guideQuestFocusStatus or "Waiting for a guide."))
end
