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
        local quote = ns.marketQuotes[item.itemID]
        local quantity = item.missing or item.need
        lines[#lines + 1] = name .. " • need " .. item.need .. " • bags " .. (item.have or "unknown")
            .. " • buy " .. (item.missing or "check bags")
        lines[#lines + 1] = "  " .. (item.source or "Check vendor / auction availability")
            .. (quote and (" • observed AH unit price " .. ns.MoneyText(quote.unitPrice) .. " • about " .. ns.MoneyText(quote.unitPrice * quantity)) or " • AH price unknown")
        if item.quests then lines[#lines + 1] = "  For: " .. table.concat(item.quests, ", ") end
    end
    if #lines == 0 then lines[1] = "No missing items are known for this plan.\nSome requirements may be unavailable; check the quest or recipe." end
    lines[#lines + 1] = "\nThis is your own shopping list. AH prices use results you searched this session; listings can change."
    return table.concat(lines, "\n")
end

function ns.ShowShoppingList(list, title)
    ns.shoppingList, ns.shoppingTitle = list, title
    if not ns.shoppingWindow then
        local frame = CreateFrame("Frame", "WowTogetherShopping", UIParent, "BackdropTemplate")
        ns.shoppingWindow = frame
        frame:SetSize(600, 440); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
        frame:SetClampedToScreen(true); ns.UIPanel(frame)
        ns.UIClose(frame)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 18); frame.title:SetPoint("TOPLEFT", 22, -22)
        local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
        scroll:SetPoint("TOPLEFT", 22, -58); scroll:SetPoint("BOTTOMRIGHT", -38, 50)
        local child = CreateFrame("Frame", nil, scroll); child:SetSize(534, 100); scroll:SetScrollChild(child)
        frame.child = child
        frame.text = ns.UILabel(child, nil, 12); frame.text:SetPoint("TOPLEFT"); frame.text:SetWidth(530)
        frame.text:SetJustifyV("TOP")
        local refresh = ns.UIButton(frame, "Refresh bags / prices", 190, function() ns.RefreshShoppingList() end)
        refresh:SetPoint("BOTTOMLEFT", 22, 12)
    end
    ns.RefreshShoppingList(); ns.shoppingWindow:Show()
end

function ns.RefreshShoppingList()
    if not ns.shoppingWindow or not ns.shoppingList then return end
    for _, item in ipairs(ns.shoppingList) do
        item.have = ns.ItemOwned(item.itemID)
        item.missing = item.have and math.max(0, item.need - item.have) or nil
    end
    ns.shoppingWindow.title:SetText(ns.shoppingTitle or "Shopping list")
    ns.shoppingWindow.text:SetText(ns.ShoppingText(ns.shoppingList))
    local height = ns.shoppingWindow.text:GetStringHeight()
    if ns.Public(height) and type(height) == "number" then ns.shoppingWindow.child:SetHeight(math.max(100, height + 8)) end
end

ns.On("COMMODITY_SEARCH_RESULTS_UPDATED", function(id)
    if not ns.GuideInteger(id) or id <= 0 or not C_AuctionHouse then return end
    local result = ns.ReadPublic(C_AuctionHouse.GetCommoditySearchResultInfo, id, 1)
    if type(result) == "table" and ns.GuideInteger(result.unitPrice) and result.unitPrice > 0 and ns.GuideInteger(result.quantity) and result.quantity > 0 then
        ns.marketQuotes[id] = {unitPrice = result.unitPrice, quantity = result.quantity}
        ns.RefreshShoppingList()
        if ns.QueueProfessionUpdate then ns.QueueProfessionUpdate() end
        if ns.RenderProfessionGuide then ns.RenderProfessionGuide() end
    end
end)
