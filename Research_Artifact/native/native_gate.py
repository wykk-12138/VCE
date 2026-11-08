"""Persist actual CLI completion while the executing process holds its lease."""
import contextlib,hashlib,io,json,os,runpy,sqlite3,stat,sys,time
from pathlib import Path
from base_native_gate import lease,event,pause,main as ordinary_main

MAX_FILES=4096
MAX_BYTES=64*1024*1024

def file_identity(path):
 if os.name!='nt':
  s=path.stat();return f'{s.st_dev}:{s.st_ino}'
 import ctypes
 from ctypes import wintypes
 class FileId(ctypes.Structure):_fields_=[('volume',ctypes.c_uint64),('id',ctypes.c_ubyte*16)]
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 create=kernel.CreateFileW;create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];create.restype=wintypes.HANDLE
 get=kernel.GetFileInformationByHandleEx;get.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.LPVOID,wintypes.DWORD];get.restype=wintypes.BOOL
 close=kernel.CloseHandle;close.argtypes=[wintypes.HANDLE];close.restype=wintypes.BOOL
 handle=create(str(path),0x80000000,7,None,3,0x02000000,None)
 if handle==wintypes.HANDLE(-1).value:raise ctypes.WinError(ctypes.get_last_error())
 try:
  data=FileId()
  if not get(handle,18,ctypes.byref(data),ctypes.sizeof(data)):raise ctypes.WinError(ctypes.get_last_error())
  return f'{data.volume}:{bytes(data.id).hex()}'
 finally:close(handle)

def selected(key,name,policy):
 if not policy.startswith('claude-project-v1'):return True
 fixed=name.lower() if os.name=='nt' else name;directory=key.lower() if os.name=='nt' else key
 if key=='0':return fixed in ({'claude.md','.claude'} if os.name=='nt' else {'CLAUDE.md','.claude'}) or (policy=='claude-project-v1' and name.startswith('.') and '.receiptcoordinator-tmp-' in name and name.endswith('.tmp'))
 if directory=='0/.claude':return fixed=='receiptcoordinator'
 return True

def snapshot(roots,policy):
 result={};work=[0,0]
 def visit(path,key):
  try:s=path.lstat()
  except FileNotFoundError:result[key]={'kind':'missing'};return
  if path.is_symlink() or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('unverified reparse node')
  work[0]+=1
  if work[0]>MAX_FILES:raise ValueError('snapshot node budget')
  if stat.S_ISDIR(s.st_mode):
   result[key]={'kind':'directory','identity':file_identity(path)}
   for child in sorted(path.iterdir(),key=lambda p:p.name):
    if selected(key,child.name,policy):visit(child,key+'/'+child.name)
  elif stat.S_ISREG(s.st_mode):
   work[1]+=s.st_size
   if work[1]>MAX_BYTES:raise ValueError('snapshot byte budget')
   raw=path.read_bytes();after=path.stat()
   if (s.st_size,s.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('unstable snapshot')
   result[key]={'kind':'file','identity':file_identity(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':s.st_size,'mtime_ns':str(s.st_mtime_ns),
    'readonly':bool(s.st_file_attributes&1) if os.name=='nt' else not bool(s.st_mode&stat.S_IWUSR)}
  else:raise ValueError('unverified node type')
 for i,root in enumerate(roots):visit(Path(root),str(i))
 return result

def main():
 if os.environ.get('EVOLUTION_GATE_COMMAND')=='status' and os.environ.get('CLOSURE_STATUS_FAILURE'):
  mode=os.environ['CLOSURE_STATUS_FAILURE']
  if mode=='malformed':print('not a native JSON response');return
  os._exit(87)
 if os.environ.get('WITNESS_ENABLED')!='1' or os.environ.get('EVOLUTION_GATE_COMMAND')!='activate':return ordinary_main()
 pause('EVOLUTION_PAUSE_BEFORE_GATE')
 with lease(os.environ['EVOLUTION_NATIVE_LEASE']):
  plan=os.environ['EVOLUTION_EXPECTED_PLAN'];generation=int(os.environ['EVOLUTION_GENERATION']);target=os.environ['EVOLUTION_TARGET']
  with sqlite3.connect(os.environ['EVOLUTION_DB'],timeout=20) as db:
   row=db.execute('SELECT generation,plan FROM evolution_heads WHERE target=?',(target,)).fetchone()
   attempt=db.execute('SELECT plan,token FROM native_attempts WHERE target=?',(target,)).fetchone()
  if row!=(generation,plan) or attempt!=(plan,os.environ['WITNESS_ATTEMPT']):event('fenced');raise SystemExit(75)
  event('enter');pause('EVOLUTION_PAUSE_IN_GATE')
  script=os.environ['EVOLUTION_ORIGINAL_CLI'];sys.argv=[script,*sys.argv[1:]];sys.path.insert(0,str(Path(script).parent))
  stdout=io.StringIO();stderr=io.StringIO();code=0
  try:
   with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
    try:runpy.run_path(script,run_name='__main__')
    except SystemExit as exc:code=0 if exc.code is None else exc.code if isinstance(exc.code,int) else 1
   text=stdout.getvalue();errors=stderr.getvalue()
   # Both hooks precede coordinator-visible return; os._exit models native gate failure.
   if os.environ.get('WITNESS_GATE_FAULT')=='before_evidence':os._exit(87)
   if code==0:
    try:
     roots=json.loads(os.environ['WITNESS_ROOTS']);policy=os.environ['WITNESS_SEAL_POLICY'];seal=snapshot(roots,policy)
     evidence={'schema':1,'plan':plan,'generation':generation,'target':target,'tool':os.environ['WITNESS_TOOL'],
      'source_sha256':os.environ['WITNESS_SOURCE_SHA'],'roots':roots,'snapshot':seal,'seal_policy':policy,
      'command':json.loads(os.environ['WITNESS_COMMAND']),'argv':list(sys.argv),'stdout':text,'stderr':errors,'exit_code':code}
     if len(text)+len(errors)>2*1024*1024:raise ValueError('response budget')
     with sqlite3.connect(os.environ['EVOLUTION_DB'],timeout=20) as db:
      db.execute('PRAGMA synchronous=NORMAL')
      db.execute('CREATE TABLE IF NOT EXISTS native_completion_evidence(plan TEXT PRIMARY KEY,evidence TEXT NOT NULL)')
      payload=json.dumps(evidence)
      record=json.dumps({'payload':payload,'sha256':hashlib.sha256(payload.encode()).hexdigest()})
      db.execute('INSERT INTO native_completion_evidence VALUES(?,?) ON CONFLICT(plan) DO UPDATE SET evidence=excluded.evidence',(plan,record))
     event('evidence_saved',nodes=len(seal))
    except (OSError,ValueError,sqlite3.Error) as exc:event('evidence_unavailable',reason=str(exc))
   if os.environ.get('WITNESS_GATE_FAULT')=='after_evidence':os._exit(87)
   pause('WITNESS_PAUSE_AFTER_EVIDENCE')
   sys.stdout.write(text);sys.stderr.write(errors)
   raise SystemExit(code)
  finally:event('leave')
if __name__=='__main__':main()
