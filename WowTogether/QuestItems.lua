local addonName, ns = ...

local function currentQuest()
    if not ns.questReady or ns.guideScanning or ns.routePlanning or ns.routePaused
        or ns.navigationPreview or ns.ReadPublic(UnitIsGhost, "player") == true
        or ns.ReadPublic(UnitOnTaxi, "player") == true then return end
    local route = ns.routeSelection and ns.selectedRoute
    local stop = route and route.stops and route.stops[1]
    if not stop or stop.kind ~= "q" or stop.travelLeg or stop.historyPreview
        or not ns.GuideInteger(stop.id) or stop.id <= 0 or not ns.active[stop.id] then return end
    return stop.id
end

local function logIndex(id)
    local api = C_QuestLog
    if not api or type(api.GetInfo) ~= "function" then return end
    local index = ns.ReadPublic(api.GetLogIndexForQuestID, id)
    if ns.GuideInteger(index) and index > 0 then
        local entry = ns.ReadPublic(api.GetInfo, index)
        if type(entry) == "table" and ns.Public(entry.isHeader) and not entry.isHeader
            and ns.Public(entry.questID) and entry.questID == id then return index end
        -- An inconsistent native lookup must never fall through to item use.
        return
    end
    if type(api.GetLogIndexForQuestID) == "function" then return end
    local count = ns.ReadPublic(api.GetNumQuestLogEntries)
    if not ns.GuideInteger(count, 1000) then return end
    for i = 1, count do
        local entry = ns.ReadPublic(api.GetInfo, i)
        if type(entry) == "table" and ns.Public(entry.isHeader) and not entry.isHeader
            and ns.Public(entry.questID) and entry.questID == id then return i end
    end
end

local function readItem()
    if type(GetQuestLogSpecialItemInfo) ~= "function" or type(UseQuestLogSpecialItem) ~= "function" then
        return nil, "Special quest-item APIs unavailable on this build."
    end
    local id = currentQuest()
    local index = id and logIndex(id)
    if not index then return nil, "Waiting for an accepted current objective with a quest item." end
    local link, texture = ns.ReadPublic(GetQuestLogSpecialItemInfo, index)
    if type(link) ~= "string" or link == "" then return nil, "No special item reported for the current objective." end
    local name = string.match(link, "%[([^%]]+)%]") or "Quest item"
    if type(texture) ~= "string" and type(texture) ~= "number" then texture = "Interface\\Icons\\INV_Misc_QuestionMark" end
    return {id = id, index = index, link = link, texture = texture, name = name}, "Ready: " .. name .. "."
end

function ns.UpdateGuideQuestItem()
    -- Called on progress/bag/item-data events, never from movement repainting.
    ns.guideQuestItem, ns.guideQuestItemStatus = readItem()
end

function ns.UseGuideQuestItem(button)
    if not button or not button:IsShown() or not button.item then return false end
    if ns.RouteInCombat() then ns.guideQuestItemStatus = "Use the guide item outside combat."; return false end
    local displayed = button.item
    local item, status = readItem()
    ns.guideQuestItem, ns.guideQuestItemStatus = item, status
    -- Re-resolve on this hardware click: headers, accepts, removals and route
    -- changes can invalidate a cached index. A changed item needs a new click.
    if not item or item.id ~= displayed.id or item.link ~= displayed.link then
        ns.UpdateNavigation()
        return false
    end
    ns.guideQuestItemStatus = "Manual use requested: " .. item.name .. ". Check the native result."
    -- Native quest buttons call this API from OnClick. No automatic use,
    -- targeting, macro execution or pcall around a potentially protected action.
    UseQuestLogSpecialItem(item.index)
    return true
end

function ns.CreateQuestItemButton(frame)
    local button = ns.UIButton(frame, "Use item", 360, ns.UseGuideQuestItem)
    frame.questItem = button
    button:SetHeight(32); button:RegisterForClicks("LeftButtonUp")
    button.caption:ClearAllPoints(); button.caption:SetPoint("LEFT", 36, 0)
    button.caption:SetSize(310, 20); button.caption:SetWordWrap(false)
    button.icon = button:CreateTexture(nil, "ARTWORK")
    button.icon:SetSize(24, 24); button.icon:SetPoint("LEFT", 4, 0)
    button:SetScript("OnEnter", function(self)
        if not GameTooltip or not self.item then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:AddLine(self.item.name, 1, 0.82, 0.3)
        GameTooltip:AddLine("Click to use for " .. ns.QuestTitle(self.item.id) .. ". Select any required target yourself.", 1, 1, 1, true)
        if ns.RouteInCombat() then GameTooltip:AddLine("Use outside combat on this beta.", 1, 0.82, 0.3, true) end
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    button:Hide()
end

function ns.UpdateQuestItemButton(state)
    local button = ns.navigation and ns.navigation.questItem
    if not button then return end
    local item = ns.guideQuestItem
    local stop = state.stop
    local show = item ~= nil and state.visible and ns.Option("routeArrow") and not state.flight and not state.busy
        and not ns.navigationPreview and stop and stop.kind == "q" and stop.id == item.id
    button:SetShown(show == true)
    button.item = show and item or nil
    if show then
        button.caption:SetText("Use item • " .. item.name)
        button.icon:SetTexture(item.texture)
        button:SetEnabled(not ns.RouteInCombat())
    end
end

function ns.QuestItemDiagnostics(output)
    output("Guide quest item: " .. (ns.guideQuestItemStatus or "Waiting for a guide objective.") .. " Manual click; outside combat.")
end
