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
import re
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
        display=until(lambda:X.XOpenDisplay(env['DISPLAY'].encode()),5)
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
        def goal(front):
            # Network orders now target the owner's exclusive company, including
            # after a genuine redeployment, rather than mutating a global front.
            if front in (0,1):
                company=read_u32(host_memory,server_symbols,'player_companies',front*16)
                assert company<1536,('missing company assignment',front,company)
                return struct.unpack('<ff',os.pread(host_memory,8,server_symbols['company_controls']+company*32+16))
            return struct.unpack('<ff',os.pread(host_memory,8,server_symbols['sim_waypoints']+front*8))

        for index in range(2):
            process=subprocess.Popen([str(CLIENT),'--connect','127.0.0.1','--port',str(port),'--tactical'],cwd=CLIENT.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            processes.append(process)
            memory=os.open(f'/proc/{process.pid}/mem',os.O_RDWR);memories.append(memory)
            clients.append({'process':process,'memory':memory,'window':0})
            clients[index]['window']=until(lambda:window_for(index))
        until(lambda: all(client_player(c,p)['connected']==1 for c in range(2) for p in range(2)))
        def remote_company(client,player):
            return struct.unpack('<6I2f2I',os.pread(clients[client]['memory'],40,client_symbols['net_company_records']+player*40))
        until(lambda:all(remote_company(c,p)[1]<768 and remote_company(c,p)[2]==client_player(c,p)['generation'] for c in range(2)for p in range(2)))
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
        # Ownership is visible through actual rendered map pixels on both clients.
        def owned_members_arrived():
            for c in range(2):
                company=remote_company(c,c)[1]
                data=os.pread(clients[c]['memory'],128*32,client_symbols['sim_entities']+(company%256)*128*32)
                rows=[struct.unpack_from('<2f6I',data,i*32)for i in range(128)]
                if not any(r[2] and r[3]==0 and r[4]<3 and r[5]==company//256 for r in rows):return False
            return True
        until(owned_members_arrived,5)
        company_pixels=[]
        for index in range(2):
            focus(index);time.sleep(.15)
            company=remote_company(index,index)[1]
            assert f'COMPANY {company}' in title(clients[index]['window'])
            entity_data=os.pread(clients[index]['memory'],32768*32,client_symbols['sim_entities'])
            rows=[struct.unpack_from('<2f6I',entity_data,i*32)for i in range(32768)]
            owned=[r for i,r in enumerate(rows)if r[2] and r[3]==0 and r[4]<3 and r[5]*256+(i>>7)==company]
            foreign=[r for i,r in enumerate(rows)if r[2] and r[3]==0 and r[4]<3 and r[5]*256+(i>>7)!=company]
            image=X.XGetImage(display,clients[index]['window'],0,0,1280,720,W(-1).value,2);assert image
            def pixels(row,green):
                px=round(((row[0]-4000)/4300+1)*640);py=round((1-(row[1]-4000)/4300)*360)
                if not(5<=px<1275 and 5<=py<715):return 0
                count=0
                for dx in range(-3,4):
                    for dy in range(-3,4):
                        pixel=X.XGetPixel(image,px+dx,py+dy);r,g,b=(pixel>>16)&255,(pixel>>8)&255,pixel&255
                        count+=(80<r<160 and g>200 and 40<b<120)if green else(r<85 and 110<g<180 and b>170)
                return count
            green=max([pixels(r,True)for r in owned],default=0)
            blue=max([pixels(r,False)for r in foreign],default=0)
            X.XDestroyImage(image);assert green>0 and blue>0,(index,company,green,blue,len(owned),read_u32(clients[index]['memory'],client_symbols,'view_company'),read_u32(clients[index]['memory'],client_symbols,'view_player'),remote_company(index,index),client_player(index,index))
            company_pixels.append({'player':index,'company':company,'owned_green_pixels':green,'foreign_allied_blue_pixels':blue})
        if '--timeout' in sys.argv:
            host.terminate();host.communicate(timeout=5)
            # until normally audits every live child: remove our retired host.
            processes.remove(host)
            until(lambda:all(read_u32(c['memory'],client_symbols,'net_connected')==0 for c in clients),5)
            until(lambda:all(read_u32(c['memory'],client_symbols,'view_company')==0xffffffff for c in clients),2)
            assert all(read_u32(c['memory'],client_symbols,'net_company_valid')==0 and read_u32(c['memory'],client_symbols,'local_sim_ticks')==0 for c in clients)
            for index in (1,0):
                key(index,0xff1b);stdout,stderr=clients[index]['process'].communicate(timeout=5)
                assert clients[index]['process'].returncode==0,(stdout,stderr)
            print(json.dumps({'suite':'graphical-company-timeout','passed':True,'company_marker_pixels_before_timeout':company_pixels,'both_remote_leases_hidden':True,'remote_validity_reset':True,'no_solo_lease_fallback':True,'local_simulation_ticks':0}))
            raise SystemExit(0)
        # Both graphical clients receive separate real player records and scopes.
        assert all(read_u32(c['memory'],client_symbols,'net_player_id')==i for i,c in enumerate(clients))
        assert all(read_u32(c['memory'],client_symbols,'net_front')==i for i,c in enumerate(clients))
        for index in range(2):
            key(index,0xff09);before=server_player(index)
            key(index,ord('w'),.8);moved=until(lambda:server_player(index) if math.hypot(server_player(index)['x']-before['x'],server_player(index)['z']-before['z'])>.5 else None)
            until(lambda: abs(client_player(1-index,index)['z']-moved['z'])<.4)
            focus(index);button(True);time.sleep(.45);button(False)
            until(lambda:server_player(index)['shots']>0)
            until(lambda:client_player(1-index,index)['shots']==server_player(index)['shots'])
        # Installed recorded PCM is actually loaded and distant remote shots route
        # through the live spatial scene (these fronts are more than1500m apart).
        for c in clients:
            assert struct.unpack('<Q',os.pread(c['memory'],8,client_symbols['audio_submitted']))[0]>0
            assert struct.unpack('<Q',os.pread(c['memory'],8,client_symbols['audio_culled']))[0]>0
            assert struct.unpack('<Q',os.pread(c['memory'],8,client_symbols['audio_footsteps_emitted']))[0]>0,'actual network walking did not route recorded footsteps'
        # Actual Ctrl/Space input traverses UDP to authority and back to the GUI.
        def ground_eye(p):
            qx,qz=p['x']-4000,p['z']-4000
            return 12+qx*qx*.000001+qz*qz*.0000005+max(0,1-abs(qx)/800)*18+1.8
        focus(0);code=X.XKeysymToKeycode(display,0xffe3)
        XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display)
        try:
            crouched=until(lambda:server_player(0) if server_player(0)['y']<ground_eye(server_player(0))-.6 else None,2)
            until(lambda:abs(client_player(0,0)['y']-crouched['y'])<.02,2)
            until(lambda:abs(struct.unpack('<f',os.pread(clients[0]['memory'],4,client_symbols['camera']+4))[0]-crouched['y'])<.1,2)
        finally:XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display)
        until(lambda:abs(server_player(0)['y']-ground_eye(server_player(0)))<.01,2)
        code=X.XKeysymToKeycode(display,0x20)
        XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display)
        try:
            airborne=until(lambda:server_player(0) if server_player(0)['y']>ground_eye(server_player(0))+.5 else None,2)
            until(lambda:client_player(0,0)['y']>ground_eye(client_player(0,0))+.2,2)
            until(lambda:struct.unpack('<f',os.pread(clients[0]['memory'],4,client_symbols['camera']+4))[0]>ground_eye(client_player(0,0))+.1,2)
            until(lambda:abs(server_player(0)['y']-ground_eye(server_player(0)))<.01,3)
            landed_tick=read_u32(host_memory,server_symbols,'sim_tick_count')
            until(lambda:read_u32(host_memory,server_symbols,'sim_tick_count')>=landed_tick+15,2)
            assert abs(server_player(0)['y']-ground_eye(server_player(0)))<.01,('held GUI jump relaunched',server_player(0),landed_tick,read_u32(host_memory,server_symbols,'sim_tick_count'))
        finally:XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display)
        # Real E/W/fire/Q from a graphical network client controls its server hull.
        os.kill(host.pid,signal.SIGSTOP)
        try:
            army=os.pread(host_memory,8192*32,server_symbols['sim_entities'])
            armor=next(i for i in range(4096) if struct.unpack_from('<I',army,i*32+8)[0]>0 and struct.unpack_from('<I',army,i*32+16)[0]==1)
            # Stage the boarding encounter in open mid-field before firing.
            # A round hidden behind unrelated friendly hulls is valid geometry,
            # but cannot establish a visible replicated-projectile footprint.
            # Keep all8192 actors and every HP/ammo/generation/pool field intact.
            p=server_player(1);p.update(x=3500.,z=2000.)
            p['y']=ground_eye(p)
            os.pwrite(host_memory,struct.pack('<3f',p['x'],p['y'],p['z']),server_symbols['sim_players']+64)
            os.pwrite(host_memory,struct.pack('<2f',p['x']+2,p['z']),server_symbols['sim_entities']+armor*32)
        finally:os.kill(host.pid,signal.SIGCONT)
        def vehicle_owner(memory,symbols,index):return struct.unpack('<i',os.pread(memory,4,symbols['sim_player_vehicle']+index*4))[0]
        key(1,ord('e'),.25)
        until(lambda:vehicle_owner(host_memory,server_symbols,1)==armor,3)
        until(lambda:vehicle_owner(clients[1]['memory'],client_symbols,1)==armor,2)
        # Keep real network steering held during bounded hull pivot/acceleration.
        # Retain the original >1m authoritative forward progress and2s budget.
        before=server_player(1);focus(1)
        code=X.XKeysymToKeycode(display,ord('w'))
        XT.XTestFakeKeyEvent(display,code,1,0);X.XFlush(display)
        try:
            until(lambda:server_player(1)['z']>before['z']+1,2)
        finally:
            XT.XTestFakeKeyEvent(display,code,0,0);X.XFlush(display)
        rifle_before=server_player(1)['shots']
        cannon_before=read_u32(host_memory,server_symbols,'vehicle_shots',4)
        focus(1);button(True)
        try:until(lambda:read_u32(host_memory,server_symbols,'vehicle_shots',4)>cannon_before,3)
        finally:button(False)
        # Authentic moving cannon sample reaches the real graphical client.
        cm=clients[1]['memory'];cp=clients[1]['process']
        def live_cannon():
            data=os.pread(cm,32768,client_symbols['net_projectiles'])
            for offset in range(0,32768,64):
                v=struct.unpack_from('<6f4If5I',data,offset)
                if v[13] and v[8]==1 and v[11]==armor:return v
        # Press again if the first short shot passed between the 10Hz snapshots.
        focus(1);button(True)
        try:
            try:until(live_cannon,4)
            except AssertionError:
                rounds=[struct.unpack_from('<6f4If5I',os.pread(host_memory,32768,server_symbols['sim_projectiles']),i*64) for i in range(512)]
                wreck_bytes=os.pread(host_memory,65536,server_symbols['sim_wrecks'])
                nearby=[struct.unpack_from('<6f10I',wreck_bytes,i*64) for i in range(1024) if struct.unpack_from('<I',wreck_bytes,i*64+52)[0]&1 and abs(struct.unpack_from('<f',wreck_bytes,i*64)[0]-server_player(1)['x'])<100 and abs(struct.unpack_from('<f',wreck_bytes,i*64+8)[0]-server_player(1)['z'])<100]
                print('CANNON_TIMEOUT_DIAGNOSTIC',json.dumps({'player':server_player(1),'armor':armor,'ammo':read_u32(host_memory,server_symbols,'sim_shell_ammo',armor*4),'cannon_shots':read_u32(host_memory,server_symbols,'vehicle_shots',4),'host_owned_rounds':[v for v in rounds if v[13] and v[11]==armor],'nearby_wrecks':nearby,'client_pitch_yaw':[struct.unpack('<f',os.pread(cm,4,client_symbols[n]))[0] for n in ('pitch','yaw')]}),flush=True)
                raise
        finally:button(False)
        os.kill(host.pid,signal.SIGSTOP)
        _,status=os.waitpid(host.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
        try:
            os.pwrite(cm,struct.pack('<I',1),client_symbols['net_projectiles_clock_frozen'])
            start=read_u32(cm,client_symbols,'frame_count')
            until(lambda:read_u32(cm,client_symbols,'frame_count')>=start+4,2)
            sample=live_cannon();assert sample,'received cannon trajectory expired before capture'
            # The owned cannon's on-axis round can be wholly covered by the HUD
            # crosshair. Turn only the cosmetic observer view while authority is
            # paused; keep the received round/eye/health/ammo/pool unchanged.
            observer_yaw=os.pread(cm,4,client_symbols['yaw'])
            os.pwrite(cm,struct.pack('<f',struct.unpack('<f',observer_yaw)[0]+.06),client_symbols['yaw'])
            start=read_u32(cm,client_symbols,'frame_count')
            until(lambda:read_u32(cm,client_symbols,'frame_count')>=start+4,2)
            until(lambda:struct.unpack('<f',os.pread(cm,4,client_symbols['recoil']))[0]==0,2)
            authority_keys=(('sim_entities',8192*32),('sim_aircraft',8192*64),('sim_projectiles',32768),('sim_players',256))
            authority_before=tuple(os.pread(cm,n,client_symbols[name])for name,n in authority_keys)
            def framebuffer(label):
                image=X.XGetImage(display,clients[1]['window'],0,0,1280,720,W(-1).value,2);assert image
                header=C.cast(image,C.POINTER(ImageHeader)).contents
                assert header.bits_per_pixel==32 and header.byte_order==0
                raw=C.string_at(header.data,header.bytes_per_line*header.height)
                raw=b''.join(raw[row*header.bytes_per_line:row*header.bytes_per_line+header.width*4]for row in range(header.height))
                rgb=bytearray(header.width*header.height*3)
                rgb[0::3]=raw[2::4];rgb[1::3]=raw[1::4];rgb[2::3]=raw[0::4]
                X.XDestroyImage(image)
                path=pathlib.Path('/tmp/red-horizon-network-projectile-'+label+'.ppm')
                path.write_bytes(b'P6\n1280 720\n255\n'+rgb)
                return rgb,str(path)
            visible,network_shell_path=framebuffer('visible')
            os.pwrite(cm,struct.pack('<I',0),client_symbols['net_projectiles_visible'])
            start=read_u32(cm,client_symbols,'frame_count')
            until(lambda:read_u32(cm,client_symbols,'frame_count')>=start+4,2)
            hidden,_=framebuffer('hidden-control')
            # At this real muzzle distance a shell can cover only a few pixels.
            # Require the same gold footprint on both sides of the hidden control:
            # unrelated aging flashes cannot establish restored shell visibility.
            os.pwrite(cm,struct.pack('<I',1),client_symbols['net_projectiles_visible'])
            start=read_u32(cm,client_symbols,'frame_count')
            until(lambda:read_u32(cm,client_symbols,'frame_count')>=start+4,2)
            restored,_=framebuffer('restored')
            # Project the received authority sample using the actual camera;
            # only repeated pixels within its small footprint qualify.
            camera=struct.unpack('<3f',os.pread(cm,12,client_symbols['camera']))
            yaw=struct.unpack('<f',os.pread(cm,4,client_symbols['yaw']))[0]
            pitch=struct.unpack('<f',os.pread(cm,4,client_symbols['pitch']))[0]+struct.unpack('<f',os.pread(cm,4,client_symbols['recoil']))[0]
            projection=struct.unpack('<2f',os.pread(cm,8,client_symbols['view_projection']))
            dx,dy,dz=(sample[i]-camera[i] for i in range(3))
            qx=math.cos(yaw)*dx-math.sin(yaw)*dz
            qz=math.sin(yaw)*dx+math.cos(yaw)*dz
            qy=math.cos(pitch)*dy-math.sin(pitch)*qz
            depth=math.sin(pitch)*dy+math.cos(pitch)*qz
            assert depth>4,'received shell is behind the observer'
            px=round(640*(1+qx*projection[0]/depth));py=round(360*(1-qy*projection[1]/depth))
            changed_shell_pixels=sum(all(frame[i]>175 and frame[i+1]>85 and frame[i+2]<100 and
                 max(abs(frame[i+c]-hidden[i+c])for c in range(3))>10 for frame in (visible,restored))
                 for y in range(max(0,py-12),min(720,py+13))for x in range(max(0,px-12),min(1280,px+13))for i in [(y*1280+x)*3])
            assert changed_shell_pixels>0,('no repeatable pixels at the real replicated shell position',changed_shell_pixels,sample,(px,py))
            assert authority_before==tuple(os.pread(cm,n,client_symbols[name])for name,n in authority_keys),'projectile cosmetic draw controls changed authority'
        finally:
            if 'observer_yaw' in locals():os.pwrite(cm,observer_yaw,client_symbols['yaw'])
            os.pwrite(cm,struct.pack('<I',1),client_symbols['net_projectiles_visible'])
            os.pwrite(cm,struct.pack('<I',0),client_symbols['net_projectiles_clock_frozen'])
            os.kill(host.pid,signal.SIGCONT)
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
        assert goal(0)==accepted_goal,'redeployment discarded company intent'
        final_owned_goal=goal(0)
        until(lambda:all(remote_company(c,0)[2]==recovered['generation'] and remote_company(c,0)[6:8]==accepted_goal for c in range(2)))
        # Second client inspects the first owner's front, without issuing an order.
        if 'TACTICAL' not in title(clients[1]['window']):key(1,0xff09)
        key(1,0xffbe)
        until(lambda:read_u32(clients[1]['memory'],client_symbols,'frame_count')>0)
        time.sleep(.12)
        image=X.XGetImage(display,clients[1]['window'],0,0,1280,720,W(-1).value,2);assert image
        gx=round(((accepted_goal[0]-4000)/4300+1)*640);gy=round((1-(accepted_goal[1]-4000)/4300)*360)
        shared_goal_pixels=0
        for dx in range(-11,12):
            for dy in range(-11,12):
                pixel=X.XGetPixel(image,gx+dx,gy+dy);r,g,b=(pixel>>16)&255,(pixel>>8)&255,pixel&255
                shared_goal_pixels+=160<r<175 and g>245 and 105<b<125
        X.XDestroyImage(image);assert shared_goal_pixels>0,('other owner goal cross not rendered',accepted_goal,gx,gy)
        final=[server_player(i) for i in range(2)]
        outputs=[]
        for index in (1,0):
            key(index,0xff1b);stdout,stderr=clients[index]['process'].communicate(timeout=5)
            assert clients[index]['process'].returncode==0,(stdout,stderr)
            assert 'local_sim_ticks=0' in stdout and f'player={index} front={index}' in stdout,stdout
            observed=re.search(r'selected_goal_x=([-0-9.]+) selected_goal_z=([-0-9.]+)',stdout)
            assert observed and all(abs(float(v)-expected)<.01 for v,expected in zip(observed.groups(),accepted_goal)),stdout
            outputs.append(stdout)
        print(json.dumps({'suite':'graphical-coop','passed':True,'port':port,'starts':starts,'remote_player_pixels':remote_pixel_counts,'company_marker_pixels':company_pixels,'other_owner_goal_displayed_without_local_order':True,'shared_goal_cross_pixels':shared_goal_pixels,'remote_company_generation_after_redeploy':True,'final':final,'cost':5,'rejected_ack_preserved_goal':True,'network_gui_board_drive_cannon_exit':True,'network_gui_crouch_jump':True,'network_camera_crouch_jump':True,'recorded_spatial_audio_live_routing':True,'recorded_footsteps_live_routing':True,'replicated_shell_changed_pixels':changed_shell_pixels,'replicated_shell_screen_position':[px,py],'replicated_shell_restored':True,'owned_shell_observer_yaw_shift_rad':.06,'owned_shell_actual_projection':projection,'owned_shell_recoil_settled':True,'replicated_shell_authority_unchanged':True,'replicated_shell_screenshot':network_shell_path,'owned_goal':final_owned_goal,'redeployment_preserved_company_intent':True,'dead':dead,'recovered':recovered,'client_stdout':outputs}))
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
