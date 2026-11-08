"""V14 wrapper with explicit binary and isolated temp root."""
from paper.evolutionstudy import client as old
from paper.evolutionstudy.client import ROOT,SOURCE,api_success,corpus,setup,installed,trace,arguments,finish
from pathlib import Path
import json,os,subprocess,tempfile,time
BINARY=ROOT/'native/target/release/receiptcoordinator.exe'
SCRATCH=ROOT/'.research-tmp/witness-v14'
SCRATCH.mkdir(parents=True,exist_ok=True)
assert SCRATCH.resolve().is_relative_to(ROOT.resolve())
METHODS=['ReceiptCoordinatorV13','JournalGuardedScoped','ReceiptCoordinatorV14','JournalWitnessScoped']
NEW_METHODS=METHODS[2:]
def call(root,tool,command,**kwargs):
 extra={'TMP':str(SCRATCH),'TEMP':str(SCRATCH),'WITNESS_TRACE':str(root/'witness_trace.jsonl'),'EVOLUTION_GATE_EVENTS':str(root/'gate_events.jsonl'),**kwargs.pop('extra',{})}
 return old.call(root,tool,command,binary=BINARY,extra=extra,**kwargs)
def start(root,tool,command,**kwargs):
 extra={'TMP':str(SCRATCH),'TEMP':str(SCRATCH),'WITNESS_TRACE':str(root/'witness_trace.jsonl'),'EVOLUTION_GATE_EVENTS':str(root/'gate_events.jsonl'),**kwargs.pop('extra',{})}
 return old.start(root,tool,command,binary=BINARY,extra=extra,**kwargs)
def plan(root,tool,method,**kwargs):
 r=call(root,tool,'plan',method=method,**kwargs);d=r.get('response',{}).get('data',{})
 assert d.get('plan',{}).get('envelope',{}).get('ok'),r
 return d
def confirm(root,tool,method,p,**kwargs):return call(root,tool,'confirm',**arguments(method,p,**kwargs))
def witnesses(root):
 p=root/'witness_trace.jsonl';return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
