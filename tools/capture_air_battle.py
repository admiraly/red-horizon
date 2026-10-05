#!/usr/bin/env python3
"""Development-only silent recording of the real 8192-unit air-battle client.
Private Xvfb/software GL; no injected shots, poses, events, damage or effects.
"""
import argparse,ctypes as C,ctypes.util,hashlib,json,os,pathlib,select,subprocess,time

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--client',required=True,type=pathlib.Path)
    p.add_argument('--output',required=True,type=pathlib.Path)
    p.add_argument('--seconds',type=int,default=12)
    a=p.parse_args();assert 3<=a.seconds<=30
    exe=a.client.resolve();output=a.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    rd,wr=os.pipe();xvfb=client=display=None
    x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
    x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong
    x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
    x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_char_p)]
    x.XFree.argtypes=[C.c_void_p];x.XCloseDisplay.argtypes=[C.c_void_p]
    x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
    x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_uint
    x.XFlush.argtypes=[C.c_void_p]
    xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
    try:
        xvfb=subprocess.Popen(['Xvfb','-displayfd',str(wr),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=(wr,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        os.close(wr);wr=None
        assert select.select([rd],[],[],10)[0],'private X server startup failed'
        number=os.read(rd,32).decode().strip();assert number.isdigit();os.close(rd);rd=None
        env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
        context=subprocess.check_output(['glxinfo','-B'],env=env,text=True,timeout=10)
        assert 'llvmpipe' in context.lower() or 'softpipe' in context.lower()
        display=x.XOpenDisplay(env['DISPLAY'].encode());assert display
        client=subprocess.Popen([str(exe),'--scenario','air-battle'],cwd=exe.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        window=None;deadline=time.monotonic()+15
        while time.monotonic()<deadline and not window:
            root,parent,children,count=C.c_ulong(),C.c_ulong(),C.POINTER(C.c_ulong)(),C.c_uint()
            x.XQueryTree(display,x.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
            for win in list(children[:count.value]):
                name=C.c_char_p()
                if x.XFetchName(display,win,C.byref(name)) and name:
                    title=name.value.decode(errors='replace');x.XFree(C.cast(name,C.c_void_p))
                    if 'RED HORIZON' in title and 'units' in title:window=win;break
            if children:x.XFree(children)
            assert client.poll() is None,'client exited before mapping'
            time.sleep(.02)
        assert window,'game window did not map'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','x11grab','-framerate','30','-video_size','1280x720','-draw_mouse','0','-i',env['DISPLAY'],'-t',str(a.seconds),'-c:v','libx264','-preset','veryfast','-crf','22',str(output)],env=env,check=True,timeout=a.seconds+15)
        # Normal Escape exit gives actual runtime telemetry, rather than killing it.
        x.XSetInputFocus(display,window,2,0)
        code=x.XKeysymToKeycode(display,0xff1b)
        xt.XTestFakeKeyEvent(display,code,1,0);x.XFlush(display);time.sleep(.2)
        xt.XTestFakeKeyEvent(display,code,0,0);x.XFlush(display)
        stdout,stderr=client.communicate(timeout=10)
        assert client.returncode==0,(stdout,stderr)
        assert 'submitted_entities=8192' in stdout,stdout
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,nb_frames:format=duration','-of','json',str(output)],text=True,timeout=10))
        assert probe['streams'][0]['width']==1280 and probe['streams'][0]['height']==720
        assert float(probe['format']['duration'])>=a.seconds-.1
        result=dict(suite='air-battle-recording',passed=True,scenario='air-battle',army=8192,revision=exe.parent.name,software_rendered=True,audio='ALSA null; silent capture',fixture='authored initial320actor encounter; remaining full army retained; no recording-time state writes',context=context,telemetry=stdout,video=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),probe=probe)
        output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:
        if client and client.poll() is None:client.terminate();client.wait(timeout=5)
        if display:x.XCloseDisplay(display)
        if xvfb:xvfb.terminate();xvfb.communicate(timeout=5)
        for fd in (rd,wr):
            if fd is not None:os.close(fd)
if __name__=='__main__':main()
