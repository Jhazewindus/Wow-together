local addonName, ns = ...

-- Blizzard artwork stays in the client. Only verified filenames are bundled;
-- DUNGEON_ARTWORK.md records their source and the beta checks still needed.
local root = "Interface\\EncounterJournal\\UI-EJ-DungeonButton-"
local icons = "Interface\\LFGFrame\\LFGICON-"
local classic = {
    ["blackfathom-deeps"] = {"BlackfathomDeeps", "BLACKFATHOMDEEPS"},
    ["blackrock-depths"] = {"BlackrockDepths", "BLACKROCKDEPTHS"},
    ["blackrock-spire"] = {"BlackrockSpire", "BLACKROCKSPIRE"},
    ["dire-maul"] = {"DireMaul", "DIREMAUL"}, ["gnomeregan"] = {"Gnomeregan", "GNOMEREGAN"},
    ["maraudon"] = {"Maraudon", "MARAUDON"}, ["ragefire-chasm"] = {"RagefireChasm", "RAGEFIRECHASM"},
    ["razorfen-downs"] = {"RazorfenDowns", "RAZORFENDOWNS"},
    ["razorfen-kraul"] = {"RazorfenKraul", "RAZORFENKRAUL"},
    ["scarlet-monastery"] = {"ScarletMonastery", "SCARLETMONASTERY"},
    ["scholomance"] = {"Scholomance", "SCHOLOMANCE"},
    ["shadowfang-keep"] = {"ShadowfangKeep", "SHADOWFANGKEEP"},
    ["stratholme"] = {"Stratholme", "STRATHOLME"}, ["the-deadmines"] = {"Deadmines", "DEADMINES"},
    ["the-stockade"] = {"TheStockade", "STORMWINDSTOCKADES"},
    ["the-temple-of-atalhakkar"] = {"SunkenTemple", "SUNKENTEMPLE"},
    ["uldaman"] = {"Uldaman", "ULDAMAN"}, ["wailing-caverns"] = {"WailingCaverns", "WAILINGCAVERNS"},
    ["zulfarrak"] = {"ZulFarrak", "ZULFARAK"},
}
local forever = { ["city-of-dalaran"] = "Dalaran", ["excavation-site-wetlands"] = "Excavation",
    ["the-hall-of-thanes"] = "OldIronforge", ["ruins-of-lordaeron"] = "RuinsofLordaeron" }
local loading = "Interface\\Glues\\LOADINGSCREENS\\Camelot160\\Main\\LoadScreen_Camelot_"
local neutral = "Interface\\LFGFrame\\UI-LFG-BACKGROUND-DUNGEONWALL"
local journal, journalIDs, checked, revision, reading, scanned = {}, {}, {}, 0, false, false
local buttonBounds = {6 / 256, 168 / 256, 6 / 128, 90 / 128}
local function normalized(value)
    value = ns.SafeTitle(value)
    return value and string.lower(string.gsub(value, "[^%w]", ""))
end
local function texture(value)
    if ns.GuideInteger(value, 1000000000) and value > 0 then return value end
    value = ns.SafeTitle(value)
    if value and string.match(string.lower(value), "^interface[\\/]")
        and not string.match(string.lower(value), "^interface[\\/]addons[\\/]") then return value end
end
local function imageInfo(asset, source, fallback)
    local path = type(asset) == "string" and asset
        or C_Texture and ns.ReadPublic(C_Texture.GetFilenameFromFileDataID, asset)
    local button = path and ns.Public(path) and type(path) == "string"
        and string.find(string.lower(path), "ui%-ej%-dungeonbutton%-")
    return {asset = asset, bounds = button and buttonBounds or nil, source = source, fallback = fallback}
end
local function repaint()
    for _, card in ipairs(ns.ui and ns.ui.cards or {}) do
        if card:IsShown() and card.activity and card.activity.dungeon then
            ns.ApplyDungeonCardArtwork(card, card.activity.dungeon)
        end
    end
