"""Validate every source point and compile discoverable fixed zone guides.

This uses the repository's Lua 5.1 host fixture with native world conversion
unavailable. It verifies catalogue/planner invariants, never beta API behavior.
"""
import argparse
import collections
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from test_addon import Client


def audit(zone=None):
    c=Client(quests=(),use_catalogue=True)
    c.guide_environment(level=1)
    c.lua.globals().grouped=False
    c.ns.guideLevel='all'
    c.ns.db.config.classQuests=False
    c.ns.db.config.soloMode=True
    c.ns.ReadProfile()
    if zone is not None and not any(q.zone == zone for q in c.ns.catalogue.quests.values()):
        raise ValueError('Unknown catalogue zone: ' + zone)
    records=0
    points=0
    reason_stages=0;reason_codes=collections.Counter();reason_review=set()
    for ident,q in c.ns.catalogue.quests.items():
        if zone is not None and q.zone != zone: continue
        records+=1
        assert isinstance(ident,(int,float)) and ident>0,ident
        assert isinstance(q.title,str) and q.title,(ident,'title')
        for role in ('starts','ends','objectives'):
            for p in (q[role].values() if q[role] is not None else []):
                assert p.mapID and p.mapID>0,(ident,role,'map')
                assert all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in (p.x,p.y)),(ident,role,'point')
                if p.locationSource and p.locationSource.startswith('Older-world'):
                    assert q.foreverStatus=='unchanged' and q.legacyFactsSource,(ident,'legacy identity')
                points+=1
        for ref in (q.requirements.values() if q.requirements is not None else []):
            assert ref.entityType in ('npc','object','item') and ref.entityID>0 \
                and (ref.quantity and ref.quantity>0 or ref.quantityUnknown==True),(ident,'requirement')
        assert q.previousQuest!=ident,(ident,'self prerequisite')
        # Check every stage/location, including records outside leveling guides.
        # This measures explanation coverage, not pickup access or data completeness.
        record=c.ns.CatalogueRecord(ident)
        c.ns.profile.level=max(1,min(60,int(q.level or 1)))
        c.ns.profile.faction=q.side if q.side in ('Horde','Alliance') else 'Horde'
        selected=c.lua.table_from({'records':[record],'title':'Catalogue audit'},recursive=True)
        for role,kind in (('starts','a'),('objectives','q'),('ends','t')):
            locations=list(q[role].values()) if q[role] is not None else []
            if not locations or kind=='q' and q.objectiveLocationsIncomplete:locations.append(None)
            for p in locations:
                stop=c.ns.PublishedGuideStop(record,p,kind) if p is not None else None
                if stop is None:
                    stop=c.lua.table_from({'id':ident,'kind':kind,'title':q.title,
                        'unknownLocation':True,'mapID':q.mapID or 0})
                route=c.lua.table_from({'stops':[stop]},recursive=True)
                decision=c.ns.GuideDestinationDecision(stop,selected,route)
                assert isinstance(decision.why,str) and decision.why.strip(),(ident,kind,'missing reason')
                assert isinstance(decision.code,str) and decision.code,(ident,kind,'reason code')
                reason_codes[decision.code]+=1;reason_stages+=1
                if decision.needsReview:reason_review.add(int(ident))
    guides=[];seen=set()
    for faction,races in (('Horde',(2,6,5,8)),('Alliance',(1,3,4,7))):
        c.ns.profile.faction=faction;c.ns.profile.classID=8
        for race in races:
            c.ns.profile.raceID=race
            for level in (1,4,8,12,18,23,33,43,53,60):
                c.ns.profile.level=level
                for g in c.ns.LevelingGuideChoices().values():
                    # Generated chapter labels title-case small words; the
                    # catalogue retains published spelling ("Swamp of Sorrows").
                    # Generated "Ungoro Crater" also omits the catalogue apostrophe.
                    if zone is not None and g.zone.casefold().replace("'", "") != zone.casefold().replace("'", ""): continue
                    key=(faction,g.key)
                    if key in seen:continue
                    seen.add(key)
                    c.ns.GenerateFixedGuide(g,False)
                    plan=list(g.fixedPlan.values())
                    reason_route=c.lua.table_from({'stops':g.fixedPlan})
                    guide_reason_codes=collections.Counter();reason_review_steps=0;cross_zone_reason_steps=0
                    positions={(s.id,s.kind):i for i,s in enumerate(plan) if s.kind in ('a','t')}
                    kinds=collections.defaultdict(list)
                    for i,s in enumerate(plan):
                        assert s.guideStep==i+1,(key,'step index')
                        decision=c.ns.GuideDestinationDecision(s,g,reason_route)
                        assert decision.why and decision.code,(key,s.id,s.kind,'missing destination reason')
                        guide_reason_codes[decision.code]+=1
                        reason_review_steps+=bool(decision.needsReview)
                        if i>0 and s.mapID>0 and plan[i-1].mapID>0 and s.mapID!=plan[i-1].mapID:
                            cross_zone_reason_steps+=1
                        kinds[s.id].append(s.kind)
                        if s.kind=='a' and not s.planNeedsReview:
                            q=c.ns.CatalogueQuest(s.id)
                            if q.previousQuest:
                                assert (q.previousQuest,'t') in positions and positions[q.previousQuest,'t']<i,(key,s.id,'prerequisite')
                            for p in (q.prerequisiteAll.values() if q.prerequisiteAll else []):
                                assert (p,'t') in positions and positions[p,'t']<i,(key,s.id,'AND prerequisite')
                            if q.prerequisiteAny:
                                assert any((p,'t') in positions and positions[p,'t']<i for p in q.prerequisiteAny.values()),(key,s.id,'OR prerequisite')
                    for id,sequence in kinds.items():
                        assert sequence[0]=='a' and sequence[-1]=='t' and all(k=='q' for k in sequence[1:-1]),(key,id,'stage order')
                        assert not c.ns.IsLevelingExcludedQuest(id) and not c.ns.IsRepeatableQuest(id),(key,id,'excluded quest')
                    assert g.optimization.after<=g.optimization.before+1e-6,(key,'distance regression')
                    geometric=g.optimization.geometricGuard
                    if geometric:
                        assert geometric.after.valid,(key,'geometry state')
                        assert geometric.after.distance<=geometric.before.distance+.001,(key,'geometry travel regression')
                        for field in ('peakLog','levelDeficitXP','minimumKills','difficultyPressure','missingLevelCurve','uncertainTravelLegs','blockedTravelLegs'):
                            assert geometric.after[field]<=geometric.before[field],(key,field,'geometry regression')
                        assert geometric.after.questXP>=geometric.before.questXP,(key,'geometry reward regression')
                        for stop,reward in geometric.before.workRewards.items():
                            assert geometric.after.workRewards[stop]>=reward,(key,'geometry reward delayed')
                    flow=g.optimization.flow
                    assert flow.after.valid,(key,'quest-flow state')
                    for field in ('peakLog','levelDeficitXP','minimumKills','difficultyPressure','uncertainTravelLegs','blockedTravelLegs'):
                        assert flow.after[field]<=flow.before[field],(key,field,'flow regression')
                    assert flow.after.questXP>=flow.before.questXP,(key,'reward regression')
                    network=g.optimization.network
                    if network:
                        assert network.after.valid, (key,'network state')
                        assert network.after.distance<=network.before.distance+1e-6, (key,'network travel regression')
                        for field in ('peakLog','levelDeficitXP','minimumKills','difficultyPressure','uncertainTravelLegs','blockedTravelLegs'):
                            assert network.after[field]<=network.before[field], (key,field,'network regression')
                        assert network.after.questXP>=network.before.questXP,(key,'network reward regression')
                        for stop,reward in network.before.workRewards.items():
                            assert network.after.workRewards[stop]>=reward,(key,'network reward delayed')
                    for name in ('terrain', 'connections'):
                        priced=g.optimization[name]
                        if not priced: continue
                        assert priced.after.valid, (key,name,'state')
                        assert priced.after.distance<=priced.before.distance+1e-6, (key,name,'travel regression')
                        for field in ('peakLog','levelDeficitXP','minimumKills','difficultyPressure','uncertainTravelLegs','blockedTravelLegs'):
                            assert priced.after[field]<=priced.before[field], (key,name,field,'regression')
                        assert priced.after.questXP>=priced.before.questXP,(key,name,'reward regression')
                        for stop,reward in priced.before.workRewards.items():
                            assert priced.after.workRewards[stop]>=reward,(key,name,'reward delayed')
                    gaps={kind:sorted({int(s.id) for s in plan if s.kind==kind and s.unknownLocation}) for kind in ('a','q','t')}
                    unread=sorted(int(id) for id in kinds if not c.ns.CatalogueQuest(id).prerequisitesRead
                        or c.ns.CatalogueQuest(id).prerequisitesUnverified)
                    unknown_counts=sorted(int(id) for id in kinds if any(r.quantityUnknown and r.action in ('kill','collect','heal','use')
                        for r in (c.ns.CatalogueQuest(id).requirements.values() if c.ns.CatalogueQuest(id).requirements else [])))
                    for i,s in enumerate(plan):
                        if s.action=='escort':
                            assert i>0 and plan[i-1].id==s.id and plan[i-1].kind in ('a','q'),(key,s.id,'escort adjacency')
                    unknown=sum(bool(s.unknownLocation) for s in plan)
                    review=sum(bool(s.planNeedsReview) for s in plan)
                    guides.append({'faction':faction,'zone':g.zone,'key':g.key,'quests':len(kinds),'steps':len(plan),
                        'unknown_location_steps':unknown, 'missing_location_quest_ids_by_stage':gaps,
                        'unverified_pickup_requirement_quest_ids':unread,
                        'unverified_objective_quantity_quest_ids':unknown_counts,
                        'prerequisite_review_steps':review, 'source_data_gap_free':unknown==0 and review==0 and not unread and not unknown_counts,
                        'reason_steps_checked':len(plan),'destination_reason_codes':dict(sorted(guide_reason_codes.items())),
                        'reason_review_steps':reason_review_steps,'cross_zone_reason_steps':cross_zone_reason_steps,
                        'flow_alternatives_evaluated':flow.candidates,'flow_loop_changes':flow.moves,
                        'geometric_guard_rejections':geometric.rejected if geometric else 0,
                        'geometric_bracket_replays':geometric.replayStates if geometric else 0,
                        'flow_state_valid':bool(flow.after.valid),'quest_log_peak':flow.after.peakLog,
                        'quest_reward_only_xp_shortfall':flow.after.levelDeficitXP,'uncertain_travel_legs':flow.after.uncertainTravelLegs,
                        'estimated_distance_before':round(g.optimization.before,2),'estimated_distance_after':round(g.optimization.after,2)})
                    print(f'{faction}: {g.zone}: {len(plan)} steps checked',flush=True)
    result={'validation':'Lua 5.1 host; native map APIs unavailable; no terrain/XP optimality claim',
        'quest_records':records,'static_points_checked':points,'fixed_zone_guides_checked':len(guides),
        'catalogue_reason_stages_checked':reason_stages,'catalogue_reason_codes':dict(sorted(reason_codes.items())),
        'reason_review_quest_ids':sorted(reason_review),
        'source_data_gap_free_guides':sum(g['source_data_gap_free'] for g in guides),
        'guides':sorted(guides,key=lambda g:(g['faction'],g['zone']))}
    if zone is not None:
        result['scope']={'zone':zone,'catalogue_records':'Exact quest zone; guide dependencies still compile normally'}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path)
    p.add_argument('--zone',help='Audit one exact catalogue zone name, including every discoverable chapter and faction. Requires a separate --output.')
    p.add_argument('--require-complete',action='store_true',help='Fail when any guide still has missing source facts; invariants alone cannot pass this gate.')
    args=p.parse_args()
    full_output=ROOT/'WowTogether/GuideAudit.json'
    if args.zone is not None and (args.output is None or args.output.resolve()==full_output.resolve()):
        p.error('--zone requires a separate --output; preserve the full GuideAudit.json')
    output=args.output or full_output
    result=audit(args.zone)
    if result['fixed_zone_guides_checked']==0:raise ValueError('No zone guides were compiled')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(f"Checked {result['fixed_zone_guides_checked']} guides and {result['static_points_checked']} source points.")
    if args.require_complete and result['source_data_gap_free_guides']!=result['fixed_zone_guides_checked']:
        print(f"INCOMPLETE: {result['fixed_zone_guides_checked']-result['source_data_gap_free_guides']} guides still need source facts.",file=sys.stderr)
        raise SystemExit(2)


if __name__=='__main__':main()
