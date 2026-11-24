"""Cleaning the quest log of quests no longer worth doing."""
import unittest

from test_leveling_path import scene, drain

SETUP = '''
local ns = ...
abandoned, selected, marked, combat = {}, 0, 0, false
function InCombatLockdown() return combat end
C_QuestLog.GetLogIndexForQuestID = function(id) return ns.active[id] and 1 or nil end
C_QuestLog.GetSelectedQuest = function() return selected end
C_QuestLog.SetSelectedQuest = function(id) selected = id end
C_QuestLog.SetAbandonQuest = function() marked = selected end
C_QuestLog.AbandonQuest = function() abandoned[#abandoned + 1] = marked; ns.active[marked] = nil end
ns.ReadQuests = function() end
function inLog(id, have, need)
    ns.active[id] = {id = id}
    ns.localProgress[id] = {objectives = {{have = have, need = need}}}
end
-- Quests of the catalogue by kind, for a level 32 character.
function pick()
    local grey, current, dungeon = {}, nil, nil
    local ids = {}
    for id in pairs(ns.catalogue.quests) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do
        local quest = ns.catalogue.quests[id]
        local level = quest.level or 0
        local plain = type(quest.xp) == "number" and quest.xp > 0 and ns.CatalogueIdentityAllowed(id, ns.profile) == true
            and not ns.IsRepeatableQuest(id) and not ns.IsProfessionQuest(id) and not ns.IsClassQuest(id)
        if plain and not ns.IsDungeonQuest(id) and level >= 8 and level <= 14 and #grey < 4 and ns.LevelingValue(id) == false then grey[#grey + 1] = id end
        if plain and not ns.IsDungeonQuest(id) and level >= 31 and level <= 33 and not current then current = id end
        if plain and ns.IsDungeonQuest(id) and level >= 8 and level <= 16 and not dungeon then dungeon = id end
    end
    return grey, current, dungeon
end
'''


def cleaner(mode='ask'):
    c = scene(32, 0.3); ns = c.ns
    drain(c)
    ns.SetOption('questCleanup', mode)
    c.lua.execute(SETUP, ns)
    grey, current, dungeon = c.lua.globals().pick()
    grey = list(grey.values())
    return c, grey, current, dungeon


def offered(c):
    return [quest.id for quest in c.ns.UselessQuests().values()]


class WhatCountsAsUselessTests(unittest.TestCase):
    def test_only_low_value_unfinished_ordinary_quests_are_offered(self):
        c, grey, current, dungeon = cleaner(); ns = c.ns; g = c.lua.globals()
        self.assertGreaterEqual(len(grey), 3)
        g.inLog(grey[0], 2, 10)              # Grey, barely started: goes.
        g.inLog(grey[1], 9, 10)              # Grey but 90% done: stays.
        g.inLog(grey[2], 10, 10)             # Grey but finished: stays, to be turned in.
        g.inLog(current, 0, 10)              # A quest of the character's own level: stays.
        if dungeon:
            g.inLog(dungeon, 0, 10)          # A dungeon quest: never touched.
        g.inLog(999999999, 0, 10)            # Unknown to the catalogue: never touched.
        self.assertEqual(offered(c), [grey[0]])
        ns.SetOption('finishNearlyDone', 'off')
        self.assertEqual(sorted(offered(c)), sorted([grey[0], grey[1]]))   # Without that setting 90% is not protected.
        ns.SetOption('finishNearlyDone', '85')
        ns.KeepLowValueQuest(grey[0])
        self.assertEqual(offered(c), [])     # The player's own "keep" is respected.


