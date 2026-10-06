local addonName, ns = ...

local function number(value, maximum)
    return ns.Public(value) and type(value) == "number" and value >= 0 and value <= maximum and value == math.floor(value)
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
        local difference = level - (quest.level or level)
        local factor = difference <= 5 and 1 or math.max(0.1, 1 - (difference - 5) * 0.2)
        local reward = math.floor(quest.xp * factor)
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
    local finish = result.unavailable and "XP curve incomplete" or ("Lv " .. result.startLevel .. " → ~Lv " .. result.finishLevel)
    return "Quest XP estimate: " .. finish .. " • " .. result.reward .. " XP"
        .. (result.baseline and " • Classic curve estimate" or " • Quest rewards only")
        .. (result.unknown > 0 and ("; " .. result.unknown .. " rewards unknown") or "")
end

function ns.GuideXPHelp(frame)
    ns.UIHelp(frame, "Estimate from unfinished guide quest rewards at route start. Kills, exploration, rested XP and party effects are excluded. Unobserved level thresholds and reward scaling use an older-world baseline; these are not verified Forever values. Missing XP reads assume the start of your level.")
end

ns.On("PLAYER_XP_UPDATE", function(unit) if ns.Public(unit) and unit == "player" and ns.db then ns.ReadGuideXP() end end)
