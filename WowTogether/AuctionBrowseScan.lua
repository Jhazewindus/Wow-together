local addonName, ns = ...

-- A price for everything on the auction house.
--
-- The item scan in AuctionScan.lua asks about one item at a time and reads
-- its whole order book: right for a shopping list, hopeless for "what is
-- anything worth". This scan browses the auction house a category at a time
-- instead. The game answers a browse with every listed item and its lowest
-- price, a page at a time, so the whole house takes a couple of minutes.
--
--   * Order: what gathering and farming produce first (trade goods,
--     consumables, reagents, gems), then recipes and odds and ends, and
--     weapons and armour last. If the player walks away half-way, the
--     prices that matter most are already in.
--   * One request at a time, each only when the game says its throttle is
--     ready. Nothing is bought, bid on or posted.
--   * Results are kept small: one lowest price and one quantity per item,
--     per realm and faction, for three days. The detailed order books the
--     item scan saves are separate and still preferred when fresh.
--   * A client without the browse functions is told so; the item scan still
--     works there.
--
-- Not verified in the game: that Forever's client answers an empty search
-- within a category with every listing, and that a browse sent by an addon
-- is accepted outside a click. The functions are checked for before use.

local LIFETIME = 3 * 24 * 60 * 60
local THROTTLE_POLL, STALL_SECONDS = 0.25, 20

-- Item classes in scan order, with the name shown while each is scanned.
-- The numbers are the game's own item class IDs.
local ORDER = {
    {7, "Trade goods"}, {0, "Consumables"}, {5, "Reagents"}, {3, "Gems"}, {9, "Recipes"},
    {1, "Containers"}, {6, "Ammunition"}, {15, "Miscellaneous"}, {12, "Quest items"}, {8, "Item enhancements"},
    {4, "Armour"}, {2, "Weapons"},
}

local state           -- the scan in progress
local store           -- this auction house's prices: {price = {[itemID] = copper}, quantity = {...}, time = {...}}

local function now()
    local value = ns.ReadPublic(GetServerTime)
    return ns.GuideInteger(value, 9000000000) and value or nil
end

-- Which auction house these prices belong to: the realm and the faction.
--
-- Both are read from the game here and now. The addon's own record of the
-- character is only filled in when its main window or a guide is opened, so
-- on a bank alt that has done neither it still says "unknown" (seen in
-- play: the scan refused to start). And a scan is never refused over this:
-- if the game will not say, the prices are filed under what is known.
local function scope()
    local realm = ns.SafeTitle(ns.ReadPublic(GetRealmName))
    if not realm and type(GetNormalizedRealmName) == "function" then realm = ns.SafeTitle(ns.ReadPublic(GetNormalizedRealmName)) end
    local faction = ns.ReadPublic(UnitFactionGroup, "player")
    if faction ~= "Horde" and faction ~= "Alliance" then
        faction = ns.profile and ns.profile.faction
        if faction ~= "Horde" and faction ~= "Alliance" then faction = "any" end
    end
    return (realm or "realm") .. ":" .. faction
end

-- One table of prices per auction house, so a scan on a Horde character is
-- still there after logging an Alliance one.
local storeKey
local function prices()
    local key = scope()
    if not ns.db then return nil end
    if store and storeKey == key then return store end
    local all = ns.db.browsePrices
    if type(all) ~= "table" or all.price ~= nil then all = {}; ns.db.browsePrices = all end
    local saved = all[key]
    if type(saved) ~= "table" or type(saved.price) ~= "table" then
        saved = {price = {}, quantity = {}, time = {}}
        all[key] = saved
    end
    saved.quantity = type(saved.quantity) == "table" and saved.quantity or {}
    saved.time = type(saved.time) == "table" and saved.time or {}
    store, storeKey = saved, key
    return store
end

