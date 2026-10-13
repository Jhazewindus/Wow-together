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
    def test_navigation_hover_deduplicates_context_and_omits_drag_prompt(self):
        c = navigator()
        game_tooltip = tooltip(c)
        c.ns.GuideStepDescription = lambda *_: "Accept Quest\nCollect Quest before entering Hall\nIronforge • 33.0, 48.0"
        c.ns.navigation.context.SetText(c.ns.navigation.context,
            "Collect Quest before entering Hall\nIronforge • 33.0, 48.0")

        c.ns.navigation.OnEnter(c.ns.navigation)
        text = "\n".join(game_tooltip.lines.values())
        self.assertEqual(text.count("Collect Quest before entering Hall"), 1)
        self.assertEqual(text.count("Ironforge • 33.0, 48.0"), 1)
        self.assertNotIn("Drag to move", text)

    def test_standalone_arrow_hover_deduplicates_route_tip_and_omits_drag_prompt(self):
        c = navigator()
        game_tooltip = tooltip(c)
        frame = c.ns.standaloneNavigation
        c.ns.GuideStepDescription = lambda *_: "Accept Quest\nCollect Quest before entering Hall\nIronforge • 33.0, 48.0"
        frame.guideTip = c.lua.table_from({'detail': 'Collect Quest before entering Hall\nIronforge • 33.0, 48.0'})

        frame.OnEnter(frame)
        text = "\n".join(game_tooltip.lines.values())
        self.assertEqual(text.count("Collect Quest before entering Hall"), 1)
        self.assertEqual(text.count("Ironforge • 33.0, 48.0"), 1)
        self.assertNotIn("Drag to move", text)
        self.assertIsNone(c.lua.eval('rawget')(c.ns.navigation.tip, 'OnEnter'))
        self.assertIsNone(c.lua.eval('rawget')(frame.tip, 'OnEnter'))


if __name__ == '__main__':
    unittest.main()
