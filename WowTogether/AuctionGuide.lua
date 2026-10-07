local addonName, ns = ...

-- User-clicked searches only. No background queries, purchases, bids or crafts.
local opened, toolbar, selected = false, nil, 1
local function status(text)
    ns.auctionGuideStatus = text
    if ns.shoppingWindow then ns.shoppingWindow.status:SetText(text) end
    if toolbar then toolbar.status:SetText(text) end
end
local function shown(frame) return frame and ns.ReadPublic(frame.IsShown, frame) == true end
local function items()
    if ns.shoppingContext and ns.shoppingWindow and ns.shoppingWindow:IsShown() then return ns.shoppingList or {} end
    local guide = ns.routeSelection
    if guide and guide.mode == "profession" then return ns.selectedRoute and ns.selectedRoute.materials or {} end
    return ns.shoppingList or {}
end

function ns.SearchGuideAuctionItem(id)
    if not ns.GuideInteger(id) or id <= 0 then return false end
    if ns.RouteInCombat() then status("Search after combat."); return false end
    if not opened then status("Open an auction house first."); return false end
    -- Search real cached names, never the fallback 'Item 123'. Loading a name
    -- requests item data; the player clicks again when it is ready.
    local name = C_Item and ns.SafeTitle(ns.ReadPublic(C_Item.GetItemInfo, id))
    if not name then ns.ItemName(id); status("Item name loading. Try again shortly."); return false end
    if shown(AuctionHouseFrame) and C_AuctionHouse and type(C_AuctionHouse.SendBrowseQuery) == "function"
        and type(AuctionHouseFrame.SendBrowseQuery) == "function" and type(AuctionHouseFrame.SetSearchText) == "function"
        and type(AuctionHouseFrame.GetCategoriesList) == "function" then
        if type(C_AuctionHouse.IsThrottledMessageSystemReady) == "function"
            and ns.ReadPublic(C_AuctionHouse.IsThrottledMessageSystemReady) ~= true then
            status("Auction search is busy. Try again shortly."); return false
        end
        if type(AreSortTypesLoaded) == "function" and ns.ReadPublic(AreSortTypesLoaded) ~= true then
            status("Auction search is loading. Try again shortly."); return false
        end
        local categories = ns.ReadPublic(AuctionHouseFrame.GetCategoriesList, AuctionHouseFrame)
        if not categories or type(categories.SetSelectedCategory) ~= "function" then status("Choose the Buy tab to search."); return false end
        categories:SetSelectedCategory(nil)
        -- The public frame helper populates Blizzard's result list and selects
        -- Buy mode. Clearing category/level filters avoids a stale armor filter.
        AuctionHouseFrame:SendBrowseQuery(name, nil, nil, {})
        AuctionHouseFrame:SetSearchText(name)
        status("Searching " .. name .. "."); return true
    end
    if shown(AuctionFrame) and shown(AuctionFrameBrowse) and BrowseName
        and type(BrowseName.SetText) == "function" and type(QueryAuctionItems) == "function"
        and type(CanSendAuctionQuery) == "function" then
        if ns.ReadPublic(CanSendAuctionQuery, "list") ~= true then status("Auction search is busy. Try again shortly."); return false end
        AuctionFrameBrowse.page = 0
        AuctionFrameBrowse.selectedCategoryIndex, AuctionFrameBrowse.selectedSubCategoryIndex,
            AuctionFrameBrowse.selectedSubSubCategoryIndex, AuctionFrameBrowse.qualityIndex = nil, nil, nil, nil
        BrowseName:SetText(name)
        if BrowseMinLevel then BrowseMinLevel:SetText("") end
        if BrowseMaxLevel then BrowseMaxLevel:SetText("") end
        if IsUsableCheckButton then IsUsableCheckButton:SetChecked(false) end
        QueryAuctionItems(name, nil, nil, 0, false, nil, false, true, nil)
        status("Searching " .. name .. "."); return true
    end
    status("Open the auction Buy / Browse tab to search."); return false
end

