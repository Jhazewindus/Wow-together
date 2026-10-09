import sys,json
from pathlib import Path
sys.path.insert(0,'tools')
root=Path.cwd();ns={'__name__':'zephras_local_capture','__file__':str(root/'tools/audit_quest_flow.py')};s=(root/'tools/audit_quest_flow.py').read_text().replace("('Horde', (2, 6, 5, 8))","('Horde', (2, 6, 5, 8, 96))").replace("('Alliance', (1, 3, 4, 7))","('Alliance', (1, 3, 4, 7, 95))");exec(compile(s,str(root/'tools/audit_quest_flow.py'),'exec'),ns)
label=sys.argv[1]
for race in [95,96]:
 f=ns['capture'](zone='Zephras Isle',race_id=race);Path('/tmp/zephras-research/'+label+'-race'+str(race)+'-flow.json').write_text(json.dumps(f,indent=2)+'\n')
