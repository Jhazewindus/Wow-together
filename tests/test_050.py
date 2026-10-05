"""Behavioral checks for local planning and opt-in beta features, under Lua 5.1."""
import json
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest, route_client
from test_importers import detail
from import_wowhead import base_facts, detail_facts
from import_warcraftdb import normalize


def solo():
    c = route_client()
    c.lua.globals().grouped = False
    c.unit_names({'player': ['Alice', 'TestRealm']})
    return c


def nearby(title='Local quest', **extra):
    return quest(title, starts=[{'mapID': 501, 'x': .21, 'y': .37, 'name': 'Hub'}],
                 objectives=[{'mapID': 501, 'x': .24, 'y': .4, 'name': 'Target'}],
                 ends=[{'mapID': 501, 'x': .21, 'y': .37, 'name': 'Hub'}], xp=500, **extra)


def world_positions(c, other_continent=False):
    c.nearby_zone_link()
    c.lua.execute('''
    function CreateVector2D(x,y) return {GetXY=function() return x,y end} end
    C_Map.GetWorldPosFromMapPos=function(map, p)
      local x,y=p:GetXY()
      return separateContinent and map or 1, CreateVector2D(x*1000+mapOffset[map], y*1000)
    end
    mapOffset={[501]=0,[502]=400,[503]=20000}
    ''')
    c.lua.globals().separateContinent = other_continent


def dungeon(c, start_map=501, entrance_map=501):
    catalogue(c, {900: nearby(categoryPath='dungeons/test-cavern'),
                  901: quest('Other pickup', map_id=start_map, categoryPath='dungeons/test-cavern')})
    c.ns.db.dungeonEntrances = c.lua.table_from({'test-cavern': {'mapID': entrance_map, 'x': .27, 'y': .41}}, recursive=True)
    return c.ns.DungeonGroups()[1]


class CircuitTests(unittest.TestCase):
    def test_local_plan_filters_detours_levels_categories_and_ambiguous_targets(self):
        c = solo()
        catalogue(c, {900: nearby(), 901: nearby('Neighbour'),
            902: quest('Far high XP', xp=100000), 903: quest('Other zone', map_id=502, xp=100000),
            904: nearby('Too high', level=25), 905: nearby('Unknown target', objectiveLocationsIncomplete=True),
            906: nearby('Class quest', categoryPath='classes/mage'),
            907: nearby('Profession', categoryPath='professions/cooking'),
            908: nearby('Dungeon', categoryPath='dungeons/test-cavern'),
            909: nearby('Locked step', previousQuest=910)})
        choices = c.ns.LocalCircuitChoices()
        self.assertGreater(len(choices), 0)
        plan = choices[1]
        self.assertEqual({r.id for r in plan.records.values()}, {900, 901})
        self.assertIn('actual XP varies', plan.reason)
        self.assertEqual(plan.xp, 1000)
        self.assertIsNone(c.ns.BuildCircuitRoute(plan, True).walkingYards)

    def test_pickup_objective_turn_in_phases_and_distance_are_bounded(self):
        c = solo()
        catalogue(c, {i: nearby(str(i)) for i in range(900, 915)})
        c.ns.SetOption('circuitLimit', 4)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,800 end')
        plan = c.ns.LocalCircuitChoices()[1]
        route = c.ns.BuildCircuitRoute(plan, True)
        self.assertEqual(len(plan.records), 4)
        self.assertLessEqual(len(route.stops), 20)
        kinds = [s.kind for s in route.stops.values()]
        self.assertEqual(kinds, sorted(kinds, key={'a': 0, 'q': 1, 't': 2}.get))
        self.assertGreater(route.walkingYards, 0)
        c.lua.execute('C_Map.GetMapWorldSize=function() return secret,800 end')
        self.assertIsNone(c.ns.BuildCircuitRoute(plan, True).walkingYards)

    def test_waiting_party_does_not_get_a_confirmed_circuit(self):
        c = route_client()
        catalogue(c, {900: nearby()})
        self.assertEqual(len(c.ns.LocalCircuitChoices()), 0)

    def test_personal_profession_quests_never_enter_party_leveling_guides(self):
        c = solo()
        catalogue(c, {900: nearby('Cooking', categoryPath='professions/cooking'),
                      901: nearby('Mage', categoryPath='classes/mage')})
        self.assertFalse(c.ns.LevelingQuestEnabled(900))
        self.assertFalse(c.ns.LevelingQuestEnabled(901))
        self.assertEqual(c.ns.ClassQuestLabel(901), 'Class quest: Mage')
        c.ns.SetOption('classQuests', True)
        self.assertTrue(c.ns.LevelingQuestEnabled(901))
        c.ns.professionSelection = 'quests:cooking'
        choices = c.ns.ProfessionChoices()
        self.assertTrue(choices[2].guide.personal)
        self.assertEqual(choices[2].guide.target.id, 900)


