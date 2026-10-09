local addonName, ns = ...

-- A separate, read-only view of the finder's current public player data.
-- Never replace native filters, scroll-box providers, scripts or row visibility.
local roles = {{"all", "All roles"}, {"TANK", "Tank"}, {"HEALER", "Healer"}, {"DAMAGER", "Damage"}, {"unknown", "Unspecified"}}
local labels = {TANK = "Tank", HEALER = "Healer", DAMAGER = "Damage"}
local function publicTable(value) return ns.Public(value) and type(value) == "table" end
local function declaredRole(value)
    return ns.Public(value) and type(value) == "string" and labels[value] and value or nil
end
local function addRole(target, role) if role then target[role] = true end end
local function player(name, class, level, assigned, tank, healer, damage)
    name, class = ns.SafeTitle(name), ns.SafeTitle(class)
    if not name then return end
    local selected = {}
    addRole(selected, declaredRole(assigned))
    for _, entry in ipairs({{"TANK", tank}, {"HEALER", healer}, {"DAMAGER", damage}}) do
        if ns.Public(entry[2]) and entry[2] == true then addRole(selected, entry[1]) end
    end
    return {name = name, class = class, level = ns.GuideInteger(level, 255) and level or nil, roles = selected}
end
local function searchPlayer(id, index, info)
    local api = C_LFGList
    if type(api.GetSearchResultPlayerInfo) == "function" then
        local data = ns.ReadPublic(api.GetSearchResultPlayerInfo, id, index)
        if not publicTable(data) then return end
        local tank, healer, damage
        -- Only documented enum bits; no hardcoded beta values or class guesses.
        local flags, enum = data.lfgRoles, Enum and Enum.LFGRoles
        if ns.GuideInteger(flags) and enum and bit and type(bit.band) == "function" then
            local function flag(key)
                return ns.GuideInteger(enum[key]) and bit.band(flags, enum[key]) ~= 0
            end
            tank, healer, damage = flag("Tank"), flag("Healer"), flag("Damage")
        end
        return player(data.name, data.className, data.level, data.assignedRole, tank, healer, damage)
    end
    if type(api.GetSearchResultMemberInfo) == "function" then
        local role, _, class, level = ns.ReadPublic(api.GetSearchResultMemberInfo, id, index)
        -- Older APIs expose the leader name, not the other members' names.
        if index == 1 then return player(info.leaderName, class, level, role) end
    end
end
local function applicantPlayer(id, index)
    if type(C_LFGList.GetApplicantMemberInfo) ~= "function" then return end
    local ok, name, _, class, level, _, _, tank, healer, damage, role = pcall(C_LFGList.GetApplicantMemberInfo, id, index)
    if ok then return player(name, class, level, role, tank, healer, damage) end
end
function ns.GroupFinderRoleMatches(row, role)
    if role == "all" then return true end
    if role == "unknown" then return next(row.roles) == nil end
    return row.roles[role] == true
