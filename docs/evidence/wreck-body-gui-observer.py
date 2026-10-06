#!/usr/bin/env python3
"""Private software-GL/UDP foot preview at a genuinely reached wreck contact.
Uses the existing client harness setup/cleanup without modifying game runtime.
Transport snapshots are frozen; synthetic server ticks provide packet freshness.
This is a client preview/read-only rendering fixture, not natural server play.
"""
import pathlib,sys
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tests'))
original=(root/'tests/test_wreck_client.py').read_text();prefix=original.split('  rows=[];sequence=0;clock=0')[0]
prefix=prefix.replace('ROOT=pathlib.Path(__file__).resolve().parents[1]', 'ROOT=pathlib.Path('+repr(str(root))+')')
body=r'''
  import threading
  world.sim_init.argtypes=[C.c_uint,C.c_uint];world.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
  world.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;world.terrain_height.argtypes=[C.c_float,C.c_float];world.terrain_height.restype=C.c_float;world.sim_checksum.restype=C.c_uint64
  assert world.sim_init(32,42)==0
  entities=(C.c_ubyte*1048576).in_dll(world,'sim_entities');players=(C.c_ubyte*256).in_dll(world,'sim_players');sites=(C.c_ubyte*384).in_dll(world,'sim_sites');vehicles=(C.c_ubyte*128).in_dll(world,'sim_vehicles');claims=(C.c_ubyte*16).in_dll(world,'sim_player_vehicle');wrecks=(C.c_ubyte*65536).in_dll(world,'sim_wrecks')
  for i in range(32):C.c_uint.from_buffer(entities,i*32+8).value=0
  C.memmove(C.addressof(entities)+12*32,struct.pack('<2f6I',3480,2000,100,0,0,0,0xffffffff,111),32)
  C.memmove(C.addressof(entities)+13*32,struct.pack('<2f6I',3500,2000,1,1,1,1,0xffffffff,112),32)
  alive=(C.c_uint*2).in_dll(world,'sim_alive');alive[0]=alive[1]=1
  for side in (0,1):
   for front in range(3):assert world.sim_order(side,front,1)==0
   assert world.sim_waypoint(side,0,3600,2000)==0;assert world.sim_waypoint(side,1,3600,2000)==0
  world.ground_init();world.sim_air_damage(13,1);assert world.player_join(0,0)==0
  C.c_float.from_buffer(players,0).value=3480;C.c_float.from_buffer(players,8).value=2000;C.c_float.from_buffer(players,4).value=world.terrain_height(3480,2000)+1.8
  assert world.player_input(0,0,1,0,math.pi/2,0)==0
  for _ in range(150):world.sim_tick()
  base=struct.unpack_from('<3f',players);record=bytes(wrecks[:64]);fixture_hash=world.sim_checksum()
  assert base[0]>3490 and base[0]<3500 and C.c_uint.in_dll(world,'sim_wreck_count').value==1
  payload=struct.pack('<6I',32,0,100,100,100,100)+bytes(players)+bytes(sites)+bytes(vehicles)+bytes(claims);assert len(payload)==808
  entity_payload=struct.pack('<I',32)+b''.join(struct.pack('<I',i)+bytes(entities[i*32:(i+1)*32]) for i in range(32))
  put('yaw',struct.pack('<f',math.pi/2));put('pitch',struct.pack('<f',0));put('tactical',struct.pack('<I',0))
  done=threading.Event();wire_clock=[150]
  def heartbeat():
   while not done.wait(.025):
    wire_clock[0]+=1;send(payload,wire_clock[0],100);send(entity_payload,wire_clock[0],101)
  thread=threading.Thread(target=heartbeat);thread.start()
  XT=C.CDLL(ctypes.util.find_library('Xtst'));XT.XTestFakeKeyEvent.argtypes=[D,C.c_uint,C.c_int,W]
  X.XSetInputFocus.argtypes=[D,W,C.c_int,W];X.XFlush.argtypes=[D];X.XStringToKeysym.argtypes=[C.c_char_p];X.XStringToKeysym.restype=W;X.XKeysymToKeycode.argtypes=[D,W];X.XKeysymToKeycode.restype=C.c_ubyte
  key=X.XKeysymToKeycode(display,X.XStringToKeysym(b'w'));assert key
  X.XSetInputFocus(display,window,1,0);XT.XTestFakeKeyEvent(display,key,1,0);X.XFlush(display)
  def authority():return get('sim_players',256)+get('sim_entities',1048576)+get('sim_sites',384)+get('sim_vehicles',128)+get('sim_projectiles',32768)
  rows=[]
  try:
   pixels,path,_=capture('body-empty-cache')
   assert get('sim_players',256)==bytes(players)
   reference=authority();empty=struct.unpack('<3f',get('visual_target',12));wish=struct.unpack('<2f',get('wish_x',8))
   assert wish[0]>.99 and abs(wish[1])<.01,(wish,empty)
   assert empty[0]>base[0]+.1,(base,empty,'empty remote cache did not preview')
   rows.append({'phase':'empty','base':base,'target':empty,'screenshot':path})
   send(struct.pack('<I',0)+record,wire_clock[0]);pixels,path,_=capture('body-admitted',record,1)
   blocked=struct.unpack('<3f',get('visual_target',12));assert abs(blocked[0]-base[0])<.00001 and abs(blocked[2]-base[2])<.00001,(base,blocked)
   assert blocked[1]==base[1] and authority()==reference and get('net_wrecks',64)==record
   rows.append({'phase':'admitted','target':blocked,'wreck_instances':u32('mesh_wreck_instances'),'screenshot':path})
   tomb=bytearray(record);struct.pack_into('<I',tomb,52,struct.unpack_from('<I',record,52)[0]&2);wire_clock[0]=1800;send(struct.pack('<I',0)+tomb,1800)
   pixels,path,_=capture('body-retired',bytes(tomb),0)
   retired=struct.unpack('<3f',get('visual_target',12));assert retired[0]>base[0]+.1 and retired[1]==base[1] and authority()==reference,(base,retired)
   rows.append({'phase':'retired','target':retired,'screenshot':path})
   assert world.sim_checksum()==fixture_hash,'observer changed physical fixture'
   assert ticks==u32('local_sim_ticks'),'network preview advanced local simulation'
   print(json.dumps({'suite':'actual-udp-client-wreck-foot-preview','passed':True,'cases':rows,'actual_keyboard_wish':wish,'client_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'source_record_sha256':hashlib.sha256(record).hexdigest(),'received_authority_except_transport_tick_unchanged':True,'preparation_public_ticks':150,'genuine_casualty_and_physical_foot_contact':True,'limits':['SoftwareGL and fake UDP transport carrying genuine frozen core snapshots; synthetic tick freshness and expiry.','Not natural server/controller replay, lossy fresh-cover guarantee, camera smoothing or artistic acceptance.','Source world remains frozen after genuine initial public-tick contact.']}))
  finally:
   done.set();thread.join(timeout=2);assert not thread.is_alive();XT.XTestFakeKeyEvent(display,key,0,0);X.XFlush(display)
'''
script=prefix+body+original[original.index('\nfinally:'):]
exec(compile(script,str(root/'tests/test_wreck_client.py'),'exec'))
