# Third-party notices

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

Changes: select numeric IDs, short entity/quest names, explicit relations,
quantities and spawn coordinates; retain only identity-matched unchanged quest
fallbacks; convert proven map points; select actual representative spawns;
annotate source provenance. No source server logic, SQL execution, scripts,
quest descriptions or third-party addon engine/UI are included.

Additional Forever NPC geographic facts come from the same MIT Mapzeroth
revision cited above (`Data/Forever/Pois.lua`, SHA256
`3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d`).
Only NPC IDs and normalized coordinates are read, not the addon engine.
