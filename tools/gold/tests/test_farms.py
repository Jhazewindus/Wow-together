"""Gold candidates, player-started routes, and measured session rates."""
import sys
import unittest
from pathlib import Path

from test_skeleton import ROOT, load_gold
from test_addon import Client


def load_component(client, private, name):
    source = (ROOT / "WowTogether_Gold" / name).read_text()
    client.lua.execute("assert(loadstring(...))(select(2, ...))", source, "WowTogether_Gold", private)


def farm_client():
    client = Client(quests=(), default_guide=True)
    client.lua.execute('''
        seconds = 1000
        UnitLevel = function() return 20 end
        GetTime = function() return seconds end
        C_Item = {GetItemInfo=function(id)
            return "Item", nil, 2, nil, nil, nil, nil, nil, nil, nil, 40
        end}
    ''')
    private = load_gold(client)
    load_component(client, private, "GoldPrices.lua")
    load_component(client, private, "GoldObservations.lua")
    client.lua.execute('''
        local api = WowTogetherModuleAPI
        api.AuctionQuote = function(id) quoteCalls = (quoteCalls or 0)+1; return 100, 0 end
        api.FarmPriorSearch = function(filter, done)
            assert(filter.minLevel == 15 and filter.maxLevel == 25 and filter.limit == 50)
            priorCalls = (priorCalls or 0)+1
            done({{npcID=22,name="Legacy boar",minLevel=18,maxLevel=20,mapID=501,zoneName="Test Zone",
                spawnPoints={{mapID=501,x=.2,y=.2},{mapID=501,x=.4,y=.2},{mapID=501,x=.4,y=.4}},
                loot={{itemID=42,chance=25,minYield=1,maxYield=1,source="legacy table, unconfirmed"}},
                sources={loot="legacy loot table",spawnPoints="legacy spawn table"}}})
            return true
        end
        api.GatheringFarmSearch = function(filter, done)
            assert(filter.limit == 50)
            gatheringCalls = (gatheringCalls or 0)+1
            done({
                {profession="Mining",professionID=186,node="Copper Vein",requiredSkill=1,ownSkill=65,
                    loot={{itemID=2770,chance=100,minYield=1,maxYield=3,source="seeded node yield"}},
                    zones={{mapID=502,name="Copper Coast",points={{mapID=502,x=.2,y=.2},{mapID=502,x=.4,y=.2},{mapID=502,x=.4,y=.4}}}}},
                {profession="Fishing",professionID=356,node="Tier 1 pool",requiredSkill=1,ownSkill=75,
                    loot={{itemID=6291,chance=100,averageYield=2,source="seeded local catch"}},
                    zones={{mapID=503,name="Redridge",points={{mapID=503,x=.2,y=.2},{mapID=503,x=.4,y=.2},{mapID=503,x=.4,y=.4}}}}
                }
            })
            return true
        end
        loopSpecs, sessionRows = {}, {}
        api.StartModuleLoop = function(module, spec)
            loopSpecs[#loopSpecs+1] = spec
            spec.onStart()
            return true
        end
        api.SetFarmSession = function(module, data)
            sessionRows[#sessionRows+1] = data
            currentSession = data
            return true
        end
        api.RequestFarmSessionRefresh = function(module) refreshCalls=(refreshCalls or 0)+1; return true end
    ''')
    load_component(client, private, "GoldFarms.lua")
    return client, private


class GoldFarmTests(unittest.TestCase):
    def test_both_searches_feed_three_ranked_hub_cards_with_explicit_estimate_basis(self):
        client, private = farm_client()
        ns = client.ns
        self.assertEqual((client.lua.globals().priorCalls, client.lua.globals().gatheringCalls), (1, 1))
        values = ns.FirstHook("goldSuggestions")
        handled, cards = values[0], values[1]
        self.assertTrue(handled)
        self.assertEqual(len(cards), 3)
        titles = [cards[i].title for i in range(1, 4)]
        self.assertTrue(any("Legacy boar" in title for title in titles))
        self.assertTrue(any("Copper Vein" in title and "Copper Coast" in title for title in titles))
        self.assertTrue(any("Tier 1 pool" in title and "Redridge" in title for title in titles))
        prior = next(cards[i] for i in range(1, 4) if "Legacy boar" in cards[i].title)
        self.assertIn("Legacy, unconfirmed", prior.detail)
        self.assertIn("120 kills/hour assumed", prior.detail)
        self.assertIn("25%", prior.detail)
        self.assertIn("core auction quote", prior.detail)

    def test_start_uses_loop_and_only_starts_the_measured_clock_after_acceptance(self):
        client, private = farm_client()
        client.lua.execute('''
            WowTogetherModuleAPI.StartModuleLoop = function(module, spec)
                pendingLoop = spec
                return true, "Waiting for confirmation."
            end
        ''')
        cards = client.ns.FirstHook("goldSuggestions")[1]
        prior = next(cards[i] for i in range(1, 4) if "Legacy boar" in cards[i].title)
        prior.start()
        spec = client.lua.globals().pendingLoop
        self.assertEqual(spec.title, "Legacy boar — Test Zone")
        self.assertEqual(len(spec.points), 3)
        self.assertEqual(len(client.lua.globals().sessionRows), 0)
        spec.onStart()
        self.assertIsNotNone(private.GoldFarms)
        self.assertEqual(client.lua.globals().sessionRows[1].startTime, 1000)

    def test_observed_loot_updates_actual_rate_and_card_basis(self):
        client, private = farm_client()
        cards = client.ns.FirstHook("goldSuggestions")[1]
        prior = next(cards[i] for i in range(1, 4) if "Legacy boar" in cards[i].title)
        prior.start()
        client.lua.globals().seconds = 2200
        private.GoldFarms.RecordLoot(42, 5, 22)
        session = client.lua.globals().currentSession
        self.assertEqual(session.estimatedCopperPerHour, 3000)
        self.assertEqual(session.actualCopperPerHour, 1500)
        self.assertIn("5 locally looted/gathered items", session.actualBasis)
        self.assertIn("core auction quote", session.actualBasis)
        self.assertEqual(client.lua.globals().refreshCalls, 2)

    def test_gathering_observer_learns_real_spots_and_measures_catches(self):
        client, private = farm_client()
        client.lua.execute('seconds=1300')
        client.ns.RunHooks("gatheringObserved", client.lua.table_from({
            "professionID": 356, "profession": "Fishing", "mapID": 503,
            "x": .2, "y": .2, "itemID": 6291, "quantity": 2,
            "source": "fishing-pool", "observedAt": 1300}))
        row = private.db.gathering["Fishing:503:fishing-pool"]
        self.assertEqual((len(row.points), row.points[1].x, row["items"][6291].total), (1, .2, 2))
        client.lua.globals().seconds = 1310
        client.ns.RunHooks("gatheringObserved", client.lua.table_from({
            "professionID": 356, "profession": "Fishing", "mapID": 503,
            "x": .2, "y": .2, "itemID": 6291, "quantity": 1,
            "source": "fishing-catch", "observedAt": 1310}))
        open_water = private.db.gathering["Fishing:503:open-water"]
        self.assertEqual(open_water["items"][6291].total, 1)
        self.assertTrue(private.GoldFarms.Probe)


if __name__ == "__main__":
    unittest.main()
