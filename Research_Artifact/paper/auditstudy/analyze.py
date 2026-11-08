"""Paired crossed project/batch analysis and explicitly modeled mixtures."""
import csv,hashlib,json,math,statistics
from pathlib import Path
import numpy as np
from .prepare import ROOT
OUT=ROOT/'recomputed/results_v17'
P=ROOT/'recomputed/tables'
METHODS=['JournalGuardedScoped','JournalPostStatus','ReceiptCoordinatorV15','JournalWitnessV15']
TOOLS=['claude','codex','grok'];Q=METHODS[0];E=METHODS[2]
RUNS={'b1':'closure-confirmation-v16-final','b2':'audit-confirmation-v17-b2','b3':'audit-confirmation-v17-b3'}
def readrows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def writecsv(name,rows):
 with (OUT/(name+'.csv')).open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def estimate(values,rng):
 """values[b,j] contains paired log ratios; resample both crossed factors."""
 a=np.asarray(values,dtype=float);B,J=a.shape
 bi=rng.integers(B,size=(4000,B));ji=rng.integers(J,size=(4000,J))
 samples=a[bi[:,:,None],ji[:,None,:]].mean(axis=(1,2))
 lo,hi=np.exp(np.quantile(samples,[.025,.975]));by=np.exp(a.mean(axis=1))
 return {'ratio':float(np.exp(a.mean())),'ci95':[float(lo),float(hi)],'pairs':B*J,'projects':J,'batches':B,'batch_ratios':{b:float(x) for b,x in zip(RUNS,by)},'loo_batch':[float(np.exp(np.delete(a,b,axis=0).mean())) for b in range(B)],'loo_project':[float(np.exp(np.delete(a,j,axis=1).mean())) for j in range(J)]}
