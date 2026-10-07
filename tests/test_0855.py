"""Affordable crafting work and concise live profession instructions."""
import unittest

from test_0836 import crafting
from test_0837 import leatherworking, success
from test_0839 import cured_hide


def hover(c):
    c.lua.execute('''GameTooltip={lines={}}
      function GameTooltip:SetOwner(owner) self.owner=owner;self.lines={} end
      function GameTooltip:IsOwned(owner) return self.owner==owner end
      function GameTooltip:ClearLines() self.lines={} end
      function GameTooltip:AddLine(text) self.lines[#self.lines+1]=text end
      function GameTooltip:Show() self.shown=true end
      function GameTooltip:Hide() self.shown=false;self.owner=nil end''')
    c.ns.UpdateNavigation()
    c.ns.navigation.OnEnter(c.ns.navigation)
    return c.lua.globals().GameTooltip


class AffordableWorkTests(unittest.TestCase):
    def test_four_leather_becomes_four_kits_then_buy_again(self):
        c = leatherworking(skill=11)
        c.lua.globals().leatherGains = False
        c.ns.ReadProfessionRecipes()
        c.ns.StartProfessionGuide(165, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'buy')
        stock = c.lua.globals().stock
        stock[2318] = 4
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        current = c.ns.selectedRoute.stops[1]
        self.assertEqual(current.label, 'Craft 4 × Light Armor Kit')
        self.assertEqual(current.craftRecipeID, 2152)
        c.ns.ShowProfessionShopping(165, 75, 'batch')
        self.assertEqual(c.ns.shoppingList[1].need, 4)
        self.assertEqual(c.ns.shoppingList[1].missing, 0)
        for i in range(1, 5):
            stock[2318] = 4 - i
            success(c, 2152, i)  # No skill gain: consumed work is not progress.
            if i < 4:
                self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 4 - i)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'buy')
        self.assertEqual(c.ns.professionData[165].skill, 11)
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_partial_hide_stock_limits_crafting_to_scarcest_reagent(self):
        c = cured_hide(skill=35)
        c.ns.StartProfessionGuide(165, 75)
        c.lua.globals().stock[783] = 4
        c.lua.globals().stock[4289] = 2
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].label, 'Craft 2 × Cured Light Hide')
        self.assertEqual(c.ns.selectedRoute.crafts, 15)  # Full milestone estimate remains separate.
        self.assertEqual({r.itemID:r.need for r in c.ns.selectedRoute.activeMaterials.values()}, {783:2, 4289:2})
        c.lua.globals().stock[783] = 3; c.lua.globals().stock[4289] = 1
        success(c, 3816, 1, 36)
        self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 1)
        self.assertIn('Skill 36', c.ns.selectedRoute.stops[1].description)

    def test_purchase_step_is_small_work_not_full_milestone_or_goal(self):
        c = cured_hide()
        c.ns.StartProfessionGuide(165, 75)
        route = c.ns.selectedRoute
        self.assertEqual(route.workCrafts, 5)
        self.assertEqual(route.workTarget, 36)
        self.assertEqual(route.crafts, 19)
        c.ns.ShowProfessionShopping(165, 75, 'batch')
        self.assertEqual({r.itemID:r.need for r in c.ns.shoppingList.values()}, {783:5, 4289:5})
        c.ns.ShowProfessionShopping(165, 75, 'goal'); c.drain()
        self.assertGreater(c.ns.shoppingList[1].need, 5)

    def test_affordable_preparation_runs_without_all_final_materials(self):
        c = leatherworking(skill=20)
        c.lua.globals().leatherGains = False
        c.lua.globals().stock[2934] = 6
        c.ns.ReadProfessionRecipes(); c.ns.StartProfessionGuide(165, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].label, 'Craft 2 × Light Leather')
        self.assertEqual(c.ns.selectedRoute.stops[1].craftRecipeID, 2881)
        c.lua.globals().stock[2934] = 3; c.lua.globals().stock[2318] = 1
        success(c, 2881, 1)
        self.assertEqual(c.ns.selectedRoute.stops[1].label, 'Craft 1 × Light Armor Kit')
        self.assertEqual(c.ns.selectedRoute.activeMaterials[1].itemID, 2318)

    def test_partial_affordability_applies_to_all_six_crafting_professions(self):
        for ident in (171, 164, 333, 202, 165, 197):
            with self.subTest(profession=ident):
                c = crafting()
                c.lua.globals().testNS, c.lua.globals().craftingID = c.ns, ident
                c.lua.execute('''
                  local facts=testNS.ProfessionFacts(171)
                  local clone={};for k,v in pairs(facts) do clone[k]=v end
                  clone.id=craftingID
                  testNS.professionGuideData.professions[craftingID]=clone
                  function GetProfessionInfo() return 'Test crafting','icon',pskill,pmaximum,10,0,craftingID end
                  C_TradeSkillUI.GetChildProfessionInfo=function()
                    return {professionID=craftingID,professionName='Test crafting',skillLevel=pskill,maxSkillLevel=pmaximum} end
                  stock[100]=6''')
                c.ns.ReadProfessionSkills(); c.ns.ReadProfessionRecipes()
                c.ns.StartProfessionGuide(ident, 75)
                self.assertEqual(c.ns.selectedRoute.stops[1].label, 'Craft 3 × Starter mixture')
                self.assertEqual(c.ns.selectedRoute.workCrafts, 5)

    def test_skill_gain_and_recipe_color_control_work_count(self):
        c = crafting()
        c.lua.execute('''C_TradeSkillUI.GetRecipeInfo=function(id)
          return {name='Recipe '..id,learned=learned[id] or false,
            canSkillUp=true,relativeDifficulty=50,numSkillUps=2} end''')
        c.ns.ReadProfessionRecipes(); c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.workCrafts, 4)
        c.lua.globals().stock[100] = 6
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 3)
        success(c, 1, 1, 25)
        self.assertEqual(c.ns.selectedRoute.recipe.id, 2)

    def test_unreadable_reagents_do_not_claim_crafting_is_possible(self):
        c = crafting()
        c.lua.globals().stock[100] = 100
        c.lua.execute('C_TradeSkillUI.GetRecipeSchematic=function() return secret end')
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'read')
        self.assertIsNone(c.ns.selectedRoute.stops[1].craftQuantity)

    def test_required_slots_share_stock_and_live_amount_overrides_reference(self):
        c = crafting()
        c.lua.execute('''stock[100]=10
          C_TradeSkillUI.GetRecipeSchematic=function()
            return {reagentSlotSchematics={
              {required=true,quantityRequired=2,reagents={{itemID=100}}},
              {required=true,quantityRequired=3,reagents={{itemID=100}}}}} end''')
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 2)
        self.assertEqual(c.ns.selectedRoute.activeMaterials[1].need, 10)

    def test_reload_keeps_goal_but_rechecks_affordable_work(self):
        c = crafting(); c.lua.globals().stock[100] = 4
        c.ns.StartProfessionGuide(171, 75)
        saved = c.ns.db.guideState[c.ns.self]
        c.ns.routeSelection = None; c.ns.pendingSavedGuide = saved
        c.ns.RestoreSavedGuide()
        self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 2)
        self.assertEqual(c.ns.routeSelection.targetSkill, 75)

    def test_closed_book_uses_confirmed_recipe_and_never_spends_stock_twice(self):
        c = crafting()
        c.ns.ProfessionFacts(171).recipes[1].materials = c.lua.table_from([[100, 2], [100, 3]], recursive=True)
        c.ns.handlers.TRADE_SKILL_CLOSE()
        c.lua.execute('C_TradeSkillUI.GetChildProfessionInfo=function() return nil end')
        c.lua.globals().stock[100] = 10
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 2)

    def test_closed_book_still_prefers_readable_native_reagent_amounts(self):
        c = crafting()
        c.ns.handlers.TRADE_SKILL_CLOSE()
        c.lua.execute('''stock[100]=10
          C_TradeSkillUI.GetRecipeSchematic=function()
            return {reagentSlotSchematics={{required=true,quantityRequired=5,reagents={{itemID=100}}}}} end''')
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].craftQuantity, 2)


