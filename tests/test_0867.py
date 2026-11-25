"""Numeric status text under host API simulation."""
import unittest

from test_addon import Client


CVARS = r'''
combat=false
statusValues={statusText='0',statusTextDisplay='PERCENT'}
function InCombatLockdown()return combat end
C_CVar={GetCVar=function(key)return statusValues[key]end,
 SetCVar=function(key,value)statusValues[key]=value end}
'''


class UnitNumbersTests(unittest.TestCase):
    def client(self):
        return Client(before_load=CVARS)

    def test_enable_uses_blizzard_numeric_mode_and_disable_restores_prior_choices(self):
        c = self.client()
        c.ns.SetOption('unitNumbers', True)
        self.assertEqual(c.lua.globals().statusValues.statusText, '1')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'NUMERIC')
        c.ns.SetOption('unitNumbers', False)
        self.assertEqual(c.lua.globals().statusValues.statusText, '0')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'PERCENT')

    def test_turn_off_preserves_native_settings_changed_by_player_while_enabled(self):
        c = self.client()
        c.ns.SetOption('unitNumbers', True)
        c.lua.execute("statusValues.statusTextDisplay='BOTH'")
        c.ns.SetOption('unitNumbers', False)
        self.assertEqual(c.lua.globals().statusValues.statusText, '0')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'BOTH')

    def test_combat_defers_cvar_writes_until_combat_ends(self):
        c = self.client()
        c.lua.globals().combat = True
        c.ns.SetOption('unitNumbers', True)
        self.assertEqual(c.lua.globals().statusValues.statusText, '0')
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertEqual(c.lua.globals().statusValues.statusText, '1')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'NUMERIC')
