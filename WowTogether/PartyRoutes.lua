local addonName, ns = ...

local revision, transfers, received = 0, {}, {}
local modes = {current = true, bundle = true, circuit = true, normal = true, dungeon = true, zone = true, chain = true}
ns.partyRouteStatus = "No party route has been started."

function ns.RouteHistoryScope(records)
    local ids, count = {}, 0
    local function add(id, depth)
        if not ns.GuideInteger(id) or id <= 0 or ids[id] or count >= 512 then return end
        ids[id], count = true, count + 1
        if (depth or 0) < 24 then
            for _, previous in ipairs(ns.CataloguePrerequisiteIDs(id)) do add(previous, (depth or 0) + 1) end
        end
    end
    for _, record in ipairs(records or {}) do add(record.id) end
    for _, record in ipairs(records or {}) do
        for _, previous in ipairs(ns.CataloguePrerequisiteIDs(record.id)) do add(previous) end
    end
    for _, record in ipairs(records or {}) do
        local quest = ns.CatalogueQuest(record.id)
        for _, id in ipairs(quest and quest.series or {}) do add(id) end
    end
    ns.partyRouteHistoryScope = ids
end

function ns.StartPartyRoute(guide)
    if not guide or guide.personal then return false end
    if not ns.PartyFeaturesEnabled() then return ns.ShowGuideOnMap(guide) end
    if ns.RouteInCombat() then
        ns.pendingPartyRouteStart = guide
        ns.guideAction = "Your route will start after combat."; ns.Refresh(); return false
    end
    if guide.fullGuide and not (ns.preparedLevelingRoute and ns.preparedLevelingRoute.guide == guide) then
        return ns.PlanLevelingGuide(guide, true)
    end
    ns.RouteHistoryScope(guide.records)
    if not ns.ShowGuideOnMap(guide) then return false end
    if not ns.selectedRoute or ns.selectedRoute.complete then ns.partyRouteStatus = "Guide already completed for your party."; return false end
    local ids, seen = {}, {}
    -- Share the selected quests, not another player's stage or coordinates.
    for _, stop in ipairs(ns.selectedRoute.stops) do
        if #ids < 20 and not seen[stop.id] then ids[#ids + 1] = stop.id; seen[stop.id] = true end
    end
    for _, record in ipairs(guide.records or {}) do
        if #ids < 20 and not seen[record.id] then ids[#ids + 1] = record.id; seen[record.id] = true end
    end
    if #ids == 0 then return false end
    local mode = modes[guide.mode] and guide.mode or "normal"
    if #(ns.partyNames or {}) == 0 then
        ns.partyRouteStatus = "Route started for you. Join a party to invite friends."
        ns.guideAction = ns.partyRouteStatus; ns.Refresh(); return true
    end
    local target = guide.target and guide.target.id or ids[1]
    if not seen[target] then target = ids[1] end
    revision = revision + 1
    local total, queued = math.ceil(#ids / 8), true
    for part = 1, total do
        local values = {}
        for index = (part - 1) * 8 + 1, math.min(part * 8, #ids) do
            local id = ids[index]
            values[#values + 1] = tostring(id) .. (mode == "bundle" and guide.pickupIDs and guide.pickupIDs[id] and "+" or "")
        end
        local packet = table.concat({"1", "V", revision, part, total, mode, ns.selectedRoute.mapID > 0 and ns.selectedRoute.mapID or guide.homeMapID,
            target, table.concat(values, ",")}, "|")
        if mode == "zone" or mode == "chain" then packet = packet .. "|" .. (guide.guideKey or guide.key) .. "|" .. guide.rangeLow .. "|" .. guide.rangeHigh end
        if guide.fixedRoute then packet = packet .. "|fixed" end
        if guide.catchup then packet = packet .. "|catchup" end
        if not ns.QueueMessage(packet) then queued = false end
    end
    ns.partyRouteStatus = queued and "Route started. Invitations queued for your party." or "Route started locally; invitation queue was full. Try Start route again."
    if #guide.records > #ids and mode ~= "zone" and mode ~= "chain" then
        ns.partyRouteStatus = ns.partyRouteStatus .. " Shared the first " .. #ids .. " quests; larger selections are limited."
    end
    ns.guideAction = ns.partyRouteStatus
    ns.ScheduleSync(); ns.Refresh()
    return true
end

local function currentPeer(sender)
    if not ns.PartyFeaturesEnabled() then return false end
    for _, name in ipairs(ns.partyNames or {}) do if name == sender then return true end end
    return false
end

function ns.BuildInvitedGuide(invite)
    if invite.mode == "zone" or invite.mode == "chain" then
        local guide = ns.InvitedLevelingGuide(invite)
        if guide then
            if invite.catchup then
                local catchup, reason = ns.PartyCatchupGuide(guide)
                if catchup then catchup.sharedBy = invite.sender end
                return catchup, reason
            end
            return guide
        end
        return nil, "The shared zone/questline guide is missing from this catalogue. Update every client."
    end
    local records, live, missing = {}, ns.RouteRecords(), 0
    for _, id in ipairs(invite.ids) do
        local record = ns.CatalogueRecord(id) or live[id] or ns.GuideRecord(id)
        if record then records[#records + 1] = record else missing = missing + 1 end
    end
    if #records == 0 then return nil, "This client has no quest records for the shared route. Sync and update every party member." end
    if invite.mode == "dungeon" then
        for _, group in ipairs(ns.DungeonGroups()) do
            for _, id in ipairs(group.ids) do if id == invite.target then return ns.DungeonGuide(group) end end
        end
    end
    local mode = invite.mode ~= "normal" and invite.mode or nil
    local target = records[1]
    for _, record in ipairs(records) do if record.id == invite.target then target = record end end
    return {key = "party:" .. invite.sender .. ":" .. invite.revision, title = mode == "current" and "Our current party quests"
            or (mode == "bundle" and "Our quests + nearby pickups")
            or (mode == "circuit" and "Party quest circuit" or target.seriesName or target.title),
        mode = mode, mapID = invite.mapID, records = records, target = target, focusKey = ns.self, pickupIDs = invite.pickupIDs,
        kind = "Party route", zone = ns.MapName(invite.mapID), profilesReady = true, sharedBy = invite.sender},
        missing > 0 and (missing .. " quest record(s) are unavailable on this client.") or nil
end

function ns.FollowPartyRoute(invite)
    if not currentPeer(invite.sender) then ns.partyRouteStatus = "The route sender left the party."; return false end
    if ns.RouteInCombat() then
        ns.pendingPartyRouteFollow = invite
        ns.partyRouteStatus = "The party route will open after combat."; return false
    end
    local guide, reason = ns.BuildInvitedGuide(invite)
    if not guide then
        local records = {}; for _, id in ipairs(invite.ids) do records[#records + 1] = {id = id} end
        ns.RouteHistoryScope(records); ns.ScheduleSync()
        ns.waitingPartyRoute, ns.partyRouteStatus, ns.guideAction = invite, reason, reason
        ns.Refresh(); return false
    end
    ns.RouteHistoryScope(guide.records)
    ns.ScheduleSync()
    if guide.fullGuide then
        ns.partyRouteStatus = "Generating " .. ns.MemberLabel(invite.sender) .. "'s guide from your party's progress."
        return ns.ShowGuideOnMap(guide)
    end
    local plan = ns.BuildGuideRoute(guide, false)
    if #plan.stops == 0 then
        local _, requirement = ns.CatalogueAllowed(guide.target.id, ns.profile, ns.self)
        ns.waitingPartyRoute = invite
        ns.partyRouteStatus = "Waiting for an eligible next step: " .. (requirement or "sync the party quest logs and prerequisite history.")
        ns.guideAction = ns.partyRouteStatus; ns.Refresh(); return false
    end
    if not ns.ShowGuideOnMap(guide) then
        ns.partyRouteStatus = "No eligible next step yet. Sync prerequisite history or finish the required earlier quest."
        ns.guideAction = ns.partyRouteStatus; ns.Refresh(); return false
    end
    ns.partyRouteStatus = "Following " .. ns.MemberLabel(invite.sender) .. "'s route, using your party's progress."
    if reason then ns.partyRouteStatus = ns.partyRouteStatus .. " " .. reason end
    ns.guideAction = ns.partyRouteStatus; ns.Refresh(); return true
end

function ns.ShowPartyRouteInvite()
    if not ns.PartyFeaturesEnabled() then return end
    local invite = ns.pendingPartyRouteInvite
    if not invite or ns.RouteInCombat() then return end
    if not currentPeer(invite.sender) then ns.pendingPartyRouteInvite = nil; return end
    if not ns.partyRoutePrompt then
        local frame = CreateFrame("Frame", "WowTogetherPartyRoutePrompt", UIParent, "BackdropTemplate")
        ns.partyRoutePrompt = frame
        frame:SetSize(500, 210); frame:SetPoint("CENTER"); frame:SetClampedToScreen(true); frame:SetFrameStrata("DIALOG"); ns.UIPanel(frame)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 18); frame.title:SetPoint("TOPLEFT", 22, -22); frame.title:SetWidth(456)
        frame.text = ns.UILabel(frame, nil, 12); frame.text:SetPoint("TOPLEFT", 22, -55); frame.text:SetSize(456, 100)
        frame.follow = ns.UIButton(frame, "Follow route", 190, function()
            local request = frame.invite; frame:Hide()
            if request then ns.FollowPartyRoute(request) end
        end, true); frame.follow:SetPoint("BOTTOMLEFT", 22, 18)
        frame.keep = ns.UIButton(frame, "Keep my route", 190, function() ns.waitingPartyRoute = nil; frame:Hide() end); frame.keep:SetPoint("BOTTOMRIGHT", -22, 18)
        ns.ResizeChoicePopup(frame, "party-invite", {frame.follow, frame.keep}, 500, 210)
    end
    local frame = ns.partyRoutePrompt
    frame.invite = invite; ns.pendingPartyRouteInvite = nil
    frame.title:SetText(ns.MemberLabel(invite.sender) .. " started a route")
    frame.text:SetText((invite.catchup and "Catch up party" or invite.guideKey and "Full zone/questline guide" or ns.QuestTitle(invite.target))
        .. " • " .. (invite.guideKey and ("levels " .. invite.rangeLow .. "–" .. invite.rangeHigh) or (#invite.ids .. " quest(s)")) .. " • " .. ns.MapName(invite.mapID)
        .. "\n\nFollow the same quest selection using your own progress. Ready turn-ins and unfinished friends stay on the plan.")
    frame:Show()
end

function ns.ReceivePartyRouteMessage(message, sender)
    if string.sub(message, 1, 4) ~= "1|V|" then return false end
    if not currentPeer(sender) then return true, false, "party route sender left roster" end
    local catchup = string.sub(message, -8) == "|catchup"
    if catchup then message = string.sub(message, 1, -9) end
    local fixedRoute = string.sub(message, -6) == "|fixed"
    if fixedRoute then message = string.sub(message, 1, -7) end
    local rev, part, total, mode, mapID, target, payload = string.match(message, "^1|V|(%d+)|(%d+)|(%d+)|(%a+)|(%d+)|(%d+)|([%d,+]+)$")
    local guideKey, rangeLow, rangeHigh
    if not rev then
        rev, part, total, mode, mapID, target, payload, guideKey, rangeLow, rangeHigh = string.match(message,
            "^1|V|(%d+)|(%d+)|(%d+)|(%a+)|(%d+)|(%d+)|([%d,+]+)|([%w%-:/]+)|(%d+)|(%d+)$")
        rangeLow, rangeHigh = tonumber(rangeLow), tonumber(rangeHigh)
    end
    rev, part, total, mapID, target = tonumber(rev), tonumber(part), tonumber(total), tonumber(mapID), tonumber(target)
    if not modes[mode] or not ns.GuideInteger(rev, 2147483647) or rev < 1 or not ns.GuideInteger(total, 3) or total < 1
        or not ns.GuideInteger(part, total) or part < 1 or not ns.GuideInteger(mapID, 1000000)
        or mapID < 1 and mode ~= "zone" and mode ~= "chain"
        or not ns.GuideInteger(target, 2147483647) or target < 1 then return true, false, "invalid party route envelope" end
    if guideKey and (mode ~= "zone" and mode ~= "chain" or #guideKey > 100
        or not ns.GuideInteger(rangeLow, 255) or rangeLow < 1 or not ns.GuideInteger(rangeHigh, 255) or rangeHigh < rangeLow) then
        return true, false, "invalid full guide identity"
    end
    if (mode == "zone" or mode == "chain") and not guideKey then return true, false, "full guide identity missing" end
    if fixedRoute and not guideKey then return true, false, "fixed route requires full guide identity" end
    if catchup and (not guideKey or mode ~= "zone" or fixedRoute) then return true, false, "invalid catch-up route identity" end
    if rev <= (received[sender] or 0) then return true, false, "old party route invitation" end
    local ids, seen, pickupIDs, canonical = {}, {}, {}, {}
    for value in string.gmatch(payload, "[^,]+") do
        local number, pickup = string.match(value, "^(%d+)(%+?)$")
        local id = tonumber(number)
        if not ns.GuideInteger(id, 2147483647) or id <= 0 or seen[id] or #ids >= 8 then return true, false, "invalid party route quest IDs" end
        if pickup == "+" and mode ~= "bundle" then return true, false, "pickup roles require a bundled route" end
        ids[#ids + 1] = id; seen[id] = true
        if pickup == "+" then pickupIDs[id] = true end
        canonical[#canonical + 1] = tostring(id) .. pickup
    end
    if table.concat(canonical, ",") ~= payload then return true, false, "invalid party route payload" end
    local bucket = transfers[sender]
    if bucket and rev < bucket.revision then return true, false, "older party route transfer" end
    if not bucket or rev > bucket.revision then
        bucket = {revision = rev, total = total, mode = mode, mapID = mapID, target = target, parts = {}, pickupIDs = {}, count = 0,
            guideKey = guideKey, rangeLow = rangeLow, rangeHigh = rangeHigh, fixedRoute = fixedRoute, catchup = catchup}
        transfers[sender] = bucket
        if C_Timer and type(C_Timer.After) == "function" then
            C_Timer.After(300, function() if transfers[sender] == bucket then transfers[sender] = nil end end)
        end
    end
    if bucket.total ~= total or bucket.mode ~= mode or bucket.mapID ~= mapID or bucket.target ~= target
        or bucket.guideKey ~= guideKey or bucket.rangeLow ~= rangeLow or bucket.rangeHigh ~= rangeHigh
        or bucket.fixedRoute ~= fixedRoute or bucket.catchup ~= catchup
        or bucket.parts[part] then return true, false, "duplicate or inconsistent party route part" end
    bucket.parts[part] = ids; bucket.count = bucket.count + 1
    for id in pairs(pickupIDs) do bucket.pickupIDs[id] = true end
    if bucket.count ~= total then return true, true end
    local all, unique = {}, {}
    for index = 1, total do
        for _, id in ipairs(bucket.parts[index]) do
            if unique[id] or #all >= 20 then transfers[sender] = nil; return true, false, "party route quest limit" end
            all[#all + 1] = id; unique[id] = true
        end
    end
    if not unique[target] then transfers[sender] = nil; return true, false, "party route target is outside selection" end
    received[sender], transfers[sender] = rev, nil
    ns.pendingPartyRouteInvite = {sender = sender, revision = rev, ids = all, mode = mode, mapID = mapID, target = target, pickupIDs = bucket.pickupIDs,
        guideKey = guideKey, rangeLow = rangeLow, rangeHigh = rangeHigh, fixedRoute = fixedRoute, catchup = catchup}
    ns.partyRouteStatus = "Route invitation received from " .. ns.MemberLabel(sender) .. "."
    ns.ShowPartyRouteInvite()
    return true, true
end

function ns.ResetPartyRoutePeer(sender)
    transfers[sender], received[sender] = nil, nil
end

function ns.PrunePartyRoutes()
    for sender in pairs(transfers) do if not currentPeer(sender) then ns.ResetPartyRoutePeer(sender) end end
    for sender in pairs(received) do if not currentPeer(sender) then received[sender] = nil end end
    local prompt = ns.partyRoutePrompt
    if prompt and prompt.invite and not currentPeer(prompt.invite.sender) then prompt:Hide() end
    if ns.pendingPartyRouteInvite and not currentPeer(ns.pendingPartyRouteInvite.sender) then ns.pendingPartyRouteInvite = nil end
    if ns.waitingPartyRoute and not currentPeer(ns.waitingPartyRoute.sender) then ns.waitingPartyRoute = nil end
end

function ns.QueuePartyRouteFollow()
    if not ns.PartyFeaturesEnabled() then return end
    local invite = ns.waitingPartyRoute
    if not invite or ns.partyFollowQueued or ns.RouteInCombat() or not C_Timer or type(C_Timer.After) ~= "function" then return end
    local context = table.concat({ns.syncStats.accepted, ns.activityRevision or 0, ns.questEntries or 0,
        ns.profile and ns.profile.level or 0}, ":")
    if ns.partyFollowContext == context then return end
    ns.partyFollowContext, ns.partyFollowQueued = context, true
    C_Timer.After(0.2, function()
        ns.partyFollowQueued = nil
        if ns.waitingPartyRoute == invite then ns.FollowPartyRoute(invite) end
    end)
end

function ns.FlushPartyRoutes()
    if not ns.PartyFeaturesEnabled() then return end
    if ns.pendingPartyRouteStart then local guide = ns.pendingPartyRouteStart; ns.pendingPartyRouteStart = nil; ns.StartPartyRoute(guide) end
    if ns.pendingPartyRouteFollow then local invite = ns.pendingPartyRouteFollow; ns.pendingPartyRouteFollow = nil; ns.FollowPartyRoute(invite) end
    ns.ShowPartyRouteInvite()
end
