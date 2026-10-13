local addonName, ns = ...

local defaults = {autoAccept = false, npcHints = true, nameplateHints = true, classQuests = true,
    dungeonPrompts = true, dungeonMapPrompt = true, zonePrompts = true, trackerOpacity = 0.08,
    trackerHeight = 350, circuitRadius = 0.16, circuitLimit = 6, mapLegend = true, routeArrow = true,
    currentQuestsFirst = true, nearbyPickups = true, fullRoute = false, routeAhead = 2, autoTurnIn = false,
    scanSkipped = false, distanceUnits = "yards", trackerAuto = true, autoSelectQuests = false,
    suggestFlights = true, autoFly = false, nearbyFlights = true, corpseArrow = true, npcMarker = "star", recordQuestData = true,
    useLearnedQuests = true, exportCharacterNames = false, fixedZoneGuides = true,
    standaloneArrow = false, travelNetwork = true, soloMode = false, questGiverStars = true, patrolHints = true, eliteSpawnHints = true, hearthstoneTips = true,
    guideOpaque = true, highlightGuideQuest = true, classTraining = true,
    inventoryServices = true, restockSupplies = true, supplyTarget = 20, groupFinderRoles = true,
    unitNumbers = false, approachMaps = true}

function ns.Option(key)
    local value = ns.db and ns.db.config and ns.db.config[key]
    if value == nil then return defaults[key] end
    return value
end

function ns.PartyFeaturesEnabled() return not ns.Option("soloMode") end

local sections = {
    {"leveling", "Leveling", {
        {"fixedZoneGuides", "Keep the zone guide order fixed", "Follow the guide's planned order. Turn this off to plan around your current quests and location."},
        {"nearbyPickups", "Add useful nearby quests", "Add eligible quests when their giver is close to your planned pickup route."},
        {"classQuests", "Include class quests", "Show quests that are only available to your class."},
        {"classTraining", "Suggest class training", "Add a nearby trainer stop at even levels when it fits the route."},
        {"zonePrompts", "Suggest the next zone", "Offer a suitable neighbouring zone when your level and progress are a good fit."},
        {"scanSkipped", "Recheck skipped quests on scan", "A successful scan clears skips for this guide so eligible quests can return."},
        {"circuitRadius", "Nearby quest detours", "Limit extra walking when adding a nearby pickup.", {{0.10, "Shortest"}, {0.16, "Small"}, {0.22, "Wider"}}}},
        "Set how zone guides choose quests and suggest your next area."},
    {"dungeons", "Dungeons", {
        {"dungeonPrompts", "Suggest dungeon quests", "Offer dungeon quests when you reach their pickup level. Earlier chain quests may still be needed."},
        {"dungeonMapPrompt", "Ask to open the dungeon map", "Ask when you enter a dungeon; you can keep playing without opening it."},
        {"approachMaps", "Show maps near dungeon entrances", "Open a live map in supported caves and tunnels outside a dungeon."}},
        "Choose when dungeon quests and maps appear in your route."},
    {"quests", "Quest log and dialogs", {
        {"highlightGuideQuest", "Highlight the current guide quest", "Select it in the game quest log and show Blizzard's map highlights when supported."},
        {"autoSelectQuests", "Open guide quests at NPCs", "Open a suitable guide quest or ready turn-in when you talk to its NPC."},
        {"autoAccept", "Auto-accept guide quests", "Accept only an opened quest that belongs to your active guide."},
        {"autoTurnIn", "Auto-turn in quests with no reward choice", "Turn in when the dialog opens if there is no reward to choose."}},
        "Choose how the addon uses the quest log and handles NPC dialogs."},
    {"navigation", "Arrow and display", {
        {"routeArrow", "Show the guide window", "Show the current step, direction and guide controls."},
        {"guideOpaque", "Solid guide background", "Use a solid background for easier reading; turn off for a translucent panel."},
        {"standaloneArrow", "Show a separate direction arrow", "Show direction, distance and travel time in a small separate panel."},
        {"distanceUnits", "Distance units", "Choose the unit shown below the arrow.", {{"yards", "Yards"}, {"metres", "Metres"}}},
        {"mapLegend", "Show map route details", "Show a short route explanation below the world map."},
        {"unitNumbers", "Always show health and resource numbers", "Keep numbers visible on Blizzard's unit bars. Turn off to restore your previous setting."}},
        "Choose what you see while following a guide step."},
    {"travel", "Travel and tips", {
        {"travelNetwork", "Use mapped travel routes", "Route through known terrain points, zone links, city gates and transports."},
        {"suggestFlights", "Suggest faster flight paths", "Suggest a flight you have unlocked when it should save time."},
        {"nearbyFlights", "Suggest nearby flight masters", "Point out a friendly unlearned flight master near you or your route."},
        {"autoFly", "Select suggested flights automatically", "Select the route's flight when its flight-master map is open, outside combat."},
        {"hearthstoneTips", "Suggest useful inns", "Suggest setting your hearthstone when a nearby inn could help later."},
        {"corpseArrow", "Guide me to my corpse", "Temporarily point to your corpse while you are a ghost, then resume the guide."}},
        "Choose which travel options and nearby tips the guide uses."},
    {"markers", "Quest markers", {
        {"npcHints", "Mark quest NPCs and items", "Mark useful NPCs beside their names and quest items in tooltips."},
        {"nameplateHints", "Show markers beside nameplates", "Show or hide quest markers beside unit names. Markers are hidden in combat."},
        {"questGiverStars", "Star guide quest givers", "Show a gold star over an eligible quest giver in your selected guide."},
        {"patrolHints", "Show quest giver patrols", "Show known wandering paths on the map."},
        {"eliteSpawnHints", "Show elite spawn points", "Show known spawn points while the matching elite quest step is active."},
        {"npcMarker", "Enemy marker style", "Choose the marker beside quest enemies.", {{"star", "Star"}, {"cross", "Cross"}, {"skull", "Skull"}, {"quest", "Quest !"}}}},
        "Choose which quest targets are marked in the world."},
    {"party", "Party and group finder", {
        {"soloMode", "Use solo leveling mode", "Turn off party messages, shared progress, invites and catch-up routes."},
        {"groupFinderRoles", "Add filters to Looking For Group", "Filter Blizzard's player list by role and class."},
        {"trackerAuto", "Show party progress when grouped", "Show in a party; hide when solo or in a raid. You can close it for this session."},
        {"trackerOpacity", "Party panel background", "Choose how dark the progress panel appears.", {{0, "Clear"}, {0.08, "Light"}, {0.25, "Medium"}, {0.5, "Dark"}}},
        {"trackerHeight", "Party panel height", "Choose how many members appear before scrolling.", {{220, "Compact"}, {350, "Standard"}, {500, "Tall"}}}},
        "Set up group finder filters and party progress."},
    {"services", "Bags and supplies", {
        {"inventoryServices", "Suggest vendor stops", "Suggest a nearby vendor when bags are nearly full or gear is badly damaged."},
        {"restockSupplies", "Suggest food and drink", "Suggest basic food or mana drink when your supply is low. Buying stays manual."},
        {"supplyTarget", "Food and drink amount", "How many of each to carry after a restock.", {{10, "10 each"}, {20, "20 each"}, {40, "40 each"}}}},
        "Optional stops for bags, repairs, food and drink."},
    {"data", "Quest data and saved progress", {
        {"recordQuestData", "Record quest offers and progress", "Save up to 300 local observations for guide research. Exports are manual."},
        {"useLearnedQuests", "Use observed quest prerequisites", "Use confirmed unlock patterns for your faction and client build."},
        {"exportCharacterNames", "Name characters in guide findings", "Include character names in guide findings. Quest research exports never include them."}},
        "Manage local quest research and saved guide skips."}
}

