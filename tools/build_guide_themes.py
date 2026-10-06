"""Compile the original 2-column/8-row landscape atlas into WoW card textures.

Pillow is needed only to regenerate the checked-in artwork. The addon loads
the resulting power-of-two, uncompressed BGRA TGA files directly.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'WowTogether' / 'Media' / 'GuideThemes'
THEMES = ('woodland', 'haunted', 'prairie', 'canyon', 'savanna', 'desert',
          'snow', 'mountains', 'jungle', 'marsh', 'volcanic', 'blighted',
          'farmland', 'coast', 'settlement', 'ruins')


def main():
    from PIL import Image, ImageStat
    source = MEDIA / 'source-atlas.png'
    image = Image.open(source).convert('RGB')
    textures = []
    for index, theme in enumerate(THEMES):
        column, row = index % 2, index // 2
        bounds = (round(column * image.width / 2), round(row * image.height / 8),
                  round((column + 1) * image.width / 2), round((row + 1) * image.height / 8))
        tile = image.crop(bounds).resize((512, 128), Image.Resampling.LANCZOS)
        # Equalize perceived strength between bright snow and dark woodland.
        light = ImageStat.Stat(tile.convert('L')).mean[0]
        opacity = min(.34, .24 * 100 / max(1, light))
        values = []
        for x in range(512):
            position = max(0, min(1, (x / 511 - .30) / .55))
            values.append(round(255 * opacity * position * position * (3 - 2 * position)))
        alpha = Image.new('L', tile.size)
        alpha.putdata(values * 128)
        tile = tile.convert('RGBA'); tile.putalpha(alpha)
        path = MEDIA / (theme + '.tga')
        tile.save(path, compression=None)
        textures.append({'theme': theme, 'file': path.name, 'source_bounds': bounds,
                         'size': [512, 128], 'max_alpha': max(values),
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {'schema': 1, 'source': source.name,
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'textures': textures}
    (MEDIA / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Compiled', len(textures), 'faded original guide-card textures.')


if __name__ == '__main__':
    main()
