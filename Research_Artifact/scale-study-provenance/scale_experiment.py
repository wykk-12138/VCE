"""Serial new-release scale study; never modifies frozen v17 measurements.

Runs the original native CLI in isolated fixtures and reuses its independent
oracle. Fixture creation, evidence inspection, and oracle work are untimed.
"""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,os,platform,random,shutil,sqlite3,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
ENGINE=Path('D:/Users/star_/Documents/ChatGPT/ReceiptCoordinator')
sys.path.insert(0,str(ENGINE))
from paper.closurestudy.client import configure,setup,call,confirm,corpus,logs,trace,api_success,BINARY
from paper.finalstudy.cases import oracle

METHODS=['JournalGuardedScoped','ReceiptCoordinatorV14','ReceiptCoordinatorV15']
SIZES=[0,64,256,512,1024,2048]
SHAPES=['nested','flat']
SCRATCH=(ENGINE/'.research-tmp/scale-2026-10-29').resolve()
OUT=PROJECT/'paper/figure-data/paper/evidence/scale-v18'
EXPECTED='b1826c1f2f917af4765b55e7ff52b65926e031df9eeb84700c0665ed74e3a36f'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def cleanup(p):
    p=p.resolve()
    if not p.is_relative_to(SCRATCH) or p==SCRATCH:raise ValueError('Unsafe fixture deletion')
    if p.exists():shutil.rmtree(p)

def one(root,item,method,n,shape):
    root=root.resolve();assert root.is_relative_to(SCRATCH)
    fixture=setup(root,item,'claude')
    d=root/'project' if shape=='flat' else root/'project/vce_scale_source'
    d.mkdir(exist_ok=True)
    payload=b'x'*1024
    for i in range(n):
        f=d/f'vce_scale_file_{i:04d}.txt';assert not f.exists();f.write_bytes(payload)
    preview=call(root,'claude','plan',method=method)
    p=preview['response']['data'];assert p['plan']['envelope']['ok'],preview
    first=confirm(root,'claude',method,p,fault='after_native')
    assert first['exit_code']==86,first
    np=len(logs(root,'adapter_profile.jsonl'));nc=len(logs(root,'components.jsonl'));nt=len(trace(root));nw=len(logs(root,'witness_trace.jsonl'))
    result=confirm(root,'claude',method,p)
    assert api_success(result),result
    commands=[r['command'] for r in trace(root)[nt:]]
    profile=logs(root,'adapter_profile.jsonl')[np:]
    components=logs(root,'components.jsonl')[nc:]
    events=logs(root,'witness_trace.jsonl')[nw:]
    evidence=None
    with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='native_completion_evidence'").fetchone()
        if exists:
            row=db.execute('SELECT evidence FROM native_completion_evidence WHERE plan=?',(p['plan']['operationId'],)).fetchone()
            if row:evidence=row[0]
    ev=json.loads(evidence) if evidence else {}
    snapshot=ev.get('snapshot',{})
    checked=oracle(root,'claude',fixture,p['prompt_id'],p['plan']['operationId'],method,result)
    assert checked['unique_api_completion'],checked
    if method=='JournalGuardedScoped':assert len(commands)==2,commands
    else:
        assert commands==[],commands
        assert any(e.get('hit') for e in events),events
        assert evidence,'missing evidence on expected valid hit'
    # Repeat the exact v17 exclusive-span accounting for comparability.
    native=sum(v['elapsed_ns'] for v in profile)
    readback=sum(v['elapsed_ns'] for v in components if v['component']=='readback')
    validation=sum(v['elapsed_ns'] for v in components if v['component']=='evidence_validation')
    nested_rb=0
    for v in components:
        if v['component']=='evidence_validation':break
        if v['component']=='readback':nested_rb+=v['elapsed_ns']
    validation=max(0,validation-nested_rb)
    publication=sum(v['elapsed_ns'] for v in components if v['component']=='publication')
    other=result['wall_ns']-native-readback-validation-publication
    assert other>=0
    return {'pass':True,'tool':'claude','scenario':'recovery','lifecycle':'cold',
        'wall_ns':result['wall_ns'],'handler_ns':result['response']['elapsed_ns'],
        'preview_ns':preview['wall_ns'],'first_ns':first['wall_ns'],
        'episode_ns':preview['wall_ns']+first['wall_ns']+result['wall_ns'],
        'commands':commands,'profile':profile,'components':components,'witness_events':events,
        'exclusive_ns':{'Native':native,'Validation':validation,'Readback':readback,'Publication':publication,'Other':other},
        'evidence_bytes':len(evidence.encode('utf-8')) if evidence else 0,
        'snapshot_entries':len(snapshot) if isinstance(snapshot,(list,dict)) else None,
        'snapshot_container_type':type(snapshot).__name__,'oracle':checked}

