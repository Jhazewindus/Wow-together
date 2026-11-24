local addonName, namespace = ...
local ns = _G.WowTogetherModuleAPI
if not namespace.enabled then return end

local prices = {}
namespace.GoldPrices = prices

local function positiveInteger(value, maximum)
    return ns.GuideInteger(value, maximum or 9000000000000) and value > 0
end

-- Ask the core's saved auction-quote lookup first. If the core has no quote,
-- use only the client item sell price; Gold does not consult TSM or write a
-- second auction cache.
function prices.Price(id)
    if not positiveInteger(id, 2147483647) then return nil end
    if type(ns.AuctionQuote) == "function" then
        local copper, age = ns.AuctionQuote(id)
        if positiveInteger(copper) and ns.GuideInteger(age, 9000000000) then
            return {copper = copper, source = "core auction quote", age = age,
                confidence = age < 6 * 60 * 60 and 1 or 0.7,
                sampleSize = "core quote", sampleBasis = "saved core auction scan",
                provenance = {kind = "core auction quote", ageSeconds = age}}
        end
    end
    local reader = C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(reader) ~= "function" then return nil end
    local copper, quality = ns.ReadPublic(function(itemID)
        local _, _, itemQuality, _, _, _, _, _, _, _, sellPrice = reader(itemID)
        return sellPrice, itemQuality
    end, id)
    if not positiveInteger(copper) then return nil end
    local grey = quality == 0
    return {copper = copper, source = "vendor", age = nil,
        confidence = grey and 1 or 0.3,
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
    return type(ns.AuctionQuote) == "function" and "core auction quote, then vendor" or "vendor only; auction quote unavailable"
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
