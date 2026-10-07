"""Destination reasons must explain a real benefit without changing the plan.

Synthetic Lua 5.1 fixtures verify reasoning and owned-frame layout. Native beta
fonts, rendering, NPC offers and terrain still require in-game testing.
"""
import unittest

from test_063 import guide_client, learner, learn, zone, order
from test_061 import run_plan
from test_routes import guide
from test_navigation import navigator
from test_087 import tip_client


def step(c, ident=900, kind='a', **extra):
    return c.lua.table_from(dict(id=ident, kind=kind, title=f'Quest {ident-900}',
                                mapID=501, x=.2, y=.25, npcName='Named giver', **extra))


def select(c, stops, ids=(900, 901)):
    c.ns.routeSelection = guide(c, ids)
    c.ns.selectedRoute = c.lua.table_from({'stops': c.lua.table_from(stops)})


class DestinationReasonTests(unittest.TestCase):
    def test_long_generic_trip_is_honest_about_its_value(self):
        c = guide_client(1); s = step(c); select(c, [s], (900,))
        short = c.ns.GuideVisibleReason(s, 501, 100)
        self.assertIn('level 12', short)
        self.assertNotIn('Skip quest', short)
        far = c.ns.RouteContext(s, 502, None, 1500)
        self.assertIn('No special unlock is known', far)
        self.assertIn('Skip quest', far)
        self.assertNotIn('optimal', far)
        self.assertFalse(c.ns.GuideDestinationDecision(s).specificBenefit)

    def test_mutated_stop_cannot_keep_a_pickup_reason_after_becoming_a_return(self):
        c = guide_client(1); s = step(c); select(c, [s], (900,))
        self.assertEqual(c.ns.GuideDestinationDecision(s).code, 'level-work')
        s.kind = 't'
        self.assertEqual(c.ns.GuideDestinationDecision(s).code, 'quest-reward')
        self.assertNotIn('level 12', c.ns.GuideVisibleReason(s, 501, 1500))

    def test_unknown_or_private_distance_does_not_invent_a_long_trip(self):
        c = guide_client(1); s = step(c); select(c, [s], (900,))
        for map_id, distance in ((0, None), (None, None), (501, c.lua.globals().secret)):
            self.assertNotIn('detour', c.ns.GuideVisibleReason(s, map_id, distance))

    def test_chain_reason_names_the_followup_and_disappears_when_completed(self):
        c = guide_client(2); c.ns.catalogue.quests[901].previousQuest = 900
        s = step(c); select(c, [s])
        d = c.ns.GuideDestinationDecision(s)
        self.assertEqual(d.code, 'prerequisite')
        self.assertIn('Required for Quest 1', d.why)
        self.assertEqual(list(d.relatedQuestIDs.values()), [901])
        c.lua.globals().finished[901] = True
        c.ns.ForgetQuestCompletion(901)
        c.ns.objectiveDisplayRevision = 1
        self.assertNotEqual(c.ns.GuideDestinationDecision(s).code, 'prerequisite')

    def test_wrong_faction_or_skipped_followup_is_not_a_benefit(self):
        for excluded in ('faction', 'skip'):
            c = guide_client(2); c.ns.catalogue.quests[901].previousQuest = 900
            if excluded == 'faction': c.ns.catalogue.quests[901].side = 'Alliance'
            else: c.ns.db.guideSkips[c.ns.self].quests[901] = True
            s = step(c); select(c, [s])
            self.assertNotEqual(c.ns.GuideDestinationDecision(s).code, 'prerequisite')

    def test_alternative_only_explains_the_branch_explicitly_selected(self):
        c = guide_client(2); c.ns.catalogue.quests[901].prerequisiteAny = c.lua.table_from([900, 999])
        s = step(c); select(c, [s])
        self.assertNotIn('Required', c.ns.GuideDestinationReason(s))
        c.ns.routeSelection = guide(c)
        c.ns.routeSelection.records[2] = c.ns.CatalogueRecord(901)
        c.ns.routeSelection.collectionDependencies = c.lua.table_from({901: [900]}, recursive=True)
        d = c.ns.GuideDestinationDecision(s)
        self.assertEqual(d.code, 'chosen-branch')
        self.assertIn('other prerequisites may also work', d.why)

    def test_learned_chain_is_scoped_and_does_not_expose_observer_names(self):
        c = learner(); learn(c)
        c.lua.globals().finished[900] = False; c.ns.ForgetQuestCompletion(900)
        s = step(c); select(c, [s])
        self.assertEqual(c.ns.GuideDestinationDecision(s).code, 'learned-prerequisite')
        self.assertNotIn('Observed by', c.ns.GuideDestinationReason(s))
        c.ns.db.config.useLearnedQuests = False
        self.assertNotEqual(c.ns.GuideDestinationDecision(s).code, 'learned-prerequisite')

    def test_useful_low_level_step_explains_what_makes_it_worthwhile(self):
        c = guide_client(2)
        c.ns.catalogue.quests[900].level = 16
        c.ns.catalogue.quests[901].level = 20
        c.ns.catalogue.quests[901].previousQuest = 900
        c.ns.profile.level = 21
        s = step(c); select(c, [s])
        d = c.ns.GuideDestinationDecision(s)
        self.assertEqual(d.code, 'useful-prerequisite')
        self.assertIn('Lower-level', d.why)
        self.assertIn('Quest 1 (level 20)', d.why)

    def test_hub_claim_respects_offer_absence_skips_and_phase_boundaries(self):
        c = guide_client(3); a, b, q, later = step(c), step(c, 901), step(c, kind='q'), step(c, 902)
        select(c, [a, b, q, later], (900, 901, 902))
        self.assertIn('2 nearby quest pickups', c.ns.GuideDestinationReason(a))
        c.ns.PickupOfferEvidence = c.lua.eval('function(key,id) if id==901 then return false end end')
        c.ns.objectiveDisplayRevision = 1
        self.assertNotEqual(c.ns.GuideDestinationDecision(a).code, 'pickup-hub')
        c.ns.PickupOfferEvidence = c.lua.eval('function() return true end')
        c.ns.db.guideSkips[c.ns.self].quests[901] = True
        c.ns.objectiveDisplayRevision = 2
        self.assertNotEqual(c.ns.GuideDestinationDecision(a).code, 'pickup-hub')

    def test_objective_area_counts_only_accepted_unfinished_work(self):
        c = guide_client(2)
        a, b = step(c, kind='q', action='kill', quantity=7), step(c, 901, 'q', action='collect', quantity=10)
        select(c, [a, b]); c.ns.active[900] = 'Quest 0'
        self.assertNotEqual(c.ns.GuideDestinationDecision(a).code, 'objective-area')
        c.ns.active[901] = 'Quest 1'; c.ns.objectiveDisplayRevision = 1
        d = c.ns.GuideDestinationDecision(a)
        self.assertEqual(d.code, 'objective-area')
        self.assertIn('2 accepted quests', d.why)
        c.ns.db.guideSkips[c.ns.self].quests[901] = True; c.ns.objectiveDisplayRevision = 2
        self.assertNotEqual(c.ns.GuideDestinationDecision(a).code, 'objective-area')

    def test_low_ready_return_still_explains_the_reward(self):
        c = guide_client(1); c.ns.profile.level = 30
        s = step(c, kind='t'); select(c, [s], (900,))
        self.assertEqual(c.ns.GuideDestinationDecision(s).code, 'quest-reward')
        self.assertIn('collect the reward', c.ns.GuideDestinationReason(s))

    def test_unknown_pickup_requirements_name_the_giver_without_inventing_access(self):
        c = guide_client(1); c.ns.catalogue.quests[900].prerequisitesUnverified = True
        s = step(c); select(c, [s], (900,))
        d = c.ns.GuideDestinationDecision(s)
        self.assertIn('Named giver', d.caution)
        self.assertTrue(d.needsReview)
        self.assertIn('Confirm availability with Named giver', c.ns.RouteContext(s, 501))
        missing = step(c, unknownLocation=True)
        self.assertIn('not mapped', c.ns.GuideDestinationDecision(missing).caution)

    def test_preview_reason_uses_preview_guide_without_changing_the_active_guide(self):
        c = guide_client(2); c.ns.catalogue.quests[901].previousQuest = 900
        s = step(c); select(c, [s], (900,))
        active = c.ns.routeSelection
        preview = guide(c, (900, 901))
        self.assertNotIn('Required for', c.ns.GuideDestinationReason(s))
        self.assertIn('Required for Quest 1', c.ns.GuideStepDescription(s, None, preview, c.ns.selectedRoute))
        self.assertEqual(c.ns.routeSelection.key, active.key)
        self.assertNotIn('Required for', c.ns.GuideDestinationReason(s))

    def test_reason_reads_are_cached_and_do_not_replan_or_mutate_skips(self):
        c = guide_client(2); g = zone(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(g); s = c.ns.selectedRoute.stops[1]
        reason = c.ns.GuideDestinationReason(s)
        fail = c.lua.eval('function() error("reason must use its cached facts") end')
        c.ns.CatalogueCompletion = fail; c.ns.WalkingDistance = fail; c.ns.BuildGuideRoute = fail
        for _ in range(25): self.assertEqual(c.ns.GuideDestinationReason(s), reason)
        self.assertEqual(order(g), before)
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_unrelated_guide_records_do_not_trigger_completion_queries(self):
        c = guide_client(30); c.ns.catalogue.quests[929].previousQuest = 900
        s = step(c); select(c, [s], tuple(range(900, 930)))
        calls = []
        def completion(key, ident, query=None):
            calls.append(ident)
            return False
        c.ns.CatalogueCompletion = completion
        self.assertIn('Required for Quest 29', c.ns.GuideDestinationReason(s))
        self.assertEqual(calls, [929])

    def test_dungeon_collection_explains_preparation_not_a_generic_zone_pickup(self):
        c = guide_client(1); s = step(c); select(c, [s], (900,))
        c.ns.routeSelection.mode = 'dungeon'; c.ns.routeSelection.zone = 'Test dungeon'
        c.ns.routeSelection.collectionGoals = c.lua.table_from({900: True})
        self.assertEqual(c.ns.GuideDestinationDecision(s).code, 'dungeon-pickup')
        self.assertIn('before entering Test dungeon', c.ns.GuideDestinationReason(s))


class VisibleReasonTests(unittest.TestCase):
    def test_reason_is_readable_in_main_or_standalone_without_hovering(self):
        c = navigator(); s = c.ns.selectedRoute.stops[1]
        c.ns.catalogue.quests[900].level = 12
        c.ns.objectiveDisplayRevision = 1
        c.lua.globals().reasonLabel = c.ns.standaloneNavigation.reason
        c.lua.execute('function reasonLabel:GetStringHeight() return 55 end')
        c.ns.SetOption('standaloneArrow', True)
        self.assertIn(c.ns.GuideDestinationReason(s), c.ns.navigation.context.text)
        self.assertFalse(c.ns.standaloneNavigation.reason.IsShown(c.ns.standaloneNavigation.reason))
        c.ns.SetOption('routeArrow', False)
        f = c.ns.standaloneNavigation
        self.assertTrue(f.reason.IsShown(f.reason))
        self.assertIn(c.ns.GuideDestinationReason(s), f.reason.text)
        self.assertGreaterEqual(f.reason.height, 55)
        self.assertGreaterEqual(f.width, f.reason.width)
        self.assertGreaterEqual(f.height, 102 + f.reason.height + 4)

    def test_standalone_advice_sits_below_the_reason_and_dismissal_keeps_it(self):
        c = tip_client(inn=False, flight=True)
        c.lua.globals().reasonLabel = c.ns.standaloneNavigation.reason
        c.lua.execute('function reasonLabel:GetStringHeight() return 44 end')
        c.ns.SetOption('standaloneArrow', True); c.ns.SetOption('routeArrow', False)
        f = c.ns.standaloneNavigation
        self.assertTrue(f.tip.IsShown(f.tip))
        self.assertLess(f.tip.point[5], f.reason.point[5] - f.reason.height)
        before = f.height; f.tip.close.OnClick()
        self.assertTrue(f.reason.IsShown(f.reason))
        self.assertEqual(f.height, before - 56)
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_main_grows_for_the_reason_without_changing_saved_size(self):
        c = navigator(); f = c.ns.navigation
        c.ns.db.arrowSize = c.lua.table_from({'width': 360, 'height': 168})
        f.SetHeight(f, 168)
        c.lua.globals().reasonLabel = f.context
        c.lua.execute('function reasonLabel:GetStringHeight() return 65 end')
        c.ns.UpdateNavigation()
        self.assertGreaterEqual(f.context.height, 65)
        self.assertGreaterEqual(f.height, 142 + 65)
        self.assertEqual(c.ns.db.arrowSize.height, 168)


if __name__ == '__main__': unittest.main()
