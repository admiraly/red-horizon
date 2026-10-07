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
        process = subprocess.Popen([str(EXE)]+(['--tactical']if '--depots' in sys.argv else [])+['--bindings',str(pathlib.Path(__file__).with_name('bindings-remapped.cfg').resolve())], cwd=EXE.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

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
        if '--supply' in sys.argv:
            until(lambda:struct.unpack('<I',os.pread(memory,4,symbols['supply_hud_available']))[0]==1)
            until(lambda:text_visible(X,display,window,0,'OWN LOW',origin=(16,562)))
            until(lambda:text_visible(X,display,window,0,'RDS',origin=(16,584)))
            def supply_unknown_visible():
                text=os.pread(memory,64,symbols['supply_hud_text']).split(b'\0')[0].decode()
                return 'UNKNOWN' in text and text_visible(X,display,window,0,'UNKNOWN',column=text.index('UNKNOWN'),origin=(16,584))
            until(supply_unknown_visible)
            if '--depots' in sys.argv:
                until(lambda:struct.unpack('<I',os.pread(memory,4,symbols['depot_hud_available']))[0]==1)
                until(lambda:text_visible(X,display,window,0,'OWN DEPOTS',origin=(16,10)))
                header=struct.unpack('<4I',os.pread(memory,16,symbols['depot_hud_report']))
                assert header[0]==0 and header[1]>0 and header[2]==2 and header[3]==0
                def depot_ready_visible():
                    text=os.pread(memory,64,symbols['depot_hud_text']).split(b'\0')[0].decode()
                    return 'R READY' in text and text_visible(X,display,window,0,'R READY',column=text.index('R READY'),origin=(16,54))
                until(depot_ready_visible)
            report=struct.unpack('<10I',os.pread(memory,40,symbols['supply_hud_report']))
            assert report[0]==0 and report[1]>0 and report[2]<768 and report[5]<=report[4]<=report[3]-report[7] and report[8:]==(0,0)
            print(json.dumps({'suite':'graphical-solo-company-supply','passed':True,'report':report,'actual_low_rounds_unknown_labels':True,'observer_memory_writes':False,'depot_inventory_labels':('--depots' in sys.argv),'limits':['Live own-company HUD labels in ordinary solo authority, no constructed shortage fixture.','Low/empty/unknown arithmetic independently checked in API fixtures; not an art/hardware-quality claim.']}))
            raise SystemExit(0)


        def player():
            values = struct.unpack('<5f11I', os.pread(memory, 64, player_address))
            return dict(zip(('x','y','z','yaw','pitch','hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation'), values))

        def key(symbol, hold=.12, observed=None):
            code = X.XKeysymToKeycode(display, symbol); assert code
            XT.XTestFakeKeyEvent(display, code, 1, 0); X.XFlush(display)
            try:
                time.sleep(hold)
                if observed is not None:until(observed,2)
            finally:
                XT.XTestFakeKeyEvent(display, code, 0, 0); X.XFlush(display); time.sleep(.10)

        def button(down):
            XT.XTestFakeButtonEvent(display, 1, int(down), 0); X.XFlush(display)

        def u32(name,offset=0):return struct.unpack('<I',os.pread(memory,4,symbols[name]+offset))[0]
        def f32(name):return struct.unpack('<f',os.pread(memory,4,symbols[name]))[0]
        def mouse(number,down):
            XT.XTestFakeButtonEvent(display,number,int(down),0);X.XFlush(display)
            if False:pass
        def motion(x,y):XT.XTestFakeMotionEvent(display,-1,x,y,0);X.XFlush(display);time.sleep(.12)
        def record():return struct.unpack('<4I2f2I',os.pread(memory,32,control))
        company=u32('player_companies');assert company<1536
        control=symbols['company_controls']+company*32

        # Every action is remapped; all process observers are read-only.
        custom=pathlib.Path(__file__).with_name('bindings-remapped.cfg')
        expected=['UP','DOWN','LEFT','RIGHT','RSHIFT','RCTRL','ENTER','T','B','N','L','M','C','X','MMB','5','6','7','8','HOME','END','INSERT','F12','F1','F2','F3','F4','F5','F6','F7','9']
        assert u32('binding_codes',0)==265 and u32('binding_codes',12*4)==ord('C')
        until(lambda:text_visible(X,display,window,0,'5 ADVANCE',column=len(f'COMPANY {company} | FRONT 1 | ')),3)
        # Unbound default movement/fire/order/quit inputs do nothing.
        before=player();key(ord('w'),.3);after=player()
        assert before['generation']==after['generation'] and math.dist((before['x'],before['z']),(after['x'],after['z']))<.001
        key(0xff1b);assert process.poll() is None,'unbound Escape still quit'
        sequence=record()[6];key(ord('4'));assert record()[6]==sequence
        # Actual remapped motion and body posture; no authority fixture edits.
        before=player();key(0xff52,.6);after=player()
        movement=math.dist((before['x'],before['z']),(after['x'],after['z']))
        assert before['generation']==after['generation'] and 1<movement<6,(before,after)
        code=X.XKeysymToKeycode(display,0xffe4);XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display);time.sleep(.25)
        assert u32('intent_buttons')&32,'remapped crouch not routed';XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display)
        # Remapped held fire/reload, with actual finite player magazine.
        mouse(1,True);time.sleep(.2);mouse(1,False);shots=player()['shots'];assert shots==0
        key(ord('l'),.45);until(lambda:player()['shots']>shots,2);ammo=player()['ammo'];assert ammo<30
        key(ord('t'),observed=lambda:player()['reload']>0)
        # Remapped wheel opens on C, cancels on X; old middle is now QUIT,
        # so cancellation is tested through the actual keyboard event callback.
        code=X.XKeysymToKeycode(display,ord('c'));XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display)
        until(lambda:u32('wheel_active')==1,2);motion(720,360);key(ord('x'))
        assert u32('wheel_active')==0 and record()[6]==sequence
        XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display);until(lambda:u32('wheel_down')==0,2)
        # Hold C and release over FOLLOW: one real accepted command and label.
        XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display);until(lambda:u32('wheel_active')==1,2)
        motion(720,360);XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display)
        until(lambda:record()[6]==sequence+1,2);assert record()[2]==3
        until(lambda:text_visible(X,display,window,1,'ORDER ACCEPTED: FOLLOW'),3)
        # Direct order modes, selection and keyboard tactical click.
        key(ord('6'),.6);until(lambda:record()[6]==sequence+2,2);assert record()[2]==1
        key(0xff50,observed=lambda:u32('selected_front')==0);seq=record()[6]
        key(ord('7'),observed=lambda:'ORDER DENIED: SELECT YOUR OWN FRONT' in title(window))
        until(lambda:'ORDER DENIED: SELECT YOUR OWN FRONT' in title(window),2);assert record()[6]==seq
        key(0xff57,observed=lambda:u32('selected_front')==1)
        key(ord('m'),observed=lambda:u32('tactical')==1)
        motion(788,368);key(ord('l'),.5);until(lambda:record()[6]==sequence+3,2)
        assert record()[2]==0 and abs(record()[4]-4994.375)<.01 and abs(record()[5]-3904.44444)<.01
        key(ord('9'),.6);until(lambda:record()[6]==sequence+4,2);assert record()[2]==4
        assert abs(record()[4]-4994.375)<.01 and abs(record()[5]-3904.44444)<.01
        until(lambda:text_visible(X,display,window,1,'ORDER ACCEPTED: DEFEND AREA'),3)
        # Weather binding and vehicle hints use loaded names, no stale defaults.
        key(0xffc9);until(lambda:'WEATHER overcast (F12 CYCLE)' in title(window),2)
        assert 'B BOARD N EXIT' in title(window)
        # Mouse-bound quit preserves a press/release delivered in one batch.
        os.kill(process.pid,signal.SIGSTOP);_,stopped=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(stopped)
        try:mouse(2,True);XT.XTestFakeButtonEvent(display,2,0,0);X.XFlush(display);time.sleep(.05)
        finally:os.kill(process.pid,signal.SIGCONT)
        stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        for action,key_name in (line.split('=')for line in custom.read_text().splitlines()if line and not line.startswith('#')):assert f'binding {action}={key_name}' in stdout
        print(json.dumps({'suite':'actual-remapped-client-input','passed':True,'actions_remapped':31,'physical_same_body_movement_m':movement,'default_keys_inactive':True,'finite_fire_reload':True,'crouch_routed':True,'keyboard_wheel_cancel_and_follow':True,'held_orders_one_charge':True,'foreign_front_rejected':True,'keyboard_tactical_point':[4994.375,3904.44444],'remapped_defend_one_charge_and_ack':True,'binding_hints_and_startup_report':True,'mouse_quit_same_event_batch':True,'executable_sha256':__import__('hashlib').sha256(EXE.read_bytes()).hexdigest(),'limits':['Real solo GLFW/OpenGL/XTest with read-only authority observers; not hardware or complete gameplay acceptance.']}))
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
