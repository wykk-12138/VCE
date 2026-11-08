"""Paired randomized CPU measurements; every arm retained independently of rank."""
import argparse,concurrent.futures,hashlib,json,math,platform,random,shutil,sqlite3,statistics,tempfile,time
from contextlib import closing
from .client import *

class Warm:
 def __init__(self,root):
  self.child=subprocess.Popen([str(RELEASE)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT,
   env=environment(root),text=True,encoding='utf-8',bufsize=1)
 def call(self,root,tool,command,**kw):
  began=time.perf_counter_ns();self.child.stdin.write(json.dumps(request(root,tool,command,**kw))+'\n');self.child.stdin.flush()
  line=self.child.stdout.readline()
  if not line:raise RuntimeError(self.child.stderr.read())
  return {'exit_code':0,'wall_ns':time.perf_counter_ns()-began,'response':json.loads(line)}
 def close(self):
  self.child.stdin.close();self.child.stdin=None;self.child.communicate(timeout=10)

def serial(root,item,method,tool,scenario,lifecycle):
 setup(root,item,tool);warm=Warm(root) if lifecycle=='warm_manager' else None
 invoke=warm.call if warm else lambda *a,**kw:call(*a,binary=RELEASE,**kw)
 try:
  planned=invoke(root,tool,'plan',method=method);p=planned['response']['data'];kw=arguments(method,p)
  assert p['plan']['envelope']['ok'],planned
  if scenario=='recovery':
   first=confirm(root,tool,method,p,binary=RELEASE,fault='after_native');assert first['exit_code']==86,first
  n=len(trace(root));r=invoke(root,tool,'confirm',**kw);assert api_success(r),r
  commands=[x['command'] for x in trace(root)[n:]]
  with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
   count=db.execute("SELECT COUNT(*) FROM operations WHERE kind='activate' AND status='succeeded' AND parent_id=?",(p['plan']['operationId'],)).fetchone()[0]
  assert count==1
  assert installed(root,tool).read_bytes().replace(b'\r\n',b'\n')==(root/'candidate.md').read_bytes().replace(b'\r\n',b'\n')
  return {'wall_ns':r['wall_ns'],'handler_ns':r['response']['elapsed_ns'],'commands':commands,'pass':True}
 finally:
  if warm:warm.close()

def batch(root,item,method,width):
 setup(root,item,'claude');projects=[]
 for i in range(width):
  p=root/f'project-{i}';shutil.copytree(root/'project',p);projects.append(p)
 plans=[plan(root,'claude',method,binary=RELEASE,project_dir=str(p)) for p in projects]
 def execute(p):return confirm(root,'claude',method,p,binary=RELEASE)
 with concurrent.futures.ThreadPoolExecutor(max_workers=width) as executor:
  # Worker startup is in the measured service batch for every method.
  begin=time.perf_counter_ns();results=list(executor.map(execute,plans));wall=time.perf_counter_ns()-begin
 for r in results:assert api_success(r),r
 desired=(root/'candidate.md').read_bytes().replace(b'\r\n',b'\n')
 for project in projects:assert (project/'.claude/receiptcoordinator/claude-project-rules.md').read_bytes().replace(b'\r\n',b'\n')==desired
 with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
  count=db.execute("SELECT COUNT(*) FROM operations WHERE kind='activate' AND status='succeeded'").fetchone()[0]
  active=db.execute('SELECT COUNT(*) FROM activations WHERE status=\'active\'').fetchone()[0]
 assert count==width and active==width
 return {'wall_ns':wall,'throughput':width/(wall/1e9),'requests_wall_ns':[r['wall_ns'] for r in results],'pass':True}

def ratio_ci(pairs,rng):
 logs=[math.log(a/b) for a,b in pairs];n=len(logs)
 avg=math.exp(statistics.mean(logs));boots=sorted(math.exp(statistics.mean(rng.choices(logs,k=n))) for _ in range(4000))
 return {'ratio':avg,'ci95':[boots[int(.025*len(boots))],boots[int(.975*len(boots))]],'pairs':n}

def summarize(rows):
 rng=random.Random(13102);groups={}
 for r in rows:
  if r.get('warmup'):continue
  key='/'.join(str(r[k]) for k in ['kind','tool','scenario','lifecycle','width'])
  groups.setdefault(key,{}).setdefault(r['method'],[]).append(r)
 summary={}
 for key,arms in groups.items():
  stats={m:{'median_ms':statistics.median(x['wall_ns'] for x in rs)/1e6,'samples':len(rs)} for m,rs in arms.items()}
  proposed={r['block']:r for r in arms['ReceiptCoordinatorV13']}
  ratios={}
  for control in ['JournalGuarded','JournalGuardedScoped']:
   controls={r['block']:r for r in arms[control]}
   pairs=[(proposed[b]['wall_ns'],controls[b]['wall_ns']) for b in proposed.keys()&controls.keys()]
   ratios[control]=ratio_ci(pairs,rng)
  summary[key]={'arms':stats,'proposed_over_control':ratios}
 return summary

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 a.out.mkdir(parents=True);items=corpus('confirmation');rng=random.Random(13101)
 spec={'binary_sha256':hashlib.sha256(RELEASE.read_bytes()).hexdigest(),'gate_sha256':hashlib.sha256((ROOT/'.research-source/native-rust-v13/native_gate.py').read_bytes()).hexdigest(),
  'methods':METHODS,'blocks':a.blocks,'warmup_blocks':1,'widths':[1,2,4,8],'cpu_count':os.cpu_count(),'platform':platform.platform(),
  'measurement':'optimized research binary; serial blocked paired order; native Python CLI remains a fresh process in warm_manager mode',
  'bootstrap':'4000 resamples of paired per-block log ratios; exploratory intervals, no optional stopping',
  'phase':'development performance comparison; evidence pool previously used; all arms retained'}
 (a.out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');rows=[];start_time=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='bench-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('w') as f:
  for block in range(-1,a.blocks):
   item=items[(block+1)%len(items)];conditions=[]
   if a.mode in {'all','serial'}:
    conditions.extend(('serial',tool,scenario,life,1) for tool in ['claude','codex','grok'] for scenario in ['normal','recovery'] for life in ['cold_manager','warm_manager'])
   if a.mode in {'all','concurrent'}:conditions.extend(('batch','claude','normal','cold_manager',width) for width in [1,2,4,8])
   rng.shuffle(conditions)
   for kind,tool,scenario,lifecycle,width in conditions:
    order=METHODS.copy();rng.shuffle(order)
    for method in order:
     root=Path(tmp)/str(len(rows))
     try:r=serial(root,item,method,tool,scenario,lifecycle) if kind=='serial' else batch(root,item,method,width)
     except Exception as e:r={'pass':False,'exception':repr(e)}
     row={'block':block,'warmup':block<0,'kind':kind,'method':method,'tool':tool,'scenario':scenario,'lifecycle':lifecycle,'width':width,
      'repository':item['repository'],'payload':item['payload']['path'],**r}
     rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
     if not row['pass']:raise RuntimeError(row)
   print(json.dumps({'block':block,'observations':len(rows),'seconds':time.perf_counter()-start_time}),flush=True)
 report={'observations':len(rows),'passed':sum(r['pass'] for r in rows),'seconds':time.perf_counter()-start_time,'comparisons':summarize(rows)}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'finished':len(rows),'seconds':report['seconds']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--blocks',type=int,default=12);p.add_argument('--mode',choices=['all','serial','concurrent'],default='all');main(p.parse_args())