def main(args):
    configure();assert digest(BINARY)==EXPECTED
    selected={}
    for item in corpus('confirmation'):selected.setdefault(item['repository'],item)
    items=list(selected.values());assert len(items)==12
    mode='smoke' if args.smoke else args.batch
    out=OUT/mode;out.mkdir(parents=True,exist_ok=False)
    SCRATCH.mkdir(parents=True,exist_ok=True)
    sizes=[0,2048] if args.smoke else SIZES
    count=1 if args.smoke else 12
    seed={'b1':18901,'b2':18902,'b3':18903,'smoke':18900}[mode]
    source_hashes={str(p.relative_to(ENGINE)):digest(p) for p in (ENGINE/'native').rglob('*')
        if p.is_file() and 'target' not in p.relative_to(ENGINE).parts}
    spec={'study':'VCE independent release-scale follow-up','started_utc':datetime.now(timezone.utc).isoformat(),
        'batch':mode,'binary':str(BINARY),'binary_sha256':digest(BINARY),'native_source_hashes':source_hashes,
        'harness_sha256':digest(Path(__file__)),'python':sys.version,'python_executable':sys.executable,
        'platform':platform.platform(),'logical_cpus':os.cpu_count(),'sizes':sizes,'shapes':SHAPES,
        'methods':METHODS,'file_bytes':1024,'projects':count,'warmup_blocks':0 if args.smoke else 1,
        'seed':seed,'inputs':items[:count],
        'measurement':'Cold recovery confirmation after actual after_native caller exit; creation, oracle and cleanup excluded.',
        'identity_note':'Release source equals distributed final implementation; executable differs from historical v17. Separate study; no pooling.',
        'layout_note':'Flat files are direct project children; nested files are in one irrelevant source subdirectory. Zero-file fixtures are independently measured in both panels.',
        'estimator':'Medians for absolute metrics; paired geometric ratios and crossed project/batch bootstrap after all three batches.'}
    save(out/'spec.json',spec)
    rng=random.Random(seed);rows=[];began=time.monotonic()
    blocks=list(range(count)) if args.smoke else [-1]+list(range(count))
    with (out/'raw.jsonl').open('w',encoding='utf-8') as f:
        for block in blocks:
            item=items[block if block>=0 else -1]
            conditions=[(shape,n) for shape in SHAPES for n in sizes];rng.shuffle(conditions)
            for shape,n in conditions:
                order=METHODS.copy();rng.shuffle(order)
                for method in order:
                    fixture=SCRATCH/f'{mode}-{len(rows):04d}'
                    assert not fixture.exists(),fixture
                    meta={'batch':mode,'block':block,'warmup':block<0,'repository':item['repository'],
                          'shape':shape,'noise':n,'method':method}
                    try: row={**meta,**one(fixture,item,method,n,shape)}
                    except Exception as exc:
                        row={**meta,'pass':False,'error':repr(exc),'retained_fixture':str(fixture)}
                        f.write(json.dumps(row)+'\n');f.flush();save(out/'failure.json',row);raise
                    rows.append(row);f.write(json.dumps(row)+'\n');f.flush();cleanup(fixture)
                print(json.dumps({'batch':mode,'block':block,'shape':shape,'files':n,'rows':len(rows),
                     'seconds':round(time.monotonic()-began,1)}),flush=True)
    assert digest(BINARY)==EXPECTED
    summary={'observations':len(rows),'scored':sum(not r['warmup'] for r in rows),
        'passed':sum(r['pass'] for r in rows),'seconds':time.monotonic()-began,
        'finished_utc':datetime.now(timezone.utc).isoformat(),'raw_sha256':digest(out/'raw.jsonl')}
    save(out/'summary.json',summary);print('COMPLETE',json.dumps(summary),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--batch',choices=['b1','b2','b3'],default='b1');main(parser.parse_args())
