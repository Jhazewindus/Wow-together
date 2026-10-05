"""Parallel class variants must not lock the unrestricted quest behind a class introduction."""
import unittest

from test_importers import detail
from import_wowhead import detail_facts, prerequisite_facts


PAGE = ('<table class="series">'
        '<tr><a href="/forever/quest=30">Local trouble</a></tr>'
        '<tr><b>Local trouble</b><a href="/forever/quest=32">Local trouble</a></tr>'
        '<tr><a href="/forever/quest=33">Next quest</a></tr></table>')
FACTS = {30: {'classMask': 256}, 31: {'classMask': 0}, 32: {'classMask': 256}}


class ParallelClassBranchTests(unittest.TestCase):
    def test_general_variant_does_not_inherit_the_parallel_class_introduction(self):
        facts = prerequisite_facts(PAGE, 31, FACTS)
        self.assertNotIn('previousQuest', facts)
        self.assertEqual(facts['prerequisiteSource'], 'Wowhead Forever parallel class branch')

    def test_class_variant_still_requires_its_class_introduction(self):
        page = PAGE.replace('<b>Local trouble</b>', '<a href="/forever/quest=31">Local trouble</a>') \
                   .replace('<a href="/forever/quest=32">Local trouble</a>', '<b>Local trouble</b>')
        self.assertEqual(prerequisite_facts(page, 32, FACTS)['previousQuest'], 30)

    def test_shared_followup_retains_completion_gate_for_either_variant(self):
        page = PAGE.replace('<b>Local trouble</b>', '<a href="/forever/quest=31">Local trouble</a>') \
                   .replace('<a href="/forever/quest=33">Next quest</a>', '<b>Next quest</b>')
        self.assertEqual(prerequisite_facts(page, 33, FACTS)['prerequisiteAny'], [31, 32])

    def test_missing_or_nonmatching_variant_metadata_does_not_remove_a_gate(self):
        for facts in (None, {}, {30: {'classMask': 256}, 32: {'classMask': 256}},
                      {30: {'classMask': 256}, 31: {'classMask': 0}},
                      {30: {'classMask': 0}, 31: {'classMask': 0}, 32: {'classMask': 256}},
                      {30: {'classMask': 256}, 31: {'classMask': 0}, 32: {'classMask': 1}}):
            with self.subTest(facts=facts):
                self.assertEqual(prerequisite_facts(PAGE, 31, facts)['previousQuest'], 30)

    def test_different_named_variants_do_not_establish_a_parallel_class_branch(self):
        page = PAGE.replace('<b>Local trouble</b>', '<b>Different quest</b>')
        self.assertEqual(prerequisite_facts(page, 31, FACTS)['previousQuest'], 30)

    def test_detail_import_uses_its_explicit_mask_with_other_variants_metadata(self):
        facts = detail_facts(detail([]) + PAGE, {'id': 42, 'reqclass': 0}, {14: 1411},
                             {30: {'classMask': 256}, 32: {'classMask': 256}})
        self.assertNotIn('previousQuest', facts)
        self.assertTrue(facts['prerequisitesRead'])


if __name__ == '__main__':
    unittest.main()
