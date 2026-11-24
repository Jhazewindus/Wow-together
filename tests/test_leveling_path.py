"""The leveling path: zone-to-zone plan, kill-XP share, pace, and its cost."""
import unittest

from test_addon import Client

SCENE = '''
local ns, level, fraction, faction, mapID, zone = ...
function UnitClass() return "Mage", "MAGE", 8 end
function UnitRace() return "Troll", "Troll", 8 end
function UnitFactionGroup() return faction end
playerLevel, playerFraction = level, fraction
function UnitLevel() return playerLevel end
C_Map = C_Map or {}
C_Map.GetBestMapForUnit = function() return mapID end
C_Map.GetPlayerMapPosition = function() return {GetXY = function() return 0.62, 0.20 end} end
C_Map.GetMapInfo = function(id) return {name = zone, mapType = 3, parentMapID = 1415} end
C_Map.GetMapWorldSize = function() return 3200, 2133 end
local function curve(l) return ns.xpCurve and ns.xpCurve[l] or ns.xpBaseline and ns.xpBaseline[l] or 20000 end
function UnitXPMax() return curve(playerLevel) end
function UnitXP() return math.floor(curve(playerLevel) * playerFraction) end
function GetXPExhaustion() return 0 end
printed = {}
ns.Print = function(text) printed[#printed + 1] = text end
'''


def scene(level=30, fraction=0.2, xp_model=False, faction='Horde', map_id=1424, zone='Hillsbrad Foothills', ui_next=False,
          path=True, quests=(), completed=()):
    c = Client(quests=quests, completed=completed, use_catalogue=True, party_mode='never',
               saved_variables={'config': {'xpModel': xp_model, 'levelingPath': path, 'uiNext': ui_next}})
    c.guide_environment(level=level)
    c.lua.execute(SCENE, c.ns, level, fraction, faction, map_id, zone)
    c.ns.ReadProfile()
    return c


def drain(c):
    for _ in range(20000):
        if not len(c.lua.globals().timers):
            break
        c.lua.eval('function() local callback = table.remove(timers, 1); callback() end')()


def steps(path):
    return [dict(zone=step.zone, start=step['from'], to=step.to, quests=step.quests, map=step.mapID, following=step.following)
            for step in path.steps.values()]


class PathShapeTests(unittest.TestCase):
    def test_path_from_level_one_is_one_unbroken_climb_through_real_zones(self):
        c = scene(1, 0.0, map_id=1411, zone='Durotar'); ns = c.ns
        path = ns.LevelingPathFrom(1, 0)
        plan = steps(path)
        self.assertGreater(len(plan), 10)
        self.assertEqual(plan[0]['start'], 1.0)
        for before, after in zip(plan, plan[1:]):
            self.assertAlmostEqual(before['to'], after['start'], places=6)   # Each zone starts where the last one ends.
            self.assertGreater(after['to'], after['start'])
            self.assertNotEqual(before['map'], after['map'])                 # A repeat visit is merged into one.
        self.assertTrue(all(step['quests'] >= 1 for step in plan))
        self.assertGreaterEqual(path.reached, 40)                            # The catalogue carries a quester that far.
        self.assertGreaterEqual(plan[0]['quests'], 8)                        # Zones are chosen for a real batch of quests.
        early = [step['zone'] for step in plan[:3]]
        self.assertTrue(set(early) & {'Durotar', 'Mulgore', 'Tirisfal Glades', 'Deathknell', 'Zephras Isle', 'The Barrens'}, early)

    def test_the_first_big_zones_are_not_reached_by_hopping_for_scraps(self):
        ns = scene(1, 0.0, map_id=1411, zone='Durotar').ns
        plan = steps(ns.LevelingPathFrom(1, 0))
        while plan and plan[-1]['quests'] < 8:
            plan.pop()                                                        # Scraps are only taken once nothing bigger is left.
        small = [step for step in plan[:8] if step['quests'] < 8]
        self.assertEqual(small, [])

    def test_the_zone_being_followed_comes_first(self):
        c = scene(30, 0.2); ns = c.ns
        free = steps(ns.LevelingPathFrom())
        target = next(step for step in free if step['map'] != free[0]['map'])
        c.lua.execute('local ns, mapID = ...; ns.routeSelection = {key = "x", mode = "zone", mapID = mapID}', ns, target['map'])
        followed = steps(ns.LevelingPathFrom())
        self.assertEqual(followed[0]['map'], target['map'])
        self.assertTrue(followed[0]['following'])
        self.assertIsNone(followed[1]['following'])

    def test_finished_quests_are_not_counted_again(self):
        c = scene(30, 0.2); ns = c.ns
        before = steps(ns.LevelingPathFrom())
        first = before[0]
        c.lua.execute('''
            local ns, mapID = ...
            local completion = ns.CatalogueCompletion
            local done = {}
            for _, zone in ipairs(ns.LevelingZoneInventory()) do
                if zone.mapID == mapID then for _, quest in ipairs(zone.quests) do done[quest.id] = true end end
            end
            ns.CatalogueCompletion = function(key, id, ...) if done[id] then return true end return completion(key, id, ...) end
        ''', ns, first['map'])
        after = steps(ns.LevelingPathFrom())
        self.assertNotIn(first['map'], [step['map'] for step in after])
        self.assertLess(sum(step['quests'] for step in after), sum(step['quests'] for step in before))


class KillShareTests(unittest.TestCase):
    def test_the_assumed_share_fades_into_the_measured_one_over_thirty_quests(self):
        ns = scene().ns
        self.assertEqual(tuple(ns.LevelingXPMultiplier()), (1.8, False))
        ns.char.xpPace = None
        for _ in range(15):
            ns.RecordQuestRewardXP(1000)
        ns.char.xpPace.total = 15 * 1000 * 1.2          # Measured so far: kills add 20%.
        factor, learned = ns.LevelingXPMultiplier()
        self.assertAlmostEqual(factor, 1.5)              # Half assumption (1.8), half evidence (1.2).
        self.assertFalse(learned)
        for _ in range(15):
            ns.RecordQuestRewardXP(1000)
        ns.char.xpPace.total = 30 * 1000 * 1.2
        self.assertEqual(tuple(ns.LevelingXPMultiplier()), (1.2, True))
        ns.char.xpPace.total = 30 * 1000 * 9
        self.assertEqual(ns.LevelingXPMultiplier()[0], 2.5)  # Rested streaks and group kills cannot run away with it.
        ns.char.xpPace.total = 1
        self.assertEqual(ns.LevelingXPMultiplier()[0], 1)    # Never below quest rewards alone.

    def test_a_larger_share_means_fewer_zones_to_the_same_level(self):
        c = scene(30, 0.0); ns = c.ns
        set_share = c.lua.eval('function(ns, total) ns.char.xpPace = {total = total, quest = 30000, quests = 30} end')
        set_share(ns, 30000)
        slow = ns.LevelingPathFrom(30, 0)
        set_share(ns, 60000)
        fast = ns.LevelingPathFrom(30, 0)
        level_after_three = lambda path: steps(path)[2]['to']
        self.assertGreater(level_after_three(fast), level_after_three(slow))
        self.assertGreaterEqual(fast.reached, slow.reached)

    def test_experience_gains_are_counted_across_a_level_up_and_give_a_pace(self):
        c = scene(30, 0.90); ns = c.ns; g = c.lua.globals()
        c.lua.execute('clock = 5000; function GetTime() return clock end')
        ns.char.xpPace = None
        ns.RecordExperienceGain()                         # Baseline.
        maximum = ns.XPState().xpMax
        g.playerFraction = 0.95
        c.lua.execute('clock = clock + 600')
        ns.RecordExperienceGain()
        gained_first = ns.char.xpPace.total
        self.assertAlmostEqual(gained_first, maximum * 0.05, delta=2)
        g.playerLevel, g.playerFraction = 31, 0.10        # Dinged.
        c.lua.execute('clock = clock + 600')
        ns.RecordExperienceGain()
        next_maximum = ns.XPState().xpMax
        self.assertAlmostEqual(ns.char.xpPace.total - gained_first, maximum * 0.05 + next_maximum * 0.10, delta=3)
        per_hour, to_level = ns.LevelingPace()
        self.assertAlmostEqual(per_hour, (maximum * 0.05 + next_maximum * 0.10) / 600 * 3600, delta=per_hour * 0.02)
        self.assertGreater(to_level, 0)
        self.assertIn('XP an hour', ns.LevelingPaceText())
        self.assertIn('level 32 in about', ns.LevelingPaceText())


