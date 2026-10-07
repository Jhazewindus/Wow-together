local addonName, ns = ...

local preview
local function cancelPreview() preview = nil end
local function layout(frame)
    local width = frame:GetWidth()
    frame.body:SetWidth(width - 62); frame.child:SetWidth(width - 58)
    frame.nextText:SetWidth(width - 48)
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
    ns.UIDivider(frame, -202)
    local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", 22, -214); scroll:SetPoint("BOTTOMRIGHT", -38, 62)
    frame.child = CreateFrame("Frame", nil, scroll); frame.child:SetSize(600, 120); scroll:SetScrollChild(frame.child)
    frame.body = ns.UILabel(frame.child, nil, 12); frame.body:SetPoint("TOPLEFT"); frame.body:SetJustifyV("TOP"); frame.body:SetWordWrap(true)
    frame.start = ns.UIButton(frame, "Start crafting guide", 172, function() ns.StartProfessionGuide(frame.professionID, ns.ProfessionGoal(frame.professionID)) end)
    frame.start:SetPoint("BOTTOMLEFT", 22, 16); ns.UIButtonTone(frame.start, true)
    frame.materials = ns.UIButton(frame, "Materials", 110, function()
        local route = frame.route
        ns.ShowShoppingList(route and route.materials or {}, frame.title:GetText() .. " • next batch")
    end)
    frame.materials:SetPoint("LEFT", frame.start, "RIGHT", 10, 0)
    frame.refresh = ns.UIButton(frame, "Refresh", 92, function() ns.RefreshProfessionPlan(frame.professionID) end)
    frame.refresh:SetPoint("BOTTOMRIGHT", -30, 16)
    local resize = ns.UIButton(frame, "↘", 20, function() end); resize:SetPoint("BOTTOMRIGHT", -4, 4)
    resize:SetScript("OnMouseDown", function() frame:StartSizing("BOTTOMRIGHT") end)
    resize:SetScript("OnMouseUp", function() frame:StopMovingOrSizing(); layout(frame) end)
    frame:SetScript("OnSizeChanged", layout); frame:SetScript("OnHide", cancelPreview)
    ns.UIHelp(frame.goal, "Plan towards this profession skill. Character level and available training control rank upgrades.")
    ns.UIHelp(frame.materials, "Materials for your next crafting batch, after subtracting bag stock. Intermediate items can have their own preparation steps.")
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
    frame.nextText:SetText(stop.label .. "\n|cffadb4be" .. stop.description .. "|r"
        .. (route.crafts and ("\nNext batch: " .. route.crafts .. " crafts • missing materials: " .. (route.estimatedCost and ns.MoneyText(route.estimatedCost) or "prices not checked")) or ""))
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
