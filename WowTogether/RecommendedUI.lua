local addonName, ns = ...

local function heading(parent, text, size, color)
    local font = ns.UILabel(parent, "GameFontNormalLarge", size or 16, color)
    font:SetText(text); font:SetWordWrap(false)
    return font
end

local function makeCard(parent, featured)
    local c = ns.UIColors
    local card = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    card.featured = featured == true
    ns.UIPanel(card)
    card:EnableMouse(true)
    card:SetScript("OnMouseUp", function(self, mouseButton)
        if mouseButton ~= "LeftButton" or not self.data then return end
        if self.data.inspect then self.data.inspect()
        elseif self.data.start then self.data.start() end
    end)
    card:SetScript("OnEnter", function(self)
        if self.data and (self.data.inspect or self.data.start) then self:SetBackdropBorderColor(unpack(c.gold)) end
    end)
    card:SetScript("OnLeave", function(self) self:SetBackdropBorderColor(unpack(c.border)) end)
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
    card.progress:SetPoint("BOTTOMLEFT", 16, 23); card.progress:SetHeight(14); card.progress:SetWordWrap(false)
    card.track = card:CreateTexture(nil, "ARTWORK")
    card.track:SetColorTexture(0.30, 0.28, 0.23, 0.75); card.track:SetHeight(2)
    card.track:SetPoint("BOTTOMLEFT", 16, 17)
    card.fill = card:CreateTexture(nil, "OVERLAY")
    card.fill:SetColorTexture(unpack(c.gold)); card.fill:SetHeight(2); card.fill:SetPoint("LEFT", card.track, "LEFT", 0, 0)
    card.follow = ns.UIButton(card, "Follow", 82, function()
        local item = card.data
        if not item then return end
        if item.start then item.start() elseif item.inspect then item.inspect() end
    end, true)
    card.follow:SetPoint("BOTTOMRIGHT", -12, 8)
    card.follow:Show()
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
    if card.icon then
        card.icon:SetTexture(item.icon or "Interface\\Icons\\INV_Misc_Book_09")
        card.icon:SetVertexColor(1, 1, 1, 1)
    end
    local total, value = tonumber(item.progressTotal) or 0, tonumber(item.progressValue) or 0
    card.fraction = total > 0 and math.max(0, math.min(1, value / total)) or 0
    ns.ApplyGuideCardTheme(card, item.guide)
    card:Show()
end

local function sessionSummaryCopy()
    local source = ns.GuideSessionSummary and ns.GuideSessionSummary()
    if type(source) ~= "table" or not ns.Public(source.title) or type(source.title) ~= "string"
        or #source.title > 120 or not ns.GuideInteger(source.quests, 4096)
        or not ns.GuideInteger(source.xp, 10000000000)
        or not ns.Public(source.seconds) or type(source.seconds) ~= "number"
        or source.seconds ~= source.seconds or source.seconds < 0 or source.seconds > 100000000 then return end
    return {title = source.title, quests = source.quests, xp = source.xp, seconds = source.seconds,
        xpKnown = source.xpKnown == true, xpPartial = source.xpPartial == true,
        timePartial = source.timePartial == true,
        startLevel = ns.GuideInteger(source.startLevel, 60) and source.startLevel or nil,
        endLevel = ns.GuideInteger(source.endLevel, 60) and source.endLevel or nil}
end

local function renderGoldSessionCard(home)
    local summary = sessionSummaryCopy()
    if not summary then home.goldSession:Hide(); return end
    local handled, spec = ns.FirstHook("goldSessionCard", summary)
    if not handled or type(spec) ~= "table" then home.goldSession:Hide(); return end
    updateCard(home.goldSession, {kind = "gold", category = "GOLD SESSION",
        title = spec.title, detail = spec.detail, action = "Open", start = spec.action})
end