class PathUseTests(unittest.TestCase):
    def test_background_calculation_reports_through_the_callback_and_is_cached(self):
        c = scene(30, 0.2); ns = c.ns
        c.lua.execute('local ns = ...; got = 0; inventories = 0; local f = ns.LevelingZoneInventory; '
                      'ns.LevelingZoneInventory = function(...) inventories = inventories + 1; return f(...) end', ns)
        callback = c.lua.eval('function(result) got = got + 1; lastPath = result end')
        drain(c)                                           # Let anything started while logging in finish first.
        ns.InvalidateLevelingPath()
        ns.LevelingPath(callback)
        ns.LevelingPath(callback)                          # A second asker while it is being worked out.
        self.assertEqual(c.lua.globals().got, 0)           # Not yet: it takes several frames.
        drain(c)
        self.assertEqual(c.lua.globals().got, 2)           # Both are told, once each.
        path = ns.LevelingPath()
        self.assertIsNotNone(path)
        self.assertIsNone(path.stale)
        self.assertGreater(len(steps(path)), 5)
        before = c.lua.globals().inventories
        for _ in range(5):                                 # Asking again costs nothing.
            ns.LevelingPath(); ns.Refresh(True); drain(c)
        self.assertEqual(c.lua.globals().inventories, before)
        ns.LevelingPath(callback)
        self.assertEqual(c.lua.globals().got, 3)           # Already known: answered at once.

    def test_the_zone_after_the_current_one_feeds_the_zone_exit_and_the_hub_card(self):
        c = scene(30, 0.2); ns = c.ns
        ns.LevelingPath(); drain(c)
        plan = steps(ns.LevelingPath())
        current = c.lua.table_from({'key': 'whatever', 'mapID': plan[0]['map'], 'mode': 'zone'})
        following = ns.LevelingPathNextGuide(current)
        self.assertEqual(following.mapID, plan[1]['map'])
        self.assertEqual(following.rangeLow, int(plan[1]['start']))
        self.assertTrue(len(list(following.records.values())) > 0)
        self.assertTrue(c.lua.eval('function(ns, guide, first) return ns.LevelingPathNextGuide(guide) == first end')(ns, current, following))
        items, state = ns.LevelingPathRecommendation()
        card = items[1]
        self.assertEqual(card.category, 'YOUR PATH: NEXT ZONE')
        self.assertEqual(card.title, plan[1]['zone'])
        self.assertIn('After ' + plan[0]['zone'], card.detail)

    def test_text_names_levels_quests_and_the_assumption_it_rests_on(self):
        c = scene(30, 0.2); ns = c.ns
        lines = list(ns.LevelingPathLines(ns.LevelingPathFrom(), 6).values())
        self.assertTrue(lines[0].startswith('Level 30 (20%)'))
        self.assertIn('Assuming kills add about 80% to quest rewards', lines[1])
        self.assertRegex(lines[2], r'^1\. .+  30\.2 to 3\d\.\d  • \d+ quests')
        self.assertIn('more, to level', lines[8])
        text = ' '.join(lines)
        self.assertTrue(all(ord(char) < 256 or char in '–•…' for char in text))

    def test_the_path_has_its_own_setting_and_stays_silent_when_that_is_off(self):
        c = scene(30, 0.2, path=False); ns = c.ns
        self.assertIsNone(ns.LevelingPath())
        drain(c)
        self.assertIsNone(ns.LevelingPath())
        ns.LevelingPathCommand()
        self.assertIn('switched off in settings', list(c.lua.globals().printed.values())[0])
        items, _ = ns.LevelingPathRecommendation()
        self.assertEqual(len(list(items.values())), 0)


class CostAndDefaultTests(unittest.TestCase):
    def test_next_zone_lookup_is_worked_out_once_not_on_every_refresh(self):
        c = scene(30, 0.2); ns = c.ns
        guide = next(g for g in ns.LevelingGuideChoices().values() if g.mode == 'zone')
        first = ns.NextZoneBaselineGuide(guide, True)
        same = c.lua.eval('function(ns, guide, first) for i = 1, 20 do if ns.NextZoneBaselineGuide(guide, true) ~= first then return false end end return true end')
        self.assertTrue(same(ns, guide, first))            # The same answer object: nothing was recomputed.
        timing = c.lua.eval('function(ns, guide) local t = os.clock(); for i = 1, 200 do ns.NextZoneBaselineGuide(guide, true) end return (os.clock() - t) * 1000 / 200 end')
        self.assertLess(timing(ns, guide), 1.0)            # Was about 25 ms a call.

    def test_the_xp_model_is_off_by_default_and_installs_switched_on_are_moved_back_once(self):
        fresh = Client(quests=(), default_guide=True, fresh_install=True)
        self.assertFalse(fresh.ns.Option('xpModel'))
        self.assertTrue(fresh.ns.Option('levelingPath') is not False)       # The path does not need the model.
        moved = Client(quests=(), default_guide=True, fresh_install=True,
                       saved_variables={'config': {'xpModel': True, 'xpModelDefault': True}})
        self.assertFalse(moved.ns.Option('xpModel'))                        # Switched on by an earlier build: back off.
        chosen = Client(quests=(), default_guide=True, saved_variables={'config': {'xpModel': True, 'xpModelOffAgain': True}})
        self.assertTrue(chosen.ns.Option('xpModel'))                        # Switched on by the player afterwards: kept.

    def test_with_default_settings_a_quest_in_the_log_is_guided_even_when_its_objective_is_in_another_zone(self):
        # Infiltration (533) starts and ends in Hillsbrad with its objective in
        # Alterac. With the XP model on, the guide filed it as low value and
        # showed "paused ... Later" with no steps.
        def stops(model):
            c = scene(33, 0.3, xp_model=model, quests=(533,), completed=(498, 552, 553)); ns = c.ns
            drain(c)
            guide = next(g for g in ns.LevelingGuideChoices().values() if g.mode == 'zone' and 'Hillsbrad' in (g.zone or ''))
            ns.ShowGuideOnMap(guide); drain(c)
            for _ in range(6):
                route = ns.selectedRoute
                if route and route.stops and len(list(route.stops.values())):
                    break
                ns.Refresh(True); drain(c)
            route = ns.selectedRoute
            return [(stop.kind, stop.id) for stop in route.stops.values()] if route and route.stops else []
        guided = stops(False)
        self.assertIn(('q', 533), guided)                                   # Its objective is a step...
        self.assertIn(('t', 533), guided)                                   # ...and so is handing it in.
        self.assertEqual(stops(True), [])                                   # The experimental model still drops it: why it is off.


if __name__ == '__main__':
    unittest.main()


