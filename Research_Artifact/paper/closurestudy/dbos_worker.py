"""One unchanged author DBOS workflow for all endpoint implementations."""
import json,os,sys,time
from pathlib import Path
from .client import call

def main(data):
 from dbos import DBOS,SetWorkflowID
 @DBOS.step()
 def endpoint(req):
  method=req['endpoint']
  result=call(Path(req['root']),req['tool'],'confirm',method=method,operation_id=req['operation_id'],prompt_id=req['prompt_id'],
   retry=method=='OriginalReplan',fault=os.environ.get('CLOSURE_NATIVE_FAULT'))
  if result['exit_code']==86 or os.environ.get('CLOSURE_ENGINE_FAULT')=='after_external':os._exit(86)
  return result
 @DBOS.workflow()
 def deploy(req):
  result=endpoint(req)
  if os.environ.get('CLOSURE_ENGINE_FAULT')=='after_step':os._exit(86)
  return result
 root=Path(data['root'])
 DBOS(config={'name':'receiptcoordinator-closure','application_version':'closure-v16','executor_id':'isolated-worker',
  'system_database_url':'sqlite:///'+(root/'dbos.sqlite').as_posix(),'enable_otlp':False,'log_level':'ERROR'})
 DBOS.launch();started=time.perf_counter_ns()
 with SetWorkflowID(data['operation_id']):result=deploy(data)
 print(json.dumps({'result':result,'workflow_ns':time.perf_counter_ns()-started}),flush=True);DBOS.destroy()
if __name__=='__main__':main(json.loads(sys.stdin.readline()))
