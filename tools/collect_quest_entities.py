"""Collect a resumable queue of public Forever NPC/object/item pages.

Two paced workers; preserve proxy/TLS, never retry access denials or execute JS.
The queue contains entity types/IDs, never arbitrary URLs. Pages remain outside
the release; only parsed game facts are bundled by the enrichment tool.
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

from quest_enrichment import entity_facts


def catalogue_queue(path):
    """Prioritize named gaps in new/changed zone quests before common sources."""
    from lupa.lua51 import LuaRuntime
    lua=LuaRuntime();ns=lua.table()
    lua.eval('function(text,ns) assert(loadstring(text))("WowTogether",ns) end')(path.read_text(),ns)
    priority={}
    def add(ref,rank):
        kind,ident=ref.entityType,ref.entityID
        if kind in ('npc','object','item') and isinstance(ident,(int,float)) and ident>0:
            key=(kind,int(ident));priority[key]=min(priority.get(key,rank),rank)
    for ident,q in ns.catalogue.quests.items():
        missing=not q.starts or not q.ends or bool(q.objectiveLocationsIncomplete)
        rank=(0 if missing else 1,{'new':0,'updated':1,'unconfirmed':2,'unchanged':3}.get(q.foreverStatus,2),
            q.minLevel or q.level or 255,ident)
        for field in ('startRefs','endRefs','requirements','providedItems'):
            for ref in (q[field].values() if q[field] is not None else []):add(ref,rank)
    for kind,entities in ns.questEntities.items():
        for ident,entity in entities.items():
            priority.setdefault((kind,int(ident)),(2,4,255,ident))
            for source in (entity.sources.values() if entity.sources is not None else []):add(source,(2,4,255,ident))
    return [list(key) for key in sorted(priority,key=lambda key:(priority[key],key))]


def collect(queue, cache, access_changed=False):
    cache.mkdir(parents=True, exist_ok=True)
    state_path = cache / 'capture.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    lock = threading.Lock()
    denials, stopped = 0, False
    def load(entry):
        nonlocal denials, stopped
        kind, ident = entry
        if kind not in ('npc', 'object', 'item') or type(ident) is not int or not 0 < ident < 2147483647:
            raise ValueError('Invalid entity queue entry')
        key = kind + '-' + str(ident)
        file = cache / (key + '.html')
        if file.exists():
            return key, {'status': 'cached'}
        if state.get(key, {}).get('status') == 404 or state.get(key, {}).get('status') == 403 and not access_changed:
            return key, {'status': 'previously unavailable'}
        with lock:
            if stopped:
                return key, {'status': 'not requested after access denials'}
        time.sleep(.5)
        try:
            request = urllib.request.Request('https://www.wowhead.com/forever/' + kind + '=' + str(ident),
                headers={'User-Agent':'WowTogether-quest-data-import/0.8'})
            with urllib.request.urlopen(request, timeout=25) as response:
                data = response.read()
            facts = entity_facts(data.decode(), kind, ident)
            if not facts['name']:
                return key, {'status': 'unrecognized page'}
            file.write_bytes(data)
            with lock:
                denials = 0
            return key, {'status': 200, 'captured': datetime.date.today().isoformat(),
                         'sha256': hashlib.sha256(data).hexdigest()}
        except ValueError:
            return key, {'status':'unrecognized entity identity; not stored'}
        except urllib.error.HTTPError as error:
            with lock:
                if error.code == 403:
                    denials += 1
                    stopped = denials >= 3
                if error.code == 429:stopped = True
            return key, {'status': error.code}
        except (urllib.error.URLError, TimeoutError, OSError):
            with lock:
                stopped = True
            return key, {'status':'transport failure; no automatic retry'}
    counts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for i, (key, result) in enumerate(executor.map(load, queue), 1):
            counts[str(result['status'])] = counts.get(str(result['status']),0) + 1
            if result['status'] != 'cached' and result['status'] != 'previously unavailable':
                state[key] = result
                temporary = state_path.with_suffix('.json.tmp')
                temporary.write_text(json.dumps(state,indent=2)+'\n'); temporary.replace(state_path)
            if i % 25 == 0:
                print(f'Entity pages: {i}/{len(queue)}; {counts}',flush=True)
    print(json.dumps({'requested_entities':len(queue),'results':counts,'stopped_after_denials':stopped}),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('queue',type=Path,nargs='?')
    parser.add_argument('--from-catalogue',type=Path,help='Build a priority queue from our generated QuestCatalogue.lua.')
    parser.add_argument('--cache',type=Path,default=Path('/tmp/wow-together-wowhead-entities'))
    parser.add_argument('--access-changed',action='store_true',help='Recheck prior 403s only after environment access changes; still stops after denials.')
    args = parser.parse_args()
    if bool(args.queue)==bool(args.from_catalogue):parser.error('Choose a JSON queue or --from-catalogue')
    queue = catalogue_queue(args.from_catalogue) if args.from_catalogue else json.loads(args.queue.read_text())
    if not isinstance(queue,list):
        raise ValueError('Expected entity queue array')
    collect(queue,args.cache,args.access_changed)


if __name__ == '__main__':
    main()
