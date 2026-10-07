"""Crafting refresh, strict mob hints and player choice for elite guides."""
import unittest

from test_addon import Client
from test_063 import guide_client, zone, order
from test_routes import guide
from test_0836 import crafting
from test_0837 import leatherworking
from test_071 import giver_client


def cured_hide(skill=31):
    c = crafting(skill=skill)
    c.lua.globals().testNS = c.ns
    c.lua.execute('''
    local facts=testNS.ProfessionFacts(165)
    for _,recipe in ipairs(facts.recipes) do
      if recipe.id==3816 then facts.recipes={recipe};break end
    end
    function GetProfessionInfo() return 'Leatherworking','icon',pskill,pmaximum,10,0,165 end
    C_TradeSkillUI.GetChildProfessionInfo=function()
      return {professionID=165,professionName='Leatherworking',skillLevel=pskill,maxSkillLevel=pmaximum} end
    C_TradeSkillUI.GetAllRecipeIDs=function() return {3816} end
    C_TradeSkillUI.GetRecipeInfo=function()
      return {name='Cured Light Hide',learned=true,canSkillUp=true,relativeDifficulty=40} end
    C_TradeSkillUI.GetRecipeSchematic=function()
      return {reagentSlotSchematics={
        {required=true,quantityRequired=1,reagents={{itemID=783}}},
        {required=true,quantityRequired=1,reagents={{itemID=4289}}}}} end
    C_Item.GetItemInfo=function(id) return id==783 and 'Light Hide' or 'Salt' end
    ''')
    c.ns.ReadProfessionSkills(); c.ns.ReadProfessionRecipes()
    return c


