# Westfall refresh, 10 October 2026

Refreshed on `guides/coverage`, based on main
`cbd1e7608dc32c2080d8b1d967fb577c10084053` (addon 0.8.65). The detailed
9 October source research, corrections, full category inventory, and explicit
coordination proposals remain in
[`../westfall-2026-10-09/README.md`](../westfall-2026-10-09/README.md).
That review's corrections are already present; no new fact is supported by
evidence in this refresh.

## Refreshed scope and gaps

The standard scoped audit checks 112 source points across three faction/chapter
guides: Horde 11–20 (24 actions), Alliance 1–10 (26), and Alliance 11–20
(127). The 54-record Westfall category and the separate Skyborn (race 95)
scope remain distinguished; Skyborn contributes 26 / 224 actions across its
two Alliance chapters and is captured separately because the standard audit
does not enumerate that custom race.

The supplied snapshot lists objective gap 92749. Refreshing the repository
baseline shows **two**: 92749 and 92819. Pickup, hand-in, uncertain pickup
requirement and quantity gaps remain zero. Quest 92749 still needs supported
acquisition/location instructions for ten Coarse Dynamite (4365); Sprite
Jumpsprocket's Stormwind position is a pickup/recipient, not a farm location.
Quest 92819's source-described detonator work remains unknown; do not replace
it with a conversation at its giver or borrow the distinct 92753 explosive
placement. The two-gap count exposes unknown work rather than inventing facts.

Other reviewed boundaries remain: distinct Alba IDs and the 92747 level
conflict; Odd Child's continent-level marker without exact Westfall spawn;
Captain Sander's four exact treasure-object interactions; actual Defias chain
hand-ins before 166; recipe/material prerequisite 36→38; dungeon and optional
handoff support; Horde scope as neutral coast/treasure work; and the actual
94947 hand-in before Skyborn 98021. The previous review retains source URLs,
IDs, hashes, source tiers, before/after records and all 54 direct category
records. There is no new source capture or native-beta observation here.

## Current full-route estimates

The current 0.8.65 host flow captures every action in the standard and Skyborn
scopes. Distances are estimates, not measured travel or proof of safe roads or
personal flight access.

| Scope | Faction and chapter | Actions | Distance estimate | Log peak | XP shortfall | Uncertain legs | Reward XP before work |
|---|---|---:|---:|---:|---:|---:|---:|
| Standard | Horde 11–20 | 24 | 20,489 | 2 | 46,760 | 9 | 25,390 |
| Standard | Alliance 1–10 | 26 | 96,913 | 3 | 11,480 | 8 | 14,000 |
| Standard | Alliance 11–20 | 127 | 136,480 | 6 | 52,780 | 37 | 692,370 |
| Skyborn | Alliance 1–10 | 26 | 96,913 | 3 | 11,480 | 8 | 14,000 |
| Skyborn | Alliance 11–20 | 224 | 239,495 | 6 | 65,780 | 37 | 2,227,023 |

The earlier 0.8.61 same-facts comparisons cover 12 standard and 8 Skyborn
starting states. They preserved all actions and endpoints and had unchanged
metrics within that compiler version; they validate preservation after the
data corrections, not optimization gains. These current 0.8.65 figures are a
new full-flow capture under the later main-branch engine. Do not treat
cross-version metric differences as a Westfall data change or apples-to-apples
route comparison. No Westfall candidate was changed in this refresh.

## Validation and player checklist

- Westfall focused regressions: 8/8 passed. Route/session regressions: 18/18
  passed.
- Standard scoped audit: three guides and 112 source points. Standard flow:
  three complete sequences valid. Separate Skyborn flow: two complete
  sequences valid.
- Lua 5.1 host load: all 87 TOC Lua files passed; interface remains 16001. No
  Lua source changed in this refresh.
- Native Forever beta behavior remains untested.

Player checklist: fresh and mid-zone Human, other Alliance races and Skyborn;
Horde neutral coast scope; chapter transitions, Scan/reload/zone entry; Sentinel
Hill offers and Alba's actual offers/positions; treasure map and each specific
object; wells' native sampling areas and counts; dynamite acquisition and 92819
detonator use; Deadmines instance/entrance, distinct dungeon quests and actual
155 hand-in before 166; Odd Child's exact spawn and safe approach; the actual
94947 hand-in before Skyborn 98021; class setting, escort adjacency and onward
handoffs. Missing offers must remain temporary deferrals and return after
confirmation; personal skips stay separate; accepted or deferred unfinished
work must not mark the guide complete.

Existing optional acquisition text, dungeon/presentation and unknown-objective
text proposals touch shared step or guide behavior. They remain unapplied until
coordinated with the main developer. No shared routing, eligibility, lifecycle
or UI code changed in this refresh.
