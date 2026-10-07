"""Compare complete fixed guides from identical source/identity states.

Host Lua 5.1; distances are estimates, not observed play times. Baselines retain
every action so a shorter prefix cannot be mistaken for a faster full guide.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_addon import Client

FIELDS = ('id', 'kind', 'mapID', 'x', 'y', 'action', 'entityID', 'entityType',
          'objectiveKey', 'quantity', 'quantityUnknown', 'unknownLocation', 'planNeedsReview')


def compare_replay(model, original, candidate, key):
    before, after = model.evaluate(original), model.evaluate(candidate)
    assert after.valid, (key, 'invalid route')
    for field in ('peakLog', 'levelDeficitXP', 'minimumKills', 'difficultyPressure',
                  'missingLevelCurve', 'uncertainTravelLegs', 'blockedTravelLegs'):
        assert after[field] <= before[field], (key, field, 'regression')
    assert after.questXP >= before.questXP, (key, 'reward XP regression')
    assert after.rewardXPBeforeWork >= before.rewardXPBeforeWork, (key, 'earlier reward regression')
    for stop in candidate.values():
        if stop.kind == 'q':
            assert after.workRewards[stop] >= before.workRewards[stop], (key, stop.id, 'reward delayed before work')
    assert after.distance <= before.distance + 0.001, (key, 'complete journey regression')
    return before, after


def describe_actions(stops, ns, rewards=None):
    """Disambiguate repeated work stages in the published old/new evidence."""
    occurrences, result = collections.Counter(), []
    for index, stop in enumerate(stops, 1):
        occurrences[stop.id, stop.kind] += 1
        action = {field: stop[field] for field in FIELDS if stop[field] is not None}
        action.update(step=index, title=ns.CatalogueQuest(stop.id).title,
                      occurrence=occurrences[stop.id, stop.kind])
        if rewards is not None and stop.kind == 'q':
            action['quest_reward_xp_before_work'] = rewards[stop]
        result.append(action)
    return result


def capture(baseline=None, flow_module=None, label=None):
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=1)
    c.lua.globals().grouped = False
    c.ns.guideLevel = 'all'
    c.ns.db.config.classQuests = False
    c.ns.db.config.soloMode = True
    c.ns.ReadProfile()
    if flow_module:
        # Re-run our prior optimizer against the current corrected quest scope.
        # This is explicitly supplied project code, never downloaded source.
        c.lua.execute('assert(loadstring(...))(select(2, ...))',
                      flow_module.read_text(), 'WowTogether', c.ns)
    result, seen = [], set()
    old_guides = {(g['faction'], g['key']): g for g in baseline['guides']} if baseline else {}
    comparisons, starting_states_checked = [], 0
    for faction, races in (('Horde', (2, 6, 5, 8)), ('Alliance', (1, 3, 4, 7))):
        c.ns.profile.faction, c.ns.profile.classID = faction, 8
        for race in races:
            c.ns.profile.raceID = race
            for level in (1, 4, 8, 12, 18, 23, 33, 43, 53, 60):
                c.ns.profile.level = level
                for guide in c.ns.LevelingGuideChoices().values():
                    key = (faction, guide.key)
                    if key in seen:
                        continue
                    seen.add(key)
                    start = time.perf_counter()
                    c.ns.GenerateFixedGuide(guide, False)
                    stops = [{k: s[k] for k in FIELDS if s[k] is not None}
                             for s in guide.fixedPlan.values()]
                    metrics = {}
                    if c.ns.NewGuideFlowModel:
                        geometry_cache = c.lua.table()
                        metric, _ = c.ns.NewFixedTravelCost(lambda a,b: c.ns.FixedGuideGeometry(a,b,geometry_cache), False, None)
                        model = c.ns.NewGuideFlowModel(guide.fixedPlan, metric, None)
                        measured = model.evaluate(guide.fixedPlan)
                        metrics = {k: v for k, v in measured.items()
                                   if isinstance(v, (int, float, str, bool))}
                    result.append({'faction': faction, 'race': race, 'key': guide.key,
                                   'zone': guide.zone, 'start_level': guide.sectionLow or guide.minLevel,
                                   'flow_start_level': model.startLevel,
                                   'compile_ms': round((time.perf_counter() - start) * 1000, 2),
                                   'stops': stops, 'flow': metrics})
                    old = old_guides.get(key)
                    if old:
                        # Map equal per-quest action occurrences to the
                        # same Lua objects for a true permutation replay.
                        original = c.lua.table_from(old['stops'], recursive=True)
                        anchors, tokens, counters = {}, {}, collections.Counter()
                        for i,s in original.items():
                            if s.unknownLocation: s.planningAnchor = anchors.get(s.id)
                            else: anchors[s.id] = s
                            counters[s.id,s.kind] += 1
                            tokens[s.id,s.kind,counters[s.id,s.kind]] = s
                        counters.clear(); candidate=[]
                        for stop in guide.fixedPlan.values():
                            counters[stop.id,stop.kind] += 1
                            token=(stop.id,stop.kind,counters[stop.id,stop.kind])
                            assert token in tokens,(key,'added stage',token)
                            source=tokens[token]
                            assert all(source[f]==stop[f] for f in FIELDS),(key,'changed facts',token)
                            candidate.append(source)
                        assert len(candidate)==len(original),(key,'removed stage')
                        model=c.ns.NewGuideFlowModel(original,metric,None)
                        candidate_table=c.lua.table_from(candidate)
                        before,after=compare_replay(model,original,candidate_table,key)
                        low=int(guide.sectionLow or guide.minLevel or model.startLevel)
                        high=int(guide.sectionHigh or guide.maxLevel or low)
                        middle=(low+high)//2
                        cap=c.ns.xpBaseline[middle]
                        states={(low,0),(middle,0),(high,0),(middle,int(cap//2) if cap else 0)}
                        state_comparisons=[]
                        for start_level,start_xp in sorted(states):
                            options=c.lua.table_from({'startLevel':start_level,'startXP':start_xp})
                            replay=c.ns.NewGuideFlowModel(original,metric,options)
                            prior,improved=compare_replay(replay,original,candidate_table,(key,start_level,start_xp))
                            starting_states_checked+=1
                            state_comparisons.append({'start_level':start_level,'start_xp':start_xp,
                                'metrics':{field:{'before':prior[field],'after':improved[field]} for field in
                                    ('questXP','rewardXPBeforeWork','levelDeficitXP','difficultyPressure')}})
                        encode=lambda values:[f'{int(s.id)}:{s.kind}' for s in values]
                        old_order=encode(original.values());new_order=encode(candidate)
                        if old_order!=new_order:
                            flow=guide.optimization.flow
                            comparisons.append({'faction':faction,'key':guide.key,'zone':guide.zone,
                                'before':old_order,'after':new_order,
                                'before_actions': describe_actions(original.values(), c.ns, before.workRewards),
                                'after_actions': describe_actions(candidate, c.ns, after.workRewards),
                                'alternatives_evaluated':flow.candidates,'accepted_loop_changes':flow.moves,
                                'loop_changes':[{'quest_ids':list(change.questIDs.values()),'near_quest_id':change.nearQuestID,
                                    'actions_moved':change.actions,'estimated_travel_units_saved':round(change.travelSaved,2),
                                    'minimum_kills_saved':change.killsSaved,
                                    'kind':change.kind or 'objective-loop',
                                    'log_peak_reduced':change.logPeakReduced or 0,
                                    'reward_only_xp_shortfall_reduced':change.levelDeficitReduced or 0,
                                    'difficulty_pressure_reduced':change.difficultyReduced or 0,
                                    'estimated_reward_xp_gained':change.rewardXPGained or 0,
                                    'reward_xp_before_work_gained':change.rewardBeforeWorkGained or 0} for change in flow.changes.values()],
                                'quest_titles':{str(int(s.id)):c.ns.CatalogueQuest(s.id).title for s in candidate},
                                'actions_preserved':len(candidate),'endpoints_preserved':True,
                                'starting_state_replays':state_comparisons,
                                'metrics':{field:{'before':round(before[field],2),'after':round(after[field],2)}
                                    for field in ('distance','peakLog','levelDeficitXP','minimumKills','difficultyPressure','questXP','rewardXPBeforeWork','uncertainTravelLegs','blockedTravelLegs')},
                                'assumptions':['Fixed full-guide scope; no optional quests removed.',
                                    'Published ground/ordinary transport graph, local attachments and uncovered legs are estimates.',
                                    'No personal flight, mount or hearth assumed; live navigation retains confirmed transports.',
                                    'Quest-reward-only Classic XP baseline; combat/exploration XP, drop/spawn delays and inventory costs remain unmeasured.',
                                    'No increased log peak, known level XP shortfall, repeated kill lower bound or uncertain/blocked travel legs.',
                                    'Reward visits move only ready hand-ins; no objective receives less previously collected quest XP.',
                                    'Reward XP before work is summed over the same objectives: earlier collection, not additional XP or measured time saved.',
                                    'Equal-travel visits require log/progression/shared-kill or earlier-reward improvement; equivalent visits are retained.']})
                    print(f'{faction}: {guide.key}: {len(stops)} actions', flush=True)
    report = {'schema': 1, 'addon': label or c.ns.VERSION,
            'flow_module_sha256': hashlib.sha256((flow_module or ROOT / 'WowTogether/QuestFlow.lua').read_bytes()).hexdigest(),
            'catalogue_sha256': hashlib.sha256((ROOT / 'WowTogether/QuestCatalogue.lua').read_bytes()).hexdigest(),
            'travel_sha256': hashlib.sha256((ROOT / 'WowTogether/TravelData.lua').read_bytes()).hexdigest(),
            'validation': 'Lua 5.1 host. Complete action sequences; estimated geography, no play-time optimality claim.',
            'guides': result}
    if baseline:
        assert report['catalogue_sha256']==baseline['catalogue_sha256'], 'Source changed; an identical-source baseline is required'
        assert report['travel_sha256']==baseline['travel_sha256'], 'Travel source changed; an identical-source baseline is required'
        assert seen==set(old_guides), 'Guide scope changed'
        report['comparison']={'baseline_version':baseline['addon'],
                              'candidate_version':report['addon'],
                              'baseline_flow_sha256':baseline.get('flow_module_sha256'),
                              'candidate_flow_sha256':report['flow_module_sha256'],
                              'catalogue_sha256':report['catalogue_sha256'],'travel_sha256':report['travel_sha256'],
                              'guides_compared':len(seen),
                              'starting_states_checked':starting_states_checked,
                              'actions_preserved':sum(len(g['stops']) for g in result),
                              'trace_note':'Loop-change traces include established candidate passes; reward-visit identifies the added ready-reward pass.',
                              'trip_changes_in_candidate_traces':sum(move['kind']=='objective-trip'
                                  for change in comparisons for move in change['loop_changes']),
                              'additional_reward_visits':sum(move['kind']=='reward-visit'
                                  for change in comparisons for move in change['loop_changes']),
                              'changed_guides':len(comparisons),'changes':comparisons}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, help='Compare every action/state with a prior capture of the identical source data.')
    parser.add_argument('--comparison-output', type=Path, help='Also write the compact, fully justified old/new comparison report.')
    parser.add_argument('--flow-module', type=Path, help='Replay a prior project QuestFlow.lua with the current corrected quest scope.')
    parser.add_argument('--label', help='Label a replay baseline; for example, the prior release with identical scope corrections.')
    args = parser.parse_args()
    if args.baseline and args.flow_module: parser.error('Use --flow-module for a baseline capture, not the new comparison')
    result = capture(json.loads(args.baseline.read_text()) if args.baseline else None, args.flow_module, args.label)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Saved {len(result['guides'])} complete guides to {args.output}", flush=True)
    if args.comparison_output:
        if 'comparison' not in result: parser.error('--comparison-output requires --baseline')
        args.comparison_output.write_text(json.dumps(result['comparison'],indent=2)+'\n')


if __name__ == '__main__':
    main()
