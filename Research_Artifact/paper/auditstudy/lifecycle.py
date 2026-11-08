"""Kill the lease-owning gate PID, immediately retry, and check real OS order."""
import argparse,ctypes,hashlib,json,msvcrt,os,shutil,subprocess,tempfile,time,traceback
from ctypes import wintypes
from pathlib import Path
from paper.closurestudy.client import BINARY,ROOT,configure,setup,corpus,plan,confirm,api_success,logs
from paper.evolutionstudy.client import start,finish,arguments
from paper.evolutionstudy.orphans import until
from paper.finalstudy import cases

SCRATCH=ROOT/'.research-tmp/audit-v17';SCRATCH.mkdir(exist_ok=True)
def lock_available(path):
 with open(path,'a+b',buffering=0) as f:
  f.seek(0)
  try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:return False
  f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);return True
def children(pid):
 class Entry(ctypes.Structure):
  _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),('priority',wintypes.LONG),('flags',wintypes.DWORD),('exe',wintypes.WCHAR*260)]
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
 k.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)];k.Process32NextW.argtypes=k.Process32FirstW.argtypes;k.CloseHandle.argtypes=[wintypes.HANDLE]
 h=k.CreateToolhelp32Snapshot(2,0);e=Entry();e.size=ctypes.sizeof(e);found=[]
 try:
  ok=k.Process32FirstW(h,ctypes.byref(e))
  while ok:
   if e.parent==pid:
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE;k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    handle=k.OpenProcess(0x1000,False,e.pid);path=''
    if handle:
     try:
      size=wintypes.DWORD(32768);buffer=ctypes.create_unicode_buffer(size.value)
      if k.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)):path=buffer.value
     finally:k.CloseHandle(handle)
    console=bool(path) and os.path.normcase(path)==os.path.normcase(str(Path(os.environ['SystemRoot'])/'System32/conhost.exe'))
    found.append({'pid':e.pid,'exe':e.exe,'image_path':path,'verified_system_console':console})
   ok=k.Process32NextW(h,ctypes.byref(e))
 finally:k.CloseHandle(h)
 return found
def kill_and_wait(pid):
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
 k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.CloseHandle.argtypes=[wintypes.HANDLE]
 h=k.OpenProcess(0x100000|0x0001,False,pid)
 if not h:raise ctypes.WinError(ctypes.get_last_error())
 try:
  requested=time.perf_counter_ns()
  if not k.TerminateProcess(h,137):raise ctypes.WinError(ctypes.get_last_error())
  assert k.WaitForSingleObject(h,5000)==0,'gate did not terminate'
  return {'kill_requested_ns':requested,'termination_observed_ns':time.perf_counter_ns()}
 finally:k.CloseHandle(h)
def status(root,tool):
 r=cases.call(root,tool,'status');e=r.get('response',{}).get('data',{}).get('envelope',{})
 return {'accepted':e.get('ok') is True and e.get('status')=='active' and not e.get('recoveryRequired') and not e.get('blockers'), 'response':r}
