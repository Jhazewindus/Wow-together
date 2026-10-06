local addonName, ns = ...

local defaults = {autoAccept = false, npcHints = true, nameplateHints = true, classQuests = false,
    dungeonPrompts = true, zonePrompts = true, trackerOpacity = 0.08,
    trackerHeight = 350, circuitRadius = 0.16, circuitLimit = 6, mapLegend = true, professionBatch = 5, routeArrow = true,
    currentQuestsFirst = true, nearbyPickups = true, fullRoute = false, routeAhead = 2, autoTurnIn = false,
    scanSkipped = false, distanceUnits = "yards", trackerAuto = true, autoSelectQuests = false,
    suggestFlights = true, autoFly = false, nearbyFlights = true, corpseArrow = true, npcMarker = "star", recordQuestData = true,
    useLearnedQuests = true, exportCharacterNames = false, fixedZoneGuides = true,
    standaloneArrow = false, travelNetwork = true, soloMode = false, questGiverStars = true, patrolHints = true, hearthstoneTips = true}

function ns.Option(key)
    local value = ns.db and ns.db.config and ns.db.config[key]
    if value == nil then return defaults[key] end
    return value
end

function ns.PartyFeaturesEnabled() return not ns.Option("soloMode") end

local sections = {
    {"play", "Play mode", {
        {"soloMode", "Solo leveling mode", "Disable party messages, shared progress, route invitations and catch-up. Guides use only your own progress, even while grouped."}}},
    {"guides", "Leveling guides", {
        {"fixedZoneGuides", "Follow fixed zone guides", "Generate a complete zone sequence once. Quest progress advances steps without reordering. Turn off for adaptive trips; start a guide again to change its mode."},
        {"nearbyPickups", "Collect useful quests nearby", "Collect useful selected-guide quests offered at an NPC visit; also add nearby pickups to quest-log trips. Level range, prerequisites and skips still apply."},
        {"classQuests", "Include class quests", "Class restrictions are shown. Personal profession quests remain in Profession guides."},
        {"dungeonPrompts", "Suggest dungeon quest collection", "Offer a plan when your character meets every known pickup level for the dungeon's relevant regular quests. Prerequisites still apply; party sync is not required."},
        {"zonePrompts", "Suggest the next nearby zone", "Offer a known questline transition after the current work is complete."},
        {"scanSkipped", "Reconsider skips when scanning", "Scan guide clears saved skips for quests in the selected guide before replanning. Leave off to keep skips."},
        {"circuitRadius", "Nearby pickup distance", "Limit how much additional walking a nearby pickup adds to the current trip.", {{0.10, "Stay close"}, {0.16, "Small detours"}, {0.22, "Wider loop"}}}}},
    {"navigation", "Arrow and map", {
        {"routeArrow", "Show the direction arrow", "A movable guide panel with the current instruction and step controls."},
        {"standaloneArrow", "Show a standalone direction arrow", "A small separately movable arrow and distance. You can hide the large direction panel and keep this arrow."},
        {"distanceUnits", "Distance units", "Choose how distances appear under the arrow.", {{"yards", "Yards"}, {"metres", "Metres"}}},
        {"mapLegend", "Show route explanation on the map", "Show route status below the world map. Route controls remain available."}}},
    {"travel", "Travel routing", {
        {"travelNetwork", "Use travel connections", "Find a short travel path through known zone crossings, city gates and transports. Guide order stays fixed. Walk segments remain estimates."},
        {"suggestFlights", "Suggest faster known flights", "Compare walking with routes learned at flight masters. Timed flights improve travel estimates."},
        {"nearbyFlights", "Nearby flight-path tips", "Show a quiet tip within 150 metres of a friendly flight master. Known paths are hidden; unknown unlocks say Check. The quest step stays in place."},
        {"hearthstoneTips", "Useful hearthstone tips", "Suggest a nearby inn when upcoming guide objectives return to that hub for multiple turn-ins. Optional advice within 150 metres; no automatic binding or route changes."},
        {"autoFly", "Select the suggested flight", "Opt-in: when you open the correct flight master's map, request the suggested reachable destination outside combat. Test this on your beta build."},
        {"corpseArrow", "Point to my corpse while dead", "Temporarily replace quest directions while you are a ghost, then resume the guide."}}},
    {"party", "Party progress", {
        {"trackerAuto", "Show party progress automatically", "Show when joining a party; hide when solo or in a raid. You can close it for the current party session."},
        {"trackerOpacity", "Party panel background", "Choose readability behind quest progress text.", {{0, "Transparent"}, {0.08, "Subtle"}, {0.25, "Dark glass"}, {0.5, "Dark"}}},
        {"trackerHeight", "Party panel size", "How much progress is visible before you scroll.", {{220, "Compact"}, {350, "Comfortable"}, {500, "Tall"}}}}},
    {"markers", "Quest markers", {
        {"npcHints", "Mark needed quest NPCs and items", "Show a marker beside public quest-related nameplates and a quest-item tooltip hint, outside combat."},
        {"nameplateHints", "Show quest markers beside names", "Turn nameplate markers on or off separately from quest-item tooltip hints. Markers hide during combat."},
        {"questGiverStars", "Star above guide quest givers", "Highlight eligible pickups in your selected guide with a large gold star. Requires visible friendly NPC nameplates; hides during combat."},
        {"patrolHints", "Show quest-giver patrols on the map", "Show a thin amber search path for upcoming quest givers with published patrol waypoints. It is a possible patrol path, not their live position."},
        {"npcMarker", "Objective marker style", "Choose a star, cross, kill skull, or quest ! beside needed enemy names.", {{"star", "Star"}, {"cross", "Cross"}, {"skull", "Skull for kills"}, {"quest", "Quest !"}}}}},
    {"automation", "Quest dialogs", {
        {"autoSelectQuests", "Open guide quests at an NPC", "Select useful pickups for this guide as the NPC list returns, or the current completed turn-in. Combine with auto-accept to collect a visit; unrelated quests stay manual."},
        {"autoAccept", "Accept guide quests only", "Opt-in: accept an opened pickup only when it belongs to the selected guide and passes its level, race, prerequisite and skip checks. Other quests stay manual."},
        {"autoTurnIn", "Turn in quests without a reward choice", "Opt-in: handle completed quest dialogs you open. Item reward choices always remain manual."}}},
    {"research", "Quest data for testing", {
        {"recordQuestData", "Record NPC offers and quest progression", "Save the latest 300 local observations for prerequisite research. Export manually; no chat or automatic uploads."},
        {"useLearnedQuests", "Use observed prerequisite patterns", "Ordinary findings apply across classes/races within a faction and build. Restricted quests keep their class/race scope. Requires an observed unlock; skipping alone teaches no prerequisite."},
        {"exportCharacterNames", "Include source names in guide findings", "Optional: attribute findings to the character that observed them. Quest data exports always omit character names."}}},
    {"professions", "Personal professions", {
        {"professionBatch", "Crafts per suggested batch", "Set the number of crafts used to calculate materials in your personal profession guide.", {{1, "1 craft"}, {5, "5 crafts"}, {10, "10 crafts"}, {20, "20 crafts"}}}}}
}

