"""Recipe shopping partitions, safe quantity filling and stalled AH recovery."""
import unittest

from test_0836 import crafting
from test_0837 import leatherworking
from test_0838 import forecast, modern
from test_0840 import scanner, market, advance, commodity


class RecipeShoppingTests(unittest.TestCase):
    def test_boxes_keep_crafting_order_and_share_the_bag_ledger(self):
        c = crafting(); c.lua.globals().stock[100] = 5
        recipes = c.ns.ProfessionFacts(171).recipes
        result = forecast(c, [{'recipe': recipes[1], 'start': 20, 'finish': 25, 'crafts': 3},
                              {'recipe': recipes[2], 'start': 25, 'finish': 29, 'crafts': 4}])
        a, b = result.groups[1], result.groups[2]
        self.assertEqual((a.recipeID, b.recipeID), (1, 2))
        self.assertEqual((a.start, a.finish, a.crafts), (20, 25, 3))
        self.assertEqual((a.materials[1].missing, b.materials[1].missing), (1, 4))
        self.assertEqual(a.materials[1].missing + b.materials[1].missing, result.materials[1].missing)

    def test_recipe_box_explains_intermediate_preparations_without_double_purchase(self):
        c = market(leatherworking(skill=20))
        recipe = next(r for r in c.ns.ProfessionFacts(165).recipes.values() if r.id == 2152)
        plan = c.lua.table_from({'steps': [{'recipe': recipe, 'crafts': 2, 'start': 20, 'finish': 22}],
                                'start': 20, 'target': 22, 'missing': 0}, recursive=True)
        c.ns.StoreAuctionQuote(2934, c.lua.table_from([[1, 100]], recursive=True), True)
        c.ns.StoreAuctionQuote(2318, c.lua.table_from([[1000, 100]], recursive=True), True)
        result = c.ns.ProfessionMaterialForecast(165, plan, False)
        group = result.groups[1]
        self.assertEqual(group.preparations[1].recipe.id, 2881)
        self.assertEqual(group.estimatedCost, 6)
        self.assertEqual({r.itemID: r.missing for r in group.materials.values()}, {2934: 6})
        self.assertEqual(result.estimatedCost, 6)

    def test_unknown_bags_remain_unknown_in_each_recipe_box(self):
        c = crafting()
        c.lua.execute('C_Item.GetItemCount=function() return secret end')
        recipes = c.ns.ProfessionFacts(171).recipes
        result = forecast(c, [{'recipe': recipes[1], 'start': 20, 'crafts': 3}])
        self.assertTrue(result.incomplete)
        self.assertIsNone(result.groups[1].materials[1].missing)
        self.assertIsNone(result.groups[1].estimatedCost)

    def test_box_search_uses_its_part_not_the_total_and_collapsing_is_persistent(self):
        c = market(crafting(skill=20)); c.ns.StartProfessionGuide(171, 75); modern(c); c.drain()
        panel = c.ns.auctionGuideToolbar
        self.assertGreater(len(panel.groups), 1)
        first = panel.groups[1]
        self.assertIn(first.data.name, first.toggle.caption.text)
        self.assertLess(panel.rows[1].quantity, panel.materials[1].missing)
        panel.rows[1].search.OnClick()
        self.assertIn(str(panel.rows[1].quantity), panel.status.text)
        self.assertEqual(c.lua.globals().ahSearches[1].name, 'Herbs')
        key = first.key
        first.toggle.OnClick()
        self.assertTrue(panel.collapsed[key])
        self.assertTrue(first.toggle.caption.text.startswith('+ '))
        c.ns.RefreshAuctionGuideSearch()
        self.assertTrue(panel.collapsed[key])
        first.toggle.OnClick()
        self.assertFalse(panel.collapsed[key])
        self.assertTrue(first.toggle.caption.text.startswith('− '))

    def test_prices_update_recipe_boxes_and_bag_changes_reduce_purchases(self):
        c = scanner(); c.ns.StoreAuctionQuote(101, c.lua.table_from([[10, 1000]], recursive=True), True)
        advance(c, 1)
        panel = c.ns.auctionGuideToolbar
        self.assertTrue(any(g.data.estimatedCost is not None for g in panel.groups.values() if g.shown))
        before = panel.materials[1].missing
        c.lua.globals().stock[panel.materials[1].itemID] = 5
        c.ns.handlers.BAG_UPDATE_DELAYED(); advance(c, 1)
        self.assertEqual(panel.materials[1].missing, max(0, before - 5))


