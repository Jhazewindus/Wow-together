"""Personal skill-based crafting paths, data boundaries and shared guide UI."""
import json
import time
import unittest
from pathlib import Path

from test_addon import Client

ROOT = Path(__file__).resolve().parents[1]


def crafting(skill=20, level=25, maximum=75):
    c = Client(quests=(), use_catalogue=False)
    c.guide_environment(level=level)
    c.lua.globals().grouped = False
    c.ns.ReadProfile()
    c.drain()
    facts = {
        'id': 171, 'name': 'Alchemy', 'recipes': [
            {'id': 1, 'name': 'Starter mixture', 'learn': 1, 'yellow': 40, 'green': 45, 'grey': 50,
             'source': 'trainer', 'materials': [[100, 2]], 'outputID': 200, 'outputQuantity': 1},
            {'id': 2, 'name': 'Later mixture', 'learn': 25, 'yellow': 55, 'green': 65, 'grey': 75,
             'source': 'trainer', 'materials': [[100, 1]], 'outputID': 201, 'outputQuantity': 1},
            {'id': 3, 'name': 'Unknown drop', 'learn': 1, 'yellow': 75, 'grey': 100,
             'source': 'drop', 'materials': [[100, 1]], 'outputID': 202}],
        'items': {100: {'name': 'Herbs'}},
        'ranks': [{'name': 'Apprentice', 'maximum': 75, 'skill': 0, 'level': 0},
                  {'name': 'Journeyman', 'maximum': 150, 'skill': 50, 'level': 10}],
        'trainers': [{'name': 'Friendly Trainer', 'hub': 'Local Town', 'maximum': 150,
                      'mapID': 501, 'x': .2, 'y': .4, 'faction': 'Horde'},
                     {'name': 'Enemy Trainer', 'hub': 'Enemy Town', 'maximum': 300,
                      'mapID': 501, 'x': .21, 'y': .37, 'faction': 'Alliance'}],
        'icon': 'Interface\\Icons\\Trade_Alchemy',
    }
    c.ns.professionGuideData.professions[171] = c.lua.table_from(facts, recursive=True)
    c.lua.execute('''
    stock={}; learned={[1]=true}
    pskill=20; pmaximum=75; color=40
    function GetProfessions() return 1,nil end
    function GetProfessionInfo(index) return 'Alchemy','icon',pskill,pmaximum,10,0,171 end
    Enum.TradeskillRelativeDifficulty={Optimal=40,Medium=50,Easy=60,Trivial=70}
    C_Item={GetItemCount=function(id) return stock[id] or 0 end,GetItemInfo=function(id) return id==100 and 'Herbs' or nil end}
    C_TradeSkillUI={GetChildProfessionInfo=function() return {professionID=171,professionName='Alchemy',skillLevel=pskill,maxSkillLevel=pmaximum} end,
      GetAllRecipeIDs=function() return {1,2,3} end,
      GetRecipeInfo=function(id) return {name='Recipe '..id,learned=learned[id] or false,canSkillUp=color~=70,relativeDifficulty=color} end,
      GetRecipeSchematic=function(id) return {reagentSlotSchematics={{required=true,quantityRequired=id==1 and 2 or 1,reagents={{itemID=100}}}}} end}
    ''')
    c.lua.globals().pskill = skill
    c.lua.globals().pmaximum = maximum
    c.ns.professionWindowOpen = True
    c.ns.ReadProfessionSkills()
    c.ns.ReadProfessionRecipes()
    return c


class ProfessionDataTests(unittest.TestCase):
    def test_facts_have_no_copied_sequence_or_editorial_fields(self):
        data = json.loads((ROOT / 'WowTogether/ProfessionData.json').read_text())
        self.assertEqual(len(data['professions']), 6)
        self.assertEqual(sum(len(v['recipes']) for v in data['professions'].values()), 2009)
        self.assertEqual(sum(len(v['trainers']) for v in data['professions'].values()), 150)
        self.assertEqual(len(data['sources']), 12)
        for info in data['professions'].values():
            self.assertEqual(len({r['id'] for r in info['recipes']}), len(info['recipes']))
            self.assertEqual(len(info['ranks']), 4)
            for recipe in info['recipes']:
                self.assertFalse({'how', 'details', 'step', 'est', 'bundle', 'writ', 'vendorText'} & set(recipe))
                self.assertIn(recipe.get('faction'), (None, 'Horde', 'Alliance'))
            self.assertTrue(all(t['name'] and t['mapID'] > 0 and 0 <= t['x'] <= 1 and 0 <= t['y'] <= 1 for t in info['trainers']))

    def test_all_six_baselines_can_make_a_bounded_preview(self):
        c = Client(quests=())
        started = time.monotonic()
        for id in (171,164,333,202,165,197):
            plan = c.ns.PlanProfessionPreview(id, 75, False)
            self.assertGreater(len(plan.steps), 0)
            self.assertEqual(plan.start, 1)
        self.assertLess(time.monotonic() - started, 5)


