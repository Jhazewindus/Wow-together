local addonName, ns = ...

local units, hints = {}, {}
ns.npcHints = hints
ns.npcHintCount = 0
ns.npcHintStatus = "NPC hints wait for public nameplate NPC IDs."

function ns.QuestItemTooltip(tooltip, data)
    if not ns.Option("npcHints") or ns.RouteInCombat() or not ns.Public(data) or type(data) ~= "table"
        or not ns.Public(data.id) or not ns.GuideInteger(data.id) then return end
    local titles, seen = {}, {}
    for _, person in ipairs(ns.PartyProfiles()) do
        local active = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
        for id in pairs(active or {}) do
            local quest = ns.CatalogueQuest(id)
            for _, item in ipairs(quest and quest.requiredItems or {}) do
                if item.itemID == data.id then
                    local finished = false
                    local progress = ns.ProgressForMember(person.key, id)
                    for _, objective in ipairs(progress and progress.objectives or {}) do
                        if ns.ObjectiveMatchesPoint(objective.text, {name = item.name}) and ns.ObjectiveFinished(objective) then finished = true end
                    end
                    if not finished and not seen[id] then titles[#titles + 1] = ns.QuestTitle(id); seen[id] = true end
                end
            end
        end
    end
    if #titles > 0 and tooltip and type(tooltip.AddLine) == "function" then
        tooltip:AddLine("× Needed for: " .. table.concat(titles, ", "), 1, 0.76, 0.28, true)
    end
end

function ns.InitializeItemHints()
    local kind = Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item
    if TooltipDataProcessor and type(TooltipDataProcessor.AddTooltipPostCall) == "function" and kind then
        TooltipDataProcessor.AddTooltipPostCall(kind, ns.QuestItemTooltip)
    end
end

function ns.NPCTargets()
    local targets, known = {}, {}
    local query = ns.NewQuestQuery()
    local function add(point, id, kind)
        if not point or not point.npc or not ns.GuideInteger(point.entityID) or point.entityID <= 0 then return end
        targets[point.entityID] = targets[point.entityID] or {kind = kind, action = point.action,
            title = ns.QuestTitle(id), label = point.name, quests = {}}
        local target = targets[point.entityID]
        if kind == "a" then target.pickup = true end
        local priority = {q = 1, a = 2, t = 3}
        if priority[kind] > priority[target.kind] then target.kind, target.action = kind, point.action end
        target.quests[id] = ns.QuestTitle(id)
    end
    for _, person in ipairs(query.profiles) do
        local active = person.key == ns.self and ns.active or (ns.members[person.key] and ns.members[person.key].active)
        if person.synced then
            for id in pairs(active or {}) do
                local quest = ns.CatalogueQuest(id)
                if quest then
                    for _, p in ipairs(quest.npcTargets or quest.objectives or {}) do
                        if p.npc and ns.GuideInteger(p.entityID) and p.entityID > 0 then known[p.entityID] = true end
                    end
                    local point = ns.RoutePointForMember(person.key, id)
                    local ready = (person.key == ns.self and ns.readyToTurnIn[id]) or (point and point.kind == "t") or ns.QuestProgressReady(person.key, id)
                    local points
                    if ready then points = quest.ends else points = quest.npcTargets or quest.objectives end
                    for _, p in ipairs(points or {}) do
                        local matched, allDone = false, true
                        local progress = ns.ProgressForMember(person.key, id)
                        for _, objective in ipairs(progress and progress.objectives or {}) do
                            if ns.ObjectiveMatchesPoint(objective.text, p) then
                                matched = true
                                if not ns.ObjectiveFinished(objective) then allDone = false end
                            end
                        end
                        if not (matched and allDone) then add(p, id, ready and "t" or "q") end
                    end
                end
            end
        end
    end
    if ns.selectedRoute and not ns.routePaused then
        for _, stop in ipairs(ns.selectedRoute.stops) do
            if stop.kind == "a" and stop.entityID and not ns.IsLevelingExcludedQuest(stop.id) then
                local quest = ns.CatalogueQuest(stop.id)
                for _, person in ipairs(query.profiles) do
                    local active = person.key == ns.self and ns.active or ns.members[person.key] and ns.members[person.key].active
                    if person.synced and not (active and active[stop.id]) and ns.CatalogueCompletion(person.key, stop.id, query) ~= true
                        and ns.CatalogueAllowed(stop.id, person.profile, person.key, query) == true then
                        for _, point in ipairs(quest and quest.starts or {}) do add(point, stop.id, "a") end
                        break
                    end
                end
            end
        end
    end
    return targets, known
end

local function hide(hint)
    local protected = type(hint.IsProtected) == "function" and hint:IsProtected()
    if not ns.Public(protected) or (protected and ns.RouteInCombat()) then ns.npcHintsPending = true; return end
    hint:Hide()
end

local function read(fn, ...)
    if type(fn) ~= "function" then return end
    local okay, value = pcall(fn, ...)
    return okay and ns.Public(value) and value or nil
end

local function region(value)
    if not ns.Public(value) then return end
    local kind = type(value)
    if kind == "table" or kind == "userdata" then return value end
end

local function markerAnchor(plate)
    local unitFrame = region(plate.UnitFrame)
    if unitFrame then return region(unitFrame.name) or region(unitFrame.healthBar) or unitFrame end
    return plate
end

function ns.UpdateNPCHints()
    if ns.RouteInCombat() then ns.npcHintsPending = true; return end
    ns.npcHintsPending, ns.npcHintCount = nil, 0
    for _, hint in pairs(hints) do hide(hint) end
    if not ns.Option("npcHints") then ns.npcHintStatus = "NPC hints disabled in settings."; return end
    if not ns.Option("nameplateHints") then ns.npcHintStatus = "Nameplate markers disabled; quest-item tooltip hints follow their own setting."; return end
    if not C_NamePlate or type(C_NamePlate.GetNamePlateForUnit) ~= "function" or type(UnitGUID) ~= "function" then
        ns.npcHintStatus = "Nameplate/NPC ID API unavailable; map objective icons still work."; return
    end
    local targets, known = ns.NPCTargets()
    local visible = read(C_NamePlate.GetNamePlates)
    if type(visible) == "table" then
        for index, plate in ipairs(visible) do
            if index > 40 then break end
            if ns.Public(plate) and (type(plate) == "table" or type(plate) == "userdata") then
                local unit = plate.namePlateUnitToken
                if ns.Public(unit) and type(unit) == "string" and string.match(unit, "^nameplate%d+$") then units[unit] = true end
            end
        end
    end
    for unit in pairs(units) do
        local guid = read(UnitGUID, unit)
        local id = type(guid) == "string" and tonumber(string.match(guid, "^Creature%-%d+%-%d+%-%d+%-%d+%-(%d+)%-"))
        local target = id and targets[id]
        local related = C_QuestLog and read(C_QuestLog.UnitIsRelatedToActiveQuest, unit)
        if not target and related == true and not (id and known[id]) then target = {kind = "q", label = "Your quest objective", quests = {}} end
        local plate = target and read(C_NamePlate.GetNamePlateForUnit, unit)
        if plate then
            local hint = hints[unit]
            if not hint then
                hint = CreateFrame("Frame", nil, UIParent)
                hint:SetSize(18, 18)
                hint:SetFrameStrata("HIGH")
                hint.icon = hint:CreateTexture(nil, "ARTWORK")
                hint.icon:SetAllPoints()
                hint.questNames = hint:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
                hint.questNames:SetFont("Fonts\\FRIZQT__.TTF", 10, "OUTLINE")
                hint.questNames:SetPoint("TOP", 0, 0); hint.questNames:SetSize(190, 27)
                hint.questNames:SetTextColor(1, 0.9, 0.62, 1)
                hint.pointer = CreateFrame("Frame", nil, hint); hint.pointer:SetSize(18, 18); hint.pointer:SetPoint("BOTTOM", 0, 0)
                hint.pointer.lines = {}
                for index, ends in ipairs({{0, 6, 0, -6}, {-6, 0, 0, -6}, {6, 0, 0, -6}}) do
                    local line = hint.pointer:CreateLine(nil, "OVERLAY")
                    line:SetThickness(2); line:SetColorTexture(1, 0.82, 0.3, 1)
                    line:SetStartPoint("CENTER", hint.pointer, ends[1], ends[2]); line:SetEndPoint("CENTER", hint.pointer, ends[3], ends[4])
                    hint.pointer.lines[index] = line
                end
                hint.symbol = hint:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
                hint.symbol:SetFont("Fonts\\FRIZQT__.TTF", 18, "OUTLINE"); hint.symbol:SetPoint("CENTER")
                hint.symbol:SetTextColor(1, 0.85, 0.3, 1)
                hint:EnableMouse(true)
                hint:SetScript("OnEnter", function(self)
                    if not GameTooltip then return end
                    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                    GameTooltip:AddLine(self.target.label, 0.96, 0.76, 0.36)
                    for _, title in pairs(self.target.quests) do GameTooltip:AddLine(title, 1, 1, 1, true) end
                    GameTooltip:Show()
                end)
                hint:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
                hints[unit] = hint
            end
            hint.target = target
            hint:ClearAllPoints()
            local friendly = target.kind == "a" or target.kind == "t"
            hint.questNames:SetShown(friendly); hint.pointer:SetShown(friendly)
            if friendly then
                local star = target.pickup == true and ns.Option("questGiverStars")
                hint:SetSize(190, star and 64 or 47); hint:SetPoint("BOTTOM", plate, "TOP", 0, 6)
                hint.questNames:ClearAllPoints(); hint.questNames:SetPoint("TOP", 0, star and -36 or 0)
                local titles = {}; for _, title in pairs(target.quests) do titles[#titles + 1] = title end; table.sort(titles)
                local shown = {}; for index = 1, math.min(2, #titles) do shown[#shown + 1] = titles[index] end
                if #titles > 2 then shown[2] = shown[2] .. " ( +" .. (#titles - 2) .. " )" end
                hint.questNames:SetText(table.concat(shown, "\n"))
                hint.icon:ClearAllPoints()
                if star then
                    hint.icon:SetSize(34, 34); hint.icon:SetPoint("TOP", 0, 0)
                    hint.icon:SetTexture("Interface\\TargetingFrame\\UI-RaidTargetingIcon_1")
                end
                hint.icon:SetShown(star); hint.pointer:SetShown(not star); hint.symbol:Hide()
            else
                hint:SetSize(16, 16); hint:SetPoint("LEFT", markerAnchor(plate), "RIGHT", 3, 0)
                hint.icon:ClearAllPoints(); hint.icon:SetAllPoints()
                local icon = ns.Option("npcMarker") == "quest" and "Interface\\GossipFrame\\AvailableQuestIcon" or ns.StopIcon(target)
                hint.icon:SetTexture(icon); hint.icon:SetShown(icon ~= nil)
                hint.symbol:SetText(ns.StopSymbol(target)); hint.symbol:SetShown(icon == nil)
            end
            hint:Show()
            ns.npcHintCount = ns.npcHintCount + 1
        end
    end
    ns.npcHintStatus = "Public NPC IDs/quest flags; alternative drop sources included. Outside combat only."
end

ns.On("NAME_PLATE_UNIT_ADDED", function(unit)
    if not ns.Public(unit) or type(unit) ~= "string" or not string.match(unit, "^nameplate%d+$") then return end
    local count = 0
    for _ in pairs(units) do count = count + 1 end
    if count >= 40 and not units[unit] then return end
    units[unit] = true
    ns.UpdateNPCHints()
end)

ns.On("NAME_PLATE_UNIT_REMOVED", function(unit)
    if not ns.Public(unit) or type(unit) ~= "string" then return end
    units[unit] = nil
    if hints[unit] then hide(hints[unit]) end
end)

ns.On("PLAYER_REGEN_DISABLED", function()
    for _, hint in pairs(hints) do hide(hint) end
    ns.npcHintsPending = true
end)