class QuantityTests(unittest.TestCase):
    def fixture(self):
        c = scanner()
        c.lua.execute('''
        display=CreateFrame('Frame'); display:Show(); display.itemID=100
        display.resultsLoaded=true; display.quantity=1; quantityCalls={}
        display.GetItemID=function(self) return self.itemID end
        display.GetQuantitySelected=function(self) return self.quantity end
        display.SetQuantitySelected=function(self,value)
          quantityCalls[#quantityCalls+1]=value; self.quantity=math.min(value,available or 1000) end
        AuctionHouseFrame.CommoditiesBuyFrame={BuyDisplay=display}
        C_AuctionHouse.StartCommoditiesPurchase=function() error('must not buy') end
        C_AuctionHouse.ConfirmCommoditiesPurchase=function() error('must not confirm') end
        ''')
        return c

    def test_fill_once_after_matching_selection_and_keep_later_edits(self):
        c = self.fixture(); self.assertTrue(c.ns.SearchGuideAuctionItem(100, 17))
        c.ns.UpdateGuideAuctionQuantity(.3)
        self.assertEqual(c.lua.globals().display.quantity, 17)
        c.lua.globals().display.quantity = 3
        c.ns.UpdateGuideAuctionQuantity(.3)
        self.assertEqual(c.lua.globals().display.quantity, 3)
        self.assertEqual(len(c.lua.globals().quantityCalls), 1)

    def test_wait_for_exact_selected_item_and_results_without_prefilling_other_item(self):
        c = self.fixture(); c.lua.globals().display.itemID = 101
        c.ns.SearchGuideAuctionItem(100, 17); c.ns.UpdateGuideAuctionQuantity(.3)
        self.assertEqual(len(c.lua.globals().quantityCalls), 0)
        c.lua.globals().display.itemID = 100; c.lua.globals().display.resultsLoaded = False
        c.ns.UpdateGuideAuctionQuantity(.3)
        self.assertEqual(len(c.lua.globals().quantityCalls), 0)
        c.lua.globals().display.resultsLoaded = True; c.ns.UpdateGuideAuctionQuantity(.3)
        self.assertEqual(c.lua.globals().display.quantity, 17)

    def test_native_stock_clamp_and_new_bags_are_respected(self):
        c = self.fixture(); c.lua.globals().stock[100] = 2
        c.ns.SearchGuideAuctionItem(100, 17)
        c.lua.globals().stock[100] = 7; c.lua.globals().available = 9
        c.ns.UpdateGuideAuctionQuantity(.3)
        self.assertEqual(c.lua.globals().quantityCalls[1], 12)
        self.assertEqual(c.lua.globals().display.quantity, 9)
        self.assertIn('9 / 12', c.ns.auctionQuantityStatus)

    def test_manual_quantity_already_selected_is_kept(self):
        c = self.fixture(); c.ns.SearchGuideAuctionItem(100, 17)
        c.lua.globals().display.quantity = 4; c.ns.UpdateGuideAuctionQuantity(.3)
        self.assertEqual(c.lua.globals().display.quantity, 4)
        self.assertEqual(len(c.lua.globals().quantityCalls), 0)

    def test_combat_protected_display_and_secret_identity_cannot_write_quantity(self):
        for case in ('combat', 'protected', 'secret'):
            with self.subTest(case=case):
                c = self.fixture(); c.ns.SearchGuideAuctionItem(100, 17)
                if case == 'combat': c.lua.globals().combat = True
                elif case == 'protected': c.lua.globals().display.protected = True
                else: c.lua.globals().display.itemID = c.lua.globals().secret
                c.ns.UpdateGuideAuctionQuantity(.3)
                self.assertEqual(len(c.lua.globals().quantityCalls), 0)

    def test_closing_changing_goal_timeout_and_new_scan_clear_pending_quantity(self):
        for case in ('close', 'goal', 'timeout', 'scan'):
            with self.subTest(case=case):
                c = self.fixture(); c.ns.SearchGuideAuctionItem(100, 17)
                if case == 'close': c.ns.handlers.AUCTION_HOUSE_CLOSED()
                elif case == 'goal': c.ns.routeSelection.targetSkill = 150
                elif case == 'timeout': c.ns.UpdateGuideAuctionQuantity(61)
                else: c.ns.StartAuctionGuideScan()
                c.ns.UpdateGuideAuctionQuantity(.3)
                self.assertEqual(len(c.lua.globals().quantityCalls), 0)

    def test_unsupported_quantity_control_and_failed_setter_leave_manual_search_working(self):
        for case in ('absent', 'throws'):
            with self.subTest(case=case):
                c = self.fixture()
                if case == 'absent': c.lua.execute('display.SetQuantitySelected=false')
                else: c.lua.execute("display.SetQuantitySelected=function() error('unsupported beta control') end")
                self.assertTrue(c.ns.SearchGuideAuctionItem(100, 17))
                c.ns.UpdateGuideAuctionQuantity(.3)
                self.assertEqual(c.lua.globals().display.quantity, 1)
                self.assertEqual(c.lua.globals().ahSearches[1].name, 'Herbs')