-- The lowest price the last whole-house scan saw for an item, shaped like
-- the item scan's quote so the same callers can read either.
function ns.BrowseQuote(id)
    local saved = prices()
    local price, seen, timestamp = saved and saved.price[id], saved and saved.time[id], now()
    if not ns.GuideInteger(price, 9000000000000) or price <= 0 or not seen or not timestamp then return nil end
    if timestamp < seen or timestamp - seen > LIFETIME then return nil end
    local quantity = saved.quantity[id] or 1
    return {unitPrice = price, median = price, quantity = quantity, offers = {{price, quantity}},
        complete = false, time = seen, browse = true}
end

function ns.BrowsePriceCount()
    local saved, count = prices(), 0
    for _ in pairs(saved and saved.price or {}) do count = count + 1 end
    return count
end

local function supported()
    local api = C_AuctionHouse
    return type(api) == "table" and type(api.SendBrowseQuery) == "function" and type(api.GetBrowseResults) == "function"
        and type(api.RequestMoreBrowseResults) == "function" and type(api.HasFullBrowseResults) == "function"
end
function ns.FullPriceScanSupported() return supported() end

local function report()
    if state and type(state.onProgress) == "function" then
        pcall(state.onProgress, {category = state.index, categories = #ORDER, name = ORDER[state.index] and ORDER[state.index][2],
            items = state.items, listings = state.listings, running = state.running, message = state.message})
    end
end

local function finish(message, completed)
    if not state then return end
    local finished = state
    finished.running, finished.message, finished.completed = false, message, completed == true
    state = nil
    if finished.items > 0 then
        ns.auctionPriceAssessment = true
        ns.auctionMarketRevision = (ns.auctionMarketRevision or 0) + 1
        if ns.ProfessionPricesChanged then ns.ProfessionPricesChanged() end
    end
    if type(finished.onProgress) == "function" then
        pcall(finished.onProgress, {category = finished.index, categories = #ORDER, items = finished.items, listings = finished.listings,
            running = false, message = message, completed = finished.completed})
    end
end

-- Takes one page of results into the store: the lowest price per item, and
-- how many are listed. An item listed under several variants keeps its lowest.
local function absorb(results)
    local saved, timestamp = prices(), now()
    if not saved or not timestamp or type(results) ~= "table" then return end
    for _, row in ipairs(results) do
        local key = type(row) == "table" and row.itemKey
        local id, price, quantity = type(key) == "table" and key.itemID, type(row) == "table" and row.minPrice, type(row) == "table" and row.totalQuantity
        if ns.GuideInteger(id, 2147483647) and id > 0 and ns.GuideInteger(price, 9000000000000) and price > 0 then
            state.listings = state.listings + 1
            local fresh = state.seen[id] ~= true
            if fresh or price < (saved.price[id] or math.huge) then saved.price[id] = price end
            saved.quantity[id] = (fresh and 0 or (saved.quantity[id] or 0)) + (ns.GuideInteger(quantity, 100000000) and quantity or 1)
            saved.time[id] = timestamp
            if fresh then state.seen[id] = true; state.items = state.items + 1 end
        end
    end
end

local step

-- Runs `action` as soon as the game's request throttle allows.
local function whenReady(action)
    local scan = state
    local function try()
        if state ~= scan or not scan.running then return end
        if not ns.AuctionHouseVisible() then finish("The auction house was closed. " .. scan.items .. " prices were saved.") return end
        local api = C_AuctionHouse
        local ready = type(api.IsThrottledMessageSystemReady) ~= "function" or ns.ReadPublic(api.IsThrottledMessageSystemReady) ~= false
        if ready then action() else ns.After("timer:AuctionBrowse", THROTTLE_POLL, try) end
    end
    try()
end

-- A request that is never answered must not hang the scan: after twenty
-- seconds the category is given up and the next one starts. Each request has
-- its own number, so an old watchdog cannot cut short a later page.
local function uptime()
    local value = ns.ReadPublic(GetTime)
    return type(value) == "number" and value or nil
