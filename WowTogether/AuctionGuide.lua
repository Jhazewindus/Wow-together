local addonName, ns = ...

local panel, forecast, nativePosition, restorePending
local function shown(frame) return frame and ns.ReadPublic(frame.IsShown, frame) == true end
function ns.AuctionHouseVisible()
    return ns.auctionHouseOpen and (shown(AuctionHouseFrame) or shown(AuctionFrame)) or false
end
local function status(text)
    ns.auctionGuideStatus, ns.auctionScanStatus = text, nil
    if ns.shoppingWindow then ns.shoppingWindow.status:SetText(text) end
    if panel then panel.status:SetText(text) end
end

function ns.AuctionGuideContext()
    local guide = ns.routeSelection
    if guide and guide.mode == "profession" and ns.professionData[guide.professionID] then
        return guide.professionID, guide.targetSkill
    end
    local context = ns.shoppingContext
    if context and ns.professionData[context.professionID] and shown(ns.shoppingWindow) then
        return context.professionID, context.target
    end
end

function ns.SearchGuideAuctionItem(id)
    if not ns.GuideInteger(id) or id <= 0 then return false end
    ns.CancelAuctionScan("Scan stopped for your material search.")
    if ns.RouteInCombat() then status("Search after combat."); return false end
    if not ns.auctionHouseOpen then status("Open an auction house first."); return false end
    local name = C_Item and ns.SafeTitle(ns.ReadPublic(C_Item.GetItemInfo, id))
    if not name then ns.ItemName(id); status("Item name loading. Try again shortly."); return false end
    if shown(AuctionHouseFrame) and C_AuctionHouse and type(C_AuctionHouse.SendBrowseQuery) == "function"
        and type(AuctionHouseFrame.SendBrowseQuery) == "function" and type(AuctionHouseFrame.SetSearchText) == "function"
        and type(AuctionHouseFrame.GetCategoriesList) == "function" then
        if type(C_AuctionHouse.IsThrottledMessageSystemReady) == "function"
            and ns.ReadPublic(C_AuctionHouse.IsThrottledMessageSystemReady) ~= true then
            status("Auction search is busy. Try again shortly."); return false
        end
        if type(AreSortTypesLoaded) == "function" and ns.ReadPublic(AreSortTypesLoaded) ~= true then
            status("Auction search is loading. Try again shortly."); return false
        end
        local categories = ns.ReadPublic(AuctionHouseFrame.GetCategoriesList, AuctionHouseFrame)
        if not categories or type(categories.SetSelectedCategory) ~= "function" then status("Choose the Buy tab to search."); return false end
        categories:SetSelectedCategory(nil)
        AuctionHouseFrame:SendBrowseQuery(name, nil, nil, {})
        AuctionHouseFrame:SetSearchText(name)
        status("Searching " .. name .. "."); return true
    end
    if shown(AuctionFrame) and shown(AuctionFrameBrowse) and BrowseName
        and type(BrowseName.SetText) == "function" and type(QueryAuctionItems) == "function"
        and type(CanSendAuctionQuery) == "function" then
        if ns.ReadPublic(CanSendAuctionQuery, "list") ~= true then status("Auction search is busy. Try again shortly."); return false end
        AuctionFrameBrowse.page = 0
        AuctionFrameBrowse.selectedCategoryIndex, AuctionFrameBrowse.selectedSubCategoryIndex,
            AuctionFrameBrowse.selectedSubSubCategoryIndex, AuctionFrameBrowse.qualityIndex = nil, nil, nil, nil
        BrowseName:SetText(name)
        if BrowseMinLevel then BrowseMinLevel:SetText("") end
        if BrowseMaxLevel then BrowseMaxLevel:SetText("") end
        if IsUsableCheckButton then IsUsableCheckButton:SetChecked(false) end
        QueryAuctionItems(name, nil, nil, 0, false, nil, false, true, nil)
        status("Searching " .. name .. "."); return true
    end
    status("Open the auction Buy / Browse tab to search."); return false
