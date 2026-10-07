"""Shared resize gestures, faithful source supplements and travel-purpose regressions."""
import unittest

from test_addon import Client
from test_navigation import navigator
from test_0811 import browser, future
from test_0835 import dungeon_client
from test_061 import world_quest
from test_063 import guide_client, zone
from test_061 import run_plan
from test_0836 import crafting
from supplement_quest_data import supplement


class ResizeTests(unittest.TestCase):
    def test_scaled_top_left_stays_fixed_and_global_release_saves_geometry(self):
        c=navigator();f=c.ns.navigation;c.lua.globals().resizeFrame=f
        c.lua.execute('''
          function resizeFrame:GetLeft() return 100 end
          function resizeFrame:GetTop() return 500 end
          function resizeFrame:GetEffectiveScale() return .75 end
          function UIParent:GetEffectiveScale() return 1.5 end
          resizeFrame.StartSizing=function(self,corner) sizingCalls=(sizingCalls or 0)+1 end
        ''')
        f.grip.OnMouseDown(f.grip,'RightButton')
        self.assertIsNone(c.lua.globals().sizingCalls)
        f.grip.OnMouseDown(f.grip,'LeftButton')
        self.assertEqual(f.point[1],'TOPLEFT');self.assertEqual((f.point[4],f.point[5]),(50,250))
        f.SetSize(f,520,260);f.OnSizeChanged()
        self.assertTrue(f.sizing)
        c.ns.handlers.GLOBAL_MOUSE_UP('LeftButton')
        self.assertIsNone(f.sizing);self.assertEqual(c.ns.db.arrowSize.width,520)
        self.assertEqual(f.context.height,52)

    def test_reentrant_native_size_callback_clamps_once_without_replanning(self):
        c=navigator();f=c.ns.navigation;c.lua.globals().resizeFrame=f
        c.lua.execute('''
          resizeFrame.SetSize=function(self,w,h)
            self.width,self.height=w,h; callbacks=(callbacks or 0)+1
            assert(callbacks<4,'recursive clamp'); self.OnSizeChanged()
          end
        ''')
        f.SetSize(f,100,9999)
        self.assertEqual((f.width,f.height),(360,480))
        self.assertLess(c.lua.globals().callbacks,4)

    def test_hide_finishes_gesture_and_preserves_previous_hide_handler(self):
        c=Client(quests=());c.ns.ShowDiagnostics('one\ntwo')
        f=c.ns.diagnosticsWindow;f.grip.OnMouseDown(f.grip,'LeftButton')
        f.SetSize(f,740,650);f.OnSizeChanged();f.OnHide()
        self.assertIsNone(f.sizing)
        self.assertEqual(c.ns.db.uiWindows.diagnostics.width,740)
        self.assertEqual(c.ns.diagnosticsText.width,655)

    def test_choice_popup_reflows_buttons_without_starting_a_guide(self):
        c=browser();c.ns.SetGuideLevel('21-30');c.ns.RequestStartRoute(future(c))
        f=c.ns.earlyGuidePrompt;f.grip.OnMouseDown(f.grip,'LeftButton')
        f.SetSize(f,780,360);f.OnSizeChanged()
        self.assertEqual(f.text.width,736)
        self.assertEqual(f.recommended.width,(780-64)/3)
        self.assertIsNone(c.ns.routeSelection)
        c.ns.handlers.GLOBAL_MOUSE_UP('LeftButton')
        self.assertEqual(c.ns.db.uiWindows['early-guide'].height,360)

    def test_material_resize_is_geometry_only_and_no_listings_is_not_zero_price(self):
        c=Client(quests=());row={'itemID':900,'name':'Supply','need':5,'have':0,'missing':5}
        c.ns.AuctionQuote=c.lua.eval('function() return {unavailable=true} end')
        self.assertIn('No listings',c.ns.ShoppingText(c.lua.table_from([row],recursive=True)))
        c.ns.ShowShoppingList(c.lua.table_from([row],recursive=True),'Supplies')
        f=c.ns.shoppingWindow
        fail=c.lua.eval('function() error("resizing must not plan or search") end')
        c.ns.RefreshProfessionShopping=fail;c.ns.RefreshAuctionGuideSearch=fail
        f.grip.OnMouseDown(f.grip,'LeftButton');f.SetSize(f,800,650);f.OnSizeChanged()
        self.assertEqual(f.rows[1].detail.width,606)
        self.assertIn('No listings',f.rows[1].detail.text)
        c.ns.handlers.GLOBAL_MOUSE_UP('LeftButton')

    def test_dungeon_compact_and_full_bounds_change_without_hiding_or_switching_guides(self):
        c=dungeon_client();c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        f.mode.OnClick();f.SetSize(f,450,340);f.OnSizeChanged()
        self.assertEqual((f.width,f.height),(450,340));self.assertTrue(f.compact)
        f.mode.OnClick();f.SetSize(f,500,400);f.OnSizeChanged()
        self.assertEqual((f.width,f.height),(940,500));self.assertFalse(f.compact)
        self.assertTrue(f.IsShown(f))

    def test_tall_quest_list_extends_visible_rows_only_after_gesture(self):
        c=browser();c.ns.SetGuideLevel('21-30');c.ns.ShowGuideQuestList(future(c));c.drain()
        f=c.ns.guideQuestList
        f.plan=c.lua.table_from([{'id':910,'kind':'q','title':'Future one','mapID':502,'x':.3,'y':.4} for _ in range(40)],recursive=True)
        c.ns.RenderGuideQuestList();old=len(f.rows)
        f.grip.OnMouseDown(f.grip,'LeftButton');f.SetSize(f,800,900);f.OnSizeChanged()
        self.assertEqual(len(f.rows),old)
        c.ns.handlers.GLOBAL_MOUSE_UP('LeftButton')
        self.assertGreater(len(f.rows),old)
        self.assertEqual(f.maximum,40*44-748)

    def test_short_map_quest_popup_hides_extra_rows_and_pages_to_every_quest(self):
        c=Client(quests=())
        c.ns.dungeonData=c.lua.table_from({'dungeons':{'ragefire-chasm':{'name':'Ragefire Chasm'}}},recursive=True)
        c.ns.DungeonMapQuestVisible=c.lua.eval('function() return true end')
        group=c.lua.table_from({'name':'Quest giver','quests':[{'id':900+i,'kind':'a'} for i in range(6)]},recursive=True)
        c.ns.ShowDungeonMapQuests(group,'ragefire-chasm');f=c.ns.dungeonMapQuestWindow
        f.grip.OnMouseDown(f.grip,'LeftButton');f.SetSize(f,380,196);f.OnSizeChanged()
        c.ns.handlers.GLOBAL_MOUSE_UP('LeftButton')
        self.assertEqual(f.rowsPerPage,1)
        self.assertTrue(f.rows[1].IsShown(f.rows[1]))
        self.assertTrue(all(not f.rows[i].IsShown(f.rows[i]) for i in (2,3,4)))
        self.assertEqual(f.pageText.text,'1 / 6')
        for i in range(2,7):
            f.next.OnClick();self.assertEqual(f.pageText.text,f'{i} / 6')
            self.assertEqual(f.rows[1].title.text,c.ns.QuestTitle(899+i))


