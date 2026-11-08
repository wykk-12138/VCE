"""Replay approval, supersession, intent, and endpoint-crash histories."""
import argparse,hashlib,json,sqlite3,tempfile,time,traceback
from contextlib import closing
from pathlib import Path
from .client import *
from .diagnose import ownership

SCENARIOS=['normal','completed_retry','before_native','after_claim','after_native','after_execute_record','after_activation_record','after_plan_commit',
 'completed_same','completed_different','pending_same','pending_different','approval_body_edit','approval_reference_edit',
 'approval_peer_claim','claimed_body_edit','source_changed','pending_body_edit','pending_reference_edit']

def reference(root,tool):return root/('project/CLAUDE.md' if tool=='claude' else 'home/.codex/config.toml' if tool=='codex' else 'home/.grok/config.toml')

def mutate(root,tool,kind):
 path=installed(root,tool) if kind=='body' else reference(root,tool)
 path.parent.mkdir(parents=True,exist_ok=True)
 # Valid, observable replacement; reference changes carry an actual configuration change.
 value=b'# External instruction owns this target\n' if kind=='body' or tool=='claude' else b'model = "external-user-model"\n'
 path.write_bytes(value);return path,value

def completed(root,tool,p,result,desired):
 with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
  rows=db.execute("SELECT id FROM operations WHERE parent_id=? AND kind='activate' AND status='succeeded'",(p['plan']['operationId'],)).fetchall()
  own=ownership(root)
  coherent=len(rows)==1 and own['activation']==rows and own['tool_state']==rows
 return api_success(result) and installed(root,tool).read_bytes().replace(b'\r\n',b'\n')==desired.replace(b'\r\n',b'\n') and coherent

def run_case(root,item,tool,method,scenario,binary=BINARY):
 setup(root,item,tool);opts={'binary':binary};p=plan(root,tool,method,**opts);first=None;second=None
 desired=(root/'candidate.md').read_bytes();expected=True;preserved=True;external=None
 if scenario in {'normal','completed_retry','before_native','after_claim','after_native','after_execute_record','after_activation_record','after_plan_commit'}:
  if scenario=='completed_retry':
   first=confirm(root,tool,method,p,**opts);assert completed(root,tool,p,first,desired),first
  elif scenario not in {'normal'}:
   first=confirm(root,tool,method,p,fault=scenario,**opts);assert first['exit_code']==86,first
 elif scenario.startswith(('completed_','pending_')) and scenario.endswith(('_same','_different')):
  first=confirm(root,tool,method,p,**({'fault':'after_native'} if scenario.startswith('pending_') else {}),**opts)
  assert first['exit_code']==86 if scenario.startswith('pending_') else completed(root,tool,p,first,desired),first
  if scenario.endswith('_different'):(root/'candidate.md').write_bytes(b'# Q: independent later deployment\n')
  q=plan(root,tool,method,**opts);second=confirm(root,tool,method,q,**opts)
  assert completed(root,tool,q,second,(root/'candidate.md').read_bytes()),second
  expected=False
 elif scenario=='approval_peer_claim':
  q=plan(root,tool,method,**opts);second=confirm(root,tool,method,q,**opts)
  assert completed(root,tool,q,second,desired),second
  expected=False
 elif scenario=='source_changed':
  first=call(root,tool,'change_source',prompt_id=p['prompt_id'],method=method,**opts);expected=False
 elif scenario in {'approval_body_edit','approval_reference_edit','claimed_body_edit','pending_body_edit','pending_reference_edit'}:
  if scenario.startswith(('claimed_','pending_')):
   first=confirm(root,tool,method,p,fault='after_claim' if scenario.startswith('claimed_') else 'after_native',**opts)
   assert first['exit_code']==86,first
  external=mutate(root,tool,'reference' if 'reference' in scenario else 'body');expected=False
 else:raise ValueError(scenario)
 before=ownership(root);disk=installed(root,tool);before_bytes=disk.read_bytes() if disk.exists() else None;n=len(trace(root))
 result=confirm(root,tool,method,p,retry=first is not None,**opts)
 after=ownership(root)
 if external:preserved=external[0].read_bytes()==external[1]
 refused_correctly=not api_success(result) and before==after and preserved and (disk.read_bytes() if disk.exists() else None)==before_bytes
 success=completed(root,tool,p,result,desired) if api_success(result) else False
 return {'pass':success if expected else refused_correctly,'expected_completion':expected,'api_success':api_success(result),
  'external_preserved':preserved,'ownership_preserved':before==after,'first':first,'second':second,'result':result,
  'actual_hard_exits':int(first is not None and first.get('exit_code')==86),
  'activation_calls':sum(x['command']=='activate' for x in trace(root)),
  'last_activation_calls':sum(x['command']=='activate' for x in trace(root)[n:]),'before':before,'after':after}

def main(a):
 out=a.out
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True);SCRATCH.mkdir(parents=True,exist_ok=True)
 items=corpus(a.split)[:a.inputs];methods=a.methods or METHODS;scenarios=a.scenarios or SCENARIOS
 binary=RELEASE if a.release else BINARY
 spec={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'profile':'optimized research' if a.release else 'debug research',
  'methods':methods,'scenarios':scenarios,'inputs':items,'phase':a.split+' regression; public input pool previously used'}
 (out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf8');rows=[];began=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='safety-',dir=SCRATCH) as tmp,(out/'raw.jsonl').open('w',encoding='utf8') as f:
  for item in items:
   for method in methods:
    for tool in ['claude','codex','grok']:
     for scenario in scenarios:
      try:r=run_case(Path(tmp)/str(len(rows)),item,tool,method,scenario,binary)
      except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
      row={'method':method,'tool':tool,'scenario':scenario,'repository':item['repository'],'payload':item['payload']['path'],**r}
      rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
      if not row['pass']:print(json.dumps(row),flush=True)
     print(json.dumps({'completed':len(rows),'method':method,'tool':tool,'failures':sum(not r['pass'] for r in rows)}),flush=True)
 report={'cases':len(rows),'passed':sum(r['pass'] for r in rows),'exceptions':sum('exception' in r for r in rows),
  'hard_exits':sum(r.get('actual_hard_exits',0) for r in rows),'seconds':time.perf_counter()-began}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--inputs',type=int,default=1);p.add_argument('--split',default='development');p.add_argument('--release',action='store_true');p.add_argument('--methods',nargs='+');p.add_argument('--scenarios',nargs='+');main(p.parse_args())