end
function ns.ReadGroupFinderPlayers(mode, role)
    local api, result, seen = C_LFGList, {}, {}
    if not api then return result, "Player roles unavailable" end
    local applicants = mode == "applicants"
    local ids, total
    if applicants then ids = ns.ReadPublic(api.GetApplicants)
    else
        total, ids = ns.ReadPublic(api.GetFilteredSearchResults or api.GetSearchResults)
    end
    if not publicTable(ids) then
        ns.groupFinderRoleStatus = (applicants and "Applicant" or "Search") .. " player data unavailable on this build."
        return result, "Player roles unavailable"
    end
    local unread, inspected = 0, 0
    for index = 1, math.min(#ids, 200) do
        local id = ids[index]
        if ns.GuideInteger(id) and id > 0 and not seen[id] then
            seen[id] = true
            local info = ns.ReadPublic(applicants and api.GetApplicantInfo or api.GetSearchResultInfo, id)
            if publicTable(info) and ns.GuideInteger(info.numMembers, 40) and info.numMembers > 0 then
                local valid = not applicants or ns.Public(info.applicationStatus) and
                    (info.applicationStatus == "applied" or info.applicationStatus == "invited")
                if valid and (applicants or ns.Public(info.isDelisted) and info.isDelisted ~= true) then
                    for member = 1, info.numMembers do
                        local row = applicants and applicantPlayer(id, member) or not applicants and searchPlayer(id, member, info)
                        inspected = inspected + 1
                        if row then
                            row.group = not applicants and ns.SafeTitle(info.name) or nil
                            if ns.GroupFinderRoleMatches(row, role or "all") then result[#result + 1] = row end
                        else unread = unread + 1 end
                    end
                end
            end
        end
    end
    ns.groupFinderRoleStatus = (applicants and "Applicants" or "Search players") .. ": " .. #result .. " matched; " .. inspected
        .. " inspected; " .. unread .. " unavailable; " .. math.max(0, #ids - 200) .. " listings beyond read limit."
    return result, #result == 0 and "No matching players" or nil
end
local function finderContext()
    local finder = LFGListFrame
    if not finder or ns.ReadPublic(finder.IsShown, finder) ~= true then return end
    local applicants, search = finder.ApplicationViewer, finder.SearchPanel
    if applicants and ns.ReadPublic(applicants.IsShown, applicants) == true then return finder, "applicants" end
    if search and ns.ReadPublic(search.IsShown, search) == true then return finder, "search" end
end
local function create()
    if ns.groupFinderRoleWindow then return ns.groupFinderRoleWindow end
    local frame = CreateFrame("Frame", "WowTogetherGroupFinderRoles", UIParent, "BackdropTemplate")
    ns.groupFinderRoleWindow = frame
    frame:SetSize(290, 410); frame:SetPoint("CENTER", 430, 0); frame:SetClampedToScreen(true)
    frame:SetFrameStrata("DIALOG"); frame:SetMovable(true); frame:EnableMouse(true); ns.UIPanel(frame)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", function() frame:StopMovingOrSizing(); frame.placed = true end)
    frame.title = ns.UILabel(frame, nil, 14, ns.UIColors.gold)
    frame.title:SetPoint("TOPLEFT", 12, -12); frame.title:SetWidth(236); frame.title:SetText("Player roles")
    frame.close = ns.UIButton(frame, "×", 24, function() frame.dismissed = true; frame:Hide() end)
    frame.close:SetPoint("TOPRIGHT", -8, -8)
    frame.role = "all"
    frame.filter = ns.UIDropdown(frame, roles, 266, function(role)
        frame.role, frame.page = role, 1; ns.RefreshGroupFinderRoles()
    end)
    frame.filter:SetPoint("TOPLEFT", 12, -42); frame.filter:SetChoice("all")
    frame.source = ns.UILabel(frame, nil, 11, ns.UIColors.muted)
    frame.source:SetPoint("TOPLEFT", 12, -82); frame.source:SetWidth(266)
    frame.rows = {}
    for index = 1, 6 do
        local row = CreateFrame("Frame", nil, frame)
        row:SetSize(266, 42); row:SetPoint("TOPLEFT", 12, -105 - (index - 1) * 44)
        row.name = ns.UILabel(row, nil, 12); row.name:SetPoint("TOPLEFT"); row.name:SetWidth(266)
        row.details = ns.UILabel(row, nil, 10, ns.UIColors.muted)
        row.details:SetPoint("TOPLEFT", 0, -19); row.details:SetWidth(266)
        frame.rows[index] = row
    end
    frame.empty = ns.UILabel(frame, nil, 12, ns.UIColors.muted)
    frame.empty:SetPoint("TOPLEFT", 12, -108); frame.empty:SetWidth(266)
    frame.page, frame.pages = 1, 1
    frame.previous = ns.UIButton(frame, "‹", 28, function() frame.page = frame.page - 1; ns.RefreshGroupFinderRoles() end)
    frame.previous:SetPoint("BOTTOMLEFT", 12, 12)
    frame.next = ns.UIButton(frame, "›", 28, function() frame.page = frame.page + 1; ns.RefreshGroupFinderRoles() end)
    frame.next:SetPoint("BOTTOMRIGHT", -12, 12)
    frame.count = ns.UILabel(frame, nil, 11, ns.UIColors.muted); frame.count:SetPoint("BOTTOM", 0, 20)
    frame:SetScript("OnHide", function() frame.filter.menu:Hide() end)
    frame:Hide()
    return frame
end
function ns.RefreshGroupFinderRoles()
    local finder, mode = finderContext()
    local frame = ns.groupFinderRoleWindow
    if not finder or not ns.Option("groupFinderRoles") then
        if frame then frame:Hide(); frame.dismissed = nil; frame.context = nil end
        return
    end
    frame = frame or create()
    if frame.dismissed then return end
    if frame.context ~= mode then frame.context, frame.page = mode, 1 end
    if not frame.placed then
        local anchor = PVEFrame or finder
        local right, top = ns.ReadPublic(anchor.GetRight, anchor), ns.ReadPublic(anchor.GetTop, anchor)
        local scale, parentScale = ns.ReadPublic(anchor.GetEffectiveScale, anchor), ns.ReadPublic(UIParent.GetEffectiveScale, UIParent)
        if ns.Public(right) and ns.Public(top) and type(right) == "number" and type(top) == "number"
            and right == right and top == top and math.abs(right) < 100000 and math.abs(top) < 100000 then
            local ratio = type(scale) == "number" and scale > 0 and scale < 100
                and type(parentScale) == "number" and parentScale > 0 and parentScale < 100 and scale / parentScale or 1
            frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", right * ratio + 8, top * ratio)
        end
    end
    local players, empty = ns.ReadGroupFinderPlayers(mode, frame.role)
    frame.pages = math.max(1, math.ceil(#players / 6)); frame.page = math.max(1, math.min(frame.pages, frame.page))
    frame.source:SetText((mode == "applicants" and "Applicants" or "Listed players") .. " · " .. #players .. " matches")
    frame.empty:SetText(empty or ""); frame.empty:SetShown(empty ~= nil)
    for index, row in ipairs(frame.rows) do
        local data = players[(frame.page - 1) * 6 + index]
        row.data = data; row:SetShown(data ~= nil)
        if data then
            local names = {}
            for _, entry in ipairs(roles) do if data.roles[entry[1]] then names[#names + 1] = entry[2] end end
            row.name:SetText(data.name)
            row.details:SetText(table.concat(names, " / ") .. (#names == 0 and "Unspecified" or "")
                .. (data.level and " · Lv " .. data.level or "") .. (data.class and " · " .. data.class or ""))
        end
    end
    frame.filter:SetChoice(frame.role); frame.count:SetText(frame.page .. " / " .. frame.pages)
    frame.previous:SetEnabled(frame.page > 1); frame.next:SetEnabled(frame.page < frame.pages)
    frame:Show()
end
function ns.InitializeGroupFinderRoles()
    -- Only the owned controller is polled/hooked. Read data once per second
    -- while the relevant native panel is visible, and promptly on its events.
    local controller, elapsed, dirty = CreateFrame("Frame"), 0, true
    ns.groupFinderRoleController = controller
    controller:SetScript("OnUpdate", function(_, delta)
        if not ns.Public(delta) or type(delta) ~= "number" then return end
        elapsed = elapsed + delta
        if elapsed < .25 then return end
        local finder = finderContext()
        if not finder or dirty or elapsed >= 1 then
            elapsed, dirty = 0, nil; ns.RefreshGroupFinderRoles()
        end
    end)
    for _, event in ipairs({"LFG_LIST_SEARCH_RESULTS_RECEIVED", "LFG_LIST_SEARCH_RESULT_UPDATED", "LFG_LIST_APPLICANT_LIST_UPDATED", "LFG_LIST_APPLICANT_UPDATED"}) do
        local previous = ns.handlers[event]
        ns.On(event, function(...) if previous then previous(...) end; dirty = true end)
    end
end
function ns.GroupFinderRoleDiagnostics(output)
    output("Group finder roles: " .. (ns.groupFinderRoleStatus or "Open Blizzard's player search or applicant list."))
end
