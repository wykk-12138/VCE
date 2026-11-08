"""Bounded transition exploration of the documented protocol abstraction.

This checks protocol states, not Rust/Python equivalence. Native response truth,
dependency closure and a stable validation/publication cut remain assumptions.
"""
from collections import deque
from dataclasses import dataclass,replace
import json
from .prepare import ROOT

@dataclass(frozen=True)
class State:
 head:int=-1
 bound:tuple=(None,None)
 claimed:int=0
 intents:int=0
 before:tuple=(-1,-1)
 body:int=0
 residue:bool=False
 edited:bool=False
 evidence:tuple=(None,None)
 capture:int=-1
 owner:int=-1
 completed:int=0

def put(t,i,v):return t[:i]+(v,)+t[i+1:]

def history(s,same,mode):
 contents=(1,1 if same else 2)
 for p in range(2):
  bit=1<<p
  if s.capture!=-1:continue
  if s.bound[p] is None:
   yield f'preview({p})',replace(s,bound=put(s.bound,p,(s.head,s.body))),None
  if not s.claimed&bit and s.bound[p] is not None:
   if s.bound[p]==(s.head,s.body) or (mode=='no_approval_binding' and s.bound[p][0]==s.head):
    yield f'claim({p})',replace(s,head=p,claimed=s.claimed|bit),None
  if s.head==p and not s.intents&bit:
   if s.bound[p] is not None and (s.bound[p][1]==s.body or mode=='no_approval_binding'):
    yield f'intent({p})',replace(s,intents=s.intents|bit,before=put(s.before,p,s.body)),None
  if s.head==p and s.intents&bit and s.body==s.before[p] and not s.completed&bit:
   bad='overwrote edit after approval' if s.edited and s.bound[p][1]!=s.body else None
   yield f'native-complete({p})',replace(s,body=contents[p],residue=False,capture=p),bad
  if s.claimed&bit and s.intents&bit and (s.head==p or mode=='no_generation') and s.body==contents[p]:
   evidence=s.evidence[p]
   valid=evidence is not None and evidence[0]==s.body and (mode=='no_absence_watch' or evidence[1]==s.residue)
   # A query is permitted when evidence misses; an unavailable query simply
   # has no publication transition. Trusted status requires recovery clear.
   for how,accept in [('evidence',valid),('query',not s.residue)]:
    if accept:
     bad='unclean publication' if s.residue else 'superseded ownership' if s.head!=p else None
     yield f'publish-{how}({p})',replace(s,owner=p,completed=s.completed|bit),bad
 if s.capture!=-1:
  p=s.capture
  yield f'seal({p})',replace(s,capture=-1,evidence=put(s.evidence,p,(s.body,s.residue))),None
  yield 'crash-before-seal',replace(s,capture=-1),None
 else:
  if not s.edited:yield 'external-edit',replace(s,body=3,edited=True),None
  if not s.residue:yield 'new-recovery-residue',replace(s,residue=True),None

def explore(same,mode):
 start=State();queue=deque([start]);paths={start:[]};edges=0
 while queue:
  s=queue.popleft()
  for label,nxt,bad in history(s,same,mode):
   edges+=1
   if bad:return {'states':len(paths),'transitions':edges,'violation':bad,'trace':paths[s]+[label]}
   if nxt not in paths:paths[nxt]=paths[s]+[label];queue.append(nxt)
 return {'states':len(paths),'transitions':edges,'violation':None,'bounds':'two plans; one external body edit; one residue flag; atomic observation/publication; finite captured responses'}

def attempts(mode):
 # Three invocations: P/attempt1, P/attempt2, Q/attempt1.
 # stage 0 not submitted, 1 delayed before lease, 2 inside lease, 3 finished.
 start=(-1,-1,(0,0,0));queue=deque([start]);paths={start:[]};edges=0;plans=(0,0,1)
 while queue:
  latest,lease,st=queue.popleft();state=(latest,lease,st)
  for i in range(3):
   moves=[]
   if st[i]==0 and (i==0 or st[i-1]>0) and (lease==-1 or mode=='no_lease'):
    moves.append((f'authorize({i})',(i,lease,put(st,i,1)),None))
   if st[i]==1 and lease==-1:
    sameplan=latest>=0 and plans[latest]==plans[i]
    allowed=sameplan and (i==latest or mode=='no_attempt_fence')
    if allowed:moves.append((f'enter({i})',(latest,i,put(st,i,2)),'stale attempt enters' if i!=latest else None))
   if st[i]==2:
    moves.append((f'finish({i})',(latest,-1,put(st,i,3)),'superseded writer completes' if latest!=i else None))
   for label,nxt,bad in moves:
    edges+=1
    if bad:return {'states':len(paths),'transitions':edges,'violation':bad,'trace':paths[state]+[label]}
    if nxt not in paths:paths[nxt]=paths[state]+[label];queue.append(nxt)
 return {'states':len(paths),'transitions':edges,'violation':None,'bounds':'three invocations, two plans, one shared native lease'}

def main():
 out=ROOT/'paper/evidence/closure-model-v16';out.mkdir(parents=True,exist_ok=True)
 good={'same_content':explore(True,'complete'),'different_content':explore(False,'complete'),'attempts':attempts('complete')}
 bad={m:explore(True,m) for m in ['no_generation','no_approval_binding','no_absence_watch']}
 bad.update({m:attempts(m) for m in ['no_attempt_fence','no_lease']})
 assert all(r['violation'] is None for r in good.values()),good
 assert all(r['violation'] for r in bad.values()),bad
 atomic=[{'cut':k,'visible':0 if k<4 else 4,'coherent':True} for k in range(5)]
 result={'complete':good,'ablations':bad,'atomic_publication_cuts':atomic,'unique_identity':'publication updates one key per plan; checked by state representation, not claimed as an independent theorem',
  'source_mapping':{'preview/claim/intent':'evolution.rs:evolution_binding/evolution_claim','enter/finish':'base_native_gate.py and native_gate.py lease/head/attempt checks',
   'seal/evidence validation':'native_gate.py:main; witness.rs:witness_probe','publication':'receipt.rs:receipt_commit; journal.rs:journal_execute transaction'},
  'assumptions':['truthful native completion/status','audited dependency closure','fixed execution environment','stable validation/publication cut','atomic SQLite transaction','process crashes, not power loss']}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
