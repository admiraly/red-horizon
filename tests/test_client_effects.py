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

        # Development-only encounter isolation: preserve every living army
        # record's HP/kind/side/generation, stocks, shell pool and event ring.
        # Relocate the background cohorts into distant hold areas so default
        # 8192-unit combat cannot exhaust the480 AI shell slots during this
        # focused renderer/input fixture. Actual tick/AI/contact remains live.
        stop()
        army_count=struct.unpack('<I',os.pread(memory,4,symbols['sim_count']))[0]
        cohort=bytearray(os.pread(memory,army_count*32,symbols['sim_entities']))
        for i in range(army_count):
            side=struct.unpack_from('<I',cohort,i*32+12)[0]
            struct.pack_into('<ff',cohort,i*32,1000. if side==0 else 7000.,7000.)
        os.pwrite(memory,cohort,symbols['sim_entities'])
        for slot in range(6):
            os.pwrite(memory,struct.pack('<I',1),symbols['orders']+slot*4)
            os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+slot*64+24)
        os.kill(process.pid,signal.SIGCONT)

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
        stop()
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
        # Let pre-isolation shots leave the real pool naturally; never fabricate
        # empty slots. A240tick TTL bounds old-flight drain to8seconds.
        until(lambda:u32('sim_projectile_count')<480,9)
        pool_before_encounter=u32('sim_projectile_count')
        # Position an actual shell-capable source and opposite living target.
        # Real AI targeting/world ticks launch the shell; no event/pool writes.
        entities=struct.unpack('<'+('ff6I'*u32('sim_count')),os.pread(memory,32*u32('sim_count'),symbols['sim_entities']))
        tank=next(i for i in range(u32('sim_count')) if entities[i*8+2]>0 and entities[i*8+3]==0 and entities[i*8+4]==1)
        opponent=next(i for i in range(u32('sim_count')) if entities[i*8+2]>0 and entities[i*8+3]==1 and entities[i*8+4]==0)
        stop()
        os.pwrite(memory,struct.pack('<ff',2000.,3860.),symbols['sim_entities']+tank*32)
        os.pwrite(memory,struct.pack('<ff',2000.,3980.),symbols['sim_entities']+opponent*32)
        # Observe200m from the opponent, outside its real160m player threat.
        # The former80m observer died in10ticks before a12tick tank flight.
        os.pwrite(memory,struct.pack('<fff',2000.,17.8242,3780.),player_address)
        for i in (tank,opponent):
            front=entities[i*8+5];side=entities[i*8+3]
            os.pwrite(memory,struct.pack('<I',1),symbols['orders']+(side*3+front)*4)
            os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+(side*3+front)*64+24)
        before_impacts=u32('effects_impacts');before_events=u32('sim_event_sequence')
        os.kill(process.pid,signal.SIGCONT)
        def matching_launch():
            ring=os.pread(memory,8192,symbols['sim_events'])
            for slot in range(256):
                event=struct.unpack_from('<fffIIIfI',ring,slot*32)
                if event[7]>before_events and event[3]==1 and event[4]==0 and abs(event[0]-2000)<.1 and abs(event[2]-3860)<.1:return event
            return None
        actual_launch=until(matching_launch,5)
        assert u32('sim_projectile_count')>0, 'launch produced no real pooled shell'

        def matching_impact():
            ring=os.pread(memory,8192,symbols['sim_events'])
            for slot in range(256):
                event=struct.unpack_from('<fffIIIfI',ring,slot*32)
                if event[7]>before_events and event[3]==3 and event[4]==0 and abs(event[0]-2000)<10 and 3960<event[2]<3990:return event
            return None
        actual_impact=until(matching_impact,5)
        assert actual_impact[5]>actual_launch[5] and actual_impact[7]>actual_launch[7], 'impact was not delayed after launch'
        assert player()['hp']==100, 'isolated observer entered enemy player-threat range'
        until(lambda:u32('effects_event_cursor')>=actual_impact[7] and u32('effects_impacts')>before_impacts,2)
        impact_frame=u32('frame_count')
        until(lambda:u32('frame_count')>=impact_frame+2,1)
        stop()
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
        # Actual E/Q vehicle controls: place only the human near the existing tank.
        tank_x,tank_z=struct.unpack('<ff',os.pread(memory,8,symbols['sim_entities']+tank*32))
        terrain_y=12+(tank_x-4000)**2*.000001+(tank_z-4000)**2*.0000005+max(0,1-abs(tank_x-4000)/800)*18
        os.pwrite(memory,struct.pack('<fff',tank_x-2,terrain_y+1.8,tank_z),player_address)
        vehicle_address=symbols['sim_player_vehicle']
        def attached():return struct.unpack('<i',os.pread(memory,4,vehicle_address))[0]
        key(ord('e'));until(lambda:attached()==tank,2)
        until(lambda:f'ARMOR #{tank} CANNON' in title(window) and ' HULL ' in title(window),2)
        position=player();key(ord('w'),.35);driven=player()
        drive_distance=math.hypot(driven['x']-position['x'],driven['z']-position['z'])
        assert drive_distance>.5,(position,driven)
        vehicle=symbols['sim_vehicles']
        ammo_before=struct.unpack('<I',os.pread(memory,4,vehicle+16))[0]
        until(lambda:struct.unpack('<I',os.pread(memory,4,vehicle+20))[0]==0,2)
        cannon_seq=u32('sim_event_sequence');rifle_shots=player()['shots']
        button(True);until(lambda:struct.unpack('<I',os.pread(memory,4,vehicle+16))[0]<ammo_before,2);button(False)
        assert player()['shots']==rifle_shots,'cannon trigger consumed infantry rifle rounds'
        def actual_cannon_launch():
            ring=os.pread(memory,8192,symbols['sim_events'])
            for slot in range(256):
                event=struct.unpack_from('<fffIIIfI',ring,slot*32)
                if event[7]>cannon_seq and event[3]==1 and event[4]==0 and abs(event[0]-driven['x'])<15 and abs(event[2]-driven['z'])<15:return event
            return None
        cannon_launch=until(actual_cannon_launch,2)
        view_frame=u32('frame_count');until(lambda:u32('frame_count')>=view_frame+2,1)
        stop()
        image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
        pixel=X.XGetPixel(image,1056,637);red,green,blue=(pixel>>16)&255,(pixel>>8)&255,pixel&255
        assert red>180 and green>80 and blue<100,('cannon HUD pixel',red,green,blue)
        bright_sky=0
        for sky_x in (400,640,880):
            for sky_y in (140,200,260):
                sky=X.XGetPixel(image,sky_x,sky_y);sr,sg,sb=(sky>>16)&255,(sky>>8)&255,sky&255
                bright_sky+=sr>180 and sg>130 and sb<100
        assert bright_sky<3,('near-camera cannon geometry covered sky',bright_sky)
        rgb=bytearray()
        for y in range(720):
            for x in range(1280):
                pixel=X.XGetPixel(image,x,y);rgb.extend(((pixel>>16)&255,(pixel>>8)&255,pixel&255))
        X.XDestroyImage(image)
        pathlib.Path('/tmp/red-horizon-vehicle-hud.ppm').write_bytes(b'P6\n1280 720\n255\n'+rgb)
        os.kill(process.pid,signal.SIGCONT)
        key(ord('q'));until(lambda:attached()==-1,2)
        until(lambda:'ON FOOT | E board Q exit' in title(window),2)
        key(0xff1b)
        stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'rendered-tracer','passed':True,'shots':shots,'tracers':total,'yellow_pixels':yellow,'screenshot':'/tmp/red-horizon-tracer.ppm','shell_source':tank,'impact_pixels':orange,'impact_events':impacts,'event_sequence':events,'actual_launch':actual_launch,'actual_impact':actual_impact,'drive_metres':drive_distance,'cannon_launch':cannon_launch,'cannon_hud_pixel':[red,green,blue],'fixture':'development-only remote held cohorts and encounter poses; HP/ammo/pool/events preserved; real AI/input/GL','observer_enemy_metres':200,'pool_before_encounter':pool_before_encounter}))
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
