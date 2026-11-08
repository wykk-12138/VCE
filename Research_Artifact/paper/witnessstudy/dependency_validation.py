"""Exercise backup and hook metadata beyond the deployed instruction/reference."""
import argparse,json,sqlite3,stat,traceback
from contextlib import closing
from paper.finalstudy import cases
from .client import *
from .validation import native_root

def one(root,item,method,tool,scenario):
 fixture=setup(root,item,tool)
 if scenario=='owned_hook':
  path=root/('home/.codex/hooks.json' if tool=='codex' else 'home/.grok/hooks/fixture.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{"hooks": []}\n')
 p=plan(root,tool,method);first=confirm(root,tool,method,p,fault='after_native');assert first['exit_code']==86,first
 files=[p for p in native_root(root,tool).rglob('*') if p.is_file()]
 if scenario=='backup':targets=sorted(p for p in files if 'bak_' in p.name or 'backup' in p.name)
 else:targets=sorted(p for p in files if 'hooks' in p.name or p.parent.name=='hooks')
 assert targets,('required native metadata missing',tool,scenario,[str(p.relative_to(root)) for p in files])
 target=targets[0];assert target.resolve().is_relative_to(root.resolve());target.chmod(target.stat().st_mode|stat.S_IWUSR)
 value=b'EXTERNAL MUTATION OF NATIVE RECOVERY METADATA\n';target.write_bytes(value)
 # The unchanged native tool decides whether the changed metadata invalidates active state.
 native=cases.call(root,tool,'status');envelope=native.get('response',{}).get('data',{}).get('envelope',{})
 expected=envelope.get('ok') is True and envelope.get('status')=='active' and not envelope.get('recoveryRequired',False)
 n=len(trace(root));nw=len(witnesses(root));result=confirm(root,tool,method,p,retry=True);commands=[r['command'] for r in trace(root)[n:]];hits=witnesses(root)[nw:]
 checked=cases.oracle(root,tool,fixture,p['prompt_id'],p['plan']['operationId'],method,result,external={target.relative_to(root).as_posix():value})
 passed=(checked['unique_api_completion'] if expected else not api_success(result)) and checked['external_preserved'] and 'status' in commands and not any(h['hit'] for h in hits)
 return {'pass':passed,'mutated':target.relative_to(root).as_posix(),'native_expected_completion':expected,'commands':commands,'hits':hits,'oracle':checked,'result':result}

def main(a):
 if a.out.exists():raise FileExistsError(a.out)
 a.out.mkdir(parents=True);item=corpus('development')[0];rows=[]
 with tempfile.TemporaryDirectory(prefix='d-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('w') as f:
  for method in NEW_METHODS:
   for tool in ['claude','codex','grok']:
    for scenario in ['backup','owned_hook']:
     if tool=='claude' and scenario=='owned_hook':continue # audited project scope does not own runtime hooks
     try:r=one(Path(tmp)/str(len(rows)),item,method,tool,scenario)
     except Exception as e:r={'pass':False,'exception':repr(e),'traceback':traceback.format_exc()}
     row={'method':method,'tool':tool,'scenario':scenario,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
     print(json.dumps({k:v for k,v in row.items() if k not in ['oracle','result','traceback']}),flush=True)
 report={'cases':len(rows),'passed':sum(r['pass'] for r in rows),'exceptions':sum('exception' in r for r in rows)}
 (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args())