def fmt(r):return f"{r['ratio']:.3f} [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}]"
def main():
 OUT.mkdir(parents=True,exist_ok=True);P.mkdir(parents=True,exist_ok=True);rows=[];provenance={};specs={}
 for b,directory in RUNS.items():
  folder=ROOT/'paper/evidence'/directory;spec=json.loads((folder/'spec.json').read_text());specs[b]=spec
  rr=readrows(folder/'raw.jsonl');assert len(rr)==884 and all(r['pass'] for r in rr);scored=[{**r,'batch':b} for r in rr if not r['warmup']];assert len(scored)==816
  assert spec['binary_sha256']=='7c7e0490eb6e63132e4dc86a3eafda28976c0da8511dd7023a23f8b2b20740f2';rows+=scored
  provenance[b]={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in ['raw.jsonl','spec.json','summary.json']}
 assert specs['b1']['inputs']==specs['b2']['inputs']==specs['b3']['inputs']
 projects=sorted({r['repository'] for r in rows});assert len(projects)==12
 groups={};rng=np.random.default_rng(17301);comp=[];sensitivity=[]
 conditions=sorted({(r['tool'],r['scenario'],r['lifecycle'],r['noise']) for r in rows});assert len(conditions)==17
 for tool,scenario,life,noise in conditions:
  key=f'{tool}/{scenario}/{life}/{noise}';pool=[r for r in rows if (r['tool'],r['scenario'],r['lifecycle'],r['noise'])==(tool,scenario,life,noise)]
  rec={'arms':{},'paired':{}};lookup={(r['batch'],r['repository'],r['method']):r for r in pool};assert len(lookup)==144
  for m in METHODS:
   rr=[r for r in pool if r['method']==m]
   rec['arms'][m]={'n':len(rr),'median_ms':statistics.median(r['wall_ns'] for r in rr)/1e6,'mean_episode_ms':statistics.mean(r['episode_ns'] for r in rr)/1e6,'median_episode_ms':statistics.median(r['episode_ns'] for r in rr)/1e6,'native_commands':sorted(set(tuple(r['commands']) for r in rr)),'mean_evidence_bytes':statistics.mean(r['evidence_bytes'] for r in rr)}
   if m==E:continue
   rec['paired'][m]={}
   for metric in ['wall_ns','episode_ns','confirmation_episode_ns']:
    a=[[math.log(lookup[b,j,E][metric]/lookup[b,j,m][metric]) for j in projects] for b in RUNS];r=estimate(a,rng);rec['paired'][m][metric]=r
    comp.append({'condition':key,'control':m,'metric':metric,'ratio':r['ratio'],'low':r['ci95'][0],'high':r['ci95'][1],'pairs':36,'projects':12,'batches':3,**r['batch_ratios']})
    sensitivity.append({'condition':key,'control':m,'metric':metric,'loo_batch_min':min(r['loo_batch']),'loo_batch_max':max(r['loo_batch']),'loo_project_min':min(r['loo_project']),'loo_project_max':max(r['loo_project'])})
  groups[key]=rec
 costs={};surface=[];thresholds=[];batch_costs=[];breakdown={}
 for t in TOOLS:
  def means(batch=None):
   data=[r for r in rows if r['tool']==t and r['lifecycle']=='cold' and r['noise']==0 and (batch is None or r['batch']==batch)]
   avg=lambda m,s,metric:statistics.mean(r[metric]/1e6 for r in data if r['method']==m and r['scenario']==s)
   return {'normal_ms':avg(E,'normal','episode_ns')-avg(Q,'normal','episode_ns'),'hit_ms':avg(E,'recovery','episode_ns')-avg(Q,'recovery','episode_ns'),'miss_ms':avg(E,'fallback','episode_ns')-avg(Q,'fallback','episode_ns'),'repeat_ms':avg(E,'completed_retry','wall_ns')-avg(Q,'completed_retry','wall_ns')}
  ds=means();dn,dh,dm,dr=(ds[k] for k in ['normal_ms','hit_ms','miss_ms','repeat_ms']);assert dh<0 and dr<0
  costs[t]={**ds,'fresh_difference_ms':dn,'interrupted_difference_ms':dh,'break_even_p':max(0,dn/(dn-dh)) if dn>0 else 0,'repeat_break_even':max(0,dn/-dr)}
  for b in RUNS:
   dd=means(b);batch_costs.append({'tool':t,'batch':b,**dd,'p_star':max(0,dd['normal_ms']/(dd['normal_ms']-dd['hit_ms'])) if dd['normal_ms']>0 else 0,'repeat_star':max(0,dd['normal_ms']/-dd['repeat_ms'])})
  for h in [1,.75,.5,.25,0]:
   df=h*dh+(1-h)*dm;v=dn/(dn-df) if dn>0 and df<0 else None
   thresholds.append({'tool':t,'hit_rate':h,'extra_repeat_rate':0,'p_star':v,'normal_difference_ms':dn,'interrupted_difference_ms':df,'repeat_star_at_p0':dn/-dr})
  for h in np.linspace(0,1,101):
   for p in np.linspace(0,1,101):
    for repeat in [0,.05,.1,.25]:
     diff=(1-p)*dn+p*(h*dh+(1-h)*dm)+repeat*dr
     surface.append({'tool':t,'interruption':float(p),'hit_rate':float(h),'valid_extra_repeats':repeat,'expected_difference_ms':float(diff),'kind':'arithmetic-mean cost model, not a measured mixed workload'})
  for m in METHODS:
   values=[]
   for r in rows:
    if (r['tool'],r['method'],r['scenario'],r['lifecycle'],r['noise'])!=(t,m,'recovery','cold',0):continue
    native=sum(v['elapsed_ns'] for v in r['profile']);rb=sum(v['elapsed_ns'] for v in r['components'] if v['component']=='readback');val=sum(v['elapsed_ns'] for v in r['components'] if v['component']=='evidence_validation');pub=sum(v['elapsed_ns'] for v in r['components'] if v['component']=='publication');nested=0
    for v in r['components']:
     if v['component']=='evidence_validation':break
     if v['component']=='readback':nested+=v['elapsed_ns']
    val=max(0,val-nested);other=r['wall_ns']-native-rb-val-pub;assert other>=0
    values.append(dict(Native=native/1e6,Validation=val/1e6,Readback=rb/1e6,Publication=pub/1e6,Other=other/1e6))
   breakdown[f'{t}/{m}']={k:statistics.mean(v[k] for v in values) for k in values[0]}
 old=json.loads((ROOT/'paper/results_v17/facts.json').read_text());rec=[groups[f'{t}/recovery/cold/0']['paired'][Q]['wall_ns'] for t in TOOLS];ep=[groups[f'{t}/recovery/cold/0']['paired'][Q]['episode_ns'] for t in TOOLS]
 macros={'RecoveryMin':min(100*(1-r['ratio']) for r in rec),'RecoveryMax':max(100*(1-r['ratio']) for r in rec),'EpisodeMin':min(100*(1-r['ratio']) for r in ep),'EpisodeMax':max(100*(1-r['ratio']) for r in ep)}
 facts={**old,'comparisons':groups,'costs':costs,'breakdown':breakdown,'timing':{'scored':2448,'total':2652,'projects':12,'batches':3,'per_cell_per_batch':1,'macros':macros,'bootstrap':'4000 paired crossed project/batch resamples','provenance':provenance}}
 (OUT/'facts.json').write_text(json.dumps(facts,indent=2)+'\n');(OUT/'timing-rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
 for name,data in [('all_comparisons',comp),('sensitivity',sensitivity),('mixture_surface',surface),('thresholds',thresholds),('batch_costs',batch_costs)]:writecsv(name,data)
 (P/'results-commands.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+f'{v:.1f}'+'}' for k,v in macros.items())+'\n')
 table=[r'\begin{table*}[!t]\centering\small',r'\caption{Recovery medians (ms) and paired ratios over three batches and twelve projects}\label{tab:timing}',r'\begin{tabular}{@{}llrrrrll@{}}\toprule',r'Adapter & Manager & J-Q & J-1 & RC-E & J-E & Recovery ratio [95\% CI] & Episode ratio [95\% CI] \\\midrule']
 for t in TOOLS:
  for life in ['cold','warm']:
   d=groups[f'{t}/recovery/{life}/0'];a=d['arms'];q=d['paired'][Q]
   table.append(t.title()+' & '+life+' & '+' & '.join(f"{a[m]['median_ms']:.2f}" for m in METHODS)+' & '+fmt(q['wall_ns'])+' & '+fmt(q['episode_ns'])+r' \\')
 table += [r'\bottomrule\end{tabular}\end{table*}'];(P/'timing-table.tex').write_text('\n'.join(table)+'\n')
 table=[r'\begin{table*}[!t]\centering\small',r'\caption{Execution-path paired ratios with crossed project/batch intervals}\label{tab:paths}',r'\begin{tabular}{@{}llp{3.65cm}p{3.65cm}p{3.65cm}@{}}\toprule',r'Adapter & Path & RC-E/J-Q confirmation & RC-E/J-Q episode & RC-E/J-1 confirmation \\\midrule']
 for t in TOOLS:
  for s,label in [('normal','Fresh'),('fallback','Evidence miss'),('completed_retry','Repeat')]:
   d=groups[f'{t}/{s}/cold/0']['paired'];table.append(f'{t.title()} & {label} & '+fmt(d[Q]['wall_ns'])+' & '+fmt(d[Q]['episode_ns'])+' & '+fmt(d[METHODS[1]]['wall_ns'])+r' \\')
 for s,n,label in [('recovery',2048,'2,048 extra files'),('unrelated_edit',0,'Unrelated edit')]:
  d=groups[f'claude/{s}/cold/{n}']['paired'];table.append('Claude & '+label+' & '+fmt(d[Q]['wall_ns'])+' & '+fmt(d[Q]['episode_ns'])+' & '+fmt(d[METHODS[1]]['wall_ns'])+r' \\')
 table += [r'\bottomrule\end{tabular}\end{table*}'];(P/'paths-table.tex').write_text('\n'.join(table)+'\n')
 bt=[r'\begin{table}[!t]\centering\small',r'\caption{Cold recovery RC-E/J-Q by independent batch}\label{tab:batches}',r'\begin{tabular}{@{}lrrr@{}}\toprule',r'Batch & Claude & Codex & Grok \\\midrule']
 for b in RUNS:bt.append(b.upper()+' & '+' & '.join(f"{groups[f'{t}/recovery/cold/0']['paired'][Q]['wall_ns']['batch_ratios'][b]:.3f}" for t in TOOLS)+r' \\')
 bt += [r'\bottomrule\end{tabular}\end{table}'];(P/'batch-table.tex').write_text('\n'.join(bt)+'\n')
 th=[r'\begin{table}[!t]\centering\small',r'\caption{Modeled break-even fractions from arithmetic means}\label{tab:threshold}',r'\begin{tabular}{@{}lrrr@{}}\toprule',r'Adapter & $p^*(1,0)$ & $p^*(.5,0)$ & $r^*(0)$ \\\midrule']
 for t in TOOLS:
  row=next(r for r in thresholds if r['tool']==t and r['hit_rate']==.5)
  th.append(t.title()+f" & {100*costs[t]['break_even_p']:.1f}\\% & "+(f"{100*row['p_star']:.1f}\\%" if row['p_star'] is not None else '--')+f" & {100*costs[t]['repeat_break_even']:.1f}\\%"+r' \\')
 th += [r'\bottomrule\end{tabular}\end{table}'];(P/'threshold-table.tex').write_text('\n'.join(th)+'\n')
 print(json.dumps({'headline':macros,'costs':costs,'scored':len(rows)}))
if __name__=='__main__':main()
