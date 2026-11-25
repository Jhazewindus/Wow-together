"""Loads the optional gold package into the test client, the way the game does after login."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ITEMS = r"""
    -- name, quality, icon, vendor price
    goldItems = {
        [2771] = {"Tin Ore", 1, "Interface\\Icons\\INV_Ore_Tin_01", 25},
        [2775] = {"Silver Ore", 2, "Interface\\Icons\\INV_Stone_16", 75},
        [2836] = {"Coarse Stone", 1, "Interface\\Icons\\INV_Stone_09", 15},
        [1206] = {"Moss Agate", 2, "Interface\\Icons\\INV_Misc_Gem_Emerald_03", 400},
        [1705] = {"Lesser Moonstone", 2, "Interface\\Icons\\INV_Misc_Gem_Crystal_01", 600},
        [3356] = {"Kingsblood", 1, "Interface\\Icons\\INV_Misc_Herb_03", 30},
        [2319] = {"Medium Leather", 1, "Interface\\Icons\\INV_Misc_LeatherScrap_05", 50},
        [4306] = {"Silk Cloth", 1, "Interface\\Icons\\INV_Fabric_Silk_01", 150},
        [3924] = {"Raptor Hide Scrap", 0, "Interface\\Icons\\INV_Misc_Pelt_Bear_Ruin_03", 181},
        [6359] = {"Firefin Snapper", 1, "Interface\\Icons\\INV_Misc_Fish_23", 5},
        [5498] = {"Small Lustrous Pearl", 2, "Interface\\Icons\\INV_Misc_Gem_Pearl_03", 125},
    }
    function GetItemInfo(id)
        local item = goldItems[id]
        if not item then return nil end
        return item[1], "|Hitem:" .. id .. ":|h[" .. item[1] .. "]|h", item[2], 30, 25, "Trade Goods", "Other", 20, "", item[3], item[4]
    end
    C_Item = C_Item or {}
    C_Item.GetItemInfo = GetItemInfo
    LOOT_ITEM_SELF = "You receive loot: %s."
    LOOT_ITEM_SELF_MULTIPLE = "You receive loot: %sx%d."
    LOOT_ITEM = "%s receives loot: %s."
    LOOT_ITEM_PUSHED_SELF = "You receive item: %s."
    GOLD_AMOUNT, SILVER_AMOUNT, COPPER_AMOUNT = "%d Gold", "%d Silver", "%d Copper"
    clock = 1000
    function GetTime() return clock end
    function GetServerTime() return 1795000000 + clock end
    function GetRealZoneText() return zoneText or "Hillsbrad Foothills" end
    function IsLoggedIn() return true end
"""


def load_gold(client, saved=None):
    """Loads the gold package the way the game does and returns its private table.

    The order matters and is the game's: the package's files run first, with
    its saved variable not yet set; then the saved data appears in the global;
    then ADDON_LOADED fires. An earlier version of this helper set the saved
    data before running the files, which hid a bug that lost everything the
    package recorded on every reload.
    """
    lua = client.lua
    lua.execute(ITEMS)
    lua.globals().WowTogetherGoldDB = None
    namespace = lua.table()
    folder = os.path.join(ROOT, 'WowTogether_Gold')
    load = lua.eval('function(source, name, addon, namespace) local chunk, problem = loadstring(source, name); '
                    'if not chunk then error(problem) end; return chunk(addon, namespace) end')
    for line in open(os.path.join(folder, 'WowTogether_Gold.toc'), encoding='utf-8'):
        line = line.strip()
        if line.endswith('.lua'):
            load(open(os.path.join(folder, line), encoding='utf-8').read(), line, 'WowTogether_Gold', namespace)
    if saved is not None:
        lua.globals().WowTogetherGoldDB = lua.table_from(saved, recursive=True)
    client.ns.frame.OnEvent(client.ns.frame, 'ADDON_LOADED', 'WowTogether_Gold')
    lua.globals().goldSpace = namespace
    return namespace


def saved_data(client):
    """What the game would write to disk at logout: a plain copy of the saved variable."""
    client.ns.frame.OnEvent(client.ns.frame, 'PLAYER_LOGOUT')

    def plain(value):
        if hasattr(value, 'items') and not isinstance(value, (str, bytes)):
            return {key: plain(item) for key, item in value.items()}
        return value
    return plain(client.lua.globals().WowTogetherGoldDB)


def item_link(client, item):
    name = client.lua.eval('function(id) return goldItems[id] and goldItems[id][1] or ("Item " .. id) end')(item)
    return '|cffffffff|Hitem:%d::::::::33:::::|h[%s]|h|r' % (item, name)


def loot(client, item, count=1):
    """The chat line the game prints when the player loots an item."""
    link = item_link(client, item)
    message = ('You receive loot: %sx%d.' % (link, count)) if count > 1 else ('You receive loot: %s.' % link)
    client.ns.frame.OnEvent(client.ns.frame, 'CHAT_MSG_LOOT', message)


def quote(client, item, copper, age=600):
    """A saved auction price for an item, as a scan would leave it."""
    client.lua.execute('local ns, id, copper, age = ...; ns.marketQuotes = ns.marketQuotes or {}; '
                       'ns.marketQuotes[id] = {unitPrice = copper, time = GetServerTime() - age}', client.ns, item, copper, age)
