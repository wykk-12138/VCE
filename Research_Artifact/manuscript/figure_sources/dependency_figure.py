"""Editable generator for supplementary Figure S1 (dependency scope)."""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
OUT=P/"figures"
METHODS=["JournalGuardedScoped","ReceiptCoordinatorV14","ReceiptCoordinatorV15","JournalWitnessV15"]
def figure(bench,rows):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','Nimbus Roman','Liberation Serif','DejaVu Serif'],'svg.fonttype':'none','font.size':9,'axes.labelsize':10,'axes.edgecolor':'black','axes.linewidth':.8,'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':220})
 colors=['#D59A37','#147D92','#B84B54','#865A9C'];labels=['Journal / query','RC / full state','RC / dependencies','Journal / dependencies']
 fig,axs=plt.subplots(1,4,figsize=(13.4,3.1),gridspec_kw={'wspace':.5});xs=[0,64,512,2048]
 for j,(m,c,label) in enumerate(zip(METHODS,colors,labels)):
  med=[bench['comparisons'][f'recovery/{n}/nested']['arms'][m]['median_ms'] for n in xs]
  axs[0].plot(xs,med,marker=['s','o','^','D'][j],color=c,linewidth=1.4,markersize=3,label=label)
  lo=[];hi=[]
  for n in xs:
   values=sorted(r['wall_ns']/1e6 for r in rows if not r['warmup'] and r['method']==m and r['scenario']=='recovery' and r['noise']==n and r['shape']=='nested');lo.append(values[len(values)//4]);hi.append(values[3*len(values)//4])
  axs[0].fill_between(xs,lo,hi,color=c,alpha=.1,linewidth=0)
  episode=[bench['comparisons'][f'recovery/{n}/nested']['arms'][m]['mean_episode_ms'] for n in xs];axs[1].plot(xs,episode,marker=['s','o','^','D'][j],color=c,linewidth=1.4,markersize=3)
  size=[bench['comparisons'][f'recovery/{n}/nested']['arms'][m]['median_evidence_bytes']/1024 for n in xs];axs[2].plot(xs,size,marker=['s','o','^','D'][j],color=c,linewidth=1.4,markersize=3)
  val=bench['comparisons']['unrelated_edit/0/nested']['arms'][m]['median_ms'];axs[3].bar(j,val,color=c,edgecolor='black',linewidth=.5)
 axs[0].set(ylabel='Recovery latency (ms)');axs[0].legend(fontsize=6.8,frameon=False,loc='center left',handlelength=1)
 axs[1].set(ylabel='Interrupted episode (ms)');axs[2].set(ylabel='Completion evidence (KiB)')
 for ax in axs[:3]:ax.set(xlabel='Additional ordinary files',xticks=[0,512,2048],ylim=(0,None))
 axs[3].set(ylabel='Recovery after edit (ms)',xticks=range(4),xticklabels=['J-Q','RC-F','RC-D','J-D'],xlabel='Endpoint / evidence policy')
 for ax,title in zip(axs,['(a) Recovery scalability','(b) Complete interrupted episode','(c) Evidence footprint','(d) Unrelated-file invalidation']):
  ax.tick_params(direction='in',top=True,right=True);ax.grid(axis='y',color='#D5D9DD',linewidth=.4,alpha=.7);ax.set_axisbelow(True)
  for sp in ax.spines.values():sp.set_visible(True);sp.set_edgecolor('black')
  ax.text(.5,-.33,title,transform=ax.transAxes,ha='center',va='top',fontsize=10)
 fig.subplots_adjust(left=.055,right=.995,top=.96,bottom=.29)
 for ext in ['png','pdf','svg']:fig.savefig(OUT/f'f08_dependencies.{ext}',bbox_inches='tight')
 plt.close(fig)
def main():
 data=P/"figure-data/paper/evidence/dependency-benchmark-v15-opt1"
 bench=json.loads((data/"summary.json").read_text(encoding="utf-8"))
 rows=[json.loads(s) for s in (data/"raw.jsonl").read_text(encoding="utf-8").splitlines()]
 figure(bench,rows)
if __name__=="__main__":main()
