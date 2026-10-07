local addonName, ns = ...

function ns.CloseUIMenus()
    for _, menu in ipairs(ns.uiMenus or {}) do menu:Hide() end
end

-- Owned menus avoid relying on secure Blizzard menu implementations in beta.
function ns.UIDropdown(parent, entries, width, callback)
    local control = ns.UIButton(parent, "", width, function() end)
    local menu = CreateFrame("Frame", nil, control, "BackdropTemplate")
    menu:SetPoint("TOPLEFT", control, "BOTTOMLEFT", 0, -2)
    menu:SetSize(width, #entries * 28 + 8); menu:SetFrameStrata("TOOLTIP"); menu:SetClampedToScreen(true)
    menu:SetFrameLevel(control:GetFrameLevel() + 20); ns.UIPanel(menu)
    control.menu, control.entries, control.options = menu, entries, {}
    for index, entry in ipairs(entries) do
        local row = ns.UIButton(menu, entry[2], width - 8, function()
            menu:Hide(); callback(entry[1])
        end)
        row:SetHeight(26); row:SetPoint("TOPLEFT", 4, -4 - (index - 1) * 28)
        row.caption:SetJustifyH("LEFT")
        control.options[entry[1]] = row
    end
    function control:SetChoice(value)
        for _, entry in ipairs(self.entries) do
            if entry[1] == value then self.caption:SetText(entry[2]); return end
        end
        self.caption:SetText("Choose…")
    end
    function control:SetVisibleEntries(predicate)
        local count = 0
        for _, entry in ipairs(self.entries) do
            local row, visible = self.options[entry[1]], predicate(entry[1])
            row:SetShown(visible)
            if visible then
                row:ClearAllPoints(); row:SetPoint("TOPLEFT", 4, -4 - count * 28)
                count = count + 1
            end
        end
        self.menu:SetHeight(count * 28 + 8); self.menu:Hide()
    end
    control.caption:ClearAllPoints(); control.caption:SetPoint("LEFT", 10, 0)
    control.caption:SetWidth(width - 34); control.caption:SetJustifyH("LEFT")
    local arrow = CreateFrame("Frame", nil, control)
    arrow:SetSize(10, 6); arrow:SetPoint("RIGHT", -10, 0)
    if type(arrow.CreateLine) == "function" then
        for _, x in ipairs({-4, 4}) do
            local line = arrow:CreateLine(nil, "OVERLAY")
            line:SetThickness(1); line:SetColorTexture(unpack(ns.UIColors.gold))
            line:SetStartPoint("CENTER", arrow, x, 2); line:SetEndPoint("CENTER", arrow, 0, -2)
        end
    else
        local fallback = ns.UILabel(arrow, nil, 10); fallback:SetPoint("CENTER"); fallback:SetText("v")
    end
    ns.uiMenus = ns.uiMenus or {}; ns.uiMenus[#ns.uiMenus + 1] = menu
    control:SetScript("OnClick", function()
        local currentWidth = control:GetWidth() or width
        menu:SetWidth(currentWidth); control.caption:SetWidth(currentWidth - 34)
        for _, row in pairs(control.options) do row:SetWidth(currentWidth - 8) end
        local opening = not menu:IsShown()
        for _, other in ipairs(ns.uiMenus) do other:Hide() end
        menu:SetShown(opening)
    end)
    control:SetScript("OnHide", function() menu:Hide() end)
    control:SetScript("OnSizeChanged", function()
        local currentWidth = control:GetWidth() or width
        control.caption:SetWidth(currentWidth - 34); menu:SetWidth(currentWidth)
        for _, row in pairs(control.options) do row:SetWidth(currentWidth - 8) end
        menu:Hide()
    end)
    menu:Hide()
    return control
end

function ns.UIHelp(frame, text)
    frame:SetScript("OnEnter", function(self)
        if self.caption then self:SetBackdropBorderColor(unpack(ns.UIColors.gold)) end
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT"); GameTooltip:AddLine(text, 1, 0.9, 0.7, true); GameTooltip:Show()
    end)
    frame:SetScript("OnLeave", function(self)
        if self.caption then self:SetBackdropBorderColor(unpack(self.primary and ns.UIColors.gold or ns.UIColors.border)) end
        if GameTooltip then GameTooltip:Hide() end
    end)
end
