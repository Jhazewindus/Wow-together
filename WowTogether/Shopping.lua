local addonName, ns = ...

ns.marketQuotes, ns.pendingItems = {}, {}

function ns.ItemName(id, fallback)
    local name
    if C_Item then name = ns.ReadPublic(C_Item.GetItemInfo, id) end
    name = ns.SafeTitle(name)
    if not name and C_Item and type(C_Item.RequestLoadItemDataByID) == "function" and not ns.pendingItems[id] then
        ns.pendingItems[id] = true; C_Item.RequestLoadItemDataByID(id)
    end
    return name or fallback or ("Item " .. id)
end

function ns.ItemOwned(id)
    local count = C_Item and ns.ReadPublic(C_Item.GetItemCount, id)
    if ns.GuideInteger(count) then return count end
end

function ns.MoneyText(copper)
    if not ns.GuideInteger(copper, 9000000000000) then return "price unknown" end
    return math.floor(copper / 10000) .. "g " .. math.floor(copper / 100) % 100 .. "s " .. copper % 100 .. "c"
end

function ns.QuestShoppingList(records, query)
    local items = {}
    for _, record in ipairs(records or {}) do
        local quest = ns.CatalogueQuest(record.id)
        if quest and quest.requiredItems and #quest.requiredItems > 0
            and (ns.active[record.id] or ns.Completed(record.id, query) ~= true) then
            for _, item in ipairs(quest.requiredItems or {}) do
                if item.buyable then
                    local row = items[item.itemID]
                    if not row then row = {itemID = item.itemID, name = item.name, need = 0, source = "Published vendor item", quests = {}}; items[item.itemID] = row end
                    row.need = row.need + item.quantity
                    row.quests[#row.quests + 1] = ns.QuestTitle(record.id)
                end
            end
        end
    end
    local result = {}
    for id, item in pairs(items) do
        item.have = ns.ItemOwned(id)
        item.missing = item.have and math.max(0, item.need - item.have) or nil
        if item.missing ~= 0 then result[#result + 1] = item end
    end
    table.sort(result, function(a, b) return a.itemID < b.itemID end)
    return result
end

function ns.ShoppingText(list)
    local lines = {}
    for _, item in ipairs(list) do
        local name = ns.ItemName(item.itemID, item.name)
        local quote = ns.AuctionQuote(item.itemID)
        local quantity = item.missing or item.need
        lines[#lines + 1] = name .. " • need " .. item.need .. " • bags " .. (item.have or "unknown")
            .. " • buy " .. (item.missing or "check bags")
        lines[#lines + 1] = "  " .. (item.source or "Check vendor / auction availability")
            .. (quote and (" • observed AH unit price " .. ns.MoneyText(quote.unitPrice) .. " • about " .. ns.MoneyText(quote.unitPrice * quantity)) or " • AH price unknown")
        if item.quests then lines[#lines + 1] = "  For: " .. table.concat(item.quests, ", ") end
    end
    if #lines == 0 then lines[1] = "No missing items are known for this plan.\nSome requirements may be unavailable; check the quest or recipe." end
    lines[#lines + 1] = "\nThis is your own shopping list. Saved AH prices expire after 6 hours; listings can change."
    return table.concat(lines, "\n")
end

function ns.ShowShoppingList(list, title)
    ns.shoppingContext = nil
    if ns.CancelProfessionShopping then ns.CancelProfessionShopping() end
    ns.shoppingList, ns.shoppingTitle = list, title
    if not ns.shoppingWindow then
        local frame = CreateFrame("Frame", "WowTogetherShopping", UIParent, "BackdropTemplate")
        ns.shoppingWindow = frame
        frame:SetSize(660, 480); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
        frame:SetClampedToScreen(true); ns.UIPanel(frame)
        ns.UIClose(frame)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 18); frame.title:SetPoint("TOPLEFT", 22, -22)
        local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
        scroll:SetPoint("TOPLEFT", 22, -104); scroll:SetPoint("BOTTOMRIGHT", -38, 62)
        local child = CreateFrame("Frame", nil, scroll); child:SetSize(600, 100); scroll:SetScrollChild(child)
        frame.child = child
        frame.text = ns.UILabel(child, nil, 12); frame.text:SetPoint("TOPLEFT"); frame.text:SetWidth(530)
        frame.text:SetJustifyV("TOP")
        frame.notice = ns.UILabel(frame, nil, 11, ns.UIColors.muted)
        frame.notice:SetPoint("TOPLEFT", 22, -62); frame.notice:SetWidth(600); frame.notice:SetHeight(38); frame.notice:SetWordWrap(true)
        frame.scope = ns.UIDropdown(frame, {{"batch", "Next batch"}, {"goal", "To skill goal"}}, 140, function(value)
            if not ns.shoppingContext then return end
            ns.shoppingContext.scope, ns.shoppingContext.signature = value, nil
            ns.RefreshProfessionShopping()
        end)
        frame.scope:SetPoint("TOPRIGHT", -35, -22)
        frame.rows = {}
        local refresh = ns.UIButton(frame, "Refresh bags / prices", 190, function() ns.RefreshShoppingList() end)
        refresh:SetPoint("BOTTOMLEFT", 22, 12)
        frame.status = ns.UILabel(frame, nil, 10, ns.UIColors.muted)
        frame.status:SetPoint("BOTTOMLEFT", 224, 12); frame.status:SetWidth(392); frame.status:SetHeight(32); frame.status:SetWordWrap(true)
        frame:SetScript("OnHide", function()
            frame.scope.menu:Hide()
            if ns.shoppingContext then ns.shoppingContext.signature = nil end
            if ns.CancelProfessionShopping then ns.CancelProfessionShopping() end
        end)
    end
    ns.RefreshShoppingList(); ns.shoppingWindow:Show()
end

function ns.RefreshShoppingList()
    if not ns.shoppingWindow or not ns.shoppingList then return end
    if ns.shoppingContext then
        ns.shoppingContext.signature = nil; ns.RefreshProfessionShopping(); return
    end
    for _, item in ipairs(ns.shoppingList) do
        item.have = ns.ItemOwned(item.itemID)
        item.missing = item.have and math.max(0, item.need - item.have) or nil
    end
    ns.RenderShoppingList()
end

function ns.RenderShoppingList()
    local frame, context = ns.shoppingWindow, ns.shoppingContext
    if not frame then return end
    frame.title:SetText(ns.shoppingTitle or "Shopping list")
    frame.title:SetWidth(context and 400 or 580)
    frame.scope:SetShown(context ~= nil)
    if context then frame.scope:SetChoice(context.scope) end
    frame.notice:SetText(context and context.notice or "After bag stock • prices from this session's auction searches.")
    for _, row in ipairs(frame.rows) do row:Hide() end
    local list = ns.shoppingList or {}
    frame.text:SetShown(#list == 0)
    frame.text:SetText(context and context.loading and "Calculating…" or "No materials needed for this step.")
    for index, item in ipairs(list) do
        local row = frame.rows[index]
        if not row then
            row = CreateFrame("Frame", nil, frame.child); row:SetSize(594, 76)
            row.title = ns.UILabel(row, nil, 13, ns.UIColors.gold); row.title:SetPoint("TOPLEFT", 0, -5); row.title:SetWidth(466)
            row.detail = ns.UILabel(row, nil, 11, ns.UIColors.muted); row.detail:SetPoint("TOPLEFT", 0, -24)
            row.detail:SetWidth(466); row.detail:SetHeight(45); row.detail:SetWordWrap(true)
            row.search = ns.UIButton(row, "Search AH", 104, function()
                if ns.SearchGuideAuctionItem then ns.SearchGuideAuctionItem(row.itemID) end
            end)
            row.search:SetPoint("TOPRIGHT", -2, -7); ns.UIDivider(row, -74)
            frame.rows[index] = row
        end
        row.itemID = item.itemID
        row:SetPoint("TOPLEFT", 0, -(index - 1) * 76)
        row.title:SetText(ns.ItemName(item.itemID, item.name))
        local quote = ns.AuctionQuote(item.itemID)
        row.detail:SetText((context and context.scope == "goal" and "Estimate " or "Need ") .. item.need
            .. " • Bags " .. (item.have or "?") .. (item.planned and item.planned > 0 and " • Make " .. item.planned or "")
            .. " • Buy " .. (item.missing or "check bags")
            .. "\n" .. (quote and (ns.MoneyText(quote.unitPrice) .. " each") or "Price not checked")
            .. " • " .. (item.source or "Vendor / gathering / auction house"))
        row:Show()
    end
    frame.child:SetHeight(math.max(100, #list * 76))
    frame.status:SetText(ns.auctionGuideStatus or "Open an auction house, then click Search AH.")
    if ns.RefreshAuctionGuideSearch then ns.RefreshAuctionGuideSearch() end
end
