import argparse,hashlib,json,os,sqlite3,tempfile,time,traceback
from contextlib import closing
from .client import *
from paper.evolutionstudy import safety
from paper.dependencystudy import validation as inherited
from paper.finalstudy.cases import oracle

def configure_inherited():
 configure()
 for mod in [inherited,inherited.previous,inherited.metadata,inherited.duplicate]:
  for key in ['BINARY','SCRATCH','call','plan','confirm','configure']:
   if hasattr(mod,key):setattr(mod,key,globals()[key])
 inherited.NEW_METHODS=['ReceiptCoordinatorV15','JournalWitnessV15']

def extra_case(root,item,tool,method,mode):
 fixture=setup(root,item,tool);p=plan(root,tool,method)
 first=confirm(root,tool,method,p,fault='after_native');assert first['exit_code']==86
 with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
  if db.execute("SELECT 1 FROM sqlite_master WHERE name='native_completion_evidence'").fetchone():db.execute('DELETE FROM native_completion_evidence');db.commit()
 before=safety.ownership(root);n=len(trace(root))
 r=confirm(root,tool,method,p,retry=True,extra={'CLOSURE_STATUS_FAILURE':mode})
 after=safety.ownership(root)
 checked=oracle(root,tool,fixture,p['prompt_id'],p['plan']['operationId'],method,r)
 return {'pass':not api_success(r) and before==after and not checked['false_success'],
         'commands':[x['command'] for x in trace(root)[n:]],'result':r,'oracle':checked}

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 configure_inherited();inherited.main(argparse.Namespace(out=a.out/'inherited'))
 rows=[];item=corpus('development')[0]
 with tempfile.TemporaryDirectory(prefix='x-',dir=SCRATCH) as tmp,(a.out/'extra.jsonl').open('w') as f:
  tasks=[('safety',m,t,s) for m in ['JournalGuardedScoped','JournalPostStatus'] for t in ['claude','codex','grok'] for s in safety.SCENARIOS]
  tasks += [('status_failure',m,t,s) for m in METHODS for t in ['claude','codex','grok'] for s in ['exit','malformed']]
  for suite,m,t,s in tasks:
   root=Path(tmp)/str(len(rows))
   try:r=safety.run_case(root,item,t,m,s,BINARY) if suite=='safety' else extra_case(root,item,t,m,s)
   except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
   row={'suite':suite,'method':m,'tool':t,'scenario':s,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
   if not r['pass']:print(json.dumps(row),flush=True)
   if len(rows)%20==0:print(json.dumps({'extra':len(rows),'failed':sum(not r['pass'] for r in rows)}),flush=True)
 inherited_report=json.loads((a.out/'inherited/summary.json').read_text())
 report={'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'inherited':inherited_report,'extra_cases':len(rows),'extra_passed':sum(r['pass'] for r in rows)}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 assert inherited_report['full_cases']==inherited_report['full_passed'] and all(r['pass'] for r in rows)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args())