class PathOnScreenTests(unittest.TestCase):
    """The path where the player looks: under the guide window and on the main page."""

    def ready(self, following=None):
        c = scene(30, 0.2); ns = c.ns
        if following:
            c.lua.execute('local ns, zone = ...; ns.routeSelection = {key = "guide", mode = "zone", zone = zone}', ns, following)
        drain(c); ns.InvalidateLevelingPath(); ns.LevelingPath(); drain(c)
        return c

    def test_a_followed_guide_is_recognised_by_its_zone_name_alone(self):
        c = scene(30, 0.2); ns = c.ns
        free = steps(ns.LevelingPathFrom())
        target = next(step for step in free if step['zone'] != free[0]['zone'])
        c.lua.execute('local ns, zone = ...; ns.routeSelection = {key = "guide", mode = "zone", zone = zone}', ns, target['zone'])
        followed = steps(ns.LevelingPathFrom())
        self.assertEqual(followed[0]['zone'], target['zone'])   # No map ID on the guide: the name is enough.
        self.assertTrue(followed[0]['following'])

    def test_strip_under_the_guide_window_says_where_this_zone_leads(self):
        plan = steps(scene(30, 0.2).ns.LevelingPathFrom())
        c = self.ready(following=plan[0]['zone']); ns = c.ns
        strip = ns.navigation.pathStrip
        state = c.lua.table_from({'visible': True})
        self.assertTrue(ns.UpdateLevelingPathStrip(state))
        self.assertTrue(strip.IsShown(strip))
        self.assertRegex(strip.text.text, r'^This zone to level 3\d\.\d, then .+')
        self.assertLessEqual(len(strip.text.text), 70)           # One line under a 360-wide window.
        ns.SetOption('guideGlance', True)
        self.assertTrue(ns.UpdateLevelingPathStrip(state))       # It stays in Glance.
        ns.SetOption('levelingPathStrip', False)
        self.assertFalse(ns.UpdateLevelingPathStrip(state))
        self.assertFalse(strip.IsShown(strip))
        ns.SetOption('levelingPathStrip', True)
        c.lua.execute('local ns = ...; ns.routeSelection.mode = "profession"', ns)
        self.assertFalse(ns.UpdateLevelingPathStrip(state))      # Only while a zone guide is being followed.

    def test_strip_names_the_zone_when_the_path_starts_elsewhere(self):
        c = self.ready(); ns = c.ns
        summary = ns.LevelingPathSummary(ns.LevelingPath())
        first = steps(ns.LevelingPath())[0]
        self.assertTrue(summary.startswith(first['zone'] + ' to level '))

    def test_main_page_lists_the_next_zones_above_the_recommended_one(self):
        plan = steps(scene(30, 0.2).ns.LevelingPathFrom())
        c = self.ready(following=plan[0]['zone']); ns = c.ns
        c.lua.execute('local ns = ...; started = nil; ns.RequestStartRoute = function(guide) started = guide end; '
                      'opened = 0; ns.OpenGuideWindow = function() opened = opened + 1 end', ns)
        if not ns.window.IsShown(ns.window):
            ns.ToggleWindow()
        ns.SetFilter('recommended'); drain(c)
        home = ns.ui.home
        panel = home.path
        self.assertTrue(panel.IsShown(panel))
        self.assertEqual(panel.count, 4)
        rows = [panel.rows[index] for index in range(1, 5)]
        current = steps(ns.LevelingPath())
        self.assertEqual(rows[0].zone.text, '1.  ' + current[0]['zone'])
        self.assertRegex(rows[0].levels.text, r'^level 30\.2 to 3\d\.\d$')
        self.assertIn('following', rows[0].quests.text)
        self.assertNotIn('following', rows[1].quests.text)
        self.assertIn('Assumes kills add about 80%', panel.note.text)
        self.assertGreater(-home.leveling.point[3], -panel.point[3])         # Above the recommended-zone card.
        extra = [home.extraCards[index].data.key for index in range(1, home.extraCount + 1)]
        self.assertFalse([key for key in extra if str(key).startswith('path:')])  # Not repeated further down.
        rows[0].OnClick(rows[0])
        self.assertEqual(c.lua.globals().opened, 1)                          # The zone being followed opens its guide.
        rows[1].OnClick(rows[1])
        self.assertIsNotNone(c.lua.globals().started)                        # Another zone starts that zone's guide.
        self.assertEqual(c.lua.globals().started.mapID, current[1]['map'])
        panel.all.OnClick()
        self.assertTrue(ns.levelingPathViewer.IsShown(ns.levelingPathViewer))


