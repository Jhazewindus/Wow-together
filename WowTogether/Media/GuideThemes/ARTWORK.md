# Guide-card artwork

The sixteen landscape motifs were generated specifically for Wow Together on
6 October 2026 using OpenAI's image-generation tool. The source request called
for original generic landscape illustrations, without game screenshots,
franchised landmarks, logos, characters or third-party reference artwork.
No downloaded artwork or ambientCG asset is included in this collection.

`source-atlas.png` preserves the generated 2-column, 8-row source. The themes
are woodland, haunted woodland, prairie, canyon, savanna, desert, snow,
mountains, jungle, marsh, volcanic, blighted woodland, farmland, coast,
settlement and ruins. They provide atmosphere; they are not maps or accurate
depictions of any game's locations.

`tools/build_guide_themes.py` extracts the tiles, resamples each panorama to
512 x 128, and bakes a faint horizontal alpha fade into uncompressed 32-bit
TGA textures. The left portion is transparent to keep text readable. Bright
snow and darker forests receive different maximum opacity for similar visual
strength. `manifest.json` records source bounds, dimensions and SHA256 values.
The Lua card layer crops the panorama proportionally when a card resizes.

The repository license accompanies the release; no third-party CC0 license
or independent copyright clearance is asserted for generated artwork.