class SettingsTests(unittest.TestCase):
    def test_acceptance_requires_opt_in_public_dialog_and_no_combat(self):
        c = solo()
        c.lua.execute('accepts=0; function AcceptQuest() accepts=accepts+1 end; function CanAcceptQuest() return allowed end; function GetQuestID() return 900 end; allowed=true')
        c.ns.InitializeOffers()
        c.ns.AutoAcceptOpenedQuest(900)
        self.assertEqual(c.lua.globals().accepts, 0)
        c.ns.SetOption('autoAccept', True)
        c.lua.globals().combat = True
        c.ns.AutoAcceptOpenedQuest(900)
        c.lua.globals().combat = False
        c.ns.AutoAcceptOpenedQuest(c.lua.globals().secret)
        c.lua.globals().allowed = c.lua.globals().secret
        c.ns.AutoAcceptOpenedQuest(900)
        c.lua.globals().allowed = False
        c.ns.AutoAcceptOpenedQuest(900)
        self.assertEqual(c.lua.globals().accepts, 0)
        c.lua.globals().allowed = True
        c.ns.AutoAcceptOpenedQuest(900)
        c.ns.AutoAcceptOpenedQuest(900)
        self.assertEqual(c.lua.globals().accepts, 1)
        c.ns.handlers.QUEST_FINISHED()
        c.ns.AutoAcceptOpenedQuest(900)
        self.assertEqual(c.lua.globals().accepts, 2)

    def test_configuration_rejects_wrong_types_and_bounds_saved_numbers(self):
        c = solo()
        c.ns.SetOption('autoAccept', 1)
        self.assertFalse(c.ns.Option('autoAccept'))
        c.ns.SetOption('circuitLimit', 100)
        self.assertEqual(c.ns.Option('circuitLimit'), 6)
        c.lua.execute('WowTogetherDB.config.trackerOpacity=0/0; WowTogetherDB.config.professionBatch=math.huge')
        c.ns.InitializeConfig()
        self.assertEqual(c.ns.Option('trackerOpacity'), .08)
        self.assertEqual(c.ns.Option('professionBatch'), 5)


