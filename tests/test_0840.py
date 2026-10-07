"""Goal-based auction materials, bounded asynchronous scans and market scope."""
import unittest

from test_addon import Client
from test_0836 import crafting
from test_0837 import leatherworking
from test_0838 import modern
from test_057 import plain


def market(c):
    c.lua.execute('serverClock=100000; function GetServerTime() return serverClock end')
    c.ns.InitializeAuctionMarket()
    return c


def scanner(skill=25, goal=75):
    c = market(crafting(skill=skill))
    facts = c.ns.ProfessionFacts(171)
    facts.recipes[2].materials[1][1] = 101
    facts.recipes[2].materials[1][2] = 1
    c.lua.execute('''
    learned[2]=true
    C_Item.GetItemInfo=function(id) return ({[100]='Herbs',[101]='Other Herb'})[id] end
    C_TradeSkillUI.GetRecipeSchematic=function(id)
      return {reagentSlotSchematics={{required=true,quantityRequired=id==1 and 2 or 1,
      reagents={{itemID=id==1 and 100 or 101}}}}} end
    ''')
    c.ns.ReadProfessionRecipes(); c.ns.StartProfessionGuide(171,goal)
    modern(c); c.drain()
    c.lua.execute('''
    scanTimers={}; tick=0; queries={}; moreCalls={}; commodityRows={}; itemRows={}; full=true
    Enum.AuctionHouseSortOrder={Price=0}
    C_Timer.After=function(delay,fn) scanTimers[#scanTimers+1]={at=tick+delay,fn=fn} end
    function runTo(limit)
      local count=0
      while true do
        local best
        for i,t in ipairs(scanTimers) do if t.at<=limit and (not best or t.at<scanTimers[best].at) then best=i end end
        if not best then break end
        local timer=table.remove(scanTimers,best);tick=timer.at;timer.fn()
        count=count+1;assert(count<3000,'scan timer loop')
      end
      tick=limit
    end
    C_AuctionHouse.MakeItemKey=function(id) return {itemID=id,itemLevel=0,itemSuffix=0,battlePetSpeciesID=0} end
    C_AuctionHouse.SendSearchQuery=function(key,sorts,owner)
      queries[#queries+1]={id=key.itemID,at=tick,sorts=sorts,owner=owner} end
    C_AuctionHouse.GetNumCommoditySearchResults=function(id) return #(commodityRows[id] or {}) end
    C_AuctionHouse.GetCommoditySearchResultInfo=function(id,i) return (commodityRows[id] or {})[i] end
    C_AuctionHouse.HasFullCommoditySearchResults=function() return full end
    C_AuctionHouse.GetNumItemSearchResults=function(key) return #(itemRows[key.itemID] or {}) end
    C_AuctionHouse.GetItemSearchResultInfo=function(key,i) return (itemRows[key.itemID] or {})[i] end
    C_AuctionHouse.HasFullItemSearchResults=function() return full end
    C_AuctionHouse.RequestMoreCommoditySearchResults=function(id) moreCalls[#moreCalls+1]={id=id,at=tick} end
    ''')
    return c


def advance(c, seconds=1):
    c.lua.globals().runTo(c.lua.globals().tick + seconds)


def commodity(c, id, price=10, quantity=1000, complete=True):
    c.lua.globals().commodityRows[id] = c.lua.table_from([{'unitPrice':price,'quantity':quantity}], recursive=True)
    c.lua.globals().full = complete
    c.ns.handlers.COMMODITY_SEARCH_RESULTS_UPDATED(id)


