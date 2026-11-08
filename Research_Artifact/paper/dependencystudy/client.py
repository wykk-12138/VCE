from paper.witnessstudy import client as shared
from paper.witnessstudy.client import ROOT,SOURCE,api_success,corpus,setup,installed,trace,arguments,finish,witnesses
from pathlib import Path
import json,os,subprocess,tempfile,time
BINARY=ROOT/'native/target/release/receiptcoordinator.exe'
SCRATCH=ROOT/'.research-tmp/v15';SCRATCH.mkdir(exist_ok=True)
assert SCRATCH.resolve().is_relative_to(ROOT.resolve())
METHODS=['JournalGuardedScoped','ReceiptCoordinatorV14','ReceiptCoordinatorV15','JournalWitnessV15']
NEW_METHODS=METHODS[2:]
def configure():
 shared.BINARY=BINARY;shared.SCRATCH=SCRATCH
def call(*a,**kw):configure();return shared.call(*a,**kw)
def plan(*a,**kw):configure();return shared.plan(*a,**kw)
def confirm(*a,**kw):configure();return shared.confirm(*a,**kw)
def start(*a,**kw):configure();return shared.start(*a,**kw)
