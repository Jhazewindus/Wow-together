"""Personal recommendations are read-only until a player chooses a guide."""
import unittest

from test_addon import Client
from test_0811 import browser
from test_061 import world_quest, run_plan
from test_063 import zone, order
from test_0836 import crafting
from test_routes import catalogue


def recommendations(c, kind=None):
    items, states = c.ns.RecommendedItems()
    return [v for v in items.values() if kind is None or v.kind == kind], states


class RecommendedHomeTests(unittest.TestCase):
    def test_open_lands_on_recommended_without_resetting_browser_filters(self):
        c = browser()
        c.ns.SetGuideLevel('21-30'); c.ns.guideSearch = 'Future'
        c.ns.window.Hide(c.ns.window); c.ns.ToggleWindow()
        self.assertEqual(c.ns.filter, 'recommended')
        self.assertEqual(c.ns.ui.viewChoice.caption.text, 'Recommended')
        self.assertEqual(c.ns.guideLevel, '21-30')
        self.assertEqual(c.ns.guideSearch, 'Future')
        self.assertEqual(c.ns.ui.home.leveling.data.guide.zone, 'Test Coast')
        self.assertFalse(any(w.IsShown(w) for w in c.ns.ui.guideControls.values()))
        self.assertIsNone(c.ns.routeSelection)

    def test_default_and_empty_states_are_honest(self):
        c = Client(default_guide=True, quests=())
        self.assertEqual(c.ns.filter, 'recommended')
        self.assertIn('loading', c.ns.ui.home.leveling.detail.text)
        self.assertEqual(c.ns.ui.home.professionCount, 0)
        self.assertEqual(c.ns.ui.home.extraCount, 0)
        self.assertIn('Learn a crafting profession', c.ns.ui.home.professionEmpty.text.text)
        self.assertIsNone(c.ns.routeSelection)

    def test_finished_and_manually_skipped_zones_are_not_recommended(self):
        for finished in (True, False):
            with self.subTest(finished=finished):
                c = browser()
                for id in (900, 901):
                    if finished: c.lua.globals().finished[id] = True
                    else:
                        c.ns.db.guideSkips[c.ns.self] = c.lua.table_from({'quests': {900: True, 901: True}}, recursive=True)
                c.ns.Refresh()
                items, states = recommendations(c, 'leveling')
                self.assertEqual(items, [])
                self.assertIn('No suitable unfinished', states.leveling)

    def test_identity_and_level_exclusions_use_existing_rules(self):
        c = browser()
        c.lua.execute("function UnitClass() return 'Shaman','SHAMAN',7 end; function UnitRace() return 'Orc','Orc',2 end")
        c.ns.ReadProfile()
        data = {900: world_quest('Current one'), 901: world_quest('Current two')}
        for index, extra in enumerate([{'side': 'Alliance'}, {'repeatable': True},
                                      {'classMask': 128}, {'raceMask': 32}]):
            for n in range(2):
                data[920+index*2+n] = world_quest('Wrong', 'Wrong '+str(index), 502+index, 12, **extra)
        catalogue(c, data); c.ns.SetFilter('recommended')
        items, _ = recommendations(c, 'leveling')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].guide.zone, 'Test Coast')
        self.assertIn('current zone', items[0].detail)
        self.assertEqual({r.id for r in items[0].guide.records.values()}, {900, 901})
        self.assertEqual(items[0].progressTotal, 2)
        del data[900], data[901]
        catalogue(c, data); c.ns.Refresh()
        self.assertEqual(recommendations(c, 'leveling')[0], [])

    def test_max_level_has_no_fabricated_leveling_card(self):
        c = browser(level=60); c.ns.SetFilter('recommended')
        items, states = recommendations(c, 'leveling')
        self.assertEqual(items, [])
        self.assertIn('Level cap reached', states.leveling)

    def test_continue_does_not_replan_or_replace_active_guide(self):
        c = browser(); g = zone(c)
        c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(c.ns.routeSelection)
        c.ns.window.Hide(c.ns.window); c.ns.ToggleWindow()
        self.assertTrue(c.ns.ui.home.resume.IsShown(c.ns.ui.home.resume))
        self.assertEqual(c.ns.ui.home.leveling.start.caption.text, 'Continue guide')
        c.ns.ui.home.leveling.start.OnClick()
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertIsNone(c.ns.routePlanning)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))

    def test_preview_and_browsing_preserve_active_route(self):
        c = browser(); g = zone(c)
        c.ns.ShowGuideOnMap(g); run_plan(c); before = order(c.ns.routeSelection)
        c.ns.SetFilter('recommended')
        c.ns.ui.home.leveling.inspect.OnClick(); c.drain()
        self.assertTrue(c.ns.guideQuestList.IsShown(c.ns.guideQuestList))
        self.assertEqual(order(c.ns.routeSelection), before)
        c.ns.ui.home.browseProfessions.OnClick()
        self.assertEqual(c.ns.filter, 'professions')
        self.assertFalse(c.ns.ui.home.IsShown(c.ns.ui.home))
        self.assertEqual(order(c.ns.routeSelection), before)

    def test_start_card_activates_the_existing_fixed_guide(self):
        c = browser(); c.ns.SetFilter('recommended')
        c.ns.ui.home.leveling.start.OnClick(); run_plan(c)
        self.assertEqual(c.ns.routeSelection.zone, 'Test Coast')
        self.assertTrue(c.ns.routeSelection.fixedRoute)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})

    def test_resize_uses_card_geometry_without_querying_planners(self):
        c = crafting(); c.ns.SetFilter('recommended')
        c.lua.execute('nsForHome=...; nsForHome.LevelingGuideChoices=function() error("quest read while resizing") end; '
                      'nsForHome.BuildProfessionGuideRoute=function() error("recipe read while resizing") end', c.ns)
        for width in (760, 860, 1080):
            c.ns.window.SetSize(c.ns.window, width, 700); c.ns.Layout()
            home = c.ns.ui.home
            self.assertEqual(home.leveling.width, width-74)
            self.assertEqual(home.cards[1].width, (width-74-12)/2)
            self.assertGreaterEqual(c.ns.ui.content.height, home.height)
        self.assertIsNone(c.ns.routeSelection)

    def test_cache_invalidates_after_quest_progress(self):
        c = browser(); c.ns.SetFilter('recommended')
        c.lua.execute('local ns=...; homeReads=0; local original=ns.LevelingGuideChoices; '
                      'ns.LevelingGuideChoices=function(...) homeReads=homeReads+1; return original(...) end', c.ns)
        c.ns.RecommendedItems(); c.ns.RecommendedItems()
        self.assertEqual(c.lua.globals().homeReads, 0)
        c.lua.globals().finished[900] = True
        c.ns.handlers.QUEST_TURNED_IN(900); c.drain()
        items, _ = recommendations(c, 'leveling')
        self.assertEqual(items[0].progressValue, 1)
        self.assertGreater(c.lua.globals().homeReads, 0)

    def test_future_provider_is_supported_and_failure_is_isolated(self):
        c = browser(); c.ns.SetFilter('recommended')
        c.lua.execute('local ns=...; ns.RegisterRecommendationProvider("future", function() '
                      'return {{key="future:one",kind="future",priority=10,title="An added activity",action="Open",'
                      'start=function() futureClicked=true end}} end); '
                      'ns.RegisterRecommendationProvider("broken", function() error("bad provider") end)', c.ns)
        c.ns.Refresh()
        self.assertEqual(c.ns.ui.home.extraCount, 1)
        self.assertEqual(c.ns.ui.home.leveling.data.guide.zone, 'Test Coast')
        self.assertIn('bad provider', c.ns.recommendationErrors.broken)
        c.ns.ui.home.extraCards[1].start.OnClick()
        self.assertTrue(c.lua.globals().futureClicked)


