"""Future-zone browsing is separate from runtime eligibility and current-guide consent."""
import unittest

from test_addon import Client
from test_063 import guide_client, zone, order
from test_061 import world_quest, run_plan
from test_066 import reload
from test_routes import catalogue


def browser(level=12, **extras):
    c = guide_client(2)
    c.lua.globals().playerLevel = level
    c.ns.ReadProfile()
    data = {900: world_quest('Current one'), 901: world_quest('Current two'),
            910: world_quest('Future one', 'Future Hills', 502, 25, minLevel=20),
            911: world_quest('Future two', 'Future Hills', 502, 25, minLevel=20)}
    data.update(extras)
    catalogue(c, data)
    c.ns.SetFilter('guides')
    return c


def future(c):
    return next(g for g in c.ns.LevelingGuideChoices().values() if g.zone == 'Future Hills')


class FutureGuideBrowserTests(unittest.TestCase):
    def test_default_recommends_current_work_explicit_bracket_previews_future(self):
        c = browser()
        self.assertEqual([g.zone for g in c.ns.LevelingGuideChoices().values()], ['Test Coast'])
        c.ns.SetGuideLevel('21-30')
        g = future(c)
        self.assertTrue(g.upcoming)
        self.assertFalse(g.levelReady)
        self.assertEqual(c.ns.ui.cards[1].category.text, 'UPCOMING ZONE GUIDE')
        self.assertEqual(c.ns.ui.cards[1].mapButton.caption.text, 'Show quest list')
        self.assertTrue(c.ns.ui.cards[1].detailsButton.IsEnabled(c.ns.ui.cards[1].detailsButton))
        self.assertIsNone(c.ns.routeSelection)
        self.assertFalse(c.ns.CatalogueAllowed(910, c.ns.profile, c.ns.self)[0])

    def test_all_levels_ranks_current_guides_before_upcoming(self):
        c = browser(); c.ns.SetGuideLevel('all')
        guides = list(c.ns.LevelingGuideChoices().values())
        self.assertEqual([g.zone for g in guides], ['Test Coast', 'Future Hills'])
        self.assertTrue(guides[0].levelReady)
        self.assertTrue(guides[1].upcoming)
        self.assertEqual(c.ns.ui.cards[1].category.text, 'RECOMMENDED ZONE GUIDE')

    def test_future_search_and_full_order_preview_do_not_replace_running_guide(self):
        c = browser(); current = zone(c)
        c.ns.ShowGuideOnMap(current); run_plan(c)
        before = order(current)
        c.ns.SetGuideLevel('21-30')
        c.ns.guideSearchDraft = 'Future'; c.ns.ApplyGuideSearch()
        card = c.ns.ui.cards[1]
        card.mapButton.OnClick(); c.drain()
        self.assertEqual({s.id for s in c.ns.guideQuestList.plan.values()}, {910, 911})
        for id in (910, 911):
            self.assertEqual([s.kind for s in c.ns.guideQuestList.plan.values() if s.id == id], ['a', 'q', 't'])
        self.assertEqual(c.ns.routeSelection.key, current.key)
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertEqual(c.ns.profile.level, 12)

    def test_warning_has_effective_suggestion_without_changing_browsing_or_route(self):
        c = browser(); current = zone(c)
        c.ns.ActivateRoute(current); before = order(current)
        c.ns.SetGuideLevel('21-30'); c.ns.guideSearch = 'Future'
        c.ns.RequestStartRoute(future(c))
        prompt = c.ns.earlyGuidePrompt
        self.assertTrue(prompt.IsShown(prompt))
        self.assertEqual(prompt.advice.recommendedLevel, 22)
        self.assertEqual(prompt.advice.recommendation.zone, 'Test Coast')
        self.assertIn('Test Coast', prompt.text.text)
        self.assertEqual(c.ns.guideLevel, '21-30')
        self.assertEqual(c.ns.guideSearch, 'Future')
        self.assertIsNone(c.ns.routePlanning)
        prompt.cancel.OnClick()
        self.assertEqual(c.ns.routeSelection.key, current.key)
        self.assertEqual(order(c.ns.routeSelection), before)

    def test_start_recommended_uses_current_effective_route(self):
        c = browser(); c.ns.SetGuideLevel('21-30')
        c.ns.RequestStartRoute(future(c))
        c.ns.earlyGuidePrompt.recommended.OnClick(); run_plan(c)
        self.assertEqual(c.ns.routeSelection.zone, 'Test Coast')
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})
        self.assertIsNone(c.ns.routeSelection.earlyStartLevel)
        self.assertFalse(c.ns.earlyGuidePrompt.IsShown(c.ns.earlyGuidePrompt))

    def test_start_anyway_waits_then_unlocks_without_reordering(self):
        c = browser(); c.ns.SetGuideLevel('21-30'); g = future(c)
        c.ns.RequestStartRoute(g)
        c.ns.earlyGuidePrompt.anyway.OnClick(); run_plan(c)
        before = order(c.ns.routeSelection)
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertEqual(c.ns.routeSelection.earlyStartLevel, 22)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.remainingSteps, 6)
        self.assertIn('recommended from level 22', c.ns.routePaused)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertFalse(c.ns.Completed(910))
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertIsNone(c.ns.selectedRoute.complete)
        c.lua.globals().playerLevel = 25; c.ns.ReadProfile(); c.ns.Refresh()
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {910, 911})
        self.assertIsNone(c.ns.routePaused)

    def test_started_early_guide_survives_reload_without_completion_credit(self):
        c = browser(); c.ns.SetGuideLevel('21-30')
        c.ns.RequestStartRoute(future(c)); c.ns.earlyGuidePrompt.anyway.OnClick(); run_plan(c)
        before = order(c.ns.routeSelection)
        fresh = reload(c)
        self.assertEqual(fresh.ns.routeSelection.earlyStartLevel, 22)
        self.assertEqual(order(fresh.ns.routeSelection), before)
        self.assertIsNone(fresh.ns.selectedRoute.complete)
        self.assertEqual(len(fresh.ns.selectedRoute.stops), 0)
        self.assertFalse(fresh.ns.Completed(910))

    def test_existing_include_current_quests_prompt_follows_early_warning(self):
        c = browser(); c.ns.active[900] = 'Current one'; c.ns.SetGuideLevel('21-30')
        c.ns.RequestStartRoute(future(c))
        self.assertIsNone(c.ns.startGuidePrompt)
        c.ns.earlyGuidePrompt.anyway.OnClick()
        self.assertTrue(c.ns.startGuidePrompt.IsShown(c.ns.startGuidePrompt))
        self.assertIsNone(c.ns.routeSelection)
        c.ns.startGuidePrompt.current.OnClick(); run_plan(c)
        self.assertEqual(c.ns.routeSelection.mode, 'bundle')
        self.assertEqual(c.ns.routeSelection.earlyStartLevel, 22)
        self.assertFalse(any(s.id == 910 for s in c.ns.selectedRoute.stops.values()))

    def test_no_suitable_unfinished_recommendation_is_not_fabricated(self):
        c = browser(); c.lua.globals().finished[900] = True; c.lua.globals().finished[901] = True
        c.ns.SetGuideLevel('21-30'); c.ns.RequestStartRoute(future(c))
        self.assertIsNone(c.ns.earlyGuidePrompt.advice.recommendation)
        self.assertFalse(c.ns.earlyGuidePrompt.recommended.IsEnabled(c.ns.earlyGuidePrompt.recommended))
        self.assertIn('No suitable unfinished', c.ns.earlyGuidePrompt.text.text)
        self.assertIsNone(c.ns.routeSelection)

    def test_future_browsing_keeps_identity_and_nonleveling_exclusions(self):
        c = browser(**{})
        data = {900: world_quest('Current one'), 901: world_quest('Current two')}
        for group, extra in enumerate([{'side': 'Alliance'}, {'repeatable': True},
                                       {'categoryPath': 'professions/cooking'}, {'categoryPath': 'dungeons/test'}]):
            for step in range(2):
                data[950 + group * 2 + step] = world_quest('Excluded ' + str(step), 'Wrong ' + str(group), 503+group, 25, **extra)
        catalogue(c, data); c.ns.SetGuideLevel('21-30')
        self.assertEqual(len(c.ns.LevelingGuideChoices()), 0)

    def test_warning_uses_prerequisite_levels_and_does_not_mutate_character(self):
        c = browser()
        c.ns.catalogue.quests[910].prerequisiteAll = c.lua.table_from([911])
        c.ns.catalogue.quests[911].minLevel = 27
        c.ns.SetGuideLevel('21-30'); advice = c.ns.GuideEarlyStartAdvice(future(c))
        self.assertEqual(advice.recommendedLevel, 27)
        self.assertEqual(c.ns.profile.level, 12)
        self.assertFalse(c.ns.CatalogueAllowed(910, c.ns.profile, c.ns.self)[0])
        self.assertFalse(c.ns.Completed(911))

    def test_suitable_guide_starts_without_early_warning_and_travel_is_unchanged(self):
        c = browser(level=25); c.ns.SetGuideLevel('21-30'); g = future(c)
        c.ns.RequestStartRoute(g); run_plan(c)
        self.assertIsNone(c.ns.earlyGuidePrompt)
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertIsNone(c.ns.routeSelection.earlyStartLevel)
        self.assertIsNone(c.ns.GuideEarlyStartAdvice(c.ns.OrgrimmarTravelGuide()))

    def test_shipped_level_twenty_bracket_is_browsable_at_twelve(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=12)
        c.lua.globals().grouped = False; c.ns.profile.classID = 7; c.ns.profile.raceID = 2
        c.ns.guideLevel = '21-30'
        guides = {g.zone: g for g in c.ns.LevelingGuideChoices().values()}
        self.assertIn('Ashenvale', guides)
        self.assertTrue(guides['Ashenvale'].upcoming)
        self.assertFalse(guides['Ashenvale'].levelReady)
        self.assertNotIn('Mulgore', guides)
        self.assertNotIn('Orgrimmar', guides)
        self.assertTrue(all(c.ns.GuideBracketMatches(g) for g in guides.values()))


if __name__ == '__main__':
    unittest.main()
