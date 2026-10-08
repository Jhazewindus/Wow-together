"""Add only the newly evidenced traversal to the complete old route for pricing."""
import copy,json
from pathlib import Path
p=Path('/tmp/wetlands-research');before=json.loads((p/'before-flow.json').read_text());after=json.loads((p/'after-flow.json').read_text());additions=[]
for old in before['guides']:
 new=next(g for g in after['guides']if(g['faction'],g['key'])==(old['faction'],old['key']))
 extra=[s for s in new['stops']if s.get('objectiveKey')=='event:455']
 if not extra:continue
 assert len(extra)==1 and not any(s.get('objectiveKey')=='event:455'for s in old['stops'])
 at=next(i for i,s in enumerate(old['stops'])if(s['id'],s['kind'])==(455,'t'))
 assert len([s for s in old['stops'][:at]if(s['id'],s['kind'])==(455,'q')])==2
 old['stops'].insert(at,copy.deepcopy(extra[0]));additions.append({'key':old['key'],'questID':455,'objectiveKey':'event:455','inserted_before':'actual 455 hand-in','old_actions_removed':0})
(p/'reconciled-before-flow.json').write_text(json.dumps(before,indent=2)+'\n');(p/'scope-reconciliation.json').write_text(json.dumps({'raw_guard':'Required action scope changed (two newly evidenced action occurrences)','method':'Keep every old action; add only the actual traversal before its hand-in in each affected chapter. Compare full identical corrected scope, not an optimization gain from missing work.','additions':additions},indent=2)+'\n')
