"""Material forecasts, user-clicked AH searches and the Elwynn detour regression.

Lua 5.1 fixtures verify logic; actual beta UI/search behavior needs client tests.
"""
import unittest

from test_addon import Client
from test_0836 import crafting
from test_0837 import leatherworking, success
from test_063 import guide_client, zone


def forecast(c, steps, missing=0):
    plan = c.lua.table_from({'steps': steps, 'start': 1, 'target': 75, 'missing': missing}, recursive=True)
    return c.ns.ProfessionMaterialForecast(171, plan, False)


def modern(c):
    c.lua.execute('''
    ahSearches={}; ahBusy=false; sortReady=true
    AuctionHouseFrame=CreateFrame('Frame'); AuctionHouseFrame:Show()
    categories={SetSelectedCategory=function(self,value) self.selected=value; self.cleared=true end}
    AuctionHouseFrame.GetCategoriesList=function() return categories end
    AuctionHouseFrame.SetSearchText=function(self,text) self.text=text end
    AuctionHouseFrame.SendBrowseQuery=function(self,name,low,high,filters)
      ahSearches[#ahSearches+1]={name=name,low=low,high=high,filters=filters} end
    C_AuctionHouse={SendBrowseQuery=function() error('bypassed visible UI') end,
      IsThrottledMessageSystemReady=function() return not ahBusy end,
      StartCommoditiesPurchase=function() error('unexpected purchase') end}
    function AreSortTypesLoaded() return sortReady end
    ''')
    c.ns.handlers.AUCTION_HOUSE_SHOW(); c.drain()