class AuctionPanelTests(unittest.TestCase):
    def test_panel_is_left_of_auction_house_and_lists_goal_amounts_not_one_batch(self):
        c = market(crafting(skill=20)); c.ns.StartProfessionGuide(171,75); modern(c); c.drain()
        panel = c.ns.auctionGuideToolbar
        self.assertEqual(panel.point[1], 'TOPRIGHT'); self.assertEqual(panel.point[3], 'TOPLEFT')
        self.assertEqual(panel.scan.caption.text, 'Scan auction house')
        self.assertIn('75', panel.goal.caption.text)
        self.assertEqual(panel.forecast.target,75)
        self.assertGreater(panel.materials[1].need,c.ns.selectedRoute.materials[1].need)
        self.assertIn('Buy ~',panel.rows[1].amount.text)
        self.assertEqual(len(c.lua.globals().ahSearches),0)
        panel.rows[1].search.OnClick()
        self.assertEqual(c.lua.globals().ahSearches[1].name,'Herbs')

    def test_goal_dropdown_changes_active_goal_without_crafting_or_buying(self):
        c = scanner(); panel = c.ns.auctionGuideToolbar
        c.ns.StartAuctionGuideScan(); advance(c)
        # The real dropdown's choices dispatch this same callback.
        option = panel.goal.options[150]
        option.OnClick(); advance(c)
        self.assertEqual(c.ns.routeSelection.targetSkill,150)
        self.assertEqual(c.ns.ProfessionGoal(171),150)
        self.assertIsNone(c.ns.AuctionScanState())

    def test_bags_deduct_once_and_intermediate_outputs_are_reused_for_goal(self):
        c = market(leatherworking(skill=1)); c.lua.globals().stock[2934] = 15
        c.ns.StartProfessionGuide(165,75); modern(c); c.drain()
        panel = c.ns.auctionGuideToolbar
        self.assertEqual(panel.forecast.target,75)
        for item in panel.materials.values():
            self.assertGreaterEqual(item.missing,0)
            self.assertIn(str(item.missing), next(r.amount.text for r in panel.rows.values() if r.itemID==item.itemID))

    def test_native_auction_frame_is_nudged_only_if_needed_then_restored(self):
        c = market(crafting()); c.ns.StartProfessionGuide(171,75)
        c.lua.execute('''
        function UIParent:GetWidth() return 1600 end
        function UIParent:GetEffectiveScale() return 1 end
        AuctionHouseFrame=CreateFrame('Frame');AuctionHouseFrame:Show();AuctionHouseFrame:SetSize(800,480)
        function AuctionHouseFrame:GetLeft() return 16 end
        function AuctionHouseFrame:GetTop() return 800 end
        function AuctionHouseFrame:GetEffectiveScale() return 1 end
        function AuctionHouseFrame:GetNumPoints() return 1 end
        function AuctionHouseFrame:GetPoint() return 'TOPLEFT',UIParent,'TOPLEFT',16,-100 end
        ''')
        c.ns.handlers.AUCTION_HOUSE_SHOW(); c.drain()
        native = c.lua.globals().AuctionHouseFrame
        self.assertEqual(native.point[3], 'BOTTOMLEFT'); self.assertEqual(native.point[4],338)
        c.lua.globals().combat = True; c.ns.handlers.AUCTION_HOUSE_CLOSED()
        self.assertEqual(native.point[4],338)
        c.lua.globals().combat = False; c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertEqual(native.point[3], 'TOPLEFT'); self.assertEqual(native.point[4],16)