local function createHome()
    local home = CreateFrame("Frame", nil, ns.ui.content)
    home:SetPoint("TOPLEFT", 0, 0)
    home.title = heading(home, "Next for you", 19, ns.UIColors.text)
    home.title:SetPoint("TOPLEFT", 0, -2)
    home.nextHeading = heading(home, "NEXT FOR YOU", 12, ns.UIColors.muted)
    home.nextRows = {}
    home.browseLeveling = ns.UIButton(home, "Browse all leveling guides", 208, function() ns.SetFilter("guides") end)
    home.browseLeveling:SetPoint("TOPRIGHT", 0, 0)
    home.resume = CreateFrame("Frame", nil, home, "BackdropTemplate")
    ns.UIPanel(home.resume, ns.UIColors.background)
    home.resume:EnableMouse(true)
    home.resume:SetScript("OnMouseUp", function(self, mouseButton)
        if mouseButton ~= "LeftButton" then return end
        if ns.PausedSessionCheckpoint() then ns.ResumeGuideSession()
        elseif ns.routeSelection then ns.OpenGuideWindow()
        else ns.SetFilter("guides") end
    end)
    home.resume:SetScript("OnEnter", function(self) self:SetBackdropBorderColor(unpack(ns.UIColors.gold)) end)
    home.resume:SetScript("OnLeave", function(self) self:SetBackdropBorderColor(unpack(ns.UIColors.border)) end)
    home.resume.category = ns.UILabel(home.resume, nil, 9, ns.UIColors.muted)
    home.resume.category:SetPoint("TOPLEFT", 14, -8); home.resume.category:SetText("CONTINUE YOUR GUIDE")
    home.resume.title = heading(home.resume, "", 13)
    home.resume.title:SetPoint("TOPLEFT", 14, -23); home.resume.title:SetHeight(18)
    home.resume.detail = ns.UILabel(home.resume, nil, 10, ns.UIColors.muted)
    home.resume.detail:SetPoint("TOPLEFT", 14, -46); home.resume.detail:SetHeight(28); home.resume.detail:SetWordWrap(true)
    home.resume.track = home.resume:CreateTexture(nil, "ARTWORK")
    home.resume.track:SetColorTexture(0.30, 0.28, 0.23, 0.75); home.resume.track:SetHeight(3)
    home.resume.track:SetPoint("BOTTOMLEFT", 14, 40)
    home.resume.fill = home.resume:CreateTexture(nil, "OVERLAY")
    home.resume.fill:SetColorTexture(unpack(ns.UIColors.gold)); home.resume.fill:SetHeight(3)
    home.resume.fill:SetPoint("LEFT", home.resume.track, "LEFT", 0, 0); home.resume.fill:SetWidth(1); home.resume.fill:Hide()
    home.resume.continueControl = ns.UIButton(home.resume, "Continue", 88, function()
        if ns.PausedSessionCheckpoint() then ns.ResumeGuideSession()
        elseif ns.routeSelection then ns.OpenGuideWindow()
        else ns.SetFilter("guides") end
    end, true)
    home.resume.continueControl:SetPoint("RIGHT", -12, 0)
    home.resume.continueControl:Show()
    home.resume.orderControl = ns.UIButton(home.resume, "Change order…", 116, function()
        if ns.routeSelection then ns.ShowGuideQuestList(ns.routeSelection) end
    end)
    home.resume.orderControl:SetPoint("RIGHT", home.resume.continueControl, "LEFT", -8, 0)
    home.resume.orderControl:Hide()
    home.resume.stopControl = ns.UIButton(home.resume, "Stop this guide", 120, function()
        if ns.routeSelection then ns.StopGuide(false) end
    end)
    home.resume.stopControl:SetPoint("RIGHT", home.resume.orderControl, "LEFT", -8, 0)
    home.resume.stopControl:Hide()
    home.goldSession = makeCard(home, false)
    home.goldSession:Hide()
    home.leveling = makeCard(home, true)
    home.professionTitle = heading(home, "Your professions", 16, ns.UIColors.text)
    home.browseProfessions = ns.UIButton(home, "Browse all professions", 180, function() ns.SetFilter("professions") end)
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