class DungeonTests(unittest.TestCase):
    def test_party_level_change_rechecks_dungeon_prompt_without_history_change(self):
        c = route_client()
        group = dungeon(c)
        c.ns.SetOption('zonePrompts', False)
        c.receive('1|P|4|2|501|Test Coast')
        c.receive('1|S|1|1|1|')
        c.receive('1|C|2|1|1|')
        c.receive('1|K|2|1|1|900,901')
        c.drain()
        self.assertIsNone(c.ns.activityPrompt)
        c.receive('1|P|10|2|501|Test Coast')
        c.drain()
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        self.assertIn(group.name, c.ns.activityPrompt.title.text)

    def test_collect_current_zone_before_nearby_entrance_zone(self):
        c = solo()
        world_positions(c)
        group = dungeon(c, start_map=502, entrance_map=502)
        plan = c.ns.DungeonGuide(group)
        route = c.ns.BuildDungeonRoute(plan, True)
        self.assertEqual(route.mapID, 501)
        self.assertEqual([s.id for s in route.stops.values()], [900])
        self.assertTrue(route.partial)
        c.lua.execute("entries={{questID=900,title='Accepted',isHeader=false}}")
        c.ns.ReadQuests()
        route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(group), True)
        self.assertEqual(route.mapID, 502)
        self.assertEqual(route.stops[1].id, 901)
        self.assertIn('entrance', route.stops[len(route.stops)].label)

    def test_entrance_is_last_and_completed_party_route_clears(self):
        c = solo()
        group = dungeon(c)
        map_canvas(c)
        plan = c.ns.DungeonGuide(group)
        route = c.ns.BuildDungeonRoute(plan, True)
        self.assertEqual([s.kind for s in route.stops.values()], ['a', 'a', 'q'])
        self.assertIn('entrance', route.stops[3].label)
        c.ns.ShowGuideOnMap(plan)
        c.lua.execute('finished[900]=true; finished[901]=true')
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertIsNone(c.ns.selectedRoute)

    def test_missing_entrance_is_honest_and_public_map_link_is_used(self):
        c = solo()
        group = dungeon(c)
        c.ns.db.dungeonEntrances = None
        plan = c.ns.DungeonGuide(group)
        self.assertIsNone(plan.entrance)
        self.assertIn('Entrance not located yet', plan.reason)
        c.lua.execute('C_Map.GetMapLinksForMap=function() return {{name="Test Cavern",position={GetXY=function() return .3,.4 end}}} end')
        point = c.ns.DungeonEntrance(group)
        self.assertAlmostEqual(point.x, .3)
        c.lua.execute('C_Map.GetMapLinksForMap=function() return {{name=secret,position=secret}} end')
        self.assertIsNone(c.ns.DungeonEntrance(group))
        c.ns.RecordDungeonEntrance(group)
        point = c.ns.DungeonEntrance(group)
        self.assertEqual(point.source, 'Player-recorded entrance')

    def test_far_or_other_continent_entrance_never_changes_route_map(self):
        for different_continent in (False, True):
            c = solo()
            world_positions(c, different_continent)
            group = dungeon(c, start_map=503, entrance_map=503)
            c.lua.execute("entries={{questID=900,title='Accepted',isHeader=false}}")
            c.ns.ReadQuests()
            route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(group), True)
            self.assertEqual(route.mapID, 501)
            self.assertTrue(route.partial)

    def test_dungeon_selection_scopes_history_without_all_character_history(self):
        c = solo()
        group = dungeon(c)
        c.ns.ShowDungeonQuests(group)
        self.assertTrue(c.ns.dungeonHistoryScope[900])
        self.assertTrue(c.ns.dungeonHistoryScope[901])
        self.assertEqual(len(list(c.ns.dungeonHistoryScope.keys())), 2)

    def test_popup_respects_level_combat_settings_and_character_scope(self):
        c = solo()
        group = dungeon(c)
        c.ns.SetOption('zonePrompts', False)
        c.ns.profile.level = 4
        c.drain()
        self.assertIsNone(c.ns.activityPrompt)
        c.ns.profile.level = 10
        c.lua.globals().combat = True
        c.ns.ScheduleActivitySuggestions()
        c.drain()
        self.assertIsNone(c.ns.activityPrompt)
        c.lua.globals().combat = False
        c.ns.ScheduleActivitySuggestions()
        c.drain()
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        self.assertTrue(c.ns.db.activityNotices['Alice-TestRealm:dungeon:test-cavern'])
        self.assertNotEqual(c.ns.ActivityNoticeKey(group.key), 'Bob-TestRealm:' + group.key)
        c.ns.activityPrompt.Hide(c.ns.activityPrompt)
        c.ns.activityRevision = 1
        c.ns.ScheduleActivitySuggestions()
        c.drain()
        self.assertFalse(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))


