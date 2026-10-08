"""Mulgore offer rechecks and native current-guide quest highlighting.

Lua 5.1 host checks; native quest log/map behavior needs beta testing.
"""
import json
import unittest

from test_addon import Client, ROOT
from test_routes import catalogue, guide, map_canvas
from test_061 import world_quest
from test_063 import order, primitive
from test_076 import npc_client, offer
from import_warcraftdb import apply_corrections


def accepted(c, ids):
    c.lua.globals().entries = c.lua.table_from([
        {'questID':id, 'title':f'Quest {id}'} for id in ids], recursive=True)
    assert c.ns.ReadQuests()


class OfferRecheckTests(unittest.TestCase):
    def test_absence_survives_other_progress_reputation_and_reload(self):
        c, g = npc_client(False)
        offer(c, (901,))
        for change in ('accepted', 'abandoned', 'turned-in', 'reputation', 'level'):
            if change == 'accepted': accepted(c, (901,))
            elif change == 'abandoned': accepted(c, ())
            elif change == 'turned-in': c.ns.handlers.QUEST_TURNED_IN(800)
            elif change == 'reputation': c.ns.handlers.UPDATE_FACTION()
            else: c.lua.globals().playerLevel = 13
            self.assertFalse(c.ns.ObservedPickupAvailable(900), change)
            self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0], change)
        fresh = Client(quests=(), saved_variables=primitive(c.ns.db))
        fresh.guide_environment(level=13)
        fresh.ns.catalogue = fresh.lua.table_from(primitive(c.ns.catalogue), recursive=True)
        self.assertFalse(fresh.ns.ObservedPickupAvailable(900))
        self.assertIsNone(fresh.ns.ObservedPickupAvailable(901))  # Old positive is not current proof.

    def test_fresh_offer_restores_fixed_steps_without_reordering_or_skip(self):
        c, g = npc_client(False)
        before = order(g)
        offer(c, (901,))
        self.assertNotIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})
        c.ns.handlers.UPDATE_FACTION()
        c.ns.UpdateSelectedRoute()
        self.assertNotIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})
        offer(c, (900, 901))
        self.assertIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})
        self.assertEqual(order(g), before)
        self.assertFalse(c.ns.db.guideSkips[c.ns.self].quests[900])
        self.assertFalse(c.ns.Completed(900))

    def test_partial_offer_preserves_other_negatives_but_restores_its_own(self):
        c, g = npc_client(False)
        offer(c, ())
        c.ns.InvalidateNPCOffers()
        offer(c, (901,), full=False)
        self.assertTrue(c.ns.ObservedPickupAvailable(901))
        self.assertFalse(c.ns.ObservedPickupAvailable(900))
        offer(c, (900,), full=False)
        self.assertTrue(c.ns.ObservedPickupAvailable(900))

    def test_partial_or_restricted_empty_lists_do_not_create_absences(self):
        c, g = npc_client(False)
        offer(c, (), full=False)
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID':c.lua.globals().secret}], recursive=True))
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        self.assertEqual(len(c.ns.pickupRechecks), 0)

    def test_an_unchecked_alternative_giver_prevents_global_absence(self):
        c, g = npc_client(False)
        point = primitive(c.ns.catalogue.quests[900].starts[1]); point['entityID'] = 124
        c.ns.catalogue.quests[900].starts[2] = c.lua.table_from(point)
        offer(c, (901,))
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        c.lua.execute("UnitGUID=function() return 'Creature-0-1-2-3-124-ABC' end")
        offer(c, ())
        self.assertFalse(c.ns.ObservedPickupAvailable(900))
        offer(c, (900,), full=False)
        self.assertTrue(c.ns.ObservedPickupAvailable(900))

    def test_accepted_work_continues_and_other_characters_builds_are_not_blocked(self):
        c, g = npc_client(False)
        g.records = c.lua.table_from([c.ns.CatalogueRecord(900)])
        g.fixedPlan = None
        c.ns.ActivateRoute(g)
        offer(c, ())
        accepted(c, (900,))
        c.ns.UpdateSelectedRoute()
        self.assertIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})
        saved = primitive(c.ns.db)
        other = Client(name='Other', quests=(), saved_variables=saved)
        other.ns.catalogue = other.lua.table_from(primitive(c.ns.catalogue), recursive=True)
        self.assertIsNone(other.ns.ObservedPickupAvailable(900))
        changed = Client(quests=(), saved_variables=saved,
            before_load='GetBuildInfo=function() return "1.60.1","new-build",0,16001 end')
        changed.ns.catalogue = changed.lua.table_from(primitive(c.ns.catalogue), recursive=True)
        self.assertIsNone(changed.ns.ObservedPickupAvailable(900))

    def test_reviewed_mulgore_quests_need_actual_offers_without_guessed_gates(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=8)
        c.lua.globals().grouped = False; c.ns.UpdateRoster()
        c.ns.profile.raceID = 6
        for id, npc in ((99082, 2993), (99101, 3222)):
            q = c.ns.CatalogueQuest(id)
            self.assertTrue(q.pickupRequiresOffer)
            parent = {99082: 99080, 99101: 99081}[id]
            self.assertEqual(q.previousQuest, parent)
            c.lua.globals().finished[parent] = True
            self.assertEqual(q.minLevel, 4)
            self.assertFalse(c.ns.CatalogueAllowed(id, c.ns.profile, c.ns.self)[0])
            c.lua.execute(f"UnitGUID=function() return 'Creature-0-1-2-3-{npc}-ABC' end")
            c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID':id}], recursive=True), False)
            self.assertTrue(c.ns.CatalogueAllowed(id, c.ns.profile, c.ns.self))
        records = {id:{'title':c.ns.QuestTitle(id)} for id in (99082,99101)}
        self.assertEqual(set(apply_corrections(records)), {99082,99101})
        self.assertTrue(all(row['pickupRequiresOffer'] for row in records.values()))


