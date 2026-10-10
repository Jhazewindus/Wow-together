# Reviewed player quest research

## Main release review — 0.8.66 (10 October 2026)

The nine commits through `53d5e12` are integrated as research. Seven zone audit
refreshes contain no new runtime data. Felwood (`d0023c8`) and Feralas
(`649d55c`) candidate catalogue/correction/exclusion changes and their candidate
regression tests are **deferred, not shipped**: their complete-route repricers
fail reward-timing/difficulty guards; Felwood's short-guide comparison also
reports invalid order and changed endpoints. Main retains its 0.8.65 quest data.
The source evidence and before/after reports below remain available for a
follow-up that reconciles complete action sets and corrects compiler behavior.
Their coverage gains describe the candidate, not the current released data.
Do not treat merging this research history as approval of those data changes.

## 2026-10-10 — Winterspring audit refresh

[The Winterspring refresh](winterspring-2026-10-10/README.md) reruns the scoped
0.8.65 audit and complete Horde/Alliance flow capture. It confirms the previously
reviewed stage corrections remain intact, with 116/142 actions, no missing
pickup/hand-in coordinates and the same open objective and Alliance pickup
gaps. Seven focused coverage tests, 18 route regressions, and a Lua 5.1 host
load of all 87 TOC files pass. No new data or shared engine behavior changed;
native offers, access, and route checks remain on the player checklist.

The [Felwood review](felwood-2026-10-09/README.md) refreshes all four faction/chapter guides, documents current NPC/item evidence and profession-only Salve exclusions, and retains the Hunter raid-location unknowns. Its scoped compilation passes; full route repricing exposes data-driven order and reward-timing tradeoffs for main-developer review.

The [Feralas review](feralas-2026-10-10/README.md) corrects nine supplied-item false farms and the Morrow Stone two-item handoff. Both complete faction chapters retain all 239 actions; objective-location gaps fall 11 → 1, with Elixir acquisition still unknown. The Horde full-route guard requires review for reward timing and difficulty pressure.

Keep supplied exports unchanged here, with their original event versions,
sessions and beta builds. These are observations from players, not a complete
quest database. Only supported corrections enter the shipped catalogue. Raw
exports are not included in the addon ZIP.

## 2026-10-09 — Eastern Plaguelands hand-in stages

[The full-zone review](eastern-plaguelands-2026-10-09/README.md) preserves the
refreshed Alliance/Horde chapter baselines, all 109 direct catalogue records,
pinned source facts and full-route comparisons. Two corrections separate
Fetid Skull and Living Rot preparation inputs from their final hand-ins. Pickup
and objective location gaps remain open; current work areas and NPCs are
preserved, and the two item transformation interactions need in-game review.

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

The [Elwynn Forest review](elwynn-forest-2026-10-08/README.md) corrects three supplied deliveries, Jorik's representative position, two item counts, Bartleby's duel instruction and Applejack exchange acquisition; it excludes the evidenced Wabbit Pelts testing placeholder. It retains all 301 remaining actions and records unresolved residue/95771 facts, eight uncertain pickup requirements, the Human race-source disagreement, hidden elite Hogger, Warrior branch selection and strict full-route tradeoffs for main-developer review.

The [Stranglethorn Vale review](stranglethorn-vale-2026-10-08/README.md) corrects eight records, retains all 132 IDs / 885 actions, closes supported conversation and quantity gaps, and leaves item/event acquisition unknown. Full-route evidence records a changed Horde endpoint and delayed rewards; Green Hills chapter-reward mapping remains withheld pending coordinated completion dependencies.

The [Swamp of Sorrows review](swamp-of-sorrows-2026-10-08/README.md) preserves 32 quest IDs / 180 actions and all source gaps after checking pinned facts. It repairs the audit tool's catalogue/chapter capitalization mismatch, validates six chapters and retains a native player checklist. Contemporary acquisition/event facts remain unavailable; no coordinates or counts are invented.

The [Swamp of Sorrows refresh](swamp-of-sorrows-2026-10-10/README.md) reruns its six-guide audit and full-flow capture on `guides/coverage`, based on main 0.8.65. Scope and gaps remain unchanged; current compiler estimates are recorded separately from the older 0.8.61 comparison. No new public source evidence or native-beta observations support changing quest facts.

