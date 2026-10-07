local addonName, ns = ...

local preview
local function cancelPreview() preview = nil end
function ns.ProfessionWindowMatches(id)
    if not ns.professionWindowOpen or not C_TradeSkillUI then return false end
    local info = ns.ReadPublic(C_TradeSkillUI.GetChildProfessionInfo)
    if type(info) ~= "table" or not ns.GuideInteger(info.professionID) or info.professionID <= 0 then
        info = ns.ReadPublic(C_TradeSkillUI.GetBaseProfessionInfo)
    end
    return type(info) == "table" and ns.GuideInteger(info.professionID) and info.professionID == id
end

function ns.FinishProfessionScan(id)
    local prompt = ns.professionScanPrompt
    if prompt and prompt.professionID == id then prompt:Hide() end
end

function ns.OfferProfessionScan(id)
    local facts = ns.ProfessionFacts(id)
    if not facts or not ns.professionData[id] then return end
    if ns.ProfessionWindowMatches(id) then ns.QueueProfessionUpdate(true); return end
    local prompt = ns.professionScanPrompt
    if not prompt then
        prompt = CreateFrame("Frame", "WowTogetherProfessionScan", UIParent, "BackdropTemplate")
        ns.professionScanPrompt = prompt
        prompt:SetSize(420, 180); prompt:SetPoint("CENTER"); prompt:SetFrameStrata("DIALOG")
        prompt:SetClampedToScreen(true); ns.UIPanel(prompt); ns.UIClose(prompt)
        prompt.title = ns.UILabel(prompt, nil, 17, ns.UIColors.gold)
        prompt.title:SetPoint("TOPLEFT", 20, -20)
        prompt.text = ns.UILabel(prompt, nil, 12)
        prompt.text:SetPoint("TOPLEFT", 20, -54); prompt.text:SetSize(380, 66); prompt.text:SetWordWrap(true)
        prompt.scan = ns.UIButton(prompt, "Scan current progress", 178, function()
            local guide = ns.routeSelection
            if not guide or guide.mode ~= "profession" or guide.professionID ~= prompt.professionID then prompt:Hide(); return end
            if ns.RouteInCombat() then prompt.text:SetText("Scan when you are out of combat."); return end
            local opener = C_TradeSkillUI and C_TradeSkillUI.OpenTradeSkill
            if type(opener) ~= "function" then
                prompt.text:SetText("Open your " .. ns.ProfessionFacts(prompt.professionID).name .. " window to scan current progress.")
                return
            end
            -- One manual click. Wait for the real recipe events before reading
            -- or treating the window as open; pcall isn't a protection bypass.
            local okay, opened = pcall(opener, prompt.professionID)
            if okay and ns.Public(opened) and opened == true then
                prompt.text:SetText("Reading your current skill, recipes and materials…")
            else
                prompt.text:SetText("Open your " .. ns.ProfessionFacts(prompt.professionID).name .. " window to scan current progress.")
            end
        end)
        prompt.scan:SetPoint("BOTTOMLEFT", 20, 18); ns.UIButtonTone(prompt.scan, true)
        prompt.later = ns.UIButton(prompt, "Later", 110, function() prompt:Hide() end)
        prompt.later:SetPoint("BOTTOMRIGHT", -20, 18)
    end
    prompt.professionID = id
    prompt.title:SetText("Scan " .. facts.name .. " progress")
    prompt.text:SetText("Open your profession window to check skill, learned recipes and materials before crafting.")
    prompt:Show(); prompt:Raise()
end

local function layout(frame)
    local width = frame:GetWidth()
    frame.body:SetWidth(width - 62); frame.child:SetWidth(width - 58)
    frame.nextText:SetWidth(width - 48)
    local height = frame.nextText:GetStringHeight()
    if ns.Public(height) and type(height) == "number" then
        frame.nextText:SetHeight(math.max(80, math.min(height, frame:GetHeight() - 280)))
    end