local function createNextRow(home)
    local row = CreateFrame("Frame", nil, home, "BackdropTemplate")
    ns.UIPanel(row, ns.UIColors.background)
    row.icon = row:CreateTexture(nil, "ARTWORK"); row.icon:SetPoint("LEFT", 12, 0); row.icon:SetSize(24, 24)
    row.glyph = ns.UILabel(row, "GameFontNormalLarge", 18, ns.UIColors.gold)
    row.glyph:SetPoint("LEFT", 12, 0); row.glyph:SetSize(24, 24); row.glyph:SetJustifyH("CENTER")
    row.title = ns.UILabel(row, "GameFontNormal", 13, ns.UIColors.text)
    row.title:SetPoint("TOPLEFT", 48, -8); row.title:SetHeight(17); row.title:SetWordWrap(false)
    row.detail = ns.UILabel(row, nil, 11, ns.UIColors.muted)
    row.detail:SetPoint("TOPLEFT", 48, -27); row.detail:SetHeight(15); row.detail:SetWordWrap(false)
    row.action = ns.UIButton(row, "Follow", 78, function()
        local item = row.data
        if not item then return end
        if item.start then item.start() elseif item.inspect then item.inspect() end
    end, true)
    row.action:SetPoint("RIGHT", -10, 0); row.action:SetHeight(28)
    return row
end

local nextGlyph = {leveling = "!", classquests = "!", dungeon = "D", dungeons = "D",
    professions = "⚒", travel = "→", gold = "◉"}

local function activeGuideHeading(guide)
    local area = guide and (guide.zone or guide.zoneName)
    if type(area) ~= "string" or area == "" then area = ns.profile and ns.profile.zone end
    local faction = ns.profile and ns.profile.faction
    if type(area) == "string" and area ~= "" and type(faction) == "string" and faction ~= "" then
        return faction .. " / " .. area .. (guide and guide.title and guide.title ~= area and (" · " .. guide.title) or "")
    end
    return guide and guide.title or "Current guide"
end

