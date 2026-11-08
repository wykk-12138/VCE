"""A live native writer outlives a forcibly terminated Rust coordinator.

Pause markers synchronize actual OS processes; no sleeps emulate native work.
The two ablations remove one guard at a time from the proposed implementation.
"""
import argparse,hashlib,json,tempfile,time,traceback
from contextlib import closing
from .client import *
from .safety import completed
from .diagnose import ownership

def events(path):return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

def until(predicate,seconds=15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if predicate():return
  time.sleep(.01)
 raise TimeoutError('history synchronization timed out')

def run_case(root,item,tool,method,schedule,ablation='',binary=BINARY):
 setup(root,item,tool);p=plan(root,tool,method,binary=binary)
 signal=root/'release';ready=signal.with_suffix('.ready');event_path=root/'gate_events.jsonl'
 key='EVOLUTION_PAUSE_BEFORE_GATE' if schedule=='delayed_old_entry' else 'EVOLUTION_PAUSE_IN_GATE'
 env={key:str(signal),'EVOLUTION_GATE_EVENTS':str(event_path)}
 if ablation:env['EVOLUTION_ABLATE_'+ablation.upper()]='1'
 child=start(root,tool,'confirm',binary=binary,extra=env,**arguments(method,p));qchild=None
 try:
  until(lambda:ready.exists() and ready.read_text().strip().isdigit());old_pid=int(ready.read_text());child.kill();child.wait(timeout=5)
  # The old native process is paused and owns inherited stdout. Do not wait for its pipe EOF yet.
  qvalue=b'# New Q owns the deployment after the coordinator crash\n';(root/'candidate.md').write_bytes(qvalue)
  qchild=start(root,tool,'plan',binary=binary,method=method,extra={'EVOLUTION_GATE_EVENTS':str(event_path)})
  blocked=None
  if schedule=='live_old_writer' and not ablation:
   # Observe the coordinator while the old writer retains the kernel lease.
   time.sleep(.20);blocked=qchild.poll() is None
   signal.touch()
  qresult=finish(qchild);q=qresult.get('response',{}).get('data',{})
  assert q.get('plan',{}).get('envelope',{}).get('ok'),qresult
  second=confirm(root,tool,method,q,binary=binary,extra={'EVOLUTION_GATE_EVENTS':str(event_path)})
  assert completed(root,tool,q,second,qvalue),second
  before=ownership(root)
  signal.touch()
  child.communicate(timeout=15) # EOF establishes termination of the gate/native process.
  history=events(event_path)
  old=[e for e in history if e['pid']==old_pid]
  disk_preserved=installed(root,tool).read_bytes().replace(b'\r\n',b'\n')==qvalue
  owns=ownership(root)==before
  retry=confirm(root,tool,method,p,binary=binary,retry=True)
  all_good=disk_preserved and owns and not api_success(retry) and ownership(root)==before
  if schedule=='delayed_old_entry':all_good=all_good and any(e['kind']=='fenced' for e in old)
  elif not ablation:all_good=all_good and blocked is True and any(e['kind']=='leave' for e in old)
  return {'pass':all_good,'later_bytes_preserved':disk_preserved,'later_ownership_preserved':owns,'new_plan_waited':blocked,
   'old_native_pid':old_pid,'killed_coordinator_pid':child.pid,'old_native_events':old,'events':history,'retry':retry,'second':second}
 finally:
  signal.touch()
  for process in [child,qchild]:
   if process is None:continue
   if process.poll() is None:process.kill()
   try:process.communicate(timeout=15)
   except subprocess.TimeoutExpired:raise RuntimeError('owned child did not terminate after releasing pause')

def main(a):
 out=a.out
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True);item=corpus('development')[0];binary=RELEASE if a.release else BINARY
 arms=[(m,'') for m in METHODS]+[('ReceiptCoordinatorV13','fence'),('ReceiptCoordinatorV13','lease')]
 spec={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'arms':arms,'schedules':['delayed_old_entry','live_old_writer'],
  'notes':'Coordinator killed by OS; native gate paused by handshake. Only matching ablation schedule is used.'}
 (out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');rows=[];began=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='orphans-',dir=SCRATCH) as tmp,(out/'raw.jsonl').open('w') as f:
  for method,ablation in arms:
   for tool in ['claude','codex','grok']:
    for schedule in spec['schedules']:
     if ablation=='fence' and schedule!='delayed_old_entry' or ablation=='lease' and schedule!='live_old_writer':continue
     try:r=run_case(Path(tmp)/str(len(rows)),item,tool,method,schedule,ablation,binary)
     except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
     row={'method':method,'tool':tool,'schedule':schedule,'ablation':ablation,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
     print(json.dumps({k:v for k,v in row.items() if k not in ['retry','second','events','old_native_events','traceback']}),flush=True)
 report={'full_cases':sum(not r['ablation'] for r in rows),'full_passed':sum(r['pass'] and not r['ablation'] for r in rows),
  'ablation_cases':sum(bool(r['ablation']) for r in rows),'ablation_bytes_regressions':sum(bool(r['ablation']) and not r.get('later_bytes_preserved',True) for r in rows),
  'exceptions':sum('exception' in r for r in rows),'seconds':time.perf_counter()-began}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--release',action='store_true');main(p.parse_args())
