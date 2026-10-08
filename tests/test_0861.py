"""Session save/pause/resume and measured personal totals under Lua 5.1.

Native beta event ordering and actual UI rendering still need the release checklist.
"""
import unittest

from test_addon import Client
from test_063 import guide_client, zone, order, primitive
from test_061 import run_plan
from test_routes import map_canvas
from test_0836 import crafting


NATIVE = '''
sessionClock=100; sessionXP=100; sessionMax=1000; playerLevel=12
function GetTime() return sessionClock end
function UnitXP() return sessionXP end
function UnitXPMax() return sessionMax end
function UnitLevel() return playerLevel end
'''


def playing():
    c = guide_client(3)
    c.lua.execute(NATIVE)
    c.ns.ReadProfile(); c.ns.ReadGuideXP()
    c.ns.ShowGuideOnMap(zone(c)); run_plan(c)
    return c


def session(c):
    return c.ns.GuideSessionSummary()


def fresh(c, completed=(), active=()):
    c.ns.handlers.PLAYER_LOGOUT()
    saved = primitive(c.ns.db)
    n = Client(quests=active, completed=completed, saved_variables=saved, before_load=NATIVE)
    n.guide_environment(level=12); map_canvas(n)
    n.lua.globals().sessionClock = 50000
    n.lua.globals().sessionXP = 600
    n.lua.globals().grouped = False
    n.ns.UpdateRoster()
    n.ns.catalogue = n.lua.table_from(primitive(c.ns.catalogue), recursive=True)
    n.ns.handlers.PLAYER_LOGIN(); run_plan(n); n.drain()
    return n


