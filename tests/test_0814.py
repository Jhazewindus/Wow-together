"""Guide background controls and the supplied Durotar research export.

Host-side Lua 5.1 checks; native beta rendering still needs player testing.
"""
import json
import unittest

from test_addon import Client, ROOT
from test_063 import order, primitive, zone
from test_061 import world_quest
from test_routes import catalogue, map_canvas


UI_RECORDER = r'''
local create = CreateFrame
function CreateFrame(...)
    local frame = create(...)
    function frame:SetBackdropColor(...) self.fill = {...} end
    function frame:SetAlpha(alpha) self.frameAlpha = alpha end
    function frame:SetChecked(checked) self.checked = checked end
    function frame:GetChecked() return self.checked end
    return frame
end
GameTooltip = {lines={}}
function GameTooltip:SetOwner(owner) self.owner=owner; self.lines={} end
function GameTooltip:AddLine(text) self.lines[#self.lines+1]=text end
function GameTooltip:Show() self.shown=true end
function GameTooltip:Hide() self.shown=false end
'''


def ui_client(saved=None):
    return Client(quests=(), before_load=UI_RECORDER, saved_variables=saved)


def click(button):
    button.OnClick(button)


class GuideBackgroundTests(unittest.TestCase):
    def test_button_only_changes_fills_while_a_guide_runs_in_combat(self):
        c = ui_client(); c.guide_environment(level=12); map_canvas(c)
        c.lua.globals().grouped = False; c.ns.UpdateRoster()
        catalogue(c, {900: world_quest('One'), 901: world_quest('Two')})
        g = zone(c); c.ns.ActivateRoute(g); before = order(g)
        c.lua.execute('''combat=true
            function forbidden() error('Background toggle changed guide/travel state') end''')
        for name in ('Refresh', 'DrawRoute', 'ResetTravelPath', 'UpdateNPCHints'):
            c.ns[name] = c.lua.globals().forbidden
        nav = c.ns.navigation
        before_text = (nav.status.text, nav.context.text, nav.title.text)
        c.ns.navigationPreview = 2
        c.ns.flightPlanCache = c.lua.table_from({'sentinel': True})
        c.ns.db.guideSkips[c.ns.self].quests[900] = True
        click(nav.background)
        self.assertFalse(c.ns.Option('guideOpaque'))
        for panel in (nav, nav.tip, nav.work):
            self.assertEqual(panel.fill[4], .18)
            self.assertIsNone(panel.frameAlpha)
        self.assertEqual(nav.background.fill[4], .98)  # Controls stay readable.
        self.assertEqual((nav.status.text, nav.context.text, nav.title.text), before_text)
        self.assertEqual(c.ns.navigationPreview, 2)
        self.assertTrue(c.ns.flightPlanCache.sentinel)
        self.assertTrue(c.ns.db.guideSkips[c.ns.self].quests[900])
        self.assertEqual(order(g), before)
        click(nav.background)
        self.assertTrue(c.ns.Option('guideOpaque'))
        for panel in (nav, nav.tip, nav.work): self.assertEqual(panel.fill[4], 1)

    def test_settings_and_button_share_one_persistent_choice(self):
        c = ui_client(); c.ns.ToggleSettings(); nav = c.ns.navigation
        check = c.ns.settings.checks.guideOpaque
        self.assertTrue(check.checked)
        click(nav.background)
        self.assertFalse(check.checked)
        check.SetChecked(check, True); click(check)
        self.assertTrue(c.ns.Option('guideOpaque'))
        self.assertEqual(nav.fill[4], 1)
        click(nav.background)
        fresh = ui_client(primitive(c.ns.db))
        fresh.ns.ToggleSettings()
        self.assertFalse(fresh.ns.Option('guideOpaque'))
        self.assertFalse(fresh.ns.settings.checks.guideOpaque.checked)
        self.assertEqual(fresh.ns.navigation.fill[4], .18)
        fresh.ns.UpdateNavigation()
        self.assertEqual(fresh.ns.navigation.fill[4], .18)

    def test_small_button_explains_current_state_and_next_action(self):
        c = ui_client(); nav = c.ns.navigation; button = nav.background
        self.assertEqual(nav.width, 360); self.assertEqual(nav.height, 168)
        self.assertEqual(button.caption.text, 'BG')
        self.assertLessEqual(14 + nav.title.width, nav.width - 10 - button.width)
        self.assertEqual(button.caption.fontFlags, '')
        button.OnEnter(button)
        self.assertEqual(c.lua.globals().GameTooltip.lines[1],
                         'Guide background: opaque. Click for see-through.')
        click(button); button.OnEnter(button)
        self.assertEqual(c.lua.globals().GameTooltip.lines[1],
                         'Guide background: see-through. Click for opaque.')


