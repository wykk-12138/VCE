"""Rebuild source-anchored predicate/read-set inventory for the pinned adapters."""
import ast,csv,hashlib,json,re
from pathlib import Path
from .prepare import ROOT,OUT
UP=ROOT/'native/adapters'
NAMES={'claude':'claude-instruct.py','codex':'codex-instruct.py','grok':'grok-receiptcoordinator.py'}
# Entries are a manually reviewed backward slice from normalized acceptance.
# The generator checks the anchors and hashes; it is not a static verifier.
ROWS=[
 ('C1','claude',['resolve_scope','collect_status'],'installed: managed import present AND instruction is a regular file','CLAUDE.md bytes/type; managed rules bytes/type; fixed scope/name','0/CLAUDE.md; 0/.claude/receiptcoordinator/**','body_missing,body_directory,body_bytes,body_identity,body_timestamp,body_readonly,reference_missing,reference_directory,reference_empty,reference_utf8','runtime=False; project scope excludes user runtime readiness; identity/metadata add conservative invalidation'),
 ('C2','claude',['find_journals','load_journal','inspect_recovery_state'],'journal exists with dictionary content OR malformed/unreadable journal -> recovery/conflict','all .journal-*.json names, types and bytes in receiptcoordinator directory, including empty membership','0/.claude/receiptcoordinator/**','journal_object,journal_array,journal_malformed,journal_directory','A committed-looking journal still requires recovery while present'),
 ('C3','claude',['_atomic_temp_directories','find_atomic_temp_residue'],'new project-root reserved-name entry OR failed enumeration -> recovery/conflict','project root identity; selected names start dot, contain .receiptcoordinator-tmp-, end .tmp; empty set is observed','0; filtered root membership','root_residue_file,root_residue_directory,near_residue_no_dot,near_residue_suffix,near_residue_marker_case','ordinary names and descendants are not queried by this predicate'),
 ('C4','claude',['find_atomic_temp_residue','inspect_recovery_state'],'reserved-name entry in managed directory OR failed enumeration -> recovery/conflict','complete managed directory including type, presence, contents and membership','0/.claude/receiptcoordinator/**','managed_residue','scan errors yield evidence miss; no reuse of a partially observed snapshot'),
 ('C5','claude',['scope_lock_path','inspect_recovery_state'],'lock_present/lock_live are diagnostics, not recovery_required or installed','lock file is conservatively included; live PID is not an input of normalized acceptance','0/.claude/receiptcoordinator/.receiptcoordinator.lock','lock_dead,lock_live','OS PID liveness excluded from N because it feeds neither accepted state nor blockers'),
 ('C6','claude',['collect_status'],'non-runtime project query does not inspect settings, source code or root backups','exclude ordinary files, nested source trees, .claude/settings.json and CLAUDE.md.bak_*','selector whitelist plus residue-name predicate','ordinary_file,ordinary_nested,project_settings,project_backup,outside_edit','exclusion applies to this pinned project invocation, not Claude user/runtime mode'),
 ('X1','codex',['show_status','inspect_directory'],'config missing, abnormal, undecodable or conflicting TOML -> rejection/inactive','config bytes/type/fingerprint/reference under selected .codex','0/**','reference_missing,reference_directory,reference_utf8,reference_empty,reference_wrong','fixed explicit --codex-dir and English output; no directory autodiscovery'),
 ('X2','codex',['_load_manifest','_validate_manifest','inspect_uninstall_directory'],'manifest missing, invalid, abnormal or ownership mismatch -> non-active','manifest schema; safe basename references; managed file identities/fingerprints','0/**','manifest_missing,manifest_invalid,manifest_directory,body_missing,body_directory,body_bytes,body_identity,body_timestamp,body_readonly','manifest names are validated before joining to the tool root'),
 ('X3','codex',['_hooks_transaction_residue','_deployment_journal_dirs'],'any matching transaction/cleanup entry -> recovery','all root entries, including previously absent residue names','0/**','residue_directory,residue_file','full tree conservatively covers all residue name patterns'),
 ('X4','codex',['show_status','inspect_directory','inspect_uninstall_directory'],'abnormal hook nodes, owned backup/fingerprint conflict -> rejection','active/disabled hook types and relevant owned backup bytes/metadata','0/**','owned_hook_changed,owned_hook_missing,owned_hook_directory,backup_changed,backup_missing','status skips parsing live hook content where declared; full tree remains conservative'),
 ('X5','codex',['inspect_directory','show_status'],'legacy file fingerprint/type can produce warnings or status errors','legacy name, node type and file fingerprint','0/**','legacy_regular,legacy_directory','warnings are distinguished from actual normalized blockers'),
 ('X6','codex',['show_status'],'outside files not reached through validated manifest references','only the selected tool home plus code identities is sealed','0/**; roots 1-4','outside_edit','independent approved content/reference readback remains mandatory'),
 ('G1','grok',['compute_status','_rule_node'],'root/rules/config abnormal, or missing/inactive compatibility state','root identity; rule/config types and bytes; compatibility markers/values','0/**','body_missing,body_directory,body_bytes,reference_missing,reference_directory,reference_utf8,reference_empty,reference_wrong','trusted paths constrain owned references to selected tool home'),
 ('G2','grok',['journal_dirs','interrupted_journals','compute_status'],'any transaction-prefix entry -> recovery, even if not a directory','complete root membership and node type; empty prefix set','0/**','residue_directory,residue_file','entry presence is observed before interpreting journal contents'),
 ('G3','grok',['load_manifest','normalize_manifest','assess_owned_state'],'manifest missing/invalid/type/path conflict -> non-active','manifest bytes and schema; canonical owned paths','0/**','manifest_missing,manifest_invalid,manifest_directory','no trusted reference escapes the home validation domain'),
 ('G4','grok',['assess_owned_state','normalized_file_mode','fingerprints_match'],'rule/config differs from managed after-state -> drift','owned file content, identity and Windows normalized read-only metadata','0/**','body_identity,body_timestamp,body_readonly,body_bytes,reference_wrong','Windows normalized modes are determined by read-only state; Unix permission-bit equivalence is not claimed'),
 ('G5','grok',['assess_owned_state','compute_status'],'owned active+disabled, abnormal/missing/drifted hook -> conflict/drift','hook membership, original/disabled type and content','0/**','owned_hook_changed,owned_hook_missing,owned_hook_directory,owned_hook_both,owned_hook_restored,hooks_directory_type','restored and disabled states are compared through the original status'),
 ('G6','grok',['assess_owned_state'],'backup missing, abnormal or inconsistent with before-state -> drift','rule/config/previous-manifest backups and fingerprints','0/**','backup_changed,backup_missing','the full-tree policy includes all validated backup references'),
 ('G7','grok',['competing_context_for','compute_status'],'extra rules/AGENTS/host version are diagnostic output','extra rules and AGENTS are conservatively captured; fixed host lookup environment','0/**; fixed environment','extra_rule,agents_md,outside_edit','the measured PATH has no grok launcher; no arbitrary external program is inside this guarantee'),
]
def main():
 OUT.mkdir(exist_ok=True);index={};sources={}
 for tool,name in NAMES.items():
  p=UP/tool/name;src=p.read_text(encoding='utf8');sources[tool]={'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  index[tool]={n.name:(n.lineno,n.end_lineno) for n in ast.walk(ast.parse(src)) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
 output=[]
 for rid,tool,funcs,branch,reads,fields,tests,reason in ROWS:
  anchors=[]
  for fun in funcs:
   assert fun in index[tool],(tool,fun);lo,hi=index[tool][fun];anchors.append(f'{fun}:{lo}-{hi}')
  output.append(dict(id=rid,adapter=tool,source=sources[tool]['path'],source_sha256=sources[tool]['sha256'],anchors='; '.join(anchors),predicate_branch=branch,reads_and_absence=reads,snapshot_fields=fields,mutations=tests,scope_or_exclusion=reason))
 with (OUT/'branch_matrix.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=output[0].keys());w.writeheader();w.writerows(output)
 maps={}
 for rel in ['native/native_gate.py','native/base_native_gate.py','native/src/adapter/normalize.rs','native/src/witness.rs','native/src/receipt.rs','native/src/journal.rs']:
  p=ROOT/rel;maps[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 (OUT/'source_audit.json').write_text(json.dumps({'kind':'manual predicate slice, generated anchor/hash verification','native_sources':sources,'implementation_sources':maps,'rows':output,'not_claimed':'exhaustive dynamic branch coverage or machine-checked source refinement'},indent=2)+'\n')
 run=ROOT/'paper/evidence/audit-branches-v17/raw.jsonl'
 if run.exists():
  results=[json.loads(s) for s in run.read_text().splitlines()];links=[]
  for row in results:
   matches=[r['id'] for r in output if r['adapter']==row['tool'] and row['scenario'] in r['mutations'].split(',')]
   if row['scenario']=='intact':matches=['positive unchanged-state control']
   assert matches,(row['tool'],row['scenario'])
   links.append({'method':row['method'],'tool':row['tool'],'scenario':row['scenario'],'audit_rows':matches,'pass':row['pass'],'evidence_hit':row.get('evidence_hit'),'native_accepted':row.get('native_before_retry')})
  (OUT/'mutation_to_branch.json').write_text(json.dumps(links,indent=2)+'\n')
 print(json.dumps({'predicate_rows':len(output),'native_sources':len(sources),'implementation_sources':len(maps)}))
if __name__=='__main__':main()
