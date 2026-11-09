local addonName, ns = ...

-- Shared constants for the existing route passes. These reproduce the values
-- used before extraction; a weight change is a separately audited decision.
ns.ROUTE_WEIGHTS = {
    walkingDistanceFactor = 1.25,
    normalizedDistanceScale = 6000,
    circuitRadiusScale = 6000,
    minimumTravelSavingSeconds = 50,
    relativeTravelSaving = 0.0005,
    questRewardFullThroughLevels = 5,
    questRewardPenaltyPerLevel = 0.2,
    minimumQuestRewardFactor = 0.1,
    minUsefulXP = 0.4,
    chainEfficiency = 0.8,
    chainCommitSteps = 2,
    chainCommitShare = 0.4,
    lowValueDelay = 0.5,
    stickiness = 0,
}

function ns.RouteCostMinimumSaving(seconds)
    return math.max(ns.ROUTE_WEIGHTS.minimumTravelSavingSeconds,
        (tonumber(seconds) or 0) * ns.ROUTE_WEIGHTS.relativeTravelSaving)
end

function ns.RouteCostQuestReward(quest, level)
    if type(quest) ~= "table" or type(quest.xp) ~= "number" or quest.xp < 0 then return nil end
    local difference = (tonumber(level) or quest.level or 1) - (quest.level or level or 1)
    local weights = ns.ROUTE_WEIGHTS
    local factor = difference <= weights.questRewardFullThroughLevels and 1
        or math.max(weights.minimumQuestRewardFactor,
            1 - (difference - weights.questRewardFullThroughLevels) * weights.questRewardPenaltyPerLevel)
    return math.floor(quest.xp * factor)
end

function ns.RouteCostModel(options)
    options = options or {}
    local model = {weights = ns.ROUTE_WEIGHTS, options = options}
    function model:travel(a, b)
        if options.travel then return options.travel(a, b) end
        if options.travelNetwork and ns.FindTravelPath then
            local path = ns.FindTravelPath(a, b, options.allowFlights)
            if path then return path.seconds, "network" end
        end
        local distance = a and b and ns.ValidTravelPoint(a) and ns.ValidTravelPoint(b)
            and ns.TravelPointDistance(a, b, options.metrics)
        if not distance then return nil, "unknown" end
        return distance * self.weights.walkingDistanceFactor / (options.speed or ns.TravelWalkSpeed()), "walk"
    end
    function model:logPressure(activeCount)
        local limit = options.logLimit
        if type(limit) ~= "number" then return 0 end
        return math.max(0, (tonumber(activeCount) or 0) - limit)
    end
    function model:rewardValue(quest, profile)
        local level = type(profile) == "table" and profile.level or nil
        return ns.RouteCostQuestReward(quest, level)
    end
    function model:chainBonus(quest, plan)
        local ids, bonus = {}, 0
        for _, stop in ipairs(plan or {}) do ids[stop.id] = true end
        for _, id in ipairs(quest and quest.prerequisiteAll or {}) do if ids[id] then bonus = bonus + 1 end end
        if quest and quest.previousQuest and ids[quest.previousQuest] then bonus = bonus + 1 end
        return bonus
    end
    function model:xpValue(quest, profile)
        if ns.QuestXP and quest and quest.id then return ns.QuestXP(quest.id, profile and profile.level) end
        return self:rewardValue(quest, profile)
    end
    function model:stepCost(stop, previousStop, state)
        local cost = 0
        if previousStop then cost = cost + (self:travel(previousStop, stop) or math.huge) end
        state = state or {}
        local pressure = self:logPressure(state.activeCount)
        local reward = self:rewardValue(ns.CatalogueQuest(stop and stop.id), state.profile)
        cost = cost + pressure * (state.logPressureWeight or 0)
            - (reward or 0) * (state.rewardWeight or 0)
            - self:chainBonus(ns.CatalogueQuest(stop and stop.id), state.plan) * (state.chainWeight or 0)
        return cost
    end
    return model
end