local function activeGuideDetail(guide, route)
    local fields, step = {}, route and (route.pendingStop or route.stops and route.stops[1])
    local number = step and tonumber(step.guideStep) or tonumber(route and route.currentStep)
    local total = tonumber(route and route.totalSteps)
    if not total or total <= 0 then total = tonumber(guide and guide.totalSteps) end
    if not total or total <= 0 then total = tonumber(guide and guide.enabledCount) end
    if not total or total <= 0 then total = tonumber(guide and guide.classQuestStepCount) end
    if (not total or total <= 0) and guide and type(guide.records) == "table" then total = #guide.records end
    if not number and total and total > 0 and route and tonumber(route.remainingSteps) then
        number = math.max(1, math.min(total, total - route.remainingSteps + 1))
    end
    if number and total and total > 0 then fields[#fields + 1] = "step " .. number .. " of " .. total end
    if #fields == 0 and total and total > 0 then fields[#fields + 1] = total .. " quest" .. (total == 1 and "" or "s") .. " in this guide" end
    local exit = tonumber(guide and (guide.mainLevelHigh or guide.rangeHigh or guide.maxLevel))
    local level = tonumber(ns.profile and ns.profile.level)
    if exit then
        if level then fields[#fields + 1] = math.max(0, exit - level) .. " levels left" end
        fields[#fields + 1] = "exit at " .. exit
    end
    if #fields == 0 then fields[1] = "Open the guide window to see the current step." end
    return table.concat(fields, " · "), number, total
end
ns.HubActiveGuideProgress = activeGuideDetail
ns.HubActiveGuideHeading = activeGuideHeading

local function layoutNext(home)
    local width, top = ns.ui.contentWidth, 8
    home:SetWidth(width); home.title:Hide()
    if home.resume:IsShown() then
        home.resume:ClearAllPoints(); home.resume:SetPoint("TOPLEFT", 0, -top); home.resume:SetSize(width, 104)
        home.resume.category:Hide()
        home.resume.title:ClearAllPoints(); home.resume.title:SetPoint("TOPLEFT", 14, -10)
        home.resume.detail:ClearAllPoints(); home.resume.detail:SetPoint("TOPLEFT", 14, -31)
        home.resume.detail:SetWidth(width - 28); home.resume.detail:SetHeight(16); home.resume.detail:SetWordWrap(false)
        home.resume.track:ClearAllPoints(); home.resume.track:SetPoint("TOPLEFT", 14, -54); home.resume.track:SetWidth(width - 28)
        home.resume.fill:SetWidth(math.max(1, (width - 28) * (home.resume.fraction or 0)))
        home.resume.fill:SetShown((home.resume.fraction or 0) > 0)
        home.resume.continueControl:ClearAllPoints(); home.resume.continueControl:SetPoint("BOTTOMLEFT", 12, 7); home.resume.continueControl:SetSize(94, 28)
        home.resume.orderControl:ClearAllPoints(); home.resume.orderControl:SetPoint("LEFT", home.resume.continueControl, "RIGHT", 8, 0); home.resume.orderControl:SetSize(122, 28)
        home.resume.stopControl:ClearAllPoints(); home.resume.stopControl:SetPoint("LEFT", home.resume.orderControl, "RIGHT", 8, 0); home.resume.stopControl:SetSize(126, 28)
        top = top + 116
    end
    home.nextHeading:ClearAllPoints(); home.nextHeading:SetPoint("TOPLEFT", 0, -top); home.nextHeading:SetWidth(width)
    top = top + 28
    for index = 1, home.nextCount or 0 do
        local row = home.nextRows[index]
        row:ClearAllPoints(); row:SetPoint("TOPLEFT", 0, -top); row:SetSize(width, 50)
        row.title:SetWidth(math.max(100, width - 170)); row.detail:SetWidth(math.max(100, width - 170))
        top = top + 58
    end
    home:SetHeight(top); ns.ui.content:SetHeight(math.max(250, top))
end

local function renderNext(home, query)
    local items = ns.RecommendedItems(query)
    home.professionCount, home.extraCount, home.nextCount = 0, 0, 0
    for _, card in ipairs(home.cards) do card:Hide() end
    for _, card in ipairs(home.extraCards) do card:Hide() end
    home.leveling:Hide(); home.goldSession:Hide(); home.professionEmpty:Hide()
    home.professionTitle:Hide(); home.browseLeveling:Hide(); home.browseProfessions:Hide(); home.moreTitle:Hide()
    ns.UpdateSessionResumeBar()
    local running = ns.routeSelection ~= nil and ns.selectedRoute ~= nil and ns.selectedRoute.complete ~= true
    home.resume.continueControl:SetShown(home.resume:IsShown())
    home.resume.orderControl:SetShown(running)
    home.resume.stopControl:SetShown(running)
    for _, item in ipairs(items) do
        if home.nextCount >= 5 then break end
        if type(item) == "table" and type(item.title) == "string" and item.title ~= ""
            and (type(item.start) == "function" or type(item.inspect) == "function") then
            home.nextCount = home.nextCount + 1
            local index = home.nextCount
            home.nextRows[index] = home.nextRows[index] or createNextRow(home)
            local row = home.nextRows[index]
            row.data = item; row.title:SetText(item.title); row.detail:SetText(type(item.detail) == "string" and item.detail or "")
            local kind = item.kind == "dungeons" and "dungeon" or item.kind
            local texture = item.icon or (type(ns.StepIconTexture) == "function" and ns.StepIconTexture(kind))
            row.icon:SetTexture(type(texture) == "string" and texture or nil)
            row.icon:SetShown(type(texture) == "string")
            row.glyph:SetText(type(texture) == "string" and "" or nextGlyph[kind] or "•")
            row.glyph:SetShown(type(texture) ~= "string")
            local action = string.find(string.lower(item.action or ""), "view", 1, true) and "Open" or "Follow"
            row.action.caption:SetText(action); row:Show()
        end
    end
    for index = (home.nextCount or 0) + 1, #home.nextRows do home.nextRows[index]:Hide() end
    home:Show(); layoutNext(home)
end

local function layoutCard(card, width, height)
    card:SetSize(width, height)
    card.category:SetWidth(width - 145)
    card.title:SetWidth(width - (card.icon and 88 or 32))
    card.count:SetWidth(120)
    card.detail:SetWidth(width - (card.featured and 126 or 122)); card.progress:SetWidth(width - 122)
    card.track:SetWidth(width - 122)
    card.fill:SetWidth(math.max(1, (width - 122) * (card.fraction or 0)))
    card.fill:SetShown((card.fraction or 0) > 0)
    ns.LayoutGuideCardTheme(card)
end

-- Resizing uses existing card data; it must not read quests, skill or recipes.
function ns.LayoutRecommended()
    local home = ns.ui.home
    if not home then return end
    if ns.Option("uiNext") then layoutNext(home); return end
    local width, top, gap = ns.ui.contentWidth, 32, 12
    home:SetWidth(width); home.title:SetWidth(width - 226)
    if home.resume:IsShown() then
        home.resume:ClearAllPoints(); home.resume:SetPoint("TOPLEFT", 0, -top); home.resume:SetSize(width, 82)
        home.resume.title:SetWidth(width - 470); home.resume.detail:SetWidth(width - 470)
        home.resume.continueControl:ClearAllPoints(); home.resume.continueControl:SetPoint("RIGHT", -12, 0); home.resume.continueControl:SetSize(88, 28)
        home.resume.orderControl:ClearAllPoints(); home.resume.orderControl:SetPoint("RIGHT", home.resume.continueControl, "LEFT", -8, 0); home.resume.orderControl:SetSize(116, 28)
        home.resume.stopControl:ClearAllPoints(); home.resume.stopControl:SetPoint("RIGHT", home.resume.orderControl, "LEFT", -8, 0); home.resume.stopControl:SetSize(120, 28)
        top = top + 94
    end
    if home.goldSession:IsShown() then
        home.goldSession:ClearAllPoints(); home.goldSession:SetPoint("TOPLEFT", 0, -top)
        layoutCard(home.goldSession, width, 112); top = top + 124
    end
    home.leveling:ClearAllPoints(); home.leveling:SetPoint("TOPLEFT", 0, -top)
    layoutCard(home.leveling, width, 164); top = top + 176
    home.professionTitle:ClearAllPoints(); home.professionTitle:SetPoint("TOPLEFT", 0, -top - 4)
    home.professionTitle:SetWidth(width - 196)
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
    if ns.Option("uiNext") then renderNext(home, query); return end
    local items, states = ns.RecommendedItems(query)
    home.professionCount, home.extraCount = 0, 0
    for _, card in ipairs(home.cards) do card:Hide() end
    for _, card in ipairs(home.extraCards) do card:Hide() end
    local featured, shown = nil, 0
    for _, item in ipairs(items) do
        if shown < 5 then
            shown = shown + 1
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
    end
    updateCard(home.leveling, featured or {title = "Your next zone", category = "LEVELING",
        detail = states.leveling or "Browse all leveling guides to find your next zone.", action = "Browse guides",
        start = function() ns.SetFilter("guides") end})
    renderGoldSessionCard(home)
    home.professionEmpty:SetShown(home.professionCount == 0)
    home.professionEmpty.text:SetText(states.professions or "Browse professions to find a crafting guide.")
    home.moreTitle:SetShown(home.extraCount > 0)
    ns.UpdateSessionResumeBar()
    local running = ns.routeSelection ~= nil and ns.selectedRoute ~= nil
    if running then home.resume.stopControl:Show(); home.resume.orderControl:Show()
    else home.resume.stopControl:Hide(); home.resume.orderControl:Hide() end
    ns.ui.metrics[2].caption:SetText("RECOMMENDATIONS"); ns.ui.metrics[2].value:SetText(tostring(#items))
    home:Show(); ns.LayoutRecommended()
end