function ns.RefreshAuctionGuideSearch()
    if not opened then if toolbar then toolbar:Hide() end; return end
    local parent = shown(AuctionHouseFrame) and AuctionHouseFrame or shown(AuctionFrame) and AuctionFrame
    if not parent or ns.RouteInCombat() then return end
    local list = items()
    if not toolbar then
        toolbar = CreateFrame("Frame", nil, parent, "BackdropTemplate")
        ns.auctionGuideToolbar = toolbar
        toolbar:SetSize(450, 64); ns.UIPanel(toolbar); toolbar:SetFrameStrata("DIALOG")
        toolbar.previous = ns.UIButton(toolbar, "‹", 28, function() selected = math.max(1, selected - 1); ns.RefreshAuctionGuideSearch() end)
        toolbar.previous:SetPoint("TOPLEFT", 7, -7)
        toolbar.next = ns.UIButton(toolbar, "›", 28, function() selected = math.min(#items(), selected + 1); ns.RefreshAuctionGuideSearch() end)
        toolbar.next:SetPoint("TOPRIGHT", -7, -7)
        toolbar.search = ns.UIButton(toolbar, "Search guide material", 362, function()
            local item = items()[selected]; if item then ns.SearchGuideAuctionItem(item.itemID) end
        end)
        toolbar.search:SetPoint("TOPLEFT", 44, -7)
        toolbar.status = ns.UILabel(toolbar, nil, 10, ns.UIColors.muted)
        toolbar.status:SetPoint("BOTTOMLEFT", 9, 7); toolbar.status:SetWidth(432)
    end
    toolbar:SetParent(parent); toolbar:ClearAllPoints(); toolbar:SetPoint("TOPLEFT", parent, "BOTTOMLEFT", 0, -5)
    selected = math.max(1, math.min(selected, #list))
    local item = list[selected]
    toolbar.search.caption:SetText(item and ("Search " .. ns.ItemName(item.itemID, item.name)) or "No guide materials")
    toolbar.search:SetEnabled(item ~= nil); toolbar.previous:SetEnabled(selected > 1); toolbar.next:SetEnabled(selected < #list)
    toolbar.status:SetText(ns.auctionGuideStatus or "Guide materials • " .. selected .. " / " .. #list)
    toolbar:SetShown(#list > 0)
end

local function changed(reprice)
    ns.RefreshShoppingList()
    if reprice and ns.ProfessionPricesChanged then ns.ProfessionPricesChanged()
    elseif ns.QueueProfessionUpdate then ns.QueueProfessionUpdate() end
end
ns.On("AUCTION_HOUSE_SHOW", function()
    opened = true
    ns.RefreshAuctionGuideSearch()
    -- Some clients create their auction frame after the SHOW event.
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, ns.RefreshAuctionGuideSearch) end
end)
ns.On("AUCTION_HOUSE_CLOSED", function() opened = false; if toolbar then toolbar:Hide() end end)
ns.On("ITEM_SEARCH_RESULTS_UPDATED", function(key)
    if not ns.Public(key) or type(key) ~= "table" or not ns.GuideInteger(key.itemID) or key.itemID <= 0 or not C_AuctionHouse then return end
    local count = ns.ReadPublic(C_AuctionHouse.GetNumItemSearchResults, key)
    if not ns.GuideInteger(count, 10000) then return end
    local best, quantity
    for i = 1, math.min(count, 100) do
        local row = ns.ReadPublic(C_AuctionHouse.GetItemSearchResultInfo, key, i)
        if type(row) == "table" and ns.GuideInteger(row.buyoutAmount) and row.buyoutAmount > 0
            and ns.GuideInteger(row.quantity) and row.quantity > 0 then
            local unit = math.ceil(row.buyoutAmount / row.quantity)
            if not best or unit < best then best, quantity = unit, row.quantity end
        end
    end
    if best then
        local old = ns.marketQuotes[key.itemID]
        ns.marketQuotes[key.itemID] = {unitPrice = best, quantity = quantity}
        changed(not old or old.unitPrice ~= best)
    end
end)
ns.On("AUCTION_ITEM_LIST_UPDATE", function()
    if not opened or type(GetNumAuctionItems) ~= "function" or type(GetAuctionItemInfo) ~= "function" or type(GetAuctionItemLink) ~= "function" then return end
    local count = ns.ReadPublic(GetNumAuctionItems, "list")
    if not ns.GuideInteger(count, 10000) then return end
    local quotes = {}
    for i = 1, math.min(count, 50) do
        local link = ns.SafeTitle(ns.ReadPublic(GetAuctionItemLink, "list", i))
        local id = link and tonumber(string.match(link, "item:(%d+)"))
        local okay, name, texture, stack, quality, usable, level, header, bid, increment, buyout = pcall(GetAuctionItemInfo, "list", i)
        if id and okay and ns.GuideInteger(stack) and stack > 0 and ns.GuideInteger(buyout) and buyout > 0 then
            local unit = math.ceil(buyout / stack)
            if not quotes[id] or unit < quotes[id].unitPrice then quotes[id] = {unitPrice = unit, quantity = stack} end
        end
    end
    local any, reprice
    for id, quote in pairs(quotes) do
        local old = ns.marketQuotes[id]
        if not old or old.unitPrice ~= quote.unitPrice then reprice = true end
        ns.marketQuotes[id], any = quote, true
    end
    if any then changed(reprice) end
end)
local previousRegen = ns.handlers.PLAYER_REGEN_ENABLED
ns.On("PLAYER_REGEN_ENABLED", function(...)
    if previousRegen then previousRegen(...) end
    if ns.shoppingContext and ns.shoppingWindow and ns.shoppingWindow:IsShown() and not ns.shoppingContext.signature then ns.RefreshProfessionShopping() end
    ns.RefreshAuctionGuideSearch()
end)