function ns.InitializeConfig()
    if type(ns.db.config) ~= "table" then ns.db.config = {} end
    -- Adopt the requested star default once; later explicit choices survive.
    if not ns.db.config.starMarkerDefault then
        if ns.db.config.npcMarker == "cross" then ns.db.config.npcMarker = "star" end
        ns.db.config.starMarkerDefault = true
    end
    ns.db.config.betaPickupCheck = nil -- Retired: this API measures sharing, not pickup eligibility.
    for key, value in pairs(defaults) do
        local configured = ns.db.config[key]
        if type(configured) ~= type(value) or (type(configured) == "number"
            and (configured ~= configured or configured == math.huge or configured == -math.huge)) then ns.db.config[key] = value end
    end
    ns.db.config.trackerOpacity = math.max(0, math.min(0.8, ns.db.config.trackerOpacity))
    ns.db.config.trackerHeight = math.max(180, math.min(600, ns.db.config.trackerHeight))
    ns.db.config.circuitRadius = math.max(0.08, math.min(0.24, ns.db.config.circuitRadius))
    ns.db.config.circuitLimit = math.max(2, math.min(6, math.floor(ns.db.config.circuitLimit)))
    ns.db.config.professionBatch = math.max(1, math.min(20, math.floor(ns.db.config.professionBatch)))
    ns.db.config.routeAhead = math.max(0, math.min(2, math.floor(ns.db.config.routeAhead)))
    if ns.db.config.distanceUnits ~= "yards" and ns.db.config.distanceUnits ~= "metres" then ns.db.config.distanceUnits = "yards" end
    if ns.db.config.npcMarker ~= "star" and ns.db.config.npcMarker ~= "cross" and ns.db.config.npcMarker ~= "skull" and ns.db.config.npcMarker ~= "quest" then ns.db.config.npcMarker = "star" end