class SessionTotalsTests(unittest.TestCase):
    def test_same_level_xp_turn_ins_and_played_time_are_measured(self):
        c = playing()
        c.lua.execute('sessionXP=400; sessionClock=190')
        c.ns.handlers.PLAYER_XP_UPDATE('player')
        c.ns.handlers.QUEST_TURNED_IN(900)
        c.ns.handlers.QUEST_TURNED_IN(900)
        c.ns.CaptureSessionCheckpoint()
        s = session(c)
        self.assertEqual((s.xp, s.quests, s.seconds), (300, 1, 90))
        self.assertEqual((s.startLevel, s.endLevel), (12, 12))
        self.assertIn('300 XP', c.ns.GuideSessionSummaryText())
        self.assertFalse(s.xpPartial)

    def test_level_boundary_counts_remaining_native_xp(self):
        c = playing()
        c.lua.execute('playerLevel=13; sessionXP=75; sessionMax=1200')
        c.ns.handlers.PLAYER_XP_UPDATE('player')
        self.assertEqual(session(c).xp, 975)
        self.assertEqual(session(c).endLevel, 13)

    def test_multi_level_uses_only_observed_native_curve(self):
        c = playing(); c.ns.xpCurve[13] = 1200
        c.lua.execute('playerLevel=14; sessionXP=50; sessionMax=1600')
        c.ns.CaptureSessionCheckpoint()
        self.assertEqual(session(c).xp, 2150)
        d = playing()
        d.lua.execute('playerLevel=14; sessionXP=50; sessionMax=1600')
        d.ns.CaptureSessionCheckpoint()
        self.assertEqual(session(d).xp, 0)
        self.assertTrue(session(d).xpPartial)
        self.assertNotIn('estimate', d.ns.GuideSessionSummaryText())

    def test_level_notification_does_not_count_the_old_xp_twice(self):
        c = playing()
        c.lua.execute('playerLevel=13')  # Level event arrives before XP resets.
        c.ns.handlers.PLAYER_LEVEL_UP(13)
        self.assertEqual(session(c).xp, 0)
        c.lua.execute('sessionXP=75; sessionMax=1200')
        c.ns.handlers.PLAYER_XP_UPDATE('player')
        self.assertEqual(session(c).xp, 975)

    def test_secret_missing_and_backwards_values_never_invent_totals(self):
        c = playing()
        c.lua.execute('sessionXP=secret; sessionClock=secret')
        c.ns.CaptureSessionCheckpoint()
        c.lua.execute('sessionXP=300; sessionClock=50')
        c.ns.CaptureSessionCheckpoint()
        self.assertEqual((session(c).xp, session(c).seconds), (0, 0))
        c.lua.execute('sessionClock=40; sessionXP=250')
        c.ns.CaptureSessionCheckpoint()
        self.assertTrue(session(c).xpPartial)
        self.assertTrue(session(c).timePartial)
        self.assertIn('At least', c.ns.GuideSessionSummaryText())

    def test_without_native_apis_summary_stays_honest(self):
        c = guide_client(3); c.ns.ActivateRoute(zone(c))
        self.assertIn('XP unavailable', c.ns.GuideSessionSummaryText())
        self.assertEqual(session(c).xp, 0)

    def test_no_active_guide_does_not_track_and_peer_progress_is_not_personal(self):
        c = playing()
        c.receive('1|C|1|1|1|900')
        self.assertEqual(session(c).quests, 0)
        c.ns.PauseGuideSession()
        c.lua.execute('sessionXP=800; sessionClock=600')
        c.ns.handlers.PLAYER_XP_UPDATE('player'); c.ns.handlers.QUEST_TURNED_IN(999)
        self.assertEqual((session(c).xp, session(c).quests, session(c).seconds), (0, 0, 0))

    def test_different_guide_finishes_previous_session_and_same_guide_continues(self):
        c = playing(); g = c.ns.routeSelection
        c.lua.execute('sessionXP=200; sessionClock=130')
        c.ns.ActivateRoute(g)
        self.assertEqual((session(c).xp, session(c).seconds), (100, 30))
        c.lua.execute('sessionXP=300; sessionClock=160')
        replacement = c.lua.table_from(primitive(g), recursive=True)
        replacement.key, replacement.title = 'other-guide', 'Other guide'
        c.ns.ActivateRoute(replacement)
        state = c.ns.db.guideSessions[c.ns.self]
        self.assertEqual((state.last.xp, state.last.seconds), (200, 60))
        self.assertEqual((state.current.xp, state.current.seconds), (0, 0))

    def test_internal_descriptor_changes_keep_tracking_and_reload_summary(self):
        c = playing()
        replacement = c.lua.table_from(primitive(c.ns.routeSelection), recursive=True)
        replacement.key = 'adaptive:updated'
        c.ns.routeSelection = replacement
        c.lua.execute('sessionXP=250; sessionClock=140')
        c.ns.SaveSelectedGuide(); c.ns.CaptureSessionCheckpoint()
        self.assertEqual((session(c).xp, session(c).seconds), (150, 40))
        self.assertEqual(session(c).key, replacement.key)
        n = fresh(c)
        self.assertEqual((session(n).xp, session(n).seconds), (150, 40))


