#!/usr/bin/env python3
"""Development-only authoritative client input/feedback test on a private X server.
The client, terrain and player simulation are the real assembled executable.
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

        def stop():
            os.kill(process.pid,signal.SIGSTOP)
            _,status=os.waitpid(process.pid,os.WUNTRACED)
            assert os.WIFSTOPPED(status), 'client did not stop'

        def u32(name):return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
        stop();count=u32('sim_count');assert count==8192
        army=bytearray(os.pread(memory,count*32,symbols['sim_entities']));stocks=os.pread(memory,count*32,symbols['infantry_weapons'])
        source=next(i for i in range(count) if struct.unpack_from('<6I',army,i*32+8)[0]>0 and struct.unpack_from('<6I',army,i*32+8)[1:3]==(1,0) and struct.unpack_from('<I',stocks,i*32+4)[0]>=2)
        target=next(i for i in range(count) if struct.unpack_from('<6I',army,i*32+8)[0]>0 and struct.unpack_from('<6I',army,i*32+8)[1:3]==(0,0))
        for i in range(count):
            side=struct.unpack_from('<I',army,i*32+12)[0];struct.pack_into('<ff',army,i*32,1000. if side==0 else 7000.,7000.)
        struct.pack_into('<ff',army,source*32,2000.,4000.);struct.pack_into('<ff',army,target*32,2000.,3980.)
        # Observe from a declared20m lateral offset. A collinear camera puts the
        # actual target body20m in front of the source flash and can fully occlude
        # its small pixels as authored torso animation changes. Keep both actors,
        # real finite firing and strict paired authority/visibility gates.
        os.pwrite(memory,army,symbols['sim_entities']);os.pwrite(memory,struct.pack('<fff',1980.,17.805,3900.),player_address)
        for slot in range(6):
            os.pwrite(memory,struct.pack('<I',1),symbols['orders']+slot*4);os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+slot*64+24)
        old=u32('effects_rifle_flashes');os.kill(process.pid,signal.SIGCONT)
        def acquired():
            if u32('effects_rifle_flashes')<=old:return False
            pool=os.pread(memory,2048,symbols['effects_records'])
            return any(struct.unpack_from('<f',pool,i*32+12)[0]>0 and abs(struct.unpack_from('<f',pool,i*32)[0]-2000)<.1 and abs(struct.unpack_from('<f',pool,i*32+8)[0]-4000)<.1 for i in range(64))
        until(acquired,5);stop()
        old_dt=os.pread(memory,8,symbols['maxdt']);old_accum=os.pread(memory,8,symbols['accum']);os.pwrite(memory,struct.pack('<d',0),symbols['maxdt']);os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
        frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3,2);stop()
        pool=os.pread(memory,2048,symbols['effects_records']);slots=[]
        for i in range(64):
            r=struct.unpack_from('<7fI',pool,i*32)
            if r[3]>0 and r[7]==2 and r[4]==.25 and abs(r[0]-2000)<.1 and abs(r[2]-4000)<.1:slots.append(i)
        assert slots,'actual source flash expired before freeze'
        def snapshot():return tuple(os.pread(memory,n,symbols[k])for k,n in [('sim_players',256),('sim_entities',count*32),('infantry_weapons',count*32),('sim_events',8192),('sim_tick_count',4)])
        def screen():
            image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image;rgb=bytearray()
            for y in range(720):
                for x in range(1280):
                    p=X.XGetPixel(image,x,y);rgb.extend(((p>>16)&255,(p>>8)&255,p&255))
            X.XDestroyImage(image);return bytes(rgb)
        authority=snapshot();rgb=screen();hidden=bytearray(pool)
        for i in slots:struct.pack_into('<f',hidden,i*32+12,0)
        os.pwrite(memory,hidden,symbols['effects_records']);frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3,2);stop();control=screen()
        assert snapshot()==authority,'paired cosmetic control changed authority'
        changed=sum(max(abs(rgb[i+j]-control[i+j])for j in range(3))>12 for i in range(0,len(rgb),3))
        assert changed>0,('actual rifle flash has no visible paired pixels',slots)
        pathlib.Path('/tmp/red-horizon-NPC-rifle.ppm').write_bytes(b'P6\n1280 720\n255\n'+rgb)
        pathlib.Path('/tmp/red-horizon-NPC-rifle-control.ppm').write_bytes(b'P6\n1280 720\n255\n'+control)
        os.pwrite(memory,pool,symbols['effects_records']);os.pwrite(memory,old_dt,symbols['maxdt']);os.pwrite(memory,old_accum,symbols['accum']);os.kill(process.pid,signal.SIGCONT)
        code=X.XKeysymToKeycode(display,0xff1b);XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display);time.sleep(.12);XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display)
        stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'actual-NPC-rifle-GL','passed':True,'army':count,'source':source,'source_flash_slots':slots,'paired_changed_pixels':changed,'paired_authority_unchanged':True,'no_HP_kind_generation_stock_event_writes':True,'screenshot':'/tmp/red-horizon-NPC-rifle.ppm','limits':['One initial position/order fixture, actual finite AI firing; paired control freezes only development clock and hides/restores actual acquired cosmetics.','Software GL visibility proof, not target GPU performance or audiovisual quality acceptance.']}))

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
