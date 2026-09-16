import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

parser = argparse.ArgumentParser(description='Run the frozen matched exact-packing protocol.')
parser.add_argument('--mousa', type=Path, required=True)
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='new output directory')
args = parser.parse_args()
inputs = Path(__file__).resolve().parent / 'fixtures'
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
protocol_path = Path(__file__).with_name('protocol.json')
protocol = json.loads(protocol_path.read_text())
binary = str(args.mousa.resolve(strict=True))
old = str(args.baseline.resolve(strict=True))
for name, digest in protocol['manifest'].items():
    assert hashlib.sha256((inputs/name).read_bytes()).hexdigest() == digest
rows = []

def call(executable, store, args, label):
    cost = out/'cost.txt'
    started = time.perf_counter_ns()
    proc = subprocess.run(['/usr/bin/time','-f','%M %U %S','-o',str(cost),executable,'-store',str(store),*args],capture_output=True,timeout=90)
    elapsed = (time.perf_counter_ns()-started)/1e6
    assert proc.returncode == 0, proc.stderr
    rss,user,system = cost.read_text().split()
    response = json.loads(proc.stdout)
    row = dict(label, wall_ms=elapsed,rss_kib=int(rss),user_s=float(user),system_s=float(system),output_bytes=len(proc.stdout),exit_code=proc.returncode,response=response,store_bytes=store.stat().st_size)
    rows.append(row)
    with (out/'observations.jsonl').open('a') as stream: stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    return response,row

def records(store):
    with closing(sqlite3.connect(store)) as db:
        return {table:dict(db.execute(f'SELECT hex(id),hex(record_json) FROM {table}')) for table in ['sources','observations','artifacts','representations','segments','source_trails']}

def copy_seed(seed, target):
    # Closing the connection, not merely its transaction, checkpoints each snapshot.
    assert not target.exists()
    for path in (seed, target):
        assert not Path(str(path) + '-wal').exists()
        assert not Path(str(path) + '-shm').exists()
    shutil.copy2(seed, target)

def metrics(response,q):
    hits=response['evidence']; texts=[hit['text'].encode() for hit in hits]
    required=q['required'].encode(); raw=(inputs/q['corpus']/q['file']).read_bytes()
    start=raw.index(required); wanted=set(range(start,start+len(required))); covered=set()
    for hit in hits:
        original=(inputs/q['corpus']/hit['item']).read_bytes()
        assert hashlib.sha256(original).hexdigest()==hit['representation_sha256']
        assert original[hit['byte_start']:hit['byte_end']]==hit['text'].encode()
        if hit['item']==q['file']: covered.update(range(hit['byte_start'],hit['byte_end']))
    return {'unique_selected_texts':len(set(texts)),'repeated_selected_bytes':sum(map(len,texts))-sum(map(len,set(texts))), 'useful_required_bytes':len(wanted&covered),'required_bytes':len(required),'complete_required_passage':wanted<=covered,'released_bytes':response['used_bytes'],'selected':len(hits),'duplicate_omitted':response.get('duplicate_omitted',0),'budget_omitted':response['budget_omitted'],'rejected':response['lifecycle_excluded']}

seeds={}
for q in protocol['questions']:
    key=(q['corpus'],q['policy'])
    if key in seeds: continue
    seed=out/('-'.join(key)+'.sqlite')
    call(old,seed,['sync','--segment-policy',q['policy'],str(inputs/q['corpus'])],dict(stage='seed',corpus=q['corpus'],policy=q['policy']))
    seeds[key]=seed

for qi,q in enumerate(protocol['questions']):
    seed=seeds[(q['corpus'],q['policy'])]
    args=['query','--budget-bytes',str(q['budget']),str(inputs/q['corpus']),q['query']]
    work=out/'query.sqlite'
    copy_seed(seed, work)
    historical,_=call(old,work,args,dict(stage='historical',**q))
    before=records(work)
    call(binary,work,['status',str(inputs/q['corpus'])],dict(stage='historical-reopen',**q))
    assert records(work)==before
    exact,_=call(binary,work,[*args[:1],'--packing-policy','exact-v1',*args[1:]],dict(stage='mixed-version',**q))
    after=records(work)
    assert all(all(after[t][k]==v for k,v in values.items()) for t,values in before.items())
    call(binary,work,['trail',str(inputs/q['corpus']),historical['trail_id']],dict(stage='historical-inspection',**q))
    call(binary,work,['trail',str(inputs/q['corpus']),exact['trail_id']],dict(stage='exact-inspection',**q))
    work.unlink()
    copy_seed(seed, work)
    ranked,_=call(binary,work,['query','--budget-bytes','1048576',str(inputs/q['corpus']),q['query']],dict(stage='ranking',**q))
    work.unlink()
    oracle=[]; seen=set(); used=0
    for hit in ranked['evidence']:
        text=hit['text'].encode()
        if text in seen: continue
        if used+len(text)>q['budget']: continue
        oracle.append(hit);used+=len(text);seen.add(text)
    for repeat in range(-1,protocol['pairs']):
        arms=['original','exact-v1'] if (repeat+qi)%2 else ['exact-v1','original']
        for arm in arms:
            copy_seed(seed, work)
            response,row=call(binary,work, [*args[:1],'--packing-policy',arm,*args[1:]],dict(stage='warmup' if repeat<0 else 'measured',repeat=repeat,arm=arm,**q))
            if arm=='original':
                for field in ['evidence','packet_id','used_bytes','budget_omitted','matched_candidates','lifecycle_excluded','expression']:
                    assert response[field]==historical[field],field
            else:
                assert response['evidence']==oracle
                assert len({h['text'] for h in oracle})==len(oracle)
            m=metrics(response,q)
            assert response['matched_candidates']==m['selected']+m['duplicate_omitted']+m['budget_omitted']+m['rejected']
            if q['corpus']=='small':
                assert m['unique_selected_texts']==(1 if arm=='original' else 2)
                assert m['complete_required_passage']==(arm=='exact-v1')
            if q['corpus']=='documentation':
                assert m['repeated_selected_bytes']==0
                assert response['packet_id']==historical['packet_id']
            with (out/'metrics.jsonl').open('a') as stream: stream.write(json.dumps(dict(q,repeat=repeat,arm=arm,stage=row['stage'],wall_ms=row['wall_ms'],rss_kib=row['rss_kib'],user_s=row['user_s'],system_s=row['system_s'],output_bytes=row['output_bytes'],store_bytes=row['store_bytes'],**m))+'\n')
            work.unlink()
(out/'protocol.json').write_bytes(protocol_path.read_bytes())
print('PASS:',len(rows),'CLI observations; all measured observations retained; historical stores and exact-byte oracle verified')
