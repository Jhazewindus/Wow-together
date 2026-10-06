"""Native dungeon backgrounds: missing assets, pooled cards and guide preservation."""
import unittest

from test_addon import Client, ROOT
from test_0811 import browser
from test_063 import order, zone
from test_061 import run_plan


NEUTRAL = r'Interface\LFGFrame\UI-LFG-BACKGROUND-DUNGEONWALL'
CLASSIC = r'Interface\EncounterJournal\UI-EJ-DungeonButton-'


def card(c, key, width=700, height=160):
    result = c.lua.eval("CreateFrame('Frame')")
    result.SetSize(result, width, height)
    group = c.lua.table_from({'key': key})
    result.activity = c.lua.table_from({'dungeon': group})
    result.Show(result)
    c.ns.ApplyGuideCardTheme(result, None, group)
    return result


class DungeonArtworkTests(unittest.TestCase):
    def test_classic_and_verified_forever_dungeons_have_distinct_client_assets(self):
        c = Client(quests=(), use_catalogue=True)
        assets = set()
        for key in c.ns.dungeonData.dungeons.keys():
            image = card(c, key).dungeonArt
            self.assertTrue(image.shown)
            if image.asset != NEUTRAL:
                assets.add(image.asset)
                self.assertTrue(image.asset.startswith('Interface\\'))
                self.assertNotIn('AddOns', image.asset)
        self.assertEqual(len(assets), 23)
        self.assertEqual(card(c, 'the-stockade').dungeonArt.asset, CLASSIC + 'TheStockade')
        self.assertEqual(card(c, 'the-temple-of-atalhakkar').dungeonArt.asset, CLASSIC + 'SunkenTemple')
        self.assertTrue(card(c, 'city-of-dalaran').dungeonArt.asset.endswith('Camelot_Dalaran'))

    def test_whole_card_is_faint_and_resizing_reuses_one_texture_without_replanning(self):
        c = browser(); g = zone(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(c.ns.routeSelection)
        target = c.ns.ui.cards[1]
        c.ns.ApplyGuideCardTheme(target, None, c.lua.table_from({'key': 'ragefire-chasm'}))
        art = target.dungeonArt
        original_texture = art.texture
        self.assertFalse(target.zoneArt.IsShown(target.zoneArt))
        target.SetSize(target, 950, 170); c.ns.LayoutGuideCardTheme(target)
        self.assertEqual((art.texture.width, art.texture.height), (948, 168))
        self.assertEqual(art.texture.alpha, .14)
        self.assertEqual(tuple(art.texture.texCoord.values()), (6/256, 168/256, 6/128, 90/128))
        self.assertEqual(art.texture.drawSublevel, -7)
        target.SetSize(target, 580, 240); c.ns.LayoutGuideCardTheme(target)
        self.assertEqual((art.texture.width, art.texture.height), (578, 238))
        self.assertTrue(c.lua.eval('rawequal')(art.texture, original_texture))
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertFalse(c.ns.Completed(900)); self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_reused_cards_clear_previous_dungeon_and_restore_zone_or_plain_rows(self):
        c = browser(); target = c.ns.ui.cards[1]
        for key, suffix in (('ragefire-chasm', 'RagefireChasm'), ('wailing-caverns', 'WailingCaverns')):
            c.ns.ApplyGuideCardTheme(target, None, c.lua.table_from({'key': key}))
            self.assertEqual(target.dungeonArt.asset, CLASSIC + suffix)
            self.assertTrue(target.dungeonArt.texture.IsShown(target.dungeonArt.texture))
        c.ns.ApplyGuideCardTheme(target, None, None)
        self.assertFalse(target.dungeonArt.shown)
        self.assertFalse(target.dungeonArt.texture.IsShown(target.dungeonArt.texture))
        self.assertFalse(target.zoneArt.IsShown(target.zoneArt))
        c.ns.ApplyGuideCardTheme(target, c.lua.table_from({'homeMapID': 1411}), None)
        self.assertFalse(target.dungeonArt.shown)
        self.assertTrue(target.zoneArt.IsShown(target.zoneArt))

    def test_missing_art_uses_lfg_or_neutral_then_plain_background(self):
        c = Client(); c.lua.globals().target = card(c, 'ragefire-chasm')
        c.lua.execute('''function target.dungeonArt.texture:SetTexture(asset)
            self.texture=asset
            return not asset:find('EncounterJournal',1,true)
        end''')
        c.ns.RefreshDungeonArtwork()
        c.ns.ApplyDungeonCardArtwork(c.lua.globals().target, c.lua.table_from({'key': 'ragefire-chasm'}))
        self.assertEqual(c.lua.globals().target.dungeonArt.asset, r'Interface\LFGFrame\LFGICON-RAGEFIRECHASM')
        c.lua.execute('''function target.dungeonArt.texture:SetTexture(asset)
            self.texture=asset; return asset:find('DUNGEONWALL',1,true) ~= nil
        end''')
        c.ns.RefreshDungeonArtwork()
        c.ns.ApplyDungeonCardArtwork(c.lua.globals().target, c.lua.table_from({'key': 'ragefire-chasm'}))
        self.assertEqual(c.lua.globals().target.dungeonArt.asset, NEUTRAL)
        c.lua.execute('function target.dungeonArt.texture:SetTexture() return false end')
        c.ns.RefreshDungeonArtwork()
        c.ns.ApplyDungeonCardArtwork(c.lua.globals().target, c.lua.table_from({'key': 'ragefire-chasm'}))
        self.assertFalse(c.lua.globals().target.dungeonArt.shown)
        self.assertFalse(c.lua.globals().target.dungeonArt.texture.IsShown(c.lua.globals().target.dungeonArt.texture))

    def test_unknown_dungeon_uses_official_neutral_art_without_adding_a_generated_image(self):
        c = Client()
        for key in ('alcaz-prison', 'blackmaw-hold', 'kroldok-stronghold', 'shapers-terrace', 'the-drowned-city'):
            target = card(c, key)
            self.assertEqual(target.dungeonArt.asset, NEUTRAL)
            self.assertIsNone(target.zoneArt)

    def test_async_journal_discovery_upgrades_visible_fallback_without_selecting_or_opening_journal(self):
        c = Client(quests=(), use_catalogue=True)
        c.lua.execute('''journalReads=0
            function EJ_GetInstanceByIndex(index, raid)
                assert(raid==false); journalReads=journalReads+1
                if index<17 then return index, 'Unrelated dungeon' end
                if index==17 then return index, 'Blackmaw Hold', nil, nil, 123 end
            end
            function EJ_GetInstanceInfo()return 'Blackmaw Hold','Description',456 end
            function EJ_SelectInstance()error('May not select an instance')end
            function EJ_SelectTier()error('May not change tiers')end
            function EncounterJournal_LoadUI()error('May not open journal')end''')
        target = card(c, 'blackmaw-hold'); c.ns.ui.cards = c.lua.table_from([target])
        self.assertEqual(target.dungeonArt.asset, NEUTRAL)
        c.drain()
        self.assertEqual(target.dungeonArt.asset, 456)
        self.assertEqual(c.lua.globals().journalReads, 18)
        self.assertEqual((target.dungeonArt.texture.width, target.dungeonArt.texture.height), (698, 158))
        # Changing the currently loaded journal data invalidates the asset cache only.
        c.lua.execute('function EJ_GetInstanceInfo()return "Blackmaw Hold","Description",789 end')
        c.ns.handlers.ADDON_LOADED('Blizzard_EncounterJournal'); c.drain()
        self.assertEqual(target.dungeonArt.asset, 789)
        self.assertIsNone(c.ns.routeSelection)

    def test_native_button_is_used_when_journal_background_cannot_load(self):
        c = Client(quests=(), use_catalogue=True)
        target = card(c, 'blackmaw-hold'); c.lua.globals().target = target
        c.lua.execute('''function EJ_GetInstanceByIndex(index)
                if index==1 then return 1,'Blackmaw Hold',nil,nil,123 end
            end
            function EJ_GetInstanceInfo()return 'Blackmaw Hold','Description',456 end
            function target.dungeonArt.texture:SetTexture(asset)
                self.texture=asset; return asset~=456
            end''')
        c.ns.RefreshDungeonArtwork()
        c.ns.ApplyDungeonCardArtwork(target, target.activity.dungeon)
        self.assertEqual(target.dungeonArt.asset, 123)

    def test_restricted_or_untrusted_native_assets_never_reach_texture_setter(self):
        for value in ('secret', "'https://example.invalid/image.png'", "'Interface\\\\AddOns\\\\Other\\\\image'"):
            c = Client(quests=(), use_catalogue=True)
            c.lua.execute(f'''function EJ_GetInstanceByIndex(index)
                    if index==1 then return 1,'Blackmaw Hold',nil,nil,{value} end
                end
                function EJ_GetInstanceInfo()return 'Blackmaw Hold','Description',{value} end''')
            self.assertEqual(card(c, 'blackmaw-hold').dungeonArt.asset, NEUTRAL)
        c = Client(quests=(), use_catalogue=True)
        c.lua.execute('function EJ_GetInstanceByIndex()return secret,secret end')
        self.assertEqual(card(c, 'blackmaw-hold').dungeonArt.asset, NEUTRAL)

    def test_combat_skips_journal_reads_and_repeated_layout_does_not_poll(self):
        c = Client(quests=(), use_catalogue=True)
        c.lua.execute('''combat=true; function InCombatLockdown()return combat end
            journalReads=0
            function EJ_GetInstanceByIndex()journalReads=journalReads+1 end''')
        target = card(c, 'ragefire-chasm')
        for _ in range(30): c.ns.LayoutDungeonCardArtwork(target)
        self.assertEqual(c.lua.globals().journalReads, 0)
        c.lua.globals().combat = False
        c.ns.ApplyDungeonCardArtwork(target, target.activity.dungeon)
        self.assertEqual(c.lua.globals().journalReads, 1)
        for _ in range(30): c.ns.ApplyDungeonCardArtwork(target, target.activity.dungeon)
        self.assertEqual(c.lua.globals().journalReads, 1)


if __name__ == '__main__':
    unittest.main()
