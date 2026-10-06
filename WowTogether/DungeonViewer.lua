local addonName, ns = ...

local colors, fallback = ns.UIColors, "Interface\\Icons\\INV_Misc_QuestionMark"
local bossFallback = "Interface\\EncounterJournal\\UI-EJ-BOSS-Default"
local selected, entered
local function coordinate(value)
    return ns.Public(value) and type(value) == "number" and value == value and math.abs(value) < 100000
end
local function keepPosition(frame)
    local left, top = ns.ReadPublic(frame.GetLeft, frame), ns.ReadPublic(frame.GetTop, frame)
    if coordinate(left) and coordinate(top) then
        frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", left, top)
    end
end
local function save(frame)
    if not ns.db then return end
    local state = type(ns.db.dungeonViewerUI) == "table" and ns.db.dungeonViewerUI or {}
    ns.db.dungeonViewerUI = state
    if frame.compact then frame.compactSize = {frame:GetWidth(), frame:GetHeight()}
    else frame.fullSize = {frame:GetWidth(), frame:GetHeight()} end
    state.fullSize, state.compactSize, state.transparent = frame.fullSize, frame.compactSize, frame.transparent == true
    local left, top = ns.ReadPublic(frame.GetLeft, frame), ns.ReadPublic(frame.GetTop, frame)
    if coordinate(left) and coordinate(top) then
        state.left, state.top = left, top
        state[frame.compact and "compactLeft" or "fullLeft"] = left
        state[frame.compact and "compactTop" or "fullTop"] = top
    end
end
local function savedSize(value, minimumWidth, minimumHeight, default)
    if type(value) == "table" and coordinate(value[1]) and coordinate(value[2]) then
        return {math.max(minimumWidth, math.min(1400, value[1])), math.max(minimumHeight, math.min(1000, value[2]))}
    end
    return default
end
local function anchor(frame, x, y, width, height)
    frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", x, -y); frame:SetSize(width, height)
end
local function layout(frame)
    if not frame.layoutReady or frame.layingOut then return end
    frame.layingOut = true
    local width, height = frame:GetWidth(), frame:GetHeight()
    frame.title:SetWidth(width - 74); frame.summary:SetWidth(width - 216)
    local mapWidth, mapHeight
    if frame.compact then
        mapWidth, mapHeight = width - 24, height - 166
        anchor(frame.floorMenu, 12, 86, math.max(130, mapWidth - 124), 26)
        anchor(frame.refresh, width - 124, 86, 112, 26)
        anchor(frame.map, 12, 122, mapWidth, mapHeight)
        frame.mapNote:Hide(); frame.bossInfo:Hide(); frame.questList:Hide()
        frame.footer:SetWidth(width - 30); frame.footer:SetText("Resize corner • Click bosses for loot in Full view")
    else
        local bossWidth, lootWidth = 200, math.max(270, math.min(350, width * .2926))
        mapWidth, mapHeight = width - bossWidth - lootWidth - 64, height - 317
        local lootX = width - lootWidth - 20
        anchor(frame.bossPanel, 20, 94, bossWidth, height - 140)
        anchor(frame.floorMenu, 232, 94, math.max(150, mapWidth - 124), 26)
        anchor(frame.refresh, 232 + mapWidth - 112, 94, 112, 26)
        anchor(frame.map, 232, 132, mapWidth, mapHeight)
        anchor(frame.mapNote, 232, height - 173, mapWidth, 58); frame.mapNote:Show()
        anchor(frame.bossInfo, 232, height - 105, mapWidth, 59); frame.bossInfo:Show()
        frame.bossName:SetWidth(mapWidth - 74); frame.bossDetail:SetWidth(mapWidth - 74)
        anchor(frame.lootPanel, lootX, 94, lootWidth, height - 140)
        frame.lootTitle:SetWidth(lootWidth - 24); frame.lootType:SetWidth(lootWidth - 24); frame.search:SetWidth(lootWidth - 24)
        frame.lootEmpty:SetWidth(lootWidth - 32)
        frame.bossRowsVisible = math.min(8, math.max(1, math.floor((height - 226) / 52)))
        frame.lootRowsVisible = math.min(7, math.max(1, math.floor((height - 299) / 47)))
        for _, row in ipairs(frame.lootRows) do row:SetWidth(lootWidth - 24); row.name:SetWidth(lootWidth - 70); row.detail:SetWidth(lootWidth - 70) end
        frame.footer:SetWidth(width - 144); frame.footer:SetText("Forever database snapshot • Cached client item stats • Your quest route stays unchanged")
        frame.questList:Show()
    end
    frame.bossPanel:SetShown(not frame.compact); frame.lootPanel:SetShown(not frame.compact)
    frame.mode.caption:SetText(frame.compact and "Full view" or "Map only")
    frame.layingOut = nil
    if frame.data then ns.RenderDungeonViewer() end
