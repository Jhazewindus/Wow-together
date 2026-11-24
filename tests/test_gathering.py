"""Gathering paths: what gives skill now, where, what unlocks next."""
import unittest

from test_addon import Client

MINING, HERBALISM, SKINNING, FISHING = 186, 182, 393, 356


def client(level=22, faction='Horde', zone='Hillsbrad Foothills'):
    c = Client(quests=(), default_guide=True)
    c.lua.execute('''
        local ns, level, faction, zone = ...
        ns.profile = ns.profile or {}
        ns.profile.level, ns.profile.faction, ns.profile.zone = level, faction, zone
        printed = {}
        ns.Print = function(text) printed[#printed + 1] = text end
    ''', c.ns, level, faction, zone)
    return c


def names(table):
    return [entry.name for entry in table.values()]


class GatheringRuleTests(unittest.TestCase):
    def test_skinning_skill_follows_the_beast_level_rule_in_both_directions(self):
        ns = client().ns
        for level, skill in ((1, 1), (10, 1), (11, 10), (15, 50), (17, 70), (20, 100), (21, 105), (30, 150), (40, 200), (52, 260), (60, 300)):
            self.assertEqual(ns.SkinningSkillForLevel(level), skill, level)
        for skill, level in ((1, 10), (9, 10), (10, 11), (55, 15), (99, 19), (100, 20), (104, 20), (105, 21), (149, 29), (150, 30), (300, 60)):
            self.assertEqual(ns.SkinningLevelForSkill(skill), level, skill)
        for skill in range(1, 301):  # Whatever the skill, the level it allows really is skinnable.
            self.assertLessEqual(ns.SkinningSkillForLevel(ns.SkinningLevelForSkill(skill)), max(skill, 1))

    def test_a_node_is_certain_for_25_points_and_grey_after_100(self):
        ns = client().ns
        self.assertIsNone(ns.GatheringColor(125, 124))
        self.assertEqual(ns.GatheringColor(125, 125), 'orange')
        self.assertEqual(ns.GatheringColor(125, 149), 'orange')
        self.assertEqual(ns.GatheringColor(125, 150), 'yellow')
        self.assertEqual(ns.GatheringColor(125, 175), 'green')
        self.assertEqual(ns.GatheringColor(125, 224), 'green')
        self.assertEqual(ns.GatheringColor(125, 225), 'grey')
        # Forever's veins stay yellow longer: green from 65 above the requirement.
        self.assertEqual(ns.GatheringColor(125, 180, 65), 'yellow')
        self.assertEqual(ns.GatheringColor(125, 190, 65), 'green')
        plan = ns.GatheringPlan(MINING, 180, 225, 35, 'Horde', 'Arathi Highlands')
        iron = next(entry for entry in plan.now.values() if entry.name == 'Iron Deposit')
        self.assertEqual(iron.color, 'yellow')                       # 125 / 150 / 190 / 225 in Forever.


