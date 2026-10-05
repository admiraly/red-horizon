#!/usr/bin/env python3
"""Development-only authoritative client input/feedback test on a private X server.
The client, terrain and player simulation are the real assembled executable.
"""
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
        assert select.select([read_fd], [], [], 10)[0], 'Xvfb startup timed out'
        number = os.read(read_fd, 32).decode().strip(); assert number.isdigit(), number
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

        def u32(name):return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
        until(lambda:player()['shots']==0)
        time.sleep(.25)
        assert u32('effects_tracers')==0
        button(True)
        until(lambda:u32('effects_tracers')==1,2)
        button(False);time.sleep(.025)
        os.kill(process.pid,signal.SIGSTOP)
        records=struct.unpack('<512f',os.pread(memory,2048,symbols['effects_records']))
        alive=sum(records[i*8+3]>0 for i in range(64));assert alive>0,alive
        image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
        yellow=0;rgb=bytearray()
        for y in range(720):
            for x in range(1280):
                pixel=X.XGetPixel(image,x,y);r,g,b=(pixel>>16)&255,(pixel>>8)&255,pixel&255
                rgb.extend((r,g,b))
                if 300<x<980 and 150<y<600 and r>180 and g>130 and b<110:yellow+=1
        X.XDestroyImage(image)
        pathlib.Path('/tmp/red-horizon-tracer.ppm').write_bytes(b'P6\n1280 720\n255\n'+rgb)
        assert yellow>3,('no actual tracer pixels',yellow)
        os.kill(process.pid,signal.SIGCONT)
        time.sleep(.3)
        total=u32('effects_tracers');shots=player()['shots']
        assert total==shots//3,(total,shots)
        time.sleep(.4)
        assert u32('effects_tracers')==total,'repeated render frames duplicated shot effect'
        pool=os.pread(memory,2048,symbols['effects_records'])
        assert all(struct.unpack_from('<f',pool,i*32+12)[0]<=0 for i in range(64) if struct.unpack_from('<I',pool,i*32+28)[0]==1),'tracers did not expire'
        # Position an actual shell-capable source and opposite living target.
        # Real AI targeting/world ticks launch the shell; no event/pool writes.
        entities=struct.unpack('<'+('ff6I'*u32('sim_count')),os.pread(memory,32*u32('sim_count'),symbols['sim_entities']))
        tank=next(i for i in range(u32('sim_count')) if entities[i*8+2]>0 and entities[i*8+3]==0 and entities[i*8+4]==1)
        opponent=next(i for i in range(u32('sim_count')) if entities[i*8+2]>0 and entities[i*8+3]==1 and entities[i*8+4]==0)
        os.pwrite(memory,struct.pack('<ff',2000.,3860.),symbols['sim_entities']+tank*32)
        os.pwrite(memory,struct.pack('<ff',2000.,3980.),symbols['sim_entities']+opponent*32)
        os.pwrite(memory,struct.pack('<fff',2000.,17.805,3900.),player_address)
        for i in (tank,opponent):
            front=entities[i*8+5];side=entities[i*8+3]
            os.pwrite(memory,struct.pack('<I',1),symbols['orders']+(side*3+front)*4)
            os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+(side*3+front)*64+24)
        before_impacts=u32('effects_impacts');before_events=u32('sim_event_sequence')
        until(lambda:u32('sim_projectile_count')>0,3)
        def matching_impact():
            ring=os.pread(memory,8192,symbols['sim_events'])
            for slot in range(256):
                event=struct.unpack_from('<fffIIIfI',ring,slot*32)
                if event[7]>before_events and event[3]==3 and event[4]==0 and abs(event[0]-2000)<10 and 3960<event[2]<3990:return event
            return None
        actual_impact=until(matching_impact,5)
        until(lambda:u32('effects_event_cursor')>=actual_impact[7] and u32('effects_impacts')>before_impacts,2)
        impact_frame=u32('frame_count')
        until(lambda:u32('frame_count')>=impact_frame+2,1)
        os.kill(process.pid,signal.SIGSTOP)
        image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
        orange=0;rgb=bytearray()
        for y in range(720):
            for x in range(1280):
                pixel=X.XGetPixel(image,x,y);r,g,b=(pixel>>16)&255,(pixel>>8)&255,pixel&255
                rgb.extend((r,g,b))
                if 250<x<1030 and 180<y<610 and r>130 and g>70 and b<100 and r>g:orange+=1
        X.XDestroyImage(image)
        pathlib.Path('/tmp/red-horizon-shell-impact.ppm').write_bytes(b'P6\n1280 720\n255\n'+rgb)
        assert orange>3,('no actual impact pixels',orange)
        events=u32('sim_event_sequence');impacts=u32('effects_impacts')
        assert events>before_events
        os.kill(process.pid,signal.SIGCONT)
        key(0xff1b)
        stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'rendered-tracer','passed':True,'shots':shots,'tracers':total,'yellow_pixels':yellow,'screenshot':'/tmp/red-horizon-tracer.ppm','shell_source':tank,'impact_pixels':orange,'impact_events':impacts,'event_sequence':events,'actual_impact':actual_impact}))
finally:
    if memory is not None: os.close(memory)
    if process is not None and process.poll() is None:
        os.kill(process.pid,signal.SIGCONT)
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