class TransitionTests(unittest.TestCase):
    def test_zone_popup_waits_until_compact_local_options_are_low(self):
        c = solo()
        world_positions(c)
        catalogue(c, {900: nearby(), 901: quest('Next zone', map_id=502, previousQuest=900),
                      902: nearby('Local A'), 903: nearby('Local B')})
        c.lua.globals().finished[900] = True
        c.ns.SetOption('dungeonPrompts', False)
        c.drain()
        self.assertIsNone(c.ns.activityPrompt)
        c.lua.execute('finished[902]=true; finished[903]=true')
        c.ns.handlers.QUEST_TURNED_IN()
        c.drain()
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        self.assertIn('Continue into', c.ns.activityPrompt.title.text)
        self.assertEqual(c.ns.activityPrompt.accept.caption.text, 'Show next zone route')

    def test_zone_change_requires_completed_previous_step_and_nearby_world_position(self):
        c = solo()
        world_positions(c)
        catalogue(c, {900: nearby(), 901: quest('Next zone', map_id=502, previousQuest=900)})
        self.assertIsNone(c.ns.ZoneTransition())
        c.lua.globals().finished[900] = True
        transition = c.ns.ZoneTransition()
        self.assertEqual(transition.target.id, 901)
        c.lua.globals().separateContinent = True
        self.assertIsNone(c.ns.ZoneTransition())
        c.lua.globals().separateContinent = False
        c.lua.globals().mapOffset[502] = 20000
        self.assertIsNone(c.ns.ZoneTransition())

    def test_missing_world_position_or_waiting_party_does_not_invent_transition(self):
        c = route_client()
        world_positions(c)
        catalogue(c, {900: nearby(), 901: quest('Next zone', map_id=502, previousQuest=900)})
        c.lua.globals().finished[900] = True
        self.assertIsNone(c.ns.ZoneTransition())
        c.lua.globals().grouped = False
        c.unit_names({'player': ['Alice', 'TestRealm']})
        c.lua.execute('C_Map.GetWorldPosFromMapPos=function() return secret,secret end')
        self.assertIsNone(c.ns.ZoneTransition())


