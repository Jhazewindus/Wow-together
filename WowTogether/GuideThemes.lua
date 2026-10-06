local addonName, ns = ...

-- Original landscape motifs decorate guide cards only. These maps do not
-- describe quest geography, change guide eligibility or select route steps.
local root = "Interface\\AddOns\\" .. addonName .. "\\Media\\GuideThemes\\"
local zoneThemes = {
    [1411] = "canyon", [1412] = "prairie", [1413] = "savanna",
    [1416] = "snow", [1417] = "prairie", [1418] = "mountains", [1419] = "volcanic",
    [1420] = "haunted", [1421] = "haunted", [1422] = "blighted", [1423] = "blighted",
    [1424] = "farmland", [1425] = "woodland", [1426] = "snow", [1427] = "volcanic",
    [1428] = "volcanic", [1429] = "farmland", [1430] = "mountains", [1431] = "haunted",
    [1432] = "mountains", [1433] = "canyon", [1434] = "jungle", [1435] = "marsh",
    [1436] = "farmland", [1437] = "marsh", [1438] = "woodland", [1439] = "coast",
    [1440] = "woodland", [1441] = "canyon", [1442] = "mountains", [1443] = "mountains",
    [1444] = "jungle", [1445] = "marsh", [1446] = "desert", [1447] = "coast",
    [1448] = "blighted", [1449] = "jungle", [1450] = "woodland", [1451] = "desert",
    [1452] = "snow", [1453] = "settlement", [1454] = "settlement", [1455] = "settlement",
    [1456] = "prairie", [1457] = "woodland", [1458] = "ruins", [2548] = "marsh", [2652] = "woodland",
}
local names = {
    woodland = {"ashenvale", "teldrassil", "darnassus", "moonglade", "the-hinterlands", "shendralas", "ruttheran-village"},
    haunted = {"duskwood", "silverpine-forest", "tirisfal-glades"},
    prairie = {"mulgore", "thunder-bluff", "arathi-highlands", "thoradins-wall"},
    canyon = {"durotar", "thousand-needles", "redridge-mountains"},
    savanna = {"the-barrens", "field-of-giants"},
    desert = {"tanaris", "silithus", "abyssal-sands"},
    snow = {"winterspring", "dun-morogh", "alterac-mountains", "alterac-valley", "anvilmar", "kharanos"},
    mountains = {"stonetalon-mountains", "desolace", "badlands", "loch-modan", "stonewrought-dam", "deadwind-pass"},
    jungle = {"feralas", "stranglethorn-vale", "ungoro-crater"},
    marsh = {"wetlands", "dustwallow-marsh", "swamp-of-sorrows", "riverglades"},
    volcanic = {"burning-steppes", "searing-gorge", "blasted-lands", "blackrock-mountain"},
    blighted = {"felwood", "western-plaguelands", "eastern-plaguelands"},
    farmland = {"elwynn-forest", "hillsbrad-foothills", "westfall"},
    coast = {"darkshore", "azshara", "blackmaw-hold", "zephras-isle", "zephras-island"},
    settlement = {"orgrimmar", "stormwind-city", "ironforge", "deeprun-tram"},
    ruins = {"undercity", "ruins-of-lordaeron", "shadowfang-keep", "crafting"},
}
local aliases = {}
local function normalized(value)
    if not ns.Public(value) or type(value) ~= "string" then return end
    return string.lower(string.gsub(value, "[^%w]", ""))
end
for theme, values in pairs(names) do
    for _, name in ipairs(values) do aliases[normalized(name)] = theme end
end

function ns.GuideCardTheme(guide, dungeon)
    if ns.Public(dungeon) and type(dungeon) == "table" then return "ruins" end
    if not ns.Public(guide) or type(guide) ~= "table" then return end
    if ns.Public(guide.mode) and guide.mode == "dungeon" then return "ruins" end
    local mapID = guide.homeMapID
    if not ns.Public(mapID) or type(mapID) ~= "number" then mapID = guide.mapID end
    if ns.Public(mapID) and type(mapID) == "number" and zoneThemes[mapID] then return zoneThemes[mapID] end
    local key = guide.key
    local slug = ns.Public(key) and type(key) == "string" and string.match(key, "([^/:]+)$")
    return aliases[normalized(slug) or ""] or aliases[normalized(guide.zone) or ""] or "ruins"
end

function ns.LayoutGuideCardTheme(card)
    if card.dungeonArt and card.dungeonArt.shown then ns.LayoutDungeonCardArtwork(card); return end
    local art = card.zoneArt
    if not art or not art:IsShown() then return end
    local width, height = (card:GetWidth() or 0) - 2, (card:GetHeight() or 0) - 2
    if width <= 0 or height <= 0 or width == art.cardWidth and height == art.cardHeight then return end
    art.cardWidth, art.cardHeight = width, height
    -- 512 x 128 source panoramas: crop centrally, never stretch the scenery.
    local ratio = width / height
    if ratio >= 4 then
        local inset = (1 - 4 / ratio) / 2
        art:SetTexCoord(0, 1, inset, 1 - inset)
    else
        local inset = (1 - ratio / 4) / 2
        art:SetTexCoord(inset, 1 - inset, 0, 1)
    end
end

function ns.ApplyGuideCardTheme(card, guide, dungeon)
    local group = dungeon or (ns.Public(guide) and type(guide) == "table" and ns.Public(guide.mode)
        and guide.mode == "dungeon" and guide.dungeon)
    if ns.Public(group) and type(group) == "table" then
        if card.zoneArt then card.zoneArt:Hide() end
        ns.ApplyDungeonCardArtwork(card, group); return
    end
    ns.HideDungeonCardArtwork(card)
    local theme = ns.GuideCardTheme(guide, dungeon)
    if not theme then if card.zoneArt then card.zoneArt:Hide() end; return end
    if not card.zoneArt then
        local art = card:CreateTexture(nil, "ARTWORK", nil, -7)
        art:SetPoint("TOPLEFT", 1, -1); art:SetPoint("BOTTOMRIGHT", -1, 1)
        card.zoneArt = art
    end
    local art = card.zoneArt
    if art.theme ~= theme then art:SetTexture(root .. theme .. ".tga"); art.theme = theme end
    art:Show(); ns.LayoutGuideCardTheme(card)
end
