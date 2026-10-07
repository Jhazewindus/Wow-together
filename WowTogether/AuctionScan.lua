local addonName, ns = ...

-- Explicit scan, exact item queries, one outstanding request, >=1 s pacing.
local scan, pump
local function status(text)
    ns.auctionScanStatus = text
    if ns.RefreshAuctionGuideSearch then ns.RefreshAuctionGuideSearch() end
end
local function schedule(job)
    if scan ~= job or job.tickQueued then return end
    job.tickQueued = true
    C_Timer.After(1, function()
        job.tickQueued = nil
        if scan == job then pump(job) end
    end)
end
function ns.AuctionScanState() return scan end
function ns.CancelAuctionScan(reason)
    if not scan then return end
    scan = nil; status(reason or "Scan stopped. Saved prices retained.")
end
local function advance(job, priced)
    job.done = job.done + 1
    if priced then job.priced = job.priced + 1 end
    job.waiting, job.more = nil, nil
    if job.done >= #job.items then
        scan = nil
        ns.auctionScanSummary = {total = #job.items, priced = job.priced, requests = job.requests}
        status("Scan complete • " .. job.priced .. "/" .. #job.items .. " priced. Path updated.")
        ns.ProfessionPricesChanged()
    else schedule(job) end
end

function ns.AuctionScanResult(id, kind, full, priced)
    local job = scan
    local waiting = job and job.waiting
    if not waiting or waiting.id ~= id then return end
    waiting.kind = kind
    if full == false and waiting.pages < 3 and C_AuctionHouse
        and type(kind == "commodity" and C_AuctionHouse.RequestMoreCommoditySearchResults or C_AuctionHouse.RequestMoreItemSearchResults) == "function" then
        job.more = true; schedule(job)
    else advance(job, priced) end
end

pump = function(job)
    if scan ~= job then return end
    local id, target = ns.AuctionGuideContext()
    if not ns.AuctionHouseVisible() then ns.CancelAuctionScan("Scan stopped: auction house closed."); return end
    if id ~= job.professionID or target ~= job.target then ns.CancelAuctionScan("Guide changed. Start a new scan."); return end
    if ns.RouteInCombat() then status("Scan paused during combat."); return end
    if ns.ReadPublic(C_AuctionHouse.IsThrottledMessageSystemReady) ~= true then
        job.busy = (job.busy or 0) + 1
        if job.busy >= 60 then ns.CancelAuctionScan("Auction house busy. Start the scan again shortly."); return end
        status("Waiting for auction house…"); schedule(job); return
    end
    if job.waiting and not job.more then return end
    job.busy = 0
    local waiting = job.waiting
    if not waiting then
        local itemID = job.items[job.done + 1]
        local key = ns.ReadPublic(C_AuctionHouse.MakeItemKey, itemID)
        if not ns.Public(key) or type(key) ~= "table" or not ns.GuideInteger(key.itemID) or key.itemID ~= itemID then advance(job, false); return end
        waiting = {id = itemID, key = key, pages = 0}
        job.waiting = waiting
    end
    job.more = nil; waiting.pages = waiting.pages + 1
    status("Scanning " .. job.done + 1 .. "/" .. #job.items .. " • " .. ns.ItemName(waiting.id))
    job.requests = job.requests + 1
    local okay
    if waiting.pages == 1 then
        local order = Enum and Enum.AuctionHouseSortOrder and Enum.AuctionHouseSortOrder.Price
        local sorts = ns.GuideInteger(order, 100) and {{sortOrder = order, reverseSort = false}} or {}
        okay = pcall(C_AuctionHouse.SendSearchQuery, waiting.key, sorts, false)
    elseif waiting.kind == "commodity" then okay = pcall(C_AuctionHouse.RequestMoreCommoditySearchResults, waiting.id)
    else okay = pcall(C_AuctionHouse.RequestMoreItemSearchResults, waiting.key) end
    if not okay then advance(job, false); return end
    local ticket = {}; waiting.ticket = ticket
    C_Timer.After(20, function()
        if scan == job and job.waiting == waiting and waiting.ticket == ticket then
            advance(job, false)
        end
    end)
end

function ns.StartAuctionGuideScan()
    if scan then ns.CancelAuctionScan(); return end
    local id, target = ns.AuctionGuideContext()
    if not id then status("Choose a crafting guide first."); return end
    if not ns.GuideInteger(target, 300) or target < 1 then status("Choose a profession skill goal first."); return end
    if not ns.AuctionHouseVisible() then status("Open an auction house first."); return end
    if ns.RouteInCombat() then status("Start the scan after combat."); return end
    if not C_AuctionHouse or type(C_AuctionHouse.MakeItemKey) ~= "function" or type(C_AuctionHouse.SendSearchQuery) ~= "function"
        or type(C_AuctionHouse.IsThrottledMessageSystemReady) ~= "function" or not ns.auctionCommodityEventReady or not ns.auctionItemEventReady
        or not C_Timer or type(C_Timer.After) ~= "function" then
        status("Scan unavailable. Use the material Search buttons."); return
    end
    local job = {professionID = id, target = target, done = 0, priced = 0, requests = 0}
    scan = job; status("Preparing material scan…")
    local worker = coroutine.create(function() return ns.ProfessionMarketItems(id, target, true) end)
    local function prepare()
        if scan ~= job then return end
        if not ns.AuctionHouseVisible() then ns.CancelAuctionScan("Scan stopped: auction house closed."); return end
        local okay, result = coroutine.resume(worker)
        if not okay then ns.CancelAuctionScan("Refresh the guide, then retry scanning."); return end
        if coroutine.status(worker) == "dead" then
            job.items = result
            if #result == 0 then ns.CancelAuctionScan("No materials to scan for this goal."); return end
            schedule(job)
        else C_Timer.After(0, prepare) end
    end
    C_Timer.After(0, prepare)
end

local previousRegen = ns.handlers.PLAYER_REGEN_ENABLED
ns.On("PLAYER_REGEN_ENABLED", function(...)
    if previousRegen then previousRegen(...) end
    if scan and scan.items then schedule(scan) end
end)
ns.On("AUCTION_HOUSE_BROWSE_RESULTS_UPDATED", function()
    if scan then ns.CancelAuctionScan("Scan stopped for auction browsing.") end
end)
