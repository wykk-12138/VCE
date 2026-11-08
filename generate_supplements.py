"""Generate the data-oriented S1/S2 files from retained records (Python 3.10+).

No third-party packages, network, language model, or experiment execution.
Usage: python generate_supplements.py [--check]
"""
from __future__ import annotations

import argparse
import collections
import csv
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import textwrap

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated'
TITLE = 'VCE: Efficient Native Configuration Deployment Recovery Using Validated Completion Evidence'
LABEL = {
    'JournalGuardedScoped': 'J-Q',
    'JournalPostStatus': 'J-1',
    'ReceiptCoordinatorV15': 'VCE',
    'JournalWitnessV15': 'J-E',
    'ReceiptCoordinatorV14': 'Full-tree',
}
ORDER = ['JournalGuardedScoped', 'JournalPostStatus', 'ReceiptCoordinatorV15', 'JournalWitnessV15']
inputs = {}
outputs = {}
checks = []


def need(ok, name):
    checks.append(name)
    if not ok:
        raise ValueError('Data check failed: ' + name)


def equal(a, b, name, tol=1e-8):
    need(math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol), name)


def read(rel):
    p = ROOT / rel
    data = p.read_bytes()
    inputs[rel] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data.decode('utf-8-sig')


def js(rel):
    return json.loads(read(rel))


def jl(rel):
    return [json.loads(s) for s in read(rel).splitlines() if s.strip()]


def csvread(rel):
    return list(csv.DictReader(io.StringIO(read(rel))))


def csvout(name, columns, rows):
    f = io.StringIO(newline='')
    w = csv.writer(f, lineterminator='\n')
    w.writerow(columns)
    w.writerows(rows)
    outputs['tables/' + name] = f.getvalue()


def f3(n):
    return 'none' if n is None else str(Decimal(f'{n:.10f}').quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))


def f4(n):
    return 'none' if n is None or n == '' else f'{float(n):.4f}'


def display(n):
    return LABEL.get(n, n)


def wrap(s, width):
    return textwrap.wrap(str(s), width=width, break_long_words=True, break_on_hyphens=False) or ['']


