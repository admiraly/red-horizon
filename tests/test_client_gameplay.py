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
            expected=(1-struct.unpack('<I',os.pread(memory,4,symbols['tactical']))[0]) if symbol==0xff09 else None
            XT.XTestFakeKeyEvent(display, code, 1, 0); X.XFlush(display)
            if expected is not None:until(lambda:struct.unpack('<I',os.pread(memory,4,symbols['tactical']))[0]==expected,3)
            elif symbol==ord('r'):until(lambda:player()['reload']>0,3)
            else:time.sleep(hold)
            XT.XTestFakeKeyEvent(display, code, 0, 0); X.XFlush(display); time.sleep(.10)

        def button(down):
            XT.XTestFakeButtonEvent(display, 1, int(down), 0); X.XFlush(display)

        spawn = player(); assert spawn['hp'] == 100 and spawn['connected'] == 1, spawn
        key(ord('w'), .4)
        moved = player(); distance = math.hypot(moved['x'] - spawn['x'], moved['z'] - spawn['z'])
        assert .5 < distance < 4, (spawn, moved)
        button(True); until(lambda: player()['ammo'] == 0, 8); button(False); time.sleep(.1)
        depleted = player(); assert depleted['shots'] >= 30 and depleted['hp'] > 0, depleted
        key(ord('r'), .06); until(lambda: player()['reload'] > 0, 2)
        # Authority can advance before the same frame publishes its window title.
        until(lambda: 'RELOADING' in title(window), 2)
        before = player()['shots']; button(True); time.sleep(.35); button(False)
        assert player()['shots'] == before and player()['ammo'] == 0, player()
        until(lambda: player()['ammo'] == 30 and player()['reload'] == 0, 4)
        button(True); until(lambda:player()['shots']>=before+3,3); button(False); time.sleep(.1)
        final = player(); assert 26 <= final['ammo'] <= 28 and 32 <= final['shots'] <= 34, final
        until(lambda: str(final['ammo']) + '/30' in title(window), 2)
        # Development fixture: isolated clear terrain, actual enemy actor and real
        # server-side rifle/LOS. Python places records; assembly executes damage.
        os.pwrite(memory, struct.pack('<fff', 2000., 17.8, 3900.), player_address)
        enemy_address = symbols['sim_entities'] + 4096 * 32
        enemy = struct.pack('<ff6I', 2000., 3940., 100, 1, 0, 1, 0xffffffff, 1)
        os.pwrite(memory, enemy, enemy_address)
        os.pwrite(memory, struct.pack('<I', 1), symbols['orders'] + 4 * 4)
        os.pwrite(memory, struct.pack('<I', 1), symbols['ai_fronts'] + 4 * 64 + 24) # documented manual-front fixture override
        hits_before = player()['hits']; button(True)
        def published_hit():
            hits=player()['hits']
            published=struct.unpack('<I',os.pread(memory,4,symbols['last_hits']))[0]
            flash=struct.unpack('<f',os.pread(memory,4,symbols['hit_flash']))[0]
            return (hits,published,flash) if hits>hits_before and published>hits_before and flash>0 else None
        observed_hit_feedback=until(published_hit,2)
        button(False)
        # The cue is finite: observe its actual publication rather than waiting
        # an arbitrary 50ms and demanding that the cue has not yet expired.
        accepted_hits = player()['hits'] - hits_before
        # Stage a different living infantry body with its genuine finite stock.
        # The old fixture changed an infantry body into a tank without equipping
        # tank shells and relied on synthetic tank-as-rifle human damage.
        # Preserve actual HP/generation/ammunition; relocate once, then let the
        # real infantry weapon, death and safe deployment run without renewal.
        os.kill(process.pid,signal.SIGSTOP)
        try:
            _,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
            attacker=None
            for ident in range(4096,8192):
                if ident==4096:continue
                values=struct.unpack('<ff6I',os.pread(memory,32,symbols['sim_entities']+ident*32))
                weapon=struct.unpack('<8I',os.pread(memory,32,symbols['infantry_weapons']+ident*32))
                if values[2]>0 and values[3]==1 and values[4]==0 and weapon[0]==values[7] and weapon[1]>=10:
                    attacker=(ident,values,weapon);break
            assert attacker,'no genuinely armed living infantry fixture source'
            ident,values,weapon=attacker
            os.pwrite(memory,struct.pack('<ff6I',2040.,3900.,values[2],1,0,1,0xffffffff,values[7]),symbols['sim_entities']+ident*32)
            assert struct.unpack('<8I',os.pread(memory,32,symbols['infantry_weapons']+ident*32))==weapon
        finally:os.kill(process.pid,signal.SIGCONT)
        damaged = until(lambda: p if (p := player())['hp'] < 100 and p['suppression'] > 0 else None, 3)
        assert damaged['suppression'] > 0, damaged
        until(lambda: player()['hp'] == 0, 9)
        dead = player(); assert 0 < dead['respawn'] <= 30, dead
        until(lambda: 'DOWN: SAFE REDEPLOY' in title(window), 1)
        # Pixel proof for the actual GL HUD's red redeployment bar.
        image = X.XGetImage(display, window, 0, 0, 1280, 720, W(-1).value, 2); assert image
        pixel = X.XGetPixel(image, 640, 79); X.XDestroyImage(image)
        red, green, blue = (pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255
        assert red > 100 and red > green * 2, ('redeploy HUD pixel', red, green, blue)
        generation = dead['generation']
        until(lambda: player()['hp'] == 100 and player()['generation'] > generation, 4)
        redeployed = player(); assert math.hypot(redeployed['x'] - 2040, redeployed['z'] - 3900) > 160, redeployed
        until(lambda: 'HP 100 ' in title(window), 2)
        final = player()
        key(0xff09); until(lambda: 'TACTICAL' in title(window))
        button(True); time.sleep(.3); button(False)
        assert player()['shots'] == final['shots'], 'tactical click fired the rifle'
        # Freeze only the final observation boundary. Escape press/release is
        # queued while stopped; the callback latch exits before another sim tick.
        # Exit telemetry publishes the last rendered HUD HP. A stopped mid-frame
        # authority may already be newer; compare the matching HUD epoch.
        os.kill(process.pid,signal.SIGSTOP)
        try:
            _,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
            final=player()
            final_hud_hp=struct.unpack('<I',os.pread(memory,4,symbols['player_hp']))[0]
            key(0xff1b)
        finally:os.kill(process.pid,signal.SIGCONT)
        stdout, stderr = process.communicate(timeout=5); assert process.returncode == 0, (stdout, stderr)
        assert f"hp={final_hud_hp}" in stdout and 'player id=0' in stdout, stdout
        print(json.dumps({'suite':'authoritative-client-gameplay','passed':True,'spawn':spawn,'moved_metres':distance,'final':final,'exit_hp_is_last_rendered_hud_value':final_hud_hp,'rendered_health_title':True,'accepted_hits':accepted_hits,'observed_hit_feedback':observed_hit_feedback,'redeploy_pixel':[red,green,blue],'damage_source_actual_infantry_id':ident,'initial_attacker_weapon':weapon,'attacker_hp_generation_preserved':True,'damaged':damaged,'dead':dead,'redeployed':redeployed,'stdout':stdout}))
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
