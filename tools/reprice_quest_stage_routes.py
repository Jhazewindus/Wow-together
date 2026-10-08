"""Compare old/new complete orders under identical corrected quest facts.

For data reviews, unlike audit_quest_flow's identical-source optimizer test.
Retain every (quest, stage, occurrence), substitute the current stage facts into
both orders, and report regressions without changing the guide engine.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

from audit_quest_flow import Client, ROOT

FIELDS = ('distance', 'peakLog', 'levelDeficitXP', 'questXP', 'rewardXPBeforeWork',
          'uncertainTravelLegs', 'difficultyPressure', 'blockedTravelLegs')


def compare(before, after):
    if before.get('geometry_source') or after.get('geometry_source'):
        raise ValueError('This replay requires both captures to use the default host geometry')
    for key in ('zone', 'travel_sha256', 'terrain_data_sha256', 'flow_module_sha256',
                'optimizer_module_sha256', 'fixed_guides_sha256', 'fixed_travel_cost_sha256',
                'travel_network_sha256', 'terrain_geometry_sha256'):
        if before.get(key) != after.get(key):
            raise ValueError('Comparison changed more than stage facts: ' + key)
    for key, file in (('catalogue_sha256', 'QuestCatalogue.lua'), ('travel_sha256', 'TravelData.lua'),
                      ('terrain_data_sha256', 'TravelTerrainData.lua'), ('flow_module_sha256', 'QuestFlow.lua'),
                      ('optimizer_module_sha256', 'FixedRouteOptimizer.lua'), ('fixed_guides_sha256', 'FixedGuides.lua'),
                      ('fixed_travel_cost_sha256', 'FixedTravelCost.lua'), ('travel_network_sha256', 'TravelNetwork.lua'),
                      ('terrain_geometry_sha256', 'TravelTerrain.lua')):
        if after[key] != hashlib.sha256((ROOT / 'WowTogether' / file).read_bytes()).hexdigest():
            raise ValueError('Candidate capture does not match current source: ' + file)
    prior = {(g['faction'], g['key']): g for g in before['guides']}
    current = {(g['faction'], g['key']): g for g in after['guides']}
    if not current or set(prior) != set(current):
        raise ValueError('Complete guide scope changed')
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=1); c.lua.globals().grouped = False
    result = []
    for key, candidate in current.items():
        original = prior[key]
        c.ns.profile.faction, c.ns.profile.classID, c.ns.profile.raceID = key[0], 8, original['race']
        counts, tokens, anchors = collections.Counter(), {}, {}
        for point in candidate['stops']:
            stop = c.lua.table_from(point)
            counts[stop.id, stop.kind] += 1
            tokens[stop.id, stop.kind, counts[stop.id, stop.kind]] = stop
            if stop.unknownLocation:
                stop.planningAnchor = anchors.get(stop.id)
            else:
                anchors[stop.id] = stop
        counts.clear(); old_order = []
        for stop in original['stops']:
            ident, kind = stop['id'], stop['kind']; counts[ident, kind] += 1
            token = ident, kind, counts[ident, kind]
            if token not in tokens:
                raise ValueError('Required action removed: ' + str(token))
            old_order.append(tokens[token])
        if len(old_order) != len(tokens):
            raise ValueError('Required action scope changed')
        old, new = c.lua.table_from(old_order), c.lua.table_from(list(tokens.values()))
        cache = c.lua.table()
        metric, _ = c.ns.NewFixedTravelCost(lambda a, b: c.ns.FixedGuideGeometry(a, b, cache), False, None)
        low, high = map(int, key[1].rsplit(':', 1)[1].split('-'))
        middle = (low + high) // 2
        states = {(low, 0), (middle, 0), (high, 0), (middle, int(c.ns.xpBaseline[middle] // 2))}
        comparisons = []
        for level, xp in sorted(states):
            model = c.ns.NewGuideFlowModel(old, metric, c.lua.table_from({'startLevel': level, 'startXP': xp}))
            a, b = model.evaluate(old), model.evaluate(new)
            delayed = [{'questID': int(s.id), 'objectiveKey': s.objectiveKey,
                        'before': a.workRewards[s], 'after': b.workRewards[s]}
                       for s in new.values() if s.kind == 'q' and b.workRewards[s] < a.workRewards[s]]
            worse = [f for f in FIELDS if (b[f] < a[f] if f in ('questXP', 'rewardXPBeforeWork')
                                          else b[f] > a[f] + .001)]
            comparisons.append({'level': level, 'xp': xp, 'valid': bool(b.valid),
                                'metrics': {f: {'before': a[f], 'after': b[f]} for f in FIELDS},
                                'regressed_metrics': worse, 'delayed_work_rewards': delayed})
        endpoints = lambda g: [(s['id'], s['kind']) for s in (g['stops'][0], g['stops'][-1])]
        result.append({'faction': key[0], 'key': key[1], 'actions_preserved': len(old_order),
                       'endpoints_preserved': endpoints(original) == endpoints(candidate),
                       'states': comparisons})
    return {'scope': 'Complete old and new orders, both repriced with corrected stage facts and default host geometry.',
            'catalogue_sha256': after['catalogue_sha256'], 'guides': result,
            'passes_optimization_guard': all(g['endpoints_preserved'] and s['valid'] and not s['regressed_metrics'] and not s['delayed_work_rewards']
                                            for g in result for s in g['states'])}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', type=Path, required=True)
    p.add_argument('--after', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    report = compare(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Optimization guard:', 'PASS' if report['passes_optimization_guard'] else 'REVIEW REQUIRED')
    raise SystemExit(0 if report['passes_optimization_guard'] else 2)
