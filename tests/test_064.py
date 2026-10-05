"""Faction-wide observed gates, legacy migration and the reported Hunt chain.

Synthetic host checks do not certify live beta offers or rendering.
"""
import copy
import json
import unittest
from test_addon import Client
from test_routes import catalogue, guide
from test_061 import world_quest
from test_063 import learner, learn, offers, primitive, zone, order
from import_warcraftdb import apply_corrections


class FactionLearningTests(unittest.TestCase):
    def test_ordinary_rule_applies_to_another_class_and_race_without_source_progress(self):
        c = learner(); learn(c)
        c.ns.profile.classID, c.ns.profile.raceID = 1, 6
        c.lua.globals().finished[900] = False
        c.ns.InvalidateNPCOffers()
        rule = c.ns.LearnedQuestRule(901)
        self.assertEqual(rule.previousQuest, 900)
        self.assertFalse(rule.classRestricted); self.assertFalse(rule.raceRestricted)
        allowed, reason = c.ns.CatalogueAllowed(901, c.ns.profile, c.ns.self)
        self.assertFalse(allowed); self.assertIn('Observed by', reason)
        self.assertIn('Quest 0', reason)
        # The new character's own hand-in, not the source's, unlocks the step.
        c.lua.globals().finished[900] = True
        self.assertTrue(c.ns.CatalogueAllowed(901, c.ns.profile, c.ns.self))

    def test_class_only_child_or_parent_keeps_class_scope_but_allows_other_races(self):
        for restricted in (900, 901):
            with self.subTest(restricted=restricted):
                c = learner(); c.ns.catalogue.quests[restricted].classMask = 64
                learn(c)
                self.assertTrue(c.ns.LearnedQuestRule(901).classRestricted)
                c.ns.profile.raceID = 6
                self.assertIsNotNone(c.ns.LearnedQuestRule(901))
                c.ns.profile.classID = 1
                self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_class_category_retains_scope_even_when_mask_is_absent(self):
        c = learner(); c.ns.catalogue.quests[900].categoryPath = 'classes/shaman'
        learn(c); c.ns.profile.classID = 1
        self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_race_only_child_or_parent_keeps_race_scope_but_allows_other_classes(self):
        for restricted in (900, 901):
            with self.subTest(restricted=restricted):
                c = learner(); c.ns.catalogue.quests[restricted].raceMask = 2
                learn(c)
                self.assertTrue(c.ns.LearnedQuestRule(901).raceRestricted)
                c.ns.profile.classID = 1
                self.assertIsNotNone(c.ns.LearnedQuestRule(901))
                c.ns.profile.raceID = 6
                self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_other_faction_and_build_never_reuse_the_rule(self):
        c = learner(); learn(c)
        c.ns.profile.faction = 'Alliance'
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        c.ns.profile.faction = 'Horde'
        c.lua.execute("function GetBuildInfo() return '1.60.1','99999','test',16001 end")
        self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_public_ordinary_rule_does_not_need_class_or_race_to_be_readable(self):
        c = learner(); learn(c)
        c.ns.profile.classID, c.ns.profile.raceID = None, None
        self.assertIsNotNone(c.ns.LearnedQuestRule(901))

    def test_ordinary_unlock_can_be_learned_without_public_class_or_race(self):
        c = learner()
        c.lua.execute("function UnitClass() return nil,nil,secret end; function UnitRace() return nil,nil,secret end")
        learn(c)
        self.assertEqual(c.ns.LearnedQuestRule(901).previousQuest, 900)

    def test_restricted_unlock_needs_the_restricted_dimension_to_be_known(self):
        c = learner(); c.ns.catalogue.quests[901].classMask = 64
        c.lua.execute("function UnitClass() return nil,nil,secret end")
        learn(c)
        self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_contradiction_from_another_class_disables_faction_wide_rule(self):
        c = learner(); learn(c); c.lua.globals().finished[900] = False
        c.lua.execute("function UnitClass() return 'Warrior','WARRIOR',1 end; function UnitRace() return 'Tauren','Tauren',6 end")
        offers(c, [901], full=False)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        self.assertTrue(json.loads(c.ns.ExportGuideFindings())['findings'][0]['disabled'])

    def legacy(self, conflict=False, restricted=False):
        c = learner()
        if restricted: c.ns.catalogue.quests[901].classMask = 64
        learn(c)
        saved = primitive(c.ns.db.questLearning)
        rule = copy.deepcopy(next(iter(saved['rules'].values())))
        base = ':'.join(str(rule[k]) for k in ('interface', 'build', 'faction'))
        rule['scope'] = base + ':7:2'
        saved['schema'] = 1
        saved['rules'] = {rule['scope'] + ':901': rule}
        if not restricted:
            second = copy.deepcopy(rule)
            second.update(scope=base + ':1:6', classID=1, raceID=6,
                          sourceCharacter='Other Tauren', characters={'Other-Tauren': True})
            if conflict:
                second['previousQuest'] = 902
                c.ns.catalogue.quests[902] = c.lua.table_from(world_quest('Other parent'), recursive=True)
            saved['rules'][second['scope'] + ':901'] = second
        c.ns.db.questLearning = c.lua.table_from(saved, recursive=True)
        c.ns.db.questResearch = c.lua.table()  # Test migration independent of retained raw replay.
        c.ns.InitializeQuestLearning()
        return c

    def test_old_matching_rules_merge_without_losing_sources_or_proofs(self):
        c = self.legacy()
        self.assertEqual(c.ns.db.questLearning.schema, 2)
        self.assertEqual(len(list(c.ns.db.questLearning.rules.items())), 1)
        c.ns.profile.classID, c.ns.profile.raceID = 1, 6
        self.assertEqual(c.ns.LearnedQuestRule(901).previousQuest, 900)
        finding = json.loads(c.ns.ExportGuideFindings())['findings'][0]
        self.assertEqual(finding['sourceCount'], 2)
        self.assertEqual(len(finding['proofs']), 2)
        c.ns.InitializeQuestLearning()
        self.assertEqual(len(json.loads(c.ns.ExportGuideFindings())['findings'][0]['proofs']), 2)

    def test_conflicting_old_classes_are_preserved_for_review_not_applied(self):
        c = self.legacy(conflict=True)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        finding = json.loads(c.ns.ExportGuideFindings())['findings'][0]
        self.assertTrue(finding['disabled'])
        self.assertIn('Conflicting', finding['reason'])
        self.assertEqual(finding['sourceCount'], 2)

    def test_old_class_rule_stays_restricted_after_migration(self):
        c = self.legacy(restricted=True)
        self.assertIsNotNone(c.ns.LearnedQuestRule(901))
        c.ns.profile.classID = 1
        self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_new_fixed_plan_uses_learned_gate_for_another_class_and_race(self):
        c = learner(); learn(c)
        c.ns.profile.classID, c.ns.profile.raceID = 1, 6
        g = zone(c); c.ns.GenerateFixedGuide(g, False)
        stages = [(s.id, s.kind) for s in g.fixedPlan.values()]
        self.assertLess(stages.index((900, 't')), stages.index((901, 'a')))

    def test_missing_offer_and_manual_skip_do_not_invent_a_predecessor(self):
        c = learner(); c.ns.active[900] = 'Quest 0'
        g = zone(c); c.ns.ActivateRoute(g)
        offers(c, [])
        before = order(g)
        skipped_id = (c.ns.selectedRoute.pendingStop or c.ns.selectedRoute.stops[1]).id
        c.ns.SkipGuide('quest')
        self.assertEqual(order(g), before)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        events = json.loads(c.ns.ExportQuestResearch())['events']
        self.assertEqual(events[-1]['event'], 'skip-quest')
        self.assertEqual(events[-1]['questID'], skipped_id)
        self.assertFalse(json.loads(c.ns.ExportGuideFindings())['findings'])