class Document:
    def __init__(self, title):
        self.blocks = [('h1', title), ('p', TITLE)]

    def h(self, title):
        self.blocks.append(('h2', title))

    def p(self, text):
        self.blocks.append(('p', text))

    def table(self, columns, rows):
        self.blocks.append(('table', (columns, [[str(x) for x in row] for row in rows])))

    def save(self, stem):
        md = []; txt = []
        for kind, value in self.blocks:
            if kind in ('h1', 'h2'):
                md.append(('# ' if kind == 'h1' else '## ') + value)
                txt.append(value + '\n' + ('=' if kind == 'h1' else '-') * min(len(value), 110))
            elif kind == 'p':
                md.append(value)
                txt.append('\n'.join(wrap(value, 110)))
            else:
                columns, rows = value
                md.append('\n'.join(['| ' + ' | '.join(columns) + ' |',
                    '| ' + ' | '.join('---' for _ in columns) + ' |'] +
                    ['| ' + ' | '.join(x.replace('|', '\\|').replace('\n', ' ') for x in row) + ' |' for row in rows]))
                widths = [min(34, max(len(columns[j]), max((len(row[j]) for row in rows), default=1))) for j in range(len(columns))]
                while sum(widths) + 3 * (len(columns) - 1) > 110:
                    idx = max(range(len(widths)), key=lambda k: widths[k])
                    widths[idx] -= 1
                plain = []
                for idx, row in enumerate([columns] + rows):
                    cells = [wrap(cell, width) for cell, width in zip(row, widths)]
                    for line in range(max(map(len, cells))):
                        plain.append(' | '.join((cell[line] if line < len(cell) else '').ljust(width) for cell, width in zip(cells, widths)).rstrip())
                    if idx == 0:
                        plain.append('-+-'.join('-' * w for w in widths))
                txt.append('\n'.join(plain))
        outputs[stem + '.md'] = '\n\n'.join(md) + '\n'
        outputs[stem + '.txt'] = '\n\n'.join(txt) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Recompute in memory and compare all generated files without writing.')
    args = parser.parse_args()
    R = 'Research_Artifact/'
    P = R + 'paper/'
    facts = js(P + 'results_v17/facts.json')
    primary = jl(P + 'results_v17/timing-rows.jsonl')
    audit = js(P + 'results_v17/source_audit.json')
    model = js(P + 'evidence/closure-model-v16/summary.json')
    comparisons = csvread(P + 'results_v17/all_comparisons.csv')
    sensitivity = csvread(P + 'results_v17/sensitivity.csv')
    batch_costs = csvread(P + 'results_v17/batch_costs.csv')
    domains = csvread(P + 'results_v17/domain_thresholds.csv')
    need(len(primary) == 2448 and not any(x['warmup'] for x in primary), '2448 primary scored observations')
    need(all(x['pass'] for x in primary), 'primary checks passed')
    need(len(audit['rows']) == 19, '19 recorded audit groups')
    by_pair = collections.defaultdict(dict)
    by_cond = collections.defaultdict(list)
    for row in primary:
        condition = (row['tool'], row['scenario'], row['lifecycle'], row['noise'])
        key = (row['batch'], row['repository']) + condition
        need(row['method'] not in by_pair[key], 'unique primary method/input/batch/condition')
        by_pair[key][row['method']] = row
        by_cond[condition + (row['method'],)].append(row)
        need(row['episode_ns'] == row['preview_ns'] + row['first_ns'] + row['wall_ns'], 'primary episode identity')
    need(len(by_pair) == 612 and all(set(v) == set(ORDER) for v in by_pair.values()), '612 complete four-method paired sets')

    inventory = []
    for folder, batch in [('closure-confirmation-v16-final', 'b1'), ('audit-confirmation-v17-b2', 'b2'), ('audit-confirmation-v17-b3', 'b3')]:
        rows = jl(P + 'evidence/' + folder + '/raw.jsonl')
        scored = [x for x in rows if not x['warmup']]
        need(len(rows) == 884 and len(scored) == 816, 'primary batch size ' + batch)
        fields = ['block','repository','tool','scenario','lifecycle','noise','method','wall_ns','first_ns','preview_ns','episode_ns','evidence_bytes']
        need(sorted(tuple(x[k] for k in fields) for x in scored) ==
             sorted(tuple(x[k] for k in fields) for x in primary if x['batch'] == batch), 'raw/combined primary identity ' + batch)
        inventory.append(['Primary ' + batch, len(scored), len(rows)-len(scored), P + 'evidence/' + folder + '/raw.jsonl'])

    # All absolute summaries are recomputed from observations.
    primary_rows = []
    for key, rows in sorted(by_cond.items()):
        tool, scenario, lifetime, noise, method = key
        need(len(rows) == 36, '36 observations per primary cell')
        primary_rows.append([tool, scenario, lifetime, noise, display(method), method, len(rows),
            statistics.median(x['wall_ns'] / 1e6 for x in rows),
            statistics.median(x['episode_ns'] / 1e6 for x in rows),
            statistics.median(x['confirmation_episode_ns'] / 1e6 for x in rows)])
    csvout('S1_Primary_Absolute.csv', ['tool','scenario','lifecycle','files','method','raw_method','n','request_median_ms','episode_median_ms','confirmation_median_ms'], primary_rows)

    # Keep the published confidence limits; independently recompute point estimates
    # and leave-one-input/batch ranges without substituting a new bootstrap design.
    paired = []
    paired_lookup = {}
    for item in comparisons:
        tool, scenario, lifetime, noise = item['condition'].split('/')
        selected = {k:v for k,v in by_pair.items() if k[2:] == (tool, scenario, lifetime, int(noise))}
        logs = {k: math.log(v['ReceiptCoordinatorV15'][item['metric']] / v[item['control']][item['metric']]) for k,v in selected.items()}
        point = math.exp(statistics.mean(logs.values()))
        equal(point, item['ratio'], 'paired primary estimate')
        key = (item['condition'], item['control'], item['metric'])
        paired_lookup[key] = (point, float(item['low']), float(item['high']), logs)
        paired.append([item['condition'], display(item['control']), item['control'], item['metric'], len(logs), point, item['low'], item['high']])
    csvout('S1_Paired_Ratios.csv', ['condition','control','raw_control','metric','n','ratio_recomputed','ci_low_recorded','ci_high_recorded'], paired)
    sensitive = []
    for item in sensitivity:
        logs = paired_lookup[(item['condition'], item['control'], item['metric'])][3]
        batch = [math.exp(statistics.mean(v for k,v in logs.items() if k[0] != omitted)) for omitted in sorted({k[0] for k in logs})]
        project = [math.exp(statistics.mean(v for k,v in logs.items() if k[1] != omitted)) for omitted in sorted({k[1] for k in logs})]
        calculated = [min(batch), max(batch), min(project), max(project)]
        for value, column in zip(calculated, ['loo_batch_min','loo_batch_max','loo_project_min','loo_project_max']):
            equal(value, item[column], 'leave-one sensitivity')
        sensitive.append([item['condition'], display(item['control']), item['metric']] + calculated)
    csvout('S1_Sensitivity.csv', ['condition','control','metric','leave_one_batch_min','leave_one_batch_max','leave_one_input_min','leave_one_input_max'], sensitive)

    def costs(tool, batch=None):
        values = []
        for scenario, metric in [('normal','episode_ns'),('recovery','episode_ns'),('fallback','episode_ns'),('completed_retry','wall_ns')]:
            pairs = [v for k,v in by_pair.items() if k[2:] == (tool,scenario,'cold',0) and (batch is None or k[0] == batch)]
            values.append(statistics.mean((x['ReceiptCoordinatorV15'][metric]-x['JournalGuardedScoped'][metric])/1e6 for x in pairs))
        normal, hit, miss, repeat = values
        pstar = 0.0 if normal <= 0 else (normal/(normal-hit) if hit < 0 else None)
        rstar = 0.0 if normal <= 0 else (-normal/repeat if repeat < 0 else None)
        return values + [pstar, rstar]

    costrows = []
    for tool in ['claude','codex','grok']:
        vals = costs(tool)
        for value, field in zip(vals, ['normal_ms','hit_ms','miss_ms','repeat_ms','break_even_p','repeat_break_even']):
            equal(value, facts['costs'][tool][field], 'mean cost/threshold ' + tool + '/' + field)
        costrows.append([tool] + vals)
    csvout('S1_Workload_Costs.csv', ['tool','normal_delta_ms','hit_delta_ms','miss_delta_ms','repeat_delta_ms','p_star_h1_r0','r_star_p0'], costrows)
    batchrows=[]
    for row in batch_costs:
        vals=costs(row['tool'],row['batch'])
        for value, field in zip(vals,['normal_ms','hit_ms','miss_ms','repeat_ms','p_star','repeat_star']):
            equal(value,row[field],'batch cost/threshold')
        batchrows.append([row['tool'],row['batch']]+vals)
    csvout('S1_Batch_Costs.csv', ['tool','batch','normal_delta_ms','hit_delta_ms','miss_delta_ms','repeat_delta_ms','p_star_h1_r0','r_star_p0'],batchrows)

    # Source-audit rows are recorded manual assessments; exporting them does not
    # turn them into an automatic program proof.
    audit_columns = ['id','adapter','source','source_sha256','anchors','predicate_branch','reads_and_absence','snapshot_fields','mutations','scope_or_exclusion']
    csvout('S1_Source_Audit.csv',audit_columns,[[row[c] for c in audit_columns] for row in audit['rows']])
    outputs['tables/S1_Source_Audit.json'] = json.dumps(audit,ensure_ascii=False,indent=2)+'\n'
    inherited=jl(P+'evidence/closure-validation-v16/inherited/raw.jsonl')
    extra=jl(P+'evidence/closure-validation-v16/extra.jsonl')
    branch=jl(P+'evidence/audit-branches-v17/raw.jsonl')
    lifecycle=jl(P+'evidence/audit-lifecycle-v17/raw.jsonl')
    dbos=jl(P+'evidence/closure-dbos-v16/raw.jsonl')
    branch_summary=js(P+'evidence/audit-branches-v17/summary.json')
    life_summary=js(P+'evidence/audit-lifecycle-v17/summary.json')
    complete=[x for x in inherited+extra if x['method'] in ORDER]
    ablated=[x for x in inherited+extra if x['method'] not in ORDER]
    need(len(complete)==398 and len(ablated)==2,'398 safety cases and two separate ablations')
    checkrows=[]
    for name,rows in [('Complete-method safety',complete),('Guard-removal cases',ablated),('Dependency mutations',branch),('Gate termination',lifecycle),('DBOS composition',dbos)]:
        checkrows.append([name,len(rows),sum(bool(x['pass']) for x in rows), 'Expected counterexamples' if rows is ablated else 'Complete safeguards'])
    need(not any(x['pass'] for x in ablated) and facts['validation']['inherited']['ablation_false_success']==2,'two expected guard-removal counterexamples')
    csvout('S1_Validation_Counts.csv',['suite','cases','raw_pass_true','role'],checkrows)
    need(len(branch)==branch_summary['cases']==162,'branch count')
    need(sum(bool(x['evidence_hit']) for x in branch)==branch_summary['hits'],'branch hit count')
    need(len(lifecycle)==life_summary['cases']==54,'lifecycle count')
    need(sum(bool(x['retry_completed']) for x in lifecycle)==life_summary['completed_retries'],'completed retry count')
    need(sum(bool(x['held_before_kill']) for x in lifecycle)==life_summary['held_before_kill'],'held lease count')
    need(sum(bool(x['available_after_termination']) for x in lifecycle)==life_summary['released_after_kill'],'released lease count')
    life_rows=[]
    for (tool,method,cut),group in sorted(_group(lifecycle,lambda x:(x['tool'],x['method'],x['cut'])).items()):
        life_rows.append([tool,display(method),cut,len(group),sum(x['retry_completed'] for x in group),sum(not x['retry_completed'] for x in group),sum(x['held_before_kill'] for x in group),sum(x['available_after_termination'] for x in group)])
    csvout('S1_Lifecycle.csv',['tool','method','cut','cases','completed_retries','safe_refusals','held_before_kill','available_after_termination'],life_rows)
    modelrows=[[name,rec['states'],rec['transitions'],rec['violation'] or 'none',rec['bounds']] for name,rec in model['complete'].items()]
    csvout('S1_Model_Checks.csv',['model','states','transitions','recorded_violation','bounds'],modelrows)
    csvout('S1_Model_Ablations.csv',['guard_removed','states','transitions','recorded_violation','counterexample'],[[name,x['states'],x['transitions'],x['violation'],' -> '.join(x['trace'])] for name,x in model['ablations'].items()])
    csvout('S1_Model_Source_Map.csv',['transition','source'],list(model['source_mapping'].items()))

    domainraw=jl(P+'evidence/audit-domain-v17/raw.jsonl')
    selector=jl(R+'manuscript/figure-data/paper/evidence/dependency-benchmark-v15-opt1/raw.jsonl')
    for name,rows,rel in [('Domain costs',domainraw,P+'evidence/audit-domain-v17/raw.jsonl'),('Earlier selector',selector,R+'manuscript/figure-data/paper/evidence/dependency-benchmark-v15-opt1/raw.jsonl')]:
        inventory.append([name,sum(not x['warmup'] for x in rows),sum(x['warmup'] for x in rows),rel])
    csvout('S1_Domain_Costs.csv',list(domains[0]),[[row[c] for c in domains[0]] for row in domains])

    # Historical records remain separate. This table is a record count, not a
    # new cross-system comparison or a substituted performance ranking.
    history=[]
    for folder in ['published-confirm-core-v6','published-confirm-netherite-v6','published-confirm-compositions-v6','published-replan-recovery-v6','published-cold-timing-final-v6','styx-confirmation2-v7','halfmoon-confirmation-v7','styx-migration-v7']:
        rel='Historical_Evidence/paper/evidence/'+folder+'/raw.jsonl'
        rows=jl(rel)
        history.append([folder,len(rows),rel])
    csvout('S1_Historical_Inventory.csv',['run','records','source'],history)
    csvout('S1_Study_Inventory.csv',['study','scored','warmups','source'],inventory)

    s1=Document('S1. Validation records and primary statistics')
    s1.p('Generated by generate_supplements.py from the retained files. Run: python generate_supplements.py. All paths in this document are relative to the extracted package root.')
    s1.h('S1.1 Data and measurement units')
    s1.table(['Study','Scored','Warm-ups'],[x[:3] for x in inventory])
    s1.p('Methods: J-Q = JournalGuardedScoped; J-1 = JournalPostStatus; VCE = ReceiptCoordinatorV15; J-E = JournalWitnessV15 (Journal + VCE evidence). RC-E is the historical label for VCE. The independent Full-tree control is ReceiptCoordinatorV14.')
    s1.p('Time: ns / 1,000,000 = ms. Evidence: bytes / 1,024 = KiB. Complete episode = preview + initial confirmation + resumed request. Additional-confirmation cost uses only its request time. Warm-ups are retained and excluded from estimates. Inputs are repository instruction payloads, not executed application workloads.')
    s1.p('Study paths: generated/tables/S1_Study_Inventory.csv. The primary matrix contains 12 inputs, 3 batches, 17 conditions, and 4 methods. Absolute medians for every cell: generated/tables/S1_Primary_Absolute.csv.')
    s1.h('S1.2 Paired estimates and cost model')
    s1.p('Each ratio is exp(mean(log(VCE/control))) over the 36 paired input/batch observations. Pointwise 95% limits below are copied from the retained 4,000-replicate crossed input/batch bootstrap analysis. This generator recomputes point estimates and leave-one-input/batch sensitivity; it does not run a new bootstrap.')
    summary=[]
    for condition in sorted({x['condition'] for x in comparisons}):
        for metric,label in [('wall_ns','Request'),('episode_ns','Episode')]:
            point,lo,hi,_=paired_lookup[(condition,'JournalGuardedScoped',metric)]
            summary.append([condition,label,f4(point),f'[{lo:.4f}, {hi:.4f}]'])
    s1.table(['Condition: tool/path/lifetime/files','Metric','VCE/J-Q','Recorded 95% CI'],summary)
    s1.p('All controls and metrics: generated/tables/S1_Paired_Ratios.csv. Recomputed sensitivity ranges: generated/tables/S1_Sensitivity.csv.')
    s1.p('Mean differences below are VCE minus J-Q in milliseconds. normal/hit/miss use complete episodes; repeat uses one additional valid confirmation. For interruption fraction p, hit fraction h, and expected valid repeats r: delta = (1-p)*normal + p*(h*hit + (1-h)*miss) + r*repeat. These are workload calculations, not measured production crash rates.')
    s1.table(['Adapter','Normal ms','Hit ms','Miss ms','Repeat ms','p* (h=1,r=0)','r* (p=0)'],[[row[0]]+[f3(x) for x in row[1:5]]+[f4(x) for x in row[5:]] for row in costrows])
    s1.p('Batch thresholds: generated/tables/S1_Batch_Costs.csv. The separate domain study is exported unchanged as generated/tables/S1_Domain_Costs.csv; empty threshold cells mean no crossover in the stated domain. Its 288 scored observations are not pooled with the separate 288-observation selector study or S2.')
    s1.h('S1.3 Native-dependency audit')
    s1.p('Audit type: '+audit['kind']+'. The table indexes recorded manual source assessments; exporting it is not automatic verification of Python or Rust. Full predicates, source SHA-256 values, exact function ranges, observed state, mutation IDs, and exclusion reasons are in generated/tables/S1_Source_Audit.csv and S1_Source_Audit.json.')
    s1.table(['ID','Adapter','Native function anchors'],[[x['id'],x['adapter'],x['anchors']] for x in audit['rows']])
    s1.p('Scope: pinned adapter invocation, fixed environment, truthful native status, stable observation/publication interval, and participating-writer serialization. Unsupported nodes, incomplete scans, or budget excess cause an evidence miss. Claude uses the selected project scope; Codex and Grok observe their selected tool homes. Source paths and scope exceptions are retained per audit row.')
    s1.h('S1.4 Failure and process-lifetime checks')
    s1.table(['Suite','Cases','Raw pass=true','Role'],checkrows)
    s1.p('The two guard-removal histories intentionally expose false completion and have pass=false in the raw records. They are separate negative controls, not failures of the complete method. A passed protective-refusal case does not mean successful deployment.')
    s1.table(['Dependency outcome','Recorded count'],[[k,v] for k,v in branch_summary.items()])
    s1.table(['Lifecycle outcome','Recorded count'],[[k,v] for k,v in life_summary.items()])
    s1.p('The gate holds the native lease and executes the native Python entry in the same process. Termination tests wait for the exact gate process to exit before retry. The 54 cases cover two payloads, three adapters, three methods, and three cuts. Detailed grouped counts: generated/tables/S1_Lifecycle.csv. Raw command, PID, lease, native-status, and oracle fields remain in Research_Artifact/paper/evidence/.')
    s1.h('S1.5 Bounded model and source map')
    s1.table(['Model','States','Transitions','Recorded violation'],[x[:4] for x in modelrows])
    s1.table(['Transition','Recorded source'],list(model['source_mapping'].items()))
    s1.p('Bounds and counterexamples: generated/tables/S1_Model_Checks.csv and S1_Model_Ablations.csv. Recorded assumptions: '+ '; '.join(model['assumptions'])+'. These finite graphs are not source-code proofs or power-loss tests.')
    s1.h('S1.6 Historical records and source access')
    s1.table(['Historical run','Rows'],[x[:2] for x in history])
    s1.p('The historical runtime evidence is not pooled with primary timing. Version/backend/boundary/compatibility details: Historical_Evidence/paper/publishedstudy/REPRODUCE.md and Historical_Evidence/paper/linuxstudy/REPRODUCE.md. The earlier format-refusal study is retained in Historical_Evidence/paper/results_v5/.')
    s1.p('Native implementation and gates: Research_Artifact/native/. Experiment and primary-analysis drivers: Research_Artifact/paper/auditstudy/ and paper/closurestudy/. The frozen results precede the namespace migration; see Research_Artifact/PROVENANCE.md. Historical hashes refer to historical source identities. The nested manuscript/ folder retains only plotting code and its data inputs; article text and author images are excluded.')
    s1.p('Read-only regeneration check: python generate_supplements.py --check. Exact inputs: generated/SOURCE_MANIFEST.csv. Check results: generated/GENERATION_REPORT.json. Data generation here reads saved observations; it does not rerun native experiments.')
    s1.save('S1_Validation_and_Statistics')

    scale=collections.defaultdict(list)
    scale_counts=[]
    binary_ids=set()
    for batch in ['b1','b2','b3']:
        rel=P+'evidence/scale-v18/'+batch+'/'
        rows=jl(rel+'raw.jsonl');spec=js(rel+'spec.json');summary=js(rel+'summary.json')
        binary_ids.add(spec['binary_sha256'])
        need(inputs[rel+'raw.jsonl']['sha256']==summary['raw_sha256'],'original scale raw hash '+batch)
        scored=[x for x in rows if not x['warmup']]
        need(len(rows)==468 and len(scored)==432,'scale batch count '+batch)
        need(all(x['pass'] for x in rows),'scale checks passed '+batch)
        seen=set()
        for row in scored:
            unique=(row['shape'],row['noise'],row['method'],row['repository'])
            need(unique not in seen,'unique scale cell');seen.add(unique)
            scale[unique[:3]].append(row)
        scale_counts.append([batch,len(scored),len(rows)-len(scored)])
    smoke=jl(P+'evidence/scale-v18/smoke/raw.jsonl')
    need(len(smoke)==12,'12 separate smoke cases')
    old_scale=js(P+'results_scale_v18/scale-summary.json')['groups']
    need(len(scale)==36 and all(len(v)==36 for v in scale.values()),'36 scale groups of 36 observations')
    scale_rows=[]
    for shape in ['nested','flat']:
        for noise in [0,64,256,512,1024,2048]:
            for method in ['JournalGuardedScoped','ReceiptCoordinatorV14','ReceiptCoordinatorV15']:
                rows=scale[(shape,noise,method)]
                medians=[statistics.median(x['wall_ns']/1e6 for x in rows),
                    statistics.median(x['exclusive_ns']['Validation']/1e6 for x in rows),
                    statistics.median(x['evidence_bytes']/1024 for x in rows)]
                old=old_scale[shape][str(noise)][method]
                for median,field in zip(medians,['wall_ms','validation_ms','evidence_kib']):equal(median,old[field]['value'],'scale median '+field)
                lo,hi=old['wall_ms']['ci95']
                scale_rows.append([shape,noise,display(method),method,len(rows),medians[0],lo,hi,medians[1],medians[2]])
    csvout('S2_Scale_Results.csv',['layout','files','method','raw_method','n','recovery_median_ms','recovery_ci_low_recorded','recovery_ci_high_recorded','validation_median_ms','evidence_median_kib'],scale_rows)

    s2=Document('S2. Scale and layout results')
    s2.p('Generated from Research_Artifact/paper/evidence/scale-v18/. The primary v17 experiment is separate; its observations are not pooled with this study.')
    s2.h('S2.1 Design and records')
    s2.table(['Factor','Values'],[['Additional files','0, 64, 256, 512, 1024, 2048'],['Size per file','1 KiB'],['Layout','Nested subdirectory; flat project root'],['Method','J-Q; Full-tree; VCE'],['Inputs','12 paired repository payloads'],['Batches','3 serial batches'],['Timing','Cold recovery after caller exit following native completion'],['Per displayed row','36 observations = 12 inputs x 3 batches']])
    s2.table(['Batch','Scored','Warm-ups'],scale_counts)
    s2.p('Separate smoke run: '+str(len(smoke))+' cases, excluded. Fixture setup, cleanup, artificial edits, and the independent oracle are outside timing. Evidence hits invoke no native process; query recovery invokes version and status. Measured executable SHA-256: '+', '.join(sorted(binary_ids))+'.')
    s2.h('S2.2 Complete results')
    s2.p('Recovery time, exclusive validation time, and evidence size are medians recomputed from the retained rows. Recovery intervals are copied from the saved 4,000-replicate crossed input/batch bootstrap output. They are pointwise 95% intervals; no new bootstrap is run by this generator. ms = ns / 1,000,000; KiB = bytes / 1,024.')
    for shape in ['nested','flat']:
        s2.h('S2.2.'+('1 Nested files' if shape=='nested' else '2 Flat files'))
        s2.table(['Files','Method','Recovery ms','Recorded 95% CI','Validation ms','Evidence KiB'],[[r[1],r[2],f3(r[5]),f'[{r[6]:.3f}, {r[7]:.3f}]',f3(r[8]),f3(r[9])] for r in scale_rows if r[0]==shape])
    s2.h('S2.3 Files and regeneration')
    s2.table(['Material','Path from package root'],[['Raw/spec/summary per batch',P+'evidence/scale-v18/b1/ (also b2/, b3/, smoke/)'],['Saved full estimates',P+'results_scale_v18/scale-summary.json'],['Generated table','generated/tables/S2_Scale_Results.csv'],['Experiment driver',P+'auditstudy/scale_v18.py'],['Original analysis provenance',R+'scale-study-provenance/'],['Source hashes','generated/SOURCE_MANIFEST.csv']])
    s2.p('Recreate this file and the CSV: python generate_supplements.py. Verify without writing: python generate_supplements.py --check. Fresh experiment execution is separate and requires the native build/environment documented in Research_Artifact/SCALE-EXTENSION-2026-10-29.md. Use a new output directory for any new measurements.')
    s2.save('S2_Scale_Results')

    # The generator itself is an input; no wall-clock timestamps or absolute paths
    # appear in generated output, so relocation does not change document bytes.
    read('generate_supplements.py')
    f=io.StringIO(newline='');w=csv.writer(f,lineterminator='\n');w.writerow(['path','bytes','sha256'])
    for path,record in sorted(inputs.items()):w.writerow([path,record['bytes'],record['sha256']])
    outputs['SOURCE_MANIFEST.csv']=f.getvalue()
    outputs['GENERATION_REPORT.json']=json.dumps({
        'generator':'generate_supplements.py','input_files':len(inputs),'checks_passed':len(checks),
        'primary_scored':len(primary),'primary_pair_sets':len(by_pair),'primary_absolute_rows':len(primary_rows),
        'paired_estimates_recomputed':len(paired),'sensitivity_rows_recomputed':len(sensitive),
        'audit_groups_exported':len(audit['rows']),'scale_scored':sum(map(len,scale.values())),
        'scale_summary_rows':len(scale_rows),'scale_medians_recomputed':len(scale_rows)*3,
        'confidence_intervals':'Retained analysis outputs, not recomputed by this generator.',
        'manual_source_audit':'Exported recorded assessment; not an automatic source proof.',
        'experimental_execution':'No new experiments run.'},indent=2)+'\n'
    if args.check:
        for rel,content in outputs.items():
            p=OUT/rel
            if not p.exists() or p.read_bytes()!=content.encode('utf-8'):
                raise ValueError('Generated file missing or differs: '+rel)
        manifest=ROOT/'FILE_MANIFEST.csv'
        if manifest.exists():
            with manifest.open(encoding='utf-8',newline='') as f:
                for item in csv.DictReader(f):
                    p=ROOT/item['path']
                    need(p.is_file() and p.stat().st_size==int(item['bytes']) and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'package integrity '+item['path'])
        print(f'PASS: {len(outputs)} generated files match; {len(checks)} data/integrity checks passed. No files written.')
    else:
        for rel,content in outputs.items():
            p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content.encode('utf-8'))
        print(f'Generated {len(outputs)} files; {len(checks)} data checks passed.')


def _group(rows,key):
    groups=collections.defaultdict(list)
    for row in rows:groups[key(row)].append(row)
    return groups


if __name__=='__main__':
    main()
