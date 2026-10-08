"""Inventory-aware optional vendor detours; public synthetic client data only."""
import unittest

from test_addon import Client
from test_navigation import navigator
from test_routes import map_canvas, catalogue, quest, guide
from test_063 import primitive


INVENTORY = r'''
clock=1; function GetTime()return clock end
function UnitOnTaxi()return false end; function UnitIsGhost()return false end
function UnitGUID() return 'Creature-0-1-2-3-'..vendorID..'-ABC' end
function UnitName() return 'Test vendor '..vendorID end
vendorID=700; repairShop=true; durability=20
function CanMerchantRepair()return repairShop end
function GetInventoryItemDurability(slot) if slot==1 then return durability,100 end end
bags = {[0]={slots=16,free=2,family=0,items={}}, [1]={slots=10,free=10,family=32,items={}}}
bagReads=0
C_Container={
    GetContainerNumSlots=function(bag) bagReads=bagReads+1; return bags[bag] and bags[bag].slots or 0 end,
    GetContainerNumFreeSlots=function(bag) return bags[bag].free,bags[bag].family end,
    GetContainerItemInfo=function(bag,slot) return bags[bag].items[slot] end,
    GetContainerItemID=function(bag,slot) local i=bags[bag].items[slot]; return i and i.itemID end,
}
stock={{id=4541,available=-1}, {id=1179,available=-1}}
function GetMerchantNumItems()return #stock end
function GetMerchantItemLink(slot) return '|Hitem:'..stock[slot].id..'|h[Supply]|h' end
C_MerchantFrame={GetItemInfo=function(slot)return {numAvailable=stock[slot].available,
    hasExtendedCost=stock[slot].extended or false, isPurchasable=true} end}
C_Item={GetItemInfo=function(id) return 'Supply '..id end}
function BuyMerchantItem()error('unexpected purchase')end
function RepairAllItems()error('unexpected repair')end
function UseContainerItem()error('unexpected sale')end
'''


def service_client(c=None):
    if c is None:
        c = navigator(.31, .37)
    else:
        c.guide_environment(level=12)
        c.lua.execute('C_Map.GetMapWorldSize=function()return 1000,1000 end; function GetPlayerFacing()return 0 end')
        catalogue(c, {900: quest()})
        c.ns.routeSelection = guide(c)
        c.ns.selectedRoute = c.lua.table_from({'mapID':501,'stops':[dict(id=900,kind='a',title='Pickup quest',mapID=501,x=.31,y=.37)]},recursive=True)
    c.lua.execute(INVENTORY)
    c.ns.profile.level, c.ns.profile.classID = 12, 8
    c.ns.db.config.classTraining = False
    c.ns.db.config.nearbyFlights = False
    c.ns.db.config.hearthstoneTips = False
    c.ns.db.config.travelNetwork = False
    c.ns.routeSelection.mode = 'zone'
    c.ns.ReadServiceInventory()
    return c


def visit(c, vendor=700, x=.23, repair=True):
    c.lua.globals().vendorID = vendor
    c.lua.globals().repairShop = repair
    c.lua.execute(f'C_Map.GetPlayerMapPosition=function()return {{GetXY=function()return {x},.37 end}} end')
    c.ns.handlers.MERCHANT_SHOW()
    c.drain()
    c.ns.handlers.MERCHANT_CLOSED()
    c.drain()
    c.lua.execute('C_Map.GetPlayerMapPosition=function()return {GetXY=function()return .21,.37 end} end; clock=clock+2')
    c.ns.UpdateNavigation()


