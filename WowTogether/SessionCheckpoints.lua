local addonName, ns = ...

-- One resumable guide in guideState; two small summaries here. Never duplicate
-- the fixed plan or persist frames, preview targets, peer credit or live clocks.
local anchor, previousXP, ready
local function integer(value, maximum)
    return ns.GuideInteger(value, maximum)
end
local function clock()
    local value = ns.ReadPublic(GetTime)
    if type(value) == "number" and value == value and value >= 0 and value < 1000000000 then return value end
end
local function store()
    return ready and ns.char and ns.char.guideSessions
end
local function xpSnapshot()
    local level, xp, maximum = ns.ReadPublic(UnitLevel, "player"), ns.ReadPublic(UnitXP, "player"), ns.ReadPublic(UnitXPMax, "player")
    if not integer(level, 60) or level < 1 or not integer(xp, 10000000) or not integer(maximum, 10000000)
        or maximum == 0 and level ~= 60 or maximum > 0 and xp >= maximum then return end
    return {level = level, xp = xp, maximum = maximum}
end
local function identity(guide)
    if type(guide) ~= "table" or not ns.Public(guide.key) or type(guide.key) ~= "string" then return end
    return guide.key .. (guide.mode == "profession" and ":" .. tostring(guide.targetSkill) or "")
end
local function safeSummary(source)
    if type(source) ~= "table" or source.schema ~= 1 or not ns.SafeTitle(source.title)
        or type(source.key) ~= "string" or #source.key > 600
        or not integer(source.xp, 10000000000) or not integer(source.quests, 4096)
        or not ns.Public(source.seconds) or type(source.seconds) ~= "number" or source.seconds ~= source.seconds
        or source.seconds < 0 or source.seconds > 100000000 then return end
    local result = {schema = 1, key = source.key, title = source.title, xp = source.xp,
        quests = source.quests, seconds = source.seconds, questIDs = {}}
    for _, key in ipairs({"xpKnown", "xpPartial", "timePartial"}) do result[key] = source[key] == true end
    for _, key in ipairs({"startLevel", "endLevel"}) do
        if integer(source[key], 60) and source[key] > 0 then result[key] = source[key] end
    end
    local count = 0
    for id, value in pairs(type(source.questIDs) == "table" and source.questIDs or {}) do
        if integer(id, 100000000) and id > 0 and value == true then
            count = count + 1; if count > 4096 then return end
            result.questIDs[id] = true
        end
    end
    if count ~= result.quests then return end
    return result
end

function ns.PausedSessionCheckpoint()
    local saved = ns.char and ns.char.guideState
    if type(saved) == "table" and saved.schema == 1 and saved.paused == true and type(saved.guide) == "table"
        and ns.SafeTitle(saved.guide.title) and type(saved.guide.key) == "string" and #saved.guide.key <= 600 then return saved end
end

local function captureXP(summary)
    local current = xpSnapshot()
    if not current then summary.xpPartial = true; previousXP = nil; return end
    summary.xpKnown, summary.endLevel = true, current.level
    summary.startLevel = summary.startLevel or current.level
    if previousXP then
        local gained = current.xp - previousXP.xp
        if current.level > previousXP.level then
            gained = previousXP.maximum - previousXP.xp + current.xp
            for level = previousXP.level + 1, current.level - 1 do
                -- Session totals use observed native thresholds, never a Classic
                -- estimate. A missing level leaves the total explicitly partial.
                local threshold = ns.xpCurve and ns.xpCurve[level]
                if not integer(threshold, 10000000) or threshold == 0 then gained = nil; break end
                gained = gained + threshold
            end
        end
        if current.level < previousXP.level or not gained or gained < 0 then summary.xpPartial = true
        else summary.xp = math.min(10000000000, summary.xp + gained) end
    end
    previousXP = current
end

