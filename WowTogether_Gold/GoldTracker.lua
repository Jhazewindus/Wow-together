local addonName, namespace = ...
local ns = _G.WowTogetherModuleAPI
if not namespace.enabled then return end

-- The farm tracker.
--
-- A window that counts what a farming session actually brought in: every
-- item the player looted, mined, picked, skinned or fished, the coins, the
-- experience, and what all of it is worth per hour. It ranks the items by
-- what they earned, so the player can see what a spot really pays.
--
-- It is separate from the farm suggestions. Those measure one chosen farm
-- against its estimate; this counts everything, whether or not a suggested
-- farm is running, and shows that farm's estimate beside the result when
-- there is one.
--
--   * Items are recorded as counts. Their value is worked out when drawn,
--     from the core's saved auction quote if there is one and the vendor
--     price otherwise, so a price scan re-values the whole session.
--   * Only what the player loots counts: "You receive loot" lines, not items
--     bought, crafted or handed over by a quest.
--   * The clock runs while farming. It starts with the first loot, and stops
--     counting after five minutes with nothing looted, so a break does not
--     dilute the hourly figures.
--   * Nothing is sold, bought, mailed or destroyed. The price scan only
--     reads auction prices, and only when the player presses the button at
--     an auction house.
local tracker = {}
namespace.GoldTracker = tracker
local prices, db = namespace.GoldPrices, namespace.db

local IDLE_SECONDS, IDLE_GRACE = 300, 60       -- stop the clock after this long without loot; keep this much of the gap
local SESSION_GAP = 1800                       -- after this long without loot, the session is over and the next loot starts a new one
local ROWS, HISTORY_KEPT, HISTORY_MIN_SECONDS = 7, 20, 300
local WIDTH, COLLAPSED_HEIGHT = 392, 34
local AUCTION, VENDOR = "core auction quote", "vendor"

if type(db.tracker) ~= "table" then db.tracker = {} end
if type(db.trackerHistory) ~= "table" then db.trackerHistory = {} end
if type(db.trackerWindow) ~= "table" then db.trackerWindow = {} end
local state = db.tracker
state.items = type(state.items) == "table" and state.items or {}
state.active = type(state.active) == "number" and state.active or 0
state.coin = type(state.coin) == "number" and state.coin or 0
state.xp = type(state.xp) == "number" and state.xp or 0
state.loots = type(state.loots) == "number" and state.loots or 0
state.zones = type(state.zones) == "table" and state.zones or {}
state.kinds = type(state.kinds) == "table" and state.kinds or {}
state.harvests = type(state.harvests) == "table" and state.harvests or {}
-- A clock reading does not survive a reload: a session comes back paused.
local running, resumedAt, lastLoot, lastXP = false, nil, nil, nil

local function clock()
    local value = ns.ReadPublic(GetTime)
    return type(value) == "number" and value or nil
end

-- Seconds of farming so far.
function tracker.Seconds()
    local now = clock()
    if running and resumedAt and now then return state.active + math.max(0, now - resumedAt) end
    return state.active
end

function tracker.Running() return running end

local function zoneName()
    local name = ns.ReadPublic(GetRealZoneText)
    return type(name) == "string" and name ~= "" and name or nil
end

local function wallClock()
    local value = ns.ReadPublic(GetServerTime)
    return type(value) == "number" and value or nil
end

function tracker.Start()
    if running then return end
    local now = clock()
    if not now then return end
    running, resumedAt, lastLoot = true, now, now
    state.zone = state.zone or zoneName()
    state.held = nil
    lastXP = nil
end

-- Where most of the session's loot came from: a session that wanders is
-- named after the zone it was mostly spent in, not the one it began in.
local function mainZone()
    local best, most = state.zone, 0
    for zone, count in pairs(state.zones) do
        if type(count) == "number" and (count > most or (count == most and zone == state.zone)) then best, most = zone, count end
    end
    return best
end

-- Writes the time farmed so far into the saved session.
--
-- Saved data is only written to disk at logout, and it holds what is in the
-- table at that moment. The running stretch used to live in memory until
-- the session was paused, so logging out mid-session saved the items and no
-- time at all: an hour of fishing came back as "0 seconds", and was then
-- thrown away as too short to keep. The stretch is now folded in at every
-- loot, and again at logout.
local function checkpoint()
    local now = clock()
    if running and now and resumedAt then
        state.active = state.active + math.max(0, now - resumedAt)
        resumedAt = now
    end
end

-- `keep` is how much of the time since the last loot still counts.
function tracker.Pause(keep)
    if not running then return end
    local now = clock()
    if now and resumedAt then
        local span = now - resumedAt
        if keep and lastLoot then span = math.min(span, math.max(0, lastLoot - resumedAt) + keep) end
        state.active = state.active + math.max(0, span)
    end
    running, resumedAt = false, nil
end

-- What kind of farming a loot came from.
--
-- The game says when a loot window is a fishing catch, and whether it came
-- from a creature or from something in the world (a vein, a herb). For the
-- world kind, the profession is the gathering spell the player just cast.
-- This is read when the loot opens and applied to the loot lines that follow
-- within a few seconds. A session is then "mostly fishing" or "mostly
-- killing", which is what lets it be offered as a farm of that kind.
local KIND_WINDOW = 4
local pendingKind, pendingAt, pendingCounted, lastCast, lastCastAt

local function castKind(name)
    if type(name) ~= "string" then return nil end
    local lower = string.lower(name)
    if string.find(lower, "fishing", 1, true) then return "Fishing" end
    if string.find(lower, "mining", 1, true) then return "Mining" end
    if string.find(lower, "herb", 1, true) then return "Herbalism" end
    if string.find(lower, "skinning", 1, true) then return "Skinning" end
end

local function onCast(unit, _, spellID)
    if unit ~= "player" or not ns.Public(spellID) or type(spellID) ~= "number" then return end
    local name
    name = ns.GoldSpellName(spellID)
    local kind = castKind(name)
    if kind then lastCast, lastCastAt = kind, clock() end
end

-- A gathering cast is followed by its loot at once; a fishing cast by its
-- catch up to half a minute later.
local function recentCast()
    local now = clock()
    if not lastCast or not now or not lastCastAt then return nil end
    if now - lastCastAt <= (lastCast == "Fishing" and 35 or 8) then return lastCast end
end

local function onLootOpened()
    local kind
    if ns.GoldIsFishingLoot() == true then
        kind = "Fishing"
    else
        local guid = ns.GoldLootSourceInfo(1)
        local source = type(guid) == "string" and string.match(guid, "^(%a+)%-") or nil
        local cast = recentCast()
        -- The fishing bobber is an object in the world too.
        if source == "GameObject" then kind = (cast == "Mining" or cast == "Herbalism" or cast == "Fishing") and cast or nil
        elseif source == "Creature" or source == "Vehicle" then kind = cast == "Skinning" and "Skinning" or "Killing"
        elseif cast then kind = cast end
    end
    local now = clock()
    -- LOOT_READY and LOOT_OPENED both announce the same loot: one harvest, counted once.
    if not (pendingAt and now and now - pendingAt < 1 and pendingKind == kind) then pendingCounted = false end
    pendingKind, pendingAt = kind, now
end

local function lootKind()
    local now = clock()
    if pendingKind and now and pendingAt and now - pendingAt <= KIND_WINDOW then return pendingKind end
end

-- The kind most of a session's loot came from.
local function mainKind(kinds)
    local best, most = nil, 0
    for kind, count in pairs(type(kinds) == "table" and kinds or {}) do
        if type(count) == "number" and count > most then best, most = kind, count end
    end
    return best
end

-- ---------------------------------------------------------------------------
-- Value.
-- ---------------------------------------------------------------------------
local function priceOf(itemID)
    local quote = prices and prices.Price and prices.Price(itemID)
    if type(quote) ~= "table" or type(quote.copper) ~= "number" or quote.copper <= 0 then return nil end
    return quote.copper, quote.source, quote.age, quote.label
end

-- An auction price from any source: the player's scan or another addon's database.
local function market(source) return type(source) == "string" and source ~= VENDOR end

local QUALITY = {[0] = {0.62, 0.62, 0.62}, [1] = {0.91, 0.90, 0.86}, [2] = {0.12, 1.00, 0.00}, [3] = {0.00, 0.44, 0.87},
    [4] = {0.64, 0.21, 0.93}, [5] = {1.00, 0.50, 0.00}}

local function itemFacts(itemID)
    local reader = C_Item and C_Item.GetItemInfo or GetItemInfo
    local name, quality, icon
    if type(reader) == "function" then
        name, quality, icon = ns.ReadPublic(function(id)
            local itemName, _, itemQuality, _, _, _, _, _, _, itemIcon = reader(id)
            return itemName, itemQuality, itemIcon
        end, itemID)
    end
    if type(name) ~= "string" or name == "" then
        -- Not in the client's cache yet: ask for it, and name it by number meanwhile.
        if C_Item and type(C_Item.RequestLoadItemDataByID) == "function" then pcall(C_Item.RequestLoadItemDataByID, itemID) end
        name = "Item " .. itemID
    end
    return name, type(quality) == "number" and quality or 1, icon
end

-- Everything the window shows, worked out from the counts and today's prices.
function tracker.Summary()
    tracker.Tick()
    local rows, auction, vendor, unpriced, pieces = {}, 0, 0, 0, 0
    local auctionKinds, vendorKinds, oldest, from = 0, 0, nil, {}
    for itemID, count in pairs(state.items) do
        if type(itemID) == "number" and type(count) == "number" and count > 0 then
            local copper, source, age, label = priceOf(itemID)
            local name, quality, icon = itemFacts(itemID)
            local value = copper and copper * count or 0
            pieces = pieces + count
            if not copper then unpriced = unpriced + count
            elseif market(source) then
                auction, auctionKinds = auction + value, auctionKinds + 1
                local name = source == AUCTION and "your scan" or source
                from[name] = (from[name] or 0) + 1
                if type(age) == "number" and (not oldest or age > oldest) then oldest = age end
            else vendor, vendorKinds = vendor + value, vendorKinds + 1 end
            rows[#rows + 1] = {itemID = itemID, name = name, quality = quality, icon = icon, count = count,
                each = copper, value = value, source = copper and (market(source) and "auction" or "vendor") or nil, label = label}
        end
    end
    table.sort(rows, function(a, b)
        if a.value ~= b.value then return a.value > b.value end
        if a.count ~= b.count then return a.count > b.count end
        return a.itemID < b.itemID
    end)
    local seconds = tracker.Seconds()
    local total = auction + vendor + state.coin
    local hours = seconds / 3600
    return {rows = rows, seconds = seconds, running = running, zone = mainZone(), kind = mainKind(state.kinds),
        total = total, auction = auction, vendor = vendor, coin = state.coin,
        perHour = seconds >= 30 and total / hours or 0,
        pieces = pieces, piecesPerHour = seconds >= 30 and pieces / hours or 0,
        xp = state.xp, xpPerHour = seconds >= 30 and state.xp / hours or 0,
        unpriced = unpriced, auctionKinds = auctionKinds, vendorKinds = vendorKinds, oldestQuote = oldest, priceSources = from,
        loots = state.loots}
end

-- "12g 40s", "40s 12c", "8c".
function tracker.Money(copper)
    copper = math.floor((copper or 0) + 0.5)
    if copper <= 0 then return "0c" end
    local gold, silver, rest = math.floor(copper / 10000), math.floor(copper % 10000 / 100), copper % 100
    if gold >= 100 then return gold .. "g" end
    if gold > 0 then return gold .. "g" .. (silver > 0 and (" " .. silver .. "s") or "") end
    if silver > 0 then return silver .. "s" .. (rest > 0 and (" " .. rest .. "c") or "") end
    return rest .. "c"
end

-- A rate: "34.2g", "86s".
function tracker.Rate(copperPerHour)
    if copperPerHour >= 10000 then return string.format("%.1fg", copperPerHour / 10000) end
    if copperPerHour >= 100 then return math.floor(copperPerHour / 100 + 0.5) .. "s" end
    return math.floor(copperPerHour + 0.5) .. "c"
end

function tracker.Clock(seconds)
    seconds = math.max(0, math.floor(seconds or 0))
    return string.format("%02d:%02d:%02d", math.floor(seconds / 3600), math.floor(seconds % 3600 / 60), seconds % 60)
end

