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
from hud_pixels import text_visible

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

        spawn = player(); assert spawn['hp'] == 100 and spawn['connected'] == 1, spawn
        until(lambda:text_visible(X,display,window,0,'COMPANY '),3)
        until(lambda:text_visible(X,display,window,1,'COMPANY '),3)
        # Real solo GUI commands address one exclusive company, stay edge-triggered
        # while the key is held, and leave the autonomous front waypoint untouched.
        def u32(name,offset=0):return struct.unpack('<I',os.pread(memory,4,symbols[name]+offset))[0]
        company=u32('player_companies');assert company<1536
        until(lambda:text_visible(X,display,window,0,'|',column=len(f'COMPANY {company} ')),3)
        control=symbols['company_controls']+company*32
        def company_record():return struct.unpack('<4I2f2I',os.pread(memory,32,control))
        def actor_rows():
            data=os.pread(memory,8192*32,symbols['sim_entities'])
            return [struct.unpack_from('<2f6I',data,i*32)for i in range(8192)]
        def safe_company_infantry():
            rows=actor_rows();hazards=os.pread(memory,8192*32,symbols['hazard_states'])
            return {i:(r[0],r[1]) for i,r in enumerate(rows)
                    if r[2] and r[3]==0 and r[4]==0 and r[5]==1 and i>>7==company%256
                    and struct.unpack_from('<I',hazards,i*32+4)[0]==0}
        waypoint_before=os.pread(memory,24,symbols['sim_waypoints'])
        key(0xffbe) # F1 inspects a front this solo player does not own.
        sequence=company_record()[6];key(ord('2'),.4)
        until(lambda:'ORDER DENIED: SELECT YOUR OWN FRONT' in title(window),2)
        assert company_record()[6]==sequence and os.pread(memory,24,symbols['sim_waypoints'])==waypoint_before
        key(0xffbf) # F2 returns to the assigned company front.
        tick_before=u32('sim_tick_count');funds_before=u32('sim_requisition')
        key(ord('2'),.7)
        until(lambda:'ORDER ACCEPTED: COST 5' in title(window),2)
        tick_after=u32('sim_tick_count');funds_after=u32('sim_requisition')
        assert company_record()[6]==sequence+1,'held order key issued multiple charged commands'
        assert funds_after==funds_before+39*(tick_after//30-tick_before//30)-5
        held_initial=safe_company_infantry();assert len(held_initial)>=8,held_initial
        start_tick=u32('sim_tick_count');until(lambda:u32('sim_tick_count')>=start_tick+30,3)
        held_final=safe_company_infantry()
        retained=set(held_initial)&set(held_final);assert len(retained)>=8
        held_travel=max(math.dist(held_initial[i],held_final[i])for i in retained)
        assert held_travel<.001,('owned infantry did not hold',held_travel)
        advance_initial=safe_company_infantry();key(ord('1'),.7)
        until(lambda:company_record()[6]==sequence+2,2)
        start_tick=u32('sim_tick_count');until(lambda:u32('sim_tick_count')>=start_tick+30,3)
        advance_final=safe_company_infantry();retained=set(advance_initial)&set(advance_final)
        assert retained and max(math.dist(advance_initial[i],advance_final[i])for i in retained)>1
        assert os.pread(memory,24,symbols['sim_waypoints'])==waypoint_before
        assert f'COMPANY {company} | ORDER ACCEPTED' in title(window)
        # Actual tactical click selects a finite company point and charges once.
        key(0xff09);until(lambda:'TACTICAL' in title(window),2)
        shots_before=player()['shots'];tick_before=u32('sim_tick_count');funds_before=u32('sim_requisition')
        XT.XTestFakeMotionEvent(display,-1,788,368,0);X.XFlush(display);time.sleep(.12)
        button(True);time.sleep(.4);button(False);time.sleep(.12)
        until(lambda:company_record()[6]==sequence+3,2)
        ordered=company_record();assert abs(ordered[4]-4994.375)<.01 and abs(ordered[5]-3904.44444)<.01,ordered
        tick_after=u32('sim_tick_count');funds_after=u32('sim_requisition')
        assert funds_after==funds_before+39*(tick_after//30-tick_before//30)-5
        assert player()['shots']==shots_before and os.pread(memory,24,symbols['sim_waypoints'])==waypoint_before
        until(lambda:text_visible(X,display,window,1,'ORDER ACCEPTED'),3)
        solo_company={'framebuffer_company_and_accepted_text':True,'key':company,'held_safe_infantry':len(held_initial),'held_travel_m':held_travel,
                      'one_charge_per_key_press':True,'foreign_front_denied':True,
                      'autonomous_front_waypoints_preserved':True,'physical_advance':True,'tactical_click_one_charge':True,'tactical_point':[ordered[4],ordered[5]]}
        # Actual tactical pixels distinguish owned formation from allies on
        # another front within the same128-ID block. Observer never writes state.
        start_frame=u32('frame_count');until(lambda:u32('frame_count')>=start_frame+3,3)
        os.kill(process.pid,signal.SIGSTOP)
        _,stopped=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(stopped)
        try:
            rows=actor_rows()
            owned=next(r for i,r in enumerate(rows)if r[2] and r[3]==0 and r[4]==0 and r[5]==1 and i>>7==company%256)
            unowned=next(r for i,r in enumerate(rows)if r[2] and r[3]==0 and r[4]==0 and r[5]==0 and i>>7==company%256)
            image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
            def count_pixels(row,owned_colour):
                px=round(((row[0]-4000)/4300+1)*640);py=round((1-(row[1]-4000)/4300)*360);count=0
                for dx in range(-4,5):
                    for dy in range(-4,5):
                        pixel=X.XGetPixel(image,px+dx,py+dy);r,g,b=(pixel>>16)&255,(pixel>>8)&255,pixel&255
                        count+=(80<r<160 and g>200 and 40<b<120)if owned_colour else(r<85 and 110<g<180 and b>170)
                return count
            owned_pixels=count_pixels(owned,True);unowned_pixels=count_pixels(unowned,False);foreign_green=count_pixels(unowned,True)
            X.XDestroyImage(image)
            assert owned_pixels>0 and unowned_pixels>0 and foreign_green==0,(owned_pixels,unowned_pixels,foreign_green,owned,unowned)
            solo_company.update(owned_marker_pixels=owned_pixels,same_ID_block_foreign_front_blue_pixels=unowned_pixels,foreign_front_owned_colour_pixels=foreign_green)
        finally:os.kill(process.pid,signal.SIGCONT)
        key(0xff1b)
        stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'actual-solo-company-command','passed':True,'company':solo_company,
                          'executable_sha256':__import__('hashlib').sha256(EXE.read_bytes()).hexdigest(),
                          'limits':['Real solo GLFW/software GL/private Xvfb; no desktop or hardware GPU performance claim.',
                                    'Read-only authority observer; actual keyboard commands drive production company movement.']}))
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