class SessionCheckpointTests(unittest.TestCase):
    def test_pause_saves_order_and_skips_and_resume_uses_current_progress(self):
        c = playing(); before = order(c.ns.routeSelection)
        c.ns.SkipGuide('quest')
        skipped = primitive(c.ns.db.guideSkips)
        self.assertTrue(c.ns.PauseGuideSession())
        self.assertIsNone(c.ns.routeSelection)
        self.assertIsNone(c.ns.selectedRoute)
        self.assertTrue(c.ns.PausedSessionCheckpoint().paused)
        c.lua.execute('finished[901]=true')
        self.assertTrue(c.ns.ResumeGuideSession()); run_plan(c)
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertNotIn(901, {s.id for s in c.ns.selectedRoute.stops.values()})
        self.assertEqual(primitive(c.ns.db.guideSkips), skipped)
        self.assertIsNone(c.ns.PausedSessionCheckpoint())

    def test_paused_login_waits_for_resume_and_does_not_count_offline_activity(self):
        c = playing(); c.lua.execute('sessionXP=200; sessionClock=160')
        c.ns.PauseGuideSession(); n = fresh(c, completed=(900,))
        self.assertIsNone(n.ns.routeSelection)
        self.assertIsNone(n.ns.pendingSavedGuide)
        self.assertIsNotNone(n.ns.PausedSessionCheckpoint())
        self.assertEqual((session(n).xp, session(n).seconds), (100, 60))
        n.ns.SetFilter('recommended')
        self.assertEqual(n.ns.ui.home.resume.button.caption.text, 'Resume')
        n.ns.ui.home.resume.button.OnClick(); run_plan(n)
        self.assertNotIn(900, {s.id for s in n.ns.selectedRoute.stops.values()})
        self.assertEqual((session(n).xp, session(n).seconds), (0, 0))

    def test_normal_reload_continues_session_without_offline_time_or_xp(self):
        c = playing(); c.lua.execute('sessionXP=250; sessionClock=150')
        n = fresh(c)
        self.assertIsNotNone(n.ns.routeSelection)
        self.assertEqual((session(n).xp, session(n).seconds), (150, 50))
        n.lua.execute('sessionXP=700; sessionClock=50030')
        n.ns.CaptureSessionCheckpoint()
        self.assertEqual((session(n).xp, session(n).seconds), (250, 80))

    def test_stop_discards_resume_exit_of_paused_window_keeps_it(self):
        c = playing(); c.ns.StopGuide(False)
        self.assertIsNone(c.ns.db.guideState[c.ns.self])
        self.assertIsNone(c.ns.db.guideSessions[c.ns.self].current)
        d = playing(); d.ns.PauseGuideSession()
        d.ns.navigation.close.OnClick()
        self.assertIsNotNone(d.ns.PausedSessionCheckpoint())
        self.assertFalse(d.ns.navigation.IsShown(d.ns.navigation))
        e = playing(); e.ns.PauseGuideSession()
        self.assertTrue(e.ns.navigation.stop.IsEnabled(e.ns.navigation.stop))
        e.ns.navigation.stop.OnClick()
        self.assertIsNone(e.ns.PausedSessionCheckpoint())
        self.assertIsNone(e.ns.routeSelection)

    def test_resume_in_combat_or_during_another_guide_never_replaces_it(self):
        c = playing(); c.ns.PauseGuideSession(); c.lua.globals().combat = True
        self.assertFalse(c.ns.ResumeGuideSession())
        self.assertIsNotNone(c.ns.PausedSessionCheckpoint())
        self.assertIsNone(c.ns.pendingSavedGuide)
        c.lua.globals().combat = False
        c.ns.ActivateRoute(zone(c))
        key = c.ns.routeSelection.key
        self.assertFalse(c.ns.ResumeGuideSession())
        self.assertEqual(c.ns.routeSelection.key, key)

    def test_real_step_saved_even_with_a_preview_or_detour(self):
        c = playing(); actual = c.ns.selectedRoute.stops[1]
        c.ns.navigationPreview = c.lua.table_from({'stop': {'id': 999, 'title': 'Other target'}}, recursive=True)
        c.ns.CaptureSessionCheckpoint()
        checkpoint = c.ns.db.guideState[c.ns.self].checkpoint
        self.assertEqual(checkpoint.questID, actual.id)
        self.assertEqual(checkpoint.next, actual.title)

    def test_profession_checkpoint_rechecks_actual_skill_and_keeps_goal(self):
        c = crafting(); c.lua.execute(NATIVE)
        c.ns.StartProfessionGuide(171, 150)
        c.ns.PauseGuideSession(); c.lua.globals().pskill = 35
        self.assertTrue(c.ns.ResumeGuideSession())
        self.assertEqual(c.ns.routeSelection.targetSkill, 150)
        self.assertEqual(c.ns.professionData[171].skill, 35)

    def test_bounded_stats_do_not_duplicate_the_guide_blueprint(self):
        c = playing()
        for _ in range(20): c.ns.CaptureSessionCheckpoint()
        data = primitive(c.ns.db.guideSessions[c.ns.self])
        self.assertEqual(set(data), {'current'})
        self.assertNotIn('fixedPlan', str(data))
        self.assertNotIn('records', str(data))
        self.assertEqual(len(c.ns.db.guideState[c.ns.self].guide.fixedPlan), 9)
        c.ns.db.guideState['Other-TestRealm'] = c.lua.table_from({'schema': 1})
        c.ns.StopGuide(True)
        self.assertIsNotNone(c.ns.db.guideState['Other-TestRealm'])

    def test_malformed_session_summary_is_discarded(self):
        c = playing()
        c.ns.db.guideSessions[c.ns.self].current.seconds = -99
        n = fresh(c)
        self.assertEqual(session(n).seconds, 0)
        self.assertEqual(session(n).xp, 0)

    def test_malformed_guide_key_does_not_break_session_initialization(self):
        for bad_entry in (False, True):
            with self.subTest(bad_entry=bad_entry):
                c = playing()
                if bad_entry: c.ns.db.guideState[c.ns.self] = True
                else: c.ns.db.guideState[c.ns.self].guide.key = None
                n = fresh(c)
                self.assertIsNone(n.ns.routeSelection)
                self.assertIsNone(n.ns.PausedSessionCheckpoint())
                self.assertIsNone(n.ns.db.guideSessions[n.ns.self].current)


