local addonName, ns = ...

-- Personal, market-scoped snapshots. Never read SavedVariables at file scope.
local lifetime, maxQuotes, maxOffers = 21600, 256, 40
local function now()
    local value = ns.ReadPublic(GetServerTime)
    return ns.GuideInteger(value, 9000000000) and value or nil
end
local function scope()
    local realm = ns.SafeTitle(ns.ReadPublic(GetRealmName))
    local _, build = ns.ReadPublic(GetBuildInfo)
    local region = ns.ReadPublic(GetCurrentRegion)
    local faction = ns.profile and ns.profile.faction
    if not realm or not ns.SafeTitle(build) or faction ~= "Horde" and faction ~= "Alliance" then return end
    return table.concat({realm, ns.GuideInteger(region, 10) and region or 0, faction, build}, ":")
end
local function validQuote(quote, timestamp)
    return type(quote) == "table" and ns.GuideInteger(quote.time, 9000000000)
        and timestamp and quote.time <= timestamp and timestamp - quote.time <= lifetime
        and (quote.unavailable == true or ns.GuideInteger(quote.unitPrice, 9000000000000) and quote.unitPrice > 0)
end

function ns.InitializeAuctionMarket()
    local saved, key, timestamp = ns.professionSaved, scope(), now()
    if not saved or not key then return end
    if ns.auctionMarketScope and ns.auctionMarketScope ~= key then
        ns.marketQuotes, ns.auctionPriceAssessment = {}, nil
    end
    ns.auctionMarketScope = key
    if type(saved.market) ~= "table" or saved.market.scope ~= key or type(saved.market.quotes) ~= "table" then
        saved.market = {scope = key, quotes = {}}
    end
    ns.auctionMarketSaved = saved.market
    local count = 0
    for id, quote in pairs(saved.market.quotes) do
        if ns.GuideInteger(id) and id > 0 and validQuote(quote, timestamp) and count < maxQuotes then
            local restored = {unitPrice = quote.unitPrice, quantity = quote.quantity, time = quote.time,
                complete = quote.complete == true, unavailable = quote.unavailable == true, cached = true, offers = {}}
            for index, offer in ipairs(type(quote.offers) == "table" and quote.offers or {}) do
                if index > maxOffers then break end
                if type(offer) == "table" and ns.GuideInteger(offer[1], 9000000000000) and offer[1] > 0
                    and ns.GuideInteger(offer[2], 10000000) and offer[2] > 0 then
                    restored.offers[#restored.offers + 1] = {offer[1], offer[2]}
                end
            end
            table.sort(restored.offers, function(a, b) return a[1] < b[1] end)
            ns.marketQuotes[id], count = restored, count + 1
        else saved.market.quotes[id] = nil end
    end
    ns.auctionMarketRestored = count
    if count > 0 then ns.auctionPriceAssessment = true end
end

function ns.AuctionQuote(id)
    local quote = ns.marketQuotes[id]
    if not quote then return end
    local timestamp = now()
    if quote.time and timestamp and not validQuote(quote, timestamp) then return end
    return quote
end

function ns.AuctionUnitPrice(id, quantity)
    local quote = ns.AuctionQuote(id)
    if not quote or quote.unavailable or not quote.unitPrice then return end
    quantity = ns.GuideInteger(quantity, 10000000) and quantity > 0 and quantity or 1
    if not quote.offers or #quote.offers == 0 then return quote.unitPrice end
    local remaining, total = quantity, 0
    for _, offer in ipairs(quote.offers) do
        local take = math.min(remaining, offer[2])
        total, remaining = total + take * offer[1], remaining - take
        if remaining == 0 then return total / quantity, quote.complete end
    end
    -- A partial book cannot supply a guaranteed full-batch buy cost.
    return quote.unitPrice, false
end

local function save(id, quote)
    local saved, key = ns.auctionMarketSaved, scope()
    if not saved or saved.scope ~= key or not quote.time then return end
    local count, oldest, oldestTime = 0
    for itemID, old in pairs(saved.quotes) do
        count = count + 1
        if not oldestTime or (old.time or 0) < oldestTime then oldest, oldestTime = itemID, old.time or 0 end
    end
    if not saved.quotes[id] and count >= maxQuotes then saved.quotes[oldest] = nil end
    saved.quotes[id] = quote
end

function ns.StoreAuctionQuote(id, offers, complete, empty)
    if not ns.GuideInteger(id) or id <= 0 or #offers == 0 and not empty then return false end
    table.sort(offers, function(a, b) return a[1] < b[1] end)
    local book, total = {}, 0
    for _, offer in ipairs(offers) do
        local last = book[#book]
        if last and last[1] == offer[1] then last[2] = last[2] + offer[2]
        elseif #book < maxOffers then book[#book + 1] = {offer[1], offer[2]}
        else complete = false; break end
        total = total + offer[2]
    end
    local quote = {unitPrice = book[1] and book[1][1], quantity = total,
        offers = book, complete = complete == true, unavailable = empty == true, time = now()}
    ns.marketQuotes[id] = quote; save(id, quote)
    ns.auctionPriceAssessment = true
    ns.auctionMarketRevision = (ns.auctionMarketRevision or 0) + 1
    if ns.ProfessionPricesChanged then ns.ProfessionPricesChanged() end
    ns.RefreshShoppingList()
    if ns.RefreshAuctionGuideSearch then ns.RefreshAuctionGuideSearch() end
    return true
end

local function foreign(row)
    return ns.Public(row.containsOwnerItem) and row.containsOwnerItem == true
        or ns.Public(row.containsAccountItem) and row.containsAccountItem == true
end
function ns.ReadCommodityAuctions(id)
    if not ns.GuideInteger(id) or id <= 0 or not C_AuctionHouse then return end
    local count = ns.ReadPublic(C_AuctionHouse.GetNumCommoditySearchResults, id)
    local knownCount = ns.GuideInteger(count, 10000)
    if not knownCount then count = 1 end -- Existing beta single-result capability.
    local full = ns.ReadPublic(C_AuctionHouse.HasFullCommoditySearchResults, id) == true
    local offers = {}
    for index = 1, math.min(count, 200) do
        local row = ns.ReadPublic(C_AuctionHouse.GetCommoditySearchResultInfo, id, index)
        if type(row) == "table" and ns.GuideInteger(row.unitPrice, 9000000000000) and row.unitPrice > 0
            and ns.GuideInteger(row.quantity, 10000000) and row.quantity > 0 then
            local quantity = row.quantity
            if foreign(row) then
                quantity = ns.GuideInteger(row.numOwnerItems, 10000000) and math.max(0, quantity - row.numOwnerItems) or 0
            end
            if quantity > 0 then offers[#offers + 1] = {row.unitPrice, quantity} end
        end
    end
    local priced = ns.StoreAuctionQuote(id, offers, full and count <= 200, knownCount and count == 0 and full)
    if ns.AuctionScanResult then ns.AuctionScanResult(id, "commodity", full, priced and #offers > 0) end
end

function ns.ReadItemAuctions(key)
    if not ns.Public(key) or type(key) ~= "table" or not ns.GuideInteger(key.itemID) or key.itemID <= 0 or not C_AuctionHouse then return end
    -- Suffixes/pets are different markets; don't mix them into a material quote.
    for _, field in ipairs({"itemSuffix", "battlePetSpeciesID"}) do
        if not ns.Public(key[field]) or key[field] ~= nil and (not ns.GuideInteger(key[field]) or key[field] ~= 0) then return end
    end
    local count = ns.ReadPublic(C_AuctionHouse.GetNumItemSearchResults, key)
    if not ns.GuideInteger(count, 10000) then return end
    local full = ns.ReadPublic(C_AuctionHouse.HasFullItemSearchResults, key) == true
    local offers = {}
    for index = 1, math.min(count, 200) do
        local row = ns.ReadPublic(C_AuctionHouse.GetItemSearchResultInfo, key, index)
        if type(row) == "table" and not foreign(row) and ns.GuideInteger(row.buyoutAmount, 9000000000000)
            and row.buyoutAmount > 0 and ns.GuideInteger(row.quantity, 10000000) and row.quantity > 0 then
            offers[#offers + 1] = {math.ceil(row.buyoutAmount / row.quantity), row.quantity}
        end
    end
    local priced = ns.StoreAuctionQuote(key.itemID, offers, full and count <= 200, count == 0 and full)
    if ns.AuctionScanResult then ns.AuctionScanResult(key.itemID, "item", full, priced and #offers > 0) end
end

ns.auctionCommodityEventReady = ns.On("COMMODITY_SEARCH_RESULTS_UPDATED", ns.ReadCommodityAuctions)
ns.auctionItemEventReady = ns.On("ITEM_SEARCH_RESULTS_UPDATED", ns.ReadItemAuctions)
ns.On("COMMODITY_SEARCH_RESULTS_ADDED", ns.ReadCommodityAuctions)
ns.On("ITEM_SEARCH_RESULTS_ADDED", ns.ReadItemAuctions)
ns.On("AUCTION_ITEM_LIST_UPDATE", function()
    if not ns.auctionHouseOpen or type(GetNumAuctionItems) ~= "function" or type(GetAuctionItemInfo) ~= "function" or type(GetAuctionItemLink) ~= "function" then return end
    local count = ns.ReadPublic(GetNumAuctionItems, "list")
    if not ns.GuideInteger(count, 10000) then return end
    local offers = {}
    for index = 1, math.min(count, 50) do
        local link = ns.SafeTitle(ns.ReadPublic(GetAuctionItemLink, "list", index))
        local id = link and tonumber(string.match(link, "item:(%d+)"))
        local okay, _, _, stack, _, _, _, _, _, _, buyout = pcall(GetAuctionItemInfo, "list", index)
        if id and okay and ns.GuideInteger(stack) and stack > 0 and ns.GuideInteger(buyout, 9000000000000) and buyout > 0 then
            offers[id] = offers[id] or {}; offers[id][#offers[id] + 1] = {math.ceil(buyout / stack), stack}
        end
    end
    for id, book in pairs(offers) do ns.StoreAuctionQuote(id, book, false) end
end)