RESEARCH_FILE = ROOT / 'research/2026-10-06-durotar-orc-rogue-build-70235.json'


def research_client():
    return Client(quests=(), use_catalogue=True, before_load='''
        grouped=false; peer=nil
        function GetBuildInfo() return '1.60.1','70235','test',16001 end
        function UnitLevel() return 1 end
        function UnitFactionGroup() return 'Horde' end
        function UnitClass() return 'Rogue','ROGUE',4 end
        function UnitRace() return 'Orc','Orc',2 end
        npcID=3143
        function UnitGUID() return 'Creature-0-1-2-3-'..npcID..'-ABC' end
        C_Map={GetBestMapForUnit=function() return 1411 end}
    ''')


class SuppliedResearchTests(unittest.TestCase):
    def test_real_stale_snapshots_do_not_invent_a_learned_prerequisite(self):
        c = research_client()
        records = json.loads(RESEARCH_FILE.read_text())['events']
        for record in records:
            c.ns.ObserveQuestLearning(c.lua.table_from(record, recursive=True),
                                     'Anonymous supplied export')
        self.assertEqual(list(c.ns.db.questLearning.rules.keys()), [])
        self.assertIsNone(c.ns.LearnedQuestRule(788))
        self.assertIsNone(c.ns.LearnedQuestRule(97279))
        self.assertEqual(list(c.ns.CataloguePrerequisiteIDs(789).values()), [788])

    def test_positive_offers_match_shipped_givers_and_pickup_eligibility(self):
        c = research_client()
        records = json.loads(RESEARCH_FILE.read_text())['events']
        pairs = {(e['npcID'], q) for e in records if e['event'] == 'offers'
                 for q in e['offered']}
        self.assertEqual(pairs, {(10176, 4641), (3143, 788), (3143, 97279)})
        for npc, quest in pairs:
            with self.subTest(npc=npc, quest=quest):
                c.ns.InvalidateNPCOffers()
                self.assertIn(npc, {p.entityID for p in c.ns.CatalogueQuest(quest).starts.values()})
                c.lua.globals().npcID = npc
                c.ns.RecordNPCOfferAvailability(
                    c.lua.table_from([{'questID': quest}], recursive=True), False)
                self.assertTrue(c.ns.ObservedPickupAvailable(quest))
                self.assertTrue(c.ns.CatalogueAllowed(quest, c.ns.profile, c.ns.self))
        self.assertFalse(c.ns.Completed(787))  # New Horde is not a mandatory parent.

    def test_missing_scorpid_offer_does_not_remove_its_existing_parent(self):
        c = research_client()
        allowed, reason = c.ns.CatalogueAllowed(789, c.ns.profile, c.ns.self)
        self.assertFalse(allowed); self.assertIn('Cutting Teeth', reason)
        c.lua.globals().finished[788] = True; c.ns.ForgetQuestCompletion(788)
        self.assertTrue(c.ns.CatalogueAllowed(789, c.ns.profile, c.ns.self))


if __name__ == '__main__':
    unittest.main()
