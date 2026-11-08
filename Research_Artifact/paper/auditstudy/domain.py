"""Measured cost inputs for mixture thresholds at two validation domains."""
import argparse,hashlib,json,random,tempfile,time
from pathlib import Path
from paper.closurestudy.benchmark import one
from paper.closurestudy.client import ROOT,BINARY,SCRATCH,configure,corpus
def main(a):
 a.out.mkdir(parents=True,exist_ok=a.resume);configure();chosen={}
 for item in corpus('confirmation'):chosen.setdefault(item['repository'],item)
 items=list(chosen.values());rng=random.Random(17401);rows=[];began=time.perf_counter()
 methods=['JournalGuardedScoped','ReceiptCoordinatorV14','ReceiptCoordinatorV15']
 conditions=[(s,n) for s in ['normal','recovery','fallback','completed_retry'] for n in [0,2048]]
 spec={'methods':methods,'conditions':conditions,'projects':12,'warmups':24,'scored':288,'order_seed':17401,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'note':'Separate paired domain-cost study, same frozen optimized binary; full-tree and scoped policies with unchanged predicates. Used for cost-mixture sensitivity, not pooled with the three-batch primary estimates.','inputs':items}
 if not a.resume:(a.out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
 else:
  rows=[json.loads(s) for s in (a.out/'raw.jsonl').read_text().splitlines()];assert all(r['pass'] for r in rows)
  (a.out/'resume.json').write_text(json.dumps({'retained_rows':len(rows),'reason':'Original runner no longer present and tool session unavailable; no failure row recorded. Resume the fixed schedule without replacing any measured cell.','binary_sha256':spec['binary_sha256']},indent=2)+'\n')
 retained=len(rows);position=0
 with tempfile.TemporaryDirectory(prefix='domain-',dir=SCRATCH) as tmp,(a.out/'raw.jsonl').open('a' if a.resume else 'w') as f:
  for block in range(-1,12):
   item=items[(block+1)%12];cs=conditions.copy();rng.shuffle(cs)
   for scenario,noise in cs:
    ms=methods.copy();rng.shuffle(ms)
    for method in ms:
     if position<retained:
      old=rows[position];assert (old['block'],old['scenario'],old['noise'],old['method'])==(block,scenario,noise,method);position+=1;continue
     r=one(Path(tmp)/str(len(rows)),item,'claude',method,scenario,'cold',noise)
     row={'block':block,'warmup':block<0,'repository':item['repository'],'tool':'claude','scenario':scenario,'noise':noise,'method':method,**r};rows.append(row);f.write(json.dumps(row)+'\n');f.flush();assert r['pass']
     position+=1
   print(json.dumps({'domain_block':block,'observations':len(rows),'seconds':time.perf_counter()-began}),flush=True)
 summary={'cases':len(rows),'scored':sum(not r['warmup'] for r in rows),'passed':sum(r['pass'] for r in rows),'seconds_this_session':time.perf_counter()-began,'resumed':a.resume,'retained_before_session':retained}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');main(p.parse_args())