class ProfessionTests(unittest.TestCase):
    def test_required_reagent_slots_merge_stock_once_and_use_observed_cost(self):
        c = solo()
        c.lua.execute('''
        C_Item={GetItemInfo=function(id) return 'Copper' end, GetItemCount=function(id) return 6 end}
        C_TradeSkillUI={GetRecipeSchematic=function() return {reagentSlotSchematics={
          {required=true,quantityRequired=2,reagents={{itemID=100}}},
          {required=true,quantityRequired=1,reagents={{itemID=100}}},
          {required=false,quantityRequired=100,reagents={{itemID=200}}}}} end}
        ''')
        c.ns.marketQuotes[100] = c.lua.table_from({'unitPrice': 25, 'quantity': 100})
        items, cost, incomplete = c.ns.RecipeMaterials(700, 3)
        self.assertEqual(len(items), 1)
        self.assertEqual((items[1].need, items[1].have, items[1].missing), (9, 6, 3))
        self.assertEqual(cost, 75)
        self.assertFalse(incomplete)
        c.ns.marketQuotes[100] = None
        self.assertIsNone(c.ns.RecipeMaterials(700, 3)[1])

    def test_private_reagents_are_unknown_not_free(self):
        c = solo()
        c.lua.execute('C_TradeSkillUI={GetRecipeSchematic=function() return {reagentSlotSchematics={{required=secret,reagents=secret}}} end}')
        items, cost, incomplete = c.ns.RecipeMaterials(700, 5)
        self.assertEqual(len(items), 0)
        self.assertIsNone(cost)
        self.assertTrue(incomplete)

    def test_live_recipes_fall_back_to_base_profession_and_stay_personal(self):
        c = solo()
        c.drain()
        c.lua.execute('''
        C_TradeSkillUI={
          GetChildProfessionInfo=function() return {professionID=0} end,
          GetBaseProfessionInfo=function() return {professionID=164,professionName='Blacksmithing',skillLevel=10,maxSkillLevel=75} end,
          GetAllRecipeIDs=function() return {1,2,3,4} end,
          GetRecipeInfo=function(id) return {name='Recipe '..id,learned=id~=3,canSkillUp=id==4 and secret or true,relativeDifficulty=id==1 and 40 or 60} end}
        Enum.TradeskillRelativeDifficulty={Optimal=40,Medium=50,Easy=60,Trivial=70}
        ''')
        c.ns.ReadProfessionRecipes()
        self.assertEqual(len(c.ns.professionData[164].recipes), 2)
        self.assertEqual(len(c.drain()), 0)
        c.ns.professionSelection = 'live:164'
        choices = c.ns.ProfessionChoices()
        self.assertEqual(choices[2].title, 'Recipe 1')
        self.assertIn('Orange', choices[2].detail)
        self.assertIn('cost unknown', choices[2].detail)

    def test_observed_auction_results_do_not_search_buy_or_send(self):
        c = solo()
        c.drain()
        c.lua.execute('''
        C_AuctionHouse={GetCommoditySearchResultInfo=function() return {unitPrice=123,quantity=10} end,
          SendSearchQuery=function() error('unexpected search') end,
          StartCommoditiesPurchase=function() error('unexpected purchase') end}
        ''')
        c.ns.handlers.COMMODITY_SEARCH_RESULTS_UPDATED(100)
        self.assertEqual(c.ns.marketQuotes[100].unitPrice, 123)
        self.assertEqual(len(c.drain()), 0)
        c.lua.execute('C_AuctionHouse.GetCommoditySearchResultInfo=function() return {unitPrice=secret,quantity=10} end')
        c.ns.handlers.COMMODITY_SEARCH_RESULTS_UPDATED(200)
        self.assertIsNone(c.ns.marketQuotes[200])

    def test_vendor_buy_list_aggregates_only_known_buyables_including_active_repeatables(self):
        c = solo()
        buyable = {'itemID': 100, 'name': 'Water', 'quantity': 2, 'buyable': True}
        drop = {'itemID': 200, 'name': 'Quest drop', 'quantity': 6}
        catalogue(c, {900: nearby(requiredItems=[buyable, drop]), 901: nearby(requiredItems=[dict(buyable)])})
        c.lua.execute('C_Item={GetItemCount=function() return 1 end}; finished[900]=true')
        self.assertEqual(c.ns.QuestShoppingList(guide(c, (900, 901)).records)[1].need, 2)
        c.ns.active[900] = 'Repeated'
        row = c.ns.QuestShoppingList(guide(c, (900, 901)).records)[1]
        self.assertEqual((row.need, row.have, row.missing), (4, 1, 3))
        c.lua.execute('C_Item.GetItemCount=function() return secret end')
        self.assertIsNone(c.ns.QuestShoppingList(guide(c, (900, 901)).records)[1].missing)

    def test_failed_item_load_does_not_retry_forever(self):
        c = solo()
        c.lua.execute('requests=0; C_Item={GetItemInfo=function() return nil end,RequestLoadItemDataByID=function() requests=requests+1 end}')
        c.ns.ItemName(100)
        c.ns.handlers.ITEM_DATA_LOAD_RESULT(100, False)
        c.ns.ItemName(100)
        self.assertEqual(c.lua.globals().requests, 1)