end
local function create()
    if ns.professionViewer then return ns.professionViewer end
    local frame = CreateFrame("Frame", "WowTogetherProfessionGuide", UIParent, "BackdropTemplate")
    ns.professionViewer = frame
    frame:SetSize(660, 570); frame:SetPoint("CENTER"); frame:SetFrameStrata("DIALOG")
    frame:SetClampedToScreen(true); frame:SetMovable(true); frame:SetResizable(true)
    if type(frame.SetResizeBounds) == "function" then frame:SetResizeBounds(540, 440, 1000, 900) end
    ns.UIPanel(frame); ns.UIClose(frame)
    frame:RegisterForDrag("LeftButton"); frame:EnableMouse(true)
    frame:SetScript("OnDragStart", function(self) self:StartMoving() end)
    frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    frame.icon = frame:CreateTexture(nil, "ARTWORK"); frame.icon:SetSize(36, 36); frame.icon:SetPoint("TOPLEFT", 18, -18)
    frame.title = ns.UILabel(frame, nil, 20, ns.UIColors.gold); frame.title:SetPoint("TOPLEFT", 64, -18)
    frame.skill = ns.UILabel(frame, nil, 11, ns.UIColors.muted); frame.skill:SetPoint("TOPLEFT", 64, -44)
    frame.goal = ns.UIDropdown(frame, {{75, "Goal: skill 75"}, {150, "Goal: skill 150"}, {225, "Goal: skill 225"}, {300, "Goal: skill 300"}}, 160,
        function(value) ns.ProfessionGoal(frame.professionID, value); ns.RefreshProfessionViewer(true) end)
    frame.goal:SetPoint("TOPRIGHT", -22, -72)
    frame.nextLabel = ns.UILabel(frame, nil, 10, ns.UIColors.gold); frame.nextLabel:SetPoint("TOPLEFT", 22, -79); frame.nextLabel:SetText("YOUR NEXT STEP")
    frame.nextText = ns.UILabel(frame, nil, 13); frame.nextText:SetPoint("TOPLEFT", 22, -114); frame.nextText:SetHeight(80)
    frame.nextText:SetWordWrap(true); frame.nextText:SetJustifyV("TOP")
    frame.divider = ns.UIDivider(frame, -202)
    frame.divider:ClearAllPoints()
    frame.divider:SetPoint("TOPLEFT", frame.nextText, "BOTTOMLEFT", -21, -12)
    frame.divider:SetPoint("TOPRIGHT", frame.nextText, "BOTTOMRIGHT", 21, -12)
    local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", frame.divider, "BOTTOMLEFT", 21, -12); scroll:SetPoint("BOTTOMRIGHT", -38, 62)
    frame.child = CreateFrame("Frame", nil, scroll); frame.child:SetSize(600, 120); scroll:SetScrollChild(frame.child)
    frame.body = ns.UILabel(frame.child, nil, 12); frame.body:SetPoint("TOPLEFT"); frame.body:SetJustifyV("TOP"); frame.body:SetWordWrap(true)
    frame.start = ns.UIButton(frame, "Start crafting guide", 172, function() ns.StartProfessionGuide(frame.professionID, ns.ProfessionGoal(frame.professionID)) end)
    frame.start:SetPoint("BOTTOMLEFT", 22, 16); ns.UIButtonTone(frame.start, true)
    frame.materials = ns.UIButton(frame, "Materials", 110, function()
        ns.ShowProfessionShopping(frame.professionID, ns.ProfessionGoal(frame.professionID), "batch")
    end)
    frame.materials:SetPoint("LEFT", frame.start, "RIGHT", 10, 0)
    frame.refresh = ns.UIButton(frame, "Refresh", 92, function() ns.RefreshProfessionPlan(frame.professionID) end)
    frame.refresh:SetPoint("BOTTOMRIGHT", -30, 16)
    local resize = ns.UIButton(frame, "↘", 20, function() end); resize:SetPoint("BOTTOMRIGHT", -4, 4)
    resize:SetScript("OnMouseDown", function() frame:StartSizing("BOTTOMRIGHT") end)
    resize:SetScript("OnMouseUp", function() frame:StopMovingOrSizing(); layout(frame) end)
    frame:SetScript("OnSizeChanged", layout); frame:SetScript("OnHide", cancelPreview)
    ns.UIHelp(frame.goal, "Plan towards this profession skill. Character level and available training control rank upgrades.")
    ns.UIHelp(frame.materials, "View next-batch materials or an estimate up to your skill goal, after bag stock and planned intermediates.")
    layout(frame)
    return frame
end

local function setBody(frame, text)
    frame.body:SetText(text)
    local height = frame.body:GetStringHeight()
    if ns.Public(height) and type(height) == "number" then frame.child:SetHeight(math.max(120, height + 12)) end
