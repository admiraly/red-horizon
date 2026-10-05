#!/usr/bin/env python3
"""Development orchestration only. Game simulation lives in NASM objects."""
import argparse,fcntl,datetime,hashlib,json,os,pathlib,platform,shlex,shutil,subprocess,sys,tarfile,time,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
RUNS=ROOT/'runs'
SCENARIOS={'scale-open':8192,'scale-front':8192,'scale-hotspot':8192,'scale-stretch':16384,'air-battle':8192}
def revision():
    sha=os.environ.get('RED_HORIZON_SOURCE_COMMIT') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    # Hash actual authored inputs too, including uncommitted sources.
    h=hashlib.sha256()
    for folder in ('src','shaders','content','schemas','tools','tests'):
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in str(p): h.update(str(p.relative_to(ROOT)).encode()); h.update(p.read_bytes())
    return sha+'-'+h.hexdigest()[:16]
def nasm():
    candidates=[os.environ.get('RED_HORIZON_NASM'),shutil.which('nasm'),str(ROOT/'.tools/nasm/nasm'),'/tmp/red-horizon-tools/nasm-2.16.03/nasm']
    for p in candidates:
        if p and pathlib.Path(p).is_file() and os.access(p,os.X_OK): return p
    raise RuntimeError('NASM missing: install NASM 2.16.03 or set RED_HORIZON_NASM to its executable')
