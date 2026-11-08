"""Predicate-directed mutations against independent original native status."""
import argparse,hashlib,importlib.util,json,os,sqlite3,stat,sys,tempfile,tomllib,traceback
from contextlib import closing
from pathlib import Path
from paper.closurestudy.client import *
from paper.finalstudy import cases
from paper.witnessstudy.validation import evidence,native_root

TMPROOT=ROOT/'.research-tmp/audit-v17';TMPROOT.mkdir(exist_ok=True)
COMMON=['intact','body_missing','body_directory','body_bytes','body_identity','body_timestamp','body_readonly','reference_missing','reference_directory','reference_utf8','reference_empty','outside_edit']
SPECIAL={
 'claude':['journal_object','journal_array','journal_malformed','journal_directory','root_residue_file','root_residue_directory','managed_residue','ordinary_file','ordinary_nested','project_settings','project_backup','near_residue_no_dot','near_residue_suffix','near_residue_marker_case','lock_dead','lock_live'],
 'codex':['manifest_missing','manifest_invalid','manifest_directory','residue_directory','residue_file','legacy_directory','legacy_regular','backup_changed','backup_missing','owned_hook_changed','owned_hook_missing','owned_hook_directory','reference_wrong'],
 'grok':['manifest_missing','manifest_invalid','manifest_directory','residue_directory','residue_file','backup_changed','backup_missing','owned_hook_changed','owned_hook_missing','owned_hook_directory','owned_hook_both','owned_hook_restored','extra_rule','agents_md','hooks_directory_type','reference_wrong']}
EXCLUDED={'claude':{'outside_edit','ordinary_file','ordinary_nested','project_settings','project_backup','near_residue_no_dot','near_residue_suffix','near_residue_marker_case'},'codex':{'outside_edit'},'grok':{'outside_edit'}}
def native_status(root,tool):
 r=cases.call(root,tool,'status');e=r.get('response',{}).get('data',{}).get('envelope',{})
 return {'accepted':e.get('ok') is True and e.get('status')=='active' and not e.get('recoveryRequired') and not e.get('blockers'),'envelope':e}
def make_writable(p):
 if p.is_file():p.chmod(p.stat().st_mode|stat.S_IWUSR)
