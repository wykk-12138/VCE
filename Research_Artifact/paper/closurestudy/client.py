from paper.witnessstudy import client as shared
from paper.witnessstudy.client import ROOT,SOURCE,api_success,corpus,setup,installed,trace,arguments,finish,witnesses
from pathlib import Path
import json,os,subprocess,tempfile,time
BINARY=ROOT/'native/target/release/receiptcoordinator.exe'
SCRATCH=ROOT/'.research-tmp/closure-v16';SCRATCH.mkdir(parents=True,exist_ok=True)
METHODS=['JournalGuardedScoped','JournalPostStatus','ReceiptCoordinatorV15','JournalWitnessV15']

def configure():shared.BINARY=BINARY;shared.SCRATCH=SCRATCH
def call(root,tool,command,**kw):
 configure();kw['extra']={'RECEIPTCOORDINATOR_COMPONENT_PROFILE':str(root/'components.jsonl'),**kw.get('extra',{})}
 return shared.call(root,tool,command,**kw)
def plan(root,tool,method,**kw):
 r=call(root,tool,'plan',method=method,**kw);p=r.get('response',{}).get('data',{})
 assert p.get('plan',{}).get('envelope',{}).get('ok'),r
 return p
def confirm(root,tool,method,p,**kw):return call(root,tool,'confirm',**arguments(method,p,**kw))
def logs(root,name):
 p=root/name;return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
