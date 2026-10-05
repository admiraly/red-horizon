#!/usr/bin/env python3
"""Development-only GL aircraft pose/role/altitude regression on a private X server.
Writes fixture records into a private client process; this verifies rendering,
Includes production authority encounters after development-only initial setup.
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

        def u32(name):return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]

        # Isolate one real sourced aircraft; fixture poses are development-only.
        def u32(name):return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
        def fixture(y=100.,heading=0.,pitch=0.,bank=0.,role=0,generation=1,distance=28.,tactical=0,visible=True):
            stop()
            os.pwrite(memory,struct.pack('<I',int(visible)),symbols['sim_count'])
            entity=struct.pack('<2f6I',2000.,3900.+distance,100,0,3,0,0,1)
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
        fixture(visible=False);background,bgpath,_=capture('background')
        fixture();level,levelpath,pose=capture('level-bomber')
        levelmask=changed(background,level);assert len(levelmask)>100,len(levelmask)
        assert pose[1]==100. and pose[15]==1.,pose
        fixture(bank=1.0);banked,bankpath,pose=capture('banked')
        assert abs(pose[11]-1.)<1e-6,pose
        bankmask=changed(level,banked);assert len(bankmask)>100,len(bankmask)
        fixture(pitch=.5,heading=.65);pitched,pitchpath,pose=capture('pitch-heading')
        assert abs(pose[7]-.5)<1e-6 and abs(pose[3]-.65)<1e-6,pose
        assert len(changed(level,pitched))>100
        fixture(role=1);fighter,fighterpath,pose=capture('fighter')
        assert pose[14]==8. and abs(pose[8]-1.)<1e-6,pose
        assert len(changed(level,fighter))>100
        # Paired top-view comparison with uniform normalized bounds excludes
        # size, palette and team tint as explanations for role differences.
        fixture(pitch=1.2,role=0);bomber_top,_,_=capture('bomber-silhouette')
        fixture(pitch=1.2,role=1);fighter_top,_,_=capture('fighter-silhouette')
        def normalized_mask(image):
            mask=changed(background,image,20)
            assert len(mask)>100,len(mask)
            x0=min(x for x,y in mask);x1=max(x for x,y in mask)
            y0=min(y for x,y in mask);y1=max(y for x,y in mask)
            return {(round((x-x0)*63/(x1-x0)),round((y-y0)*63/(y1-y0))) for x,y in mask}
        bm,fm=normalized_mask(bomber_top),normalized_mask(fighter_top)
        silhouette_iou=len(bm&fm)/len(bm|fm)
        assert silhouette_iou<.85,('roles share scaled source silhouette',silhouette_iou)
        # Height must move source geometry, not remain at legacy terrain+90.
        fixture(y=108.);raised,raisedpath,pose=capture('raised')
        assert pose[1]==108.,pose
        raisedmask=changed(background,raised);assert len(raisedmask)>100
        assert sum(y for x,y in raisedmask)/len(raisedmask)<sum(y for x,y in levelmask)/len(levelmask)-30
        # Mid detail, distant marker and map marker share absolute sidecar pose.
        for distance,tactical,label in ((250.,0,'mid'),(900.,0,'distant'),(900.,1,'map')):
            fixture(y=160.,heading=.4,pitch=.2,bank=.3,distance=distance,tactical=tactical)
            _,_,pose=capture(label)
            assert pose[1]==160. and pose[15]==1.,(label,pose)
        # Recycled entities cannot consume an old sidecar.
        fixture(role=1,generation=2);_,_,pose=capture('stale-generation')
        assert pose[1]==90. and pose[15]==0. and pose[14]==3.,pose
        fixture(visible=False);ordnance_background,_,_=capture('ordnance-background')
        def ordnance(kind,active,velocity):
            stop()
            record=struct.pack('<6f4If5I',2000.,100.,3912.,*velocity,240,0,kind,80,18.,0,1,active,1,0)
            os.pwrite(memory,record,symbols['sim_projectiles'])
            os.kill(process.pid,signal.SIGCONT)
        ordnance(3,1,(0.,-8.,0.));bomb,bombpath,_=capture('falling-bomb')
        bombmask=changed(ordnance_background,bomb);assert len(bombmask)>8,len(bombmask)
        ordnance(4,1,(8.,0.,0.));round_image,roundpath,_=capture('air-round')
        roundmask=changed(ordnance_background,round_image);assert len(roundmask)>8,len(roundmask)
        assert bombmask!=roundmask
        ordnance(4,0,(8.,0.,0.));cleared,_,_=capture('inactive-air-round')
        assert len(changed(ordnance_background,cleared))<8
        # Real authority encounter: only initial actor poses/cohorts are fixtures.
        # The flight AI, projectiles, impacts, damage and event records run normally.
        def encounter(fighters=False):
            stop()
            os.pwrite(memory,bytes(64*32),symbols['sim_entities'])
            os.pwrite(memory,bytes(64*64),symbols['sim_aircraft'])
            os.pwrite(memory,bytes(32768),symbols['sim_projectiles'])
            os.pwrite(memory,bytes(8192),symbols['sim_events'])
            os.pwrite(memory,bytes(2048),symbols['effects_records'])
            for name in ('sim_event_sequence','effects_event_cursor','sim_tick_count','sim_projectile_count'):
                os.pwrite(memory,struct.pack('<I',0),symbols[name])
            os.pwrite(memory,struct.pack('<I',64),symbols['sim_count'])
            os.pwrite(memory,struct.pack('<2I',1,1),symbols['sim_alive'])
            os.pwrite(memory,struct.pack('<6I',*[1]*6),symbols['orders'])
            actors=((31,2000.,2500.,0,3,200),(63,2450.,2500.,1,3,200)) if fighters else ((15,2000.,2000.,0,3,200),(32,2900.,2000.,1,0,100))
            for i,x,z,side,kind,hp in actors:
                os.pwrite(memory,struct.pack('<2f6I',x,z,hp,side,kind,0,0xffffffff,1),symbols['sim_entities']+i*32)
            view=(2200.,160.,2200.,0.,0.) if fighters else (2300.,150.,1900.,1.34,-.26)
            os.pwrite(memory,struct.pack('<5f',*view),player_address)
            os.pwrite(memory,struct.pack('<f',view[3]),symbols['yaw'])
            os.pwrite(memory,struct.pack('<f',view[4]),symbols['pitch'])
            os.pwrite(memory,struct.pack('<I',0),symbols['tactical'])
            os.pwrite(memory,struct.pack('<d',1./30.),symbols['thirty'])
            os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
            os.kill(process.pid,signal.SIGCONT)

        def events():
            result=[]
            sequence=u32('sim_event_sequence')
            ring=os.pread(memory,8192,symbols['sim_events'])
            for offset in range(0,8192,32):
                record=struct.unpack_from('<3f3IfI',ring,offset)
                if record[7] and record[7]<=sequence:result.append(record)
            return result

        encounter()
        actual_launch=until(lambda:next((e for e in events() if e[3]==6),None),10)
        actual_impact=until(lambda:next((e for e in events() if e[3]==7),None),10)
        until(lambda:u32('effects_event_cursor')>=actual_impact[7],2)
        stop()
        records=[struct.unpack_from('<7fI',os.pread(memory,2048,symbols['effects_records']),i*32)for i in range(64)]
        assert any(r[7] in (2,3) and r[3]>0 and all(abs(r[c]-actual_impact[c])<.001 for c in range(3)) for r in records),('real bomb impact produced no matching active cosmetic',actual_impact)
        # Place a development observer near the acquired real impact after freezing.
        view=(actual_impact[0],actual_impact[1]+15.,actual_impact[2]-80.,0.,-.185)
        os.pwrite(memory,struct.pack('<5f',*view),player_address)
        os.pwrite(memory,struct.pack('<f',0.),symbols['yaw']);os.pwrite(memory,struct.pack('<f',view[4]),symbols['pitch'])
        os.pwrite(memory,struct.pack('<d',1e30),symbols['thirty']);os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
        os.kill(process.pid,signal.SIGCONT)
        start=u32('frame_count');until(lambda:u32('frame_count')>=start+3,3)
        frozen_ticks=u32('local_sim_ticks')
        impactrgb,impactpath,_=capture('actual-bomb-impact')
        stop();acquired_effects=os.pread(memory,2048,symbols['effects_records'])
        authority_names=(('sim_entities',64*32),('sim_aircraft',64*64),('sim_projectiles',32768),('sim_events',8192))
        acquired_authority=tuple(os.pread(memory,size,symbols[name])for name,size in authority_names)
        os.pwrite(memory,bytes(2048),symbols['effects_records']);os.kill(process.pid,signal.SIGCONT)
        controlrgb,_,_=capture('actual-bomb-impact-control')
        impact_changed=len(changed(impactrgb,controlrgb,10));assert impact_changed>8,impact_changed
        stop()
        assert acquired_authority==tuple(os.pread(memory,size,symbols[name])for name,size in authority_names),'paired cosmetic control changed authority'
        os.pwrite(memory,acquired_effects,symbols['effects_records']);os.kill(process.pid,signal.SIGCONT)
        encounter(fighters=True)
        actual_gun=until(lambda:next((e for e in events() if e[3]==8),None),18)
        until(lambda:u32('effects_event_cursor')>=actual_gun[7],2)
        actual_destroy=until(lambda:next((e for e in events() if e[3]==9),None),18)
        until(lambda:u32('effects_event_cursor')>=actual_destroy[7],2)
        stop()
        records=[struct.unpack_from('<7fI',os.pread(memory,2048,symbols['effects_records']),i*32)for i in range(64)]
        assert any(r[7]==4 and r[3]>0 and all(abs(r[c]-actual_destroy[c])<.001 for c in range(3))for r in records),('real aircraft destruction produced no debris',actual_destroy)
        view=(actual_destroy[0],actual_destroy[1],actual_destroy[2]-80.,0.,0.)
        os.pwrite(memory,struct.pack('<5f',*view),player_address)
        os.pwrite(memory,struct.pack('<f',0.),symbols['yaw']);os.pwrite(memory,struct.pack('<f',0.),symbols['pitch'])
        os.pwrite(memory,struct.pack('<d',1e30),symbols['thirty']);os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
        os.kill(process.pid,signal.SIGCONT)
        start=u32('frame_count');until(lambda:u32('frame_count')>=start+3,3)
        frozen_ticks=u32('local_sim_ticks')
        destroyrgb,destroypath,_=capture('actual-aircraft-destruction')
        stop();acquired_effects=os.pread(memory,2048,symbols['effects_records'])
        authority_names=(('sim_entities',64*32),('sim_aircraft',64*64),('sim_projectiles',32768),('sim_events',8192))
        acquired_authority=tuple(os.pread(memory,size,symbols[name])for name,size in authority_names)
        os.pwrite(memory,bytes(2048),symbols['effects_records']);os.kill(process.pid,signal.SIGCONT)
        controlrgb,_,_=capture('actual-aircraft-destruction-control')
        destroy_changed=len(changed(destroyrgb,controlrgb,10));assert destroy_changed>8,destroy_changed
        stop()
        assert acquired_authority==tuple(os.pread(memory,size,symbols[name])for name,size in authority_names),'paired cosmetic control changed authority'
        os.pwrite(memory,acquired_effects,symbols['effects_records']);os.kill(process.pid,signal.SIGCONT)
        print(json.dumps({'suite':'rendered-aircraft','passed':True,
                          'fixture':'development-only initial cohorts/poses; production flight/weapons/events and GL; paired cosmetic controls preserve authority',
                          'bomber_pixels':len(levelmask),'normalized_silhouette_iou':silhouette_iou,'bank_changed_pixels':len(bankmask),
                          'bomb_pixels':len(bombmask),'air_round_pixels':len(roundmask),
                          'actual_bomb_launch':actual_launch,'actual_bomb_impact':actual_impact,
                          'actual_air_gun':actual_gun,'actual_air_destroyed':actual_destroy,
                          'actual_impact_effect_pixels':impact_changed,'actual_destroy_effect_pixels':destroy_changed,
                          'mid_distant_map_absolute_y':True,'stale_generation_fallback':True,
                          'screenshots':[bgpath,levelpath,bankpath,pitchpath,fighterpath,raisedpath,bombpath,roundpath,impactpath,destroypath]}))

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
