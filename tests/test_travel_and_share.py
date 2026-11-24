"""The clickable Hearthstone/teleport button and automatic quest sharing."""
import unittest

from test_addon import Client

RECORD = '''
local ns = ...
local button = ns.navigation.travelButton
button.attributes, button.attributeWrites = {}, 0
button.SetAttribute = function(self, key, value) self.attributes[key] = value; self.attributeWrites = self.attributeWrites + 1 end
combat = false
function InCombatLockdown() return combat end
function travelState(method, id, name, remaining)
    local leg = {method = method, name = name, to = {personal = {id = id, name = name, method = method, remaining = remaining or 0}}}
    return {visible = true, stop = {id = 1, kind = "travel", personalTransport = true, travelLeg = leg, label = "x"}}
end
'''


def card():
    c = Client(quests=(), default_guide=True)
    c.drain()
    c.lua.execute(RECORD, c.ns)
    return c


class TravelButtonTests(unittest.TestCase):
    def test_hearthstone_step_shows_a_secure_item_button(self):
        c = card(); ns = c.ns; g = c.lua.globals()
        button = ns.navigation.travelButton
        self.assertFalse(button.IsShown(button))
        self.assertTrue(ns.UpdateTravelButton(g.travelState("hearth", "HEARTH", "Orgrimmar")))
        self.assertTrue(button.IsShown(button))
        self.assertEqual(button.attributes.type, "item")
        self.assertEqual(button.attributes.item, "item:6948")
        self.assertIsNone(button.attributes.spell)
        self.assertEqual(button.caption.text, "Use Hearthstone to Orgrimmar")

    def test_teleport_step_shows_a_secure_spell_button_with_its_cooldown(self):
        c = card(); ns = c.ns; g = c.lua.globals()
        button = ns.navigation.travelButton
        ns.UpdateTravelButton(g.travelState("teleport", "TELEPORT_3567", "Teleport: Orgrimmar", 95))
        self.assertEqual((button.attributes.type, button.attributes.spell), ("spell", 3567))
        self.assertIsNone(button.attributes.item)
        self.assertTrue(button.caption.text.startswith("Cast Teleport: Orgrimmar (ready in "))

    def test_the_secure_click_handler_is_never_replaced(self):
        c = card()
        own = c.lua.eval('function(ns, name) return rawget(ns.navigation.travelButton, name) ~= nil end')
        self.assertFalse(own(c.ns, "OnClick"))     # Replacing OnClick would stop the template from acting on the click.
        self.assertTrue(own(c.ns, "PostClick"))    # The addon only observes the click.

    def test_nothing_about_the_button_changes_in_combat_and_it_catches_up_after(self):
        c = card(); ns = c.ns; g = c.lua.globals()
        button = ns.navigation.travelButton
        ns.UpdateTravelButton(g.travelState("hearth", "HEARTH", "Orgrimmar"))
        writes = button.attributeWrites
        g.combat = True
        ns.UpdateTravelButton(g.travelState("teleport", "TELEPORT_3563", "Teleport: Undercity"))
        self.assertEqual(button.attributeWrites, writes)             # Still the Hearthstone.
        self.assertEqual(button.attributes.type, "item")
        ns.UpdateTravelButton(c.lua.table_from({"visible": True, "stop": c.lua.table_from({"kind": "q"})}))
        self.assertTrue(button.IsShown(button))                       # Not hidden mid-fight either.
        self.assertTrue(button.stale)
        c.lua.execute('local ns = ...; scheduled = 0; local s = ns.ScheduleRefresh; ns.ScheduleRefresh = function(...) scheduled = scheduled + 1 end', ns)
        g.combat = False
        ns.frame.OnEvent(ns.frame, "PLAYER_REGEN_ENABLED")
        self.assertEqual(g.scheduled, 1)                              # Brought up to date when the fight ends.
        ns.UpdateTravelButton(g.travelState("teleport", "TELEPORT_3563", "Teleport: Undercity"))
        self.assertEqual((button.attributes.type, button.attributes.spell), ("spell", 3563))

    def test_other_steps_the_setting_and_unknown_teleports_hide_it(self):
        c = card(); ns = c.ns; g = c.lua.globals()
        button = ns.navigation.travelButton
        ns.UpdateTravelButton(g.travelState("hearth", "HEARTH", "Orgrimmar"))
        self.assertFalse(ns.UpdateTravelButton(c.lua.table_from({"visible": True, "stop": c.lua.table_from({"kind": "q"})})))
        self.assertFalse(button.IsShown(button))
        self.assertIsNone(button.attributes.type)                     # Cleared, so a stray click does nothing.
        self.assertFalse(ns.UpdateTravelButton(g.travelState("teleport", "SOMETHING_ELSE", "Mystery")))
        ns.SetOption("travelButton", False)
        self.assertFalse(ns.UpdateTravelButton(g.travelState("hearth", "HEARTH", "Orgrimmar")))
        ns.SetOption("travelButton", True)
        self.assertTrue(ns.UpdateTravelButton(g.travelState("hearth", "HEARTH", "Orgrimmar")))
        self.assertFalse(ns.UpdateTravelButton(g.travelState("ship", "BOAT", "Ratchet")))  # Boats are not a button.


