"""Editable single-column VCE motivation figure and abbreviated real source.

Preserves the reviewed diagram's scenario and source-branch mapping. Solid
fills and consistent typography replace the preceding raster presentation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, patheffects
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle

MANUSCRIPT = Path(__file__).resolve().parents[1]
WIDTH_PT, HEIGHT_PT = 252.0, 171.0
INK, RED, RED_FILL = "#222222", "#A84040", "#F3D6D6"
LIGHT, MID, DARK = "#F5F5F5", "#E6E6E6", "#D4D4D4"
TITLE_PT, CAPTION_PT, CODE_PT = 7.7, 6.9, 5.7
STYLE = {"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
         "font.size": 6.3, "pdf.fonttype": 42, "ps.fonttype": 42,
         "svg.fonttype": "none", "savefig.facecolor": "white"}
PURPOSE = ("Explain the native completion-record gap and three independent changes affecting response reuse, "
           "linked to the actual crash checkpoint, dependency snapshot miss, and current-ownership refusal "
           "in abbreviated source excerpts.")
ALT_TEXT = ("Panel a, top: the native tool installs configuration and returns success; the manager exits before "
            "recording completion. Query-based recovery inspects the tool again. Panel a, bottom: with saved "
            "success and the same installed content, a reference can change, new recovery residue can appear, "
            "or a later plan can acquire ownership. Panel b links the caller exit to after_native, A and B to "
            "the snapshot-mismatch evidence miss, and C to rejection of a superseded plan. Red marks the crash, "
            "changed state, and affected branches.")

def register_fonts():
    for base in (Path("C:/Windows/Fonts"), Path("/mnt/c/Windows/Fonts")):
        for name in ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf", "consola.ttf"):
            path = base / name
            if path.is_file(): font_manager.fontManager.addfont(str(path))

def label(ax, x, y, text, size=6.3, *, align="center", bold=False,
          color=INK, code=False, group="", bounds=None):
    obj = ax.text(x,y,text,ha=align,va="center",fontsize=size,
                  fontweight="bold" if bold else "normal",color=color,
                  fontfamily="Consolas" if code else "Times New Roman",linespacing=1.0,zorder=7)
    obj._figure_group, obj._allowed_bounds = group, bounds
    return obj

def box(ax,x,y,w,h,fill="white",edge="black",lw=.55,z=2):
    obj=Rectangle((x,y),w,h,facecolor=fill,edgecolor=edge,linewidth=lw,zorder=z)
    ax.add_patch(obj)
    return obj

def line(ax,points,color=INK,lw=.55,dashed=False,z=3):
    return ax.plot([p[0] for p in points],[p[1] for p in points],color=color,linewidth=lw,
                   linestyle=(0,(2,1.5)) if dashed else "-",zorder=z)[0]

def arrow(ax,x1,y1,x2,y2,color=INK,lw=.65,scale=5):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=scale,
                                linewidth=lw,color=color,shrinkA=0,shrinkB=0,zorder=5))

def leader(ax,points):
    obj=line(ax,points,RED,.7,True,8)
    obj.set_path_effects([patheffects.Stroke(linewidth=1.7,foreground="white"),patheffects.Normal()])
    x,y=points[-1]
    arrow(ax,x-2,y,x,y,color=RED,lw=.7,scale=4.2)
    ax.patches[-1].set_zorder(10)

def badge(ax,x,y,text):
    ax.add_patch(Circle((x,y),2.55,facecolor=INK,edgecolor=INK,lw=.3,zorder=9))
    label(ax,x,y+.1,text,5.8,bold=True,color="white",group="badge").set_zorder(11)

def document(ax,x,y):
    w,h,fold=5.2,7.0,1.4
    ax.add_patch(Polygon([(x,y),(x+w-fold,y),(x+w,y+fold),(x+w,y+h),(x,y+h)],
                        closed=True,facecolor="white",edgecolor=INK,lw=.5,zorder=4))
    line(ax,[(x+w-fold,y),(x+w-fold,y+fold),(x+w,y+fold)],lw=.4,z=5)
    for yy in (y+3,y+4.4,y+5.8): line(ax,[(x+1,yy),(x+w-1,yy)],lw=.35,z=5)

def draw_left(ax):
    label(ax,53,7.7,"Completion-record gap",TITLE_PT,bold=True,group="title")
    box(ax,6,15,38,11,MID); box(ax,60,15,43,11,MID)
    label(ax,25,20.5,"Manager",6.8,bold=True)
    label(ax,81.5,20.5,"Native tool",6.8,bold=True)
    line(ax,[(25,26),(25,74)],dashed=True,lw=.5,z=1)
    line(ax,[(81.5,26),(81.5,82)],dashed=True,lw=.5,z=1)
    arrow(ax,25,33,81.5,33); label(ax,53,29,"Deploy",6.3)
    arrow(ax,81.5,42,25,42); label(ax,53,38,"Success",6.3)
    for d in (-1,1): line(ax,[(23,50-2*d),(27,50+2*d)],RED,1.05,z=9)
    label(ax,32,50,"Caller exits",6.5,color=RED,align="left")
    box(ax,5,57,41,9,LIGHT); label(ax,25.5,61.5,"Record pending",6.1)
    box(ax,68,57,27,9,"white",edge="none",lw=0)
    label(ax,81.5,61.5,"Installed",6.1)
    line(ax,[(4,69),(103,69)],"#AAAAAA",.45,True)
    box(ax,6,73,38,10,MID); label(ax,25,78,"Recovery",6.5,bold=True)
    arrow(ax,44,78,81.5,78); label(ax,65.5,73.5,"Query state",5.7)
    label(ax,65.5,83,"Query-based path",5.4)
    line(ax,[(1,88),(105,88)],"black",.55)
    label(ax,53,94,"Saved response validity",TITLE_PT,bold=True,group="title")
    box(ax,5,100,38,9,LIGHT); label(ax,24,104.5,"Saved success",6.1)
    document(ax,49,100.5); label(ax,59,104,"=",7); document(ax,64,100.5)
    label(ax,87.5,104.5,"Same installed\ncontent",5.4)
    rows=[(116,"Reference\nchanged","Ref A","Ref B","A"),
          (129,"New recovery\nresidue","Absent","Present","B"),
          (142,"Ownership\nchanged","Plan P","Plan Q","C")]
    for yy,title,before,after,letter in rows:
        label(ax,5,yy,title,5.9,align="left")
        box(ax,45,yy-4.5,20,9,LIGHT); label(ax,55,yy,before,5.9)
        arrow(ax,67,yy,74,yy,scale=4.2)
        box(ax,76,yy-4.5,21,9,RED_FILL,RED,.65); label(ax,86.5,yy,after,5.9)
        badge(ax,101.3,yy,letter)
    box(ax,4,150,98,10,DARK)
    label(ax,53,155,"Validate dependencies + ownership",5.9)

def source_block(ax,top,bottom,title):
    box(ax,115,top,134,bottom-top)
    box(ax,115,top,134,9,MID)
    label(ax,118,top+4.5,title,6.65,align="left",bold=True)

def source_line(ax,y,text):
    return label(ax,118,y,text,CODE_PT,align="left",code=True,group="code",bounds=(117,15,248,161))

def draw_right(ax):
    label(ax,182,7.7,"Source excerpts (abridged)",TITLE_PT,bold=True,group="title")
    source_block(ax,15,61,"receipt.rs: execution / publication")
    box(ax,117,35.5,130,13,RED_FILL,edge="none",lw=0)
    for yy,text in zip((27,33,39,45,51,57),[
        "let native = run_adapter_with(...).await?;","...",
        "crate::research_fault::checkpoint(",'  "after_native");',"...","receipt_commit(...)?;"]):
        source_line(ax,yy,text)
    source_block(ax,65,119,"witness.rs: completion dependencies")
    box(ax,121,86.5,110,6,RED_FILL,edge="none",lw=0)
    box(ax,117,104.5,114,6,LIGHT,edge="none",lw=0)
    for yy,text in zip((77.5,83.5,89.5,95.5,101.5,107.5),[
        'if ... && ev["snapshot"] !=',"  witness_snapshot(...)? {","  return Ok(None);",
        "}","...","Ok(Some(response))"]): source_line(ax,yy,text)
    badge(ax,236.5,89.5,"A"); badge(ax,244,89.5,"B")
    label(ax,118,115.5,"None → reconcile; Some → reuse",6.1,align="left")
    source_block(ax,123,161,"evolution.rs: current ownership")
    highlight=box(ax,121,139,110,7,RED_FILL,edge="none",lw=0)
    source_line(ax,135.5,"if head != (g, plan.id.clone()) {")
    returned=source_line(ax,142.5,"  return Err(Error::drift(...));")
    source_line(ax,149,"}"); badge(ax,244,142.5,"C")
    label(ax,118,157,"Reject superseded plan",6.2,align="left")
    return highlight,returned

def make_figure():
    register_fonts()
    with plt.rc_context(STYLE):
        fig=plt.figure(figsize=(WIDTH_PT/72,HEIGHT_PT/72),facecolor="white")
        ax=fig.add_axes([0,0,1,1]); ax.set(xlim=(0,WIDTH_PT),ylim=(HEIGHT_PT,0)); ax.axis("off")
        box(ax,1,1,104,161,lw=.65,z=0); box(ax,112,1,139,161,lw=.65,z=0)
        draw_left(ax); highlight,returned=draw_right(ax)
        leader(ax,[(64,50),(108,50),(108,39),(117,39)])
        leader(ax,[(104,129),(108,129),(108,89.5),(120.5,89.5)])
        line(ax,[(104,116),(108,116)],RED,.7,True,9)
        leader(ax,[(104,142),(110,142),(110,142.5),(120.5,142.5)])
        label(ax,53,167,"(a) Gap and evidence validity",CAPTION_PT,group="caption")
        label(ax,182,167,"(b) Source branches for recovery",CAPTION_PT,group="caption")
        fig._semicolon_check=(highlight,returned)
        return fig

def check_layout(fig):
    fig.canvas.draw(); renderer=fig.canvas.get_renderer(); ax=fig.axes[0]; failures=[]
    for text in ax.texts:
        ext=text.get_window_extent(renderer)
        xy=ax.transData.inverted().transform(ext.get_points())
        x0,x1=min(xy[:,0]),max(xy[:,0]); y0,y1=min(xy[:,1]),max(xy[:,1])
        if x0<0 or x1>WIDTH_PT or y0<0 or y1>HEIGHT_PT:
            failures.append({"text":text.get_text(),"kind":"outside canvas"})
        if text._allowed_bounds:
            a,b,c,d=text._allowed_bounds
            if x0<a or x1>c or y0<b or y1>d:
                failures.append({"text":text.get_text(),"kind":"outside source block","x1":x1})
    hl,returned=fig._semicolon_check
    hb,tb=hl.get_window_extent(renderer),returned.get_window_extent(renderer)
    covered=bool(tb.x1+1<=hb.x1 and tb.y0>=hb.y0 and tb.y1<=hb.y1)
    if not covered: failures.append({"text":returned.get_text(),"kind":"highlight clips return"})
    report={"text_bounds_pass":not failures,"semicolon_highlight_pass":covered,"failures":failures}
    if failures: raise ValueError(report)
    return report

def export(output_dir:Path):
    output_dir.mkdir(parents=True,exist_ok=True)
    with plt.rc_context(STYLE):
        fig=make_figure(); report=check_layout(fig)
        for ext in ("pdf","svg","png"):
            opts={"dpi":600} if ext=="png" else {}
            if ext=="pdf": opts["metadata"]={"Title":"VCE Figure 1: completion gap and source branches","CreationDate":None,"ModDate":None}
            if ext=="svg": opts["metadata"]={"Title":"VCE Figure 1","Description":ALT_TEXT,"Date":None}
            fig.savefig(output_dir/f"f01_gap.{ext}",facecolor="white",**opts)
        plt.close(fig)
    report.update({"figure":"f01_gap","purpose":PURPOSE,"alt_text":ALT_TEXT,
        "kind":"conceptual schematic and abridged real source; no measured quantities",
        "revision_date":"2026-10-18","width_inches":WIDTH_PT/72,"height_inches":HEIGHT_PT/72,
        "png_dpi":600,"minimum_label_points":5.4,"code_points":CODE_PT,
        "title_points":TITLE_PT,"subfigure_caption_points":CAPTION_PT,
        "palette":{"light_gray":LIGHT,"middle_gray":MID,"dark_gray":DARK,"red_fill":RED_FILL,"red_stroke":RED},
        "uniform_flat_fills":True,
        "source_files":["native/src/receipt.rs:49-62","native/src/witness.rs:109-117","native/src/evolution.rs:79-80"],
        "omissions":["arguments and intervening statements marked ...","ownership error-message argument marked ..."],
        "matplotlib_version":matplotlib.__version__,"font_family":"Times New Roman (labels) and Consolas (source excerpts)",
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "files":{ext:hashlib.sha256((output_dir/f"f01_gap.{ext}").read_bytes()).hexdigest() for ext in ("pdf","svg","png")}})
    (output_dir/"f01_gap-provenance.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,default=MANUSCRIPT/"figures")
    args=parser.parse_args()
    print(json.dumps(export(args.output_dir),indent=2))
