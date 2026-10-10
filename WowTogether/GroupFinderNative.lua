local addonName, ns = ...

-- Forever Browse integration. Result IDs and native result order stay intact;
-- only the ScrollBox's displayed tree is filtered. No searches or invite calls.
local state = {role = "all", classID = 0}
local function publicTable(value) return ns.Public(value) and type(value) == "table" end
local function visible(frame) return frame and ns.ReadPublic(frame.IsShown, frame) == true end
local function writable(frame)
    return (type(frame) == "table" or type(frame) == "userdata")
        and ns.ReadPublic(frame.IsProtected, frame) ~= true and not ns.RouteInCombat()
end
local function filtered() return state.role ~= "all" or state.classID ~= 0 end

local function dropdown(parent, entries, width, callback)
    local button = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    button:SetSize(width, 22)
    button:SetNormalFontObject("GameFontHighlightSmall"); button:SetHighlightFontObject("GameFontHighlightSmall")
    local arrow = button:CreateTexture(nil, "OVERLAY")
    arrow:SetTexture("Interface\\ChatFrame\\UI-ChatIcon-ScrollDown-Up")
    arrow:SetSize(16, 16); arrow:SetPoint("RIGHT", -3, 0)
    local menu = CreateFrame("Frame", nil, button, "BackdropTemplate")
    menu:SetPoint("TOPLEFT", button, "BOTTOMLEFT", 0, -1)
    menu:SetSize(width, #entries * 22 + 12); menu:SetFrameStrata("TOOLTIP"); menu:SetClampedToScreen(true)
    menu:SetBackdrop({bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", tile = true, tileSize = 16, edgeSize = 16,
        insets = {left = 4, right = 4, top = 4, bottom = 4}})
    menu:SetBackdropColor(.05, .04, .025, .98); menu:SetBackdropBorderColor(.7, .57, .3, 1)
    button.menu, button.options = menu, {}
    for index, choice in ipairs(entries) do
        local row = CreateFrame("Button", nil, menu, "UIPanelButtonTemplate")
        row:SetSize(width - 12, 22); row:SetPoint("TOPLEFT", 6, -6 - (index - 1) * 22)
        row:SetText(choice[2]); row:SetNormalFontObject("GameFontHighlightSmall")
        row:SetScript("OnClick", function() menu:Hide(); callback(choice[1]) end)
        button.options[choice[1]] = row
    end
    function button:SetChoice(value)
        for _, choice in ipairs(entries) do if choice[1] == value then self:SetText(choice[2] .. "   "); return end end
    end
    button:SetScript("OnClick", function()
        local opening = not menu:IsShown()
        ns.CloseUIMenus(); menu:SetShown(opening)
    end)
    button:SetScript("OnHide", function() menu:Hide() end)
    ns.uiMenus = ns.uiMenus or {}; ns.uiMenus[#ns.uiMenus + 1] = menu
    menu:Hide()
    return button
end

local function createBar(browse)
    local bar = CreateFrame("Frame", nil, browse)
    ns.groupFinderNativeBar = bar
    bar:SetSize(294, 24)
    bar:SetPoint("TOPLEFT", browse.CategoryDropdown, "BOTTOMLEFT", 0, -1)
    bar:SetFrameLevel(browse:GetFrameLevel() + 10)
    bar.label = bar:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    bar.label:SetPoint("LEFT", 0, 0); bar.label:SetText("Players:")
    bar.roles = dropdown(bar, ns.GroupFinderRoleChoices, 112, function(value)
        state.role = value; ns.RefreshNativeGroupFinder(true)
    end)
    bar.roles:SetPoint("LEFT", 48, 0); bar.roles:SetChoice(state.role)
    bar.classes = dropdown(bar, ns.GroupFinderClassChoices, 120, function(value)
        state.classID = value; ns.RefreshNativeGroupFinder(true)
    end)
    bar.classes:SetPoint("LEFT", 166, 0); bar.classes:SetChoice(state.classID)
    bar:SetScript("OnHide", function() bar.roles.menu:Hide(); bar.classes.menu:Hide() end)
    return bar
end

local function clearSelection(browse)
    local selection = browse.selectionBehavior
    if selection and type(selection.ClearSelections) == "function" then selection:ClearSelections() end
end
local function setProvider(browse, provider)
    clearSelection(browse)
    browse.ScrollBox:SetDataProvider(provider, ScrollBoxConstants and ScrollBoxConstants.RetainScrollPosition)
    -- Let the native buttons follow their own selection state and click logic.
    if type(browse.UpdateButtonState) == "function" then browse:UpdateButtonState() end
end
local function restore(browse)
    if not writable(browse) or not writable(browse.ScrollBox) or not state.filtered then return end
    local current = browse.ScrollBox:GetDataProvider()
    if current == state.filtered and state.base then
        if not pcall(setProvider, browse, state.base) then
            ns.groupFinderNativeStatus = "Native results restoration deferred; provider update failed."
            return
        end
        if state.empty and browse.NoResultsFound then browse.NoResultsFound:Hide() end
    end
    state.filtered, state.signature, state.empty = nil, nil, nil
end

function ns.ApplyNativeGroupFinder(force)
    local browse = state.browse
    if not browse or state.applying or not writable(browse) or not writable(browse.ScrollBox) then return end
    local current = browse.ScrollBox:GetDataProvider()
    if current ~= state.filtered then state.base, state.signature = current, nil end
    if not ns.Option("groupFinderRoles") or not filtered() then restore(browse); return end
    if not visible(browse) or not visible(LFGParentFrame) or browse.searching or browse.searchFailed
        or not state.base or not publicTable(browse.results) then return end
    if #browse.results > 1000 then
        restore(browse); ns.groupFinderNativeStatus = "Too many loaded listings; native results retained."; return
    end
    local entries, signature, inspected, matched = {}, {state.role, tostring(state.classID)}, 0, 0
    for index, id in ipairs(browse.results) do
        if ns.GuideInteger(id) then
            local info = C_LFGList and ns.ReadPublic(C_LFGList.GetSearchResultInfo, id)
            if publicTable(info) and ns.GuideInteger(info.numMembers, 40) and ns.Public(info.hasSelf) then
                local category = not info.hasSelf and (info.numMembers <= 1 and 1 or 2) or nil
                local keep = category ~= 1 -- The requested filters concern solo Players, not group recruitment roles.
                if category == 1 then
                    inspected = inspected + 1
                    local row = ns.GroupFinderListedPlayer(id, 1, info)
                    keep = row and ns.GroupFinderRoleMatches(row, state.role)
                        and (state.classID == 0 or row.classID == state.classID)
                    if keep then matched = matched + 1 end
                end
                if keep then
                    entries[#entries + 1] = {index = index, resultID = id, category = category}
                    signature[#signature + 1] = id .. ":" .. (category or 0)
                end
            end
        end
    end
    signature = table.concat(signature, ",")
    if not force and current == state.filtered and state.signature == signature then return end
    local provider, lastCategory, group = CreateTreeDataProvider()
    for _, entry in ipairs(entries) do
        if LFGVANILLA_SETTING_BROWSE_SHOW_COLLAPSIBLE_CATEGORIES and entry.category then
            if entry.category ~= lastCategory then
                group = provider:Insert({dividerType = entry.category})
                lastCategory = entry.category
            end
            group:Insert(entry)
        else
            -- A self-listing is never nested under the previous category.
            provider:Insert({index = entry.index, resultID = entry.resultID})
            group, lastCategory = nil, nil
        end
    end
    state.applying = true
    local ok = pcall(setProvider, browse, provider)
    state.applying = nil
    if not ok then
        local restored = pcall(setProvider, browse, state.base)
        -- Keep a partially applied provider recoverable on the next poll.
        state.filtered = not restored and ns.ReadPublic(browse.ScrollBox.GetDataProvider, browse.ScrollBox) or nil
        state.signature = nil
        if restored then
            if state.empty and browse.NoResultsFound then browse.NoResultsFound:Hide() end
            state.empty = nil
        end
        state.role, state.classID = "all", 0
        local bar = ns.groupFinderNativeBar
        if bar then bar.roles:SetChoice("all"); bar.classes:SetChoice(0) end
        ns.groupFinderNativeStatus = "Native filter update failed; original results restored when available."
        return
    end
    state.filtered, state.signature, state.empty = provider, signature, #entries == 0
    if browse.NoResultsFound then
        if state.empty then browse.NoResultsFound:SetText("No matching players") end
        browse.NoResultsFound:SetShown(state.empty)
    end
    ns.groupFinderNativeStatus = matched .. "/" .. inspected .. " solo players match; native groups and result IDs retained."
end

function ns.RefreshNativeGroupFinder(force)
    local browse, bar = LFGBrowseFrame, ns.groupFinderNativeBar
    if not browse or not visible(LFGParentFrame) or not visible(browse) or not ns.Option("groupFinderRoles") then
        if bar then bar:Hide() end
        if state.browse then restore(state.browse) end
        return
    end
    if ns.RouteInCombat() then
        if bar then bar.roles:SetEnabled(false); bar.classes:SetEnabled(false) end
        ns.groupFinderNativeStatus = "Filter changes deferred until combat ends."
        return
    end
    if not writable(browse) or not writable(browse.ScrollBox) or not browse.CategoryDropdown
        or type(browse.ScrollBox.GetDataProvider) ~= "function" or type(browse.ScrollBox.SetDataProvider) ~= "function"
        or type(browse.UpdateResults) ~= "function" or type(CreateTreeDataProvider) ~= "function" or type(hooksecurefunc) ~= "function" then
        ns.groupFinderNativeStatus = "This client has no supported unprotected native Browse provider."
        return
    end
    if not state.browse then
        state.browse = browse
        hooksecurefunc(browse, "UpdateResults", function()
            -- A post-hook keeps Blizzard's update method and returned results intact.
            -- The owned controller reapplies filters outside this native call stack.
            if not state.applying then state.signature = nil end
        end)
    end
    bar = bar or createBar(browse)
    bar.roles:SetChoice(state.role); bar.classes:SetChoice(state.classID)
    bar.roles:SetEnabled(true); bar.classes:SetEnabled(true); bar:Show()
    ns.ApplyNativeGroupFinder(force)
    if not filtered() then ns.groupFinderNativeStatus = "Native Browse filters ready; all roles and classes." end
end
