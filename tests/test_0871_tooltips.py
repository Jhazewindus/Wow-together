"""Guide arrow hover text removes duplicate lines and generic prompts."""
import unittest

from test_navigation import navigator


def tooltip(c):
    c.lua.execute('''GameTooltip={lines={}}
      function GameTooltip:SetOwner(owner) self.owner=owner;self.lines={} end
      function GameTooltip:IsOwned(owner) return self.owner==owner end
      function GameTooltip:ClearLines() self.lines={} end
      function GameTooltip:AddLine(text) self.lines[#self.lines+1]=text end
      function GameTooltip:Show() self.shown=true end
      function GameTooltip:Hide() self.shown=false;self.owner=nil end''')
    return c.lua.globals().GameTooltip


class GuideTooltipTests(unittest.TestCase):
    def test_navigation_hover_uses_only_fields_not_already_shown_on_card(self):
        c = navigator()
        game_tooltip = tooltip(c)
        c.lua.execute('''local ns = ...
          ns.GuideStepPresentation = function() return {title='Quest',what='Accept Quest',why='Collect Quest before entering Hall',
            status='Required',location='Ironforge • 33.0, 48.0',details={'Collect Quest before entering Hall','Ironforge • 33.0, 48.0'}} end''', c.ns)
        c.ns.navigation.presentation = None

        c.ns.navigation.OnEnter(c.ns.navigation)
        text = "\n".join(game_tooltip.lines.values())
        self.assertEqual(text.count("Collect Quest before entering Hall"), 0)
        self.assertEqual(text.count("Ironforge • 33.0, 48.0"), 1)
        self.assertNotIn("Drag to move", text)

    def test_standalone_arrow_tooltip_includes_why_and_deduplicates_fields(self):
        c = navigator()
        game_tooltip = tooltip(c)
        frame = c.ns.standaloneNavigation
        c.lua.execute('''local ns = ...
          ns.GuideStepPresentation = function() return {title='Quest',what='Accept Quest',why='Collect Quest before entering Hall',
            status='Required',location='Ironforge • 33.0, 48.0',details={'Collect Quest before entering Hall','Ironforge • 33.0, 48.0'}} end''', c.ns)

        frame.OnEnter(frame)
        text = "\n".join(game_tooltip.lines.values())
        self.assertEqual(text.count("Collect Quest before entering Hall"), 1)
        self.assertEqual(text.count("Ironforge • 33.0, 48.0"), 1)
        self.assertIsNone(c.lua.eval('rawget')(c.ns.navigation.tip, 'OnEnter'))
        self.assertIsNone(c.lua.eval('rawget')(frame.tip, 'OnEnter'))


if __name__ == '__main__':
    unittest.main()
