"""Card previews never replace a running guide before explicit Start route."""
import unittest

from test_063 import guide_client, zone, order
from test_061 import run_plan
from test_0811 import browser, future
from test_073 import travel_client


class GuidePreviewTests(unittest.TestCase):
    def test_loading_closed_and_replaced_previews_cannot_start_stale_guide(self):
        c = browser(); c.ns.ui.cards[1].OnClick()
        frame = c.ns.guideQuestList
        self.assertFalse(frame.start.IsEnabled(frame.start))
        frame.start.OnClick(); self.assertIsNone(c.ns.routeSelection)
        frame.Hide(frame); frame.start.OnClick(); c.drain()
        self.assertIsNone(c.ns.routeSelection)
        self.assertIsNone(frame.plan)
        c.ns.SetGuideLevel('21-30'); c.ns.ui.cards[1].OnClick()
        c.drain()
        self.assertEqual({s.id for s in frame.plan.values()}, {910, 911})
        self.assertEqual(frame.startGuide.key, future(c).key)
        self.assertIsNone(c.ns.routeSelection)

    def test_start_uses_the_previewed_order_and_closes_preview(self):
        c = guide_client(4); c.ns.SetFilter('guides')
        c.ns.ui.cards[1].OnClick(); c.drain()
        frame = c.ns.guideQuestList
        expected = order(frame.startGuide)
        self.assertIsNone(c.ns.routeSelection)
        frame.start.OnClick(); run_plan(c)
        self.assertFalse(frame.IsShown(frame))
        self.assertEqual(order(c.ns.routeSelection), expected)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901, 902, 903})

    def test_future_preview_start_keeps_current_guide_until_warning_accepted(self):
        c = browser(); current = zone(c)
        c.ns.ShowGuideOnMap(current); run_plan(c); expected = order(current)
        c.ns.SetGuideLevel('21-30'); c.ns.ui.cards[1].OnClick(); c.drain()
        frame = c.ns.guideQuestList
        frame.start.OnClick()
        self.assertTrue(c.ns.earlyGuidePrompt.IsShown(c.ns.earlyGuidePrompt))
        self.assertFalse(frame.IsShown(frame))
        self.assertEqual(c.ns.routeSelection.key, current.key)
        self.assertEqual(order(c.ns.routeSelection), expected)
        c.ns.earlyGuidePrompt.cancel.OnClick()
        self.assertEqual(order(c.ns.routeSelection), expected)

    def test_popup_start_preserves_include_current_quests_choice(self):
        c = guide_client(2); c.ns.active[900] = 'Quest 0'; c.ns.SetFilter('guides')
        c.ns.ui.cards[1].OnClick(); c.drain(); c.ns.guideQuestList.start.OnClick()
        self.assertTrue(c.ns.startGuidePrompt.IsShown(c.ns.startGuidePrompt))
        self.assertIsNone(c.ns.routeSelection)
        c.ns.startGuidePrompt.selected.OnClick(); run_plan(c)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})

    def test_card_recycling_and_resize_keep_preview_read_only(self):
        c = browser(); c.ns.ui.cards[1].OnClick(); c.drain()
        frame = c.ns.guideQuestList; expected = order(frame.startGuide)
        failure = c.lua.eval('function() error("resize must not generate a guide") end')
        c.ns.GenerateFixedGuide = failure
        frame.grip.OnMouseDown(frame.grip, 'LeftButton')
        frame.SetSize(frame, 580, 410); frame.OnSizeChanged()
        c.ns.handlers.GLOBAL_MOUSE_UP('LeftButton')
        self.assertEqual(order(frame.startGuide), expected)
        self.assertIsNone(c.ns.routeSelection)
        c.ns.SetFilter('library'); card = c.ns.ui.cards[1]
        self.assertTrue(card.count.IsShown(card.count))
        c.ns.SetFilter('guides')
        self.assertFalse(card.count.IsShown(card.count))
        self.assertFalse(card.detailsButton.IsShown(card.detailsButton))

    def test_travel_card_previews_without_navigation_then_starts_normally(self):
        c = travel_client(); c.ns.guideSearch = 'orgrimmar'; c.ns.SetFilter('guides')
        c.ns.ui.cards[1].OnClick(); frame = c.ns.guideQuestList
        self.assertIsNone(c.ns.routeSelection)
        self.assertEqual(len(frame.plan), 0)
        self.assertIn('Orgrimmar', frame.empty.text)
        frame.start.OnClick(); run_plan(c)
        self.assertEqual(c.ns.routeSelection.key, 'travel:orgrimmar')
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .115)


if __name__ == '__main__': unittest.main()
