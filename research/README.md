# Reviewed player quest research

Keep supplied exports unchanged here, with their original event versions,
sessions and beta builds. These are observations from players, not a complete
quest database. Only supported corrections enter the shipped catalogue. Raw
exports are not included in the addon ZIP.

## 2026-10-08 — expanded Dun Morogh review after main 0.8.60

[The full-zone review](dun-morogh-2026-10-08/README.md) captures all 55 compiled
quest IDs, updates one boar work point from current NPC coordinates, and retains
both Rime identities, tester provenance and Winter Wolf hint safeguards. The
three source gaps remain open. Complete standard/dwarf comparisons preserve
151/30 actions and expose compiler tradeoffs for main-developer review. This
extends, rather than replaces, the earlier selected-source evidence below.

## 2026-10-08 — Mulgore prerequisites, NPC locations and race coverage

[The Mulgore review](mulgore-2026-10-08/README.md) retains 74 quest IDs, current
source evidence, standard/Tauren full-route comparisons and a player checklist.
Three prerequisite links and seven NPC-location records are corrected (eight
distinct quests). Existing source gaps and actual-offer confirmation remain.
The old early-chapter orders violate the newly established prerequisites;
optimization and the suppressed single-quest Broodmother chapter require a
coordinated shared-engine decision. This remains a data/research draft.

## 2026-10-08 — Durotar stage facts and compiler handoff

[The Durotar review](durotar-2026-10-08/README.md) retains the full 103-quest
inventory, source evidence, six supported stage corrections, before/after audits,
full-route comparisons and a player checklist. Five objective gaps close; four
remain. The optimization guard reports shared-compiler tradeoffs, so this is a
data/research draft requiring main-developer review before merge.

## 2026-10-08 — Dun Morogh source coverage review

[The structured review](2026-10-08-dun-morogh-review.json) records selected public
facts from four files at the repository's pinned QuestieDB revision. Downloaded
file hashes matched `tools/forever_source_manifest.json`. Only factual IDs,
short names, quantities and one existing representative spawn are retained;
upstream code and quest prose are excluded. This is independent source research,
not a new player report or a live beta observation.

The three open records remain open:

| Quest | Supported facts retained | Evidence still needed |
| --- | --- | --- |
| 282 — Senir's Observations | Predecessor 218; Grelin → Thalos; distinct from quest 420 | Current-beta offer/character/completion evidence for unresolved pickup conditions |
| 95217 — The Quarry's Smith | 12 Copper Bars, 4 Toughened Boar Hides; explicit hide drop from Scarred Crag Boar at a published spawn | An applicable local Copper Bar acquisition source and position |
| 98423 — The Treaty of Understanding | Item 281030 starts the quest; Magni receives it in Ironforge | Explicit item acquisition relation and position |

No gap is closed by assuming a familiar quest chain is exhaustive, choosing a
remote item drop as a local farming point, or inventing an item pickup NPC.
The existing Treacherous Cold → Rime's Wrath tester correction remains intact.
`tests/test_zone_coverage.py` exercises the scoped audit, keeps the global report
safe, and guards these supported facts and unresolved boundaries. Use the
`--zone` workflow in `QUEST_DATA.md` for the next supported correction.

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

## 2026-10-06 — Astranaar ground-line feedback

The author is an unlabeled friend. The Dutch report says routing went through
Alliance Astranaar; the follow-up clarifies that **only the map line crossed it**,
with no named Astranaar waypoint. The current quest/coordinates were not supplied.
Keep this distinct from missing-pickup and flight-unlock reports.

Raw attachment `2026-10-06-astranaar-findings-supplied.txt` is retained byte-for-byte,
50,016 bytes, SHA-256
`a65c543c680fa3e0647e53e911f57cb84a8f60b77b590c3f97c8f448c87d716e`.
Its header says 0.8.19, but the recoverable 77 whole events are exactly the same
0.8.12–0.8.14/build-70235 prefix as the earlier Kadrak export. It ends at a 59 KB
left marker, not valid complete JSON. `2026-10-06-astranaar-review.json` references
that existing recovered prefix instead of counting the events twice. No exact
current route, additional unlock rule or new map coordinates are inferred.

Independent review of the pinned Mapzeroth Forever geography found Astranaar's
taxi point had no faction in our adapted graph, while its town/service metadata
already said Alliance. Apply the source's known town ownership to 26 missing
flight-point labels. Derive 48 approximate occupied-location rectangles from
town/city centers, same-map taxi points and scoped service positions. In-game,
add an estimated 100-yard margin with public physical map sizes. Astranaar's
literal source range is x 0.345–0.370, y 0.4801–0.520 on map 1440. These are
occupied-location bounds, not guard ranges or surveyed roads.

Source: commit `fd68cfe2153379898680c66a01833846f9933587`,
`Data/Forever/Pois.lua`, SHA-256
`3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d`.
See `TRAVEL_DATA.md`, `TravelData.json` and the MIT attribution. Our own segment
checks reject hostile crossings, including local map previews and flight access.
Use existing graph alternatives only; retain markers/progress and show a caution
if no bypass is known. No terrain mesh or new road connections are fabricated.

Durotar was rechecked against inherited main 0.8.60 in [the follow-up review](durotar-2026-10-08/refresh-0.8.60/README.md). Its existing corrections and gaps remain; new coordination findings cover ordinary Vile Familiars class eligibility and the omitted Need for a Cure cross-zone acquisition handoff.

The [Mulgore 0.8.60 follow-up](mulgore-2026-10-08/refresh-0.8.60/README.md) retains the earlier corrections and gaps, rechecks Baine and the Battleboars, and records current/pinned race-mask disagreements for Our Ancient Enemy, Drive Them Out and The High Chieftain.

The [Dun Morogh follow-up](dun-morogh-2026-10-08/refresh-0.8.60/README.md) retains the boar correction and tester gate, rechecks distinct Rime objectives and Winter Wolf relations, and records the later Search for Incendicite pickup/handoff limitation.
