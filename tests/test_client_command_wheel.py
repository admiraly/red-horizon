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
        process = subprocess.Popen([str(EXE)]+(['--width','320','--height','240'] if '--small' in sys.argv else []), cwd=EXE.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

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
        memory = os.open(f'/proc/{process.pid}/mem', os.O_RDONLY)
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

        def u32(name,offset=0):return struct.unpack('<I',os.pread(memory,4,symbols[name]+offset))[0]
        def f32(name):return struct.unpack('<f',os.pread(memory,4,symbols[name]))[0]
        def mouse(number,down):
            XT.XTestFakeButtonEvent(display,number,int(down),0);X.XFlush(display)
            if number==2 and not down:until(lambda:u32('wheel_down')==0,2)
        def motion(x,y):XT.XTestFakeMotionEvent(display,-1,x,y,0);X.XFlush(display);time.sleep(.12)
        def record():return struct.unpack('<4I2f2I',os.pread(memory,32,control))
        company=u32('player_companies');assert company<1536
        control=symbols['company_controls']+company*32
        key(0xffbf) # Own front1, no authority edits.
        if '--small' in sys.argv:
            mouse(2,True);until(lambda:u32('wheel_active')==1,2)
            labels={'MOVE':(136,43),'HOLD':(67,112),'FOLLOW':(193,112),'RETREAT':(118,181)}
            for word,origin in labels.items():until(lambda:text_visible(X,display,window,0,word,width=320,height=240,origin=origin),3)
            image=X.XGetImage(display,window,0,0,320,240,W(-1).value,2);assert image
            try:
                rgb=bytearray()
                for y in range(240):
                    for x in range(320):
                        pixel=X.XGetPixel(image,x,y);rgb.extend(((pixel>>16)&255,(pixel>>8)&255,pixel&255))
                pathlib.Path('/tmp/command-wheel-small.ppm').write_bytes(b'P6\n320 240\n255\n'+rgb)
            finally:X.XDestroyImage(image)
            mouse(2,False);assert u32('wheel_active')==0 and record()[6]==0
            key(0xff1b);stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
            print(json.dumps({'suite':'actual-small-command-wheel','passed':True,'viewport':[320,240],'four_framebuffer_labels':labels,'center_cancel_uncharged':True,'capture':'/tmp/command-wheel-small.ppm','limits':['Minimum viewport software GL label/layout check; human readability unverified.']}))
            raise SystemExit(0)
        initial=record();shots=player()['shots'];yaw=f32('yaw');pitch=f32('pitch')
        mouse(2,True);until(lambda:u32('wheel_active')==1,2)
        assert u32('wheel_point_valid')==1,'default crosshair failed to intersect visible ground'
        aimed=struct.unpack('<2f',os.pread(memory,8,symbols['wheel_point']))
        assert math.dist(aimed,(player()['x'],player()['z']))>5
        until(lambda:text_visible(X,display,window,0,'MOVE',origin=(616,266)),3)
        until(lambda:text_visible(X,display,window,0,'HOLD',origin=(530,352)),3)
        until(lambda:text_visible(X,display,window,0,'FOLLOW',origin=(690,352)),3)
        until(lambda:text_visible(X,display,window,0,'RETREAT',origin=(598,438)),3)
        tick=u32('sim_tick_count');motion(640,280)
        until(lambda:u32('wheel_selected')==0,2)
        assert abs(f32('yaw')-yaw)<.00001 and abs(f32('pitch')-pitch)<.00001,'menu cursor changed aim'
        mouse(1,True);held_code=X.XKeysymToKeycode(display,ord('4'));XT.XTestFakeKeyEvent(display,held_code,1,0);X.XFlush(display);time.sleep(.6);mouse(1,False)
        assert record()==initial and player()['shots']==shots,'open wheel leaked direct key/fire intent'
        assert u32('sim_tick_count')>tick+5,'wheel paused the battlefield'
        image=X.XGetImage(display,window,0,0,1280,720,W(-1).value,2);assert image
        selected_pixel=X.XGetPixel(image,650,310);X.XDestroyImage(image)
        r,g,b=(selected_pixel>>16)&255,(selected_pixel>>8)&255,selected_pixel&255
        assert 20<r<40 and 70<g<90 and 55<b<75,('selected wedge colour',r,g,b)
        tick0=u32('sim_tick_count');funds0=u32('sim_requisition');mouse(2,False)
        until(lambda:record()[6]==initial[6]+1,2);ordered=record()
        assert ordered[2]==0 and math.dist(ordered[4:6],aimed)<.001,('crosshair target not committed',ordered,aimed)
        tick1=u32('sim_tick_count');funds1=u32('sim_requisition')
        assert funds1==funds0+39*(tick1//30-tick0//30)-5
        until(lambda:text_visible(X,display,window,1,'ORDER ACCEPTED'),3)
        time.sleep(.6);assert record()[6]==ordered[6],'release or held direct key repeated a command'
        XT.XTestFakeKeyEvent(display,held_code,0,0);X.XFlush(display);time.sleep(.1)
        # Center release, right cancel and Escape cancel do not spend or quit.
        before=record();mouse(2,True);until(lambda:u32('wheel_active')==1,2);mouse(2,False);until(lambda:u32('wheel_active')==0,2);assert record()==before
        mouse(2,True);until(lambda:u32('wheel_active')==1,2);motion(720,360);mouse(3,True);until(lambda:u32('wheel_active')==0,2);mouse(3,False);time.sleep(.2);assert u32('wheel_active')==0;mouse(2,False);assert record()==before
        mouse(2,True);until(lambda:u32('wheel_active')==1,2);motion(560,360)
        # Both Escape edges delivered in one actual GLFW event batch.
        os.kill(process.pid,signal.SIGSTOP);_,stopped=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(stopped)
        try:
            code=X.XKeysymToKeycode(display,0xff1b);XT.XTestFakeKeyEvent(display,code,1,0);XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display);time.sleep(.05)
        finally:os.kill(process.pid,signal.SIGCONT)
        until(lambda:u32('wheel_active')==0,2);assert process.poll() is None;mouse(2,False);assert record()==before
        # Follow and hold go through the same authority lease/cost; raw move
        # waypoint survives. Restored cursor seeding prevents a camera snap.
        yaw=f32('yaw');pitch=f32('pitch');mouse(2,True);until(lambda:u32('wheel_active')==1,2);motion(720,360);mouse(2,False)
        until(lambda:record()[6]==before[6]+1,2);assert record()[2]==3 and record()[4:6]==ordered[4:6]
        time.sleep(.4);assert abs(f32('yaw')-yaw)<.00001 and abs(f32('pitch')-pitch)<.00001
        mouse(2,True);until(lambda:u32('wheel_active')==1,2);XT.XTestFakeMotionEvent(display,-1,560,360,0);mouse(2,False);until(lambda:record()[2]==1,2)
        assert record()[4:6]==ordered[4:6] and player()['shots']==shots
        # Inspect foreign front; normal authority rejects a released order.
        key(0xffbe);seq=record()[6];mouse(2,True);until(lambda:u32('wheel_active')==1,2);motion(640,440);mouse(2,False)
        until(lambda:'ORDER DENIED: SELECT YOUR OWN FRONT' in title(window),2);assert record()[6]==seq
        # A middle hold on tactical map cannot start a hidden first-person menu.
        key(0xff09);mouse(2,True);time.sleep(.3);assert u32('wheel_active')==0;mouse(2,False)
        key(0xff1b);stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'actual-solo-command-wheel','passed':True,'crosshair_point':aimed,'committed_point':ordered[4:6],'four_framebuffer_labels':True,'selection_colour_rgb':[r,g,b],'release_one_charge':True,'held_input_no_fire_or_order':True,'direct_key_held_through_close_consumed':True,'escape_same_event_batch_cancels':True,'world_continues':True,'aim_frozen_and_cursor_restored':True,'center_right_escape_cancel':True,'follow_hold_preserve_waypoint':True,'release_uses_final_cursor':True,'foreign_front_rejected':True,'tactical_middle_suppressed':True,'executable_sha256':__import__('hashlib').sha256(EXE.read_bytes()).hexdigest(),'limits':['Actual GLFW/GL/XTest on private software GL, not target hardware quality.','Four existing orders only; full contextual roster/remapping separate.']}))
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
