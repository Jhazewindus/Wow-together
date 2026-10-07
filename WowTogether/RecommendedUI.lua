local addonName, ns = ...

local function heading(parent, text, size, color)
    local font = ns.UILabel(parent, "GameFontNormalLarge", size or 16, color)
    font:SetText(text); font:SetWordWrap(false)
    return font
end

local function makeCard(parent, featured)
    local c = ns.UIColors
    local card = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    ns.UIPanel(card)
    card.category = ns.UILabel(card, nil, 9, c.gold)
    card.category:SetPoint("TOPLEFT", 16, -12); card.category:SetHeight(12); card.category:SetWordWrap(false)
    card.title = heading(card, "", featured and 21 or 17, c.text)
    card.title:SetPoint("TOPLEFT", featured and 16 or 72, -33); card.title:SetHeight(23)
    card.count = ns.UILabel(card, nil, 11, c.gold)
    card.count:SetPoint("TOPRIGHT", -16, -15); card.count:SetHeight(14); card.count:SetJustifyH("RIGHT"); card.count:SetWordWrap(false)
    card.detail = ns.UILabel(card, nil, 12, c.text)
    card.detail:SetPoint("TOPLEFT", 16, featured and -66 or -76)
    card.detail:SetHeight(featured and 34 or 35); card.detail:SetWordWrap(true); card.detail:SetJustifyV("TOP")
    card.progress = ns.UILabel(card, nil, 10, c.muted)
    card.progress:SetPoint("BOTTOMLEFT", 16, 47); card.progress:SetHeight(14); card.progress:SetWordWrap(false)
    card.track = card:CreateTexture(nil, "ARTWORK")
    card.track:SetColorTexture(0.30, 0.28, 0.23, 0.75); card.track:SetHeight(2)
    card.track:SetPoint("BOTTOMLEFT", 16, 42)
    card.fill = card:CreateTexture(nil, "OVERLAY")
    card.fill:SetColorTexture(unpack(c.gold)); card.fill:SetHeight(2); card.fill:SetPoint("LEFT", card.track, "LEFT", 0, 0)
    card.start = ns.UIButton(card, "Start guide", 126, function()
        if card.data and card.data.start then card.data.start() end
    end, true)
    card.start:SetPoint("BOTTOMLEFT", 16, 10)
    card.inspect = ns.UIButton(card, "Quest list", 112, function()
        if card.data and card.data.inspect then card.data.inspect() end
    end)
    card.inspect:SetPoint("BOTTOMRIGHT", -16, 10)
    if not featured then
        card.icon = card:CreateTexture(nil, "ARTWORK")
        card.icon:SetPoint("TOPLEFT", 16, -32); card.icon:SetSize(44, 44); card.icon:SetAlpha(1)
    end
    return card
end

local function updateCard(card, item)
    card.data = item
    card.category:SetText(item.category or "RECOMMENDED")
    card.title:SetText(item.title); card.count:SetText(item.count or "")
    card.detail:SetText(item.detail or ""); card.progress:SetText(item.progress or "")
    card.start.caption:SetText(item.action or "View guide"); card.start:SetEnabled(item.start ~= nil)
    card.inspect.caption:SetText(item.secondary or "View guide")
    card.inspect:SetShown(item.inspect ~= nil and item.secondary ~= item.action)
    if card.icon then card.icon:SetTexture(item.icon or "Interface\\Icons\\INV_Misc_Book_09") end
    local total, value = tonumber(item.progressTotal) or 0, tonumber(item.progressValue) or 0
    card.fraction = total > 0 and math.max(0, math.min(1, value / total)) or 0
    ns.ApplyGuideCardTheme(card, item.guide)
    card:Show()
end

local function createHome()
    local home = CreateFrame("Frame", nil, ns.ui.content)
    home:SetPoint("TOPLEFT", 0, 0)
    home.title = heading(home, "Recommended for you", 19, ns.UIColors.text)
    home.title:SetPoint("TOPLEFT", 0, -2)
    home.browseLeveling = ns.UIButton(home, "Browse leveling", 136, function() ns.SetFilter("guides") end)
    home.browseLeveling:SetPoint("TOPRIGHT", 0, 0)
    home.resume = CreateFrame("Frame", nil, home, "BackdropTemplate")
    ns.UIPanel(home.resume, ns.UIColors.background)
    home.resume.category = ns.UILabel(home.resume, nil, 9, ns.UIColors.muted)
    home.resume.category:SetPoint("TOPLEFT", 14, -8); home.resume.category:SetText("CONTINUE YOUR GUIDE")
    home.resume.title = heading(home.resume, "", 13)
    home.resume.title:SetPoint("TOPLEFT", 14, -23); home.resume.title:SetHeight(18)
    home.resume.button = ns.UIButton(home.resume, "Continue", 112, ns.OpenGuideWindow, true)
    home.resume.button:SetPoint("RIGHT", -14, 0)
    home.leveling = makeCard(home, true)
    home.professionTitle = heading(home, "Your professions", 16, ns.UIColors.text)
    home.browseProfessions = ns.UIButton(home, "Browse professions", 150, function() ns.SetFilter("professions") end)
    home.professionEmpty = CreateFrame("Frame", nil, home, "BackdropTemplate")
    ns.UIPanel(home.professionEmpty)
    home.professionEmpty.text = ns.UILabel(home.professionEmpty, nil, 12, ns.UIColors.muted)
    home.professionEmpty.text:SetPoint("TOPLEFT", 16, -16); home.professionEmpty.text:SetHeight(32)
    home.professionEmpty.text:SetWordWrap(true); home.professionEmpty.text:SetJustifyV("TOP")
    home.moreTitle = heading(home, "More ways to progress", 16, ns.UIColors.text)
    home.cards, home.extraCards = {}, {}
    ns.ui.home = home
    return home