class CraftTextTests(unittest.TestCase):
    def test_hover_has_one_instruction_and_no_quest_location_fallback(self):
        c = cured_hide(skill=35); c.ns.StartProfessionGuide(165, 75)
        tooltip = hover(c)
        text = '\n'.join(tooltip.lines.values())
        self.assertEqual(text.count('Skill 35'), 1)
        self.assertEqual(text.count('Gather or buy materials'), 1)
        self.assertLess(len(text), 350)
        self.assertNotIn('quest tracker', text)
        self.assertNotIn('Location not mapped', text)
        self.assertNotIn('complete buy list', text)
        c.lua.globals().stock[783] = 4; c.lua.globals().stock[4289] = 4
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        text = '\n'.join(tooltip.lines.values())
        self.assertEqual(text.count('Craft 4 × Cured Light Hide'), 1)
        self.assertNotIn('Gather or buy', text)
        self.assertEqual(c.ns.navigation.context.text.count('Skill 35'), 1)

    def test_trainer_hover_preserves_useful_rank_reason_and_location(self):
        c = crafting(skill=75); c.ns.StartProfessionGuide(171, 150)
        text = c.ns.GuideStepDescription(c.ns.selectedRoute.stops[1])
        self.assertEqual(text.count('raises it to 150'), 1)
        self.assertIn('Friendly Trainer', text)
        self.assertIn('20.0, 40.0', text)
        self.assertNotIn('quest tracker', text)
        purpose = c.ns.GuideDestinationPurpose(c.ns.selectedRoute.stops[1])
        self.assertIn('capped at 75', purpose)
        self.assertIn('raises it to 150', purpose)
        self.assertIn('Friendly Trainer', purpose)


if __name__ == '__main__':
    unittest.main()
