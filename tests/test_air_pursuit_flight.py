#!/usr/bin/env python3
"""Matched public flight vs full-strength stale pursuit; initial births only."""
import ctypes as C,hashlib,json,math,os,pathlib,statistics,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
class Observation(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in ('owner_gen','target','target_gen','tick','known')]+[('reserved',C.c_uint*5)]

with tempfile.TemporaryDirectory(prefix='rh-air-pursuit-flight-') as folder:
 td=pathlib.Path(folder);objects=[]
 for source in [p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]+[R/'tests/terrain_probe.asm']:
  obj=td/(source.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True)
 so=td/'candidate.so';link(so,objects)
 source=(R/'src/ai/air_pursuit.asm').read_text();control_source=source.replace('air_pursuit_blend:\n','air_pursuit_blend:\n movaps xmm0,xmm1\n xor eax,eax\n ret\n',1);(td/'control.asm').write_text(control_source)
 obj=td/'control.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(td/'control.asm'),'-o',str(obj)],check=True)
 control=td/'control.so';link(control,[obj if p.name=='air_pursuit.asm.o'else p for p in objects])
 reports=[]
 for tag,path in [('weighted',so),('full_strength',control)]:
  repeats=[]
  for repeat in range(2):
   l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
   assert l.sim_init(64,7)==0
   e=(Entity*32768).in_dll(l,'sim_entities');a=(Air*32768).in_dll(l,'sim_aircraft');o=(Observation*32768).in_dll(l,'sim_air_observations');now=C.c_uint.in_dll(l,'sim_tick_count')
   for i in range(64):e[i].hp=0
   for side in (0,1):
    for front in range(3):assert l.sim_order(side,front,1)==0
   assert l.sim_waypoint(0,0,7000.,4000.)==0 and l.sim_waypoint(1,0,1000.,4000.)==0
   for i,side,z,h in ((31,0,4000,0),(63,1,4400,math.pi)):
    e[i]=Entity(4000,z,200,side,3,0,-1,1);a[i]=Air(200,h,0,0,7,1,0,-1,0,180,1,7*math.sin(h),0,7*math.cos(h),0,1)
   seen=stale=0;rounds={31:180,63:180};samples=[];births=set();mission_error=[];max_move_error=max_yaw=max_vertical_change=0
   events=(C.c_uint*(256*8)).in_dll(l,'sim_events')
   for step in range(360):
    old={i:(e[i].x,a[i].y,e[i].z,a[i].heading,a[i].vy,a[i].speed)for i in rounds};l.sim_tick()
    for i in rounds:
     if e[i].hp:
      assert 5<=a[i].speed<=7 and -.012002<=a[i].speed-old[i][5]<=.010002
      max_move_error=max(max_move_error,abs(math.dist(old[i][:3],(e[i].x,a[i].y,e[i].z))-a[i].speed));yaw=abs(math.atan2(math.sin(a[i].heading-old[i][3]),math.cos(a[i].heading-old[i][3])));max_yaw=max(max_yaw,yaw);max_vertical_change=max(max_vertical_change,abs(a[i].vy-old[i][4]))
     assert a[i].ammo<=rounds[i];rounds[i]=a[i].ammo
     if o[i].known:
      age=now.value-o[i].tick
      if age==0:seen+=1
      elif age<90:stale+=1
      if i==31 and 75<=age<90 and e[i].hp:
       desired=math.atan2(7000-e[i].x,4000-e[i].z);mission_error.append(abs(math.atan2(math.sin(a[i].heading-desired),math.cos(a[i].heading-desired))))
    for j in range(256):
     if events[j*8+3]==8 and events[j*8+7]:births.add(events[j*8+7])
    if step%30==29:samples.append([now.value,a[31].heading,a[31].bank,a[31].vy,rounds[31],e[31].hp])
   assert max_move_error<.001 and max_yaw<=.04001 and max_vertical_change<=.02401
   repeats.append({'checksum':hex(l.sim_checksum()),'real_round_births':len(births),'hp':{i:e[i].hp for i in rounds},'rounds':rounds,'fresh_samples':seen,'stale_samples':stale,'late_memory_mission_heading_errors':mission_error,'maximum_step_error_m':max_move_error,'maximum_yaw_step':max_yaw,'maximum_vertical_acceleration':max_vertical_change,'samples':samples})
  assert repeats[0]==repeats[1]
  reports.append({'policy':tag,**repeats[0]})
 weighted,full=reports
 assert weighted['real_round_births']==full['real_round_births']==2
 assert weighted['hp']==full['hp']=={31:176,63:176}
 assert weighted['rounds']==full['rounds']=={31:179,63:179}
 assert weighted['stale_samples']==full['stale_samples']==178
 assert weighted['samples'][0]==full['samples'][0], 'emergency response changed'
 assert len(weighted['late_memory_mission_heading_errors'])==len(full['late_memory_mission_heading_errors'])==15
 weighted_error=statistics.mean(weighted['late_memory_mission_heading_errors']);full_error=statistics.mean(full['late_memory_mission_heading_errors'])
 assert weighted_error<full_error-.3,(weighted_error,full_error)
 print(json.dumps({'suite':'air-confidence-physical-flight','passed':True,'late_memory_mean_mission_heading_error':{'weighted':weighted_error,'full_strength':full_error},'reports':reports,'control_source_sha256':hashlib.sha256(control_source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'initial_births_only':True,'limits':['Controlled360tick encounter per replay, no general survival/tactics/art/scale/network acceptance.']}))
