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
        struct.pack_into('<ff',army,source*32,2000.,4000.);struct.pack_into('<ff',army,target*32,2000.,4100.)
        os.pwrite(memory,army,symbols['sim_entities']);os.pwrite(memory,struct.pack('<5f',1990.,17.805,3990.,math.pi/4,0.),player_address)
        for slot in range(6):
            os.pwrite(memory,struct.pack('<I',1),symbols['orders']+slot*4);os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+slot*64+24)
        os.kill(process.pid,signal.SIGCONT)
        def acquired():
            row=struct.unpack('<2I5fI',os.pread(memory,32,symbols['infantry_aims']+source*32))
            return row if row[7]&3==3 and u32('sim_tick_count')-row[1]<8 else False
        actual=until(acquired,5);stop()
        old_dt=os.pread(memory,8,symbols['maxdt']);old_accum=os.pread(memory,8,symbols['accum']);os.pwrite(memory,struct.pack('<d',0),symbols['maxdt']);os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
        old_mesh_dt=os.pread(memory,4,symbols['dt_min'])
        os.pwrite(memory,struct.pack('<f',0),symbols['dt_min'])
        # Set only the development visual camera at the actual target eye,
        # avoiding an unsettled teleport interpolation during the paired capture.
        eye=os.pread(memory,12,player_address)
        os.pwrite(memory,eye,symbols['camera'])
        os.pwrite(memory,struct.pack('<f',math.pi/4),symbols['yaw'])
        os.pwrite(memory,struct.pack('<f',0),symbols['pitch'])
        frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3,2);stop()
        instance=struct.unpack('<16f',os.pread(memory,64,symbols['mesh_infantry_pose']))
        assert int(instance[12])==source and int(instance[15])&4,instance
        actual=struct.unpack('<2I5fI',os.pread(memory,32,symbols['infantry_aims']+source*32))
        assert abs(actual[2]+3*math.pi/4)<1e-5 and actual[7]&3==3,actual
        assert abs(instance[11]+instance[3]-actual[2])<1e-5,instance
        pool=os.pread(memory,32,symbols['infantry_aims']+source*32)
        def snapshot():return tuple(os.pread(memory,n,symbols[k])for k,n in [('sim_players',256),('sim_entities',count*32),('infantry_weapons',count*32),('sim_events',8192),('sim_tick_count',4)])
        def screen():
            image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image;rgb=bytearray()
            for y in range(720):
                for x in range(1280):
                    p=X.XGetPixel(image,x,y);rgb.extend(((p>>16)&255,(p>>8)&255,p&255))
            X.XDestroyImage(image);return bytes(rgb)
        leg_frames=os.pread(memory,4,symbols['mesh_selected_frames']+source*4)
        leg_blend=os.pread(memory,4,symbols['mesh_selected_lerp']+source*4)
        authority=snapshot();rgb=screen();hidden=bytearray(pool)
        struct.pack_into('<I',hidden,28,0)
        os.pwrite(memory,hidden,symbols['infantry_aims']+source*32);frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3,2);stop();control=screen()
        assert os.pread(memory,4,symbols['mesh_selected_frames']+source*4)==leg_frames
        assert os.pread(memory,4,symbols['mesh_selected_lerp']+source*4)==leg_blend
        assert snapshot()==authority,'paired cosmetic control changed authority'
        changed=sum(max(abs(rgb[i+j]-control[i+j])for j in range(3))>12 for i in range(0,len(rgb),3))
        assert changed>0,('actual aiming has no visible paired pixels',actual,instance)
        pathlib.Path('/tmp/red-horizon-NPC-aim.ppm').write_bytes(b'P6\n1280 720\n255\n'+rgb)
        pathlib.Path('/tmp/red-horizon-NPC-aim-control.ppm').write_bytes(b'P6\n1280 720\n255\n'+control)
        os.pwrite(memory,pool,symbols['infantry_aims']+source*32);os.pwrite(memory,old_mesh_dt,symbols['dt_min']);os.pwrite(memory,old_dt,symbols['maxdt']);os.pwrite(memory,old_accum,symbols['accum']);os.kill(process.pid,signal.SIGCONT)
        code=X.XKeysymToKeycode(display,0xff1b);XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display);time.sleep(.12);XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display)
        stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'actual-NPC-aim-GL','passed':True,'army':count,'source':source,'actual_pose':actual,'render_instance':instance,'paired_changed_pixels':changed,'paired_authority_unchanged':True,'locomotion_frames_blend_unchanged':True,'no_HP_kind_generation_stock_event_writes':True,'screenshot':'/tmp/red-horizon-NPC-aim.ppm','limits':['One initial position/order fixture, actual finite AI aiming/firing; paired control freezes only development authority and animation clocks and hides/restores only actual aim metadata.','Software GL visibility proof, not target GPU performance or audiovisual quality acceptance.']}))

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
