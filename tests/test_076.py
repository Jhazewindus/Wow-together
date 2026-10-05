"""NPC visits use actual offers without rebuilding fixed objective order."""
import json
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas
from test_061 import world_quest
from test_063 import order, primitive


def npc_client(unknown=True):
    c = Client(quests=())
    c.guide_environment(level=12); map_canvas(c)
    c.lua.globals().grouped = False
    c.unit_names({'player': ['Alice', 'TestRealm']})
    q = world_quest('First')
    q['starts'][0]['entityID'] = 123
    other = world_quest('Second', starts=[] if unknown else q['starts'], prerequisitesRead=True)
    third = world_quest('Third', starts=[] if unknown else q['starts'], prerequisitesRead=True)
    catalogue(c, {900: q, 901: other, 902: third})
    c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
    g = guide(c, (900, 901, 902), key='level-zone:test')
    g.fixedRoute, g.fullGuide, g.mode, g.mapID, g.homeMapID = True, True, 'zone', 501, 501
    c.ns.ActivateRoute(g)
    return c, g


def offer(c, ids=(900, 901, 902), full=True):
    c.ns.ReadQuests()
    c.ns.offered = c.lua.table_from({i: True for i in ids})
    c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': i} for i in ids], recursive=True), full)
    c.ns.UpdateSelectedRoute(None, c.ns.NewQuestQuery())
    c.ns.Refresh()


def pickup_ids(c):
    return [s.id for s in c.ns.selectedRoute.stops.values() if s.npcVisitPickup]


