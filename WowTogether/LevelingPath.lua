local addonName, ns = ...

-- The leveling path: which zone to quest in now, which next, and the level
-- each one should leave the character at, all the way to 60.
--
-- A zone guide answers "what do I do here". This answers "where do I go":
-- it walks the character through the zones in the order that keeps quests
-- worth their experience, and says what level to expect at each hand-over.
--
-- How it is worked out:
--   * Every zone's quests for this character come from the catalogue, the
--     same ones the zone guides use. Finished and skipped quests are left out.
--   * Starting from the character's level and experience, it repeatedly picks
--     the zone with the most experience on offer right now, counting only
--     quests that are neither too hard (more than two levels above) nor worth
--     too little at that level, and "does" them in level order, levelling up
--     along the way with the experience curve. The zone being followed comes
--     first; staying on the same continent is preferred.
--   * Quest rewards are not all the experience there is: kills on the way
--     add to them. The guide measures that from the character's own play
--     (experience gained in total against experience from quest rewards) and
--     scales the projection by it. Before it has seen any play it assumes
--     kills add 80% to quest rewards, an assumption that is replaced
--     gradually over the first thirty quests turned in and says so until then.
--   * A zone is only chosen while it has a worthwhile batch of quests, so the
--     path does not hop across the world for three quests; leftovers that
--     never add up to a batch are skipped, as a player would skip them.
--
-- Quest experience falls off for quests far below the character with
-- Classic's table (or the character's own observed rewards when the XP model
-- has them). Nothing here changes a route; it informs what is suggested next.
local BATCHES, MAX_STEPS, MAX_LEVEL = {8, 4, 1}, 90, 60   -- a zone needs this many quests on offer; smaller batches only if nothing else
local ABOVE = 2                  -- quests more than this many levels above the character wait
local WORTH = 0.3                -- a quest must pay this share of a typical quest at the character's level
local SAME_CONTINENT, FOLLOWING = 1.4, 1000
local IN_LOG = 0.25              -- each quest already in the log makes its zone this much more attractive (up to four)
-- Before any play is seen, kills are assumed to add 80% to quest rewards.
-- In this catalogue quest rewards cover only about two thirds of the
-- experience needed between levels 21 and 50, so a character who quests
-- their way up necessarily earns the rest from kills; 1.8 is also the usual
-- Classic proportion (a little over half of experience from quest rewards).
local PRIOR, LEARNED_AT, FORGET_AFTER = 1.8, 30, 150
local PACE_WINDOW, PACE_EVERY = 1800, 60

local inventory, inventoryFor
local path, pathFor   -- the next zones, as last calculated (see `caches` below)

-- ---------------------------------------------------------------------------
-- Pace: how fast the character levels, and how much of it is not quest rewards.
-- ---------------------------------------------------------------------------
local lastState, marks = nil, {}

local function pace()
    if not ns.char then return nil end
    if type(ns.char.xpPace) ~= "table" then ns.char.xpPace = {total = 0, quest = 0, quests = 0} end
    return ns.char.xpPace
end

local function now()
    local value = ns.ReadPublic(GetTime)
    return type(value) == "number" and value or nil
end

