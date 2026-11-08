"""Mutate hidden native state and stored evidence; compare with the native oracle."""
import argparse,hashlib,json,shutil,sqlite3,traceback
from contextlib import closing
from paper.finalstudy.cases import oracle
from paper.evolutionstudy.diagnose import ownership
from paper.evolutionstudy.orphans import until
from .client import *

SCENARIOS=['sealed_recovery','evidence_missing','evidence_truncated','evidence_checksum','evidence_wrong_plan','evidence_wrong_source',
 'native_residue','manifest_invalid','body_changed','reference_changed','unrelated_inside','timestamp_changed','identity_changed',
 'gate_before_evidence','gate_after_evidence','parent_after_evidence','seal_node_budget','adapter_changed']

def native_root(root,tool):return root/'project' if tool=='claude' else root/'home'/('.codex' if tool=='codex' else '.grok')
def residue(root,tool):
 path=root/('project/.claude/receiptcoordinator/.journal-v14.json' if tool=='claude' else 'home/.codex/.codex-receiptcoordinator-transaction-v14' if tool=='codex' else 'home/.grok/.grok-receiptcoordinator-transaction-v14')
 if tool=='claude':path.write_text('{"state":"pending"}')
 else:path.mkdir()
 return path

def evidence(root,p):
 with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
  exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='native_completion_evidence'").fetchone()
  if not exists:return None
  row=db.execute('SELECT evidence FROM native_completion_evidence WHERE plan=?',(p['plan']['operationId'],)).fetchone()
 return json.loads(row[0]) if row else None

def corrupt_record(root,p,kind):
 with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
  if kind=='missing':db.execute('DELETE FROM native_completion_evidence WHERE plan=?',(p['plan']['operationId'],))
  else:
   r=evidence(root,p);value=json.loads(r['payload'])
   if kind=='truncated':text='{"payload":'
   elif kind=='checksum':r['sha256']='0'*64;text=json.dumps(r)
   else:
    value['plan' if kind=='wrong_plan' else 'source_sha256']='wrong-value';payload=json.dumps(value)
    text=json.dumps({'payload':payload,'sha256':hashlib.sha256(payload.encode()).hexdigest()})
   db.execute('UPDATE native_completion_evidence SET evidence=? WHERE plan=?',(text,p['plan']['operationId']))
  db.commit()