class PathFollowingTests(unittest.TestCase):
    """Following the path: zone guides chained, each handing over to the next."""

    STUBS = '''
        local ns = ...
        asked, started = {}, {}
        ns.RequestStartRoute = function(guide) asked[#asked + 1] = guide end
        ns.StartPartyRoute = function(guide) started[#started + 1] = guide end
        combat = false
        function InCombatLockdown() return combat end
        -- The guide window's state, as the hand-over reads it again a few seconds later.
        currentState = nil
        local realState = ns.NavigationState
        ns.NavigationState = function(...) if currentState then return currentState end return realState(...) end
        ns.UpdateNavigation = function() end      -- The window itself is not under test here.
        function exitState(withNext)
            currentState = {visible = true, stop = {id = 0, kind = "notice", reasonCode = "zone-exit",
                nextGuide = withNext and {zone = "somewhere"} or nil, label = "finished"}}
            return currentState
        end
        function noStepsState(reason)
            ns.routeSelection.pendingReason = reason
            currentState = {visible = true, stop = {id = 0, kind = "notice", label = reason}}
            return currentState
        end
    '''

    def following(self, running=True):
        plan = steps(scene(30, 0.2).ns.LevelingPathFrom())
        c = scene(30, 0.2); ns = c.ns
        drain(c)
        # A stand-in for a running zone guide: the real route builder would
        # discard a guide that is not in the catalogue, so it is switched off.
        c.lua.execute('local ns = ...; ns.UpdateSelectedRoute = function() end', ns)
        if running:
            c.lua.execute('local ns, zone = ...; ns.routeSelection = {key = "guide", mode = "zone", zone = zone}; '
                          'ns.selectedRoute = {stops = {}, complete = false}', ns, plan[0]['zone'])
        ns.InvalidateLevelingPath(); ns.LevelingPath(); drain(c)
        c.lua.execute(self.STUBS, ns)
        return c, steps(ns.LevelingPath())

    def count(self, c, name):
        return len(list(c.lua.globals()[name].values()))

    def test_following_keeps_the_running_zone_and_is_remembered_for_the_character(self):
        c, plan = self.following(); ns = c.ns
        self.assertFalse(ns.LevelingPathFollowing())
        ns.FollowLevelingPath(); drain(c)
        self.assertTrue(ns.LevelingPathFollowing())
        self.assertTrue(ns.char.levelingPathMode)                    # Saved with the character.
        self.assertEqual(self.count(c, 'asked'), 0)                  # Already on the path's first zone: nothing restarts.
        self.assertIn('Following your leveling path', list(c.lua.globals().printed.values())[0])
        self.assertTrue(ns.LevelingPathSummary(ns.LevelingPath()).startswith('Path: this zone to level'))

    def test_following_with_no_guide_running_starts_the_first_zone(self):
        c, plan = self.following(running=False); ns = c.ns
        ns.FollowLevelingPath(); drain(c)
        self.assertEqual(self.count(c, 'asked'), 1)                  # Started by hand, so it may ask about current quests.
        self.assertEqual(c.lua.globals().asked[1].mapID, plan[0]['map'])

    def test_a_finished_zone_hands_over_to_the_next_zone_on_the_path(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        g.printed = c.lua.table()
        self.assertTrue(ns.LevelingPathChain(g.exitState(True)))
        self.assertEqual(self.count(c, 'started'), 0)                # Not instantly: a few seconds after the step appears.
        drain(c)
        self.assertEqual(self.count(c, 'started'), 1)
        self.assertEqual(g.started[1].mapID, plan[1]['map'])         # The path's next zone, not just any zone.
        self.assertEqual(self.count(c, 'asked'), 0)                  # A hand-over never opens a prompt.
        line = list(g.printed.values())[0]
        self.assertIn(plan[0]['zone'] + ' is done for your level. Now following ' + plan[1]['zone'], line)
        ns.LevelingPathChain(g.exitState(True)); drain(c)
        self.assertEqual(self.count(c, 'started'), 1)                # The same hand-over is not repeated.

    def test_a_completed_route_also_hands_over(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        ns.selectedRoute.complete = True
        self.assertTrue(ns.LevelingPathChain(c.lua.table_from({'visible': True})))
        drain(c)
        self.assertEqual(g.started[1].mapID, plan[1]['map'])

    def test_a_zone_with_nothing_left_worth_the_level_hands_over_without_the_xp_model(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        working = c.lua.table_from({'visible': True, 'stop': c.lua.table_from({'kind': 'q', 'id': 1})})
        self.assertFalse(ns.LevelingPathChain(working))                      # Still the path's first zone: stay.
        c.lua.execute('''
            local ns, name = ...
            local completion, done = ns.CatalogueCompletion, {}
            for _, zone in ipairs(ns.LevelingZoneInventory()) do
                if zone.zone == name then for _, quest in ipairs(zone.quests) do done[quest.id] = true end end
            end
            ns.CatalogueCompletion = function(key, id, ...) if done[id] then return true end return completion(key, id, ...) end
            ns.questHistoryCount = (ns.questHistoryCount or 0) + 20
        ''', ns, plan[0]['zone'])
        ns.LevelingPath(c.lua.eval('function() end')); drain(c)              # The path is worked out again.
        self.assertNotEqual(steps(ns.LevelingPath())[0]['zone'], plan[0]['zone'])
        self.assertTrue(ns.LevelingPathChain(working))                       # Nothing left here: hand over, mid-list.
        drain(c)
        self.assertEqual(self.count(c, 'started'), 1)

    def test_a_zone_the_player_chose_against_the_path_is_not_left_on_the_paths_say_so(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        c.lua.execute('local ns = ...; ns.routeSelection = {key = "own choice", mode = "zone", zone = "Nowhere In Particular"}; '
                      'ns.selectedRoute = {stops = {}, complete = false}', ns)
        ns.LevelingPath(c.lua.eval('function() end')); drain(c)
        working = c.lua.table_from({'visible': True, 'stop': c.lua.table_from({'kind': 'q', 'id': 1})})
        self.assertFalse(ns.LevelingPathChain(working))
        drain(c)
        self.assertEqual(self.count(c, 'started'), 0)

    def test_a_guide_left_with_no_steps_hands_over_and_the_path_does_not_send_the_player_straight_back(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        g.printed = c.lua.table()
        # What the player saw: everything left in the guide skipped, and the path still naming this zone first.
        self.assertEqual(steps(ns.LevelingPath())[0]['zone'], plan[0]['zone'])
        self.assertTrue(ns.LevelingPathChain(g.noStepsState('Remaining guide steps are skipped.')))
        drain(c)
        self.assertEqual(self.count(c, 'started'), 1)
        self.assertNotEqual(g.started[1].mapID, plan[0]['map'])
        self.assertIn(plan[0]['zone'] + ' has no steps left that you can take. Now following ', list(g.printed.values())[0])
        self.assertEqual(ns.char.levelingPathSetAside[plan[0]['zone']], 30)
        fresh = steps(ns.LevelingPathFrom())
        self.assertNotEqual(fresh[0]['zone'], plan[0]['zone'])               # Not offered again at this level...
        later = [step['zone'] for step in steps(ns.LevelingPathFrom()) if step['start'] >= 31]
        self.assertIn(plan[0]['zone'], [step['zone'] for step in steps(ns.LevelingPathFrom())] + later)   # ...only once outgrown.

    def test_a_passing_notice_is_not_a_hand_over(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        self.assertTrue(ns.LevelingPathChain(g.noStepsState('Waiting for quest data.')))
        c.lua.execute('currentState = {visible = true, stop = {id = 12, kind = "q"}}')   # A real step again within seconds.
        drain(c)
        self.assertEqual(self.count(c, 'started'), 0)
        self.assertIsNone(ns.char.levelingPathSetAside)

    def test_a_quest_with_a_skipped_step_no_longer_counts_for_its_zone(self):
        c, plan = self.following(); ns = c.ns
        before = steps(ns.LevelingPathFrom())[0]['quests']
        c.lua.execute('''
            local ns, name = ...
            for _, zone in ipairs(ns.LevelingZoneInventory()) do
                if zone.zone == name then
                    local count = 0
                    for _, quest in ipairs(zone.quests) do
                        if quest.level <= 32 and count < 3 then
                            ns.char.guideSkips.steps[quest.id] = {["q:1:x"] = true}      -- "Skip step", not "Skip quest"
                            count = count + 1
                        end
                    end
                end
            end
        ''', ns, plan[0]['zone'])
        after = [step for step in steps(ns.LevelingPathFrom()) if step['zone'] == plan[0]['zone']]
        self.assertTrue(not after or after[0]['quests'] < before)

    def test_nothing_is_chained_unless_the_path_is_followed_and_the_zone_is_really_done(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        self.assertFalse(ns.LevelingPathChain(g.exitState(True)))     # Path not followed.
        ns.FollowLevelingPath(); drain(c)
        self.assertFalse(ns.LevelingPathChain(g.exitState(False)))    # "Gain more XP here first" is not a hand-over.
        self.assertFalse(ns.LevelingPathChain(c.lua.table_from({'visible': True, 'stop': c.lua.table_from({'kind': 'q'})})))
        c.lua.execute('local ns = ...; ns.routeSelection.mode = "profession"', ns)
        self.assertFalse(ns.LevelingPathChain(g.exitState(True)))     # A profession guide is left alone.
        drain(c)
        self.assertEqual(self.count(c, 'started'), 0)

    def test_combat_and_a_change_of_guide_cancel_the_hand_over(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        g.combat = True
        ns.LevelingPathChain(g.exitState(True)); drain(c)
        self.assertEqual(self.count(c, 'started'), 0)                # Not in a fight.
        g.combat = False
        ns.LevelingPathChain(g.exitState(True))
        c.lua.execute('local ns = ...; ns.routeSelection = {key = "other", mode = "zone", zone = "Elsewhere"}', ns)
        drain(c)
        self.assertEqual(self.count(c, 'started'), 0)                # The player picked something else meanwhile.

    def test_stopping_ends_the_chain_and_the_command_and_button_switch_it(self):
        c, plan = self.following(); ns = c.ns; g = c.lua.globals()
        ns.LevelingPathCommand('follow'); drain(c)
        self.assertTrue(ns.LevelingPathFollowing())
        ns.LevelingPathCommand('stop')
        self.assertFalse(ns.LevelingPathFollowing())
        self.assertIsNone(ns.char.levelingPathMode)
        self.assertFalse(ns.LevelingPathChain(g.exitState(True)))
        if not ns.window.IsShown(ns.window):
            ns.ToggleWindow()
        ns.SetFilter('recommended'); drain(c)
        panel = ns.ui.home.path
        self.assertEqual(panel.follow.caption.text, 'Follow path')
        self.assertEqual(panel.heading.text, 'YOUR LEVELING PATH')
        panel.follow.OnClick(); drain(c); ns.Refresh(); drain(c)
        self.assertTrue(ns.LevelingPathFollowing())
        self.assertEqual(panel.follow.caption.text, 'Stop path')
        self.assertIn('FOLLOWING', panel.heading.text)
        self.assertIn('chained', panel.note.text)

    def test_every_next_zone_answer_comes_from_the_path(self):
        c, plan = self.following(); ns = c.ns
        current = c.lua.table_from({'key': 'guide', 'mode': 'zone', 'zone': plan[0]['zone']})
        self.assertEqual(ns.NextLevelingGuide(current).mapID, plan[1]['map'])
        ns.InvalidateLevelingPath()
        unknown = c.lua.table_from({'key': 'x', 'mode': 'zone', 'zone': 'Nowhere', 'rangeLow': 20, 'rangeHigh': 29})
        fallback = ns.NextLevelingGuide(unknown)                      # Off the path: the lowest zone above its band.
        self.assertTrue(fallback is None or fallback.rangeLow > 29)


class FinishFirstTests(unittest.TestCase):
    """A zone is not left while it holds finished or nearly finished quests."""

    PICK = '''
        local ns, mapID = ...
        -- A quest that is turned in on this map, and a low-level one from elsewhere.
        local here, low, far
        local ids = {}
        for id in pairs(ns.catalogue.quests) do ids[#ids + 1] = id end
        table.sort(ids)
        for _, id in ipairs(ids) do
            local quest = ns.catalogue.quests[id]
            local onMap, offMap = false, true
            for _, list in ipairs({quest.ends, quest.objectives, quest.starts}) do
                for _, point in ipairs(type(list) == "table" and list or {}) do
                    if point.mapID == mapID then offMap = false end
                end
            end
            for _, point in ipairs(quest.ends or {}) do if point.mapID == mapID then onMap = true end end
            if onMap and not here and (quest.level or 0) >= 25 then here = id end
            if onMap and here and id ~= here and not low and (quest.level or 0) > 0 and (quest.level or 0) <= 22 then low = id end
            if offMap and not far and (quest.level or 0) >= 25 and quest.ends and #quest.ends > 0 then far = id end
        end
        return here, low, far
    '''

    def setting(self):
        plan = steps(scene(30, 0.2).ns.LevelingPathFrom())
        c = scene(30, 0.2); ns = c.ns
        drain(c)
        c.lua.execute('local ns = ...; ns.UpdateSelectedRoute = function() end', ns)
        c.lua.execute('local ns = ...; ns.routeSelection = {key = "guide", mode = "zone", zone = "Hillsbrad Foothills", mapID = 1424, records = {}}; '
                      'ns.selectedRoute = {stops = {}, complete = false}', ns)
        ns.InvalidateLevelingPath(); ns.LevelingPath(); drain(c)
        c.lua.execute(PathFollowingTests.STUBS, ns)
        here, low, far = c.lua.eval('function(ns, mapID) ' + self.PICK.replace('local ns, mapID = ...', '') + ' end')(ns, 1424)
        self.assertTrue(here and far)
        c.lua.execute('''
            local ns = ...
            function inLog(id, have, need)
                ns.active[id] = ns.active[id] or {id = id}
                ns.localProgress[id] = {objectives = {{have = have, need = need}}}
            end
            function outOfLog(id) ns.active[id] = nil; ns.localProgress[id] = nil; ns.readyToTurnIn[id] = nil end
        ''', ns)
        return c, here, low, far

    def test_progress_is_the_average_of_the_objectives_and_the_threshold_is_a_setting(self):
        c, here, low, far = self.setting(); ns = c.ns; g = c.lua.globals()

        def nearly():
            result = ns.QuestNearlyDone(here)
            return result[0] if isinstance(result, tuple) else result

        self.assertIsNone(ns.QuestProgressFraction(here))            # Not in the log.
        g.inLog(here, 9, 10)
        self.assertAlmostEqual(ns.QuestProgressFraction(here), 0.9)
        self.assertTrue(nearly())
        c.lua.execute('local ns, id = ...; ns.localProgress[id] = {objectives = {{have = 3, need = 10}, {finished = true}}}', ns, here)
        self.assertAlmostEqual(ns.QuestProgressFraction(here), 0.65)  # One of two done, the other 3 of 10.
        self.assertFalse(nearly())
        g.inLog(here, 8, 10)
        self.assertFalse(nearly())                                    # 80% is short of the default 85%.
        ns.SetOption('finishNearlyDone', '70')
        self.assertTrue(nearly())
        ns.SetOption('finishNearlyDone', 'off')
        self.assertFalse(nearly())
        ns.SetOption('finishNearlyDone', '85')
        g.inLog(here, 10, 10)
        self.assertFalse(nearly())                                    # Finished is not "nearly": it is a turn-in.

    def test_a_nearly_finished_quest_stays_worth_doing_however_little_it_pays(self):
        c, here, low, far = self.setting(); ns = c.ns; g = c.lua.globals()
        if not low:
            self.skipTest('no low-level quest on this map in the catalogue')
        g.inLog(low, 2, 10)
        before = ns.LevelingValue(low)
        g.inLog(low, 9, 10)
        value, reason = ns.LevelingValue(low)
        self.assertTrue(value)
        self.assertIn('90% through this one: finish it before leaving the zone', reason)
        ns.SetOption('finishNearlyDone', 'off')
        self.assertEqual(ns.LevelingValue(low)[0] if isinstance(ns.LevelingValue(low), tuple) else ns.LevelingValue(low),
                         before[0] if isinstance(before, tuple) else before)   # Off: judged as before.

    def test_hand_over_waits_for_finished_quests_to_be_turned_in(self):
        c, here, low, far = self.setting(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        g.printed = c.lua.table()
        g.inLog(here, 10, 10)
        self.assertFalse(ns.LevelingPathChain(g.exitState(True)))     # Held: something to turn in here.
        drain(c)
        self.assertEqual(len(list(g.started.values())), 0)
        lines = list(g.printed.values())
        self.assertEqual(len(lines), 1)
        self.assertIn('before leaving Hillsbrad Foothills, turn in ' + ns.QuestTitle(here), lines[0])
        ns.LevelingPathChain(g.exitState(True)); drain(c)
        self.assertEqual(len(list(g.printed.values())), 1)            # Said once, not on every update.
        g.outOfLog(here)                                              # Turned in.
        self.assertTrue(ns.LevelingPathChain(g.exitState(True)))
        drain(c)
        self.assertEqual(len(list(g.started.values())), 1)            # Now the next zone starts.

    def test_hand_over_waits_for_nearly_finished_quests_but_not_for_other_zones(self):
        c, here, low, far = self.setting(); ns = c.ns; g = c.lua.globals()
        ns.FollowLevelingPath(); drain(c)
        g.printed = c.lua.table()
        g.inLog(far, 10, 10)                                          # Finished, but it belongs to another zone.
        g.inLog(here, 5, 10)                                          # Half done: not worth staying for.
        ready, nearly = ns.ZoneUnfinishedBusiness(ns.routeSelection)
        self.assertEqual((len(list(ready.values())), len(list(nearly.values()))), (0, 0))
        g.inLog(here, 9, 10)
        self.assertFalse(ns.LevelingPathChain(g.exitState(True)))
        self.assertIn('finish ' + ns.QuestTitle(here) + ' (90%)', list(g.printed.values())[0])
        c.lua.execute('local ns, id = ...; ns.routeSelection.records = {{id = id}}', ns, far)
        ready, nearly = ns.ZoneUnfinishedBusiness(ns.routeSelection)
        self.assertEqual(list(ready.values()), [])                    # Handed in elsewhere: part of that trip, not a reason to stay.


class WhereThePathStartsTests(unittest.TestCase):
    """The path begins where the character is, not across the sea."""

    def test_it_opens_on_the_continent_the_character_stands_on(self):
        c = scene(32, 0.85, map_id=1417, zone='Arathi Highlands'); ns = c.ns
        path = ns.LevelingPath() or (drain(c), ns.LevelingPath())[1]
        drain(c); path = ns.LevelingPath()
        first = list(path.steps.values())[0]
        home = c.lua.eval('''function(ns) for _, zone in ipairs(ns.LevelingZoneInventory()) do
            if zone.mapID == 1417 then return string.match(zone.key or "", ":([%w%-]+)/") or string.match(zone.key or "", "^([%w%-]+)/") end end end''')(ns)
        self.assertIsNotNone(home)
        self.assertEqual(first.continent, home)

    def test_a_zone_whose_quests_are_already_in_the_log_comes_first_when_standing_in_it(self):
        c = scene(32, 0.85, map_id=1417, zone='Arathi Highlands'); ns = c.ns
        drain(c)
        held = c.lua.eval('''function(ns)
            for _, zone in ipairs(ns.LevelingZoneInventory()) do
                if zone.mapID == 1417 then
                    for _, quest in ipairs(zone.quests) do
                        if quest.level <= 34 and ns.QuestXP(quest.id, 32) and ns.CatalogueIdentityAllowed(quest.id, ns.profile) == true
                            and not ns.IsGroupQuest(quest.id) and not ns.IsDungeonQuest(quest.id) then
                            ns.active[quest.id] = {id = quest.id}
                            return quest.id
                        end
                    end
                end
            end
        end''')(ns)
        if not held:
            self.skipTest('no Arathi quest within two levels of 32 in the catalogue')
        ns.InvalidateLevelingPath(); ns.LevelingPath(); drain(c)
        first = list(ns.LevelingPath().steps.values())[0]
        self.assertEqual(first.mapID, 1417)                          # One quest in the log is enough to start here.


class NewHubTests(unittest.TestCase):
    """The path block on the new Hub's Play page."""

    def test_play_page_shows_the_path_block_above_next_for_you_and_no_duplicate_row(self):
        c = scene(32, 0.85, map_id=1417, zone='Arathi Highlands', ui_next=True); ns = c.ns
        drain(c); ns.InvalidateLevelingPath(); ns.LevelingPath(); drain(c)
        if not ns.window.IsShown(ns.window):
            ns.ToggleWindow()
        ns.SetFilter('recommended'); drain(c); ns.Refresh(); drain(c)
        self.assertTrue(ns.Option('uiNext'))
        home = ns.ui.home
        panel = home.path
        self.assertIsNotNone(panel)
        self.assertTrue(panel.IsShown(panel))
        self.assertEqual(panel.count, 4)
        self.assertEqual(panel.follow.caption.text, 'Follow path')
        self.assertGreater(-home.nextHeading.point[3], -panel.point[3])   # "Next for you" sits below the block.
        keys = [home.nextRows[index].data.key for index in range(1, home.nextCount + 1)]
        self.assertFalse([key for key in keys if str(key).startswith('path:')])
        first = list(ns.LevelingPath().steps.values())[0]
        self.assertEqual(panel.rows[1].zone.text, '1.  ' + first.zone)


class BackgroundCostTests(unittest.TestCase):
    """The path must never be felt: little work per frame, and not redone on every quest change."""

    def playing(self):
        c = scene(32, 0.85, map_id=1424, zone='Hillsbrad Foothills'); ns = c.ns
        c.lua.execute('clock = 1000; function GetTime() return clock end')
        drain(c); ns.InvalidateLevelingPath(); ns.LevelingPath(); drain(c)
        c.lua.execute('local ns = ...; builds = 0; local f = ns.QuestXPMultiplier; '
                      'refreshes = 0; local r = ns.ScheduleRefresh; ns.ScheduleRefresh = function(...) refreshes = refreshes + 1; return r(...) end', ns)
        return c

    def revision(self, c):
        return c.lua.eval('function(ns) return ns.levelingPathRevision or 0 end')(c.ns)

    def turn_in(self, c):
        c.lua.execute('local ns = ...; ns.questHistoryCount = (ns.questHistoryCount or 0) + 1; clock = clock + 2', c.ns)

    def test_quest_changes_do_not_each_trigger_a_recalculation(self):
        c = self.playing(); ns = c.ns
        before = self.revision(c)
        for _ in range(10):                                   # Ten quests accepted or turned in over twenty seconds.
            self.turn_in(c); ns.LevelingPath(); drain(c)
        self.assertEqual(self.revision(c), before)            # The path on screen is allowed to be a little old.
        self.assertIsNotNone(ns.LevelingPath())
        c.lua.execute('clock = clock + 31')
        ns.LevelingPath(); drain(c)
        self.assertEqual(self.revision(c), before + 1)        # Half a minute later it is brought up to date, once.

    def test_someone_waiting_for_the_answer_gets_a_fresh_one_at_once(self):
        c = self.playing(); ns = c.ns
        before = self.revision(c)
        self.turn_in(c)
        c.lua.execute('local ns = ...; answered = 0; ns.LevelingPath(function() answered = answered + 1 end)', ns)
        drain(c)
        self.assertEqual(c.lua.globals().answered, 1)
        self.assertEqual(self.revision(c), before + 1)        # A hand-over or the chat command is never given a stale path.

    def test_each_frame_gets_a_bounded_share_of_the_work(self):
        c = self.playing(); ns = c.ns
        # A clock on which every reading is 0.4 ms later: work must stop after a few readings.
        c.lua.execute('profile = 0; readings = 0; function debugprofilestop() profile = profile + 0.4; readings = readings + 1; return profile end')
        ns.InvalidateLevelingPath()
        ns.LevelingPath()
        frames, worst = 0, 0
        pop = c.lua.eval('function() local callback = table.remove(timers, 1); callback() end')
        while len(c.lua.globals().timers) and frames < 100000:
            before = c.lua.globals().readings
            pop(); frames += 1
            worst = max(worst, c.lua.globals().readings - before)
        self.assertGreater(frames, 100)                       # Spread over many frames...
        self.assertLessEqual(worst, 6)                        # ...each stopping once its 1.5 ms are used (a start reading and at most five checks).
        self.assertIsNotNone(ns.LevelingPath())

    def test_only_the_next_zones_are_worked_out_until_the_whole_path_is_asked_for(self):
        c = self.playing(); ns = c.ns
        near = ns.LevelingPath()
        self.assertEqual(len(steps(near)), 12)
        self.assertTrue(near.partial)
        self.assertIn('open the whole path', ' '.join(ns.LevelingPathLines(near).values()))
        ns.LevelingPathWhole(); drain(c)
        whole = ns.LevelingPathWhole()
        self.assertGreater(len(steps(whole)), 20)
        self.assertIsNone(whole.partial)
        self.assertEqual([step['zone'] for step in steps(whole)[:12]], [step['zone'] for step in steps(near)])

    def test_a_recalculation_that_changes_nothing_on_screen_redraws_nothing(self):
        c = self.playing(); ns = c.ns; g = c.lua.globals()
        g.refreshes = 0
        c.lua.execute('clock = clock + 31; local ns = ...; ns.questHistoryCount = (ns.questHistoryCount or 0) + 1', ns)
        before = self.revision(c)
        ns.LevelingPath(); drain(c)
        self.assertEqual(self.revision(c), before + 1)        # Recalculated...
        self.assertEqual(g.refreshes, 0)                      # ...same first zones and levels: no refresh of the addon.


class SoloEliteTests(unittest.TestCase):
    """Alone, elite quests are set aside by the guide instead of put in front of the player."""

    def elite(self, c):
        return c.lua.eval('''function(ns)
            local ids = {}
            for id in pairs(ns.catalogue.quests) do ids[#ids + 1] = id end
            table.sort(ids)
            for _, id in ipairs(ids) do
                local quest = ns.catalogue.quests[id]
                if quest.questType == "Elite" and (quest.level or 0) >= 30 and (quest.level or 0) <= 34
                    and ns.CatalogueIdentityAllowed(id, ns.profile) == true then return id end
            end
        end''')(c.ns)

    def value(self, ns, quest):
        result = ns.LevelingValue(quest)
        return result if isinstance(result, tuple) else (result, None)

    def test_an_elite_quest_is_set_aside_alone_and_planned_in_a_group_or_when_allowed(self):
        c = scene(32, 0.3); ns = c.ns
        quest = self.elite(c)
        if not quest:
            self.skipTest('no elite quest of this level in the catalogue')
        c.lua.execute('grouped = false; function IsInGroup() return grouped end; local ns = ...; ns.partyNames = {}', ns)
        value, reason = self.value(ns, quest)
        self.assertFalse(value)
        self.assertIn('Elite quest: set aside while you play alone', reason)
        ns.SetOption('soloEliteQuests', True)
        self.assertNotIn('set aside while you play alone', str(self.value(ns, quest)[1]))
        ns.SetOption('soloEliteQuests', False)
        c.lua.execute('grouped = true')
        self.assertNotIn('set aside while you play alone', str(self.value(ns, quest)[1]))

    def test_an_elite_quest_that_is_nearly_done_is_still_finished(self):
        c = scene(32, 0.3); ns = c.ns
        quest = self.elite(c)
        if not quest:
            self.skipTest('no elite quest of this level in the catalogue')
        c.lua.execute('function IsInGroup() return false end; local ns, id = ...; ns.partyNames = {}; '
                      'ns.active[id] = {id = id}; ns.localProgress[id] = {objectives = {{have = 9, need = 10}}}', ns, quest)
        value, reason = self.value(ns, quest)
        self.assertTrue(value)
        self.assertIn('90% through this one', reason)


class TooHardTests(unittest.TestCase):
    """A quest far above the character waits, whatever put it in front of them."""

    def hard(self, ns, quest, level):
        result = ns.QuestTooHard(quest, level)
        return result[0] if isinstance(result, tuple) else result

    def test_the_line_is_two_levels_by_default_and_a_setting(self):
        c = scene(33, 0.3); ns = c.ns
        self.assertTrue(self.hard(ns, 503, 33))                    # Gol'dir is level 36: three above.
        self.assertFalse(self.hard(ns, 503, 34))                   # Two above: fine.
        reason = ns.QuestTooHard(503, 33)[1]
        self.assertEqual(reason, "Level 36 quest: too hard at level 33. It comes back when you are level 34.")
        ns.SetOption('questLevelsAbove', '3')
        self.assertFalse(self.hard(ns, 503, 33))
        ns.SetOption('questLevelsAbove', 'any')
        self.assertFalse(self.hard(ns, 503, 30))
        ns.SetOption('questLevelsAbove', '2')

    def test_finished_and_nearly_finished_work_is_never_held_back(self):
        c = scene(33, 0.3); ns = c.ns
        c.lua.execute('local ns = ...; ns.active[503] = {id = 503}; ns.localProgress[503] = {objectives = {{have = 10, need = 10}}}', ns)
        self.assertFalse(self.hard(ns, 503, 33))                   # Done: hand it in.
        c.lua.execute('local ns = ...; ns.localProgress[503] = {objectives = {{have = 9, need = 10}}}', ns)
        self.assertFalse(self.hard(ns, 503, 33))                   # 90%: finish it.
        c.lua.execute('local ns = ...; ns.localProgress[503] = {objectives = {{have = 2, need = 10}}}', ns)
        self.assertTrue(self.hard(ns, 503, 33))
        c.lua.execute('local ns = ...; ns.localProgress[503] = {objectives = {}}', ns)
        self.assertTrue(self.hard(ns, 503, 33))                    # Nothing to do but travel there: still too hard.

    def test_a_too_hard_quest_in_the_log_is_not_planned_even_as_a_hand_in_or_a_prerequisite(self):
        # What happened in play: level 33, Gol'dir (36) in the log, the guide sending the
        # player into Alterac for it as "required for Blackmoore's Legacy later in this guide".
        def planned(setting):
            c = scene(33, 0.3, quests=(503,), completed=(498, 533, 552, 553)); ns = c.ns
            ns.SetOption('questLevelsAbove', setting)
            c.lua.execute('local ns = ...; ns.readyToTurnIn[503] = true', ns)      # A travel quest: "ready" on accepting.
            drain(c)
            guide = next(g for g in ns.LevelingGuideChoices().values() if g.mode == 'zone' and 'Hillsbrad' in (g.zone or ''))
            ns.ShowGuideOnMap(guide); drain(c)
            for _ in range(6):
                route = ns.selectedRoute
                if route and route.stops and len(list(route.stops.values())):
                    break
                ns.Refresh(True); drain(c)
            route = ns.selectedRoute
            return [stop.id for stop in route.stops.values()] if route and route.stops else []
        self.assertNotIn(503, planned('2'))
        self.assertIn(503, planned('any'))                          # The player's choice still stands.


class CleanLinkTests(unittest.TestCase):
    """The clean-up is one click away on the line under the guide window."""

    def test_the_link_shows_the_count_and_opens_the_question(self):
        import test_quest_cleanup as cleanup
        c, grey, current, dungeon = cleanup.cleaner(); ns = c.ns; g = c.lua.globals()
        c.lua.execute('local ns = ...; ns.routeSelection = {key = "guide", mode = "zone", zone = "Hillsbrad Foothills", mapID = 1424}', ns)
        ns.InvalidateLevelingPath(); ns.LevelingPath(); drain(c)
        state = c.lua.table_from({'visible': True})
        strip = ns.navigation.pathStrip
        ns.UpdateLevelingPathStrip(state)
        self.assertFalse(strip.clean.IsShown(strip.clean))          # Nothing to clean: no link.
        g.inLog(grey[0], 2, 10); g.inLog(grey[1], 0, 5)
        ns.ForgetUselessQuestCount()
        ns.UpdateLevelingPathStrip(state)
        self.assertTrue(strip.clean.IsShown(strip.clean))
        self.assertEqual(strip.clean.caption.text, 'Clean log (2)')
        strip.clean.OnClick(strip.clean)
        self.assertTrue(ns.questCleanupPrompt.IsShown(ns.questCleanupPrompt))
        self.assertEqual(len(list(g.abandoned.values())), 0)        # The click asks; it abandons nothing.
        ns.questCleanupPrompt.yes.OnClick(); drain(c)
        ns.UpdateLevelingPathStrip(state)
        self.assertFalse(strip.clean.IsShown(strip.clean))          # Cleaned: the link goes away.


class RealStuckStateTests(unittest.TestCase):
    """The stuck state as the game produces it, not a stand-in: every remaining step skipped."""

    def stuck(self):
        c = scene(33, 0.3, quests=(503,), completed=(498, 533, 552, 553)); ns = c.ns
        drain(c)
        guide = next(g for g in ns.LevelingGuideChoices().values() if g.mode == 'zone' and 'Hillsbrad' in (g.zone or ''))
        ns.ShowGuideOnMap(guide); drain(c)
        for _ in range(6):
            if ns.selectedRoute and not ns.routePlanning:
                break
            ns.Refresh(True); drain(c)
        # Skip every quest the guide still lists, as the player did.
        c.lua.execute('''
            local ns = ...
            for _, record in ipairs(ns.routeSelection.records or {}) do ns.char.guideSkips.quests[record.id] = true end
            started, printed = {}, {}
            ns.StartPartyRoute = function(guide) started[#started + 1] = guide end
            ns.Print = function(text) printed[#printed + 1] = text end
        ''', ns)
        ns.Refresh(True); drain(c)
        return c

    def test_the_window_state_for_all_steps_skipped_is_recognised_and_handed_over(self):
        c = self.stuck(); ns = c.ns; g = c.lua.globals()
        route = ns.selectedRoute
        self.assertEqual(len(list(route.stops.values())), 0)
        self.assertIsNotNone(ns.routePaused)                         # "Remaining guide steps are skipped."
        state = ns.NavigationState()
        self.assertEqual(state.stop.kind, 'notice')
        ns.char.levelingPathMode = True
        ns.LevelingPath(); drain(c)
        self.assertTrue(ns.LevelingPathChain(ns.NavigationState()))
        drain(c)
        self.assertEqual(len(list(g.started.values())), 1)           # The next zone starts.
        self.assertNotEqual(g.started[1].zone, 'Hillsbrad Foothills')
        self.assertIn('Hillsbrad Foothills has no steps left that you can take. Now following', ' '.join(g.printed.values()))


class NothingHoldsThatCannotBeDoneTests(unittest.TestCase):
    """A quest the player cannot or will not do never keeps them in a zone."""

    def business(self, c):
        ready, nearly = c.ns.ZoneUnfinishedBusiness(c.ns.routeSelection)
        return list(ready.values()), list(nearly.values())

    def test_a_too_hard_travel_quest_in_the_log_does_not_hold_the_hand_over(self):
        # Gol'dir again: level 36, no objectives (so "ready" on accepting), handed in in Alterac.
        c = scene(33, 0.3, quests=(503,), completed=(498, 533, 552, 553)); ns = c.ns
        drain(c)
        c.lua.execute('local ns = ...; ns.readyToTurnIn[503] = true; '
                      'ns.routeSelection = {key = "g", mode = "zone", zone = "Hillsbrad Foothills", mapID = 1416, homeMapID = 1424, records = {{id = 503}}}', ns)
        self.assertEqual(self.business(c), ([], []))                 # (The guide's current step is in Alterac, its zone is Hillsbrad.)
        ns.SetOption('questLevelsAbove', 'any')                      # Allowed again: still handed in elsewhere, so no hold.
        self.assertEqual(self.business(c), ([], []))

    def test_a_skipped_step_releases_a_nearly_finished_quest(self):
        c = scene(33, 0.3); ns = c.ns
        drain(c)
        here = c.lua.eval('''function(ns)
            local ids = {}
            for id in pairs(ns.catalogue.quests) do ids[#ids + 1] = id end
            table.sort(ids)
            for _, id in ipairs(ids) do
                local quest = ns.catalogue.quests[id]
                local level = quest.level or 0
                if level >= 30 and level <= 34 and quest.questType ~= "Elite" and quest.ends and quest.ends[1] and quest.ends[1].mapID == 1424 then return id end
            end
        end''')(ns)
        c.lua.execute('local ns, id = ...; ns.active[id] = {id = id}; ns.localProgress[id] = {objectives = {{have = 9, need = 10}}}; '
                      'ns.routeSelection = {key = "g", mode = "zone", zone = "Hillsbrad Foothills", mapID = 1424, records = {}}', ns, here)
        ready, nearly = self.business(c)
        self.assertEqual(len(nearly), 1)                             # 90% done: finish it first.
        c.lua.execute('local ns, id = ...; ns.char.guideSkips.steps[id] = {["q:1:x"] = true}', ns, here)
        self.assertEqual(self.business(c), ([], []))                 # The player skipped it: it no longer holds them.


class OneStopTests(unittest.TestCase):
    """Following the path and its zone guide stop together."""

    def running(self):
        c = scene(30, 0.2); ns = c.ns
        drain(c)
        plan = steps(ns.LevelingPathFrom())
        c.lua.execute('''
            local ns, zone = ...
            ns.UpdateSelectedRoute = function() end
            ns.routeSelection = {key = "guide", mode = "zone", zone = zone}
            ns.selectedRoute = {stops = {}, complete = false}
            stops, printed = 0, {}
            local stop = ns.StopGuide
            ns.StopGuide = function(...) stops = stops + 1; if ns.LevelingPathGuideStopped then ns.LevelingPathGuideStopped(select(2, ...)) end; ns.routeSelection = nil end
            ns.Print = function(text) printed[#printed + 1] = text end
            ns.char.levelingPathMode = true
        ''', ns, plan[0]['zone'])
        return c

    def test_stop_path_also_stops_its_zone_guide(self):
        c = self.running(); ns = c.ns; g = c.lua.globals()
        ns.StopLevelingPathMode()
        self.assertFalse(ns.LevelingPathFollowing())
        self.assertEqual(g.stops, 1)                                 # The zone guide went with it.
        self.assertIsNone(ns.routeSelection)
        self.assertEqual(len(list(g.printed.values())), 1)           # One message, not two.

    def test_stopping_the_zone_guide_also_ends_the_path(self):
        c = self.running(); ns = c.ns; g = c.lua.globals()
        ns.StopGuide(False)
        self.assertFalse(ns.LevelingPathFollowing())
        self.assertIn('Stopped following your leveling path', list(g.printed.values())[0])

    def test_a_pause_or_a_non_path_guide_leaves_the_path_alone(self):
        c = self.running(); ns = c.ns; g = c.lua.globals()
        ns.StopGuide(False, True)                                    # Paused with its checkpoint kept.
        self.assertTrue(ns.LevelingPathFollowing())
        c.lua.execute('local ns = ...; ns.routeSelection = {key = "p", mode = "profession"}', ns)
        ns.StopGuide(False)
        self.assertTrue(ns.LevelingPathFollowing())                  # A profession guide is not the path's.


class GuideCrossingIntoAnotherZoneTests(unittest.TestCase):
    """A zone guide whose current step is on a neighbouring map is still that zone's guide."""

    def test_the_followed_zone_is_the_guides_own_zone_not_the_map_of_its_current_step(self):
        c = scene(33, 0.3); ns = c.ns
        drain(c)
        # As in play: the Hillsbrad guide, with the route currently in Alterac Mountains.
        c.lua.execute('local ns = ...; ns.routeSelection = {key = "h", mode = "zone", zone = "Hillsbrad Foothills", mapID = 1416, homeMapID = 1424}', ns)
        first = steps(ns.LevelingPathFrom())[0]
        self.assertEqual(first['zone'], 'Hillsbrad Foothills')
        self.assertTrue(first['following'])
        c.lua.execute('local ns = ...; ns.routeSelection.zone = nil', ns)     # Without a name, the home map decides.
        first = steps(ns.LevelingPathFrom())[0]
        self.assertEqual(first['map'], 1424)