class AskFirstTests(unittest.TestCase):
    def test_a_level_up_asks_with_the_list_and_abandons_nothing_until_answered(self):
        c, grey, current, dungeon = cleaner(); ns = c.ns; g = c.lua.globals()
        g.inLog(grey[0], 2, 10); g.inLog(grey[1], 0, 5); g.inLog(current, 0, 10)
        ns.frame.OnEvent(ns.frame, "PLAYER_LEVEL_UP", 32); drain(c)
        prompt = ns.questCleanupPrompt
        self.assertTrue(prompt.IsShown(prompt))
        self.assertEqual(prompt.title.text, 'Abandon 2 quests no longer worth doing?')
        self.assertIn(ns.QuestTitle(grey[0]), prompt.body.text)
        self.assertIn('XP now', prompt.body.text)
        self.assertIn('cannot be undone', prompt.body.text)
        self.assertEqual(len(list(g.abandoned.values())), 0)
        prompt.yes.OnClick(); drain(c)
        self.assertEqual(sorted(g.abandoned.values()), sorted([grey[0], grey[1]]))
        self.assertIsNotNone(ns.active[current])                      # The useful quest is untouched.
        self.assertIn('Abandoned 2 quests no longer worth doing', list(g.printed.values())[-1])

    def test_keep_them_is_remembered_and_the_command_asks_afresh(self):
        c, grey, current, dungeon = cleaner(); ns = c.ns; g = c.lua.globals()
        g.inLog(grey[0], 2, 10)
        ns.QuestLogCleanup(False)
        ns.questCleanupPrompt.no.OnClick()
        self.assertEqual(ns.QuestLogCleanup(False), 0)                # Not offered again this session.
        self.assertFalse(ns.questCleanupPrompt.IsShown(ns.questCleanupPrompt))
        self.assertEqual(ns.QuestLogCleanup(True), 1)                 # /wt clean looks at everything again.
        self.assertTrue(ns.questCleanupPrompt.IsShown(ns.questCleanupPrompt))
        self.assertEqual(len(list(g.abandoned.values())), 0)

    def test_nothing_happens_in_combat_or_when_there_is_nothing_to_clean(self):
        c, grey, current, dungeon = cleaner(); ns = c.ns; g = c.lua.globals()
        g.inLog(current, 0, 10)
        self.assertEqual(ns.QuestLogCleanup(True), 0)
        self.assertIn('Nothing to clean', list(g.printed.values())[-1])
        g.inLog(grey[0], 2, 10)
        g.combat = True
        self.assertEqual(ns.QuestLogCleanup(True), 0)
        self.assertIn('Leave combat', list(g.printed.values())[-1])
        self.assertFalse(ns.AbandonQuests(ns.UselessQuests()))
        self.assertEqual(len(list(g.abandoned.values())), 0)


class SettingTests(unittest.TestCase):
    def test_automatic_abandons_after_a_level_up_and_says_what_went(self):
        c, grey, current, dungeon = cleaner('auto'); ns = c.ns; g = c.lua.globals()
        g.inLog(grey[0], 2, 10); g.inLog(grey[1], 9, 10)
        ns.frame.OnEvent(ns.frame, "PLAYER_LEVEL_UP", 32); drain(c)
        self.assertEqual(list(g.abandoned.values()), [grey[0]])       # The nearly finished one is still kept.
        self.assertIn('Abandoned 1 quest no longer worth doing: ' + ns.QuestTitle(grey[0]), list(g.printed.values())[-1])
        self.assertTrue(ns.questCleanupPrompt is None or not ns.questCleanupPrompt.IsShown(ns.questCleanupPrompt))

    def test_off_does_nothing_on_its_own_but_the_command_still_works(self):
        c, grey, current, dungeon = cleaner('off'); ns = c.ns; g = c.lua.globals()
        g.inLog(grey[0], 2, 10)
        ns.frame.OnEvent(ns.frame, "PLAYER_LEVEL_UP", 32); drain(c)
        self.assertEqual(len(list(g.abandoned.values())), 0)
        self.assertIsNone(ns.questCleanupPrompt)
        self.assertEqual(ns.QuestLogCleanup(True), 1)

    def test_always_clean_switches_the_setting_and_asking_is_the_default(self):
        c, grey, current, dungeon = cleaner(); ns = c.ns; g = c.lua.globals()
        self.assertEqual(scene(32, 0.3).ns.Option('questCleanup'), 'ask')
        g.inLog(grey[0], 2, 10)
        ns.QuestLogCleanup(False)
        ns.questCleanupPrompt.always.OnClick(); drain(c)
        self.assertEqual(ns.Option('questCleanup'), 'auto')
        self.assertEqual(list(g.abandoned.values()), [grey[0]])


if __name__ == '__main__':
    unittest.main()