end

local function previewText(id, plan)
    local facts = ns.ProfessionFacts(id)
    local lines = {"CRAFTING PATH", "Balanced materials and crafting time • approximate batches", ""}
    if plan.start >= plan.target then lines[#lines + 1] = "Goal reached. Choose a higher skill goal when ready." end
    for _, step in ipairs(plan.steps) do
        lines[#lines + 1] = "|cffffd17a" .. step.start .. "–" .. step.finish .. "|r  " .. step.recipe.name .. "  •  ~" .. math.ceil(step.crafts) .. " crafts"
    end
    if plan.missing > 0 then lines[#lines + 1] = "\nContinue with your trainer's available recipes. Open your profession window to check new options." end
    lines[#lines + 1] = "\nRANK TRAINING"
    for _, rank in ipairs(facts.ranks) do
        if rank.maximum <= plan.target and rank.maximum > plan.start then
            local trainer = ns.ProfessionTrainer(id, rank.maximum)
            lines[#lines + 1] = rank.name .. " • cap " .. rank.maximum .. " • skill " .. rank.skill .. " / character level " .. rank.level
                .. (trainer and ("\n    " .. trainer.name .. " • " .. trainer.hub) or "")
        end
    end
    lines[#lines + 1] = "\nSkill gains vary. The next step adapts to your actual recipes, materials and skill."
    return table.concat(lines, "\n")
end

function ns.RefreshProfessionViewer(force)
    local frame = ns.professionViewer
    if not frame or not frame.professionID then return end
    local id, facts = frame.professionID, ns.ProfessionFacts(frame.professionID)
    local info, goal = ns.professionData[id], ns.ProfessionGoal(id)
    frame.title:SetText(facts.name); frame.icon:SetTexture(facts.icon); frame.goal:SetChoice(goal)
    frame.skill:SetText(info and ("Skill " .. (info.skill or "?") .. " / " .. (info.maximum or "?") .. (info.cached and " • Last recorded" or "")) or "Choose a profession to learn")
    local guide = ns.routeSelection
    local active = guide and guide.mode == "profession" and guide.professionID == id and guide.targetSkill == goal
    local route
    if active then ns.UpdateProfessionRoute(guide); route = ns.selectedRoute
    else route = ns.BuildProfessionGuideRoute({key = "profession:" .. id, professionID = id, targetSkill = goal, title = facts.name}) end
    frame.route = route
    local stop = route.stops[1]
    frame.nextText:SetText(stop.label .. "\n|cffadb4be" .. stop.description .. "|r")
    layout(frame)
    frame.materials:SetEnabled(route.materials and #route.materials > 0)
    local signature = table.concat({id, goal, info and info.skill or 1, ns.professionRevision or 0}, ":")
    if not force and signature == frame.planSignature then return end
    frame.planSignature = signature
    cancelPreview()
    setBody(frame, "Calculating your crafting path…")
    local job = {frame = frame, signature = signature}
    preview = job
    local worker = coroutine.create(function() return ns.PlanProfessionPreview(id, goal, true) end)
    local function run()
        if preview ~= job or frame.planSignature ~= signature or not frame:IsShown() then return end
        if ns.RouteInCombat() then
            -- Existing contents stay usable. Resume calculation after combat.
            cancelPreview(); frame.planSignature = nil; return
        end
        local okay, result = coroutine.resume(worker)
        if not okay then
            ns.professionStatus = "Crafting preview failed: " .. tostring(result)
            cancelPreview(); setBody(frame, "Refresh to try your crafting path again."); return
        end
        if coroutine.status(worker) == "dead" then
            cancelPreview(); frame.plan = result; setBody(frame, previewText(id, result))
        elseif C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, run)
        else cancelPreview(); setBody(frame, "Open your profession window to view your next craft.") end
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, run) else run() end
end

function ns.ShowProfessionViewer(id)
    if not ns.ProfessionFacts(id) then return end
    ns.ReadProfessionSkills()
    local frame = create()
    frame.professionID = id; frame:Show(); frame:Raise()
    ns.RefreshProfessionViewer(true)
end
function ns.ResumeProfessionPreview()
    if ns.professionViewer and ns.professionViewer:IsShown() and not ns.professionViewer.planSignature then ns.RefreshProfessionViewer(true) end
end