def one(root,item,tool,method,cut):
 setup(root,item,tool);p=plan(root,tool,method);ready=root/'ready.json';life=root/'lifecycle.jsonl';gate=root/'gate_events.jsonl'
 env={'AUDIT_LIFECYCLE':str(life),'AUDIT_CUT':cut,'AUDIT_READY':str(ready),'PYTHONPATH':str(ROOT/'paper/auditstudy/hooks'),'EVOLUTION_GATE_EVENTS':str(gate)}
 began=time.perf_counter_ns();child=start(root,tool,'confirm',binary=BINARY,extra=env,**arguments(method,p));terminated=False
 try:
  until(lambda:ready.exists() and ready.stat().st_size>0,seconds=20)
  mark=json.loads(ready.read_text());pid=mark['pid'];assert mark['ppid']==child.pid
  held=not lock_available(mark['lease']);descendants=children(pid)
  killed=kill_and_wait(pid);terminated=True
  immediate=lock_available(mark['lease']);retry_started=time.perf_counter_ns()
  retry=start(root,tool,'confirm',binary=BINARY,extra={'EVOLUTION_GATE_EVENTS':str(gate)},**arguments(method,p,retry=True))
  result=finish(retry,retry_started);first=finish(child,began);released=lock_available(mark['lease']);check=status(root,tool)
  h=logs(root,'lifecycle.jsonl');g=logs(root,'gate_events.jsonl');writes=[e for e in h if e['kind']=='replace_completed']
  later=[e for e in g if e['pid']!=pid and e['ns']>=retry_started]
  same_pid=all(e['pid']==pid for e in h)
  order=all(e['ns']<killed['termination_observed_ns'] for e in h) and all(e['ns']>=killed['termination_observed_ns'] for e in later)
  safe=not api_success(result) or check['accepted']
  after_ok=cut!='after' or api_success(result)
  spawn_events=[e for e in h if e['kind']=='subprocess_spawn']
  writer_children=[c for c in descendants if not c['verified_system_console']]
  passed=held and released and not writer_children and not spawn_events and same_pid and order and safe and after_ok and (cut!='during' or bool(writes)) and not api_success(first)
  return {'pass':passed,'gate_pid':pid,'manager_pid':child.pid,'held_before_kill':held,'available_immediately_after_termination':immediate,'available_after_termination':released,'gate_children_at_cut':descendants,'unexpected_gate_children':writer_children,'spawn_events':spawn_events,'same_native_gate_pid':same_pid,'ordering_valid':order,'retry_started_ns':retry_started,**killed,'writes_before_kill':len(writes),'retry_completed':api_success(result),'native_current':check['accepted'],'first':first,'retry':result,'oracle':check,'lifecycle_events':h,'gate_events':g}
 finally:
  ready.with_suffix('.release').touch()
  if child.poll() is None:child.kill()
  child.communicate(timeout=15)
def main(a):
 assert os.name=='nt';configure();a.out.mkdir(parents=True,exist_ok=False);rows=[];selected={}
 for item in corpus('confirmation'):selected.setdefault(item['repository'],item)
 items=list(selected.values())[:2]
 spec={'methods':['JournalGuardedScoped','ReceiptCoordinatorV15','JournalWitnessV15'],'tools':['claude','codex','grok'],'cuts':['before','during','after'],'inputs':items,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'hook_sha256':hashlib.sha256((ROOT/'paper/auditstudy/hooks/sitecustomize.py').read_bytes()).hexdigest(),'during':'Pause after the first actual atomic replacement returns in original activation. Gate is then killed via TerminateProcess and process handle waited before retry.','timing':'Validity experiment only; test hook excluded from all timing runs.'}
 spec['external_grok_launcher_present']=shutil.which('grok') is not None
 assert not spec['external_grok_launcher_present'],'This pinned lifecycle contract excludes an external Grok host launcher'
 (a.out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='l-',dir=SCRATCH) as temp,(a.out/'raw.jsonl').open('w') as f:
  for item in items:
   for method in spec['methods']:
    for tool in spec['tools']:
     for cut in spec['cuts']:
      try:r=one(Path(temp)/str(len(rows)),item,tool,method,cut)
      except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
      row={'repository':item['repository'],'method':method,'tool':tool,'cut':cut,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
      print(json.dumps({k:v for k,v in row.items() if k not in ['first','retry','oracle','lifecycle_events','gate_events','traceback']}),flush=True)
      if not r['pass']:raise RuntimeError(row)
 report={'cases':len(rows),'passed':sum(r['pass'] for r in rows),'safe_refusals':sum(not r['retry_completed'] for r in rows),'completed_retries':sum(r['retry_completed'] for r in rows),'same_pid_cases':sum(r['same_native_gate_pid'] for r in rows),'held_before_kill':sum(r['held_before_kill'] for r in rows),'released_after_kill':sum(r['available_after_termination'] for r in rows),'unexpected_gate_children':sum(len(r['unexpected_gate_children']) for r in rows),'system_console_children':sum(sum(c['verified_system_console'] for c in r['gate_children_at_cut']) for r in rows)}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args())
