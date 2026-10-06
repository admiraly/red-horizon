#!/usr/bin/env python3
"""Verify incremental dependencies and frozen background jobs in an isolated repo."""
import argparse,json,os,pathlib,shutil,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--nasm',required=True);p.add_argument('--source-root',type=pathlib.Path);args=p.parse_args()
if args.source_root:ROOT=args.source_root.resolve()
with tempfile.TemporaryDirectory(prefix='red horizon tools test-') as temp:
    root=pathlib.Path(temp)
    for folder in ('tools','src','schemas','shaders','content','tests'):
        if (ROOT/folder).exists(): shutil.copytree(ROOT/folder,root/folder)
    shutil.copy2(ROOT/'.gitignore',root/'.gitignore')
    env=os.environ.copy();env.pop('RED_HORIZON_SOURCE_COMMIT',None);env['RED_HORIZON_NASM']=str(pathlib.Path(args.nasm).resolve())
    def run(*argv):
        return subprocess.check_output(argv,cwd=root,env=env,text=True)
    run('git','init','-q');run('git','config','user.name','Test');run('git','config','user.email','test@example.invalid');run('git','add','.');run('git','commit','-qm','isolated fixture')
    def dev(*argv): return run('python3','tools/dev.py',*argv)
    # Setup failure must also leave a terminal result, not permanently 'running'.
    missing_env=dict(env);missing_env['RED_HORIZON_NASM']=str(root/'missing-nasm')
    setup_job=json.loads(subprocess.check_output(['python3','tools/dev.py','bench','--ticks','1','--background'],cwd=root,env=missing_env,text=True))
    setup_result=pathlib.Path(setup_job['result']);deadline=time.monotonic()+10
    while not setup_result.exists() and time.monotonic()<deadline:time.sleep(.05)
    assert setup_result.exists(),'worker setup failure has no terminal result'
    setup=json.loads(setup_result.read_text());assert setup['status']=='failed' and setup['stage']=='worker_setup' and setup['exit_code']==1
    assert json.loads(dev('collect',setup_job['job_id']))['status']=='failed'
    inputs={str(p.relative_to(root)):p.read_bytes() for folder in ('src','shaders','schemas') for p in (root/folder).rglob('*') if p.is_file()}
    cold=json.loads(dev('build'));warm=json.loads(dev('build','--changed'))
    assert pathlib.Path(cold['executable']).is_relative_to(root/'build/revisions'), 'executable escaped build tree'
    assert all((root/name).read_bytes()==content for name,content in inputs.items()), 'build mutated authored source'
    assert cold['assembled']>=2 and warm['assembled']==0
    source=root/'src/sim/world.asm';source.write_text(source.read_text()+'\n; incremental test\n')
    changed=json.loads(dev('build','--changed'));assert changed['assembled']==1
    # Actual include/incbin dependencies: a shader edit must touch one renderer
    # object and no headless objects; a nested player include must propagate.
    dev('build','--target','client','--objects-only')
    shader=root/'shaders/battle.vert';shader.write_text(shader.read_text()+'\n// dependency fixture\n')
    assert json.loads(dev('build'))['assembled']==0
    shader_build=json.loads(dev('build','--target','client','--objects-only'))
    assert shader_build['assembled_sources']==['src/render/shaders.asm'],shader_build
    include=root/'schemas/player.inc'
    nested=root/'schemas/test-nested.inc';nested.write_text('; nested fixture\n')
    include.write_text(include.read_text()+'\n%ifidn __OUTPUT_FORMAT__,elf64\n%include "schemas/test-nested.inc"\n%endif\n')
    player_dependencies={'src/sim/scenarios.asm','src/sim/company_remote.asm','src/nav/crowd.asm','src/ai/company_control.asm','src/ai/company_transfer.asm','src/game/ground_motion.asm','src/game/player.asm','src/game/vehicles.asm'}
    # These report modules deliberately include player.inc. Preserve exact-set
    # invalidation checks across historical frozen and current source fixtures.
    for name in ('src/ai/company_supply.asm','src/ai/depot_supply.asm','src/sim/depot_supply_remote.asm','src/ai/infantry_supply_route.asm','src/game/player_ammunition.asm','src/sim/player_ammunition_remote.asm'):
        if (root/name).is_file():player_dependencies.add(name)
    player_build=json.loads(dev('build'))
    assert set(player_build['assembled_sources'])==player_dependencies,player_build
    nested.write_text('; nested fixture changed\n')
    player_build=json.loads(dev('build'))
    assert set(player_build['assembled_sources'])==player_dependencies,player_build
    client_build=json.loads(dev('build','--target','client','--objects-only'))
    assert set(client_build['assembled_sources'])=={'src/platform/linux/client.asm','src/net/client.asm','src/render/effects.asm','src/render/meshes.asm','src/audio/emitters.asm','src/render/air_trails.asm','src/audio/footsteps.asm','src/render/hazard_warning.asm'},client_build
    inputs={str(p.relative_to(root)):p.read_bytes() for folder in ('src','shaders','schemas') for p in (root/folder).rglob('*') if p.is_file()}
    fast=dev('test','--suite','fast')
    assert '"suite": "fast-combat"' in fast
    assert all((root/name).read_bytes()==content for name,content in inputs.items()), 'fast check mutated authored source'
    job=json.loads(dev('bench','--ticks','30','--realtime','--background'))
    frozen=pathlib.Path(job['source_snapshot']);assert frozen.is_dir()
    assert (frozen/'src/sim/world.asm').read_bytes()==source.read_bytes()
    previous_exe=(root/'build/red-horizon-server').read_bytes()
    previous_obj=(root/'build/src_sim_world.asm.o').read_bytes()
    source.write_text('INTENTIONALLY INVALID ASSEMBLY\n')
    result=pathlib.Path(job['result']);deadline=time.monotonic()+15
    while not result.exists() and time.monotonic()<deadline: time.sleep(.1)
    assert result.exists(),'background job did not finish'
    r=json.loads(result.read_text());assert r['status']=='passed' and r['revision']==job['revision']
    report=list((frozen/'runs').glob('bench-*.json'));assert len(report)==1
    assert json.loads(report[0].read_text())['revision']==job['revision']
    invalid=subprocess.run(['python3','tools/dev.py','build'],cwd=root,env=env,capture_output=True)
    assert invalid.returncode!=0,'invalid source falsely succeeded'
    assert (root/'build/red-horizon-server').read_bytes()==previous_exe
    assert (root/'build/src_sim_world.asm.o').read_bytes()==previous_obj
    status=json.loads(dev('collect',job['job_id']));assert status['status']=='passed'
print(json.dumps({'suite':'tools','passed':True,'checks':['cold/incremental','single module invalidation','shader isolation','transitive includes','source preservation','failed build preserves previous objects','fast real-core suite','immutable background source','revision identity','failed assembly reported','job collection','terminal missing-NASM worker setup']}))
