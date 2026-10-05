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
            assert ref.entityType in ('npc','object','item') and ref.entityID>0 and ref.quantity>0,(ident,'requirement')
        assert q.previousQuest!=ident,(ident,'self prerequisite')
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
                    positions={(s.id,s.kind):i for i,s in enumerate(plan) if s.kind in ('a','t')}
                    kinds=collections.defaultdict(list)
                    for i,s in enumerate(plan):
                        assert s.guideStep==i+1,(key,'step index')
                        kinds[s.id].append(s.kind)
                        if s.kind=='a' and not s.planNeedsReview:
                            q=c.ns.CatalogueQuest(s.id)
                            if q.previousQuest:
                                assert (q.previousQuest,'t') in positions and positions[q.previousQuest,'t']<i,(key,s.id,'prerequisite')
                            if q.prerequisiteAny:
                                assert any((p,'t') in positions and positions[p,'t']<i for p in q.prerequisiteAny.values()),(key,s.id,'OR prerequisite')
                    for id,sequence in kinds.items():
                        assert sequence[0]=='a' and sequence[-1]=='t' and all(k=='q' for k in sequence[1:-1]),(key,id,'stage order')
                        assert not c.ns.IsLevelingExcludedQuest(id) and not c.ns.IsRepeatableQuest(id),(key,id,'excluded quest')
                    assert g.optimization.after<=g.optimization.before+1e-6,(key,'distance regression')
                    guides.append({'faction':faction,'zone':g.zone,'key':g.key,'quests':len(kinds),'steps':len(plan),
                        'unknown_location_steps':sum(bool(s.unknownLocation) for s in plan),
                        'prerequisite_review_steps':sum(bool(s.planNeedsReview) for s in plan),
                        'estimated_distance_before':round(g.optimization.before,2),'estimated_distance_after':round(g.optimization.after,2)})
                    print(f'{faction}: {g.zone}: {len(plan)} steps checked',flush=True)
    return {'validation':'Lua 5.1 host; native map APIs unavailable; no terrain/XP optimality claim',
        'quest_records':c.ns.catalogue.count,'static_points_checked':points,'fixed_zone_guides_checked':len(guides),
        'guides':sorted(guides,key=lambda g:(g['faction'],g['zone']))}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'WowTogether/GuideAudit.json')
    args=p.parse_args();result=audit()
    if result['fixed_zone_guides_checked']==0:raise ValueError('No zone guides were compiled')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(f"Checked {result['fixed_zone_guides_checked']} guides and {result['static_points_checked']} source points.")


if __name__=='__main__':main()