end
local qualityColors = {[2] = {0.25, 0.80, 0.30, 1}, [3] = {0.35, 0.60, 1, 1}, [4] = {0.72, 0.44, 0.94, 1}, [5] = {1, 0.55, 0.15, 1}}
local slots = {[1]="Head",[2]="Neck",[3]="Shoulder",[5]="Chest",[6]="Waist",[7]="Legs",[8]="Feet",[9]="Wrist",[10]="Hands",[11]="Finger",[12]="Trinket",[13]="One-hand",[14]="Shield",[15]="Ranged",[16]="Back",[17]="Two-hand",[21]="Main hand",[22]="Off hand",[23]="Held in off hand",[25]="Thrown",[26]="Ranged"}
local function image(texture, asset)
    local good = asset and ns.ReadPublic(texture.SetTexture, texture, asset) == true
    if not good then texture:SetTexture(fallback) end
    return good
end
local function heading(parent, text, size, x, y, width)
    local font = ns.UILabel(parent, "GameFontNormal", size or 13)
    font:SetPoint("TOPLEFT", x, y); font:SetSize(width, 24); font:SetWordWrap(false); font:SetText(text)
    return font
end
local function paging(parent, previous, nextPage)
    local bar = CreateFrame("Frame", nil, parent)
    bar:SetSize(180, 26); bar:SetPoint("BOTTOM", 0, 10)
    bar.prev = ns.UIButton(bar, "‹", 26, previous); bar.prev:SetPoint("LEFT")
    bar.next = ns.UIButton(bar, "›", 26, nextPage); bar.next:SetPoint("RIGHT")
    bar.text = ns.UILabel(bar, nil, 10, colors.muted); bar.text:SetPoint("CENTER"); bar.text:SetSize(120, 18); bar.text:SetJustifyH("CENTER")
    return bar
end
local function selectBoss(id)
    local frame = ns.dungeonViewer
    if not frame or not frame.data then return end
    for index, boss in ipairs(frame.data.bosses) do
        if boss.id == id then
            frame.bossID, frame.lootPage = id, 1
            frame.bossPage = math.floor((index - 1) / frame.bossRowsVisible) + 1
            if boss.mapID then
                for floor, map in ipairs(frame.data.maps) do if map.mapID == boss.mapID then frame.floor = floor; break end end
            end
            ns.RenderDungeonViewer(); return
        end
    end
