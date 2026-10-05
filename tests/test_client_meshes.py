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
        def actor():return struct.unpack('<ff6I',os.pread(memory,32,symbols['sim_entities']))
        def selected():return u32('mesh_selected_frames')
        def capture(path):
            os.kill(process.pid,signal.SIGSTOP)
            image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
            rgb=bytearray();region=bytearray()
            for y in range(720):
                for x in range(1280):
                    p=X.XGetPixel(image,x,y);pixel=bytes(((p>>16)&255,(p>>8)&255,p&255));rgb.extend(pixel)
                    if 550<=x<730 and 300<=y<510:region.extend(pixel)
            X.XDestroyImage(image)
            pathlib.Path(path).write_bytes(b'P6\n1280 720\n255\n'+rgb)
            frame=selected();blend=struct.unpack('<f',os.pread(memory,4,symbols['mesh_selected_lerp']))[0]
            os.kill(process.pid,signal.SIGCONT)
            return region,frame,blend
        until(lambda:u32('mesh_low_instances')>0 and u32('mesh_high_instances')>0 and u32('mesh_marker_instances')>0)
        initial_lod=[u32(name) for name in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances')]
        # Pose/front fixture only; model geometry, clips, movement and input paths
        # are real assembled runtime and the licensed baked source pack.
        os.pwrite(memory,struct.pack('<I',1),symbols['orders'])
        os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+24)
        os.pwrite(memory,struct.pack('<ff',2000.,3912.),symbols['sim_entities'])
        os.pwrite(memory,struct.pack('<ff',2020.,3915.),symbols['sim_entities']+12*32)
        os.pwrite(memory,struct.pack('<fff',2000.,17.805,3900.),player_address)
        time.sleep(.4)
        until(lambda:u32('mesh_high_instances')>0)
        assert u32('mesh_high_instances')<=256
        before=actor();image_a,frame_a,blend_a=capture('/tmp/red-horizon-soldier-idle-a.ppm')
        until(lambda:selected()!=frame_a,2)
        image_b,frame_b,blend_b=capture('/tmp/red-horizon-soldier-idle-b.ppm')
        assert before[:2]==actor()[:2],'held actor moved during idle comparison'
        pack=pathlib.Path('content/models/battle.rham').read_bytes() if pathlib.Path('content/models/battle.rham').exists() else (EXE.parent/'content/models/battle.rham').read_bytes()
        mo,co=struct.unpack_from('<II',pack,24)
        clips_first,clips_count=struct.unpack_from('<II',pack,mo+20)
        clips=[struct.unpack_from('<IIfI',pack,co+(clips_first+i)*16) for i in range(clips_count)]
        idle=next(c for c in clips if c[3]==0)
        assert idle[0]<=frame_a<idle[0]+idle[1] and idle[0]<=frame_b<idle[0]+idle[1] and frame_a!=frame_b,(frame_a,frame_b,idle)
        assert 0<=blend_a<1 and 0<=blend_b<1
        changed=sum(image_a[i:i+3]!=image_b[i:i+3] for i in range(0,len(image_a),3));assert changed>8,('no rendered source-pose change',changed)
        # Real tactical click and advance drives this actor; no displacement writes.
        key(0xff09);key(0xffbe)
        XT.XTestFakeMotionEvent(display,-1,342,360,0);X.XFlush(display);time.sleep(.1)
        button(True);time.sleep(.12);button(False);time.sleep(.1)
        key(0xff09)
        until(lambda:math.hypot(actor()[0]-before[0],actor()[1]-before[1])>.15,3)
        moving=actor();walks=[c for c in clips if c[3]==1]
        until(lambda:any(c[0]<=selected()<c[0]+c[1] for c in walks),2)
        image_walk,frame_walk,blend_walk=capture('/tmp/red-horizon-soldier-walk.ppm')
        assert any(c[0]<=frame_walk<c[0]+c[1] for c in walks),(frame_walk,walks)
        # The converter's tank has only a movement clip: hold must freeze tracks.
        tank_id=12
        os.pwrite(memory,struct.pack('<I',1),symbols['orders'])
        time.sleep(.25)
        tank_frame=struct.unpack('<I',os.pread(memory,4,symbols['mesh_selected_frames']+tank_id*4))[0]
        tank_blend=struct.unpack('<f',os.pread(memory,4,symbols['mesh_selected_lerp']+tank_id*4))[0]
        assert tank_frame==0 and tank_blend==0,(tank_frame,tank_blend)
        key(0xff1b);stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        assert 'meshes loaded=16' in stdout
        print(json.dumps({'suite':'animated-source-meshes','passed':True,'idle_frames':[frame_a,frame_b],'idle_changed_pixels':changed,'walk_frame':frame_walk,'walk_blend':blend_walk,'actual_actor_moved_metres':math.hypot(moving[0]-before[0],moving[1]-before[1]),'stationary_tracks_frozen':True,'source_meshes':16,'initial_lod_counts':initial_lod,'stdout':stdout}))
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
