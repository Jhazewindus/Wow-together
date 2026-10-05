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
    local kind = stop.stepKind or stop.kind
    if ns.GuideInteger(stop.entityID) and stop.entityID > 0 then
        return table.concat({kind, stop.mapID, "npc", stop.entityID}, ":")
    end
    if type(stop.x) ~= "number" or type(stop.y) ~= "number" then return kind .. ":" .. (stop.mapID or 0) .. ":unknown" end
    return table.concat({kind, stop.mapID, math.floor(stop.x * 100000 + 0.5),
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
    if ns.guideScanning or ns.routePlanning then return end
    if ns.routeSelection and ns.routeSelection.mode == "travel" then return end
    local stop = ns.navigation and ns.navigation.state and ns.navigation.state.stop
    if ns.navigationPreview or stop and stop.kind == "corpse" or ns.navigation and ns.navigation.state and ns.navigation.state.flight then return end
    if not stop or stop.kind ~= "f" then stop = ns.selectedRoute and (ns.selectedRoute.pendingStop or ns.selectedRoute.stops[1]) end
    local state = saved()
    if not stop or not state then return end
    if kind == "quest" then state.quests[stop.id] = true
    elseif kind == "step" then
        state.steps[stop.id] = state.steps[stop.id] or {}
        state.steps[stop.id][ns.GuideStepKey(stop)] = true
    else return end
    ns.RecordQuestResearch(kind == "quest" and "skip-quest" or "skip-step", {questID = stop.id,
        guideKey = ns.routeSelection and ns.routeSelection.key, stepKey = ns.GuideStepKey(stop),
        stepKind = stop.stepKind or stop.kind, guideStep = stop.guideStep})
    ns.routeSignature = nil
    ns.navigationPreview = nil
    ns.forceRouteReplan = true
    ns.ResetTravelPath()
    -- A hidden/resizing dashboard must not delay a user-requested route edit.
    ns.UpdateSelectedRoute(nil, ns.NewQuestQuery())
    ns.UpdateNavigation()
    ns.DrawRoute(nil, true)
    ns.Refresh()
end

function ns.ResetGuideSkips()
    local state = saved()
    if not state then return end
    state.quests, state.steps = {}, {}
    ns.routeSignature, ns.forceRouteReplan = nil, true
    ns.guideAction = "Skipped quests and steps restored for this character."
    ns.Refresh()
end

local function scanGuideProgress(guide, refresh, cooperative)
    guide = guide or ns.routeSelection
    if not guide then return end
    if guide.mode == "travel" then
        if ns.selectedRoute then ns.selectedRoute.travelOriginMap = nil end
        ns.ResetTravelPath(); ns.UpdateTravelGuide(guide); ns.Refresh(); return
    end
    if refresh ~= false and ns.Option("scanSkipped") then
        local state = saved()
        for _, record in ipairs(guide.records or {}) do state.quests[record.id], state.steps[record.id] = nil, nil end
    end
    ns.RouteHistoryScope(guide.records)
    ns.ReadQuests(); ns.ReadGuide()
    local checked, completed, active, total = 0, 0, 0, 0
    for id in pairs(ns.partyRouteHistoryScope or {}) do
        total = total + 1
        local done = ns.Completed(id)
        if done ~= nil then checked = checked + 1 end
        if done == true then completed = completed + 1 end
        if ns.active[id] then active = active + 1 end
        if cooperative and total % 40 == 0 then coroutine.yield() end
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
    if refresh ~= false then
        if guide.fixedRoute then
            ns.navigationPreview, ns.routeSignature = nil, nil
            ns.Refresh(); return
        end
        if guide.fullGuide and not guide.baseGuide then
            local fresh = ns.RebuildLevelingGuide(guide)
            fresh.batchIDs = nil
            ns.navigationPreview = nil
            ns.PlanLevelingGuide(fresh, false)
            return
        end
        local choices
        if guide.mode == "current" or guide.mode == "bundle" then choices = ns.CurrentQuestChoices()
        else choices = ns.GuideChoices(true) end
        local fresh
        for _, choice in ipairs(type(choices) == "table" and choices or {}) do
            if choice.key == guide.key then fresh = choice; break end
        end
        if guide.baseGuide then fresh = ns.MergeCurrentQuests(guide.baseGuide)
        elseif (guide.mode == "current" or guide.mode == "bundle") and not fresh then fresh = choices and choices[1] end
        ns.routeSelection = fresh or guide
        ns.navigationPreview, ns.routeSignature, ns.forceRouteReplan = nil, nil, true
        ns.Refresh()
        ns.guideAction = "Guide replanned using current quests, history and saved skip choices."
    end
end

function ns.CancelGuideScan()
    ns.guideScanning = nil
end

function ns.ScanGuideProgress(guide, refresh)
    guide = guide or ns.routeSelection
    if not guide then return end
    -- Internal history reads stay synchronous. User scans yield to the UI
    -- before reading and between history batches; no timer is saved to disk.
    if refresh == false then return scanGuideProgress(guide, false) end
    if ns.guideScanning or ns.routePlanning then return end
    if not C_Timer or type(C_Timer.After) ~= "function" then
        ns.guideScanStatus = "Guide scan unavailable: timer API missing."
        return
    end
    local scan = {guide = guide, selectionKey = ns.routeSelection and ns.routeSelection.key}
    local worker = coroutine.create(function() scanGuideProgress(guide, refresh, true) end)
    ns.guideScanning = scan
    ns.UpdateNavigation()
    local function advance()
        if ns.guideScanning ~= scan then return end
        if (ns.routeSelection and ns.routeSelection.key) ~= scan.selectionKey then ns.CancelGuideScan(); ns.UpdateNavigation(); return end
        scan.executing = true
        local ok, detail = coroutine.resume(worker)
        scan.executing = nil
        if ns.guideScanning ~= scan then return end
        if not ok then
            ns.guideScanning = nil
            ns.guideScanStatus = "Guide scan failed; the selected guide is retained."
            ns.guideScanError = ns.Public(detail) and type(detail) == "string" and string.sub(detail, 1, 400) or "Unknown scan failure"
            ns.Refresh(); ns.UpdateNavigation()
        elseif coroutine.status(worker) == "dead" then
            ns.guideScanning, ns.guideScanError = nil, nil
            ns.Refresh(); ns.UpdateNavigation(); ns.DrawRoute(nil, true)
        else C_Timer.After(0.01, advance) end
    end
    C_Timer.After(0.01, advance)
end

function ns.InitializeGuideStepHistory(guide, route)
    local history, current = {}, route and route.stops[1]
    local function add(record, point, kind)
        local stop = ns.PublishedGuideStop(record, point, kind)
        if stop then
            stop.historyPreview = true
            history[#history + 1] = stop
            if #history > 40 then table.remove(history, 1) end
        end
    end
    -- History confirms completed quests and accepted pickups, not the order
    -- in which a player visited locations. These are read-only previews.
    for _, record in ipairs(guide.records or {}) do
        local quest = ns.CatalogueQuest(record.id)
        if quest and ns.Completed(record.id) == true and not ns.active[record.id] then
            add(record, quest.starts and quest.starts[1], "a")
            for _, point in ipairs(quest.objectives or {}) do add(record, point, "q") end
            add(record, quest.ends and quest.ends[1], "t")
        end
    end
    if current and ns.active[current.id] and current.kind ~= "a" then
        local record, quest = {id = current.id, title = current.title}, ns.CatalogueQuest(current.id)
        if quest then add(record, quest.starts and quest.starts[1], "a") end
    end
    ns.guideStepHistory = history
end

function ns.RememberGuideStep(before, after)
    if not after or before.id == after.id and ns.GuideStepKey(before) == ns.GuideStepKey(after) then return end
    ns.guideStepHistory = ns.guideStepHistory or {}
    ns.guideStepHistory[#ns.guideStepHistory + 1] = before
    if #ns.guideStepHistory > 40 then table.remove(ns.guideStepHistory, 1) end
    ns.navigationPreview = nil
end

function ns.PreviewGuideStep(delta)
    if ns.guideScanning or ns.routePlanning then return end
    local index = (ns.navigationPreview and ns.navigationPreview.index or 0) + delta
    local stop
    if index < 0 then
        local history = ns.guideStepHistory or {}
        stop = history[#history + index + 1]
    elseif index > 0 then stop = ns.selectedRoute and ns.selectedRoute.stops[index + 1] end
    if index == 0 then ns.navigationPreview = nil
    elseif stop then ns.navigationPreview = {index = index, stop = stop}
    else return end
    ns.UpdateNavigation()
end

function ns.GuideStepNeeded(stop)
    if ns.GuideQuestSkipped(stop.id) or #ns.FilterGuideStages({stop}) == 0 then return false end
    for _, person in ipairs(ns.PartyProfiles()) do
        local active = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
        if active and active[stop.id] then
            local destination = ns.RoutePointForMember(person.key, stop.id)
            if stop.kind == "q" and not ns.QuestProgressReady(person.key, stop.id)
                and not (destination and destination.kind == "t")
                and not (person.key == ns.self and ns.readyToTurnIn[stop.id]) then
                local progress, matched, unfinished = ns.ProgressForMember(person.key, stop.id), false, false
                for _, objective in ipairs(progress and progress.objectives or {}) do
                    if ns.ObjectiveMatchesPoint(objective.text, {name = stop.targetName or stop.npcName, itemName = stop.itemName}) then
                        matched = true
                        if not ns.ObjectiveFinished(objective) then unfinished = true end
                    end
                end
                if not matched or unfinished then return true end
            end
        end
    end
    return false
end

function ns.PinCurrentDestination(old, route)
    if ns.forceRouteReplan then ns.forceRouteReplan = nil; return route end
    local before = old and old.stops[1]
    if not before or before.kind ~= "q" or not ns.GuideStepNeeded(before) then return route end
    if route.mapID ~= before.mapID then return old end
    for index, stop in ipairs(route.stops) do
        if stop.id == before.id and ns.GuideStepKey(stop) == ns.GuideStepKey(before) then
            table.remove(route.stops, index); table.insert(route.stops, 1, stop); return route
        end
    end
    -- Keep a committed objective while crossing a zone. A changed POI alone
    -- does not demonstrate objective completion.
    return route
end

function ns.MergeCurrentQuests(guide)
    local copy, seen, records, pickups = {}, {}, {}, {}
    for key, value in pairs(guide) do copy[key] = value end
    for _, record in ipairs(guide.records or {}) do
        records[#records + 1], seen[record.id], pickups[record.id] = record, true, true
    end
    for _, current in ipairs(ns.CurrentQuestChoices() or {}) do
        for _, record in ipairs(current.records) do
            if not seen[record.id] then records[#records + 1], seen[record.id] = record, true end
            if not (current.pickupIDs and current.pickupIDs[record.id]) then pickups[record.id] = nil end
        end
    end
    copy.records, copy.pickupIDs, copy.mode, copy.baseGuide = records, pickups, "bundle", guide
    copy.fixedPlan = nil -- Explicitly including extra work creates a new fixed sequence.
    copy.batchIDs = nil -- A new selection must not inherit the previous trip's quest set.
    copy.mapID = guide.mapID or guide.target and guide.target.mapID or ns.profile.mapID
    copy.key, copy.title = "with-log:" .. guide.key, guide.title .. " + current quests"
    return copy
end

function ns.RequestStartRoute(guide)
    if not guide then return end
    if guide.mode == "travel" then return ns.ShowGuideOnMap(guide) end
    if guide.personal then return ns.ShowGuideOnMap(guide) end
    if not ns.HasCurrentPartyQuests() or guide.mode == "current" or guide.mode == "bundle" then return ns.StartPartyRoute(guide) end
    if not ns.startGuidePrompt then
        local frame = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
        frame:SetSize(500, 220); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
        frame:SetClampedToScreen(true); ns.UIPanel(frame)
        local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton"); close:SetPoint("TOPRIGHT", -4, -4)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 16); frame.title:SetPoint("TOPLEFT", 20, -24); frame.title:SetWidth(450)
        frame.text = ns.UILabel(frame, nil, 12); frame.text:SetPoint("TOPLEFT", 20, -62); frame.text:SetSize(450, 80)
        frame.selected = ns.UIButton(frame, "Start selected guide", 215, function()
            local chosen = ns.startGuidePrompt.guide; ns.startGuidePrompt:Hide(); ns.StartPartyRoute(chosen)
        end, true); frame.selected:SetPoint("BOTTOMLEFT", 20, 24)
        frame.current = ns.UIButton(frame, "Include current quests", 215, function()
            local chosen = ns.MergeCurrentQuests(ns.startGuidePrompt.guide); ns.startGuidePrompt:Hide(); ns.StartPartyRoute(chosen)
        end); frame.current:SetPoint("BOTTOMRIGHT", -20, 24)
        ns.startGuidePrompt = frame
    end
    ns.startGuidePrompt.guide = guide
    ns.startGuidePrompt.title:SetText("Start " .. guide.title)
    ns.startGuidePrompt.text:SetText("Use this guide's plan, or include worthwhile quests already in your party's logs?\nUnfinished low-level quests are filtered; ready hand-ins and useful prerequisites stay. Including current quests can cause unusual routes and long detours.")
    ns.startGuidePrompt:Show()
end
