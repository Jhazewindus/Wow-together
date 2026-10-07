"""Solo isolation, giver markers and read-only ordered guide browsing."""
import sys
import unittest
from pathlib import Path

from test_addon import Client
from test_063 import guide_client, zone, order
from test_061 import world_quest
from test_057 import plain
from test_routes import catalogue


def giver_client():
    c = guide_client(2)
    for quest in c.ns.catalogue.quests.values():
        quest.starts[1].entityID = 123
    c.ns.ActivateRoute(zone(c))
    c.lua.execute('''
    plate=CreateFrame('Frame');plate.namePlateUnitToken='nameplate1'
    C_NamePlate={GetNamePlateForUnit=function() return plate end,GetNamePlates=function() return {plate} end}
    function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end
    function SetRaidTarget() error('Cosmetic hint must not set a raid mark') end
    ''')
    c.ns.UpdateNPCHints()
    return c


class SoloTests(unittest.TestCase):
    def test_saved_solo_mode_skips_message_registration_and_party_roster(self):
        c = Client(saved_variables={'config': {'soloMode': True}})
        self.assertFalse(c.ns.syncReady)
        self.assertIsNone(c.ns.syncStats.registration)
        self.assertIsNone(c.ns.handlers.CHAT_MSG_ADDON)
        self.assertEqual(len(c.ns.partyNames), 0)
        self.assertEqual(len(c.ns.PartyProfiles()), 1)
        self.assertTrue(c.ns.questReady)
        c.ns.SyncNow(True)
        self.assertEqual(c.drain(), [])
        self.assertIn('Solo leveling', c.ns.status)

    def test_disabling_cancels_queued_messages_and_ignores_snapshots(self):
        c = Client(); c.ns.QueueMessage('1|Z|901')
        c.receive('1|S|1|1|1|1')
        self.assertIsNotNone(c.ns.members['Bob-TestRealm'])
        c.ns.SetOption('soloMode', True)
        self.assertEqual(c.ns.TransportState().queued, 0)
        self.assertFalse(c.ns.QueueMessage('1|H'))
        before = c.ns.syncStats.received
        c.receive('1|S|2|1|1|2')
        self.assertEqual(c.ns.syncStats.received, before)
        self.assertEqual(len(list(c.ns.members.keys())), 0)
        self.assertEqual(c.drain(), [])

    def test_reenable_uses_fresh_state_and_old_pump_cannot_send_new_session_twice(self):
        c = Client(); c.ns.QueueMessage('1|Z|901')
        c.receive('1|S|1|1|1|1')
        c.ns.SetOption('soloMode', True); c.ns.SetOption('soloMode', False)
        self.assertIsNone(c.ns.members['Bob-TestRealm'])
        messages = [m for _, m, _ in c.drain()]
        self.assertNotIn('1|Z|901', messages)
        self.assertEqual(messages.count('1|H'), 1)
        self.assertTrue(c.ns.syncReady)
        self.assertIsNotNone(c.ns.handlers.CHAT_MSG_ADDON)
        c.receive('1|S|2|1|1|2')
        self.assertIsNotNone(c.ns.members['Bob-TestRealm'].active[2])

    def test_solo_keeps_local_events_objectives_and_fixed_order_live_while_grouped(self):
        c = guide_client(2); g = zone(c); c.ns.ActivateRoute(g); before = order(g)
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.ns.SetOption('soloMode', True)
        c.lua.execute("entries={{questID=900,title='Accepted',isHeader=false}};C_QuestLog.GetQuestObjectives=function() return {{text='Boar slain',numFulfilled=2,numRequired=6,type='monster',finished=false}} end")
        c.ns.handlers.QUEST_ACCEPTED(1, 900); c.drain()
        self.assertIsNotNone(c.ns.active[900])
        self.assertEqual(c.ns.localProgress[900].objectives[1].have, 2)
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertEqual(c.ns.TransportState().queued, 0)
        self.assertEqual(len(c.ns.PartyProfiles()), 1)

    def test_solo_hides_party_views_controls_prompts_and_manual_tracker(self):
        c = Client()
        c.ns.pendingPartyRouteFollow = c.lua.table_from({'sender': 'Bob-TestRealm'})
        c.ns.partyRoutePrompt = c.lua.globals().CreateFrame('Frame'); c.ns.partyRoutePrompt.Show(c.ns.partyRoutePrompt)
        c.ns.ShowActivityPrompt('catchup:501', 'Catch up', 'Party progress', c.lua.eval('function() end'))
        c.ns.SetOption('soloMode', True)
        self.assertEqual(c.ns.filter, 'guides')
        for key in ('all', 'shared', 'different'):
            row = c.ns.ui.viewChoice.options[key]
            self.assertFalse(row.IsShown(row))
            c.ns.SetFilter(key); self.assertEqual(c.ns.filter, 'guides')
        for widget in (c.ns.ui.syncButton, c.ns.ui.trackerButton, c.ns.partyRoutePrompt, c.ns.activityPrompt):
            self.assertFalse(widget.IsShown(widget))
        c.ns.ToggleTracker(); self.assertFalse(c.ns.tracker.IsShown(c.ns.tracker))
        self.assertIsNone(c.ns.pendingPartyRouteFollow)
        self.assertFalse(c.ns.ShowPartyCatchup(None, True))
        self.assertEqual(c.ns.ui.metrics[1].value.text, 'SOLO')
        c.ns.SetOption('soloMode', False)
        self.assertTrue(c.ns.ui.syncButton.IsShown(c.ns.ui.syncButton))

    def test_solo_toggle_persists_and_probe_does_not_report_sync_failure(self):
        c = Client(); c.ns.SetOption('soloMode', True)
        other = Client(saved_variables=plain(c.ns.db))
        self.assertTrue(other.ns.Option('soloMode'))
        other.ns.Diagnostics()
        self.assertIn('party features disabled', other.ns.diagnosticsText.text)
        self.assertNotIn('Sync unavailable', other.ns.ui.status.text)


