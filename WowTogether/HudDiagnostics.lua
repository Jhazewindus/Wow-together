local addonName, ns = ...

-- What the guide window is, as the game sees it.
--
-- A window that looks wrong on one machine and right in the test host cannot
-- be fixed by guessing. `/wt hud` prints the facts that decide what is drawn
-- (shown, alpha, size, position, background, which header controls exist and
-- where) and any error one of the window's add-on parts raised. `/wt hud
-- reset` puts the window back to how a new install has it.
local function read(object, method, ...)
    if not object or type(object[method]) ~= "function" then return nil end
    local a, b, c, d = ns.ReadPublic(object[method], object, ...)
    return a, b, c, d
end

local function number(value)
    return type(value) == "number" and (math.floor(value * 100 + 0.5) / 100) or tostring(value)
end

local function describe(name, region)
    if not region then return name .. " missing" end
    local text = read(region, "GetText")
    return name .. " " .. (read(region, "IsShown") and "shown" or "HIDDEN")
        .. " alpha " .. number(read(region, "GetAlpha"))
        .. " at " .. number(read(region, "GetLeft")) .. "," .. number(read(region, "GetTop"))
        .. " size " .. number(read(region, "GetWidth")) .. "x" .. number(read(region, "GetHeight"))
        .. (type(text) == "string" and (" text \"" .. string.sub(text, 1, 30) .. "\"") or "")
end

function ns.HudDiagnostics(output)
    output = output or ns.Print
    local frame = ns.navigation
    if not frame then output("Guide window: not created."); return end
    if ns.testBuild and output == ns.Print then output("Test build: " .. ns.testBuild .. ".") end
    local r, g, b, a = read(frame, "GetBackdropColor")
    local br, bg, bb, ba = read(frame, "GetBackdropBorderColor")
    output("Guide window: " .. (read(frame, "IsShown") and "shown" or "HIDDEN") .. ", visible " .. tostring(read(frame, "IsVisible"))
        .. ", alpha " .. number(read(frame, "GetAlpha")) .. " (effective " .. number(read(frame, "GetEffectiveAlpha")) .. ")"
        .. ", scale " .. number(read(frame, "GetEffectiveScale")) .. ", size " .. number(read(frame, "GetWidth")) .. "x" .. number(read(frame, "GetHeight"))
        .. ", left " .. number(read(frame, "GetLeft")) .. ", top " .. number(read(frame, "GetTop"))
        .. ", strata " .. tostring(read(frame, "GetFrameStrata")) .. " level " .. tostring(read(frame, "GetFrameLevel")) .. ".")
    output("Guide window settings: Glance " .. tostring(ns.Option("guideGlance")) .. ", solid background " .. tostring(ns.Option("guideOpaque"))
        .. ", window on " .. tostring(ns.Option("routeArrow")) .. ", separate arrow " .. tostring(ns.Option("standaloneArrow"))
        .. ". Fill " .. number(r) .. "," .. number(g) .. "," .. number(b) .. " alpha " .. number(a)
        .. "; border " .. number(br) .. "," .. number(bg) .. "," .. number(bb) .. " alpha " .. number(ba) .. ".")
    -- Where the window is fastened, and whether the game can place it at all.
    local anchors = {}
    local count = read(frame, "GetNumPoints")
    for index = 1, type(count) == "number" and math.min(count, 4) or 0 do
        local okay, point, relativeTo, relativePoint, x, y = pcall(frame.GetPoint, frame, index)
        if okay then
            local name = type(relativeTo) == "table" and type(relativeTo.GetName) == "function" and relativeTo:GetName() or tostring(relativeTo)
            anchors[#anchors + 1] = tostring(point) .. " to " .. tostring(name) .. " " .. tostring(relativePoint)
                .. " " .. number(ns.Public(x) and x or "withheld") .. "," .. number(ns.Public(y) and y or "withheld")
        end
    end
    output("Guide window placement: " .. tostring(count) .. " anchor(s)" .. (#anchors > 0 and (": " .. table.concat(anchors, "; ")) or "")
        .. ". Game can place it: " .. tostring(ns.NavigationPlaced and ns.NavigationPlaced())
        .. ". In combat: " .. tostring(ns.RouteInCombat()) .. ". Glance applied: " .. tostring(ns.GlanceActive and ns.GlanceActive())
        .. (ns.GlancePending and ns.GlancePending() and " (a switch is waiting for combat to end)" or "")
        .. (frame.heightPending and "; a height change is waiting for combat to end" or "") .. ".")
    if ns.hudNotes and #ns.hudNotes > 0 then output("Guide window repairs (" .. tostring(ns.hudRepairs or 0) .. "): " .. table.concat(ns.hudNotes, " | ") .. ".") end
    -- What kind of frame the game thinks this is, and a control: a plain
    -- frame given the same anchor and size. If the control has a position
    -- and the window does not, the cause is the window's own state.
    local flags = {}
    for _, method in ipairs({"IsRectValid", "IsUserPlaced", "IsProtected", "IsAnchoringRestricted", "IsClampedToScreen", "IsMovable", "IsResizable", "IsForbidden"}) do
        if type(frame[method]) == "function" then
            local okay, first, second = pcall(frame[method], frame)
            flags[#flags + 1] = method .. " " .. (okay and (tostring(first) .. (second ~= nil and ("/" .. tostring(second)) or "")) or "error")
        end
    end
    local control = "not tried"
    if not ns.RouteInCombat() then
        local okay, message = pcall(function()
            ns.hudControlFrame = ns.hudControlFrame or CreateFrame("Frame", nil, UIParent)
            local probe = ns.hudControlFrame
            probe:SetSize(frame:GetWidth(), frame:GetHeight())
            probe:ClearAllPoints()
            local point, relativeTo, relativePoint, x, y = frame:GetPoint(1)
            if point then probe:SetPoint(point, relativeTo, relativePoint, x, y) else probe:SetPoint("CENTER") end
            probe:Show()
            control = "left " .. number(probe:GetLeft()) .. ", top " .. number(probe:GetTop())
            probe:Hide()
        end)
        if not okay then control = "error " .. string.sub(tostring(message), 1, 80) end
    end
    output("Guide window kind: " .. table.concat(flags, ", ") .. ". Control frame with the same anchor and size: " .. control .. ".")
    output("Header: " .. describe("title", frame.title) .. "; " .. describe("step", frame.step) .. ".")
    output("Header buttons: " .. describe("pause", frame.pause) .. "; " .. describe("menu", frame.menu) .. "; " .. describe("close", frame.close) .. ".")
    output("Body: " .. describe("status", frame.status) .. "; " .. describe("skip", frame.skipStep) .. ".")
    output("Attached: " .. describe("path strip", frame.pathStrip) .. "; " .. describe("travel button", frame.travelButton)
        .. "; " .. describe("quest item", frame.questItem) .. ".")
    local errors = {}
    for name, message in pairs(ns.hudErrors or {}) do errors[#errors + 1] = name .. ": " .. string.sub(tostring(message), 1, 160) end
    table.sort(errors)
    output("Errors in the window's add-on parts: " .. (#errors > 0 and table.concat(errors, " | ") or "none recorded") .. ".")
end

-- Back to how a new install has it: full window, solid background, default
-- place and size, shown.
function ns.ResetHud()
    local frame = ns.navigation
    if not frame then return end
    if ns.RouteInCombat() then ns.Print("Leave combat before resetting the guide window."); return end
    ns.SetOption("guideGlance", false)
    ns.SetOption("guideOpaque", true)
    ns.SetOption("routeArrow", true)
    if ns.db then ns.db.arrowPosition, ns.db.arrowSize = nil, nil end
    frame:SetAlpha(1); frame:SetScale(1)
    frame:ClearAllPoints(); frame:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, 160)
    frame:SetSize(360, 168); frame.normalHeight = 168
    ns.hudErrors = nil
    if ns.UpdateNavigationBackground then ns.UpdateNavigationBackground() end
    if ns.UpdateNavigation then ns.UpdateNavigation() end
    if ns.LayoutNavigation then ns.LayoutNavigation() end
    ns.Print("Guide window reset: full window, solid background, default place and size. /wt hud prints its state.")
end

function ns.HudCommand(argument)
    if string.find(string.lower(argument or ""), "reset", 1, true) then ns.ResetHud() else ns.HudDiagnostics() end
end
