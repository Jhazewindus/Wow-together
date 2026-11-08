"""Account world facts migrate separately from per-character progress."""
import unittest

from test_addon import Client
from test_063 import primitive


class CharacterStorageTests(unittest.TestCase):
    def test_old_account_data_migrates_current_progress_and_merges_world_inns(self):
        client = Client(quests=())
        ns = client.ns
        ns.db.schema = None
        ns.char.schema = None
        ns.db.questHistory = client.lua.table_from({
            'Alice-TestRealm': {'70009': {101: True}},
            'Bob-TestRealm': {'70009': {202: True}},
        }, recursive=True)
        ns.db.guideServices = client.lua.table_from({
            'Alice-TestRealm': {'boundInnID': 'A', 'inns': {'A': {
                'id': 'A', 'name': 'Alice Inn', 'mapID': 1, 'x': .1, 'y': .2}}},
            'Bob-TestRealm': {'boundInnID': 'B', 'inns': {'B': {
                'id': 'B', 'name': 'Bob Inn', 'mapID': 2, 'x': .3, 'y': .4}}},
        }, recursive=True)
        ns.db.offerKnowledge = client.lua.table_from({
            'Alice-TestRealm': {50: {'context': '12:', 'offered': {101: True}}},
            'Bob-TestRealm': {60: {'context': '20:', 'offered': {202: True}}},
        }, recursive=True)
        ns.MigrateCharacterStorage()
        self.assertTrue(ns.char.questHistory['70009'][101])
        self.assertIsNone(ns.char.questHistory['70009'][202])
        self.assertEqual(ns.char.guideServices.boundInnID, 'A')
        inns = ns.db.innLocations["70009"]
        self.assertEqual(set(inns.keys()), {'A', 'B'})
        self.assertTrue(ns.db.offerKnowledgeBuilds['70009'].unknown['legacy:12:'][101][50].offered)
        ns.db.guideServices['Other-TestRealm'] = client.lua.table_from({"inns": {
            "C": {"id": "C", "mapID": 3, "x": .5, "y": .6}}}, recursive=True)
        ns.MigrateCharacterStorage()
        self.assertIsNone(ns.db.innLocations["70009"].C)

    def test_fresh_alt_has_empty_progress_and_can_use_account_world_facts(self):
        main = Client(quests=())
        main.ns.db.innLocations = main.lua.table_from({'70009': {'A': {'id': 'A', 'mapID': 1, 'x': .1, 'y': .2}}}, recursive=True)
        main.ns.db.offerKnowledgeBuilds = main.lua.table_from({'70009': {'Horde': {'101': {900: {50: {'offered': True}}}}}}, recursive=True)
        alt = Client(name='Alt', quests=(), saved_variables=primitive(main.ns.db))
        self.assertEqual(len(list(alt.ns.char.questHistory['70009'].keys())), 0)
        self.assertIsNotNone(alt.ns.db.innLocations['70009'].A)
        self.assertTrue(alt.ns.db.offerKnowledgeBuilds['70009'].Horde['101'][900][50].offered)


if __name__ == '__main__':
    unittest.main()
