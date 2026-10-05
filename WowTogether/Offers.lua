local addonName, ns = ...

ns.offered = {}
ns.turnInStatus = "Automatic turn-in is off."

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
    ns.offered = {}
    if not ns.gossipReady then return end
    local quests = C_GossipInfo.GetAvailableQuests()
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
    ns.SendOffers()
    ns.Refresh()
end

function ns.InitializeOffers()
    ns.gossipReady = C_GossipInfo and type(C_GossipInfo.GetAvailableQuests) == "function" or false
    ns.offerReady = ns.gossipReady or type(GetQuestID) == "function"
    if type(GetQuestID) == "function" then
        ns.On("QUEST_DETAIL", function()
            local id = GetQuestID()
            if ns.Public(id) and type(id) == "number" and id > 0
                and id <= 2147483647 and id == math.floor(id) then
                ns.offered = {[id] = true}
                local title = type(GetTitleText) == "function" and GetTitleText() or nil
                ns.ObserveQuestGiver({{questID = id, title = title}})
                ns.SendOffers()
                ns.Refresh()
                ns.AutoAcceptOpenedQuest(id)
            end
        end)
        ns.On("QUEST_FINISHED", function()
            ns.autoAcceptAttempt, ns.turnInProgressAttempt, ns.turnInRewardAttempt = nil, nil, nil
            ns.offered = {}; ns.SendOffers(); ns.Refresh()
        end)
        ns.On("QUEST_PROGRESS", function() ns.AutoTurnInOpenedQuest("progress") end)
        ns.On("QUEST_COMPLETE", function() ns.AutoTurnInOpenedQuest("reward") end)
    end
    if not ns.gossipReady then return end
    ns.On("GOSSIP_SHOW", function() ns.ReadOffers() end)
    ns.On("GOSSIP_CLOSED", function()
        ns.offered = {}
        ns.SendOffers()
        ns.Refresh()
    end)
end
