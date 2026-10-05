#!/usr/bin/env python3
"""Verify incremental dependencies and frozen background jobs in an isolated repo."""
import argparse,json,os,pathlib,shutil,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--nasm',required=True);args=p.parse_args()
with tempfile.TemporaryDirectory(prefix='red-horizon-tools-test-') as temp:
    root=pathlib.Path(temp)
    for folder in ('tools','src','schemas','shaders','content','tests'):
        if (ROOT/folder).exists(): shutil.copytree(ROOT/folder,root/folder)
    shutil.copy2(ROOT/'.gitignore',root/'.gitignore')
    env=os.environ.copy();env.pop('RED_HORIZON_SOURCE_COMMIT',None);env['RED_HORIZON_NASM']=str(pathlib.Path(args.nasm).resolve())
    def run(*argv):
        return subprocess.check_output(argv,cwd=root,env=env,text=True)
    run('git','init','-q');run('git','config','user.name','Test');run('git','config','user.email','test@example.invalid');run('git','add','.');run('git','commit','-qm','isolated fixture')
    def dev(*argv): return run('python3','tools/dev.py',*argv)
    cold=json.loads(dev('build'));warm=json.loads(dev('build','--changed'))
    assert cold['assembled']>=2 and warm['assembled']==0
    source=root/'src/sim/world.asm';source.write_text(source.read_text()+'\n; incremental test\n')
    changed=json.loads(dev('build','--changed'));assert changed['assembled']==1
    job=json.loads(dev('bench','--ticks','30','--realtime','--background'))
    frozen=pathlib.Path(job['source_snapshot']);assert frozen.is_dir()
    assert (frozen/'src/sim/world.asm').read_bytes()==source.read_bytes()
    source.write_text('INTENTIONALLY INVALID ASSEMBLY\n')
    result=pathlib.Path(job['result']);deadline=time.monotonic()+15
    while not result.exists() and time.monotonic()<deadline: time.sleep(.1)
    assert result.exists(),'background job did not finish'
    r=json.loads(result.read_text());assert r['status']=='passed' and r['revision']==job['revision']
    report=list((frozen/'runs').glob('bench-*.json'));assert len(report)==1
    assert json.loads(report[0].read_text())['revision']==job['revision']
    invalid=subprocess.run(['python3','tools/dev.py','build'],cwd=root,env=env,capture_output=True)
    assert invalid.returncode!=0,'invalid source falsely succeeded'
    status=json.loads(dev('collect',job['job_id']));assert status['status']=='passed'
print(json.dumps({'suite':'tools','passed':True,'checks':['cold/incremental','single module invalidation','immutable background source','revision identity','failed assembly reported','job collection']}))