class ScanRecoveryTests(unittest.TestCase):
    def forty(self, c):
        c.lua.globals().testNS = c.ns
        c.lua.execute('''
        testNS.ProfessionMarketItems=function() local ids={} for i=1,40 do ids[i]=i end return ids end
        C_Item.GetItemInfo=function(id) if id~=10 then return 'Material '..id end end
        C_Item.RequestLoadItemDataByID=function() end
        C_AuctionHouse.SendSearchQuery=function(key,sorts,owner)
          queries[#queries+1]={id=key.itemID,at=tick}
          testNS.AuctionScanResult(key.itemID,'commodity',true,true)
        end
        ''')

    def test_silent_missing_name_at_ten_does_not_strand_forty_item_queue(self):
        c = scanner(); self.forty(c)
        c.ns.StartAuctionGuideScan(); advance(c, 10)
        self.assertIn('Loading material 10/40', c.ns.auctionScanStatus)
        self.assertNotIn('Item 10', c.ns.auctionScanStatus)
        advance(c, 40)
        self.assertIsNone(c.ns.AuctionScanState())
        summary = c.ns.auctionScanSummary
        self.assertEqual((summary.total, summary.priced, summary.skipped), (40, 39, 1))
        self.assertEqual(summary.failures[1].itemID, 10)
        self.assertEqual(len(c.lua.globals().queries), 39)
        self.assertNotIn(10, [q.id for q in c.lua.globals().queries.values()])

    def test_failed_item_loader_and_invalid_item_key_advance_safely(self):
        for case in ('loader', 'key', 'query_throw', 'query_false'):
            with self.subTest(case=case):
                c = scanner(); self.forty(c)
                if case == 'loader':
                    c.lua.execute("C_Item.RequestLoadItemDataByID=function() error('invalid item ID') end")
                else:
                    c.lua.execute("C_Item.GetItemInfo=function(id) return 'Material '..id end")
                    if case == 'key':
                        c.lua.execute('C_AuctionHouse.MakeItemKey=function(id) if id~=10 then return {itemID=id} end end')
                    else:
                        c.lua.execute('''local send=C_AuctionHouse.SendSearchQuery
                        C_AuctionHouse.SendSearchQuery=function(key,...)
                          if key.itemID==10 then ''' + ("error('invalid key')" if case=='query_throw' else 'return false') + ''' end
                          return send(key,...) end''')
                c.ns.StartAuctionGuideScan(); advance(c, 60)
                self.assertIsNone(c.ns.AuctionScanState())
                self.assertEqual((c.ns.auctionScanSummary.total, c.ns.auctionScanSummary.skipped), (40, 1))
                self.assertEqual(c.ns.auctionScanSummary.failures[1].itemID, 10)

    def test_silent_search_event_loss_is_counted_and_queue_continues(self):
        c = scanner(); self.forty(c)
        c.lua.execute('''C_Item.GetItemInfo=function(id) return 'Material '..id end
          local send=C_AuctionHouse.SendSearchQuery
          C_AuctionHouse.SendSearchQuery=function(key,...) if key.itemID~=10 then return send(key,...) end end''')
        c.ns.StartAuctionGuideScan(); advance(c, 11)
        self.assertIn('waiting', c.ns.auctionScanStatus)
        advance(c, 60)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertEqual(c.ns.auctionScanSummary.skipped, 1)
        self.assertIn('20 seconds', c.ns.auctionScanSummary.failures[1].reason)

    def test_metadata_arriving_during_load_wait_is_queried_normally(self):
        c = scanner()
        c.lua.execute('''C_Item.GetItemInfo=function(id) if loaded or id~=100 then return 'Material '..id end end
          C_Item.RequestLoadItemDataByID=function() end''')
        c.ns.StartAuctionGuideScan(); advance(c, 2)
        self.assertEqual(len(c.lua.globals().queries), 0)
        c.lua.globals().loaded = True; c.ns.handlers.ITEM_DATA_LOAD_RESULT(100, True)
        advance(c, 1)
        self.assertEqual(c.lua.globals().queries[1].id, 100)
        commodity(c, 100); advance(c); commodity(c, 101)
        self.assertEqual(c.ns.auctionScanSummary.priced, 2)

    def test_panel_failure_cannot_prevent_timeout_or_request_progress(self):
        c = scanner()
        c.lua.globals().auctionTest = c.ns
        c.lua.execute('''local refresh=auctionTest.RefreshAuctionGuideSearch
          auctionTest.RefreshAuctionGuideSearch=function()
            if auctionTest.AuctionScanState() then error('UI refresh failure') end
            return refresh() end''')
        c.ns.StartAuctionGuideScan(); advance(c, 45)
        self.assertIsNone(c.ns.AuctionScanState())
        self.assertEqual(c.ns.auctionScanSummary.skipped, 2)
        self.assertIn('UI refresh failure', c.ns.auctionScanUIError)

    def test_old_timeout_does_not_advance_another_item_or_pagination_request(self):
        c = scanner(); c.ns.StartAuctionGuideScan(); advance(c)
        commodity(c, 100, complete=False); advance(c, 10)
        commodity(c, 100, complete=False); advance(c, 10)
        self.assertEqual(c.ns.AuctionScanState().done, 0)
        self.assertEqual(c.ns.AuctionScanState().waiting.pages, 3)
        commodity(c, 100); advance(c); commodity(c, 101); advance(c, 30)
        self.assertEqual((c.ns.auctionScanSummary.total, c.ns.auctionScanSummary.priced), (2, 2))
        self.assertEqual(c.ns.auctionScanSummary.skipped, 0)

    def test_loading_and_timeout_failures_keep_existing_price_and_never_guess_zero(self):
        c = scanner(); c.ns.StoreAuctionQuote(100, c.lua.table_from([[12, 200]], recursive=True), True)
        c.lua.execute('''C_Item.GetItemInfo=function(id) if id==101 then return 'Other Herb' end end
          C_Item.RequestLoadItemDataByID=function() end''')
        c.ns.StartAuctionGuideScan(); advance(c, 45)
        self.assertEqual(c.ns.AuctionUnitPrice(100, 1), (12, True))
        self.assertIsNone(c.ns.AuctionUnitPrice(101))
        self.assertEqual(c.ns.auctionScanSummary.skipped, 2)

    def test_failed_item_load_notification_is_safe_and_a_new_scan_can_retry(self):
        c = scanner()
        c.lua.execute('''C_Item.GetItemInfo=function(id) if id==101 then return 'Other Herb' end end
          C_Item.RequestLoadItemDataByID=function() end''')
        c.ns.StartAuctionGuideScan(); advance(c)
        c.ns.handlers.ITEM_DATA_LOAD_RESULT(100, False); advance(c)
        self.assertEqual(c.ns.AuctionScanState().done, 1)
        c.ns.CancelAuctionScan()
        c.lua.execute("C_Item.GetItemInfo=function(id) return 'Material '..id end")
        c.ns.StartAuctionGuideScan(); advance(c)
        self.assertEqual(c.lua.globals().queries[1].id, 100)

    def test_stopping_scan_keeps_partial_failure_evidence_for_probe(self):
        c = scanner(); self.forty(c)
        c.ns.StartAuctionGuideScan(); advance(c, 16)
        c.ns.CancelAuctionScan()
        self.assertTrue(c.ns.auctionScanSummary.cancelled)
        self.assertEqual(c.ns.auctionScanSummary.failures[1].itemID, 10)
        self.assertLess(c.ns.auctionScanSummary.done, c.ns.auctionScanSummary.total)


if __name__ == '__main__':
    unittest.main()
