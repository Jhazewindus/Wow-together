local addonName, ns = ...

local pending
function ns.CancelProfessionShopping() pending = nil end

function ns.RefreshProfessionShopping()
    local context, frame = ns.shoppingContext, ns.shoppingWindow
    if not context or not frame or not frame:IsShown() then return end
    local id, target = context.professionID, context.target
    local signature = table.concat({id, target, context.scope, ns.professionRevision or 0}, ":")
    if context.signature == signature then ns.RenderShoppingList(); return end
    pending = nil
    context.signature = signature
    if context.scope == "batch" then
        local guide = ns.routeSelection
        local active = guide and guide.mode == "profession" and guide.professionID == id and guide.targetSkill == target
        local route = active and ns.selectedRoute or ns.BuildProfessionGuideRoute({professionID = id,
            key = "profession:" .. id, targetSkill = target, title = ns.ProfessionFacts(id).name})
        ns.shoppingList = route.materials or {}
        context.notice = "Next batch • materials still needed after bag stock."
        context.loading = nil; ns.RenderShoppingList(); return
    end
    context.loading = true
    context.notice = "Estimating materials to skill " .. target .. "…"
    ns.shoppingList = {}; ns.RenderShoppingList()
    local job = {context = context}; pending = job
    local worker = coroutine.create(function()
        local plan = ns.PlanProfessionPreview(id, target, true)
        return ns.ProfessionMaterialForecast(id, plan, true)
    end)
    local function run()
        if pending ~= job or ns.shoppingContext ~= context or not frame:IsShown() then return end
        if ns.RouteInCombat() then
            pending = nil; context.signature = nil; context.notice = "Material estimate paused."; ns.RenderShoppingList(); return
        end
        local okay, result = coroutine.resume(worker)
        if not okay then
            pending = nil; context.loading = nil; context.signature = nil
            context.notice = "Refresh to retry the material estimate."
            ns.professionStatus = "Material forecast failed: " .. tostring(result); ns.RenderShoppingList(); return
        end
        if coroutine.status(worker) == "dead" then
            pending = nil; context.loading = nil
            ns.shoppingList = result.materials
            context.notice = "Skill " .. result.start .. " → " .. target .. " • approximate quantities; skill-ups vary."
                .. (result.incomplete and "\nPartial estimate: some recipe or bag data is missing." or "\nIncludes intermediates you will craft. Buy for the next batch first.")
            ns.RenderShoppingList()
        elseif C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, run)
        else pending = nil; context.loading = nil; context.signature = nil
            context.notice = "Material estimate unavailable."; ns.RenderShoppingList() end
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, run) else run() end
end

function ns.ShowProfessionShopping(id, target, scope)
    if not ns.ProfessionFacts(id) then return end
    ns.ShowShoppingList({}, ns.ProfessionFacts(id).name .. " materials")
    ns.shoppingContext = {professionID = id, target = target or ns.ProfessionGoal(id), scope = scope == "goal" and "goal" or "batch"}
    ns.RefreshProfessionShopping()
end