class QuestFocusTests(unittest.TestCase):
    def client(self):
        c, g = npc_client(False)
        accepted(c, (900, 901))
        c.lua.execute('''
            selections, tracks = {}, {}
            C_QuestLog.SetSelectedQuest=function(id) selections[#selections+1]=id end
            C_SuperTrack={SetSuperTrackedQuestID=function(id) tracks[#tracks+1]=id end}
            C_Map.SetUserWaypoint=function() error('Unexpected user waypoint') end
        ''')
        c.ns.selectedRoute = c.lua.table_from({'mapID':501, 'stops':[{
            'id':900, 'kind':'q', 'title':'First', 'label':'Kill target',
            'mapID':501, 'x':.6, 'y':.4}]}, recursive=True)
        return c

    def test_selects_accepted_current_step_once_then_changes_with_progress(self):
        c = self.client()
        c.ns.UpdateGuideQuestFocus(); c.ns.UpdateGuideQuestFocus()
        self.assertEqual(list(c.lua.globals().selections.values()), [900])
        self.assertEqual(list(c.lua.globals().tracks.values()), [900])
        c.ns.selectedRoute.stops[1].id, c.ns.selectedRoute.stops[1].kind = 901, 't'
        c.ns.UpdateGuideQuestFocus()
        self.assertEqual(list(c.lua.globals().selections.values()), [900,901])

    def test_native_selection_avoids_blizzard_lua_details_helper_and_does_not_open_map(self):
        c = self.client()
        c.lua.execute('''
            QuestMapFrame_ShowQuestDetails=function() error('Taint-prone UI helper called') end
            OpenQuestLog=function() error('Should not open quest log') end
            WorldMapFrame.Show=function() error('Should not open world map') end
        ''')
        c.ns.UpdateGuideQuestFocus()
        self.assertEqual(c.lua.globals().selections[1], 900)
        self.assertEqual(len(c.lua.globals().selections), 1)

    def test_disabled_arrow_panels_still_select_but_option_off_does_not(self):
        c = self.client()
        c.ns.db.config.routeArrow, c.ns.db.config.standaloneArrow = False, False
        c.ns.UpdateGuideQuestFocus()
        self.assertEqual(len(c.lua.globals().selections), 1)
        c.ns.db.config.highlightGuideQuest = False
        c.ns.selectedRoute.stops[1].id = 901
        c.ns.UpdateGuideQuestFocus()
        self.assertEqual(len(c.lua.globals().selections), 1)

    def test_combat_defers_and_rechecks_latest_step_in_shared_event_handler(self):
        c = self.client()
        c.lua.globals().combat = True
        c.ns.UpdateGuideQuestFocus()
        c.ns.selectedRoute.stops[1].id = 901
        c.ns.UpdateGuideQuestFocus()
        self.assertEqual(len(c.lua.globals().selections), 0)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertEqual(list(c.lua.globals().selections.values()), [901])

    def test_unaccepted_private_loading_preview_and_missing_apis_are_handled(self):
        c = self.client()
        for id in (902, 0, c.lua.globals().secret):
            c.ns.selectedRoute.stops[1].id = id
            c.ns.UpdateGuideQuestFocus()
        c.ns.selectedRoute.stops[1].id = 900
        c.ns.guideScanning = c.lua.table_from({'guide':c.ns.routeSelection})
        c.ns.UpdateGuideQuestFocus()
        self.assertEqual(len(c.lua.globals().selections), 0)
        c.ns.guideScanning = None
        c.ns.navigationPreview = c.lua.table_from({'stop':{'id':901}}, recursive=True)
        c.ns.UpdateGuideQuestFocus()
        self.assertEqual(c.lua.globals().selections[1], 900)
        c.lua.execute('C_QuestLog.SetSelectedQuest=nil; C_SuperTrack=nil')
        c.ns.UpdateGuideQuestFocus()
        self.assertIn('unavailable', c.ns.guideQuestFocusStatus)

    def test_native_selection_event_cannot_reenter_or_repeat_on_navigation_ticks(self):
        c = self.client()
        c.lua.globals().focus = c.ns.UpdateGuideQuestFocus
        c.lua.execute('C_QuestLog.SetSelectedQuest=function(id) selections[#selections+1]=id; focus() end')
        c.ns.UpdateGuideQuestFocus()
        for _ in range(5): c.ns.UpdateNavigation()
        self.assertEqual(len(c.lua.globals().selections), 1)

    def test_refresh_and_real_skip_follow_the_new_fixed_guide_target(self):
        c = self.client()
        g = c.ns.routeSelection
        g.records = c.lua.table_from([c.ns.CatalogueRecord(900), c.ns.CatalogueRecord(901)])
        g.fixedPlan = None
        c.ns.ActivateRoute(g)
        before = order(g)
        c.ns.Refresh()
        first = c.ns.selectedRoute.stops[1].id
        self.assertEqual(c.lua.globals().selections[len(c.lua.globals().selections)], first)
        c.ns.SkipGuide('quest')
        second = c.ns.selectedRoute.stops[1].id
        self.assertNotEqual(second, first)
        self.assertEqual(c.lua.globals().selections[len(c.lua.globals().selections)], second)
        self.assertEqual(order(g), before)