class NPCVisitTests(unittest.TestCase):
    def test_baine_report_uses_three_real_shipped_quests_without_a_special_case(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=6); map_canvas(c)
        c.lua.globals().grouped = False
        c.unit_names({'player': ['Pachu', 'Bloodwind']})
        c.lua.execute("C_Map.GetBestMapForUnit=function() return 1412 end; function UnitGUID() return 'Creature-0-1-2-3-2993-ABC' end; function UnitName(unit) if unit=='npc' then return 'Baine Bloodhoof' end end")
        c.ns.ReadProfile()
        g = guide(c, (745, 746, 767), key='level-zone:mulgore')
        g.fixedRoute, g.mode, g.mapID = True, 'zone', 1412
        c.ns.ActivateRoute(g)
        before = order(g)
        offer(c, (745, 746, 767))
        self.assertEqual(set(pickup_ids(c)), {745, 746, 767})
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 767)
        self.assertEqual(order(g), before)
        self.assertIsNone(c.ns.CatalogueQuest(745).starts)
        self.assertTrue(c.ns.NPCPickupPoint(745))

    def test_fully_mapped_quests_also_collect_at_one_visit(self):
        c, g = npc_client(unknown=False)
        before = order(g)
        offer(c)
        self.assertEqual(pickup_ids(c), [900, 901, 902])
        self.assertEqual(order(g), before)
        self.assertEqual([(s.id,s.kind) for s in c.ns.selectedRoute.stops.values()][:3], [(900,'a'),(901,'a'),(902,'a')])
        self.assertEqual(len(c.ns.selectedRoute.stops), len(g.fixedPlan))

    def test_missing_pickup_points_fill_only_runtime_pickup_steps(self):
        c, g = npc_client()
        before = order(g)
        offer(c)
        for s in c.ns.selectedRoute.stops.values():
            if s.npcVisitPickup:
                self.assertEqual(s.entityID, 123)
                self.assertTrue(s.approximate)
                self.assertFalse(s.unknownLocation)
                self.assertIsNone(s.published)
        self.assertEqual(order(g), before)
        self.assertTrue(next(s for s in g.fixedPlan.values() if s.id == 901 and s.kind == 'a').unknownLocation)

    def test_accepting_each_pickup_updates_now_then_restores_original_objective_sequence(self):
        c, g = npc_client(unknown=False)
        before = order(g)
        offer(c)
        for i, id in enumerate((900, 901, 902)):
            c.lua.globals().entries[i+1] = c.lua.table_from({'questID': id, 'title': c.ns.QuestTitle(id)})
            c.ns.handlers.QUEST_ACCEPTED(i+1, id)
            self.assertNotIn(id, pickup_ids(c))
            self.assertTrue(c.ns.active[id])
            self.assertFalse(c.ns.Completed(id))
        self.assertEqual(pickup_ids(c), [])
        self.assertEqual([(s.id,s.kind) for s in c.ns.selectedRoute.stops.values()], [(s.id,s.kind) for s in g.fixedPlan.values() if s.kind != 'a'])
        self.assertEqual(order(g), before)

    def test_skip_step_keeps_its_key_when_the_observed_position_changes(self):
        c, g = npc_client()
        c.ns.db.guideSkips[c.ns.self].quests[900] = True
        raw = next(s for s in g.fixedPlan.values() if s.id == 901 and s.kind == 'a')
        offer(c, (901,902))
        self.assertEqual(c.ns.selectedRoute.stops[1].fixedStepKey, c.ns.GuideStepKey(raw))
        c.ns.SkipGuide('step')
        c.lua.execute('C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .3,.4 end} end')
        offer(c, (901,902))
        self.assertNotIn(901, pickup_ids(c))
        self.assertIn(902, pickup_ids(c))
        self.assertFalse(c.ns.Completed(901))

    def test_selection_filters_and_known_prerequisites_still_apply(self):
        c, g = npc_client()
        c.ns.catalogue.quests[901].previousQuest = 899
        c.ns.catalogue.quests[902].level = 25
        c.ns.catalogue.quests[903] = c.lua.table_from(world_quest('Unrelated'), recursive=True)
        offer(c, (900,901,902,903))
        self.assertEqual(pickup_ids(c), [900])
        c.ns.db.config.nearbyPickups = False
        c.ns.UpdateSelectedRoute(None, c.ns.NewQuestQuery())
        self.assertEqual(pickup_ids(c), [])

    def test_repeatables_professions_excluded_quests_class_and_faction_stay_out(self):
        for fields in ({'repeatable':True}, {'categoryPath':'professions/cooking'}, {'levelingExcluded':'edition'}, {'classMask':1}, {'side':'Alliance'}):
            c, g = npc_client()
            for key, value in fields.items(): c.ns.catalogue.quests[901][key] = value
            offer(c)
            self.assertNotIn(901, pickup_ids(c), fields)

    def test_partial_dialog_does_not_replace_the_complete_visit_or_infer_other_absence(self):
        c, g = npc_client()
        offer(c)
        offer(c, (900,), full=False)
        self.assertEqual(set(pickup_ids(c)), {900,901,902})
        self.assertTrue(c.ns.ObservedPickupAvailable(901))

    def test_public_full_list_removing_a_quest_stops_its_pickup(self):
        c, g = npc_client()
        offer(c)
        offer(c, (900,902))
        self.assertNotIn(901, pickup_ids(c))
        self.assertFalse(c.ns.ObservedPickupAvailable(901))

    def test_secret_npc_identity_or_position_cannot_create_geography(self):
        for restriction in ('function UnitGUID() return secret end', 'C_Map.GetPlayerMapPosition=function() return {GetXY=function() return secret,.4 end} end'):
            c, g = npc_client()
            c.lua.execute(restriction)
            offer(c)
            self.assertIsNone(c.ns.NPCPickupPoint(901))
            self.assertEqual(pickup_ids(c), [])

    def test_new_character_reuses_build_locations_but_not_availability_or_credit(self):
        c, g = npc_client()
        offer(c)
        saved = primitive(c.ns.db)
        fresh = Client(name='Another', quests=(), saved_variables=saved)
        fresh.guide_environment(level=12)
        fresh.lua.globals().grouped = False; fresh.ns.UpdateRoster()
        fresh.ns.catalogue = fresh.lua.table_from(primitive(c.ns.catalogue), recursive=True)
        self.assertTrue(fresh.ns.NPCPickupPoint(901))
        self.assertIsNone(fresh.ns.ObservedPickupAvailable(901))
        self.assertFalse(fresh.ns.Completed(901))
        fresh.lua.execute("function GetBuildInfo() return '1.60.1','different','test',16001 end")
        fresh.ns.InitializeNPCPickups()
        self.assertIsNone(fresh.ns.NPCPickupPoint(901))

    def test_reload_restores_pending_visit_and_original_fixed_plan(self):
        c, g = npc_client()
        offer(c); c.ns.handlers.PLAYER_LOGOUT()
        saved = primitive(c.ns.db)
        self.assertEqual(set(saved['guideState'][c.ns.self]['guide']['npcVisitPickupIDs'].values()), {900,901,902})
        fresh = Client(quests=(), saved_variables=saved)
        fresh.guide_environment(level=12); map_canvas(fresh)
        fresh.lua.globals().grouped = False; fresh.ns.UpdateRoster()
        fresh.ns.catalogue = fresh.lua.table_from(primitive(c.ns.catalogue), recursive=True)
        fresh.ns.handlers.PLAYER_LOGIN(); fresh.drain()
        self.assertEqual(order(fresh.ns.routeSelection), order(g))
        self.assertEqual(set(pickup_ids(fresh)), {900,901,902})
        self.assertIsNone(fresh.ns.ObservedPickupAvailable(901))

    def test_automation_advances_only_on_returned_native_lists_and_acceptance_events(self):
        c, g = npc_client()
        c.ns.db.config.autoSelectQuests = c.ns.db.config.autoAccept = True
        c.lua.globals().testNS = c.ns
        c.lua.execute('''
        selectedQuests = {}
        function GetQuestID() return openedQuest end
        function GetTitleText() return 'Quest '..openedQuest end
        C_GossipInfo = {
            GetAvailableQuests=function()
                local list={}
                for id=900,902 do if not testNS.active[id] then list[#list+1]={questID=id} end end
                return list
            end,
            SelectAvailableQuest=function(id)
                selectedQuests[#selectedQuests+1]=id; openedQuest=id
                testNS.handlers.QUEST_DETAIL()
            end
        }
        function AcceptQuest()
            entries[#entries+1]={questID=openedQuest,title='Quest '..openedQuest}
            testNS.handlers.QUEST_ACCEPTED(#entries,openedQuest)
            testNS.handlers.QUEST_FINISHED()
            C_Timer.After(0,function() testNS.ReadOffers() end)
        end
        ''')
        c.ns.InitializeOffers()
        c.ns.gossipReady = True
        c.ns.ReadOffers(); c.drain()
        self.assertEqual(list(c.lua.globals().selectedQuests.values()), [900,901,902])
        self.assertEqual(set(c.ns.active.keys()), {900,901,902})
        self.assertEqual(pickup_ids(c), [])

    def test_auto_selection_does_not_imply_auto_accept_or_run_in_combat(self):
        c, g = npc_client()
        c.lua.execute('C_GossipInfo={SelectAvailableQuest=function(id) selectedQuest=id end}; function AcceptQuest() error("auto-accept is off") end')
        offer(c)
        c.ns.AutoSelectGuideQuest()
        self.assertIsNone(c.lua.globals().selectedQuest)
        c.ns.db.config.autoSelectQuests = True
        c.lua.globals().combat = True; c.ns.AutoSelectGuideQuest()
        self.assertIsNone(c.lua.globals().selectedQuest)
        c.lua.globals().combat = False; c.ns.AutoSelectGuideQuest()
        self.assertEqual(c.lua.globals().selectedQuest, 900)
        self.assertEqual(len(c.ns.active), 0)

    def test_findings_export_contains_public_pickup_geography_as_valid_json(self):
        c, g = npc_client()
        offer(c)
        exported = json.loads(c.ns.ExportGuideFindings())
        self.assertEqual({p['questID'] for p in exported['pickupLocations']['quests']}, {900,901,902})
        self.assertTrue(exported['pickupLocations']['approximate'])
        self.assertNotIn('Alice', c.ns.ExportGuideFindings())

    def test_quest_greeting_slots_select_all_useful_quests_in_sequence(self):
        c, g = npc_client()
        c.ns.db.config.autoSelectQuests = c.ns.db.config.autoAccept = True
        c.lua.globals().testNS = c.ns
        c.lua.execute('''
        selectedQuests = {}
        function available()
            local list={}
            for id=900,902 do if not testNS.active[id] then list[#list+1]=id end end
            return list
        end
        function GetNumAvailableQuests() return #available() end
        function GetAvailableQuestInfo(slot) return 'Quest',12,false,false,available()[slot] end
        function GetAvailableTitle(slot) return 'Quest '..available()[slot] end
        function GetQuestID() return openedQuest end
        function GetTitleText() return 'Quest '..openedQuest end
        function SelectAvailableQuest(slot)
            openedQuest=available()[slot]; selectedQuests[#selectedQuests+1]=openedQuest
            testNS.handlers.QUEST_DETAIL()
        end
        function AcceptQuest()
            entries[#entries+1]={questID=openedQuest,title='Quest '..openedQuest}
            testNS.handlers.QUEST_ACCEPTED(#entries,openedQuest)
            testNS.handlers.QUEST_FINISHED()
            C_Timer.After(0,function() testNS.handlers.QUEST_GREETING() end)
        end
        ''')
        c.ns.InitializeOffers()
        c.ns.handlers.QUEST_GREETING(); c.drain()
        self.assertEqual(list(c.lua.globals().selectedQuests.values()), [900,901,902])
        self.assertEqual(set(c.ns.active.keys()), {900,901,902})

    def test_adaptive_guide_collects_same_visit_without_pin_overriding_pickups(self):
        c, g = npc_client(unknown=False)
        g.fixedRoute, g.fullGuide = False, False
        c.ns.ActivateRoute(g)
        c.lua.globals().entries[1] = c.lua.table_from({'questID':900,'title':'First'})
        c.ns.ReadQuests(); c.ns.UpdateSelectedRoute(None, c.ns.NewQuestQuery())
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'q')
        offer(c, (901,902))
        self.assertEqual(pickup_ids(c), [901,902])
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'a')

    def test_same_character_reload_discards_old_availability(self):
        c, g = npc_client()
        offer(c); saved = primitive(c.ns.db)
        fresh = Client(quests=(), saved_variables=saved)
        fresh.guide_environment(level=12)
        fresh.ns.catalogue = fresh.lua.table_from(primitive(c.ns.catalogue), recursive=True)
        self.assertIsNone(fresh.ns.ObservedPickupAvailable(901))

    def test_partial_offer_creates_a_missing_character_bucket_before_merging(self):
        c, g = npc_client()
        c.ns.db.offerKnowledge[c.ns.self] = None
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID':901}], recursive=True), False)
        self.assertTrue(c.ns.ObservedPickupAvailable(901))
        self.assertIsNone(c.ns.ObservedPickupAvailable(902))


if __name__ == '__main__':
    unittest.main()
