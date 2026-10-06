# Dungeon card artwork

0.8.22 references Blizzard client textures; it does not redistribute the images.
Dungeon cards stretch one image across the full card at uniform 14% opacity.
The one-pixel border, text and controls stay above the decoration. Original
generated zone-card motifs remain separate, in `Media/GuideThemes/ARTWORK.md`.

## Runtime selection

The optional native journal read uses `EJ_GetInstanceByIndex(index, false)`
and `EJ_GetInstanceInfo(id)` from the current journal tier. It does not open the
journal, select an instance or change tiers. Exact known names/aliases join the
returned artwork to dungeon cards. Enumeration is capped at 128 entries and
batched in groups of 16; it starts only when a dungeon card needs artwork outside
combat. Completion repaints visible cards; ordinary layout does not poll APIs.

Artwork candidates are native journal background/button, published dungeon
filenames, then `Interface\LFGFrame\UI-LFG-BACKGROUND-DUNGEONWALL` (file ID
337489). `Texture:SetTexture` has a documented boolean success result; a failed,
restricted, missing or thrown result tries the next candidate. If none loads,
the ordinary dark card remains. No in-game network requests occur. A true texture
result does not prove that a particular beta build rendered the correct picture.

Classic journal button illustrations occupy part of a padded 256×128 canvas.
The cropped interior is x=6–168, y=6–90, then stretched over the entire card.
Crop bounds were visually checked on publicly displayed Ragefire Chasm, Wailing
Caverns and Shadowfang Keep journal images for the host preview. Preview source
images are not included in the repository or addon release. Other client images
use full bounds. `C_Texture.GetFilenameFromFileDataID` identifies this button
format when available; missing capability preserves full image bounds.

## Published filename references: 23 of 28 complexes

These references establish filenames, not installation on the running beta.
Classic primary paths have prefix
`Interface\EncounterJournal\UI-EJ-DungeonButton-`; secondary paths have prefix
`Interface\LFGFrame\LFGICON-`. Extensions are omitted for native texture lookup.

| Dungeon | Journal suffix | LFG suffix |
| --- | --- | --- |
| Blackfathom Deeps | BlackfathomDeeps | BLACKFATHOMDEEPS |
| Blackrock Depths | BlackrockDepths | BLACKROCKDEPTHS |
| Blackrock Spire | BlackrockSpire | BLACKROCKSPIRE |
| Dire Maul | DireMaul | DIREMAUL |
| Gnomeregan | Gnomeregan | GNOMEREGAN |
| Maraudon | Maraudon | MARAUDON |
| Ragefire Chasm | RagefireChasm | RAGEFIRECHASM |
| Razorfen Downs | RazorfenDowns | RAZORFENDOWNS |
| Razorfen Kraul | RazorfenKraul | RAZORFENKRAUL |
| Scarlet Monastery | ScarletMonastery | SCARLETMONASTERY |
| Scholomance | Scholomance | SCHOLOMANCE |
| Shadowfang Keep | ShadowfangKeep | SHADOWFANGKEEP |
| Stratholme | Stratholme | STRATHOLME |
| The Deadmines | Deadmines | DEADMINES |
| The Stockade | TheStockade | STORMWINDSTOCKADES |
| Sunken Temple | SunkenTemple | SUNKENTEMPLE |
| Uldaman | Uldaman | ULDAMAN |
| Wailing Caverns | WailingCaverns | WAILINGCAVERNS |
| Zul'Farrak | ZulFarrak | ZULFARAK |

Forever paths have prefix
`Interface\Glues\LOADINGSCREENS\Camelot160\Main\LoadScreen_Camelot_`.

| Dungeon | Suffix | File ID |
| --- | --- | --- |
| City of Dalaran | Dalaran | 7963775 |
| Excavation Site: Wetlands | Excavation | 7963777 |
| Hall of Thanes | OldIronforge | 7963781 |
| Ruins of Lordaeron | RuinsofLordaeron | 7963782 |

No unique filename was verified for Alcaz Prison, Blackmaw Hold, Krol'dok
Stronghold, Shaper's Terrace or The Drowned City. Those cards use a native
journal image if exposed, otherwise the neutral official background. Unknown
future dungeons use the same fallback; an unrelated dungeon image is not assigned.

## Sources and reproduction

Checked 6 October 2026. Sources provide UI/API contracts and filename metadata;
they do not grant redistribution rights to Blizzard's artwork.

- [Gethe/wow-ui-source Forever snapshot](https://github.com/Gethe/wow-ui-source/tree/a84e2b1b41d3d4137127c07e4da448aa3251d6f1):
  `Interface/AddOns/Blizzard_EncounterJournal/Mainline/Blizzard_EncounterJournal.lua`
  shows the journal return positions (instance ID/name and fifth-return button;
  third-return background from `EJ_GetInstanceInfo`). Captured SHA256:
  `b4e31fc68be7db95cdbcf0395b106d4d97ab0a0cb853d03de6f674c287f4145e`.
  `Interface/AddOns/Blizzard_APIDocumentationGenerated/SimpleTextureBaseAPIDocumentation.lua`
  documents `SetTexture` success; `TextureUtilsDocumentation.lua` documents
  `C_Texture.GetFilenameFromFileDataID`.
- [wowdev/wow-listfile snapshot](https://github.com/wowdev/wow-listfile/tree/2ee24a9d0ff98f614997587e32ee6a0074d0de65):
  `parts/interface.csv` contains the 19 Classic journal/LFG names, neutral
  background and four Forever loading images. Captured SHA256:
  `f41981d597d1826d836909ca270ff699cb0cf169243eab9e959907370e1133f4`.
  Each row is `fileDataID;filename`. Only filename facts are used; no textures
  or source addon code are copied into this module.
- [Blizzard UI Add-On Development Policy](https://us.forums.blizzard.com/en/wow/t/ui-add-on-development-policy/24534).
  Artwork remains Blizzard's property. Referencing client assets is distinct
  from packaging downloaded images; no external image reuse license is claimed.

The Wowhead Forever dungeon overview includes screenshots, but we did not verify
redistribution terms for those images. No screenshots are bundled as substitutes.
The supplied host-rendered preview illustrates this layout using publicly
displayed official journal images; fonts/icons and character state are examples,
not an in-game beta capture.

## Beta checks

`/wt probe` reports native journal and filename capabilities plus counts of
specific/neutral images resolved in the session. Check each dungeon's actual
appearance, resize, scrolling, tab reuse and combat on the build in front of you.
Host Lua 5.1 checks cover selection/fallback, sizing, card reuse, restricted
data, cache refresh and preservation of guides; they cannot prove native asset
availability or rendered output. The five unresolved filenames remain explicit.
