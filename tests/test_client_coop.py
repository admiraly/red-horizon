#!/usr/bin/env python3
"""Real two-render-client co-op on private Xvfb and a dedicated assembly server.
Development fixtures position an encounter on the authoritative server only.
"""
import ctypes as C
import ctypes.util
import json
import math
import os
import pathlib
import select
import signal
import struct
import subprocess
import sys
import tempfile
import time

CLIENT, SERVER = (pathlib.Path(arg).resolve() for arg in sys.argv[1:3])
D, W = C.c_void_p, C.c_ulong
X = C.CDLL(ctypes.util.find_library('X11')); XT = C.CDLL(ctypes.util.find_library('Xtst'))
X.XOpenDisplay.argtypes=[C.c_char_p]; X.XOpenDisplay.restype=D
X.XDefaultRootWindow.argtypes=[D]; X.XDefaultRootWindow.restype=W
X.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)]
X.XFetchName.argtypes=[D,W,C.POINTER(C.c_char_p)]
X.XFree.argtypes=[D]; X.XRaiseWindow.argtypes=[D,W]; X.XSetInputFocus.argtypes=[D,W,C.c_int,W]
X.XFlush.argtypes=[D]; X.XCloseDisplay.argtypes=[D]
X.XGetImage.argtypes=[D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int];X.XGetImage.restype=D
X.XGetPixel.argtypes=[D,C.c_int,C.c_int];X.XGetPixel.restype=W
X.XDestroyImage.argtypes=[D]
X.XKeysymToKeycode.argtypes=[D,W]; X.XKeysymToKeycode.restype=C.c_uint
XT.XTestFakeKeyEvent.argtypes=[D,C.c_uint,C.c_int,W]
XT.XTestFakeButtonEvent.argtypes=[D,C.c_uint,C.c_int,W]
XT.XTestFakeMotionEvent.argtypes=[D,C.c_int,C.c_int,C.c_int,W]
class ImageHeader(C.Structure):
    _fields_=[('width',C.c_int),('height',C.c_int),('xoffset',C.c_int),('format',C.c_int),('data',D),('byte_order',C.c_int),('bitmap_unit',C.c_int),('bitmap_bit_order',C.c_int),('bitmap_pad',C.c_int),('depth',C.c_int),('bytes_per_line',C.c_int),('bits_per_pixel',C.c_int)]
processes=[]; memories=[]; display=None; read_fd,write_fd=os.pipe(); host=None

def symbols(exe):
    result={}
    for line in subprocess.check_output(['nm','-n',str(exe)],text=True).splitlines():
        columns=line.split()
        if len(columns)==3:result[columns[2]]=int(columns[0],16)
    return result

def until(predicate,seconds=10):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=predicate()
        if result:return result
        assert all(p.poll() is None for p in processes),'a co-op process exited early'
        time.sleep(.02)
    raise AssertionError('co-op condition timed out')