The [Tanaris review](tanaris-2026-10-08/README.md) corrects five supplied deliveries and field-sampling input/count semantics. It quarantines 43 evidenced level-60 scepter/reputation records while preserving their catalogue facts and unresolved gaps. The whole ordinary scope retains 60 IDs / 338 actions; same-scope comparisons expose a Horde travel/reward regression requiring shared-compiler review.

The [Tanaris refresh](tanaris-2026-10-10/README.md) reruns the four-guide audit and full-flow estimate on the 0.8.65-based branch. Ordinary scope remains 60 quest IDs / 338 actions with 2 pickup and 1 objective location gap; the previously reviewed endgame gates and their source gaps remain documented. No new Tanaris source evidence or data change supports another correction; the earlier Horde 51–60 route guard remains REVIEW REQUIRED.

The [Hinterlands review](hinterlands-2026-10-08/README.md) corrects the supplied venom parcel and maps Rhapsody's two missing liver drops to actual published Feralas points. All 50 IDs / 183 actions and all 16 strict replay states survive; recorded objective gaps 2 → 0. Elevation/approach uncertainty and three external Zul'Farrak prerequisite handoffs remain explicit coordination/player-check items.

The [Hinterlands refresh](hinterlands-2026-10-10/README.md) rechecks four full chapters and 64 points on the 0.8.65-based branch. All 50 IDs / 183 actions and zero recorded stage-location gaps remain; prerequisite review steps and external Zul'Farrak facts remain open. Current flow estimates are recorded separately from the earlier same-facts comparison, and no terrain or native-beta claim is added.

[Final combined guide validation](coverage-integration-2026-10-08/README.md): 1,562/1,563 host tests pass, including all 64 zone regressions; the sole historical catalogue fingerprint assertion remains. All 152 sections / 11,833 source points are checked, with 33 recorded gap-free sections and 390 unresolved ordinary records. No native beta or complete-terrain claim.