function ns.InitializeConfig()
    if type(ns.db.config) ~= "table" then ns.db.config = {} end
    -- Adopt the requested star default once; later explicit choices survive.
    if not ns.db.config.starMarkerDefault then
        if ns.db.config.npcMarker == "cross" then ns.db.config.npcMarker = "star" end
        ns.db.config.starMarkerDefault = true
    end
    ns.db.config.betaPickupCheck = nil -- Retired: this API measures sharing, not pickup eligibility.
    ns.db.config.professionBatch = nil -- Craft quantities now belong to the guide.
    for key, value in pairs(defaults) do
        local configured = ns.db.config[key]
        if type(configured) ~= type(value) or (type(configured) == "number"
            and (configured ~= configured or configured == math.huge or configured == -math.huge)) then ns.db.config[key] = value end
    end
    ns.db.config.trackerOpacity = math.max(0, math.min(0.8, ns.db.config.trackerOpacity))
    ns.db.config.trackerHeight = math.max(180, math.min(600, ns.db.config.trackerHeight))
    ns.db.config.circuitRadius = math.max(0.08, math.min(0.24, ns.db.config.circuitRadius))
    ns.db.config.circuitLimit = math.max(2, math.min(6, math.floor(ns.db.config.circuitLimit)))
    ns.db.config.routeAhead = math.max(0, math.min(2, math.floor(ns.db.config.routeAhead)))
    if ns.db.config.distanceUnits ~= "yards" and ns.db.config.distanceUnits ~= "metres" then ns.db.config.distanceUnits = "yards" end
    if ns.db.config.npcMarker ~= "star" and ns.db.config.npcMarker ~= "cross" and ns.db.config.npcMarker ~= "skull" and ns.db.config.npcMarker ~= "quest" then ns.db.config.npcMarker = "star" end
    if ns.db.config.supplyTarget ~= 10 and ns.db.config.supplyTarget ~= 20 and ns.db.config.supplyTarget ~= 40 then ns.db.config.supplyTarget = 20 end