class ForecastTests(unittest.TestCase):
    def test_five_point_gap_estimates_recipe_specific_work_and_stops_at_actual_skill(self):
        c=crafting(skill=150,maximum=225)
        facts=c.ns.ProfessionFacts(171)
        facts.recipes[1].yellow,facts.recipes[1].green,facts.recipes[1].grey=145,165,180
        facts.recipes[2].learn=155
        facts.recipes[2].yellow,facts.recipes[2].green,facts.recipes[2].grey=160,170,190
        c.lua.globals().color=50; c.lua.globals().stock[100]=1000
        c.ns.ReadProfessionRecipes();c.ns.StartProfessionGuide(171,225)
        self.assertEqual(c.ns.selectedRoute.crafts,8)
        self.assertEqual(c.ns.selectedRoute.skillTarget,155)
        self.assertIn('~8',c.ns.selectedRoute.stops[1].label)
        self.assertEqual(c.ns.selectedRoute.estimatedCraftsToMilestone,8)
        for i in range(1,4): success(c,1,i,150+i)
        self.assertEqual(c.ns.professionData[171].skill,153)
        self.assertEqual(c.ns.selectedRoute.crafts,4)
        self.assertEqual(c.ns.selectedRoute.skillTarget,155)
        self.assertEqual(c.ns.selectedRoute.estimatedCraftsToMilestone,4)
        self.assertFalse(c.ns.selectedRoute.complete)
        success(c,1,4,154)
        self.assertEqual(c.ns.selectedRoute.crafts,2)
        success(c,1,5,155)
        self.assertNotEqual(c.ns.selectedRoute.skillTarget,155)

    def test_failed_skillup_at_146_continues_crafting_without_cap_training(self):
        c=crafting(skill=146,maximum=150)
        recipe=c.ns.ProfessionFacts(171).recipes[1]
        recipe.yellow,recipe.green,recipe.grey=150,170,190
        c.lua.globals().stock[100]=1000
        c.ns.StartProfessionGuide(171,225)
        for i in range(1,5): success(c,1,i)
        self.assertEqual(c.ns.professionData[171].skill,146)
        self.assertEqual(c.ns.selectedRoute.stops[1].action,'craft')
        self.assertEqual(c.ns.selectedRoute.recipe.id,1)
        self.assertEqual(c.ns.selectedRoute.skillTarget,150)
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_recipe_training_below_150_cap_does_not_add_expert_detour(self):
        c = crafting(skill=146,maximum=150)
        facts = c.ns.ProfessionFacts(171)
        facts.ranks[3] = c.lua.table_from({'name':'Expert','maximum':225,'skill':125,'level':20})
        facts.trainers[3] = c.lua.table_from({'name':'Distant Expert','hub':'Far city','maximum':225,
                                            'mapID':502,'x':.8,'y':.8,'faction':'Horde'})
        facts.recipes[2].learn, facts.recipes[2].yellow, facts.recipes[2].green, facts.recipes[2].grey = 130,150,170,190
        c.lua.globals().color=70
        c.ns.ReadProfessionRecipes(); c.ns.StartProfessionGuide(171,150)
        self.assertEqual(c.ns.selectedRoute.stops[1].npcName,'Friendly Trainer')
        self.assertNotIn('Expert',c.ns.selectedRoute.stops[1].description)
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_stock_is_subtracted_once_across_different_recipes(self):
        c = crafting(); c.lua.globals().stock[100] = 5
        recipes = c.ns.ProfessionFacts(171).recipes
        result = forecast(c, [{'recipe': recipes[1], 'start': 20, 'crafts': 3},
                              {'recipe': recipes[2], 'start': 25, 'crafts': 4}])
        row = result.materials[1]
        self.assertEqual((row.need, row.have, row.missing), (10, 5, 5))
        self.assertIsNone(result.estimatedCost)

    def test_previously_crafted_intermediate_is_not_bought_or_made_twice(self):
        c = leatherworking(); c.lua.globals().stock[2934] = 15
        facts = c.ns.ProfessionFacts(165)
        recipes = {r.id:r for r in facts.recipes.values()}
        plan = c.lua.table_from({'steps':[{'recipe':recipes[2881], 'start':1, 'crafts':5},
                                         {'recipe':recipes[2152], 'start':6, 'crafts':5}],
                                 'start':1,'target':11,'missing':0}, recursive=True)
        result = c.ns.ProfessionMaterialForecast(165,plan,False)
        rows = {r.itemID:r for r in result.materials.values()}
        self.assertEqual(rows[2934].need,15)
        self.assertEqual(rows[2934].missing,0)
        self.assertEqual(rows[2318].missing,0)
        self.assertEqual(rows[2318].planned,5)
        self.assertEqual(result.estimatedCost,0)

    def test_partial_and_unreadable_inventory_are_honest(self):
        c = crafting()
        c.lua.execute('C_Item.GetItemCount=function() return secret end')
        c.ns.QueueProfessionUpdate(); c.drain()
        r = c.ns.ProfessionFacts(171).recipes[1]
        result = forecast(c,[{'recipe':r,'start':20,'crafts':2},{'recipe':r,'start':22,'crafts':2}],missing=40)
        self.assertTrue(result.incomplete)
        self.assertIsNone(result.materials[1].missing)
        self.assertIsNone(result.estimatedCost)

    def test_estimate_rounds_up_crafts_and_prices_only_missing_materials(self):
        c = crafting(); c.lua.globals().stock[100] = 1
        c.ns.marketQuotes[100] = c.lua.table_from({'unitPrice':30})
        result = forecast(c,[{'recipe':c.ns.ProfessionFacts(171).recipes[1],'start':20,'crafts':1.5}])
        self.assertEqual(result.materials[1].need,4)
        self.assertEqual(result.estimatedCost,90)

    def test_goal_window_refreshes_and_cancelled_jobs_cannot_overwrite_new_context(self):
        c = crafting(); c.ns.StartProfessionGuide(171,75)
        c.ns.ShowProfessionShopping(171,75,'goal')
        self.assertTrue(c.ns.shoppingContext.loading)
        c.ns.ShowProfessionShopping(171,75,'batch'); c.drain()
        self.assertEqual(c.ns.shoppingContext.scope,'batch')
        self.assertEqual(c.ns.shoppingList[1].need,10)
        self.assertFalse(c.ns.shoppingContext.loading)
        c.ns.ShowProfessionShopping(171,75,'goal'); c.drain()
        self.assertGreater(c.ns.shoppingList[1].need,10)
        self.assertIn('approximate',c.ns.shoppingWindow.notice.text)
        c.ns.shoppingWindow.Hide(c.ns.shoppingWindow)
        c.ns.shoppingWindow.OnHide()
        c.ns.ShowShoppingList(c.lua.table(),'Quest items'); c.drain()
        self.assertIsNone(c.ns.shoppingContext)
        self.assertEqual(c.ns.shoppingWindow.title.text,'Quest items')

    def test_bag_refresh_does_not_remove_planned_output_credit(self):
        c = leatherworking(); c.ns.ShowProfessionShopping(165,75,'goal'); c.drain()
        before = {r.itemID:r.missing for r in c.ns.shoppingList.values()}
        c.ns.RefreshShoppingList(); c.drain()
        self.assertEqual(before,{r.itemID:r.missing for r in c.ns.shoppingList.values()})

    def test_close_or_combat_cancels_estimation_and_resume_completes(self):
        c = crafting(); c.ns.ShowProfessionShopping(171,75,'goal')
        c.lua.globals().combat = True; c.drain()
        self.assertIsNone(c.ns.shoppingContext.signature)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED(); c.drain()
        self.assertFalse(c.ns.shoppingContext.loading)
        self.assertGreater(len(c.ns.shoppingList),0)


