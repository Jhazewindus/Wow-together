# Third-party notices

Guide-card landscape artwork is generated specifically for this project;
no downloaded third-party images are included in that collection. See
`Media/GuideThemes/ARTWORK.md` for its provenance and source atlas.

Dungeon cards reference Blizzard artwork already in the client. Blizzard owns
those assets; no Blizzard image files are redistributed in this addon and the
repository license does not license them. Native APIs and published filename
metadata are attributed in [DUNGEON_ARTWORK.md](DUNGEON_ARTWORK.md). No external
Wowhead image or screenshot is bundled.

Geographic travel facts adapted from [Mapzeroth](https://github.com/tr0tsky0/Mapzeroth),
Forever 0.6.0 (`fd68cfe2153379898680c66a01833846f9933587`). Its addon engine/UI is not included.
The project publishes this license:

```text
MIT License

Copyright (c) 2026 tr0tsky0

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Older-world factual fallback

Numeric/name facts adapted from CMaNGOS classic-db, pinned revision
`ec4f596146be6467ea93c57397858e329e2db852`, snapshot
`Full_DB/ClassicDB_1_12_1_z2815.sql.gz`:
https://github.com/cmangos/classic-db/tree/ec4f596146be6467ea93c57397858e329e2db852

The source is distributed under GPL version 3. The extracted/adapted factual
catalogue data is supplied in editable Lua source with its source revision,
checksum and transformations documented in QUEST_DATA.md. See
LEGACY_DATA_LICENSE.txt for the full upstream license and
LEGACY_DATA_COPYRIGHT.md for its Blizzard content/copyright notice.
The original addon code retains the repository's Apache-2.0 license.

Version 0.8.27 also selects interior creature/object spawn coordinates from
this same licensed snapshot. Explicit client floor rectangles transform only
unambiguous spawns; no source server/event logic is copied or evaluated.
Factual client encounter positions, map/floor IDs and rectangles come from
`eXPeRi91/ClientDB-Diff` revision
`ac1d02cba59374c5d599f78ede0cd3984f4312a1`. CSV URLs/checksums, transformations
and unresolved positions are documented in DungeonMapData.json and
DUNGEON_VIEWER.md. The CSV metadata is factual game data, not copied code/art.
These older Classic references still require Forever beta verification.

Changes: select numeric IDs, short entity/quest names, explicit relations,
quantities, spawn coordinates and the player XP-per-level baseline (estimate only); retain only identity-matched unchanged quest
fallbacks; convert proven map points; select actual representative spawns;
annotate source provenance. No source server logic, SQL execution, scripts,
quest descriptions or third-party addon engine/UI are included.

Additional Forever NPC geographic facts come from the same MIT Mapzeroth
revision cited above (`Data/Forever/Pois.lua`, SHA256
`3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d`).
Only IDs, settlement/faction labels and normalized coordinates are read, not
the addon engine. Version 0.8.7 also uses these facts for optional service tips;
GuideServiceData.json records the scope. Neutral settlement ownership is not
used as proof of a flight master's faction.

## Published Forever facts

Factual IDs, short names, counts, relationships, map bounds, explicit patrol paths and coordinates
were selected from Questie/QuestieDB revision
`e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`:
https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6

The selected source files and SHA256 values are in
`data-tools/forever_source_manifest.json` in the release and
`tools/forever_source_manifest.json` in this repository. Literal data parsing
does not run their providers. No source engine, UI, route logic, functions or
quest prose is included. The inspected source does not provide an explicit
license file; no license grant is asserted for that source. This selection
contains factual game data, rather than copied implementation.

Narrow coordinate observations from public Wowhead Forever comments retain
quest/comment IDs for attribution in the coverage report. Comment prose and
artwork are excluded; observations are labeled as needing beta verification.

## Dungeon viewer facts (0.8.24)

DungeonJournalData records factual NPC/item IDs, names, levels and loot relationships
from captured Wowhead Forever zone/NPC pages; the provenance manifest contains each
URL and SHA-256. Website scripts, editorial prose and image files are not bundled.
Map/portrait/icon filenames reference Blizzard client assets checked against the
public wowdev filename list. Blizzard retains its artwork rights; this project's
MIT license does not license Blizzard textures or preview images. See
DUNGEON_VIEWER.md for source versions, scope and beta limitations.