def run_case(root,item,method,tool,scenario):
 fixture=setup(root,item,tool);opts={}
 if scenario=='adapter_changed':
  relative=Path('adapters')/tool/({'claude':'claude-instruct.py','codex':'codex-instruct.py','grok':'grok-receiptcoordinator.py'}[tool]);script=root/'source'/relative;script.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/relative,script);opts={'source_root':str(root/'source')}
 p=plan(root,tool,method,**opts);external={};expected=scenario not in {'native_residue','manifest_invalid','body_changed','reference_changed'} and not (scenario=='timestamp_changed' and tool=='codex')
 if scenario=='seal_node_budget':
  extra=native_root(root,tool)/'irrelevant-many';extra.mkdir()
  for i in range(4097):(extra/str(i)).write_bytes(b'')
 if scenario.startswith('gate_'):
  first=confirm(root,tool,method,p,extra={'WITNESS_GATE_FAULT':scenario.removeprefix('gate_')})
  assert not api_success(first),first
 elif scenario=='parent_after_evidence':
  signal=root/'release'
  child=start(root,tool,'confirm',extra={'WITNESS_PAUSE_AFTER_EVIDENCE':str(signal)},**arguments(method,p))
  try:
   until(lambda:signal.with_suffix('.ready').exists() and signal.with_suffix('.ready').read_text().strip().isdigit())
   assert evidence(root,p) is not None
   child.kill();child.wait(timeout=5);signal.touch();child.communicate(timeout=15)
   first={'killed_coordinator_pid':child.pid}
  finally:
   signal.touch()
   if child.poll() is None:child.kill()
   child.communicate(timeout=15)
 else:
  first=confirm(root,tool,method,p,fault='after_native',**opts);assert first['exit_code']==86,first
 record=evidence(root,p)
 if scenario not in {'gate_before_evidence','seal_node_budget'}:assert record is not None,(scenario,first)
 if scenario.startswith('evidence_'):corrupt_record(root,p,scenario.removeprefix('evidence_'))
 elif scenario=='native_residue':residue(root,tool)
 elif scenario=='manifest_invalid':
  path=root/('project/.claude/receiptcoordinator/.journal-invalid.json' if tool=='claude' else 'home/.codex/.codex-receiptcoordinator-manifest.json' if tool=='codex' else 'home/.grok/.grok-receiptcoordinator-manifest.json');path.write_bytes(b'{invalid');external[path.relative_to(root).as_posix()]=b'{invalid'
 elif scenario in {'body_changed','reference_changed'}:
  path=installed(root,tool) if scenario=='body_changed' else root/('project/CLAUDE.md' if tool=='claude' else 'home/.codex/config.toml' if tool=='codex' else 'home/.grok/config.toml')
  value=b'# External changed content\n' if tool=='claude' or scenario=='body_changed' else b'model = "external"\n';path.write_bytes(value);external[path.relative_to(root).as_posix()]=value
  if tool=='claude' and scenario=='reference_changed':fixture['memory_before']=value;fixture['copied'].pop('CLAUDE.md',None)
 elif scenario=='unrelated_inside':(native_root(root,tool)/'notes-unrelated.txt').write_text('unrelated settled edit')
 elif scenario=='timestamp_changed':
  path=installed(root,tool);s=path.stat();os.utime(path,ns=(s.st_atime_ns,s.st_mtime_ns+1_000_000_000))
 elif scenario=='identity_changed':
  path=installed(root,tool);s=path.stat();replacement=path.with_name('replacement.tmp');replacement.write_bytes(path.read_bytes());os.utime(replacement,ns=(s.st_atime_ns,s.st_mtime_ns));os.replace(replacement,path)
 elif scenario=='adapter_changed':
  with script.open('a',encoding='utf8') as f:f.write('\n# Changed adapter identity for evidence invalidation test\n')
 before=ownership(root);n=len(trace(root));nw=len(witnesses(root));r=confirm(root,tool,method,p,retry=True,**opts)
 commands=[v['command'] for v in trace(root)[n:]];hits=witnesses(root)[nw:]
 check=oracle(root,tool,fixture,p['prompt_id'],p['plan']['operationId'],method,r,external=external)
 fast_expected=scenario in {'sealed_recovery','gate_after_evidence','parent_after_evidence'}
 passed=(check['unique_api_completion'] if expected else not api_success(r) and ownership(root)==before) and check['external_preserved']
 if method!='A_NoEvidenceSeal':passed=passed and (commands==[] if fast_expected else 'status' in commands or scenario in {'body_changed','reference_changed'})
 return {'pass':passed,'expected_completion':expected,'api_success':api_success(r),'commands':commands,'hits':hits,'first':first,'result':r,'oracle':check,
  'evidence_bytes':len(json.dumps(record).encode()) if record else 0,'snapshot_nodes':len(json.loads(record['payload'])['snapshot']) if record else 0}

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 a.out.mkdir(parents=True);rows=[];item=corpus('development')[0];began=time.perf_counter()
 scenarios=a.scenarios or SCENARIOS
 arms=[(m,s) for m in NEW_METHODS for s in scenarios]
 if a.ablations:arms+=[('A_NoEvidenceSeal',s) for s in ['native_residue','manifest_invalid']]
 (a.out/'spec.json').write_text(json.dumps({'methods':NEW_METHODS,'scenarios':scenarios,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'input':item,'ablations':a.ablations},indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='v-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('w') as f:
  for method,sc in arms:
   for tool in ['claude','codex','grok']:
    try:r=run_case(Path(tmp)/str(len(rows)),item,method,tool,sc)
    except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
    row={'method':method,'tool':tool,'scenario':sc,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    print(json.dumps({k:v for k,v in row.items() if k not in ['first','result','oracle','traceback']}),flush=True)
 report={'full_cases':sum(r['method']!='A_NoEvidenceSeal' for r in rows),'full_passed':sum(r['pass'] and r['method']!='A_NoEvidenceSeal' for r in rows),
  'ablation_cases':sum(r['method']=='A_NoEvidenceSeal' for r in rows),'ablation_false_success':sum(r['method']=='A_NoEvidenceSeal' and r.get('oracle',{}).get('false_success',False) for r in rows),
  'exceptions':sum('exception' in r for r in rows),'seconds':time.perf_counter()-began}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--scenarios',nargs='+');p.add_argument('--ablations',action='store_true');main(p.parse_args())