function ns.CaptureSessionCheckpoint()
    local state, guide = store(), ns.routeSelection
    if not state or not state.current or not guide or not identity(guide) then
        if ready then ns.UpdateSessionUI() end
        return
    end
    local summary, now = state.current, clock()
    -- Legacy adaptive guides can replace their descriptor during progress.
    -- Keep that session continuous; explicit guide starts are handled by Begin.
    summary.key, summary.title = identity(guide), guide.title
    if now and anchor and now >= anchor then summary.seconds = math.min(100000000, summary.seconds + now - anchor)
    elseif not now or anchor and now < anchor then summary.timePartial = true end
    anchor = now
    captureXP(summary)
    local saved = ns.char.guideState
    if type(saved) == "table" and type(saved.guide) == "table" and saved.guide.key == guide.key then
        -- Checkpoint metadata describes the real quest step, not the arrow's
        -- corpse, flight, merchant detour or history preview.
        local route = ns.selectedRoute
        local step = route and (route.stops and route.stops[1] or route.pendingStop)
        local checkpoint = {title = guide.title, complete = route and route.complete == true}
        if step then
            if integer(step.id, 100000000) then checkpoint.questID = step.id end
            if integer(step.guideStep, 4096) then checkpoint.step = step.guideStep end
            if ns.SafeTitle(step.title) then checkpoint.next = step.title end
        end
        saved.checkpoint = checkpoint
    end
    ns.UpdateSessionUI()
end

function ns.BeginGuideSession(guide)
    local state = store()
    if not state or not guide or type(guide.key) ~= "string" then return end
    if state.current and state.current.key ~= identity(guide) then ns.FinishGuideSession() end
    if state.current then ns.CaptureSessionCheckpoint() end
    if not state.current then
        state.current = {schema = 1, key = identity(guide), title = guide.title,
            xp = 0, quests = 0, seconds = 0, questIDs = {}}
    end
    -- Reloading continues the logical session, but not its offline time/XP.
    anchor, previousXP = clock(), xpSnapshot()
    local summary = state.current
    if previousXP then
        summary.xpKnown, summary.endLevel = true, previousXP.level
        summary.startLevel = summary.startLevel or previousXP.level
    else summary.xpPartial = true end
    if not anchor then summary.timePartial = true end
end

function ns.FinishGuideSession()
    local state = store()
    if not state or not state.current then return end
    ns.CaptureSessionCheckpoint()
    state.last, state.current = state.current, nil
    anchor, previousXP = nil, nil
end

function ns.PauseGuideSession()
    if not ns.routeSelection or ns.routePlanning or ns.guideScanning then return false end
    ns.SaveSelectedGuide(); ns.CaptureSessionCheckpoint()
    local saved = ns.char.guideState
    if type(saved) ~= "table" or type(saved.guide) ~= "table" or saved.guide.key ~= ns.routeSelection.key then return false end
    saved.paused = true
    ns.StopGuide(false, true)
    ns.ShowSessionCheckpoint()
    return true
end

function ns.ResumeGuideSession()
    local saved = ns.PausedSessionCheckpoint()
    if not saved or ns.routeSelection or ns.routePlanning or ns.guideScanning then return false end
    if ns.RouteInCombat() then ns.Print("Resume your guide after combat."); return false end
    saved.paused = nil
    ns.pendingSavedGuide = saved
    ns.RestoreSavedGuide()
    ns.OpenGuideWindow(); ns.Refresh()
    return ns.routeSelection ~= nil or ns.routePlanning ~= nil
end

local function duration(seconds)
    local minutes = math.floor(seconds / 60)
    return minutes >= 60 and string.format("%dh %02dm", math.floor(minutes / 60), minutes % 60)
        or minutes > 0 and string.format("%dm", minutes) or string.format("%ds", math.floor(seconds))
end
function ns.GuideSessionSummary()
    local state = store()
    return state and (state.current or state.last)