class SourceSupplementTests(unittest.TestCase):
    def test_missing_pickup_can_be_added_without_overwriting_existing_gates_or_handin(self):
        q=world_quest('Existing');q.pop('starts');q.update(previousQuest=12,raceMask=8,classMask=128)
        detail={'starts':[{'mapID':501,'x':.1,'y':.2,'name':'Published giver','entityID':42}],
                'ends':[{'mapID':999,'x':.9,'y':.9}], 'previousQuest':99,'raceMask':0}
        refs={'starts':[],'ends':[],'requirements':[],'provided':[]}
        result=supplement(q,detail,refs,{})
        self.assertEqual(result['starts'],detail['starts']);self.assertEqual(result['ends'],q['ends'])
        self.assertEqual(result['previousQuest'],12);self.assertEqual(result['raceMask'],8)
        self.assertNotIn('starts',q)

    def test_empty_or_partial_table_cannot_remove_reviewed_item_use_or_unknown_work(self):
        q=world_quest('Use tool');q['requirements']=[{'entityType':'npc','entityID':42,'name':'Target','action':'use','useItemName':'Tool','quantity':3}]
        q['objectives']=[];q['objectiveLocationsIncomplete']=True;q['prerequisitesRead']=True
        refs={'starts':[],'ends':[],'requirements':[],'provided':[]}
        result=supplement(q,{},refs,{'npc':{},'item':{},'object':{}})
        self.assertEqual(result['requirements'],q['requirements'])
        self.assertTrue(result['objectiveLocationsIncomplete'])
        self.assertEqual(result['missingRequirements'][0]['useItemName'],'Tool')

    def test_real_published_entity_can_resolve_an_unknown_objective_without_invented_coordinates(self):
        q=world_quest('Hunt');q['requirements']=[{'entityType':'npc','entityID':42,'name':'Target','action':'kill','quantity':3}]
        q['objectives']=[];q['objectiveLocationsIncomplete']=True;q['prerequisitesRead']=True
        refs={'starts':[],'ends':[],'requirements':[],'provided':[]}
        entities={'npc':{42:{'name':'Target','locations':[{'mapID':501,'x':.32,'y':.45}]}},'item':{},'object':{}}
        result=supplement(q,{},refs,entities)
        p=result['objectives'][0]
        self.assertEqual((p['x'],p['y']),(.32,.45));self.assertEqual(p['quantity'],3)
        self.assertEqual(p['action'],'kill');self.assertFalse(result.get('objectiveLocationsIncomplete',False))