class GiverTests(unittest.TestCase):
    def test_gold_star_anchors_above_eligible_guide_giver_and_has_own_toggle(self):
        c = giver_client(); hint = c.ns.npcHints['nameplate1']
        self.assertTrue(hint.IsShown(hint)); self.assertTrue(hint.icon.IsShown(hint.icon))
        self.assertIn('UI-RaidTargetingIcon_1', hint.icon.texture)
        self.assertEqual(hint.icon.width, 34)
        self.assertEqual(hint.point[1], 'BOTTOM'); self.assertEqual(hint.point[3], 'TOP')
        self.assertFalse(hint.pointer.IsShown(hint.pointer))
        c.ns.SetOption('questGiverStars', False)
        self.assertFalse(hint.icon.IsShown(hint.icon)); self.assertTrue(hint.pointer.IsShown(hint.pointer))

    def test_locked_accepted_and_unrelated_quests_do_not_get_pickup_star(self):
        c = giver_client()
        for q in c.ns.catalogue.quests.values(): q.previousQuest = 902
        catalogue(c, {**{i:plain(q) for i,q in c.ns.catalogue.quests.items()}, 902:world_quest('Required parent')})
        c.ns.UpdateNPCHints(); self.assertEqual(c.ns.npcHintCount, 0)
        c.lua.globals().finished[902] = True; c.ns.UpdateNPCHints()
        self.assertTrue(c.ns.npcHints['nameplate1'].icon.IsShown(c.ns.npcHints['nameplate1'].icon))
        for i in (900,901): c.ns.active[i] = 'Accepted'
        c.ns.UpdateNPCHints(); self.assertEqual(c.ns.npcHintCount, 0)

    def test_combat_secret_npc_and_missing_plate_do_not_leave_stale_star(self):
        c = giver_client(); hint = c.ns.npcHints['nameplate1']
        c.lua.globals().combat = True; c.ns.handlers.PLAYER_REGEN_DISABLED()
        self.assertFalse(hint.IsShown(hint))
        c.lua.globals().combat = False; c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertTrue(hint.IsShown(hint))
        c.lua.execute('function UnitGUID() return secret end'); c.ns.UpdateNPCHints()
        self.assertFalse(hint.IsShown(hint))
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end; C_NamePlate.GetNamePlateForUnit=function() return nil end")
        c.ns.UpdateNPCHints(); self.assertEqual(c.ns.npcHintCount, 0)


