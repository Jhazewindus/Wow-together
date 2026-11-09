"""Replay public game events into the separate Gold addon."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_skeleton import ROOT, load_gold
from test_addon import Client
sys.path.insert(0, str(ROOT / "tools" / "gold"))
from ingest_observations import ingest, load_exports


GUID = "Creature-0-0-0-0-123-00000001"
NODE = "GameObject-0-0-0-0-456-00000002"


def observation_client():
    client = Client(quests=(), default_guide=True)
    client.lua.execute('''
        now, serverTime, groupSize = 100, 100000, 2
        inside, instanceKind, instanceID = false, "none", 0
        GetTime = function() return now end
        GetServerTime = function() return serverTime end
        GetNumGroupMembers = function() return groupSize end
        IsInInstance = function() return inside, instanceKind end
        GetInstanceInfo = function() return "Test", nil, nil, nil, nil, nil, nil, instanceID end
        C_Spell = {GetSpellInfo = function(id)
            if id == 77 then return {name="Mining"} end
        end}
        C_Map = {GetBestMapForUnit = function() return 501 end,
            GetPlayerMapPosition = function() return {GetXY=function() return .2, .4 end} end}
    ''')
    private = load_gold(client)
    price_source = (ROOT / "WowTogether_Gold" / "GoldPrices.lua").read_text()
    client.lua.execute("assert(loadstring(...))(select(2, ...))", price_source, "WowTogether_Gold", private)
    source = (ROOT / "WowTogether_Gold" / "GoldObservations.lua").read_text()
    client.lua.execute("assert(loadstring(...))(select(2, ...))", source, "WowTogether_Gold", private)
    return client, private.GoldObservations, private


class GoldObservationTests(unittest.TestCase):
    def test_loot_and_cast_events_replay_through_registered_handlers(self):
        client, _, private = observation_client()
        client.lua.execute('''
            lootGUID = "Creature-0-0-0-0-123-00000001"
            GetNumLootItems = function() return 1 end
            GetLootSourceInfo = function() return lootGUID, 1 end
            GetLootSlotLink = function() return "|Hitem:42|h[Test item]|h" end
            GetLootSlotInfo = function() return nil, nil, 2 end
        ''')
        client.ns.frame.OnEvent(client.ns.frame, "LOOT_OPENED")
        record = private.db.observations["70009"].mobs[123]
        self.assertEqual((record.looted, record.drops[42].total), (1, 2))
        client.ns.frame.OnEvent(client.ns.frame, "UNIT_SPELLCAST_SUCCEEDED", "player", "Cast-1", 77)
        client.lua.globals().lootGUID = NODE
        client.ns.frame.OnEvent(client.ns.frame, "LOOT_OPENED")
        self.assertEqual(private.db.observations["70009"].nodes[501][1].visits, 1)
        client.lua.execute('''
            now = 110
            CombatLogGetCurrentEventInfo = function()
                return 0, "PARTY_KILL", false, nil, nil, nil, nil,
                    "Creature-0-0-0-0-123-00000002"
            end
        ''')
        client.ns.frame.OnEvent(client.ns.frame, "COMBAT_LOG_EVENT_UNFILTERED")
        client.ns.frame.OnEvent(client.ns.frame, "CHAT_MSG_LOOT",
                                "Bob receives loot: |Hitem:43|h[Other item]|h|r x3")
        self.assertEqual((record.looted, record.drops[43].total), (2, 3))

    def test_kills_are_deduplicated_and_pace_uses_party_size(self):
        client, observations, private = observation_client()
        self.assertTrue(observations.RecordKill(GUID, 100))
        self.assertFalse(observations.RecordKill(GUID, 101))
        self.assertTrue(observations.RecordKill(GUID[:-1] + "2", 105))
        self.assertTrue(observations.RecordKill(GUID[:-1] + "3", 112))
        pace = private.db.observations["70009"].mobs[123].pace[2]
        self.assertEqual((pace.seconds, pace.sampleSize, pace.source), (6, 2, "local observation"))
        client.lua.execute('''
            now = 120
            CombatLogGetCurrentEventInfo = function()
                return 0, "UNIT_DIED", false, nil, nil, nil, nil,
                    "Creature-0-0-0-0-123-00000004"
            end
        ''')
        observations.CombatLog()
        self.assertEqual(pace.sampleSize, 3)

    def test_loot_uses_looted_corpses_as_drop_denominator(self):
        _, observations, private = observation_client()
        first, second = GUID, GUID[:-1] + "2"
        self.assertTrue(observations.RecordLoot(first, 42, 2, "local observation"))
        self.assertTrue(observations.RecordLoot(first, 42, 2, "local observation"))
        self.assertTrue(observations.RecordLoot(first, 43, 1, "local observation"))
        self.assertTrue(observations.RecordLoot(second, 43, 1, "local observation"))
        record = private.db.observations["70009"].mobs[123]
        self.assertEqual(record.looted, 2)
        self.assertEqual((record.drops[42].n, record.drops[42].total,
                          record.drops[42].sampleSize), (1, 2, 2))
        self.assertEqual((record.drops[43].n, record.drops[43].sampleSize), (2, 2))
        self.assertEqual(record.drops[42].source, "local observation")

    def test_gathering_visits_and_dungeon_run_are_recorded(self):
        client, observations, private = observation_client()
        observations.RecordGatherCast("player", "Mining", 77)
        self.assertTrue(observations.RecordLoot(NODE, 42, 2, "local observation"))
        self.assertTrue(observations.RecordLoot(NODE, 43, 1, "local observation"))
        observations.RecordGatherCast("player", "Mining", 77)
        self.assertTrue(observations.RecordLoot(NODE, 42, 1, "local observation"))
        node = private.db.observations["70009"].nodes[501][1]
        self.assertEqual((node.visits, node["items"][42].total,
                          node["items"][42].sampleSize), (2, 3, 2))
        client.lua.execute('''
            inside, instanceKind, instanceID = true, "party", 900
            C_Item = {GetItemInfo=function(id)
                return "Item", nil, 0, nil, nil, nil, nil, nil, nil, nil, 50
            end}
        ''')
        observations.CheckInstance()
        self.assertTrue(observations.RecordLoot(GUID, 42, 2, "local observation"))
        client.lua.execute('now = 220; inside, instanceKind = false, "none"')
        observations.CheckInstance()
        run = private.db.observations["70009"].runs[900][1]
        self.assertEqual((run.durationSeconds, run.lootCopper, run.pricedItems,
                          run.totalItems, run.memberCount), (120, 100, 2, 2, 2))
        self.assertEqual((run.source, run.sampleSize), ("local observation", 1))

    def test_m_packets_are_versioned_deduplicated_and_separate(self):
        client, observations, private = observation_client()
        observations.RecordLoot(GUID, 42, 2, "local observation")
        packet = observations.DropPacket(123, 42)
        self.assertTrue(packet.startswith("1|M|D|"))
        self.assertFalse(observations.ReceiveM(packet)[0])
        other = "1|M|D|deadbeef|123|42|4|2|3|1"
        self.assertTrue(observations.ReceiveM(other))
        self.assertFalse(observations.ReceiveM(other)[0])
        peer = private.db.observations["70009"].peers["deadbeef"][123]
        self.assertEqual((peer.drops[42].n, peer.drops[42].sampleSize,
                          peer.drops[42].source), (2, 4, "party observation"))
        self.assertEqual(private.db.observations["70009"].mobs[123].looted, 1)
        self.assertFalse(observations.ReceiveM("1|M|D|deadbeef|123|42|1|2|3|2")[0])
        self.assertEqual(client.ns.ReceivePartyPlanMessage(other, "Bob-Test Realm")[0], True)

    def test_research_export_includes_provenance_and_sample_size(self):
        client, observations, _ = observation_client()
        observations.RecordLoot(GUID, 42, 1, "local observation")
        observations.RecordGatherCast("player", "Mining", 77)
        observations.RecordLoot(NODE, 43, 2, "local observation")
        events = observations.ExportEvents()
        drop = events[1]
        self.assertEqual((drop.event, drop.npcID, drop.itemID, drop.sampleSize,
                          drop.provenance), ("gold-drop", 123, 42, 1, "local observation"))
        exported = json.loads(client.ns.ExportQuestResearch())
        node = next(row for row in exported["events"] if row["event"] == "gold-node")
        self.assertEqual(node["items"][0]["itemID"], 43)
        self.assertEqual(node["items"][0]["sampleSize"], 1)

    def test_ingester_preserves_sample_basis_and_deduplicates_exports(self):
        client, observations, _ = observation_client()
        observations.RecordLoot(GUID, 42, 2, "local observation")
        document = client.ns.ExportQuestResearch()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tester.json"
            path.write_text(document)
            rows = load_exports([path, path])
        result = ingest(rows)
        self.assertEqual(result["candidateCount"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["kind"], "gold-drop")
        self.assertEqual(candidate["facts"]["looted"], 1)
        self.assertEqual(candidate["facts"]["dropRate"], 1)
        self.assertEqual(candidate["sampleSize"], 1)
        self.assertEqual(candidate["provenance"], ["local observation"])
        bad = dict(rows[0], looted=0)
        self.assertEqual(ingest([bad])["candidateCount"], 0)


if __name__ == "__main__":
    unittest.main()
