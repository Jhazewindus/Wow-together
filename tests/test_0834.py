"""Bracket-specific scopes, dependency carryover and stable fixed guide progress.

Lua 5.1 host fixtures exercise logic; Forever availability still needs beta tests.
"""
import unittest

from test_addon import Client
from test_061 import world_quest, run_plan
from test_063 import guide_client, order
from test_066 import reload
from test_routes import catalogue


BASE = 'level-zone:kalimdor/test-coast'


def browser(level=12):
    c = guide_client(2)
    c.lua.globals().playerLevel = level
    c.ns.ReadProfile()
    catalogue(c, {
        900: world_quest('Starter one', level=5, xp=100),
        901: world_quest('Starter two', level=6, xp=100),
        910: world_quest('Middle one', level=12, xp=200),
        911: world_quest('Middle two', level=13, xp=200),
        920: world_quest('Later one', level=25, minLevel=20, xp=500),
        921: world_quest('Later two', level=26, minLevel=20, xp=500),
        930: world_quest('Final one', level=55, minLevel=50, xp=1000),
        931: world_quest('Final two', level=56, minLevel=50, xp=1000),
    })
    return c


def section(c, bracket='11-20'):
    c.ns.guideLevel = bracket
    return c.ns.LevelingGuideChoices()[1]


def ids(guide):
    return {r.id for r in guide.records.values()}


