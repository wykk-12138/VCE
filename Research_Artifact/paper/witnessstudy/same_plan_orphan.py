"""A delayed writer for P must be retired by P's own successful retry."""
import argparse,hashlib,json
from .client import *
from paper.evolutionstudy.orphans import until
from paper.finalstudy.cases import oracle

def run_case(root,item,method,tool):
 fixture=setup(root,item,tool);p=plan(root,tool,method);signal=root/'release';log=root/'gate_events.jsonl'
 child=start(root,tool,'confirm',extra={'EVOLUTION_PAUSE_BEFORE_GATE':str(signal)},**arguments(method,p))
 try:
  until(lambda:signal.with_suffix('.ready').exists() and signal.with_suffix('.ready').read_text().strip().isdigit())
  old_pid=int(signal.with_suffix('.ready').read_text());child.kill();child.wait(timeout=5)
  second=confirm(root,tool,method,p,retry=True);assert api_success(second),second
  signal.touch();child.communicate(timeout=15)
  events=[json.loads(x) for x in log.read_text().splitlines()];old=[x for x in events if x['pid']==old_pid]
  checked=oracle(root,tool,fixture,p['prompt_id'],p['plan']['operationId'],method,second)
  return {'pass':any(x['kind']=='fenced' for x in old) and checked['unique_api_completion'],'delayed_native_entered':any(x['kind']=='enter' for x in old),
   'old_native_events':old,'unique_api_completion':checked['unique_api_completion'],'oracle':checked}
 finally:
  signal.touch()
  if child.poll() is None:child.kill()
  child.communicate(timeout=15)

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 a.out.mkdir(parents=True);rows=[];item=corpus('development')[0]
 (a.out/'spec.json').write_text(json.dumps({'methods':METHODS,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'scenario':'delayed orphan of P after successful retry of P'},indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='s-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('w') as f:
  for method in METHODS:
   for tool in ['claude','codex','grok']:
    row={'method':method,'tool':tool,**run_case(Path(tmp)/str(len(rows)),item,method,tool)};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    print(json.dumps({k:v for k,v in row.items() if k not in ['oracle','old_native_events']}),flush=True)
 report={'cases':len(rows),'passed':sum(r['pass'] for r in rows),'delayed_native_entries':sum(r['delayed_native_entered'] for r in rows)}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args())
