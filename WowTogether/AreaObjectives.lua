local addonName, ns = ...

-- Presentation grouping only. Quest credit, skips and the immutable guide
-- sequence remain independent. Never cross a pickup/turn-in/travel barrier.
local RANGE = 250 / 0.9144
local cached
local function number(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > 0 and value < 1000000
end

function ns.AreaObjectives(stop)
    local route = ns.selectedRoute
    if not route or not stop or stop.kind ~= "q" or stop.travelLeg or stop.flightPlan
        or ns.navigationPreview or ns.routePlanning or ns.guideScanning or ns.routePaused
        or stop.unknownLocation or not ns.ValidTravelPoint(stop) then return {} end
    if cached and cached.route == route and cached.stop == stop and cached.progress == ns.localProgress
        and cached.revision == ns.objectiveDisplayRevision then return cached.items end
    local width, height
    if C_Map then width, height = ns.ReadPublic(C_Map.GetMapWorldSize, stop.mapID) end
    if not number(width) or not number(height) then return {} end
    local result, seen = {}, {}
    for _, candidate in ipairs(route.stops or {}) do
        if candidate.kind ~= "q" or candidate.mapID ~= stop.mapID or candidate.unknownLocation
            or not ns.ValidTravelPoint(candidate) then break end
        local key = candidate.memberKey or ns.self
        local member = key ~= ns.self and ns.members[key]
        local active = key == ns.self and ns.active or member and not member.syncPending and member.active
        local facts = ns.GuideStepFacts(candidate)
        local action = facts.action
        local nearby = ((candidate.x - stop.x) * width)^2 + ((candidate.y - stop.y) * height)^2 <= RANGE^2
        if not nearby then break end
        if active and active[candidate.id] and not ns.GuideQuestSkipped(candidate.id)
            and #ns.FilterGuideStages({candidate}) > 0 and ns.CatalogueCompletion(key, candidate.id) ~= true
            and action ~= "use" and (action == "kill" or action == "loot" or action == "gather" or action == "collect")
            and not facts.finished and facts.remaining ~= 0 then
            local identity = key .. ":" .. candidate.id .. ":" .. (candidate.objectiveKey
                or table.concat({facts.action or "", facts.item or "", facts.target or "", candidate.progressName or ""}, ":"))
            if not seen[identity] then
                result[#result + 1] = {stop = candidate, facts = facts, action = ns.GuideStepAction(candidate, facts)}
                seen[identity] = true
            end
        elseif action ~= "kill" and action ~= "loot" and action ~= "gather" and action ~= "collect" then break end
    end
    cached = {route = route, stop = stop, progress = ns.localProgress, revision = ns.objectiveDisplayRevision, items = result}
    return result
end

function ns.CreateAreaObjectives(frame)
    local panel = CreateFrame("Frame", nil, frame, "BackdropTemplate")
    frame.work = panel
    panel:SetSize(360, 30); panel:SetPoint("TOPLEFT", frame, "BOTTOMLEFT", 0, -4)
    ns.UIPanel(panel, ns.UIColors.background)
    panel.heading = ns.UILabel(panel, nil, 10, ns.UIColors.gold)
    panel.heading:SetPoint("TOPLEFT", 10, -7); panel.heading:SetSize(238, 16); panel.heading:SetWordWrap(false)
    panel.map = ns.UIButton(panel, "Map NPC", 94, ns.ShowConfirmationOnMap)
    panel.map:SetHeight(22); panel.map:SetPoint("TOPRIGHT", -4, -4)
    ns.UIHelp(panel.map, "Show this confirmation NPC. On supported maps, this button also places a Blizzard waypoint for this check only.")
    panel.scroll = CreateFrame("ScrollFrame", nil, panel)
    panel.scroll:SetPoint("TOPLEFT", 8, -25); panel.scroll:SetSize(344, 96)
    panel.content = CreateFrame("Frame", nil, panel.scroll); panel.content:SetSize(340, 96)
    panel.scroll:SetScrollChild(panel.content); panel.scroll:EnableMouseWheel(true)
    panel.scroll:SetScript("OnMouseWheel", function(_, delta)
        if not ns.Public(delta) or type(delta) ~= "number" then return end
        panel.offset = math.max(0, math.min(panel.maximum or 0, (panel.offset or 0) - delta * 32))
        panel.scroll:SetVerticalScroll(panel.offset)
    end)
    panel.rows = {}
    panel:Hide()
end

function ns.UpdateAreaObjectives(state)
    local panel = ns.navigation and ns.navigation.work
    if not panel then return end
    local confirmation = ns.CurrentQuestConfirmation()
    ns.ClearConfirmationWaypoint(confirmation)
    local show = state.visible and ns.Option("routeArrow") and not state.flight and state.stop.kind ~= "corpse"
        and state.stop.kind ~= "f" and not state.stop.travelLeg and not state.busy
    local items = show and not confirmation and ns.AreaObjectives(state.stop) or {}
    state.areaObjectives = items
    panel:SetShown(show and (confirmation ~= nil or #items > 1))
    panel.map:SetShown(show and confirmation ~= nil)
    panel.scroll:SetShown(#items > 1)
    if confirmation then
        panel.heading:SetWidth(238)
        panel:SetHeight(30); panel.heading:SetText("Confirm with " .. (confirmation.npcName or "quest giver"))
        panel.map:SetEnabled(not ns.RouteInCombat() and not confirmation.unknownLocation)
    elseif #items > 1 then
        panel.heading:SetWidth(340)
        panel.heading:SetText("In this area • " .. #items .. " objectives" .. (#items > 3 and " • Scroll" or ""))
        local height = math.min(3, #items) * 32
        panel:SetHeight(30 + height); panel.scroll:SetHeight(height); panel.content:SetHeight(#items * 32)
        panel.maximum = math.max(0, (#items - 3) * 32)
        local stepKey = state.stop.id .. ":" .. ns.GuideStepKey(state.stop) .. ":" .. (state.stop.memberKey or ns.self)
        if panel.guide ~= ns.routeSelection or panel.step ~= stepKey then panel.offset = 0 end
        panel.guide, panel.step = ns.routeSelection, stepKey
        panel.offset = math.min(panel.maximum, panel.offset or 0); panel.scroll:SetVerticalScroll(panel.offset)
        if panel.items ~= items then
            for index, item in ipairs(items) do
                local row = panel.rows[index]
                if not row then
                    row = CreateFrame("Frame", nil, panel.content); row:SetSize(338, 32)
                    row:SetPoint("TOPLEFT", 0, -(index - 1) * 32); row:EnableMouse(true)
                    row.action = ns.UILabel(row, nil, 11); row.action:SetPoint("TOPLEFT", 2, -1); row.action:SetSize(272, 15); row.action:SetWordWrap(false)
                    row.count = ns.UILabel(row, nil, 11, ns.UIColors.gold); row.count:SetPoint("TOPRIGHT", -2, -1); row.count:SetSize(58, 15); row.count:SetJustifyH("RIGHT")
                    row.quest = ns.UILabel(row, nil, 9, ns.UIColors.muted); row.quest:SetPoint("TOPLEFT", 2, -17); row.quest:SetSize(332, 13); row.quest:SetWordWrap(false)
                    row:SetScript("OnEnter", function(self)
                        if not GameTooltip or not self.item then return end
                        GameTooltip:SetOwner(self, "ANCHOR_RIGHT"); GameTooltip:AddLine(ns.GuideStepDescription(self.item.stop), 1, 1, 1, true); GameTooltip:Show()
                    end)
                    row:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
                    panel.rows[index] = row
                end
                row.item = item; row.action:SetText(item.action); row.count:SetText(item.facts.progress or "")
                row.quest:SetText(item.stop.title .. (item.stop.forPlayer and item.stop.forPlayer ~= "You" and (" • " .. item.stop.forPlayer) or "")); row:Show()
            end
        end
    end
    for index = #items + 1, #panel.rows do panel.rows[index]:Hide() end
    panel.items = items
    local anchor = panel:IsShown() and panel or ns.navigation
    local item = ns.navigation.questItem
    if item then
        item:ClearAllPoints(); item:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -4)
        if item:IsShown() then anchor = item end
    end
    if panel.tipAnchor ~= anchor then
        ns.navigation.tip:ClearAllPoints(); ns.navigation.tip:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -4)
        panel.tipAnchor = anchor
    end
end
