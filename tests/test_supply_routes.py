#!/usr/bin/env python3
"""Actual sparse movement/finite credit and read-only selector fault fixtures.
Each scene declares startup positions/low stock once, then never writes state.
Original massive-world verification remains separate and unchanged.
"""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];source=pathlib.Path(sys.argv[1]if len(sys.argv)>1 else root/'build/libsim.so')
nasm=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
with tempfile.TemporaryDirectory(prefix='rh-supply-route-')as directory:
 td=pathlib.Path(directory);private=td/'core.so';private.write_bytes(source.read_bytes());core=C.CDLL(str(private),mode=C.RTLD_GLOBAL)
 # Probe is a development ABI wrapper; authority is the private actual core.
 obj=td/'probe.o';subprocess.run([nasm,'-f','elf64',str(root/'tests/probe_supply_goal.asm'),'-o',str(obj)],check=True)
 probe=td/'probe.so';subprocess.run(['gcc','-shared','-o',str(probe),str(obj)],check=True);p=C.CDLL(str(probe))
 core.sim_checksum.restype=C.c_uint64;p.probe_supply_goal.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_void_p];p.probe_supply_goal.restype=C.c_int
 core.company_control_order.argtypes=[C.c_uint]*3+[C.c_float]*2
 e=(C.c_uint*262144).in_dll(core,'sim_entities');w=(C.c_uint*262144).in_dll(core,'infantry_weapons');stores=(C.c_uint*48).in_dll(core,'depot_ammunition');sites=(C.c_uint*96).in_dll(core,'sim_sites');players=(C.c_uint*64).in_dll(core,'sim_players');assign=(C.c_uint*16).in_dll(core,'player_companies');controls=(C.c_ubyte*49152).in_dll(core,'company_controls');count=C.c_uint.in_dll(core,'sim_count');abi_calls=0
 def fp(i,v):e[i]=struct.unpack('<I',struct.pack('<f',v))[0]
 def sfp(i,v):sites[i]=struct.unpack('<I',struct.pack('<f',v))[0]
 def pose(actor=0):return tuple(struct.unpack('<f',struct.pack('<I',e[actor*8+i]))[0]for i in (0,1))
 def selector(actor=0):
  global abi_calls
  out=(C.c_ubyte*16)(*([0xa7]*16));regs=(C.c_uint64*7)();before=core.sim_checksum();rc=p.probe_supply_goal(actor,C.byref(out,4),8,regs);abi_calls+=1
  assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,) and core.sim_checksum()==before
  assert bytes(out[:4])+bytes(out[12:])==bytes([0xa7]*8)
  if rc==-1:assert bytes(out)==bytes([0xa7]*16);return rc,None
  return rc,struct.unpack('<2f',bytes(out[4:12]))
 def setup(x=900.,enemy_root=False,mode=0):
  assert core.sim_init(2,73)==0
  fp(0,x);fp(1,3900.);e[5]=1
  fp(8,1000. if enemy_root else 7000.);fp(9,1300. if enemy_root else 6500.);e[13]=0 if enemy_root else 2
  w[1]=12;w[2]=0;w[4]=108
  if enemy_root:assert core.sim_order(1,0,1)==0
  assert core.player_join(0,1)==0;key=assign[0];assert core.company_control_order(0,key,mode,x,4200.)==0
  return key,bytes(controls[key*32:key*32+32])
 def conservation():return sum(w[i*8+1]+w[i*8+2]+w[i*8+4]for i in range(count.value)if e[i*8+4]==0)+sum(stores[i*4]for i in range(12))
 key,intent=setup();assert selector()==(4,(1000.,3900.));initial=conservation();previous=pose();first=None;samples=[]
 for tick in range(1,1501):
  core.sim_tick();current=pose();step=math.dist(previous,current);assert step<=.1204,(tick,step);previous=current
  assert bytes(controls[key*32:key*32+32])==intent and conservation()==initial
  assert e[2]==100 and e[7]==1
  if w[6]and first is None:
   first=tick;assert math.dist(current,(1000.,3900.))<=60 and w[6]==90 and stores[16]==11910
   assert w[1]+w[2]==102 and selector()[0]==-1
  if tick in (1,300,600,900,1500)or tick==first:samples.append([tick,*current,w[1]+w[2],w[6],stores[16]])
 assert first==360 and pose()[1]>4030 and pose()[0]<940
 arrival={'initial_declared_carried':12,'initial_declared_spent':108,'primary_goal':[900,4200],'credit_tick':first,'samples':samples,'conserved_rounds':initial,'primary_control_bytes_preserved':True,'role_speed_bound_m_per_tick':.1204}
 # Real occupation captures command root and cuts the depot's graph path.
 # No state writes after setup: real operation evaluation supplies the cut.
 key,intent=setup(700.,enemy_root=True);initial=conservation();cut=None;before_cut=None;previous=pose()
 for tick in range(1,1201):
  core.sim_tick();current=pose();assert math.dist(previous,current)<=.1204;previous=current
  assert conservation()==initial and bytes(controls[key*32:key*32+32])==intent
  assert w[6]==0 and stores[16]==12000 and e[2]==100 and e[7]==1
  if sites[4*8+5]==0 and cut is None:cut=tick;before_cut=current;assert sites[2]==1 and selector()[0]==-1
 assert cut==600 and pose()[1]>3960 and pose()[0]<before_cut[0]
 interrupted={'actual_root_capture_and_cut_tick':cut,'cut_position':before_cut,'final_position':pose(),'received':w[6],'store_remaining':stores[16],'primary_control_bytes_preserved':True}
 # Human commands other than advance cannot be replaced by a detour.
 modes=[]
 for mode in (1,2,3,4):
  key,intent=setup(mode=mode);assert selector()[0]==-1
  for _ in range(60):core.sim_tick()
  assert bytes(controls[key*32:key*32+32])==intent and w[6]==0;modes.append(mode)
 # Read-only selection fixtures: corruption, unavailable stores and boundaries.
 setup();rejected=[]
 for array,index,value,label in [(stores,16,0,'empty malformed'),(stores,18,0,'undeclared'),(stores,19,1,'reserved'),(sites,4*8+2,1,'enemy'),(sites,4*8+4,2,'role'),(sites,4*8+5,0,'cut'),(sites,4*8+6,0,'destroyed'),(sites,4*8+7,4,'contest'),(w,0,2,'generation'),(w,1,31,'magazine'),(e,2,0,'dead')]:
  old=array[index];array[index]=value;assert selector()[0]==-1;array[index]=old;rejected.append(label)
 old=stores[16];oldissued=stores[17];stores[16]=0;stores[17]=12000;assert selector()[0]==-1;stores[16]=old;stores[17]=oldissued
 for value in (math.nan,-1.,8001.):
  old=e[0];fp(0,value);assert selector()[0]==-1;e[0]=old
 for value in (math.nan,-1.,8001.):
  old=sites[32];sfp(32,value);assert selector()[0]==-1;sites[32]=old
 fp(0,400.);assert selector()[0]==4;fp(0,399.);assert selector()[0]==-1;fp(0,900.)
 for actor in (2,32768,0xffffffff):assert selector(actor)[0]==-1
 old=count.value;count.value=32769;out=(C.c_float*2)();regs=(C.c_uint64*7)();assert p.probe_supply_goal(0,out,8,regs)==-1;count.value=old
 # Both labels mirrored without changing physical bodies/stores preserve choice.
 setup();a=selector();e[3]=1
 for i in range(12):sites[i*8+2]^=1
 assert selector()==a
 print(json.dumps({'suite':'infantry-supply-routes','passed':True,'physical_arrival_and_resumption':arrival,'actual_capture_interrupt':interrupted,'human_hold_retreat_follow_defend_preserved':modes,'readonly_rejected_source_stock_cases':rejected,'radius_finite_pose_and_index_gates':True,'physical_labels_only_mirror_choice':True,'selector_abi_calls':abi_calls,'core_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),'limits':['Two-actor startup construction, then genuine ticks with no live pose/HP/clock/stock renewal. Not original massive-world acceptance.','Read-only selector faults are static query fixtures, not sustained battles.','No convoy/production/player-vehicle-air rearm or hardware budget claim.']}))
