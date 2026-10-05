"""Host-side Lua 5.1 checks. These do not establish Forever client compatibility."""
import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MOCK = r'''
secret = {}
issecretvalue = function(v) return rawequal(v, secret) end
logs, timers, sent, delays = {}, {}, {}, {}
SlashCmdList = {}
UIParent = {}
Minimap = {}
UISpecialFrames = {}
function GetZoneText() return "Durotar" end
controlDown = false
function IsControlKeyDown() return controlDown end
DEFAULT_CHAT_FRAME = {AddMessage = function(_, msg) logs[#logs+1] = msg end}
local methods = {}
function methods:SetScript(name, callback) self[name] = callback end
function methods:CreateFontString() return setmetatable({}, {__index=methods}) end
function methods:CreateTexture() return setmetatable({}, {__index=methods}) end
function methods:CreateLine() return setmetatable({}, {__index=methods}) end
-- Mainline SimpleLineAPIDocumentation: relativePoint, relativeTo, offsetX, offsetY.
-- Line anchors do not have the additional anchor string accepted by SetPoint.
function methods:SetStartPoint(point, relativeTo, x, y, ...)
    assert(type(point)=='string' and type(x)=='number' and type(y)=='number' and select('#', ...)==0, 'four-argument line anchor required')
    self.startPoint = {point, relativeTo, x, y}
end
function methods:SetEndPoint(point, relativeTo, x, y, ...)
    assert(type(point)=='string' and type(x)=='number' and type(y)=='number' and select('#', ...)==0, 'four-argument line anchor required')
    self.endPoint = {point, relativeTo, x, y}
end
function methods:GetFrameLevel() return self.frameLevel or 0 end
function methods:SetFrameLevel(level) self.frameLevel = level end
function methods:SetParent(parent) self.parent = parent end
function methods:GetStringHeight() return 100 end
function methods:IsShown() return self.shown or false end
function methods:SetShown(value) self.shown = value end
function methods:Hide() self.shown = false end
function methods:Show() self.shown = true end
function methods:SetText(text) self.text = text end
function methods:GetText() return self.text end
function methods:SetPoint(...) self.point = {...} end
function methods:SetSize(width, height) self.width, self.height = width, height end
function methods:SetWidth(width) self.width = width end
function methods:SetHeight(height) self.height = height end
function methods:GetWidth() return self.width end
function methods:GetHeight() return self.height end
setmetatable(methods, {__index=function() return function() end end})
function CreateFrame() return setmetatable({}, {__index=methods}) end
function GetBuildInfo() return '1.60.1', '70009', 'test', 16001 end
WOW_PROJECT_ID, LE_EXPANSION_LEVEL_CURRENT = 1, 0
function GetRealmName() return 'Test Realm' end
function UnitFullName(unit)
    if unitNames then
        local parts = unitNames[unit]
        if parts then return parts[1], parts[2] end
        return nil
    end
    if unit == 'player' then return player, 'Test Realm' end
    if unit == 'party1' then return peer, 'Test Realm' end
end
grouped, raid = true, false
function IsInGroup() return grouped end
function IsInRaid() return raid end
C_Timer = {After=function(delay, fn) timers[#timers+1] = fn; delays[#delays+1] = delay end}
-- Deliberately arbitrary enum codes ensure the addon never hardcodes success=0.
Enum = {RegisterAddonMessagePrefixResult={Success=7, DuplicatePrefix=8, InvalidPrefix=9},
        SendAddonMessageResult={Success=7, AddonMessageThrottle=8, InvalidChatType=9}}
registrationResult, prefixConfirmed = 7, true
C_ChatInfo = {
 RegisterAddonMessagePrefix=function() return registrationResult end,
 IsAddonMessagePrefixRegistered=function() return prefixConfirmed end,
 SendAddonMessage=function(prefix, message, channel)
   assert(#message <= 255, 'oversized message')
   local result = 7
   if sendResults and #sendResults > 0 then result = table.remove(sendResults, 1) end
   sent[#sent+1] = {prefix, message, channel, result}
   return result
 end,
}
entries, finished = {}, {}
C_QuestLog = {
 GetNumQuestLogEntries=function() return #entries end,
 GetInfo=function(i) return entries[i] end,
 IsQuestFlaggedCompleted=function(id) return finished[id] or false end,
}
'''

