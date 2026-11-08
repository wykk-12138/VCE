"""Reproduce cross-plan and approval-window histories on the frozen executable."""
import argparse,hashlib,json,os,sqlite3,tempfile,time
from pathlib import Path
from contextlib import closing
from paper.finalstudy.cases import ROOT,BINARY,corpus,setup,call,installed,api_success,trace

def ownership(root):
 with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
  return {'activation':db.execute('SELECT operation_id FROM activations ORDER BY id').fetchall(),
   'tool_state':db.execute('SELECT last_operation_id FROM tool_state ORDER BY tool,scope,project_dir').fetchall()}
def plan(root,tool):return call(root,tool,'plan')['response']['data']
def confirm(root,tool,m,p,**kw):return call(root,tool,'confirm',method=m,operation_id=p['plan']['operationId'],prompt_id=p['prompt_id'],**kw)
def run_case(root,item,tool,method,scenario):
 setup(root,item,tool);p=plan(root,tool);new_value=None
 if scenario.startswith('approval_'):
  target=installed(root,tool) if scenario=='approval_body_edit' else root/('project/CLAUDE.md' if tool=='claude' else 'home/.codex/config.toml' if tool=='codex' else 'home/.grok/config.toml')
  target.parent.mkdir(parents=True,exist_ok=True)
  new_value=b'EXTERNAL EDIT AFTER APPROVAL\n' if scenario=='approval_body_edit' else (target.read_bytes()+b'\n# EXTERNAL EDIT AFTER APPROVAL\n')
  target.write_bytes(new_value);before=ownership(root);r=confirm(root,tool,method,p)
  return {'result':r,'api_success':api_success(r),'external_preserved':target.read_bytes()==new_value,'before':before,'after':ownership(root),'activation_calls':sum(x['command']=='activate' for x in trace(root))}
 pending=scenario.startswith('pending_');different=scenario.endswith('_different')
 first=confirm(root,tool,method,p,**({'fault':'after_native'} if pending else {}))
 if pending:assert first['exit_code']==86
 else:assert api_success(first),first
 if different:(root/'candidate.md').write_bytes(b'# Later approved independent deployment\n')
 q=plan(root,tool);second=confirm(root,tool,method,q);assert api_success(second),second
 before=ownership(root);before_bytes=installed(root,tool).read_bytes();n=len(trace(root));r=confirm(root,tool,method,p,retry=True)
 after=ownership(root)
 return {'p':p['plan']['operationId'],'q':q['plan']['operationId'],'first':first,'second':second,'result':r,
  'api_success':api_success(r),'later_ownership_preserved':before==after,'later_bytes_preserved':installed(root,tool).read_bytes()==before_bytes,
  'before':before,'after':after,'retry_activation_calls':sum(x['command']=='activate' for x in trace(root)[n:])}
def main(out):
 os.environ['TMP']=os.environ['TEMP']=str(ROOT/'.research-tmp/evolution-v13')
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True);item=corpus('development')[0];methods=['ReceiptCoordinator','NativeJournal']
 scenarios=['completed_same','completed_different','pending_same','pending_different','approval_body_edit','approval_reference_edit']
 spec={'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'methods':methods,'tools':['claude','codex','grok'],'scenarios':scenarios,'input':item,'phase':'development diagnosis; not holdout confirmation'}
 (out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf8');start=time.perf_counter();rows=[]
 scratch=ROOT/'.research-tmp/evolution-v13';scratch.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='diagnose-',dir=scratch) as tmp,(out/'raw.jsonl').open('w',encoding='utf8') as f:
  for m in methods:
   for t in spec['tools']:
    for sc in scenarios:
     try:r=run_case(Path(tmp)/str(len(rows)),item,t,m,sc)
     except Exception as e:r={'exception':str(e)}
     row={'method':m,'tool':t,'scenario':sc,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
     print(json.dumps({k:v for k,v in row.items() if k not in ['first','second','result','before','after']}),flush=True)
 report={'cases':len(rows),'exceptions':sum('exception' in r for r in rows),'ownership_regressions':sum(r.get('later_ownership_preserved') is False for r in rows),'external_edits_overwritten':sum(r.get('external_preserved') is False for r in rows),'seconds':time.perf_counter()-start}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