end

local function layoutCard(card, width, height)
    card:SetSize(width, height)
    card.category:SetWidth(width - 145)
    card.title:SetWidth(width - (card.icon and 88 or 32))
    card.count:SetWidth(120)
    card.detail:SetWidth(width - 32); card.progress:SetWidth(width - 32)
    card.track:SetWidth(width - 32)
    card.fill:SetWidth(math.max(1, (width - 32) * (card.fraction or 0)))
    card.fill:SetShown((card.fraction or 0) > 0)
    ns.LayoutGuideCardTheme(card)
end

-- Resizing uses existing card data; it must not read quests, skill or recipes.
function ns.LayoutRecommended()
    local home = ns.ui.home
    if not home then return end
    local width, top, gap = ns.ui.contentWidth, 32, 12
    home:SetWidth(width); home.title:SetWidth(width - 160)
    if home.resume:IsShown() then
        home.resume:ClearAllPoints(); home.resume:SetPoint("TOPLEFT", 0, -top); home.resume:SetSize(width, 52)
        home.resume.title:SetWidth(width - 168); top = top + 64
    end
    home.leveling:ClearAllPoints(); home.leveling:SetPoint("TOPLEFT", 0, -top)
    layoutCard(home.leveling, width, 164); top = top + 176
    home.professionTitle:ClearAllPoints(); home.professionTitle:SetPoint("TOPLEFT", 0, -top - 4)
    home.professionTitle:SetWidth(width - 166)
    home.browseProfessions:ClearAllPoints(); home.browseProfessions:SetPoint("TOPRIGHT", 0, -top)
    top = top + 32
    local columns = width >= 640 and 2 or 1
    local tileWidth = (width - (columns - 1) * gap) / columns
    local function grid(cards, count)
        for i = 1, count do
            local row, col = math.floor((i - 1) / columns), (i - 1) % columns
            local card = cards[i]
            card:ClearAllPoints(); card:SetPoint("TOPLEFT", col * (tileWidth + gap), -top - row * 188)
            layoutCard(card, tileWidth, 176)
        end
        top = top + math.ceil(count / columns) * 188
    end
    if home.professionCount == 0 then
        home.professionEmpty:ClearAllPoints(); home.professionEmpty:SetPoint("TOPLEFT", 0, -top)
        home.professionEmpty:SetSize(width, 68); home.professionEmpty.text:SetWidth(width - 32); top = top + 80
    else grid(home.cards, home.professionCount) end
    if home.extraCount > 0 then
        home.moreTitle:ClearAllPoints(); home.moreTitle:SetPoint("TOPLEFT", 0, -top - 4)
        home.moreTitle:SetWidth(width); top = top + 38
        grid(home.extraCards, home.extraCount)
    end
    home:SetHeight(top); ns.ui.content:SetHeight(math.max(250, top))
end

function ns.RenderRecommended(query)
    local home = ns.ui.home or createHome()
    local items, states = ns.RecommendedItems(query)
    home.professionCount, home.extraCount = 0, 0
    for _, card in ipairs(home.cards) do card:Hide() end
    for _, card in ipairs(home.extraCards) do card:Hide() end
    local featured
    for _, item in ipairs(items) do
        if item.kind == "leveling" and not featured then featured = item
        else
            local profession = item.kind == "professions"
            local countKey, pool = profession and "professionCount" or "extraCount", profession and home.cards or home.extraCards
            home[countKey] = home[countKey] + 1
            local index = home[countKey]
            pool[index] = pool[index] or makeCard(home, false)
            updateCard(pool[index], item)
        end
    end
    updateCard(home.leveling, featured or {title = "Your next zone", category = "LEVELING",
        detail = states.leveling or "Browse leveling guides to find your next zone.", action = "Browse guides",
        start = function() ns.SetFilter("guides") end})
    home.professionEmpty:SetShown(home.professionCount == 0)
    home.professionEmpty.text:SetText(states.professions or "Browse professions to find a crafting guide.")
    home.moreTitle:SetShown(home.extraCount > 0)
    local running = ns.routeSelection and ns.selectedRoute and not ns.selectedRoute.complete
    home.resume:SetShown(running == true)
    home.resume.title:SetText(running and ns.routeSelection.title or "")
    ns.ui.metrics[2].caption:SetText("RECOMMENDATIONS"); ns.ui.metrics[2].value:SetText(tostring(#items))
    home:Show(); ns.LayoutRecommended()
end
