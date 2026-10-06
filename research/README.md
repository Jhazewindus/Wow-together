# Reviewed player quest research

Keep supplied exports unchanged here, with their original event versions,
sessions and beta builds. These are observations from players, not a complete
quest database. Only supported corrections enter the shipped catalogue. Raw
exports are not included in the addon ZIP.

## 2026-10-06 — Durotar, anonymous Orc rogue

Source: the friend's export supplied in this chat, without a character/tester
name. File: [2026-10-06-durotar-orc-rogue-build-70235.json](2026-10-06-durotar-orc-rogue-build-70235.json).
SHA-256: `05b7c9e53e3bff65f8f7f9b32fcd5975cd94a80548d5111d9b4738f1b36d19fa`.

23 events, no dropped observations. Level 1, Horde, Orc (race 2), rogue
(class 4), client 1.60.1, build 70235, interface 16001. The export header says
0.8.13, but events retain three sessions: 0.8.8 (1–15), 0.8.12 (16–19),
0.8.13 (20–23). Events comprise 13 reputation notifications, 5 offer snapshots,
3 automatic pickup deferrals, 1 hand-in and 1 pickup restoration.

### Confirmed facts already in the catalogue

| Quest | Confirmed quest giver | Evidence |
| --- | --- | --- |
| 4641 — Your Place in the World | 10176 — Kaltunk | Positive offer, sequence 4 |
| 788 — Cutting Teeth | 3143 — Gornek | Positive offer, sequence 12; active in later snapshots |
| 97279 — Wayward Weapons | 3143 — Gornek | Positive offers, sequences 5, 13, 15; active later |

The export records the hand-in of 4641 at sequence 9. Later snapshots show
788 and 97279 accepted while 787 (The New Horde) remains incomplete. This
supports keeping 787 out of their mandatory prerequisite chain, as the current
catalogue already does.

### Evidence that does not justify a new rule

- Immediately after the 4641 hand-in, sequence 10 still reports it active and
  not completed. The partial positive offer of 788 at sequence 12 has the same
  stale history. A subsequent complete list at sequence 13 omits 788 again.
  These snapshots do not establish a reliable new 4641 → 788 prerequisite.
- 789 (Sting of the Scorpid) is deferred but never positively offered. Do not
  infer its unlock or replace its existing Cutting Teeth requirement from this
  export. Manual/automatic deferrals are not completed prerequisites.
- Reputation events are notifications without standings. They do not prove
  a reputation gate. No NPC/mob coordinates or objective locations were exported.

Integration: retain this file and replay it in `tests/test_0814.py`. Verify
positive giver IDs against the shipped catalogue, preserve existing eligibility,
and prevent ambiguous/stale history from creating an account-wide learned gate.
No prerequisite, race restriction or map coordinate is changed by this report;
mapping coverage is unchanged. Additional before/after NPC offer snapshots with
consistent completion history can support a later correction.