end
local function watchdog()
    local scan = state
    scan.request = (scan.request or 0) + 1
    local request, asked = scan.request, uptime()
    ns.After("timer:AuctionBrowse", STALL_SECONDS, function()
        if state ~= scan or not scan.running or scan.request ~= request or not scan.waiting then return end
        local current = uptime()
        if asked and current and current - asked < STALL_SECONDS then return end      -- The timer came early: not a stall.
        scan.waiting = nil
        scan.skipped = scan.skipped + 1
        step()
    end)
end

step = function()
    if not state then return end
    state.index = state.index + 1
    local entry = ORDER[state.index]
    if not entry then
        finish("Done: " .. state.items .. " items priced from " .. state.listings .. " listings."
            .. (state.skipped > 0 and (" " .. state.skipped .. " categories did not answer.") or ""), true)
        return
    end
    state.message = "Scanning " .. entry[2] .. "…"
    report()
    whenReady(function()
        local sorts = {}
        if Enum and Enum.AuctionHouseSortOrder then sorts[1] = {sortOrder = Enum.AuctionHouseSortOrder.Price, reverseSort = false} end
        state.waiting = "first"
        local okay = pcall(C_AuctionHouse.SendBrowseQuery, {searchString = "", sorts = sorts, filters = {},
            itemClassFilters = {{classID = entry[1]}}})
        if not okay then state.waiting = nil; state.skipped = state.skipped + 1; step(); return end
        watchdog()
    end)
end

local function more()
    if not state or not state.running then return end
    if ns.ReadPublic(C_AuctionHouse.HasFullBrowseResults) == true then state.waiting = nil; step(); return end
    whenReady(function()
        state.waiting = "more"
        local okay = pcall(C_AuctionHouse.RequestMoreBrowseResults)
        if not okay then state.waiting = nil; step(); return end
        watchdog()
    end)
end

ns.On("AUCTION_HOUSE_BROWSE_RESULTS_UPDATED", function()
    if not state or state.waiting ~= "first" then return end
    state.waiting = nil
    local okay, results = pcall(C_AuctionHouse.GetBrowseResults)
    if okay then absorb(results) end
    report()
    more()
end)
ns.On("AUCTION_HOUSE_BROWSE_RESULTS_ADDED", function(added)
    if not state or state.waiting ~= "more" then return end
    state.waiting = nil
    absorb(added)
    report()
    more()
end)
-- At an auction house the character's details are wanted by every price
-- function, so they are read now, not when the main window next opens.
ns.On("AUCTION_HOUSE_SHOW", function()
    if ns.ReadProfile then pcall(ns.ReadProfile) end
end)
ns.On("AUCTION_HOUSE_CLOSED", function()
    if state then finish("The auction house was closed. " .. state.items .. " prices were saved.") end
end)

-- Starts the scan. `onProgress` is called with {category, categories, name,
-- items, listings, running, message, completed} as it goes.
function ns.StartFullPriceScan(onProgress)
    if state then return false, "A scan of the auction house is already running." end
    if not ns.AuctionHouseVisible() then return false, "Open the auction house first." end
    if not supported() then return false, "This client cannot browse the whole auction house. Items are looked up one at a time instead." end
    if ns.AuctionScanState and ns.AuctionScanState() then return false, "Another auction scan is already running." end
    if not prices() then return false, "The addon's saved data is not loaded yet. Try again in a moment." end
    state = {index = 0, items = 0, listings = 0, skipped = 0, running = true, seen = {}, onProgress = onProgress}
    step()
    return true
end

function ns.StopFullPriceScan()
    if not state then return false end
    finish("Stopped. " .. state.items .. " prices were saved.")
    return true
end

function ns.FullPriceScanRunning() return state ~= nil end

function ns.FullPriceScanDiagnostics(output)
    output("Whole-house price scan: " .. (supported() and "available" or "not available on this client") .. "; "
        .. ns.BrowsePriceCount() .. " item prices saved for this realm and faction" .. (state and "; running" or "") .. ".")
end
