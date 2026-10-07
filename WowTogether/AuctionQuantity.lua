local addonName, ns = ...

-- Only the commodity display's public quantity setter, after the player's
-- material search and matching selection. Never start or confirm a purchase.
local pending
function ns.ClearGuideAuctionQuantity()
    pending = nil
    local panel = ns.auctionGuideToolbar
    if panel then panel:SetScript("OnUpdate", nil) end
end
function ns.UpdateGuideAuctionQuantity(elapsed)
    if not pending then return end
    pending.age, pending.tick = pending.age + elapsed, pending.tick + elapsed
    if pending.tick < 0.25 then return end
    pending.tick = 0
    local id, target = ns.AuctionGuideContext()
    if not ns.AuctionHouseVisible() or pending.age > 60 or id ~= pending.professionID or target ~= pending.target then
        ns.ClearGuideAuctionQuantity(); return
    end
    if ns.RouteInCombat() then return end
    local frame = AuctionHouseFrame and AuctionHouseFrame.CommoditiesBuyFrame
    local display = frame and frame.BuyDisplay
    if not display or ns.ReadPublic(display.IsShown, display) ~= true
        or ns.ReadPublic(display.GetItemID, display) ~= pending.itemID then return end
    if ns.ReadPublic(display.IsProtected, display) ~= false or type(display.SetQuantitySelected) ~= "function"
        or type(display.GetQuantitySelected) ~= "function" then
        ns.auctionQuantityStatus = "Native quantity input unavailable; enter the buy amount manually."
        ns.ClearGuideAuctionQuantity(); return
    end
    if not ns.Public(display.resultsLoaded) or display.resultsLoaded ~= true then return end
    local selected = ns.ReadPublic(display.GetQuantitySelected, display)
    if selected ~= 1 then
        ns.auctionQuantityStatus = "Kept the manually selected quantity."
        ns.ClearGuideAuctionQuantity(); return
    end
    local quantity = pending.quantity
    local have = ns.ItemOwned(pending.itemID)
    if have and pending.have then quantity = math.max(0, quantity - math.max(0, have - pending.have)) end
    ns.ClearGuideAuctionQuantity() -- One-shot: later events must respect edits.
    if quantity <= 0 then return end
    local okay = pcall(display.SetQuantitySelected, display, quantity)
    local actual = okay and ns.ReadPublic(display.GetQuantitySelected, display)
    ns.auctionQuantityStatus = ns.GuideInteger(actual, 10000000) and ("Quantity filled: " .. actual
        .. " / " .. quantity .. ". Purchase remains manual.") or "Quantity could not be filled; enter it manually."
end
function ns.PrepareGuideAuctionQuantity(itemID, quantity)
    ns.ClearGuideAuctionQuantity()
    if not ns.GuideInteger(quantity, 10000000) or quantity <= 0 or not ns.auctionGuideToolbar
        or ns.ReadPublic(ns.auctionGuideToolbar.IsShown, ns.auctionGuideToolbar) ~= true then return end
    local id, target = ns.AuctionGuideContext()
    pending = {itemID = itemID, quantity = quantity, have = ns.ItemOwned(itemID), professionID = id,
        target = target, age = 0, tick = 0}
    ns.auctionQuantityStatus = "Waiting for the searched commodity selection."
    ns.auctionGuideToolbar:SetScript("OnUpdate", function(_, elapsed) ns.UpdateGuideAuctionQuantity(elapsed) end)
end
