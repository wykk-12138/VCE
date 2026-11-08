"""Vector figures with declared evidence roles and hashed inputs."""
import csv,hashlib,json,shutil,statistics
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from matplotlib.colors import ListedColormap
P=Path(__file__).resolve().parent;ROOT=P/'figure-data';OUT=P/'figures'
font_path=Path('C:/Windows/Fonts/times.ttf')
if font_path.is_file():font_manager.fontManager.addfont(str(font_path))
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams['svg.fonttype']='none'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','Nimbus Roman','Liberation Serif','DejaVu Serif'],'font.size':8,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,
 'legend.fontsize':7,'pdf.fonttype':42,'ps.fonttype':42,'axes.edgecolor':'black','axes.linewidth':.7,'mathtext.fontset':'stix',
 'xtick.direction':'in','ytick.direction':'in','savefig.facecolor':'white'})
COL=['#C67B45','#496F9A','#007F82','#88729E'];METHODS=['JournalGuardedScoped','JournalPostStatus','ReceiptCoordinatorV15','JournalWitnessV15'];LABEL=['J-Q','J-1','RC-E','J-E']
TOOLS=['claude','codex','grok'];TL=['Claude','Codex','Grok'];SOURCES={};MANIFEST=[]
def load(rel):
 p=ROOT/rel;SOURCES[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 if p.suffix=='.jsonl':return [json.loads(s) for s in p.read_text().splitlines()]
 if p.suffix=='.csv':return list(csv.DictReader(p.open(encoding='utf-8-sig')))
 return json.loads(p.read_text())
def frame(a):
 for sp in a.spines.values():sp.set_visible(True);sp.set_color('black')
 a.tick_params(top=True,right=True,length=2.5,width=.6);a.set_axisbelow(True);a.grid(axis='y',lw=.35,color='#DDE3E7')
def panels(n=4,h=2.32,diagram=False):
 f,axs=plt.subplots(1,n,figsize=(7.12 if n==4 else 3.5,h));axs=np.atleast_1d(axs)
 f.subplots_adjust(left=.07 if n==4 else .05,right=.985,top=.79 if not diagram else .94,bottom=.28 if not diagram else .18,wspace=.62 if not diagram else .14)
 for a in axs:
  frame(a)
  if diagram:a.set(xlim=(0,1),ylim=(0,1),xticks=[],yticks=[]);a.grid(False)
 return f,axs
def caps(f,axs,names):
 for i,(a,name) in enumerate(zip(axs,names)):
  pos=a.get_position();f.text(pos.x0+pos.width/2,.018,f'({chr(97+i)}) {name}',ha='center',va='bottom',fontsize=8)
def save(f,name,purpose,inputs):
 for ext in ['pdf','svg']:f.savefig(OUT/f'{name}.{ext}')
 f.savefig(OUT/f'{name}.png',dpi=220);plt.close(f)
 MANIFEST.append({'figure':name,'purpose':purpose,'sources':inputs,'sha256':hashlib.sha256((OUT/f'{name}.pdf').read_bytes()).hexdigest()})
def box(a,x,y,w,h,text,fc='#E3EEEA',fs=8):
 a.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.014,rounding_size=.02',fc=fc,ec='black',lw=.65));a.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs)
def arrow(a,x1,y1,x2,y2):a.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=8,color='#354650',lw=.8))