class SectionScopeTests(unittest.TestCase):
    def test_all_levels_is_separate_real_guides_and_sections_have_stable_keys(self):
        c = browser(); c.ns.guideLevel = 'all'
        guides = list(c.ns.LevelingGuideChoices().values())
        self.assertEqual(len(guides), 4)
        self.assertEqual({(g.sectionLow, g.sectionHigh) for g in guides},
                         {(1, 10), (11, 20), (21, 30), (51, 60)})
        for g in guides:
            self.assertEqual(g.zoneGuideKey, BASE)
            self.assertEqual(g.key, BASE + f':levels:{g.sectionLow}-{g.sectionHigh}')
            self.assertEqual(len(g.records), 2)
            self.assertTrue(all(g.sectionLow <= r.level <= g.sectionHigh for r in g.records.values()))
        self.assertEqual(guides[0].sectionLow, 11)

    def test_middle_section_omits_unrelated_starter_and_future_quests(self):
        c = browser(); g = section(c)
        self.assertEqual(ids(g), {910, 911})
        self.assertEqual((g.minLevel, g.maxLevel, g.mainLevelLow, g.mainLevelHigh), (12, 13, 12, 13))
        self.assertIn('Levels 11–20', g.title)
        self.assertEqual(c.ns.GuideXPProjection(g).reward, 400)
        c.ns.ShowGuideQuestList(g); c.drain()
        self.assertEqual({s.id for s in c.ns.guideQuestList.plan.values()}, {910, 911})
        self.assertEqual(len(c.ns.guideQuestList.plan), 6)
        c.ns.SetFilter('guides')
        self.assertIn('2 quests', c.ns.ui.cards[1].reason.text)
        self.assertFalse(c.ns.ui.cards[1].count.IsShown(c.ns.ui.cards[1].count))

    def test_empty_and_isolated_sections_do_not_create_guides(self):
        c = browser()
        c.ns.catalogue.quests[940] = c.lua.table_from(world_quest('Only quest', level=35), recursive=True)
        self.assertEqual(len(c.ns.LevelingGuideChoices(True, None, '31-40')), 0)
        self.assertEqual(len(c.ns.LevelingGuideChoices(True, None, '41-50')), 0)
        final = list(c.ns.LevelingGuideChoices(True, None, '51+').values())
        self.assertEqual(len(final), 1)
        self.assertEqual(ids(final[0]), {930, 931})

    def test_dependency_from_earlier_bracket_and_another_zone_is_preserved(self):
        c = browser()
        c.ns.catalogue.quests[899] = c.lua.table_from(
            world_quest('Required introduction', 'Other Zone', 502, 5, xp=50), recursive=True)
        c.ns.catalogue.quests[910].previousQuest = 899
        g = section(c)
        self.assertEqual(ids(g), {899, 910, 911})
        self.assertEqual((g.mainLevelLow, g.mainLevelHigh), (12, 13))
        c.ns.GenerateFixedGuide(g, False)
        ops = [(s.id, s.kind) for s in g.fixedPlan.values()]
        self.assertLess(ops.index((899, 't')), ops.index((910, 'a')))
        self.assertIn('Middle one', c.ns.LevelingValue(899)[1])
        self.assertNotIn(900, ids(g))

    def test_branching_and_observed_dependencies_stay_in_section_scope(self):
        c = browser()
        c.ns.catalogue.quests[910].prerequisiteAny = c.lua.table_from([900, 901])
        c.ns.LearnedPrerequisiteIDs = c.lua.eval('function(id) if id==911 then return {900} end return {} end')
        self.assertEqual(ids(section(c)), {900, 901, 910, 911})

    def test_nearby_cross_bracket_chain_continues_without_importing_distant_future(self):
        c = browser(level=20)
        catalogue(c, {
            900: world_quest('Last local work', level=20, series=[900, 901, 902]),
            901: world_quest('Nearby continuation', 'Other Zone', 502, 21, previousQuest=900),
            902: world_quest('Much later continuation', 'Other Zone', 502, 40, previousQuest=901),
            903: world_quest('Second local quest', level=19),
        })
        g = section(c)
        self.assertEqual(ids(g), {900, 901, 903})
        self.assertEqual((g.mainLevelLow, g.mainLevelHigh), (19, 20))
        c.ns.GenerateFixedGuide(g, False)
        self.assertTrue(any(s.id == 901 and s.mapID == 502 for s in g.fixedPlan.values()))

    def test_remote_pickup_zone_is_not_a_leveling_section_and_exclusions_remain(self):
        c = browser(level=25)
        catalogue(c, {
            900: world_quest('Local one', level=25), 901: world_quest('Local two', level=26),
            902: world_quest('Remote one', 'Pickup Zone', 502, 25,
                             objectives=[{'mapID': 503, 'x': .3, 'y': .4}]),
            903: world_quest('Remote two', 'Pickup Zone', 502, 26,
                             objectives=[{'mapID': 503, 'x': .3, 'y': .4}]),
            904: world_quest('Wrong faction', level=25, side='Alliance'),
            905: world_quest('Repeat', level=25, repeatable=True),
            906: world_quest('Profession', level=25, categoryPath='professions/cooking'),
            907: world_quest('Dungeon', level=25, categoryPath='dungeons/test'),
        })
        c.ns.guideLevel = '21-30'
        self.assertEqual(len(c.ns.LevelingGuideChoices()), 1)
        self.assertEqual(ids(c.ns.LevelingGuideChoices()[1]), {900, 901})

    def test_future_preview_does_not_bypass_actual_level_or_pickup_minimum(self):
        c = browser(); g = section(c, '21-30')
        self.assertFalse(g.levelReady); self.assertTrue(g.upcoming)
        self.assertEqual(ids(g), {920, 921})
        c.ns.RequestStartRoute(g)
        self.assertEqual(c.ns.earlyGuidePrompt.advice.recommendedLevel, 22)
        c.ns.earlyGuidePrompt.anyway.OnClick(); run_plan(c)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertFalse(c.ns.selectedRoute.complete)
        c.lua.globals().playerLevel = 25; c.ns.ReadProfile(); c.ns.Refresh()
        self.assertEqual(ids(c.ns.routeSelection), {920, 921})
        self.assertTrue(c.ns.selectedRoute.stops[1])

    def test_class_toggle_filters_later_without_losing_saved_instructions(self):
        c = browser(); c.ns.profile.classID = 8
        c.ns.catalogue.quests[912] = c.lua.table_from(
            world_quest('Own class', categoryPath='classes/mage', classMask=128), recursive=True)
        c.ns.SetOption('classQuests', False)
        g = section(c)
        self.assertEqual(ids(g), {910, 911, 912})
        self.assertEqual(g.enabledCount, 2)
        c.ns.GenerateFixedGuide(g, False); before = order(g)
        self.assertNotIn(912, {s.id for s in c.ns.BuildFixedGuideRoute(g, False).stops.values()})
        c.ns.SetOption('classQuests', True)
        self.assertEqual(order(g), before)
        self.assertIn(912, {s.id for s in c.ns.BuildFixedGuideRoute(g, False).stops.values()})

    def test_shipped_mulgore_has_distinct_starter_and_later_forever_sections(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=12)
        c.lua.globals().grouped = False
        c.ns.profile.mapID, c.ns.profile.raceID, c.ns.profile.classID = 1412, 6, 1
        c.ns.guideLevel = 'all'
        guides = {g.sectionLow: g for g in c.ns.LevelingGuideChoices().values() if g.zone == 'Mulgore'}
        self.assertIn(1, guides); self.assertIn(21, guides)
        self.assertNotIn(96259, ids(guides[1]))
        self.assertIn(96259, ids(guides[21]))
        self.assertEqual((guides[21].mainLevelLow, guides[21].mainLevelHigh), (30, 30))
        self.assertFalse(guides[21].levelReady)
        # The stable zone identity also retains art if a beta map ID/name changes.
        themed = c.lua.table_from({'key': guides[21].key, 'zoneGuideKey': guides[21].zoneGuideKey,
                                  'zone': 'Localized zone', 'homeMapID': 0})
        self.assertEqual(c.ns.GuideCardTheme(themed), 'prairie')


