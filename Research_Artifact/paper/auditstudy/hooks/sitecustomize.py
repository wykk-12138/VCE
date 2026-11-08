"""Test-only process/write observations; enabled solely in lifecycle fixtures.

Loaded with PYTHONPATH in those children, never in timing runs. Neither the gate
nor the original native scripts are edited. Pauses are synchronization points,
not measured latency or a substitute for killing the actual OS process.
"""
import json,os,runpy,sys,time
from pathlib import Path
if os.environ.get('AUDIT_LIFECYCLE') and os.environ.get('EVOLUTION_GATE_COMMAND')=='activate':
 _log=Path(os.environ['AUDIT_LIFECYCLE']);_cut=os.environ['AUDIT_CUT']
 _ready=Path(os.environ['AUDIT_READY']);_released=_ready.with_suffix('.release')
 _original=os.environ['EVOLUTION_ORIGINAL_CLI'];_replaced=False
 def event(kind,**fields):
  with _log.open('a',encoding='utf8') as f:f.write(json.dumps({'kind':kind,'pid':os.getpid(),'ppid':os.getppid(),'ns':time.perf_counter_ns(),**fields})+'\n')
 def pause():
  event('pause',cut=_cut,lease=os.environ['EVOLUTION_NATIVE_LEASE'])
  _ready.write_text(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),'lease':os.environ['EVOLUTION_NATIVE_LEASE']}))
  end=time.monotonic()+25
  while not _released.exists():
   if time.monotonic()>end:raise TimeoutError('lifecycle handshake')
   time.sleep(.005)
 def audit(name,args):
  if name in {'subprocess.Popen','os.system','os.posix_spawn','os.spawn'}:
   event('subprocess_spawn',audit_event=name,executable=str(args[0]))
 sys.addaudithook(audit)
 _replace=os.replace
 def replace(src,dst,*args,**kwargs):
  global _replaced
  result=_replace(src,dst,*args,**kwargs)
  event('replace_completed',source=str(src),destination=str(dst),backend='os.replace')
  if not _replaced:
   _replaced=True
   if _cut=='during':pause()
  return result
 os.replace=replace
 def profile(frame,kind,arg):
  global _replaced
  if kind=='return' and frame.f_code.co_name=='replace_atomic' and os.path.normcase(frame.f_code.co_filename)==os.path.normcase(_original):
   src=frame.f_locals.get('source');dst=frame.f_locals.get('destination')
   # Codex's Windows backend publishes via native handles rather than os.replace.
   # Observe the real return and resulting names, without changing its method.
   if dst is not None and Path(dst).is_file() and src is not None and not Path(src).exists():
    event('replace_completed',source=str(src),destination=str(dst),backend='adapter.replace_atomic')
    if not _replaced:
     _replaced=True
     if _cut=='during':pause()
 sys.setprofile(profile)
 _run=runpy.run_path
 def run_path(path,*args,**kwargs):
  if os.path.normcase(os.path.abspath(path))!=os.path.normcase(os.path.abspath(_original)):return _run(path,*args,**kwargs)
  event('native_enter',script=str(path))
  if _cut=='before':pause()
  code=0
  try:return _run(path,*args,**kwargs)
  except SystemExit as exc:
   code=exc.code or 0
   raise
  except BaseException:
   code=1
   raise
  finally:
   event('native_return',code=code)
   if _cut=='after' and code==0:pause()
 runpy.run_path=run_path
 event('hook_loaded',script=_original)