class SuppliedResearchTests(unittest.TestCase):
    def test_partial_duplicates_are_preserved_and_only_whole_events_recovered(self):
        folder = ROOT / 'research'
        reviewed = json.loads((folder/'2026-10-06-mulgore-recovered-events.json').read_text())
        self.assertTrue(reviewed['partial'])
        self.assertTrue(reviewed['deduplicated'])
        self.assertEqual(reviewed['eventCount'], 94)
        recovered = []
        for source in reviewed['sources']:
            raw = (folder/source).read_text()
            self.assertIn('KB left)', raw)
            decoder, events = json.JSONDecoder(), []
            pos = raw.index('"events":[')+len('"events":[')
            while True:
                while pos<len(raw) and raw[pos] in ' \n\r\t,': pos += 1
                try: event, pos = decoder.raw_decode(raw,pos)
                except json.JSONDecodeError: break
                events.append(event)
            self.assertEqual(events, reviewed['events'])
            recovered.append(events)
        self.assertEqual(recovered[0], recovered[1])
        for id,npc in ((99082,2993),(99101,3222)):
            self.assertFalse(any(id in e.get('offered', []) for e in reviewed['events']))
            self.assertTrue(any(e.get('event')=='defer-pickup' and e.get('questID')==id for e in reviewed['events']))
            self.assertTrue(any(e.get('npcID')==npc and e.get('completeList') for e in reviewed['events']))

    def test_new_kadrak_export_is_partial_and_does_not_establish_the_live_quest_id(self):
        reviewed = json.loads((ROOT/'research/2026-10-06-kadrak-recovered-events.json').read_text())
        self.assertTrue(reviewed['partial'])
        self.assertEqual(reviewed['eventCount'], 77)
        self.assertEqual(reviewed['lastSequence'], 77)
        self.assertFalse(any(e.get('npcID') == 11821 for e in reviewed['events']))
        self.assertFalse(any(id in e.get('active', []) for e in reviewed['events'] for id in (6541,6542)))


