"""Local host extension of the existing audit's race loop; no runtime changes."""
import json,sys
from pathlib import Path
sys.path[:0]=['tools','tests']
import audit_quest_flow as flow
source=Path('tools/audit_quest_flow.py').read_text()
old="('Alliance', (1, 3, 4, 7))"
assert source.count(old)==1
# Keep the exact capture implementation, adding only the published race ID.
exec(compile(source.replace(old,"('Alliance', (1, 3, 4, 7, 95))"),'tools/audit_quest_flow.py','exec'),flow.__dict__)
for label,catalogue in [('before',Path('/tmp/westfall-research/before-catalogue.lua')),('after',None)]:
 result=flow.capture(zone='Westfall',race_id=95,catalogue=catalogue)
 Path(f'research/westfall-2026-10-09/skyborn-{label}-flow.json').write_text(json.dumps(result,indent=2)+'\n')
 print(label,[(g['key'],len(g['stops']))for g in result['guides']],flush=True)
