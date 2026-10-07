#!/usr/bin/env python3
"""Development-only actual sourced terrain / cosmetic weather GL and input proof.
"""
from xvfb_display import read_display_number
import ctypes as C
import ctypes.util
import json
import math
import os
import pathlib
import re
import select
import signal
import struct
import subprocess
import sys
import tempfile
import time

EXE = pathlib.Path(sys.argv[1]).resolve()
X = C.CDLL(ctypes.util.find_library('X11'))
XT = C.CDLL(ctypes.util.find_library('Xtst'))
D, W = C.c_void_p, C.c_ulong
X.XOpenDisplay.argtypes = [C.c_char_p]; X.XOpenDisplay.restype = D
X.XDefaultRootWindow.argtypes = [D]; X.XDefaultRootWindow.restype = W
X.XQueryTree.argtypes = [D, W, C.POINTER(W), C.POINTER(W), C.POINTER(C.POINTER(W)), C.POINTER(C.c_uint)]
X.XFetchName.argtypes = [D, W, C.POINTER(C.c_char_p)]
X.XFree.argtypes = [D]
X.XRaiseWindow.argtypes = [D, W]
X.XSetInputFocus.argtypes = [D, W, C.c_int, W]
X.XFlush.argtypes = [D]
X.XKeysymToKeycode.argtypes = [D, W]; X.XKeysymToKeycode.restype = C.c_uint
X.XCloseDisplay.argtypes = [D]
X.XGetImage.argtypes = [D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int]; X.XGetImage.restype = D
X.XGetPixel.argtypes = [D,C.c_int,C.c_int]; X.XGetPixel.restype = W
X.XDestroyImage.argtypes = [D]
XT.XTestFakeKeyEvent.argtypes = [D, C.c_uint, C.c_int, W]
XT.XTestFakeButtonEvent.argtypes = [D, C.c_uint, C.c_int, W]
XT.XTestFakeMotionEvent.argtypes = [D, C.c_int, C.c_int, C.c_int, W]