def diagrams():
 from figure_sources.gap_figure import export as export_gap, PURPOSE as gap_purpose
 gap_report=export_gap(OUT)
 MANIFEST.append({'figure':'f01_gap','purpose':gap_purpose,'sources':[],
                  'generator':'figure_sources/gap_figure.py','sha256':gap_report['files']['pdf']})
 f,a=panels(4,1.66,True)
 heads=['Approval manager','Native gate','Evidence validator','Manager transaction'];bodies=['Source + target binding\nLogical generation','One gate/writer PID\nLease: runpy + capture','Response + dependencies\nIndependent readback','Execution + activation\nTool state + approval']
 for ax,h,b in zip(a,heads,bodies):
  box(ax,.06,.65,.88,.23,h,fs=8);arrow(ax,.5,.63,.5,.48);box(ax,.06,.13,.88,.33,b,fc='#E7EBF3',fs=7.4)
 caps(f,a,['Approve','Capture','Validate or query','Publish']);save(f,'f02_overview','Map the four responsibilities and persistence domains',[])
 f,a=panels(2,2.0,True)
 for ax,head in zip(a,['Stored evidence','Current observations']):box(ax,.06,.78,.88,.15,head,fs=7.8)
 for y,t in zip([.54,.31,.08],['Plan / generation / code','Actual response','Files + absence watch']):box(a[0],.06,y,.88,.16,t,fs=7.1)
 for y,t,c in zip([.54,.31,.08],['Binding still current','Content + reference','No new native residue'],['#E3EEEA','#E3EEEA','#F0E5D9']):box(a[1],.06,y,.88,.16,t,fc=c,fs=7.1)
 caps(f,a,['Capture conditions','Validate conditions']);save(f,'f03_validity','Distinguish saved nodes from absence observations',[])
 f,a=panels(2,1.92,True)
 for ax,labels in zip(a,[['P completes','Q claims same bytes','Retry P: reject'],['P / attempt 1 waits','P / attempt 2 completes','Attempt 1: fenced']]):
  for y,t in zip([.70,.39,.08],labels):box(ax,.06,y,.88,.19,t,fc='#E3EEEA' if y>.1 else '#F0E0DD',fs=7.2)
  arrow(ax,.5,.69,.5,.60);arrow(ax,.5,.38,.5,.29)
 caps(f,a,['Logical ownership','Physical execution']);save(f,'f04_ownership','Explain why generation and attempt identity are separate',[])