LOG = '''
local ns = ...
pushed, selected, grouped, raid, party = {}, 0, true, false, {"Eli"}
zoneName, instanceName, inInstance = "Hillsbrad Foothills", nil, false
questLog = {
    {isHeader = true, title = "Hillsbrad Foothills"},
    {questID = 501, title = "Elixir of Pain", isHeader = false},
    {questID = 502, title = "Battle of Hillsbrad", isHeader = false},
    {isHeader = true, title = "Arathi Highlands"},
    {questID = 601, title = "Hammerfall", isHeader = false},
    {isHeader = true, title = "Razorfen Kraul"},
    {questID = 701, title = "Going, Going, Guano!", isHeader = false},
    {questID = 702, title = "A Vengeful Fate", isHeader = false},
}
pushable = {[501] = true, [502] = false, [601] = true, [701] = true, [702] = true}
C_QuestLog.GetNumQuestLogEntries = function() return #questLog end
C_QuestLog.GetInfo = function(index) return questLog[index] end
C_QuestLog.IsPushableQuest = function(id) return pushable[id] == true end
C_QuestLog.GetQuestsOnMap = function() return {} end
C_QuestLog.GetSelectedQuest = function() return selected end
C_QuestLog.SetSelectedQuest = function(id) selected = id end
function QuestLogPushQuest() pushed[#pushed + 1] = selected end
function IsInGroup() return grouped end
function IsInRaid() return raid end
function UnitExists(unit) local index = tonumber(string.match(unit, "^party(%d)$")); return index ~= nil and party[index] ~= nil end
function UnitName(unit) local index = tonumber(string.match(unit, "^party(%d)$")); return index and party[index] or "Me" end
function GetRealZoneText() return zoneName end
function GetZoneText() return zoneName end
function IsInInstance() return inInstance end
function GetInstanceInfo() return instanceName end
combat = false
function InCombatLockdown() return combat end
printed = {}
ns.Print = function(text) printed[#printed + 1] = text end
'''


def sharer(mode='area'):
    c = Client(quests=(), default_guide=True, party_mode='never',
               saved_variables={'config': {'autoShareQuests': mode, 'shareAskDefault': True}})
    c.drain()
    c.lua.execute(LOG, c.ns)
    c.lua.execute('timers = {}')
    return c


def run(c):
    for _ in range(200):
        if not len(c.lua.globals().timers):
            break
        c.lua.eval('function() local callback = table.remove(timers, 1); callback() end')()


def pushed(c):
    return list(c.lua.globals().pushed.values())