def mutate(root,tool,scenario):
 base=native_root(root,tool);body=installed(root,tool);reference=root/('project/CLAUDE.md' if tool=='claude' else f'home/.{tool}/config.toml')
 touched=[]
 def change(p,kind='bytes',value=b'EXTERNAL MUTATION\n'):
  assert p.resolve().is_relative_to(root.resolve());make_writable(p);touched.append(p.relative_to(root).as_posix())
  if kind=='remove':p.unlink()
  elif kind=='directory':
   if p.exists():p.rename(p.with_name(p.name+'.saved-v17'))
   p.mkdir()
  elif kind=='identity':
   s=p.stat();q=p.with_name(p.name+'.replacement');q.write_bytes(p.read_bytes());os.utime(q,ns=(s.st_atime_ns,s.st_mtime_ns));os.replace(q,p)
  elif kind=='timestamp':
   s=p.stat();os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1_000_000_000))
  elif kind=='readonly':p.chmod(stat.S_IREAD)
  else:p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(value)
 if scenario=='intact':pass
 elif scenario.startswith('body_'):change(body,{'missing':'remove','directory':'directory','identity':'identity','timestamp':'timestamp','readonly':'readonly'}.get(scenario[5:],'bytes'))
 elif scenario.startswith('reference_'):
  key=scenario[10:];change(reference,{'missing':'remove','directory':'directory'}.get(key,'bytes'),b'\xff\xfe' if key=='utf8' else b'' if key=='empty' else b'model_instructions_file = "wrong.md"\n' if tool=='codex' else b'model="external"\n')
 elif scenario=='outside_edit':change(root/'outside.txt')
 elif scenario.startswith('journal_'):
  change(base/'.claude/receiptcoordinator/.journal-audit.json','directory' if scenario=='journal_directory' else 'bytes',{'journal_object':b'{"state":"committed"}','journal_array':b'[]'}.get(scenario,b'{invalid'))
 elif scenario.startswith('root_residue'):change(base/'.CLAUDE.md.receiptcoordinator-tmp-audit.tmp','directory' if scenario.endswith('directory') else 'bytes')
 elif scenario=='managed_residue':change(base/'.claude/receiptcoordinator/.rules.receiptcoordinator-tmp-audit.tmp')
 elif scenario=='ordinary_file':change(base/'audit-note.txt')
 elif scenario=='ordinary_nested':change(base/'source/audit/deep-note.txt')
 elif scenario=='project_settings':change(base/'.claude/settings.json',value=b'{"new":"setting"}\n')
 elif scenario=='project_backup':
  paths=sorted(base.glob('CLAUDE.md.bak_*'));assert paths;change(paths[0])
 elif scenario.startswith('near_residue'):
  name={'near_residue_no_dot':'x.receiptcoordinator-tmp-audit.tmp','near_residue_suffix':'.x.receiptcoordinator-tmp-audit.tmpx','near_residue_marker_case':'.x.RECEIPTCOORDINATOR-TMP-audit.tmp'}[scenario];change(base/name)
 elif scenario.startswith('lock_'):
  # Path verified against scope_lock_path in the pinned native source.
  change(base/'.claude/receiptcoordinator/.receiptcoordinator.lock',value=json.dumps({'pid':os.getpid() if scenario=='lock_live' else 2147483647}).encode())
 elif scenario.startswith('manifest_'):
  change(base/f'.{tool}-receiptcoordinator-manifest.json',{'manifest_missing':'remove','manifest_directory':'directory'}.get(scenario,'bytes'),b'{}')
 elif scenario.startswith('residue_'):change(base/f'.{tool}-receiptcoordinator-transaction-audit','directory' if scenario.endswith('directory') else 'bytes')
 elif scenario.startswith('legacy_'):change(base/'gpt5.5-unrestricted.md','directory' if scenario.endswith('directory') else 'bytes')
 elif scenario.startswith('backup_'):
  paths=sorted(p for p in base.rglob('*') if p.is_file() and ('backup' in p.name or 'bak_' in p.name));assert paths;change(paths[0],'remove' if scenario.endswith('missing') else 'bytes')
 elif scenario.startswith('owned_hook_'):
  original=base/'hooks.json' if tool=='codex' else base/'hooks/fixture.json'
  paths=sorted(p for p in base.rglob('*') if p.is_file() and ('disabled' in p.name) and ('hooks' in p.name or p.parent.name=='hooks'));assert paths,(tool,scenario)
  target=paths[0]
  if scenario.endswith('both'):change(original,value=target.read_bytes())
  elif scenario.endswith('restored'):touched.extend([target.relative_to(root).as_posix(),original.relative_to(root).as_posix()]);target.rename(original)
  else:change(target,'remove' if scenario.endswith('missing') else 'directory' if scenario.endswith('directory') else 'bytes')
 elif scenario=='extra_rule':change(base/'rules/extra.md',value=b'# Extra context\n')
 elif scenario=='agents_md':change(base/'AGENTS.md',value=b'# Extra agent context\n')
 elif scenario=='hooks_directory_type':
  p=base/'hooks'
  if p.exists():p.rename(base/'hooks.saved-v17')
  change(p)
 else:raise ValueError(scenario)
 return touched