end

function ns.SetOption(key, value)
    if defaults[key] == nil or type(value) ~= type(defaults[key]) then return end
    local changed = ns.Option(key) ~= value
    if key == "recordQuestData" and ns.Option(key) ~= value then ns.ResearchCaptureBoundary() end
    ns.db.config[key] = value
    ns.InitializeConfig()
    if key == "unitNumbers" then
        if ns.ApplyUnitNumbers then ns.ApplyUnitNumbers() end
        if ns.RenderSettings then ns.RenderSettings() end
        return
    end
    if key == "approachMaps" then
        if ns.CheckApproachMap then ns.CheckApproachMap() end
        if ns.RenderSettings then ns.RenderSettings() end
        return
    end
    if key == "guideOpaque" then
        ns.UpdateNavigationBackground()
        if ns.RenderSettings then ns.RenderSettings() end
        return
    end
    if key == "soloMode" and changed then ns.ApplyPartyMode() end
    if key == "inventoryServices" and not value then ns.ClearInventoryService() end
    if key == "inventoryServices" and value or key == "restockSupplies" or key == "supplyTarget" then ns.QueueServiceInventory() end
    ns.flightPlanCache = nil
    ns.ResetTravelPath()
    if key == "nearbyPickups" or key == "useLearnedQuests" then ns.forceRouteReplan, ns.routeSignature = true, nil end
    if key == "classQuests" and changed then
        ns.navigationPreview, ns.routeSignature, ns.forceRouteReplan = nil, nil, true
        -- Apply immediately even if the main window is hidden or being resized.
        ns.UpdateSelectedRoute(nil, ns.NewQuestQuery())
    end
    if ns.RenderSettings then ns.RenderSettings() end
    if ns.UpdateNPCHints then ns.UpdateNPCHints() end
    if ns.DrawRoute then ns.DrawRoute() end
    ns.Refresh()
end

function ns.AutoAcceptOpenedQuest(id)
    if not ns.Option("autoAccept") or type(AcceptQuest) ~= "function" or ns.RouteInCombat()
        or not ns.GuideInteger(id) or id <= 0 or ns.active[id] or ns.autoAcceptAttempt == id then return end
    if not ns.CanAutoAcceptGuideQuest(id) then return end
    if type(CanAcceptQuest) == "function" then
        local allowed = CanAcceptQuest()
        if not ns.Public(allowed) or allowed ~= true then return end
    end
    ns.autoAcceptAttempt = id
    -- Opt-in, one eligible opened pickup in the selected guide only.
    AcceptQuest()
    ns.ScheduleSync()
end