class GatheringPlanTests(unittest.TestCase):
    def test_mining_at_87_points_at_tin_and_silver_and_names_iron_as_next(self):
        ns = client().ns
        plan = ns.GatheringPlan(MINING, 87, 150)
        now = names(plan.now)
        self.assertEqual(now[:2], ['Silver Vein', 'Tin Vein'])      # Hardest first.
        self.assertIn('Copper Vein', now)                            # Still green until 101.
        self.assertEqual((plan.nextUnlock.name, plan.nextUnlock.skill), ('Iron Deposit', 125))
        here = {entry.name: entry for entry in plan.local_.values()}
        self.assertEqual(here['Tin Vein'].color, 'orange')
        zones = list(plan.zones.values())
        self.assertEqual(zones[0], 'Hillsbrad Foothills')            # The zone the character is in leads.
        self.assertIn('The Barrens', zones)
        text = ns.GatheringText(plan)
        self.assertIn('Tin Vein (65) • a point every time until 90', text)
        self.assertIn('IN HILLSBRAD FOOTHILLS', text)
        self.assertIn('Hillsbrad Foothills (you are here)', text)
        self.assertIn('Iron Deposit at skill 125 (38 to go)', text)
        self.assertIn('Train Expert from skill 125', text)

    def test_grey_nodes_drop_out_and_locked_ones_say_how_far(self):
        ns = client(level=35, zone='Arathi Highlands').ns
        plan = ns.GatheringPlan(MINING, 130, 225)
        self.assertNotIn('Copper Vein', names(plan.now))             # Grey from 101.
        here = {entry.name: entry for entry in plan.local_.values()}
        self.assertEqual(here['Gold Vein'].short, 25)                # Needs 155.
        self.assertIn('Gold Vein • needs 155, you are 25 short', ns.GatheringText(plan))

    def test_zones_respect_faction_and_stay_near_the_characters_level(self):
        horde = client(level=14, faction='Horde', zone='The Barrens').ns
        zones = list(horde.GatheringPlan(HERBALISM, 55, 75).zones.values())
        self.assertIn('The Barrens', zones)
        for alliance_zone in ('Westfall', 'Loch Modan', 'Darkshore', 'Redridge Mountains'):
            self.assertNotIn(alliance_zone, zones)
        alliance = client(level=14, faction='Alliance', zone='Westfall').ns
        zones = list(alliance.GatheringPlan(HERBALISM, 55, 75).zones.values())
        self.assertEqual(zones[0], 'Westfall')
        self.assertNotIn('The Barrens', zones)
        self.assertNotIn('Silverpine Forest', zones)
        low = client(level=12, faction='Horde', zone='The Barrens').ns
        self.assertEqual(list(low.GatheringPlan(HERBALISM, 275, 300).zones.values()), [])  # Nowhere a level 12 should farm.

    def test_herbalism_lists_every_herb_in_skill_order_up_to_black_lotus(self):
        ns = client(level=60, zone='Winterspring').ns
        plan = ns.GatheringPlan(HERBALISM, 300, 300)
        self.assertIn('Black Lotus', names(plan.now))
        self.assertIsNone(plan.nextUnlock)
        self.assertIn('Everything is unlocked.', ns.GatheringText(plan))
        start = ns.GatheringPlan(HERBALISM, 1, 75)
        self.assertEqual(sorted(names(start.now)), ['Peacebloom', 'Silverleaf'])
        self.assertEqual((start.nextUnlock.name, start.nextUnlock.skill), ('Earthroot', 15))

    def test_rank_advice_follows_skill_cap_and_character_level(self):
        ns = client().ns
        self.assertIn('Train Journeyman now', ns.GatheringPlan(MINING, 60, 75, 12).rank)
        self.assertIn('needs character level 10', ns.GatheringPlan(MINING, 60, 75, 8).rank)
        self.assertIn('Train Journeyman from skill 50', ns.GatheringPlan(MINING, 30, 75, 12).rank)
        self.assertIn('Train Artisan from skill 200', ns.GatheringPlan(MINING, 180, 225, 40).rank)
        self.assertIsNone(ns.GatheringPlan(MINING, 280, 300, 60).rank)

    def test_skinning_compares_skill_with_the_beasts_the_character_fights(self):
        ns = client(level=30, zone='Hillsbrad Foothills').ns
        behind = ns.GatheringPlan(SKINNING, 140, 150)
        self.assertEqual((behind.beastTop, behind.ownLevelNeeds, behind.behind), (28, 150, 10))
        self.assertEqual(behind.beastSure, 24)                       # Level 24 needs 120: within 25 of 140.
        text = ns.GatheringText(behind)
        self.assertIn('Beasts of your level (30) need skill 150: you are 10 short', text)
        self.assertIn('Hillsbrad Foothills (you are here)', text)
        self.assertEqual(ns.GatheringSummary(behind), '10 skill short for level 30 beasts')
        level = ns.GatheringPlan(SKINNING, 150, 150)
        self.assertEqual(level.behind, 0)
        self.assertIn('You can skin everything you fight at level 30', ns.GatheringText(level))
        self.assertEqual((level.nextUnlock.name, level.nextUnlock.skill), ('Level 31 beasts', 155))

    def test_text_uses_only_glyphs_the_game_fonts_have(self):
        ns = client().ns
        for profession, skill in ((MINING, 87), (HERBALISM, 140), (SKINNING, 140), (FISHING, 140)):
            text = ns.GatheringText(ns.GatheringPlan(profession, skill, 150))
            self.assertTrue(all(ord(char) < 256 or char in '–•…' for char in text), profession)

    def test_gameobject_loot_and_local_message_record_a_real_node_yield(self):
        c = client()
        ns, lua = c.ns, c.lua
        lua.execute('''
            local ns=...
            ns.RegisterModule("Gold", {})
            ns.profile={mapID=501}
            ns.ReadProfile=function() end
            ns.PlayerPoint=function() return {x=.4,y=.6} end
            ns.gatheringData[186]={id=186,name="Mining",skill=65,maximum=75}
            function GetTime() return 100 end
            function GetLootSourceInfo() return "0xF11000000000ABCD", 1 end
            function GetNumLootItems() return 1 end
            function GetLootSlotLink() return "|Hitem:2770:0:0:0:0:0:0|h[Copper Ore]|h" end
            function GetLootSlotInfo() return "Copper Ore", "icon", 3 end
            LOOT_ITEM_SELF="You receive loot: %s"
            gathered={}
            WowTogetherModuleAPI.RegisterGatheringObserver("Gold", function(event) gathered[#gathered+1]=event end)
        ''', ns)
        ns.handlers.LOOT_OPENED()
        ns.handlers.CHAT_MSG_LOOT('You receive loot: |Hitem:2770:0:0:0:0:0:0|h[Copper Ore]|h x3')
        event = lua.globals().gathered[1]
        self.assertEqual((event.profession, event.itemID, event.quantity), ('Mining', 2770, 3))
        self.assertEqual((event.mapID, event.x, event.y, event.source), (501, .4, .6, 'gather-node'))