class ProfessionRefreshTests(unittest.TestCase):
    def test_cured_hide_at_31_is_material_work_and_shows_crafts_before_buying(self):
        c = cured_hide(); c.ns.StartProfessionGuide(165, 75)
        route = c.ns.selectedRoute
        self.assertEqual(route.recipe.name, 'Cured Light Hide')
        self.assertEqual(route.stops[1].action, 'buy')
        self.assertIn('~19 × Cured Light Hide', route.stops[1].description)
        self.assertEqual({r.itemID:r.need for r in route.materials.values()}, {783:19, 4289:19})
        c.lua.globals().stock[783] = 19; c.lua.globals().stock[4289] = 19
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'craft')
        c.lua.globals().pskill = 32
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertEqual(c.ns.selectedRoute.crafts, 18)
        self.assertNotIn('Learn Cured', c.ns.selectedRoute.stops[1].label)

    def test_empty_and_unreadable_lists_preserve_confirmed_learned_recipe(self):
        c = cured_hide()
        for body in ('return {}', 'return {3816}'):
            c.ns.professionData[165].recipeRefreshPending = True
            c.lua.execute('C_TradeSkillUI.GetAllRecipeIDs=function() '+body+' end; C_TradeSkillUI.GetRecipeInfo=function() return nil end')
            c.ns.ReadProfessionRecipes()
            self.assertTrue(c.ns.professionData[165].known[3816].learned)
            self.assertTrue(c.ns.professionData[165].recipeRefreshPending)
            self.assertTrue(c.ns.professionSaved.skills[165].known[3816])

    def test_partial_read_retains_positive_knowledge_and_refresh_request(self):
        c = crafting()
        c.ns.professionData[171].recipeRefreshPending = True
        c.lua.execute('''C_TradeSkillUI.GetRecipeInfo=function(id)
          if id~=1 then return {name='Recipe '..id,learned=false,canSkillUp=true,relativeDifficulty=40} end end''')
        c.ns.ReadProfessionRecipes()
        self.assertTrue(c.ns.professionData[171].known[1].learned)
        self.assertTrue(c.ns.professionData[171].recipeRefreshPending)
        self.assertIsNone(c.ns.professionData[171].known[1].difficulty)

    def test_trainer_update_with_closed_book_requests_refresh_then_accepts_new_recipe(self):
        c = crafting(skill=26)
        c.lua.globals().color = 70
        c.lua.execute('''C_TradeSkillUI.GetRecipeInfo=function(id)
          return {name='Recipe '..id,learned=learned[id] or false,canSkillUp=id~=1,relativeDifficulty=id==1 and 70 or 40} end''')
        c.ns.ReadProfessionRecipes(); c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'train')
        c.ns.handlers.TRADE_SKILL_CLOSE()
        c.lua.globals().learned[2] = True
        c.ns.handlers.TRAINER_UPDATE(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'read')
        self.assertIn('Open your Alchemy window', c.ns.selectedRoute.stops[1].label)
        c.ns.handlers.TRADE_SKILL_SHOW(); c.drain()
        self.assertTrue(c.ns.professionData[171].known[2].learned)
        self.assertFalse(c.ns.professionData[171].recipeRefreshPending)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'buy')

    def test_native_preparation_reagents_override_reference_and_deduct_stock_once(self):
        c = leatherworking(skill=20)
        c.lua.globals().stock[2318] = 1; c.lua.globals().stock[2934] = 5
        c.lua.execute('''C_TradeSkillUI.GetRecipeSchematic=function(id)
          return {reagentSlotSchematics={{required=true,quantityRequired=id==2881 and 5 or 2,
          reagents={{itemID=id==2881 and 2934 or 2318}}}}} end''')
        recipe = next(r for r in c.ns.ProfessionFacts(165).recipes.values() if r.id == 2152)
        rows, cost, prep, incomplete = c.ns.ProfessionMaterials(165, recipe, 2, 20, True)
        mats = {r.itemID:r for r in rows.values()}
        self.assertFalse(incomplete)
        self.assertEqual(prep[1].crafts, 3)
        self.assertEqual(mats[2934].need, 15)
        self.assertEqual(mats[2934].missing, 10)

    def test_start_scan_opens_only_on_click_and_waits_for_real_recipe_event(self):
        c = cured_hide(); c.ns.handlers.TRADE_SKILL_CLOSE()
        c.lua.execute('openCalls=0; C_TradeSkillUI.OpenTradeSkill=function(id) openCalls=openCalls+1;openedID=id;return true end')
        c.ns.StartProfessionGuide(165, 75)
        prompt = c.ns.professionScanPrompt
        self.assertTrue(prompt.IsShown(prompt))
        self.assertEqual(c.lua.globals().openCalls, 0)
        prompt.scan.OnClick()
        self.assertEqual(c.lua.globals().openedID, 165)
        self.assertEqual(c.lua.globals().openCalls, 1)
        self.assertFalse(c.ns.professionWindowOpen)
        self.assertTrue(c.ns.professionData[165].recipeRefreshPending)
        c.ns.handlers.TRADE_SKILL_SHOW(); c.drain()
        self.assertFalse(prompt.IsShown(prompt))
        self.assertFalse(c.ns.professionData[165].recipeRefreshPending)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'buy')

    def test_scan_opener_missing_failed_secret_or_combat_keeps_manual_fallback(self):
        for implementation in ('nil', 'function() return false end', 'function() return secret end',
                               'function() error("unsupported") end'):
            with self.subTest(implementation=implementation):
                c = cured_hide(); c.ns.handlers.TRADE_SKILL_CLOSE()
                c.lua.execute('C_TradeSkillUI.OpenTradeSkill='+implementation)
                c.ns.StartProfessionGuide(165, 75)
                prompt = c.ns.professionScanPrompt; prompt.scan.OnClick()
                self.assertTrue(prompt.IsShown(prompt))
                self.assertIn('Open your Leatherworking window', prompt.text.text)
        c = cured_hide(); c.ns.handlers.TRADE_SKILL_CLOSE()
        c.lua.execute('C_TradeSkillUI.OpenTradeSkill=function() error("called in combat") end')
        c.ns.StartProfessionGuide(165, 75); c.lua.globals().combat = True
        c.ns.professionScanPrompt.scan.OnClick()
        self.assertIn('out of combat', c.ns.professionScanPrompt.text.text)

    def test_existing_open_book_scans_without_popup_and_later_preserves_guide(self):
        c = cured_hide(); c.ns.StartProfessionGuide(165, 75)
        self.assertIsNone(c.ns.professionScanPrompt)
        c.ns.handlers.TRADE_SKILL_CLOSE(); c.ns.StartProfessionGuide(165, 75)
        prompt = c.ns.professionScanPrompt; prompt.later.OnClick()
        self.assertFalse(prompt.IsShown(prompt))
        self.assertEqual(c.ns.routeSelection.professionID, 165)

    def test_popup_from_previous_profession_cannot_open_after_switching_guides(self):
        c = cured_hide(); c.ns.handlers.TRADE_SKILL_CLOSE()
        c.ns.StartProfessionGuide(165, 75)
        c.lua.execute('C_TradeSkillUI.OpenTradeSkill=function() error("stale popup opened") end')
        c.ns.routeSelection.mode = 'zone'
        c.ns.professionScanPrompt.scan.OnClick()
        self.assertFalse(c.ns.professionScanPrompt.IsShown(c.ns.professionScanPrompt))