class TargetAndSourceTests(unittest.TestCase):
    def test_repeatable_active_progress_overrides_older_completion_history(self):
        c = solo()
        c.ns.active[900] = 'Repeatable drops'
        c.lua.execute('finished[900]=true; C_QuestLog.GetQuestObjectives=function() return {{text="Drops: 2/6",type="item",numFulfilled=2,numRequired=6,finished=false}} end')
        c.ns.ReadProgress()
        self.assertEqual(c.ns.TrackerValue(c.ns.self, 900, 1), '2/6')
        c.ns.active[900] = None
        self.assertEqual(c.ns.TrackerValue(c.ns.self, 900, 1), 'Done')

    def test_alternative_npc_targets_work_without_route_coordinates_and_bootstrap_existing_plates(self):
        c = solo()
        catalogue(c, {900: nearby(npcTargets=[{'entityID': 100, 'name': 'Drop A', 'npc': True, 'action': 'collect'},
                                            {'entityID': 200, 'name': 'Drop B', 'npc': True, 'action': 'collect'}])})
        c.ns.active[900] = 'Drops'
        c.lua.execute('''
        plate=CreateFrame('Frame'); plate.namePlateUnitToken='nameplate1'
        C_NamePlate={GetNamePlates=function() return {plate} end,GetNamePlateForUnit=function() return plate end}
        function UnitGUID() return 'Creature-0-1-1-1-200-ABC' end
        ''')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 1)
        self.assertEqual(c.ns.npcHints['nameplate1'].target.label, 'Drop B')
        self.assertIn('ReadyCheck-NotReady', c.ns.StopIcon(c.ns.npcHints['nameplate1'].target))
        c.ns.SetOption('npcHints', False)
        self.assertFalse(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))

    def test_client_quest_flag_fallback_requires_public_true(self):
        c = solo()
        c.lua.execute('''
        plate=CreateFrame('Frame'); plate.namePlateUnitToken='nameplate1'
        C_NamePlate={GetNamePlates=function() return {plate} end,GetNamePlateForUnit=function() return plate end}
        function UnitGUID() return nil end
        C_QuestLog.UnitIsRelatedToActiveQuest=function() return secret end
        ''')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)
        c.lua.execute('C_QuestLog.UnitIsRelatedToActiveQuest=function() return true end')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 1)
        self.assertEqual(c.ns.npcHints['nameplate1'].target.label, 'Your quest objective')

    def test_parser_retains_ambiguous_unmapped_npcs_without_inventing_locations_or_kills(self):
        points = [{'point': 'sourcerequirement', 'objective': 0, 'id': i, 'type': 1,
                   'name': 'Drop source', 'item': 'Drop', 'coord': [30, 20]} for i in (100, 200)]
        points.append({'point': 'requirement', 'objective': 300, 'id': 300, 'type': 1, 'reacthorde': 1, 'name': 'Friendly', 'coord': [40, 40]})
        facts = detail_facts(detail(points), {'id': 42}, {})
        self.assertNotIn('objectives', facts)
        self.assertEqual([p['entityID'] for p in facts['npcTargets']], [100, 200, 300])
        self.assertEqual(facts['npcTargets'][1]['itemName'], 'Drop')
        self.assertNotIn('action', facts['npcTargets'][2])

    def test_required_item_table_does_not_capture_reward_items(self):
        table = '<table class="icon-list"><tr data-icon-list-quantity="2"><td><a href="/forever/item=159">Water</a></td></tr></table>'
        reward = table.replace('159', '200')
        data = 'WH.Gatherer.addData(3, 16, ' + json.dumps({'159': {'jsonequip': {'buyprice': 25}}}) + ');'
        facts = detail_facts(table + detail([]) + reward + data, {'id': 42}, {14: 1411})
        self.assertEqual(facts['requiredItems'], [{'itemID': 159, 'quantity': 2, 'name': 'Water', 'buyable': True, 'buyPrice': 25}])
        self.assertNotIn('requiredItems', detail_facts(detail([]) + reward, {'id': 42}, {14: 1411}))

    def test_published_xp_is_preserved_without_inventing_it(self):
        self.assertEqual(base_facts({'id': 42, 'name': 'Test', 'xp': 750})['xp'], 750)
        self.assertNotIn('xp', base_facts({'id': 42, 'name': 'Test'}))
        self.assertEqual(normalize({'record_id': 42}, {'data': {'rewards': {'xp': 750}}})['xp'], 750)


if __name__ == '__main__':
    unittest.main()
