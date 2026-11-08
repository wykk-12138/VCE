import argparse,hashlib,json,os,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from .client import *
from paper.finalstudy.cases import oracle
PYTHON=Path(os.environ.get('RC_DBOS_PYTHON',sys.executable))
ARMS=['OriginalReplan','JournalGuardedScoped','ReceiptCoordinatorV15','JournalWitnessV15']
SCENARIOS=['normal','after_native','after_external','after_step','external_after_step']

def invoke(request,fault=None):
 env={**os.environ,'TMP':str(SCRATCH),'TEMP':str(SCRATCH),'PYTHONIOENCODING':'utf-8','CLOSURE_NATIVE_FAULT':'after_native' if fault=='after_native' else '',
  'CLOSURE_ENGINE_FAULT':fault if fault in {'after_external','after_step'} else ''}
 began=time.perf_counter_ns();p=subprocess.run([str(PYTHON),'-m','paper.closurestudy.dbos_worker'],input=json.dumps(request)+'\n',capture_output=True,text=True,encoding='utf8',cwd=ROOT,env=env,timeout=120)
 elapsed=time.perf_counter_ns()-began
 if p.returncode==86:return {'exit_code':86,'wall_ns':elapsed}
 if p.returncode:raise RuntimeError((p.returncode,p.stderr[-2500:],p.stdout[-1000:]))
 result=next(json.loads(s) for s in reversed(p.stdout.splitlines()) if s.startswith('{'))
 return {'exit_code':0,'wall_ns':elapsed,**result}

def one(root,item,tool,method,scenario):
 fixture=setup(root,item,tool);p=plan(root,tool,method)
 req={'root':str(root),'tool':tool,'endpoint':method,'operation_id':p['plan']['operationId'],'prompt_id':p['prompt_id']}
 initial=None;external={}
 if scenario!='normal':
  initial=invoke(req,'after_step' if scenario=='external_after_step' else scenario);assert initial['exit_code']==86,initial
  if scenario=='external_after_step':
   path=installed(root,tool);path.write_bytes(b'# External edit after durable step\n');external[path.relative_to(root).as_posix()]=path.read_bytes()
 n=len(trace(root));result=invoke(req);calls=trace(root);checked=oracle(root,tool,fixture,p['prompt_id'],p['plan']['operationId'],method,result['result'],external)
 historical=scenario=='external_after_step'
 # Direct activity is a boundary demonstration: retain duplicates and failed
 # current completion as observations, never count a cached response as current.
 passed=(checked['api_success'] and checked['external_preserved'] and len(calls)==n) if historical else checked['unique_api_completion'] if method!='OriginalReplan' else checked['api_success']
 return {'pass':passed,'initial':initial,'result':result,'oracle':checked,'historical_response':historical,
  'activation_calls':sum(x['command']=='activate' for x in calls),'retry_commands':[x['command'] for x in calls[n:]],'hard_exits':int(initial is not None)}

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 a.out.mkdir(parents=True);rows=[];items=corpus('confirmation')[:a.inputs];began=time.perf_counter()
 version=subprocess.check_output([str(PYTHON),'-c','import importlib.metadata;print(importlib.metadata.version("dbos"))'],text=True).strip()
 (a.out/'spec.json').write_text(json.dumps({'runtime':'DBOS','version':version,'database':'per-case SQLite','arms':ARMS,'scenarios':SCENARIOS,'inputs':items,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'role':'same author workflow; only external endpoint changes; timings descriptive'},indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='db-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('w') as f:
  for item in items:
   for t in ['claude','codex','grok']:
    for s in SCENARIOS:
     for m in ARMS:
      try:r=one(Path(tmp)/str(len(rows)),item,t,m,s)
      except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
      row={'method':m,'tool':t,'scenario':s,'repository':item['repository'],**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
      if not r['pass']:print(json.dumps(row),flush=True)
    print(json.dumps({'cases':len(rows),'passed':sum(r['pass'] for r in rows),'seconds':time.perf_counter()-began}),flush=True)
 report={'cases':len(rows),'passed':sum(r['pass'] for r in rows),'errors':sum('exception' in r for r in rows),'seconds':time.perf_counter()-began,
  'arms':{m:{'cases':sum(r['method']==m for r in rows),'unique_current':sum(r['method']==m and not r.get('historical_response',False) and r.get('oracle',{}).get('unique_api_completion',False) for r in rows),
   'historical':sum(r['method']==m and r.get('historical_response',False) for r in rows),'activations':sum(r.get('activation_calls',0) for r in rows if r['method']==m)} for m in ARMS}}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert all(r['pass'] for r in rows)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--inputs',type=int,default=2);main(p.parse_args())
