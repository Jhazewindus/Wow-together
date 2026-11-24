import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua


EXPECTED_PREVIOUS = {
    78089: 78088, 78090: 78089, 78092: 78091, 78093: 78092,
    79235: 79229, 79358: 96264, 79361: 79364, 79364: 79360,
    79366: 79361, 88757: 87318, 88758: 88757, 91859: 91858,
    91860: 91859, 91861: 91860, 91862: 91861, 93465: 93464,
    94497: 94495, 94499: 94497, 94500: 94499, 94501: 94500,
    94502: 94501, 94503: 94502, 94505: 94503, 94974: 94973,
    94981: 94980, 94998: 94997, 95034: 96204, 95036: 95034,
    95111: 95036, 95125: 95111, 95126: 95125, 96135: 79358,
    96204: 91862, 96264: 94789, 96782: 96781, 98396: 98394,
    98731: 98396, 98738: 98404,
}


class QuestDataRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = own_lua(ROOT / 'WowTogether_QuestData/QuestCatalogue.lua', 'catalogue')['quests']
        cls.corrections = json.loads((ROOT / 'tools/quest_corrections.json').read_text())
        cls.refresh_rows = [row for row in cls.corrections
                            if row.get('source', '').startswith('https://www.wowhead.com/forever/quest=')
                            and 'captured 2026-11-24;' in row.get('source', '')
                            and row.get('prerequisiteCorrection')]

    def test_confirmed_chain_predecessors_are_in_the_shipped_catalogue(self):
        actual = {ident: self.catalogue[ident].get('previousQuest') for ident in EXPECTED_PREVIOUS}
        self.assertEqual(actual, EXPECTED_PREVIOUS)
        self.assertEqual({row['questID'] for row in self.refresh_rows}, set(EXPECTED_PREVIOUS))

    def test_every_imported_link_has_page_hash_and_matching_quest_identities(self):
        self.assertEqual(len(self.refresh_rows), 38)
        for row in self.refresh_rows:
            with self.subTest(quest=row['questID']):
                quest = self.catalogue[row['questID']]
                parent = self.catalogue[row['prerequisiteCorrection']['previousQuest']]
                self.assertEqual(row['title'], quest['title'])
                self.assertEqual(row['previousTitle'], parent['title'])
                self.assertRegex(row['source'], r'https://www\.wowhead\.com/forever/quest=\d+')
                self.assertRegex(row['source'], r'SHA-256 [0-9a-f]{64}')
                self.assertIn(f"{parent['title']} immediately before {quest['title']}", row['source'])

    def test_unverified_questie_candidate_is_not_added_as_a_correction(self):
        # The Questie candidate for 95621 was absent from its captured Series
        # table, so it remains outside this batch of reviewed corrections.
        self.assertNotIn(95621, {row['questID'] for row in self.refresh_rows})


if __name__ == '__main__':
    unittest.main()
