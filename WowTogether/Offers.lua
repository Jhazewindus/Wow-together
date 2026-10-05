local addonName, ns = ...

ns.offered = {}
ns.turnInStatus = "Automatic turn-in is off."

function ns.InvalidateNPCOffers()
    if ns.db and ns.db.offerKnowledge then ns.db.offerKnowledge[ns.self] = {} end
end

local function offerContext()
    local ids = {}; for id in pairs(ns.active or {}) do ids[#ids + 1] = id end; table.sort(ids)
    local level = ns.ReadPublic(UnitLevel, "player") or ns.profile and ns.profile.level or 0
    return tostring(level) .. ":" .. table.concat(ids, ",")
end

function ns.RecordNPCOfferAvailability(quests, complete)
    local guid = ns.ReadPublic(UnitGUID, "npc")
    local id = type(guid) == "string" and tonumber(string.match(guid, "^Creature%-%d+%-%d+%-%d+%-%d+%-(%d+)%-"))
    if not id or not ns.Public(quests) or type(quests) ~= "table" then return end
    local offered = {}
    for _, quest in ipairs(quests) do
        if not ns.Public(quest) or type(quest) ~= "table" or not ns.Public(quest.questID)
            or not ns.GuideInteger(quest.questID) or quest.questID <= 0 then return end
        offered[quest.questID] = true
    end
    if complete == false then
        local previous = ns.db.offerKnowledge[ns.self][id]
        if previous and previous.context == offerContext() then
            for questID in pairs(previous.offered) do offered[questID] = true end
        end
    end
    ns.db.offerKnowledge[ns.self][id] = {context = offerContext(), offered = offered, complete = complete ~= false}
end

function ns.ObservedPickupAvailable(id)
    local quest, knowledge = ns.CatalogueQuest(id), ns.db.offerKnowledge and ns.db.offerKnowledge[ns.self]
    if not quest or not knowledge then return end
    local checked, total = 0, 0
    for _, point in ipairs(quest.starts or {}) do
        total = total + 1
        local observed = point.npc and knowledge[point.entityID]
        if observed and observed.context == offerContext() then
            if observed.offered[id] then return true end
            if observed.complete ~= false then checked = checked + 1 end
        end
    end
    if total > 0 and checked == total then return false end
end

function ns.AutoSelectGuideQuest()
    if not ns.Option("autoSelectQuests") or ns.RouteInCombat() then return end
    local stop = ns.selectedRoute and ns.selectedRoute.stops[1]
    if not stop or ns.autoGossipAttempt == stop.id then return end
    if stop.kind == "a" and ns.offered[stop.id] and C_GossipInfo and type(C_GossipInfo.SelectAvailableQuest) == "function" then
        ns.autoGossipAttempt = stop.id
        C_GossipInfo.SelectAvailableQuest(stop.id)
    elseif stop.kind == "t" and C_GossipInfo and type(C_GossipInfo.SelectActiveQuest) == "function" then
        local quests = ns.ReadPublic(C_GossipInfo.GetActiveQuests)
        for _, quest in ipairs(type(quests) == "table" and quests or {}) do
            if ns.Public(quest) and type(quest) == "table" and ns.Public(quest.questID) and quest.questID == stop.id
                and ns.Public(quest.isComplete) and quest.isComplete == true then
                ns.autoGossipAttempt = stop.id
                C_GossipInfo.SelectActiveQuest(stop.id); return
            end
        end
    end
end

function ns.AutoTurnInOpenedQuest(stage)
    if not ns.Option("autoTurnIn") then ns.turnInStatus = "Automatic turn-in is off."; return end
    if ns.RouteInCombat() then ns.turnInStatus = "Turn-in left manual during combat."; return end
    local id = ns.ReadPublic(GetQuestID)
    if not ns.GuideInteger(id) or id <= 0 or not ns.active[id] then
        ns.turnInStatus = "Waiting for a public, accepted quest dialog."; return
    end
    if stage == "progress" then
        if type(CompleteQuest) ~= "function" or ns.ReadPublic(IsQuestCompletable) ~= true then
            ns.turnInStatus = "Quest progress is incomplete or unavailable."; return
        end
        if ns.turnInProgressAttempt == id then return end
        ns.turnInProgressAttempt = id
        ns.turnInStatus = "Opening the completed quest's reward dialog."
        CompleteQuest()
    elseif stage == "reward" then
        local choices = ns.ReadPublic(GetNumQuestChoices)
        if not ns.GuideInteger(choices, 100) or type(GetQuestReward) ~= "function" then
            ns.turnInStatus = "Reward API or choice count unavailable; complete manually."; return
        end
        if choices > 0 then ns.turnInStatus = "Choose your quest reward manually."; return end
        if ns.turnInRewardAttempt == id then return end
        ns.turnInRewardAttempt = id
        ns.turnInStatus = "Requested turn-in without a reward choice."
        -- The native completion dialog is already open. Never select gossip,
        -- pick a reward, or attempt to bypass a protected-action failure.
        GetQuestReward(0)
        ns.ScheduleSync()
    end
end

function ns.ReadOffers()
    ns.InvalidatePickupAvailability()
    ns.offered = {}
    if not ns.gossipReady then return end
    ns.ReadQuests()
    local quests = ns.ReadPublic(C_GossipInfo.GetAvailableQuests)
    if ns.Public(quests) and type(quests) == "table" then
        for _, quest in ipairs(quests) do
            if ns.Public(quest) and type(quest) == "table" then
                local id = quest.questID
                if ns.Public(id) and type(id) == "number" and id > 0
                    and id <= 2147483647 and id == math.floor(id) then ns.offered[id] = true end
            end
        end
    end
    if ns.ObserveQuestGiver and type(quests) == "table" then ns.ObserveQuestGiver(quests) end
    ns.RecordNPCOfferAvailability(quests)
    ns.SendOffers()
    ns.ScheduleSync()
    ns.Refresh()
    ns.AutoSelectGuideQuest()
end

function ns.ReadGreetingOffers()
    ns.InvalidatePickupAvailability()
    if not ns.greetingReady then return end
    ns.ReadQuests()
    local count = ns.ReadPublic(GetNumAvailableQuests)
    if not ns.GuideInteger(count, 100) then ns.greetingReadStatus = "Public quest count unavailable; no absence inferred."; return end
    local quests, slots = {}, {}
    for index = 1, count do
        -- Mainline's QuestFrame uses the fifth return as the public quest ID.
        -- Capability and returned fields must still be retested on Forever.
        local _, _, _, _, id = ns.ReadPublic(GetAvailableQuestInfo, index)
        if not ns.GuideInteger(id) or id <= 0 then ns.greetingReadStatus = "Public quest ID unavailable; no absence inferred."; return end
        local title = ns.SafeTitle(ns.ReadPublic(GetAvailableTitle, index))
        quests[#quests + 1] = {questID = id, title = title}
        slots[id] = index
    end
    ns.greetingSlots, ns.offered = slots, {}
    ns.greetingReadStatus = "Read " .. count .. " public quest(s) from the greeting list."
    for _, quest in ipairs(quests) do ns.offered[quest.questID] = true end
    ns.RecordNPCOfferAvailability(quests)
    ns.ObserveQuestGiver(quests)
    ns.SendOffers(); ns.ScheduleSync(); ns.Refresh()
    local stop = ns.selectedRoute and ns.selectedRoute.stops[1]
    if ns.Option("autoSelectQuests") and not ns.RouteInCombat() and stop and stop.kind == "a"
        and slots[stop.id] and type(SelectAvailableQuest) == "function" and ns.autoGossipAttempt ~= stop.id then
        ns.autoGossipAttempt = stop.id
        SelectAvailableQuest(slots[stop.id])
    end
end

function ns.InitializeOffers()
    ns.db.offerKnowledge = type(ns.db.offerKnowledge) == "table" and ns.db.offerKnowledge or {}
    ns.db.offerKnowledge[ns.self] = type(ns.db.offerKnowledge[ns.self]) == "table" and ns.db.offerKnowledge[ns.self] or {}
    for id, observation in pairs(ns.db.offerKnowledge[ns.self]) do
        if type(observation) ~= "table" or type(observation.context) ~= "string" or type(observation.offered) ~= "table" then
            ns.db.offerKnowledge[ns.self][id] = nil
        end
    end
    ns.gossipReady = C_GossipInfo and type(C_GossipInfo.GetAvailableQuests) == "function" or false
    ns.greetingReady = type(GetNumAvailableQuests) == "function" and type(GetAvailableQuestInfo) == "function"
    ns.offerReady = ns.gossipReady or ns.greetingReady or type(GetQuestID) == "function"
    if ns.greetingReady then ns.On("QUEST_GREETING", ns.ReadGreetingOffers) end
    if type(GetQuestID) == "function" then
        ns.On("QUEST_DETAIL", function()
            ns.InvalidatePickupAvailability()
            local id = GetQuestID()
            if ns.Public(id) and type(id) == "number" and id > 0
                and id <= 2147483647 and id == math.floor(id) then
                ns.offered = {[id] = true}
                local title = type(GetTitleText) == "function" and GetTitleText() or nil
                ns.ObserveQuestGiver({{questID = id, title = title}})
                ns.RecordNPCOfferAvailability({{questID = id}}, false)
                ns.SendOffers()
                ns.Refresh()
                ns.AutoAcceptOpenedQuest(id)
            end
        end)
        ns.On("QUEST_FINISHED", function()
            ns.greetingSlots, ns.autoGossipAttempt = nil, nil
            ns.autoAcceptAttempt, ns.turnInProgressAttempt, ns.turnInRewardAttempt = nil, nil, nil
            ns.offered = {}; ns.SendOffers(); ns.Refresh()
        end)
        ns.On("QUEST_PROGRESS", function() ns.AutoTurnInOpenedQuest("progress") end)
        ns.On("QUEST_COMPLETE", function() ns.AutoTurnInOpenedQuest("reward") end)
    end
    if not ns.gossipReady then return end
    ns.On("GOSSIP_SHOW", function() ns.ReadOffers() end)
    ns.On("GOSSIP_CLOSED", function()
        ns.autoGossipAttempt = nil
        ns.offered = {}
        ns.SendOffers()
        ns.Refresh()
    end)
end
