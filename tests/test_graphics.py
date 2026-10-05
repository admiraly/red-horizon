#!/usr/bin/env python3
"""Run the actual assembly client on a private Xvfb/software GL display."""
import json,os,pathlib,selectors,shutil,subprocess,sys,time,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
exe=pathlib.Path(sys.argv[1]).resolve()
if not shutil.which('Xvfb'): raise SystemExit('Xvfb missing: install xorg-x11-server-Xvfb (Fedora) or xvfb (Ubuntu)')
folder=ROOT/'runs'/('headless-graphics-'+uuid.uuid4().hex[:10]);folder.mkdir(parents=True)
read_fd,write_fd=os.pipe();server=None
try:
    with (folder/'xvfb.log').open('wb') as log:
        server=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=log,stderr=log)
    os.close(write_fd);write_fd=-1
    selector=selectors.DefaultSelector();selector.register(read_fd,selectors.EVENT_READ)
    assert selector.select(10),'Xvfb did not become ready'
    display=os.read(read_fd,64).decode().strip();assert display.isdigit(),display
    selector.close();os.close(read_fd);read_fd=-1
    env=os.environ.copy();env['DISPLAY']=':'+display;env.pop('WAYLAND_DISPLAY',None);env['LIBGL_ALWAYS_SOFTWARE']='1';env['RH_AUDIO_DEVICE']='null'
    result={'suite':'graphics','revision':exe.parent.name,'software_rendered':True,'display_isolated':True,'resolution':[1280,720],'runs':[]}
    if shutil.which('glxinfo'):
        probe=subprocess.run(['glxinfo','-B'],env=env,capture_output=True,text=True,timeout=10,check=True)
        result['context']=probe.stdout
        assert 'llvmpipe' in probe.stdout.lower() or 'softpipe' in probe.stdout.lower(),'software renderer was not established'
    for mode in ('first-person','tactical'):
        image=folder/(mode+'.ppm');cmd=[str(exe),'--frames','30','--screenshot',str(image)]
        if mode=='tactical':cmd.append('--tactical')
        begin=time.perf_counter();run=subprocess.run(cmd,cwd=exe.parent,env=env,capture_output=True,text=True,timeout=30,check=True)
        (folder/(mode+'.log')).write_text(run.stdout+run.stderr)
        assert 'submitted_entities=8192' in run.stdout,run.stdout
        data=image.read_bytes();header=b'P6\n1280 720\n255\n';assert data.startswith(header)
        pixels=data[len(header):];assert len(pixels)==1280*720*3
        # Catch missing/black/constant-frame output, not an art-quality assertion.
        assert max(pixels)>150 and len(set(pixels))>20,'blank/unvaried framebuffer'
        timing=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"client_metrics"')]
        if timing:
            assert timing[0]['cpu_samples']>0 and timing[0]['gpu_samples']>0
            for prefix in ('cpu_frame','gpu_draw'):
                assert 0<=timing[0][prefix+'_p95_ms']<=timing[0][prefix+'_p99_ms'],timing[0]
        result['runs'].append({'mode':mode,'exit_code':run.returncode,'seconds':time.perf_counter()-begin,'screenshot':str(image),'telemetry':run.stdout,'timing':timing})
    controls=subprocess.run([sys.executable,str(ROOT/'tests/test_controls.py'),str(exe)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=50)
    (folder/'controls.log').write_text(controls.stdout+controls.stderr)
    assert controls.returncode==0,controls.stdout+controls.stderr
    result['controls']=json.loads(controls.stdout.strip())
    result['passed']=True;(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'suite':'graphics','passed':True,'renderer':'software','modes':2,'entities_submitted':8192,'report':str(folder/'result.json')}))
finally:
    if read_fd>=0:os.close(read_fd)
    if write_fd>=0:os.close(write_fd)
    if server:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