class FishingTests(unittest.TestCase):
    """Fishing levels by catches, so the advice is where every cast is one."""

    def test_a_confirmed_fishing_loot_message_reports_its_cast_position_to_gold(self):
        c = client()
        ns, lua = c.ns, c.lua
        lua.execute('''
            local ns=...
            ns.RegisterModule("Gold", {})
            ns.profile={mapID=501}
            ns.ReadProfile=function() end
            ns.PlayerPoint=function() return {x=.25,y=.75} end
            ns.gatheringData[356]={id=356,name="Fishing",skill=75,maximum=75}
            function GetTime() return 100 end
            LOOT_ITEM_SELF="You receive loot: %s"
            gathered={}
            WowTogetherModuleAPI.RegisterGatheringObserver("Gold", function(event) gathered[#gathered+1]=event end)
        ''', ns)
        ns.handlers.UNIT_SPELLCAST_SENT('player', 'Fishing', None, 7620)
        ns.handlers.CHAT_MSG_LOOT('You receive loot: |Hitem:6291:0:0:0:0:0:0|h[Raw Brilliant Smallfish]|h.')
        event = lua.globals().gathered[1]
        self.assertEqual(event.profession, 'Fishing')
        self.assertEqual((event.mapID, event.x, event.y), (501, .25, .75))
        self.assertEqual((event.itemID, event.quantity, event.source), (6291, 1, 'fishing-catch'))

    def test_waters_are_ranked_by_the_skill_for_a_sure_catch_and_lures_extend_them(self):
        ns = client(level=24, faction='Horde', zone='Hillsbrad Foothills').ns
        plan = ns.GatheringPlan(FISHING, 60, 75)
        self.assertEqual(plan.sureTier, 25)                           # Starting zones only, without a lure.
        self.assertEqual(plan.lure.name, 'Nightcrawlers')             # Usable from 50, +50.
        self.assertEqual(plan.lureTier, 75)                           # 110 covers the 75 waters, not the 150 ones.
        self.assertIn('The Barrens', list(plan.lureZones.values()))
        self.assertNotIn('Westfall', list(plan.lureZones.values()))   # Alliance water.
        water = plan.water
        self.assertEqual((water.cast, water.always, water.canCast, water.sure, water.need), (55, 150, True, False, 90))
        self.assertIsNone(water.lure)                                 # Nothing usable at 60 adds 90.
        text = ns.GatheringText(plan)
        self.assertIn('IN HILLSBRAD FOOTHILLS', text)
        self.assertIn('Fish get away here until skill 150 (90 to go). No lure you can use covers that gap.', text)
        self.assertIn('With Nightcrawlers (+50): ', text)
        self.assertEqual(ns.GatheringSummary(plan), '90 skill short for a sure catch here')

    def test_the_weakest_lure_that_covers_the_gap_is_named(self):
        ns = client(level=36, faction='Horde', zone='Stranglethorn Vale').ns
        plan = ns.GatheringPlan(FISHING, 130, 150)
        self.assertEqual(plan.water.lure, 'Aquadynamic Fish Attractor')  # 225 needed: only +100 gets there from 130.
        self.assertEqual(ns.GatheringSummary(plan), 'Use Aquadynamic Fish Attractor here')
        closer = ns.GatheringPlan(FISHING, 200, 225)
        self.assertEqual(closer.water.lure, 'Shiny Bauble')
        sure = ns.GatheringPlan(FISHING, 225, 225)
        self.assertTrue(sure.water.sure)
        self.assertIn('Every cast is a catch here.', ns.GatheringText(sure))
        early = ns.GatheringPlan(FISHING, 100, 150)
        self.assertFalse(early.water.canCast)
        self.assertIn('You cannot fish here yet: it needs skill 130.', ns.GatheringText(early))

    def test_expert_is_a_book_and_artisan_is_a_quest(self):
        ns = client(level=30).ns
        self.assertIn('Train Journeyman now', ns.GatheringPlan(FISHING, 60, 75).rank)
        self.assertIn('Buy the book Expert Fishing', ns.GatheringPlan(FISHING, 140, 150).rank)
        self.assertIn('From skill 125, buy the book', ns.GatheringPlan(FISHING, 100, 150).rank)
        self.assertIn('needs character level 35', ns.GatheringPlan(FISHING, 225, 225).rank)
        self.assertIn("Do Nat Pagle's quest", ns.GatheringPlan(FISHING, 225, 225, 40).rank)
        self.assertIsNone(ns.GatheringPlan(FISHING, 280, 300, 60).rank)

    def test_fishing_is_read_from_a_secondary_slot_and_gets_a_card(self):
        c = client()
        c.lua.execute('''
            function GetProfessions() return nil, nil, nil, 4 end
            function GetProfessionInfo(slot) return "Fishing", "icon", 60, 75, 0, 0, 356 end
        ''')
        ns = c.ns
        self.assertTrue(ns.ReadProfessionSkills())
        self.assertEqual(ns.gatheringData[FISHING].skill, 60)
        cards = {choice.title: choice for choice in ns.ProfessionChoices().values()}
        self.assertEqual(cards['Fishing'].count, 'Skill 60 / 75')
        self.assertIsNone(ns.GatheringZoneTip('Hillsbrad Foothills'))  # The zone tip stays quiet about fishing.


