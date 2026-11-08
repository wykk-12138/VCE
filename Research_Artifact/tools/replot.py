"""Regenerate all 10 figures into a separate output directory."""
import argparse, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,default=ROOT/'recomputed/figures')
a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'manuscript'))
spec=importlib.util.spec_from_file_location('delivery_figures',ROOT/'manuscript/make_figures.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.OUT=a.out
from figure_sources import dependency_figure
dependency_figure.OUT=a.out
module.diagrams();module.experiments();module.mixture()
(a.out/'figure_manifest.json').write_text(json.dumps({'figures':module.MANIFEST,'source_sha256':module.SOURCES},indent=2)+'\n',encoding='utf-8')
assert len(module.MANIFEST)==10
print(json.dumps({'figures':len(module.MANIFEST),'output':str(a.out),'frozen_inputs_modified':False}))
