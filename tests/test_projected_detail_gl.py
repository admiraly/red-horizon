#!/usr/bin/env python3
"""Development-only projected actor detail oracle on a private X server.
Frozen, explicitly written fixture records verify production rendering only;
natural combat and hardware density measurements are recorded separately.
"""
import ctypes as C
import ctypes.util
import json
import os
import pathlib
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
X.XCloseDisplay.argtypes = [D]
X.XGetImage.argtypes = [D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int]; X.XGetImage.restype = D
X.XGetPixel.argtypes = [D,C.c_int,C.c_int]; X.XGetPixel.restype = W
X.XDestroyImage.argtypes = [D]
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
        deadline = time.monotonic() + 5
        while not display and time.monotonic() < deadline:
            assert server.poll() is None, 'private Xvfb exited during startup'
            display = X.XOpenDisplay(env['DISPLAY'].encode())
            if not display: time.sleep(.01)
        if not display:
            server_log.seek(0)
            raise AssertionError('private Xvfb connection timed out: ' + server_log.read().decode(errors='replace'))
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
        XT.XTestFakeMotionEvent(display, 0, 640, 360, 0)
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

        # Freeze only this private process's simulation clock, leaving real GL
        # rendering running. Pose/pool fixture writes are explicitly development
        # test setup; no claim that these were shots produced by gameplay.
        stop()
        os.pwrite(memory,struct.pack('<I',0),symbols['air_trails_visible'])
        os.pwrite(memory,struct.pack('<d',1e30),symbols['thirty'])
        os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
        # A stopped process can already be inside sim_tick. Let that tick finish
        # before installing scene fixtures and recording the frozen counter.
        start=struct.unpack('<I',os.pread(memory,4,symbols['frame_count']))[0]
        os.kill(process.pid,signal.SIGCONT)
        until(lambda:struct.unpack('<I',os.pread(memory,4,symbols['frame_count']))[0]>=start+3,3)
        stop()
        os.pwrite(memory,struct.pack('<5f',2000.,100.,3900.,0.,0.),player_address)
        for name in ('yaw','pitch'):
            os.pwrite(memory,struct.pack('<f',0),symbols[name])
        os.pwrite(memory,bytes(32768),symbols['sim_projectiles'])
        os.pwrite(memory,struct.pack('<I',0),symbols['sim_projectile_count'])
        os.pwrite(memory,bytes(2048),symbols['effects_records'])
        os.kill(process.pid,signal.SIGCONT)

        # Isolate one real sourced aircraft; fixture poses are development-only.
        def u32(name):return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
        def fixture(y=100.,heading=0.,pitch=0.,bank=0.,role=0,generation=1,distance=28.,tactical=0,visible=True):
            stop()
            os.pwrite(memory,struct.pack('<I',int(visible)),symbols['sim_count'])
            entity=struct.pack('<2f6I',2040.,3900.+distance,100,0,3,0,0,1)
            os.pwrite(memory,entity,symbols['sim_entities'])
            air=struct.pack('<5f6I3f2I',y,heading,pitch,bank,10.,role,0,0,0,10,generation,0.,0.,10.,0,1)
            assert len(air)==64
            os.pwrite(memory,air,symbols['sim_aircraft'])
            os.pwrite(memory,struct.pack('<I',tactical),symbols['tactical'])
            os.kill(process.pid,signal.SIGCONT)

        def capture(label):
            start=u32('frame_count');until(lambda:u32('frame_count')>=start+4,3)
            stop()
            image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
            rgb=bytearray()
            for y in range(720):
                for x in range(1280):
                    pixel=X.XGetPixel(image,x,y);rgb.extend(((pixel>>16)&255,(pixel>>8)&255,pixel&255))
            X.XDestroyImage(image)
            path=pathlib.Path(tempfile.gettempdir())/('red-horizon-aircraft-'+label+'.ppm')
            path.write_bytes(b'P6\n1280 720\n255\n'+rgb)
            assert u32('local_sim_ticks')==frozen_ticks
            # Probe the actual uploaded instance, alongside pixel evidence.
            pose=struct.unpack('<16f',os.pread(memory,64,symbols['mesh_aircraft_pose']))
            os.kill(process.pid,signal.SIGCONT)
            return rgb,str(path),pose

        def changed(a,b,threshold=35):
            return {(x,y) for y in range(170,550) for x in range(260,1020)
                    if max(abs(a[(y*1280+x)*3+c]-b[(y*1280+x)*3+c]) for c in range(3))>threshold}

        frozen_ticks=u32('local_sim_ticks')
        import math,hashlib
        pack=pathlib.Path('content/models/battle.rham').read_bytes()
        header=struct.unpack_from('<12I',pack);mo=header[6]
        focal=max(struct.unpack('<2f',os.pread(memory,8,symbols['view_projection']))[i]*struct.unpack('<2f',os.pread(memory,8,symbols['view_half_size']))[i]for i in range(2))
        expected=[640000.]*9
        for i in range(header[3]):
            row=struct.unpack_from('<8I5f3I',pack,mo+i*64)
            role=row[0]
            expected[role]=max(expected[role],min(8000.,max(row[10:13])*row[8]*focal/1.5)**2)
        reports=[]
        def counts():return tuple(u32(n)for n in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances'))
        fixture(visible=False);background,_,_=capture('projected-detail-background')
        for role in (0,1):
            fixture(role=role,bank=.7,distance=1200.)
            rgb,_,pose=capture('projected-distant-'+str(role))
            assert counts()==(0,1,0),(role,counts())
            pixels=len(changed(background,rgb,12));assert pixels>=2,(role,pixels)
            table=struct.unpack('<9f',os.pread(memory,36,symbols['mesh_actor_detail_ranges2']))
            assert all(abs(a-b)<=max(1.,b*2e-6)for a,b in zip(table,expected)),(table,expected)
            reports.append({'role':'bomber'if role==0 else'fighter','distance_metres':1200,'model_counts':counts(),'visible_changed_pixels':pixels,'actual_instance_role':pose[14]})
        # Both sides of the actual current infantry threshold: exactly one
        # actor representation, no disappearing entity or model+marker overlap.
        distance=math.sqrt(expected[0])
        for value in (distance-2,distance+2):
            fixture(distance=value)
            stop();os.pwrite(memory,struct.pack('<I',0),symbols['sim_entities']+16);os.kill(process.pid,signal.SIGCONT)
            rgb,_,_=capture('projected-infantry-boundary-'+str(round(value)))
            observed=counts();assert observed==((0,1,0)if value<distance else(0,0,1)),(value,distance,observed)
            reports.append({'role':'infantry','distance_metres':value,'model_counts':observed})
        fixture(role=1,distance=1200.,tactical=1);capture('projected-map-marker');assert counts()==(0,0,2),('aircraft plus local human map markers',counts())
        assert u32('local_sim_ticks')==frozen_ticks
        print(json.dumps({'suite':'projected-role-detail-actual-GL','passed':True,'cases':reports,'authoritative_ticks_unchanged':True,'map_marker_retained':True,'ranges2':expected,'executable_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'limits':['Static isolated GL pose/content fixture, not actual combat; original army hardware hotspot verified separately.','800m retained floor, projected authored max span threshold1.5pixels, cap8000m; projected bound is not a guaranteed visible pixel area.']}))

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