class Client:
    def __init__(self, name='Alice', peer='Bob', quests=(1, 2), completed=(), default_guide=False, use_catalogue=False):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCK)
        g = self.lua.globals()
        g.player, g.peer = name, peer
        for i, quest in enumerate(quests, 1):
            g.entries[i] = self.lua.table_from({'questID': quest, 'title': f'Quest {quest}', 'isHeader': False})
        for quest in completed:
            g.finished[quest] = True
        self.ns = self.lua.table()
        toc = (ROOT / 'WowTogether/WowTogether.toc').read_text()
        for line in toc.splitlines():
            if line.endswith('.lua'):
                self.lua.execute('assert(loadstring(...))(select(2, ...))',
                                 (ROOT / 'WowTogether' / line).read_text(), 'WowTogether', self.ns)
        if not use_catalogue:
            self.ns.catalogue = self.lua.table_from({'count': 0, 'quests': self.lua.table()})
        self.ns.handlers.ADDON_LOADED('WowTogether')
        if not default_guide:
            self.ns.SetFilter('all')

    def guide_environment(self, level=5, current_quests_first=False):
        # Synthetic beta API data; these coordinates/NPCs are not a game database.
        self.lua.execute(r"""
        playerLevel = 5
        function UnitLevel() return playerLevel end
        function UnitFactionGroup() return 'Horde' end
        function UnitName(unit) if unit == 'npc' then return 'Guide NPC' end end
        combat = false
        function InCombatLockdown() return combat end
        C_Map = {
          GetBestMapForUnit=function() return 501 end,
          GetMapInfo=function(id) return {name=id == 501 and 'Test Coast' or 'Test Hills'} end,
          GetPlayerMapPosition=function() return {GetXY=function() return 0.21, 0.37 end} end,
          CanSetUserWaypointOnMap=function() return waypointAllowed ~= false end,
          SetUserWaypoint=function(point) waypoint = point; return waypointAccepted ~= false end,
        }
        UiMapPoint = {CreateFromCoordinates=function(map, x, y) return {map=map, x=x, y=y} end}
        WorldMapFrame = CreateFrame('Frame')
        function WorldMapFrame:SetMapID(map) self.mapID = map end
        questLevels = {}
        C_QuestLog.GetQuestDifficultyLevel=function(id) return questLevels[id] or 0 end
        """)
        self.lua.globals().playerLevel = level
        # Legacy discovery tests explicitly exercise the new-pickup mode.
        self.ns.db.config.currentQuestsFirst = current_quests_first
        self.ns.ReadGuide()

    def unit_names(self, names):
        self.lua.globals().unitNames = self.lua.table_from({
            unit: self.lua.table_from(parts) for unit, parts in names.items()
        })
        self.ns.UpdateRoster()

    def view_text(self):
        ui = self.ns.ui
        parts = [ui.status.text, ui.party.text, ui.hint.text]
        for i in range(1, ui.visibleCards + 1):
            card = ui.cards[i]
            parts += [card.category.text, card.title.text]
            if card.reason.IsShown(card.reason):
                parts.append(card.reason.text)
            for j in range(1, len(card.memberCells) + 1):
                cell = card.memberCells[j]
                if cell.IsShown(cell):
                    parts.append(f'{cell.name.text}: {cell.state.text} ({cell.history.text})')
        return '\n'.join(parts)

    def receive(self, message, sender='Bob-TestRealm', channel='PARTY'):
        self.ns.Receive('WowTogetherV1', message, channel, sender)

    def drain(self, include_results=False):
        g = self.lua.globals()
        count = 0
        while len(g.timers):
            fn = g.timers[1]
            self.lua.eval('table.remove')(g.timers, 1)
            fn()
            count += 1
            assert count < 1000, 'timer loop'
        width = 4 if include_results else 3
        result = [tuple(g.sent[i][j] for j in range(1, width + 1)) for i in range(1, len(g.sent)+1)]
        g.sent = self.lua.table()
        return result

