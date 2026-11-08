import argparse,hashlib,json,sqlite3,traceback
from contextlib import closing
from paper.finalstudy import cases
from paper.evolutionstudy import safety,orphans
from paper.witnessstudy import validation as previous,dependency_validation as metadata,same_plan_orphan as duplicate
from .client import *

CUSTOM=['unrelated_inside','bulk_unrelated','root_residue_file','root_residue_directory','receiptcoordinator_residue','remove_memory','change_settings','project_backup']
def custom(root,item,method,scenario):
 fixture=setup(root,item,'claude');p=plan(root,'claude',method);first=confirm(root,'claude',method,p,fault='after_native');assert first['exit_code']==86,first
 expected=scenario in {'unrelated_inside','bulk_unrelated','change_settings','project_backup'};external={}
 if scenario=='unrelated_inside':(root/'project/note.txt').write_text('ordinary note')
 elif scenario=='bulk_unrelated':
  folder=root/'project/source';folder.mkdir()
  for i in range(4097):(folder/str(i)).write_bytes(b'ordinary unrelated source')
 elif scenario.startswith('root_residue'):
  path=root/'project/.CLAUDE.md.receiptcoordinator-tmp-pending.tmp'
  if scenario.endswith('directory'):path.mkdir()
  else:path.write_bytes(b'unfinished native write')
 elif scenario=='receiptcoordinator_residue':(root/'project/.claude/receiptcoordinator/.target.receiptcoordinator-tmp-pending.tmp').write_bytes(b'unfinished native write')
 elif scenario=='remove_memory':(root/'project/CLAUDE.md').unlink();fixture['memory_before']=b'';fixture['copied'].pop('CLAUDE.md',None)
 elif scenario=='change_settings':
  path=root/'project/.claude/settings.json';value=b'{"unrelated":true}\n';path.write_bytes(value);fixture['copied']['.claude/settings.json']=value
 elif scenario=='project_backup':
  targets=sorted((root/'project').glob('CLAUDE.md.bak_*'));assert targets;targets[0].write_bytes(b'changed archive')
 n=len(trace(root));nw=len(witnesses(root));result=confirm(root,'claude',method,p,retry=True);commands=[x['command'] for x in trace(root)[n:]];hits=witnesses(root)[nw:]
 if scenario=='remove_memory':
  # Native status and DB refusal checked directly because the old oracle requires a memory file to exist.
  native=cases.call(root,'claude','status');checked={'false_success':api_success(result),'unique_api_completion':False,'external_preserved':not (root/'project/CLAUDE.md').exists(),'native_status':native}
 else:checked=cases.oracle(root,'claude',fixture,p['prompt_id'],p['plan']['operationId'],method,result,external=external)
 passed=(checked['unique_api_completion'] if expected else not api_success(result)) and checked['external_preserved']
 if method!='A_NoResidueWatch':passed=passed and (commands==[] if expected else not any(h['hit'] for h in hits))
 return {'pass':passed,'expected_completion':expected,'api_success':api_success(result),'commands':commands,'hits':hits,'oracle':checked,'result':result}

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 a.out.mkdir(parents=True);configure();rows=[];item=corpus('development')[0];began=time.perf_counter();os.environ['TMP']=os.environ['TEMP']=str(SCRATCH)
 (a.out/'spec.json').write_text(json.dumps({'methods':NEW_METHODS,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'scope':'Claude project dependency refinement; other tools retain full snapshots','custom':CUSTOM},indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='v-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('w') as f:
  tasks=[]
  for method in NEW_METHODS:
   for tool in ['claude','codex','grok']:
    tasks.extend(('safety',method,tool,sc) for sc in safety.SCENARIOS)
    tasks.extend(('evidence',method,tool,sc) for sc in previous.SCENARIOS if not(tool=='claude' and sc in {'unrelated_inside','seal_node_budget'}))
    tasks.extend(('orphans',method,tool,sc) for sc in ['delayed_old_entry','live_old_writer'])
    tasks.append(('same_plan',method,tool,'delayed_same'))
    if tool!='claude':tasks.extend(('metadata',method,tool,sc) for sc in ['backup','owned_hook'])
   tasks.extend(('custom',method,'claude',sc) for sc in CUSTOM)
  tasks.extend(('custom','A_NoResidueWatch','claude',sc) for sc in ['root_residue_file','root_residue_directory'])
  for suite,method,tool,sc in tasks:
   root=Path(tmp)/str(len(rows))
   try:
    if suite=='safety':r=safety.run_case(root,item,tool,method,sc,BINARY)
    elif suite=='evidence':r=previous.run_case(root,item,method,tool,sc)
    elif suite=='orphans':r=orphans.run_case(root,item,tool,method,sc,binary=BINARY)
    elif suite=='same_plan':r=duplicate.run_case(root,item,method,tool)
    elif suite=='metadata':r=metadata.one(root,item,method,tool,sc)
    else:r=custom(root,item,method,sc)
   except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
   row={'suite':suite,'method':method,'tool':tool,'scenario':sc,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
   if not r['pass']:print(json.dumps({k:v for k,v in row.items() if k not in ['first','second','oracle','result']}),flush=True)
   if len(rows)%20==0:print(json.dumps({'cases':len(rows),'full_failures':sum(not r['pass'] and r['method']!='A_NoResidueWatch' for r in rows)}),flush=True)
 report={'full_cases':sum(r['method']!='A_NoResidueWatch' for r in rows),'full_passed':sum(r['pass'] and r['method']!='A_NoResidueWatch' for r in rows),
  'ablation_cases':2,'ablation_false_success':sum(r['method']=='A_NoResidueWatch' and r.get('oracle',{}).get('false_success',False) for r in rows),
  'exceptions':sum('exception' in r for r in rows),'seconds':time.perf_counter()-began}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args())
