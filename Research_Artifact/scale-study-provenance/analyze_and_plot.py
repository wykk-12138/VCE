"""Reproducible v17 re-presentation plus independently measured release scale study."""
from pathlib import Path
import csv,hashlib,json,math,sys
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DATA=ROOT/'paper/figure-data/paper'
OUT=HERE/'artifacts'
OUT.mkdir(exist_ok=True)
TOOLS=['claude','codex','grok']
METHODS=['JournalGuardedScoped','JournalPostStatus','ReceiptCoordinatorV15','JournalWitnessV15']
Q,J1,E,JE=METHODS
FULL='ReceiptCoordinatorV14'
NAMES={Q:'J-Q',J1:'J-1',E:'VCE',JE:'J-E',FULL:'Full-tree'}
COLORS={Q:'#70777C',J1:'#A0A7AC',E:'#B65C53',JE:'#B79235',FULL:'#B79235'}
MARKERS={Q:'o',J1:'^',E:'o',JE:'s',FULL:'s'}
SIZES=[0,64,256,512,1024,2048]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def writecsv(p,rr):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def crossed(a,rng,log=False,stat='mean'):
    a=np.asarray(a,float);B,J=a.shape
    bi=rng.integers(B,size=(4000,B));ji=rng.integers(J,size=(4000,J))
    res=a[bi[:,:,None],ji[:,None,:]].reshape(4000,-1)
    values=np.median(res,axis=1) if stat=='median' else res.mean(axis=1)
    point=np.median(a) if stat=='median' else a.mean()
    if log:values=np.exp(values);point=np.exp(point)
    return {'value':float(point),'ci95':[float(x) for x in np.quantile(values,[.025,.975])],
            'projects':J,'batches':B,'cells':B*J}