end
local function create()
    if ns.dungeonViewer then return ns.dungeonViewer end
    local frame = CreateFrame("Frame", "WowTogetherDungeonViewer", UIParent, "BackdropTemplate")
    ns.dungeonViewer = frame
    local state = type(ns.db.dungeonViewerUI) == "table" and ns.db.dungeonViewerUI or {}
    frame.fullSize = savedSize(state.fullSize, 940, 500, {1080, 650})
    frame.compactSize = savedSize(state.compactSize, 380, 300, {500, 420})
    frame:SetSize(unpack(frame.fullSize)); frame:SetPoint("CENTER"); frame:SetFrameStrata("MEDIUM"); frame:SetClampedToScreen(true)
    local left, top = state.fullLeft or state.left, state.fullTop or state.top
    if coordinate(left) and coordinate(top) then frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", left, top) end
    ns.UIPanel(frame, colors.background); frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving); frame:SetScript("OnDragStop", function() frame:StopMovingOrSizing(); save(frame) end)
    frame.title = heading(frame, "Dungeon atlas", 20, 20, -18, 950)
    frame.summary = ns.UILabel(frame, nil, 11, colors.muted); frame.summary:SetPoint("TOPLEFT", 20, -49); frame.summary:SetSize(960, 20)
    ns.UIClose(frame); ns.UIDivider(frame, -80)
    frame.bossPanel = CreateFrame("Frame", nil, frame, "BackdropTemplate"); ns.UIPanel(frame.bossPanel)
    frame.bossPanel:SetPoint("TOPLEFT", 20, -94); frame.bossPanel:SetSize(200, 510)
    frame.bossTitle = heading(frame.bossPanel, "Bosses", 13, 12, -10, 176)
    frame.bossRows, frame.lootRows, frame.tiles, frame.pins, frame.itemRequests = {}, {}, {}, {}, {}
    frame.bossRowsVisible, frame.lootRowsVisible = 8, 7
    for slot = 1, frame.bossRowsVisible do
        local row = ns.UIButton(frame.bossPanel, "", 178, function() end)
        row:SetPoint("TOPLEFT", 11, -40 - (slot - 1) * 52); row:SetHeight(48); row.caption:Hide()
        row.icon = row:CreateTexture(nil, "ARTWORK"); row.icon:SetPoint("LEFT", 5, 0); row.icon:SetSize(36, 36)
        row.name = heading(row, "", 11, 46, -5, 124); row.name:SetHeight(27); row.name:SetWordWrap(true)
        row.detail = ns.UILabel(row, nil, 9, colors.muted); row.detail:SetPoint("BOTTOMLEFT", 46, 4); row.detail:SetSize(124, 12)
        row:SetScript("OnClick", function() if row.boss then selectBoss(row.boss.id) end end)
        frame.bossRows[slot] = row
    end
    frame.bossPages = paging(frame.bossPanel, function() frame.bossPage = frame.bossPage - 1; ns.RenderDungeonViewer() end,
        function() frame.bossPage = frame.bossPage + 1; ns.RenderDungeonViewer() end)
    frame.bossPanel:EnableMouseWheel(true)
    frame.bossPanel:SetScript("OnMouseWheel", function(_, delta) if ns.Public(delta) and type(delta) == "number" then frame.bossPage = frame.bossPage - delta; ns.RenderDungeonViewer() end end)
    frame.floorMenu = ns.UIDropdown(frame, {{1, "Floor 1"}}, 270, function(index) frame.floor = index; ns.RenderDungeonViewer() end)
    frame.floorMenu:SetPoint("TOPLEFT", 232, -94)
    frame.refresh = ns.UIButton(frame, "Refresh map", 112, function() ns.RefreshDungeonViewer(true) end); frame.refresh:SetPoint("TOPLEFT", 620, -94)
    frame.map = CreateFrame("Frame", nil, frame, "BackdropTemplate"); ns.UIPanel(frame.map)
    frame.map:SetPoint("TOPLEFT", 232, -132); frame.map:SetSize(500, 333)
    frame.empty = ns.UILabel(frame.map, nil, 13, colors.muted); frame.empty:SetPoint("CENTER"); frame.empty:SetSize(410, 96); frame.empty:SetJustifyH("CENTER")
    frame.mapNote = ns.UILabel(frame, nil, 10, colors.muted); frame.mapNote:SetPoint("TOPLEFT", 232, -477); frame.mapNote:SetSize(500, 58)
    frame.bossInfo = CreateFrame("Frame", nil, frame, "BackdropTemplate"); frame.bossInfo:SetPoint("TOPLEFT", 232, -545); frame.bossInfo:SetSize(500, 59); ns.UIPanel(frame.bossInfo)
    frame.portrait = frame.bossInfo:CreateTexture(nil, "ARTWORK"); frame.portrait:SetPoint("LEFT", 8, 0); frame.portrait:SetSize(44, 44)
    frame.bossName = heading(frame.bossInfo, "Select a boss", 14, 62, -8, 425)
    frame.bossDetail = ns.UILabel(frame.bossInfo, nil, 10, colors.muted); frame.bossDetail:SetPoint("TOPLEFT", 62, -34); frame.bossDetail:SetSize(425, 16)
    frame.lootPanel = CreateFrame("Frame", nil, frame, "BackdropTemplate"); ns.UIPanel(frame.lootPanel)
    frame.lootPanel:SetPoint("TOPLEFT", 744, -94); frame.lootPanel:SetSize(316, 510)
    frame.lootTitle = heading(frame.lootPanel, "Boss loot", 13, 12, -10, 292)
    frame.lootType = ns.UIDropdown(frame.lootPanel, {{"all", "All notable loot"}, {"equipment", "Equipment"}, {"other", "Quest items & other"}}, 292,
        function(value) frame.category, frame.lootPage = value, 1; ns.RenderDungeonViewer() end)
    frame.lootType:SetPoint("TOPLEFT", 12, -39)
    frame.search = ns.UIEditBox(frame.lootPanel, "Search this boss's loot", 292)
    frame.search:SetPoint("TOPLEFT", 12, -73); frame.search:SetScript("OnTextChanged", function(self)
        local value = self:GetText()
        if not ns.Public(value) or type(value) ~= "string" then return end
        self.placeholder:SetShown(value == ""); frame.query, frame.lootPage = value, 1; if frame:IsShown() then ns.RenderDungeonViewer() end
    end)
    for slot = 1, frame.lootRowsVisible do
        local row = CreateFrame("Button", nil, frame.lootPanel)
        row:SetPoint("TOPLEFT", 12, -112 - (slot - 1) * 47); row:SetSize(292, 44)
        row.icon = row:CreateTexture(nil, "ARTWORK"); row.icon:SetPoint("LEFT", 0, 0); row.icon:SetSize(34, 34)
        row.name = heading(row, "", 11, 44, -3, 246); row.name:SetHeight(25); row.name:SetWordWrap(true)
        row.detail = ns.UILabel(row, nil, 9, colors.muted); row.detail:SetPoint("BOTTOMLEFT", 44, 2); row.detail:SetSize(246, 12)
        row:SetScript("OnEnter", function()
            if not row.item or not GameTooltip then return end
            GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
            if row.item.link then GameTooltip:SetHyperlink(row.item.link)
            else GameTooltip:AddLine(row.item.name, 1, 1, 1); GameTooltip:AddLine("Item " .. row.item.id .. " • Loading client tooltip…", .65, .67, .66) end
            GameTooltip:Show()
        end)
        row:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
        row:SetScript("OnClick", function()
            if row.item and row.item.link and type(HandleModifiedItemClick) == "function" then HandleModifiedItemClick(row.item.link) end
        end)
        frame.lootRows[slot] = row
    end
    frame.lootPages = paging(frame.lootPanel, function() frame.lootPage = frame.lootPage - 1; ns.RenderDungeonViewer() end,
        function() frame.lootPage = frame.lootPage + 1; ns.RenderDungeonViewer() end)
    frame.lootEmpty = ns.UILabel(frame.lootPanel, nil, 12, colors.muted); frame.lootEmpty:SetPoint("TOPLEFT", 16, -150); frame.lootEmpty:SetSize(280, 160)
    frame.footer = ns.UILabel(frame, nil, 10, colors.muted); frame.footer:SetPoint("BOTTOMLEFT", 20, 15); frame.footer:SetSize(760, 20)
    frame.footer:SetText("Forever database snapshot • Client tooltips show cached stats • No quest route is changed")
    frame.questList = ns.UIButton(frame, "Quest list", 96, function()
        for _, group in ipairs(ns.DungeonGroups()) do if group.key == selected then ns.ShowDungeonQuestList(group); return end end
    end); frame.questList:SetPoint("BOTTOMRIGHT", -20, 12)
    frame.mode = ns.UIButton(frame, "Map only", 108, function()
        if frame.compact then frame.compactSize = {frame:GetWidth(), frame:GetHeight()}
        else frame.fullSize = {frame:GetWidth(), frame:GetHeight()} end
        save(frame)
        keepPosition(frame)
        frame.compact = not frame.compact
        if type(frame.SetResizeBounds) == "function" then frame:SetResizeBounds(frame.compact and 380 or 940, frame.compact and 300 or 500, 1400, 1000) end
        local size = frame.compact and (frame.compactSize or {500, 420}) or (frame.fullSize or {1080, 650})
        frame:SetSize(unpack(size))
        local geometry = ns.db.dungeonViewerUI or {}
        local x, y = geometry[frame.compact and "compactLeft" or "fullLeft"], geometry[frame.compact and "compactTop" or "fullTop"]
        if coordinate(x) and coordinate(y) then frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", x, y) end
        layout(frame); save(frame)
    end); frame.mode:SetPoint("TOPRIGHT", -20, -47)
    frame.background = ns.UIButton(frame, "BG", 34, function()
        frame.transparent = not frame.transparent
        frame:SetBackdropColor(colors.background[1], colors.background[2], colors.background[3], frame.transparent and .08 or .98)
        frame.map:SetBackdropColor(colors.panel[1], colors.panel[2], colors.panel[3], frame.transparent and .08 or .98)
        save(frame)
    end); frame.background:SetPoint("TOPRIGHT", -136, -47)
    ns.UIHelp(frame.background, "Toggle the window background. Map, labels and markers stay visible.")
    frame:SetResizable(true)
    if type(frame.SetResizeBounds) == "function" then frame:SetResizeBounds(940, 500, 1400, 1000) end
    frame.grip = CreateFrame("Button", nil, frame); frame.grip:SetSize(16, 16); frame.grip:SetPoint("BOTTOMRIGHT", -2, 2)
    frame.grip.icon = frame.grip:CreateTexture(nil, "ARTWORK"); frame.grip.icon:SetAllPoints()
    frame.grip.icon:SetTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    frame.grip:SetScript("OnMouseDown", function(_, key) if key == "LeftButton" then frame:StartSizing("BOTTOMRIGHT") end end)
    frame.grip:SetScript("OnMouseUp", function() frame:StopMovingOrSizing(); layout(frame); save(frame) end)
    frame.transparent = state.transparent == true
    if frame.transparent then
        frame:SetBackdropColor(colors.background[1], colors.background[2], colors.background[3], .08)
        frame.map:SetBackdropColor(colors.panel[1], colors.panel[2], colors.panel[3], .08)
    end
    frame.layoutReady = true
    frame:SetScript("OnSizeChanged", function() layout(frame) end)
    layout(frame)
    frame.floor, frame.bossPage, frame.lootPage, frame.category, frame.query = 1, 1, 1, "all", ""
    frame:Hide()
    if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherDungeonViewer") end
    return frame
