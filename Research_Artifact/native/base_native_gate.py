"""Run an unchanged Python adapter while its execution process owns the native lease.

The lease is acquired before checking the durable target generation. A delayed
old process therefore cannot enter the adapter after a newer claim. This gate
is shared by both v13 endpoint implementations; it is not a claimed novelty.
"""
import contextlib,json,os,runpy,sqlite3,sys,time
from pathlib import Path

@contextlib.contextmanager
def lease(path):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('a+b',buffering=0) as f:
  started=time.monotonic()
  while True:
   f.seek(0)
   try:
    if os.name=='nt':
     import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    else:
     import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    break
   except OSError:
    if time.monotonic()-started>60:raise TimeoutError('native lease timeout')
    time.sleep(.01)
  try:yield
  finally:
   f.seek(0)
   if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
   else:fcntl.flock(f,fcntl.LOCK_UN)
def event(kind,**extra):
 path=os.environ.get('EVOLUTION_GATE_EVENTS')
 if path:
  line=json.dumps({'kind':kind,'pid':os.getpid(),'ns':time.perf_counter_ns(),'command':os.environ.get('EVOLUTION_GATE_COMMAND'),**extra})+'\n'
  fd=os.open(path,os.O_CREAT|os.O_APPEND|os.O_WRONLY)
  try:os.write(fd,line.encode())
  finally:os.close(fd)
def pause(key):
 path=os.environ.get(key)
 if path and os.environ.get('EVOLUTION_GATE_COMMAND')=='activate':
  p=Path(path);p.with_suffix('.ready').write_text(str(os.getpid()))
  start=time.monotonic()
  while not p.exists():
   if time.monotonic()-start>25:raise TimeoutError('development gate pause')
   time.sleep(.01)
def main():
 pause('EVOLUTION_PAUSE_BEFORE_GATE')
 guard=contextlib.nullcontext() if os.environ.get('EVOLUTION_ABLATE_LEASE')=='1' else lease(os.environ['EVOLUTION_NATIVE_LEASE'])
 with guard:
  expected=os.environ.get('EVOLUTION_EXPECTED_PLAN')
  if expected:
   with sqlite3.connect(os.environ['EVOLUTION_DB'],timeout=20) as db:
    row=db.execute('SELECT generation,plan FROM evolution_heads WHERE target=?',(os.environ['EVOLUTION_TARGET'],)).fetchone()
   if row!=(int(os.environ['EVOLUTION_GENERATION']),expected) and os.environ.get('EVOLUTION_ABLATE_FENCE')!='1':
    event('fenced');print('superseded native invocation',file=sys.stderr);raise SystemExit(75)
  if os.environ.get('WITNESS_ATTEMPT'):
   with sqlite3.connect(os.environ['EVOLUTION_DB'],timeout=20) as db:
    attempt=db.execute('SELECT plan,token FROM native_attempts WHERE target=?',(os.environ['EVOLUTION_TARGET'],)).fetchone()
   if attempt!=(os.environ['EVOLUTION_EXPECTED_PLAN'],os.environ['WITNESS_ATTEMPT']):event('fenced');raise SystemExit(75)
  event('enter');pause('EVOLUTION_PAUSE_IN_GATE')
  script=os.environ['EVOLUTION_ORIGINAL_CLI'];sys.argv=[script,*sys.argv[1:]];sys.path.insert(0,str(Path(script).parent))
  try:runpy.run_path(script,run_name='__main__')
  finally:event('leave')
if __name__=='__main__':main()
