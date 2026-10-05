"""Repeatable Lua 5.1 host benchmarks, call counts and output fingerprints.

Uses the same fixtures as the host tests. Timings do not measure beta FPS or
native API costs. Run sequentially on an idle host when comparing releases.
"""
import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_addon import Client
from test_routes import map_canvas
from test_068 import maps


def client():
    c = Client(quests=(789, 792, 4402, 97279), completed=(788, 4641), use_catalogue=True)
    c.guide_environment(level=12)
    c.lua.globals().grouped = False
    c.lua.execute("function UnitClass() return 'Shaman','SHAMAN',7 end; function UnitRace() return 'Orc','Orc',2 end")
    c.ns.ReadProfile()
    c.ns.profile.mapID = 1411
    c.unit_names({'player': ('Alice', 'Test Realm')})
    map_canvas(c)
    c.lua.execute('C_Map.GetMapWorldSize=function() return 5000,3500 end')
    return c


def median_ms(callback, repeats=5):
    callback()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        callback()
        samples.append((time.perf_counter() - start) * 1000)
    return round(statistics.median(samples), 3)


def instrument(c):
    c.lua.globals().perfNS = c.ns
    c.lua.execute('''
    perfCalls={}
    local function wrap(t,k,label)
      local fn=t[k];if type(fn)~='function' then return end
      t[k]=function(...) perfCalls[label]=(perfCalls[label] or 0)+1;return fn(...) end
    end
    for _,k in ipairs({'PartyProfiles','Completed','CatalogueRecord','GuideRecord',
      'WalkingDistance','LearnedPrerequisiteIDs','BuildFixedGuideRoute'}) do wrap(perfNS,k,k) end
    wrap(_G,'GetBuildInfo','GetBuildInfo')
    wrap(C_QuestLog,'IsQuestFlaggedCompleted','IsQuestFlaggedCompleted')
    for _,k in ipairs({'GetMapWorldSize','GetWorldPosFromMapPos','GetMapPosFromWorldPos'}) do wrap(C_Map,k,k) end
    ''')


def calls(c, callback):
    c.lua.execute('perfCalls={}')
    callback()
    return dict(c.lua.globals().perfCalls.items())


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def benchmark():
    c = client()
    guide = c.ns.ZoneGuideForMap(1412, True)
    result = {'environment': 'Lua 5.1 host mocks; timing is not in-game FPS',
              'catalogue': c.ns.catalogue.count}
    result['browse_ms'] = median_ms(c.ns.LevelingGuideChoices)
    result['zone_digest'] = digest('|'.join(g.key + ':' + ','.join(str(r.id) for r in g.records.values())
                                          for g in c.ns.LevelingGuideChoices().values()))
    compile_guide = lambda: c.ns.GenerateFixedGuide(guide, False)
    progress = lambda: c.ns.BuildFixedGuideRoute(guide, False)
    result['compile_mulgore_ms'] = median_ms(compile_guide, 3)
    result['fixed_digest'] = digest('|'.join(':'.join(str(s[k]) for k in ('id', 'kind', 'mapID', 'x', 'y', 'guideStep'))
                                           for s in guide.fixedPlan.values()))
    compile_guide()
    result['progress_ms'] = median_ms(progress)
    c.ns.routeSelection, c.ns.selectedRoute, c.ns.filter = guide, progress(), 'guides'
    result['dashboard_refresh_ms'] = median_ms(c.ns.Refresh)
    instrument(c)
    for name, callback in (('browse', c.ns.LevelingGuideChoices), ('compile', compile_guide),
                           ('progress', progress), ('dashboard_refresh', c.ns.Refresh)):
        result[name + '_calls'] = calls(c, callback)

    m = client()
    maps(m)
    m.ns.db.config.fullRoute = True
    stops = [{'id': 789, 'kind': 'q', 'mapID': 501 if i % 2 else 502,
              'x': .1 + (i % 80) * .01, 'y': .4, 'title': 'Map benchmark', 'label': 'Benchmark'}
             for i in range(240)]
    m.ns.selectedRoute = m.lua.table_from({'mapID': 501, 'stops': stops}, recursive=True)
    m.ns.routeSelection = m.lua.table_from({'key': 'benchmark-map', 'title': 'Benchmark', 'records': []}, recursive=True)
    m.ns.routePaused, m.ns.routePlanning = None, None
    m.ns.AttachRouteProvider()
    world = m.lua.globals().WorldMapFrame
    world.SetMapID(world, 10)
    m.ns.DrawRoute()
    result['full_map_redraw_ms'] = median_ms(m.ns.DrawRoute)
    instrument(m)
    result['map_calls'] = calls(m, m.ns.DrawRoute)
    result['arrow_calls'] = calls(m, lambda: [m.ns.NavigationState() for _ in range(20)])
    result['map_geometry_digest'] = digest('|'.join(str(m.ns.routeProvider.lines[i][anchor][j])
        for i in range(1, m.ns.routeStats.lines + 1) for anchor in ('startPoint', 'endPoint') for j in (3, 4)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Also save the JSON report to this path.')
    args = parser.parse_args()
    report = json.dumps(benchmark(), indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(report)
    print(report, end='')


if __name__ == '__main__':
    main()