def experiments():
 factrel='paper/results_v17/facts.json';facts=load(factrel);d=facts['comparisons']
 rawrel='paper/results_v17/timing-rows.jsonl';raw=[r for r in load(rawrel) if not r['warmup']]
 validrel='paper/evidence/closure-validation-v16/inherited/raw.jsonl';valid=load(validrel)
 extrarel='paper/evidence/closure-validation-v16/extra.jsonl';extra=load(extrarel)
 f,a=panels(h=2.48)
 safety=[r for r in valid+extra if r['suite']=='safety']
 complete=[sum(r['method']==m and r['expected_completion'] and r['pass'] for r in safety) for m in METHODS]
 refused=[sum(r['method']==m and not r['expected_completion'] and r['pass'] for r in safety) for m in METHODS]
 a[0].bar(LABEL,complete,color='#007F82',label='Completion');a[0].bar(LABEL,refused,bottom=complete,color='#8FA9BE',label='Safe refusal');a[0].set(ylabel='Histories',ylim=(0,64));a[0].legend(loc='upper left',bbox_to_anchor=(-.13,1.36),frameon=False,ncol=2,fontsize=6.5)
 branchrel='paper/evidence/audit-branches-v17/raw.jsonl';br=load(branchrel)
 matrix=[[sum(r['tool']==t and pred(r) for r in br) for pred in [lambda r:r['evidence_hit'],lambda r:not r['evidence_hit'] and r['native_before_retry'],lambda r:not r['native_before_retry']]] for t in TOOLS]
 a[1].imshow(matrix,cmap=ListedColormap(['#E6F0EC','#C6DDD5','#8FBEB4','#467F85']),aspect='auto')
 a[1].set(xticks=range(3),xticklabels=['Hit','Miss /\nactive','Reject'],yticks=range(3),yticklabels=TL)
 for y,row in enumerate(matrix):
  for xx,value in enumerate(row):a[1].text(xx,y,str(value),ha='center',va='center',fontsize=8)
 # Each denominator is the targeted ablation matrix, not a general failure rate.
 earlier=load('paper/results_v14/facts.json')['validation'];current=facts['validation']['inherited']
 a[2].bar(['No state\nvalidation','No residue\nwatch'],[earlier['ablation_false_success'],current['ablation_false_success']],color=['#BC6D57','#8D769D']);a[2].set(ylabel='False-success cases',ylim=(0,7));a[2].set_yticks([0,2,4,6])
 liferel='paper/evidence/audit-lifecycle-v17/raw.jsonl';lr=load(liferel);cuts=['before','during','after']
 completed=[sum(r['cut']==c and r['retry_completed'] for r in lr) for c in cuts];refused=[sum(r['cut']==c and not r['retry_completed'] for r in lr) for c in cuts]
 a[3].bar(range(3),completed,color='#007F82');a[3].bar(range(3),refused,bottom=completed,color='#8FA9BE');a[3].set(xticks=range(3),xticklabels=['Before','During','After'],ylabel='Gate-kill histories',ylim=(0,21),yticks=[0,6,12,18])
 caps(f,a,['Safety outcomes','Differential status','Targeted ablations','Immediate retry']);save(f,'f05_validity','Tie safety, predicate mutations and actual gate termination to separate obligations',[validrel,extrarel,branchrel,liferel,'paper/results_v14/facts.json',factrel])
 f,a=panels(h=2.45);x=np.arange(3);width=.19
 for j,(m,label,c) in enumerate(zip(METHODS,LABEL,COL)):
  a[0].bar(x+(j-1.5)*width,[d[f'{t}/recovery/cold/0']['arms'][m]['median_ms'] for t in TOOLS],width,color=c,label=label)
  a[1].bar(x+(j-1.5)*width,[d[f'{t}/recovery/cold/0']['arms'][m]['median_episode_ms'] for t in TOOLS],width,color=c)
 for ax,yl in zip(a[:2],['Recovery (ms)','Whole episode (ms)']):ax.set(xticks=x,xticklabels=TL,ylabel=yl)
 f.legend(*a[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.40,1.01),ncol=4,frameon=False)
 counts=[[len(d[f'claude/{s}/cold/0']['arms'][m]['native_commands'][0]) for s in ['normal','recovery','fallback']] for m in METHODS]
 a[2].imshow(counts,cmap=ListedColormap(['#E8F0EC','#ACC9CC','#6E99A7','#3C607B']),vmin=0,vmax=3,aspect='auto');a[2].set(xticks=range(3),xticklabels=['Fresh','Hit','Miss'],yticks=range(4),yticklabels=LABEL)
 for y,row in enumerate(counts):
  for xx,v in enumerate(row):a[2].text(xx,y,str(v),ha='center',va='center',color='white' if v>=2 else 'black',fontsize=8)
 for i,t in enumerate(TOOLS):
  for j,life in enumerate(['cold','warm']):
   r=d[f'{t}/recovery/{life}/0']['paired']['JournalGuardedScoped']['wall_ns'];y=i*2+j
   a[3].errorbar(r['ratio'],y,xerr=[[r['ratio']-r['ci95'][0]],[r['ci95'][1]-r['ratio']]],fmt='o' if j==0 else 's',color=COL[2] if j==0 else COL[1],capsize=2,ms=3)
 a[3].set(yticks=np.arange(6),yticklabels=['C cold','C warm','X cold','X warm','G cold','G warm'],xlabel='RC-E / J-Q',xlim=(0,.25),xticks=[0,.1,.2]);a[3].invert_yaxis()
 caps(f,a,['Cold recovery','Complete interruption','Native processes','Paired recovery ratios']);save(f,'f06_recovery','Test latency and work reductions under matched semantics',[factrel,rawrel])
 f,a=panels(h=2.48)
 cols=['#B98154','#468C91','#93B6AA','#82739B','#B8C0C7'];keys=['Native','Validation','Readback','Publication','Other'];xx=np.arange(6);bottom=np.zeros(6)
 for k,c in zip(keys,cols):
  v=[facts['breakdown'][f'{t}/{m}'][k] for t in TOOLS for m in ['JournalGuardedScoped','ReceiptCoordinatorV15']]
  a[0].bar(xx,v,bottom=bottom,color=c,width=.7,label=k);bottom+=v
 a[0].set(xticks=xx,xticklabels=['C-Q','C-E','X-Q','X-E','G-Q','G-E'],ylabel='Recovery work (ms)');a[0].tick_params(axis='x',labelsize=6)
 f.legend(*a[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.52,1.01),ncol=5,frameon=False,fontsize=6.5)
 domainrel='paper/results_v17/domain_thresholds.csv';dd=load(domainrel)
 for m,c,label in [('ReceiptCoordinatorV14','#88729E','Full'),('ReceiptCoordinatorV15','#007F82','Scoped')]:
  vals=[next(r for r in dd if r['method']==m and int(r['ordinary_files'])==n and float(r['hit_rate'])==1) for n in [0,2048]]
  # Plot measured normal and interrupted whole-episode differences, retaining
  # costs above zero and negative saving values on the same common scale.
  for off,key,style in [(-.09,'normal_ms','o'),(.09,'hit_ms','s')]:
   a[1].plot(np.arange(2)+off,[float(r[key]) for r in vals],marker=style,ms=3,color=c,ls='--' if key=='normal_ms' else '-',label=label if key=='normal_ms' else None)
 a[1].axhline(0,color='#333333',lw=.65);a[1].set(xticks=[0,1],xticklabels=['0','2,048'],xlabel='Ordinary source files',ylabel='Episode difference (ms)');a[1].legend(frameon=False,fontsize=6.3,loc='upper left')
 h=np.linspace(.01,1,100)
 for t,c in zip(TOOLS,[COL[2],COL[1],COL[3]]):
  d=facts['costs'][t];df=h*d['hit_ms']+(1-h)*d['miss_ms'];v=np.where(df<0,d['normal_ms']/(d['normal_ms']-df),np.nan)
  a[2].plot(h,v,color=c,label=t.title())
 a[2].set(xlabel='Recovery hit fraction h',ylabel='Break-even interruption p*',xlim=(0,1),ylim=(0,1));a[2].legend(frameon=False,fontsize=6.1,loc='upper right')
 r=np.linspace(0,.25,101)
 for t,c in zip(TOOLS,[COL[2],COL[1],COL[3]]):
  d=facts['costs'][t];a[3].plot(r,d['normal_ms']+r*d['repeat_ms'],color=c)
 a[3].axhline(0,color='#333333',lw=.7);a[3].set(xlabel='Valid repeats r',ylabel='Cost difference (ms)')
 caps(f,a,['Exclusive components','Validation domain','Recovery crossover','Repeat amortization']);save(f,'f07_cost','Locate saved work and quantify validation-domain and workload activation boundaries; domain circles=fresh, squares=interrupted',[factrel,rawrel,domainrel])
 from figure_sources.dependency_figure import main as dependency_figure
 dependency_figure()
 dependency_inputs=['paper/results_v15/facts.json','paper/evidence/dependency-benchmark-v15-opt1/summary.json','paper/evidence/dependency-benchmark-v15-opt1/raw.jsonl']
 for rel in dependency_inputs:load(rel)
 MANIFEST.append({'figure':'f08_dependencies','purpose':'Explain dependency-selector scale and invalidation; separate assertion-enabled selector build','sources':dependency_inputs,'sha256':hashlib.sha256((OUT/'f08_dependencies.pdf').read_bytes()).hexdigest()})
 if facts['composition'] is None:
  f,a=panels(h=2.4)
  for ax in a:ax.text(.5,.5,'DBOS validation\nin progress',ha='center',va='center',transform=ax.transAxes)
  caps(f,a,['Pending','Pending','Pending','Pending']);save(f,'f09_runtime','Temporary layout placeholder; never final evidence',[]);return
 cprel='paper/evidence/closure-dbos-v16/raw.jsonl';cp=load(cprel);legacyrel='paper/results_v7/composition.csv';legacy=load(legacyrel)
 f,a=panels(h=2.4);cm=['OriginalReplan','JournalGuardedScoped','ReceiptCoordinatorV15','JournalWitnessV15'];cl=['Replan','J-Q','RC-E','J-E']
 a[0].bar(cl,[sum(r['method']==m and not r['historical_response'] and r['oracle']['unique_api_completion'] for r in cp) for m in cm],color=COL);a[0].set(ylabel='Unique current completions',ylim=(0,27),yticks=[0,6,12,18,24])
 for j,(m,c) in enumerate(zip(cm,COL)):
  vals=[statistics.mean(r['activation_calls'] for r in cp if r['method']==m and r['scenario']==s) for s in ['after_native','after_external','after_step']]
  a[1].bar(x+(j-1.5)*width,vals,width,color=c)
 a[1].set(xticks=x,xticklabels=['Native','Return','Step'],ylabel='Activations / episode',ylim=(0,2.5))
 for j,(m,c) in enumerate(zip(cm,COL)):
  vals=[statistics.mean(len(r['retry_commands']) for r in cp if r['method']==m and r['scenario']==s) for s in ['after_native','after_external','after_step']]
  a[2].bar(x+(j-1.5)*width,vals,width,color=c)
 a[2].set(xticks=x,xticklabels=['Native','Return','Step'],ylabel='Native processes on retry')
 for j,e in enumerate(['NativeJournal','ReceiptCoordinator']):
  vals=[int(next(r for r in legacy if r['engine']==engine and r['endpoint']==e)['unique_completions']) for engine in ['Styx','Halfmoon']]
  a[3].bar(np.arange(2)+(j-.5)*.33,vals,.33,color=COL[0 if j==0 else 2],label='Journal' if j==0 else 'RC (query)')
 a[3].set(xticks=[0,1],xticklabels=['Styx','Halfmoon'],ylabel='Query-contract completions',ylim=(0,160));a[3].legend(frameon=False,fontsize=6,loc='upper left',bbox_to_anchor=(-.14,1.35))
 f.legend([plt.Rectangle((0,0),1,1,fc=c) for c in COL],cl,loc='upper left',bbox_to_anchor=(.08,1.015),ncol=4,frameon=False)
 caps(f,a,['Final DBOS outcomes','Crash boundary','Resumed native work','Published compositions']);save(f,'f09_runtime','Separate endpoint mechanism from durable workflow response caching',[cprel,legacyrel])