class GatheringIntegrationTests(unittest.TestCase):
    def learned(self, slots):
        c = client()
        c.lua.execute('''
            local slots = ...
            function GetProfessions() return slots[1] and 1 or nil, slots[2] and 2 or nil end
            function GetProfessionInfo(slot)
                local entry = slots[slot]
                return entry.name, "icon", entry.skill, entry.maximum, 0, 0, entry.id
            end
        ''', c.lua.table_from([c.lua.table_from(slot) for slot in slots]))
        return c

    def test_primary_gathering_professions_are_read_and_forgotten_when_unlearned(self):
        c = self.learned([{'name': 'Mining', 'skill': 87, 'maximum': 150, 'id': MINING},
                          {'name': 'Skinning', 'skill': 140, 'maximum': 150, 'id': SKINNING}])
        ns = c.ns
        self.assertTrue(ns.ReadProfessionSkills())
        self.assertEqual(ns.gatheringData[MINING].skill, 87)
        self.assertEqual(ns.gatheringData[SKINNING].maximum, 150)
        self.assertIsNone(ns.gatheringData[HERBALISM])
        c.lua.execute('function GetProfessions() return nil, nil end')
        self.assertTrue(ns.ReadProfessionSkills())
        self.assertIsNone(ns.gatheringData[MINING])

    def test_browser_lists_gathering_cards_after_crafting_ones_with_live_advice(self):
        c = self.learned([{'name': 'Mining', 'skill': 87, 'maximum': 150, 'id': MINING}])
        ns = c.ns
        ns.ReadProfessionSkills()
        choices = list(ns.ProfessionChoices().values())
        titles = [choice.title for choice in choices]
        self.assertEqual(titles[-4:], ['Mining', 'Fishing', 'Herbalism', 'Skinning'])  # Learned first, then by name.
        mining = choices[-4]
        self.assertEqual(mining.category, 'YOUR PROFESSION')
        self.assertEqual(mining.count, 'Skill 87 / 150')
        self.assertEqual(mining.detail, 'Tin Vein here gives skill')
        self.assertEqual(choices[-1].category, 'GATHERING PROFESSION')
        self.assertEqual((mining.gathering, mining.profession), (MINING, MINING))

    def test_viewer_shows_the_plan_and_a_learn_hint_for_an_unlearned_profession(self):
        c = self.learned([{'name': 'Mining', 'skill': 87, 'maximum': 150, 'id': MINING}])
        ns = c.ns
        ns.ShowGatheringViewer(MINING)
        viewer = ns.gatheringViewer
        self.assertTrue(viewer.IsShown(viewer))
        self.assertEqual(viewer.title.text, 'Mining')
        self.assertIn('GIVES SKILL NOW', viewer.body.text)
        ns.ShowGatheringViewer(HERBALISM)
        self.assertIn('Learn Herbalism from a trainer', viewer.body.text)

    def test_entering_a_zone_says_once_what_gives_skill_there_and_stays_quiet_otherwise(self):
        c = self.learned([{'name': 'Mining', 'skill': 87, 'maximum': 150, 'id': MINING},
                          {'name': 'Skinning', 'skill': 140, 'maximum': 150, 'id': SKINNING}])
        ns = c.ns
        c.lua.execute('local ns = ...; ns.profile.level = 30; zoneName = "Hillsbrad Foothills"; function GetRealZoneText() return zoneName end', ns)
        ns.ReadProfessionSkills()
        self.assertEqual(ns.GatheringZoneTip('Hillsbrad Foothills'),
                         'Gathering in Hillsbrad Foothills: Tin Vein, Silver Vein give Mining skill; '
                         'Skinning is 10 short for beasts your level: skin level 24–28 ones.')
        self.assertIsNone(ns.GatheringZoneTip('Winterspring'))       # Nothing there for this character.
        for _ in range(2):                                            # Arriving twice says it once.
            ns.GatheringZoneArrived(); c.drain()
        printed = list(c.lua.globals().printed.values())
        self.assertEqual(len(printed), 1)
        self.assertTrue(printed[0].startswith('Gathering in Hillsbrad Foothills'))
        c.lua.execute('zoneName = "Winterspring"')
        ns.GatheringZoneArrived(); c.drain()
        self.assertEqual(len(list(c.lua.globals().printed.values())), 1)
        ns.SetOption('gatheringTips', False)
        c.lua.execute('zoneName = "Arathi Highlands"')
        ns.GatheringZoneArrived(); c.drain()
        self.assertEqual(len(list(c.lua.globals().printed.values())), 1)  # Switched off: silent.

    def test_chat_command_gives_one_line_per_learned_gathering_profession(self):
        c = self.learned([{'name': 'Mining', 'skill': 87, 'maximum': 150, 'id': MINING},
                          {'name': 'Herbalism', 'skill': 140, 'maximum': 150, 'id': HERBALISM}])
        c.ns.GatheringCommand()
        printed = list(c.lua.globals().printed.values())
        self.assertEqual(len(printed), 2)
        self.assertTrue(printed[0].startswith('Mining 87: Tin Vein here gives skill. Next: Iron Deposit at 125'))
        none = self.learned([])
        none.ns.GatheringCommand()
        self.assertIn('No gathering profession learned', list(none.lua.globals().printed.values())[0])


if __name__ == '__main__':
    unittest.main()


class GatheringBrowserTests(unittest.TestCase):
    def test_profession_browser_renders_gathering_cards_and_opens_the_viewer(self):
        helper = GatheringIntegrationTests()
        c = helper.learned([{'name': 'Mining', 'skill': 87, 'maximum': 150, 'id': MINING}])
        ns = c.ns
        ns.ReadProfessionSkills()
        if not ns.window.IsShown(ns.window):
            ns.ToggleWindow()
        ns.SetFilter('professions')
        c.drain()
        cards = [ns.ui.cards[index] for index in range(1, ns.ui.visibleCards + 1)]
        titles = [card.title.text for card in cards]
        self.assertIn('Mining', titles)
        self.assertIn('Herbalism', titles)
        self.assertIn('Tailoring', titles)                       # Crafting cards are still there.
        mining = cards[titles.index('Mining')]
        self.assertEqual(mining.activity.gathering, MINING)
        mining.detailsButton.OnClick()
        viewer = ns.gatheringViewer
        self.assertIsNotNone(viewer)
        self.assertTrue(viewer.IsShown(viewer))
        self.assertEqual(viewer.professionID, MINING)
        self.assertIsNone(ns.routeSelection)                     # No crafting guide was started for it.
