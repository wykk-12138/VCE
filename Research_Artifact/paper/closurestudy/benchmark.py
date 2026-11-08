"""Frozen-design serial confirmation; all intervals retain preview explicitly."""
import argparse,hashlib,json,os,platform,random,sqlite3,statistics,tempfile,time
from contextlib import closing
from .client import *
from paper.evolutionstudy.benchmark import ratio_ci
from paper.evolutionstudy.client import environment,request
from paper.finalstudy.cases import oracle

class Warm:
 def __init__(self,root):
  self.child=subprocess.Popen([str(BINARY)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT,
   env=environment(root,{'TMP':str(SCRATCH),'TEMP':str(SCRATCH),'RECEIPTCOORDINATOR_COMPONENT_PROFILE':str(root/'components.jsonl'),'WITNESS_TRACE':str(root/'witness_trace.jsonl')}),text=True,encoding='utf8')
  self.call(root,'claude','records')
 def call(self,root,tool,command,**kw):
  begin=time.perf_counter_ns();self.child.stdin.write(json.dumps(request(root,tool,command,**kw))+'\n');self.child.stdin.flush()
  line=self.child.stdout.readline();assert line,'warm manager exited'
  return {'exit_code':0,'wall_ns':time.perf_counter_ns()-begin,'response':json.loads(line)}
 def close(self):self.child.stdin.close();self.child.stdin=None;self.child.communicate(timeout=15)

def one(root,item,tool,method,scenario,life,noise):
 fixture=setup(root,item,tool)
 if noise:
  d=root/'project/source';d.mkdir(exist_ok=True)
  for i in range(noise):(d/f'{i}.txt').write_bytes(b'x'*1024)
 preview=call(root,tool,'plan',method=method);p=preview['response']['data'];assert p['plan']['envelope']['ok'],preview
 first=None
 if scenario!='normal':
  first=confirm(root,tool,method,p,**({} if scenario=='completed_retry' else {'fault':'after_native'}))
  assert api_success(first) if scenario=='completed_retry' else first['exit_code']==86,first
 if scenario=='fallback':
  with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='native_completion_evidence'").fetchone():db.execute('DELETE FROM native_completion_evidence');db.commit()
 if scenario=='unrelated_edit':(root/'project/new-source.txt').write_text('unrelated source edit')
 warm=Warm(root) if life=='warm' else None
 try:
  np=len(logs(root,'adapter_profile.jsonl'));nc=len(logs(root,'components.jsonl'));nt=len(trace(root))
  r=warm.call(root,tool,'confirm',**arguments(method,p)) if warm else confirm(root,tool,method,p)
  assert api_success(r),r
  profile=logs(root,'adapter_profile.jsonl')[np:];components=logs(root,'components.jsonl')[nc:];commands=[x['command'] for x in trace(root)[nt:]]
  footprint=0
  with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='native_completion_evidence'").fetchone():
    row=db.execute('SELECT evidence FROM native_completion_evidence WHERE plan=?',(p['plan']['operationId'],)).fetchone()
    footprint=len(row[0].encode()) if row else 0
  checked=oracle(root,tool,fixture,p['prompt_id'],p['plan']['operationId'],method,r);assert checked['unique_api_completion'],checked
  initial=first['wall_ns'] if first else 0
  return {'pass':True,'wall_ns':r['wall_ns'],'handler_ns':r['response']['elapsed_ns'],'preview_ns':preview['wall_ns'],
   'first_ns':initial,'confirmation_episode_ns':initial+r['wall_ns'],'episode_ns':preview['wall_ns']+initial+r['wall_ns'],
   'commands':commands,'all_commands':[x['command'] for x in trace(root)[:-1]],'profile':profile,'components':components,'evidence_bytes':footprint,'oracle':checked}
 finally:
  if warm:warm.close()

def summarize(rows):
 groups={};rng=random.Random(16102)
 for r in rows:
  if r['warmup']:continue
  key=f"{r['tool']}/{r['scenario']}/{r['lifecycle']}/{r['noise']}";groups.setdefault(key,{}).setdefault(r['method'],[]).append(r)
 result={}
 for key,arms in groups.items():
  proposed={r['block']:r for r in arms['ReceiptCoordinatorV15']}
  rec={'arms':{},'paired':{}}
  for m,rs in arms.items():
   rec['arms'][m]={'n':len(rs),'median_ms':statistics.median(r['wall_ns'] for r in rs)/1e6,
    'mean_episode_ms':statistics.mean(r['episode_ns'] for r in rs)/1e6,'median_episode_ms':statistics.median(r['episode_ns'] for r in rs)/1e6,
    'native_commands':sorted(set(tuple(r['commands']) for r in rs)), 'mean_evidence_bytes':statistics.mean(r['evidence_bytes'] for r in rs)}
   paired={r['block']:r for r in rs}
   if m!='ReceiptCoordinatorV15':rec['paired'][m]={metric:ratio_ci([(proposed[i][metric],paired[i][metric]) for i in sorted(proposed)],rng) for metric in ['wall_ns','episode_ns','confirmation_episode_ns']}
  result[key]=rec
 return result

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 a.out.mkdir(parents=True);configure()
 # One fixed first-priority payload per repository makes each paired block
 # a distinct project, rather than overweighting projects with two payloads.
 selected={}
 for item in corpus('confirmation'):selected.setdefault(item['repository'],item)
 items=list(selected.values());assert len(items)==12
 rng=random.Random(16101);rows=[];began=time.perf_counter()
 conditions=[(t,s,l,0) for t in ['claude','codex','grok'] for s,l in [('normal','cold'),('recovery','cold'),('recovery','warm'),('fallback','cold'),('completed_retry','cold')]]
 conditions += [('claude','recovery','cold',2048),('claude','unrelated_edit','cold',0)]
 if a.smoke:conditions=[(t,'normal','cold',0) for t in ['claude','codex','grok']]+[('claude','recovery','warm',0)]
 spec={'methods':METHODS,'conditions':conditions,'blocks':a.blocks,'warmup_blocks':0 if a.smoke else 1,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),
  'profile':'opt-level=3, debug-assertions=false; explicit research CLI entry','platform':platform.platform(),'cpus':os.cpu_count(),
  'inputs':items,'input_note':'One fixed first-priority payload per previously used public confirmation repository; no new holdout claim','estimator':'geometric mean of paired ratios; 4000 project-block bootstrap replicates; pointwise 95% CI',
  'episode':'preview + first confirmation (if any) + measured confirmation; fixture edits and independent oracle excluded'}
 (a.out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='b-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('w') as f:
  for block in range(0 if a.smoke else -1,a.blocks):
   item=items[(block+1)%len(items)];order=conditions.copy();rng.shuffle(order)
   for tool,scenario,life,noise in order:
    methods=METHODS.copy();rng.shuffle(methods)
    for method in methods:
     try:r=one(Path(tmp)/str(len(rows)),item,tool,method,scenario,life,noise)
     except Exception as e:r={'pass':False,'exception':repr(e)}
     row={'block':block,'warmup':block<0,'tool':tool,'scenario':scenario,'lifecycle':life,'noise':noise,'method':method,'repository':item['repository'],**r}
     rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
     if not r['pass']:raise RuntimeError(row)
   print(json.dumps({'block':block,'observations':len(rows),'seconds':time.perf_counter()-began}),flush=True)
 report={'observations':len(rows),'scored':sum(not r['warmup'] for r in rows),'passed':sum(r['pass'] for r in rows),'seconds':time.perf_counter()-began,'comparisons':summarize(rows)}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'finished':len(rows),'seconds':report['seconds']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--blocks',type=int,default=12);p.add_argument('--smoke',action='store_true');main(p.parse_args())