class AuctionTests(unittest.TestCase):
    def test_modern_toolbar_and_material_button_search_only_when_clicked(self):
        c = crafting(); c.ns.StartProfessionGuide(171,75); modern(c)
        self.assertEqual(len(c.lua.globals().ahSearches),0)
        self.assertTrue(c.ns.auctionGuideToolbar.IsShown(c.ns.auctionGuideToolbar))
        c.ns.auctionGuideToolbar.rows[1].search.OnClick()
        self.assertEqual(c.lua.globals().ahSearches[1].name,'Herbs')
        self.assertTrue(c.lua.globals().categories.cleared)
        self.assertEqual(len(c.lua.globals().ahSearches[1].filters),0)
        c.ns.ShowProfessionShopping(171,75,'batch')
        c.ns.shoppingWindow.rows[1].search.OnClick()
        self.assertEqual(len(c.lua.globals().ahSearches),2)

    def test_closed_busy_combat_and_uncached_names_do_not_search(self):
        c = crafting()
        self.assertFalse(c.ns.SearchGuideAuctionItem(100)); modern(c)
        c.lua.globals().ahBusy = True
        self.assertFalse(c.ns.SearchGuideAuctionItem(100))
        c.lua.globals().ahBusy = False; c.lua.globals().combat = True
        self.assertFalse(c.ns.SearchGuideAuctionItem(100))
        c.lua.globals().combat = False; c.lua.globals().sortReady = False
        self.assertFalse(c.ns.SearchGuideAuctionItem(100))
        c.lua.globals().sortReady = True
        self.assertFalse(c.ns.SearchGuideAuctionItem(999))
        c.ns.handlers.AUCTION_HOUSE_CLOSED()
        self.assertFalse(c.ns.SearchGuideAuctionItem(100))
        self.assertEqual(len(c.lua.globals().ahSearches),0)

    def test_legacy_browse_search_clears_filters_and_uses_exact_name(self):
        c = crafting()
        c.lua.execute('''
        legacyQueries={}; AuctionFrame=CreateFrame('Frame'); AuctionFrame:Show()
        AuctionFrameBrowse=CreateFrame('Frame'); AuctionFrameBrowse:Show(); AuctionFrameBrowse.page=8
        BrowseName=CreateFrame('EditBox'); BrowseMinLevel=CreateFrame('EditBox'); BrowseMaxLevel=CreateFrame('EditBox')
        function CanSendAuctionQuery() return true end
        function QueryAuctionItems(...) legacyQueries[#legacyQueries+1]={...} end
        ''')
        c.ns.handlers.AUCTION_HOUSE_SHOW(); c.drain()
        self.assertTrue(c.ns.SearchGuideAuctionItem(100))
        args = c.lua.globals().legacyQueries[1]
        self.assertEqual(args[1],'Herbs'); self.assertEqual(args[4],0)
        self.assertFalse(args[5]); self.assertFalse(args[7]); self.assertTrue(args[8])
        self.assertEqual(c.lua.globals().BrowseName.text,'Herbs')
        self.assertEqual(c.lua.globals().AuctionFrameBrowse.page,0)

    def test_new_prices_rechoose_unfinished_batch_immediately(self):
        c = crafting(skill=25)
        facts = c.ns.ProfessionFacts(171)
        facts.recipes[2].materials[1][1] = 101
        c.lua.globals().learned[2] = True
        c.lua.execute('''C_TradeSkillUI.GetRecipeSchematic=function(id)
          return {reagentSlotSchematics={{required=true,quantityRequired=id==1 and 2 or 1,
            reagents={{itemID=id==1 and 100 or 101}}}}} end''')
        c.ns.ReadProfessionRecipes(); c.ns.StartProfessionGuide(171,75)
        self.assertEqual(c.ns.selectedRoute.recipe.id,2)
        c.ns.marketQuotes[100] = c.lua.table_from({'unitPrice':1,'quantity':100})
        c.lua.execute('C_AuctionHouse={GetCommoditySearchResultInfo=function() return {unitPrice=10000,quantity=100} end}')
        c.ns.handlers.COMMODITY_SEARCH_RESULTS_UPDATED(101); c.drain()
        self.assertEqual(c.ns.selectedRoute.recipe.id,1)
        self.assertEqual(c.ns.professionData[171].skill,25)
        self.assertEqual(c.ns.selectedRoute.skillTarget,40)
        self.assertEqual(c.ns.selectedRoute.crafts,15)

    def test_item_auction_prices_use_buyout_per_item_and_guard_private_data(self):
        c = crafting()
        c.lua.execute('''C_AuctionHouse={GetNumItemSearchResults=function() return 3 end,
          GetItemSearchResultInfo=function(key,i)
            if i==1 then return {buyoutAmount=100,quantity=5} end
            if i==2 then return {buyoutAmount=0,quantity=10} end
            return {buyoutAmount=secret,quantity=10} end}''')
        c.ns.handlers.ITEM_SEARCH_RESULTS_UPDATED(c.lua.table_from({'itemID':100})); c.drain()
        self.assertEqual(c.ns.marketQuotes[100].unitPrice,20)
        c.ns.handlers.ITEM_SEARCH_RESULTS_UPDATED(c.lua.table_from({'itemID':c.lua.globals().secret}))

    def test_legacy_prices_use_stack_size_and_never_submit_queries(self):
        c = crafting()
        c.lua.execute('''
        function GetNumAuctionItems() return 2,2 end
        function GetAuctionItemLink(_,i) return i==1 and '|Hitem:100:0|h[Herbs]|h' or '|Hitem:101:0|h[Unknown]|h' end
        function GetAuctionItemInfo(_,i) return 'Herbs','icon',5,1,true,1,nil,1,1,i==1 and 100 or secret end
        function QueryAuctionItems() error('unexpected automatic search') end
        ''')
        c.ns.handlers.AUCTION_HOUSE_SHOW(); c.ns.handlers.AUCTION_ITEM_LIST_UPDATE(); c.drain()
        self.assertEqual(c.ns.marketQuotes[100].unitPrice,20)
        self.assertIsNone(c.ns.marketQuotes[101])


