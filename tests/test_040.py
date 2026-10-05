import unittest
from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest, route_client


def objectives(c, id=900, have=2, need=6, done=False):
    c.lua.globals().objectiveData = c.lua.table_from({id: [{'text': f'Quest drops: {have}/{need}',
        'type': 'item', 'numFulfilled': have, 'numRequired': need, 'finished': done}]}, recursive=True)
    c.lua.execute('C_QuestLog.GetQuestObjectives=function(id) return objectiveData[id] end')
    c.ns.ReadProgress()


class UpdateTests(unittest.TestCase):
    def test_library_typing_is_deferred_enter_commits_and_page_is_bounded(self):
        c = Client(quests=())
        catalogue(c, {i: quest('Drop quest ' + str(i)) for i in range(100, 1000)})
        c.ns.SetFilter('library')
        c.ns.QueueLibrarySearch('D')
        c.ns.QueueLibrarySearch('Drop')
        self.assertIsNone(c.ns.librarySearch)
        c.ns.ApplyLibrarySearch()
        self.assertEqual(c.ns.librarySearch, 'Drop')
        self.assertEqual(c.ns.ui.visibleCards, 24)
        self.assertIn('900 results', c.ns.ui.libraryCount.text)
        c.ns.libraryPage = 38
        c.ns.Refresh()
        self.assertEqual(c.ns.ui.visibleCards, 12)
        c.ns.QueueLibrarySearch('missing')
        c.drain()
        self.assertEqual(c.ns.librarySearch, 'missing')
        self.assertEqual(c.ns.ui.visibleCards, 0)

    def test_pause_search_and_level_brackets_use_quest_level(self):
        c = route_client()
        catalogue(c, {900: quest(level=5, minLevel=1), 901: quest(level=12, minLevel=4),
                      902: quest(level=24), 903: {'title': 'No level', 'categoryPath': 'classes/mage'}})
        c.ns.OpenLibraryZone('map:501', 501)
        c.ns.SetLibraryLevel('11-20')
        items = c.ns.LibraryItems()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[1].id, 901)
        c.ns.SetLibraryLevel('party')
        self.assertEqual(c.ns.LibraryLevelRange(), (9, 15))
        c.ns.SetLibraryLevel('all')
        c.ns.QueueLibrarySearch('mage')
        c.drain()
        self.assertEqual(c.ns.LibraryItems()[1].id, 903)

    def test_real_catalogue_with_missing_zone_fields_can_be_searched(self):
        c = Client(quests=(), use_catalogue=True)
        c.ns.librarySearchDraft = 'd'
        c.ns.SetFilter('library')
        c.ns.ApplyLibrarySearch()
        self.assertEqual(c.ns.ui.visibleCards, 24)
        self.assertGreater(c.ns.catalogue.count, 5000)

    def test_nearby_pickups_and_objectives_form_one_circuit(self):
        c = route_client()
        catalogue(c, {900: quest(), 901: quest('Neighbour',
            starts=[{'mapID': 501, 'x': .21, 'y': .26, 'name': 'Neighbour NPC'}],
            objectives=[{'mapID': 501, 'x': .61, 'y': .41, 'name': 'Nearby target'}],
            ends=[{'mapID': 501, 'x': .21, 'y': .26, 'name': 'Neighbour NPC'}])})
        route = c.ns.BuildGuideRoute(guide(c, (900, 901), key='zone-route:501'), False)
        self.assertEqual([route.stops[i].kind for i in range(1, 7)], ['a', 'a', 'q', 'q', 't', 't'])
        self.assertEqual(route.stops[1].id, 901)  # The pickup nearest the player's position.
        for id in (900, 901):
            self.assertEqual([s.kind for s in route.stops.values() if s.id == id], ['a', 'q', 't'])

    def test_hello_retains_progress_and_missing_snapshot_recovery_is_bounded(self):
        c = route_client()
        c.receive('1|S|20|1|1|900')
        c.receive('1|P|12|2|501|Test Coast')
        c.receive('1|H')
        member = c.ns.members['Bob-TestRealm']
        self.assertTrue(member.active[900])
        self.assertTrue(member.syncPending)
        messages = [m for _, m, _ in c.drain()]
        self.assertEqual(messages.count('1|Q|Bob-TestRealm'), 3)
        c.receive('1|S|1|1|1|900')  # Reloaded peer restarts its revision counter.
        self.assertIsNone(member.syncPending)
        self.assertEqual(member.activeRevision, 1)

    def test_request_reply_includes_active_profile_destinations_and_objectives(self):
        c = route_client()
        c.lua.execute("entries={{questID=900,title='Shared quest',isHeader=false}}")
        c.ns.ReadQuests()
        objectives(c)
        c.receive('1|Q|Alice-TestRealm')
        messages = [m for _, m, _ in c.drain()]
        for kind in ('S', 'P', 'R', 'D', 'C', 'K'):
            self.assertTrue(any(m.startswith('1|' + kind + '|') for m in messages), kind)

    def test_route_does_not_clear_during_transient_peer_refresh(self):
        c = route_client()
        map_canvas(c)
        c.receive('1|S|1|1|1|900')
        c.receive('1|P|5|2|501|Test Coast')
        c.receive('1|R|1|900|501|60000|40000|q')
        c.receive('1|C|2|1|1|')
        c.receive('1|K|2|1|1|900')
        selection = guide(c, focus='Bob-TestRealm')
        selection.key = 'series:900'
        c.ns.ShowGuideOnMap(selection)
        c.receive('1|H')
        self.assertIsNotNone(c.ns.routeSelection)
        self.assertIsNotNone(c.ns.selectedRoute)
        self.assertIn('Waiting', c.ns.routeStats.status)
        self.assertGreater(c.ns.routeStats.pins, 0)
        c.receive('1|S|1|1|1|900')
        c.receive('1|P|5|2|501|Test Coast')
        c.receive('1|R|1|900|501|61000|41000|q')
        self.assertIsNone(c.ns.routePaused)

    def test_completed_local_quest_keeps_other_players_objective_and_turn_in(self):
        c = route_client()
        map_canvas(c)
        c.lua.execute("entries={{questID=900,title='Shared quest',isHeader=false}}")
        c.ns.ReadQuests(); c.ns.ReadGuide()
        c.receive('1|S|1|1|1|900')
        c.receive('1|P|12|2|501|Test Coast')
        c.receive('1|R|1|900|501|60000|40000|q')
        c.ns.ShowGuideOnMap(guide(c))
        c.lua.execute('entries={}; finished[900]=true')
        c.ns.SyncNow(False)
        self.assertIsNotNone(c.ns.selectedRoute)
        self.assertEqual(c.ns.selectedRoute.stops[1].memberKey, 'Bob-TestRealm')
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'q')
        c.receive('1|R|1|900|501|20000|25000|t')
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 't')
        c.receive('1|S|3|1|1|')
        self.assertIsNotNone(c.ns.routeSelection)
        c.receive('1|C|4|1|1|900')
        c.receive('1|K|4|1|1|900')
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)

    def test_three_players_only_clear_markers_after_last_completion(self):
        c = route_client()
        c.unit_names({'player': ('Alice', 'Test Realm'), 'party1': ('Bob', 'Test Realm'), 'party2': ('Carol', 'Test Realm')})
        c.lua.globals().finished[900] = True
        for sender in ('Bob-TestRealm', 'Carol-TestRealm'):
            c.receive('1|S|1|1|1|900', sender)
            c.receive('1|P|12|2|501|Test Coast', sender)
        self.assertFalse(c.ns.PartyQuestFinished(900))
        c.receive('1|S|3|1|1|', 'Bob-TestRealm'); c.receive('1|C|4|1|1|900', 'Bob-TestRealm')
        self.assertFalse(c.ns.PartyQuestFinished(900))
        route = c.ns.BuildGuideRoute(guide(c), False)
        self.assertEqual(route.stops[1].memberKey, 'Carol-TestRealm')
        c.receive('1|S|3|1|1|', 'Carol-TestRealm'); c.receive('1|C|4|1|1|900', 'Carol-TestRealm')
        self.assertTrue(c.ns.PartyQuestFinished(900))

    def test_ready_player_does_not_advance_party_past_unfinished_objectives(self):
        c = route_client()
        c.ns.active[900] = 'Shared quest'
        c.ns.routeLocations[900] = c.lua.table_from({'kind': 't', 'mapID': 501, 'x': .2, 'y': .25})
        c.receive('1|S|1|1|1|900')
        c.receive('1|R|1|900|501|60000|40000|q')
        route = c.ns.BuildGuideRoute(guide(c), False)
        self.assertEqual(route.stops[1].kind, 'q')
        self.assertEqual(route.stops[1].memberKey, 'Bob-TestRealm')
        c.receive('1|R|1|900|501|20000|25000|t')
        self.assertEqual(c.ns.BuildGuideRoute(guide(c), False).stops[1].kind, 't')

    def test_new_active_snapshot_invalidates_old_negative_history(self):
        c = route_client()
        c.receive('1|S|1|1|1|900'); c.receive('1|C|2|1|1|'); c.receive('1|K|2|1|1|900')
        self.assertFalse(c.ns.CatalogueCompletion('Bob-TestRealm', 900))
        c.receive('1|S|3|1|1|')
        self.assertIsNone(c.ns.CatalogueCompletion('Bob-TestRealm', 900))
        c.receive('1|C|4|1|1|900')
        self.assertTrue(c.ns.CatalogueCompletion('Bob-TestRealm', 900))

    def test_objective_counts_round_trip_and_tracker_compares_party(self):
        a, b = route_client(), Client(name='Bob', peer='Alice', quests=(900,))
        a.lua.execute("entries={{questID=900,title='Drop quest',isHeader=false}}")
        a.ns.ReadQuests()
        objectives(a, have=2); objectives(b, have=4)
        a.ns.SyncNow()
        for _, message, _ in a.drain(): b.receive(message, sender='Alice-TestRealm')
        p = b.ns.ProgressForMember('Alice-TestRealm', 900)
        self.assertEqual(p.objectives[1].have, 2)
        self.assertEqual(p.objectives[1].need, 6)
        self.assertEqual(b.ns.TrackerValue(b.ns.self, 900, 1), '4/6')
        self.assertEqual(b.ns.TrackerValue('Alice-TestRealm', 900, 1), '2/6')
        texts = [b.ns.tracker.lines[i].text for i in range(1, len(b.ns.tracker.lines)+1)]
        self.assertIn('2/6', texts)
        self.assertIn('4/6', texts)

    def test_restricted_counts_are_unknown_and_never_compared_or_serialized(self):
        c = route_client()
        c.ns.active[900] = 'Drops'
        c.lua.execute('C_QuestLog.GetQuestObjectives=function() return {{text=secret,type="item",numFulfilled=secret,numRequired=secret,finished=secret}} end')
        c.ns.ReadProgress()
        self.assertEqual(c.ns.TrackerValue(c.ns.self, 900, 1), '…')
        self.assertEqual(c.ns.restrictedObjectives, 1)
        self.assertIsNone(c.ns.localProgress[900].objectives[1].have)
        c.ns.SendProgress(True, 1)
        messages = [m for _, m, _ in c.drain()]
        self.assertTrue(any(',u,-,-,item,Objective' in m for m in messages))
        self.assertFalse(any('table:' in m for m in messages))

    def test_objective_revision_order_multipart_limits_and_unknown_counts(self):
        c = route_client()
        c.receive('1|D|2|900|10|2|2|3,0,-,-,event,Talk to NPC')
        c.receive('1|D|2|900|10|1|2|1,0,2,6,item,Drops;2,1,5,5,monster,Enemies')
        self.assertIsNone(c.ns.ProgressForMember('Bob-TestRealm', 900))
        c.receive('1|S|2|1|1|900')
        p = c.ns.ProgressForMember('Bob-TestRealm', 900)
        self.assertEqual(len(p.objectives), 3)
        self.assertEqual(p.objectives[1].have, 2)
        self.assertEqual(c.ns.TrackerValue('Bob-TestRealm', 900, 3), 'In progress')
        c.receive('1|D|2|900|9|1|1|1,0,1,6,item,Old data')
        self.assertEqual(c.ns.ProgressForMember('Bob-TestRealm', 900).objectives[1].have, 2)
        c.receive('1|D|2|900|11|1|1|13,0,1,6,item,Invalid index')
        self.assertEqual(c.ns.ProgressForMember('Bob-TestRealm', 900).objectives[1].have, 2)
        c.receive('1|D|2|900|11|1|1|1,0,1,6,item,Foreign', sender='Mallory-TestRealm')
        self.assertIsNone(c.ns.members['Mallory-TestRealm'])

    def test_tracker_toggle_persists_and_completion_does_not_hide_peer_quest(self):
        c = route_client()
        self.assertTrue(c.ns.tracker.IsShown(c.ns.tracker))
        c.ns.ToggleTracker(); self.assertFalse(c.ns.db.trackerVisible)
        c.ns.ToggleTracker(); self.assertTrue(c.ns.db.trackerVisible)
        c.lua.globals().finished[900] = True
        c.receive('1|S|1|1|1|900')
        c.receive('1|D|1|900|1|1|1|1,0,2,6,item,Drops')
        self.assertEqual(c.ns.TrackerRows()[1].id, 900)
        self.assertEqual(c.ns.TrackerValue(c.ns.self, 900, 1), 'Done')
        self.assertEqual(c.ns.TrackerValue('Bob-TestRealm', 900, 1), '2/6')

    def test_tracker_scroll_reaches_every_quest_and_objective(self):
        c = route_client()
        for id in range(900, 907):
            c.ns.active[id] = 'Quest ' + str(id)
        c.lua.execute('C_QuestLog.GetQuestObjectives=function() return {{text="First",finished=false},{text="Second",finished=false},{text="Third",finished=false},{text="Fourth",finished=false},{text="Fifth",finished=false}} end')
        c.ns.ReadProgress(); c.ns.RenderTracker()
        items, height, count = c.ns.TrackerDisplayLines()
        self.assertEqual(count, 7)
        self.assertGreater(height, c.ns.Option('trackerHeight'))
        self.assertTrue(any(items[i].text == 'Fifth' for i in range(1, len(items)+1)))
        c.ns.tracker.scroll.OnMouseWheel(c.ns.tracker.scroll, -1000)
        self.assertEqual(c.ns.tracker.scrollOffset, c.ns.tracker.scrollMaximum)
        shown = [c.ns.tracker.lines[i].text for i in range(1, len(c.ns.tracker.lines)+1)
                 if c.ns.tracker.lines[i].IsShown(c.ns.tracker.lines[i])]
        self.assertIn('Fifth', shown)
        self.assertLess(len(c.ns.tracker.lines), 65)
        c.ns.ScrollTracker(1000)
        self.assertEqual(c.ns.tracker.scrollOffset, 0)

    def test_restricted_objective_slot_does_not_shift_other_members_counters(self):
        c = route_client()
        c.ns.active[900] = 'Quest'
        c.lua.execute('C_QuestLog.GetQuestObjectives=function() return {secret,{text="Second",numFulfilled=2,numRequired=4,finished=false}} end')
        c.ns.ReadProgress()
        self.assertEqual(c.ns.TrackerValue(c.ns.self, 900, 1), '…')
        self.assertEqual(c.ns.TrackerValue(c.ns.self, 900, 2), '2/4')
        self.assertEqual(c.ns.localProgress[900].objectives[2].index, 2)

    def test_progress_packets_stay_within_byte_limit_with_maximum_counts_and_utf8(self):
        c = route_client()
        id = 2147483647
        c.ns.active[id] = 'Long counts'
        data = [{'text': 'é' * 60, 'numFulfilled': 2147483647, 'numRequired': 2147483647,
                 'type': 'abcdefghijkl', 'finished': False} for _ in range(12)]
        c.lua.globals().objectiveData = c.lua.table_from({id: data}, recursive=True)
        c.lua.execute('C_QuestLog.GetQuestObjectives=function(id) return objectiveData[id] end')
        c.ns.ReadProgress(); c.ns.SendProgress(True, 2147483647)
        messages = [m for _, m, _ in c.drain() if m.startswith('1|D|')]
        self.assertEqual(len(messages), 6)
        self.assertTrue(all(len(m.encode('utf-8')) <= 255 for m in messages))
        self.assertTrue(all('é' * 32 in m for m in messages))

    def test_party_completion_ignores_known_wrong_class_but_not_low_level(self):
        c = route_client()
        catalogue(c, {900: quest(classMask=128)})
        c.lua.globals().pyBand = lambda a, b: int(a) & int(b)
        c.lua.globals().pyShift = lambda a, b: int(a) << int(b)
        c.lua.execute('bit={band=function(a,b) return pyBand(a,b) end,lshift=function(a,b) return pyShift(a,b) end}')
        c.ns.profile.classID = 8
        c.lua.globals().finished[900] = True
        c.receive('1|S|1|1|1|')
        c.receive('1|P|12|2|501|Test Coast|7|8')
        self.assertTrue(c.ns.PartyQuestFinished(900))
        c.receive('1|S|2|1|1|900')  # Live activity overrides outdated catalogue restrictions.
        self.assertFalse(c.ns.PartyQuestFinished(900))
        c.receive('1|S|3|1|1|')
        c.receive('1|P|1|2|501|Test Coast|8|8')
        self.assertFalse(c.ns.PartyQuestFinished(900))
        c.receive('1|C|4|1|1|900')
        self.assertTrue(c.ns.PartyQuestFinished(900))

    def test_finished_objectives_without_turn_in_location_do_not_fall_back_to_kill_area(self):
        c = route_client()
        catalogue(c, {900: quest(ends=[])})
        c.ns.active[900] = 'Finished objectives'
        objectives(c, have=6, done=True)
        self.assertIsNone(c.ns.RouteStop(c.ns.CatalogueRecord(900), c.ns.self))
        c.lua.execute('C_QuestLog.IsComplete=function() return true end')
        c.ns.ReadRouteLocations()
        self.assertIsNone(c.ns.routeLocations[900])
        c.lua.execute('C_QuestLog.GetQuestObjectives=nil')
        c.ns.ReadProgress()
        self.assertIsNone(c.ns.RouteStop(c.ns.CatalogueRecord(900), c.ns.self))

    def test_npc_hints_use_public_ids_and_guard_combat_and_secret_guids(self):
        c = route_client()
        catalogue(c, {900: quest(objectives=[{'mapID': 501, 'x': .6, 'y': .4, 'name': 'Enemy',
                                             'entityID': 111, 'npc': True, 'action': 'kill'}])})
        c.ns.active[900] = 'Kill quest'
        c.lua.execute('plate=CreateFrame("Frame"); C_NamePlate={GetNamePlateForUnit=function() return plate end}; function UnitGUID() return "Creature-0-1-2-3-111-ABC" end')
        c.ns.handlers.NAME_PLATE_UNIT_ADDED('nameplate1')
        self.assertEqual(c.ns.npcHintCount, 1)
        self.assertTrue(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))
        c.lua.globals().combat = True
        c.ns.handlers.PLAYER_REGEN_DISABLED()
        self.assertFalse(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertTrue(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))
        c.lua.execute('function UnitGUID() return secret end')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)
        self.assertFalse(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))


if __name__ == '__main__':
    unittest.main()