-- Called on every experience change. Works out what was gained across level-ups.
function ns.RecordExperienceGain()
    local state = ns.XPState and ns.XPState()
    if not state then return end
    local record, previous = pace(), lastState
    lastState = state
    if not record or not previous then return end
    local gained
    if state.level == previous.level then gained = state.xp - previous.xp
    elseif state.level == previous.level + 1 then gained = (previous.xpMax - previous.xp) + state.xp
    else return end
    if gained <= 0 or gained > previous.xpMax then return end
    record.total = record.total + gained
    record.session = (record.session or 0) + gained
    local time = now()
    if time and (#marks == 0 or time - marks[#marks].time >= PACE_EVERY) then
        marks[#marks + 1] = {time = time, total = record.session}
        while #marks > 2 and time - marks[1].time > PACE_WINDOW do table.remove(marks, 1) end
    end
end

-- Called when a quest is turned in, with the experience it paid.
function ns.RecordQuestRewardXP(reward)
    local record = pace()
    if not record or not ns.Public(reward) or type(reward) ~= "number" or reward <= 0 then return end
    record.quest, record.quests = record.quest + reward, record.quests + 1
    if record.quests > FORGET_AFTER then
        -- Keep the ratio, halve the weight: recent play counts for more.
        record.total, record.quest, record.quests = record.total / 2, record.quest / 2, math.floor(record.quests / 2)
    end
end

-- How much total experience the character earns per point of quest reward:
-- 1 until enough of their own play has been seen. Returns the factor and
-- whether it was learned.
function ns.LevelingXPMultiplier()
    local record = pace()
    if not record or record.quests < 1 or record.quest <= 0 then return PRIOR, false end
    local observed = math.max(1, math.min(2.5, record.total / record.quest))
    -- The assumption fades as evidence arrives: all measured after thirty quests.
    local weight = math.min(1, record.quests / LEARNED_AT)
    local factor = PRIOR * (1 - weight) + observed * weight
    return math.floor(factor * 20 + 0.5) / 20, weight >= 1
end

-- Experience per hour over the last half hour of play, and seconds to the next level.
function ns.LevelingPace()
    if #marks < 2 then return nil end
    local first, last = marks[1], marks[#marks]
    local elapsed = last.time - first.time
    if elapsed < 120 or last.total <= first.total then return nil end
    local perHour = (last.total - first.total) / elapsed * 3600
    local state = ns.XPState and ns.XPState()
    return perHour, state and perHour > 0 and state.toNextLevel / perHour * 3600 or nil
end

-- ---------------------------------------------------------------------------
-- The path.
-- ---------------------------------------------------------------------------
-- Is this zone of the path the zone a guide is about? Guides carry the map
-- they were built for, sometimes a separate home map, and always the zone's
-- name; any of the three settles it.
-- A guide's own zone map. `mapID` on a running guide is the map its current
-- step is on, which changes as the route crosses into a neighbouring zone;
-- `homeMapID` is the zone the guide is about.
local function homeMap(guide)
    return guide and (guide.homeMapID or guide.mapID) or nil
end

local function sameZone(zone, guide)
    if not zone or not guide then return false end
    -- Names settle it when both are known: a Hillsbrad guide whose current
    -- step is in Alterac is still the Hillsbrad guide.
    if type(zone.zone) == "string" and zone.zone ~= "" and type(guide.zone) == "string" and guide.zone ~= "" then
        return zone.zone == guide.zone
    end
    return zone.mapID ~= nil and zone.mapID == homeMap(guide)
end

local function threshold(level)
    local value = ns.xpCurve and ns.xpCurve[level] or ns.xpBaseline and ns.xpBaseline[level]
    return type(value) == "number" and value > 0 and value or nil
end

local function identity()
    local profile = ns.profile or {}
    return table.concat({tostring(ns.catalogue), tostring(ns.catalogueLocationRevision or 0), tostring(profile.faction),
        tostring(profile.classID), tostring(profile.raceID), tostring(ns.Option("classQuests"))}, "|")
end

-- What the path depends on. Read at most once a second: it is asked for on
-- every update of the guide window.
local signatureAt, signatureValue
local function signature()
    local time = ns.ReadPublic(GetTime)
    if type(time) == "number" and signatureAt and time - signatureAt < 1 then return signatureValue end
    local state = ns.XPState and ns.XPState()
    local count, sum = 0, 0
    for id in pairs(ns.active or {}) do count, sum = count + 1, sum + id end
    local factor = ns.LevelingXPMultiplier()
    signatureValue = table.concat({identity(), state and state.level or 0, state and math.floor(state.xp / state.xpMax * 4) or 0,
        ns.questHistoryCount or 0, count, sum, tostring(ns.routeSelection and ns.routeSelection.key),
        tostring(ns.routeSelection and ns.routeSelection.zone), factor,
        ns.GuideSkipSignature and ns.GuideSkipSignature() or 0, ns.levelingPathBurnRevision or 0}, "|")
    signatureAt = type(time) == "number" and time or nil
    return signatureValue
end

-- Quests that never belong on a solo leveling path, checked once per character.
local function eligible(id)
    if ns.IsRepeatableQuest(id) or ns.IsLevelingExcludedQuest(id) or ns.IsProfessionQuest(id) or ns.IsDungeonQuest(id) then return false end
    if ns.IsGroupQuest and ns.IsGroupQuest(id) then return false end
    return ns.CatalogueIdentityAllowed(id, ns.profile) == true
end

-- ---------------------------------------------------------------------------
-- Working in the background without being felt.
-- ---------------------------------------------------------------------------
-- The calculation runs a little on each frame. How much is decided by the
-- clock, not by counting items: the game runs this code several times slower
-- than a test host, and a slice sized by count that took 4 ms there took
-- tens of milliseconds in play, for seventy frames in a row. Each frame now
-- gets at most BUDGET_MS of work. Routinely only the next HORIZON zones are
-- worked out; the whole path to 60 only when the player opens it. And a path
-- that exists is not redone more often than every REBUILD_EVERY seconds.
local HORIZON, BUDGET_MS, REBUILD_EVERY = 12, 1.5, 30
local sliceStart, sliceCount = nil, 0

local function clock()
    if type(debugprofilestop) ~= "function" then return nil end
    local value = debugprofilestop()
    return type(value) == "number" and value or nil
end

-- Called inside every loop of the calculation: hands the frame back when
-- this frame's share of time is used up.
local function breathe(cooperative)
    if not cooperative then return end
    sliceCount = sliceCount + 1
    if sliceCount % 8 ~= 0 then return end
    local time = clock()
    if time and sliceStart then
        if time - sliceStart >= BUDGET_MS then coroutine.yield() end
    elseif sliceCount % 120 == 0 then
        coroutine.yield()   -- No clock on this client: fall back to a small count.
    end
end

local function zones(cooperative)
    local key = identity()
    if inventory and inventoryFor == key then return inventory end
    local pause = cooperative and function() breathe(true) end or nil
    local list = ns.LevelingZoneInventory(pause)
    for _, zone in ipairs(list) do
        local kept = {}
        for _, quest in ipairs(zone.quests) do
            if eligible(quest.id) then kept[#kept + 1] = quest end
            breathe(cooperative)
        end
        zone.quests = kept
        zone.continent = string.match(zone.key or "", ":([%w%-]+)/") or string.match(zone.key or "", "^([%w%-]+)/")
    end
    inventory, inventoryFor = list, key
    return list
end

-- Works the path out from the character's present state, `limit` zones
-- ahead. `start` overrides that state ({level, xp}) for tests and what-if
-- questions.
local function simulate(cooperative, start, limit)
    local state = start or ns.XPState and ns.XPState()
    if not state or not threshold(state.level) then return nil end
    limit = limit or MAX_STEPS
    local list = zones(cooperative)
    local level, xp = state.level, state.xp or 0
    local factor, learned = ns.LevelingXPMultiplier()
    local following = ns.routeSelection and ns.routeSelection.mode == "zone" and ns.routeSelection or nil

    -- Which quests are still open is read once, not once per zone per step.
    local open = {}
    for index, zone in ipairs(list) do
        local kept = {}
        for _, quest in ipairs(zone.quests) do
            if not (ns.GuideQuestHasSkips and ns.GuideQuestHasSkips(quest.id) or ns.GuideQuestSkipped(quest.id))
                and not (ns.CatalogueCompletion(ns.self, quest.id) == true and not (ns.active and ns.active[quest.id])) then
                kept[#kept + 1] = quest
            end
            breathe(cooperative)
        end
        open[index] = kept
    end

    -- A quest's reward at a level: its published experience scaled for how
    -- far below the character it is, or nil when that is too little to count.
    local multipliers, references = {}, {}
    local function reward(quest, at)
        local difference = at - quest.level
        local multiplier = multipliers[difference]
        if multiplier == nil then multiplier = ns.QuestXPMultiplier(difference); multipliers[difference] = multiplier end
        local value = math.floor((quest.xp or 0) * multiplier)
        if value <= 0 then return nil end
        local reference = references[at]
        if reference == nil then
            reference = ns.CatalogueXPReference and ns.CatalogueXPReference(at) or false
            references[at] = reference
        end
        if reference and value < reference * WORTH then return nil end
        return value
    end

    local done, steps, continent = {}, {}, nil
    -- The character starts somewhere: that continent is preferred from the
    -- first step, so the path does not open with a trip across the sea.
    local here = not start and ns.profile and ns.profile.mapID or nil
    for _, zone in ipairs(list) do
        if here and zone.mapID == here or following and sameZone(zone, following) then continent = zone.continent end
    end
    -- Zones whose guide ran out of steps the player could take, and the
    -- level that happened at: not offered again until the character is past it.
    local setAside = ns.char and type(ns.char.levelingPathSetAside) == "table" and ns.char.levelingPathSetAside or {}
    while level < MAX_LEVEL and #steps < limit do
        -- What every zone offers at this level.
        local offers = {}
        for index, zone in ipairs(list) do
            local total, count, held = 0, 0, 0
            local blocked = setAside[zone.zone]
            for _, quest in ipairs(open[index]) do
                if blocked and level <= blocked then break end
                if quest.level > level + ABOVE then break end
                if not done[quest.id] then
                    local value = reward(quest, level)
                    if value then
                        total, count = total + value, count + 1
                        -- Already picked up: part of the work is done.
                        if #steps == 0 and not start and ns.active and ns.active[quest.id] then held = held + 1 end
                    end
                end
            end
            if count > 0 then offers[#offers + 1] = {zone = zone, index = index, total = total, count = count, held = held} end
            breathe(cooperative)
        end
        -- The zone being followed comes first. Otherwise the biggest batch,
        -- preferring the continent the character is already on; a smaller
        -- batch is only taken when no zone has a full one.
        local best
        if #steps == 0 then
            for _, offer in ipairs(offers) do
                if following and sameZone(offer.zone, following) then best = offer end
            end
            if not best and here then
                for _, offer in ipairs(offers) do
                    -- Standing in a zone with a batch on offer, or with its quests already in the log.
                    if offer.zone.mapID == here and (offer.count >= BATCHES[2] or offer.held > 0) then best = offer end
                end
            end
        end
        for _, batch in ipairs(BATCHES) do
            if best then break end
            local bestScore
            for _, offer in ipairs(offers) do
                if offer.count >= batch then
                    local score = offer.total * (offer.zone.continent and offer.zone.continent == continent and SAME_CONTINENT or 1)
                        * (1 + IN_LOG * math.min(4, offer.held))
                    if not bestScore or score > bestScore then best, bestScore = offer, score end
                end
            end
        end
        if not best then break end
        local zone = best.zone
        local from, quests, gained = level + xp / threshold(level), 0, 0
        local progressed = true
        while progressed and level < MAX_LEVEL do
            progressed = false
            for _, quest in ipairs(open[best.index]) do
                if quest.level > level + ABOVE then break end
                if not done[quest.id] then
                    local value = reward(quest, level)
                    if value then
                        done[quest.id], progressed = true, true
                        quests, gained, xp = quests + 1, gained + value, xp + value * factor
                        while level < MAX_LEVEL and threshold(level) and xp >= threshold(level) do
                            xp, level = xp - threshold(level), level + 1
                        end
                        if not threshold(level) then break end
                    end
                end
            end
            breathe(cooperative)
        end
        if quests == 0 then break end
        local ceiling = threshold(level)
        local to = level >= MAX_LEVEL and MAX_LEVEL or level + (ceiling and xp / ceiling or 0)
        local previous = steps[#steps]
        if previous and previous.mapID == zone.mapID then
            -- Back in the same zone straight away: one visit, not two.
            previous.to, previous.quests, previous.xp = to, previous.quests + quests, previous.xp + gained
        else
            steps[#steps + 1] = {key = zone.key, zone = zone.zone, title = zone.title, mapID = zone.mapID, continent = zone.continent,
                from = from, to = to, quests = quests, xp = gained,
                following = #steps == 0 and following ~= nil and sameZone(zone, following) or nil}
        end
        continent = zone.continent
        if not ceiling then break end
    end
    local more = #steps >= limit and level < MAX_LEVEL
    return {steps = steps, level = state.level, fraction = state.xp and state.xpMax and state.xp / state.xpMax or 0,
        factor = factor, learned = learned, reached = level,
        partial = more and limit < MAX_STEPS or nil, capped = more and limit >= MAX_STEPS or nil}
end

-- Two answers are kept: the next few zones, which everything on screen
-- uses, and the whole path, which only its own window asks for.
local caches = {near = {limit = HORIZON, waiting = {}}, whole = {limit = MAX_STEPS, waiting = {}}}

local function headline(result)
    local first, second = result and result.steps[1], result and result.steps[2]
    return first and (tostring(first.zone) .. "|" .. string.format("%.1f", first.to) .. "|" .. tostring(second and second.zone)) or ""
end

local function request(kind, callback)
    -- The path has its own setting. It reads quest rewards from the
    -- catalogue and does not depend on the experimental XP model.
    if ns.Option("levelingPath") == false then
        if callback then callback(nil) end
        return nil
    end
    local cache = caches[kind]
    local wanted = signature()
    if cache.path and cache.pathFor == wanted then
        if callback then callback(cache.path) end
        return cache.path
    end
    if not C_Timer or type(C_Timer.After) ~= "function" then
        cache.path, cache.pathFor = simulate(false, nil, cache.limit), wanted
        if kind == "near" then path, pathFor = cache.path, wanted end
        if callback then callback(cache.path) end
        return cache.path
    end
    -- Something changed, but a path exists: unless someone is waiting for
    -- the answer, it can be a little out of date. Redoing it on every quest
    -- accepted or turned in is what made play stutter.
    local time = now()
    if cache.path and not callback and time and cache.builtAt and time - cache.builtAt < REBUILD_EVERY then
        return cache.path
    end
    -- Whoever asks while a calculation is running is told when it is done.
    if callback then cache.waiting[#cache.waiting + 1] = callback end
    if not cache.building then
        local limit, startedFor = cache.limit, wanted
        cache.building = coroutine.create(function() return simulate(true, nil, limit) end)
        local function step()
            sliceStart, sliceCount = clock(), 0
            local okay, result = coroutine.resume(cache.building)
            if not okay then
                cache.building, cache.waiting = nil, {}
                ns.levelingPathStatus = "Path calculation failed: " .. tostring(result)
                return
            end
            if coroutine.status(cache.building) == "dead" then
                cache.building = nil
                local changed = headline(cache.path) ~= headline(result)
                cache.path, cache.pathFor, cache.builtAt = result, startedFor, now()
                if kind == "near" then path, pathFor = result, startedFor end
                ns.levelingPathRevision = (ns.levelingPathRevision or 0) + 1
                local owed = cache.waiting
                cache.waiting = {}
                for _, done in ipairs(owed) do done(result) end
                -- Only when what is on screen would read differently is anything redrawn.
                if kind == "near" and changed and ns.ScheduleRefresh then ns.ScheduleRefresh(true) end
                if ns.RefreshLevelingPathViewer then ns.RefreshLevelingPathViewer() end
                return
            end
            ns.After("path", 0, step)
        end
        ns.After("path", 0, step)
    end
    if cache.path then cache.path.stale = true end
    return cache.path
end

-- The next zones of the path. It is recalculated in the background, a little
-- per frame; until that finishes the previous one is returned. `callback`,
-- when given, runs once a fresh path is ready.
function ns.LevelingPath(callback) return request("near", callback) end

-- The whole path to 60, for its own window.
function ns.LevelingPathWhole(callback) return request("whole", callback) end

-- For tests and what-if questions: the path from a given level, calculated at once.
function ns.LevelingPathFrom(level, xp, limit)
    return simulate(false, level and {level = level, xp = xp or 0, xpMax = threshold(level)} or nil, limit)
end

function ns.InvalidateLevelingPath()
    pathFor, inventoryFor, signatureAt = nil, nil, nil
    for _, cache in pairs(caches) do cache.pathFor, cache.builtAt = nil, nil end
end

-- The zone after the one being followed, from the last calculated path; never
-- calculates. Returns the guide shape the zone-exit logic expects.
local nextGuides, nextGuidesFor = {}, nil
local function findNextGuide(currentGuide)
    for index, step in ipairs(path.steps) do
        if sameZone(step, currentGuide) or step.key == currentGuide.key then
            for following = index + 1, #path.steps do
                local candidate = path.steps[following]
                if not sameZone(candidate, currentGuide) then
                    local low = math.floor(candidate.from)
                    return ns.LevelingZoneGuide(candidate.key, low, math.max(low, math.floor(candidate.to)))
                end
            end
            return nil
        end
    end
    return nil
end
function ns.LevelingPathNextGuide(currentGuide)
    if not path or not currentGuide then return nil end
    -- Asked on every refresh: the same guide object is handed back until the
    -- path itself changes, so nothing downstream is rebuilt for it.
    if nextGuidesFor ~= path then nextGuides, nextGuidesFor = {}, path end
    local key = tostring(homeMap(currentGuide)) .. ":" .. tostring(currentGuide.zone) .. ":" .. tostring(currentGuide.key)
    local cached = nextGuides[key]
    if cached == nil then
        cached = findNextGuide(currentGuide) or false
        nextGuides[key] = cached
    end
    return cached or nil
end

-- The zone to move on to after a guide: the path's when it is known, else
-- the lowest zone above the guide's band. Everything that says "next zone"
-- asks here, so the guide window, the zone-exit step and the path agree.
function ns.NextLevelingGuide(currentGuide)
    return ns.LevelingPathNextGuide(currentGuide)
        or ns.NextZoneBaselineGuide and ns.NextZoneBaselineGuide(currentGuide, true) or nil
end

local function levelText(value)
    if value >= MAX_LEVEL then return tostring(MAX_LEVEL) end
    return string.format("%.1f", math.floor(value * 10) / 10)
end

local function duration(seconds)
    if seconds < 90 then return "about a minute" end
    if seconds < 5400 then return "about " .. math.floor(seconds / 60 + 0.5) .. " min" end
    return string.format("about %.1f hours", seconds / 3600)
end

-- The pace line: experience per hour and time to the next level, when known.
function ns.LevelingPaceText()
    local perHour, toLevel = ns.LevelingPace()
    if not perHour then return nil end
    local state = ns.XPState()
    local rate = perHour >= 10000 and string.format("%.1fk", perHour / 1000) or tostring(math.floor(perHour + 0.5))
    return rate .. " XP an hour" .. (toLevel and state and (" • level " .. (state.level + 1) .. " in " .. duration(toLevel)) or "")
end

-- The path as text lines; `limit` caps the number of zones listed.
function ns.LevelingPathLines(result, limit)
    local lines = {}
    if not result or #result.steps == 0 then
        lines[1] = result and "No zone has quests worth your level right now." or "The path is being worked out."
        return lines
    end
    local paceLine = ns.LevelingPaceText()
    lines[#lines + 1] = "Level " .. result.level .. " (" .. math.floor(result.fraction * 100 + 0.5) .. "%)" .. (paceLine and (" • " .. paceLine) or "")
    lines[#lines + 1] = result.learned
        and ("Counting x" .. string.format("%.2f", result.factor) .. " for kills on the way, measured from your own play.")
        or ("Assuming kills add about " .. math.floor((result.factor - 1) * 100 + 0.5)
            .. "% to quest rewards; this is measured from your own play as you turn quests in.")
    for index, step in ipairs(result.steps) do
        if limit and index > limit then
            lines[#lines + 1] = "…and " .. (#result.steps - limit) .. " more, to level " .. levelText(result.steps[#result.steps].to)
            break
        end
        lines[#lines + 1] = index .. ". " .. step.zone .. "  " .. levelText(step.from) .. " to " .. levelText(step.to)
            .. "  • " .. step.quests .. (step.quests == 1 and " quest" or " quests") .. (step.following and "  (following)" or "")
    end
    if result.partial then
        lines[#lines + 1] = "The path goes on from here: open the whole path for the zones after these."
    elseif result.reached < MAX_LEVEL and not result.capped then
        lines[#lines + 1] = "At this pace the quests known to the guide run out around level " .. result.reached
            .. "; dungeons or extra kills fill the rest."
    end
    return lines
end

-- The zone guide for a step, at the bracket it will be played in.
function ns.LevelingPathGuide(step)
    local level = math.max(1, math.floor(step.from))
    local bracket = level >= 51 and "51+" or (math.floor((level - 1) / 10) * 10 + 1) .. "-" .. (math.floor((level - 1) / 10) * 10 + 10)
    for _, guide in ipairs(ns.LevelingGuideChoices and ns.LevelingGuideChoices(true, nil, bracket) or {}) do
        if guide.mode == "zone" and (guide.homeMapID or guide.mapID) == step.mapID then return guide end
    end
    for _, guide in ipairs(ns.LevelingGuideChoices and ns.LevelingGuideChoices(true, nil, "all") or {}) do
        if guide.mode == "zone" and (guide.homeMapID or guide.mapID) == step.mapID then return guide end
    end
end

-- A card for the Hub: the zone after the one being played, with the levels
-- the path expects, and the whole path one click away. Registered by
-- Recommended.lua, which loads after this file.
function ns.LevelingPathRecommendation()
    local result = ns.LevelingPath()
    if not result then return {}, "Your leveling path is being worked out." end
    local step, after = result.steps[2], result.steps[3]
    if not step then return {}, "ready" end
    return {{key = "path:" .. tostring(step.key), kind = "leveling", priority = 990, title = step.zone,
        category = "YOUR PATH: NEXT ZONE", count = "Lv " .. levelText(step.from) .. " to " .. levelText(step.to),
        detail = "After " .. result.steps[1].zone .. " (to about level " .. levelText(result.steps[1].to) .. "). "
            .. step.quests .. " quests worth your level there" .. (after and (", then " .. after.zone .. ".") or "."),
        action = ns.LevelingPathFollowing() and "Show path" or "Follow path",
        start = function() if ns.LevelingPathFollowing() then ns.ShowLevelingPath() else ns.FollowLevelingPath() end end,
        inspect = function() ns.ShowLevelingPath() end}}, "ready"
end

-- ---------------------------------------------------------------------------
-- Following the path: zone guides chained into one.
-- ---------------------------------------------------------------------------
-- With this on, the player follows the path instead of a single zone: when
-- the guide for a zone says the zone is done for their level (its zone-exit
-- step, or the route completing), the next zone's guide starts by itself.
-- It only ever acts at that hand-over, outside combat, a few seconds after
-- the zone-exit step appears, and says what it did. Stopping a guide by hand
-- pauses the chain; it never restarts a guide the player stopped.
local CHAIN_DELAY, CHAIN_AGAIN = 3, 120
local CHAIN_LIMIT, CHAIN_WINDOW = 3, 600   -- more hand-overs than this in ten minutes means something is wrong
local chainPending, chained, handovers = false, {}, {}
local lastHoldAt, lastHold

function ns.LevelingPathFollowing()
    return ns.char ~= nil and ns.char.levelingPathMode == true
end

local function redraw()
    if ns.RefreshLevelingPathViewer then ns.RefreshLevelingPathViewer() end
    if ns.ScheduleRefresh then ns.ScheduleRefresh(true) end
end

local function startStep(step, byHand)
    local guide = ns.LevelingPathGuide(step)
    if not guide then return false end
    -- A start the player asked for may ask them things (their current quests,
    -- an early start); a hand-over in the middle of play must not.
    if byHand then ns.RequestStartRoute(guide, true) else ns.StartPartyRoute(guide) end
    return true
end

function ns.FollowLevelingPath()
    if not ns.char then return end
    if ns.Option("levelingPath") == false then
        ns.Print("The leveling path is switched off in settings.")
        return
    end
    ns.char.levelingPathMode = true
    ns.Print("Following your leveling path: when a zone is done for your level, the next zone's guide starts by itself. /wt path stop ends this.")
    ns.LevelingPath(function(result)
        if not ns.LevelingPathFollowing() or not result or #result.steps == 0 then redraw(); return end
        local first = result.steps[1]
        local running = ns.routeSelection and ns.selectedRoute and not ns.selectedRoute.complete
        if not (first.following and running) then startStep(first, true) end
        redraw()
    end)
end

-- Following the path and its zone guide are one thing to the player: one
-- stop ends both, whichever button it comes from.
local stopping = false
function ns.StopLevelingPathMode()
    if not ns.char or stopping then return end
    local wasFollowing = ns.char.levelingPathMode == true
    ns.char.levelingPathMode = nil
    stopping = true
    if wasFollowing and ns.routeSelection and ns.routeSelection.mode == "zone" and ns.StopGuide then ns.StopGuide(false) end
    stopping = false
    ns.Print("Stopped following your leveling path. Pick a zone or press Follow path to carry on.")
    redraw()
end

-- Called when a guide is stopped by hand: a zone guide that belonged to the
-- path takes the path with it. A pause (the checkpoint is kept) does not.
function ns.LevelingPathGuideStopped(paused)
    if stopping or paused or not ns.LevelingPathFollowing() then return end
    local guide = ns.routeSelection
    if not guide or guide.mode ~= "zone" then return end
    ns.char.levelingPathMode = nil
    ns.Print("Stopped following your leveling path.")
end

-- Does this quest belong to the zone a guide is about?
local function questInZone(id, guide, records)
    if records[id] then return true end
    local quest = ns.CatalogueQuest(id)
    if not quest then return false end
    for _, list in ipairs({quest.ends, quest.objectives, quest.starts}) do
        for _, point in ipairs(type(list) == "table" and list or {}) do
            if type(point) == "table" and point.mapID and point.mapID == homeMap(guide) then return true end
        end
    end
    return false
end

-- What still ties the player to a zone: quests of that zone in their log
-- that are finished and not turned in, or nearly finished. A zone is not
-- left while there are any. Returns the two lists of quest titles.
function ns.ZoneUnfinishedBusiness(guide)
    local ready, nearly = {}, {}
    if not guide then return ready, nearly end
    local records = {}
    for _, record in ipairs(guide.records or {}) do records[record.id] = true end
    local ids = {}
    for id in pairs(ns.active or {}) do ids[#ids + 1] = id end
    table.sort(ids)
    local state = ns.XPState and ns.XPState()
    local level = state and state.level or ns.profile and ns.profile.level
    local alone = ns.ReadPublic(IsInGroup) ~= true and #(ns.partyNames or {}) == 0
    -- Is the quest handed in on this guide's map? Unknown ends count only for a quest the guide lists.
    local function endsHere(id)
        local quest = ns.CatalogueQuest(id)
        local ends = quest and type(quest.ends) == "table" and quest.ends or {}
        if #ends == 0 then return records[id] == true end
        for _, point in ipairs(ends) do
            if type(point) == "table" and point.mapID and point.mapID == homeMap(guide) then return true end
        end
        return false
    end
    for _, id in ipairs(ids) do
        -- Only quests the player can and will do keep them here: not ones
        -- they skipped (a step is enough), not ones too hard for their level,
        -- not elite ones while alone.
        local doable = not (ns.GuideQuestHasSkips and ns.GuideQuestHasSkips(id) or ns.GuideQuestSkipped(id))
            and not (ns.QuestTooHard and ns.QuestTooHard(id, level))
            and not (alone and ns.IsGroupQuest(id) and ns.Option("soloEliteQuests") ~= true and not ns.QuestNearlyDone(id))
        if doable and questInZone(id, guide, records) then
            local title = ns.QuestTitle(id) or ("quest " .. id)
            if ns.readyToTurnIn and ns.readyToTurnIn[id] == true or ns.QuestProgressReady(ns.self, id) == true then
                -- A hand-in elsewhere is part of the trip there, not a reason to stay.
                if endsHere(id) then ready[#ready + 1] = title end
            else
                local close, fraction = ns.QuestNearlyDone(id)
                if close then nearly[#nearly + 1] = title .. " (" .. math.floor(fraction * 100 + 0.5) .. "%)" end
            end
        end
    end
    return ready, nearly
end

local function few(list)
    local shown = {}
    for index = 1, math.min(3, #list) do shown[index] = list[index] end
    return table.concat(shown, ", ") .. (#list > 3 and (" and " .. (#list - 3) .. " more") or "")
end

-- Says once what is left, and again only when that changes.
local toldBusiness
local function holdFor(guide)
    local ready, nearly = ns.ZoneUnfinishedBusiness(guide)
    if #ready == 0 and #nearly == 0 then toldBusiness = nil; return false end
    local parts = {}
    if #ready > 0 then parts[#parts + 1] = "turn in " .. few(ready) end
    if #nearly > 0 then parts[#parts + 1] = "finish " .. few(nearly) end
    local message = "Leveling path: before leaving " .. (guide.zone or "this zone") .. ", " .. table.concat(parts, " and ") .. "."
    if toldBusiness ~= message then toldBusiness = message; ns.Print(message) end
    ns.levelingPathStatus = message
    return true
end

-- Called with the guide window's state on every full update: hands over to
-- the next zone when the current zone's guide is finished.
-- Guides the path itself has had as its first zone. Only those are left on
-- the path's say-so; a zone the player picked against the path is theirs.
local onPath = {}

-- Why the guide being followed has nothing more for the player, or nil.
--   "complete"   every quest of the guide is done
--   "exit"       the guide's own zone-finished step (experimental XP model)
--   "no steps"   the guide is left with a notice and no step to take: what
--                remains is skipped, blocked or set aside
--   "exhausted"  the path had this zone first and no longer does
local function zoneFinished(guide, state)
    local stop = state and state.stop
    if stop and stop.reasonCode == "zone-exit" then return stop.nextGuide ~= nil and "exit" or nil end
    if ns.selectedRoute ~= nil and ns.selectedRoute.complete == true then return "complete" end
    if ns.routePlanning or ns.guideScanning then return nil end
    -- No step to take: the route is empty and the guide says why it is
    -- paused (ns.routePaused, e.g. "Remaining guide steps are skipped."). The
    -- window then shows a notice, which may carry the ID of the quest that is
    -- pending, so the stop's ID says nothing here.
    local route = ns.selectedRoute
    local empty = route ~= nil and type(route.stops) == "table" and #route.stops == 0
    if empty and (type(ns.routePaused) == "string" or guide.pendingReason ~= nil) and (not stop or stop.kind == "notice") then
        return "no steps"
    end
    local first = path and not path.stale and path.steps[1] or nil
    if first and first.following and sameZone(first, guide) then onPath[tostring(guide.key)] = true end
    if first ~= nil and not sameZone(first, guide) and onPath[tostring(guide.key)] == true then return "exhausted" end
    return nil
end

-- The path stops offering a zone whose guide has no steps left for the
-- player, until the character has outgrown the level that happened at.
-- Without this the path would send them straight back: it counts quests the
-- guide cannot route (blocked by a quest they skipped, or by one it does not
-- know how to start).
local function setAsideZone(guide)
    if not ns.char or type(guide.zone) ~= "string" or guide.zone == "" then return end
    local state = ns.XPState and ns.XPState()
    local level = state and state.level or ns.profile and ns.profile.level
    if not level then return end
    if type(ns.char.levelingPathSetAside) ~= "table" then ns.char.levelingPathSetAside = {} end
    for zone, at in pairs(ns.char.levelingPathSetAside) do
        if type(at) ~= "number" or at < level then ns.char.levelingPathSetAside[zone] = nil end   -- Outgrown: forget.
    end
    ns.char.levelingPathSetAside[guide.zone] = level
    ns.levelingPathBurnRevision = (ns.levelingPathBurnRevision or 0) + 1
    signatureAt = nil
end

function ns.LevelingPathChain(state)
    if chainPending or not ns.LevelingPathFollowing() or ns.Option("levelingPath") == false then return false end
    local guide = ns.routeSelection
    if not guide or guide.mode ~= "zone" then return false end
    if not zoneFinished(guide, state) or not C_Timer or type(C_Timer.After) ~= "function" then return false end
    -- Finished and nearly finished quests of this zone come first. Looked
    -- at once a second: this runs on every update of the guide window.
    local time = now()
    if time and lastHoldAt and time - lastHoldAt < 1 then
        if lastHold then return false end
    else
        lastHoldAt, lastHold = time, holdFor(guide)
        if lastHold then return false end
    end
    chainPending = true
    ns.After("path", CHAIN_DELAY, function()
        chainPending = false
        if not ns.LevelingPathFollowing() or ns.routeSelection ~= guide then return end   -- Switched off, or the player moved on.
        if ns.RouteInCombat() or ns.routePlanning then return end                          -- Tried again on the next update.
        if holdFor(guide) then return end                                                  -- Something was finished meanwhile.
        -- Still nothing to do here, a few seconds later? (A notice can be a passing state.)
        local why = zoneFinished(guide, ns.NavigationState and ns.NavigationState() or state)
        if not why then return end
        setAsideZone(guide)
        ns.LevelingPath(function(result)
            if not result or not ns.LevelingPathFollowing() or ns.routeSelection ~= guide then return end
            local following
            for _, step in ipairs(result.steps) do
                if not sameZone(step, guide) then following = step; break end
            end
            if not following then
                ns.Print("Leveling path: no other zone has quests worth your level right now. " .. (guide.zone or "This zone") .. " stays your guide.")
                chained[tostring(guide.key)] = now() or 0
                return
            end
            local time, last = now() or 0, chained[following.key]
            if last and time - last < CHAIN_AGAIN then return end                          -- Never bounce between two zones.
            chained[following.key] = time
            -- Zones that are "done" the moment they start would send the
            -- player hopping: after three hand-overs in ten minutes, stop and say so.
            while #handovers > 0 and time - handovers[1] > CHAIN_WINDOW do table.remove(handovers, 1) end
            if #handovers >= CHAIN_LIMIT then
                ns.char.levelingPathMode = nil
                ns.Print("Leveling path: stopped following, because zone guides kept finishing straight away. Pick a zone by hand and send /wt probe.")
                redraw()
                return
            end
            handovers[#handovers + 1] = time
            ns.Print("Leveling path: " .. (guide.zone or "this zone")
                .. (why == "no steps" and " has no steps left that you can take." or " is done for your level.")
                .. " Now following " .. following.zone .. ", to about level " .. levelText(following.to) .. ".")
            startStep(following, false)
        end)
    end)
    return true
end

-- /wt path            the next zones in chat
-- /wt path follow     chain zone guides along the path
-- /wt path stop       stop chaining
function ns.LevelingPathCommand(argument)
    argument = string.lower(argument or "")
    if string.find(argument, "follow", 1, true) then ns.FollowLevelingPath(); return end
    if string.find(argument, "stop", 1, true) then ns.StopLevelingPathMode(); return end
    if ns.Option("levelingPath") == false then
        ns.Print("The leveling path is switched off in settings.")
        return
    end
    ns.Print("Working out your leveling path...")
    ns.LevelingPath(function(result)
        for _, line in ipairs(ns.LevelingPathLines(result, 8)) do ns.Print(line) end
    end)
end

local viewer
function ns.RefreshLevelingPathViewer()
    if not viewer or not viewer:IsShown() then return end
    local result = ns.LevelingPathWhole()
    viewer.body:SetText(table.concat(ns.LevelingPathLines(result), "\n")
        .. (result and result.stale and "\n\nUpdating..." or ""))
    local height = ns.ReadPublic(viewer.body.GetStringHeight, viewer.body)
    if type(height) == "number" and height > 0 then viewer:SetHeight(math.max(160, math.min(640, height + 78))) end
end

function ns.ShowLevelingPath()
    if not viewer then
        local colors = ns.UIColors
        viewer = CreateFrame("Frame", "WowTogetherLevelingPath", UIParent, "BackdropTemplate")
        ns.levelingPathViewer = viewer
        viewer:SetSize(460, 420); viewer:SetPoint("CENTER"); viewer:SetFrameStrata("DIALOG")
        viewer:SetClampedToScreen(true); viewer:SetMovable(true); viewer:EnableMouse(true)
        viewer:RegisterForDrag("LeftButton")
        viewer:SetScript("OnDragStart", viewer.StartMoving); viewer:SetScript("OnDragStop", viewer.StopMovingOrSizing)
        ns.UIPanel(viewer); ns.UIClose(viewer)
        viewer.title = ns.UILabel(viewer, "GameFontNormalLarge", 17, colors.gold)
        viewer.title:SetPoint("TOPLEFT", 18, -18); viewer.title:SetText("Your leveling path")
        viewer.body = ns.UILabel(viewer, nil, 12, colors.text)
        viewer.body:SetPoint("TOPLEFT", 18, -52); viewer.body:SetPoint("TOPRIGHT", -18, -52)
        viewer.body:SetJustifyH("LEFT"); viewer.body:SetJustifyV("TOP"); viewer.body:SetWordWrap(true)
        if type(UISpecialFrames) == "table" then table.insert(UISpecialFrames, "WowTogetherLevelingPath") end
    end
    viewer:Show(); viewer:Raise()
    viewer.body:SetText("Working out your leveling path...")
    ns.LevelingPathWhole(function() ns.RefreshLevelingPathViewer() end)
    ns.RefreshLevelingPathViewer()
end

-- ---------------------------------------------------------------------------
-- The path where the player looks: a strip under the guide window (it stays
-- in Glance), and a block on the main window's recommended page.
-- ---------------------------------------------------------------------------

-- One line for the guide window: how far this zone takes you, where next, the pace.
function ns.LevelingPathSummary(result)
    if not result or #result.steps == 0 then return nil end
    local first, second = result.steps[1], result.steps[2]
    local line = (ns.LevelingPathFollowing() and "Path: " or "")
        .. (first.following and (ns.LevelingPathFollowing() and "this zone" or "This zone") or first.zone) .. " to level " .. levelText(first.to)
    if second then line = line .. ", then " .. second.zone end
    -- The pace is in the tooltip and on the main window: a number that
    -- changes as you play does not belong in a line you glance at.
    return line
end

local function pathTooltip(owner)
    if not GameTooltip then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:AddLine("Your leveling path", 1, 0.82, 0.3)
    for _, line in ipairs(ns.LevelingPathLines(path, 6)) do GameTooltip:AddLine(line, 1, 1, 1, true) end
    GameTooltip:AddLine("Click for the whole path.", 0.68, 0.71, 0.75, true)
    GameTooltip:Show()
end

function ns.CreateLevelingPathStrip(frame)
    if frame.pathStrip then return frame.pathStrip end
    local colors = ns.UIColors
    local strip = CreateFrame("Button", nil, frame, "BackdropTemplate")
    -- A line of text that belongs to the guide window, not a box of its
    -- own: no border, and in Glance no fill either. It lines up with the
    -- window's rows.
    strip:SetSize(360, 20); ns.UIPanel(strip, colors.panel)
    strip:SetBackdropBorderColor(0, 0, 0, 0)
    strip.text = ns.UILabel(strip, nil, 11, colors.muted)
    strip.text:SetPoint("LEFT", 14, 0); strip.text:SetHeight(16); strip.text:SetWordWrap(false); strip.text:SetJustifyH("LEFT")
    -- "Clean log (3)": shown when the log holds quests no longer worth doing.
    -- It opens the same question as /wt clean; nothing is abandoned by the click itself.
    strip.clean = CreateFrame("Button", nil, strip)
    strip.clean:SetSize(96, 18); strip.clean:SetPoint("RIGHT", -8, 0)
    strip.clean.caption = ns.UILabel(strip.clean, nil, 11, colors.gold)
    strip.clean.caption:SetPoint("RIGHT", 0, 0); strip.clean.caption:SetJustifyH("RIGHT"); strip.clean.caption:SetWordWrap(false)
    strip.clean:SetScript("OnClick", function() if ns.QuestLogCleanup then ns.QuestLogCleanup(true) end end)
    strip.clean:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:AddLine("Clean your quest log", 1, 0.82, 0.3)
        GameTooltip:AddLine("Shows the quests no longer worth doing and asks before abandoning any.", 1, 1, 1, true)
        GameTooltip:Show()
    end)
    strip.clean:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    strip.clean:Hide()
    strip:SetScript("OnClick", function() ns.ShowLevelingPath() end)
    strip:SetScript("OnEnter", function(self) self.text:SetTextColor(unpack(colors.gold)); pathTooltip(self) end)
    strip:SetScript("OnLeave", function(self) self.text:SetTextColor(unpack(colors.muted)); if GameTooltip then GameTooltip:Hide() end end)
    strip:Hide()
    frame.pathStrip = strip
    return strip
end

-- Called with the guide window's state on every full update.
function ns.UpdateLevelingPathStrip(state)
    ns.LevelingPathChain(state)
    local strip = ns.navigation and ns.navigation.pathStrip
    if not strip then return false end
    local guide = ns.routeSelection
    local wanted = state and state.visible and ns.Option("routeArrow") and ns.Option("levelingPathStrip") ~= false
        and ns.Option("levelingPath") ~= false and not ns.navigationPreview and guide and guide.mode == "zone"
    local line = wanted and ns.LevelingPathSummary(ns.LevelingPath()) or nil
    if not line then strip:Hide(); return false end
    if strip.shownText ~= line then strip.shownText = line; strip.text:SetText(line) end
    local useless = ns.UselessQuestCount and ns.UselessQuestCount() or 0
    if strip.cleanCount ~= useless then
        strip.cleanCount = useless
        strip.clean:SetShown(useless > 0)
        if useless > 0 then strip.clean.caption:SetText("Clean log (" .. useless .. ")") end
        strip.text:SetWidth(math.max(60, (strip:GetWidth() or 360) - 28 - (useless > 0 and 100 or 0)))
    end
    local glance = ns.GlanceActive()
    if strip.glance ~= glance then
        strip.glance = glance
        strip:SetBackdropBorderColor(0, 0, 0, 0)
        if glance then strip:SetBackdropColor(0, 0, 0, 0) elseif ns.UpdateNavigationBackground then ns.UpdateNavigationBackground() end
    end
    strip:Show()
    return true
end

-- The next zones for the main window: up to `limit` rows of {zone, levels, quests, following}.
function ns.LevelingPathRows(limit)
    local result = ns.LevelingPath()
    if not result then return nil end
    local rows = {}
    for index, step in ipairs(result.steps) do
        if index > (limit or 4) then break end
        rows[index] = {zone = step.zone, levels = levelText(step.from) .. " to " .. levelText(step.to),
            quests = step.quests, following = step.following == true, step = step}
    end
    return rows, result
end

function ns.LevelingPathDiagnostics(output)
    local factor, learned = ns.LevelingXPMultiplier()
    local record = pace()
    output("Leveling path: " .. (ns.LevelingPathFollowing() and "following (zone guides chain); " or "not followed; ")
        .. (path and ("next " .. #path.steps .. " zones worked out, to level " .. tostring(path.reached)) or "not calculated yet")
        .. "; kill share x" .. factor .. (learned and " from your play" or " (assumed, still being measured)")
        .. "; " .. (record and record.quests or 0) .. " quest rewards seen. " .. (ns.LevelingPaceText() or "Pace not measured yet."))
end

ns.On("PLAYER_XP_UPDATE", function(unit)
    if ns.Public(unit) and unit == "player" and ns.char then ns.RecordExperienceGain() end
end)
