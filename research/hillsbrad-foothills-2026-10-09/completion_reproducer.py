import sys,json
from pathlib import Path
sys.path.insert(0,'tests');from test_stv_coverage import client
from test_routes import guide
from test_063 import primitive
out=[]
for label,level,ids in [('accepted unfinished',25,[527]),('deferred parent hand-in',25,[528]),('higher-level remaining',21,[519]),('mixed remainder',25,[527,528,519,98094]),('full Hillsbrad guide',25,None)]:
 c=client('Horde',level=level);c.ns.partyNames=c.lua.table();c.ns.profile.mapID=1424;c.ns.profile.zone='Hillsbrad Foothills';c.ns.questReady=True;g=c.ns.ZoneGuideForMap(1424,True) if ids is None else guide(c,ids);ids=[r.id for r in g.records.values()];g.fixedRoute=True;g.key='hillsbrad-completion-reproducer';c.ns.routeSelection=g
 if label in ['accepted unfinished','mixed remainder','full Hillsbrad guide']:c.ns.active[527]='Battle of Hillsbrad'
 c.ns.GenerateFixedGuide(g,False);c.ns.questReady=True;c.ns.selectedRoute=c.ns.BuildFixedGuideRoute(g,False);c.ns.UpdateFixedGuideRoute(g)
 r=c.ns.selectedRoute;out.append({'case':label,'level':level,'questIDs':ids,'complete':bool(r.complete),'pendingReason':r.pendingReason,'completionProgress':primitive(r.completionProgress),'remainingSteps':r.remainingSteps,'deferredQuests':r.deferredQuests,'routePaused':c.ns.routePaused,'stops':len(list(r.stops.values()))})
 assert not r.complete,label
print(json.dumps(out,indent=2));(Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/hillsbrad-completion-reproducer.json')).write_text(json.dumps(out,indent=2)+'\n')
