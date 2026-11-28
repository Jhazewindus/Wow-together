local addonName, ns = ...

-- What it takes to get into an instance: attunements and keys.
--
-- The Instances view lists dungeons and raids. Each can need something
-- before the door opens: a quest chain that attunes the character, or a key
-- that one member of the group carries. This file says which, works out how
-- far the character has got, and tells a dungeon which steps of another
-- instance's chain happen inside it, so they can be done in the same run.
--
--   * Chains are quest IDs in the order the game links them (read from the
--     quest catalogue's own "next in chain" data, per faction).
--   * A key or amulet the character already carries counts as done whatever
--     the quest log says.
--   * A key that drops from a creature has no chain: it is only "carried"
--     or "not yet".
--   * Where it is not known whether Forever still needs something, the entry
--     says so instead of guessing.
--
-- Sources for what Forever requires (read 25 November 2026): Blizzard's raid
-- overview of 20 October 2026 as reported by wowforever.ninja,
-- conquestcapped.com and wow4ever.quest. Only facts were taken.

-- Raids. The addon's dungeon data has none; these are enough to list them.
ns.instanceRaids = {
    {key = "onyxias-lair", name = "Onyxia's Lair", level = 60, where = "Dustwallow Marsh",
        note = "40 players. Opens 9 December 2026."},
    {key = "the-barrow-deeps", name = "The Barrow Deeps", level = 60, note = "New in Forever. Opens 9 December 2026."},
    {key = "hyjal-summit", name = "Hyjal Summit", level = 60, note = "New in Forever. Opens 9 December 2026."},
}

-- instance key -> what it needs. `everyone`: every member needs it (an
-- attunement) as opposed to one carrier for the group (a key).
ns.instanceAccess = {
    ["onyxias-lair"] = {{
        title = "Drakefire Amulet", kind = "Attunement", everyone = true, itemID = 16309,
        chains = {
            Horde = {4903, 4941, 4974, 6566, 6567, 6568, 6569, 6570, 6582, 6583, 6584, 6585, 6601, 6602},
            Alliance = {4182, 4183, 4184, 4185, 4186, 4223, 4224, 4241, 4242, 4264, 4282, 4322, 6402, 6403, 6501, 6502},
        },
        note = "Every raider needs their own. It only has to be in your bags.",
    }},
    ["the-barrow-deeps"] = {{title = "No attunement", kind = "Open", open = true,
        note = "Blizzard's raid overview lists no attunement for this raid."}},
    ["hyjal-summit"] = {{title = "No attunement", kind = "Open", open = true,
        note = "Blizzard's raid overview lists no attunement for this raid."}},
    ["blackrock-spire"] = {{
        title = "Seal of Ascension", kind = "Key", itemID = 12344, scope = "the upper spire",
        chains = {Horde = {4742, 4743}, Alliance = {4742, 4743}},
        uncertain = "Guides disagree on whether Forever's upper spire door still needs it. One carrier opens it for the group if it does.",
    }},
    ["scholomance"] = {{
        title = "Skeleton Key", kind = "Key", itemID = 13704,
        chains = {Horde = {838, 964, 5514, 5802, 5804, 5511}, Alliance = {5533, 5537, 5538, 5801, 5803, 5505}},
        note = "One carrier opens the door for the group.",
    }},
    ["blackrock-depths"] = {{
        title = "Shadowforge Key", kind = "Key", itemID = 11000, scope = "the back half",
        chains = {Horde = {3801, 3802}, Alliance = {3801, 3802}},
        note = "Opens the doors past the Shadowforge Lock. One carrier is enough.",
    }},
    ["stratholme"] = {{
        title = "Key to the City", kind = "Key", itemID = 12382, scope = "the service entrance",
        drop = "Drops from Magistrate Barthilas inside Stratholme.",
    }},
    ["dire-maul"] = {{
        title = "Crescent Key", kind = "Key", itemID = 18249, scope = "the north and west wings",
        drop = "Chase Pusillin through Dire Maul East; he drops it.",
    }},
}

local function faction()
    local value = ns.profile and ns.profile.faction
    return (value == "Horde" or value == "Alliance") and value or nil
end

local function carries(itemID)
    if not itemID then return false end
    local reader = C_Item and C_Item.GetItemCount or GetItemCount
    if type(reader) ~= "function" then return false end
    local count = ns.ReadPublic(reader, itemID, true)       -- true: the bank counts too.
    return type(count) == "number" and count > 0
end

local function questDone(id)
    return ns.CatalogueCompletion and ns.CatalogueCompletion(ns.self, id) == true
        and not (ns.active and ns.active[id] ~= nil)
end

-- Which dungeon a quest of a chain is done in, by the catalogue's own category ("dungeons/blackrock-spire").
local function questInstance(id)
    local quest = ns.CatalogueQuest(id)
    return quest and type(quest.categoryPath) == "string" and string.match(quest.categoryPath, "^dungeons/(.+)$") or nil
end

-- How far the character has got with one requirement.
--   state: "open" (nothing needed), "have", "progress", "none", "drop" (a drop, not carried), "unknown" (no faction yet)
function ns.InstanceAccessStatus(entry)
    local status = {entry = entry, title = entry.title, kind = entry.kind}
    if entry.open then status.state = "open"; status.text = entry.title; return status end
    if carries(entry.itemID) then
        status.state = "have"
        status.text = entry.kind .. ": " .. entry.title .. " • you have it"
        return status
    end
    if not entry.chains then
        status.state = "drop"
        status.text = entry.kind .. ": " .. entry.title .. " • not yet. " .. (entry.drop or "")
        return status
    end
    local side = faction()
    local chain = side and entry.chains[side]
    if not chain then status.state = "unknown"; status.text = entry.kind .. ": " .. entry.title; return status end
    local done, nextID = 0, nil
    for _, id in ipairs(chain) do
        if questDone(id) then done = done + 1 elseif not nextID then nextID = id end
    end
    status.total, status.done, status.nextID, status.chain = #chain, done, nextID, chain
    if done >= #chain then
        status.state = "have"
        status.text = entry.kind .. ": " .. entry.title .. " • done"
    else
        status.state = done > 0 and "progress" or "none"
        -- The catalogue's title first: the log's own can be missing while the quest data loads.
        local known = nextID and ns.CatalogueQuest(nextID)
        status.nextTitle = nextID and (known and known.title or ns.QuestTitle(nextID) or ("quest " .. nextID)) or nil
        status.inLog = nextID ~= nil and ns.active ~= nil and ns.active[nextID] ~= nil
        status.text = entry.kind .. ": " .. entry.title .. " • "
            .. (done > 0 and ("step " .. (done + 1) .. " of " .. #chain) or ("not started, " .. #chain .. " steps"))
            .. (status.nextTitle and (" • next: " .. status.nextTitle) or "")
    end
    return status
end

-- Everything an instance needs, with the character's progress.
function ns.InstanceAccess(key)
    local list = {}
    for _, entry in ipairs(ns.instanceAccess[key] or {}) do list[#list + 1] = ns.InstanceAccessStatus(entry) end
    return list
end

-- Build one route through the known unfinished access chains for this
-- instance. The quest catalogue contributes the prerequisites and locations.
function ns.BuildInstanceAccessGuide(key)
    if type(key) ~= "string" then return end
    local ids, titles, seen = {}, {}, {}
    for _, status in ipairs(ns.InstanceAccess(key)) do
        if status.state ~= "have" and type(status.chain) == "table" then
            titles[#titles + 1] = status.title
            for _, id in ipairs(status.chain) do
                if not seen[id] then ids[#ids + 1], seen[id] = id, true end
            end
        end
    end
    if #ids == 0 or type(ns.BuildInstanceAccessQuestGuide) ~= "function" then return end
    local title = "Get " .. table.concat(titles, " and ")
    return ns.BuildInstanceAccessQuestGuide(key, title, ids)
end

-- Steps of other instances' chains that are done inside this dungeon and
-- are still ahead of the character: "do these in the same run".
function ns.InstanceAlsoHere(key)
    local list, side = {}, faction()
    if not side then return list end
    for owner, entries in pairs(ns.instanceAccess) do
        for _, entry in ipairs(entries) do
            local chain = entry.chains and entry.chains[side]
            if chain and not carries(entry.itemID) then
                local here = {}
                for _, id in ipairs(chain) do
                    if questInstance(id) == key and not questDone(id) then here[#here + 1] = id end
                end
                if #here > 0 and not (owner == key and #here == #chain) then
                    list[#list + 1] = {title = entry.title, owner = owner, steps = here,
                        text = #here .. (#here == 1 and " step" or " steps") .. " of the " .. entry.title .. " here"}
                end
            end
        end
    end
    table.sort(list, function(a, b) return a.title < b.title end)
    return list
end

-- The lines a dungeon or raid card shows about getting in.
function ns.InstanceAccessLines(key)
    local lines = {}
    for _, status in ipairs(ns.InstanceAccess(key)) do lines[#lines + 1] = status.text end
    for _, also in ipairs(ns.InstanceAlsoHere(key)) do
        if also.owner ~= key then lines[#lines + 1] = "Also: " .. also.text end
    end
    return lines
end

-- The longer explanation, for a tooltip.
function ns.InstanceAccessTooltip(tooltip, key)
    for _, status in ipairs(ns.InstanceAccess(key)) do
        local entry = status.entry
        tooltip:AddLine(" ")
        tooltip:AddLine(entry.title, 1, 0.82, 0.3)
        if status.state == "open" then
            tooltip:AddLine(entry.note or "Nothing is needed to enter.", 1, 1, 1, true)
        else
            tooltip:AddLine((entry.everyone and "Everyone in the group needs it" or "One member of the group needs it")
                .. (entry.scope and (", for " .. entry.scope) or "") .. ".", 1, 1, 1, true)
            if status.state == "have" then
                tooltip:AddLine("You have it.", 0.4, 1, 0.4)
            elseif status.total then
                tooltip:AddLine(status.done .. " of " .. status.total .. " steps done."
                    .. (status.nextTitle and (" Next: " .. status.nextTitle .. (status.inLog and " (in your log)" or "") .. ".") or ""), 1, 1, 1, true)
            elseif entry.drop then
                tooltip:AddLine(entry.drop, 1, 1, 1, true)
            end
            if entry.note then tooltip:AddLine(entry.note, 0.68, 0.71, 0.75, true) end
            if entry.uncertain then tooltip:AddLine(entry.uncertain, 1, 0.6, 0.3, true) end
        end
    end
    for _, also in ipairs(ns.InstanceAlsoHere(key)) do
        if also.owner ~= key then
            tooltip:AddLine(" ")
            tooltip:AddLine("Also done in here", 1, 0.82, 0.3)
            local names = {}
            for index, id in ipairs(also.steps) do if index <= 4 then names[#names + 1] = ns.QuestTitle(id) or ("quest " .. id) end end
            tooltip:AddLine(also.text .. ": " .. table.concat(names, ", ") .. (#also.steps > 4 and "…" or "") .. ".", 1, 1, 1, true)
        end
    end
end

-- The same explanation as plain lines, for a card's own tooltip.
function ns.InstanceAccessHelp(key)
    local lines = {}
    for _, status in ipairs(ns.InstanceAccess(key)) do
        local entry = status.entry
        lines[#lines + 1] = ""
        lines[#lines + 1] = entry.title
        if status.state == "open" then
            lines[#lines + 1] = entry.note or "Nothing is needed to enter."
        else
            lines[#lines + 1] = (entry.everyone and "Everyone in the group needs it" or "One member of the group needs it")
                .. (entry.scope and (", for " .. entry.scope) or "") .. "."
            if status.state == "have" then lines[#lines + 1] = "You have it."
            elseif status.total then
                lines[#lines + 1] = status.done .. " of " .. status.total .. " steps done."
                    .. (status.nextTitle and (" Next: " .. status.nextTitle .. (status.inLog and " (in your log)" or "") .. ".") or "")
            elseif entry.drop then lines[#lines + 1] = entry.drop end
            if entry.note then lines[#lines + 1] = entry.note end
            if entry.uncertain then lines[#lines + 1] = entry.uncertain end
        end
    end
    for _, also in ipairs(ns.InstanceAlsoHere(key)) do
        if also.owner ~= key then
            local names = {}
            for index, id in ipairs(also.steps) do if index <= 4 then names[#names + 1] = ns.QuestTitle(id) or ("quest " .. id) end end
            lines[#lines + 1] = ""
            lines[#lines + 1] = "Also done in here: " .. also.text .. " (" .. table.concat(names, ", ") .. (#also.steps > 4 and "…" or "") .. ")."
        end
    end
    return table.concat(lines, "\n")
end

-- Dungeons or raids: which half of the Instances view is showing.
function ns.InstanceKind() return ns.db and ns.db.instanceKind == "raids" and "raids" or "dungeons" end
function ns.SetInstanceKind(kind)
    if not ns.db then return end
    ns.db.instanceKind = kind == "raids" and "raids" or "dungeons"
    if ns.Refresh then ns.Refresh() end
end

-- What a click on a requirement does: show the next step's quest, the same
-- view the quest lists open.
function ns.OpenInstanceAccess(key)
    for _, status in ipairs(ns.InstanceAccess(key)) do
        if status.nextID and type(ns.ShowQuestDetails) == "function" then ns.ShowQuestDetails(status.nextID); return true end
    end
    return false
end

function ns.InstanceAccessDiagnostics(output)
    local parts = {}
    for _, key in ipairs({"onyxias-lair", "blackrock-spire", "scholomance", "blackrock-depths", "stratholme", "dire-maul"}) do
        for _, status in ipairs(ns.InstanceAccess(key)) do
            parts[#parts + 1] = status.title .. " " .. (status.state == "have" and "have" or status.total and (status.done .. "/" .. status.total) or status.state)
        end
    end
    output("Instance access: " .. table.concat(parts, "; ") .. ".")
end
