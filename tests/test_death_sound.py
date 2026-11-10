"""Local death sound settings, feign-death guard and duplicate protection."""
import unittest

from test_addon import Client


def sound_client():
    c = Client()
    c.lua.execute('''
    deathClock = 100
    deathSoundCalls = {}
    isFeigningDeath = false
    function GetTime() return deathClock end
    function UnitIsFeignDeath(unit) return isFeigningDeath end
    function PlaySoundFile(path, channel)
        deathSoundCalls[#deathSoundCalls + 1] = {path, channel}
        return true, #deathSoundCalls
    end
    ''')
    return c


class DeathSoundTests(unittest.TestCase):
    def test_default_setting_plays_once_on_local_death_at_master_volume(self):
        c = sound_client()
        self.assertTrue(c.ns.Option('deathSound'))
        c.ns.handlers.PLAYER_DEAD()
        self.assertEqual(len(c.lua.globals().deathSoundCalls), 1)
        self.assertEqual(c.lua.globals().deathSoundCalls[1][1],
            'Interface\\AddOns\\WowTogether\\Media\\Sounds\\death.ogg')
        self.assertEqual(c.lua.globals().deathSoundCalls[1][2], 'Master')

    def test_setting_off_suppresses_playback(self):
        c = sound_client()
        c.ns.SetOption('deathSound', False)
        c.ns.handlers.PLAYER_DEAD()
        self.assertEqual(len(c.lua.globals().deathSoundCalls), 0)

    def test_feign_death_does_not_handle_the_later_real_death(self):
        c = sound_client()
        c.lua.globals().isFeigningDeath = True
        c.ns.handlers.PLAYER_DEAD()
        self.assertEqual(len(c.lua.globals().deathSoundCalls), 0)
        c.lua.globals().isFeigningDeath = False
        c.ns.handlers.PLAYER_DEAD()
        self.assertEqual(len(c.lua.globals().deathSoundCalls), 1)

    def test_duplicate_events_and_five_second_throttle_play_once(self):
        c = sound_client()
        c.ns.handlers.PLAYER_DEAD()
        c.lua.globals().deathClock = 101
        c.ns.handlers.PLAYER_DEAD()
        self.assertEqual(len(c.lua.globals().deathSoundCalls), 1)

        c.ns.handlers.PLAYER_ALIVE()
        c.lua.globals().deathClock = 104
        c.ns.handlers.PLAYER_DEAD()
        self.assertEqual(len(c.lua.globals().deathSoundCalls), 1)

        c.ns.handlers.PLAYER_ALIVE()
        c.lua.globals().deathClock = 105
        c.ns.handlers.PLAYER_DEAD()
        self.assertEqual(len(c.lua.globals().deathSoundCalls), 2)

    def test_probe_reports_setting_and_successful_play_count(self):
        c = sound_client()
        c.ns.handlers.PLAYER_DEAD()
        c.ns.handlers.PLAYER_ALIVE()
        c.lua.globals().deathClock = 106
        c.ns.handlers.PLAYER_DEAD()
        c.ns.handlers.PLAYER_ALIVE()
        c.lua.globals().deathClock = 112
        c.ns.handlers.PLAYER_DEAD()
        c.ns.Diagnostics()
        self.assertIn('Death sound: on (played 3 times this session)', c.ns.diagnosticsText.text)


if __name__ == '__main__':
    unittest.main()
