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

## 2026-10-06 — supplied Mulgore probe and overlapping partial exports

The unlabeled probe identifies Pachu Bloodwind, level 8 Horde Tauren warrior,
0.8.16 on build 70235. Mikmans is the explicitly named author of the quest-log
highlight request; do not assume all three attachments belong to him.

Raw supplied text is retained byte-for-byte:

- `2026-10-06-mulgore-probe-supplied.txt`: SHA-256
  `7a2b7d177fdcbe74c4680df3313009f01d95539e9a1bc5427eaaf71a4c721d8b`.
- `2026-10-06-mulgore-findings-supplied.txt`: SHA-256
  `6b411e15539bd20fe267168d0868336c2f216acf46bae3934a80200914077259`.
- `2026-10-06-mulgore-research-supplied.txt`: SHA-256
  `79f3aa6064004a2c5909d464ecce507eb183b870cff03d73733fd19a34b1cbec`.

The two exports end at pasted truncation markers (29/23 KB left); they are not
valid full JSON. `2026-10-06-mulgore-recovered-events.json` is an explicitly
partial derived review: 94 complete identical events, deduplicated once, ending
at sequence 94. Findings after the event array and later events are unavailable.
Original session/addon/build fields are preserved; newer headers do not upgrade
older evidence to build 70235. Raw research is excluded from release archives.

Complete NPC lists omit Our Ancient Enemy (99101; Brave Wildrunner/3222) and
The High Chieftain (99082; Baine Bloodhoof/2993), with recorded deferrals; neither
has a positive offer in the recovered portion. That supports retaining pending
NPC confirmation and reviewed `pickupRequiresOffer` flags. It does not identify
an exact prerequisite, reputation requirement, class or race exclusion. No new
account-wide learned parent, completion or map location is inferred. The manual
Attack on Camp Narache skip is personal feedback, not missing-offer evidence.
`tests/test_0819.py` verifies the recovery/provenance and shared offer behavior.

## 2026-10-06 — additional Report to Kadrak feedback

Source author is unlabeled; do not attribute it to Mikmans, Pachu or the main
developer. The Dutch report says Darn Talongrip has no quest, then corrects
that the character already had Report to Kadrak. Raw supplied file:
`2026-10-06-kadrak-findings-supplied.txt`, SHA-256
`c3132a77b1d750dc8536f428eef1e2d6ddda25997dee364fc41fbf24e7d34ebe`.
It ends at a 50 KB left marker. `2026-10-06-kadrak-recovered-events.json` retains
77 whole events through sequence 77, explicitly partial. Its header says 0.8.17
but recovered events are 0.8.12–0.8.14/build 70235: Horde Undead priest levels
21–22, Stonetalon/Barrens. Neither Darn/11821 nor an accepted/completed/offered
Report to Kadrak ID appears in this portion. No live diagnosis or new unlock is
inferred from the missing tail.

Independent review of the existing pinned Forever fact source proves reciprocal
exclusiveTo lists for 6541/6542. Both unchanged identities/levels and NPCs match
our catalogue. See `tools/quest_corrections.json` for the source commit/file hash
and reviewed explicit-alternative fields. This is factual quest data, not copied
provider/UI/routing code. Do not merge other similarly named quests or bulk import
unreviewed relationships. Keep the selected quest's real work and completion;
exclude the unchosen alternative from that player's runnable scope only.
