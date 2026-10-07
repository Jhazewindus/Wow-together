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


def audit():
    c=Client(quests=(),use_catalogue=True)
    c.guide_environment(level=1)
    c.lua.globals().grouped=False
    c.ns.guideLevel='all'
    c.ns.db.config.classQuests=False
    c.ns.db.config.soloMode=True
    c.ns.ReadProfile()
    points=0
    reason_stages=0;reason_codes=collections.Counter();reason_review=set()
    for ident,q in c.ns.catalogue.quests.items():
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
                        'estimated_distance_before':round(g.optimization.before,2),'estimated_distance_after':round(g.optimization.after,2)})
                    print(f'{faction}: {g.zone}: {len(plan)} steps checked',flush=True)
    return {'validation':'Lua 5.1 host; native map APIs unavailable; no terrain/XP optimality claim',
        'quest_records':c.ns.catalogue.count,'static_points_checked':points,'fixed_zone_guides_checked':len(guides),
        'catalogue_reason_stages_checked':reason_stages,'catalogue_reason_codes':dict(sorted(reason_codes.items())),
        'reason_review_quest_ids':sorted(reason_review),
        'source_data_gap_free_guides':sum(g['source_data_gap_free'] for g in guides),
        'guides':sorted(guides,key=lambda g:(g['faction'],g['zone']))}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'WowTogether/GuideAudit.json')
    p.add_argument('--require-complete',action='store_true',help='Fail when any guide still has missing source facts; invariants alone cannot pass this gate.')
    args=p.parse_args();result=audit()
    if result['fixed_zone_guides_checked']==0:raise ValueError('No zone guides were compiled')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(f"Checked {result['fixed_zone_guides_checked']} guides and {result['static_points_checked']} source points.")
    if args.require_complete and result['source_data_gap_free_guides']!=result['fixed_zone_guides_checked']:
        print(f"INCOMPLETE: {result['fixed_zone_guides_checked']-result['source_data_gap_free_guides']} guides still need source facts.",file=sys.stderr)
        raise SystemExit(2)


if __name__=='__main__':main()
