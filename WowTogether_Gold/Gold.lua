local addonName, namespace = ...
local ns = _G.WowTogetherModuleAPI

namespace.enabled = false
if type(ns) ~= "table" or type(ns.version) ~= "number" or ns.version < 1
    or type(ns.RegisterModule) ~= "function" then
    if DEFAULT_CHAT_FRAME and type(DEFAULT_CHAT_FRAME.AddMessage) == "function" then
        DEFAULT_CHAT_FRAME:AddMessage("Wow Together Gold: Gold API v1 is required; module disabled.")
    end
    return
end

if type(WowTogetherGoldDB) ~= "table" then WowTogetherGoldDB = {} end
local db = WowTogetherGoldDB
db.schema = 1
if type(db.settings) ~= "table" then db.settings = {} end
namespace.db = db

local function settingsValue(key) return db.settings[key] end
local function setSettingsValue(key, value) db.settings[key] = value end

local function command(text)
    local action, rest = string.match(text or "", "^(%S+)%s*(.-)%s*$")
    if action == "prices" then
        local prices = namespace.GoldPrices
        if prices and prices.Command then return prices.Command(rest) end
        ns.Print("Gold prices are unavailable.")
    else
        ns.Print("Gold tab is available in the Wow Together window. /wt gold prices shows price sources.")
    end
end

local function probe(output)
    output("Gold module: ready; saved schema " .. db.schema)
    output("Loot recording: " .. (ns.Option("gold.recordLoot") and "on" or "off"))
    local prices = namespace.GoldPrices
    if prices and prices.Probe then prices.Probe(output) end
    local observations = namespace.GoldObservations
    if observations and observations.Probe then observations.Probe(output) end
end

ns.RegisterModule("Gold", {
    tab = {title = "Gold", render = function(page)
        -- The tab is intentionally empty until suggestions have measured data.
        page:SetHeight(250)
    end},
    settingsGroup = {title = "Gold", description = "Choose what Gold may record and share.",
        entries = {
            {key = "gold.recordLoot", label = "Record loot and gathering",
                help = "Save observations from your own play for future farming suggestions.", default = true},
            {key = "gold.shareObservations", label = "Share Gold observations with party",
                help = "Share measured farming facts with party members running Wow Together Gold.", default = true},
        },
        get = settingsValue, set = setSettingsValue},
    slash = command,
    probe = probe,
})
namespace.enabled = true
