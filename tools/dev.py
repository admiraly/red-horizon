#!/usr/bin/env python3
"""Development orchestration only. Game simulation lives in NASM objects."""
import argparse,math,fcntl,datetime,hashlib,json,os,pathlib,platform,shlex,shutil,subprocess,sys,tarfile,time,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
RUNS=ROOT/'runs'
SCENARIOS={'scale-open':8192,'scale-front':8192,'scale-hotspot':8192,'scale-stretch':16384,'air-battle':8192}
CLIENT_SCENARIOS=('scale-open','air-battle','scale-front','scale-hotspot')
LOCAL_SCENARIOS=('air-battle','scale-front','scale-hotspot')
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
    execute([sys.executable,'tools/terrain_surfaces.py','--check'], stdout=sys.stderr)
    execute([sys.executable,'tools/terrain_relief.py','--check'], stdout=sys.stderr)
    execute([sys.executable,'tools/terrain_grade.py','--check'], stdout=sys.stderr)
    execute([sys.executable,'tools/terrain_world.py','--check'], stdout=sys.stderr)
    execute([sys.executable,'tools/ground_content.py','--check'], stdout=sys.stderr)
    BUILD.mkdir(exist_ok=True)
    sources=[p for folder in ('sim','nav','ai','game') for p in (ROOT/'src'/folder).glob('*.asm')]
    if target=='headless': sources += [ROOT/'src/platform/linux/headless.asm']; libs=['-lm']; executable_name='red-horizon-server'
    elif target=='coop':
        sources += [ROOT/'src/net/coop_server.asm']; libs=['-lm']; executable_name='red-horizon-coop-server'
    elif target=='client':
        sources += list((ROOT/'src/render').glob('*.asm'))+list((ROOT/'src/audio').glob('*.asm'))+[ROOT/'src/platform/linux/client.asm',ROOT/'src/platform/linux/input_bindings.asm',ROOT/'src/platform/linux/frame_pacing.asm',ROOT/'src/platform/linux/listen_host.asm']+([ROOT/'src/net/client.asm'] if (ROOT/'src/net/client.asm').exists() else []); libs=['-Wl,-l:libglfw.so.3','-lGL','-lm','-lasound']; executable_name='red-horizon'
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
    if getattr(args,'census',False): raise RuntimeError('--census requires --client')
    scenario=args.scenario
    units=args.units if args.units is not None else SCENARIOS[scenario]
    if scenario in ('scale-front','scale-hotspot') and units<8192:
        raise RuntimeError(f'{scenario} requires at least 8192 units')
    exe=build('headless')
    cmd=[str(exe),'--units',str(units),'--ticks',str(args.ticks),'--seed',str(args.seed)]
    if scenario in LOCAL_SCENARIOS: cmd+=['--scenario',scenario]
    if args.realtime: cmd.append('--realtime')
    memory_path=RUNS/('memory-'+uuid.uuid4().hex[:10]+'.txt'); RUNS.mkdir(exist_ok=True)
    timer=pathlib.Path('/usr/bin/time')
    if timer.exists(): cmd=[str(timer),'-f','%M','-o',str(memory_path),*cmd]
    start=time.perf_counter(); r=subprocess.run(cmd,cwd=exe.parent,check=True,capture_output=True,text=True)
    peak_memory=int(memory_path.read_text().strip()) if memory_path.exists() else None
    if memory_path.exists(): memory_path.unlink()
    try: metrics=json.loads(r.stdout)
    except json.JSONDecodeError: raise RuntimeError('Runtime did not emit valid JSON: '+r.stdout[:1000])
    result={'scenario':scenario,'revision':exe.parent.name,'seed':args.seed,'wall_seconds':time.perf_counter()-start,'hardware':platform.platform(),'cpu_model':next((line.split(':',1)[1].strip() for line in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),'realtime':args.realtime,'runtime':metrics,'coverage':{'replicated':0,'visible':0,'gpu':'unmeasured','audio':'unmeasured','threads':1,'peak_runtime_rss_kib':peak_memory,'allocation_counts':{'sim_tick_heap':0,'basis':'source audit of static assembly simulation; process total unmeasured'},'navigation_backlog':metrics.get('navigation',{}).get('pending','unmeasured'),'network_bandwidth':'unmeasured in CPU-only headless benchmark'}}
    path=RUNS/('bench-'+uuid.uuid4().hex[:10]+'.json'); atomic(path,result); print(json.dumps(result,indent=2)); print('Report: '+str(path))
def client_view_args(args):
    view=[value for name in ('width','height','fov','sensitivity','bindings','frame_cap') if getattr(args,name,None) is not None
          for value in ('--'+name.replace('_','-'),str(pathlib.Path(args.bindings).resolve()) if name=='bindings' else str(getattr(args,name)))]
    return view+(['--hidden'] if getattr(args,'hidden',False) else [])+(['--no-vsync'] if getattr(args,'no_vsync',False) else [])
def client_scenario_args(args):
    if args.scenario not in CLIENT_SCENARIOS:
        raise RuntimeError('Client scenarios implemented only for '+', '.join(CLIENT_SCENARIOS))
    if args.connect and args.scenario in LOCAL_SCENARIOS:
        raise RuntimeError(f'{args.scenario} initial cohort fixture is local-only')
    if args.units not in (None,8192):
        raise RuntimeError('Client currently has a fixed 8192-unit scenario')
    return ['--scenario',args.scenario] if args.scenario in LOCAL_SCENARIOS else []
def census_requested(args):
    return bool(getattr(args,'census',False))
def validate_census_request(args,benchmark=False):
    if getattr(args,'census_map',None) and not census_requested(args):
        raise RuntimeError('--census-map requires --census')
    if not census_requested(args): return
    if not getattr(args,'client',True) or getattr(args,'headless',False):
        raise RuntimeError('--census requires --client without --headless')
    frames=args.frames if args.frames is not None else (600 if benchmark else None)
    if frames is None or not 1<=frames<=10000:
        raise RuntimeError('--census requires bounded --frames 1..10000 (GPU bench defaults to600)')
def visibility_report(stdout,args):
    """Validate actual final-frame ID capture; submitted instance counts are separate."""
    def unique_fields(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate field '+key)
            result[key]=value
        return result
    rows=[]
    for line in stdout.splitlines():
        if '"visibility_census"' not in line: continue
        try: row=json.loads(line,object_pairs_hook=unique_fields)
        except (json.JSONDecodeError,ValueError) as error:
            raise RuntimeError('Client reported malformed visibility_census JSON') from error
        rows.append(row)
    if len(rows)!=1:
        raise RuntimeError('Client must report exactly one visibility_census row')
    row=rows[0]
    if not isinstance(row,dict) or row.get('visibility_census') is not True:
        raise RuntimeError('Client reported invalid visibility_census marker')
    dimensions=(args.width or 1280,args.height or 720)
    for name,expected in zip(('width','height'),dimensions):
        if type(row.get(name)) is not int or row[name]!=expected:
            raise RuntimeError('visibility_census framebuffer dimensions do not match request')
    for name in ('visible_actors','visible_high','visible_low','visible_markers','individually_detailed_actors'):
        if type(row.get(name)) is not int or not 0<=row[name]<=32768:
            raise RuntimeError('visibility_census invalid actor count: '+name)
    if row['visible_actors']!=sum(row[name] for name in ('visible_high','visible_low','visible_markers')):
        raise RuntimeError('visibility_census visible group counts do not sum to actors')
    if row['individually_detailed_actors']!=row['visible_high']+row['visible_low']:
        raise RuntimeError('visibility_census detailed count does not match high/low models')
    if row['visible_actors']>dimensions[0]*dimensions[1]:
        raise RuntimeError('visibility_census actor count exceeds framebuffer pixels')
    for name in ('source_tick','invalid_codes'):
        if type(row.get(name)) is not int or not 0<=row[name]<=0xffffffff:
            raise RuntimeError('visibility_census invalid '+name)
    if row['invalid_codes']!=0:
        raise RuntimeError('visibility_census framebuffer contains invalid actor codes')
    if row.get('authority_readonly') is not True:
        raise RuntimeError('visibility_census must be authority read-only')
    hashes=[row.get(name) for name in ('authority_before','authority_after')]
    if any(not isinstance(value,str) or len(value)!=16 or any(c not in '0123456789abcdef' for c in value) for value in hashes) or hashes[0]!=hashes[1]:
        raise RuntimeError('visibility_census authority checksum is invalid or changed')
    cost=row.get('readback_reduce_ms')
    if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:
        raise RuntimeError('visibility_census invalid readback/reduction timing')
    return row
def gpu_benchmark(args):
    validate_census_request(args,benchmark=True)
    if getattr(args,'frame_cap',None) is not None and not 30<=args.frame_cap<=240:
        raise RuntimeError('--frame-cap must be30..240Hz')
    if not os.environ.get('DISPLAY'):
        raise RuntimeError('Hardware GPU benchmark requires an accessible X11/XWayland DISPLAY')
    if args.connect or getattr(args,'listen',False):
        raise RuntimeError('Hardware GPU benchmark currently measures local solo only')
    scenario_args=client_scenario_args(args)
    if args.units not in (None,8192) or args.seed!=42:
        raise RuntimeError('Client currently has a fixed 8192-unit seed42 scenario; use --seed 42')
    frames=args.frames if args.frames is not None else 600
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
    if census_requested(args): cmd.append('--census')
    if getattr(args,'census_map',None): cmd+=['--census-map',str(pathlib.Path(args.census_map).resolve())]
    if args.tactical: cmd.append('--tactical')
    if args.weather: cmd+=['--weather',args.weather]
    cmd+=scenario_args
    started=time.perf_counter(); run=subprocess.run(cmd,cwd=exe.parent,env=env,capture_output=True,text=True,timeout=max(60,frames/10),check=True)
    (folder/'client.log').write_text(run.stdout+run.stderr)
    metrics=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"client_metrics"')]
    if len(metrics)!=1 or metrics[0]['gpu_samples']==0:
        raise RuntimeError('Client did not report completed GPU timer samples')
    phases=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"client_phase_metrics"')]
    if {r.get('phase') for r in phases}!={'simulation','render_routes','audio_pump'} or len(phases)!=3:
        raise RuntimeError('Client CPU phase telemetry missing')
    if any(r.get('clock_errors')!=0 or r.get('samples')!=frames for r in phases):
        raise RuntimeError('Client CPU phase clock or sample count failed')
    presentation=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"client_presentation"')]
    if len(presentation)!=1: raise RuntimeError('Client must report one actual presentation-settings row')
    presented=presentation[0]
    expected=(int(getattr(args,'hidden',False)),int(not getattr(args,'no_vsync',False)),args.width or 1280,args.height or 720)
    if tuple(presented.get(k) for k in ('hidden','swap_interval_requested','viewport_width','viewport_height'))!=expected:
        raise RuntimeError('Client presentation settings disagree with requested benchmark')
    if (presented.get('framebuffer_width'),presented.get('framebuffer_height'))!=expected[2:]:
        raise RuntimeError('Actual framebuffer disagrees with the fixed render viewport')
    pacing=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"client_pacing"')]
    if len(pacing)!=1 or pacing[0].get('frame_cap_requested')!=(getattr(args,'frame_cap',None) or 0) or pacing[0].get('clock_errors')!=0:
        raise RuntimeError('Client frame pacing request or monotonic clock failed')
    renderers=[line.split('=',1)[1] for line in run.stdout.splitlines() if line.startswith('client_render_device=')]
    if len(renderers)!=1 or any(name in renderers[0].lower() for name in ('llvmpipe','softpipe','software rasterizer','swiftshader')):
        raise RuntimeError('Actual client renderer is missing or software-rendered')
    battle_metrics=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"battle_metrics"')]
    if len(battle_metrics)>1:
        raise RuntimeError('Client reported multiple battle_metrics rows')
    result={'scenario':('local-solo-'+args.scenario if args.scenario in LOCAL_SCENARIOS else 'local-solo-initial-view'),'revision':exe.parent.name,'cpu_model':next((line.split(':',1)[1].strip() for line in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),
            'hardware':platform.platform(),'context':context,'resolution':[args.width or 1280,args.height or 720],'seed':42,
            'vertical_fov_degrees':args.fov if args.fov is not None else 'legacy projection1.05/1.87','mouse_sensitivity':args.sensitivity if args.sensitivity is not None else .002,'units_at_start':8192,'view':'tactical' if args.tactical else 'first-person','weather':args.weather or 'clear',
            'requested_frames':frames,'phase_metrics':phases,'presentation':presented,'frame_pacing':pacing[0],'client_renderer':renderers[0],'wall_seconds':time.perf_counter()-started,'metrics':metrics[0],
            'screenshot':str(screenshot),'screenshot_sha256':hashlib.sha256(screenshot.read_bytes()).hexdigest(),
            'telemetry':run.stdout,'coverage':{'replicated':0,'audio_device':'ALSA null','audio_playback':'physical output and listening unverified','visible_individual_count':'unmeasured','detailed_counts':'final mesh telemetry only','simulation_threads':1,'graphics_driver_threads':'unmeasured','work_timing_scope':'events/simulation/render/swap; explicit cap waits excluded','vsync_requested':bool(presented['swap_interval_requested']),'window_hidden':bool(presented['hidden']),'swap_pacing_enforced':'unmeasured; requested interval is reported','warmup_excluded':False,'resolution_limit':'Actual configured framebuffer; this scene alone does not establish dense-hotspot1080p acceptance','gpu_timing_scope':'draws; excludes presentation; last8 pending queries may be omitted','camera':('player-following camera, initially authored '+args.scenario+' view; combat/redeployment can change view and density' if args.scenario in LOCAL_SCENARIOS else 'player-following initial deployment view; combat/redeployment can change view; not dense hotspot/front coverage')}}
    if battle_metrics: result['battle_metrics']=battle_metrics[0]
    if census_requested(args):
        census=visibility_report(run.stdout,args)
        result['visibility_census']=census
        result['coverage'].update(visible_individual_count=census['visible_actors'],
            individually_detailed_actors=census['individually_detailed_actors'],
            detailed_counts={'high':census['visible_high'],'low':census['visible_low'],'markers':census['visible_markers']},
            visibility_scope='unique actor IDs with surviving final-frame pixels in opaque world depth including weapon occlusion before translucent effects/HUD; high/low models individually detailed; markers separate; one frame, not peak',
            census_timing_scope='allocation at startup; final MRT drawing and pre-draw checksum included in final CPU frame; readback/reduction/blit/file/report excluded; separate cost measures readback/reduction only; last8 pending GPU queries may be omitted')
    if getattr(args,'census_map',None):
        actor_map=pathlib.Path(args.census_map).resolve()
        if actor_map.stat().st_size!=result['resolution'][0]*result['resolution'][1]*4:
            raise RuntimeError('visibility_census raw map size disagrees with framebuffer')
        result['actor_map']={'path':str(actor_map),'bytes':actor_map.stat().st_size,'sha256':hashlib.sha256(actor_map.read_bytes()).hexdigest(),'format':'little-endian R32UI; low16 bits actor ID+1; bits16..17 high1/low2/marker3'}
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
    env=os.environ.copy(); env['RED_HORIZON_SOURCE_COMMIT']=metadata['revision'].split('-')[0]
    try:
        env['RED_HORIZON_NASM']=nasm()
    except Exception as error:
        atomic(folder/'result.json',{'job_id':job,'exit_code':1,'revision':metadata['revision'],'seconds':time.perf_counter()-begin,'status':'failed','stage':'worker_setup','error':str(error)})
        raise
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
        q=sub.add_parser(name); q.add_argument('--scenario',choices=list(SCENARIOS),default='scale-open'); q.add_argument('--units',type=int); q.add_argument('--ticks',type=int,default=300); q.add_argument('--seed',type=int,default=1); q.add_argument('--realtime',action='store_true'); q.add_argument('--headless',action='store_true'); q.add_argument('--client',action='store_true'); q.add_argument('--frames',type=int); q.add_argument('--hidden',action='store_true'); q.add_argument('--no-vsync',action='store_true'); q.add_argument('--frame-cap',type=int); q.add_argument('--census',action='store_true'); q.add_argument('--census-map'); q.add_argument('--screenshot'); q.add_argument('--tactical',action='store_true'); q.add_argument('--weather',choices=['clear','overcast','rain','fog']); q.add_argument('--width',type=int); q.add_argument('--height',type=int); q.add_argument('--fov',type=float); q.add_argument('--sensitivity',type=float); q.add_argument('--bindings'); q.add_argument('--listen',action='store_true'); q.add_argument('--connect'); q.add_argument('--port',type=int,default=7777); q.add_argument('--background',action='store_true')
    q=sub.add_parser('coop'); q.add_argument('--scenario',choices=CLIENT_SCENARIOS,default='scale-open'); q.add_argument('--port',type=int,default=7777); q.add_argument('--ticks',type=int,default=0); q.add_argument('--units',type=int,default=8192); q.add_argument('--background',action='store_true')
    q=sub.add_parser('test'); q.add_argument('--suite',choices=['all','fast','simulation','operation','waypoints','terrain','navigation','aircraft','player','tactics','combat','vehicles','effects','hazards','ordnance','air-admission','crowd','controller-crowd','ground-motion','ground-surfaces','terrain-body','terrain-grade','ground-support','wrecks','reload','audio','network','tools','graphics','headless'],default='all'); q.add_argument('--extended',action='store_true'); q.add_argument('--background',action='store_true')
    q=sub.add_parser('reload'); q.add_argument('--background',action='store_true')
    args=p.parse_args()
    if args.command in ('run','server','bench'): validate_census_request(args,benchmark=args.command=='bench' and args.client)
    if getattr(args,'background',False): background(args); return 0
    if args.command in ('doctor','configure'): doctor()
    elif args.command=='build': build(args.target,args.objects_only)
    elif args.command in ('run','server','bench'):
        if (args.listen or args.weather or client_view_args(args)) and not args.client: raise RuntimeError('--weather/--width/--height/--fov/--sensitivity/--bindings/--hidden/--no-vsync/--frame-cap/--listen require --client')
        if args.command=='bench' and args.client:
            gpu_benchmark(args)
        elif args.client:
            scenario_args=client_scenario_args(args)
            exe=build('client');
            if args.listen:
                if args.connect: raise RuntimeError('--listen cannot combine with --connect')
                build('coop')
            cmd=[str(exe),*client_view_args(args),*(['--listen'] if args.listen else [])];
            if args.frames: cmd+=['--frames',str(args.frames)]
            if census_requested(args): cmd.append('--census')
            if args.census_map: cmd+=['--census-map',str(pathlib.Path(args.census_map).resolve())]
            if args.screenshot: cmd+=['--screenshot',str(pathlib.Path(args.screenshot).resolve())]
            if args.tactical: cmd+=['--tactical']
            if args.weather: cmd+=['--weather',args.weather]
            cmd+=scenario_args
            if args.connect: cmd+=['--connect',args.connect,'--port',str(args.port)]
            if census_requested(args):
                run=subprocess.run(cmd,cwd=exe.parent,check=True,capture_output=True,text=True)
                print(run.stdout,end=''); print(run.stderr,end='',file=sys.stderr)
                visibility_report(run.stdout,args)
            else: subprocess.run(cmd,cwd=exe.parent,check=True)
        else: run_headless(args,args.command=='bench')
    elif args.command=='coop':
        exe=build('coop'); execute([str(exe),'--port',str(args.port),'--ticks',str(args.ticks),'--units',str(args.units),'--scenario',args.scenario],capture_output=False)
    elif args.command=='package': package()
    elif args.command=='jobs': jobs()
    elif args.command=='collect': jobs(args.job_id)
    elif args.command in ('test','reload'):
        os.environ.setdefault('RED_HORIZON_NASM',nasm())
        BUILD.mkdir(exist_ok=True)
        suite='reload' if args.command=='reload' else args.suite
        if suite in ('all','headless','fast','simulation','operation','waypoints','terrain','navigation','aircraft','player','tactics','combat','vehicles','effects','hazards','ordnance','air-admission','crowd','controller-crowd','ground-motion','ground-surfaces','terrain-body','terrain-grade','ground-support','graphics','wrecks'):
            exe=build('headless'); library=BUILD/'libsim.so'
            objects=[str(BUILD/(str(p.relative_to(ROOT)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (ROOT/'src'/folder).glob('*.asm')]
            probe=BUILD/'terrain_probe.o'
            execute([nasm(),'-f','elf64','tests/terrain_probe.asm','-o',str(probe)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects,str(probe),'-lm'])
            if suite in ('all','headless','fast'): execute([sys.executable,'tests/test_fast.py',str(exe),str(library)])
            if suite in ('all','headless','fast','simulation') and (ROOT/'tests/test_scenarios.py').exists():execute([sys.executable,'tests/test_scenarios.py',str(library)])
            if suite in ('all','headless','fast','simulation') and (ROOT/'tests/test_dense_scenarios.py').exists():execute([sys.executable,'tests/test_dense_scenarios.py',str(library)])
            if suite in ('all','headless','fast','simulation','player'):execute([sys.executable,'tests/test_squad_deployment.py',str(library)])
            if suite in ('all','headless','fast','simulation','player'):
                execute([sys.executable,'tests/test_deployment_blast.py',str(library)])
                execute([sys.executable,'tests/test_deployment_blast_control.py'])
            if suite in ('all','headless','simulation'): execute([sys.executable,'tests/test_simulation.py',str(exe),str(library)])
            if suite in ('all','headless','fast','simulation','aircraft'): execute([sys.executable,'tests/test_bomb_release.py',str(library)])
            for test in ('operation','waypoints','terrain','navigation','aircraft','player','tactics','combat','vehicles'):
                if suite in ('all','headless','fast','simulation',test) and (ROOT/'tests'/('test_'+test+'.py')).exists(): execute([sys.executable,'tests/test_'+test+'.py',str(library)])
        if suite in ('all','headless','fast','simulation','aircraft'):
            execute([sys.executable,'tests/test_air_gun_nose.py',str(library)])
            execute([sys.executable,'tests/test_air_gun_intercept.py'])
            execute([sys.executable,'tests/test_air_gunnery.py'])
            execute([sys.executable,'tests/test_air_bank.py'])
            execute([sys.executable,'tests/test_air_vertical.py'])
            execute([sys.executable,'tests/test_air_threats.py'])
            execute([sys.executable,'tests/test_air_observation.py'])
            execute([sys.executable,'tests/test_air_pursuit.py'])
            execute([sys.executable,'tests/test_air_pursuit_flight.py'])
            execute([sys.executable,'tests/test_air_recovery.py'])
            execute([sys.executable,'tests/test_air_holding.py'])
            execute([sys.executable,'tests/test_air_separation.py'])
            execute([sys.executable,'tests/test_air_crash.py'])
            execute([sys.executable,'tests/test_air_crash_remote.py'])
            execute([sys.executable,'tests/test_air_world.py',str(library)])
            execute([sys.executable,'tests/test_air_flight_trace.py',str(library)])
            if suite in ('all','headless') and getattr(args,'extended',False):execute([sys.executable,'tests/test_air_world_bounds.py',str(library)])
            execute([sys.executable,'tests/test_air_strike.py',str(library)])
            execute([sys.executable,'tests/test_air_escort.py',str(library)])
        if suite in ('all','headless','fast','simulation','tactics'):
            execute([sys.executable,'tests/test_company_assault.py',str(library)])
            execute([sys.executable,'tests/test_company_control.py'])
            execute([sys.executable,'tests/test_company_transfer.py'])
            execute([sys.executable,'tests/test_company_follow.py'])
            execute([sys.executable,'tests/test_company_defend.py'])
            execute([sys.executable,'tests/test_company_supply.py',str(ROOT)])
            execute([sys.executable,'tests/test_depot_supply.py',str(ROOT)])
            execute([sys.executable,'tests/test_command_wheel.py'])
            execute([sys.executable,'tests/test_input_bindings.py'])
            execute([sys.executable,'tests/test_input_frames.py'])
        if suite in ('all','headless','fast','simulation','player','combat'):
            execute([sys.executable,'tests/test_player_ammunition.py',str(library)])
            execute([sys.executable,'tests/test_player_ammunition_report.py',str(library)])
            execute([sys.executable,'tests/test_player_ammunition_abi.py',str(library)])
            execute([sys.executable,'tests/test_player_threat_ammunition.py',str(library)])
            execute([sys.executable,'tests/test_infantry_cadence.py',str(library)])
            execute([sys.executable,'tests/test_infantry_human_targets.py',str(library)])
            execute([sys.executable,'tests/test_infantry_aim.py',str(library)])
            execute([sys.executable,'tests/test_infantry_aim_motion.py',str(library)])
            execute([sys.executable,'tests/test_model_aim_mask.py'])
            execute([sys.executable,'tests/test_infantry_shot_events.py',str(library)])
            execute([sys.executable,'tests/test_player_blast.py',str(library)])
            execute([sys.executable,'tests/test_player_blast.py',str(library),'--artillery'])
            execute([sys.executable,'tests/test_player_bomb.py',str(library)])
            execute([sys.executable,'tests/test_player_blast_gates.py',str(library)])
            execute([sys.executable,'tests/test_player_blast_abi.py',str(library)])
            execute([sys.executable,'tests/test_tick_publication.py',str(library)])
        if suite in ('all','headless','fast','simulation','combat'):
            execute([sys.executable,'tests/test_infantry_ammunition.py',str(library)])
            execute([sys.executable,'tests/test_depot_ammunition.py'])
            execute([sys.executable,'tests/test_infantry_resupply.py',str(library)])
            execute([sys.executable,'tests/test_infantry_rounds.py',str(library)])
            execute([sys.executable,'tests/test_supply_routes.py',str(library)])
            execute([sys.executable,'tests/test_supply_route_interruptions.py',str(library)])
            execute([sys.executable,'tests/test_infantry_weapon_abi.py'])
            execute([sys.executable,'tests/test_ground_acquisition.py',str(library)])
            execute([sys.executable,'tests/test_ground_target_selection.py',str(library)])
        if suite in ('all','headless','player'):
            execute([sys.executable,'tests/test_site_deployment.py',str(library)])
        if suite in ('all','headless','fast','simulation','navigation'):
            execute([sys.executable,'tests/test_wreck_nav_outcomes.py',str(library)])
            execute([sys.executable,'tests/test_wreck_nav_contract.py',str(library)])
        if suite in ('all','headless','combat'):
            execute([sys.executable,'tests/test_shell_contact.py',str(library)])
            execute([sys.executable,'tests/test_world_contact.py'])
            execute([sys.executable,'tests/test_world_los.py'])
            execute([sys.executable,'tests/test_world_los_outcomes.py',str(library)])
            execute([sys.executable,'tests/test_wreck_cover_outcomes.py',str(library)])
            execute([sys.executable,'tests/test_blast_visibility_batch.py'])
            execute([sys.executable,'tests/test_projectile_contact_type.py'])
            execute([sys.executable,'tests/test_world_contact_outcomes.py',str(library)])
        if suite in ('all','headless','terrain-body','vehicles','wrecks'):
            execute([sys.executable,'tests/test_world_body.py'])
            execute([sys.executable,'tests/test_world_body_outcomes.py',str(library)])
            execute([sys.executable,'tests/test_wreck_movement_outcomes.py',str(library)])
            execute([sys.executable,'tests/test_wreck_prediction.py',str(library)])
            body_probe=BUILD/'world_body_probe.o'; body_library=BUILD/'libworldbodystep.so'
            execute([nasm(),'-f','elf64','tests/probe_world_body.asm','-o',str(body_probe)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(body_library),*objects,str(body_probe),'-lm'])
            execute([sys.executable,'tests/test_world_body_step.py',str(body_library)])
        if suite in ('all','headless','terrain','combat'):
            execute([sys.executable,'tests/test_terrain_ground_query.py'])
            execute([sys.executable,'tests/test_terrain_solid_query.py'])
        if suite in ('all','headless','fast','simulation','terrain','vehicles','ground-support'):
            execute([sys.executable,'tests/test_ground_eye_outcomes.py',str(library)])
        if suite in ('all','headless','fast','simulation','combat','vehicles','wrecks'):
            execute([sys.executable,'tests/test_wrecks.py'])
            execute([sys.executable,'tests/test_wreck_remote.py'])
            execute([sys.executable,'tests/test_segment_box.py'])
            execute([sys.executable,'tests/test_segment_sphere.py'])
            execute([sys.executable,'tests/test_wreck_query.py'])
            execute([sys.executable,'tests/test_wreck_body_query.py'])
            execute([sys.executable,'tests/test_wreck_query_context.py'])
            execute([sys.executable,'tests/test_wreck_outcomes.py',str(library)])
            if getattr(args,'extended',False) or suite=='wrecks':execute([sys.executable,'tests/test_wreck_scale.py',str(library)])
        if suite in ('all','headless','terrain','vehicles','ground-support'):
            execute([sys.executable,'tests/test_ground_support.py'])
            execute([sys.executable,'tests/test_ground_contact.py'])
            execute([sys.executable,'tests/test_suspension.py'])
            execute([sys.executable,'tests/test_ground_visual.py'])
            execute([sys.executable,'tests/test_ground_eye.py'])
        if suite in ('all','headless','simulation','terrain','vehicles','ground-motion','ground-surfaces','terrain-grade'):
            execute([sys.executable,'tests/test_terrain_relief.py'])
            execute([sys.executable,'tests/test_terrain_grade.py'])
            execute([sys.executable,'tests/test_terrain_height.py'])
            if (ROOT/'tests/test_terrain_grade_outcomes.py').exists(): execute([sys.executable,'tests/test_terrain_grade_outcomes.py',str(library)])
        if suite in ('all','headless','fast','simulation','terrain','vehicles','ground-motion','ground-surfaces'):
            execute([sys.executable,'tests/test_terrain_surface.py'])
            execute([sys.executable,'tests/test_ground_surface_outcomes.py',str(library)])
        if suite in ('all','headless','fast','simulation','vehicles','ground-motion','ground-surfaces'):
            execute([sys.executable,'tests/test_ground_motion.py'])
            execute([sys.executable,'tests/test_ground_motion_outcomes.py',str(library)])
            if getattr(args,'extended',False): execute([sys.executable,'tests/test_ground_motion_outcomes.py',str(library),'--legacy'])
        if suite in ('all','headless','fast','simulation','ordnance'):
            execute([sys.executable,'tests/test_ordnance_admission.py'])
            execute([sys.executable,'tests/test_ordnance_fairness.py',str(library)])
            if getattr(args,'extended',False): execute([sys.executable,'tests/test_ordnance_fairness.py',str(library),'--legacy'])
        if suite in ('all','headless','fast','simulation','aircraft','air-admission'):
            execute([sys.executable,'tests/test_air_admission.py'])
            execute([sys.executable,'tests/test_air_admission_fairness.py',str(library)])
            if getattr(args,'extended',False): execute([sys.executable,'tests/test_air_admission_fairness.py',str(library),'--legacy'])
        if suite in ('all','headless','fast','simulation','navigation','crowd','controller-crowd','ground-motion','ground-surfaces'):
            execute([sys.executable,'tests/test_crowd.py'])
            execute([sys.executable,'tests/test_crowd_outcomes.py',str(library)])
            if getattr(args,'extended',False): execute([sys.executable,'tests/test_crowd_outcomes.py',str(library),'--legacy'])
        if suite in ('all','headless','fast','simulation','navigation','player','vehicles','crowd','controller-crowd','ground-motion','ground-surfaces'):
            execute([sys.executable,'tests/test_controller_crowd_outcomes.py',str(library)])
            if getattr(args,'extended',False): execute([sys.executable,'tests/test_controller_crowd_outcomes.py',str(library),'--legacy'])
            if getattr(args,'extended',False) and suite in ('all','headless','controller-crowd','ground-motion','ground-surfaces'): execute([sys.executable,'tools/bench_controllers.py',str(library)])
        if suite in ('all','headless','fast','simulation','terrain','navigation','player','vehicles','ground-motion','ground-surfaces','terrain-body','terrain-grade'):
            execute([sys.executable,'tests/test_terrain_body.py'])
            execute([sys.executable,'tests/test_terrain_body_outcomes.py',str(library)])
            if getattr(args,'extended',False): execute([sys.executable,'tests/test_terrain_body_outcomes.py',str(library),'--legacy'])
        if suite in ('all','headless','fast','simulation','hazards'):
            hazard_probe=BUILD/'hazard_steering_probe.o'
            hazard_library=BUILD/'libhazards.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'tests/hazard_steering_probe.asm'),'-o',str(hazard_probe)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(hazard_library),*objects,str(probe),str(hazard_probe),'-lm'])
            for test in ('hazards','hazard_steering','hazard_outcomes'):
                execute([sys.executable,'tests/test_'+test+'.py',str(hazard_library)])
            execute([sys.executable,'tests/test_hazard_warning.py','--nasm',nasm()])
            execute([sys.executable,'tests/test_hazard_budget.py','--nasm',nasm()])
        if suite in ('all','headless','fast','effects') and (ROOT/'tests/test_effects.py').exists():
            effects=BUILD/'effects_test.o'; effects_library=BUILD/'libeffects.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/effects.asm'),'-o',str(effects)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(effects_library),*objects,str(probe),str(effects),'-lm'])
            execute([sys.executable,'tests/test_effects.py',str(effects_library)])
            execute([sys.executable,'tests/test_air_burst.py',str(effects_library)])
            lights=BUILD/'event_lights_test.o'; lights_library=BUILD/'libeventlights.so'; lights_probe=BUILD/'event_lights_probe.o'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/event_lights.asm'),'-o',str(lights)])
            execute([nasm(),'-f','elf64',str(ROOT/'tests/probe_event_lights.asm'),'-o',str(lights_probe)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(lights_library),*objects,str(probe),str(effects),str(lights),str(lights_probe),'-lm','-lGL'])
            execute([sys.executable,'tests/test_event_lights.py',str(lights_library)])
            trails=BUILD/'trails_test.o';trails_library=BUILD/'libtrails.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/air_trails.asm'),'-o',str(trails)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(trails_library),*objects,str(probe),str(trails),str(effects),'-lm'])
            execute([sys.executable,'tests/test_air_trails.py',str(trails_library)])
        if suite in ('all','headless','fast','reload'): execute([sys.executable,'tests/test_reload.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio'): execute([sys.executable,'tests/test_audio.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio'): execute([sys.executable,'tests/test_aircraft_audio.py'])
        if suite in ('all','headless','fast','audio') and (ROOT/'tests/test_audio_emitters.py').exists(): execute([sys.executable,'tests/test_audio_emitters.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio') and (ROOT/'tests/test_audio_battle.py').exists(): execute([sys.executable,'tests/test_audio_battle.py','--nasm',nasm()])
        if suite in ('all','headless','fast','audio') and (ROOT/'tests/test_footsteps.py').exists(): execute([sys.executable,'tests/test_footsteps.py','--nasm',nasm()])
        if suite in ('all','headless','network'):
            execute([sys.executable,'tests/test_projectile_priority.py'])
            execute([sys.executable,'tests/test_net.py','--nasm',nasm()])
        if suite in ('all','headless','network') and (ROOT/'tests/test_coop.py').exists():
            server=build('coop')
            build('headless')
            adapter=BUILD/'net_client_test.o'; library=BUILD/'libcoopclient.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/net/client.asm'),'-o',str(adapter)])
            objects=[str(BUILD/(str(p.relative_to(ROOT)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (ROOT/'src'/folder).glob('*.asm')]
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects,str(adapter),'-lm'])
            execute([sys.executable,'tests/test_coop.py','--server',str(server),'--client-lib',str(library),*(['--extended'] if getattr(args,'extended',False) else [])])
            execute([sys.executable,'tests/test_coop_scenarios.py',str(server),str(library)])
            execute([sys.executable,'tests/test_company_control_network.py',str(server)])
            execute([sys.executable,'tests/test_company_remote.py',str(library),str(server)])
            execute([sys.executable,'tests/test_company_supply_network.py',str(library),str(server)])
            execute([sys.executable,'tests/test_company_transfer_network.py',str(server),str(library)])
            execute([sys.executable,'tests/test_company_follow_network.py',str(server),str(library)])
            execute([sys.executable,'tests/test_company_defend_network.py',str(server),str(library)])
            execute([sys.executable,'tests/test_infantry_ammunition_network.py',str(server),str(library)])
            execute([sys.executable,'tests/test_infantry_ammunition_network.py',str(server),str(library),'--resupply-encounter'])
            execute([sys.executable,'tests/test_supply_route_network.py',str(server)])
            execute([sys.executable,'tests/test_player_ammunition_network.py',str(server),str(library)])
            execute([sys.executable,'tests/test_player_blast_network.py',str(server),str(library)])
            execute([sys.executable,'tests/test_infantry_event_network.py',str(server),str(library)])
            execute([sys.executable,'tests/test_infantry_aim_network.py',str(library)])
            execute([sys.executable,'tests/test_infantry_aim_delivery.py',str(server),str(library)])
            execute([sys.executable,'tests/test_player_ammunition_udp_faults.py',str(library)])
            if (ROOT/'tests/test_coop_movement.py').exists():execute([sys.executable,'tests/test_coop_movement.py',str(server),str(library)])
            if (ROOT/'tests/test_net_projectiles.py').exists():execute([sys.executable,'tests/test_net_projectiles.py',str(library),str(server)])
            if (ROOT/'tests/test_net_events.py').exists(): execute([sys.executable,'tests/test_net_events.py',str(library)])
            if (ROOT/'tests/test_coop_combat.py').exists(): execute([sys.executable,'tests/test_coop_combat.py',str(server),str(library)])
            execute([sys.executable,'tests/test_ground_network.py',str(library),str(server)])
            execute([sys.executable,'tests/test_wreck_network.py',str(library),str(server),*(['--extended'] if getattr(args,'extended',False) else [])])
            execute([sys.executable,'tests/test_air_crash_network.py',str(library),str(server),*(['--extended'] if getattr(args,'extended',False) else [])])
            execute([sys.executable,'tests/test_air_crash_stream.py'])
        if suite in ('all','headless','tools'):
            execute([sys.executable,'tests/test_dense_driver.py'])
            if (ROOT/'tests/test_tools.py').exists(): execute([sys.executable,'tests/test_tools.py','--nasm',nasm()])
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
            environment_probe=BUILD/'environment_asset_probe.o'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/environment.asm'),'-o',str(environment_object)])
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'tests/probe_environment_asset.asm'),'-o',str(environment_probe)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(environment_library),str(environment_object),str(environment_probe),'-lGL'])
            execute([sys.executable,'tests/test_texture_assets.py',str(environment_library),str(ROOT/'content/textures/terrain.rhtx')])
        if suite == 'ground-support':
            client=build('client')
            execute([sys.executable,'tests/test_support_gl.py',str(client),str(library)])
            execute([sys.executable,'tests/test_infantry_aim_gl.py',str(client)])
            execute([sys.executable,'tests/test_support_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_wreck_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_wreck_client.py',str(client),str(library),'--udp'])
            execute([sys.executable,'tests/test_air_crash_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_air_crash_client.py',str(client),str(library),'--udp'])
            execute([sys.executable,'tests/test_air_crash_plume_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_air_crash_plume_client.py',str(client),str(library),'--udp'])
            execute([sys.executable,'tests/test_ground_eye_client.py',str(client),str(build('coop'))])
            execute([sys.executable,'tests/test_ground_gl.py',str(client)])
        if suite in ('all','graphics'):
            execute([sys.executable,'tests/test_battle_metrics.py'])
            census_object=BUILD/'visibility_census_test.o'; census_probe=BUILD/'visibility_probe.o'; census_library=BUILD/'libvisibility.so'
            execute([nasm(),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/render/visibility_census.asm'),'-o',str(census_object)])
            execute([nasm(),'-f','elf64',str(ROOT/'tests/probe_visibility_reduce.asm'),'-o',str(census_probe)])
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(census_library),str(census_object),str(census_probe),'-lGL'])
            execute([sys.executable,'tests/test_visibility_reduce.py',str(census_library)])
            execute([sys.executable,'tests/test_visibility_framebuffer.py',str(census_library)])
            client=build('client')
            execute([sys.executable,'tests/test_graphics.py',str(client)])
            execute([sys.executable,'tests/test_client_presentation.py',str(client)])
            execute([sys.executable,'tests/test_frame_pacing.py'])
            build('coop')
            execute([sys.executable,'tests/test_listen_host.py',str(client)])
            execute([sys.executable,'tests/test_mesh_material_gl.py',str(client)])
            execute([sys.executable,'tests/test_hdr_gl.py',str(client)])
            execute([sys.executable,'tests/test_event_lights_gl.py',str(client)])
            execute([sys.executable,'tests/test_wreck_instance.py'])
            execute([sys.executable,'tests/test_air_crash_instance.py'])
            execute([sys.executable,'tests/test_air_crash_plume.py'])
            execute([sys.executable,'tests/test_air_crash_plume_gl.py',str(client)])
            execute([sys.executable,'tests/test_hazard_warning_gl.py',str(client)])
            execute([sys.executable,'tests/test_census_cli.py',str(client)])
            view_library=BUILD/'libviewsettings.so'
            execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(view_library),str(BUILD/'src_render_view_settings.asm.o'),'-lm'])
            execute([sys.executable,'tests/test_view_settings_kernel.py',str(view_library)])
            execute([sys.executable,'tests/test_view_settings.py',str(client)])
            execute([sys.executable,'tests/test_client_view_projection.py',str(client)])
            execute([sys.executable,'tests/test_dense_client.py',str(client)])
            if (ROOT/'tests/test_visibility_gl.py').exists():execute([sys.executable,'tests/test_visibility_gl.py',str(client)])
            if (ROOT/'tests/test_client_aircraft.py').exists(): execute([sys.executable,'tests/test_client_aircraft.py',str(client)])
            execute([sys.executable,'tests/test_aircraft_audio_client.py',str(client),str(build('coop'))])
            execute([sys.executable,'tests/test_air_burst_gl.py',str(client)])
            execute([sys.executable,'tests/test_projected_detail_gl.py',str(client)])
            execute([sys.executable,'tests/test_ground_gl.py',str(client)])
            execute([sys.executable,'tests/test_road_gl.py',str(client)])
            execute([sys.executable,'tests/test_relief_gl.py',str(client)])
            execute([sys.executable,'tests/test_support_gl.py',str(client),str(library)])
            execute([sys.executable,'tests/test_infantry_aim_gl.py',str(client)])
            execute([sys.executable,'tests/test_support_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_wreck_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_wreck_client.py',str(client),str(library),'--udp'])
            execute([sys.executable,'tests/test_air_crash_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_air_crash_client.py',str(client),str(library),'--udp'])
            execute([sys.executable,'tests/test_air_crash_plume_client.py',str(client),str(library)])
            execute([sys.executable,'tests/test_air_crash_plume_client.py',str(client),str(library),'--udp'])
            execute([sys.executable,'tests/test_ground_eye_client.py',str(client),str(build('coop'))])
            if (ROOT/'tests/test_client_environment.py').exists(): execute([sys.executable,'tests/test_client_environment.py',str(client)])
            if (ROOT/'tests/test_client_meshes.py').exists(): execute([sys.executable,'tests/test_client_meshes.py',str(client)])
            if (ROOT/'tests/test_client_shells.py').exists(): execute([sys.executable,'tests/test_client_shells.py',str(client)])
            if (ROOT/'tests/test_client_effects.py').exists(): execute([sys.executable,'tests/test_client_effects.py',str(client)])
            execute([sys.executable,'tests/test_client_infantry.py',str(client)])
            execute([sys.executable,'tests/test_client_infantry_aim.py',str(client)])
            execute([sys.executable,'tests/test_infantry_presentation.py'])
            if (ROOT/'tests/test_client_gameplay.py').exists(): execute([sys.executable,'tests/test_client_gameplay.py',str(client)])
            execute([sys.executable,'tests/test_client_feedback.py',str(client)])
            execute([sys.executable,'tests/test_client_player_blast.py',str(client)])
            execute([sys.executable,'tests/test_player_ammunition_hud.py',str(client)])
            execute([sys.executable,'tests/test_player_ammunition_hud.py',str(client),'--small'])
            execute([sys.executable,'tests/test_client_company.py',str(client),'--between-frame-tap','--tap-only'])
            execute([sys.executable,'tests/test_client_company.py',str(client)])
            execute([sys.executable,'tests/test_quit_event.py',str(client)])
            execute([sys.executable,'tests/test_client_command_wheel.py',str(client)])
            execute([sys.executable,'tests/test_client_command_wheel.py',str(client),'--small'])
            execute([sys.executable,'tests/test_client_bindings.py',str(client)])
            execute([sys.executable,'tests/test_client_bindings.py',str(client),'--supply','--depots'])
            execute([sys.executable,'tests/test_bindings_cli.py',str(client)])
            if (ROOT/'tests/test_client_coop.py').exists():
                server=build('coop')
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server)])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--timeout'])
                execute([sys.executable,'tests/test_player_ammunition_hud.py',str(client),str(server),'--udp'])
                execute([sys.executable,'tests/test_player_ammunition_hud.py',str(client),str(server),'--udp','--small'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--supply','--depots'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--supply','--supply-small','--depots'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--transfer'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--transfer-fault'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--retreat'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--follow'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--wheel-fault'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--transfer-hud'])
                execute([sys.executable,'tests/test_client_coop.py',str(client),str(server),'--transfer-hud','--mixed-bindings','--transfer-fault'])
    return 0
if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,subprocess.CalledProcessError,OSError) as e: print('ERROR: '+str(e),file=sys.stderr); sys.exit(1)
