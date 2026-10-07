"""Craft estimates follow actual skill, including failed gains and bag changes."""
import unittest
from test_0836 import crafting
from test_addon import Client


def leatherworking(skill=1):
    c = crafting(skill=skill)
    c.lua.execute('''
    function GetProfessionInfo() return 'Leatherworking','icon',pskill,pmaximum,10,0,165 end
    C_Item.GetItemInfo=function(id) return ({[2318]='Light Leather',[2934]='Ruined Leather Scraps',[2304]='Light Armor Kit'})[id] end
    C_TradeSkillUI.GetChildProfessionInfo=function()
      return {professionID=165,professionName='Leatherworking',skillLevel=pskill,maxSkillLevel=pmaximum} end
    C_TradeSkillUI.GetAllRecipeIDs=function() return {2881,2152} end
    leatherGains=true
    C_TradeSkillUI.GetRecipeInfo=function(id)
      return {name=id==2881 and 'Light Leather' or 'Light Armor Kit',learned=true,
        canSkillUp=id~=2881 or leatherGains,relativeDifficulty=id==2881 and not leatherGains and 70 or 40} end
    C_TradeSkillUI.GetRecipeSchematic=function(id)
      return {reagentSlotSchematics={{required=true,quantityRequired=id==2881 and 3 or 1,
        reagents={{itemID=id==2881 and 2934 or 2318}}}}} end
    ''')
    c.ns.ReadProfessionSkills(); c.ns.ReadProfessionRecipes()
    return c


def success(c, recipe, sequence, skill=None):
    if skill is not None: c.lua.globals().pskill = skill
    c.ns.handlers.UNIT_SPELLCAST_SUCCEEDED('player', f'Craft-{sequence}', recipe)
    c.drain()