class MarketTests(unittest.TestCase):
    def test_intermediate_is_made_when_raw_cost_and_craft_time_beat_buying(self):
        c = market(leatherworking(skill=20))
        recipe = next(r for r in c.ns.ProfessionFacts(165).recipes.values() if r.id==2152)
        c.ns.StoreAuctionQuote(2934,c.lua.table_from([[1,100]],recursive=True),True)
        c.ns.StoreAuctionQuote(2318,c.lua.table_from([[1000,100]],recursive=True),True)
        rows, cost, prep, incomplete = c.ns.ProfessionMaterials(165,recipe,2,20,True)
        self.assertEqual(prep[1].recipe.id,2881)
        self.assertEqual(prep[1].crafts,2)
        self.assertEqual({r.itemID:r.missing for r in rows.values()},{2934:6})
        self.assertEqual(cost,6)
        c.ns.StoreAuctionQuote(2318,c.lua.table_from([[1,100]],recursive=True),True)
        rows, cost, prep, incomplete = c.ns.ProfessionMaterials(165,recipe,2,20,True)
        self.assertEqual(len(prep),0)
        self.assertEqual({r.itemID:r.missing for r in rows.values()},{2318:2})
        self.assertEqual(cost,2)

    def test_saved_prices_restore_on_a_new_client_and_unknown_login_faction_does_not_erase_them(self):
        c = market(crafting())
        c.ns.StoreAuctionQuote(100,c.lua.table_from([[12,200]],recursive=True),True)
        saved = plain(c.ns.db)
        other = Client(quests=(),saved_variables=saved,before_load='''
          function GetServerTime() return 100010 end
          function UnitLevel() return 20 end
          function UnitFactionGroup() return nil end''')
        self.assertEqual(other.ns.professionSaved.market.quotes[100].unitPrice,12)
        self.assertIsNone(other.ns.AuctionQuote(100))
        other.lua.execute("function UnitFactionGroup() return 'Horde' end")
        other.ns.handlers.PLAYER_LOGIN()
        self.assertEqual(other.ns.AuctionUnitPrice(100,1),(12,True))
        self.assertTrue(other.ns.marketQuotes[100].cached)

    def test_quote_book_prices_quantity_and_does_not_assume_cheapest_stack_covers_all(self):
        c = scanner()
        c.lua.globals().commodityRows[100] = c.lua.table_from([
            {'unitPrice':20,'quantity':20},{'unitPrice':5,'quantity':2}],recursive=True)
        c.ns.ReadCommodityAuctions(100)
        self.assertEqual(c.ns.AuctionUnitPrice(100,10),(17,True))
        self.assertEqual(c.ns.AuctionUnitPrice(100,30),(5,False))
        self.assertEqual(c.ns.marketQuotes[100].quantity,22)

    def test_prices_save_restore_only_same_realm_faction_build_and_expire(self):
        c = market(crafting())
        c.ns.StoreAuctionQuote(100,c.lua.table_from([[12,200]],recursive=True),True)
        self.assertEqual(c.ns.professionSaved.market.quotes[100].unitPrice,12)
        c.ns.marketQuotes = c.lua.table(); c.ns.InitializeAuctionMarket()
        self.assertEqual(c.ns.auctionMarketRestored,1)
        self.assertTrue(c.ns.marketQuotes[100].cached)
        c.lua.globals().serverClock = 121601
        self.assertIsNone(c.ns.AuctionQuote(100))
        self.assertIsNone(c.ns.AuctionUnitPrice(100))
        c.lua.globals().serverClock = 100001
        c.ns.profile.faction = 'Alliance'; c.ns.InitializeAuctionMarket()
        self.assertIsNone(c.ns.AuctionQuote(100))
        self.assertEqual(len(c.ns.professionSaved.market.quotes),0)

    def test_expired_saved_price_does_not_leak_through_planner_fallback(self):
        c = market(crafting()); c.lua.globals().stock[100] = 0
        c.ns.StoreAuctionQuote(100,c.lua.table_from([[12,200]],recursive=True),True)
        c.lua.globals().serverClock = 121601
        c.ns.professionRevision = c.ns.professionRevision+1
        c.ns.StartProfessionGuide(171,75)
        self.assertIsNone(c.ns.selectedRoute.estimatedCost)

    def test_empty_full_response_clears_price_and_private_rows_cannot_create_quote(self):
        c = scanner(); commodity(c,100,10)
        c.lua.globals().commodityRows[100] = c.lua.table()
        c.ns.ReadCommodityAuctions(100)
        self.assertTrue(c.ns.AuctionQuote(100).unavailable)
        self.assertIsNone(c.ns.AuctionUnitPrice(100))
        c.lua.globals().commodityRows[101] = c.lua.table_from([
            {'unitPrice':c.lua.globals().secret,'quantity':100}],recursive=True)
        c.ns.ReadCommodityAuctions(101)
        self.assertIsNone(c.ns.AuctionQuote(101))

    def test_own_item_auctions_and_secret_suffixes_are_not_material_prices(self):
        c = scanner()
        c.lua.globals().itemRows[100] = c.lua.table_from([
            {'buyoutAmount':100,'quantity':5,'containsOwnerItem':True},
            {'buyoutAmount':200,'quantity':5}],recursive=True)
        c.ns.ReadItemAuctions(c.lua.table_from({'itemID':100}))
        self.assertEqual(c.ns.AuctionUnitPrice(100,1),(40,True))
        c.ns.ReadItemAuctions(c.lua.table_from({'itemID':101,'itemSuffix':c.lua.globals().secret}))
        self.assertIsNone(c.ns.AuctionQuote(101))

    def test_cache_is_bounded_and_keeps_latest_prices(self):
        c = market(crafting())
        for id in range(1000,1260):
            c.lua.globals().serverClock += 1
            c.ns.StoreAuctionQuote(id,c.lua.table_from([[10,1]],recursive=True),True)
        self.assertEqual(len(list(c.ns.professionSaved.market.quotes.keys())),256)
        self.assertIsNone(c.ns.professionSaved.market.quotes[1000])
        self.assertIsNotNone(c.ns.professionSaved.market.quotes[1259])