end
local function discover()
    if scanned or reading or ns.RouteInCombat() or type(EJ_GetInstanceByIndex) ~= "function" then return end
    reading = true
    local names, index, generation = {}, 1, revision
    for key, info in pairs(ns.dungeonData and ns.dungeonData.dungeons or {}) do
        local name = normalized(info.name); if name then names[name] = key end
        for _, alias in ipairs(info.aliases or {}) do
            local aliasName = normalized(alias); if aliasName then names[aliasName] = key end
        end
    end
    local function finish()
        reading, scanned, revision = false, true, revision + 1
        repaint()
        if ns.RefreshDungeonViewer then ns.RefreshDungeonViewer(true) end
    end
    local function batch()
        if generation ~= revision then return end
        if ns.RouteInCombat() then reading = false; return end
        for _ = 1, 16 do
            local ok, id, name, _, _, button = pcall(EJ_GetInstanceByIndex, index, false)
            if not ok or not ns.GuideInteger(id) or id <= 0 then
                finish(); return
            end
            local key = names[normalized(name) or ""]
            if key then
                journalIDs[key] = id
                local _, _, background = ns.ReadPublic(EJ_GetInstanceInfo, id)
                local images = {}
                local backgroundAsset, buttonAsset = texture(background), texture(button)
                if backgroundAsset then images[#images + 1] = imageInfo(backgroundAsset, "Client dungeon journal") end
                if buttonAsset then images[#images + 1] = imageInfo(buttonAsset, "Client dungeon journal") end
                if #images > 0 then journal[key] = images; checked[key] = nil end
            end
            index = index + 1
            if index > 128 then finish(); return end
        end
        if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, batch)
        else finish() end
    end
    batch()
end

function ns.HideDungeonCardArtwork(card)
    local art = card.dungeonArt
    if not art then return end
    art.shown = false
    art.texture:Hide()
end

function ns.LayoutDungeonCardArtwork(card)
    local art = card.dungeonArt
    if not art or not art.shown then return end
    local width, height = (card:GetWidth() or 0) - 2, (card:GetHeight() or 0) - 2
    if width <= 0 or height <= 0 or width == art.width and height == art.height then return end
    art.width, art.height = width, height
    local bounds = art.bounds or {0, 1, 0, 1}
    -- Fill the entire card with one faint image. Crop source button padding,
    -- then stretch the illustration to the card, as requested.
    art.texture:ClearAllPoints(); art.texture:SetPoint("TOPLEFT", 1, -1)
    art.texture:SetSize(width, height); art.texture:SetTexCoord(unpack(bounds))
    art.texture:SetAlpha(0.14)
end

function ns.ApplyDungeonCardArtwork(card, group)
    if not ns.Public(group) or type(group) ~= "table" or not ns.SafeTitle(group.key) then
        ns.HideDungeonCardArtwork(card); return
    end
    discover()
    if not card.dungeonArt then
        card.dungeonArt = {texture = card:CreateTexture(nil, "ARTWORK", nil, -7)}
    end
    local art, key = card.dungeonArt, group.key
    if art.key == key and art.revision == revision and art.shown then
        ns.LayoutDungeonCardArtwork(card); return
    end
    local candidates = {}
    for _, info in ipairs(journal[key] or {}) do candidates[#candidates + 1] = info end
    if classic[key] then
        candidates[#candidates + 1] = imageInfo(root .. classic[key][1], "Client dungeon illustration")
        candidates[#candidates + 1] = imageInfo(icons .. classic[key][2], "Client dungeon illustration")
    elseif forever[key] then
        candidates[#candidates + 1] = imageInfo(loading .. forever[key], "Client Forever loading artwork")
    end
    candidates[#candidates + 1] = imageInfo(neutral, "Neutral client background", true)
    local selected = checked[key]
    if selected == nil then
        for _, candidate in ipairs(candidates) do
            if ns.ReadPublic(art.texture.SetTexture, art.texture, candidate.asset) == true then selected = candidate; break end
        end
        checked[key] = selected or false
    end
    art.key, art.revision, art.asset, art.source = key, revision, selected and selected.asset, selected and selected.source
    if not selected then ns.HideDungeonCardArtwork(card); return end
    if ns.ReadPublic(art.texture.SetTexture, art.texture, selected.asset) ~= true then ns.HideDungeonCardArtwork(card); return end
    art.texture:Show()
    art.bounds, art.width, art.height, art.shown = selected.bounds, nil, nil, true
    ns.LayoutDungeonCardArtwork(card)
end

function ns.RefreshDungeonArtwork()
    journal, journalIDs, checked, reading, scanned, revision = {}, {}, {}, false, false, revision + 1
    repaint()
    if ns.RefreshDungeonViewer then ns.RefreshDungeonViewer(true) end
end

function ns.DungeonJournalInstance(key) return journalIDs[key] end
ns.DiscoverDungeonArtwork = discover

function ns.DungeonArtworkDiagnostics(output)
    local specific, fallback = 0, 0
    for _, info in pairs(checked) do
        if info then if info.fallback then fallback = fallback + 1 else specific = specific + 1 end end
    end
    output("Dungeon artwork: 23 published client references; " .. specific .. " specific images resolved, "
        .. fallback .. " neutral backgrounds used this session. " .. (reading and "Reading journal." or "Client textures only."))
end