class CraftBatchTests(unittest.TestCase):
    def test_failed_gain_while_gathering_does_not_reduce_the_skill_gap(self):
        c = crafting()
        c.lua.globals().stock[100] = 2
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'craft')
        self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 1)
        c.lua.globals().stock[100] = 0
        success(c, 1, 1)  # Player crafts the one affordable item without a skill gain.
        self.assertEqual(c.ns.selectedRoute.crafts, 5)
        self.assertEqual(c.ns.selectedRoute.materials[1].need, 10)
        self.assertEqual(c.ns.professionData[171].skill, 20)

    def test_guide_chooses_quantity_and_retired_settings_cannot_override_it(self):
        c = crafting()
        c.lua.execute('WowTogetherDB.config.professionBatch=20')
        c.ns.InitializeConfig()
        self.assertIsNone(c.ns.Option('professionBatch'))
        self.assertIsNone(c.ns.settings.pages.professions)
        self.assertIsNone(c.ns.settings.dropdowns.professionBatch)
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.crafts, 5)
        c.lua.globals().color = 50
        c.ns.handlers.TRADE_SKILL_LIST_UPDATE(); c.drain()
        self.assertEqual(c.ns.selectedRoute.crafts, 8)
        c.lua.globals().color = 60
        c.ns.handlers.TRADE_SKILL_LIST_UPDATE(); c.drain()
        self.assertEqual(c.ns.selectedRoute.crafts, 20)
        saved = c.ns.db.guideState[c.ns.self]
        self.assertGreaterEqual(saved.guide.professionBatch.total, 20)
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_main_menu_has_requested_order_and_switches_views(self):
        c = crafting()
        menu = c.ns.ui.viewChoice
        self.assertEqual(len(menu.entries), 6)
        expected = [('recommended', 'Recommended'), ('guides', 'Leveling'), ('professions', 'Professions'), ('dungeons', 'Dungeons'),
                    ('review', 'Quest log'), ('library', 'All quests')]
        for i, (key, title) in enumerate(expected, 1):
            self.assertEqual(menu.entries[i][1], key)
            self.assertEqual(menu.entries[i][2], title)
            menu.options[key].OnClick()
            self.assertEqual(c.ns.filter, key)
            self.assertEqual(menu.caption.text, title)

    def test_unavailable_craft_event_keeps_actual_skill_progress_working(self):
        c = Client(quests=(), before_load='unsupportedEvents={UNIT_SPELLCAST_SUCCEEDED=true}')
        c.guide_environment(level=25)
        c.lua.execute('''
        pskill=11
        function GetProfessions() return 1,nil end
        function GetProfessionInfo() return 'Alchemy','icon',pskill,75,10,0,171 end
        ''')
        c.ns.ReadProfile(); c.ns.ReadProfessionSkills()
        c.ns.StartProfessionGuide(171, 75)
        self.assertFalse(c.ns.professionCraftEventReady)
        self.assertIsNone(c.ns.handlers.UNIT_SPELLCAST_SUCCEEDED)
        self.assertFalse(c.ns.selectedRoute.complete)
        c.lua.globals().pskill = 75
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertEqual(c.ns.professionData[171].skill, 75)
        self.assertTrue(c.ns.selectedRoute.complete)

    def test_remaining_batch_logic_applies_to_all_six_crafting_professions(self):
        for profession in (171, 164, 333, 202, 165, 197):
            with self.subTest(profession=profession):
                c = crafting(skill=11)
                c.lua.globals().craftingID = profession
                c.lua.globals().professionTestNS = c.ns
                c.lua.execute('''
                local facts=professionTestNS.ProfessionFacts(craftingID)
                local recipes={}
                for _, r in ipairs(facts.recipes) do recipes[r.id]=r end
                function GetProfessionInfo() return facts.name,'icon',pskill,pmaximum,10,0,craftingID end
                C_Item.GetItemCount=function(id) return stock[id] or 1000 end
                C_TradeSkillUI.GetChildProfessionInfo=function()
                  return {professionID=craftingID,professionName=facts.name,skillLevel=pskill,maxSkillLevel=pmaximum} end
                C_TradeSkillUI.GetAllRecipeIDs=function()
                  local ids={}; for _,r in ipairs(facts.recipes) do
                    if r.learn and r.learn<=pskill and (r.source=='start' or r.source=='trainer') then ids[#ids+1]=r.id end
                  end; return ids end
                C_TradeSkillUI.GetRecipeInfo=function(id) return {name=recipes[id].name,learned=true,
                  canSkillUp=not string.match(recipes[id].name,'^Runed .* Rod$'),relativeDifficulty=50} end
                C_TradeSkillUI.GetRecipeSchematic=function(id)
                  local slots={}; for _,mat in ipairs(recipes[id].materials) do
                    slots[#slots+1]={required=true,quantityRequired=mat[2],reagents={{itemID=mat[1]}}}
                  end; return {reagentSlotSchematics=slots} end
                ''')
                c.ns.ReadProfessionSkills(); c.ns.ReadProfessionRecipes()
                c.ns.StartProfessionGuide(profession, 75)
                route = c.ns.selectedRoute
                self.assertEqual(route.stops[1].action, 'craft')
                initial, recipe = route.crafts, route.recipe.id
                self.assertGreater(initial, 1)
                success(c, recipe, 1)  # A successful craft with no skill point.
                self.assertEqual(c.ns.selectedRoute.recipe.id, recipe)
                self.assertEqual(c.ns.selectedRoute.crafts, initial)
                self.assertEqual(c.ns.professionData[profession].skill, 11)
                self.assertFalse(c.ns.selectedRoute.complete)

    def test_leather_then_kits_skill_11_continues_from_current_skill(self):
        c = leatherworking()
        stock = c.lua.globals().stock
        stock[2934] = 15
        c.ns.StartProfessionGuide(165, 75)
        self.assertEqual(c.ns.selectedRoute.recipe.id, 2881)
        self.assertEqual(c.ns.selectedRoute.crafts, 14)
        for i in range(1, 6):
            stock[2934], stock[2318] = 15 - i * 3, i
            # The player manually makes leather, even after fresh leather stock
            # makes kits the next efficient recommendation.
            c.lua.globals().pskill = i + 1
            c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
            self.assertEqual(c.ns.selectedRoute.recipe.id, 2152)
            self.assertEqual(c.ns.selectedRoute.crafts, 14 - i)
        self.assertEqual(c.ns.selectedRoute.recipe.id, 2152)
        for i in range(1, 6):
            stock[2318], stock[2304] = 5 - i, i
            success(c, 2152, 5 + i, 6 + i)
        self.assertEqual(c.ns.professionData[165].skill, 11)
        self.assertEqual(c.ns.selectedRoute.crafts, 4)
        self.assertEqual(c.ns.selectedRoute.skillTarget, 15)
        self.assertIn('Skill 11', c.ns.selectedRoute.stops[1].description)
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_consumed_intermediates_are_not_requested_again_mid_batch(self):
        c = leatherworking(skill=20)
        c.lua.globals().leatherGains = False
        c.ns.ReadProfessionRecipes()
        stock = c.lua.globals().stock
        stock[2934] = 15
        c.ns.StartProfessionGuide(165, 75)
        self.assertEqual(c.ns.selectedRoute.recipe.id, 2152)
        self.assertEqual(c.ns.selectedRoute.stops[1].craftRecipeID, 2881)
        for i in range(1, 6):
            stock[2934], stock[2318] = 15 - i * 3, i
            success(c, 2881, i)
        self.assertEqual(c.ns.selectedRoute.stops[1].craftRecipeID, 2152)
        self.assertEqual(c.ns.selectedRoute.crafts, 5)
        for i in range(1, 4):
            stock[2318], stock[2304] = 5 - i, i
            success(c, 2152, 5 + i, 20 + i)
            self.assertEqual(c.ns.selectedRoute.crafts, 5 - i)
            self.assertEqual(len(c.ns.selectedRoute.preparations), 0)
            self.assertEqual(c.ns.selectedRoute.stops[1].action, 'craft')
        self.assertEqual(c.ns.professionData[165].skill, 23)

    def test_no_skill_gain_does_not_finish_stage_or_goal(self):
        c = crafting(skill=74)
        c.lua.globals().stock[100] = 20
        c.ns.StartProfessionGuide(171, 75)
        for i in range(1, 4):
            success(c, 1, i)
            self.assertFalse(c.ns.selectedRoute.complete)
            self.assertEqual(c.ns.selectedRoute.skillTarget, 75)
            self.assertEqual(c.ns.selectedRoute.crafts, 1)
            self.assertEqual(c.ns.professionData[171].skill, 74)
        success(c, 1, 4, 75)
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertIsNone(c.ns.routeSelection.professionBatch)

    def test_bag_events_and_viewers_preserve_partially_finished_batch(self):
        c = leatherworking()
        c.lua.globals().stock[2934] = 30
        c.ns.StartProfessionGuide(165, 75)
        c.lua.globals().stock[2934] = 27
        c.lua.globals().stock[2318] = 1
        success(c, 2881, 1, 2)
        for _ in range(4):
            c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
            self.assertEqual(c.ns.selectedRoute.crafts, 13)
            self.assertEqual(c.ns.selectedRoute.recipe.id, 2152)
        c.ns.ShowProfessionViewer(165); c.drain()
        self.assertEqual(c.ns.professionViewer.route.crafts, 13)
        c.ns.ShowProfessionViewer(171); c.drain()
        self.assertEqual(c.ns.routeSelection.professionBatch.remaining, 13)
        self.assertEqual(c.ns.selectedRoute.recipe.id, 2152)

    def test_batch_reloads_remaining_crafts_and_skill(self):
        c = leatherworking()
        c.lua.globals().stock[2934] = 30
        c.ns.StartProfessionGuide(165, 75)
        c.lua.globals().stock[2934] = 24
        c.lua.globals().stock[2318] = 2
        success(c, 2881, 1, 3)
        success(c, 2881, 2, 3)
        saved = c.ns.db.guideState[c.ns.self]
        self.assertEqual(saved.guide.professionBatch.remaining, 12)
        c.ns.routeSelection = None
        c.ns.pendingSavedGuide = saved
        c.ns.RestoreSavedGuide()
        self.assertEqual(c.ns.selectedRoute.crafts, 12)
        self.assertEqual(c.ns.selectedRoute.recipe.id, 2152)
        self.assertEqual(c.ns.professionData[165].skill, 3)

    def test_malformed_checkpoint_is_ignored(self):
        c = crafting()
        c.ns.StartProfessionGuide(171, 75)
        saved = c.ns.db.guideState[c.ns.self]
        saved.guide.professionBatch.remaining = 999
        c.ns.routeSelection = None
        c.ns.pendingSavedGuide = saved
        c.ns.RestoreSavedGuide()
        self.assertLessEqual(c.ns.selectedRoute.crafts, 5)

    def test_secret_unrelated_duplicate_or_stopped_cast_does_not_count(self):
        c = crafting()
        c.lua.globals().stock[100] = 100
        c.ns.StartProfessionGuide(171, 75)
        event, secret = c.ns.handlers.UNIT_SPELLCAST_SUCCEEDED, c.lua.globals().secret
        for args in [('party1','x',1), ('player','x',999), (secret,'x',1),
                     ('player',secret,1), ('player','x',secret)]: event(*args)
        self.assertEqual(c.ns.routeSelection.professionBatch.remaining, 5)
        event('player','unique-cast',1); event('player','unique-cast',1)
        self.assertEqual(c.ns.routeSelection.professionBatch.remaining, 4)
        self.assertEqual(c.ns.professionCraftsObserved, 1)
        c.drain()
        c.ns.StopGuide(True)
        event('player','later',1); c.drain()
        self.assertIsNone(c.ns.routeSelection)

    def test_actual_skill_limits_batch_even_if_other_craft_gained_points(self):
        c = leatherworking(skill=11)
        c.lua.globals().stock[2934] = 30
        c.ns.StartProfessionGuide(165, 75)
        self.assertEqual(c.ns.selectedRoute.skillTarget, 15)
        c.lua.globals().pskill = 14
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertEqual(c.ns.selectedRoute.crafts, 1)
        c.lua.globals().pskill = 15
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertGreater(c.ns.selectedRoute.skillTarget, 15)
        self.assertEqual(c.ns.routeSelection.professionBatch.startSkill, 15)

    def test_fresh_primary_skill_wins_over_stale_crafting_window(self):
        c = crafting(skill=20)
        c.ns.StartProfessionGuide(171, 75)
        c.lua.execute('C_TradeSkillUI.GetChildProfessionInfo=function() return {professionID=171,professionName="Alchemy",skillLevel=20,maxSkillLevel=75} end')
        c.lua.globals().pskill = 25
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertEqual(c.ns.professionData[171].skill, 25)
        self.assertEqual(c.ns.professionData[171].recipeSkill, 20)
        self.assertIn('Skill 25', c.ns.selectedRoute.stops[1].description)

    def test_native_grey_cancels_old_batch(self):
        c = crafting()
        c.ns.StartProfessionGuide(171, 75)
        c.lua.globals().color = 70
        c.ns.handlers.TRADE_SKILL_LIST_UPDATE(); c.drain()
        self.assertIsNone(c.ns.routeSelection.professionBatch)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'read')

    def test_profession_icons_full_opacity_hide_when_card_reused(self):
        c = crafting()
        c.ns.SetFilter('professions')
        tile = c.ns.ui.cards[1]
        self.assertEqual(tile.professionIcon.alpha, 1)
        texture = tile.professionIcon.texture
        c.ns.SetFilter('guides')
        self.assertFalse(tile.professionIcon.IsShown(tile.professionIcon))
        c.ns.SetFilter('professions')
        self.assertEqual(tile.professionIcon.texture, texture)
        self.assertEqual(tile.professionIcon.alpha, 1)
        self.assertTrue(tile.professionIcon.IsShown(tile.professionIcon))


if __name__ == '__main__': unittest.main()
