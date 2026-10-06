"""Retained Lua 5.1 heap across real data loads and representative host actions.

Full collection occurs only in this external measurement harness. It is never
added to the addon. Results exclude native frames/textures and client attribution.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_addon import Client, MOCK
from lupa.lua51 import LuaRuntime


def sources(ref=None):
    def read(name):
        if ref:
            return subprocess.check_output(['git', 'show', ref + ':WowTogether/' + name], cwd=ROOT).decode()
        return (ROOT / 'WowTogether' / name).read_text()
    toc = read('WowTogether.toc')
    return {name: read(name) for name in toc.splitlines() if name.endswith('.lua')}


def measure(source):
    c = Client.__new__(Client)
    c.lua = LuaRuntime(unpack_returned_tuples=True)
    c.lua.execute(MOCK)
    c.lua.globals().player, c.lua.globals().peer = 'Alice', 'Bob'
    c.lua.globals().grouped = False
    c.ns = c.lua.table()
    def retained():
        c.lua.eval('collectgarbage')('collect')
        return round(c.lua.eval('collectgarbage')('count') / 1024, 3)
    previous, per_file = retained(), []
    for name, text in source.items():
        c.lua.execute('assert(loadstring(...))(select(2, ...))', text, 'WowTogether', c.ns)
        total = retained()
        per_file.append({'file': name, 'mib': round(total - previous, 3)})
        previous = total
    result = {'after_files_mib': retained(), 'file_deltas': per_file}
    c.ns.handlers.ADDON_LOADED('WowTogether')
    result['startup_mib'] = retained()
    c.guide_environment(level=12)
    c.lua.execute("function UnitClass() return 'Shaman','SHAMAN',7 end; function UnitRace() return 'Orc','Orc',2 end")
    c.ns.ReadProfile(); c.ns.profile.mapID = 1411
    c.ns.LevelingGuideChoices()
    c.ns.LibraryItems()
    result['browse_mib'] = retained()
    guide = c.ns.ZoneGuideForMap(1412, True)
    c.ns.GenerateFixedGuide(guide, False)
    c.ns.ActivateRoute(guide, c.ns.BuildFixedGuideRoute(guide, False))
    result['guide_mib'] = retained()
    c.ns.ShowDungeonViewer('wailing-caverns', True)
    c.drain()
    result['dungeon_mib'] = retained()
    for _ in range(20):
        c.ns.Refresh(True); c.ns.LibraryItems(); c.ns.DungeonViewerData('wailing-caverns')
        c.drain()
    result['repeated_use_mib'] = retained()
    if c.ns.PackedDataStats:
        result['compartments'] = [dict(v.items()) for v in c.ns.PackedDataStats().values()]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', help='Compare with a committed addon revision.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = {'environment': 'Lua 5.1 host, retained heap after collection; not in-game addon memory',
              'current': measure(sources())}
    if args.baseline_ref:
        result['baseline_ref'] = args.baseline_ref
        result['baseline'] = measure(sources(args.baseline_ref))
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
