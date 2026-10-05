#!/usr/bin/env python3
"""Development-only independent physical review; production movement remains NASM."""
from pathlib import Path
import sys, math, json, hashlib, subprocess
oracle=Path('/mnt/titan_nv3/projects/red-horizon-workers/crowd-oracle/tests/test_crowd_outcomes.py')
library=Path('/tmp/rh-crowd-tactics-shadow/intent.so')
expected='b5744d5412d482b6344e4c55ec2c5043f194c9e358383196a44fa1b787696c01'
assert hashlib.sha256(library.read_bytes()).hexdigest()==expected
source=oracle.read_text().split('reports=[]')[0]
sys.argv=[str(oracle),str(library)]
ns={'__file__':str(oracle)}
exec(compile(source,str(oracle),'exec'),ns)
rows=[]
for count in (3,5,8):
    for mode in ('shared','divergent'):
        goals=[(1012,2000)] if mode=='shared' else [(1012,2000),(988,2000),(1000,2012)]
        records=[(i,1000,2000,0,i%len(goals),goals[i%len(goals)]) for i in range(count)]
        ns['setup'](records)
        entities=ns['entities']
        previous={(i,j):-1.1 for i in range(count) for j in range(i+1,count)}
        for tick in range(400):
            before=[ns['pos'](entities[i]) for i in range(count)]
            ns['lib'].sim_tick()
            for i in range(count):
                assert math.dist(before[i],ns['pos'](entities[i]))<=.1215
                assert entities[i].hp==100
            for (i,j),old in previous.copy().items():
                start=(before[i][0]-before[j][0],before[i][1]-before[j][1])
                end=(entities[i].x-entities[j].x,entities[i].z-entities[j].z)
                swept=ns['segment_distance']((0,0),start,end)-1.1
                assert swept>=min(0,old)-.003,(count,mode,tick,i,j,'overlap deepened',old,swept)
                previous[i,j]=math.dist(ns['pos'](entities[i]),ns['pos'](entities[j]))-1.1
        rows.append({'count':count,'mode':mode,'ticks':400,
                     'final_poses':[ns['pos'](entities[i]) for i in range(count)],
                     'min_final_gap':min(previous.values()),
                     'minimum_displacement':min(math.dist((1000,2000),ns['pos'](entities[i])) for i in range(count))})
report={'suite':'crowd-independent-intent-review','passed':True,
        'invocation':'python3 /tmp/rh-crowd-independent-intent-review.py',
        'review_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'oracle_path':str(oracle),'oracle_sha256':hashlib.sha256(oracle.read_bytes()).hexdigest(),
        'oracle_worker_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=oracle.parents[1],text=True).strip(),
        'library_path':str(library),'library_sha256':expected,
        'kernel_source_commit':'af1a24a',
        'kernel_worker_reported_build_provenance':'16 frozen root objects from e95c522 plus current crowd kernel replacement; source identity reported by crowd_core worker',
        'cases':rows,
        'scope':'Independent real world sim_tick; controlled friendly exact-coincident infantry initial poses and actual explicit goals. Every relative sweep forbids deepening recovered penetration within .003m; actual speed and HP checked. Not complete operation, vehicle driving or saturated-neighbor acceptance.'}
Path('/tmp/rh-crowd-independent-intent-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