class SessionUITests(unittest.TestCase):
    def test_resume_bar_continue_is_read_only_and_session_panel_close_keeps_guide(self):
        c = playing(); before = order(c.ns.routeSelection)
        c.ns.SetFilter('recommended')
        self.assertEqual(c.ns.ui.home.resume.button.caption.text, 'Continue')
        c.ns.ui.home.resume.button.OnClick()
        c.ns.ui.home.resume.session.OnClick()
        self.assertTrue(c.ns.sessionWindow.IsShown(c.ns.sessionWindow))
        c.ns.sessionWindow.close.OnClick()
        self.assertEqual(order(c.ns.routeSelection), before)

    def test_panel_resize_and_live_totals_are_compact(self):
        c = playing(); c.ns.ShowSessionCheckpoint(); f = c.ns.sessionWindow
        f.SetSize(f, 100, 100); f.OnSizeChanged()
        self.assertEqual((f.width, f.height), (400, 226))
        self.assertGreater(f.next.height, 20)
        c.lua.execute('sessionXP=400; sessionClock=220')
        f.OnUpdate(f, 1)
        self.assertIn('300 XP', f.stats.text)
        self.assertIn('2m played', f.stats.text)
        self.assertNotIn('API', f.stats.text)

    def test_pause_button_and_summary_action_resume_without_replanning_order(self):
        c = playing(); before = order(c.ns.routeSelection)
        c.ns.navigation.pause.OnClick()
        self.assertEqual(c.ns.navigation.pause.caption.text, 'Resume')
        self.assertEqual(c.ns.sessionWindow.action.caption.text, 'Resume guide')
        c.ns.sessionWindow.action.OnClick(); run_plan(c)
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertFalse(c.ns.sessionWindow.IsShown(c.ns.sessionWindow))

    def test_last_summary_remains_accessible_after_stopping(self):
        c = playing(); c.lua.execute('sessionXP=200; sessionClock=140')
        c.ns.StopGuide(False); c.ns.SetFilter('recommended')
        home = c.ns.ui.home
        self.assertTrue(home.resume.IsShown(home.resume))
        self.assertEqual(home.resume.category.text, 'LAST SESSION')
        self.assertEqual(home.resume.button.caption.text, 'Browse guides')
        home.resume.session.OnClick()
        self.assertIn('100 XP', c.ns.sessionWindow.stats.text)
        self.assertFalse(c.ns.sessionWindow.action.IsEnabled(c.ns.sessionWindow.action))
        self.assertIsNone(c.ns.routeSelection)


if __name__ == '__main__':
    unittest.main()
