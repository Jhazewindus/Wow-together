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

-- Saved data.
--
-- The game fills in an addon's saved variables AFTER its files have run, just
-- before ADDON_LOADED. So at this point WowTogetherGoldDB is not the saved
-- table yet. The package used to take whatever was there now (nothing, so a
-- new empty table) and work in that for the whole session, while the real
-- saved table arrived a moment later, was never looked at, and was written
-- back unchanged at logout. Nothing recorded ever survived a reload: not
-- sessions, not settings, not learned rates.
--
-- The files still need a table to work with as they load, so one is made
-- here and every file keeps its references to it. When the saved data
-- arrives it is merged INTO this table, piece by piece so that no reference
-- goes stale, and this table becomes the one the game saves.
local db = {}
db.schema = 1
if type(db.settings) ~= "table" then db.settings = {} end
namespace.db = db

local function adopt(target, saved)
    for key, value in pairs(saved) do
        if type(value) == "table" and type(target[key]) == "table" then adopt(target[key], value)
        else target[key] = value end
    end
end

local restored = false
function namespace.RestoreSavedData()
    if restored then return false end
    restored = true
    local saved = ns.ReadGoldSavedData()
    if type(saved) == "table" and saved ~= db then adopt(db, saved) end
    db.schema = 1
    ns.WriteGoldSavedData(db)
    -- Each part of the package may have read the empty table already: let it look again.
    for _, name in ipairs({"GoldObservations", "GoldFarms", "GoldTracker"}) do
        local part = namespace[name]
        if type(part) == "table" and type(part.Restored) == "function" then pcall(part.Restored) end
    end
    return true
end
ns.On("ADDON_LOADED", function(name) if name == addonName then namespace.RestoreSavedData() end end)
-- A second chance, in case the event was missed: by now the saved data is certainly there.
if type(ns.After) == "function" then ns.After("timer:Gold", 1, function() namespace.RestoreSavedData() end) end
-- And whatever happens, the table the package worked in is the one that gets saved.
ns.On("PLAYER_LOGOUT", function() if restored then ns.WriteGoldSavedData(db) end end)

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
            {key = "gold.otherPrices", label = "Use TradeSkillMaster or Auctionator prices",
                help = "Value items with the auction prices those addons already keep, when one is installed. Your own scan is still used when it is under an hour old.", default = true},
            {key = "gold.marketValue", label = "Use TradeSkillMaster's market value instead of its lowest buyout",
                help = "Lowest buyout is what an item can be sold for right now. Market value is smoothed over recent scans, so one cheap listing does not move it.", default = false},
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