def execute(cmd,**kwargs):
    return subprocess.run(cmd,cwd=ROOT,check=True,**kwargs)
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(data,indent=2)+'\n'); tmp.replace(path)
def doctor():
    data={'platform':platform.platform(),'machine':platform.machine(),'cpu':platform.processor(),'python':platform.python_version(),'revision':revision(),'display':os.environ.get('DISPLAY'),'remote':subprocess.check_output(['git','remote','-v'],cwd=ROOT,text=True).strip(),'runtime_language':'NASM x86-64','license':'pending owner approval'}
    for tool in ('gcc','make','ninja','gh','glxinfo'): data[tool]=shutil.which(tool)
    try: data['nasm']=subprocess.check_output([nasm(),'-v'],text=True).strip()
    except RuntimeError as e: data['nasm']=str(e)
    if pathlib.Path('/proc/cpuinfo').exists():
        data['cpu']=next((l.split(':',1)[1].strip() for l in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')),'unknown')
    data['writable_project']=os.access(ROOT,os.W_OK)
    data['recorded_rifle_available']=(ROOT/'content/audio/rifle.pcm').is_file()
    data['recorded_footstep_available']=(ROOT/'content/audio/footstep.pcm').is_file()
    if shutil.which('glxinfo') and os.environ.get('DISPLAY'):
        probe=subprocess.run(['glxinfo','-B'],capture_output=True,text=True,timeout=10)
        data['gpu_probe']={'exit_code':probe.returncode,'details':probe.stdout.strip() if probe.returncode==0 else probe.stderr.strip()}
    print(json.dumps(data,indent=2)); atomic(RUNS/'doctor.json',data)
def build(target,objects_only=False):
    BUILD.mkdir(exist_ok=True)
    with (BUILD/'build.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return build_locked(target,objects_only)
def build_locked(target,objects_only=False):
    start=time.perf_counter(); tool=nasm(); execute([sys.executable,'tools/schema.py'])
    BUILD.mkdir(exist_ok=True)
    sources=[p for folder in ('sim','nav','ai','game') for p in (ROOT/'src'/folder).glob('*.asm')]
    if target=='headless': sources += [ROOT/'src/platform/linux/headless.asm']; libs=['-lm']; executable_name='red-horizon-server'
    elif target=='coop':
        sources += [ROOT/'src/net/coop_server.asm']; libs=['-lm']; executable_name='red-horizon-coop-server'
    elif target=='client':
        sources += list((ROOT/'src/render').glob('*.asm'))+list((ROOT/'src/audio').glob('*.asm'))+[ROOT/'src/platform/linux/client.asm']+([ROOT/'src/net/client.asm'] if (ROOT/'src/net/client.asm').exists() else []); libs=['-Wl,-l:libglfw.so.3','-lGL','-lm','-lasound']; executable_name='red-horizon'
    else: raise RuntimeError('Unsupported target')
    if not sources or any(not s.exists() for s in sources): raise RuntimeError(f'{target} sources not integrated yet')
    objects=[]; assembled=0
    # Ask NASM for its actual transitive includes/incbins; unrelated shaders or
    # schemas must not invalidate every object. Compiler/flags also own the cache.
    tool_hash=hashlib.sha256(pathlib.Path(tool).read_bytes()).hexdigest()
    flags=['-f','elf64','-g','-F','dwarf','-I',str(ROOT)+'/']
    assembled_sources=[]
    for source in sources:
        obj=BUILD/(str(source.relative_to(ROOT)).replace('/','_')+'.o'); dep=obj.with_suffix('.sha256')
        output=subprocess.check_output([tool,*flags,'-M','-MT','object',str(source)],cwd=ROOT,text=True)
        dependency_paths=shlex.split(output.partition(':')[2].replace('\\\n',' '))
        h=hashlib.sha256(json.dumps([tool_hash,flags]).encode())
        for dependency in sorted(set(dependency_paths)):
            path=pathlib.Path(dependency)
            if not path.is_absolute(): path=ROOT/path
            h.update(str(path).encode()+b'\0'); h.update(hashlib.sha256(path.read_bytes()).digest())
        digest=h.hexdigest()
        if not obj.exists() or not dep.exists() or dep.read_text()!=digest:
            temporary=obj.with_suffix('.new')
            execute([tool,*flags,str(source),'-o',str(temporary)])
            temporary.replace(obj); dep.write_text(digest); assembled+=1
            assembled_sources.append(str(source.relative_to(ROOT)))
        objects.append(obj)
    if objects_only:
        result={'target':target,'revision':revision(),'objects_only':True,'assembled':assembled,'assembled_sources':assembled_sources,'seconds':time.perf_counter()-start,'executable':None}
        atomic(BUILD/(target+'-objects-build.json'),result); print(json.dumps(result)); return None
    if pathlib.Path(executable_name).name!=executable_name: raise RuntimeError('Invalid executable basename')
    exe=BUILD/executable_name
    signature=hashlib.sha256(b''.join(o.read_bytes() for o in objects)+repr(libs).encode()).hexdigest()
    linkstamp=exe.with_suffix('.linkhash')
    if not exe.exists() or not linkstamp.exists() or linkstamp.read_text()!=signature:
        temporary=exe.with_suffix('.new'); execute(['gcc','-no-pie','-Wl,-z,noexecstack','-o',str(temporary),*[str(o) for o in objects],*libs]); temporary.replace(exe); linkstamp.write_text(signature)
    # Immutable copy used by every launched run.
    rev=revision()
    frozen=BUILD/'revisions'/rev/executable_name; frozen.parent.mkdir(parents=True,exist_ok=True)
    if not frozen.exists() or frozen.read_bytes()!=exe.read_bytes(): shutil.copy2(exe,frozen)
    # Relative shader and content paths must also be immutable for runs.
    for folder in ('shaders','content'):
        if (ROOT/folder).exists(): shutil.copytree(ROOT/folder,frozen.parent/folder,dirs_exist_ok=True)
    result={'target':target,'revision':rev,'assembled':assembled,'assembled_sources':assembled_sources,'seconds':time.perf_counter()-start,'executable':str(frozen)}
    atomic(BUILD/(target+'-build.json'),result); print(json.dumps(result)); return frozen
def run_headless(args,benchmark=False):
    exe=build('headless'); scenario=args.scenario
    if scenario in ('scale-front','scale-hotspot'):
        raise RuntimeError(f'{scenario} fixture not implemented; refusing to relabel scale-open')
    cmd=[str(exe),'--units',str(args.units or SCENARIOS[scenario]),'--ticks',str(args.ticks),'--seed',str(args.seed)]
    if scenario=='air-battle': cmd+=['--scenario','air-battle']
    if args.realtime: cmd.append('--realtime')
    memory_path=RUNS/('memory-'+uuid.uuid4().hex[:10]+'.txt'); RUNS.mkdir(exist_ok=True)
    timer=pathlib.Path('/usr/bin/time')
    if timer.exists(): cmd=[str(timer),'-f','%M','-o',str(memory_path),*cmd]
    start=time.perf_counter(); r=subprocess.run(cmd,cwd=exe.parent,check=True,capture_output=True,text=True)
    peak_memory=int(memory_path.read_text().strip()) if memory_path.exists() else None
    if memory_path.exists(): memory_path.unlink()
    try: metrics=json.loads(r.stdout)
    except json.JSONDecodeError: raise RuntimeError('Runtime did not emit valid JSON: '+r.stdout[:1000])
    result={'scenario':scenario,'revision':exe.parent.name,'seed':args.seed,'wall_seconds':time.perf_counter()-start,'hardware':platform.platform(),'cpu_model':next((line.split(':',1)[1].strip() for line in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),'realtime':args.realtime,'runtime':metrics,'coverage':{'replicated':0,'visible':0,'gpu':'unmeasured','audio':'unmeasured','threads':1,'peak_runtime_rss_kib':peak_memory,'allocation_counts':{'sim_tick_heap':0,'basis':'source audit of static assembly simulation; process total unmeasured'},'navigation_backlog':metrics.get('navigation',{}).get('pending','unmeasured'),'network_bandwidth':'not implemented'}}
    path=RUNS/('bench-'+uuid.uuid4().hex[:10]+'.json'); atomic(path,result); print(json.dumps(result,indent=2)); print('Report: '+str(path))
def client_view_args(args):
    return [value for name in ('width','height','fov','sensitivity') if getattr(args,name,None) is not None
            for value in ('--'+name,str(getattr(args,name)))]
def gpu_benchmark(args):
    if not os.environ.get('DISPLAY'):
        raise RuntimeError('Hardware GPU benchmark requires an accessible X11/XWayland DISPLAY')
    if args.connect:
        raise RuntimeError('Hardware GPU benchmark currently measures local solo only')
    if args.scenario not in ('scale-open','air-battle'):
        raise RuntimeError('Client GPU fixtures implemented only for scale-open and air-battle')
    if args.units not in (None,8192) or args.seed!=42:
        raise RuntimeError('Client currently has a fixed 8192-unit seed42 scenario; use --seed 42')
    frames=args.frames or 600
    if not 30<=frames<=10000:
        raise RuntimeError('GPU benchmark frames must be30..10000 (bounded profiler capacity)')
    if not shutil.which('glxinfo'):
        raise RuntimeError('glxinfo is required to verify hardware rendering')
    env=os.environ.copy(); env['RH_AUDIO_DEVICE']='null'
    context=subprocess.run(['glxinfo','-B'],env=env,capture_output=True,text=True,timeout=15,check=True).stdout
    if 'Accelerated: yes' not in context or any(name in context.lower() for name in ('llvmpipe','softpipe','software rasterizer')):
        raise RuntimeError('GPU benchmark requires a verified accelerated GL context; software rendering is a separate graphics test')
    exe=build('client'); folder=RUNS/('gpu-bench-'+uuid.uuid4().hex[:10]); folder.mkdir(parents=True)
    screenshot=folder/'final.ppm'; cmd=[str(exe),'--frames',str(frames),'--screenshot',str(screenshot),*client_view_args(args)]
    if args.tactical: cmd.append('--tactical')
    if args.weather: cmd+=['--weather',args.weather]
    if args.scenario=='air-battle':cmd+=['--scenario','air-battle']
    started=time.perf_counter(); run=subprocess.run(cmd,cwd=exe.parent,env=env,capture_output=True,text=True,timeout=max(60,frames/10),check=True)
    (folder/'client.log').write_text(run.stdout+run.stderr)
    metrics=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"client_metrics"')]
    if len(metrics)!=1 or metrics[0]['gpu_samples']==0:
        raise RuntimeError('Client did not report completed GPU timer samples')
    result={'scenario':('local-solo-air-battle' if args.scenario=='air-battle' else 'local-solo-initial-view'),'revision':exe.parent.name,'cpu_model':next((line.split(':',1)[1].strip() for line in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),
            'hardware':platform.platform(),'context':context,'resolution':[args.width or 1280,args.height or 720],'seed':42,
            'vertical_fov_degrees':args.fov if args.fov is not None else 'legacy projection1.05/1.87','mouse_sensitivity':args.sensitivity if args.sensitivity is not None else .002,'units_at_start':8192,'view':'tactical' if args.tactical else 'first-person','weather':args.weather or 'clear',
            'requested_frames':frames,'wall_seconds':time.perf_counter()-started,'metrics':metrics[0],
            'screenshot':str(screenshot),'screenshot_sha256':hashlib.sha256(screenshot.read_bytes()).hexdigest(),
            'telemetry':run.stdout,'coverage':{'replicated':0,'audio_device':'ALSA null','visible_individual_count':'unmeasured','detailed_counts':'final mesh telemetry only','threads':1,'vsync':True,'warmup_excluded':False,'resolution_limit':'Actual configured framebuffer; this scene alone does not establish dense-hotspot1080p acceptance','gpu_timing_scope':'draws; excludes presentation; last8 pending queries may be omitted','camera':('initial authored air-battle view; not SCALE-HOTSPOT acceptance' if args.scenario=='air-battle' else 'initial idle view only; not dense hotspot/front coverage')}}
    atomic(folder/'result.json',result); print(json.dumps(result,indent=2)); print('Report: '+str(folder/'result.json'))
def background(args):
    job=uuid.uuid4().hex[:12]; folder=RUNS/'jobs'/job; folder.mkdir(parents=True)
    argv=[a for a in sys.argv[1:] if a!='--background']
    snapshot=folder/'source'; snapshot.mkdir()
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    for rel in paths:
        if not rel: continue
        source=ROOT/rel
        if source.is_file():
            dest=snapshot/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
    data={'job_id':job,'revision':revision(),'source_snapshot':str(snapshot),'command':argv,'status':'running','log':str(folder/'job.log'),'result':str(folder/'result.json')}
    atomic(folder/'job.json',data)
    with (folder/'job.log').open('wb') as log:
        proc=subprocess.Popen([sys.executable,str(ROOT/'tools/dev.py'),'_worker',job,*argv],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    data['pid']=proc.pid; atomic(folder/'job.json',data); print(json.dumps(data,indent=2))
def worker(job,argv):
    folder=RUNS/'jobs'/job; begin=time.perf_counter()
    metadata=json.loads((folder/'job.json').read_text())
    env=os.environ.copy(); env['RED_HORIZON_SOURCE_COMMIT']=metadata['revision'].split('-')[0]; env['RED_HORIZON_NASM']=nasm()
    snapshot=folder/'source'
    code=subprocess.run([sys.executable,str(snapshot/'tools/dev.py'),*argv],cwd=snapshot,env=env).returncode
    atomic(folder/'result.json',{'job_id':job,'exit_code':code,'revision':metadata['revision'],'seconds':time.perf_counter()-begin,'status':'passed' if code==0 else 'failed'})
    return code
def jobs(job=None):
    folders=[RUNS/'jobs'/job] if job else sorted((RUNS/'jobs').glob('*'))
    for folder in folders:
        if not (folder/'job.json').exists(): raise RuntimeError('Unknown job ID')
        data=json.loads((folder/'job.json').read_text())
        if (folder/'result.json').exists(): data.update(json.loads((folder/'result.json').read_text()))
        print(json.dumps(data,indent=2))
def package():
    server=build('headless'); client=build('client'); coop=build('coop') if (ROOT/'src/net/coop_server.asm').exists() else None; rev=client.parent.name
    if server.parent.name!=rev or (coop and coop.parent.name!=rev): raise RuntimeError('Sources changed between package builds; rerun package')
    stage=BUILD/'packages'/rev; stage.mkdir(parents=True,exist_ok=True)
    shutil.copy2(server,stage/server.name); shutil.copy2(client,stage/client.name)
    if coop: shutil.copy2(coop,stage/coop.name)
    for folder in ('content','docs'):
        shutil.copytree(ROOT/folder,stage/folder,dirs_exist_ok=True)
    for name in ('README.md','THIRD_PARTY.md'): shutil.copy2(ROOT/name,stage/name)
    (stage/'run-client.sh').write_text('#!/bin/sh\ncd "$(dirname "$0")" || exit 1\nexec ./red-horizon "$@"\n')
    (stage/'run-client.sh').chmod(0o755)
    hashes={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    atomic(stage/'manifest.json',{'revision':rev,'platform':platform.platform(),'files':hashes,'runtime_dependencies':['glibc','GLFW>=3.3','OpenGL>=4.5','ALSA'],'license':'code pending owner approval; see asset credits'})
    archive=stage.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as tar: tar.add(stage,arcname='red-horizon')
    print(json.dumps({'package':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'revision':rev,'public_release':False}))
def main():
    if len(sys.argv)>1 and sys.argv[1]=='_worker': return worker(sys.argv[2],sys.argv[3:])
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    for name in ('doctor','configure','jobs','package'): sub.add_parser(name)
    q=sub.add_parser('collect'); q.add_argument('job_id')
    q=sub.add_parser('build'); q.add_argument('--target',choices=['headless','client','coop'],default='headless'); q.add_argument('--changed',action='store_true'); q.add_argument('--objects-only',action='store_true'); q.add_argument('--background',action='store_true')
    for name in ('run','server','bench'):
        q=sub.add_parser(name); q.add_argument('--scenario',choices=list(SCENARIOS),default='scale-open'); q.add_argument('--units',type=int); q.add_argument('--ticks',type=int,default=300); q.add_argument('--seed',type=int,default=1); q.add_argument('--realtime',action='store_true'); q.add_argument('--headless',action='store_true'); q.add_argument('--client',action='store_true'); q.add_argument('--frames',type=int); q.add_argument('--screenshot'); q.add_argument('--tactical',action='store_true'); q.add_argument('--weather',choices=['clear','overcast','rain','fog']); q.add_argument('--width',type=int); q.add_argument('--height',type=int); q.add_argument('--fov',type=float); q.add_argument('--sensitivity',type=float); q.add_argument('--connect'); q.add_argument('--port',type=int,default=7777); q.add_argument('--background',action='store_true')
    q=sub.add_parser('coop'); q.add_argument('--port',type=int,default=7777); q.add_argument('--ticks',type=int,default=0); q.add_argument('--units',type=int,default=8192); q.add_argument('--background',action='store_true')
    q=sub.add_parser('test'); q.add_argument('--suite',choices=['all','fast','simulation','operation','waypoints','terrain','navigation','aircraft','player','tactics','combat','vehicles','effects','reload','audio','network','tools','graphics','headless'],default='all'); q.add_argument('--extended',action='store_true'); q.add_argument('--background',action='store_true')
    q=sub.add_parser('reload'); q.add_argument('--background',action='store_true')
    args=p.parse_args()
    if getattr(args,'background',False): background(args); return 0
    if args.command in ('doctor','configure'): doctor()
    elif args.command=='build': build(args.target,args.objects_only)
    elif args.command in ('run','server','bench'):
        if (args.weather or client_view_args(args)) and not args.client: raise RuntimeError('--weather/--width/--height/--fov/--sensitivity require --client')
        if args.command=='bench' and args.client:
            gpu_benchmark(args)
        elif args.client:
            exe=build('client'); cmd=[str(exe),*client_view_args(args)];
            if args.frames: cmd+=['--frames',str(args.frames)]
            if args.screenshot: cmd+=['--screenshot',str(pathlib.Path(args.screenshot).resolve())]
            if args.tactical: cmd+=['--tactical']
            if args.weather: cmd+=['--weather',args.weather]
            if args.scenario=='air-battle':cmd+=['--scenario','air-battle']
            elif args.scenario!='scale-open':raise RuntimeError('Client scenario is implemented only for scale-open and air-battle')
            if args.connect and args.scenario=='air-battle':raise RuntimeError('air-battle initial cohort fixture is local-only')
            if args.connect: cmd+=['--connect',args.connect,'--port',str(args.port)]
            subprocess.run(cmd,cwd=exe.parent,check=True)
        else: run_headless(args,args.command=='bench')
    elif args.command=='coop':
        exe=build('coop'); execute([str(exe),'--port',str(args.port),'--ticks',str(args.ticks),'--units',str(args.units)],capture_output=False)
    elif args.command=='package': package()
    elif args.command=='jobs': jobs()
    elif args.command=='collect': jobs(args.job_id)
    elif args.command in ('test','reload'):
        os.environ.setdefault('RED_HORIZON_NASM',nasm())
        suite='reload' if args.command=='reload' else args.suite
        if suite in ('all','headless','fast','simulation','operation','waypoints','terrain','navigation','aircraft','player','tactics','combat','vehicles','effects'):
            exe=build('headless'); library=BUILD/'libsim.so'
            objects=[str(BUILD/(str(p.relative_to(ROOT)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (ROOT/'src'/folder).glob('*.asm')]
            probe=BUILD/'terrain_probe.o'
            execute([nasm(),'-f','elf64','tests/terrain_probe.asm','-o',str(probe)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects,str(probe),'-lm'])
            if suite in ('all','headless','fast'): execute([sys.executable,'tests/test_fast.py',str(exe),str(library)])
            if suite in ('all','headless','fast','simulation') and (ROOT/'tests/test_scenarios.py').exists():execute([sys.executable,'tests/test_scenarios.py',str(library)])
            if suite in ('all','headless','simulation'): execute([sys.executable,'tests/test_simulation.py',str(exe),str(library)])
            for test in ('operation','waypoints','terrain','navigation','aircraft','player','tactics','combat','vehicles'):
                if suite in ('all','headless','fast','simulation',test) and (ROOT/'tests'/('test_'+test+'.py')).exists(): execute([sys.executable,'tests/test_'+test+'.py',str(library)])
        if suite in ('all','headless','fast','effects') and (ROOT/'tests/test_effects.py').exists():
            effects=BUILD/'effects_test.o'; effects_library=BUILD/'libeffects.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/effects.asm'),'-o',str(effects)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(effects_library),*objects,str(probe),str(effects),'-lm'])
            execute([sys.executable,'tests/test_effects.py',str(effects_library)])
            trails=BUILD/'trails_test.o';trails_library=BUILD/'libtrails.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/air_trails.asm'),'-o',str(trails)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(trails_library),*objects,str(probe),str(trails),str(effects),'-lm'])
            execute([sys.executable,'tests/test_air_trails.py',str(trails_library)])
        if suite in ('all','headless','fast','reload'): execute([sys.executable,'tests/test_reload.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio'): execute([sys.executable,'tests/test_audio.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio') and (ROOT/'tests/test_audio_emitters.py').exists(): execute([sys.executable,'tests/test_audio_emitters.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio') and (ROOT/'tests/test_audio_battle.py').exists(): execute([sys.executable,'tests/test_audio_battle.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio') and (ROOT/'tests/test_footsteps.py').exists(): execute([sys.executable,'tests/test_footsteps.py','--nasm',nasm()])
        if suite in ('all','headless','network'): execute([sys.executable,'tests/test_net.py','--nasm',nasm()])
        if suite in ('all','headless','network') and (ROOT/'tests/test_coop.py').exists():
            server=build('coop')
            build('headless')
            adapter=BUILD/'net_client_test.o'; library=BUILD/'libcoopclient.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/net/client.asm'),'-o',str(adapter)])
            objects=[str(BUILD/(str(p.relative_to(ROOT)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (ROOT/'src'/folder).glob('*.asm')]
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects,str(adapter),'-lm'])
            execute([sys.executable,'tests/test_coop.py','--server',str(server),'--client-lib',str(library),*(['--extended'] if getattr(args,'extended',False) else [])])
            if (ROOT/'tests/test_coop_movement.py').exists():execute([sys.executable,'tests/test_coop_movement.py',str(server),str(library)])
            if (ROOT/'tests/test_net_projectiles.py').exists():execute([sys.executable,'tests/test_net_projectiles.py',str(library),str(server)])
            if (ROOT/'tests/test_net_events.py').exists(): execute([sys.executable,'tests/test_net_events.py',str(library)])
            if (ROOT/'tests/test_coop_combat.py').exists(): execute([sys.executable,'tests/test_coop_combat.py',str(server),str(library)])
        if suite in ('all','headless','tools') and (ROOT/'tests/test_tools.py').exists(): execute([sys.executable,'tests/test_tools.py','--nasm',nasm()])
        if suite in ('all','headless','fast'):
            execute([sys.executable,'tools/assets.py'])
            if (ROOT/'tools/audio_assets.py').exists(): execute([sys.executable,'tools/audio_assets.py'])
            if (ROOT/'tools/footstep_assets.py').exists(): execute([sys.executable,'tools/footstep_assets.py'])
        if suite in ('all','headless','fast') and (ROOT/'tests/test_mesh_assets.py').exists():
            mesh_object=BUILD/'mesh_asset_test.o'; mesh_library=BUILD/'libmeshassets.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/mesh_assets.asm'),'-o',str(mesh_object)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(mesh_library),str(mesh_object)])
            execute([sys.executable,'tests/test_mesh_assets.py',str(mesh_library),str(ROOT/'content/models/battle.rham')])
        if suite in ('all','headless','fast') and (ROOT/'tests/test_texture_assets.py').exists():
            environment_object=BUILD/'environment_asset_test.o'; environment_library=BUILD/'libenvironment.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/environment.asm'),'-o',str(environment_object)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(environment_library),str(environment_object),'-lGL'])
            execute([sys.executable,'tests/test_texture_assets.py',str(environment_library),str(ROOT/'content/textures/terrain.rhtx')])
        if suite in ('all','graphics'):
            client=build('client')
            execute([sys.executable,'tests/test_graphics.py',str(client)])
            view_library=BUILD/'libviewsettings.so'
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(view_library),str(BUILD/'src_render_view_settings.asm.o'),'-lm'])
            execute([sys.executable,'tests/test_view_settings_kernel.py',str(view_library)])
            execute([sys.executable,'tests/test_view_settings.py',str(client)])
            execute([sys.executable,'tests/test_client_view_projection.py',str(client)])
            if (ROOT/'tests/test_client_aircraft.py').exists(): execute([sys.executable,'tests/test_client_aircraft.py',str(client)])
            if (ROOT/'tests/test_client_environment.py').exists(): execute([sys.executable,'tests/test_client_environment.py',str(client)])
            if (ROOT/'tests/test_client_meshes.py').exists(): execute([sys.executable,'tests/test_client_meshes.py',str(client)])
            if (ROOT/'tests/test_client_shells.py').exists(): execute([sys.executable,'tests/test_client_shells.py',str(client)])
            if (ROOT/'tests/test_client_effects.py').exists(): execute([sys.executable,'tests/test_client_effects.py',str(client)])
            if (ROOT/'tests/test_client_gameplay.py').exists(): execute([sys.executable,'tests/test_client_gameplay.py',str(client)])
            if (ROOT/'tests/test_client_coop.py').exists(): execute([sys.executable,'tests/test_client_coop.py',str(client),str(build('coop'))])
    return 0
if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,subprocess.CalledProcessError,OSError) as e: print('ERROR: '+str(e),file=sys.stderr); sys.exit(1)
