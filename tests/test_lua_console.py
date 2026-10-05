"""Read-only in-game Lua checks and bounded, public output formatting."""
import unittest
from test_addon import Client
from test_050 import solo


class LuaConsoleTests(unittest.TestCase):
    def test_multiple_returns_preserve_nil_and_do_not_send_or_print_to_chat(self):
        c = solo()
        logs, sends = len(c.lua.globals().logs), len(c.lua.globals().sent)
        result = c.ns.RunLuaInspection('return 12, nil, false, "ok", nil')
        self.assertIn('Return 2: nil', result)
        self.assertIn('Return 3: false', result)
        self.assertIn('Return 5: nil', result)
        self.assertEqual(len(c.lua.globals().logs), logs)
        self.assertEqual(len(c.lua.globals().sent), sends)

    def test_locals_assert_print_and_nested_api_tables(self):
        c = solo()
        c.lua.execute('C_GossipInfo={GetAvailableQuests=function() return {{questID=900,title="Offered"}} end}')
        result = c.ns.RunLuaInspection('local q=C_GossipInfo.GetAvailableQuests(); assert(q[1].questID==900); print(q); return #q')
        self.assertIn('["questID"] = 900', result)
        self.assertIn('["title"] = "Offered"', result)
        self.assertIn('Return 1: 1', result)

    def test_syntax_and_failed_assertions_are_shown_as_errors(self):
        c = solo()
        self.assertIn('Syntax error:', c.ns.RunLuaInspection('return ('))
        self.assertIn('Lua error:', c.ns.RunLuaInspection('assert(false,"test failed")'))
        self.assertIn('test failed', c.ns.RunLuaInspection('assert(false,"test failed")'))

    def test_secret_result_key_and_field_are_redacted_before_formatting(self):
        c = solo()
        c.lua.execute('UnitHealth=function() return secret end; C_QuestLog.GetInfo=function() return {[secret]="hidden key",health=secret,questID=900} end')
        result = c.ns.RunLuaInspection('return UnitHealth("player"), C_QuestLog.GetInfo(1)')
        self.assertIn('Return 1: <restricted>', result)
        self.assertIn('[<restricted>] = "hidden key"', result)
        self.assertIn('["health"] = <restricted>', result)
        self.assertNotIn('table:', result)

    def test_read_only_environment_has_no_action_frame_state_or_loader_access(self):
        c = solo()
        c.lua.execute('C_Map.SetUserWaypoint=function() error("must not call") end; AcceptQuest=function() error("must not call") end')
        result = c.ns.RunLuaInspection('return type(AcceptQuest),type(CreateFrame),type(loadstring),type(setfenv),type(_G),type(ns),type(C_Map.SetUserWaypoint)')
        self.assertEqual(result.count('"nil"'), 7)
        self.assertIn('Lua error:', c.ns.RunLuaInspection('C_Map.SetUserWaypoint({})'))
        self.assertIn('Read-only API table', c.ns.RunLuaInspection('C_Map.GetMapInfo=nil'))
        self.assertEqual(c.ns.RunLuaInspection('local a=7; return a'), 'Return 1: 7')
        self.assertEqual(c.ns.RunLuaInspection('return type(a)'), 'Return 1: "nil"')

    def test_capability_helper_reports_actual_functions_outside_callable_subset(self):
        c = solo()
        c.lua.execute('C_NamePlate={GetNamePlateForUnit=function() error("never called") end}; AcceptQuest=function() error("never called") end')
        result = c.ns.RunLuaInspection('return apiType("C_NamePlate.GetNamePlateForUnit"), apiType("AcceptQuest"),apiType("C_Missing.GetNothing")')
        self.assertEqual(result, 'Return 1: "function"\nReturn 2: "function"\nReturn 3: "nil"')

    def test_no_loops_or_recursion_but_keywords_in_quotes_comments_and_long_strings_work(self):
        c = solo()
        for code in ('while true do end','repeat until false','for i=1,10 do end','local f=function() return 1 end'):
            self.assertIn('straight-line', c.ns.RunLuaInspection(code))
        for code in ('return "while function for repeat"', '-- while true do end\nreturn "ok"', 'return [=[while "function" repeat for]=]', '--[=[repeat forever]=]\nreturn "ok"'):
            self.assertNotIn('straight-line', c.ns.RunLuaInspection(code))
        self.assertIn('String size limit', c.ns.RunLuaInspection('return string.rep("huge",10000000)'))

    def test_cycles_and_large_tables_have_bounded_outputs(self):
        c = solo()
        result = c.ns.RunLuaInspection('local t={}; t.self=t; return t')
        self.assertIn('<cycle>', result)
        c.lua.execute('huge={}; for i=1,5000 do huge[i]=string.rep("x",1000) end; C_QuestLog.GetInfo=function() return huge end')
        result = c.ns.RunLuaInspection('return C_QuestLog.GetInfo(1)')
        self.assertLessEqual(len(result), 24100)
        self.assertIn('truncated', result)

    def test_compiler_capability_and_combat_leave_checks_unexecuted(self):
        c = solo()
        c.lua.execute('loadstring=nil')
        self.assertIn('compilation is unavailable', c.ns.RunLuaInspection('return 1'))
        c.lua.globals().combat = True
        self.assertIn('outside combat', c.ns.RunLuaInspection('return 1'))

    def test_slash_command_opens_owned_paste_and_output_window(self):
        c = solo()
        c.lua.globals().SlashCmdList.WOWTOGETHER('lua')
        frame = c.ns.luaConsole
        self.assertTrue(frame)
        self.assertEqual(frame.input.GetText(frame.input), 'return GetBuildInfo()')
        self.assertIn('Results stay here', frame.output.GetText(frame.output))
        self.assertIn('WowTogetherLuaConsole', c.lua.globals().UISpecialFrames.values())
        frame.input.SetText(frame.input, 'return 7')
        frame.run.OnClick()
        self.assertEqual(frame.output.GetText(frame.output), 'Return 1: 7')


if __name__ == '__main__':
    unittest.main()