-- "from TradeSkillMaster", "from your scan and TradeSkillMaster".
local function sourcesText(from)
    local names = {}
    for name in pairs(from or {}) do names[#names + 1] = name end
    table.sort(names)
    return #names > 0 and (" from " .. table.concat(names, " and ")) or ""
end

local function ageText(seconds)
    if type(seconds) ~= "number" then return "" end
    if seconds < 3600 then return math.max(1, math.floor(seconds / 60)) .. " min old" end
    if seconds < 172800 then return math.floor(seconds / 3600) .. " h old" end
    return math.floor(seconds / 86400) .. " days old"
end

-- ---------------------------------------------------------------------------
-- Recording.
-- ---------------------------------------------------------------------------
-- Where the player harvests.
--
-- Every catch, vein, herb and looted corpse is a spot worth returning to.
-- The place the player was standing is kept, by kind and by zone, and these
-- spots are what a route is drawn from: they come before any position that
-- shipped with the addon, and in a zone the addon knows nothing about they
-- are the only source there is. Three spots make a route.
--
-- Standing in one place and fishing for an hour is one spot, not three
-- hundred: a harvest within about twenty-five yards of a known spot adds to
-- that spot's count. Eighty spots are kept per kind and zone; when that is
-- full the least-used one makes way.
local SPOT_GAP, SPOT_LIMIT = 0.006, 80      -- map fractions: about 25 yards in an ordinary zone
if type(db.spots) ~= "table" then db.spots = {} end

local function recordSpot(kind)
    if type(kind) ~= "string" or type(ns.PlayerSpot) ~= "function" then return end
    local here = ns.PlayerSpot()
    if type(here) ~= "table" or type(here.mapID) ~= "number" or type(here.x) ~= "number" or type(here.y) ~= "number" then return end
    if type(db.spots) ~= "table" then db.spots = {} end
    db.spots[kind] = type(db.spots[kind]) == "table" and db.spots[kind] or {}
    local list = db.spots[kind][here.mapID]
    if type(list) ~= "table" then list = {}; db.spots[kind][here.mapID] = list end
    for _, spot in ipairs(list) do
        local dx, dy = spot.x - here.x, spot.y - here.y
        if dx * dx + dy * dy <= SPOT_GAP * SPOT_GAP then
            spot.n = (spot.n or 1) + 1
            return
        end
    end
    if #list >= SPOT_LIMIT then
        local least = 1
        for index, spot in ipairs(list) do if (spot.n or 1) < (list[least].n or 1) then least = index end end
        table.remove(list, least)
    end
    list[#list + 1] = {x = here.x, y = here.y, n = 1}
    tracker.paceChanged = true                         -- A new spot: the farms are worked out again with it.
    tracker.changed = true
end

-- The spots the player has harvested at, most-used first.
function tracker.Spots(kind, mapID)
    local list = type(db.spots) == "table" and type(db.spots[kind]) == "table" and db.spots[kind][mapID]
    local out = {}
    for _, spot in ipairs(type(list) == "table" and list or {}) do
        if type(spot) == "table" and type(spot.x) == "number" and type(spot.y) == "number" then
            out[#out + 1] = {mapID = mapID, x = spot.x, y = spot.y, n = spot.n or 1}
        end
    end
    table.sort(out, function(a, b) if a.n ~= b.n then return a.n > b.n end if a.x ~= b.x then return a.x < b.x end return a.y < b.y end)
    return out
end

-- A session is one activity in one place.
--
-- Fishing for twenty minutes and then killing for twenty is two runs, and so
-- is killing in one zone and then in the next: mixed together they give a
-- gold-per-hour figure that describes neither, filed under whichever had
-- more loot. So when the loot changes kind or zone and stays changed, the
-- run so far is closed and saved, and a new one starts from the moment the
-- change began.
--
-- "Stays changed" matters. A mob that attacks while fishing, a vein mined
-- between kills, and skinning what was just killed are all part of the same
-- run. The change has to hold for five loots in a row, or two minutes,
-- before it counts; anything shorter is left where it is. Loot whose kind
-- is not known never starts a split.
local SPLIT_LOOTS, SPLIT_SECONDS = 5, 120
local streak

local function sessionKind() return state.runKind end
local function sessionZone() return state.runZone end

local function splitSession()
    local carry, now = streak, clock()
    streak = nil
    -- Take the new activity's loot back out of the run that is ending.
    for itemID, count in pairs(carry.items) do
        local left = (state.items[itemID] or 0) - count
        state.items[itemID] = left > 0 and left or nil
    end
    if carry.zone and state.zones[carry.zone] then
        local left = state.zones[carry.zone] - carry.pieces
        state.zones[carry.zone] = left > 0 and left or nil
    end
    if carry.kind and state.kinds[carry.kind] then
        local left = state.kinds[carry.kind] - carry.pieces
        state.kinds[carry.kind] = left > 0 and left or nil
    end
    state.loots = math.max(0, state.loots - carry.loots)
    local total, wall = state.active, state.lastLootWall
    state.active = math.max(0, carry.activeAt)          -- The old run ends where the change began.
    local before = {zone = state.runZone, kind = state.runKind, seconds = state.active}
    tracker.Stop()                                       -- Saved if it was a real one; the slate is clean.
    -- The new run starts with what was looted since the change.
    state.items, state.loots = carry.items, carry.loots
    state.zones, state.kinds, state.harvests = {}, {}, {}
    if carry.kind then state.harvests[carry.kind] = carry.loots end
    if carry.zone then state.zones[carry.zone] = carry.pieces end
    if carry.kind then state.kinds[carry.kind] = carry.pieces end
    state.runKind, state.runZone, state.zone = carry.kind, carry.zone, carry.zone
    state.active = math.max(0, total - carry.activeAt)
    state.lastLootWall = wall
    running, resumedAt, lastLoot = true, now, now
    tracker.changed = true
    if before.seconds >= HISTORY_MIN_SECONDS and type(ns.Print) == "function" then
        ns.Print("Farm session: your " .. string.lower(before.kind or "session") .. " in " .. tostring(before.zone or "the last zone")
            .. " is saved. Now counting " .. string.lower(carry.kind or "a new session") .. " in " .. tostring(carry.zone or "this zone") .. ".")
    end
end

function tracker.NoteActivity(itemID, count, kind, zone)
    if not kind or not zone then return end              -- Unknown: belongs to whatever is going on.
    if not state.runKind then state.runKind, state.runZone = kind, zone; return end
    if kind == state.runKind and zone == state.runZone then
        streak = nil                                     -- Back to the run: what came between was part of it.
        return
    end
    if not streak or streak.kind ~= kind or streak.zone ~= zone then
        streak = {kind = kind, zone = zone, items = {}, loots = 0, pieces = 0,
            activeAt = state.active, startedAt = clock()}
    end
    streak.items[itemID] = (streak.items[itemID] or 0) + count
    streak.loots, streak.pieces = streak.loots + 1, streak.pieces + count
    local now = clock()
    if streak.loots >= SPLIT_LOOTS or (now and streak.startedAt and now - streak.startedAt >= SPLIT_SECONDS and streak.loots >= 2) then
        splitSession()
    end
end

function tracker.AddItem(itemID, count)
    if not ns.GuideInteger(itemID, 2147483647) or itemID < 1 or not ns.GuideInteger(count, 100000) or count < 1 then return false end
    -- The window need not be open for the clock to be right: a long gap
    -- since the last loot is settled here, before this loot starts it again.
    tracker.Tick()
    if not running then
        if db.settings["gold.trackerAutoStart"] == false then return false end
        tracker.Start()
        if not running then return false end
    end
    checkpoint()
    local zone, kind = zoneName(), lootKind()
    state.items[itemID] = (state.items[itemID] or 0) + count
    state.loots = state.loots + 1
    lastLoot = clock() or lastLoot
    state.lastLootWall = wallClock() or state.lastLootWall
    if zone then state.zones[zone] = (state.zones[zone] or 0) + count end
    if kind then
        state.kinds[kind] = (state.kinds[kind] or 0) + count
        -- A harvest is one loot window: one catch, one vein, one corpse.
        if not pendingCounted then
            pendingCounted = true
            state.harvests[kind] = (state.harvests[kind] or 0) + 1
            recordSpot(kind)
        end
    end
    tracker.NoteActivity(itemID, count, kind, zone)
    tracker.changed = true
    return true
end

function tracker.AddCoin(copper)
    if not running or type(copper) ~= "number" or copper <= 0 then return false end
    checkpoint()
    state.coin = state.coin + copper
    lastLoot = clock() or lastLoot
    state.lastLootWall = wallClock() or state.lastLootWall
    tracker.changed = true
    return true
end

-- Does a chat line start the way one of the game's own-loot messages does?
local function ownLoot(message)
    for _, template in ipairs({LOOT_ITEM_SELF_MULTIPLE, LOOT_ITEM_SELF}) do
        if type(template) == "string" and ns.Public(template) then
            local prefix = string.match(template, "^(.-)%%s")
            if prefix and prefix ~= "" and string.sub(message, 1, #prefix) == prefix then return true end
        end
    end
    return false
end

local function onLootMessage(message)
    if not ns.Public(message) or type(message) ~= "string" or not ownLoot(message) then return end
    local itemID = tonumber(string.match(message, "|Hitem:(%d+):"))
    if not itemID then return end
    local count = tonumber(string.match(message, "|h|r%s*[xX](%d+)") or string.match(message, "%]%s*[xX](%d+)")) or 1
    tracker.AddItem(itemID, count)
end

-- "You loot 3 Silver, 20 Copper": the amounts next to the game's own words for each coin.
local function coinPattern(template)
    if type(template) ~= "string" or not ns.Public(template) then return nil end
    local escaped = string.gsub(template, "([%(%)%.%+%-%*%?%[%]%^%$])", "%%%1")
    return (string.gsub(escaped, "%%d", "(%%d+)"))
end
local function onMoneyMessage(message)
    if not ns.Public(message) or type(message) ~= "string" then return end
    local copper = 0
    for _, entry in ipairs({{GOLD_AMOUNT, 10000}, {SILVER_AMOUNT, 100}, {COPPER_AMOUNT, 1}}) do
        local pattern = coinPattern(entry[1])
        local amount = pattern and tonumber(string.match(message, pattern))
        if amount then copper = copper + amount * entry[2] end
    end
    if copper > 0 then tracker.AddCoin(copper) end
end

local function onExperience(unit)
    if unit ~= nil and unit ~= "player" then return end
    local xp, maximum = ns.ReadPublic(UnitXP, "player"), ns.ReadPublic(UnitXPMax, "player")
    if type(xp) ~= "number" or type(maximum) ~= "number" then return end
    local previous = lastXP
    lastXP = {xp = xp, maximum = maximum}
    if not running or not previous then return end
    local gained = xp >= previous.xp and xp - previous.xp or (previous.maximum - previous.xp) + xp
    if gained > 0 and gained <= previous.maximum then state.xp = state.xp + gained; tracker.changed = true end
end

-- Throws the session away: nothing is kept.
function tracker.Reset()
    tracker.Pause()
    state.items, state.active, state.coin, state.xp, state.loots, state.zone = {}, 0, 0, 0, 0, nil
    state.zones, state.kinds, state.lastLootWall, state.held = {}, {}, nil, nil
    state.harvests = {}
    state.runKind, state.runZone = nil, nil
    streak = nil
    lastLoot, lastXP = nil, nil
    tracker.idled = nil
    tracker.changed = true
end

-- Ends the session: it goes to Past sessions if it was a real one (five
-- minutes or more, worth something), and a new one can begin.
function tracker.Stop()
    tracker.Pause()
    local summary = tracker.Summary()
    if summary.seconds >= HISTORY_MIN_SECONDS and summary.total > 0 then
        local top = {}
        for index = 1, math.min(3, #summary.rows) do
            local row = summary.rows[index]
            top[index] = {itemID = row.itemID, name = row.name, count = row.count, value = row.value}
        end
        -- Every item with its count (the forty most numerous), so the session
        -- can be valued again at tomorrow's prices.
        local kept, order = {}, {}
        for _, row in ipairs(summary.rows) do order[#order + 1] = row end
        table.sort(order, function(a, b) if a.count ~= b.count then return a.count > b.count end return a.itemID < b.itemID end)
        for index = 1, math.min(40, #order) do kept[order[index].itemID] = order[index].count end
        table.insert(db.trackerHistory, 1, {zone = summary.zone or "Unknown", seconds = math.floor(summary.seconds),
            total = math.floor(summary.total), perHour = math.floor(summary.perHour), top = top,
            kind = summary.kind, items = kept, coin = math.floor(summary.coin),
            harvests = summary.kind and state.harvests[summary.kind] or nil,
            when = ns.ReadPublic(GetServerTime)})
        while #db.trackerHistory > HISTORY_KEPT do table.remove(db.trackerHistory) end
        tracker.paceChanged = true
    end
    state.items, state.active, state.coin, state.xp, state.loots, state.zone = {}, 0, 0, 0, 0, nil
    state.zones, state.kinds, state.lastLootWall, state.held = {}, {}, nil, nil
    state.harvests = {}
    state.runKind, state.runZone = nil, nil
    streak = nil
    lastLoot, lastXP = nil, nil
    tracker.idled = nil
    tracker.changed = true
end

-- The best hourly rate the player has recorded in a zone.
function tracker.BestFor(zone)
    local best
    for _, entry in ipairs(db.trackerHistory) do
        if entry.zone == zone and (not best or entry.perHour > best.perHour) then best = entry end
    end
    return best
end

-- What a past session is worth an hour at today's prices. A session saved
-- before item counts were kept is valued from its three top items, or its
-- old total if that is higher.
local function sessionRate(entry)
    if type(entry) ~= "table" or type(entry.seconds) ~= "number" or entry.seconds <= 0 then return 0 end
    local value = 0
    if type(entry.items) == "table" then
        for itemID, count in pairs(entry.items) do
            local copper = priceOf(itemID)
            if copper and type(count) == "number" then value = value + copper * count end
        end
        value = value + (type(entry.coin) == "number" and entry.coin or 0)
    else
        for _, item in ipairs(entry.top or {}) do
            local copper = item.itemID and priceOf(item.itemID)
            if copper and type(item.count) == "number" then value = value + copper * item.count end
        end
        value = math.max(value, entry.total or 0)
    end
    return value * 3600 / entry.seconds
end

-- The player's own farming, as farms: the best ten minutes or more they have
-- recorded in each zone for each kind, valued at today's prices. These are
-- measurements, not estimates, and they exist whether or not the farm data
-- knows the zone.
local OWN_MIN_SECONDS = 600
function tracker.OwnFarms()
    local best, list = {}, {}
    local function consider(zone, kind, seconds, rate, top, live)
        if type(zone) ~= "string" or seconds < OWN_MIN_SECONDS or rate <= 0 then return end
        local key = "own:" .. zone .. ":" .. tostring(kind or "any")
        if not best[key] or rate > best[key].estimate then
            best[key] = {key = key, own = true, zone = zone, category = kind, estimate = rate, measured = true,
                routable = false, minutes = math.floor(seconds / 60), live = live, topItems = top,
                name = kind and ("Your " .. string.lower(kind)) or "Your session"}
        end
    end
    for _, entry in ipairs(db.trackerHistory) do
        consider(entry.zone, entry.kind, entry.seconds or 0, sessionRate(entry), entry.top)
    end
    local summary = tracker.Summary()
    if summary.zone then
        local top = {}
        for index = 1, math.min(3, #summary.rows) do top[index] = {itemID = summary.rows[index].itemID, name = summary.rows[index].name, count = summary.rows[index].count} end
        consider(summary.zone, summary.kind, summary.seconds, summary.perHour, top, true)
    end
    for _, farm in pairs(best) do list[#list + 1] = farm end
    table.sort(list, function(a, b) if a.estimate ~= b.estimate then return a.estimate > b.estimate end return a.key < b.key end)
    return list
end

-- How many harvests this session has seen, of every kind. A farm's loop asks
-- this as the player reaches each stop, to learn whether the stop had anything.
function tracker.HarvestTotal()
    local total = 0
    for _, count in pairs(state.harvests) do if type(count) == "number" then total = total + count end end
    return total
end

-- The player's own pace at one kind of gathering: harvests an hour across
-- every session of that kind they have recorded, and the minutes behind it.
-- Farm estimates use this before any assumption. A session saved before
-- harvests were counted gives a pace only for fishing, where every item is
-- one catch.
function tracker.KindPace(kind)
    if type(kind) ~= "string" then return nil end
    local harvests, seconds = 0, 0
    local function add(sessionKind, count, items, duration)
        if sessionKind ~= kind or type(duration) ~= "number" or duration < OWN_MIN_SECONDS then return end
        if type(count) ~= "number" and kind == "Fishing" and type(items) == "table" then
            count = 0
            for _, pieces in pairs(items) do if type(pieces) == "number" then count = count + pieces end end
        end
        if type(count) == "number" and count > 0 then harvests, seconds = harvests + count, seconds + duration end
    end
    for _, entry in ipairs(db.trackerHistory) do add(entry.kind, entry.harvests, entry.items, entry.seconds) end
    add(mainKind(state.kinds), state.harvests[kind], state.items, tracker.Seconds())
    if seconds <= 0 then return nil end
    return harvests * 3600 / seconds, math.floor(seconds / 60)
end

-- The items worth scanning: this session's first, then recent sessions' top earners.
function tracker.ScanList()
    local ids, seen = {}, {}
    local function add(itemID)
        if type(itemID) == "number" and itemID > 0 and not seen[itemID] and #ids < 50 then seen[itemID] = true; ids[#ids + 1] = itemID end
    end
    local summary = tracker.Summary()
    table.sort(summary.rows, function(a, b) if a.count ~= b.count then return a.count > b.count end return a.itemID < b.itemID end)
    for _, row in ipairs(summary.rows) do if row.quality > 0 then add(row.itemID) end end
    for _, entry in ipairs(db.trackerHistory) do
        for _, item in ipairs(entry.top or {}) do add(item.itemID) end
    end
    return ids
end

-- ---------------------------------------------------------------------------
-- The window.
-- ---------------------------------------------------------------------------
local window, scanPanel
local colors = ns.UIColors or {}
local GOLD, TEXT, MUTED = colors.gold or {1, 0.82, 0.3, 1}, colors.text or {0.9, 0.9, 0.86, 1}, colors.muted or {0.68, 0.71, 0.75, 1}

-- A button too narrow for the usual side padding: centre its caption instead.
local function compact(button, size)
    button:SetSize(size, size)
    button.caption:ClearAllPoints(); button.caption:SetPoint("CENTER", 0, 0)
    return button
end

local function tile(parent, caption)
    local frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    ns.UIPanel(frame, colors.background)
    frame.value = ns.UILabel(frame, "GameFontNormalLarge", 17, GOLD)
    frame.value:SetPoint("TOP", 0, -8); frame.value:SetJustifyH("CENTER")
    frame.caption = ns.UILabel(frame, nil, 10, MUTED)
    frame.caption:SetPoint("BOTTOM", 0, 7); frame.caption:SetJustifyH("CENTER")
    frame.caption:SetText(caption)
    return frame
end

local function itemRow(parent, width)
    width = width or (WIDTH - 24)
    local row = CreateFrame("Frame", nil, parent)
    row.width = width
    row:SetSize(width, 22)
    -- A bar behind the row, as wide as the item's share of the best earner.
    row.bar = row:CreateTexture(nil, "BACKGROUND")
    row.bar:SetColorTexture(GOLD[1], GOLD[2], GOLD[3], 0.13)
    row.bar:SetPoint("TOPLEFT", 0, -1); row.bar:SetHeight(20)
    row.icon = row:CreateTexture(nil, "ARTWORK")
    row.icon:SetSize(18, 18); row.icon:SetPoint("LEFT", 2, 0)
    row.name = ns.UILabel(row, nil, 12)
    row.name:SetPoint("LEFT", 26, 0); row.name:SetWidth(width - 172); row.name:SetWordWrap(false)
    row.count = ns.UILabel(row, nil, 11, MUTED)
    row.count:SetPoint("RIGHT", -92, 0); row.count:SetWidth(50); row.count:SetJustifyH("RIGHT"); row.count:SetWordWrap(false)
    row.value = ns.UILabel(row, nil, 12, GOLD)
    row.value:SetPoint("RIGHT", -4, 0); row.value:SetWidth(84); row.value:SetJustifyH("RIGHT"); row.value:SetWordWrap(false)
    row:EnableMouse(true)
    row:SetScript("OnEnter", function(self)
        local data = self.data
        if not data or not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:AddLine(data.name, 1, 0.82, 0.3)
        GameTooltip:AddLine(data.count .. " looted" .. (data.each and (" • " .. tracker.Money(data.each) .. " each") or ""), 1, 1, 1)
        local seconds = tracker.Seconds()
        if seconds >= 30 then
            GameTooltip:AddLine(string.format("%.0f", data.count * 3600 / seconds) .. " per hour"
                .. (data.each and (" • " .. tracker.Rate(data.value * 3600 / seconds) .. " per hour") or ""), 1, 1, 1)
        end
        GameTooltip:AddLine(data.source == "auction" and ("Valued at an auction price: " .. tostring(data.label or "your scan") .. ".")
            or data.source == "vendor" and "Valued at what a vendor pays: no auction price is saved for it."
            or "No price known yet. Scan prices at an auction house.", 0.68, 0.71, 0.75, true)
        GameTooltip:Show()
    end)
    row:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    return row
end

local function savePosition(frame, store)
    frame:StopMovingOrSizing()
    local point, _, relative, x, y = frame:GetPoint(1)
    if type(point) == "string" and type(x) == "number" and type(y) == "number" then
        store.point, store.relative, store.x, store.y = point, relative, x, y
    end
end

local function restorePosition(frame, store, defaultPoint, defaultX, defaultY)
    frame:ClearAllPoints()
    if type(store.point) == "string" and type(store.x) == "number" and type(store.y) == "number" then
        frame:SetPoint(store.point, UIParent, store.relative or store.point, store.x, store.y)
    else
        frame:SetPoint(defaultPoint, UIParent, defaultPoint, defaultX, defaultY)
    end
end

local function create()
    if window then return window end
    window = CreateFrame("Frame", "WowTogetherFarmTracker", UIParent, "BackdropTemplate")
    tracker.window = window
    window:SetSize(WIDTH, 300); window:SetFrameStrata("MEDIUM"); window:SetClampedToScreen(true)
    window:SetMovable(true); window:EnableMouse(true); window:RegisterForDrag("LeftButton")
    window:SetScript("OnDragStart", window.StartMoving)
    window:SetScript("OnDragStop", function(self) savePosition(self, db.trackerWindow) end)
    restorePosition(window, db.trackerWindow, "RIGHT", -260, 60)
    ns.UIPanel(window)

    window.title = ns.UILabel(window, nil, 10, GOLD)
    window.title:SetPoint("TOPLEFT", 12, -11); window.title:SetText("FARM SESSION")
    window.clock = ns.UILabel(window, "GameFontNormal", 13)
    window.clock:SetPoint("LEFT", window.title, "RIGHT", 10, 0); window.clock:SetWordWrap(false)

    window.close = ns.UIClose(window, function() tracker.Hide() end)
    compact(window.close, 22); window.close:ClearAllPoints(); window.close:SetPoint("TOPRIGHT", -6, -6)
    window.fold = ns.UIButton(window, "–", 22, function()
        db.trackerWindow.collapsed = not db.trackerWindow.collapsed
        tracker.Refresh(true)
    end)
    compact(window.fold, 22); window.fold:SetPoint("RIGHT", window.close, "LEFT", -4, 0)
    ns.UIHelp(window.fold, "Fold the window down to one line, or open it again.")
    window.reset = ns.UIButton(window, "Reset", 50, function(self)
        -- Two clicks: the first arms it, the second within a few seconds does it.
        local now = clock() or 0
        if self.armedAt and now - self.armedAt < 4 then
            self.armedAt = nil; tracker.Reset(); tracker.Refresh(true)
        else
            self.armedAt = now; tracker.Refresh(true)
        end
    end)
    window.reset:SetHeight(22); window.reset:SetPoint("RIGHT", window.fold, "LEFT", -4, 0)
    ns.UIHelp(window.reset, "Throw this session away. Nothing is kept. Click twice.")
    window.stop = ns.UIButton(window, "Stop", 46, function()
        tracker.Stop(); tracker.Refresh(true)
    end)
    window.stop:SetHeight(22); window.stop:SetPoint("RIGHT", window.reset, "LEFT", -4, 0)
    ns.UIHelp(window.stop, "End this session. If it ran five minutes or more it is kept in Past sessions, and your next loot starts a new one.")
    window.toggle = ns.UIButton(window, "Pause", 58, function()
        if running then tracker.Pause(); state.held = true else tracker.Start() end
        tracker.Refresh(true)
    end)
    window.toggle:SetHeight(22); window.toggle:SetPoint("RIGHT", window.stop, "LEFT", -4, 0)

    window.body = CreateFrame("Frame", nil, window)
    window.body:SetPoint("TOPLEFT", 0, -COLLAPSED_HEIGHT); window.body:SetPoint("BOTTOMRIGHT", 0, 0)
    local body = window.body

    body.zone = ns.UILabel(body, nil, 11, MUTED)
    body.zone:SetPoint("TOPLEFT", 12, -2); body.zone:SetWidth(WIDTH - 24); body.zone:SetWordWrap(false)

    body.tiles = {tile(body, "GOLD PER HOUR"), tile(body, "TOTAL"), tile(body, "ITEMS PER HOUR")}
    local tileWidth = (WIDTH - 24 - 12) / 3
    for index, frame in ipairs(body.tiles) do
        frame:SetSize(tileWidth, 50)
        frame:SetPoint("TOPLEFT", 12 + (index - 1) * (tileWidth + 6), -22)
    end

    body.heading = ns.UILabel(body, nil, 10, GOLD)
    body.heading:SetPoint("TOPLEFT", 12, -82)
    body.side = ns.UILabel(body, nil, 10, MUTED)
    body.side:SetPoint("TOPRIGHT", -12, -82); body.side:SetJustifyH("RIGHT"); body.side:SetWordWrap(false)
    body.rows = {}
    for index = 1, ROWS do
        local row = itemRow(body)
        row:SetPoint("TOPLEFT", 12, -98 - (index - 1) * 23)
        body.rows[index] = row
    end
    body.more = ns.UILabel(body, nil, 11, MUTED)
    body.more:SetWidth(WIDTH - 24); body.more:SetWordWrap(false)
    body.empty = ns.UILabel(body, nil, 12, MUTED)
    body.empty:SetPoint("TOPLEFT", 12, -102); body.empty:SetWidth(WIDTH - 24); body.empty:SetWordWrap(true)

    body.split = ns.UILabel(body, nil, 11)
    body.split:SetWidth(WIDTH - 24); body.split:SetWordWrap(false)
    body.basis = ns.UILabel(body, nil, 10, MUTED)
    body.basis:SetWidth(WIDTH - 24); body.basis:SetWordWrap(true)

    body.history = ns.UIButton(body, "History", 70, function()
        window.showHistory = not window.showHistory
        tracker.Refresh(true)
    end)
    body.history:SetHeight(22)
    body.farms = ns.UIButton(body, "Farms", 62, function()
        if type(ns.OpenModulePage) == "function" then ns.OpenModulePage("Gold") end
    end)
    body.farms:SetHeight(22)
    ns.UIHelp(body.farms, "Open the Gold page: suggested farms, your sessions and prices.")

    -- The clock and the idle check, twice a second while the window is up.
    window:SetScript("OnUpdate", function(self, elapsed)
        self.elapsed = (self.elapsed or 0) + (type(elapsed) == "number" and elapsed or 0)
        if self.elapsed < 0.5 then return end
        self.elapsed = 0
        tracker.Tick()
        tracker.Refresh()
    end)
    return window
end

-- Stops the clock when nothing has been looted for a while, and ends the
-- session when the break is a long one.
--
-- The tracker counts all the time, not only during a chosen farm, so a
-- session has to end by itself or it becomes "everything since last week".
-- Half an hour without loot (measured on the wall clock, so it holds across
-- a logout) closes it: it goes to Past sessions if it was a real one, and
-- the next loot begins a new one. A session the player paused by hand is
-- theirs to resume and is left alone.
local ending = false
function tracker.Tick()
    local now = clock()
    if running and now and lastLoot and now - lastLoot >= IDLE_SECONDS then
        tracker.Pause(IDLE_GRACE)
        tracker.idled = true
        tracker.changed = true
    end
    local wall = wallClock()
    if not running and not ending and not state.held and wall and type(state.lastLootWall) == "number"
        and wall - state.lastLootWall >= SESSION_GAP then
        ending = true
        tracker.Stop()
        ending = false
        tracker.endedByItself = true
    end
end

local function farmEstimate()
    local farms = namespace.GoldFarms
    local session = farms and type(farms.ActiveSession) == "function" and farms.ActiveSession()
    if type(session) == "table" and type(session.estimate) == "number" and session.estimate > 0 then return session end
end

local lastDrawn
-- A newly kept session changes the player's pace, and with it every estimate that uses it.
local function recostFarms()
    if not tracker.paceChanged then return end
    tracker.paceChanged = nil
    local farms = namespace.GoldFarms
    if farms and type(farms.PricesChanged) == "function" then pcall(farms.PricesChanged) end
end

function tracker.Refresh(force)
    recostFarms()
    if not window or not window:IsShown() then return end
    local seconds = math.floor(tracker.Seconds())
    -- Counts change rarely; the clock every second. Redraw only what moved.
    local stamp = seconds .. ":" .. tostring(running) .. ":" .. tostring(window.showHistory) .. ":" .. tostring(db.trackerWindow.collapsed)
    if not force and not tracker.changed and stamp == lastDrawn then return end
    local summary = tracker.Summary()
    lastDrawn, tracker.changed = stamp, nil

    local collapsed = db.trackerWindow.collapsed == true
    window.clock:SetText(tracker.Clock(seconds) .. (collapsed and ("  •  " .. tracker.Rate(summary.perHour) .. "/h  •  " .. tracker.Money(summary.total)) or ""))
    window.clock:SetTextColor(unpack(running and TEXT or MUTED))
    window.toggle.caption:SetText(running and "Pause" or (seconds > 0 and "Resume" or "Start"))
    ns.UIButtonTone(window.toggle, not running)
    local now = clock() or 0
    local armed = window.reset.armedAt and now - window.reset.armedAt < 4
    if not armed then window.reset.armedAt = nil end
    window.reset.caption:SetText(armed and "Sure?" or "Reset")
    window.fold.caption:SetText(collapsed and "+" or "–")
    window.toggle:SetShown(not collapsed); window.reset:SetShown(not collapsed); window.stop:SetShown(not collapsed)
    local something = seconds > 0 or summary.total > 0
    window.stop:SetEnabled(something); window.reset:SetEnabled(something)
    window.body:SetShown(not collapsed)
    if collapsed then window:SetHeight(COLLAPSED_HEIGHT); return end

    local body = window.body
    local estimate = farmEstimate()
    local best = summary.zone and tracker.BestFor(summary.zone)
    local status = running and "" or (tracker.idled and "paused: nothing looted for five minutes" or (seconds > 0 and "paused" or "starts with your first loot"))
    body.zone:SetText((summary.zone or zoneName() or "No zone yet") .. (summary.kind and ("  •  " .. string.lower(summary.kind)) or "")
        .. (status ~= "" and ("  •  " .. status) or "")
        .. (estimate and ("  •  estimate " .. tracker.Rate(estimate.estimate) .. "/h") or "")
        .. (not estimate and best and ("  •  your best here " .. tracker.Rate(best.perHour) .. "/h") or ""))
    -- A rate needs half a minute of farming behind it before it means anything.
    local measured = summary.seconds >= 30
    body.tiles[1].value:SetText(measured and tracker.Rate(summary.perHour) or "–")
    body.tiles[2].value:SetText(summary.total > 0 and tracker.Money(summary.total) or "–")
    body.tiles[3].value:SetText(measured and tostring(math.floor(summary.piecesPerHour + 0.5)) or "–")

    local y
    if window.showHistory then
        body.heading:SetText("PAST SESSIONS")
        body.side:SetText(#db.trackerHistory .. " kept")
        for index, row in ipairs(body.rows) do
            local entry = db.trackerHistory[index]
            row.data = nil
            row:SetShown(entry ~= nil)
            if entry then
                local topRate = db.trackerHistory[1] and 1 or 1
                local highest = 0
                for _, other in ipairs(db.trackerHistory) do highest = math.max(highest, other.perHour or 0) end
                row.bar:SetWidth(math.max(2, (WIDTH - 24) * (highest > 0 and (entry.perHour or 0) / highest or 0)))
                row.icon:SetTexture(nil)
                row.name:ClearAllPoints(); row.name:SetPoint("LEFT", 6, 0); row.name:SetWidth(172)
                row.name:SetText(entry.zone); row.name:SetTextColor(unpack(TEXT))
                row.count:SetText(math.floor((entry.seconds or 0) / 60) .. " min")
                row.value:SetText(tracker.Rate(entry.perHour or 0) .. "/h")
            end
        end
        local shown = math.min(#db.trackerHistory, ROWS)
        body.empty:SetShown(shown == 0)
        body.empty:SetText("No past sessions yet. A session of five minutes or more is kept when you stop it.")
        body.more:Hide()
        y = -98 - math.max(shown, shown == 0 and 2 or 0) * 23
    else
        body.heading:SetText("TOP EARNERS")
        body.side:SetText(summary.xpPerHour > 0 and (string.format("%.1fk", summary.xpPerHour / 1000) .. " XP per hour") or "")
        local highest = summary.rows[1] and summary.rows[1].value or 0
        for index, row in ipairs(body.rows) do
            local data = summary.rows[index]
            row.data = data
            row:SetShown(data ~= nil)
            if data then
                row.bar:SetWidth(math.max(2, (WIDTH - 24) * (highest > 0 and data.value / highest or 0)))
                row.icon:SetTexture(data.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
                row.name:ClearAllPoints(); row.name:SetPoint("LEFT", 26, 0); row.name:SetWidth(152)
                local color = QUALITY[data.quality] or QUALITY[1]
                row.name:SetText(data.name); row.name:SetTextColor(color[1], color[2], color[3])
                row.count:SetText("×" .. data.count)
                row.value:SetText(data.each and tracker.Money(data.value) or "no price")
                row.value:SetTextColor(unpack(data.source == "auction" and GOLD or MUTED))
            end
        end
        local shown = math.min(#summary.rows, ROWS)
        body.empty:SetShown(shown == 0)
        body.empty:SetText("Nothing looted yet. Kill, mine, pick, skin or fish, and what you get is counted and valued here.")
        y = -98 - math.max(shown, shown == 0 and 2 or 0) * 23
        local hidden, hiddenValue = 0, 0
        for index = ROWS + 1, #summary.rows do hidden, hiddenValue = hidden + 1, hiddenValue + summary.rows[index].value end
        body.more:SetShown(hidden > 0)
        if hidden > 0 then
            body.more:ClearAllPoints(); body.more:SetPoint("TOPLEFT", 12, y - 2)
            body.more:SetText("…and " .. hidden .. " more worth " .. tracker.Money(hiddenValue))
            y = y - 18
        end
    end

    body.split:ClearAllPoints(); body.split:SetPoint("TOPLEFT", 12, y - 8)
    body.split:SetText("Auction " .. tracker.Money(summary.auction) .. "  •  Vendor " .. tracker.Money(summary.vendor)
        .. "  •  Coins " .. tracker.Money(summary.coin))
    local basis
    if summary.auctionKinds + summary.vendorKinds + summary.unpriced == 0 then
        basis = "Values use your last auction scan where there is one, and the vendor price otherwise."
    else
        basis = summary.auctionKinds .. (summary.auctionKinds == 1 and " item" or " items") .. " at auction price" .. sourcesText(summary.priceSources)
            .. (summary.oldestQuote and (" (oldest scan " .. ageText(summary.oldestQuote) .. ")") or "")
            .. ", " .. summary.vendorKinds .. " at vendor price"
            .. (summary.unpriced > 0 and (", " .. summary.unpriced .. " with no price") or "") .. "."
    end
    body.basis:ClearAllPoints(); body.basis:SetPoint("TOPLEFT", 12, y - 26)
    -- A note about the farm just started (it has no route, say) takes this line while it is current.
    local noted = tracker.note and (clock() or 0) < (tracker.noteUntil or 0)
    body.basis:SetText(noted and tracker.note or basis)
    body.basis:SetTextColor(unpack(noted and {1, 0.6, 0.3} or MUTED))
    body.history:ClearAllPoints(); body.history:SetPoint("TOPLEFT", 12, y - 56)
    body.history.caption:SetText(window.showHistory and "Session" or "History")
    body.farms:ClearAllPoints(); body.farms:SetPoint("LEFT", body.history, "RIGHT", 6, 0)
    window:SetHeight(COLLAPSED_HEIGHT + (-y) + 56 + 22 + 12)
end

function tracker.Show()
    create()
    db.trackerWindow.shown = true
    window:Show()
    tracker.Refresh(true)
end
function tracker.Hide()
    if window then window:Hide() end
    db.trackerWindow.shown = false
end
function tracker.Toggle()
    if window and window:IsShown() then tracker.Hide() else tracker.Show() end
end

-- ---------------------------------------------------------------------------
-- The price scan, at an auction house.
--
-- It reads what things sell for so that farms can be ranked by real prices
-- and a session valued at them. Three kinds of item go in, in this order:
-- what the player farmed, what they have seen drop, and what the farms near
-- their level drop according to the farm data. The last is what makes the
-- scan worth running before any farming has been done.
--
-- The core scans at most fifty items at a time, so the list is worked
-- through in batches, one after another, while the auction house stays open.
-- Items whose price is less than an hour old are left alone.
-- ---------------------------------------------------------------------------
local BATCH, FRESH_SECONDS, SCAN_LIMIT, FOUND_ROWS = 50, 3600, 300, 8
local scanState = {status = nil, total = 0, done = 0, priced = 0, running = false, queue = nil, found = {}, checked = {}}

-- Looked up within the hour: either it has a price that recent, or the scan
-- found nobody selling it. Neither needs asking again yet.
local function freshPrice(itemID)
    local copper, source, age = priceOf(itemID)
    if copper ~= nil and source == AUCTION and type(age) == "number" and age < FRESH_SECONDS then return true end
    if copper ~= nil and market(source) and source ~= AUCTION then return true end      -- Priced by another addon's database.
    local now, checked = clock(), scanState.checked[itemID]
    return now ~= nil and checked ~= nil and now - checked < FRESH_SECONDS
end

-- What a scan would cover now, and how much of each kind.
function tracker.ScanPlan()
    local ids, seen, groups = {}, {}, {farmed = 0, seen = 0, farms = 0}
    local function add(itemID, group)
        if type(itemID) ~= "number" or itemID <= 0 or seen[itemID] or #ids >= SCAN_LIMIT then return end
        local _, quality = itemFacts(itemID)
        if quality == 0 then return end                 -- Grey: a vendor buys it; nobody lists it.
        seen[itemID] = true
        groups[group] = groups[group] + 1
        if not freshPrice(itemID) then ids[#ids + 1] = itemID end
    end
    local summary = tracker.Summary()
    table.sort(summary.rows, function(a, b) if a.count ~= b.count then return a.count > b.count end return a.itemID < b.itemID end)
    for _, row in ipairs(summary.rows) do add(row.itemID, "farmed") end
    for _, entry in ipairs(db.trackerHistory) do
        for _, item in ipairs(entry.top or {}) do add(item.itemID, "farmed") end
    end
    local observations = namespace.GoldObservations
    if observations and type(observations.SeenItems) == "function" then
        for _, itemID in ipairs(observations.SeenItems(200)) do add(itemID, "seen") end
    end
    local farms = namespace.GoldFarms
    if farms and type(farms.ScanItems) == "function" then
        for _, itemID in ipairs(farms.ScanItems(SCAN_LIMIT)) do add(itemID, "farms") end
    end
    groups.total = groups.farmed + groups.seen + groups.farms
    groups.fresh = groups.total - #ids
    return ids, groups
end
-- Kept for callers that only want the list.
function tracker.ScanList() return (tracker.ScanPlan()) end

local function scanFinished(message)
    scanState.running, scanState.queue = false, nil
    scanState.status = message
    table.sort(scanState.found, function(a, b) if a.copper ~= b.copper then return a.copper > b.copper end return a.itemID < b.itemID end)
    -- New prices change which farm is best.
    local farms = namespace.GoldFarms
    if scanState.priced > 0 and farms and type(farms.PricesChanged) == "function" then farms.PricesChanged() end
    tracker.changed = true
    tracker.RefreshScan(); tracker.Refresh(true)
end

local function nextBatch(attempt)
    if not scanState.running or not scanState.queue then return end
    if #scanState.queue == 0 then
        scanFinished("Done: " .. scanState.priced .. " of " .. scanState.total .. " are for sale and now have a price."
            .. (scanState.priced < scanState.total and " The rest are not listed." or "") .. " Farms are ranked with them.")
        return
    end
    local batch = {}
    for index = 1, math.min(BATCH, #scanState.queue) do batch[index] = scanState.queue[index] end
    local remaining = #batch
    local okay, reason = ns.StartFarmCandidateScan(batch, function(row)
        scanState.done = scanState.done + 1
        remaining = remaining - 1
        if type(row) == "table" and type(row.itemID) == "number" then scanState.checked[row.itemID] = clock() end
        if type(row) == "table" and type(row.minBuyout) == "number" and row.minBuyout > 0 then
            scanState.priced = scanState.priced + 1
            scanState.found[#scanState.found + 1] = {itemID = row.itemID, copper = row.minBuyout}
        end
        scanState.status = "Scanning " .. scanState.done .. " of " .. scanState.total .. "…"
        if remaining <= 0 then
            for _ = 1, #batch do table.remove(scanState.queue, 1) end
            -- The core finishes its own bookkeeping after this call returns.
            ns.After("timer:GoldScan", 0.5, function() nextBatch(1) end)
        end
        tracker.RefreshScan()
    end)
    if okay == false then
        -- The previous batch may still be closing: try a few times before giving up.
        if (attempt or 1) < 6 and scanState.done > 0 then
            ns.After("timer:GoldScan", 1, function() nextBatch((attempt or 1) + 1) end)
            return
        end
        scanFinished(scanState.done > 0 and ("Stopped after " .. scanState.done .. " of " .. scanState.total .. ": " .. tostring(reason))
            or (type(reason) == "string" and reason or "The scan could not start."))
    end
end

function tracker.StartScan()
    if scanState.running then return false end
    local ids = tracker.ScanPlan()
    if #ids == 0 then return false end
    if type(ns.StartFarmCandidateScan) ~= "function" then
        scanState.status = "Price scanning is not available in this version."
        tracker.RefreshScan(); return false
    end
    scanState.running, scanState.queue, scanState.total, scanState.done, scanState.priced, scanState.found = true, ids, #ids, 0, 0, {}
    scanState.status = "Scanning 0 of " .. scanState.total .. "…"
    nextBatch(1)
    tracker.RefreshScan()
    return scanState.running
end

function tracker.StopScan(message)
    if scanState.full then
        if type(ns.StopFullPriceScan) == "function" then ns.StopFullPriceScan() end
        return
    end
    if not scanState.running then return end
    scanFinished(message or ("Stopped after " .. scanState.done .. " of " .. scanState.total .. "."))
end

-- The whole auction house, a category at a time: every listed item gets a
-- price, materials first. A couple of minutes; the player is asked first.
function tracker.FullScanAvailable()
    return type(ns.StartFullPriceScan) == "function" and type(ns.FullPriceScanSupported) == "function" and ns.FullPriceScanSupported() == true
end

function tracker.StartFullScan()
    if scanState.running then return false end
    scanState.confirming = nil
    local okay, reason = ns.StartFullPriceScan(function(progress)
        scanState.full = progress.running == true
        scanState.running = progress.running == true
        scanState.total, scanState.done = progress.categories or 0, math.max(0, (progress.category or 1) - (progress.running and 1 or 0))
        scanState.status = progress.running
            and ((progress.message or "Scanning…") .. "  " .. (progress.items or 0) .. " items so far.")
            or progress.message
        if not progress.running then
            scanState.found = {}
            local farms = namespace.GoldFarms
            if (progress.items or 0) > 0 and farms and type(farms.PricesChanged) == "function" then farms.PricesChanged() end
            tracker.changed = true
            tracker.Refresh(true)
        end
        tracker.RefreshScan()
    end)
    if okay == false then
        scanState.status = type(reason) == "string" and reason or "The scan could not start."
        tracker.RefreshScan()
        return false
    end
    return true
end

local function scanRow(parent)
    local row = CreateFrame("Frame", nil, parent)
    row:SetSize(WIDTH - 24, 20)
    row.icon = row:CreateTexture(nil, "ARTWORK")
    row.icon:SetSize(16, 16); row.icon:SetPoint("LEFT", 2, 0)
    row.name = ns.UILabel(row, nil, 12)
    row.name:SetPoint("LEFT", 24, 0); row.name:SetWidth(WIDTH - 24 - 24 - 90); row.name:SetWordWrap(false)
    row.price = ns.UILabel(row, nil, 12, GOLD)
    row.price:SetPoint("RIGHT", -2, 0); row.price:SetWidth(84); row.price:SetJustifyH("RIGHT"); row.price:SetWordWrap(false)
    return row
end

local function countLine(parent)
    local line = CreateFrame("Frame", nil, parent)
    line:SetSize(WIDTH - 24, 18)
    line.label = ns.UILabel(line, nil, 12); line.label:SetPoint("LEFT", 0, 0); line.label:SetWordWrap(false)
    line.count = ns.UILabel(line, nil, 12, GOLD); line.count:SetPoint("RIGHT", 0, 0); line.count:SetJustifyH("RIGHT")
    return line
end

function tracker.RefreshScan()
    if not scanPanel or not scanPanel:IsShown() then return end
    local ids, groups = tracker.ScanPlan()
    local atAuction = type(ns.AuctionHouseVisible) == "function" and ns.AuctionHouseVisible() == true
    local lines = {{"Dropped by farms near your level", groups.farms}, {"Seen dropping while you played", groups.seen},
        {"Farmed by you", groups.farmed}}
    local y = -50
    for index, line in ipairs(scanPanel.counts) do
        line:ClearAllPoints(); line:SetPoint("TOPLEFT", 12, y); y = y - 19
        line.label:SetText(lines[index][1]); line.count:SetText(tostring(lines[index][2]))
        line.label:SetTextColor(unpack(lines[index][2] > 0 and TEXT or MUTED))
    end
    y = y - 4
    scanPanel.plan:ClearAllPoints(); scanPanel.plan:SetPoint("TOPLEFT", 12, y)
    scanPanel.plan:SetText(groups.total == 0 and (tracker.FullScanAvailable()
            and "Nothing in particular to look up for this character. Scan everything prices the whole auction house."
            or "Nothing to price yet: the farm data has not been read for your level. Try again in a moment.")
        or (#ids == 0 and ("Nothing left to look up: all " .. groups.total .. " are priced or were checked in the last hour.")
            or (#ids .. " to look up" .. (groups.fresh > 0 and (", " .. groups.fresh .. " already priced or checked") or "") .. ".")))
    y = y - 22

    local fraction = scanState.total > 0 and math.min(1, scanState.done / scanState.total) or 0
    scanPanel.track:ClearAllPoints(); scanPanel.track:SetPoint("TOPLEFT", 12, y); scanPanel.track:SetSize(WIDTH - 24, 6)
    scanPanel.track:SetShown(scanState.total > 0)
    scanPanel.fill:SetWidth(math.max(1, (WIDTH - 24) * fraction)); scanPanel.fill:SetShown(scanState.total > 0)
    if scanState.total > 0 then y = y - 14 end
    scanPanel.status:ClearAllPoints(); scanPanel.status:SetPoint("TOPLEFT", 12, y)
    scanPanel.status:SetText(scanState.status or (atAuction and "Ready." or "Open an auction house to scan."))
    y = y - 34

    -- After a scan: the most valuable things it found.
    local found = #scanState.found
    scanPanel.foundHeading:SetShown(found > 0)
    if found > 0 then
        scanPanel.foundHeading:ClearAllPoints(); scanPanel.foundHeading:SetPoint("TOPLEFT", 12, y); y = y - 16
    end
    for index, row in ipairs(scanPanel.rows) do
        local entry = scanState.found[index]
        row:SetShown(entry ~= nil)
        if entry then
            local name, quality, icon = itemFacts(entry.itemID)
            local color = QUALITY[quality] or QUALITY[1]
            row:ClearAllPoints(); row:SetPoint("TOPLEFT", 12, y); y = y - 21
            row.icon:SetTexture(icon or "Interface\\Icons\\INV_Misc_QuestionMark")
            row.name:SetText(name); row.name:SetTextColor(color[1], color[2], color[3])
            row.price:SetText(tracker.Money(entry.copper) .. " each")
        end
    end
    if found > 0 then y = y - 6 end

    -- Two ways to scan: everything (when the client can), or just the gaps.
    local full = tracker.FullScanAvailable()
    scanPanel.everything:SetShown(full and not scanState.running and not scanState.confirming)
    scanPanel.confirm:SetShown(scanState.confirming == true)
    scanPanel.yes:SetShown(scanState.confirming == true); scanPanel.no:SetShown(scanState.confirming == true)
    if scanState.confirming then
        scanPanel.confirm:ClearAllPoints(); scanPanel.confirm:SetPoint("TOPLEFT", 12, y)
        scanPanel.yes:ClearAllPoints(); scanPanel.yes:SetPoint("TOPLEFT", 12, y - 54)
        scanPanel.no:ClearAllPoints(); scanPanel.no:SetPoint("LEFT", scanPanel.yes, "RIGHT", 8, 0)
        scanPanel.go:Hide(); scanPanel.note:Hide(); scanPanel.everythingNote:Hide()
        scanPanel:SetHeight(-y + 54 + 24 + 14)
        return
    end
    scanPanel.go:Show(); scanPanel.note:Show()
    if full and not scanState.running then
        scanPanel.everything:ClearAllPoints(); scanPanel.everything:SetPoint("TOPLEFT", 12, y)
        scanPanel.everything:SetEnabled(atAuction); ns.UIButtonTone(scanPanel.everything, atAuction)
        scanPanel.everythingNote:ClearAllPoints(); scanPanel.everythingNote:SetPoint("LEFT", scanPanel.everything, "RIGHT", 10, 0)
        scanPanel.everythingNote:Show()
        y = y - 32
    else
        scanPanel.everythingNote:Hide()
    end
    scanPanel.go:ClearAllPoints(); scanPanel.go:SetPoint("TOPLEFT", 12, y)
    local ready = atAuction and #ids > 0
    if scanState.running then
        scanPanel.go.caption:SetText("Stop"); scanPanel.go:SetEnabled(true); ns.UIButtonTone(scanPanel.go, false)
    else
        scanPanel.go.caption:SetText(#ids > 0 and ("Scan " .. #ids .. (#ids == 1 and " item" or " items")) or "Up to date")
        scanPanel.go:SetEnabled(ready); ns.UIButtonTone(scanPanel.go, ready and not full)
    end
    scanPanel.note:ClearAllPoints(); scanPanel.note:SetPoint("LEFT", scanPanel.go, "RIGHT", 10, 0)
    scanPanel.note:SetText(scanState.running and "Keep the auction house open."
        or (#ids > 0 and ((full and "Only what farms need: about " or "About ") .. math.max(1, math.ceil(#ids * 2 / 60)) .. " min.") or ""))
    scanPanel:SetHeight(-y + 24 + 14)
end

-- The auction window, asked of the core: the gold package does not reach
-- for the game's own frames itself.
local function auctionHost()
    if type(ns.AuctionHouseAnchor) ~= "function" then return nil end
    local host = ns.AuctionHouseAnchor()
    return type(host) == "table" and type(host.GetObjectType) == "function" and host or nil
end

function tracker.ShowScan()
    if not scanPanel then
        scanPanel = CreateFrame("Frame", "WowTogetherPriceScan", UIParent, "BackdropTemplate")
        tracker.scanPanel = scanPanel
        scanPanel:SetSize(WIDTH, 260); scanPanel:SetFrameStrata("HIGH"); scanPanel:SetClampedToScreen(true)
        scanPanel:SetMovable(true); scanPanel:EnableMouse(true); scanPanel:RegisterForDrag("LeftButton")
        scanPanel:SetScript("OnDragStart", scanPanel.StartMoving)
        scanPanel:SetScript("OnDragStop", function(self) db.scanWindow = db.scanWindow or {}; savePosition(self, db.scanWindow) end)
        ns.UIPanel(scanPanel)
        scanPanel.close = ns.UIClose(scanPanel)
        compact(scanPanel.close, 22); scanPanel.close:ClearAllPoints(); scanPanel.close:SetPoint("TOPRIGHT", -6, -6)
        scanPanel.title = ns.UILabel(scanPanel, nil, 10, GOLD)
        scanPanel.title:SetPoint("TOPLEFT", 12, -11); scanPanel.title:SetText("PRICE SCAN")
        scanPanel.sub = ns.UILabel(scanPanel, nil, 11, MUTED)
        scanPanel.sub:SetPoint("TOPLEFT", 12, -27); scanPanel.sub:SetWidth(WIDTH - 24); scanPanel.sub:SetWordWrap(false)
        local others = prices and prices.Sources and prices.Sources() or {}
        scanPanel.sub:SetText(#others > 0 and ("Fills the gaps " .. others[1] .. " has no price for.")
            or "Looks up what farm drops sell for, to rank farms by real prices.")
        scanPanel.counts = {countLine(scanPanel), countLine(scanPanel), countLine(scanPanel)}
        scanPanel.plan = ns.UILabel(scanPanel, nil, 11, MUTED)
        scanPanel.plan:SetWidth(WIDTH - 24); scanPanel.plan:SetWordWrap(true)
        scanPanel.track = scanPanel:CreateTexture(nil, "BACKGROUND")
        scanPanel.track:SetColorTexture(1, 1, 1, 0.08)
        scanPanel.fill = scanPanel:CreateTexture(nil, "ARTWORK")
        scanPanel.fill:SetColorTexture(GOLD[1], GOLD[2], GOLD[3], 0.9)
        scanPanel.fill:SetPoint("TOPLEFT", scanPanel.track, "TOPLEFT"); scanPanel.fill:SetHeight(6)
        scanPanel.status = ns.UILabel(scanPanel, nil, 12)
        scanPanel.status:SetWidth(WIDTH - 24); scanPanel.status:SetWordWrap(true)
        scanPanel.foundHeading = ns.UILabel(scanPanel, nil, 10, GOLD)
        scanPanel.foundHeading:SetText("WORTH MOST")
        scanPanel.rows = {}
        for index = 1, FOUND_ROWS do scanPanel.rows[index] = scanRow(scanPanel) end
        scanPanel.go = ns.UIButton(scanPanel, "Scan", 132, function()
            if scanState.running then tracker.StopScan() else tracker.StartScan() end
        end, true)
        scanPanel.go:SetHeight(24)
        scanPanel.note = ns.UILabel(scanPanel, nil, 10, MUTED)
        scanPanel.note:SetWidth(WIDTH - 24 - 142); scanPanel.note:SetWordWrap(true)
        scanPanel.everything = ns.UIButton(scanPanel, "Scan everything", 132, function()
            scanState.confirming = true; tracker.RefreshScan()
        end, true)
        scanPanel.everything:SetHeight(24)
        scanPanel.everythingNote = ns.UILabel(scanPanel, nil, 10, MUTED)
        scanPanel.everythingNote:SetWidth(WIDTH - 24 - 142); scanPanel.everythingNote:SetWordWrap(true)
        scanPanel.everythingNote:SetText("A price for every item listed. A couple of minutes.")
        scanPanel.confirm = ns.UILabel(scanPanel, nil, 12)
        scanPanel.confirm:SetWidth(WIDTH - 24); scanPanel.confirm:SetWordWrap(true)
        scanPanel.confirm:SetText("Scan the whole auction house? It takes a couple of minutes: materials first, then recipes, then weapons and armour. "
            .. "Stay at the auction house until it is done. Nothing is bought or sold.")
        scanPanel.yes = ns.UIButton(scanPanel, "Start scan", 110, function() tracker.StartFullScan() end, true)
        scanPanel.yes:SetHeight(24)
        scanPanel.no = ns.UIButton(scanPanel, "Not now", 90, function() scanState.confirming = nil; tracker.RefreshScan() end)
        scanPanel.no:SetHeight(24)
    end
    -- Beside the auction house unless the player has put it somewhere themselves.
    local host = auctionHost()
    if type(db.scanWindow) == "table" and type(db.scanWindow.point) == "string" then
        restorePosition(scanPanel, db.scanWindow, "CENTER", 320, 40)
    elseif host then
        scanPanel:ClearAllPoints(); scanPanel:SetPoint("TOPLEFT", host, "TOPRIGHT", 8, 0)
    else
        restorePosition(scanPanel, {}, "CENTER", 320, 40)
    end
    scanPanel:Show(); scanPanel:Raise()
    tracker.RefreshScan()
end

-- ---------------------------------------------------------------------------
-- The Gold page in the main window: the session, the farms to try, the
-- prices and the past sessions, each with its own buttons.
-- ---------------------------------------------------------------------------
local PAGE_ROWS, PAGE_FARMS, PAGE_HISTORY = 8, 5, 4      -- PAGE_FARMS: how many farms are visible at once
local FARM_LIST, FARM_ROW = 40, 50                        -- how many can be scrolled through; one row's height
local FARM_FILTERS = {{nil, "Best"}, {"Killing", "Killing"}, {"Mining", "Mining"}, {"Herbalism", "Herbs"},
    {"Skinning", "Skinning"}, {"Fishing", "Fishing"}}

local function section(page, text)
    local label = ns.UILabel(page, nil, 10, GOLD)
    label:SetText(text)
    return label
end

local function percent(chance)
    local value = (chance or 0) * 100
    if value >= 10 then return string.format("%d%%", math.floor(value + 0.5)) end
    if value >= 1 then return string.format("%.1f%%", value) end
    return string.format("%.2f%%", value)
end

-- What to call a farm. The farm data names a fishing farm after its skill
-- band ("Water tier 4"), which says nothing to a player: it is fishing.
function tracker.FarmTitle(farm)
    if farm.category == "Fishing" and not farm.own then return "Fishing" end
    return farm.name
end

-- One line under a farm's name: how far it can be trusted, in three words.
-- How much of what a fishing zone gives the farm data accounts for: the sum
-- of its fish's chances. Well under a whole means fish are missing from the
-- list, and the estimate is too low by about that much.
function tracker.FishCoverage(farm)
    if farm.category ~= "Fishing" or farm.own then return nil end
    if type(farm.chanceCoverage) == "number" then return farm.chanceCoverage end
    if type(farm.top) ~= "table" then return nil end
    local total = 0
    for _, item in ipairs(farm.top) do
        if type(item.chance) == "number" then total = total + item.chance end
    end
    return total
end

function tracker.FarmBasis(farm, withKind)
    local coverage = tracker.FishCoverage(farm)
    local data = farm.mine and ("your results, " .. farm.mine.minutes .. " min")
        or (farm.measured and "your results" or (coverage and coverage < 0.7 and "partial farm data" or "farm data"))
    local mine = farm.ownSpots or 0
    local route
    if farm.routable then
        route = farm.knownSpots and farm.knownSpots > 0 and ("loop, " .. farm.knownSpots .. " known spots" .. (mine > 0 and (", " .. mine .. " yours") or ""))
            or (mine > 0 and ("loop, " .. mine .. " spots of yours") or "loop")
    else
        route = mine > 0 and ("no route yet, " .. mine .. " of 3 spots found") or "no route"
    end
    return (withKind and farm.category and (farm.category .. "  •  ") or "") .. route .. "  •  " .. data
        .. "  •  " .. ((farm.auctionPriced or 0) > 0 and "auction prices" or "vendor prices")
end

-- What a farm's estimate rests on, short enough to read: the pace, the few
-- items that make up most of it, and where its prices came from.
function tracker.FarmTooltip(owner, farm)
    if not GameTooltip then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    if farm.own then
        GameTooltip:AddLine(farm.name, 1, 0.82, 0.3)
        GameTooltip:AddLine(farm.zone, 1, 1, 1)
        GameTooltip:AddLine(" ")
        GameTooltip:AddDoubleLine("You made", tracker.Rate(farm.estimate or 0) .. " an hour", 0.68, 0.71, 0.75, 1, 0.82, 0.3)
        GameTooltip:AddDoubleLine("Measured over", farm.minutes .. " min", 0.68, 0.71, 0.75, 1, 1, 1)
        for _, item in ipairs(farm.topItems or {}) do
            if item.itemID then
                local name, quality, icon = itemFacts(item.itemID)
                local color = QUALITY[quality] or QUALITY[1]
                GameTooltip:AddDoubleLine((icon and ("|T" .. tostring(icon) .. ":14|t ") or "") .. name, "×" .. tostring(item.count or "?"),
                    color[1], color[2], color[3], 1, 1, 1)
            end
        end
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine("Your own result, valued at today's prices. Track counts a new session here; there is no route to follow.", 0.68, 0.71, 0.75, true)
        GameTooltip:Show()
        return
    end
    GameTooltip:AddLine(tracker.FarmTitle(farm), 1, 0.82, 0.3)
    GameTooltip:AddLine(farm.zone .. (farm.profession and farm.profession ~= tracker.FarmTitle(farm) and ("  •  " .. farm.profession) or ""), 1, 1, 1)
    GameTooltip:AddLine(" ")
    if farm.mine then
        -- Joined with the player's own session here: what they made and looted, on the data's route.
        GameTooltip:AddDoubleLine("You made", tracker.Rate(farm.estimate or 0) .. " an hour", 0.68, 0.71, 0.75, 1, 0.82, 0.3)
        GameTooltip:AddDoubleLine("Measured over", farm.mine.minutes .. " min" .. (farm.mine.live and ", this session" or ""), 0.68, 0.71, 0.75, 1, 1, 1)
        for _, item in ipairs(farm.mine.topItems or {}) do
            if item.itemID then
                local name, quality, icon = itemFacts(item.itemID)
                local color = QUALITY[quality] or QUALITY[1]
                GameTooltip:AddDoubleLine((icon and ("|T" .. tostring(icon) .. ":14|t ") or "") .. name, "×" .. tostring(item.count or "?"),
                    color[1], color[2], color[3], 1, 1, 1)
            end
        end
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine("Your own result, valued at today's prices. The farm data alone put this at "
            .. tracker.Rate(farm.dataEstimate or 0) .. " an hour.", 0.68, 0.71, 0.75, true)
        GameTooltip:AddLine(farm.routable and (farm.seededRoute
                and ("Start leads you round the best of the " .. tostring(farm.knownSpots or "known") .. " known spots here and counts your session.")
                or "Start leads you round a loop and counts your session.")
            or "No route: no spots are known in this zone. Track counts your session while you work it, and the spots you find become a route.", 1, 0.6, 0.3, true)
        GameTooltip:Show()
        return
    end
    GameTooltip:AddDoubleLine("Estimate", tracker.Rate(farm.estimate or 0) .. " an hour", 0.68, 0.71, 0.75, 1, 0.82, 0.3)
    if farm.pace then
        GameTooltip:AddDoubleLine("Pace", math.floor(farm.pace + 0.5) .. " " .. (farm.paceUnit or "kills") .. " an hour"
            .. (farm.paceAssumed and ", assumed" or ", yours"), 0.68, 0.71, 0.75, 1, 1, 1)
    end
    if farm.top and #farm.top > 0 then
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine("Worth most", 1, 0.82, 0.3)
        for _, item in ipairs(farm.top) do
            local name, quality, icon = itemFacts(item.itemID)
            local color = QUALITY[quality] or QUALITY[1]
            GameTooltip:AddDoubleLine((icon and ("|T" .. tostring(icon) .. ":14|t ") or "") .. name,
                percent(item.chance) .. "  •  " .. (item.each and tracker.Money(item.each) or "no price"),
                color[1], color[2], color[3], 1, 1, 1)
        end
        if (farm.others or 0) > 0 then
            GameTooltip:AddLine("and " .. farm.others .. " other " .. (farm.others == 1 and "drop" or "drops"), 0.68, 0.71, 0.75)
        end
    end
    GameTooltip:AddLine(" ")
    local priced = (farm.auctionPriced or 0) + (farm.vendorPriced or 0)
    GameTooltip:AddLine((farm.auctionPriced or 0) == 0
        and "Priced at vendor value only. Run a price scan at an auction house to rank it by what it really sells for."
        or ((farm.auctionPriced or 0) .. " of " .. priced .. " prices are from your auction scan."), 0.68, 0.71, 0.75, true)
    GameTooltip:AddLine(farm.measured and "Based on your own results here." or "From the farm data. Not yet confirmed by your own play.", 0.68, 0.71, 0.75, true)
    local coverage = tracker.FishCoverage(farm)
    if coverage and coverage < 0.7 then
        GameTooltip:AddLine("The farm data only lists fish for " .. math.floor(coverage * 100 + 0.5) .. "% of catches here, so this is too low. Fish here for ten minutes and your own result replaces it.", 1, 0.6, 0.3, true)
    end
    local farmsPart = namespace.GoldFarms
    local plan = farm.routable and not farm.own and farmsPart and type(farmsPart.LoopPlan) == "function" and farmsPart.LoopPlan(farm.key) or nil
    if plan and plan.seconds and plan.seconds > 0 then
        local lap = plan.lapSeconds or plan.seconds
        GameTooltip:AddDoubleLine("Lap", plan.stops .. " of " .. plan.available .. " spots, about " .. math.max(1, math.floor(lap / 60 + 0.5)) .. " min", 0.68, 0.71, 0.75, 1, 1, 1)
        if plan.respawn then
            local minutes = math.floor(plan.respawn / 60 * 10 + 0.5) / 10
            GameTooltip:AddLine("Sized so a spot is back when you return to it: about " .. minutes .. " min to come back, "
                .. tostring(plan.respawnNote or "assumed") .. ".", 0.68, 0.71, 0.75, true)
            if plan.short then
                GameTooltip:AddLine("Every known spot is in the loop and a lap is still " .. math.floor(plan.short / 60 + 0.5)
                    .. " min shorter than that: expect some empty spots.", 1, 0.6, 0.3, true)
            end
        end
    end
    if farm.routable and farm.seededRoute then
        GameTooltip:AddLine("Start leads you round the best of the " .. tostring(farm.knownSpots or "known")
            .. " known spots here. They come from older data and are not yet confirmed: spots you harvest at replace them.", 0.68, 0.71, 0.75, true)
    else
    if farm.routable then
        GameTooltip:AddLine("Start route draws the loop on your map and leads you round it.", 0.68, 0.71, 0.75, true)
    else
        GameTooltip:AddLine("No route: no spots are known in this zone, so there is nothing to draw. Track counts your session while you work it, and the spots you find become a route.", 1, 0.6, 0.3, true)
    end
    end
    GameTooltip:Show()
end

local function farmRow(parent, width, page)
    page = page or parent
    local row = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    row:SetSize(width, 46)
    ns.UIPanel(row, colors.background)
    row.name = ns.UILabel(row, nil, 13)
    row.name:SetPoint("TOPLEFT", 10, -7); row.name:SetWidth(width - 92); row.name:SetWordWrap(false)
    row.estimate = ns.UILabel(row, nil, 12, GOLD)
    row.estimate:SetPoint("TOPLEFT", 10, -26); row.estimate:SetWidth(62); row.estimate:SetWordWrap(false)
    row.basis = ns.UILabel(row, nil, 10, MUTED)
    row.basis:SetPoint("TOPLEFT", 74, -27); row.basis:SetWidth(width - 74 - 84); row.basis:SetWordWrap(false)
    row:EnableMouse(true)
    row:SetScript("OnEnter", function(self) if self.farm then tracker.FarmTooltip(self, self.farm) end end)
    row:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    row.go = ns.UIButton(row, "Start", 84, function(self)
        local farms = namespace.GoldFarms
        if self.own then
            -- One of the player's own: there is no route to give, only the session to count.
            if not running then tracker.Start() end
            tracker.Show()
            if page.goldPage then tracker.RenderPage(page) end
            return
        end
        if not farms or not self.key then return end
        if self.active then farms.Stop("stopped by player") else farms.Start(self.key) end
        if not self.active and not self.routable then
            tracker.note = "No route: no spots are known in " .. tostring(self.zone or "this zone") .. ". "
                .. "Go there and work wherever you like; this counts it, and the spots you find become a route."
            tracker.noteUntil = (clock() or 0) + 600
            ns.Print(tracker.note)
        else
            tracker.note = nil
        end
        tracker.changed = true
        if page.goldPage then tracker.RenderPage(page) end
        tracker.Refresh(true)
    end)
    row.go:SetHeight(26); row.go:SetPoint("RIGHT", -8, 0)
    return row
end

local function buildPage(page, width)
    local view = {width = width}
    view.title = ns.UILabel(page, nil, 10, GOLD); view.title:SetText("FARM SESSION")
    view.clock = ns.UILabel(page, "GameFontNormalLarge", 18)
    view.zone = ns.UILabel(page, nil, 11, MUTED); view.zone:SetWordWrap(false)
    view.toggle = ns.UIButton(page, "Start", 76, function()
        if running then tracker.Pause(); state.held = true else tracker.Start() end
        tracker.RenderPage(page); tracker.Refresh(true)
    end)
    view.reset = ns.UIButton(page, "Reset", 64, function(self)
        local now = clock() or 0
        if self.armedAt and now - self.armedAt < 4 then self.armedAt = nil; tracker.Reset() else self.armedAt = now end
        tracker.RenderPage(page); tracker.Refresh(true)
    end)
    ns.UIHelp(view.reset, "Throw this session away. Nothing is kept. Click twice.")
    view.stop = ns.UIButton(page, "Stop", 64, function()
        tracker.Stop(); tracker.RenderPage(page); tracker.Refresh(true)
    end)
    ns.UIHelp(view.stop, "End this session. If it ran five minutes or more it is kept under Past sessions, and your next loot starts a new one.")
    view.window = ns.UIButton(page, "Show on screen", 124, function()
        tracker.Toggle(); tracker.RenderPage(page)
    end, true)
    ns.UIHelp(view.window, "Keep the farm session on screen as a small window while you play.")
    view.tiles = {tile(page, "GOLD PER HOUR"), tile(page, "TOTAL"), tile(page, "ITEMS PER HOUR"), tile(page, "XP PER HOUR")}
    view.earners = section(page, "TOP EARNERS")
    -- Two columns: what you earned on the left, what to try on the right.
    view.left = math.floor((width - 16) * 0.48)
    view.right = width - 16 - view.left
    view.rows = {}
    for index = 1, PAGE_ROWS do view.rows[index] = itemRow(page, view.left) end
    view.empty = ns.UILabel(page, nil, 12, MUTED); view.empty:SetWidth(view.left); view.empty:SetWordWrap(true)
    view.more = ns.UILabel(page, nil, 11, MUTED); view.more:SetWordWrap(false)
    view.split = ns.UILabel(page, nil, 11); view.split:SetWordWrap(false)
    view.basis = ns.UILabel(page, nil, 10, MUTED); view.basis:SetWidth(width); view.basis:SetWordWrap(true)
    view.farmsHeading = section(page, "FARMS TO TRY")
    view.farmsNote = ns.UILabel(page, nil, 11, MUTED); view.farmsNote:SetWidth(view.right); view.farmsNote:SetWordWrap(true)
    -- The farms scroll inside their own window: five are visible, the rest
    -- are a turn of the mouse wheel away, best first.
    view.farmScroll = CreateFrame("ScrollFrame", nil, page)
    view.farmChild = CreateFrame("Frame", nil, view.farmScroll)
    view.farmChild:SetSize(view.right, FARM_ROW)
    view.farmScroll:SetScrollChild(view.farmChild)
    view.farmOffset = 0
    view.farmScroll:EnableMouseWheel(true)
    view.farmScroll:SetScript("OnMouseWheel", function(_, delta)
        tracker.ScrollFarms(page, -(tonumber(delta) or 0))
    end)
    view.farmBar = page:CreateTexture(nil, "BACKGROUND"); view.farmBar:SetColorTexture(1, 1, 1, 0.07)
    view.farmThumb = page:CreateTexture(nil, "ARTWORK"); view.farmThumb:SetColorTexture(GOLD[1], GOLD[2], GOLD[3], 0.7)
    view.farmCount = ns.UILabel(page, nil, 10, MUTED); view.farmCount:SetJustifyH("RIGHT"); view.farmCount:SetWordWrap(false)
    view.farms = {}
    -- One chip per kind of farm: the best of everything, killing, and each gathering profession.
    view.chips = {}
    for index, entry in ipairs(FARM_FILTERS) do
        local chip = ns.UIButton(page, entry[2], 8 + #entry[2] * 7 + 12, function(self)
            if self.count == 0 then return end
            db.settings["gold.farmKind"] = self.category or false
            tracker.changed = true
            tracker.RenderPage(page)
        end)
        chip:SetHeight(20); chip.category, chip.title = entry[1], entry[2]
        chip.caption:ClearAllPoints(); chip.caption:SetPoint("CENTER", 0, 0)
        chip:HookScript("OnEnter", function(self)
            if not GameTooltip then return end
            GameTooltip:SetOwner(self, "ANCHOR_TOP")
            GameTooltip:AddLine(self.category and (self.category .. " farms") or "The best farms of every kind", 1, 0.82, 0.3)
            GameTooltip:AddLine(self.count == 0 and "None yet. The farm data has no rates for this kind, and you have not recorded ten minutes of it. Do some, and it appears here."
                or (self.count .. (self.count == 1 and " farm" or " farms") .. " for your level."), 0.68, 0.71, 0.75, true)
            GameTooltip:Show()
        end)
        chip:HookScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
        view.chips[index] = chip
    end
    view.historyHeading = section(page, "PAST SESSIONS")
    view.historyNote = ns.UILabel(page, nil, 11, MUTED); view.historyNote:SetWidth(width); view.historyNote:SetWordWrap(true)
    view.history = {}
    for index = 1, PAGE_HISTORY do view.history[index] = itemRow(page, width) end
    -- A live clock while the page is open.
    page:SetScript("OnUpdate", function(self, elapsed)
        self.goldElapsed = (self.goldElapsed or 0) + (type(elapsed) == "number" and elapsed or 0)
        if self.goldElapsed < 1 then return end
        self.goldElapsed = 0
        if self:IsShown() then tracker.RenderPage(self, true) end
    end)
    return view
end

function tracker.RenderPage(page, clockOnly)
    recostFarms()
    local measuredWidth = page:GetWidth()
    local width = math.max(420, math.min(860, (type(measuredWidth) == "number" and measuredWidth > 0 and measuredWidth or 584) - 32))
    if not page.goldPage or page.goldPage.width ~= width then
        if page.goldPage then return end      -- Built for another width: keep what is there; it is rebuilt on reload.
        page.goldPage = buildPage(page, width)
    end
    local view, left = page.goldPage, 16
    local summary = tracker.Summary()
    local seconds = math.floor(summary.seconds)
    view.clock:SetText(tracker.Clock(seconds))
    view.clock:SetTextColor(unpack(running and TEXT or MUTED))
    if clockOnly and not tracker.changed and view.drawnRunning == running then return end
    view.drawnRunning = running

    view.title:ClearAllPoints(); view.title:SetPoint("TOPLEFT", left, -14)
    view.clock:ClearAllPoints(); view.clock:SetPoint("TOPLEFT", left, -28)
    local estimate = farmEstimate()
    local best = summary.zone and tracker.BestFor(summary.zone)
    local status = running and "running" or (tracker.idled and "paused: nothing looted for five minutes" or (seconds > 0 and "paused" or "starts with your first loot"))
    view.zone:ClearAllPoints(); view.zone:SetPoint("TOPLEFT", left, -52); view.zone:SetWidth(width - 20)
    view.zone:SetText((summary.zone or zoneName() or "No zone yet") .. (summary.kind and ("  •  " .. string.lower(summary.kind)) or "") .. "  •  " .. status
        .. (estimate and ("  •  estimate " .. tracker.Rate(estimate.estimate) .. "/h") or "")
        .. (not estimate and best and ("  •  your best here " .. tracker.Rate(best.perHour) .. "/h") or ""))
    view.window:ClearAllPoints(); view.window:SetPoint("TOPRIGHT", page, "TOPLEFT", left + width, -22)
    view.window.caption:SetText(window and window:IsShown() and "Hide from screen" or "Show on screen")
    view.reset:ClearAllPoints(); view.reset:SetPoint("RIGHT", view.window, "LEFT", -6, 0)
    local now = clock() or 0
    local armed = view.reset.armedAt and now - view.reset.armedAt < 4
    if not armed then view.reset.armedAt = nil end
    view.reset.caption:SetText(armed and "Sure?" or "Reset")
    view.stop:ClearAllPoints(); view.stop:SetPoint("RIGHT", view.reset, "LEFT", -6, 0)
    view.toggle:ClearAllPoints(); view.toggle:SetPoint("RIGHT", view.stop, "LEFT", -6, 0)
    local something = seconds > 0 or summary.total > 0
    view.stop:SetEnabled(something); view.reset:SetEnabled(something)
    view.toggle.caption:SetText(running and "Pause" or (seconds > 0 and "Resume" or "Start"))

    local measured = summary.seconds >= 30
    local tileWidth = (width - 18) / 4
    local values = {measured and tracker.Rate(summary.perHour) or "–", summary.total > 0 and tracker.Money(summary.total) or "–",
        measured and tostring(math.floor(summary.piecesPerHour + 0.5)) or "–",
        measured and summary.xpPerHour > 0 and string.format("%.1fk", summary.xpPerHour / 1000) or "–"}
    for index, frame in ipairs(view.tiles) do
        frame:ClearAllPoints(); frame:SetSize(tileWidth, 50)
        frame:SetPoint("TOPLEFT", left + (index - 1) * (tileWidth + 6), -74)
        frame.value:SetText(values[index])
    end

    -- Left column: top earners.
    local top = -138
    local y = top
    view.earners:ClearAllPoints(); view.earners:SetPoint("TOPLEFT", left, y); y = y - 16
    local highest = summary.rows[1] and summary.rows[1].value or 0
    for index, row in ipairs(view.rows) do
        local data = summary.rows[index]
        row.data = data
        row:SetShown(data ~= nil)
        if data then
            row:ClearAllPoints(); row:SetPoint("TOPLEFT", left, y); y = y - 23
            row.bar:SetWidth(math.max(2, view.left * (highest > 0 and data.value / highest or 0)))
            row.icon:SetTexture(data.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
            local color = QUALITY[data.quality] or QUALITY[1]
            row.name:SetText(data.name); row.name:SetTextColor(color[1], color[2], color[3])
            row.count:SetText("×" .. data.count)
            row.value:SetText(data.each and tracker.Money(data.value) or "no price")
            row.value:SetTextColor(unpack(data.source == "auction" and GOLD or MUTED))
        end
    end
    view.empty:SetShown(#summary.rows == 0)
    if #summary.rows == 0 then
        view.empty:ClearAllPoints(); view.empty:SetPoint("TOPLEFT", left, y - 2)
        view.empty:SetText("Nothing looted yet. Kill, mine, pick, skin or fish, and what you get is counted and valued here.")
        y = y - 52
    end
    local hidden, hiddenValue = 0, 0
    for index = PAGE_ROWS + 1, #summary.rows do hidden, hiddenValue = hidden + 1, hiddenValue + summary.rows[index].value end
    view.more:SetShown(hidden > 0)
    if hidden > 0 then
        view.more:ClearAllPoints(); view.more:SetPoint("TOPLEFT", left, y - 2)
        view.more:SetText("…and " .. hidden .. " more worth " .. tracker.Money(hiddenValue))
        y = y - 18
    end
    local leftBottom = y

    -- Right column: farms to try.
    local farms = namespace.GoldFarms
    local counts = farms and type(farms.Categories) == "function" and farms.Categories() or {}
    local chosen = db.settings["gold.farmKind"] or nil
    local own = tracker.OwnFarms()
    for _, farm in ipairs(own) do
        if farm.category and counts[farm.category] ~= nil then counts[farm.category] = counts[farm.category] + 1 end
    end
    -- Only now, with the player's own farms counted, can a kind be called empty.
    if chosen and (counts[chosen] or 0) == 0 then chosen = nil end
    local suggestions, problem = {}, nil
    if farms and type(farms.Suggestions) == "function" then suggestions, problem = farms.Suggestions(FARM_LIST, chosen) end
    -- The player's own results go in with the data's, best first.
    --
    -- Where the farm data has exactly one farm of the same kind in the same
    -- zone as one of the player's own, they are the same farm and are shown
    -- as one: the player's measured rate and what they actually looted, on
    -- the data's route. (Fishing is one farm per zone, so it always joins.
    -- Killing is one farm per creature, so a zone's kills do not belong to
    -- any single one and stay separate.)
    local place, joined = {}, {}
    for _, farm in ipairs(suggestions) do
        local key = tostring(farm.category) .. "|" .. tostring(farm.zone)
        if place[key] == nil then place[key] = farm else place[key] = false end
    end
    for _, mine in ipairs(own) do
        local match = mine.category and place[mine.category .. "|" .. mine.zone]
        if match and not match.mine then
            match.mine, match.dataEstimate = mine, match.estimate
            match.estimate, match.measured = mine.estimate, true
            joined[mine] = true
        end
    end
    local merged = {}
    for _, farm in ipairs(suggestions) do merged[#merged + 1] = farm end
    for _, farm in ipairs(own) do
        if not joined[farm] and (chosen == nil or farm.category == chosen) then merged[#merged + 1] = farm end
    end
    -- The player's own results come first in spirit: a rate they measured
    -- is a fact, a rate from the farm data is a guess built on an assumed
    -- pace. So for ordering, a guess counts for six tenths of its figure
    -- (nine tenths once the pace is the player's own). The figure shown is
    -- not changed. A measured 8g an hour therefore sits above an estimated
    -- 12g, but not above an estimated 20g: the data still gets to point at
    -- something clearly better than anything tried so far.
    local function standing(farm)
        local rate = farm.estimate or 0
        if farm.own or farm.mine then return rate end
        return rate * (farm.paceAssumed == false and 0.9 or 0.6)
    end
    table.sort(merged, function(a, b)
        local x, y = standing(a), standing(b)
        if x ~= y then return x > y end
        return tostring(a.key) < tostring(b.key)
    end)
    suggestions = {}
    for index = 1, math.min(FARM_LIST, #merged) do suggestions[index] = merged[index] end
    if view.farmKind ~= (chosen or false) then view.farmKind, view.farmOffset = chosen or false, 0 end      -- A new list starts at its top.
    local right = left + view.left + 16
    y = top
    view.farmsHeading:ClearAllPoints(); view.farmsHeading:SetPoint("TOPLEFT", right, y); y = y - 18
    local x, total = right, #own
    for _, name in pairs(farms and farms.CATEGORIES or {}) do total = total + (counts[name] or 0) end
    for _, chip in ipairs(view.chips) do
        chip.count = chip.category and (counts[chip.category] or 0) or total
        chip:ClearAllPoints(); chip:SetPoint("TOPLEFT", x, y)
        x = x + chip:GetWidth() + 4
        local selected = chip.category == chosen
        ns.UIButtonTone(chip, selected)
        chip.caption:SetAlpha(chip.count == 0 and 0.35 or 1)
    end
    y = y - 28
    view.farmCount:ClearAllPoints(); view.farmCount:SetPoint("TOPRIGHT", page, "TOPLEFT", left + width, top)
    view.farmCount:SetText(#suggestions > PAGE_FARMS and (#suggestions .. " farms, best first: scroll for more") or "")
    local visible = math.min(PAGE_FARMS, #suggestions) * FARM_ROW
    local barWidth = #suggestions > PAGE_FARMS and 8 or 0
    view.farmScroll:ClearAllPoints(); view.farmScroll:SetPoint("TOPLEFT", right, y)
    view.farmScroll:SetSize(view.right, math.max(1, visible))
    view.farmScroll:SetShown(#suggestions > 0)
    view.farmChild:SetSize(view.right, math.max(FARM_ROW, #suggestions * FARM_ROW))
    for index, farm in ipairs(suggestions) do
        local row = view.farms[index]
        if not row then row = farmRow(view.farmChild, view.right, page); view.farms[index] = row end
        row.farm = farm
        row:Show()
        row:ClearAllPoints(); row:SetPoint("TOPLEFT", 0, -(index - 1) * FARM_ROW)
        row:SetWidth(view.right - barWidth - (barWidth > 0 and 4 or 0))
        row.name:SetText(tracker.FarmTitle(farm) .. "  •  " .. farm.zone)
        row.name:SetTextColor(unpack((farm.own or farm.mine) and GOLD or TEXT))
        row.estimate:SetText(tracker.Rate(farm.estimate or 0) .. "/h")
        row.basis:SetText(farm.own and ("measured over " .. farm.minutes .. " min" .. (farm.live and ", this session" or ""))
            or tracker.FarmBasis(farm, chosen == nil))                 -- Among the best of every kind, say which kind.
        row.go.key, row.go.active, row.go.own = farm.key, farm.active, farm.own
        row.go.routable, row.go.zone, row.go.title = farm.routable == true, farm.zone, tracker.FarmTitle(farm)
        row.go.caption:SetText(farm.own and "Track" or (farm.active and "Stop" or (farm.routable and "Start route" or "Track")))
        -- A farm with a route is the one to press: it is the bright button.
        ns.UIButtonTone(row.go, not farm.active and (farm.routable == true or farm.own == true))
    end
    for index = #suggestions + 1, #view.farms do view.farms[index].farm = nil; view.farms[index]:Hide() end
    -- Where the list is scrolled to, kept within its ends.
    local furthest = math.max(0, #suggestions * FARM_ROW - visible)
    view.farmOffset = math.max(0, math.min(furthest, view.farmOffset or 0))
    view.farmFurthest = furthest
    view.farmScroll:SetVerticalScroll(view.farmOffset)
    view.farmBar:SetShown(barWidth > 0); view.farmThumb:SetShown(barWidth > 0)
    if barWidth > 0 then
        view.farmBar:ClearAllPoints(); view.farmBar:SetPoint("TOPLEFT", page, "TOPLEFT", right + view.right - 6, y); view.farmBar:SetSize(4, visible)
        local length = math.max(18, visible * visible / (#suggestions * FARM_ROW))
        view.farmThumb:ClearAllPoints()
        view.farmThumb:SetPoint("TOPLEFT", page, "TOPLEFT", right + view.right - 6, y - (visible - length) * (furthest > 0 and view.farmOffset / furthest or 0))
        view.farmThumb:SetSize(4, length)
    end
    y = y - visible
    view.farmsNote:SetShown(#suggestions == 0)
    if #suggestions == 0 then
        view.farmsNote:ClearAllPoints(); view.farmsNote:SetPoint("TOPLEFT", right, y - 2)
        view.farmsNote:SetText(type(problem) == "string" and problem ~= "" and ("No farms to suggest yet: " .. problem)
            or "No farms to suggest yet. They appear here once the farm data has been read for your level and zone.")
        y = y - 52
    end
    y = math.min(leftBottom, y) - 10

    -- Under both: where the value came from, and the price scan.
    view.split:ClearAllPoints(); view.split:SetPoint("TOPLEFT", left, y)
    view.split:SetText("Auction " .. tracker.Money(summary.auction) .. "  •  Vendor " .. tracker.Money(summary.vendor)
        .. "  •  Coins " .. tracker.Money(summary.coin))
    view.basis:ClearAllPoints(); view.basis:SetPoint("TOPLEFT", left, y - 17)
    view.basis:SetText(summary.auctionKinds + summary.vendorKinds + summary.unpriced == 0
        and "Values and farm estimates use real auction prices once you have scanned: the Price scan button is under the auction house window."
        or (summary.auctionKinds .. (summary.auctionKinds == 1 and " item" or " items") .. " at auction price" .. sourcesText(summary.priceSources)
            .. (summary.oldestQuote and (" (oldest scan " .. ageText(summary.oldestQuote) .. ")") or "")
            .. ", " .. summary.vendorKinds .. " at vendor price"
            .. (summary.unpriced > 0 and (", " .. summary.unpriced .. " with no price") or "") .. "."))
    y = y - 46

    -- Past sessions.
    view.historyHeading:ClearAllPoints(); view.historyHeading:SetPoint("TOPLEFT", left, y); y = y - 16
    local bestRate = 0
    for _, entry in ipairs(db.trackerHistory) do bestRate = math.max(bestRate, entry.perHour or 0) end
    for index, row in ipairs(view.history) do
        local entry = db.trackerHistory[index]
        row.data = nil
        row:SetShown(entry ~= nil)
        if entry then
            row:ClearAllPoints(); row:SetPoint("TOPLEFT", left, y); y = y - 23
            row.bar:SetWidth(math.max(2, width * (bestRate > 0 and (entry.perHour or 0) / bestRate or 0)))
            row.icon:SetTexture(nil)
            row.name:ClearAllPoints(); row.name:SetPoint("LEFT", 6, 0); row.name:SetWidth(width - 160)
            local best = entry.top and entry.top[1]
            row.name:SetText(entry.zone .. (best and best.name and ("  •  mostly " .. best.name) or "")); row.name:SetTextColor(unpack(TEXT))
            row.count:SetText(math.floor((entry.seconds or 0) / 60) .. " min")
            row.value:SetText(tracker.Rate(entry.perHour or 0) .. "/h"); row.value:SetTextColor(unpack(GOLD))
        end
    end
    view.historyNote:SetShown(#db.trackerHistory == 0)
    if #db.trackerHistory == 0 then
        view.historyNote:ClearAllPoints(); view.historyNote:SetPoint("TOPLEFT", left, y - 2)
        view.historyNote:SetText("None yet. A session of five minutes or more is kept when you stop it, or when it ends by itself.")
        y = y - 24
    end
    page:SetHeight(-y + 20)
end

-- Moves the farm list by rows: one notch of the wheel is one farm.
function tracker.ScrollFarms(page, rows)
    local view = page and page.goldPage
    if not view then return end
    local furthest = view.farmFurthest or 0
    view.farmOffset = math.max(0, math.min(furthest, (view.farmOffset or 0) + rows * FARM_ROW))
    tracker.changed = true
    tracker.RenderPage(page)
end

-- A "Price scan" button on the auction house itself, so the scan is one
-- click from where it is used.
local function auctionButton()
    local host = auctionHost()
    if not host or tracker.auctionButton then return end
    local button = ns.UIButton(host, "Price scan", 104, function() tracker.ShowScan() end, true)
    button:SetHeight(24); button:SetFrameStrata("HIGH")
    button:SetPoint("TOPRIGHT", host, "BOTTOMRIGHT", -8, -6)
    ns.UIHelp(button, "Wow Together: look up what farm drops sell for, to rank farms by real prices. Nothing is bought or sold.")
    tracker.auctionButton = button
end

-- ---------------------------------------------------------------------------
-- Events and commands.
-- ---------------------------------------------------------------------------
ns.On("LOOT_READY", onLootOpened)
ns.On("LOOT_OPENED", onLootOpened)
ns.On("UNIT_SPELLCAST_SUCCEEDED", onCast)
ns.On("UNIT_SPELLCAST_CHANNEL_START", onCast)
-- Leaving the game: settle the clock so the session's time is saved with it.
ns.On("PLAYER_LOGOUT", function()
    tracker.Tick()
    if running then tracker.Pause() end
end)
ns.On("CHAT_MSG_LOOT", onLootMessage)
ns.On("CHAT_MSG_MONEY", onMoneyMessage)
ns.On("PLAYER_XP_UPDATE", onExperience)
ns.On("AUCTION_HOUSE_SHOW", function()
    scanState.status = nil
    auctionButton()
    -- At an auction house with prices to look up: offer the scan.
    scanState.confirming = nil
    if db.settings["gold.scanAtAuction"] ~= false and (#(tracker.ScanPlan()) > 0 or tracker.FullScanAvailable()) then tracker.ShowScan() end
    tracker.RefreshScan()
end)
ns.On("AUCTION_HOUSE_CLOSED", function()
    if scanState.running then tracker.StopScan("The auction house was closed after " .. scanState.done .. " of " .. scanState.total .. ". Open it again to carry on.") end
    if scanPanel and not scanState.running then scanPanel:Hide() end
end)
ns.On("PLAYER_LOGIN", function() if db.trackerWindow.shown then tracker.Show() end end)

-- Starting a suggested farm puts the tracker on screen: it is what shows
-- whether the farm pays what was estimated.
do
    local farms = namespace.GoldFarms
    if farms and type(farms.Start) == "function" then
        local start = farms.Start
        farms.Start = function(...)
            local started, reason = start(...)
            if db.settings["gold.trackerWithFarm"] ~= false then tracker.Show() end
            return started, reason
        end
    end
end

function tracker.Command(text)
    local action = string.lower(string.match(text or "", "^%s*(%S*)") or "")
    if action == "reset" then tracker.Reset(); tracker.Refresh(true); ns.Print("Farm session thrown away.")
    elseif action == "end" then tracker.Stop(); tracker.Refresh(true); ns.Print("Farm session ended.")
    elseif action == "pause" then tracker.Pause(); state.held = true; tracker.Refresh(true)
    elseif action == "start" or action == "resume" then tracker.Start(); tracker.Show()
    elseif action == "scan" then tracker.ShowScan()
    else tracker.Toggle() end
end

-- The saved data has just arrived (see Gold.lua): take it as the session's state.
function tracker.Restored()
    state.items = type(state.items) == "table" and state.items or {}
    state.zones = type(state.zones) == "table" and state.zones or {}
    state.kinds = type(state.kinds) == "table" and state.kinds or {}
    state.harvests = type(state.harvests) == "table" and state.harvests or {}
    for _, key in ipairs({"active", "coin", "xp", "loots"}) do
        if type(state[key]) ~= "number" then state[key] = 0 end
    end
    if type(db.trackerHistory) ~= "table" then db.trackerHistory = {} end
    if type(db.trackerWindow) ~= "table" then db.trackerWindow = {} end
    -- A clock reading does not survive a reload: the session comes back paused.
    running, resumedAt, lastLoot, lastXP = false, nil, nil, nil
    tracker.changed = true
    if db.trackerWindow.shown then
        if window then restorePosition(window, db.trackerWindow, "RIGHT", -260, 60) end
        tracker.Show()
    end
end

function tracker.Probe(output)
    local summary = tracker.Summary()
    output("Farm tracker: " .. (running and "running" or "paused") .. ", " .. tracker.Clock(summary.seconds) .. ", "
        .. #summary.rows .. " kinds of item, " .. tracker.Money(summary.total) .. " (" .. tracker.Rate(summary.perHour) .. "/h); "
        .. summary.auctionKinds .. " at auction price, " .. summary.vendorKinds .. " at vendor price, " .. summary.unpriced
        .. " unpriced; " .. #db.trackerHistory .. " past sessions.")
end

if db.trackerWindow.shown then
    -- Loaded after login (the package is load-on-demand): show at once.
    local shown = ns.ReadPublic(IsLoggedIn)
    if shown == true then tracker.Show() end
end