class QuestShareTests(unittest.TestCase):
    def test_zone_quests_that_can_be_shared_go_out_once_when_the_group_forms(self):
        c = sharer(); ns = c.ns
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE")
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE")            # Several roster events: one run.
        self.assertEqual(len(c.lua.globals().timers), 1)
        run(c)
        self.assertEqual(pushed(c), [501])                            # 502 cannot be shared; 601 and 70x belong elsewhere.
        self.assertEqual(list(c.lua.globals().printed.values()), ["Shared 1 quest with your party: Elixir of Pain."])
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(pushed(c), [501])                            # Same line-up: not offered again.

    def test_a_new_member_is_offered_the_quests_and_the_log_selection_is_put_back(self):
        c = sharer(); ns = c.ns
        c.lua.execute('selected = 601')
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(c.lua.globals().selected, 601)               # What the player had selected is restored.
        c.lua.execute('party = {"Eli", "Biggie"}')
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(pushed(c), [501, 501])

    def test_inside_a_dungeon_its_quests_are_shared(self):
        c = sharer(); ns = c.ns
        c.lua.execute('zoneName, instanceName, inInstance = "Razorfen Kraul", "Razorfen Kraul", true')
        ns.frame.OnEvent(ns.frame, "PLAYER_ENTERING_WORLD"); run(c)
        self.assertEqual(pushed(c), [701, 702])
        self.assertIn("Shared 2 quests", list(c.lua.globals().printed.values())[0])

    def test_quests_with_work_on_the_current_map_count_whatever_their_header(self):
        c = sharer(); ns = c.ns
        c.lua.execute('C_Map = C_Map or {}; C_Map.GetBestMapForUnit = function() return 1424 end; C_QuestLog.GetQuestsOnMap = function() return {{questID = 601}} end')
        self.assertEqual([quest.id for quest in ns.ShareableQuests().values()], [501, 601])

    def test_every_quest_setting_off_setting_raids_and_solo(self):
        c = sharer(); ns = c.ns
        ns.SetOption("autoShareQuests", "all")
        self.assertEqual([quest.id for quest in ns.ShareableQuests().values()], [501, 601, 701, 702])
        ns.SetOption("autoShareQuests", "off")
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(pushed(c), [])
        ns.SetOption("autoShareQuests", "area")
        c.lua.execute('raid = true')
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(pushed(c), [])                               # Never in a raid.
        c.lua.execute('raid = false; party = {}')
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(pushed(c), [])                               # Nobody to share with.

    def test_sharing_waits_for_combat_to_end(self):
        c = sharer(); ns = c.ns
        c.lua.execute('combat = true')
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE")
        for _ in range(3):
            c.lua.eval('function() local callback = table.remove(timers, 1); callback() end')()
        self.assertEqual(pushed(c), [])
        c.lua.execute('combat = false')
        run(c)
        self.assertEqual(pushed(c), [501])

    def test_the_share_command_offers_again_and_can_cover_every_quest(self):
        c = sharer(); ns = c.ns
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        ns.ShareQuestsCommand(""); run(c)
        self.assertEqual(pushed(c), [501, 501])
        ns.ShareQuestsCommand("all"); run(c)
        self.assertEqual(pushed(c)[2:], [501, 601, 701, 702])

    def test_a_client_without_quest_sharing_schedules_nothing(self):
        c = sharer(); ns = c.ns
        c.lua.execute('QuestLogPushQuest = nil')
        before = len(c.lua.globals().timers)
        ns.ScheduleQuestShare(1)
        self.assertEqual(len(c.lua.globals().timers), before)         # No timer of ours on such a client.
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(ns.questShareStats.runs, 0)


if __name__ == '__main__':
    unittest.main()