class SkillPlannerTests(unittest.TestCase):
    def test_profession_skill_not_character_level_controls_recipe(self):
        low, high = crafting(skill=20, level=25), crafting(skill=25, level=25)
        self.assertEqual(low.ns.ProfessionNextRecipe(171, 20).id, 1)
        self.assertEqual(high.ns.ProfessionNextRecipe(171, 25).id, 2)
        self.assertEqual(low.ns.professionData[171].skill, 20)
        self.assertEqual(low.ns.professionData[171].maximum, 75)

    def test_owned_materials_and_observed_cost_affect_recommendation(self):
        c = crafting(skill=25)
        c.lua.globals().stock[100] = 30
        c.ns.QueueProfessionUpdate(); c.drain()
        self.assertEqual(c.ns.ProfessionNextRecipe(171, 25).id, 1)  # Both batches free: known recipe avoids training.
        c.lua.globals().stock[100] = 0
        c.ns.marketQuotes[100] = c.lua.table_from({'unitPrice': 500})
        c.ns.QueueProfessionUpdate(); c.drain()
        self.assertEqual(c.ns.ProfessionNextRecipe(171, 25).id, 2)

    def test_unknown_drop_is_not_treated_as_trainer_recipe(self):
        c = crafting()
        r = c.ns.ProfessionFacts(171).recipes[3]
        self.assertEqual(c.ns.ProfessionSkillChance(171, r, 20, True), 0)
        c.lua.globals().learned[3] = True
        c.ns.ReadProfessionRecipes()
        self.assertEqual(c.ns.ProfessionSkillChance(171, r, 20, True), 1)

    def test_faction_acquisition_gate_respects_actual_learned_recipe(self):
        c = crafting()
        recipe = c.ns.ProfessionFacts(171).recipes[1]
        recipe.faction = 'Alliance'
        self.assertEqual(c.ns.ProfessionSkillChance(171, recipe, 20, True), 1)
        c.lua.globals().learned[1] = False
        c.ns.ReadProfessionRecipes()
        self.assertEqual(c.ns.ProfessionSkillChance(171, recipe, 20, True), 0)

    def test_live_grey_and_private_skill_gain_override_baseline_orange(self):
        c = crafting()
        c.lua.globals().color = 70
        c.ns.ReadProfessionRecipes()
        self.assertEqual(c.ns.ProfessionSkillChance(171, c.ns.ProfessionFacts(171).recipes[1], 20, True), 0)
        c.lua.execute('C_TradeSkillUI.GetRecipeInfo=function(id) return {name="Recipe",learned=true,canSkillUp=secret,relativeDifficulty=secret} end')
        c.ns.ReadProfessionRecipes()
        self.assertEqual(c.ns.ProfessionSkillChance(171, c.ns.ProfessionFacts(171).recipes[1], 20, True), 0)

    def test_rank_training_is_character_level_gated_and_friendly(self):
        c = crafting(skill=75, level=9)
        c.ns.StartProfessionGuide(171, 150)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'wait')
        self.assertIn('character level 10', c.ns.selectedRoute.stops[1].label)
        c.lua.globals().playerLevel = 10
        c.ns.ReadProfile(); c.ns.QueueProfessionUpdate(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'train')
        self.assertEqual(c.ns.selectedRoute.stops[1].npcName, 'Friendly Trainer')

    def test_invalid_primary_profession_read_does_not_erase_cached_skill(self):
        c = crafting()
        c.lua.execute('GetProfessions=function() return secret end')
        self.assertFalse(c.ns.ReadProfessionSkills())
        self.assertEqual(c.ns.professionData[171].skill, 20)
        c.lua.execute('GetProfessions=function() return nil,nil end')
        self.assertTrue(c.ns.ReadProfessionSkills())
        self.assertIsNone(c.ns.professionData[171])

    def test_intermediate_materials_stock_and_output_quantities(self):
        c = crafting()
        data = c.ns.ProfessionFacts(171)
        data.recipes[4] = c.lua.table_from({'id': 4,'name': 'Bolt','learn': 1,'yellow': 50,'grey': 75,'source': 'trainer',
                                        'materials': [[100, 2]],'outputID': 300,'outputQuantity': 2}, recursive=True)
        # Replacing the table invalidates the per-profession producer index.
        c.ns.professionGuideData.professions[171] = c.lua.table_from({k:v for k,v in data.items()})
        recipe = c.lua.table_from({'id': 99,'name':'Coat','materials':[[300,3],[300,2]]}, recursive=True)
        c.lua.globals().stock[300] = 1
        c.lua.globals().stock[100] = 1
        items, cost, prep, incomplete = c.ns.ProfessionMaterials(171, recipe, 1, 20, True)
        rows = {r.itemID:r for r in items.values()}
        self.assertEqual(rows[100].missing, 3)
        self.assertEqual(rows[100].need, 4)
        self.assertEqual(sum(p.crafts for p in prep.values()), 2)
        self.assertIsNone(cost)
        self.assertFalse(incomplete)

    def test_unknown_prices_are_not_zero_cost(self):
        c = crafting()
        c.ns.StartProfessionGuide(171, 75)
        self.assertIsNone(c.ns.selectedRoute.estimatedCost)
        self.assertEqual(c.ns.selectedRoute.materials[1].missing, 10)
        c.ns.marketQuotes[100] = c.lua.table_from({'unitPrice':20})
        c.ns.QueueProfessionUpdate(); c.drain()
        self.assertEqual(c.ns.selectedRoute.estimatedCost, 200)

    def test_native_changed_reagents_override_published_materials(self):
        c = crafting()
        c.lua.execute('C_TradeSkillUI.GetRecipeSchematic=function() return {reagentSlotSchematics={{required=true,quantityRequired=3,reagents={{itemID=400}}}}} end')
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.materials[1].itemID, 400)
        self.assertEqual(c.ns.selectedRoute.materials[1].need, 15)
        c.lua.execute('C_TradeSkillUI.GetRecipeSchematic=function() return {reagentSlotSchematics=secret} end')
        c.ns.QueueProfessionUpdate(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'read')

    def test_multi_skill_gains_limit_batch_at_goal_and_rank_cap(self):
        c = crafting(skill=73)
        c.lua.execute('''
        stock[100]=100
        C_TradeSkillUI.GetRecipeInfo=function(id) return {name='Recipe '..id,learned=id==1,
          canSkillUp=true,relativeDifficulty=40,numSkillUps=id==1 and 3 or 1} end
        ''')
        c.ns.ReadProfessionRecipes()
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.crafts, 1)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'craft')