class TrainerTests(unittest.TestCase):
    def test_uncached_rank_spell_requests_are_bounded_even_if_success_still_has_no_name(self):
        c=crafting()
        c.lua.execute('''
        spellRequests={}
        C_Spell={GetSpellInfo=function() return nil end,
          RequestLoadSpellData=function(id) spellRequests[#spellRequests+1]=id end}
        function UnitName() return 'Nearby Trainer' end
        function GetNumTrainerServices() return 1 end
        function GetTrainerServiceInfo() return 'Expert Alchemy','available','icon',20 end
        ''')
        c.ns.handlers.TRAINER_SHOW(); c.drain()
        count=len(c.lua.globals().spellRequests)
        self.assertGreater(count,0)
        for id in list(c.lua.globals().spellRequests.values()): c.ns.handlers.SPELL_DATA_LOAD_RESULT(id,True)
        c.drain()
        self.assertEqual(len(c.lua.globals().spellRequests),count)

    def test_observed_available_expert_replaces_stale_published_rank_for_both_shapes(self):
        for shape in ('classic','modern'):
            with self.subTest(shape=shape):
                c=crafting(skill=150,maximum=150)
                facts=c.ns.ProfessionFacts(171)
                facts.ranks[3]=c.lua.table_from({'name':'Expert','maximum':225,'skill':125,'level':20})
                facts.trainers[3]=c.lua.table_from({'name':'Distant Expert','hub':'Far city','maximum':225,
                    'mapID':502,'x':.8,'y':.8,'faction':'Horde'})
                c.ns.StartProfessionGuide(171,225)
                self.assertEqual(c.ns.selectedRoute.stops[1].npcName,'Distant Expert')
                c.lua.globals().trainerShape=shape
                c.lua.execute('''
                function UnitName() return 'Nearby Trainer' end
                function GetNumTrainerServices() return 1 end
                function GetTrainerServiceInfo()
                  if trainerShape=='classic' then return 'Alchemy','Expert','available',true end
                  return 'Expert Alchemy','available','icon',20 end
                ''')
                c.ns.handlers.TRAINER_SHOW(); c.drain()
                self.assertEqual(c.ns.selectedRoute.stops[1].npcName,'Nearby Trainer')
                self.assertEqual(c.ns.selectedRoute.stops[1].mapID,501)
                self.assertEqual(len(list(c.ns.professionSaved.trainers.values())),1)

    def test_unavailable_or_private_offerings_do_not_invent_trainer_rank(self):
        c=crafting()
        c.lua.execute('''
        function UnitName() return 'Nearby Trainer' end
        function GetNumTrainerServices() return 1 end
        function GetTrainerServiceInfo() return 'Expert Alchemy','unavailable','icon',20 end
        ''')
        c.ns.handlers.TRAINER_SHOW(); c.drain()
        self.assertEqual(len(c.ns.professionSaved.trainers),0)
        c.lua.execute("GetTrainerServiceInfo=function() return 'Expert Alchemy',secret,'available',true end")
        c.ns.handlers.TRAINER_SHOW(); c.drain()
        self.assertEqual(len(c.ns.professionSaved.trainers),0)

    def test_offered_recipe_is_evidence_without_assuming_rank_or_other_build(self):
        c=crafting()
        c.lua.execute('''
        function UnitName() return 'Nearby Trainer' end
        function GetNumTrainerServices() return 1 end
        function GetTrainerServiceInfo() return 'Later mixture','available','icon',20 end
        ''')
        c.ns.handlers.TRAINER_SHOW(); c.drain()
        trainer=c.ns.ProfessionTrainer(171,150,2)
        self.assertEqual(trainer.name,'Nearby Trainer')
        self.assertEqual(trainer.maximum,0)
        self.assertEqual(len(c.ns.ObservedProfessionTrainers(171,225)),0)
        c.lua.execute("GetBuildInfo=function() return '1.60.1','different-build','date',16001 end")
        self.assertEqual(len(c.ns.ObservedProfessionTrainers(171,150,2)),0)