def analyze():
    facts=read(DATA/'results_v17/facts.json');raw=rows(DATA/'results_v17/timing-rows.jsonl')
    assert len(raw)==2448 and all(r['pass'] and not r['warmup'] for r in raw)
    projects=sorted({r['repository'] for r in raw});batches=sorted({r['batch'] for r in raw})
    rng=np.random.default_rng(18951);primary={};flat=[]
    for tool,scenario,life,noise in sorted({(r['tool'],r['scenario'],r['lifecycle'],r['noise']) for r in raw}):
        key=f'{tool}/{scenario}/{life}/{noise}'
        pool=[r for r in raw if (r['tool'],r['scenario'],r['lifecycle'],r['noise'])==(tool,scenario,life,noise)]
        lu={(r['batch'],r['repository'],r['method']):r for r in pool};assert len(lu)==144
        primary[key]={}
        for m in METHODS:
            primary[key][m]={}
            for metric in ['wall_ns','episode_ns']:
                if m==Q:est={'value':1.,'ci95':[1.,1.],'projects':12,'batches':3,'cells':36}
                elif m==E:
                    existing=facts['comparisons'][key]['paired'][Q][metric]
                    est={'value':existing['ratio'],'ci95':existing['ci95'],'projects':12,'batches':3,'cells':36}
                else:
                    a=[[math.log(lu[b,p,m][metric]/lu[b,p,Q][metric]) for p in projects] for b in batches]
                    est=crossed(a,rng,log=True)
                est['median_ms']=float(np.median([r[metric]/1e6 for r in pool if r['method']==m]))
                primary[key][m][metric]=est
                flat.append({'condition':key,'method':m,'metric':metric,'ratio_to_JQ':est['value'],
                    'low':est['ci95'][0],'high':est['ci95'][1],'median_ms':est['median_ms']})
    save(OUT/'primary-comparisons.json',primary);writecsv(OUT/'primary-comparisons.csv',flat)
    scale=[];provenance={}
    for b in ['b1','b2','b3']:
        folder=DATA/'evidence/scale-v18'/b
        ss=read(folder/'summary.json');rr=rows(folder/'raw.jsonl');spec=read(folder/'spec.json')
        assert len(rr)==468 and ss['scored']==432 and all(r['pass'] for r in rr)
        assert spec['binary_sha256']=='b1826c1f2f917af4765b55e7ff52b65926e031df9eeb84700c0665ed74e3a36f'
        scale += [r for r in rr if not r['warmup']]
        provenance[b]={k:sha(folder/k) for k in ['raw.jsonl','spec.json','summary.json']}
    assert len(scale)==1296
    lu={(r['batch'],r['repository'],r['shape'],r['noise'],r['method']):r for r in scale}
    assert len(lu)==1296
    rng=np.random.default_rng(18952);sg={};sr=[]
    for shape in ['nested','flat']:
        sg[shape]={}
        for n in SIZES:
            sg[shape][str(n)]={}
            for m in [Q,FULL,E]:
                pool=[lu[b,p,shape,n,m] for b in batches for p in projects]
                rec={}
                for metric in ['wall_ms','validation_ms','evidence_kib']:
                    def value(r):return r['wall_ns']/1e6 if metric=='wall_ms' else r['exclusive_ns']['Validation']/1e6 if metric=='validation_ms' else r['evidence_bytes']/1024
                    a=[[value(lu[b,p,shape,n,m]) for p in projects] for b in batches]
                    rec[metric]=crossed(a,rng,stat='median')
                    rec[metric]['observations']=[value(r) for r in pool]
                if m!=Q:
                    for control in [Q,FULL]:
                        a=[[math.log(lu[b,p,shape,n,m]['wall_ns']/lu[b,p,shape,n,control]['wall_ns']) for p in projects] for b in batches]
                        rec['ratio_to_'+control]=crossed(a,rng,log=True)
                assert all(len(r['commands'])==(2 if m==Q else 0) for r in pool)
                sg[shape][str(n)][m]=rec
                sr.append({'shape':shape,'ordinary_files':n,'method':m,
                    **{metric:rec[metric]['value'] for metric in ['wall_ms','validation_ms','evidence_kib']},
                    'wall_ci_low':rec['wall_ms']['ci95'][0],'wall_ci_high':rec['wall_ms']['ci95'][1],
                    'pairs':36,'projects':12,'batches':3})
    save(OUT/'scale-summary.json',{'groups':sg,'provenance':provenance,'scored':1296,'warmups':108,
        'bootstrap':'4000 independent crossed project/batch resamples; medians for absolute metrics, geometric means for paired ratios.'})
    writecsv(OUT/'scale-summary.csv',sr)
    save(OUT/'analysis-provenance.json',{'primary_sha256':sha(DATA/'results_v17/timing-rows.jsonl'),
        'facts_sha256':sha(DATA/'results_v17/facts.json'),'new_scale':provenance,
        'no_direction_based_exclusions':True,'primary_VCE_estimates_preserved':True,
        'new_estimates':'J-1/J-Q, J-E/J-Q from frozen paired records; scale estimates from separate release study.',
        'seeds':{'primary':18951,'scale':18952},'bootstrap_samples':4000})
    return facts,primary,sg