function ns.CreateSettings()
    local frame = CreateFrame("Frame", "WowTogetherSettings", UIParent, "BackdropTemplate")
    ns.settings = frame
    frame:SetSize(620, 550); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
    frame:SetClampedToScreen(true); ns.UIPanel(frame, ns.UIColors.background)
    frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    local title = ns.UILabel(frame, "GameFontNormalLarge", 20)
    title:SetPoint("TOPLEFT", 22, -18); title:SetText("Settings")
    ns.UIClose(frame); ns.UIDivider(frame, -89)
    frame.checks, frame.dropdowns, frame.pages, frame.values = {}, {}, {}, {}
    local choices = {}
    for _, section in ipairs(sections) do
        choices[#choices + 1] = {section[1], section[2]}
        local page = CreateFrame("Frame", nil, frame)
        page:SetPoint("TOPLEFT", 22, -104); page:SetSize(576, 374); frame.pages[section[1]] = page
        page.heading = ns.UILabel(page, "GameFontNormal", 13)
        page.heading:SetPoint("TOPLEFT", 32, -2); page.heading:SetSize(540, 18); page.heading:SetWordWrap(false)
        page.heading:SetText(section[2])
        page.description = ns.UILabel(page, nil, 10)
        page.description:SetPoint("TOPLEFT", 32, -22); page.description:SetSize(540, 28); page.description:SetWordWrap(true)
        page.description:SetJustifyV("TOP"); page.description:SetText(section[4]); page.description:SetTextColor(unpack(ns.UIColors.muted))
        local cursor = 54
        for _, entry in ipairs(section[3]) do
            local key = entry[1]
            local caption = ns.UILabel(page, "GameFontNormal", 12)
            caption:SetPoint("TOPLEFT", 32, -cursor); caption:SetSize(entry[4] and 318 or 544, 16); caption:SetWordWrap(false); caption:SetText(entry[2])
            local help = ns.UILabel(page, nil, 10)
            help:SetPoint("TOPLEFT", 32, -cursor - 18); help:SetWidth(540); help:SetHeight(42); help:SetWordWrap(true); help:SetJustifyV("TOP"); help:SetText(entry[3]); help:SetTextColor(unpack(ns.UIColors.muted))
            local measured = ns.ReadPublic(help.GetStringHeight, help)
            local helpHeight = type(measured) == "number" and math.max(16, math.min(42, measured)) or 30
            help:SetHeight(helpHeight)
            if entry[4] then
                local select = ns.UIDropdown(page, entry[4], 200, function(value) ns.SetOption(key, value) end)
                select:SetPoint("TOPRIGHT", -4, -cursor + 4); frame.dropdowns[key] = select
            else
                local check = CreateFrame("CheckButton", nil, page, "UICheckButtonTemplate")
                check:SetSize(24, 24); check:SetPoint("TOPLEFT", 0, -cursor + 2)
                check:SetScript("OnClick", function(self) ns.SetOption(key, self:GetChecked() == true) end)
                frame.checks[key] = check
            end
            cursor = cursor + 18 + helpHeight + 10
        end
        page.optionsHeight = cursor + 4
        page.contentHeight = page.optionsHeight
        page:Hide()
    end
    local research = frame.pages.data
    local instructions = ns.UILabel(research, nil, 11)
    local extraTop = research.optionsHeight + 8
    instructions:SetPoint("TOPLEFT", 32, -extraTop); instructions:SetSize(520, 64); instructions:SetWordWrap(true); instructions:SetJustifyV("TOP")
    instructions:SetText("For useful findings, check the quest giver before and after a chain step. Export after your session and share the text file with the tester name.")
    local export = ns.UIButton(research, "Export quest data", 150, ns.ShowQuestResearch)
    local buttonTop = extraTop + 72
    export:SetPoint("TOPLEFT", 32, -buttonTop)
    frame.researchExport = export
    frame.findingsExport = ns.UIButton(research, "Export guide findings", 175, ns.ShowGuideFindings)
    frame.findingsExport:SetPoint("TOPLEFT", 194, -buttonTop)
    local reset = ns.UIButton(research, "Reset guide skips", 135, ns.ResetGuideSkips)
    reset:SetPoint("TOPRIGHT", -4, -buttonTop)
    ns.UIHelp(reset, "Clear saved quest and step skips for this character across every guide and zone. Quest completion is unchanged.")
    frame.resetSkips = reset
    research.contentHeight = buttonTop + 38
    frame.section = ns.UIDropdown(frame, choices, 280, function(key) frame.sectionKey = key; ns.RenderSettings() end)
    frame.section:SetPoint("TOPLEFT", 22, -51); frame.sectionKey = "leveling"
    frame.note = ns.UILabel(frame, nil, 11)
    frame.note:SetPoint("BOTTOMLEFT", 22, 16); frame.note:SetWidth(390); frame.note:SetHeight(28); frame.note:SetTextColor(unpack(ns.UIColors.muted))
    frame.note:Hide()
    frame:Hide()
    if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherSettings") end
end

function ns.RenderSettings()
    if not ns.settings then return end
    local page = ns.settings.pages[ns.settings.sectionKey]
    local height = math.max(240, 104 + page.contentHeight + 64)
    if ns.settings:GetHeight() ~= height then
        -- Keep the title in place while switching between short/long pages.
        local left, top = ns.ReadPublic(ns.settings.GetLeft, ns.settings), ns.ReadPublic(ns.settings.GetTop, ns.settings)
        if type(left) == "number" and type(top) == "number" then
            ns.settings:ClearAllPoints(); ns.settings:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", left, top)
        end
        ns.settings:SetHeight(height)
    end
    page:SetHeight(page.contentHeight)
    for key, check in pairs(ns.settings.checks) do check:SetChecked(ns.Option(key)) end
    for key, control in pairs(ns.settings.dropdowns) do control:SetChoice(ns.Option(key)) end
    for key, page in pairs(ns.settings.pages) do page:SetShown(key == ns.settings.sectionKey) end
    ns.settings.section:SetChoice(ns.settings.sectionKey)
end

function ns.ToggleSettings()
    ns.settings:SetShown(not ns.settings:IsShown()); ns.RenderSettings()
end
