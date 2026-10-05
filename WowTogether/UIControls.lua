local addonName, ns = ...

-- Owned menus avoid relying on secure Blizzard menu implementations in beta.
function ns.UIDropdown(parent, entries, width, callback)
    local control = ns.UIButton(parent, "", width, function() end)
    local menu = CreateFrame("Frame", nil, control, "BackdropTemplate")
    menu:SetPoint("TOPLEFT", control, "BOTTOMLEFT", 0, -2)
    menu:SetSize(width, #entries * 30 + 8); menu:SetFrameStrata("DIALOG")
    menu:SetFrameLevel(control:GetFrameLevel() + 20); ns.UIPanel(menu)
    control.menu, control.entries, control.options = menu, entries, {}
    for index, entry in ipairs(entries) do
        local row = ns.UIButton(menu, entry[2], width - 8, function()
            menu:Hide(); callback(entry[1])
        end)
        row:SetHeight(28); row:SetPoint("TOPLEFT", 4, -4 - (index - 1) * 30)
        control.options[entry[1]] = row
    end
    function control:SetChoice(value)
        for _, entry in ipairs(self.entries) do
            if entry[1] == value then self.caption:SetText(entry[2] .. "  ▾"); return end
        end
        self.caption:SetText("Choose…  ▾")
    end
    control:SetScript("OnClick", function() menu:SetShown(not menu:IsShown()) end)
    control:SetScript("OnHide", function() menu:Hide() end)
    menu:Hide()
    return control
end

function ns.UIHelp(frame, text)
    frame:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT"); GameTooltip:AddLine(text, 1, 0.9, 0.7, true); GameTooltip:Show()
    end)
    frame:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
end
