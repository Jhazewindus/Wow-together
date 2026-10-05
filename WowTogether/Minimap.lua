local addonName, ns = ...

function ns.CreateMinimap()
    if not Minimap then return end
    local icon = CreateFrame("Button", "WowTogetherMinimapButton", Minimap)
    ns.minimapButton = icon
    icon:SetSize(32, 32)
    icon:SetPoint("TOPRIGHT", Minimap, "TOPRIGHT", 5, 5)
    icon:SetFrameStrata("MEDIUM")
    icon:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    local image = icon:CreateTexture(nil, "ARTWORK")
    image:SetTexture("Interface\\Icons\\INV_Misc_Map_01")
    image:SetSize(20, 20)
    image:SetPoint("CENTER", 0, 0)
    image:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    local rim = icon:CreateTexture(nil, "OVERLAY")
    rim:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    rim:SetSize(54, 54)
    rim:SetPoint("TOPLEFT", 0, 0)
    icon:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    icon:SetScript("OnClick", function(_, mouseButton)
        if mouseButton == "RightButton" then ns.Diagnostics() else ns.ToggleWindow() end
    end)
    icon:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:AddLine("Wow Together", 0.93, 0.73, 0.39)
        GameTooltip:AddLine("Quest with friends", 0.85, 0.89, 0.92)
        GameTooltip:AddLine("Left-click: party quest view", 1, 1, 1)
        GameTooltip:AddLine("Right-click: diagnostics", 1, 1, 1)
        GameTooltip:Show()
    end)
    icon:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    icon:SetShown(not ns.db.minimapHidden)
end

function ns.ToggleMinimap()
    ns.db.minimapHidden = not ns.db.minimapHidden
    if ns.minimapButton then ns.minimapButton:SetShown(not ns.db.minimapHidden) end
end
