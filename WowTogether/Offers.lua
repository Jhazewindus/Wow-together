local addonName, ns = ...

ns.offered = {}

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
        ns.On("QUEST_FINISHED", function() ns.autoAcceptAttempt = nil; ns.offered = {}; ns.SendOffers(); ns.Refresh() end)
    end
    if not ns.gossipReady then return end
    ns.On("GOSSIP_SHOW", function() ns.ReadOffers() end)
    ns.On("GOSSIP_CLOSED", function()
        ns.offered = {}
        ns.SendOffers()
        ns.Refresh()
    end)
end