end

-- Make space only when the normal auction placement leaves no room on its
-- left. Remember/restore the native anchors; never move it during combat.
local function restoreNativePosition()
    if not nativePosition then return end
    if ns.RouteInCombat() then restorePending = true; return end
    local frame = nativePosition.frame
    frame:ClearAllPoints()
    for _, point in ipairs(nativePosition.points) do frame:SetPoint(unpack(point, 1, 5)) end
    nativePosition, restorePending = nil, nil
end
local function makeRoom(parent)
    if nativePosition or ns.RouteInCombat() then return end
    local left, top = ns.ReadPublic(parent.GetLeft, parent), ns.ReadPublic(parent.GetTop, parent)
    local width, screen = ns.ReadPublic(parent.GetWidth, parent), ns.ReadPublic(UIParent.GetWidth, UIParent)
    local scale = ns.ReadPublic(parent.GetEffectiveScale, parent)
    local uiScale = ns.ReadPublic(UIParent.GetEffectiveScale, UIParent)
    if not ns.Public(left) or type(left) ~= "number" or not ns.Public(top) or type(top) ~= "number"
        or not ns.Public(width) or type(width) ~= "number" or not ns.Public(screen) or type(screen) ~= "number"
        or not ns.Public(scale) or type(scale) ~= "number" or not ns.Public(uiScale) or type(uiScale) ~= "number" or uiScale <= 0 then return end
    left, top, width = left * scale / uiScale, top * scale / uiScale, width * scale / uiScale
    local required = 338
    if left >= required or required + width > screen - 12 then return end
    local count = ns.ReadPublic(parent.GetNumPoints, parent)
    if not ns.GuideInteger(count, 10) or count < 1 then return end
    local points = {}
    for index = 1, count do
        local okay, point, relative, relativePoint, x, y = pcall(parent.GetPoint, parent, index)
        if not okay or not ns.Public(point) or not ns.Public(relative) or not ns.Public(relativePoint)
            or not ns.Public(x) or not ns.Public(y) then return end
        points[index] = {point, relative, relativePoint, x, y}
    end
    nativePosition = {frame = parent, points = points}
    parent:ClearAllPoints(); parent:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", required * uiScale / scale, top * uiScale / scale)
end

