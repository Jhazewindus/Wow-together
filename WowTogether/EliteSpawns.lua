local addonName, ns = ...

-- Possible locations of the current target, not live NPC tracking. Keep these
-- separate from route destinations, ordering and ordinary nameplate markers.
local empty, cached = {}, nil
local skull = "Interface\\TargetingFrame\\UI-RaidTargetingIcon_8"
local actions = {kill = true, loot = true, collect = true}

local function valid(point)
    return ns.Public(point) and type(point) == "table" and ns.GuideInteger(point.mapID) and point.mapID > 0
        and ns.Public(point.x) and ns.Public(point.y) and type(point.x) == "number" and type(point.y) == "number"
        and point.x >= 0 and point.x <= 1 and point.y >= 0 and point.y <= 1
end

function ns.EliteSpawnPoints()
    local route = ns.selectedRoute
    local stop = route and route.stops and route.stops[1]
    if not ns.Option("eliteSpawnHints") or not ns.routeSelection or not stop or stop.kind ~= "q"
        or ns.routePaused or ns.guideScanning or ns.routePlanning or ns.navigationPreview
        or ns.ReadPublic(UnitOnTaxi, "player") == true or ns.ReadPublic(UnitIsGhost, "player") == true
        or stop.travelLeg or stop.dungeonEntrance then return empty end
    if ns.CurrentQuestConfirmation() or ns.CurrentClassTrainingStop() then return empty end
    local quest = ns.CatalogueQuest(stop.id)
    local facts = ns.GuideStepFacts(stop)
    if not quest or not actions[facts.action] or stop.entityType == "object" or stop.entityType == "item" then return empty end
    local npc = facts.npc ~= nil or stop.entityType == "npc"
    if not npc then
        for _, point in ipairs(quest.objectives or {}) do
            if point.npc and point.entityID == stop.entityID then npc = true; break end
        end
    end
    if not npc then return empty end
    local ids, seen, signature = {}, {}, {stop.id, ns.GuideStepKey(stop), quest.foreverStatus or "",
        tostring(quest.legacyFactsSource ~= nil)}
    local function add(id)
        if not ns.GuideInteger(id) or id <= 0 or seen[id] then return end
        seen[id] = true
        local entity = ns.questEntities and ns.questEntities.npc and ns.questEntities.npc[id]
        local data = ns.eliteSpawnData and ns.eliteSpawnData.npcs[id]
        local rank = entity and entity.classification
        if not ns.Public(rank) then return end
        if rank == nil then rank = data and data.classification end
        if not ns.Public(rank) then return end
        if rank ~= 1 and rank ~= 2 and rank ~= 3 and not (rank == nil and quest.questType == "Elite") then return end
        ids[#ids + 1] = {id = id, entity = entity, data = data}
        signature[#signature + 1] = id
    end
    add(stop.entityID)
    for _, id in ipairs(stop.alternativeEntityIDs or {}) do add(id) end
    if #ids == 0 or not ns.GuideStepNeeded(stop) then return empty end
    local key = table.concat(signature, ":")
    if cached and cached.key == key and cached.quest == quest then return cached.points end
    local points, locations = {}, {}
    for _, target in ipairs(ids) do
        local name = ns.SafeTitle(target.entity and target.entity.name) or ns.SafeTitle(target.data and target.data.name)
            or facts.npc or facts.target or stop.title
        local function point(value)
            if not valid(value) then return end
            local identity = table.concat({target.id, value.mapID, value.x, value.y}, ":")
            if locations[identity] then return end
            locations[identity] = true
            points[#points + 1] = {mapID = value.mapID, x = value.x, y = value.y,
                entityID = target.id, name = name, questID = stop.id, title = stop.title}
        end
        local function packed(values)
            for _, value in ipairs(values or {}) do point({mapID = value[1], x = value[2], y = value[3]}) end
        end
        local data = target.data
        if data then
            packed(data.published)
            if quest.foreverStatus == "unchanged" and quest.legacyFactsSource then
                for _, id in ipairs(data.referenceQuestIDs or {}) do
                    if id == stop.id then packed(data.reference); break end
                end
            end
        end
        -- Future catalogue updates can add public points without rebuilding
        -- this optional overlay dataset. Match the exact mob, not all quest mobs.
        for _, value in ipairs(quest.objectives or {}) do if value.npc and value.entityID == target.id then point(value) end end
        for _, alternatives in ipairs(quest.objectiveAlternatives or {}) do
            for _, value in ipairs(alternatives.locations or {}) do
                if value.npc and value.entityID == target.id then point(value) end
            end
        end
    end
    cached = {key = key, quest = quest, points = #points > 0 and points or empty}
    return cached.points
end

function ns.HideEliteSpawnMarkers(provider)
    for _, pin in ipairs(provider.elitePins or {}) do
        if ns.ReadPublic(pin.IsProtected, pin) == false then pin:Hide()
        else ns.routeRedrawPending = true end
    end
    provider.elitePoints, provider.eliteStepKey, provider.eliteQuestID = empty, nil, nil
    ns.routeStats.eliteSpawns = 0
end

function ns.DrawEliteSpawnMarkers(provider, surface, mapID, context)
    local points = ns.EliteSpawnPoints()
    provider.elitePoints = points
    provider.elitePins = provider.elitePins or {}
    local stop = ns.selectedRoute and ns.selectedRoute.stops[1]
    if #points > 0 and stop then
        provider.eliteStepKey, provider.eliteQuestID = ns.GuideStepKey(stop), stop.id
    end
    local count, placed = 0, {}
    for _, point in ipairs(points) do
        local projected = ns.ProjectMapPoint(point, mapID, context)
        local x, y
        if projected then x, y = ns.RouteProject(surface, projected) end
        if x and x >= 0 and x <= surface.width and y >= 0 and y <= surface.height then
            -- Overlapping map views can describe the same physical spawn.
            local identity = point.entityID .. ":" .. math.floor(projected.x * 1000000 + .5)
                .. ":" .. math.floor(projected.y * 1000000 + .5)
            if not placed[identity] then
                placed[identity], count = true, count + 1
                local pin = provider.elitePins[count]
                if not pin then
                    pin = CreateFrame("Button", nil, provider.overlay); pin:SetSize(18, 18)
                    pin.icon = pin:CreateTexture(nil, "OVERLAY"); pin.icon:SetAllPoints(); pin.icon:SetTexture(skull)
                    pin:SetScript("OnEnter", function(self)
                        if not GameTooltip or not self.spawn then return end
                        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                        GameTooltip:AddLine(self.spawn.name, 1, .82, .3)
                        GameTooltip:AddLine("Possible spawn", 1, 1, 1)
                        GameTooltip:AddLine(self.spawn.title, .8, .8, .8, true); GameTooltip:Show()
                    end)
                    pin:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
                    provider.elitePins[count] = pin
                end
                pin.spawn = point; pin:ClearAllPoints()
                pin:SetPoint("CENTER", provider.overlay, "TOPLEFT", x, -y); pin:Show()
            end
        end
    end
    ns.routeStats.eliteSpawns = count
end

function ns.RefreshEliteSpawnMarkers()
    local provider = ns.routeProvider
    if not provider or not provider.overlay then return end
    if ns.ReadPublic(provider.owningMap.IsShown, provider.owningMap) ~= true then
        if provider.elitePoints ~= empty then ns.HideEliteSpawnMarkers(provider) end
        return
    end
    local points = ns.EliteSpawnPoints()
    if points == provider.elitePoints then return end
    if #points == 0 then ns.HideEliteSpawnMarkers(provider) end
    -- Owned unprotected pins can follow objective changes during combat;
    -- protected map reparenting still uses the existing deferred path.
    ns.DrawRoute(provider, true)
end