server = process = display = memory = None
window = 0
read_fd, write_fd = os.pipe()
try:
    with tempfile.TemporaryFile() as server_log:
        server = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x720x24', '-nolisten', 'tcp'], pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=server_log)
        os.close(write_fd); write_fd = None

        number = read_display_number(read_fd,10); assert number.isdigit(), number
        os.close(read_fd); read_fd = None
        env = dict(os.environ, DISPLAY=':' + number, LIBGL_ALWAYS_SOFTWARE='1', RH_AUDIO_DEVICE='null')
        env.pop('WAYLAND_DISPLAY', None)
        display = X.XOpenDisplay(env['DISPLAY'].encode()); assert display
        process = subprocess.Popen([str(EXE)], cwd=EXE.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def title(win):
            name = C.c_char_p()
            if not X.XFetchName(display, win, C.byref(name)) or not name: return ''
            result = name.value.decode(errors='replace'); X.XFree(C.cast(name, D)); return result

        def until(predicate, seconds=10):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                result = predicate()
                if result: return result
                assert process.poll() is None, 'client exited during test'
                time.sleep(.02)
            raise AssertionError('condition timed out: ' + (title(window) if window else 'startup'))

        def find_ready():
            root, parent, children, count = W(), W(), C.POINTER(W)(), C.c_uint()
            X.XQueryTree(display, X.XDefaultRootWindow(display), C.byref(root), C.byref(parent), C.byref(children), C.byref(count))
            result = 0
            for win in list(children[:count.value]):
                text = title(win)
                if 'RED HORIZON' in text and 'HP 100 ' in text: result = win; break
            if children: X.XFree(children)
            return result

        window = until(find_ready)
        X.XRaiseWindow(display, window); X.XSetInputFocus(display, window, 2, 0); X.XFlush(display); time.sleep(.15)
        symbols = {}
        for line in subprocess.check_output(['nm', '-n', str(EXE)], text=True).splitlines():
            columns = line.split()
            if len(columns) == 3: symbols[columns[2]] = int(columns[0], 16)
        memory = os.open(f'/proc/{process.pid}/mem', os.O_RDWR)
        player_address = symbols['sim_players']

        def player():
            values = struct.unpack('<5f11I', os.pread(memory, 64, player_address))
            return dict(zip(('x','y','z','yaw','pitch','hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation'), values))

        def key(symbol, hold=.12):
            code = X.XKeysymToKeycode(display, symbol); assert code
            XT.XTestFakeKeyEvent(display, code, 1, 0); X.XFlush(display); time.sleep(hold)
            XT.XTestFakeKeyEvent(display, code, 0, 0); X.XFlush(display); time.sleep(.10)

        def button(down):
            XT.XTestFakeButtonEvent(display, 1, int(down), 0); X.XFlush(display)

        # Real source textures and presets exercised by actual rendered clients.
        capture_folder=pathlib.Path(tempfile.mkdtemp(prefix='rh-weather-captures-'))
        captures={}
        for preset in ('clear','overcast','rain','fog'):
            path=capture_folder/(preset+'.ppm')
            run=subprocess.run([str(EXE),'--hidden','--weather',preset,'--frames','20','--screenshot',str(path)],cwd=EXE.parent,env=env,capture_output=True,text=True,timeout=30)
            assert run.returncode==0,(preset,run.stdout,run.stderr)
            data=path.read_bytes().split(b'\n',3)[3];assert len(data)==1280*720*3
            captures[preset]=data
        def mean_region(data,x0,y0,x1,y1):
            return [sum(data[(y*1280+x)*3+c] for y in range(y0,y1) for x in range(x0,x1))/((x1-x0)*(y1-y0)) for c in range(3)]
        sky={name:mean_region(data,400,90,700,240) for name,data in captures.items()}
        ground={name:mean_region(data,200,550,500,650) for name,data in captures.items()}
        assert sum(abs(a-b) for a,b in zip(sky['clear'],sky['overcast']))>15,(sky,ground)
        assert sum(ground['rain'])<sum(ground['clear'])*.85,ground
        assert sum(abs(a-b) for a,b in zip(sky['fog'],sky['clear']))>10,sky
        # Actual source sampling produces ground detail rather than a flat material.
        clear=captures['clear'];values=[clear[(600*1280+x)*3] for x in range(200,500)]
        assert max(values)-min(values)>10,('texture detail missing',min(values),max(values))
        X.XRaiseWindow(display,window);X.XSetInputFocus(display,window,2,0);X.XFlush(display);time.sleep(.1)
        # Freeze only simulation scheduling while real weather transitions and
        # F4 input run. Never patch player health, shaders or framebuffer.
        def stop():
            os.kill(process.pid,signal.SIGSTOP)
            _,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
        def u32(name):return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
        stop()
        os.pwrite(memory,struct.pack('<d',1e30),symbols['thirty'])
        os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
        before_frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT)
        until(lambda:u32('frame_count')>=before_frame+3,5)
        frozen_ticks=u32('local_sim_ticks')
        initial=player();weather_address=symbols['environment_weather']
        def weather():return struct.unpack('<4f',os.pread(memory,16,weather_address))
        assert struct.unpack('<I',os.pread(memory,4,symbols['environment_preset']))[0]==0
        key(0xffc1) # F4: clear -> overcast
        until(lambda:'WEATHER overcast (F4 CYCLE)' in title(window))
        assert 0.15<weather()[1]<.82,'weather jumped instead of transitioning'
        key(0xffc1);until(lambda:'WEATHER rain (F4 CYCLE)' in title(window))
        until(lambda:weather()[2]>.2,2)
        key(0xffc1);until(lambda:'WEATHER fog (F4 CYCLE)' in title(window))
        key(0xffc1);until(lambda:'WEATHER clear (F4 CYCLE)' in title(window))
        final=player()
        assert u32('local_sim_ticks')==frozen_ticks,'authority tick advanced during F4 isolation'
        assert (initial['x'],initial['z'],initial['hp'],initial['ammo'],initial['shots'],initial['generation'])==(final['x'],final['z'],final['hp'],final['ammo'],final['shots'],final['generation']),(initial,final)
        # Then freeze cosmetic clocks for paired rain-phase screenshots.
        stop()
        os.pwrite(memory,struct.pack('<d',0),symbols['maxdt'])
        os.kill(process.pid,signal.SIGCONT)
        def pose(y,heading=0.,look=0.):
            stop()
            os.pwrite(memory,struct.pack('<3f',2000.,y,2200.),player_address)
            os.pwrite(memory,struct.pack('<3f',2000.,y,2200.),symbols['camera'])
            os.pwrite(memory,struct.pack('<f',heading),symbols['yaw'])
            os.pwrite(memory,struct.pack('<f',look),symbols['pitch'])
            os.kill(process.pid,signal.SIGCONT)
        def fixture(time_value,rain_value,cloud=.96,density=.00045):
            stop()
            os.pwrite(memory,struct.pack('<4f',time_value,cloud,rain_value,density),weather_address)
            os.kill(process.pid,signal.SIGCONT)
        def capture(label):
            start=u32('frame_count');until(lambda:u32('frame_count')>=start+4,5)
            stop()
            image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
            rgb=bytearray()
            for y in range(720):
                for x in range(1280):
                    pixel=X.XGetPixel(image,x,y)
                    rgb.extend(((pixel>>16)&255,(pixel>>8)&255,pixel&255))
            X.XDestroyImage(image)
            (capture_folder/(label+'.ppm')).write_bytes(b'P6\n1280 720\n255\n'+rgb)
            assert u32('local_sim_ticks')==frozen_ticks,'authority tick advanced in render fixture'
            os.kill(process.pid,signal.SIGCONT)
            return rgb
        # Ground photograph evidence away from all strategic corridors/objectives.
        pose(19.42,0.,-.35);fixture(0.,0.,.15,.00008)
        capture('off-corridor-grass')
        fixture(0.,1.);capture('off-corridor-rain')
        rain_masks=[]
        for heading,label in ((0.,'forward'),(math.pi/2,'side')):
            pose(100.,heading,0.)
            masks=[]
            for phase in (0.,.13):
                fixture(phase,0.);dry=capture(label+'-dry-'+str(phase))
                fixture(phase,1.);wet=capture(label+'-rain-'+str(phase))
                mask=set()
                for y in range(50,270):
                    for x in range(320,1180):
                        offset=(y*1280+x)*3
                        if max(abs(wet[offset+c]-dry[offset+c]) for c in range(3))>=3:
                            mask.add((x,y))
                assert len(mask)>20,('rain vanished across viewing direction',label,phase,len(mask))
                masks.append(mask)
            moved=len(masks[0]^masks[1]);assert moved>20,('precipitation did not move',label,moved)
            rain_masks.append({'view':label,'visible_pixels':[len(m) for m in masks],'moved_pixels':moved})
        key(0xff1b);stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'client-environment','passed':True,'preset_sky_rgb':sky,'preset_ground_rgb':ground,'source_ground_range':[min(values),max(values)],'actual_F4_all_presets':True,'player_authority_unchanged':True,'frozen_fixture_rain_motion':rain_masks,'off_corridor_grass':str(capture_folder/'off-corridor-grass.ppm'),'screenshots':[str(capture_folder/(name+'.ppm')) for name in captures],'preset_clients_hidden':True,'per_run_screenshot_paths':True}))

finally:
    if process is not None and process.poll() is None:
        try:os.kill(process.pid,signal.SIGCONT)
        except ProcessLookupError:pass
    if memory is not None: os.close(memory)
    if process is not None and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
    if display: X.XCloseDisplay(display)
    if server is not None and server.poll() is None:
        server.terminate()
        try: server.wait(timeout=3)
        except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=3)
    if read_fd is not None: os.close(read_fd)
    if write_fd is not None: os.close(write_fd)
