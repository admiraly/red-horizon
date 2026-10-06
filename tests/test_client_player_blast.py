#!/usr/bin/env python3
"""Development-only authoritative client input/feedback test on a private X server.
The client, terrain and player simulation are the real assembled executable.
"""
import ctypes as C
import ctypes.util
import json
import math
import os
import signal
import pathlib
import re
import select
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

        spawn=player();assert spawn['hp']==100 and spawn['connected']==1
        # One coherent startup pose fixture; preserve every original army body's
        # HP,kind,generation and finite stores. No later authority writes.
        os.kill(process.pid,signal.SIGSTOP)
        try:
            _,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
            os.pwrite(memory,struct.pack('<fff',2005.,17.8,3900.),player_address)
            for ident,x,z,target in ((12,2000.,3900.,0xffffffff),(4108,2000.,4300.,12)):
                address=symbols['sim_entities']+ident*32
                row=list(struct.unpack('<ff6I',os.pread(memory,32,address)))
                assert row[2]>0 and row[4]==1 and row[7]>0,row
                row[0],row[1],row[5],row[6]=x,z,(1 if ident==12 else 0),target
                os.pwrite(memory,struct.pack('<ff6I',*row),address)
            for index in (1,3):
                os.pwrite(memory,struct.pack('<I',1),symbols['orders']+index*4)
                os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+index*64+24)
            shells_before=struct.unpack('<I',os.pread(memory,4,symbols['sim_shell_ammo']+4108*4))[0]
            assert 0<shells_before<=64
            fixture_tick=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]
            sequence=struct.unpack('<I',os.pread(memory,4,symbols['sim_event_sequence']))[0]
        finally:os.kill(process.pid,signal.SIGCONT)
        impacts=[]
        def actual_death():
            global sequence
            now=struct.unpack('<I',os.pread(memory,4,symbols['sim_event_sequence']))[0]
            for number in range(sequence+1,now+1):
                event=struct.unpack('<3f3IfI',os.pread(memory,32,symbols['sim_events']+(number&255)*32))
                if event[3]==3 and event[4]==1 and math.hypot(event[0]-2005.,event[2]-3900.)<18:impacts.append(event)
            sequence=now
            body=player()
            return body if body['hp']==0 else None
        dead=until(actual_death,25);assert dead['generation']==spawn['generation'] and impacts,(dead,impacts)
        shells_after=struct.unpack('<I',os.pread(memory,4,symbols['sim_shell_ammo']+4108*4))[0]
        assert shells_after<shells_before
        until(lambda:'DOWN: SAFE REDEPLOY' in title(window),2)
        image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
        pixel=X.XGetPixel(image,640,79);X.XDestroyImage(image)
        rgb=((pixel>>16)&255,(pixel>>8)&255,pixel&255);assert rgb[0]>100 and rgb[0]>rgb[1]*2,rgb
        redeployed=until(lambda:p if (p:=player())['hp']==100 and p['generation']>dead['generation'] else None,5)
        key(0xff1b);stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'actual-GL-player-physical-shell-death','passed':True,'units':8192,'startup_fixture_tick':fixture_tick,'preserved_army_health_kind_generation_stores':True,'no_live_renewal':True,'real_hostile_impacts':impacts,'finite_shells_before_after':[shells_before,shells_after],'dead':dead,'redeployed':redeployed,'actual_red_redeploy_pixel':rgb,'executable_sha256':__import__('hashlib').sha256(EXE.read_bytes()).hexdigest(),'limits':['One initial local authority pose/order fixture, original8192 army bodies retained; no multiplayer human-blast pixel acceptance.','Actual software GL, not hardware quality; dedicated bomber physical core trace is separate.']}))

finally:
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