class InventoryServiceTests(unittest.TestCase):
    def test_only_regular_bag_slots_count_and_no_bank_is_scanned(self):
        c = service_client()
        self.assertEqual(c.ns.serviceInventory.free, 2)
        self.assertEqual(c.ns.serviceInventory.slots, 16)
        c.lua.execute('bags[1].family=0')
        c.ns.ReadServiceInventory()
        self.assertEqual(c.ns.serviceInventory.free, 12)
        c.lua.execute('C_Container.GetContainerNumSlots=function(bag)assert(bag>=0 and bag<=4); return 0 end')
        c.ns.ReadServiceInventory()
        self.assertIsNone(c.ns.serviceInventory.free)

    def test_vendor_advice_requires_an_actual_visit(self):
        c = service_client()
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.guideServiceData.inns = c.lua.table_from([dict(id='inn',name='Inn',mapID=501,x=.23,y=.37,faction='Horde')],recursive=True)
        self.assertIsNone(c.ns.CurrentGuideTip())
        visit(c)
        value = c.ns.CurrentGuideTip()
        self.assertEqual(value.kind, 'service')
        self.assertIn('2 bag slots free', value.text)
        self.assertIn('Gear at 20%', value.text)
        self.assertIn('Buy ~20 Supply', value.detail)

    def test_click_detour_and_done_preserve_quest_order_credit_and_skips(self):
        c = service_client(); visit(c)
        before = primitive(c.ns.selectedRoute)
        c.ns.navigation.tip.OnMouseUp(c.ns.navigation.tip, 'LeftButton')
        self.assertEqual(c.ns.navigation.state.stop.kind, 'service')
        self.assertIn('Sell items', c.ns.navigation.context.text)
        self.assertEqual(c.ns.navigation.skipQuest.caption.text, 'Done')
        self.assertFalse(c.ns.navigation.back.IsEnabled(c.ns.navigation.back))
        self.assertEqual(primitive(c.ns.selectedRoute), before)
        c.ns.navigation.skipQuest.OnClick()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertIsNone(c.ns.CurrentGuideTip())
        self.assertEqual(primitive(c.ns.selectedRoute), before)
        self.assertFalse(c.ns.GuideQuestSkipped(900)); self.assertFalse(c.ns.Completed(900))

    def test_skip_visit_never_creates_a_quest_skip_or_research_event(self):
        c = service_client(); visit(c)
        c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip())
        before = primitive(c.ns.db.questResearch)
        c.ns.navigation.skipStep.OnClick()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertEqual(primitive(c.ns.db.questResearch), before)

    def test_small_arrow_can_accept_finish_and_dismiss(self):
        c = service_client(); visit(c)
        c.ns.db.config.routeArrow, c.ns.db.config.standaloneArrow = False, True
        c.ns.UpdateNavigation(); small = c.ns.standaloneNavigation
        self.assertTrue(small.tip.IsShown(small.tip))
        small.tip.OnMouseUp(small.tip, 'LeftButton')
        self.assertEqual(small.state.stop.kind, 'service')
        self.assertTrue(small.training.IsShown(small.training))
        small.training.done.OnClick()
        self.assertEqual(small.state.stop.id, 900)
        self.assertFalse(small.training.IsShown(small.training))

    def test_map_adds_optional_stop_without_mutating_the_original_route(self):
        c = service_client(); visit(c); map_canvas(c)
        before = primitive(c.ns.selectedRoute)
        c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip())
        display = c.ns.RouteForDisplay()
        self.assertEqual(display.stops[1].kind, 'service')
        self.assertEqual(display.stops[2].id, 900)
        self.assertEqual(primitive(c.ns.selectedRoute), before)

    def test_dismissal_lasts_until_recovery_then_can_warn_again(self):
        c = service_client(); visit(c)
        c.ns.db.config.restockSupplies = False
        c.ns.UpdateNavigation(); c.ns.navigation.tip.close.OnClick()
        c.lua.execute('bags[0].free=1; durability=10; clock=clock+2')
        c.ns.ReadServiceInventory()
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.lua.execute('bags[0].free=8; durability=100')
        c.ns.ReadServiceInventory()
        c.lua.execute('bags[0].free=1; durability=10')
        c.ns.ReadServiceInventory()
        self.assertIsNotNone(c.ns.CurrentGuideTip())

    def test_needs_recover_automatically_without_replanning_the_guide(self):
        c = service_client(); visit(c); c.ns.db.config.restockSupplies = False
        c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip())
        c.lua.execute('bags[0].free=7; durability=90')
        c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertIsNone(c.ns.db.inventoryServiceCharacters[c.ns.self].pending)

    def test_food_counts_usable_tier_only_and_drink_is_for_mana_classes(self):
        c = service_client(); visit(c)
        c.lua.execute('bags[0].free=10; durability=100; bags[0].items[1]={itemID=4541,stackCount=20}; bags[0].items[2]={itemID=1179,stackCount=2}')
        c.ns.ReadServiceInventory()
        self.assertFalse(c.ns.CurrentGuideTip().needs.food)
        self.assertTrue(c.ns.CurrentGuideTip().needs.drink)
        c.ns.profile.classID = 1
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.profile.level = 25
        c.ns.ReadServiceInventory()
        self.assertEqual(c.ns.serviceInventory.food, 0)
        # A visited low-tier vendor cannot be proposed to restock obsolete food.
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_accepted_restock_keeps_remaining_amount_until_the_selected_target(self):
        c = service_client(); visit(c)
        c.lua.execute('bags[0].free=10; durability=100')
        c.ns.ReadServiceInventory(); c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip())
        c.lua.execute('bags[0].items[1]={itemID=4541,stackCount=6}; bags[0].items[2]={itemID=1179,stackCount=20}')
        c.ns.ReadServiceInventory(); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'service')
        self.assertIn('Buy ~14', c.ns.navigation.context.text)
        c.lua.execute('bags[0].items[1].stackCount=20')
        c.ns.ReadServiceInventory(); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)

    def test_no_repairs_at_nonrepair_vendor_and_unavailable_stock_is_not_recommended(self):
        c = service_client(); c.lua.execute('bags[0].free=10')
        c.ns.ReadServiceInventory(); visit(c, repair=False)
        value = c.ns.CurrentGuideTip()
        self.assertIsNone(value.needs.repair)
        c.lua.execute('stock[1].available=0; stock[2].extended=true')
        visit(c, repair=False)
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_nearest_vendor_with_needed_services_wins_and_empty_match_is_safe(self):
        c = service_client(); visit(c,701,.24,False); visit(c,702,.23,True)
        self.assertEqual(c.ns.CurrentGuideTip().place.npcID, 702)
        c.lua.execute('bags[0].free=10; durability=100; bags[0].items[1]={itemID=4541,stackCount=20}; bags[0].items[2]={itemID=1179,stackCount=20}')
        c.ns.ReadServiceInventory()
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_range_and_added_walking_prevent_far_or_backward_detours(self):
        c = service_client(); visit(c,701,.05,True)  # 320 yards round trip added; exceeds 150.
        self.assertIsNone(c.ns.CurrentGuideTip())
        visit(c,702,.80,True)  # Near neither character nor next quest.
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_hostile_crossing_is_rejected_even_for_an_observed_friendly_vendor(self):
        c = service_client(); visit(c)
        c.ns.travelData.settlements = c.lua.table_from([dict(name='Enemy',faction='Alliance',mapID=501,
            minX=.218,maxX=.222,minY=.30,maxY=.40)],recursive=True)
        c.lua.globals().clock += 2
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_faction_build_and_realm_scope_do_not_reuse_another_worlds_vendor(self):
        c = service_client(); visit(c)
        c.ns.profile.faction = 'Alliance'
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.profile.faction = 'Horde'
        c.lua.execute('function GetBuildInfo()return "1.60.1","OTHER","test",16001 end')
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_combat_flight_ghost_scans_and_previews_suspend_detours(self):
        c = service_client(); visit(c)
        value = c.ns.CurrentGuideTip()
        for code in ('combat=true', 'function UnitOnTaxi()return true end', 'function UnitIsGhost()return true end'):
            c.lua.execute(code)
            self.assertIsNone(c.ns.CurrentGuideTip())
            self.assertFalse(c.ns.AcceptInventoryServiceTip(value))
            c.lua.execute('combat=false; function UnitOnTaxi()return false end; function UnitIsGhost()return false end')
        for key in ('guideScanning','routePlanning','navigationPreview'):
            c.ns[key] = c.lua.table_from({'guide': c.ns.routeSelection})
            self.assertIsNone(c.ns.CurrentGuideTip())
            self.assertFalse(c.ns.AcceptInventoryServiceTip(value))
            c.ns[key] = None

    def test_pending_visit_survives_reload_but_stop_or_different_guide_clears_it(self):
        c = service_client(); visit(c); c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip())
        saved = primitive(c.lua.globals().WowTogetherDB)
        fresh = service_client(Client(quests=(),saved_variables=saved))
        # Install the same synthetic route after the new client's initialization.
        fresh.ns.UpdateNavigation()
        self.assertEqual(fresh.ns.navigation.state.stop.kind, 'service')
        fresh.ns.StopGuide(False)
        self.assertIsNone(fresh.ns.db.inventoryServiceCharacters[fresh.ns.self].pending)
        c.ns.routeSelection.key = 'other-zone'
        self.assertIsNone(c.ns.CurrentInventoryServiceStop())

    def test_off_setting_clears_the_pending_visit_and_professions_get_no_detour(self):
        c = service_client(); visit(c); c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip())
        c.ns.SetOption('inventoryServices',False)
        self.assertIsNone(c.ns.db.inventoryServiceCharacters[c.ns.self].pending)
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.SetOption('inventoryServices',True)
        c.ns.routeSelection.mode = 'profession'
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_missing_and_private_api_values_do_not_become_zero_supplies_or_free_slots(self):
        c = service_client(); visit(c)
        c.lua.execute('C_Container.GetContainerNumSlots=function()return secret end; GetInventoryItemDurability=nil')
        c.ns.ReadServiceInventory()
        self.assertIsNone(c.ns.serviceInventory.free)
        self.assertIsNone(c.ns.serviceInventory.durability)
        self.assertIsNone(c.ns.serviceInventory.food)
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.lua.execute(INVENTORY)
        c.lua.execute('C_Container.GetContainerItemInfo=function()return secret end; function GetInventoryItemDurability()return secret,secret end')
        c.ns.ReadServiceInventory()
        self.assertIsNone(c.ns.serviceInventory.food)
        self.assertIsNone(c.ns.serviceInventory.durability)

    def test_legacy_bag_and_merchant_apis_work_without_modern_tables(self):
        c = service_client()
        c.lua.execute('''GetContainerNumSlots=C_Container.GetContainerNumSlots
            GetContainerNumFreeSlots=C_Container.GetContainerNumFreeSlots
            GetContainerItemID=C_Container.GetContainerItemID
            function GetContainerItemInfo(bag,slot) local i=bags[bag].items[slot]; if i then return 'icon',i.stackCount,false end end
            C_Container=nil; C_MerchantFrame=nil
            function GetMerchantItemInfo()return 'Supply','icon',100,5,-1,true,false end''')
        visit(c)
        self.assertTrue(c.ns.CurrentGuideTip().needs.food)

    def test_inventory_events_are_batched_and_movement_never_rescans_bags(self):
        c = service_client(); visit(c)
        c.lua.globals().bagReads = 0
        for _ in range(20): c.ns.UpdateNavigation()
        self.assertEqual(c.lua.globals().bagReads, 0)
        for _ in range(20): c.ns.handlers.BAG_UPDATE_DELAYED()
        c.drain()
        self.assertEqual(c.lua.globals().bagReads, 5)
        self.assertIsNotNone(c.ns.handlers.BAG_UPDATE_DELAYED)

    def test_vendor_and_tip_reads_never_execute_transactions(self):
        c = service_client(); visit(c)
        self.assertTrue(c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip()))
        c.ns.handlers.MERCHANT_SHOW(); c.drain()
        self.assertTrue(c.ns.FinishInventoryService())

    def test_learned_vendor_is_shared_with_compatible_characters_but_needs_are_personal(self):
        c = service_client(); visit(c)
        c.ns.DismissInventoryServiceTip(c.ns.CurrentGuideTip())
        saved = primitive(c.lua.globals().WowTogetherDB)
        other = service_client(Client(name='Other',quests=(),saved_variables=saved))
        self.assertIsNotNone(other.ns.CurrentGuideTip())
        self.assertEqual(other.ns.CurrentGuideTip().place.npcID,700)

    def test_off_feature_performs_no_new_inventory_reads(self):
        c = service_client(); visit(c)
        c.ns.SetOption('inventoryServices',False)
        c.lua.globals().bagReads = 0
        for _ in range(10): c.ns.handlers.BAG_UPDATE_DELAYED()
        c.drain()
        self.assertEqual(c.lua.globals().bagReads,0)
        c.ns.SetOption('inventoryServices',True); c.drain()
        self.assertEqual(c.lua.globals().bagReads,5)

    def test_one_broken_item_triggers_repairs_even_with_other_gear_at_full_durability(self):
        c = service_client(); visit(c)
        c.lua.execute('bags[0].free=8; function GetInventoryItemDurability(slot)if slot==1 then return 0,80 elseif slot==2 then return 100,100 end end')
        c.ns.db.config.restockSupplies = False
        c.ns.ReadServiceInventory()
        self.assertTrue(c.ns.CurrentGuideTip().needs.repair)
        self.assertIn('Gear at 0%',c.ns.CurrentGuideTip().text)

    def test_unknown_or_failed_reads_do_not_clear_a_saved_dismissal(self):
        c = service_client(); visit(c)
        c.ns.DismissInventoryServiceTip(c.ns.CurrentGuideTip())
        c.lua.execute('C_Container.GetContainerNumSlots=function()error("unavailable")end; function GetInventoryItemDurability()return secret,100 end')
        c.ns.ReadServiceInventory()
        self.assertTrue(c.ns.db.inventoryServiceCharacters[c.ns.self].dismissed.bags)
        self.assertTrue(c.ns.db.inventoryServiceCharacters[c.ns.self].dismissed.repair)

    def test_temporarily_unknown_inventory_retains_an_accepted_visit_without_claiming_completion(self):
        c = service_client(); visit(c)
        c.ns.AcceptInventoryServiceTip(c.ns.CurrentGuideTip())
        c.lua.execute('C_Container.GetContainerNumSlots=function()return secret end; function GetInventoryItemDurability()return secret,secret end')
        c.ns.ReadServiceInventory(); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind,'service')
        self.assertIn('Check bag space',c.ns.navigation.context.text)
        self.assertIn('Check repairs',c.ns.navigation.context.text)
        self.assertNotIn('Buy ~20',c.ns.navigation.context.text)
        self.assertIsNotNone(c.ns.db.inventoryServiceCharacters[c.ns.self].pending)

    def test_known_terrain_barrier_rejects_an_estimated_shortcut_to_a_vendor(self):
        c = service_client(); visit(c)
        c.lua.globals().testNS = c.ns
        c.lua.execute('testNS.TerrainWalkCrossing=function()return {name="Mapped cliff"}end; clock=clock+2')
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_private_merchant_fields_do_not_infer_food_stock(self):
        c = service_client(); c.lua.execute('bags[0].free=8; durability=100; C_MerchantFrame.GetItemInfo=function()return {numAvailable=-1,hasExtendedCost=secret}end')
        c.ns.ReadServiceInventory(); visit(c)
        self.assertIsNone(c.ns.CurrentGuideTip())


if __name__ == '__main__':
    unittest.main()
