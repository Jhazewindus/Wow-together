local addonName, ns = ...

-- These are progress suggestions, not geographic routes or a prerequisite solver.
function ns.Suggestions()
    local suggestions = {}
    for _, row in ipairs(ns.Rows()) do
        if row.people >= 2 then
            local offered, finished, unknown = {}, {}, {}
            for _, member in ipairs(row.members) do
                if not member.active then
                    if member.offered then offered[#offered + 1] = member.name
                    elseif member.history == "completed" then finished[#finished + 1] = member.name
                    else unknown[#unknown + 1] = member.name end
                end
            end
            local category, reason, action, priority
            if row.active == row.people then
                category, priority = "Continue together", 100
                reason = "All " .. row.people .. " synced players have this quest active."
                action = "Compare your objectives and continue together. Travel and objective progress are not scored yet."
            elseif row.active + #offered == row.people then
                category, priority = "Pick up, then join", 90
                reason = table.concat(offered, ", ") .. " reported this quest offered by a quest giver."
                action = "Pick it up manually, then sync to confirm it is active for everyone."
            elseif row.active >= 2 then
                category, priority = "Partly shared", 60
                reason = row.active .. "/" .. row.people .. " synced players have it active; the others have different progress."
                action = "Check the other players before treating this as a whole-party quest."
            elseif #unknown > 0 then
                category, priority = "Check pickup", 40
                reason = table.concat(unknown, ", ") .. " need a pickup check. Unfinished history does not establish eligibility."
                action = "Visit the quest giver or try normal WoW quest sharing; sync after accepting."
            else
                category, priority = "Different progress", 20
                reason = table.concat(finished, ", ") .. " reported it completed. No new pickup offer is known."
                action = "Prefer a shared quest, or agree to help the player who still has this active."
            end
            suggestions[#suggestions + 1] = {row = row, category = category, priority = priority,
                reason = reason, action = action}
        end
    end
    table.sort(suggestions, function(a, b)
        if a.priority ~= b.priority then return a.priority > b.priority end
        return a.row.id < b.row.id
    end)
    return suggestions
end
