#!/usr/bin/env python3
"""Development-only XTest input against the actual client on its private display."""
import ctypes as C,ctypes.util,json,os,pathlib,re,subprocess,sys,time
exe=pathlib.Path(sys.argv[1]).resolve()
x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong
x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_char_p)]
x.XFree.argtypes=[C.c_void_p]
x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
x.XRaiseWindow.argtypes=[C.c_void_p,C.c_ulong]
x.XFlush.argtypes=[C.c_void_p]
x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_ubyte
x.XCloseDisplay.argtypes=[C.c_void_p]
xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong]
display=x.XOpenDisplay(None);assert display,'private display unavailable'
process=subprocess.Popen([str(exe),'--tactical'],cwd=exe.parent,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
window=0
try:
    def title(win):
        name=C.c_char_p()
        if not x.XFetchName(display,win,C.byref(name)) or not name:return ''
        result=name.value.decode(errors='replace');x.XFree(C.cast(name,C.c_void_p));return result
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        root=C.c_ulong();parent=C.c_ulong();children=C.POINTER(C.c_ulong)();count=C.c_uint()
        x.XQueryTree(display,x.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
        for win in list(children[:count.value]):
            if 'RED HORIZON' in title(win) and 'rifle 30/30' in title(win):window=win;break
        if children:x.XFree(children)
        if window:break
        assert process.poll() is None,'client exited before mapping'
        time.sleep(.05)
    assert window,'client window did not map'
    x.XRaiseWindow(display,window);x.XSetInputFocus(display,window,2,0);x.XFlush(display);time.sleep(.2)
    first_title=title(window)
    def key(symbol,hold=.12):
        code=x.XKeysymToKeycode(display,symbol);assert code
        xt.XTestFakeKeyEvent(display,code,1,0);x.XFlush(display);time.sleep(hold)
        xt.XTestFakeKeyEvent(display,code,0,0);x.XFlush(display);time.sleep(.12)
    def button(down):xt.XTestFakeButtonEvent(display,1,int(down),0);x.XFlush(display)
    def click(px,py):
        xt.XTestFakeMotionEvent(display,-1,px,py,0);x.XFlush(display);time.sleep(.12)
        button(True);time.sleep(.12);button(False);time.sleep(.12)
    def until(predicate,seconds=8):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            current=title(window)
            if predicate(current):return current
            assert process.poll() is None,'client exited during input test'
            time.sleep(.05)
        raise AssertionError('input state timed out: '+title(window))
    key(0xff09);key(0xff09) # FPS then back to map
    key(0xffbf) # F2 -> front1
    click(788,368);click(0,0) # valid waypoint, then outside world
    key(0xff09) # return to FPS
    key(ord('w'),.25)
    button(True);until(lambda t:'rifle 0/30' in t);button(False)
    key(ord('r'));until(lambda t:'RELOADING' in t,2)
    button(True);time.sleep(.35)
    assert 'rifle 0/30 RELOADING' in title(window),'reload failed to block fire'
    button(False);until(lambda t:'rifle 30/30' in t and 'RELOADING' not in t,4)
    button(True);time.sleep(.35);button(False);time.sleep(.1)
    last_title=title(window);key(0xff1b) # Escape
    stdout,stderr=process.communicate(timeout=5);assert process.returncode==0,(stdout,stderr)
    shots=int(re.search(r'shots=(\d+)',stdout).group(1))
    ammo,reloads,front=map(int,re.search(r'weapon ammo=(\d+) reloads=(\d+) front=(\d+)',stdout).groups())
    assert 1<=ammo<=29 and shots==60-ammo and reloads==1 and front==1,(stdout,stderr)
    orders=int(re.search(r'waypoint_orders=(\d+)',stdout).group(1));assert orders==1,stdout
    goal=re.search(r'selected_goal_x=([\d.]+) selected_goal_z=([\d.]+)',stdout);assert goal,stdout
    gx,gz=map(float,goal.groups());assert abs(gx-4994.375)<.02 and abs(gz-3904.444)<.02,(gx,gz)
    camera=re.search(r'camera_x=([\d.]+) camera_z=([\d.]+)',stdout)
    cx,cz=map(float,camera.groups())
    start=re.search(r'start_player_x=([\d.]+) start_player_z=([\d.]+)',stdout);assert start,stdout
    sx,sz=map(float,start.groups())
    assert abs(cx-sx)+abs(cz-sz)>.2,'W movement did not contribute'
    print(json.dumps({'suite':'controls','passed':True,'shots':shots,'ammo':ammo,'reloads':reloads,'front':front,'waypoint_orders':orders,'goal':[gx,gz],'first_title':first_title,'last_title':last_title}))
finally:
    if process.poll() is None:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    x.XCloseDisplay(display)
