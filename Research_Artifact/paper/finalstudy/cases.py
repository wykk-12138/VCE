"""Isolated public-byte fixtures, real Rust calls and independent database oracle."""
import hashlib
import json
import os
import sqlite3
import subprocess
import time
import tomllib
from contextlib import closing
from pathlib import Path
from .prepare import ROOT,SOURCE

BINARY=ROOT/'native/target/release/receiptcoordinator.exe'
METHODS=['OriginalConfirm','OriginalReplan','VerifiedCoordinator','NativeJournal','ReceiptCoordinator',
         'A_NoAtomic','A_Unkeyed','A_NoOutcome','A_Replay']
SCENARIOS=['normal','after_native','after_execute_record','after_activation_record','after_plan_commit',
           'completed_retry','external_instruction','external_context','source_changed','before_native',
           'double_exit','corrupt_receipt','reference_changed']


def normalized(raw):return raw.decode('utf-8').replace('\r\n','\n').encode('utf-8')


def corpus(split):
    version='v5' if split=='confirmation' else 'v4'
    manifest=json.loads((ROOT/f'paper/evidence/public_corpus_{version}.json').read_text(encoding='utf-8'))
    result=[]
    for project in manifest['projects']:
        if project.get('tree_truncated') or not project.get('files'):continue
        inputs=[f for f in project['files'] if f['kind']=='instruction'][:2]
        for row in inputs:result.append({'repository':project['repository'],'commit':project['commit'],'split':split,
                                       'payload':row,'project_files':project['files']})
    return result