class ElwynnRegressionTests(unittest.TestCase):
    def test_zero_level_zero_xp_props_do_not_steer_any_zone_guide(self):
        c = guide_client(3)
        q = c.ns.catalogue.quests[900]; q.level,q.xp=0,0
        g = zone(c); c.ns.GenerateFixedGuide(g,False)
        self.assertNotIn(900,{s.id for s in g.fixedPlan.values()})
        self.assertIsNotNone(c.ns.CatalogueQuest(900))  # Library facts remain.
        q.level,q.xp = 0,None
        self.assertFalse(c.ns.IsLevelingExcludedQuest(900))
        q.level,q.xp = 1,0
        self.assertFalse(c.ns.IsLevelingExcludedQuest(900))

    def test_real_elwynn_preview_has_no_applejack_detour(self):
        c = Client(quests=(7,),completed=(783,5261),use_catalogue=True)
        c.guide_environment(level=2)
        c.lua.globals().pyBand = lambda a,b:int(a)&int(b)
        c.lua.globals().pyShift = lambda a,b:int(a)<<int(b)
        c.lua.execute('''
        grouped=false; bit={band=function(a,b) return pyBand(a,b) end,lshift=function(a,b) return pyShift(a,b) end}
        function UnitFactionGroup() return 'Alliance' end
        function UnitClass() return 'Warrior','WARRIOR',1 end
        function UnitRace() return 'Human','Human',1 end
        C_Map.GetBestMapForUnit=function() return 1429 end
        C_Map.GetMapInfo=function() return {name='Elwynn Forest'} end
        ''')
        c.ns.UpdateRoster(); c.ns.ReadProfile()
        g = c.ns.ZoneGuideForMap(1429,True); c.ns.GenerateFixedGuide(g,False)
        route = c.ns.BuildFixedGuideRoute(g,False)
        self.assertNotIn(91736,{s.id for s in g.fixedPlan.values()})
        self.assertNotIn(91736,{s.id for s in route.previewStops.values()})
        self.assertIn(18,{s.id for s in route.previewStops.values()})
        self.assertEqual(c.ns.CatalogueQuest(91736).title,'Applejack Still')


if __name__ == '__main__': unittest.main()