class DestinationPurposeTests(unittest.TestCase):
    def test_travel_to_handin_names_quest_and_giver_while_retaining_transport_directions(self):
        c=navigator();goal={'id':900,'kind':'t','title':'Important return','npcName':'Named giver','mapID':502,'x':.1,'y':.2}
        stop=c.lua.table_from({'kind':'travel','goal':goal,'id':900,'mapID':501,'x':.2,'y':.3},recursive=True)
        c.ns.TravelPathSummary=c.lua.eval('function() return "Take the zeppelin.\\nContinue to the far shore." end')
        context=c.ns.RouteContext(stop,501)
        self.assertIn('Take the zeppelin',context);self.assertIn('Important return',context);self.assertIn('Named giver',context)
        self.assertIn('Important return',context.splitlines()[0])

    def test_objective_purpose_uses_live_action_instead_of_a_crossing_name(self):
        c=navigator();goal=c.lua.table_from({'id':900,'kind':'q','title':'Quest goal','npcName':'Target','action':'kill','quantity':7},recursive=True)
        wrapper=c.lua.table_from({'kind':'travel','title':'Crossing','goal':goal})
        reason=c.ns.GuideDestinationPurpose(wrapper)
        self.assertIn('Kill',reason);self.assertIn('7',reason);self.assertIn('Quest goal',reason)
        self.assertNotIn('Crossing',reason)

    def test_long_trainer_trip_explains_blocking_cap_before_recipe_details(self):
        c=crafting(skill=150,maximum=150)
        facts=c.ns.ProfessionFacts(171)
        facts.ranks[3]=c.lua.table_from({'name':'Expert','maximum':225,'skill':125,'level':20})
        facts.trainers[3]=c.lua.table_from({'name':'Distant Trainer','hub':'Far city','maximum':225,
                                          'mapID':502,'x':.8,'y':.8,'faction':'Horde'})
        c.ns.StartProfessionGuide(171,225)
        goal=c.ns.selectedRoute.stops[1]
        wrapper=c.lua.table_from({'kind':'travel','goal':goal})
        c.ns.TravelPathSummary=c.lua.eval('function() return "Travel to Far city." end')
        first=c.ns.RouteContext(wrapper,501).splitlines()[0]
        self.assertIn('capped at 150',first);self.assertIn('raises it to 225',first)
        self.assertIn('Distant Trainer',first)
        self.assertNotIn('only trainer',first)

    def test_known_prerequisite_is_a_reason_but_an_alternative_is_not_required(self):
        c=guide_client(2);g=zone(c)
        c.ns.catalogue.quests[901].previousQuest=900
        c.ns.ShowGuideOnMap(g);run_plan(c)
        goal=c.lua.table_from({'id':900,'kind':'a','title':'First quest','mapID':501,'x':.2,'y':.4})
        self.assertIn('Required for Quest 1',c.ns.GuideDestinationReason(goal))
        c.ns.catalogue.quests[901].previousQuest=None
        c.ns.catalogue.quests[901].prerequisiteAny=c.lua.table_from([900,999])
        c.ns.selectedRoute=c.lua.table_from({'stops':[goal]},recursive=True)
        reason=c.ns.GuideDestinationReason(goal)
        self.assertNotIn('Required',reason);self.assertIn('selected guide',reason)

    def test_consecutive_nearby_pickups_explain_single_visit_and_cache_until_route_changes(self):
        c=guide_client(2);g=zone(c);c.ns.ShowGuideOnMap(g);run_plan(c)
        goal=c.ns.selectedRoute.stops[1]
        self.assertEqual(goal.kind,'a')
        reason=c.ns.GuideDestinationReason(goal)
        self.assertIn('2 nearby quest pickups',reason)
        fail=c.lua.eval('function() error("unchanged arrow must use cached reasoning") end')
        c.ns.CatalogueCompletion=fail;c.ns.WalkingDistance=fail
        self.assertEqual(c.ns.GuideDestinationReason(goal),reason)

    def test_larger_hub_search_finishes_with_existing_cooperative_budget(self):
        c=guide_client(26);g=zone(c);c.ns.ShowGuideOnMap(g)
        self.assertLess(run_plan(c),200)
        self.assertEqual(len(g.fixedPlan),78)

    def test_long_walk_in_same_zone_shows_reason_not_only_interaction_hint(self):
        c=navigator();goal=c.lua.table_from({'id':900,'kind':'t','title':'Long return',
                                            'mapID':501,'x':.1,'y':.2,'npcName':'Giver'})
        reason=c.ns.RouteContext(goal,501,None,1500)
        self.assertIn('collect the reward for Long return',reason.splitlines()[0])
        self.assertNotIn('Hand in the completed quest',reason)


if __name__=='__main__':unittest.main()
