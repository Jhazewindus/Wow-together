"""HUD title controls and the secondary Glance renderer."""
import unittest
import re
from pathlib import Path

from test_addon import Client
from test_navigation import navigator


class HudTitleTests(unittest.TestCase):
    def test_title_controls_pause_open_hub_and_hide_without_stopping(self):
        c = navigator(); frame = c.ns.navigation
        guide = c.ns.routeSelection
        frame.close.OnClick()
        self.assertFalse(frame.IsShown(frame))
        self.assertEqual(c.ns.routeSelection.key, guide.key)
        c.ns.OpenGuideWindow()
        self.assertTrue(frame.IsShown(frame))
        frame.menu.OnClick()
        self.assertTrue(c.ns.window.IsShown(c.ns.window))
        self.assertEqual(c.ns.filter, 'recommended')

    def test_arrow_command_restores_a_hidden_hud_without_first_turning_it_off(self):
        c = navigator(); frame = c.ns.navigation
        frame.close.OnClick()
        self.assertTrue(c.ns.guideWindowHidden)
        self.assertTrue(c.ns.Option('routeArrow'))
        c.ns.ToggleNavigation()
        self.assertFalse(c.ns.guideWindowHidden)
        self.assertTrue(c.ns.Option('routeArrow'))
        self.assertTrue(frame.IsShown(frame))

    def test_play_tab_glance_action_opens_the_hud_in_glance_mode(self):
        c = navigator()
        c.ns.SetOption('uiNext', True)
        c.ns.OpenGuideWindow()
        c.ns.window.Hide(c.ns.window)
        c.ns.SetHubTab('Play')
        home = c.ns.ui.home
        self.assertTrue(home.resume.glanceControl.IsShown(home.resume.glanceControl))
        home.resume.glanceControl.OnClick()
        self.assertTrue(c.ns.Option('guideGlance'))
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))

    def test_step_counter_toggles_one_line_glance_and_back(self):
        c = navigator(); frame = c.ns.navigation
        frame.stepButton.OnMouseUp(frame.stepButton, 'LeftButton')
        self.assertTrue(c.ns.Option('guideGlance'))
        self.assertTrue(frame.glance)
        self.assertFalse(frame.context.IsShown(frame.context))
        self.assertFalse(frame.distance.IsShown(frame.distance))
        self.assertTrue(frame.status.text)
        frame.stepButton.OnMouseUp(frame.stepButton, 'LeftButton')
        self.assertFalse(c.ns.Option('guideGlance'))
        self.assertFalse(frame.glance)
        self.assertTrue(frame.status.IsShown(frame.status))

    def test_shared_step_icon_table_has_probed_texture_or_glyph_for_every_kind(self):
        c = navigator()
        symbols = c.ns.STEP_SYMBOLS
        coreKinds = {'accept', 'turnin', 'turninIncomplete', 'kill', 'collect', 'use', 'talk', 'travel',
                     'fly', 'hearth', 'teleport', 'ship', 'party', 'wait', 'farm', 'dungeon'}
        self.assertTrue(coreKinds.issubset(set(symbols.keys())))
        self.assertEqual(coreKinds, set(symbols.keys()))
        for key in coreKinds:
            symbol = symbols[key]
            self.assertTrue(symbol.glyph)
            self.assertIsNotNone(symbol.available)
        self.assertTrue(c.ns.stepIconStatus.startswith('Step icons: '))

    def test_glance_keeps_step_symbol_and_shows_three_rows_without_arrow_overlap(self):
        c = navigator(); frame = c.ns.navigation
        c.ns.selectedRoute = c.lua.table_from({'mapID': 501, 'stops': [
            {'id': 900, 'mapID': 501, 'x': .21, 'y': .27, 'kind': 'a', 'title': 'Pickup quest', 'npcName': 'Deino'},
            {'id': 901, 'mapID': 501, 'x': .22, 'y': .27, 'kind': 'q', 'title': 'Venom', 'label': 'Kill Laughing Sisters', 'action': 'kill', 'quantity': 8},
            {'id': 902, 'mapID': 501, 'x': .23, 'y': .27, 'kind': 'q', 'title': 'Shells', 'label': 'Collect Salt Flat Venom', 'action': 'collect', 'quantity': 5},
        ]}, recursive=True)
        c.ns.UpdateNavigation()
        frame.stepButton.OnMouseUp(frame.stepButton, 'LeftButton')
        self.assertTrue(frame.glance)
        self.assertEqual(frame.icon.width, 20)
        self.assertEqual(frame.icon.point[2], 14)
        self.assertEqual(frame.status.point[2], 42)
        self.assertEqual(frame.symbol.text, '!')
        self.assertEqual(frame.height, 150)
        for line in frame.icon.lines.values():
            self.assertFalse(line.IsShown(line))
        self.assertTrue(frame.glanceRows[1].frame.IsShown(frame.glanceRows[1].frame))
        self.assertTrue(frame.glanceRows[2].frame.IsShown(frame.glanceRows[2].frame))
        self.assertTrue(frame.glanceRows[1].text.text)
        self.assertTrue(frame.glanceRows[2].text.text)
        self.assertNotEqual(frame.glanceRows[1].text.text, frame.glanceRows[2].text.text)
        self.assertNotIn('Work on', frame.glanceRows[1].text.text)
        frame.stepButton.OnMouseUp(frame.stepButton, 'LeftButton')
        c.ns.UpdateNavigation()

    def test_chip_renders_inside_hud_and_moves_to_standalone_when_hud_hides(self):
        c = navigator(); frame = c.ns.navigation
        c.ns.ShowSuggestionChip('dungeon', 'nearby', 'Entrance nearby', c.lua.table_from([
            {'label': 'Open map'}, {'label': 'Not now'}], recursive=True))
        chip = c.ns.suggestionChipFrame
        self.assertTrue(c.lua.eval('rawequal')(chip.GetParent(chip), frame))
        self.assertEqual(chip.height, 30)
        self.assertEqual(frame.height, 198)
        self.assertEqual(chip.actions[1].caption.text, 'Open map')
        self.assertEqual(chip.actions[2].caption.text, 'Not now')
        self.assertGreaterEqual(chip.text.fontHeight, 10)
        self.assertGreaterEqual(chip.actions[1].caption.fontHeight, 10)
        frame.close.OnClick()
        self.assertFalse(frame.IsShown(frame))
        self.assertTrue(c.lua.eval('rawequal')(c.ns.suggestionChipFrame.GetParent(c.ns.suggestionChipFrame), c.lua.globals().UIParent))

    def test_efficiency_menu_is_on_step_counter_and_no_small_full_button_remains(self):
        c = navigator(); frame = c.ns.navigation
        self.assertIsNone(frame.modeButton)
        c.ns.routeSelection.mode = 'zone'
        frame.stepButton.OnMouseUp(frame.stepButton, 'RightButton')
        self.assertTrue(frame.modeMenu.IsShown(frame.modeMenu))
        for label in (frame.title, frame.step, frame.status, frame.context, frame.distance,
                      frame.peek, frame.pause.caption, frame.menu.caption,
                      frame.skipStep.caption, frame.skipQuest.caption,
                      frame.modeMenu.efficient.caption, frame.modeMenu.complete.caption):
            self.assertGreaterEqual(label.fontHeight, 10)

    def test_navigation_lua_uses_only_supported_glyphs(self):
        path = Path(__file__).resolve().parents[1] / 'WowTogether' / 'Navigation.lua'
        source = path.read_text(encoding='utf-8')
        supported = set('·•–—…’')
        invalid = {char for char in source if ord(char) > 255 and char not in supported}
        self.assertEqual(invalid, set())
        self.assertIn('frame.kindIcon:SetVertexColor(unpack(ns.UIColors.text))', source)
        self.assertIn('row.icon:SetVertexColor(unpack(ns.UIColors.muted))', source)
        self.assertIn('row.icon:SetVertexColor(1, 1, 1, 1)', source)
        for signature in ('["travel-fly"] = "fly"', '["travel-hearth"] = "hearth"',
                          '["travel-teleport"] = "teleport"', '["travel-ship"] = "ship"'):
            self.assertIn(signature, source)
        guide_text = path.with_name('GuideText.lua').read_text(encoding='utf-8')
        symbol_table = guide_text.split('local STEP_SYMBOLS = {', 1)[1].split('ns.STEP_SYMBOLS', 1)[0]
        glyphs = re.findall(r'glyph\s*=\s*"([^"]*)"', symbol_table)
        self.assertTrue(glyphs)
        self.assertTrue(all(all(ord(char) < 128 for char in glyph) for glyph in glyphs))

    def test_road_leg_names_objective_place_not_trail_waypoint_or_progress(self):
        c = navigator()
        goal = c.ns.selectedRoute.stops[1]
        goal.objectiveAreaName = 'The Salt Flats'
        leg = c.lua.table_from({'method': 'walk', 'name': 'Path waypoint 0/9',
            'to': {'trail': True, 'name': 'Path waypoint 0/9', 'mapID': 501}}, recursive=True)
        travel = c.lua.table_from({'id': goal.id, 'kind': 'travel', 'title': 'Path waypoint 0/9',
            'label': 'Path waypoint 0/9', 'goal': goal, 'travelLeg': leg}, recursive=True)
        presentation = c.ns.GuideStepPresentation(travel, None, c.ns.routeSelection, c.ns.selectedRoute)
        self.assertEqual(presentation.what, 'Follow the road towards The Salt Flats')
        self.assertNotIn('Path waypoint', presentation.what)
        self.assertNotIn('0/9', presentation.what)
        leg.to.trail = None
        leg.to.terrain = c.lua.table_from({'name': 'Ridge waypoint 2/6'})
        terrain_presentation = c.ns.GuideStepPresentation(travel, None, c.ns.routeSelection, c.ns.selectedRoute)
        self.assertEqual(terrain_presentation.what, 'Follow the road towards The Salt Flats')
        self.assertNotIn('Ridge waypoint', terrain_presentation.what)
        self.assertNotIn('2/6', terrain_presentation.what)

    def test_generated_hud_control_icons_use_the_probed_registry(self):
        c = navigator()
        c.lua.execute(r'''local ns = ...
          ns.StepIconTexture = function(name) return "Generated\\" .. name end
        ''', c.ns)
        c.ns.CreateNavigation()
        frame = c.ns.navigation
        self.assertTrue(frame.pause.hasIcon)
        self.assertTrue(frame.menu.hasIcon)
        self.assertTrue(frame.close.hasIcon)
        self.assertTrue(frame.scan.hasIcon)
        for bar in frame.menu.bars.values(): self.assertFalse(bar.IsShown(bar))
        self.assertEqual(frame.close.caption.text, '')


if __name__ == '__main__':
    unittest.main()
