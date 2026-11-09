local addonName, namespace = ...
local ns = _G.WowTogetherModuleAPI
if not namespace.enabled then return end

local prices = {}
namespace.GoldPrices = prices
local db = namespace.db
if type(db.prices) ~= "table" then db.prices = {} end
local MAX_QUOTES, MAX_AGE = 300, 24 * 60 * 60

local function positiveInteger(value, maximum)
    return ns.GuideInteger(value, maximum or 9000000000000) and value > 0
end
local function timestamp()
    local value = ns.ReadPublic(GetServerTime)
    return ns.GuideInteger(value, 9000000000) and value or nil
end
local function scope()
    local realm = ns.SafeTitle(ns.ReadPublic(GetRealmName))
    local faction = ns.SafeTitle(ns.ReadPublic(UnitFactionGroup, "player"))
    if not realm or not faction then return nil end
    return realm .. ":" .. faction
end
local function quoteStore()
    local key = scope()
    if not key then return nil end
    if type(db.prices[key]) ~= "table" then db.prices[key] = {} end
    return db.prices[key]
end

-- The scanner is a future core capability. Calling this function while it is
-- absent has no auction side effect; its callback is the only AH store writer.
function prices.StartScan(itemIDs)
    local scanner = ns.StartFarmCandidateScan
    if type(scanner) ~= "function" then return false, "Farm candidate scan unavailable" end
    if type(itemIDs) ~= "table" then return false, "Item list unavailable" end
    local ids, seen = {}, {}
    for _, id in ipairs(itemIDs) do
        if positiveInteger(id, 2147483647) and not seen[id] then
            if #ids >= MAX_QUOTES then return false, "Too many farm candidates" end
            seen[id] = true; ids[#ids + 1] = id
        end
    end
    if #ids == 0 then return false, "No farm candidates" end
    return scanner(ids, function(id, quote) prices.StoreQuote(id, quote) end)
end

function prices.StoreQuote(id, quote)
    local saved, now = quoteStore(), timestamp()
    if not saved or not now or not positiveInteger(id, 2147483647) or type(quote) ~= "table"
        or not positiveInteger(quote.count, 10000000) then return false end
    local minimum = positiveInteger(quote.minBuyout) and quote.minBuyout or nil
    local median = positiveInteger(quote.median) and quote.median or nil
    if not minimum and not median then return false end
    local count, oldest, oldestTime = 0, nil, nil
    for itemID, previous in pairs(saved) do
        count = count + 1
        if not oldestTime or (previous.time or 0) < oldestTime then
            oldest, oldestTime = itemID, previous.time or 0
        end
    end
    if not saved[id] and count >= MAX_QUOTES then saved[oldest] = nil end
    saved[id] = {minBuyout = minimum, median = median, count = quote.count,
        time = now, complete = quote.complete == true}
    return true
end

local function auctionQuote(id)
    local saved, now = quoteStore(), timestamp()
    local quote = saved and saved[id]
    if not quote or not now or not ns.GuideInteger(quote.time, 9000000000)
        or quote.time > now or now - quote.time >= MAX_AGE then
        if quote and saved then saved[id] = nil end
        return nil
    end
    local age = now - quote.time
    local copper = positiveInteger(quote.median) and quote.median
        or positiveInteger(quote.minBuyout) and quote.minBuyout or nil
    if not copper or not positiveInteger(quote.count, 10000000) then return nil end
    return {copper = copper, source = "AH scan", age = age,
        confidence = age < 6 * 60 * 60 and 1 or 0.7,
        sampleSize = quote.count, sampleBasis = "auction listings",
        provenance = {kind = "own scan", scope = scope(), observedAt = quote.time,
            complete = quote.complete == true}}
end

local function vendorFacts(id)
    local reader = C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(reader) ~= "function" then return nil, nil end
    local price, quality = ns.ReadPublic(function(itemID)
        local _, _, itemQuality, _, _, _, _, _, _, _, sellPrice = reader(itemID)
        return sellPrice, itemQuality
    end, id)
    if not positiveInteger(price) then return nil, quality end
    return price, quality
end
local function vendorQuote(copper, grey, floor)
    if not copper then return nil end
    return {copper = copper, source = floor and "vendor floor" or "vendor", age = nil,
        confidence = (grey or floor) and 1 or 0.3,
        sampleSize = 1, sampleBasis = "item metadata lookup",
        provenance = {kind = "client item data", vendorOnly = grey == true}}
end

local function tsmQuote(id)
    if type(TSM_API) ~= "table" or type(TSM_API.ToItemString) ~= "function"
        or type(TSM_API.GetCustomPriceValue) ~= "function" then return nil end
    local item = ns.ReadPublic(TSM_API.ToItemString, "i:" .. id)
    if type(item) ~= "string" then return nil end
    for _, method in ipairs({"DBMarket", "DBMinBuyout", "DBRegionMarketAvg"}) do
        local copper = ns.ReadPublic(TSM_API.GetCustomPriceValue, method, item)
        if positiveInteger(copper) then
            return {copper = copper, source = "TSM " .. method, age = nil,
                confidence = method == "DBRegionMarketAvg" and 0.5 or 0.7,
                sampleSize = "unknown", sampleBasis = "TSM does not supply a sample count",
                provenance = {kind = "TSM", method = method, freshness = "unknown"}}
        end
    end
end

function prices.Price(id)
    if not positiveInteger(id, 2147483647) then return nil end
    local vendor, quality = vendorFacts(id)
    local grey = quality == 0
    if grey then return vendorQuote(vendor, true, false) end
    local market = tsmQuote(id) or auctionQuote(id)
    if market and vendor and market.copper < vendor then return vendorQuote(vendor, false, true) end
    return market or vendorQuote(vendor, false, false)
end

-- A newer core may supply the §3 result table. The local price API remains
-- usable while that core export is unavailable.
if type(ns.Gold) == "table" then ns.Gold.Price = prices.Price end

local function sourceStatus()
    return type(TSM_API) == "table" and type(TSM_API.ToItemString) == "function"
        and type(TSM_API.GetCustomPriceValue) == "function" and "available" or "unavailable"
end
local function scanStatus()
    return type(ns.StartFarmCandidateScan) == "function" and "available" or "unavailable"
end
local function storedCount()
    local saved, count = quoteStore(), 0
    for _ in pairs(saved or {}) do count = count + 1 end
    return count
end
function prices.Command(text)
    local id = tonumber(text)
    if positiveInteger(id, 2147483647) then
        local quote = prices.Price(id)
        if not quote then ns.Print("Gold price unavailable for item " .. id .. "."); return end
        local age = quote.age and (math.floor(quote.age / 3600) .. "h old") or "age unknown"
        ns.Print("Item " .. id .. ": " .. quote.copper .. " copper • " .. quote.source
            .. " • confidence " .. math.floor(quote.confidence * 100) .. "% • samples "
            .. tostring(quote.sampleSize) .. " • " .. age)
        return
    end
    ns.Print("Gold prices: TSM " .. sourceStatus() .. "; farm AH scan " .. scanStatus()
        .. "; " .. storedCount() .. " saved quotes (24h expiry).")
end
function prices.Probe(output)
    output("Gold prices: TSM " .. sourceStatus() .. "; farm AH scan " .. scanStatus()
        .. "; saved quotes " .. storedCount() .. "; 24h expiry.")
end