def setup(root,item,tool):
    root=Path(root);home=root/'home';project=root/'project'
    for name in ['.grok','.codex','.claude','AppData/Roaming','AppData/Local']:(home/name).mkdir(parents=True,exist_ok=True)
    project.mkdir()
    copied={}
    for source in item['project_files']:
        path=ROOT/source['local_path'];raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Public corpus source changed')
        target=project/source['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        copied[source['path']]=raw
    desired=(ROOT/item['payload']['local_path']).read_bytes()
    (root/'candidate.md').write_bytes(desired)
    (home/'.grok/config.toml').write_bytes(b'model = "fixture"\n')
    (home/'.codex/config.toml').write_bytes(b'model = "fixture"\n')
    if not (project/'CLAUDE.md').exists():(project/'CLAUDE.md').write_bytes(b'# Generated context for isolated deployment\n')
    (root/'outside.txt').write_bytes(b'UNMANAGED OUTSIDE CONTEXT\n')
    return {'desired':desired,'copied':copied,'memory_before':(project/'CLAUDE.md').read_bytes()}


def installed(root,tool):
    return Path(root)/{'claude':'project/.claude/receiptcoordinator/claude-project-rules.md',
                       'codex':'home/.codex/gpt-unrestricted.md','grok':'home/.grok/rules/99-receiptcoordinator.md'}[tool]


def call(root,tool,command,**kwargs):
    root=Path(root)
    fault=kwargs.pop('fault',None)
    corrupt=kwargs.pop('corrupt',None)
    native_fault=kwargs.pop('native_fault',None)
    test_environment=kwargs.pop('test_environment',{})
    env={**os.environ,'RECEIPTCOORDINATOR_RESEARCH_TRACE':str(root/'adapter_calls.jsonl'),
         'RECEIPTCOORDINATOR_RESEARCH_FAULT':fault or '', 'PYTHONIOENCODING':'utf-8','CUDA_VISIBLE_DEVICES':'','HIP_VISIBLE_DEVICES':''}
    # Exclude Windows Store's non-installed python3 alias in this child's PATH;
    # the unchanged resolver then finds the actual Python installation.
    env['PATH']=os.pathsep.join(entry for entry in os.environ['PATH'].split(os.pathsep) if 'windowsapps' not in entry.lower())
    # The compiled original adapter uses explicit opts.home; process-local env
    # additionally isolates paths read by third-party CLI dependencies.
    env.update({'HOME':str(root/'home'),'USERPROFILE':str(root/'home'),
                'APPDATA':str(root/'home/AppData/Roaming'),'LOCALAPPDATA':str(root/'home/AppData/Local')})
    for key in ['GROK_RECEIPTCOORDINATOR_FAULT_INJECT','CLAUDE_RECEIPTCOORDINATOR_FAULT_INJECT','CODEX_RECEIPTCOORDINATOR_FAULT_INJECT']:
        env.pop(key,None)
    env.pop('RECEIPTCOORDINATOR_RESEARCH_CORRUPT',None)
    if corrupt:env['RECEIPTCOORDINATOR_RESEARCH_CORRUPT']=str(corrupt)
    if native_fault:env['GROK_RECEIPTCOORDINATOR_FAULT_INJECT']=native_fault
    env['RECEIPTCOORDINATOR_RESEARCH_PROFILE']=str(root/'adapter_profile.jsonl')
    env.update(test_environment)
    request={'command':command,'root':str(root),'source_root':str(SOURCE),'tool':tool,**kwargs}
    start=time.perf_counter_ns()
    child=subprocess.run([str(BINARY)],input=json.dumps(request)+'\n',cwd=ROOT,env=env,capture_output=True,text=True,
                         encoding='utf-8',timeout=90)
    elapsed=time.perf_counter_ns()-start
    if child.returncode==86 and fault:return {'exit_code':86,'fault':fault,'wall_ns':elapsed}
    if child.returncode!=0:raise RuntimeError(f'Rust child failed: {child.returncode}: {child.stderr}')
    try:response=json.loads(child.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):raise RuntimeError(f'Invalid Rust response: {child.stdout}: {child.stderr}')
    return {'exit_code':child.returncode,'wall_ns':elapsed,'response':response}


def api_success(result):
    response=result.get('response',{})
    return response.get('ok',False) and response.get('data',{}).get('result',{}).get('envelope',{}).get('ok',False)


def trace(root):
    path=Path(root)/'adapter_calls.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def crash_snapshot(root,tool,desired,plan_id):
    root=Path(root);body=installed(root,tool)
    with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
        operations=db.execute("SELECT id,status,parent_id FROM operations WHERE kind='activate'").fetchall()
        activations=db.execute('SELECT prompt_id,status,operation_id FROM activations').fetchall()
        states=db.execute('SELECT status,last_operation_id FROM tool_state').fetchall()
        plan=db.execute('SELECT status FROM operations WHERE id=?',(plan_id,)).fetchone()
    return {'disk_matches':body.exists() and normalized(body.read_bytes())==normalized(desired),
            'executions':operations,'activations':activations,'tool_states':states,'plan_status':plan[0]}


def oracle(root,tool,fixture,prompt_id,plan_id,method,result,external=None,approved=True):
    root=Path(root);body=installed(root,tool);expected=normalized(fixture['desired']);desired_sha=hashlib.sha256(fixture['desired']).hexdigest()
    actual=body.read_bytes() if body.exists() else None
    disk_ok=actual is not None and normalized(actual)==expected
    if tool=='claude':
        memory=(root/'project/CLAUDE.md').read_text(encoding='utf-8')
        reference=any(line.strip()=='@.claude/receiptcoordinator/claude-project-rules.md' for line in memory.splitlines())
    elif tool=='codex':
        config=tomllib.loads((root/'home/.codex/config.toml').read_text(encoding='utf-8'))
        value=config.get('model_instructions_file','')
        destination=Path(value) if Path(value).is_absolute() else root/'home/.codex'/value
        reference=destination.resolve()==body.resolve()
    else:reference=(root/'home/.grok/.grok-receiptcoordinator-manifest.json').is_file()
    native=call(root,tool,'status')
    envelope=native.get('response',{}).get('data',{}).get('envelope',{})
    status_ok=envelope.get('ok') is True and envelope.get('status')=='active' and not envelope.get('recoveryRequired')
    with closing(sqlite3.connect(root/'switch/receiptcoordinator.db')) as db:
        db.row_factory=sqlite3.Row
        operations=[dict(row) for row in db.execute("SELECT * FROM operations WHERE kind='activate'")]
        activations=[dict(row) for row in db.execute('SELECT * FROM activations')]
        states=[dict(row) for row in db.execute('SELECT * FROM tool_state')]
        plan=dict(db.execute('SELECT * FROM operations WHERE id=?',(plan_id,)).fetchone())
    successes=[row for row in operations if row['status']=='succeeded']
    matching=[row for row in successes if row['prompt_id']==prompt_id]
    active=next((row for row in activations if row['prompt_id']==prompt_id and row['status']=='active'),None)
    related=next((row for row in matching if active and row['id']==active['operation_id']),None)
    recorded=bool(related and active['fingerprint']==desired_sha and
                  any(row['status']=='active' and row['last_operation_id']==related['id'] and row['fingerprint']==desired_sha for row in states))
    # A fresh preview on retry is still one requested logical deployment episode.
    unique=len(matching)==1
    context={}
    for name,raw in fixture['copied'].items():
        path=root/'project'/name
        context[name]=(raw in path.read_bytes()) if name=='CLAUDE.md' else path.exists() and path.read_bytes()==raw
    context['original_project_memory']=fixture['memory_before'] in (root/'project/CLAUDE.md').read_bytes()
    context['outside']=(root/'outside.txt').read_bytes()==b'UNMANAGED OUTSIDE CONTEXT\n'
    for relative,raw in (external or {}).items():context['external:'+relative]=(root/relative).read_bytes()==raw
    preserved=all(context.values())
    coherent=bool(approved and disk_ok and reference and status_ok and recorded and preserved)
    success=api_success(result)
    return {'disk_correct':disk_ok,'native_reference_correct':reference,'native_status_aligned':status_ok,
            'manager_records_coherent':recorded,'state_coherent':coherent,'logical_completion_unique':unique,
            'successful_execute_records':len(matching),'duplicate_execute_records':max(0,len(matching)-1),
            'external_preserved':preserved,'preservation_checks':context,'api_success':success,
            'correct_api_completion':success and coherent,'unique_api_completion':success and coherent and unique,
            'false_success':success and not coherent,'original_plan_status':plan['status'],
            'native_status_response':native,'activation_records':activations,
            'execute_records':[{'id':row['id'],'status':row['status'],'parent_id':row['parent_id']} for row in operations]}


def execute(root,item,tool,method,scenario):
    root=Path(root);fixture=setup(root,item,tool)
    started=time.perf_counter_ns();plan=call(root,tool,'plan')
    data=plan.get('response',{}).get('data',{})
    if not data.get('plan',{}).get('envelope',{}).get('ok'):
        return {'repository':item['repository'],'payload':item['payload']['path'],'tool':tool,'method':method,'scenario':scenario,
                'supported':False,'reason':'original preview refused','plan_response':plan,'duration_ns':time.perf_counter_ns()-started,
                'actual_hard_exits':0,'contract_pass':False,'adapter_calls':trace(root)}
    op=data['plan']['operationId'];prompt=data['prompt_id'];external={};exits=[];initial=None;snapshot=None
    arguments={'operation_id':op,'prompt_id':prompt,'method':method}
    second=None
    if scenario.startswith('after_') or scenario in {'external_instruction','external_context','before_native','double_exit','reference_changed'}:
        fault=scenario if scenario.startswith('after_') or scenario=='before_native' else 'after_native'
        initial=call(root,tool,'confirm',**arguments,fault=fault)
        if initial['exit_code']!=86:raise RuntimeError(f'Fault {fault} was not reached: {initial}')
        exits.append(initial);retry=True
        snapshot=crash_snapshot(root,tool,fixture['desired'],op)
        if scenario=='external_instruction':
            path=installed(root,tool);raw=b'EXTERNAL USER INSTRUCTION AFTER CRASH\n';path.write_bytes(raw)
            external[path.relative_to(root).as_posix()]=raw
        elif scenario=='external_context':
            path=root/'project/CLAUDE.md' if tool=='claude' else root/'outside.txt'
            raw=path.read_bytes()+b'\nEXTERNAL UNRELATED CONTEXT\n';path.write_bytes(raw)
            external[path.relative_to(root).as_posix()]=raw
        elif scenario=='reference_changed':
            path=root/'project/CLAUDE.md' if tool=='claude' else root/'home'/('.codex/config.toml' if tool=='codex' else '.grok/.grok-receiptcoordinator-manifest.json')
            raw=(b'# EXTERNAL REPLACED REFERENCE\n' if tool=='claude' else b'{"external": true}\n' if tool=='grok' else b'model = "externally-changed"\nmodel_instructions_file = "user-owned.md"\n')
            path.write_bytes(raw);external[path.relative_to(root).as_posix()]=raw
            if tool=='claude':fixture['memory_before']=raw;fixture['copied'].pop('CLAUDE.md',None)
        elif scenario=='double_exit':
            second=call(root,tool,'confirm',**arguments,retry=True,fault='after_execute_record')
            if second['exit_code']==86:exits.append(second)
    elif scenario=='completed_retry':
        initial=call(root,tool,'confirm',**arguments);retry=True
    elif scenario=='source_changed':
        initial=call(root,tool,'change_source',prompt_id=prompt);retry=False
    else:retry=False
    before=trace(root);resume_started=time.perf_counter_ns()
    result=call(root,tool,'confirm',**arguments,retry=retry,
                corrupt=installed(root,tool) if scenario=='corrupt_receipt' else None)
    if scenario=='corrupt_receipt':external[installed(root,tool).relative_to(root).as_posix()]=b'EXTERNAL CHANGE BEFORE OUTCOME VALIDATION\n'
    measured=time.perf_counter_ns()-resume_started if scenario!='normal' else time.perf_counter_ns()-started
    actions=trace(root);after_count=actions[len(before):]
    profile_path=root/'adapter_profile.jsonl'
    profile=[json.loads(line) for line in profile_path.read_text().splitlines()] if profile_path.exists() else []
    # Oracle calls are outside time and action counts.
    checked=oracle(root,tool,fixture,prompt,op,method,result,external,approved=scenario!='source_changed')
    expected_complete=scenario not in {'external_instruction','source_changed','corrupt_receipt','reference_changed'}
    if scenario=='external_context' and tool!='claude':
        # The original sentinel now has a recorded external value, and preserving
        # that value satisfies the context obligation rather than the old bytes.
        checked['preservation_checks']['outside']=True
        checked['external_preserved']=all(checked['preservation_checks'].values())
        checked['state_coherent']=bool(checked['disk_correct'] and checked['native_reference_correct'] and checked['native_status_aligned'] and checked['manager_records_coherent'] and checked['external_preserved'])
        checked['correct_api_completion']=checked['api_success'] and checked['state_coherent']
        checked['unique_api_completion']=checked['correct_api_completion'] and checked['logical_completion_unique']
        checked['false_success']=checked['api_success'] and not checked['state_coherent']
    contract=(checked['unique_api_completion'] if expected_complete else not checked['api_success']) and checked['external_preserved']
    return {'repository':item['repository'],'payload':item['payload']['path'],'payload_bytes':item['payload']['bytes'],
            'payload_sha256':item['payload']['sha256'],'tool':tool,'method':method,'scenario':scenario,'supported':True,
            'duration_ns':measured,'resume_wall_ns':result['wall_ns'],'expected_completion':expected_complete,
            'actual_hard_exits':len(exits),'initial':initial,'second':second,'crash_snapshot':snapshot,'result':result,'plan_response':plan,'adapter_calls':actions,
            'native_profile':profile,'total_activation_calls':sum(r['command']=='activate' for r in actions),
            'resume_activation_calls':sum(r['command']=='activate' for r in after_count),
            **checked,'contract_pass':bool(contract)}
