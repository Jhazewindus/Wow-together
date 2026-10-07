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


def capture(baseline=None):
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=1)
    c.lua.globals().grouped = False
    c.ns.guideLevel = 'all'
    c.ns.db.config.classQuests = False
    c.ns.db.config.soloMode = True
    c.ns.ReadProfile()
    result, seen = [], set()
    old_guides = {(g['faction'], g['key']): g for g in baseline['guides']} if baseline else {}
    comparisons = []
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
                        before=model.evaluate(original)
                        after=model.evaluate(c.lua.table_from(candidate))
                        assert after.valid,(key,'invalid route')
                        for field in ('peakLog','levelDeficitXP','minimumKills','difficultyPressure','uncertainTravelLegs','blockedTravelLegs'):
                            assert after[field]<=before[field],(key,field,'regression')
                        assert after.questXP>=before.questXP,(key,'reward XP regression')
                        assert after.distance<=before.distance+0.001,(key,'complete journey regression')
                        encode=lambda values:[f'{int(s.id)}:{s.kind}' for s in values]
                        old_order=encode(original.values());new_order=encode(candidate)
                        if old_order!=new_order:
                            flow=guide.optimization.flow
                            comparisons.append({'faction':faction,'key':guide.key,'zone':guide.zone,
                                'before':old_order,'after':new_order,
                                'alternatives_evaluated':flow.candidates,'accepted_loop_changes':flow.moves,
                                'loop_changes':[{'quest_ids':list(change.questIDs.values()),'near_quest_id':change.nearQuestID,
                                    'actions_moved':change.actions,'estimated_travel_units_saved':round(change.travelSaved,2),
                                    'minimum_kills_saved':change.killsSaved} for change in flow.changes.values()],
                                'quest_titles':{str(int(s.id)):c.ns.CatalogueQuest(s.id).title for s in candidate},
                                'actions_preserved':len(candidate),'endpoints_preserved':True,
                                'metrics':{field:{'before':round(before[field],2),'after':round(after[field],2)}
                                    for field in ('distance','peakLog','levelDeficitXP','minimumKills','difficultyPressure','questXP','uncertainTravelLegs','blockedTravelLegs')},
                                'assumptions':['Fixed full-guide scope; no optional quests removed.',
                                    'Published ground/ordinary transport graph, local attachments and uncovered legs are estimates.',
                                    'No personal flight, mount or hearth assumed; live navigation retains confirmed transports.',
                                    'Quest-reward-only Classic XP baseline; combat/exploration XP, drop/spawn delays and inventory costs remain unmeasured.',
                                    'No increased log peak, known level XP shortfall, repeated kill lower bound or uncertain/blocked travel legs.']})
                    print(f'{faction}: {guide.key}: {len(stops)} actions', flush=True)
    report = {'schema': 1, 'addon': c.ns.VERSION,
            'catalogue_sha256': hashlib.sha256((ROOT / 'WowTogether/QuestCatalogue.lua').read_bytes()).hexdigest(),
            'travel_sha256': hashlib.sha256((ROOT / 'WowTogether/TravelData.lua').read_bytes()).hexdigest(),
            'validation': 'Lua 5.1 host. Complete action sequences; estimated geography, no play-time optimality claim.',
            'guides': result}
    if baseline:
        assert report['catalogue_sha256']==baseline['catalogue_sha256'], 'Source changed; an identical-source baseline is required'
        assert report['travel_sha256']==baseline['travel_sha256'], 'Travel source changed; an identical-source baseline is required'
        assert seen==set(old_guides), 'Guide scope changed'
        report['comparison']={'baseline_version':baseline['addon'],'guides_compared':len(seen),
                              'changed_guides':len(comparisons),'changes':comparisons}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, help='Compare every action/state with a prior capture of the identical source data.')
    parser.add_argument('--comparison-output', type=Path, help='Also write the compact, fully justified old/new comparison report.')
    args = parser.parse_args()
    result = capture(json.loads(args.baseline.read_text()) if args.baseline else None)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Saved {len(result['guides'])} complete guides to {args.output}", flush=True)
    if args.comparison_output:
        if 'comparison' not in result: parser.error('--comparison-output requires --baseline')
        args.comparison_output.write_text(json.dumps(result['comparison'],indent=2)+'\n')


if __name__ == '__main__':
    main()
