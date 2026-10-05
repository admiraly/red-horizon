#!/usr/bin/env python3
"""Development orchestration only. Game simulation lives in NASM objects."""
import argparse,fcntl,datetime,hashlib,json,os,pathlib,platform,shutil,subprocess,sys,time,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
RUNS=ROOT/'runs'
SCENARIOS={'scale-open':8192,'scale-front':8192,'scale-hotspot':8192,'scale-stretch':16384,'firing-range':128}
def revision():
    sha=os.environ.get('RED_HORIZON_SOURCE_COMMIT') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    # Hash actual authored inputs too, including uncommitted sources.
    h=hashlib.sha256()
    for folder in ('src','shaders','content','schemas','tools'):
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
    for tool in ('gcc','make','ninja','gh'): data[tool]=shutil.which(tool)
    try: data['nasm']=subprocess.check_output([nasm(),'-v'],text=True).strip()
    except RuntimeError as e: data['nasm']=str(e)
    if pathlib.Path('/proc/cpuinfo').exists():
        data['cpu']=next((l.split(':',1)[1].strip() for l in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')),'unknown')
    print(json.dumps(data,indent=2)); atomic(RUNS/'doctor.json',data)
def build(target):
    BUILD.mkdir(exist_ok=True)
    with (BUILD/'build.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return build_locked(target)
def build_locked(target):
    start=time.perf_counter(); tool=nasm(); execute([sys.executable,'tools/schema.py'])
    BUILD.mkdir(exist_ok=True)
    sources=list((ROOT/'src/sim').glob('*.asm'))
    if target=='headless': sources += [ROOT/'src/platform/linux/headless.asm']; libs=[]; name='red-horizon-server'
    elif target=='client':
        sources += list((ROOT/'src/render').glob('*.asm'))+[ROOT/'src/platform/linux/client.asm']; libs=['-Wl,-l:libglfw.so.3','-lGL','-lm']; name='red-horizon'
    else: raise RuntimeError('Unsupported target')
    if not sources or any(not s.exists() for s in sources): raise RuntimeError(f'{target} sources not integrated yet')
    objects=[]; assembled=0
    # Include hashes ensure generated layout or shader edits invalidate appropriate objects.
    includes=list((ROOT/'schemas').glob('*'))+list((ROOT/'shaders').glob('*'))
    for s in sources:
        obj=BUILD/(str(s.relative_to(ROOT)).replace('/','_')+'.o'); dep=obj.with_suffix('.sha256')
        digest=hashlib.sha256(s.read_bytes()+b''.join(p.read_bytes() for p in includes if p.is_file())).hexdigest()
        if not obj.exists() or not dep.exists() or dep.read_text()!=digest:
            execute([tool,'-f','elf64','-g','-F','dwarf','-I',str(ROOT)+'/',str(s),'-o',str(obj)]); dep.write_text(digest); assembled+=1
        objects.append(obj)
    exe=BUILD/name
    signature=hashlib.sha256(b''.join(o.read_bytes() for o in objects)+repr(libs).encode()).hexdigest()
    linkstamp=exe.with_suffix('.linkhash')
    if not exe.exists() or not linkstamp.exists() or linkstamp.read_text()!=signature:
        temporary=exe.with_suffix('.new'); execute(['gcc','-no-pie','-Wl,-z,noexecstack','-o',str(temporary),*[str(o) for o in objects],*libs]); temporary.replace(exe); linkstamp.write_text(signature)
    # Immutable copy used by every launched run.
    rev=revision(); frozen=BUILD/'revisions'/rev/name; frozen.parent.mkdir(parents=True,exist_ok=True)
    if not frozen.exists() or frozen.read_bytes()!=exe.read_bytes(): shutil.copy2(exe,frozen)
    # Relative shader and content paths must also be immutable for runs.
    for folder in ('shaders','content'):
        if (ROOT/folder).exists(): shutil.copytree(ROOT/folder,frozen.parent/folder,dirs_exist_ok=True)
    result={'target':target,'revision':rev,'assembled':assembled,'seconds':time.perf_counter()-start,'executable':str(frozen)}
    atomic(BUILD/(target+'-build.json'),result); print(json.dumps(result)); return frozen
def run_headless(args,benchmark=False):
    exe=build('headless'); scenario=args.scenario
    if scenario in ('scale-front','scale-hotspot'):
        raise RuntimeError(f'{scenario} fixture not implemented; refusing to relabel scale-open')
    cmd=[str(exe),'--units',str(args.units or SCENARIOS[scenario]),'--ticks',str(args.ticks),'--seed',str(args.seed)]
    start=time.perf_counter(); r=subprocess.run(cmd,cwd=exe.parent,check=True,capture_output=True,text=True)
    try: metrics=json.loads(r.stdout)
    except json.JSONDecodeError: raise RuntimeError('Runtime did not emit valid JSON: '+r.stdout[:1000])
    result={'scenario':scenario,'revision':revision(),'seed':args.seed,'wall_seconds':time.perf_counter()-start,'hardware':platform.platform(),'runtime':metrics,'coverage':{'replicated':0,'visible':0,'gpu':'unmeasured','audio':'unmeasured','threads':1}}
    path=RUNS/('bench-'+uuid.uuid4().hex[:10]+'.json'); atomic(path,result); print(json.dumps(result,indent=2)); print('Report: '+str(path))
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
def main():
    if len(sys.argv)>1 and sys.argv[1]=='_worker': return worker(sys.argv[2],sys.argv[3:])
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    for name in ('doctor','configure','jobs'): sub.add_parser(name)
    q=sub.add_parser('collect'); q.add_argument('job_id')
    q=sub.add_parser('build'); q.add_argument('--target',choices=['headless','client'],default='headless'); q.add_argument('--changed',action='store_true'); q.add_argument('--background',action='store_true')
    for name in ('run','server','bench'):
        q=sub.add_parser(name); q.add_argument('--scenario',choices=list(SCENARIOS),default='scale-open'); q.add_argument('--units',type=int); q.add_argument('--ticks',type=int,default=300); q.add_argument('--seed',type=int,default=1); q.add_argument('--headless',action='store_true'); q.add_argument('--client',action='store_true'); q.add_argument('--frames',type=int); q.add_argument('--background',action='store_true')
    q=sub.add_parser('test'); q.add_argument('--suite',choices=['all','simulation','reload'],default='all'); q.add_argument('--background',action='store_true')
    q=sub.add_parser('reload'); q.add_argument('--background',action='store_true')
    args=p.parse_args()
    if getattr(args,'background',False): background(args); return 0
    if args.command in ('doctor','configure'): doctor()
    elif args.command=='build': build(args.target)
    elif args.command in ('run','server','bench'):
        if args.client:
            exe=build('client'); cmd=[str(exe)];
            if args.frames: cmd+=['--frames',str(args.frames)]
            execute(cmd)
        else: run_headless(args,args.command=='bench')
    elif args.command=='jobs': jobs()
    elif args.command=='collect': jobs(args.job_id)
    elif args.command in ('test','reload'):
        suite='reload' if args.command=='reload' else args.suite
        if suite in ('all','simulation'): exe=build('headless'); library=BUILD/'libsim.so'; execute(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*[str(o) for o in BUILD.glob('src_sim_*.o')]]); execute([sys.executable,'tests/test_simulation.py',str(exe),str(library)])
        if suite in ('all','reload'): execute([sys.executable,'tests/test_reload.py','--nasm',nasm()])
    return 0
if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,subprocess.CalledProcessError,OSError) as e: print('ERROR: '+str(e),file=sys.stderr); sys.exit(1)