local function create(parent)
    if panel then return panel end
    panel = CreateFrame("Frame", "WowTogetherAuctionMaterials", parent, "BackdropTemplate")
    ns.auctionGuideToolbar = panel
    panel:SetSize(320, 480); ns.UIPanel(panel); panel:SetFrameStrata("DIALOG"); panel:SetClampedToScreen(true)
    panel.title = ns.UILabel(panel, nil, 17, ns.UIColors.gold); panel.title:SetPoint("TOPLEFT", 14, -15); panel.title:SetText("Crafting materials")
    ns.UIClose(panel, function() panel.dismissed = true; panel:Hide(); ns.CancelAuctionScan() end)
    panel.scan = ns.UIButton(panel, "Scan auction house", 292, ns.StartAuctionGuideScan)
    panel.scan:SetPoint("TOPLEFT", 14, -46); ns.UIButtonTone(panel.scan, true)
    panel.profession = ns.UILabel(panel, nil, 12); panel.profession:SetPoint("TOPLEFT", 14, -92); panel.profession:SetWidth(145)
    panel.goal = ns.UIDropdown(panel, {{75,"Goal: 75"},{150,"Goal: 150"},{225,"Goal: 225"},{300,"Goal: 300"}}, 135, function(value)
        local id = ns.AuctionGuideContext()
        if not id then return end
        ns.CancelAuctionScan("Goal changed. Start a new scan.")
        ns.ProfessionGoal(id, value)
        local guide = ns.routeSelection
        if guide and guide.mode == "profession" and guide.professionID == id then
            guide.targetSkill, guide.professionBatch = value, nil
        elseif ns.shoppingContext then ns.shoppingContext.target = value end
        ns.ProfessionPricesChanged()
    end)
    panel.goal:SetPoint("TOPRIGHT", -14, -84)
    panel.notice = ns.UILabel(panel, nil, 11, ns.UIColors.muted)
    panel.notice:SetPoint("TOPLEFT", 14, -120); panel.notice:SetSize(292, 48); panel.notice:SetWordWrap(true)
    local scroll = CreateFrame("ScrollFrame", nil, panel, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", 14, -178); scroll:SetPoint("BOTTOMRIGHT", -32, 44)
    panel.child = CreateFrame("Frame", nil, scroll); panel.child:SetSize(274, 100); scroll:SetScrollChild(panel.child)
    panel.rows = {}
    panel.status = ns.UILabel(panel, nil, 10, ns.UIColors.muted)
    panel.status:SetPoint("BOTTOMLEFT", 14, 9); panel.status:SetSize(292, 28); panel.status:SetWordWrap(true)
    ns.UIHelp(panel.scan, "Price materials and suitable recipe alternatives for your skill goal. You choose what to buy.")
    return panel
end

local function renderRows(list)
    ns.auctionGuideItems = list
    for _, row in ipairs(panel.rows) do row:Hide() end
    for index, item in ipairs(list) do
        if index > 256 then break end
        local row = panel.rows[index]
        if not row then
            row = CreateFrame("Frame", nil, panel.child); row:SetSize(274, 78)
            row.name = ns.UILabel(row, nil, 12, ns.UIColors.gold); row.name:SetPoint("TOPLEFT", 0, -4); row.name:SetSize(181, 30); row.name:SetWordWrap(true)
            row.amount = ns.UILabel(row, nil, 11); row.amount:SetPoint("TOPLEFT", 0, -35); row.amount:SetWidth(268)
            row.price = ns.UILabel(row, nil, 10, ns.UIColors.muted); row.price:SetPoint("TOPLEFT", 0, -53); row.price:SetWidth(268)
            row.search = ns.UIButton(row, "Search", 78, function() ns.SearchGuideAuctionItem(row.itemID) end)
            row.search:SetPoint("TOPRIGHT", -1, -4); ns.UIDivider(row, -77)
            panel.rows[index] = row
        end
        row.itemID = item.itemID; row:SetPoint("TOPLEFT", 0, -(index - 1) * 78)
        row.name:SetText(ns.ItemName(item.itemID, item.name))
        row.amount:SetText("Buy " .. (item.missing and ("~" .. item.missing) or "check bags") .. " • Bags " .. (item.have or "?"))
        local quote = ns.AuctionQuote(item.itemID)
        local unit, complete = ns.AuctionUnitPrice(item.itemID, item.missing)
        row.price:SetText(quote and quote.unavailable and "No listings found" or unit and (ns.MoneyText(math.ceil(unit)) .. " each"
            .. (quote.cached and " • saved" or "") .. (complete == false and " • estimate" or "")) or "Price not checked")
        row:Show()
    end
    panel.child:SetHeight(math.max(100, math.min(#list, 256) * 78))
end

local function startForecast(id, target, signature)
    local job = {signature = signature}; forecast = job
    panel.planSignature = signature
    panel.notice:SetText("Estimating materials to skill " .. target .. "…")
    local worker = coroutine.create(function()
        return ns.ProfessionMaterialForecast(id, ns.PlanProfessionPreview(id, target, true), true)
    end)
    local function run()
        if forecast ~= job or not ns.auctionHouseOpen or panel.dismissed then return end
        local currentID, currentTarget = ns.AuctionGuideContext()
        if currentID ~= id or currentTarget ~= target then forecast = nil; return end
        if ns.RouteInCombat() then forecast = nil; panel.planSignature = nil; return end
        local okay, result = coroutine.resume(worker)
        if not okay then
            forecast = nil; panel.planSignature = nil; panel.notice:SetText("Refresh your guide to estimate materials.")
            ns.auctionForecastError = tostring(result); return
        end
        if coroutine.status(worker) == "dead" then
            forecast = nil; panel.materials = result.materials; panel.forecast = result
            renderRows(result.materials)
            panel.notice:SetText("Skill " .. result.start .. " → " .. target .. " • approximate buy amounts.\n"
                .. (result.estimatedCost and ("Est. materials: " .. ns.MoneyText(result.estimatedCost)) or "Scan for material prices")
                .. (result.incomplete and " • partial guide" or ""))
        elseif C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, run)
        else forecast = nil; panel.notice:SetText("Material estimate unavailable.") end
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, run) else run() end
end

function ns.RefreshAuctionGuideSearch()
    if not ns.auctionHouseOpen then if panel then panel:Hide() end; return end
    local parent = shown(AuctionHouseFrame) and AuctionHouseFrame or shown(AuctionFrame) and AuctionFrame
    if not parent or ns.RouteInCombat() then return end
    local id, target = ns.AuctionGuideContext()
    local list = ns.shoppingList or {}
    if not id and #list == 0 then if panel then panel:Hide() end; return end
    create(parent)
    if panel.dismissed then return end
    makeRoom(parent)
    panel:SetParent(parent); panel:ClearAllPoints(); panel:SetPoint("TOPRIGHT", parent, "TOPLEFT", -6, 0)
    panel:Show(); panel.scan.caption:SetText(ns.AuctionScanState() and "Stop scan" or "Scan auction house")
    panel.scan:SetEnabled(id ~= nil); panel.goal:SetShown(id ~= nil)
    panel.status:SetText(ns.auctionScanStatus or ns.auctionGuideStatus or "Search an item, or scan prices for your goal.")
    if id then
        panel.profession:SetText(ns.ProfessionFacts(id).name); panel.goal:SetChoice(target)
        local info = ns.professionData[id]
        local signature = table.concat({id,target,info.skill or 1,ns.professionRevision or 0,ns.auctionMarketRevision or 0}, ":")
        if panel.planSignature ~= signature then startForecast(id, target, signature)
        elseif panel.materials then renderRows(panel.materials) end
    else
        forecast, panel.planSignature = nil, nil
        panel.profession:SetText("Shopping list"); panel.notice:SetText("Missing materials after bag stock.")
        renderRows(list)
    end
end

ns.On("AUCTION_HOUSE_SHOW", function()
    ns.auctionHouseOpen = true
    if panel then panel.dismissed = nil end
    ns.RefreshAuctionGuideSearch()
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, ns.RefreshAuctionGuideSearch) end
end)
ns.On("AUCTION_HOUSE_CLOSED", function()
    ns.auctionHouseOpen = false; forecast = nil
    ns.CancelAuctionScan("Scan stopped: auction house closed.")
    if panel then panel:Hide(); panel.planSignature = nil; panel.goal.menu:Hide() end
    restoreNativePosition()
end)
local previousRegen = ns.handlers.PLAYER_REGEN_ENABLED
ns.On("PLAYER_REGEN_ENABLED", function(...)
    if previousRegen then previousRegen(...) end
    if restorePending then restoreNativePosition() end
    if ns.shoppingContext and ns.shoppingWindow and ns.shoppingWindow:IsShown() and not ns.shoppingContext.signature then
        ns.RefreshProfessionShopping()
    end
    ns.RefreshAuctionGuideSearch()
end)
local previousItem = ns.handlers.ITEM_DATA_LOAD_RESULT
ns.On("ITEM_DATA_LOAD_RESULT", function(...)
    if previousItem then previousItem(...) end
    if ns.auctionHouseOpen then ns.RefreshAuctionGuideSearch() end
end)
