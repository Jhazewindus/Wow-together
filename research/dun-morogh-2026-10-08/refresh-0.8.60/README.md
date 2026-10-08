# Dun Morogh follow-up review — 8 October 2026

Main subsequently advanced to 0.8.61; see the [combined integration review](integration-0.8.61/README.md) for inherited session/lifecycle checks and final validation.

The repeated assignment continues `guides/coverage` at `8371d24`, retaining main
`eec9b99` (0.8.60) and the earlier correction commit `2aa164c`. This follow-up
changes research/documentation only. Packed quest data is byte-identical to the
last combined full-suite source; all earlier zone work remains intact.

## Refreshed evidence and complete captured scope

All 24 pinned QuestieDB files and 57 prior quest-page captures passed SHA-256
verification. Twenty-two priority/hub/handoff quest pages, thirteen linked entity
pages and the current 60-entry Dun Morogh category list were freshly captured.
Adjacent files retain typed facts, URLs, capture dates, hashes and source tiers.
Downloaded scripts were not executed and guide prose was not copied. The parent
review retains the same-day secondary findings and recorded source denials.

Standard and dwarf captures retain **55 distinct quests and 151/30 actions** in
the two existing chapters. Class templates do not imply suitability for every
actor. The category-only records are repeatables 308/403, edition-only 5841 and
later handoffs 466/467. Preserve existing exclusions, useful prerequisite
exceptions, group warnings, chapter transitions and the full fixed action set.
No terrain shortcut or personal flight unlock is established by this review.

## Priority checks

- **Treacherous Cold 99162 → Rime's Wrath 99161:** retain the actual predecessor
  hand-in and exact tester provenance: 7 October 2026, level 7 Alliance dwarf,
  client build 70245, addon 0.8.42. Fresh web pages do not independently establish
  this gate, so the observation is not relabeled as a verified web prerequisite.
- **Distinct Rime identities:** 99160 requires ten Minor Ice Elementals 276003;
  99161 requires one Avala's Core 286325 from Avala 276009. Keep both quest IDs,
  distinct work and quantities. Three distinct rifle items remain for 99162.
  Recent no-loot/relog comments describe beta interaction failures, not a new
  dependency, proof of completion or permission to permanently skip work.
- **Winter Wolf 1131:** the fresh NPC page retains a broad Chunk of Boar Meat 769
  loot relation. Stocking Jetsteam 317 still requires four meat and two Thick
  Bear Furs 6952. Source-list sample counts are not guaranteed drops or quest
  quantities. No generic monster layer or raid/star marker is restored. Keep
  native-false vetoes and accepted, readable, unfinished-objective checks.
- **The Quarry's Smith 95217:** retain the reviewed Scarred Crag Boar 1689 point
  at 73.8,52.6, four hides 267416, twelve Copper Bars 2840 and the missing Copper
  acquisition flag. NPC 1698 is Frast Dokner, a distinct pickup/hand-in entity;
  it must not be mistaken for the boar or an invented Copper vendor.
- **Starter hubs:** preserve the compiled pickups, objective pairing and real
  hand-ins. Fresh quarry/hub comments support overlapping work and existing
  item-started notes, but do not establish universal unlocks, spawn rates or
  minimum drop quantities. An 8 October leopard-spawn/drop complaint is a
  dated observation, not a reason to change required counts or discard work.

The prior player checklist and 55 focused checks cover dwarf/gnome fresh and
mid-progress orders, actual gates, marker vetoes, offers, personal skips and
unresolved starters. Native beta offers/rendering still require player checks.

## Remaining facts and later handoff

Pickup/objective/hand-in gaps remain **1/1/0**, with **one unverified pickup
condition** and no recorded unknown objective quantities. Treaty 98423's item
starter 281030 has no typed acquisition position. The repeated vault comment is
secondhand and provides no exact source ID/coordinate; Magni's hand-in cannot
stand in for the pickup. Copper Bar pages still list remote Fel Interlopers and
crafting sources rather than a verified local acquisition for every eligible
character. Senir 282's additional offer conditions remain unknown; preserve its
predecessor 218 and distinct same-title 420. No further gap closes.

**Search for Incendicite 466** is level 22/min 20, starts/ends at Pilot Stonegear 1377
in Dun Morogh and requires six Incendicite Ore 3340 from the retained Wetlands
work. **Stonegear's Search 467** is level 23/min 20, starts at Mountaineer Kadrell 1340
in Loch Modan or Pilot Longbeard 2092 in Ironforge, and ends at Stonegear. Both
records and pickup alternatives remain in the catalogue. A current comment gives
a mining/AH acquisition lead and cave entrance; it is not a surveyed Forever
route or evidence that the ordinary quest must become profession-only.

The shared `LevelingGuides.lua:localWork` rule excludes 466's remote-only work from
the Dun Morogh chapter;467's primary pickup is outside Dun Morogh. No 21–30 zone
section appears in the captured scope. This useful later pickup/handoff needs a
main-developer inclusion decision if it should be visible from the originating
zone. Do not silently claim the 181 captured actions cover all terrain or all
useful later pickups, relabel levels, or change the shared compiler here.

## Route comparison and validation

The historical pre-boar-correction captures still match current runtime hashes.
Both complete orders were repriced with the retained corrected facts. All 16
candidate and baseline states are valid; all actions and endpoints survive.
An identical-order replay passes. This documentation-only follow-up does not
change route order itself.

The earlier correction's estimates remain 110,330.68 → 108,044.93 travel, log
peak 8 → 10, XP deficit 6,700 unchanged, reward XP before work 432,255 → 411,915,
and uncertain legs 25 → 26. Rewards precede work later for 319/320/412/413/415/417/
419/95212 in at least one state. The 11–20 chapter stays unchanged. Both strict
optimization guards require review; exact metrics are retained beside this file.
These are host estimates without native geometry, surveyed approaches or flight
unlock observations. Main handles any coordinated routing/eligibility/lifecycle
or UI change; no such module was authored here.

All **55 focused tests** pass and all **84 TOC Lua files** compile under
Lua 5.1/interface 16001. The refreshed two-section audit passes 164 source points.
The combined branch's last full run passed 1,492 of 1,493 checks; the sole failure
is the known historical catalogue fingerprint assertion, with fixture unchanged.
At that baseline, subsequent guide commits had changed only research/docs. Host checks do not certify native
beta availability, safe terrain or actual quest completion timing.

## Player checklist

Run the [original full Dun Morogh checklist](../README.md#player-checklist),
recording build, addon revision, race/class/level, party and class-setting context.

1. Hand in all three Treacherous Cold rifles before 99161; verify 99160's separate
   ten-elemental objective. Record actual offers and IDs, not only titles.
2. Check Winter Wolf hints with 317 accepted, meat unfinished/completed and native
   true/false flags. Unrelated or completed work must produce no generic marker.
3. Verify the retained boar point/counts, record Copper's actual acquisition,
   Treaty starter and Senir offers. Preserve temporary deferrals and personal
   skips through Scan/reload/zone entry; unfinished work must prevent false completion.
4. Complete both applicable full chapters and neighbouring-zone handoffs. On a
   suitable level 20+ character, record 466/467's actual pickups, ore acquisition
   and cave approach for the main developer's coverage decision. Report terrain,
   reward timing and log pressure rather than assuming host estimates are optimal.