class StrictMobMarkerTests(unittest.TestCase):
    def test_drop_starter_is_unmarked_until_its_objective_is_in_an_active_quest(self):
        c = giver_client()
        for quest in c.ns.catalogue.quests.values():
            quest.starts[1].action = 'start-item'
            quest.objectives[1].entityID = 123
            quest.objectives[1].npc = True
            quest.objectives[1].name = 'Quest enemy'
        c.lua.execute('C_QuestLog.UnitIsRelatedToActiveQuest=function() return true end')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)
        c.ns.active[900] = 'Accepted quest'
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 1)
        self.assertEqual(c.ns.npcHints['nameplate1'].target.kind, 'q')
        c.ns.active[900] = None
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)

    def test_unknown_enemy_is_unmarked_even_when_generic_native_flag_is_true(self):
        c = giver_client(); c.ns.active[900] = 'Accepted quest'
        c.lua.execute('''function UnitGUID() return 'Creature-0-1-2-3-999-ABC' end
          C_QuestLog.UnitIsRelatedToActiveQuest=function() return true end''')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)


class GroupQuestGuideTests(unittest.TestCase):
    def test_fixed_and_adaptive_guides_keep_elite_and_raid_work_while_solo(self):
        for kind in ('Elite', 'Raid'):
            for fixed in (True, False):
                with self.subTest(kind=kind, fixed=fixed):
                    c = guide_client(2)
                    c.ns.db.config.fixedZoneGuides = fixed
                    for q in c.ns.catalogue.quests.values(): q.questType = kind
                    g = zone(c)
                    route = c.ns.BuildGuideRoute(g, False)
                    self.assertEqual({s.id for s in route.stops.values()}, {900, 901})
                    self.assertEqual({s.kind for s in route.stops.values()}, {'a', 'q', 't'})
                    self.assertTrue(c.ns.LevelingQuestEnabled(900))
                    self.assertIn(kind + ' quest:', c.ns.RouteContext(route.stops[1], 501))
                    self.assertIn('Skip quest', c.ns.GuideStepDescription(route.stops[1]))

    def test_group_flag_does_not_bypass_level_faction_or_prerequisite_checks(self):
        c = guide_client(2)
        q = c.ns.catalogue.quests[900]; q.questType = 'Elite'
        q.level = 30
        self.assertFalse(c.ns.LevelingValue(900)[0])
        q.level = 12; q.side = 'Alliance'
        self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        q.side = 'Horde'; q.previousQuest = 901
        self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        q.previousQuest = None; q.questType = 'Normal'
        self.assertIsNone(c.ns.QuestGroupWarning(900))

    def test_quest_list_labels_difficulty_separately_from_availability_and_level(self):
        c = guide_client(2)
        c.ns.catalogue.quests[900].questType = 'Elite'
        c.ns.ShowGuideQuestList(zone(c)); c.drain()
        row = next(r for r in c.ns.guideQuestList.rows.values() if r.stop.id == 900 and r.stop.kind == 'a')
        self.assertIn('Elite', row.state.text)
        self.assertIn('Available', row.state.text)
        self.assertNotIn('Needs a party', row.state.text)
        c.ns.catalogue.quests[900].level = 30
        c.ns.RenderGuideQuestList()
        self.assertIn('Outside level range', row.state.text)

    def test_skip_is_only_explicit_and_scan_preserves_skip_without_completion_credit(self):
        c = guide_client(2)
        for q in c.ns.catalogue.quests.values(): q.questType = 'Elite'
        g = zone(c); c.ns.ActivateRoute(g); before = order(g)
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        c.ns.SkipGuide('quest')
        self.assertTrue(c.ns.GuideQuestSkipped(900))
        c.ns.ScanGuideProgress(g, True); c.drain()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {901})
        self.assertEqual(order(g), before)
        self.assertFalse(c.ns.Completed(900))
        c.ns.ResetGuideSkips()
        self.assertIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})

    def test_real_big_picture_is_runnable_after_its_prerequisite_while_solo(self):
        c = Client(quests=(), completed=(91745,), use_catalogue=True)
        c.guide_environment(level=3)
        c.lua.globals().grouped = False
        c.ns.UpdateRoster(); c.ns.ReadProfile()
        c.ns.profile.faction, c.ns.profile.mapID = 'Alliance', 1429
        c.ns.profile.raceID, c.ns.profile.classID = 1, 1
        self.assertEqual(c.ns.CatalogueQuest(91752).title, 'The Big Picture')
        self.assertEqual(c.ns.CatalogueQuest(91752).questType, 'Elite')
        self.assertTrue(c.ns.LevelingQuestEnabled(91752))
        selected = guide(c, (91752,))
        route = c.ns.BuildGuideRoute(selected, False)
        self.assertIn(91752, {s.id for s in route.stops.values()})
        self.assertIn('bring a party', c.ns.RouteContext(route.stops[1], 1429))


if __name__ == '__main__': unittest.main()
