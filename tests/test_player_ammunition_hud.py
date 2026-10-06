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

server = process = display = memory = host = None
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
        connection=[]
        if '--udp' in sys.argv:
            host=subprocess.Popen([str(pathlib.Path(sys.argv[2]).resolve()),'--port','0','--ticks','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            ready=json.loads(host.stdout.readline());connection=['--connect','127.0.0.1','--port',str(ready['port'])]
        process = subprocess.Popen([str(EXE)]+connection+(['--width','320','--height','240'] if '--small' in sys.argv else []), cwd=EXE.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

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

        from hud_pixels import text_visible
        width,height=(320,240) if '--small' in sys.argv else (1280,720)
        def stock():
            if host is None:return struct.unpack('<8I',os.pread(memory,32,symbols['player_ammunition']))
            until(lambda:struct.unpack('<I',os.pread(memory,4,symbols['rifle_hud_available']))[0]==1,3)
            r=struct.unpack('<10I',os.pread(memory,40,symbols['rifle_hud_report']));assert r[0]==0 and r[8]==1
            return (r[1],r[3],r[4],r[5],r[6],r[7],0,0)
        def feedback(text):
            until(lambda: os.pread(memory,64,symbols['rifle_hud_text']).split(b'\0')[0].decode()==text,3)
            until(lambda:text_visible(X,display,window,0,text,width=width,height=height,origin=(16,height-48)),3)
        if host is None:
            # One declared startup pose fixture; no HP/ammo/clock writes or renewal.
            os.kill(process.pid,signal.SIGSTOP)
            _,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
            try:os.pwrite(memory,struct.pack('<fff',2000.,17.8,3900.),player_address)
            finally:os.kill(process.pid,signal.SIGCONT)
        else:
            addresses={}
            for line in subprocess.check_output(['nm','-n',str(pathlib.Path(sys.argv[2]).resolve())],text=True).splitlines():
                r=line.split()
                if len(r)==3:addresses[r[2]]=int(r[0],16)
            host_memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
            os.kill(host.pid,signal.SIGSTOP);_,status=os.waitpid(host.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
            try:os.pwrite(host_memory,struct.pack('<fff',2000.,17.8,3900.),addresses['sim_players'])
            finally:os.kill(host.pid,signal.SIGCONT);os.close(host_memory)
            until(lambda:abs(player()['x']-2000.)<1,3)
        spawn=player();generation=spawn['generation'];trace=[]
        assert stock()[1]==90 and spawn['ammo']==30
        feedback('RIFLE 30/30 R90')
        for magazine in range(4):
            button(True);until(lambda:player()['ammo']==0,8);button(False);time.sleep(.12)
            p,s=player(),stock()
            assert p['generation']==generation and p['hp']>0 and s[3]==0
            assert p['ammo']+s[1]+s[2]==120
            trace.append([p['shots'],p['ammo'],s[1],s[2]])
            if magazine<3:
                feedback('RIFLE EMPTY R'+str(s[1])+' RELOAD')
                key(ord('r'),.06);until(lambda:player()['reload']>0,2)
                until(lambda:player()['ammo']==30 and player()['reload']==0,4)
                assert stock()[1]==90-(magazine+1)*30,(magazine,player(),stock(),trace,title(window))
                until(lambda:'R'+str(stock()[1]) in title(window),2)
            else:feedback('RIFLE EMPTY REARM DEPOT')
        assert player()['shots']==120 and stock()[1:4]==(0,120,0)
        before=player()['shots'];key(ord('r'),.06);button(True);time.sleep(.5);button(False)
        assert player()['shots']==before and player()['reload']==0
        feedback('RIFLE EMPTY REARM DEPOT')
        from PIL import Image
        image=X.XGetImage(display,window,0,0,width,height,W(-1).value,2);assert image
        try:
            pixels=[((v>>16)&255,(v>>8)&255,v&255)for y in range(height)for x in range(width)for v in [X.XGetPixel(image,x,y)]]
            output=Image.new('RGB',(width,height));output.putdata(pixels);output.save('/tmp/player-ammunition-'+('coop-' if host else 'solo-')+str(width)+'x'+str(height)+'.png')
        finally:X.XDestroyImage(image)
        key(0xff1b);stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
        print(json.dumps({'suite':'player-ammunition-real-coop-hud' if host else 'player-ammunition-real-solo-hud','passed':True,'units':8192,'scenario':'original-army-one-authority-player-pose-fixture','resolution':[width,height],'actual_same_body_shots':120,'stock_trace':trace,'actual_empty_fire_reload_blocked':True,'framebuffer_reserve_reload_empty_text':True,'initial_player_pose_fixture':[2000,17.8,3900],'live_pose_hp_stock_clock_renewal':False,'limits':['Software GL, no hardware/frame-budget or human readability acceptance.','One rendered client; exact server correlation and multi-client timeout are separate.']}))
finally:
    if host is not None and host.poll() is None:
        host.terminate();host.communicate(timeout=5)
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
