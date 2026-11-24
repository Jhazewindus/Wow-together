local addonName, ns = ...

-- A clickable Hearthstone or teleport on the guide card.
--
-- When the next step of the route is the character's own transport ("Use
-- your Hearthstone", "Cast Teleport: Orgrimmar") the card shows a button
-- that does it when the player clicks. The game only lets an addon do this
-- through a secure button and a real click, so:
--   * nothing is ever used or cast on its own;
--   * the button's item or spell, its position and whether it shows can
--     only change outside combat - during a fight it stays as it is and is
--     brought up to date when the fight ends.
-- The secure click handler the template installs is left in place; this
-- file only observes clicks (PostClick) and never replaces OnClick.
local HEARTHSTONE = 6948
local FALLBACK_ICON = "Interface\\Icons\\INV_Misc_QuestionMark"

-- What the current step asks the player to use, or nil.
function ns.TravelButtonAction(state)
    local stop = state and state.stop
    local leg = stop and stop.personalTransport and stop.travelLeg
    if type(leg) ~= "table" then return nil end
    local transport = type(leg.to) == "table" and leg.to.personal or nil
    local remaining = transport and tonumber(transport.remaining) or 0
    if leg.method == "hearth" then
        local where = transport and transport.name or leg.name
        return {kind = "item", id = HEARTHSTONE, remaining = remaining,
            label = "Use Hearthstone" .. (type(where) == "string" and where ~= "" and (" to " .. where) or "")}
    elseif leg.method == "teleport" then
        local spell = transport and tonumber(string.match(tostring(transport.id or ""), "^TELEPORT_(%d+)$"))
        if not spell then return nil end
        return {kind = "spell", id = spell, remaining = remaining, label = "Cast " .. tostring(transport.name or leg.name or "teleport")}
    end
    return nil
end

local function icon(action)
    local texture
    if action.kind == "item" then
        texture = C_Item and ns.ReadPublic(C_Item.GetItemIconByID, action.id)
    else
        texture = C_Spell and ns.ReadPublic(C_Spell.GetSpellTexture, action.id) or ns.ReadPublic(GetSpellTexture, action.id)
    end
    if type(texture) ~= "string" and type(texture) ~= "number" then texture = FALLBACK_ICON end
    return texture
end

function ns.CreateTravelButton(frame)
    if frame.travelButton then return frame.travelButton end
    local button = CreateFrame("Button", nil, frame, "SecureActionButtonTemplate,BackdropTemplate")
    button:SetSize(360, 32); ns.UIPanel(button, ns.UIColors.panel)
    button.caption = ns.UILabel(button, nil, 12)
    button.caption:SetPoint("LEFT", 36, 0); button.caption:SetSize(310, 20)
    button.caption:SetWordWrap(false); button.caption:SetJustifyH("LEFT")
    button.icon = button:CreateTexture(nil, "ARTWORK")
    button.icon:SetSize(24, 24); button.icon:SetPoint("LEFT", 4, 0)
    -- Secure buttons act on the press or the release depending on a client
    -- setting; registering both keeps the click working either way.
    button:RegisterForClicks("AnyUp", "AnyDown")
    button:SetScript("PostClick", function(self)
        if self.action then ns.travelButtonStatus = "Clicked: " .. self.action.label .. "." end
    end)
    button:SetScript("OnEnter", function(self)
        if not GameTooltip or not self.action then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:AddLine(self.action.label, 1, 0.82, 0.3)
        GameTooltip:AddLine("Click to do this step. Nothing is used or cast unless you click.", 1, 1, 1, true)
        if self.action.remaining > 0 then GameTooltip:AddLine("Still on cooldown.", 1, 0.82, 0.3, true) end
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    button:Hide()
    frame.travelButton = button
    return button
end

-- Called with the card's state on every full update. Returns whether the
-- button is showing, so the panels under the card can stack around it.
function ns.UpdateTravelButton(state)
    local button = ns.navigation and ns.navigation.travelButton
    if not button then return false end
    local wanted = state and state.visible and ns.Option("routeArrow") and ns.Option("travelButton") ~= false
        and not ns.navigationPreview and ns.TravelButtonAction(state) or nil
    if ns.RouteInCombat() then
        -- A secure button may not be shown, hidden or re-aimed in combat.
        button.stale = true
        ns.travelButtonStatus = "Waiting for combat to end."
        return button:IsShown()
    end
    button.stale = nil
    if not wanted then
        if button.action then
            button:SetAttribute("type", nil); button:SetAttribute("item", nil); button:SetAttribute("spell", nil)
        end
        button.action = nil
        button:Hide()
        ns.travelButtonStatus = "Hidden: the current step is not a Hearthstone or teleport."
        return false
    end
    local previous = button.action
    if not previous or previous.kind ~= wanted.kind or previous.id ~= wanted.id then
        button:SetAttribute("type", wanted.kind)
        button:SetAttribute("item", wanted.kind == "item" and ("item:" .. wanted.id) or nil)
        button:SetAttribute("spell", wanted.kind == "spell" and wanted.id or nil)
        button.icon:SetTexture(icon(wanted))
    end
    button.action = wanted
    local wait = wanted.remaining > 0 and ns.FormatTravelDuration and (" (ready in " .. ns.FormatTravelDuration(wanted.remaining) .. ")") or ""
    button.caption:SetText(wanted.label .. wait)
    button:Show()
    ns.travelButtonStatus = "Showing: " .. wanted.label .. "."
    return true
end

-- Leaving combat: bring a button that could not change up to date.
ns.On("PLAYER_REGEN_ENABLED", function()
    local button = ns.navigation and ns.navigation.travelButton
    if button and button.stale and ns.ScheduleRefresh then ns.ScheduleRefresh(true) end
end)

function ns.TravelButtonDiagnostics(output)
    output("Travel button: " .. (ns.Option("travelButton") == false and "off in settings"
        or (ns.travelButtonStatus or "not shown yet")) .. " One click of yours per use; changes only outside combat.")
end