class ProfessionWindowTests(unittest.TestCase):
    def test_learned_cards_first_click_preview_then_reuse_mini_window(self):
        c = crafting()
        c.ns.SetFilter('professions')
        self.assertEqual(c.ns.ui.visibleCards, 6)
        tile = c.ns.ui.cards[1]
        self.assertEqual(tile.activity.profession, 171)
        self.assertEqual(tile.category.text, 'YOUR PROFESSION')
        self.assertIn('Skill 20 / 75', tile.count.text)
        self.assertLess(tile.width, c.ns.ui.contentWidth)
        self.assertFalse(tile.mapButton.IsShown(tile.mapButton))
        tile.OnClick(); c.drain()
        viewer = c.ns.professionViewer
        self.assertTrue(viewer.IsShown(viewer))
        self.assertIn('CRAFTING PATH', viewer.body.text)
        self.assertIsNone(c.ns.routeSelection)
        viewer.start.OnClick()
        self.assertEqual(c.ns.routeSelection.mode, 'profession')
        self.assertEqual(c.ns.navigation.skipStep.caption.text, 'Next recipe')
        self.assertEqual(c.ns.navigation.skipQuest.caption.text, 'Materials')
        self.assertFalse(c.ns.navigation.back.IsEnabled(c.ns.navigation.back))

    def test_craft_progress_bags_training_and_actual_goal_control_steps(self):
        c = crafting(skill=20)
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'buy')
        c.lua.globals().stock[100] = 50
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'craft')
        c.lua.globals().pskill = 25
        c.ns.handlers.SKILL_LINES_CHANGED(); c.drain()
        self.assertEqual(c.ns.professionData[171].skill, 25)
        c.lua.globals().pskill = 75
        c.ns.handlers.TRADE_SKILL_LIST_UPDATE(); c.drain()
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'complete')
        self.assertEqual(len(c.lua.globals().sent), 0)

    def test_next_recipe_does_not_skip_quests_or_fake_skill(self):
        c = crafting()
        c.ns.StartProfessionGuide(171, 75)
        c.ns.SkipGuide('step')
        self.assertEqual(c.ns.professionData[171].skill, 20)
        self.assertEqual(c.ns.selectedRoute.stops[1].action, 'read')
        self.assertFalse(c.ns.selectedRoute.complete)
        self.assertIsNone(c.ns.db.guideSkips[c.ns.self].quests[0])
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(c.ns.selectedRoute.recipe.id, 1)

    def test_primary_id_is_seventh_return_and_private_id_cannot_replace(self):
        c = crafting()
        c.lua.execute('GetProfessionInfo=function() return "Alchemy","icon",21,75,10,0,secret end')
        self.assertFalse(c.ns.ReadProfessionSkills())
        self.assertEqual(c.ns.professionData[171].skill, 20)

    def test_gathering_first_does_not_hide_second_crafting_profession(self):
        c = crafting()
        c.lua.execute('''
        function GetProfessions() return 2,1 end
        local previous=GetProfessionInfo
        function GetProfessionInfo(i) if i==2 then return 'Herbalism','icon',35,75,0,0,182 end; return previous(i) end
        ''')
        self.assertTrue(c.ns.ReadProfessionSkills())
        self.assertEqual(c.ns.professionData[171].skill, 20)

    def test_current_colors_are_not_reused_at_a_changed_skill(self):
        c = crafting()
        c.lua.globals().pskill = 50
        c.ns.ReadProfessionSkills()
        self.assertEqual(c.ns.ProfessionSkillChance(171, c.ns.ProfessionFacts(171).recipes[1], 50, True), 0)

    def test_merchant_prices_exclude_extended_currency_and_do_not_buy(self):
        c = crafting()
        c.lua.execute('''
        function GetMerchantNumItems() return 2 end
        function GetMerchantItemLink(i) return '|Hitem:'..(i==1 and 100 or 999)..'|h|h' end
        function GetMerchantItemInfo(i) return 'Material','icon',100,5,-1,true,i==2 end
        function BuyMerchantItem() error('Unexpected purchase') end
        ''')
        c.ns.handlers.MERCHANT_SHOW(); c.drain()
        self.assertEqual(c.ns.professionVendorQuotes[100].unitPrice, 20)
        self.assertIsNone(c.ns.professionVendorQuotes[999])
        c.ns.StartProfessionGuide(171, 75)
        self.assertEqual(c.ns.selectedRoute.estimatedCost, 200)

    def test_profession_cards_do_not_unpack_all_recipes(self):
        c = Client(quests=())
        c.ns.SetFilter('professions')
        stat = next(s for s in c.ns.PackedDataStats().values() if s.name == 'crafting-professions')
        self.assertEqual(stat.decoded, 0)
        c.ns.ShowProfessionViewer(171); c.drain()
        stat = next(s for s in c.ns.PackedDataStats().values() if s.name == 'crafting-professions')
        self.assertGreater(stat.decoded, 0)
        self.assertLessEqual(stat.decoded, 4)  # At most one profession's details.

    def test_profession_resume_saved_goal_and_stop_remains_stopped(self):
        c = crafting()
        c.ns.StartProfessionGuide(171, 150)
        saved = c.ns.db.guideState[c.ns.self]
        self.assertEqual(saved.guide.professionID, 171)
        self.assertIsNone(saved.guide.records)
        c.ns.routeSelection = None
        c.ns.pendingSavedGuide = saved
        c.ns.RestoreSavedGuide()
        self.assertEqual(c.ns.routeSelection.targetSkill, 150)
        c.ns.StopGuide(True)
        self.assertIsNone(c.ns.db.guideState[c.ns.self])
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        self.assertIsNone(c.ns.routeSelection)
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))

    def test_repeated_events_coalesce_and_defer_reading_in_combat(self):
        c = crafting()
        c.ns.StartProfessionGuide(171, 75)
        c.lua.execute('reads=0; local old=GetProfessions; GetProfessions=function() reads=reads+1; return old() end')
        for _ in range(20): c.ns.QueueProfessionUpdate(True)
        c.drain()
        self.assertEqual(c.lua.globals().reads, 1)
        c.lua.globals().combat = True
        c.ns.QueueProfessionUpdate(True); c.drain()
        self.assertEqual(c.lua.globals().reads, 1)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED(); c.drain()
        self.assertEqual(c.lua.globals().reads, 2)

    def test_future_preview_can_close_or_change_goal_without_old_result(self):
        c = crafting()
        c.ns.ShowProfessionViewer(171)
        frame = c.ns.professionViewer
        frame.goal.options[75].OnClick()
        c.drain()
        self.assertEqual(frame.plan.target, 75)
        c.ns.ShowProfessionViewer(171)
        frame.Hide(frame); frame.OnHide()
        c.drain()
        self.assertFalse(frame.IsShown(frame))