def plot():
    # Reuse the installed, pinned local plotting bundle, isolated from the app.
    deps=Path('D:/Users/star_/Documents/ChatGPT/AI4paper/VCE-YuJiang-revision-v3/review-cache/python-deps')
    sys.path.insert(0,str(deps))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib import font_manager
    from matplotlib.text import Text
    from PIL import Image
    fp=Path('C:/Windows/Fonts/times.ttf')
    if fp.exists():font_manager.fontManager.addfont(str(fp))
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],
        'font.size':8.5,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
        'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,
        'xtick.direction':'out','ytick.direction':'out','xtick.major.size':3,'ytick.major.size':3,
        'pdf.fonttype':42,'svg.fonttype':'none','mathtext.fontset':'stix','savefig.facecolor':'white'})
    facts=read(DATA/'results_v17/facts.json');primary=read(OUT/'primary-comparisons.json');scale=read(OUT/'scale-summary.json')['groups']
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True);reports=[]
    def frame(ax):ax.set_axisbelow(True);ax.grid(axis='y',color='#E5E5E5',lw=.4)
    def export(fig,stem,purpose):
        fig.canvas.draw();renderer=fig.canvas.get_renderer();bad=[]
        for artist in fig.findobj(Text):
            if not artist.get_visible() or not artist.get_text().strip():continue
            bb=artist.get_window_extent(renderer)
            if bb.x0<-.5 or bb.y0<-.5 or bb.x1>fig.bbox.width+.5 or bb.y1>fig.bbox.height+.5:bad.append(artist.get_text())
        if bad:raise RuntimeError((stem,'text exceeds canvas',bad))
        for ext in ['pdf','svg']:fig.savefig(figdir/(stem+'.'+ext))
        fig.savefig(figdir/(stem+'.png'),dpi=240)
        preview=figdir/(stem+'-preview.png');fig.savefig(preview,dpi=130)
        im=Image.open(preview);im.thumbnail((1100,850));im.save(preview);im.convert('L').save(figdir/(stem+'-gray.png'))
        reports.append({'name':stem,'purpose':purpose,'width_inches':fig.get_figwidth(),'height_inches':fig.get_figheight(),
            'text_bounds_pass':True,'sha256_pdf':sha(figdir/(stem+'.pdf'))})
        plt.close(fig)
    # A: common comparative grammar for recovery and full-episode benefits.
    fig,axs=plt.subplots(1,2,figsize=(7.12,2.85));fig.subplots_adjust(left=.15,right=.97,bottom=.19,top=.78,wspace=.33)
    labels=[t.title()+' / '+life for t in TOOLS for life in ['cold','warm']]
    for j,(ax,metric,title) in enumerate(zip(axs,['wall_ns','episode_ns'],['(a) Recovery confirmation','(b) Complete interrupted episode'])):
        for i,(t,life) in enumerate((t,l) for t in TOOLS for l in ['cold','warm']):
            for m,off in [(E,-.11),(JE,.11)]:
                r=primary[f'{t}/recovery/{life}/0'][m][metric]
                ax.errorbar(r['value'],i+off,xerr=[[r['value']-r['ci95'][0]],[r['ci95'][1]-r['value']]],fmt=MARKERS[m],
                    color=COLORS[m],ms=4,capsize=2,lw=1)
        ax.axvline(1,color=COLORS[Q],ls='--',lw=.8);ax.set_yticks(range(6),labels if j==0 else [])
        ax.set_ylim(5.5,-.5);ax.set_xlabel('Time relative to J-Q (lower is better)');ax.set_title(title,pad=9,fontweight='bold')
        ax.grid(axis='y',color='#E5E5E5',lw=.4);ax.set_axisbelow(True)
        if j==0:
            ax.set_xscale('log');ax.set_xlim(.035,1.15);ax.set_xticks([.05,.1,.2,.5,1],['0.05','0.1','0.2','0.5','1'])
        else:ax.set_xlim(.61,1.04);ax.set_xticks([.65,.75,.85,1],['0.65','0.75','0.85','1'])
    handles=[Line2D([],[],marker=MARKERS[m],color=COLORS[m],ls='',label=NAMES[m]) for m in [E,JE]]
    handles += [Line2D([],[],color=COLORS[Q],ls='--',label='J-Q reference')]
    fig.legend(handles=handles,loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.56,1.0))
    export(fig,'f05_recovery_effects','Paired recovery and complete-episode effects with 95% crossed intervals; historical main experiment.')
    # B: four execution paths make the role of each control visible.
    fig=plt.figure(figsize=(7.12,4.55));grid=fig.add_gridspec(2,3,height_ratios=[1,1.03],left=.09,right=.985,bottom=.13,top=.86,hspace=.67,wspace=.26)
    scenarios=['normal','recovery','fallback','completed_retry'];xlabels=['Fresh','Recovery\nhit','Evidence\nmiss','Valid\nrepeat']
    for k,t in enumerate(TOOLS):
        ax=fig.add_subplot(grid[0,k]);frame(ax)
        for m,off in [(J1,-.18),(E,0),(JE,.18)]:
            rr=[primary[f'{t}/{s}/cold/0'][m]['wall_ns'] for s in scenarios]
            ax.errorbar(np.arange(4)+off,[r['value'] for r in rr],
                yerr=[[r['value']-r['ci95'][0] for r in rr],[r['ci95'][1]-r['value'] for r in rr]],
                fmt=MARKERS[m],color=COLORS[m],ms=4,capsize=2,lw=.8)
        ax.axhline(1,color=COLORS[Q],ls='--',lw=.8);ax.set_yscale('log');ax.set_ylim(.035,1.6)
        ax.set_yticks([.05,.1,.2,.5,1],['0.05','0.1','0.2','0.5','1'] if k==0 else [])
        ax.set_xticks(range(4),xlabels);ax.tick_params(axis='x',labelsize=7)
        ax.set_title(f'({chr(97+k)}) {t.title()}',fontweight='bold',pad=7)
        if k==0:ax.set_ylabel('Confirmation time / J-Q')
    handles=[Line2D([],[],marker=MARKERS[m],color=COLORS[m],ls='',label=NAMES[m]) for m in [J1,E,JE]]
    handles.append(Line2D([],[],color=COLORS[Q],ls='--',label='J-Q reference'))
    fig.legend(handles=handles,loc='upper center',ncol=4,frameon=False,bbox_to_anchor=(.54,1.0))
    ax=fig.add_subplot(grid[1,:]);frame(ax)
    xx=np.array([0,1,2,4,5,6,8,9,10]);bottom=np.zeros(9)
    ckeys=['Native','Validation','Readback','Publication','Other']
    component_colors=['#6E7478','#B65C53','#D6C49A','#B5BABE','#E6E6E6']
    for key,color,hatch in zip(ckeys,component_colors,['','////','','..','']):
        vals=[facts['breakdown'][f'{t}/{m}'][key] for t in TOOLS for m in [Q,E,JE]]
        ax.bar(xx,vals,bottom=bottom,width=.7,label=key,color=color,
            edgecolor='#454545' if hatch else 'white',linewidth=.25,hatch=hatch);bottom+=vals
    ax.set_xticks(xx,[NAMES[m] for t in TOOLS for m in [Q,E,JE]]);ax.set_ylabel('Mean recovery work (ms)');ax.set_ylim(0,max(bottom)*1.06)
    ax.set_title('(d) Where recovery time is spent',fontweight='bold',loc='left',pad=26)
    ax.legend(loc='lower center',bbox_to_anchor=(.6,1.03),ncol=5,frameon=False,fontsize=7.2,columnspacing=.9)
    for x,t in zip([1,5,9],TOOLS):ax.text(x,-.28,t.title(),transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=8.5)
    export(fig,'f06_paths_and_work','Four matched execution paths plus exclusive mean recovery components; all unfavorable paths retained.')
    # C: six measured x values in each directory shape, same frozen release.
    fig,axs=plt.subplots(2,2,figsize=(7.12,4.55),sharex=True);fig.subplots_adjust(left=.105,right=.985,bottom=.15,top=.84,hspace=.3,wspace=.28)
    for col,shape in enumerate(['nested','flat']):
        for m in [Q,FULL,E]:
            rr=[scale[shape][str(n)][m]['wall_ms'] for n in SIZES]
            axs[0,col].errorbar(SIZES,[r['value'] for r in rr],yerr=[[r['value']-r['ci95'][0] for r in rr],[r['ci95'][1]-r['value'] for r in rr]],
                color=COLORS[m],marker=MARKERS[m],ms=3.6,capsize=2,lw=1.1,ls='--' if m==Q else '-')
        for m in [FULL,E]:
            rr=[scale[shape][str(n)][m]['evidence_kib'] for n in SIZES]
            axs[1,col].errorbar(SIZES,[r['value'] for r in rr],yerr=[[r['value']-r['ci95'][0] for r in rr],[r['ci95'][1]-r['value'] for r in rr]],
                color=COLORS[m],marker=MARKERS[m],ms=3.6,capsize=2,lw=1.1)
        axs[0,col].set_title(f'({chr(97+col)}) '+('Unrelated subdirectory' if shape=='nested' else 'Files at the project root'),fontweight='bold',pad=9)
        axs[1,col].set_xlabel('Additional ordinary files')
        for row in [0,1]:
            ax=axs[row,col];frame(ax);ax.set_xscale('symlog',linthresh=64,linscale=1,base=2)
            ax.set_xticks(SIZES,['0','64','256','512','1,024','2,048']);ax.tick_params(axis='x',labelsize=7)
            ax.set_xlim(-8,2500);ax.set_ylim(bottom=0)
    axs[0,0].set_ylabel('Recovery median (ms)');axs[1,0].set_ylabel('Evidence median (KiB)')
    for row in [0,1]:
        top=max(axs[row,0].get_ylim()[1],axs[row,1].get_ylim()[1]);axs[row,0].set_ylim(0,top);axs[row,1].set_ylim(0,top)
    handles=[Line2D([],[],marker=MARKERS[m],color=COLORS[m],ls='--' if m==Q else '-',label='Scoped (VCE)' if m==E else NAMES[m]) for m in [Q,FULL,E]]
    fig.legend(handles=handles,loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.55,.995))
    fig.text(.55,.035,'Measured scale study: 12 projects × 3 batches; 95% crossed intervals',ha='center',fontsize=8)
    export(fig,'f07_scale_layout','Independent release-scale study; 6 measured sizes, 2 layouts, 3 methods, all 1296 scored records.')
    # D: explicitly modeled, with no interpolation masquerading as new trials.
    fig,axs=plt.subplots(1,2,figsize=(7.12,2.85));fig.subplots_adjust(left=.1,right=.98,bottom=.22,top=.77,wspace=.31)
    tc=['#70777C','#B65C53','#B79235'];styles=['-','--',':']
    for t,c,ls in zip(TOOLS,tc,styles):
        d=facts['costs'][t];h=np.linspace(0,1,501);df=h*d['hit_ms']+(1-h)*d['miss_ms']
        p=np.where(df<0,d['normal_ms']/(d['normal_ms']-df),np.nan)
        axs[0].plot(h,100*p,color=c,ls=ls,label=t.title(),lw=1.4)
        r=np.linspace(0,.25,251);axs[1].plot(r,d['normal_ms']+r*d['repeat_ms'],color=c,ls=ls,lw=1.4)
        cross=d['repeat_break_even'];axs[1].plot(cross,0,'o',color=c,ms=4)
    for ax in axs:frame(ax)
    axs[0].set(xlabel='Valid-evidence fraction h on recovery',ylabel='Break-even interruption p* (%)',xlim=(0,1),ylim=(0,100))
    axs[1].axhline(0,color='#454545',lw=.75);axs[1].set(xlabel='Additional valid confirmations r',ylabel='Mean cost difference (ms)',xlim=(0,.25))
    axs[0].set_title('(a) Recovering the initial investment',fontweight='bold',pad=9)
    axs[1].set_title('(b) Amortization without interruption',fontweight='bold',pad=9)
    fig.legend(*axs[0].get_legend_handles_labels(),loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.54,.995))
    fig.text(.55,.025,'Model from measured path costs: (a) r = 0; (b) p = 0. Lower cost lies below zero.',ha='center',fontsize=7.8)
    export(fig,'f08_amortization','Modeled workload thresholds from unchanged measured v17 arithmetic means; not new mixed-workload measurements.')
    save(OUT/'figure-manifest.json',reports)
    print('PLOTS',json.dumps(reports),flush=True)

if __name__=='__main__':
    if '--plot-only' not in sys.argv:analyze()
    if '--analyze-only' not in sys.argv:plot()
