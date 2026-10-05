"""Read-only in-game Lua checks and bounded, public output formatting."""
import unittest
from test_addon import Client
from test_050 import solo


def console_client(measurement=True):
    """Model the EditBox method boundary and native SetText callbacks."""
    c = solo()
    c.lua.globals().consoleMeasurement = measurement
    c.lua.execute(r'''
    local create = CreateFrame
    function CreateFrame(kind, ...)
        local widget = create(kind, ...)
        local createFontString = widget.CreateFontString
        function widget:CreateFontString(...)
            local font = createFontString(self, ...)
            if consoleMeasurement then
                function font:GetStringHeight()
                    local text = self.text or ''
                    if text == '' then return 0 end
                    local columns = math.max(1, math.floor((self.width or 692) / 7))
                    local lines = 0
                    for line in (text .. '\n'):gmatch('(.-)\n') do
                        lines = lines + math.max(1, math.ceil(#line / columns))
                    end
                    return lines * 14
                end
            else
                local inherited = getmetatable(font).__index
                setmetatable(font, {__index=function(_, key)
                    if key ~= 'GetStringHeight' then return inherited[key] end
                end})
            end
            return font
        end
        if kind == 'EditBox' then
            local inherited = getmetatable(widget).__index
            setmetatable(widget, {__index=function(_, key)
                if key ~= 'GetStringHeight' and key ~= 'GetTextHeight' then return inherited[key] end
            end})
            function widget:SetText(text)
                self.text = text
                self.textChanges = (self.textChanges or 0) + 1
                if self.OnTextChanged then self.OnTextChanged(self, false) end
            end
        end
        if kind == 'ScrollFrame' then
            function widget:UpdateScrollChildRect() self.scrollUpdates = (self.scrollUpdates or 0) + 1 end
        end
        return widget
    end
    ''')
    return c


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
        c = console_client()
        c.lua.globals().SlashCmdList.WOWTOGETHER('lua')
        frame = c.ns.luaConsole
        self.assertTrue(frame)
        self.assertIsNone(frame.input.GetStringHeight)
        self.assertIsNone(frame.output.GetStringHeight)
        self.assertEqual(frame.input.GetText(frame.input), 'return GetBuildInfo()')
        self.assertIn('Results stay here', frame.output.GetText(frame.output))
        self.assertIn('WowTogetherLuaConsole', c.lua.globals().UISpecialFrames.values())
        frame.input.SetText(frame.input, 'return 7')
        frame.run.OnClick()
        self.assertEqual(frame.output.GetText(frame.output), 'Return 1: 7')

    def test_wrapped_paste_and_multiline_results_grow_scroll_children_and_clear_shrinks(self):
        c = console_client()
        c.ns.ShowLuaConsole()
        frame = c.ns.luaConsole
        frame.input.SetText(frame.input, '-- ' + 'a' * 3000 + '\nreturn 7')
        self.assertGreater(frame.input.height, 180)
        self.assertEqual(frame.input.parent.height, 180)
        self.assertGreater(frame.input.parent.scrollUpdates, 0)
        frame.run.OnClick()
        self.assertEqual(frame.output.text, 'Return 1: 7')
        frame.input.SetText(frame.input, 'print(string.rep("x\\n", 100)); return 7')
        self.assertEqual(frame.input.height, 180)
        frame.run.OnClick()
        self.assertGreater(frame.output.height, 272)
        self.assertEqual(frame.output.parent.height, 272)
        self.assertGreater(frame.output.parent.scrollUpdates, 0)
        frame.output.SetText(frame.output, '')
        self.assertEqual(frame.output.height, 272)
        frame.Hide(frame)
        c.ns.ShowLuaConsole()
        self.assertTrue(frame.shown)
        self.assertEqual(frame.output.text, '')

    def test_missing_text_measurement_does_not_break_open_paste_or_run(self):
        c = console_client(measurement=False)
        c.ns.ShowLuaConsole()
        frame = c.ns.luaConsole
        frame.input.SetText(frame.input, 'return 7')
        frame.run.OnClick()
        self.assertEqual(frame.output.text, 'Return 1: 7')
        self.assertEqual(frame.input.height, 180)
        self.assertEqual(frame.output.height, 272)


if __name__ == '__main__':
    unittest.main()
