local addonName, ns = ...

-- One exact-item request at a time, paced at >=1 s. Missing metadata and
-- missing server events both have bounded waits, independent of UI rendering.
local scan, pump
local function status(text)
    ns.auctionScanStatus = text
    if ns.RefreshAuctionGuideSearch then
        local okay, err = pcall(ns.RefreshAuctionGuideSearch)
        if not okay then ns.auctionScanUIError = tostring(err) end
    end
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
    if scan.items then
        ns.auctionScanSummary = {total = #scan.items, done = scan.done, priced = scan.priced,
            skipped = scan.skipped, requests = scan.requests, failures = scan.failures, cancelled = true}
    end
    scan = nil; status(reason or "Scan stopped. Saved prices retained.")
end
local function advance(job, priced, reason)
    if scan ~= job then return end
    if reason then
        job.skipped = job.skipped + 1
        if #job.failures < 20 then
            job.failures[#job.failures + 1] = {itemID = job.items[job.done + 1], reason = reason}
        end
    end
    job.done = job.done + 1
    if priced then job.priced = job.priced + 1 end
    job.waiting, job.more = nil, nil
    if job.done >= #job.items then
        scan = nil
        ns.auctionScanSummary = {total = #job.items, priced = job.priced, skipped = job.skipped,
            requests = job.requests, failures = job.failures}
        status("Scan complete • " .. job.priced .. "/" .. #job.items .. " priced"
            .. (job.skipped > 0 and " • " .. job.skipped .. " skipped" or "") .. ". Path updated.")
        ns.ProfessionPricesChanged()
    else schedule(job) end
end

function ns.AuctionScanResult(id, kind, full, priced)
    local job = scan
    local waiting = job and job.waiting
    if not waiting or waiting.phase ~= "query" or waiting.id ~= id then return end
    waiting.kind = kind
    if full == false and waiting.pages < 3 and C_AuctionHouse
        and type(kind == "commodity" and C_AuctionHouse.RequestMoreCommoditySearchResults or C_AuctionHouse.RequestMoreItemSearchResults) == "function" then
        job.more = true; schedule(job)
    else advance(job, priced) end
end

local function watch(job, waiting, ticket)
    C_Timer.After(1, function()
        if scan ~= job or job.waiting ~= waiting or waiting.ticket ~= ticket then return end
        if not ns.AuctionHouseVisible() then ns.CancelAuctionScan("Scan stopped: auction house closed."); return end
        local id, target = ns.AuctionGuideContext()
        if id ~= job.professionID or target ~= job.target then ns.CancelAuctionScan("Guide changed. Start a new scan."); return end
        waiting.elapsed = waiting.elapsed + 1
        if waiting.elapsed >= 20 then advance(job, false, "No auction reply within 20 seconds"); return end
        status("Scanning " .. job.done + 1 .. "/" .. #job.items .. " • " .. waiting.name
            .. " • waiting " .. (20 - waiting.elapsed) .. "s")
        watch(job, waiting, ticket)
    end)
end

pump = function(job)
    if scan ~= job then return end
    local id, target = ns.AuctionGuideContext()
    if not ns.AuctionHouseVisible() then ns.CancelAuctionScan("Scan stopped: auction house closed."); return end
    if id ~= job.professionID or target ~= job.target then ns.CancelAuctionScan("Guide changed. Start a new scan."); return end
    if ns.RouteInCombat() then status("Scan paused during combat."); return end
    local waiting = job.waiting
    if waiting and waiting.phase == "query" and not job.more then return end
    if not waiting then
        waiting = {id = job.items[job.done + 1], phase = "metadata", pages = 0, loads = 0}
        job.waiting = waiting
    end
    if waiting.phase == "metadata" then
        -- The beta can leave a silent query pending for an uncached/invalid
        -- ID. Load its public metadata first; do not query an unresolved ID.
        waiting.name = C_Item and ns.SafeTitle(ns.ReadPublic(C_Item.GetItemInfo, waiting.id))
        if not waiting.name and C_Item and type(C_Item.GetItemInfo) == "function" then
            if waiting.loads == 0 then ns.pendingItems[waiting.id], ns.failedItemLoads[waiting.id] = nil, nil end
            ns.ItemName(waiting.id)
            waiting.loads = waiting.loads + 1
            if ns.failedItemLoads[waiting.id] or waiting.loads > 5 then
                advance(job, false, "Item details unavailable"); return
            end
            status("Loading material " .. job.done + 1 .. "/" .. #job.items .. " • " .. (6 - waiting.loads) .. "s")
            schedule(job); return
        end
        waiting.name = waiting.name or ns.ItemName(waiting.id)
        waiting.key = ns.ReadPublic(C_AuctionHouse.MakeItemKey, waiting.id)
        if not ns.Public(waiting.key) or type(waiting.key) ~= "table"
            or not ns.GuideInteger(waiting.key.itemID) or waiting.key.itemID ~= waiting.id then
            advance(job, false, "Item key unavailable"); return
        end
        waiting.phase = "ready"
    end
    if ns.ReadPublic(C_AuctionHouse.IsThrottledMessageSystemReady) ~= true then
        job.busy = (job.busy or 0) + 1
        if job.busy >= 60 then ns.CancelAuctionScan("Auction house busy. Start the scan again shortly."); return end
        status("Waiting for auction house…"); schedule(job); return
    end
    job.busy = 0
    job.more = nil; waiting.pages = waiting.pages + 1
    waiting.phase, waiting.elapsed = "query", 0
    local ticket = {}; waiting.ticket = ticket
    -- Install before name/UI/query calls: a failing call or synchronous result
    -- cannot strand the queue or advance a newer request from an old timer.
    watch(job, waiting, ticket)
    status("Scanning " .. job.done + 1 .. "/" .. #job.items .. " • " .. waiting.name)
    job.requests = job.requests + 1
    local okay, result
    if waiting.pages == 1 then
        local order = Enum and Enum.AuctionHouseSortOrder and Enum.AuctionHouseSortOrder.Price
        local sorts = ns.GuideInteger(order, 100) and {{sortOrder = order, reverseSort = false}} or {}
        okay, result = pcall(C_AuctionHouse.SendSearchQuery, waiting.key, sorts, false)
    elseif waiting.kind == "commodity" then okay, result = pcall(C_AuctionHouse.RequestMoreCommoditySearchResults, waiting.id)
    else okay, result = pcall(C_AuctionHouse.RequestMoreItemSearchResults, waiting.key) end
    if scan == job and job.waiting == waiting and waiting.ticket == ticket
        and (not okay or ns.Public(result) and result == false) then
        advance(job, false, "Auction query rejected")
    end
end

function ns.StartAuctionGuideScan()
    if scan then ns.CancelAuctionScan(); return end
    if ns.ClearGuideAuctionQuantity then ns.ClearGuideAuctionQuantity() end
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
    local job = {professionID = id, target = target, done = 0, priced = 0, skipped = 0, requests = 0, failures = {}}
    scan = job; ns.auctionScanSummary, ns.auctionScanUIError = nil, nil; status("Preparing material scan…")
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
