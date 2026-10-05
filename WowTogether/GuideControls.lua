local addonName, ns = ...

ns.guideScanStatus = "Select a guide to scan its quest history."

function ns.InitializeGuideControls()
    if type(ns.db.guideSkips) ~= "table" then ns.db.guideSkips = {} end
    local state = ns.db.guideSkips[ns.self]
    if type(state) ~= "table" then state = {}; ns.db.guideSkips[ns.self] = state end
    if type(state.quests) ~= "table" then state.quests = {} end
    if type(state.steps) ~= "table" then state.steps = {} end
end

local function saved()
    return ns.db and ns.db.guideSkips and ns.db.guideSkips[ns.self]
end

function ns.GuideQuestSkipped(id)
    local state = saved()
    return state and state.quests[id] == true or false
end

function ns.GuideStepKey(stop)
    if ns.GuideInteger(stop.entityID) and stop.entityID > 0 then
        return table.concat({stop.kind, stop.mapID, "npc", stop.entityID}, ":")
    end
    return table.concat({stop.kind, stop.mapID, math.floor(stop.x * 100000 + 0.5),
        math.floor(stop.y * 100000 + 0.5)}, ":")
end

function ns.FilterGuideStages(stages)
    local state, result = saved(), {}
    for _, stop in ipairs(stages) do
        local steps = state and state.steps[stop.id]
        if not steps or steps[ns.GuideStepKey(stop)] ~= true then result[#result + 1] = stop end
    end
    return result
end

function ns.GuideSelectionHasSkips(guide)
    local state = saved()
    if not state then return false end
    for _, record in ipairs(guide.records or {}) do
        if state.quests[record.id] == true then return true end
        for _, value in pairs(state.steps[record.id] or {}) do if value == true then return true end end
    end
    return false
end

function ns.SkipGuide(kind)
    local stop = ns.selectedRoute and ns.selectedRoute.stops[1]
    local state = saved()
    if not stop or not state then return end
    if kind == "quest" then state.quests[stop.id] = true
    elseif kind == "step" then
        state.steps[stop.id] = state.steps[stop.id] or {}
        state.steps[stop.id][ns.GuideStepKey(stop)] = true
    else return end
    ns.routeSignature = nil
    ns.Refresh()
end

function ns.ResetGuideSkips()
    local state = saved()
    if not state then return end
    state.quests, state.steps = {}, {}
    ns.routeSignature = nil
    ns.guideAction = "Skipped quests and steps restored for this character."
    ns.Refresh()
end

function ns.ScanGuideProgress(guide, refresh)
    guide = guide or ns.routeSelection
    if not guide then return end
    ns.RouteHistoryScope(guide.records)
    ns.ReadQuests(); ns.ReadGuide()
    local checked, completed, active, total = 0, 0, 0, 0
    for id in pairs(ns.partyRouteHistoryScope or {}) do
        total = total + 1
        local done = ns.Completed(id)
        if done ~= nil then checked = checked + 1 end
        if done == true then completed = completed + 1 end
        if ns.active[id] then active = active + 1 end
    end
    ns.guideScanStatus = "Guide history: " .. checked .. "/" .. total .. " checked; " .. completed .. " completed; " .. active .. " active."
    if checked < total then ns.guideScanStatus = ns.guideScanStatus .. " Restricted history stays unknown." end
    if #(ns.partyNames or {}) > 0 then
        -- Reuse the bounded catalogue-map request; peers query their own
        -- completion flags. Never copy our completion into their progress.
        local mapID = guide.mapID or guide.target and guide.target.mapID
        if ns.GuideInteger(mapID) and mapID > 0 then ns.QueueMessage("1|Z|" .. mapID) end
        ns.guideScanStatus = ns.guideScanStatus .. " Friends' history waits for their received snapshots."
    end
    ns.ScheduleSync()
    if refresh ~= false then ns.Refresh() end
end

function ns.ShowGuideScanReport()
    if not ns.guideScanWindow then
        local frame = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
        frame:SetSize(360, 170); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
        frame:SetClampedToScreen(true); ns.UIPanel(frame)
        local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton"); close:SetPoint("TOPRIGHT", -4, -4)
        local title = ns.UILabel(frame, "GameFontNormalLarge", 14)
        title:SetPoint("TOPLEFT", 18, -20); title:SetText("Guide progression")
        frame.body = ns.UILabel(frame, nil, 11); frame.body:SetPoint("TOPLEFT", 18, -52)
        frame.body:SetSize(320, 100); frame.body:SetJustifyV("TOP")
        ns.guideScanWindow = frame
    end
    ns.guideScanWindow.body:SetText(ns.guideScanStatus .. "\n\nSkipped steps are personal navigation choices. They do not complete quests or unlock prerequisites.")
    ns.guideScanWindow:Show()
end
