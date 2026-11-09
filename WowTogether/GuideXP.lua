local addonName, ns = ...

local cachedLevelingSignature, cachedLevelingValues, cachedLevelingCount
local lastLevelingDiagnostic

local function number(value, maximum)
    return ns.Public(value) and type(value) == "number" and value >= 0 and value <= maximum and value == math.floor(value)
end

local function median(values)
    table.sort(values)
    local count = #values
    if count == 0 then return nil end
    if count % 2 == 1 then return values[(count + 1) / 2] end
    return (values[count / 2] + values[count / 2 + 1]) / 2
end

local cachedSamples, cachedSampleCount, cachedSampleRevision, cachedObserved = nil, -1, -1, {}
local function indexObservedSamples()
    local samples = ns.char and ns.char.xpSamples or {}
    if samples == cachedSamples and #samples == cachedSampleCount and (ns.xpSampleRevision or 0) == cachedSampleRevision then return end
    cachedSamples, cachedSampleCount, cachedSampleRevision, cachedObserved = samples, #samples, ns.xpSampleRevision or 0, {}
    for _, sample in ipairs(samples) do
        if type(sample) == "table" and sample.difference and sample.rested ~= true and ns.Public(sample.multiplier)
            and type(sample.multiplier) == "number" and sample.multiplier >= 0 and sample.multiplier <= 2 then
            local values = cachedObserved[sample.difference] or {}
            values[#values + 1] = sample.multiplier
            cachedObserved[sample.difference] = values
        end
    end
    for difference, values in pairs(cachedObserved) do
        if #values >= 20 then cachedObserved[difference] = median(values) else cachedObserved[difference] = nil end
    end
end

local function observedMultiplier(difference)
    indexObservedSamples()
    local values = cachedObserved[difference]
    if values then return values, 20 end
    return nil, 0
end

function ns.QuestXPMultiplier(difference)
    difference = number(difference, 60) and difference or 0
    if difference <= ns.ROUTE_WEIGHTS.questRewardFullThroughLevels then return 1, "table", 0 end
    local count = 0
    if ns.Option("xpModel") then
        local observed
        observed, count = observedMultiplier(difference)
        if observed then return math.max(0, math.min(1, observed)), "observed", count end
    end
    local weights = ns.ROUTE_WEIGHTS
    return math.max(weights.minimumQuestRewardFactor,
        1 - (difference - weights.questRewardFullThroughLevels) * weights.questRewardPenaltyPerLevel), "table", count
end

function ns.RecordQuestXPSample(id, xpReward)
    local quest = ns.CatalogueQuest(id)
    local level = ns.profile and ns.profile.level
    if not ns.char or not quest or not number(xpReward, 10000000) or xpReward <= 0 or not number(level, 60) then return false end
    ns.char.xpSamples = type(ns.char.xpSamples) == "table" and ns.char.xpSamples or {}
    local rested = (ns.ReadPublic(GetXPExhaustion) or 0) > 0
    local difference = math.max(0, level - (quest.level or level))
    local nominal = number(quest.xp, 10000000) and quest.xp or nil
    local multiplier = nominal and nominal > 0 and xpReward / nominal or nil
    ns.char.xpSamples[#ns.char.xpSamples + 1] = {questID = id, questLevel = quest.level or level,
        playerLevel = level, xpReward = xpReward, rested = rested,
        difference = difference, multiplier = multiplier}
    while #ns.char.xpSamples > 500 do table.remove(ns.char.xpSamples, 1) end
    ns.xpSampleRevision = (ns.xpSampleRevision or 0) + 1
    return true
end

function ns.XPCalibrationSummary()
    local observed, tableBuckets, counts = 0, 0, {}
    for difference = 0, 8 do
        local _, source, count = ns.QuestXPMultiplier(difference)
        counts[difference] = count
        if source == "observed" then observed = observed + 1 else tableBuckets = tableBuckets + 1 end
    end
    return observed, tableBuckets, counts
end

function ns.XPState()
    local level = ns.ReadPublic(UnitLevel, "player")
    local xp = ns.ReadPublic(UnitXP, "player")
    local maximum = ns.ReadPublic(UnitXPMax, "player")
    local rested = ns.ReadPublic(GetXPExhaustion)
    if not number(level, 60) or level < 1 or not number(xp, 10000000)
        or not number(maximum, 10000000) or maximum < 1 or xp >= maximum then return end
    if not number(rested, 10000000) then rested = 0 end
    return {level = level, xp = xp, xpMax = maximum, rested = rested,
        toNextLevel = math.max(0, maximum - xp)}
end

-- Classic quest XP overlevel table: quests at up to +5 levels pay nominal XP;
-- each level below the player thereafter loses 20%, with a 10% floor. Forever
-- may override this only after a tester provides captured reward comparisons.
function ns.QuestXP(id, level)
    local quest = ns.CatalogueQuest(id)
    if not quest or not number(quest.xp, 10000000) then return end
    level = number(level, 60) and level or ns.profile and ns.profile.level
    if not number(level, 60) then return end
    local difference = level - (quest.level or level)
    local factor = ns.QuestXPMultiplier(difference)
    return math.floor(quest.xp * factor)
end

function ns.ZoneXPRemaining(guide, profile, query)
    if type(guide) ~= "table" then return end
    local total, unknown, seen, work = 0, 0, {}, 0
    local function add(id)
        if seen[id] then return end
        seen[id] = true
        if ns.CatalogueCompletion(ns.self, id, query) == true and not ns.active[id] then return end
        local reward = ns.QuestXP(id, profile and profile.level)
        if reward then total = total + reward else unknown = unknown + 1 end
        work = work + 1
        if query and query.cooperative and work % 100 == 0 then coroutine.yield() end
    end
    for _, record in ipairs(guide.records or {}) do add(record.id) end
    for id in pairs(ns.active or {}) do
        if ns.readyToTurnIn and ns.readyToTurnIn[id] or ns.QuestProgressReady(ns.self, id) == true then add(id) end
    end
    return total, unknown
end

local function zoneProjection(guide, profile, query)
    profile = profile or ns.profile
    local state = query and query.policyXPState or ns.XPState()
    if not state or not profile or not number(profile.level, 60) then return end
    local remaining, unknown = ns.ZoneXPRemaining(guide, profile, query)
    if not remaining then return end
    local level, xp, curveIncomplete = state.level, state.xp + remaining, false
    while level < 60 do
        local threshold = ns.xpCurve and ns.xpCurve[level] or ns.xpBaseline and ns.xpBaseline[level]
        if not number(threshold, 10000000) or threshold < 1 then curveIncomplete = true; break end
        if xp < threshold then break end
        xp, level = xp - threshold, level + 1
    end
    local nextGuide = ns.NextZoneBaselineGuide and ns.NextZoneBaselineGuide(guide, true)
    if nextGuide and (nextGuide.rangeLow or 255) > level then nextGuide = nil end
    local threshold = ns.xpCurve and ns.xpCurve[level] or ns.xpBaseline and ns.xpBaseline[level]
    return {remaining = remaining, unknown = unknown, level = level, xp = xp, curveIncomplete = curveIncomplete,
        percent = level >= 60 and 1 or threshold and threshold > 0 and xp / threshold or nil,
        nextGuide = nextGuide}
end

function ns.ZoneExitProjection(guide, profile, query)
    if type(guide) ~= "table" then return end
    profile = profile or ns.profile
    local state = query and query.policyXPState or ns.XPState()
    if query and state then query.policyXPState = state end
    if not state or not profile then return zoneProjection(guide, profile, query) end
    if not query then return zoneProjection(guide, profile, query) end
    local key = table.concat({tostring(guide.key), tostring(profile.level), tostring(state.level), tostring(state.xp),
        tostring(state.xpMax), tostring(ns.guideProgressRevision or 0), tostring(ns.xpSampleRevision or 0),
        tostring(ns.questHistoryCount or 0), tostring(ns.objectiveDisplayRevision or 0)}, ":")
    local cache = query.policyCache
    if not cache then cache = {}; query.policyCache = cache end
    cache.zoneExit = cache.zoneExit or {}
    local cached = cache.zoneExit[key]
    if cached ~= nil then return cached ~= false and cached or nil end
    local result = zoneProjection(guide, profile, query)
    cache.zoneExit[key] = result or false
    if ns.policyMetrics then ns.policyMetrics.zoneExitCalls = (ns.policyMetrics.zoneExitCalls or 0) + 1 end
    return result
end

local function xpCompletionRevision()
    return table.concat({tostring(ns.catalogue), tostring(ns.guideProgressRevision or 0),
        tostring(ns.questHistoryCount or 0), tostring(ns.objectiveDisplayRevision or 0),
        tostring(ns.xpSampleRevision or 0), tostring(ns.profile and ns.profile.faction),
        tostring(ns.profile and ns.profile.class), tostring(ns.profile and ns.profile.level)}, ":")
end

function ns.XPDiagnosticsText()
    if not ns.Option("xpModel") then return "off" end
    local revision = xpCompletionRevision()
    if not lastLevelingDiagnostic or lastLevelingDiagnostic.revision ~= revision
        or lastLevelingDiagnostic.level ~= (ns.profile and ns.profile.level) then return "on; not computed yet" end
    return "on; " .. lastLevelingDiagnostic.count .. " quest estimates cached for level " .. lastLevelingDiagnostic.level
end

function ns.XPLevelingValue(id, query)
    local level = ns.PartyLevelFloor(query)
    if not level then return end
    local revision = xpCompletionRevision()
    local signature = revision .. ":" .. tostring(query)
    if cachedLevelingSignature ~= signature then
        cachedLevelingSignature, cachedLevelingValues, cachedLevelingCount = signature, {}, 0
    end
    local levelValues = cachedLevelingValues[level]
    if not levelValues then levelValues = {}; cachedLevelingValues[level] = levelValues end
    local cached = levelValues[id]
    if cached then return cached.value, cached.reason end
    local function save(value, reason)
        levelValues[id] = {value = value, reason = reason}
        cachedLevelingCount = cachedLevelingCount + 1
        lastLevelingDiagnostic = {revision = revision, level = level, count = cachedLevelingCount}
        return value, reason
    end
    local quest = ns.CatalogueQuest(id)
    if not quest then return save(true) end
    local own = ns.QuestXP(id, level) or 0
    local reference = ns.CatalogueXPReference(level) or quest.xp or 0
    local minimum = reference * ns.ROUTE_WEIGHTS.minUsefulXP
    local best, nextID = own, nil
    -- A low-level pickup remains useful when it directly unlocks a worthwhile
    -- next quest. Follow-up eligibility is still checked by existing policy.
    for nextQuestID in pairs(ns.CatalogueFollowers(id)) do
        if ns.CatalogueIdentityAllowed(nextQuestID, ns.profile) == true
            and ns.CatalogueCompletion(ns.self, nextQuestID, query) ~= true then
            local value = ns.QuestXP(nextQuestID, level) or 0
            if value > best then best, nextID = value, nextQuestID end
        end
    end
    if best >= minimum and best > 0 then
        if nextID and own < minimum then return save(true, "Unlocks " .. ns.QuestTitle(nextID) .. " for its quest XP.") end
        return save(true, "Quest XP fits your current level.")
    end
    return save(false, "Low XP for your current level; keep it under Later.")
end

function ns.CatalogueFreshnessText(now)
    local catalogue = ns.catalogue or {}
    local metadata = catalogue.meta or {}
    local captured = metadata.captured or catalogue.captured
    local build = metadata.build or catalogue.clientBuild or catalogue.build
    local age
    local year, month, day = type(captured) == "string" and string.match(captured, "^(%d%d%d%d)%-(%d%d)%-(%d%d)$")
    if year and type(time) == "function" then
        local okay, stamp = pcall(time, {year = tonumber(year), month = tonumber(month), day = tonumber(day), hour = 12})
        local current = now or (type(time) == "function" and time())
        if okay and type(stamp) == "number" and type(current) == "number" then
            age = math.max(0, math.floor((current - stamp) / 86400))
        end
    end
    local text = "Quest data captured " .. (captured or "on an unknown date")
        .. (age and (" (" .. age .. " day" .. (age == 1 and "" or "s") .. " ago)") or " (age unknown)")
        .. "; build " .. (build and tostring(build) or "not recorded") .. "."
    if age and age > 21 then text = text .. " Data may predate the current patch." end
    return text
end

local function snapshot(guide)
    return number(guide.xpStartLevel, 60) and guide.xpStartLevel >= 1
        and number(guide.xpFinishLevel, 60) and guide.xpFinishLevel >= guide.xpStartLevel
        and number(guide.xpReward, 1000000000) and number(guide.xpUnknown, 512)
end

function ns.InitializeGuideXP()
    local _, build = ns.ReadPublic(GetBuildInfo)
    build = build and tostring(build) or "unknown"
    ns.db.xpBuilds = type(ns.db.xpBuilds) == "table" and ns.db.xpBuilds or {}
    local curve = ns.db.xpBuilds[build]
    if type(curve) ~= "table" then curve = {}; ns.db.xpBuilds[build] = curve end
    for level, xp in pairs(curve) do
        if not number(level, 60) or level < 1 or not number(xp, 10000000) or xp < 1 then curve[level] = nil end
    end
    ns.xpCurve = curve
    ns.ReadGuideXP()
end

function ns.ReadGuideXP()
    local level, maximum = ns.ReadPublic(UnitLevel, "player"), ns.ReadPublic(UnitXPMax, "player")
    if ns.xpCurve and number(level, 60) and level > 0 and number(maximum, 10000000) and maximum > 0 then ns.xpCurve[level] = maximum end
end

function ns.GuideXPProjection(guide, query)
    if not guide or not guide.fullGuide then return end
    local level = ns.profile and ns.profile.level
    if not number(level, 60) or level < 1 then return end
    local xp = ns.ReadPublic(UnitXP, "player")
    local maximum = ns.xpCurve and ns.xpCurve[level] or ns.xpBaseline and ns.xpBaseline[level]
    local initial = number(xp, 10000000) and maximum and xp < maximum and xp or 0
    local result = {startLevel = level, startXP = initial, reward = 0, unknown = 0, assumedStart = not number(xp, 10000000)}
    local progress, unavailable, baseline = initial, false, false
    query = query or ns.NewQuestQuery()
    local ids = {}
    local function add(id)
        if ids[id] then return end
        ids[id] = true
        local quest = ns.CatalogueQuest(id)
        if not quest or ns.Completed(id, query) == true or ns.GuideQuestSkipped(id) or ns.IsRepeatableQuest(id)
            or ns.IsLevelingExcludedQuest(id) or ns.IsProfessionQuest(id) or ns.IsDungeonQuest(id) or not ns.ClassQuestEnabled(id)
            or ns.IsGroupQuest(id) and #(ns.partyNames or {}) == 0
            or quest.pickupRequiresOffer and ns.PickupOfferEvidence(ns.self, id) ~= true
            or ns.CatalogueIdentityAllowed(id, ns.profile) ~= true
            or (quest.level or 0) < result.startLevel - 3 and ns.LevelingValue(id, query) == false then return end
        if not number(quest.xp, 10000000) then result.unknown = result.unknown + 1; return end
        -- Published reward is nominal. The older-world overlevel reduction is
        -- an estimate, not a claim about the current Forever reward formula.
        local reward = ns.QuestXP(id, level)
        result.reward, progress = result.reward + reward, progress + reward
        while level < 60 do
            local threshold = ns.xpCurve and ns.xpCurve[level]
            if not threshold then threshold = ns.xpBaseline and ns.xpBaseline[level]; baseline = true end
            if not number(threshold, 10000000) or threshold < 1 then unavailable = true; break end
            if progress < threshold then break end
            progress, level = progress - threshold, level + 1
        end
    end
    if guide.fixedPlan then
        for _, stop in ipairs(guide.fixedPlan) do if stop.kind == "t" and #ns.FilterGuideStages({stop}) > 0 then add(stop.id) end end
    else for _, record in ipairs(guide.records or {}) do add(record.id) end end
    result.finishLevel, result.baseline, result.unavailable = level, baseline, unavailable
    return result
end

function ns.CaptureGuideXP(guide)
    if snapshot(guide) then return end
    local result = ns.GuideXPProjection(guide)
    if not result then return end
    guide.xpStartLevel, guide.xpStart = result.startLevel, result.startXP
    guide.xpFinishLevel, guide.xpReward, guide.xpUnknown = result.finishLevel, result.reward, result.unknown
    guide.xpBaseline, guide.xpUnavailable, guide.xpAssumedStart = result.baseline, result.unavailable, result.assumedStart
end

function ns.GuideXPText(guide, query)
    local current = ns.routeSelection
    if current and current.key == guide.key and current.xpStartLevel then guide = current end
    local result = snapshot(guide) and {startLevel = guide.xpStartLevel, finishLevel = guide.xpFinishLevel,
        reward = guide.xpReward, unknown = guide.xpUnknown, unavailable = guide.xpUnavailable, baseline = guide.xpBaseline, assumedStart = guide.xpAssumedStart}
        or ns.GuideXPProjection(guide, query)
    if not result then return "" end
    if guide.mode == "zone" then
        local projection = ns.ZoneExitProjection(guide, ns.profile, query)
        if projection then
            local state = ns.XPState()
            local remainingLevels = projection.remaining / math.max(1, state and state.xpMax or 1)
            if projection.curveIncomplete then
                return string.format("Remaining here: ~%.1f levels • XP curve incomplete; projected exit unavailable",
                    remainingLevels)
            end
            local percent = projection.percent and (" (" .. math.floor(projection.percent * 100 + 0.5) .. "%)") or ""
            local nextGuide = projection.nextGuide
            local line
            local zoneFinishing = ns.GuideZoneFinishing and ns.GuideZoneFinishing(guide, ns.profile, projection, query)
            if zoneFinishing then
                local eligible = 0
                for _, record in ipairs(guide.records or {}) do
                    if ns.LevelingValue(record.id, query) ~= false then eligible = eligible + 1 end
                end
                line = "Finishing " .. (guide.zone or "this zone") .. ": " .. eligible
                    .. " quests left worth doing" .. (nextGuide and (", then " .. nextGuide.zone .. " at " .. tostring(nextGuide.rangeLow)) or "")
            else
                line = string.format("Remaining here: ~%.1f levels • leaves you at level %d%s",
                    remainingLevels, projection.level, percent)
            end
            if nextGuide and not zoneFinishing then line = line .. "\nThen: " .. nextGuide.zone .. " ("
                .. tostring(nextGuide.rangeLow or "?") .. "–" .. tostring(nextGuide.rangeHigh or "?") .. ")" end
            return line
        end
    end
    local finish = result.unavailable and "XP curve incomplete" or ("Lv " .. result.startLevel .. " → ~Lv " .. result.finishLevel)
    return "Quest XP estimate: " .. finish .. " • " .. result.reward .. " XP"
        .. (result.baseline and " • Classic curve estimate" or " • Quest rewards only")
        .. (result.unknown > 0 and ("; " .. result.unknown .. " rewards unknown") or "")
end

function ns.GuideXPHelp(frame)
    local freshness = ns.CatalogueFreshnessText and ns.CatalogueFreshnessText()
    ns.UIHelp(frame, "Quest reward estimate; kills, exploration, rested XP and party effects are excluded. Unobserved level thresholds and reward scaling use an older-world baseline, not a verified Forever curve. Missing XP reads assume the start of your level."
        .. (freshness and ("\n" .. freshness) or ""))
end

ns.On("PLAYER_XP_UPDATE", function(unit) if ns.Public(unit) and unit == "player" and ns.db then ns.ReadGuideXP() end end)