class HuntChainTests(unittest.TestCase):
    def test_import_preserves_reported_gate_without_relabeling_it_as_published(self):
        records = {747: {'title': 'The Hunt Begins'}, 750: {'title': 'The Hunt Continues'}}
        self.assertEqual(apply_corrections(records), [750])
        self.assertEqual(records[750]['previousQuest'], 747)
        self.assertIn('Tester report', records[750]['prerequisiteSource'])
        self.assertEqual(apply_corrections(records), [750])
        records[750]['previousQuest'] = 999
        with self.assertRaises(ValueError): apply_corrections(records)

    def test_real_catalogue_hunt_requires_actual_hand_in_in_both_route_modes(self):
        c = Client(quests=(747,), use_catalogue=True)
        c.lua.globals().entries[1].title = 'The Hunt Begins'
        c.ns.ReadQuests()
        c.guide_environment(level=3)
        c.ns.profile.classID, c.ns.profile.raceID = 1, 6
        c.lua.globals().grouped = False
        q = c.ns.CatalogueQuest(750)
        self.assertEqual(q.previousQuest, 747)
        c.ns.active[747] = 'The Hunt Begins'
        c.ns.offered[750] = True  # An offer still cannot bypass this known gate.
        allowed, reason = c.ns.CatalogueAllowed(750, c.ns.profile, c.ns.self)
        self.assertFalse(allowed); self.assertIn('The Hunt Begins', reason)
        g = guide(c, (747, 750)); g.fixedRoute = True
        route = c.ns.BuildGuideRoute(g, False)
        stages = [(s.id, s.kind) for s in g.fixedPlan.values()]
        self.assertLess(stages.index((747, 't')), stages.index((750, 'a')))
        self.assertNotIn(750, {s.id for s in route.previewStops.values()})
        g.fixedRoute = False
        self.assertIsNone(c.ns.RouteStop(c.ns.CatalogueRecord(750), c.ns.self))
        c.lua.globals().finished[747] = True
        self.assertTrue(c.ns.CatalogueAllowed(750, c.ns.profile, c.ns.self))


if __name__ == '__main__':
    unittest.main()