def mixture():
 facts=load('paper/results_v17/facts.json');f,a=panels(h=2.48);p=np.linspace(0,1,101);h=np.linspace(0,1,101)
 for ax,t in zip(a[:3],TOOLS):
  d=facts['costs'][t];v=(1-p[:,None])*d['normal_ms']+p[:,None]*(h[None,:]*d['hit_ms']+(1-h[None,:])*d['miss_ms'])
  ax.contourf(h,p,v,levels=[-2000,-500,-100,-25,0,25,100,500,2000],colors=['#1A6D72','#4A9995','#85BEB1','#CBE0CA','#F4E5C4','#DCAE79','#BD7856','#935044'])
  ax.contour(h,p,v,levels=[0],colors='black',linewidths=.9)
  ax.set(xlabel='Hit fraction h',ylabel='Interruption p',xticks=[0,.5,1],yticks=[0,.5,1])
  for repeat,style in [(.05,'--'),(.1,':')]:ax.contour(h,p,v+repeat*d['repeat_ms'],levels=[0],colors='black',linestyles=style,linewidths=.8)
  frame(ax);ax.grid(False)
 for t,c in zip(TOOLS,[COL[2],COL[1],COL[3]]):
  d=facts['costs'][t];r=np.linspace(0,.25,101);a[3].plot(r,np.maximum(0,(d['normal_ms']+r*d['repeat_ms'])/(d['normal_ms']-d['hit_ms'])),color=c,label=t.title())
 a[3].set(xlabel='Valid repeats r',ylabel='p* at h = 1');a[3].legend(frameon=False,fontsize=6)
 f.text(.41,.98,'Zero-cost contours: r = 0 (solid), 0.05 (dashed), 0.10 (dotted)',ha='center',va='top',fontsize=7)
 caps(f,a,['Claude cost domain','Codex cost domain','Grok cost domain','Combined amortization']);save(f,'f10_mixture','Show explicitly modeled interruption/hit/repeat cost domains; blue-green means lower expected cost',['paper/results_v17/facts.json'])

if __name__=='__main__':
 diagrams();experiments();mixture();(P/'figure_manifest.json').write_text(json.dumps({'figures':MANIFEST,'source_sha256':SOURCES},indent=2)+'\n');print(json.dumps({'figures':len(MANIFEST)}))