end
local function setPages(bar, page, pages)
    bar.prev:SetEnabled(page > 1); bar.next:SetEnabled(page < pages); bar.text:SetText(page .. " / " .. pages)
end
local function updateFloorMenu(frame)
    local control = frame.floorMenu
    for _, row in pairs(control.options) do row:Hide() end
    control.entries = {}
    for index, map in ipairs(frame.data.maps) do
        control.entries[index] = {index, map.name}
        local row = control.options[index]
        if not row then
            local floor = index
            row = ns.UIButton(control.menu, map.name, 262, function() control.menu:Hide(); frame.floor = floor; ns.RenderDungeonViewer() end)
            control.options[index] = row
        end
        row.caption:SetText(map.name); row:ClearAllPoints(); row:SetPoint("TOPLEFT", 4, -4 - (index - 1) * 28); row:SetHeight(26); row:Show()
    end
    control.menu:SetHeight(math.max(36, #control.entries * 28 + 8))
    control:SetEnabled(#control.entries > 0)
    if #control.entries == 0 then control.caption:SetText("No verified floor map") else control:SetChoice(frame.floor) end
end
local function drawMap(frame, map)
    for _, tile in ipairs(frame.tiles) do tile:Hide() end
    for _, pin in ipairs(frame.pins) do pin:Hide() end
    frame.empty:Hide()
    if not map then frame.empty:SetText("No verified interior map yet.\n\nYou can still browse published bosses and loot here."); frame.empty:Show(); return end
    local columns, rows = math.ceil(map.width / map.tileWidth), math.ceil(map.height / map.tileHeight)
    local scale = math.min(frame.map:GetWidth() / map.width, frame.map:GetHeight() / map.height)
    local ox, oy = (frame.map:GetWidth() - map.width * scale) / 2, (frame.map:GetHeight() - map.height * scale) / 2
    local loaded = true
    for index, asset in ipairs(map.tiles) do
        local tile = frame.tiles[index]
        if not tile then tile = frame.map:CreateTexture(nil, "ARTWORK"); frame.tiles[index] = tile end
        local column, row = (index - 1) % columns, math.floor((index - 1) / columns)
        local width, height = math.min(map.tileWidth, map.width - column * map.tileWidth), math.min(map.tileHeight, map.height - row * map.tileHeight)
        tile:ClearAllPoints(); tile:SetPoint("TOPLEFT", ox + column * map.tileWidth * scale, -oy - row * map.tileHeight * scale)
        tile:SetSize(width * scale, height * scale); tile:SetTexCoord(0, width / map.tileWidth, 0, height / map.tileHeight)
        if ns.ReadPublic(tile.SetTexture, tile, asset) == true then tile:Show() else loaded = false end
    end
    -- A partial map is misleading; fall back as a whole when any tile is missing.
    if not loaded then
        for _, tile in ipairs(frame.tiles) do tile:Hide() end
        frame.empty:SetText("This map's textures are unavailable on your build.\n\nBosses and loot remain available."); frame.empty:Show(); return
    end
    for index, position in ipairs(map.bosses or {}) do
        local pin = frame.pins[index]
        if not pin then
            pin = ns.UIButton(frame.map, "", 26, function() end, true); pin:SetHeight(26)
            pin:SetFrameLevel(frame.map:GetFrameLevel() + 10); frame.pins[index] = pin
            pin:SetScript("OnClick", function()
                if frame.compact then frame.mode:GetScript("OnClick")() end
                if pin.bossID then selectBoss(pin.bossID) end
            end)
        end
        pin.bossID = position.id
        local name
        for bossIndex, boss in ipairs(frame.data.bosses) do if boss.id == position.id then name = boss.name; pin.caption:SetText(bossIndex); break end end
        ns.UIHelp(pin, name or "Boss"); ns.UIButtonTone(pin, position.id == frame.bossID)
        pin:ClearAllPoints(); pin:SetPoint("CENTER", frame.map, "TOPLEFT", ox + position.x * map.width * scale, -oy - position.y * map.height * scale); pin:Show()
    end
end
function ns.RenderDungeonViewer()
    local frame = ns.dungeonViewer
    if not frame or not frame:IsShown() or not frame.data or frame.rendering then return end
    frame.rendering = true
    local data, boss = frame.data
    frame.title:SetText(data.name)
    frame.summary:SetText("Lv " .. data.definition.runLevelLow .. "–" .. data.definition.runLevelHigh .. " • " .. #data.bosses
        .. (frame.compact and " bosses" or " published encounters • Browse from anywhere"))
    frame.bossTitle:SetText("Bosses • " .. #data.bosses)
    local pages = math.max(1, math.ceil(#data.bosses / frame.bossRowsVisible))
    frame.bossPage = math.max(1, math.min(pages, frame.bossPage)); setPages(frame.bossPages, frame.bossPage, pages)
    for _, value in ipairs(data.bosses) do if value.id == frame.bossID then boss = value; break end end
    for slot, row in ipairs(frame.bossRows) do
        local value = slot <= frame.bossRowsVisible and data.bosses[(frame.bossPage - 1) * frame.bossRowsVisible + slot] or nil
        row.boss = value; row:SetShown(value ~= nil)
        if value then
            row.name:SetText(value.name); row.detail:SetText((value.rare and "Rare • " or "") .. (value.level and "Lv " .. value.level or ""))
            image(row.icon, value.portrait or bossFallback); ns.UIButtonTone(row, frame.bossID == value.id); ns.UIHelp(row, value.name .. "\nSelect to see published loot.")
        end
    end
    frame.floor = math.max(1, math.min(math.max(1, #data.maps), frame.floor)); updateFloorMenu(frame)
    local map = data.maps[frame.floor]; drawMap(frame, map)
    if frame.compact then frame.footer:SetText(map and (map.reference and "Classic layout reference" or "Client map • Full view opens boss loot") or "Map data unavailable") end
    frame.mapNote:SetText(map and (map.reference and "Classic client layout reference; Forever changes may differ.\n" or "Current client floor map.\n")
        .. (#(map.bosses or {}) > 0 and "Click a numbered boss to view loot." or "Boss positions are not exposed for this floor. Use the boss list; no locations are guessed.")
        or "Interior map data has not been published or exposed by this client.")
    frame.bossName:SetText(boss and boss.name or "Boss data not yet published")
    frame.bossDetail:SetText(boss and ((boss.rare and "Rare encounter • " or "") .. #boss.loot .. " notable drops • Database snapshot") or "No encounters are inferred from nearby trash NPCs.")
    image(frame.portrait, boss and boss.portrait or bossFallback)
    local loot = ns.DungeonViewerLoot(boss, frame.query, frame.category)
    frame.lootTitle:SetText("Boss loot • " .. #loot); frame.lootType:SetChoice(frame.category)
    pages = math.max(1, math.ceil(#loot / frame.lootRowsVisible)); frame.lootPage = math.max(1, math.min(pages, frame.lootPage)); setPages(frame.lootPages, frame.lootPage, pages)
    for slot, row in ipairs(frame.lootRows) do
        local value = slot <= frame.lootRowsVisible and loot[(frame.lootPage - 1) * frame.lootRowsVisible + slot] or nil
        row:SetShown(value ~= nil); row.item = nil
        if value then
            local item = ns.DungeonViewerItem(value); row.item = item
            image(row.icon, item.icon); row.name:SetText(item.name); row.name:SetTextColor(unpack(qualityColors[item.quality] or colors.text))
            row.detail:SetText((slots[item.slot] or (item.classID == 12 and "Quest item") or "Other loot") .. (item.requiredLevel and " • Requires " .. item.requiredLevel or ""))
            if not item.link and not frame.itemRequests[item.id] and C_Item and type(C_Item.RequestLoadItemDataByID) == "function" then
                frame.itemRequests[item.id] = true; C_Item.RequestLoadItemDataByID(item.id)
            end
        end
    end
    frame.lootEmpty:SetShown(#loot == 0)
    frame.lootEmpty:SetText(boss and (#boss.loot == 0 and "No notable drops published for this encounter yet." or "No items match this filter.") or "Boss and loot data are not available for this dungeon yet.")
    frame.rendering = nil
end
function ns.RefreshDungeonViewer(reload)
    local frame = ns.dungeonViewer
    if not frame or not frame:IsShown() or not selected then return end
    if reload then
        if ns.DiscoverDungeonArtwork then ns.DiscoverDungeonArtwork() end
        frame.data = ns.DungeonViewerData(selected)
    end
    ns.RenderDungeonViewer()
end
function ns.ShowDungeonViewer(group, mapOnly)
    local key = type(group) == "table" and group.key or group
    if type(key) ~= "string" or not ns.dungeonData or not ns.dungeonData.dungeons[key] then return end
    if ns.DiscoverDungeonArtwork then ns.DiscoverDungeonArtwork() end
    local frame = create()
    if (frame.compact == true) ~= (mapOnly == true) then frame.mode:GetScript("OnClick")() end
    if selected ~= key then
        frame.floor, frame.bossPage, frame.lootPage, frame.category, frame.query, frame.bossID = 1, 1, 1, "all", "", nil
        frame.floorMenu.menu:Hide(); frame.lootType.menu:Hide(); frame.search:SetText("")
    end
    selected, frame.data = key, ns.DungeonViewerData(key)
    if frame.data and not frame.bossID and frame.data.bosses[1] then frame.bossID = frame.data.bosses[1].id end
    frame:Show(); ns.RenderDungeonViewer()
end
function ns.CheckDungeonViewerEntry()
    if not ns.db then return end
    local key, instance = ns.DungeonEntryKey()
    if not key then entered = nil; if ns.dungeonEntryPrompt then ns.dungeonEntryPrompt:Hide() end; return end
    local entry = key .. ":" .. instance
    if entered == entry or not ns.Option("dungeonMapPrompt") or ns.RouteInCombat() then return end
    entered = entry
    if not ns.dungeonEntryPrompt then
        local frame = CreateFrame("Frame", "WowTogetherDungeonEntryPrompt", UIParent, "BackdropTemplate")
        ns.dungeonEntryPrompt = frame
        frame:SetSize(360, 150); frame:SetPoint("CENTER", 0, 170); frame:SetClampedToScreen(true); frame:SetFrameStrata("DIALOG"); ns.UIPanel(frame)
        frame.title = heading(frame, "Open map?", 18, 18, -16, 320)
        frame.text = ns.UILabel(frame, nil, 12, colors.muted); frame.text:SetPoint("TOPLEFT", 18, -48); frame.text:SetSize(324, 38)
        frame.open = ns.UIButton(frame, "Open map", 144, function() local dungeon = frame.key; frame:Hide(); ns.ShowDungeonViewer(dungeon, true) end, true); frame.open:SetPoint("BOTTOMLEFT", 18, 16)
        frame.later = ns.UIButton(frame, "Not now", 120, function() frame:Hide() end); frame.later:SetPoint("BOTTOMRIGHT", -18, 16)
    end
    local frame = ns.dungeonEntryPrompt
    frame.key = key; frame.text:SetText(ns.dungeonData.dungeons[key].name .. "\nBrowse the map, bosses and their loot."); frame:Show()
end
function ns.InitializeDungeonViewer()
    -- Chain existing handlers after all modules initialize; preserve the single
    -- dispatch frame and profession item-cache handler.
    local function listen(event, callback)
        local previous = ns.handlers[event]
        ns.On(event, function(...) if previous then previous(...) end; callback(...) end)
    end
    listen("ITEM_DATA_LOAD_RESULT", function(id)
        if ns.GuideInteger(id) and ns.dungeonViewer and ns.dungeonViewer.itemRequests[id] then ns.RefreshDungeonViewer() end
    end)
    listen("ZONE_CHANGED_NEW_AREA", ns.CheckDungeonViewerEntry)
    listen("PLAYER_ENTERING_WORLD", ns.CheckDungeonViewerEntry)
    listen("PLAYER_REGEN_ENABLED", ns.CheckDungeonViewerEntry)
    ns.CheckDungeonViewerEntry()
end
function ns.DungeonViewerDiagnostics(output)
    local counts = ns.dungeonJournalData and ns.dungeonJournalData.counts or {}
    output("Dungeon viewer: " .. (counts.bosses or 0) .. " encounters; " .. (counts.lootEntries or 0) .. " notable boss-drop entries; " .. (counts.mapReferences or 0) .. " client layout references. Native map/portrait availability needs beta testing.")
end
