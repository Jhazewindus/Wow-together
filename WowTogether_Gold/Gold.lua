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
    elseif action == nil or action == "" or action == "track" or action == "tracker" then
        local tracker = namespace.GoldTracker
        if tracker then tracker.Command(action == "track" or action == "tracker" and rest or rest or "")
        else ns.Print("The farm tracker is unavailable.") end
    elseif action == "reset" or action == "pause" or action == "start" or action == "resume" or action == "scan" then
        local tracker = namespace.GoldTracker
        if tracker then tracker.Command(action) else ns.Print("The farm tracker is unavailable.") end
    elseif action == "stop" then
        local farms = namespace.GoldFarms
        if farms and farms.Stop then farms.Stop("stopped by player")
        else ns.Print("Gold session unavailable.") end
    else
        ns.Print("Gold is in the main window: press Gold on the left. The farm tracker and the price scan open from there.")
    end
end

local function probe(output)
    output("Gold module: ready; saved schema " .. db.schema)
    output("Loot recording: " .. (ns.Option("gold.recordLoot") and "on" or "off"))
    local prices = namespace.GoldPrices
    if prices and prices.Probe then prices.Probe(output) end
    local observations = namespace.GoldObservations
    if observations and observations.Probe then observations.Probe(output) end
    local farms = namespace.GoldFarms
    if farms and farms.Probe then farms.Probe(output) end
    local tracker = namespace.GoldTracker
    if tracker and tracker.Probe then tracker.Probe(output) end
end

ns.RegisterModule("Gold", {
    tab = {title = "Gold", render = function(page)
        local farms = namespace.GoldFarms
        if farms and farms.Render then farms.Render(page) else page:SetHeight(250) end
    end},
    settingsGroup = {title = "Gold", description = "Choose what Gold may record and share.",
        entries = {
            {key = "gold.recordLoot", label = "Record loot and gathering",
                help = "Save observations from your own play for future farming suggestions.", default = true},
            {key = "gold.trackerAutoStart", label = "Start the farm tracker with the first loot",
                help = "The farm session clock starts by itself when you loot something. Off: press Start in the tracker.", default = true},
            {key = "gold.trackerWithFarm", label = "Show the farm tracker when I start a farm",
                help = "Starting a suggested farm puts the farm session window on screen.", default = true},
            {key = "gold.scanAtAuction", label = "Offer a price scan at the auction house",
                help = "Open the price scan when you visit an auction house with farmed items to price. Nothing is bought or sold.", default = true},
            {key = "gold.shareObservations", label = "Share Gold observations with party",
                help = "Share measured farming facts with party members running Wow Together Gold.", default = true},
        },
        get = settingsValue, set = setSettingsValue},
    slash = command,
    probe = probe,
})
namespace.enabled = true