end

function ns.SetOption(key, value)
    if defaults[key] == nil or type(value) ~= type(defaults[key]) then return end
    local changed = ns.Option(key) ~= value
    if key == "recordQuestData" and ns.Option(key) ~= value then ns.ResearchCaptureBoundary() end
    ns.db.config[key] = value
    ns.InitializeConfig()
    if key == "soloMode" and changed then ns.ApplyPartyMode() end
    ns.flightPlanCache = nil
    ns.ResetTravelPath()
    if key == "nearbyPickups" or key == "useLearnedQuests" then ns.forceRouteReplan, ns.routeSignature = true, nil end
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
        page.contentHeight = section[1] == "research" and 310 or #section[3] * 52
        for index, entry in ipairs(section[3]) do
            local key, y = entry[1], -(index - 1) * 52
            local caption = ns.UILabel(page, "GameFontNormal", 12)
            caption:SetPoint("TOPLEFT", 32, y - 3); caption:SetSize(entry[4] and 318 or 544, 16); caption:SetWordWrap(false); caption:SetText(entry[2])
            local help = ns.UILabel(page, nil, 10)
            help:SetPoint("TOPLEFT", 32, y - 22); help:SetSize(540, 26); help:SetJustifyV("TOP"); help:SetText(entry[3]); help:SetTextColor(unpack(ns.UIColors.muted))
            if entry[4] then
                local select = ns.UIDropdown(page, entry[4], 200, function(value) ns.SetOption(key, value) end)
                select:SetPoint("TOPRIGHT", -4, y + 4); frame.dropdowns[key] = select
            else
                local check = CreateFrame("CheckButton", nil, page, "UICheckButtonTemplate")
                check:SetSize(24, 24); check:SetPoint("TOPLEFT", 0, y + 2)
                check:SetScript("OnClick", function(self) ns.SetOption(key, self:GetChecked() == true) end)
                frame.checks[key] = check
            end
        end
        page:Hide()
    end
    local research = frame.pages.research
    local instructions = ns.UILabel(research, nil, 11)
    instructions:SetPoint("TOPLEFT", 32, -180); instructions:SetSize(520, 80)
    instructions:SetText("Visit quest givers before and after turning in a prerequisite.\nExport after your session, then Select all and Ctrl+C. Send the export as a text file, labeled with your tester name.\nLevel/reputation changes are recorded as possible alternative causes.")
    local export = ns.UIButton(research, "Export quest data", 150, ns.ShowQuestResearch)
    export:SetPoint("TOPLEFT", 32, -272)
    frame.researchExport = export
    frame.findingsExport = ns.UIButton(research, "Export guide findings", 175, ns.ShowGuideFindings)
    frame.findingsExport:SetPoint("TOPLEFT", 196, -272)
    frame.section = ns.UIDropdown(frame, choices, 280, function(key) frame.sectionKey = key; ns.RenderSettings() end)
    frame.section:SetPoint("TOPLEFT", 22, -51); frame.sectionKey = "play"
    frame.note = ns.UILabel(frame, nil, 11)
    frame.note:SetPoint("BOTTOMLEFT", 22, 16); frame.note:SetWidth(390); frame.note:SetHeight(28); frame.note:SetTextColor(unpack(ns.UIColors.muted))
    local reset = ns.UIButton(frame, "Reset guide skips", 135, ns.ResetGuideSkips)
    reset:SetPoint("BOTTOMRIGHT", -22, 18)
    ns.UIHelp(reset, "Clear every saved quest/step skip for this character, across all guides and zones. Quest completion is unchanged.")
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
    ns.settings.note:SetText(ns.Option("soloMode") and "Solo leveling: party features are disabled.\nQuest progress and saved guides still update." or "Party guides help useful catch-up first.\nChoose quest-log detours when starting a guide.")
end

function ns.ToggleSettings()
    ns.settings:SetShown(not ns.settings:IsShown()); ns.RenderSettings()
end