class SectionProgressTests(unittest.TestCase):
    def test_scan_location_log_and_browser_changes_keep_section_order(self):
        c = browser(); g = section(c)
        c.ns.ShowGuideOnMap(g); run_plan(c); before = order(g)
        c.ns.guideLevel = '21-30'
        c.lua.execute("entries={{questID=910,title='Middle one',isHeader=false}};"
                      "C_Map.GetPlayerMapPosition=function()return {GetXY=function()return .8,.8 end}end")
        c.ns.SyncNow(False); c.drain(); c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(ids(c.ns.routeSelection), {910, 911})
        self.assertEqual(order(c.ns.routeSelection), before)
        c.lua.execute('entries={}')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertEqual(ids(c.ns.routeSelection), {910, 911})

    def test_adaptive_rescan_also_keeps_section_and_start_xp(self):
        c = browser(); c.ns.db.config.fixedZoneGuides = False
        g = section(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        reward = c.ns.routeSelection.xpReward
        c.ns.guideLevel = '21-30'
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(ids(c.ns.routeSelection), {910, 911})
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertEqual(c.ns.routeSelection.xpReward, reward)

    def test_reload_section_keeps_scope_metadata_and_skips(self):
        c = browser(); g = section(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        c.ns.SkipGuide('quest'); before = order(g)
        fresh = reload(c)
        restored = fresh.ns.routeSelection
        self.assertEqual(ids(restored), {910, 911})
        self.assertEqual((restored.zoneGuideKey, restored.sectionLow, restored.sectionHigh), (BASE, 11, 20))
        self.assertEqual(order(restored), before)
        self.assertTrue(fresh.ns.GuideQuestSkipped(910))

    def test_legacy_saved_full_zone_remains_full_zone_after_upgrade_and_scan(self):
        c = browser()
        invite = c.lua.table_from({'guideKey': BASE, 'mode': 'zone', 'rangeLow': 11, 'rangeHigh': 20,
                                   'sender': 'Bob-TestRealm', 'fixedRoute': True}, recursive=True)
        g = c.ns.InvitedLevelingGuide(invite)
        self.assertEqual(len(g.records), 8); self.assertIsNone(g.sectionLow)
        c.ns.ShowGuideOnMap(g); run_plan(c)
        c.ns.SaveSelectedGuide()
        c.ns.db.guideState[c.ns.self].addon = '0.8.33'
        fresh = reload(c)
        self.assertEqual(fresh.ns.routeSelection.key, BASE)
        self.assertEqual(len(fresh.ns.routeSelection.records), 8)
        before = order(fresh.ns.routeSelection)
        fresh.ns.guideLevel = '21-30'; fresh.ns.ScanGuideProgress(); fresh.drain()
        self.assertEqual(len(fresh.ns.routeSelection.records), 8)
        self.assertEqual(order(fresh.ns.routeSelection), before)

    def test_new_shared_section_reconstructs_scope_and_rejects_mismatched_range(self):
        c = browser(); g = section(c)
        invite = c.lua.table_from({'guideKey': g.key, 'mode': 'zone', 'rangeLow': 11, 'rangeHigh': 20,
                                   'sender': 'Bob-TestRealm', 'fixedRoute': True}, recursive=True)
        shared = c.ns.BuildInvitedGuide(invite)
        self.assertEqual(ids(shared), {910, 911})
        self.assertEqual(shared.key, g.key)
        invite.rangeHigh = 30
        self.assertIsNone(c.ns.InvitedLevelingGuide(invite))
        for key in (BASE + ':levels:12-20', BASE + ':levels:11-30'):
            invite.guideKey = key
            self.assertIsNone(c.ns.InvitedLevelingGuide(invite))

    def test_map_lookup_uses_current_section_except_explicit_full_zone_catchup(self):
        c = browser()
        self.assertEqual(ids(c.ns.ZoneGuideForMap(501)), {910, 911})
        full = c.ns.ZoneGuideForMap(501, True)
        self.assertEqual(full.key, BASE)
        self.assertEqual(len(full.records), 8)
        self.assertIsNone(full.sectionLow)

    def test_next_section_is_offered_only_when_current_work_ends_and_is_not_forced(self):
        c = browser(level=8); g = section(c, '1-10')
        c.ns.db.config.zonePrompts = False
        c.ns.ShowGuideOnMap(g); run_plan(c)
        self.assertIsNone(c.ns.LevelingZoneTransition())
        c.lua.globals().finished[900] = True; c.lua.globals().finished[901] = True
        c.lua.globals().playerLevel = 12; c.ns.ReadProfile(); c.ns.Refresh()
        next_guide = c.ns.LevelingZoneTransition()
        self.assertIsNotNone(next_guide)
        self.assertEqual(next_guide.sectionLow, 11)
        self.assertEqual(c.ns.routeSelection.key, g.key)


if __name__ == '__main__':
    unittest.main()
