local addonName, namespace = ...
local ns = _G.WowTogetherModuleAPI
if not namespace.enabled then return end

local prices = {}
namespace.GoldPrices = prices

local function positiveInteger(value, maximum)
    return ns.GuideInteger(value, maximum or 9000000000000) and value > 0
end

-- Where a price comes from, best first:
--
--   1. the player's own scan, when it is less than an hour old (exact, and
--      what the price scan button is for)
--   2. TradeSkillMaster's AuctionDB, if that addon is installed: its lowest
--      buyout, which is what the item can be sold for right now and matches
--      what the player's own scan records; else its market value. A setting
--      swaps the two for anyone who prefers the smoothed figure.
--   3. Auctionator's last price, if that addon is installed
--   4. the player's own scan, however old
--   5. what a vendor pays
--
-- Other addons' databases are only read, through the lookups they publish
-- for the purpose; nothing is written to them and nothing is copied out.
-- An auction price below the vendor price is not a price anyone would sell
-- at, so the vendor price is used instead.
local FRESH_SCAN = 3600

local function vendorPrice(id)
    local reader = C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(reader) ~= "function" then return nil end
    local copper, quality = ns.ReadPublic(function(itemID)
        local _, _, itemQuality, _, _, _, _, _, _, _, sellPrice = reader(itemID)
        return sellPrice, itemQuality
    end, id)
    if not positiveInteger(copper) then return nil, quality end
    return copper, quality
end

local function scanQuote(id)
    if type(ns.AuctionQuote) ~= "function" then return nil end
    local copper, age = ns.AuctionQuote(id)
    if positiveInteger(copper) and ns.GuideInteger(age, 9000000000) then return copper, age end
end

local function tsmPrice(id)
    local db = namespace.db
    local smoothed = db and db.settings and db.settings["gold.marketValue"] == true
    local order = smoothed and {{"dbmarket", "market value"}, {"dbminbuyout", "lowest buyout"}}
        or {{"dbminbuyout", "lowest buyout"}, {"dbmarket", "market value"}}
    for _, entry in ipairs(order) do
        local value = ns.GoldExternalPrice("TradeSkillMaster", entry[1], id)
        if value then return math.floor(value + 0.5), entry[2] end
    end
end

local function auctionatorPrice(id)
    local value = ns.GoldExternalPrice("Auctionator", nil, id)
    if value then return math.floor(value + 0.5) end
end

-- Which other price databases are there to read.
function prices.Sources()
    return ns.GoldExternalPriceSources()
end

-- Is this a price from an auction house (any source), as opposed to a vendor's?
function prices.IsMarket(source) return type(source) == "string" and source ~= "vendor" end

local function useOthers()
    local db = namespace.db
    return not (db and db.settings and db.settings["gold.otherPrices"] == false)
end

function prices.Price(id)
    if not positiveInteger(id, 2147483647) then return nil end
    local vendor, quality = vendorPrice(id)
    local copper, source, age, label
    local scanned, scanAge = scanQuote(id)
    if scanned and scanAge < FRESH_SCAN then
        copper, source, age, label = scanned, "core auction quote", scanAge, "your scan"
    end
    if not copper and useOthers() then
        local value, kind = tsmPrice(id)
        if value then copper, source, label = value, "TradeSkillMaster", "TradeSkillMaster " .. kind end
        if not copper then
            value = auctionatorPrice(id)
            if value then copper, source, label = value, "Auctionator", "Auctionator" end
        end
    end
    if not copper and scanned then copper, source, age, label = scanned, "core auction quote", scanAge, "your scan" end
    if copper and (not vendor or copper >= vendor) then
        return {copper = copper, source = source, age = age, label = label, market = true,
            confidence = (age == nil or age < 6 * 60 * 60) and 1 or 0.7,
            sampleSize = source, sampleBasis = label,
            provenance = {kind = source, ageSeconds = age}}
    end
    if not vendor then return nil end
    return {copper = vendor, source = "vendor", age = nil, label = "vendor", market = false,
        confidence = quality == 0 and 1 or 0.3,
        sampleSize = 1, sampleBasis = "client item metadata",
        provenance = {kind = "vendor price", qualityKnown = ns.Public(quality)}}
end

-- The core scan owns its saved quote. This wrapper only starts a scan when the
-- public scanner exists and supplies a bounded set of distinct item IDs.
function prices.StartScan(itemIDs)
    local scanner = ns.StartFarmCandidateScan
    if type(scanner) ~= "function" then return false, "Farm candidate scan unavailable." end
    if type(itemIDs) ~= "table" then return false, "Item list unavailable." end
    local ids, seen = {}, {}
    for _, id in ipairs(itemIDs) do
        if positiveInteger(id, 2147483647) and not seen[id] then
            if #ids >= 50 then return false, "Too many farm candidates." end
            seen[id] = true; ids[#ids + 1] = id
        end
    end
    if #ids == 0 then return false, "No farm candidates." end
    return scanner(ids, function() end)
end

local function quoteStatus()
    local others = prices.Sources()
    return "your scan when under an hour old"
        .. (useOthers() and #others > 0 and (", then " .. table.concat(others, ", then ")) or (#others > 0 and " (other addons' prices switched off)" or ", no other price addon found"))
        .. ", then an older scan, then vendor"
end
local function scanStatus()
    return type(ns.StartFarmCandidateScan) == "function" and "available" or "unavailable"
end
function prices.Command(text)
    local id = tonumber(text)
    if positiveInteger(id, 2147483647) then
        local quote = prices.Price(id)
        if not quote then ns.Print("Gold price unavailable for item " .. id .. "."); return end
        local age = quote.age ~= nil and (math.floor(quote.age / 3600) .. "h old") or "age not applicable"
        ns.Print("Item " .. id .. ": " .. quote.copper .. " copper • " .. quote.source
            .. " • confidence " .. math.floor(quote.confidence * 100) .. "% • " .. age)
        return
    end
    ns.Print("Gold prices: " .. quoteStatus() .. "; farm AH scan " .. scanStatus() .. ".")
end
function prices.Probe(output)
    output("Gold prices: " .. quoteStatus() .. "; farm AH scan " .. scanStatus() .. ".")
end