The [Thoradin's Wall review](thoradins-wall-2026-10-08/README.md) reconciles two records' object handoffs using published beta-observation positions in Loch Modan and Arathi. Both factions retain the full three-quest/nine-action chain, actual hand-in gates and saved guide key; zero recorded gaps stay zero. Treating the single local category as optional Arathi support remains a concrete, unapplied lifecycle/presentation proposal.

The [Thoradin's Wall refresh](thoradins-wall-2026-10-10/README.md) confirms both nine-action faction guides still have zero recorded stage gaps and the current full-flow estimates remain unchanged. The standalone category is not supported as a recommended region; optional Arathi handoff support remains a proposal for main-developer coordination because presentation changes affect saved guide progress.

The [Un'Goro Crater review](ungoro-crater-2026-10-08/README.md) corrects five records: container contents, a supported Felwood heart farm with alternatives, Lost!/Ringo escort separation and Devilsaur Barb use. The full 44-ID scope retains 141 Horde / 138 Alliance actions after removing only false canteen farming. Objective gaps fall 6 → 4; an existing unknown item-use count becomes explicit. Complete-route evidence records delayed rewards, an Alliance log-peak increase and omitted dungeon handoffs requiring shared-builder coordination. All 76 zone regressions pass; current source queue has 388 unresolved ordinary records.

The [Western Plaguelands review](western-plaguelands-2026-10-08/README.md) corrects fourteen records: supplied branches/bottles and other handoffs, actual assembled-item hand-ins, and Menethil's known delivery. Retain 96 IDs / 407 audit actions; objective gaps 23 → 11. Published optional introductions conflict with current required gates; the coordination proposal is unapplied. Eight Western replay states retain all actions/endpoints but expose delayed rewards and an Alliance log-peak increase; eight neighbouring Eastern replays preserve unchanged same-facts metrics. All 85 zone regressions pass; current source queue has 377 unresolved ordinary records.

The [Westfall review](westfall-2026-10-09/README.md) corrects eleven records: treasure-object interactions, actual Alba hub positions and explicit unknown detonator work. Standard full scope retains 45 IDs / 177 actions; separate Skyborn scope retains 26/224 actions and its actual cross-zone hand-in chain. Recorded objective gaps increase 1 → 2 by exposing a false conversation mapping. Twenty strict complete-route states pass with unchanged same-facts metrics. Dungeon handoffs, unlocated acquisition/use instructions, coarse Odd Child geography and optional Sweet Amber support remain documented. All 93 zone regressions pass; source queue has 378 unresolved ordinary records.

The [Westfall refresh](westfall-2026-10-10/README.md) reruns the standard audit and captures current 0.8.65 flows for standard and Skyborn scopes. Westfall remains 45 standard compiled IDs / 177 actions plus 26 Skyborn IDs / 224 actions. Objective gaps remain 92749 and 92819; route metrics are kept separate from the earlier 0.8.61 same-facts comparisons.

The [Wetlands review](wetlands-2026-10-09/README.md) corrects ten records: crate/barrel/corpse interactions, supplied tinder use, separate Algaz traversal and distinct Call of Water inputs. All 73 compiled IDs remain; 6/179/76 actions become 6/180/77 by adding actual traversal work. Recorded 5/11/5 source gaps remain. Twelve reconciled full-scope states preserve endpoints and valid orders, but delayed rewards and an uncertain-travel increase keep the guard REVIEW REQUIRED. Explicit ship endpoints, source conflicts and native player checklist accompany the review. All 102 zone regressions pass; global audit checks 11,835 points and source queue retains 378 unresolved ordinary records.

The [Wetlands refresh](wetlands-2026-10-10/README.md) reruns the three-guide audit and full-flow capture on the 0.8.65-based branch. Scope remains 6/180/77 actions; source gaps remain 5/11/5 with six uncertain pickup requirements and three unknown Call of Water quantities. Current metrics are separated from the earlier 0.8.61 comparison, whose 21–30 guard remains REVIEW REQUIRED.

The [Winterspring review](winterspring-2026-10-09/README.md) corrects ten stage records: object investigations, item-start and supplied deliveries, and the mechanical-yeti input. Three explicitly profession-only records leave ordinary scope while catalogue facts/gaps remain. All remaining 56 IDs / 116 Horde / 142 Alliance actions survive; objective-gap union 6 → 3 represents two crystal closures and one profession gap excluded, not solved. Eight Winterspring and eight affected Eastern states preserve valid complete orders/endpoints but expose Alliance reward delays requiring review. All 109 zone regressions pass; global audit checks 11,831 points and source queue has 373 unresolved ordinary records.

The [Teldrassil review](teldrassil-2026-10-09/README.md) corrects thirteen records: supplied deliveries, distinct moonwell input/use/output stages, planter interaction and Ferocitas container hand-in semantics. Both Alliance chapters retain all 61 compiled IDs / 241 actions. Existing Crown pickup/return and jewel-opening gaps remain; newly identified Ban'ethil escape work raises the distinct gap union two to three. Eight complete same-facts states preserve actions/endpoints, but 1–10 log peak, uncertain travel and reward delays require review. All 115 zone regressions pass; native cave/escort/transport checks remain pending.

The [Tirisfal Glades review](tirisfal-glades-2026-10-09/README.md) corrects ten records: supplied class scroll/residue delivery, actual Rudolph head drop, termite input/use/return, burial input and six-victim interactions. All 96 compiled IDs remain; one explicit Discipline unknown-work placeholder raises actions 222/170/6 to 223/170/6. Two source gaps close and three event/choice/escort gaps become visible. Six class pickup conditions and two counts remain unverified. Marla's acquisition-before-burial order and Discipline's five-of-many target model are concrete shared-code review blockers. Full Tirisfal route guards require review; affected Western Plaguelands eight-state replay passes unchanged metrics.

The [Zephras Isle review](zephras-isle-2026-10-09/README.md) corrects two racial-use instructions without inventing items, spell IDs or counts. Standard and Skyborn/Ironborn captures retain 132 compiled IDs across all faction/race branches; 32 same-facts states preserve complete actions/endpoints and unchanged metrics. Two all-stage quest gaps and eight uncertain pickup IDs remain. Island access/transport and generic ability tooltip wording require native/coordinated review. All 126 zone regressions pass.

## Main release integration

[0.8.62](release-0.8.62-2026-10-09/README.md) integrates all reviewed zone facts
and adds complete-journey safeguards to the initial geometric optimization.
[Dustwallow Marsh](dustwallow-marsh-2026-10-09/README.md) includes faction object
pickups, supplied deliveries and explicit gossip-placeholder exclusions. Original
source comparisons and unresolved coordination proposals remain available.