class GuideBrowseTests(unittest.TestCase):
    def test_carry_your_weight_is_low_value_at_twelve_and_fixed_guides_do_not_bypass_it(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=12)
        self.assertFalse(c.ns.LevelingValue(791)[0])
        g = next(g for g in c.ns.LevelingGuideChoices().values() if g.zone == 'Durotar')
        c.ns.GenerateFixedGuide(g, False); original = order(g)
        route = c.ns.BuildFixedGuideRoute(g, False)
        self.assertFalse(any(s.id == 791 for s in route.stops.values()))
        self.assertFalse(any(s.id == 791 for s in route.previewStops.values()))
        self.assertEqual(order(g), original)
        self.assertFalse(c.ns.GuideQuestSkipped(791))
        c.ns.profile.level = 7
        self.assertTrue(c.ns.LevelingValue(791))
        self.assertFalse(any(s.id == 791 for s in c.ns.BuildFixedGuideRoute(g, False).previewStops.values()))
        starter = next(g for g in c.ns.LevelingGuideChoices(True, None, '1-10').values() if g.zone == 'Durotar')
        c.ns.GenerateFixedGuide(starter, False)
        self.assertTrue(any(s.id == 791 for s in c.ns.BuildFixedGuideRoute(starter, False).previewStops.values()))

    def test_fixed_guide_keeps_useful_chains_and_ready_turnins_but_filters_current_old_work(self):
        c = guide_client(2)
        catalogue(c, {900: world_quest('Old work', level=7),
                      901: world_quest('Current work')})
        g = c.ns.ZoneGuideForMap(501, True); c.ns.GenerateFixedGuide(g, False)
        c.ns.active[900] = 'Old work'
        self.assertFalse(any(s.id == 900 for s in c.ns.BuildFixedGuideRoute(g, False).stops.values()))
        included = c.ns.MergeCurrentQuests(g)
        self.assertFalse(any(s.id == 900 for s in c.ns.BuildFixedGuideRoute(included, False).stops.values()))
        c.ns.readyToTurnIn[900] = True
        self.assertTrue(any(s.id == 900 and s.kind == 't' for s in c.ns.BuildFixedGuideRoute(g, False).stops.values()))
        c.ns.active[900] = None; c.ns.readyToTurnIn[900] = None
        catalogue(c, {900: world_quest('Old work', level=7),
                      901: world_quest('Current work', previousQuest=900)})
        c.ns.GenerateFixedGuide(g, False)
        self.assertIn('Current work', c.ns.LevelingValue(900)[1])
        self.assertEqual(c.ns.BuildFixedGuideRoute(g, False).stops[1].id, 900)

    def test_fixed_start_asks_before_including_active_low_level_quests(self):
        c = guide_client(2); g = zone(c); c.ns.active[900] = 'Quest 0'
        c.ns.RequestStartRoute(g)
        self.assertTrue(c.ns.startGuidePrompt.IsShown(c.ns.startGuidePrompt))
        self.assertIsNone(c.ns.routeSelection)
        c.ns.startGuidePrompt.selected.OnClick(); c.drain()
        self.assertEqual(c.ns.routeSelection.key, g.key)
        c.ns.RequestStartRoute(g); c.ns.startGuidePrompt.current.OnClick(); c.drain()
        self.assertEqual(c.ns.routeSelection.mode, 'bundle')

    def test_adaptive_selected_guide_filters_current_old_work_but_keeps_ready_handins(self):
        c = guide_client(2)
        catalogue(c, {900: world_quest('Old work', level=7), 901: world_quest('Current work')})
        g = c.ns.ZoneGuideForMap(501, True); c.ns.active[900] = 'Old work'
        self.assertFalse(any(s.id == 900 for s in c.ns.BuildLevelingRoute(g, False, False).previewStops.values()))
        included = c.ns.MergeCurrentQuests(g)
        self.assertFalse(any(s.id == 900 for s in c.ns.BuildLevelingRoute(included, False, False).previewStops.values()))
        c.ns.readyToTurnIn[900] = True
        # A retained adaptive trip need not detour to a distant hand-in now,
        # but the full eligible preview must keep it for the next trip.
        self.assertTrue(any(s.id == 900 and s.kind == 't' for s in c.ns.BuildLevelingRoute(g, False, False).previewStops.values()))

    def test_all_welcome_variants_stay_in_catalogue_but_not_guides_or_retained_steps(self):
        c = Client(quests=(),use_catalogue=True); c.guide_environment(level=5)
        ids = {i for i,q in c.ns.catalogue.quests.items() if q.title == 'Welcome!'}
        self.assertEqual(len(ids), 7)
        self.assertTrue(all(c.ns.IsLevelingExcludedQuest(i) for i in ids))
        self.assertFalse(any(r.id in ids for g in c.ns.LevelingGuideChoices().values() for r in g.records.values()))
        c = guide_client(2); g = zone(c); c.ns.GenerateFixedGuide(g, False)
        c.ns.catalogue.quests[900].levelingExcluded = "Collector's Edition reward"
        result = c.ns.BuildFixedGuideRoute(g, False)
        self.assertFalse(any(s.id==900 for s in result.stops.values()))

    def test_selected_future_bracket_previews_without_qualifying_through_earlier_work(self):
        c = guide_client(2)
        catalogue(c,{900:world_quest('Starter',level=12),901:world_quest('Future',level=25,minLevel=20),
                     902:world_quest('Future two',level=26,minLevel=20)})
        c.ns.guideLevel='21-30'
        self.assertEqual(len(c.ns.LevelingGuideChoices()),1)
        self.assertFalse(c.ns.LevelingGuideChoices()[1].levelReady)
        c.ns.profile.level=25
        self.assertEqual(len(c.ns.LevelingGuideChoices()),1)

    def test_pickup_only_areas_capitals_are_hidden_but_real_later_sections_qualify(self):
        c=guide_client(2);c.ns.profile.level=25;c.ns.guideLevel='21-30'
        records={900+i:world_quest('Starter '+str(i),level=5) for i in range(20)}
        records[950]=world_quest('Outlier',level=25,minLevel=20)
        records[951]=world_quest('Outlier two',level=25,minLevel=20)
        catalogue(c,records);self.assertEqual(len(c.ns.LevelingGuideChoices()),1)
        self.assertEqual({r.id for r in c.ns.LevelingGuideChoices()[1].records.values()}, {950, 951})
        for map_id in (501,1454):
            catalogue(c,{900:world_quest('Pickup one',map_id=map_id,level=25,minLevel=20,objectives=[{'mapID':502,'x':.3,'y':.4,'name':'Remote work'}]),
                         901:world_quest('Pickup two',map_id=map_id,level=25,minLevel=20,objectives=[{'mapID':502,'x':.4,'y':.5,'name':'Remote work'}])})
            self.assertEqual(len(c.ns.LevelingGuideChoices()),0)

    def test_ordered_preview_is_read_only_scrollable_and_reuses_started_fixed_order(self):
        c=guide_client(30);g=zone(c);c.ns.GenerateFixedGuide(g,False);expected=order(g)
        c.ns.ShowGuideQuestList(g);frame=c.ns.guideQuestList
        self.assertEqual([(s.id,s.kind,s.mapID,s.x,s.y) for s in frame.plan.values()],expected)
        self.assertIsNone(c.ns.routeSelection)
        # Pool size follows the visible rows plus the partially visible edge,
        # independent of how compact the presentation is.
        self.assertLessEqual(len(frame.rows), int(frame.scroll.height / frame.rows[1].height) + 2)
        frame.offset=frame.maximum;c.ns.RenderGuideQuestList()
        self.assertEqual(max(r.step for r in frame.rows.values() if r.IsShown(r)),len(frame.plan))
        c.ns.ActivateRoute(g);c.ns.ShowGuideQuestList(zone(c))
        self.assertEqual([(s.id,s.kind,s.mapID,s.x,s.y) for s in frame.plan.values()],expected)
        self.assertEqual(order(c.ns.routeSelection),expected)

    def test_preview_loads_cooperatively_cancels_on_close_and_card_button_does_not_start(self):
        c=guide_client(12);c.ns.SetFilter('guides');c.ns.Refresh()
        card=c.ns.ui.cards[1]
        self.assertEqual(card.mapButton.caption.text,'Show quest list')
        self.assertEqual(card.detailsButton.caption.text,'Start route')
        card.mapButton.OnClick();frame=c.ns.guideQuestList
        self.assertIn('Loading',frame.summary.text);frame.Hide(frame);c.drain()
        self.assertIsNone(frame.plan);self.assertIsNone(c.ns.routeSelection)
        card.mapButton.OnClick();c.drain()
        self.assertIsNotNone(frame.plan);self.assertIsNone(c.ns.routeSelection)

    def test_catalogue_regeneration_preserves_bonus_exclusion_and_checks_identity(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
        from import_warcraftdb import generate
        self.assertIn('levelingExcluded',generate({5805:{'title':'Welcome!'}},'2026-10-05'))
        with self.assertRaises(ValueError): generate({5805:{'title':'A different quest'}},'2026-10-05')


if __name__ == '__main__': unittest.main()