try:
    with tempfile.TemporaryFile() as xlog:
        xvfb=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=xlog)
        processes.append(xvfb);os.close(write_fd);write_fd=None
        assert select.select([read_fd],[],[],10)[0]
        number=os.read(read_fd,32).decode().strip();assert number.isdigit(),number
        os.close(read_fd);read_fd=None
        env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
        display=X.XOpenDisplay(env['DISPLAY'].encode());assert display
        host=subprocess.Popen([str(SERVER),'--port','0','--ticks','0'],cwd=SERVER.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        processes.append(host);assert select.select([host.stdout],[],[],10)[0]
        ready=json.loads(host.stdout.readline());port=ready['port'];assert port>0,ready
        client_symbols=symbols(CLIENT);server_symbols=symbols(SERVER)
        host_memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR);memories.append(host_memory)
        clients=[]

        def title(win):
            name=C.c_char_p()
            if not X.XFetchName(display,win,C.byref(name)) or not name:return ''
            text=name.value.decode(errors='replace');X.XFree(C.cast(name,D));return text

        def window_for(index):
            root,parent,children,count=W(),W(),C.POINTER(W)(),C.c_uint()
            X.XQueryTree(display,X.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
            result=0
            for win in list(children[:count.value]):
                text=title(win)
                if f'CO-OP P{index} OWN FRONT {index}' in text and 'HP 100 ' in text:result=win;break
            if children:X.XFree(children)
            return result

        def read_u32(memory,sym,name,offset=0):return struct.unpack('<I',os.pread(memory,4,sym[name]+offset))[0]
        def record(memory,sym,index):
            values=struct.unpack('<5f11I',os.pread(memory,64,sym['sim_players']+index*64))
            return dict(zip(('x','y','z','yaw','pitch','hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation'),values))
        def server_player(index):return record(host_memory,server_symbols,index)
        def client_player(index,slot):return record(clients[index]['memory'],client_symbols,slot)
        def focus(index):
            win=clients[index]['window'];X.XRaiseWindow(display,win);X.XSetInputFocus(display,win,2,0);X.XFlush(display);time.sleep(.1)
        def key(index,symbol,hold=.10):
            focus(index);code=X.XKeysymToKeycode(display,symbol);assert code
            XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display);time.sleep(hold)
            XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display);time.sleep(.1)
        def button(down):XT.XTestFakeButtonEvent(display,1,int(down),0);X.XFlush(display)
        def click(index,px,py,before_press=None):
            focus(index);XT.XTestFakeMotionEvent(display,-1,px,py,0);X.XFlush(display);time.sleep(.12)
            if before_press:before_press()
            button(True);time.sleep(.12);button(False);time.sleep(.1)
        def goal(front):return struct.unpack('<ff',os.pread(host_memory,8,server_symbols['sim_waypoints']+front*8))

        for index in range(2):
            process=subprocess.Popen([str(CLIENT),'--connect','127.0.0.1','--port',str(port),'--tactical'],cwd=CLIENT.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            processes.append(process)
            memory=os.open(f'/proc/{process.pid}/mem',os.O_RDONLY);memories.append(memory)
            clients.append({'process':process,'memory':memory,'window':0})
            clients[index]['window']=until(lambda:window_for(index))
        until(lambda: all(client_player(c,p)['connected']==1 for c in range(2) for p in range(2)))
        starts=[server_player(i) for i in range(2)];assert starts[0]['front']==0 and starts[1]['front']==1,starts
        remote_pixel_counts=[]
        for index in range(2):
            focus(index);time.sleep(.15)
            remote=client_player(index,1-index)
            px=round(((remote['x']-4000)/4300+1)*640)
            py=round((1-(remote['z']-4000)/4300)*360)
            image=X.XGetImage(display,clients[index]['window'],0,0,1280,720,W(-1).value,2);assert image
            count=0
            for dx in range(-4,5):
                for dy in range(-4,5):
                    pixel=X.XGetPixel(image,px+dx,py+dy)
                    r,g,b=(pixel>>16)&255,(pixel>>8)&255,pixel&255
                    count+=r<100 and g>180 and b>160
            header=C.cast(image,C.POINTER(ImageHeader)).contents
            if header.bits_per_pixel==32 and header.byte_order==0:
                raw=C.string_at(header.data,header.bytes_per_line*header.height)
                raw=b''.join(raw[row*header.bytes_per_line:row*header.bytes_per_line+header.width*4] for row in range(header.height))
                rgb=bytearray(header.width*header.height*3)
                rgb[0::3]=raw[2::4];rgb[1::3]=raw[1::4];rgb[2::3]=raw[0::4]
                pathlib.Path(f'/tmp/red-horizon-v2-coop-player-{index}.ppm').write_bytes(f'P6\n{header.width} {header.height}\n255\n'.encode()+rgb)
            X.XDestroyImage(image);assert count>0,('remote player not visible on map',index,remote,px,py)
            remote_pixel_counts.append(count)
        # Both graphical clients receive separate real player records and scopes.
        assert all(read_u32(c['memory'],client_symbols,'net_player_id')==i for i,c in enumerate(clients))
        assert all(read_u32(c['memory'],client_symbols,'net_front')==i for i,c in enumerate(clients))
        for index in range(2):
            key(index,0xff09);before=server_player(index)
            key(index,ord('w'),.4);moved=until(lambda:server_player(index) if math.hypot(server_player(index)['x']-before['x'],server_player(index)['z']-before['z'])>.5 else None)
            until(lambda: abs(client_player(1-index,index)['z']-moved['z'])<.4)
            focus(index);button(True);time.sleep(.45);button(False)
            until(lambda:server_player(index)['shots']>0)
            until(lambda:client_player(1-index,index)['shots']==server_player(index)['shots'])
        # Installed recorded PCM is actually loaded and distant remote shots route
        # through the live spatial scene (these fronts are more than1500m apart).
        for c in clients:
            assert struct.unpack('<Q',os.pread(c['memory'],8,client_symbols['audio_submitted']))[0]>0
            assert struct.unpack('<Q',os.pread(c['memory'],8,client_symbols['audio_culled']))[0]>0
        # Real E/W/fire/Q from a graphical network client controls its server hull.
        os.kill(host.pid,signal.SIGSTOP)
        try:
            army=os.pread(host_memory,8192*32,server_symbols['sim_entities'])
            armor=next(i for i in range(4096) if struct.unpack_from('<I',army,i*32+8)[0]>0 and struct.unpack_from('<I',army,i*32+16)[0]==1)
            p=server_player(1)
            os.pwrite(host_memory,struct.pack('<2f',p['x']+2,p['z']),server_symbols['sim_entities']+armor*32)
        finally:os.kill(host.pid,signal.SIGCONT)
        def vehicle_owner(memory,symbols,index):return struct.unpack('<i',os.pread(memory,4,symbols['sim_player_vehicle']+index*4))[0]
        key(1,ord('e'),.25)
        until(lambda:vehicle_owner(host_memory,server_symbols,1)==armor,3)
        until(lambda:vehicle_owner(clients[1]['memory'],client_symbols,1)==armor,2)
        before=server_player(1);key(1,ord('w'),.35)
        until(lambda:server_player(1)['z']>before['z']+1,2)
        rifle_before=server_player(1)['shots']
        cannon_before=read_u32(host_memory,server_symbols,'vehicle_shots',4)
        focus(1);button(True)
        try:until(lambda:read_u32(host_memory,server_symbols,'vehicle_shots',4)>cannon_before,3)
        finally:button(False)
        assert server_player(1)['shots']==rifle_before,'network cannon consumed rifle counter'
        until(lambda:'ARMOR #' in title(clients[1]['window']),2)
        key(1,ord('q'),.25)
        until(lambda:vehicle_owner(host_memory,server_symbols,1)==-1,3)
        until(lambda:vehicle_owner(clients[1]['memory'],client_symbols,1)==-1,2)
        # Pausing our own host proves graphical clients cannot tick the world.
        os.kill(host.pid,signal.SIGSTOP);time.sleep(.25)
        paused_ticks=[read_u32(c['memory'],client_symbols,'sim_tick_count') for c in clients]
        paused_records=[client_player(i,i) for i in range(2)]
        key(0,ord('w'),.35);time.sleep(.1)
        assert paused_ticks==[read_u32(c['memory'],client_symbols,'sim_tick_count') for c in clients]
        assert paused_records==[client_player(i,i) for i in range(2)]
        assert all(read_u32(c['memory'],client_symbols,'local_sim_ticks')==0 for c in clients)
        os.kill(host.pid,signal.SIGCONT);time.sleep(.25)
        # First advance targets this front's next hostile site, not the human.
        site=client_symbols['sim_sites']+6*32
        owner=struct.unpack('<I',os.pread(clients[1]['memory'],4,site+8))[0]
        if owner!=1:site+=32
        expected_advance=struct.unpack('<ff',os.pread(clients[1]['memory'],8,site))
        key(1,ord('1'))
        until(lambda:read_u32(clients[1]['memory'],client_symbols,'waypoint_orders')==1)
        assert goal(1)==expected_advance,(goal(1),expected_advance)
        # Order ownership denial stays local/readable; accepted order reaches the
        # actual server once, including exactly5 spending after accounting income.
        key(0,0xff09);key(0,0xffc0) # map, F3 selects front2 (not owned)
        forbidden=goal(2);click(0,788,368)
        until(lambda:'ORDER DENIED: SELECT YOUR OWN FRONT' in title(clients[0]['window']))
        assert goal(2)==forbidden
        key(0,0xffbe) # F1 is its assigned front
        tick_before=read_u32(host_memory,server_symbols,'sim_tick_count')
        req_before=read_u32(host_memory,server_symbols,'sim_requisition')
        click(0,788,368)
        until(lambda:abs(goal(0)[0]-4994.375)<.01 and abs(goal(0)[1]-3904.44444)<.01)
        tick_after=read_u32(host_memory,server_symbols,'sim_tick_count')
        req_after=read_u32(host_memory,server_symbols,'sim_requisition')
        income=39*((tick_after//30)-(tick_before//30))
        assert req_after==req_before+income-5,(req_before,req_after,tick_before,tick_after)
        until(lambda:read_u32(clients[0]['memory'],client_symbols,'waypoint_orders')==1)
        # A real rejected ACK must never invent a new goal or accepted-order UI.
        accepted_goal=goal(0)
        display_goal=struct.unpack('<ff',os.pread(clients[0]['memory'],8,client_symbols['net_goal']))
        saved_req=[]
        def empty_funds():
            until(lambda:4<=read_u32(host_memory,server_symbols,'sim_tick_count')%30<=9,2)
            saved_req.append(read_u32(host_memory,server_symbols,'sim_requisition'))
            os.pwrite(host_memory,struct.pack('<I',0),server_symbols['sim_requisition'])
        click(0,938,343,empty_funds)
        until(lambda:'SERVER REJECTED REQUEST' in title(clients[0]['window']),2)
        assert goal(0)==accepted_goal
        assert read_u32(clients[0]['memory'],client_symbols,'waypoint_orders')==1
        assert struct.unpack('<ff',os.pread(clients[0]['memory'],8,client_symbols['net_goal']))==display_goal
        os.pwrite(host_memory,struct.pack('<I',saved_req[0]),server_symbols['sim_requisition'])
        # Actual server enemy attack drives death, replicated to both clients.
        player_address=server_symbols['sim_players']
        os.pwrite(host_memory,struct.pack('<fff',2000.,17.8,3900.),player_address)
        os.pwrite(host_memory,struct.pack('<ff6I',2040.,3900.,400,1,1,0,0xffffffff,1),server_symbols['sim_entities']+4096*32)
        os.pwrite(host_memory,struct.pack('<I',1),server_symbols['orders']+3*4)
        os.pwrite(host_memory,struct.pack('<I',1),server_symbols['ai_fronts']+3*64+24) # documented manual front
        until(lambda:server_player(0)['hp']<100,3)
        until(lambda:server_player(0)['hp']==0,9)
        dead=server_player(0)
        until(lambda:all(client_player(i,0)['hp']==0 for i in range(2)),1)
        until(lambda:'DOWN: SAFE REDEPLOY' in title(clients[0]['window']),1)
        until(lambda:server_player(0)['hp']==100 and server_player(0)['generation']>dead['generation'],4)
        recovered=server_player(0)
        until(lambda:all(client_player(i,0)['generation']==recovered['generation'] for i in range(2)),2)
        final=[server_player(i) for i in range(2)]
        outputs=[]
        for index in range(2):
            key(index,0xff1b);stdout,stderr=clients[index]['process'].communicate(timeout=5)
            assert clients[index]['process'].returncode==0,(stdout,stderr)
            assert 'local_sim_ticks=0' in stdout and f'player={index} front={index}' in stdout,stdout
            outputs.append(stdout)
        print(json.dumps({'suite':'graphical-coop','passed':True,'port':port,'starts':starts,'remote_player_pixels':remote_pixel_counts,'final':final,'cost':5,'rejected_ack_preserved_goal':True,'network_gui_board_drive_cannon_exit':True,'recorded_spatial_audio_live_routing':True,'owned_goal':goal(0),'dead':dead,'recovered':recovered,'client_stdout':outputs}))
finally:
    if host is not None and host.poll() is None:
        try:os.kill(host.pid,signal.SIGCONT)
        except ProcessLookupError:pass
    for memory in memories:os.close(memory)
    if display:X.XCloseDisplay(display);display=None
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
    if read_fd is not None:os.close(read_fd)
    if write_fd is not None:os.close(write_fd)