class AlternativeQuestTests(unittest.TestCase):
    def client(self, current=6541, completed=()):
        c = Client(quests=(current,) if current else (), completed=completed, use_catalogue=True)
        c.guide_environment(level=21); map_canvas(c)
        c.lua.globals().grouped = False
        c.unit_names({'player':['Alice','TestRealm']})
        c.ns.profile.raceID = 5
        return c

    def test_shipped_report_variants_both_directions_keep_active_work(self):
        for chosen,other in ((6541,6542),(6542,6541)):
            c = self.client(chosen)
            self.assertEqual(list(c.ns.CatalogueQuest(chosen).exclusiveQuests.values()), [other])
            self.assertEqual(c.ns.CatalogueAlternativeTaken(other,c.ns.self), chosen)
            self.assertFalse(c.ns.CatalogueAllowed(other,c.ns.profile,c.ns.self)[0])
            self.assertIsNone(c.ns.CatalogueAlternativeTaken(chosen,c.ns.self))
            self.assertFalse(c.ns.Completed(other))

    def test_fixed_guides_do_not_request_the_duplicate_or_count_it_as_unfinished(self):
        c = self.client()
        g = guide(c,(6541,6542)); g.fixedRoute, g.fullGuide, g.mode = True,True,'zone'
        c.ns.ActivateRoute(g)
        before = order(g)
        self.assertNotIn(6542, {s.id for s in c.ns.selectedRoute.stops.values()})
        progress = c.ns.selectedRoute.completionProgress
        self.assertEqual((progress.total,progress.unfinished,progress.completed), (1,1,0))
        accepted(c, ())
        c.ns.handlers.QUEST_TURNED_IN(6541)
        c.ns.UpdateSelectedRoute()
        progress = c.ns.selectedRoute.completionProgress
        self.assertEqual((progress.total,progress.unfinished,progress.completed), (1,0,1))
        self.assertFalse(c.ns.Completed(6542))
        self.assertEqual(order(g), before)

    def test_same_title_without_an_explicit_relation_does_not_block_another_chain_step(self):
        c, g = npc_client(False)
        c.ns.catalogue.quests[900].title, c.ns.catalogue.quests[901].title = 'Repeated title','Repeated title'
        accepted(c, (900,))
        self.assertIsNone(c.ns.CatalogueAlternativeTaken(901,c.ns.self))
        self.assertTrue(c.ns.CatalogueAllowed(901,c.ns.profile,c.ns.self))

    def test_source_correction_validates_both_identities_and_does_not_infer_a_relation(self):
        records = {6541:{'title':'Report to Kadrak'},6542:{'title':'Report to Kadrak'}}
        self.assertEqual(apply_corrections(records), [6541,6542])
        self.assertEqual(records[6542]['exclusiveQuests'],[6541])
        self.assertIn('e0a6eaa86f181ac99262e34126bcd2ed1a1712d6',records[6541]['exclusiveQuestSource'])
        records[6542]['title']='Other quest'
        with self.assertRaises(ValueError): apply_corrections(records)

    def test_alternative_scope_is_personal_and_active_quests_override_old_exclusion(self):
        c = self.client()
        # Owning both due to changed beta behavior must not discard real work.
        accepted(c,(6541,6542))
        self.assertIsNone(c.ns.CatalogueAlternativeTaken(6542,c.ns.self))
        accepted(c,(6541,))
        key='Bob-TestRealm'
        c.ns.members[key]=c.lua.table_from({'active':{},'completed':{},'activeRevision':1,
            'completionRevision':1,'historyRevision':1,'historyChecked':{6541:True,6542:True}},recursive=True)
        self.assertIsNone(c.ns.CatalogueAlternativeTaken(6542,key))
        c.ns.members[key].active[6541]='Report to Kadrak'
        self.assertEqual(c.ns.CatalogueAlternativeTaken(6542,key),6541)
        c.ns.members[key].syncPending=True
        self.assertIsNone(c.ns.CatalogueAlternativeTaken(6542,key))


