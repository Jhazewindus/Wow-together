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
    return ready and ns.db and ns.db.guideSessions and ns.db.guideSessions[ns.self]
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
    local saved = ns.db and ns.db.guideState and ns.db.guideState[ns.self]
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
    local saved = ns.db.guideState[ns.self]
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
    local saved = ns.db.guideState[ns.self]
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
    local running = guide and ns.selectedRoute
    home.resume:SetShown(running ~= nil or saved ~= nil or summary ~= nil)
    home.resume.category:SetText(saved and "PAUSED GUIDE" or running and "CONTINUE YOUR GUIDE" or "LAST SESSION")
    home.resume.title:SetText(running and guide.title or saved and saved.guide.title or summary and summary.title or "")
    home.resume.button.caption:SetText(saved and "Resume" or running and "Continue" or "Browse guides")
    home.resume.detail:SetText(ns.GuideSessionSummaryText())
end

function ns.UpdateSessionUI()
    ns.UpdateSessionResumeBar()
    local frame = ns.sessionWindow
    if not frame or not frame:IsShown() then return end
    local saved, summary = ns.PausedSessionCheckpoint(), ns.GuideSessionSummary()
    frame.guide:SetText(ns.routeSelection and ns.routeSelection.title or saved and saved.guide.title or summary and summary.title or "No guide selected")
    frame.stats:SetText(ns.GuideSessionSummaryText())
    local levels = summary and summary.startLevel and summary.endLevel
    frame.levels:SetText(levels and ("Level " .. summary.startLevel .. (summary.endLevel ~= summary.startLevel and " → " .. summary.endLevel or "")) or "")
    local entry = saved or ns.db.guideState[ns.self]
    local checkpoint = type(entry) == "table" and type(entry.checkpoint) == "table" and entry.checkpoint or nil
    local nextStep = checkpoint and ns.SafeTitle(checkpoint.next)
    frame.next:SetText(nextStep and ("Next: " .. nextStep) or checkpoint and checkpoint.complete and "Guide complete." or "")
    frame.action.caption:SetText(saved and "Resume guide" or "Save & pause")
    frame.action:SetEnabled(saved ~= nil or ns.routeSelection ~= nil and not ns.routePlanning and not ns.guideScanning)
end

function ns.ShowSessionCheckpoint()
    if not ns.sessionWindow then
        local frame = CreateFrame("Frame", "WowTogetherSessionCheckpoint", UIParent, "BackdropTemplate")
        ns.sessionWindow = frame
        frame:SetSize(480, 226); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG"); ns.UIPanel(frame)
        frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag("LeftButton")
        frame:SetScript("OnDragStart", frame.StartMoving)
        frame.title = ns.UILabel(frame, "GameFontNormalLarge", 17, ns.UIColors.gold)
        frame.title:SetPoint("TOPLEFT", 18, -16); frame.title:SetText("Session checkpoint")
        frame.close = ns.UIClose(frame)
        frame.guide = ns.UILabel(frame, "GameFontNormal", 13)
        frame.guide:SetPoint("TOPLEFT", 18, -48); frame.guide:SetHeight(20); frame.guide:SetWordWrap(false)
        frame.stats = ns.UILabel(frame, nil, 12)
        frame.stats:SetPoint("TOPLEFT", 18, -80); frame.stats:SetHeight(32); frame.stats:SetWordWrap(true)
        frame.levels = ns.UILabel(frame, nil, 11, ns.UIColors.gold)
        frame.levels:SetPoint("TOPLEFT", 18, -118); frame.levels:SetHeight(16)
        frame.next = ns.UILabel(frame, nil, 11, ns.UIColors.muted)
        frame.next:SetPoint("TOPLEFT", 18, -143); frame.next:SetWordWrap(true); frame.next:SetJustifyV("TOP")
        frame.action = ns.UIButton(frame, "Save & pause", 134, function()
            if ns.PausedSessionCheckpoint() then
                if ns.ResumeGuideSession() then frame:Hide() end
            else ns.PauseGuideSession() end
        end, true)
        frame.action:SetPoint("BOTTOMRIGHT", -18, 16)
        ns.EnableWindowResize(frame, {key = "sessionCheckpoint", minWidth = 400, minHeight = 226,
            maxWidth = 700, maxHeight = 420, layout = function(self)
                local width, height = self:GetWidth(), self:GetHeight()
                self.title:SetWidth(width - 64)
                for _, key in ipairs({"guide", "stats", "levels", "next"}) do self[key]:SetWidth(width - 36) end
                self.next:SetHeight(height - 196)
            end})
        -- Only the visible summary repaints on a one-second clock. No recurring
        -- timer or hidden-window scan; guide checkpoints follow existing events.
        frame:SetScript("OnUpdate", function(self, elapsed)
            self.elapsed = (self.elapsed or 0) + elapsed
            if self.elapsed >= 1 then self.elapsed = 0; ns.CaptureSessionCheckpoint() end
        end)
        UISpecialFrames[#UISpecialFrames + 1] = "WowTogetherSessionCheckpoint"
    end
    ns.sessionWindow:Show(); ns.sessionWindow:Raise(); ns.CaptureSessionCheckpoint(); ns.UpdateSessionUI()
end

function ns.InitializeSessionCheckpoints()
    ns.db.guideSessions = type(ns.db.guideSessions) == "table" and ns.db.guideSessions or {}
    local saved = ns.db.guideSessions[ns.self]
    local source = type(saved) == "table" and saved or {}
    local state = {current = safeSummary(source.current), last = safeSummary(source.last)}
    ns.db.guideSessions[ns.self], ready = state, true
    local guideState = ns.db.guideState[ns.self]
    if state.current and (type(guideState) ~= "table" or not guideState.guide or guideState.paused
        or state.current.key ~= identity(guideState.guide)) then state.last, state.current = state.current, nil end
    local function chain(event, callback)
        local previous = ns.handlers[event]
        ns.On(event, function(...)
            if previous then previous(...) end
            callback(...)
        end)
    end
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
