"""The shipped optional farm package keeps one legacy zone per creature."""
import unittest
from test_addon import Client


class FarmPriorDataTests(unittest.TestCase):
    def test_real_package_uses_one_majority_zone_and_retains_skinning_yields(self):
        c = Client(quests=(), default_guide=True)
        self.assertTrue(c.ns.EnsureOptionalData("WowTogether_GoldData"))
        data = c.ns.farmPriorData
        self.assertGreater(data.count, 1000)
        count, duplicates = c.lua.eval(r'''
            function(data)
                local seen, count, duplicates = {}, 0, 0
                for index = 1, data.count do
                    local row = data.records[index]
                    count = count + 1
                    if seen[row.npcID] then duplicates = duplicates + 1 end
                    seen[row.npcID] = true
                end
                return count, duplicates
            end
        ''')(data)
        self.assertEqual(count, data.count)
        self.assertEqual(duplicates, 0)

        flesh_eater = data.records[1]
        self.assertEqual((flesh_eater.npcID, flesh_eater.name, flesh_eater.mapID, flesh_eater.zoneName),
                         (3, "Flesh Eater", 1431, "Duskwood"))
        boar = next(data.records[index] for index in range(1, data.count + 1)
                    if data.records[index].npcID == 113)
        self.assertTrue(boar.skinnable)
        self.assertIn(2318, {boar.skinningLoot[index].itemID for index in range(1, len(boar.skinningLoot) + 1)})

    def test_skinning_yields_join_the_creature_farm_for_a_character_with_skinning(self):
        c = Client(quests=(), default_guide=True)
        c.lua.execute('''
            UnitLevel = function() return 5 end
            ticks = 0
            function debugprofilestop() ticks = ticks + 0.1; return ticks end
            farmFilter = {minLevel = 5, maxLevel = 10, mapID = 1429, limit = 50}
            function saveFarmRows(rows) farmRows = rows end
        ''')
        c.ns.profile.level = 5
        c.ns.gatheringData[393] = c.lua.table_from({"skill": 1}, recursive=True)
        api = c.lua.globals().WowTogetherModuleAPI
        self.assertTrue(api.FarmPriorSearch(c.lua.globals().farmFilter, c.lua.globals().saveFarmRows))
        c.drain()
        rows = c.lua.globals().farmRows
        boar = next(rows[index] for index in range(1, len(rows) + 1) if rows[index].npcID == 113)
        self.assertTrue(boar.skinnable)
        loot = {boar.loot[index].itemID for index in range(1, len(boar.loot) + 1)}
        self.assertTrue({2318, 2934}.issubset(loot))

    def test_skinning_yields_are_omitted_when_the_character_has_not_learned_skinning(self):
        c = Client(quests=(), default_guide=True)
        c.lua.execute('''
            UnitLevel = function() return 5 end
            ticks = 0
            function debugprofilestop() ticks = ticks + 0.1; return ticks end
            farmFilter = {minLevel = 5, maxLevel = 10, mapID = 1429, limit = 50}
            function saveFarmRows(rows) farmRows = rows end
        ''')
        api = c.lua.globals().WowTogetherModuleAPI
        self.assertTrue(api.FarmPriorSearch(c.lua.globals().farmFilter, c.lua.globals().saveFarmRows))
        c.drain()
        rows = c.lua.globals().farmRows
        boar = next(rows[index] for index in range(1, len(rows) + 1) if rows[index].npcID == 113)
        loot = {boar.loot[index].itemID for index in range(1, len(boar.loot) + 1)}
        self.assertFalse({2318, 2934} & loot)


if __name__ == "__main__":
    unittest.main()