class RecommendedProfessionTests(unittest.TestCase):
    def test_only_known_crafting_professions_are_recommended(self):
        c = crafting(); c.ns.professionData[186] = c.lua.table_from({'skill': 10, 'maximum': 75})
        c.ns.SetFilter('recommended')
        items, _ = recommendations(c, 'professions')
        self.assertEqual([i.professionID for i in items], [171])
        self.assertEqual(items[0].count, 'Skill 20 / 75')
        self.assertIn('Starter mixture', items[0].detail)
        self.assertIsNone(c.ns.routeSelection)
        self.assertIsNone(c.ns.selectedRoute)
        self.assertEqual(c.ns.ProfessionGoal(171), 225)

    def test_saved_goal_and_current_skill_drive_cards_and_completed_goal(self):
        c = crafting(skill=75); c.ns.ProfessionGoal(171, 75); c.ns.SetFilter('recommended')
        items, _ = recommendations(c, 'professions')
        self.assertEqual(items[0].action, 'View guide')
        self.assertEqual(items[0].progressValue, 75)
        self.assertEqual(items[0].progressTotal, 75)
        c.ns.ProfessionGoal(171, 150); c.ns.Refresh()
        items, _ = recommendations(c, 'professions')
        self.assertEqual(items[0].action, 'Start guide')
        self.assertIn('Journeyman', items[0].detail)

    def test_rank_and_character_level_blocks_are_explained(self):
        c = crafting(skill=75, level=9); c.ns.ProfessionGoal(171, 150); c.ns.SetFilter('recommended')
        items, _ = recommendations(c, 'professions')
        self.assertIn('character level 10', items[0].detail)
        self.assertIsNone(c.ns.routeSelection)

    def test_profession_preview_and_continue_preserve_running_batch(self):
        c = crafting(); c.ns.StartProfessionGuide(171, 75)
        c.ns.SetFilter('recommended')
        before = c.ns.routeSelection.professionBatch.remaining
        c.ns.ui.home.cards[1].inspect.OnClick()
        self.assertEqual(c.ns.routeSelection.professionID, 171)
        self.assertEqual(c.ns.routeSelection.professionBatch.remaining, before)
        self.assertEqual(c.ns.ui.home.cards[1].start.caption.text, 'Continue guide')
        c.ns.ui.home.cards[1].start.OnClick()
        self.assertEqual(c.ns.routeSelection.targetSkill, 75)
        self.assertEqual(c.ns.routeSelection.professionBatch.remaining, before)

    def test_visible_home_updates_on_skill_changes_and_profession_removal(self):
        c = crafting(); c.ns.SetFilter('recommended'); c.ns.window.Show(c.ns.window)
        c.lua.globals().pskill = 25
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertEqual(c.ns.ui.home.cards[1].data.count, 'Skill 25 / 75')
        c.lua.execute('function GetProfessions() return nil,nil end')
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertEqual(c.ns.ui.home.professionCount, 0)
        self.assertFalse(c.ns.ui.home.cards[1].IsShown(c.ns.ui.home.cards[1]))

    def test_open_reads_native_profession_skill_again(self):
        c = crafting(); c.ns.SetFilter('professions')
        c.lua.globals().pskill = 31
        c.ns.window.Hide(c.ns.window); c.ns.ToggleWindow()
        self.assertEqual(c.ns.ui.home.cards[1].data.count, 'Skill 31 / 75')


if __name__ == '__main__':
    unittest.main()