def one(root,item,tool,method,scenario):
 fixture=setup(root,item,tool)
 if scenario.startswith('owned_hook_'):
  p=root/('home/.codex/hooks.json' if tool=='codex' else 'home/.grok/hooks/fixture.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{"hooks": []}\n')
 p=plan(root,tool,method);first=confirm(root,tool,method,p,fault='after_native');assert first['exit_code']==86
 record=evidence(root,p);assert record;value=json.loads(record['payload']);before=native_status(root,tool);assert before['accepted']
 touched=mutate(root,tool,scenario);observed=native_status(root,tool)
 n=len(trace(root));nw=len(witnesses(root));r=confirm(root,tool,method,p,retry=True);calls=[c['command'] for c in trace(root)[n:]];hits=witnesses(root)[nw:];hit=any(h['hit'] for h in hits)
 after=native_status(root,tool);success=api_success(r);postcondition=True
 if success:
  body=installed(root,tool);content=body.is_file() and cases.normalized(body.read_bytes())==cases.normalized(fixture['desired'])
  if tool=='claude':reference='@.claude/receiptcoordinator/claude-project-rules.md' in (root/'project/CLAUDE.md').read_text().splitlines()
  elif tool=='codex':
   reference_value=tomllib.loads((root/'home/.codex/config.toml').read_text()).get('model_instructions_file','');reference=(root/'home/.codex'/reference_value).resolve()==body.resolve()
  else:reference=(root/'home/.grok/.grok-receiptcoordinator-manifest.json').is_file()
  with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
   db.row_factory=sqlite3.Row;ops=[dict(x) for x in db.execute("SELECT id FROM operations WHERE kind='activate' AND prompt_id=? AND status='succeeded'",(p['prompt_id'],))]
   act=[dict(x) for x in db.execute("SELECT operation_id,fingerprint FROM activations WHERE prompt_id=? AND status='active'",(p['prompt_id'],))]
   states=[dict(x) for x in db.execute("SELECT last_operation_id,fingerprint FROM tool_state WHERE status='active'")]
  digest=hashlib.sha256(fixture['desired']).hexdigest();coherent=len(ops)==1 and any(x['operation_id']==ops[0]['id'] and x['fingerprint']==digest for x in act) and any(x['last_operation_id']==ops[0]['id'] and x['fingerprint']==digest for x in states)
  postcondition=content and reference and coherent
 excluded=scenario in EXCLUDED[tool];required=not excluded and scenario!='intact'
 # A conservative miss can still query and complete. Predicate rejection must
 # never be converted into evidence acceptance or successful publication.
 checks={'hit_implies_native':not hit or observed['accepted'],'success_implies_native':not success or after['accepted'],
  'native_rejection_preserved':observed['accepted'] or not success,'excluded_reuses':not excluded or hit and observed['accepted'],
  'selected_mutation_invalidates':not required or not hit,'intact_reuses':scenario!='intact' or hit and success,'successful_postcondition_coherent':postcondition}
 return {'pass':all(checks.values()),'checks':checks,'mutated':touched,'excluded':excluded,'evidence_hit':hit,'native_before_retry':observed['accepted'],'native_after_retry':after['accepted'],'api_success':success,'commands':calls,'witness_events':hits,'saved_snapshot_keys':list(value['snapshot']),'native_before':before,'native_observed':observed,'native_after':after,'result':r}
def main(a):
 configure();a.out.mkdir(parents=True,exist_ok=False);items={}
 for item in corpus('confirmation'):items.setdefault(item['repository'],item)
 item=next(iter(items.values()));rows=[]
 spec={'methods':['ReceiptCoordinatorV15','JournalWitnessV15'],'common':COMMON,'adapter_cases':SPECIAL,'input':item,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'oracle':'Frozen original adapter status, independent of retained evidence; same normalized acceptance and empty blockers.','claim':'Finite mutation checks corroborate the separately supplied predicate/read-set source audit; not exhaustive Python branch coverage.'}
 (a.out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='d-',dir=TMPROOT) as temp,(a.out/'raw.jsonl').open('w') as f:
  for method in spec['methods']:
   for tool in ['claude','codex','grok']:
    for sc in COMMON+SPECIAL[tool]:
     try:r=one(Path(temp)/str(len(rows)),item,tool,method,sc)
     except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
     row={'method':method,'tool':tool,'scenario':sc,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
     if not r['pass']:print(json.dumps(row),flush=True);raise RuntimeError('differential check failed')
     if len(rows)%12==0:print(json.dumps({'cases':len(rows),'passed':sum(r['pass'] for r in rows)}),flush=True)
 report={'cases':len(rows),'passed':sum(r['pass'] for r in rows),'hits':sum(r['evidence_hit'] for r in rows),'native_rejections':sum(not r['native_before_retry'] for r in rows),'false_evidence_acceptance':sum(r['evidence_hit'] and not r['native_before_retry'] for r in rows),'false_completion':sum(r['api_success'] and not r['native_after_retry'] for r in rows),'excluded_hits':sum(r['excluded'] and r['evidence_hit'] for r in rows)}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args())