class GuideQuestItemTests(unittest.TestCase):
    def client(self):
        c = QuestFocusTests().client()
        c.lua.execute('''
            itemReads, used = 0, {}
            C_QuestLog.GetLogIndexForQuestID=function(id)
                for i, entry in ipairs(entries) do if entry.questID==id then return i end end
            end
            GetQuestLogSpecialItemInfo=function(index)
                itemReads=itemReads+1
                local entry=entries[index]
                if entry and entry.questID==900 and not itemMissing then
                    return '|Hitem:123|h[Testing Wand]|h', 12345, 1, false
                end
            end
            UseQuestLogSpecialItem=function(index) used[#used+1]=index end
        ''')
        c.ns.UpdateGuideQuestItem(); c.ns.UpdateNavigation()
        return c

    def click(self, c):
        b=c.ns.navigation.questItem
        return b.OnClick(b, 'LeftButton')

    def test_manual_click_uses_current_log_index_not_quest_id_and_never_auto_uses(self):
        c=self.client()
        b=c.ns.navigation.questItem
        self.assertTrue(b.IsShown(b))
        self.assertIn('Testing Wand', b.caption.text)
        reads=c.lua.globals().itemReads
        for _ in range(5): c.ns.UpdateNavigation()
        self.assertEqual(c.lua.globals().itemReads,reads)
        self.assertEqual(len(c.lua.globals().used),0)
        self.assertTrue(self.click(c))
        self.assertEqual(list(c.lua.globals().used.values()),[1])

    def test_changed_log_headers_or_order_are_resolved_again_on_click(self):
        c=self.client()
        c.lua.execute("table.insert(entries,1,{isHeader=true,title='Zone'})")
        self.assertTrue(self.click(c))
        self.assertEqual(list(c.lua.globals().used.values()),[2])

    def test_changed_route_or_removed_item_never_uses_the_stale_button(self):
        c=self.client()
        c.ns.selectedRoute.stops[1].id=901
        self.assertFalse(self.click(c))
        self.assertFalse(c.ns.navigation.questItem.IsShown(c.ns.navigation.questItem))
        c.ns.selectedRoute.stops[1].id=900
        c.ns.UpdateGuideQuestItem(); c.ns.UpdateNavigation()
        c.lua.globals().itemMissing=True
        self.assertFalse(self.click(c))
        self.assertEqual(len(c.lua.globals().used),0)

    def test_bad_native_index_cannot_use_a_header_or_another_quest(self):
        c=self.client()
        c.lua.execute('C_QuestLog.GetLogIndexForQuestID=function() return 2 end')
        self.assertFalse(self.click(c))
        self.assertEqual(len(c.lua.globals().used),0)

    def test_no_lookup_api_falls_back_to_verified_public_quest_entries(self):
        c=self.client()
        c.lua.execute("C_QuestLog.GetLogIndexForQuestID=nil; table.insert(entries,1,{isHeader=true,title='Zone'})")
        self.assertTrue(self.click(c))
        self.assertEqual(list(c.lua.globals().used.values()),[2])

    def test_combat_block_is_not_queued_for_later_automatic_use(self):
        c=self.client()
        c.lua.globals().combat=True; c.ns.UpdateNavigation()
        self.assertFalse(c.ns.navigation.questItem.enabled)
        self.assertFalse(self.click(c))
        c.lua.globals().combat=False; c.ns.handlers.PLAYER_REGEN_ENABLED()
        c.ns.UpdateNavigation()
        self.assertEqual(len(c.lua.globals().used),0)
        self.assertTrue(c.ns.navigation.questItem.enabled)
        self.assertTrue(self.click(c))

    def test_missing_restricted_or_uncached_item_data_hides_button_until_event(self):
        c=self.client()
        c.lua.execute('GetQuestLogSpecialItemInfo=function() return secret end')
        c.ns.UpdateGuideQuestItem(); c.ns.UpdateNavigation()
        self.assertIsNone(c.ns.guideQuestItem)
        self.assertFalse(self.click(c))
        c.lua.execute("GetQuestLogSpecialItemInfo=function() return '|Hitem:123|h[Testing Wand]|h',12345,1,false end")
        c.ns.handlers.ITEM_DATA_LOAD_RESULT(123,True)
        self.assertTrue(c.ns.navigation.questItem.IsShown(c.ns.navigation.questItem))
        c.lua.execute('UseQuestLogSpecialItem=nil')
        c.ns.UpdateGuideQuestItem(); c.ns.UpdateNavigation()
        self.assertIn('unavailable',c.ns.guideQuestItemStatus)
        self.assertFalse(self.click(c))

    def test_non_objective_states_preview_flight_and_loading_do_not_offer_item_use(self):
        c=self.client()
        stop=c.ns.selectedRoute.stops[1]
        for kind in ('a','t','corpse','notice','f','loading'):
            stop.kind=kind
            c.ns.UpdateGuideQuestItem(); c.ns.UpdateNavigation()
            self.assertIsNone(c.ns.guideQuestItem,kind)
        stop.kind='q'
        c.ns.navigationPreview=c.lua.table_from({'stop':dict(id=901,kind='q',title='Other',mapID=501,x=.5,y=.5)},recursive=True)
        c.ns.UpdateGuideQuestItem(); self.assertIsNone(c.ns.guideQuestItem)
        c.ns.navigationPreview=None
        c.lua.execute('UnitOnTaxi=function() return true end')
        c.ns.UpdateGuideQuestItem(); self.assertIsNone(c.ns.guideQuestItem)
        c.lua.execute('UnitOnTaxi=function() return false end; UnitIsGhost=function() return true end')
        c.ns.UpdateGuideQuestItem(); self.assertIsNone(c.ns.guideQuestItem)
        c.lua.execute('UnitIsGhost=function() return false end')
        c.ns.guideScanning=c.lua.table_from({'guide':c.ns.routeSelection})
        c.ns.UpdateGuideQuestItem(); self.assertIsNone(c.ns.guideQuestItem)

    def test_item_strip_keeps_objectives_and_tips_separate_and_respects_hidden_panel(self):
        c=self.client()
        nav=c.ns.navigation
        same=c.lua.eval('rawequal')
        self.assertTrue(same(nav.questItem.point[2],nav))
        self.assertTrue(same(nav.tip.point[2],nav.questItem))
        c.ns.db.config.routeArrow=False
        c.ns.UpdateNavigation()
        self.assertFalse(nav.questItem.IsShown(nav.questItem))
        self.assertFalse(self.click(c))
        self.assertEqual(len(c.lua.globals().used),0)


if __name__ == '__main__': unittest.main()
