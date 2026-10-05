"""Capture independent, public quest pages from the guide audit's factual queue.

Resumable, two paced workers, normal verified HTTPS only. Previously denied
IDs remain excluded. This tool never evaluates source scripts or overwrites
the generated addon; run build_quest_dataset.py after capture finishes.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

from import_wowhead import json_after


def capture(queue, cache, denied=()):
    cache.mkdir(parents=True, exist_ok=True)
    state_path=cache/'capture.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    for ident in denied:state.setdefault(str(ident),{'status':403})
    lock=threading.Lock();stopped=False;denial_streak=0
    def load(ident):
        nonlocal stopped,denial_streak
        if type(ident) is not int or not 0<ident<2147483647:raise ValueError('Invalid quest ID')
        path=cache/('quest-'+str(ident)+'.html')
        if path.exists():return ident,{'status':'cached'}
        if state.get(str(ident),{}).get('status') in (403,404):return ident,{'status':'previously unavailable'}
        with lock:
            if stopped:return ident,{'status':'not requested after denials'}
        time.sleep(.5)
        try:
            req=urllib.request.Request('https://www.wowhead.com/forever/quest='+str(ident),
                headers={'User-Agent':'WowTogether-quest-data-import/0.8'})
            with urllib.request.urlopen(req,timeout=25) as response:data=response.read()
            page=data.decode('utf-8');meta=json_after(page,f'$.extend(g_quests[{ident}], ')
            if not isinstance(meta,dict) or meta.get('id')!=ident:return ident,{'status':'unrecognized page'}
            path.write_bytes(data)
            with lock:denial_streak=0
            return ident,{'status':200,'captured':datetime.date.today().isoformat(),'sha256':hashlib.sha256(data).hexdigest()}
        except urllib.error.HTTPError as error:
            with lock:
                if error.code==403:
                    denial_streak+=1;stopped=stopped or denial_streak>=3
                if error.code==429:stopped=True
            return ident,{'status':error.code}
        except (urllib.error.URLError,TimeoutError,OSError):
            with lock:stopped=True
            return ident,{'status':'transport failure; no automatic retry'}
    counts={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for index,(ident,result) in enumerate(executor.map(load,queue),1):
            status=str(result['status']);counts[status]=counts.get(status,0)+1
            if status not in ('cached','previously unavailable','not requested after denials'):
                state[str(ident)]=result
                temporary=state_path.with_suffix('.json.tmp')
                temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(state_path)
            if index%25==0:print(f'Quest pages: {index}/{len(queue)}; {counts}',flush=True)
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({'quests':len(queue),'results':counts,'stopped_after_denials':stopped}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('queue',type=Path,help='GuideSourceQueue.json from guide_source_queue.py')
    p.add_argument('--cache',type=Path,default=Path('/tmp/wow-together-wowhead'))
    p.add_argument('--denials',type=Path,help='Existing QuestCatalogue.json capture failures to exclude')
    args=p.parse_args()
    rows=json.loads(args.queue.read_text())['quests']
    # New IDs first: their factual gaps cannot use an old-world fallback.
    ids=sorted({r['questID'] for r in rows},key=lambda i:(i<90000,i))
    denied=[r['questID'] for r in json.loads(args.denials.read_text()).get('unavailable_details',[]) if r.get('status')==403] if args.denials else []
    capture(ids,args.cache,denied)


if __name__=='__main__':main()