end
function ns.GuideSessionSummaryText()
    local summary = ns.GuideSessionSummary()
    if not summary then return "Your session summary appears when you start a guide." end
    local xp = summary.xpKnown and ((summary.xpPartial and "At least " or "") .. summary.xp .. " XP") or "XP unavailable"
    local time = (summary.timePartial and "At least " or "") .. duration(summary.seconds) .. " played"
    return xp .. " • " .. summary.quests .. " quests completed • " .. time
end

function ns.UpdateSessionResumeBar()
    local home = ns.ui and ns.ui.home
    if not home then return end
    local guide, saved, summary = ns.routeSelection, ns.PausedSessionCheckpoint(), ns.GuideSessionSummary()
    local running = guide and ns.selectedRoute and ns.selectedRoute.complete ~= true
    if ns.Option("uiNext") then
        local displayGuide = running and guide or saved and saved.guide
        local active = displayGuide ~= nil
        home.resume:SetShown(active)
        home.resume.category:Hide()
        home.resume.title:SetText(active and ns.HubActiveGuideHeading and ns.HubActiveGuideHeading(displayGuide) or active and displayGuide.title or "")
        local detail, step, total
        if active and ns.HubActiveGuideProgress then detail, step, total = ns.HubActiveGuideProgress(displayGuide, running and ns.selectedRoute) end
        if saved and saved.checkpoint and saved.checkpoint.step then
            step = saved.checkpoint.step
            if total and total > 0 then detail = "step " .. step .. " of " .. total end
        end
        home.resume.detail:SetText(detail or "")
        home.resume.fraction = step and total and total > 0 and math.max(0, math.min(1, (step - 1) / total)) or 0
        return
    end
    home.resume:SetShown(running ~= nil or saved ~= nil or summary ~= nil)
    home.resume.category:SetText(saved and "PAUSED GUIDE" or running and "CONTINUE YOUR GUIDE" or "LAST SESSION")
    home.resume.title:SetText(running and guide.title or saved and saved.guide.title or summary and summary.title or "")
    home.resume.detail:SetText(ns.GuideSessionSummaryText())
end

function ns.UpdateSessionUI()
    ns.UpdateSessionResumeBar()
end

function ns.ShowSessionCheckpoint()
    ns.CaptureSessionCheckpoint()
    local saved = ns.PausedSessionCheckpoint()
    if not saved then return false end
    ns.ShowSuggestionChip("session", saved.guide.key,
        "Guide paused — " .. saved.guide.title .. " · " .. ns.GuideSessionSummaryText(),
        {{label = "Resume", callback = function() ns.ResumeGuideSession() end}, {label = "Dismiss"}})
    return true
end

function ns.InitializeSessionCheckpoints()
    local saved = ns.char.guideSessions
    local source = type(saved) == "table" and saved or {}
    local state = {current = safeSummary(source.current), last = safeSummary(source.last)}
    ns.char.guideSessions, ready = state, true
    local guideState = ns.char.guideState
    if state.current and (type(guideState) ~= "table" or not guideState.guide or guideState.paused
        or state.current.key ~= identity(guideState.guide)) then state.last, state.current = state.current, nil end
    local function chain(event, callback) ns.On(event, callback) end
    chain("PLAYER_XP_UPDATE", function(unit) if ns.Public(unit) and unit == "player" then ns.CaptureSessionCheckpoint() end end)
    -- PLAYER_LEVEL_UP can precede the reset of UnitXP. The XP event (and
    -- existing batched guide refresh) reads the settled level/XP pair instead.
    chain("QUEST_TURNED_IN", function(id)
        local summary = state.current
        if summary and ns.routeSelection and integer(id, 100000000) and id > 0
            and summary.quests < 4096 and not summary.questIDs[id] then
            summary.questIDs[id], summary.quests = true, summary.quests + 1
        end
        ns.CaptureSessionCheckpoint()
    end)
    chain("PLAYER_LOGOUT", ns.CaptureSessionCheckpoint)
end