class AuctionScanTests(unittest.TestCase):
    def test_priced_recipe_is_preferred_to_an_unknown_price_heuristic(self):
        c = scanner()
        commodity(c,101,10000)
        advance(c)
        self.assertEqual(c.ns.selectedRoute.recipe.id,2)
        plan = c.ns.PlanProfessionPreview(171,75,False)
        self.assertEqual({s.recipe.id for s in plan.steps.values()},{2})

    def test_native_cast_time_breaks_equal_cost_ties_toward_faster_recipe(self):
        c = scanner()
        facts = c.ns.ProfessionFacts(171)
        facts.recipes[1].materials[1][2] = 1
        c.lua.execute('''C_TradeSkillUI.GetRecipeSchematic=function(id)
          return {reagentSlotSchematics={{required=true,quantityRequired=1,reagents={{itemID=id==1 and 100 or 101}}}}} end
          C_Spell={GetSpellInfo=function(id) return {castTime=id==1 and 10000 or 1000} end}''')
        commodity(c,100,10); commodity(c,101,10); advance(c)
        self.assertEqual(c.ns.selectedRoute.recipe.id,2)

    def test_scan_prices_alternatives_with_paced_exact_queries_and_updates_path(self):
        c = scanner()
        self.assertEqual(list(c.ns.ProfessionMarketItems(171,75,False).values()),[100,101])
        self.assertEqual(len(c.lua.globals().queries),0)
        c.ns.StartAuctionGuideScan(); advance(c)
        queries = c.lua.globals().queries
        self.assertEqual(queries[1].id,100)
        self.assertEqual(queries[1].sorts[1].sortOrder,0)
        self.assertFalse(queries[1].sorts[1].reverseSort)
        self.assertFalse(queries[1].owner)
        commodity(c,101,1)  # Unrelated arrival cannot finish the pending 100 query.
        self.assertEqual(c.ns.AuctionScanState().done,0)
        commodity(c,100,10000); advance(c)
        self.assertEqual(queries[2].id,101)
        self.assertGreaterEqual(queries[2].at-queries[1].at,1)
        commodity(c,101,1); advance(c)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertEqual(c.ns.auctionScanSummary.priced,2)
        self.assertEqual(c.ns.selectedRoute.recipe.id,2)
        self.assertEqual(c.ns.auctionGuideToolbar.forecast.target,75)
        self.assertEqual(c.ns.professionSaved.market.quotes[101].unitPrice,1)

    def test_busy_server_waits_then_sends_one_request_and_never_overlaps(self):
        c = scanner(); c.lua.globals().ahBusy = True
        c.ns.StartAuctionGuideScan(); advance(c,5)
        self.assertEqual(len(c.lua.globals().queries),0)
        c.lua.globals().ahBusy = False; advance(c)
        self.assertEqual(len(c.lua.globals().queries),1)
        advance(c,5)
        self.assertEqual(len(c.lua.globals().queries),1)

    def test_partial_results_fetch_at_most_three_pages(self):
        c = scanner(); c.ns.StartAuctionGuideScan(); advance(c)
        commodity(c,100,10,10,False); advance(c)
        commodity(c,100,10,10,False); advance(c)
        commodity(c,100,10,10,False); advance(c)
        self.assertEqual(len(c.lua.globals().moreCalls),2)
        self.assertEqual(c.lua.globals().queries[2].id,101)
        self.assertFalse(c.ns.marketQuotes[100].complete)

    def test_close_manual_search_and_goal_change_cancel_remaining_requests(self):
        for action in ('close','manual','goal'):
            with self.subTest(action=action):
                c = scanner(); c.ns.StartAuctionGuideScan(); advance(c)
                if action=='close': c.ns.handlers.AUCTION_HOUSE_CLOSED()
                elif action=='manual': c.ns.SearchGuideAuctionItem(101)
                else: c.ns.routeSelection.targetSkill = 150
                commodity(c,100,10); advance(c,30)
                self.assertIsNone(c.ns.AuctionScanState())
                self.assertEqual(len(c.lua.globals().queries),1)

    def test_hidden_native_auction_window_stops_even_without_closed_event(self):
        c = scanner(); c.ns.StartAuctionGuideScan(); advance(c)
        c.lua.globals().AuctionHouseFrame.Hide(c.lua.globals().AuctionHouseFrame)
        commodity(c,100,10); advance(c,30)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertEqual(len(c.lua.globals().queries),1)

    def test_combat_pauses_queries_and_resumes_from_same_item(self):
        c = scanner(); c.ns.StartAuctionGuideScan(); c.lua.globals().combat = True
        advance(c,2); self.assertEqual(len(c.lua.globals().queries),0)
        c.lua.globals().combat = False; c.ns.handlers.PLAYER_REGEN_ENABLED(); advance(c)
        self.assertEqual(c.lua.globals().queries[1].id,100)
        c.lua.globals().combat = True; commodity(c,100,10); advance(c)
        self.assertEqual(len(c.lua.globals().queries),1)
        c.lua.globals().combat = False; c.ns.handlers.PLAYER_REGEN_ENABLED(); advance(c)
        self.assertEqual(c.lua.globals().queries[2].id,101)

    def test_timeout_unsupported_api_and_dropped_results_do_not_guess_prices(self):
        c = scanner(); c.ns.StartAuctionGuideScan(); advance(c,45)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertEqual(c.ns.auctionScanSummary.priced,0)
        self.assertEqual(c.ns.auctionScanSummary.requests,2)
        self.assertIsNone(c.ns.AuctionUnitPrice(100))
        c = scanner(); c.lua.execute('C_AuctionHouse.SendSearchQuery=nil')
        c.ns.StartAuctionGuideScan(); advance(c)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertIn('Scan unavailable',c.ns.auctionScanStatus)

    def test_press_scan_again_stops_and_browsing_is_not_hijacked(self):
        c = scanner(); c.ns.StartAuctionGuideScan(); advance(c)
        c.ns.StartAuctionGuideScan(); advance(c,30)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertEqual(len(c.lua.globals().queries),1)
        c.ns.StartAuctionGuideScan(); advance(c)
        c.ns.handlers.AUCTION_HOUSE_BROWSE_RESULTS_UPDATED(); advance(c,30)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertEqual(len(c.lua.globals().queries),2)

    def test_market_scan_excludes_locked_drop_and_incompatible_profession_recipes(self):
        c = scanner(goal=75)
        facts = c.ns.ProfessionFacts(171)
        facts.recipes[4] = c.lua.table_from({'id':4,'name':'Enemy recipe','learn':1,'grey':100,
            'source':'trainer','faction':'Alliance','materials':[[999,1]]},recursive=True)
        facts.recipes[5] = c.lua.table_from({'id':5,'name':'Later recipe','learn':150,'grey':200,
            'source':'trainer','materials':[[998,1]]},recursive=True)
        self.assertEqual(list(c.ns.ProfessionMarketItems(171,75,False).values()),[100,101])


if __name__ == '__main__': unittest.main()