class AddonTests(unittest.TestCase):
    def test_load_and_saved_variables(self):
        c = Client()
        self.assertEqual(c.lua.globals().WowTogetherDB.version, 1)
        self.assertTrue(c.ns.questReady)
        self.assertEqual(c.ns.active[1], 'Quest 1')
        chat_count = len(c.lua.globals().logs)
        c.ns.Diagnostics()
        self.assertTrue(c.ns.diagnosticsWindow.IsShown(c.ns.diagnosticsWindow))
        self.assertIn('70009', c.ns.diagnosticsText.text)
        self.assertIn('C_QuestLog.GetInfo: present', c.ns.diagnosticsText.text)
        self.assertEqual(len(c.lua.globals().logs), chat_count)
        c.lua.globals().C_QuestLog.GetInfo = None
        c.ns.Diagnostics()
        self.assertIn('C_QuestLog.GetInfo: missing', c.ns.diagnosticsText.text)
        self.assertEqual(len(c.lua.globals().logs), chat_count)

    def test_modern_registration_and_send_diagnostics(self):
        c = Client()
        self.assertTrue(c.ns.syncReady)
        self.assertEqual(c.ns.syncStats.registration, 'Success (7)')
        c.ns.SyncNow()
        c.drain()
        c.ns.Diagnostics()
        self.assertIn('Prefix confirmation: true', c.ns.diagnosticsText.text)
        self.assertIn('Last send result: Success (7)', c.ns.diagnosticsText.text)
        self.assertGreater(c.ns.syncStats.sendAttempts, 0)
        self.assertIn('Local active quest IDs: 2', c.ns.diagnosticsText.text)

    def test_prefix_confirmation_overrides_enum_result(self):
        c = Client()
        c.lua.globals().prefixConfirmed = False
        c.ns.InitializeSync()
        self.assertFalse(c.ns.syncReady)
        c.ns.SyncNow()
        self.assertEqual(c.drain(), [])
        c.lua.globals().prefixConfirmed = True
        c.lua.globals().registrationResult = 8
        c.ns.InitializeSync()
        self.assertTrue(c.ns.syncReady)
        self.assertEqual(c.ns.syncStats.registration, 'DuplicatePrefix (8)')

    def test_registration_fallback_modern_and_legacy(self):
        c = Client()
        g = c.lua.globals()
        g.C_ChatInfo.IsAddonMessagePrefixRegistered = None
        c.ns.InitializeSync()
        self.assertTrue(c.ns.syncReady)
        g.registrationResult = True
        g.Enum = None
        c.ns.InitializeSync()
        self.assertTrue(c.ns.syncReady)
        g.registrationResult = 999
        c.ns.InitializeSync()
        self.assertFalse(c.ns.syncReady)

    def test_receive_diagnostics_explain_rejection(self):
        c = Client()
        c.receive('1|S|1|1|1|1', sender='Stranger-TestRealm')
        c.receive('1|S|1|1|1|1')
        c.ns.Diagnostics()
        self.assertIn('sender outside detected roster', c.ns.diagnosticsText.text)
        self.assertEqual(c.ns.syncStats.received, 2)
        self.assertEqual(c.ns.syncStats.accepted, 1)
        self.assertEqual(c.ns.syncStats.snapshots, 1)

    def test_two_players_sync_completion_and_shared_quests(self):
        a = Client(quests=range(1, 41), completed=(50,))
        b = Client('Bob', 'Alice', quests=(2, 50), completed=(1,))
        a.ns.SyncNow()
        b.ns.SyncNow()
        for _ in range(20):
            am, bm = a.drain(), b.drain()
            if not am and not bm:
                break
            for _, message, channel in am:
                b.receive(message, 'Alice-TestRealm', channel)
            for _, message, channel in bm:
                a.receive(message, 'Bob-TestRealm', channel)
        else:
            self.fail('sync did not settle')
        self.assertTrue(a.ns.members['Bob-TestRealm'].active[50])
        self.assertTrue(b.ns.members['Alice-TestRealm'].active[40])
        self.assertTrue(a.ns.members['Bob-TestRealm'].completed[1])
        self.assertTrue(b.ns.members['Alice-TestRealm'].completed[50])
        rows = a.ns.Rows()
        self.assertEqual(rows[1].id, 2)
        self.assertEqual(rows[1].active, 2)
        self.assertEqual(rows[1].people, 2)

    def test_out_of_order_chunks_and_duplicates(self):
        c = Client()
        c.receive('1|S|4|2|2|3')
        self.assertIsNone(c.ns.members['Bob-TestRealm'])
        c.receive('1|S|4|2|2|3')
        c.receive('1|S|4|1|2|1,2')
        self.assertTrue(c.ns.members['Bob-TestRealm'].active[3])
        c.receive('1|S|3|1|1|999')
        self.assertIsNone(c.ns.members['Bob-TestRealm'].active[999])

    def test_reloaded_peer_resets_revision(self):
        c = Client()
        c.receive('1|S|100|1|1|9')
        c.receive('1|H')
        c.receive('1|S|1|1|1|7')
        self.assertTrue(c.ns.members['Bob-TestRealm'].active[7])
        self.assertIsNone(c.ns.members['Bob-TestRealm'].active[9])

    def test_malformed_and_untrusted_packets(self):
        c = Client()
        for packet in ['1|S|1|0|1|1', '1|S|1|1|65|1', '1|S|1|1|1|1,,2',
                       '1|S|1|1|1|0', '1|S|1|1|1|-2', '1|S|1|1|1|2147483648',
                       '1|S|1|1|1|1,', '1|S|1|1|1|' + ','.join(['1']*19), 'x'*256]:
            c.receive(packet)
        c.receive('1|S|1|1|1|3', sender='Stranger-TestRealm')
        c.receive('1|S|1|1|1|3', channel='RAID')
        self.assertIsNone(c.ns.members['Bob-TestRealm'])

    def test_secret_values_are_ignored(self):
        c = Client()
        g = c.lua.globals()
        g.entries[1].questID = g.secret
        g.finished[2] = g.secret
        c.ns.ReadQuests()
        self.assertIsNone(c.ns.active[1])
        self.assertIsNone(c.ns.Completed(2))
        c.ns.Receive('WowTogetherV1', g.secret, 'PARTY', 'Bob-TestRealm')
        self.assertIsNone(c.ns.members['Bob-TestRealm'])

    def test_missing_apis_and_solo_mode(self):
        c = Client()
        c.lua.globals().C_QuestLog.GetInfo = None
        self.assertFalse(c.ns.ReadQuests())
        c.ns.Diagnostics()
        c = Client()
        c.lua.globals().grouped = False
        c.ns.SyncNow()
        self.assertEqual(c.drain(), [])
        self.assertIn('Local quest view', c.ns.status)

    def test_raid_and_missing_messaging(self):
        c = Client()
        c.lua.globals().raid = True
        c.ns.SyncNow()
        self.assertEqual(c.drain(), [])
        c = Client()
        c.lua.globals().C_ChatInfo.SendAddonMessage = None
        c.ns.InitializeSync()
        self.assertFalse(c.ns.syncReady)
        c.ns.SyncNow()
        self.assertEqual(c.drain(), [])

    def test_transfer_limit_is_reported(self):
        c = Client(quests=range(1, 1200))
        c.ns.SyncNow()
        c.drain()
        self.assertIn('Sync limit reached', c.ns.status)

    def test_forever_surnames_self_echo_and_party_match(self):
        c = Client()
        c.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee'),
                      'party2': ('Elianus', 'Bronchilius')})
        c.receive('1|S|1|1|1|8', sender='Barry Batsman-ClassicBetaPvP2')
        self.assertEqual(c.ns.syncStats.ignored, 1)
        self.assertIsNone(c.ns.members['Barry-Batsman'])
        c.receive('1|S|1|1|1|2,3', sender='Shamoone Heehee-ClassicBetaPvP')
        self.assertTrue(c.ns.members['Shamoone-Heehee'].active[3])
        self.assertEqual(c.ns.Rows()[1].active, 2)
        self.assertEqual(c.ns.Rows()[1].people, 2)  # Third party member has no snapshot.
        c.ns.Diagnostics()
        self.assertIn('Shamoone Heehee: quest snapshot received', c.ns.diagnosticsText.text)
        self.assertIn('matched full character name', c.ns.diagnosticsText.text)

    def test_forever_two_client_transfer(self):
        a = Client(quests=(1, 2), completed=(3,))
        b = Client(quests=(2, 3), completed=(1,))
        a.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee')})
        b.unit_names({'player': ('Shamoone', 'Heehee'), 'party1': ('Barry', 'Batsman')})
        a.ns.SyncNow()
        b.ns.SyncNow()
        for _ in range(20):
            am, bm = a.drain(), b.drain()
            if not am and not bm:
                break
            for _, message, channel in am:
                a.receive(message, 'Barry Batsman-ClassicBetaPvP2', channel)
                b.receive(message, 'Barry Batsman-ClassicBetaPvP2', channel)
            for _, message, channel in bm:
                a.receive(message, 'Shamoone Heehee-ClassicBetaPvP', channel)
                b.receive(message, 'Shamoone Heehee-ClassicBetaPvP', channel)
        else:
            self.fail('surname sync did not settle')
        self.assertTrue(a.ns.members['Shamoone-Heehee'].completed[1])
        self.assertTrue(b.ns.members['Barry-Batsman'].completed[3])
        self.assertEqual(a.ns.Rows()[1].active, 2)
        self.assertGreater(a.ns.syncStats.accepted, 0)

    def test_surname_matching_rejects_partial_unknown_and_ambiguous_names(self):
        c = Client()
        c.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee')})
        for sender in ['Shamoone-ClassicBetaPvP', 'Shamoone Other-ClassicBetaPvP',
                       'ShamooneHeehee-ClassicBetaPvP', 'Stranger Heehee-ClassicBetaPvP']:
            c.receive('1|S|1|1|1|8', sender=sender)
        self.assertEqual(c.ns.syncStats.accepted, 0)
        c.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee'),
                      'party2': ('Shamoone', 'Heehee')})
        c.receive('1|S|1|1|1|8', sender='Shamoone Heehee-ClassicBetaPvP')
        self.assertEqual(c.ns.syncStats.accepted, 0)
        c.ns.Diagnostics()
        self.assertIn('ambiguous party identity', c.ns.diagnosticsText.text)

    def test_traditional_names_keep_realm_validation(self):
        c = Client()
        c.receive('1|S|1|1|1|8', sender='Bob-WrongRealm')
        self.assertEqual(c.ns.syncStats.accepted, 0)
        c.receive('1|S|1|1|1|8', sender='Bob-Test Realm')
        self.assertTrue(c.ns.members['Bob-TestRealm'].active[8])

    def test_remote_only_quest_titles_and_local_preference(self):
        c = Client(quests=(1,))
        c.receive('1|S|4|1|1|1,50')
        c.receive('1|T|4|50|A Friend in Need')
        c.receive('1|T|4|1|Different locale title')
        rows = {c.ns.Rows()[i].id: c.ns.Rows()[i].title for i in range(1, len(c.ns.Rows()) + 1)}
        self.assertEqual(rows[50], 'A Friend in Need')
        self.assertEqual(rows[1], 'Quest 1')
        c.ns.Render()
        self.assertIn('A Friend in Need', c.view_text())
        self.assertNotIn('[50]', c.view_text())
        c.ns.Diagnostics()
        self.assertIn('Quest names resolved: 2/2', c.ns.diagnosticsText.text)

    def test_out_of_order_titles_and_stale_titles(self):
        c = Client()
        c.receive('1|T|5|50|Before the Snapshot')
        self.assertIsNone(c.ns.members['Bob-TestRealm'])
        c.receive('1|S|5|1|1|50')
        self.assertEqual(c.ns.QuestTitle(50), 'Before the Snapshot')
        c.receive('1|S|6|1|1|50')
        c.receive('1|T|5|50|Old title')
        self.assertEqual(c.ns.QuestTitle(50), 'Before the Snapshot')
        c.receive('1|T|6|50|Current title')
        self.assertEqual(c.ns.QuestTitle(50), 'Current title')
        c.receive('1|T|6|51|Not an active quest')
        self.assertIsNone(c.ns.members['Bob-TestRealm'].titles[51])

    def test_secret_and_oversized_titles_are_safe(self):
        c = Client()
        self.assertIsNone(c.ns.SafeTitle(c.lua.globals().secret))
        self.assertIsNone(c.ns.SafeTitle('   '))
        clean = c.ns.SafeTitle('Danger|Hquest:2|hName|h\nNext')
        self.assertNotIn('|', clean)
        self.assertNotIn('\n', clean)
        title = 'é' * 200
        shortened = c.ns.SafeTitle(title)
        self.assertLessEqual(len(shortened.encode('utf-8')), 180)
        self.assertTrue(shortened.endswith('...'))
        c.receive('1|S|1|1|1|50')
        c.receive('1|T|1|50|' + 'x' * 181)
        self.assertIsNone(c.ns.members['Bob-TestRealm'].titles[50])

    def test_titles_sent_with_matching_snapshot_and_bounded_packets(self):
        c = Client(quests=(50,))
        c.lua.globals().entries[1].title = 'é' * 200
        c.ns.SyncNow()
        messages = [message for _, message, _ in c.drain()]
        snapshot = next(message for message in messages if message.startswith('1|S|'))
        title = next(message for message in messages if message.startswith('1|T|'))
        self.assertEqual(snapshot.split('|')[2], title.split('|')[2])
        self.assertLessEqual(len(title.encode('utf-8')), 255)
        self.assertIn('é', title)

    def test_three_player_shared_quest_count(self):
        c = Client(quests=(2,))
        c.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee'),
                      'party2': ('Elianus', 'Bronchilius')})
        c.receive('1|S|1|1|1|2', sender='Shamoone Heehee-ClassicBetaPvP')
        c.receive('1|S|1|1|1|2', sender='Elianus Bronchilius-ClassicBetaPvP2')
        self.assertEqual(c.ns.Rows()[1].active, 3)
        self.assertEqual(c.ns.Rows()[1].people, 3)

    def test_member_statuses_distinguish_active_completed_and_unknown(self):
        c = Client(quests=(1,), completed=(50,))
        c.receive('1|S|1|1|1|50')
        c.receive('1|T|1|50|Already Finished')
        c.ns.Render()
        self.assertIn('You: Completed', c.view_text())
        self.assertIn('Bob Test Realm: Active', c.view_text())
        self.assertIn('Not in log', c.view_text())
        c.receive('1|C|2|1|1|1')
        c.ns.Render()
        self.assertIn('Bob Test Realm: Completed', c.view_text())
        self.assertNotIn('Not in log', c.view_text())

    def test_cached_titles_are_pruned_and_unsynced_peer_is_visible(self):
        c = Client()
        c.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee'),
                      'party2': ('Elianus', 'Bronchilius')})
        c.receive('1|S|1|1|1|2,50', sender='Shamoone Heehee-ClassicBetaPvP')
        c.receive('1|T|1|50|Retained title', sender='Shamoone Heehee-ClassicBetaPvP')
        c.receive('1|S|2|1|1|2,50', sender='Shamoone Heehee-ClassicBetaPvP')
        self.assertEqual(c.ns.QuestTitle(50), 'Retained title')
        c.ns.Render()
        self.assertIn('SHARED ACTIVE QUEST', c.view_text())
        self.assertEqual(c.ns.ui.metrics[1].value.text, '2 / 3')
        self.assertIn('Elianus Bronchilius • level pending |cffe4b66awaiting', c.view_text())
        c.receive('1|S|3|1|1|2', sender='Shamoone Heehee-ClassicBetaPvP')
        self.assertIsNone(c.ns.members['Shamoone-Heehee'].titles[50])

    def test_throttled_head_is_retried_with_backoff(self):
        c = Client()
        c.lua.globals().sendResults = c.lua.table_from([8, 8, 7])
        c.ns.SyncNow()
        messages = [message for _, message, _ in c.drain()]
        self.assertEqual(messages[:3], ['1|H'] * 3)
        self.assertTrue(any(message.startswith('1|S|') for message in messages))
        self.assertEqual(c.ns.syncStats.retries, 2)
        self.assertEqual(c.ns.syncStats.failures, 0)
        delays = [c.lua.globals().delays[i] for i in range(1, len(c.lua.globals().delays)+1)]
        self.assertIn(2, delays)
        self.assertIn(4, delays)
        self.assertEqual(c.ns.TransportState().queued, 0)

    def test_permanent_throttle_stops_bounded_transfer_and_can_retry(self):
        c = Client()
        c.lua.globals().sendResults = c.lua.table_from([8] * 6)
        c.ns.SyncNow()
        messages = c.drain()
        self.assertEqual(len(messages), 6)
        self.assertEqual(c.ns.syncStats.failures, 1)
        self.assertEqual(c.ns.TransportState().queued, 0)
        self.assertIn('Delivery failed', c.ns.status)
        c.ns.SyncNow()
        self.assertTrue(any(message.startswith('1|S|') for _, message, _ in c.drain()))

    def test_send_failure_discards_dependent_titles(self):
        c = Client()
        c.lua.globals().sendResults = c.lua.table_from([9])
        c.ns.SyncNow()
        messages = c.drain()
        self.assertEqual(len(messages), 1)
        self.assertEqual(c.ns.syncStats.failures, 1)
        self.assertEqual(c.ns.TransportState().queued, 0)

    def test_unchanged_events_and_repeated_manual_clicks_do_not_flood(self):
        c = Client()
        c.ns.SyncNow()
        initial_queue = c.ns.TransportState().queued
        for _ in range(50):
            c.ns.SyncNow()
        self.assertEqual(c.ns.TransportState().queued, initial_queue)
        c.drain()
        attempts = c.ns.syncStats.sendAttempts
        for _ in range(100):
            c.ns.ScheduleSync()
        c.drain()
        self.assertEqual(c.ns.syncStats.sendAttempts, attempts)
        self.assertGreater(c.ns.syncStats.coalesced, 0)
        c.lua.globals().entries[1].questID = 3
        c.ns.ScheduleSync()
        self.assertTrue(any(message.startswith('1|S|') for _, message, _ in c.drain()))

    def test_ui_filters_and_minimap_clicks(self):
        c = Client(quests=(1, 2))
        c.receive('1|S|1|1|1|2,3')
        c.receive('1|T|1|3|Friend Quest')
        c.ns.SetFilter('shared')
        self.assertEqual(c.ns.ui.visibleCards, 1)
        self.assertEqual(c.ns.ui.cards[1].title.text, 'Quest 2')
        c.ns.SetFilter('different')
        self.assertEqual(c.ns.ui.visibleCards, 2)
        c.ns.SetFilter('all')
        self.assertEqual(c.ns.ui.visibleCards, 3)
        self.assertEqual(c.ns.ui.zone.text, 'Durotar')
        icon = c.ns.minimapButton
        self.assertTrue(icon.IsShown(icon))
        icon.OnClick(icon, 'LeftButton')
        self.assertTrue(c.ns.window.IsShown(c.ns.window))
        icon.OnClick(icon, 'RightButton')
        self.assertTrue(c.ns.diagnosticsWindow.IsShown(c.ns.diagnosticsWindow))
        c.ns.ToggleMinimap()
        self.assertFalse(icon.IsShown(icon))
        self.assertTrue(c.lua.globals().WowTogetherDB.minimapHidden)
        c.ns.CreateMinimap()
        self.assertFalse(c.ns.minimapButton.IsShown(c.ns.minimapButton))

    def test_quest_giver_offers_sync_only_positive_evidence(self):
        c = Client(quests=(1,))
        c.receive('1|S|1|1|1|2')
        c.lua.execute("C_GossipInfo = {GetAvailableQuests=function() return {{questID=2}, {questID=secret}} end}")
        c.ns.InitializeOffers()
        c.ns.handlers.GOSSIP_SHOW()
        self.assertTrue(c.ns.offered[2])
        self.assertEqual(c.ns.MemberStates(2)[1].status, 'Offered by quest giver')
        c.ns.Render()
        self.assertIn('Quest giver offered', c.view_text())
        self.assertTrue(any(message.startswith('1|O|') for _, message, _ in c.drain()))
        c.ns.handlers.GOSSIP_CLOSED()
        self.assertIsNone(c.ns.offered[2])
        self.assertNotEqual(c.ns.MemberStates(2)[1].status, 'Offered by quest giver')
        c.receive('1|O|2|1|1|1')
        self.assertEqual(c.ns.MemberStates(1)[2].status, 'Offered by quest giver')
        c.receive('1|O|3|1|1|')
        self.assertNotEqual(c.ns.MemberStates(1)[2].status, 'Offered by quest giver')
        self.assertFalse(any('Ineligible' in c.ns.MemberStates(id)[1].status for id in (1, 2)))

    def test_missing_minimap_and_offer_api_are_optional(self):
        c = Client()
        c.lua.globals().Minimap = None
        c.ns.minimapButton = None
        c.ns.CreateMinimap()
        self.assertIsNone(c.ns.minimapButton)
        c.ns.ToggleMinimap()
        c.ns.InitializeOffers()
        self.assertFalse(c.ns.offerReady)
        c.ns.Diagnostics()
        self.assertIn('C_GossipInfo.GetAvailableQuests: missing', c.ns.diagnosticsText.text)

    def test_throttled_multipart_snapshot_reaches_peer_with_titles(self):
        a = Client(quests=range(1, 41))
        b = Client('Bob', 'Alice')
        # Hello and part 1 succeed, part 2 is rejected once, then its retry succeeds.
        a.lua.globals().sendResults = a.lua.table_from([7, 7, 8, 7])
        a.ns.SyncNow()
        for _, message, channel, result in a.drain(include_results=True):
            if result == 7:
                b.receive(message, 'Alice-TestRealm', channel)
        self.assertEqual(a.ns.syncStats.retries, 1)
        self.assertTrue(b.ns.members['Alice-TestRealm'].active[40])
        self.assertEqual(b.ns.QuestTitle(40), 'Quest 40')
        self.assertEqual(len(b.ns.members['Alice-TestRealm'].titles), 40)

    def test_negative_history_requires_matching_checked_revision(self):
        c = Client(quests=(1,))
        c.receive('1|S|1|1|1|50')
        c.receive('1|K|4|1|1|1,50')
        self.assertEqual(c.ns.MemberStates(1)[2].history, 'unknown')
        c.receive('1|C|5|1|1|')
        self.assertEqual(c.ns.MemberStates(1)[2].history, 'unknown')
        c.receive('1|K|5|1|1|1,50')
        self.assertEqual(c.ns.MemberStates(1)[2].history, 'not_completed')
        self.assertEqual(c.ns.MemberStates(1)[2].status, 'Not in log; history unfinished')
        c.receive('1|C|6|1|1|1')
        self.assertEqual(c.ns.MemberStates(1)[2].history, 'completed')

    def test_restricted_completion_is_not_reported_as_unfinished(self):
        c = Client(quests=(1, 2))
        c.lua.globals().finished[2] = c.lua.globals().secret
        c.ns.SyncNow()
        messages = [message for _, message, _ in c.drain()]
        c_packet = next(message for message in messages if message.startswith('1|C|'))
        k_packet = next(message for message in messages if message.startswith('1|K|'))
        self.assertEqual(c_packet.split('|')[2], k_packet.split('|')[2])
        self.assertEqual(k_packet.split('|')[-1], '1')
        self.assertEqual(c.ns.MemberStates(2)[1].history, 'unknown')

    def test_suggestions_rank_shared_then_offered_then_unverified(self):
        c = Client(quests=(1, 2))
        c.receive('1|S|1|1|1|2,3')
        c.receive('1|C|2|1|1|')
        c.receive('1|K|2|1|1|1,2,3')
        c.receive('1|O|3|1|1|1')
        suggestions = c.ns.Suggestions()
        self.assertEqual(suggestions[1].row.id, 2)
        self.assertEqual(suggestions[1].category, 'Continue together')
        self.assertEqual(suggestions[2].row.id, 1)
        self.assertEqual(suggestions[2].category, 'Pick up, then join')
        self.assertEqual(suggestions[3].category, 'Check pickup')
        self.assertIn('does not establish eligibility', suggestions[3].reason)
        c.ns.SetFilter('suggestions')
        self.assertEqual(c.ns.ui.visibleCards, 3)
        self.assertIn('CONTINUE TOGETHER', c.view_text())
        self.assertIn('Pick it up manually', c.view_text())

    def test_completion_differences_and_unsynced_players_are_not_eligible_claims(self):
        c = Client(quests=(1,), completed=(3,))
        c.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee'),
                      'party2': ('Elianus', 'Bronchilius')})
        c.receive('1|S|1|1|1|3', sender='Shamoone Heehee-ClassicBetaPvP')
        c.receive('1|C|2|1|1|1', sender='Shamoone Heehee-ClassicBetaPvP')
        c.receive('1|K|2|1|1|1,3', sender='Shamoone Heehee-ClassicBetaPvP')
        self.assertEqual(c.ns.Suggestions()[1].category, 'Different progress')
        c.ns.SetFilter('suggestions')
        self.assertIn('still need to sync', c.view_text())
        self.assertNotIn('All 3', c.view_text())
        solo = Client()
        self.assertEqual(len(solo.ns.Suggestions()), 0)

    def test_diagnostics_copy_closes_after_native_copy_interval(self):
        c = Client()
        c.ns.Diagnostics()
        edit, window = c.ns.diagnosticsText, c.ns.diagnosticsWindow
        edit.OnKeyDown(edit, 'C')
        c.drain()
        self.assertTrue(window.IsShown(window))
        c.lua.globals().controlDown = True
        edit.OnKeyDown(edit, 'C')
        self.assertTrue(window.IsShown(window))
        self.assertEqual(c.lua.globals().delays[len(c.lua.globals().delays)], 0.1)
        c.drain()
        self.assertFalse(window.IsShown(window))
        c.ns.Diagnostics()
        edit.OnKeyDown(edit, 'C')
        c.ns.Diagnostics()  # Refreshed/new report must not close on the old callback.
        c.drain()
        self.assertTrue(window.IsShown(window))

    def test_compact_party_cells_run_left_to_right(self):
        c = Client(quests=(1,))
        c.unit_names({'player': ('Barry', 'Batsman'), 'party1': ('Shamoone', 'Heehee'),
                      'party2': ('Elianus', 'Bronchilius')})
        c.receive('1|S|1|1|1|1', sender='Shamoone Heehee-ClassicBetaPvP')
        c.receive('1|S|1|1|1|1', sender='Elianus Bronchilius-ClassicBetaPvP')
        c.ns.Render()
        card = c.ns.ui.cards[1]
        cells = card.memberCells
        self.assertEqual(len(cells), 3)
        self.assertLess(card.height, 130)  # Smaller than the old two-player card.
        self.assertEqual(cells[1].point[3], cells[2].point[3])
        self.assertLess(cells[1].point[2], cells[2].point[2])
        self.assertLess(cells[2].point[2], cells[3].point[2])
        self.assertLessEqual(cells[3].point[2] + cells[3].width, card.width)

    def test_character_context_is_guarded_and_synced(self):
        c = Client()
        c.guide_environment(level=5)
        c.ns.SyncNow()
        messages = [message for _, message, _ in c.drain()]
        self.assertIn('1|P|5|2|501|Durotar', messages)
        c.receive('1|P|22|2|502|Other Zone')
        self.assertEqual(c.ns.members['Bob-TestRealm'].profile.level, 22)
        c.lua.globals().playerLevel = c.lua.globals().secret
        c.ns.ReadProfile()
        self.assertEqual(c.ns.profile.level, 0)
        c.receive('1|P|9999|2|502|Other Zone')
        self.assertEqual(c.ns.members['Bob-TestRealm'].profile.level, 22)

    def test_native_questlines_preserve_markers_without_inventing_npc(self):
        c = Client()
        c.guide_environment()
        c.lua.execute(r"""
        C_QuestLine = {
          GetAvailableQuestLines=function() return {{questID=100, questLineID=7, questLineName='Coastal Story',
            questName='First Step', startMapID=502, x=0.4, y=0.6, isHidden=false}} end,
          GetQuestLineInfo=function(id) if id == 100 then return {questID=100, questLineID=7,
            questLineName='Coastal Story', questName='First Step', startMapID=502, x=0.4, y=0.6, isHidden=false} end end,
          RequestQuestLinesForMap=function(map) requestedGuideMap = map end,
        }
        questLevels[100] = 5
        """)
        c.ns.ReadGuide()
        choices = c.ns.GuideChoices()
        line = next(choices[i] for i in range(1, len(choices)+1) if choices[i].kind == 'Questline')
        self.assertEqual(line.title, 'Coastal Story')
        self.assertTrue(line.hasPoint)
        self.assertEqual(line.target.npc, '')
        self.assertEqual(line.destination, 'Visit the client questline marker')
        self.assertEqual(line.target.mapID, 501)  # Coordinates belong to the queried map.
        self.assertEqual(c.lua.globals().requestedGuideMap, 501)

    def test_observed_npc_hub_is_persisted_and_shared(self):
        c = Client()
        c.guide_environment()
        c.ns.ObserveQuestGiver(c.lua.table_from([c.lua.table_from({'questID': 100, 'title': 'NPC Quest', 'questLevel': 5})]))
        choices = c.ns.GuideChoices()
        hub = next(choices[i] for i in range(1, len(choices)+1) if choices[i].kind == 'Quest hub')
        self.assertEqual(hub.destination, 'Talk to Guide NPC')
        self.assertEqual(hub.target.x, 0.21)
        self.assertTrue(hub.hasPoint)
        self.assertEqual(c.ns.QuestTitle(100), 'NPC Quest')
        self.assertEqual(c.lua.globals().WowTogetherDB.guideBuilds['70009'][100].npc, 'Guide NPC')
        c.ns.SyncNow()
        messages = [message for _, message, _ in c.drain()]
        self.assertTrue(any(message.startswith('1|G|100|') for message in messages))
        self.assertFalse(any('Kaltunk' in message for message in messages))

    def test_level_gap_changes_guide_direction_from_data(self):
        c = Client()
        c.guide_environment(level=4)
        c.receive('1|S|1|1|1|20')
        c.receive('1|P|20|2|501|Test Coast')
        c.receive('1|G|100|7|501|21000|37000|4|n|Low Quest|Coastal Story|Guide NPC')
        c.receive('1|G|200|8|502|50000|50000|18|n|High Quest|Mountain Story|Mountain NPC')
        choices = c.ns.GuideChoices()
        self.assertEqual(choices[1].title, 'Coastal Story')
        self.assertTrue(choices[1].catchup)
        self.assertIn('4–20', choices[1].reason)
        self.assertIn('lower-level', choices[1].reason)
        c.lua.globals().playerLevel = 19
        c.ns.ReadProfile()
        choices = c.ns.GuideChoices()
        self.assertEqual(choices[1].title, 'Mountain Story')
        self.assertFalse(choices[1].catchup)

    def test_missing_levels_and_faction_differences_are_explained(self):
        c = Client()
        c.guide_environment()
        c.receive('1|G|100|7|501|21000|37000|5|n|Low Quest|Coastal Story|Guide NPC')
        choices = c.ns.GuideChoices()
        self.assertTrue(any('Waiting for every' in choices[i].reason for i in range(1, len(choices)+1)))
        c.receive('1|P|5|1|501|Test Coast')
        c.receive('1|S|1|1|1|1')
        choices = c.ns.GuideChoices()
        self.assertTrue(any('Faction differences' in choices[i].reason for i in range(1, len(choices)+1)))

    def test_level_context_alone_does_not_mark_progress_ready(self):
        c = Client()
        c.guide_environment()
        c.receive('1|P|20|2|501|Test Coast')
        c.receive('1|G|100|7|501|21000|37000|5|n|Low Quest|Coastal Story|Guide NPC')
        choices = c.ns.GuideChoices()
        self.assertFalse(choices[1].profilesReady)
        self.assertIn('quest snapshot', choices[1].reason)
        self.assertFalse(choices[1].catchup)

    def test_guide_context_is_resent_after_party_changes(self):
        c = Client()
        c.guide_environment()
        c.ns.SyncNow()
        c.drain()
        c.lua.globals().peer = 'Carol'
        c.ns.UpdateRoster()
        c.ns.SyncNow(False)
        messages = [message for _, message, _ in c.drain()]
        self.assertTrue(any(message.startswith('1|P|') for message in messages))
        self.assertTrue(any(message.startswith('1|G|') for message in messages))

    def test_guide_map_click_uses_known_coordinates_and_defers_in_combat(self):
        c = Client()
        c.guide_environment()
        c.receive('1|G|100|7|501|21000|37000|5|n|Low Quest|Coastal Story|Guide NPC')
        choices = c.ns.GuideChoices()
        guide = next(choices[i] for i in range(1, len(choices)+1) if choices[i].hasPoint)
        c.lua.globals().combat = True
        self.assertFalse(c.ns.ShowGuideOnMap(guide))
        self.assertIsNone(c.lua.globals().waypoint)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertEqual(c.lua.globals().waypoint.map, 501)
        self.assertEqual(c.lua.globals().waypoint.x, 0.21)
        self.assertTrue(c.lua.globals().WorldMapFrame.IsShown(c.lua.globals().WorldMapFrame))
        self.assertEqual(c.lua.globals().WorldMapFrame.mapID, 501)
        c.lua.globals().waypointAllowed = False
        self.assertFalse(c.ns.ShowGuideOnMap(guide))
        c.lua.globals().waypointAllowed = True
        c.lua.globals().waypointAccepted = False
        self.assertFalse(c.ns.ShowGuideOnMap(guide))

    def test_guide_without_destination_never_creates_a_waypoint(self):
        c = Client()
        c.guide_environment()
        choices = c.ns.GuideChoices()
        unmapped = next(choices[i] for i in range(1, len(choices)+1) if not choices[i].hasPoint)
        self.assertFalse(c.ns.ShowGuideOnMap(unmapped))
        self.assertIsNone(c.lua.globals().waypoint)

    def test_resizing_reflows_cards_and_saves_size(self):
        c = Client(default_guide=True)
        self.assertEqual(c.ns.filter, 'guides')
        c.ns.window.SetSize(c.ns.window, 1080, 800)
        c.ns.window.OnSizeChanged(c.ns.window, 1080, 800)
        self.assertEqual(c.ns.ui.contentWidth, 1006)
        self.assertEqual(c.ns.ui.cards[1].width, 1006)
        self.assertLessEqual(c.ns.ui.metrics[3].point[2] + c.ns.ui.metrics[3].width, 1080)
        c.ns.ui.resizeGrip.OnMouseUp(c.ns.ui.resizeGrip)
        self.assertEqual(c.lua.globals().WowTogetherDB.windowSize.width, 1080)
        self.assertEqual(c.lua.globals().WowTogetherDB.windowSize.height, 800)

    def test_direct_quest_dialog_learns_a_giver(self):
        c = Client()
        c.guide_environment()
        c.lua.execute("function GetQuestID() return 100 end; function GetTitleText() return 'Direct Offer' end")
        c.ns.InitializeOffers()
        c.ns.handlers.QUEST_DETAIL()
        self.assertTrue(c.ns.offered[100])
        self.assertEqual(c.lua.globals().WowTogetherDB.guideBuilds['70009'][100].title, 'Direct Offer')
        c.ns.handlers.QUEST_FINISHED()
        self.assertIsNone(c.ns.offered[100])
        # Having the direct-dialog API does not imply a gossip API exists.
        c.ns.ReadOffers()
        self.assertFalse(c.ns.gossipReady)

    def test_invalid_guide_records_and_secret_locations_are_rejected(self):
        c = Client()
        c.guide_environment()
        c.receive('1|G|100|7|501|100001|37000|5|n|Low Quest|Coastal Story|Guide NPC')
        self.assertIsNone(c.ns.members['Bob-TestRealm'])
        c.lua.execute("C_Map.GetPlayerMapPosition=function() return secret end")
        c.ns.ObserveQuestGiver(c.lua.table_from([c.lua.table_from({'questID': 100, 'title': 'NPC Quest'})]))
        self.assertIsNone(c.lua.globals().WowTogetherDB.guideBuilds['70009'][100])

    def test_departed_peer_and_empty_snapshot(self):
        c = Client()
        c.receive('1|S|1|1|1|9')
        c.receive('1|S|2|1|1|')
        self.assertIsNone(c.ns.members['Bob-TestRealm'].active[9])
        c.lua.globals().peer = None
        c.ns.UpdateRoster()
        self.assertIsNone(c.ns.members['Bob-TestRealm'])

if __name__ == '__main__':
    unittest.main()