class ShareAskFirstTests(unittest.TestCase):
    """By default nothing is shared until the player says so, once per place."""

    def test_entering_a_zone_asks_and_shares_nothing_until_answered(self):
        c = sharer('ask'); ns = c.ns
        ns.frame.OnEvent(ns.frame, "ZONE_CHANGED_NEW_AREA"); run(c)
        self.assertEqual(pushed(c), [])                               # Nothing went out.
        prompt = ns.questSharePrompt
        self.assertTrue(prompt.IsShown(prompt))
        self.assertIn('Share 1 quest for Hillsbrad Foothills with your party?', prompt.text.text)
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertEqual(pushed(c), [])                               # Still waiting for the answer.

    def test_yes_shares_now_and_covers_quests_accepted_there_later(self):
        c = sharer('ask'); ns = c.ns
        ns.frame.OnEvent(ns.frame, "ZONE_CHANGED_NEW_AREA"); run(c)
        ns.questSharePrompt.yes.OnClick(); run(c)
        self.assertEqual(pushed(c), [501])
        self.assertFalse(ns.questSharePrompt.IsShown(ns.questSharePrompt))
        c.lua.execute('pushable[502] = true')                         # A new shareable quest in the same zone.
        ns.frame.OnEvent(ns.frame, "QUEST_ACCEPTED", 1, 502); run(c)
        self.assertEqual(pushed(c), [501, 502])                       # Shared without asking again.
        self.assertFalse(ns.questSharePrompt.IsShown(ns.questSharePrompt))

    def test_no_is_remembered_for_that_place_and_another_place_asks_again(self):
        c = sharer('ask'); ns = c.ns
        ns.frame.OnEvent(ns.frame, "ZONE_CHANGED_NEW_AREA"); run(c)
        ns.questSharePrompt.no.OnClick(); run(c)
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        ns.frame.OnEvent(ns.frame, "QUEST_ACCEPTED", 1, 501); run(c)
        self.assertEqual(pushed(c), [])
        self.assertFalse(ns.questSharePrompt.IsShown(ns.questSharePrompt))   # Not asked again here.
        c.lua.execute('zoneName, instanceName, inInstance = "Razorfen Kraul", "Razorfen Kraul", true')
        ns.frame.OnEvent(ns.frame, "PLAYER_ENTERING_WORLD"); run(c)
        self.assertTrue(ns.questSharePrompt.IsShown(ns.questSharePrompt))
        self.assertIn('Share 2 quests for Razorfen Kraul', ns.questSharePrompt.text.text)

    def test_always_switches_to_sharing_without_asking(self):
        c = sharer('ask'); ns = c.ns
        ns.frame.OnEvent(ns.frame, "ZONE_CHANGED_NEW_AREA"); run(c)
        ns.questSharePrompt.always.OnClick(); run(c)
        self.assertEqual(ns.Option('autoShareQuests'), 'area')
        self.assertEqual(pushed(c), [501])

    def test_the_question_waits_for_combat_goes_away_with_the_party_and_is_not_asked_for_nothing(self):
        c = sharer('ask'); ns = c.ns
        c.lua.execute('combat = true')
        ns.frame.OnEvent(ns.frame, "ZONE_CHANGED_NEW_AREA")
        for _ in range(2):
            c.lua.eval('function() local callback = table.remove(timers, 1); if callback then callback() end end')()
        self.assertTrue(ns.questSharePrompt is None or not ns.questSharePrompt.IsShown(ns.questSharePrompt))  # Not mid-fight.
        c.lua.execute('combat = false'); run(c)
        self.assertTrue(ns.questSharePrompt.IsShown(ns.questSharePrompt))
        c.lua.execute('party = {}')
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertFalse(ns.questSharePrompt.IsShown(ns.questSharePrompt))   # Alone again: nothing to ask.
        c.lua.execute('party = {"Eli"}; pushable = {}')
        ns.frame.OnEvent(ns.frame, "GROUP_ROSTER_UPDATE"); run(c)
        self.assertFalse(ns.questSharePrompt.IsShown(ns.questSharePrompt))   # Nothing shareable here: no question.

    def test_asking_is_the_default_and_an_earlier_share_everything_default_moves_once(self):
        fresh = Client(quests=(), default_guide=True, fresh_install=True)
        self.assertEqual(fresh.ns.Option('autoShareQuests'), 'ask')
        moved = Client(quests=(), default_guide=True, saved_variables={'config': {'autoShareQuests': 'area'}})
        self.assertEqual(moved.ns.Option('autoShareQuests'), 'ask')
        kept = Client(quests=(), default_guide=True, saved_variables={'config': {'autoShareQuests': 'area', 'shareAskDefault': True}})
        self.assertEqual(kept.ns.Option('autoShareQuests'), 'area')
