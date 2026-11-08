"""Isolated real-process client. No baseline-specific outcomes or delays."""
import json,os,subprocess,time
from pathlib import Path
from paper.finalstudy.cases import ROOT,SOURCE,api_success,corpus,setup,installed,trace

BINARY=ROOT/'native/target/release/receiptcoordinator.exe'
RELEASE=ROOT/'native/target/release/receiptcoordinator.exe'
METHODS=['ReceiptCoordinatorV13','JournalGuarded','JournalGuardedScoped']
SCRATCH=ROOT/'.research-tmp/evolution-v13'
assert SCRATCH.resolve().is_relative_to(ROOT.resolve()), 'fixture cleanup must remain inside the workspace'

def environment(root,extra=None,fault=None):
 root=Path(root)
 env={**os.environ,'RECEIPTCOORDINATOR_RESEARCH_TRACE':str(root/'adapter_calls.jsonl'),
  'RECEIPTCOORDINATOR_RESEARCH_PROFILE':str(root/'adapter_profile.jsonl'),
  'RECEIPTCOORDINATOR_RESEARCH_FAULT':fault or '', 'PYTHONIOENCODING':'utf-8',
  'CUDA_VISIBLE_DEVICES':'','HIP_VISIBLE_DEVICES':'','TMP':str(SCRATCH),'TEMP':str(SCRATCH),
  'HOME':str(root/'home'),'USERPROFILE':str(root/'home'),
  'APPDATA':str(root/'home/AppData/Roaming'),'LOCALAPPDATA':str(root/'home/AppData/Local')}
 env['PATH']=os.pathsep.join(p for p in env['PATH'].split(os.pathsep) if 'windowsapps' not in p.lower())
 for k in ['GROK_RECEIPTCOORDINATOR_FAULT_INJECT','CLAUDE_RECEIPTCOORDINATOR_FAULT_INJECT','CODEX_RECEIPTCOORDINATOR_FAULT_INJECT','RECEIPTCOORDINATOR_RESEARCH_CORRUPT']:
  env.pop(k,None)
 env.update(extra or {})
 return env

def request(root,tool,command,**kwargs):
 return {'command':command,'root':str(root),'source_root':str(SOURCE),'tool':tool,**kwargs}

def start(root,tool,command,binary=BINARY,fault=None,extra=None,**kwargs):
 child=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
  cwd=ROOT,env=environment(root,extra,fault),text=True,encoding='utf-8')
 child.stdin.write(json.dumps(request(root,tool,command,**kwargs))+'\n');child.stdin.flush()
 # Close stdin so the one-request process exits; orphan tests deliberately retain pipes.
 child.stdin.close();child.stdin=None
 return child

def finish(child,started=None,fault=None):
 out,err=child.communicate(timeout=90)
 elapsed=time.perf_counter_ns()-(started or time.perf_counter_ns())
 if child.returncode==86 and fault:return {'exit_code':86,'fault':fault,'wall_ns':elapsed}
 if child.returncode!=0:raise RuntimeError(f'child {child.returncode}: {err[-3000:]}')
 try:response=json.loads(out.strip().splitlines()[-1])
 except (ValueError,IndexError):raise RuntimeError(f'invalid response: {out}: {err}')
 return {'exit_code':0,'wall_ns':elapsed,'response':response}

def call(root,tool,command,**kwargs):
 began=time.perf_counter_ns();fault=kwargs.get('fault')
 return finish(start(root,tool,command,**kwargs),began,fault)

def plan(root,tool,method,**kwargs):
 r=call(root,tool,'plan',method=method,**kwargs)
 d=r.get('response',{}).get('data',{})
 if not d.get('plan',{}).get('envelope',{}).get('ok'):raise AssertionError(('plan failed',r))
 return d

def arguments(method,p,**kwargs):
 return dict(method=method,operation_id=p['plan']['operationId'],prompt_id=p['prompt_id'],**kwargs)

def confirm(root,tool,method,p,**kwargs):return call(root,tool,'confirm',**arguments(method,p,**kwargs))
