#!/usr/bin/env python3
"""Actual public turn trajectories against assembled omitted-lift controls."""
import ctypes as C,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];NASM=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-load-')as d:
 folder=Path(d);objects=[]
 for src in sorted(p for name in ('sim','nav','ai','game')for p in (R/'src'/name).glob('*.asm'))+[R/'tests/terrain_probe.asm']:
  obj=folder/(src.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(R)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 candidate=folder/'candidate.so';link(candidate,objects)
 source=(R/'src/ai/air_bank.asm').read_text();start=source.index(' ; Desired signed yaw*speed');end=source.index(' movss xmm1,[gravity]\n call atan2f',start)
 changed=source[:start]+source[end:];asm=folder/'control.asm';asm.write_text(changed);obj=folder/'control.o'
 subprocess.run([NASM,'-f','elf64','-I',str(R)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
 control=folder/'control.so';link(control,[obj if p.name=='air_bank.asm.o'else p for p in objects])
 reports=[]
 for side in (0,1):
  for role in (0,1):
   pair=[]
   for path,label in [(candidate,'lift-envelope'),(control,'omitted-lift-envelope')]:
    repeats=[]
    for repeat in range(2):
     l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
     assert l.sim_init(64,42)==0
     e=(Entity*32768).in_dll(l,'sim_entities');a=(Air*32768).in_dll(l,'sim_aircraft')
     for i in range(64):e[i].hp=0
     for team in (0,1):
      for front in range(3):assert l.sim_order(team,front,1)==0
     # Outward corner flight genuinely invokes the production emergency turn.
     # Exactly one initial own birth; no later pose, health, stores or clock writes.
     x=z=(6900.,1100.)[side];h=(math.pi/4,-3*math.pi/4)[side];speed=(5.,7.)[role]
     e[31]=Entity(x,z,200,side,3,1,-1,1)
     a[31]=Air(l.terrain_height(x,z)+(110.,140.)[role],h,0,0,speed,role,0,-1,0,(8,180)[role],1,speed*math.sin(h),0,speed*math.cos(h),0,1)
     rows=[];maximum_load=1.;maximum_excess=0.;maximum_error=0.;maximum_roll=0.;minimum_clearance=8000.
     for tick in range(360):
      old=(e[31].x,a[31].y,e[31].z);oldbank=a[31].bank;oldheading=a[31].heading;l.sim_tick();air=a[31]
      assert e[31].hp==200 and e[31].gen==air.gen==1 and air.ammo==(8,180)[role]
      assert 0<=e[31].x<=8000 and 0<=e[31].z<=8000
      actual=1/math.cos(air.bank);allowed=min((4.5,8.)[role],.9*(air.speed/(2.2,2.3)[role])**2)
      maximum_load=max(maximum_load,actual);maximum_excess=max(maximum_excess,actual-allowed)
      if label=='lift-envelope':assert actual<=allowed+2e-6,(side,role,tick,actual,allowed)
      roll=abs(air.bank-oldbank);maximum_roll=max(maximum_roll,roll);assert roll<=(.060002,.100002)[role]
      norm=math.sqrt(air.vx**2+air.vy**2+air.vz**2);step=math.dist(old,(e[31].x,air.y,e[31].z))
      maximum_error=max(maximum_error,abs(norm-air.speed),abs(step-air.speed));assert maximum_error<.001,(side,role,label,tick,old,(e[31].x,air.y,e[31].z),norm,step,air.speed,air.bank)
      yaw=math.atan2(math.sin(air.heading-oldheading),math.cos(air.heading-oldheading))
      assert abs(yaw+.0109*math.tan(air.bank)/air.speed)<5e-7
      minimum_clearance=min(minimum_clearance,e[31].x,e[31].z,8000-e[31].x,8000-e[31].z)
      rows.append((e[31].x,air.y,e[31].z,air.bank,air.speed,actual))
     repeats.append(dict(maximum_load_g=maximum_load,maximum_envelope_excess_g=maximum_excess,maximum_roll_step=maximum_roll,maximum_motion_error_m=maximum_error,minimum_map_clearance_m=minimum_clearance,trace_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),checksum=f'{l.sim_checksum():016x}'))
    assert repeats[0]==repeats[1];pair.append(dict(policy=label,**repeats[0]))
   assert pair[1]['maximum_envelope_excess_g']>.15 and pair[1]['maximum_load_g']>pair[0]['maximum_load_g']+.15,pair
   assert pair[0]['trace_sha256']!=pair[1]['trace_sha256']
   reports.append(dict(side=side,role=role,ticks=360,paired=pair))
 # Causal reserve admission: assembled removal changes only acquired holding.
 flight_source=(R/'src/ai/aircraft.asm').read_text()
 reserve_needle=' cmp dword [rcx+r12*8+4],1\n jne .bank_policy_ready\n mov esi,1'
 assert flight_source.count(reserve_needle)==1
 reserve_control=flight_source.replace(reserve_needle,reserve_needle.replace('mov esi,1','xor esi,esi'))
 asm=folder/'no_orbit_reserve.asm';asm.write_text(reserve_control);obj=folder/'no_orbit_reserve.o'
 subprocess.run([NASM,'-f','elf64','-I',str(R)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
 no_reserve=folder/'no_orbit_reserve.so';link(no_reserve,[obj if p.name=='aircraft.asm.o'else p for p in objects])
 holding=[]
 for side in (0,1):
  for role in (0,1):
   pair=[]
   for path,label in [(candidate,'holding-maneuver-reserve'),(no_reserve,'omitted-holding-reserve')]:
    l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;assert l.sim_init(64,42)==0
    e=(Entity*32768).in_dll(l,'sim_entities');a=(Air*32768).in_dll(l,'sim_aircraft');sites=((C.c_uint*8)*12).in_dll(l,'sim_sites')
    for site in (0,4,8,3,7,11):sites[site][6]=0
    for i in range(64):e[i].hp=0
    for team in (0,1):
     for front in range(3):assert l.sim_order(team,front,1)==0
    speed=(5.,7.)[role];e[31]=Entity(4000,4000,200,side,3,1,-1,1);a[31]=Air(200,math.pi/2,0,0,speed,role,0,-1,0,0,1,speed,0,0,0,1)
    phase=((C.c_uint*2)*32768).in_dll(l,'sim_air_holding');arrival=None;late=[];bad=0;closest=8000.;rows=[]
    for tick in range(1,3001):
     old=(e[31].x,a[31].y,e[31].z);l.sim_tick();air=a[31];gap=math.hypot(e[31].x-(2800.,5200.)[side],e[31].z-4000)
     assert e[31].hp==200 and air.gen==e[31].gen==1 and air.ammo==0 and air.mode==3
     assert abs(math.dist(old,(e[31].x,air.y,e[31].z))-air.speed)<.001
     assert 0<=e[31].x<=8000 and 0<=e[31].z<=8000
     closest=min(closest,gap)
     if phase[31][1]and arrival is None:arrival=tick
     if tick>1400:
      late.append(gap);bad+=not((900.,950.)[role]-75<gap<(900.,950.)[role]+75)
     rows.append((e[31].x,air.y,e[31].z,air.bank,air.mode))
    assert arrival is not None and closest<150
    if label=='holding-maneuver-reserve':assert bad==0
    pair.append(dict(policy=label,arrival_tick=arrival,closest_gap_m=closest,late_radial_range_m=[min(late),max(late)],late_out_of_band_frames=bad,trace_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),checksum=f'{l.sim_checksum():016x}'))
   if role==0 and side==0:assert pair[1]['late_out_of_band_frames']>10,pair
   holding.append(dict(side=side,role=role,ticks=3000,paired=pair))
 print(json.dumps(dict(suite='air-load-public-flight',passed=True,reports=reports,holding_capture=holding,holding_control_sha256=hashlib.sha256(reserve_control.encode()).hexdigest(),source_sha256=hashlib.sha256(source.encode()).hexdigest(),control_sha256=hashlib.sha256(changed.encode()).hexdigest(),library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),initial_births_only=True,limits=['Coordinated-turn lift/structural checks cover original5..7m/tick flights; low-speed lift, energy and landing acceptance require separate scopes.','Initial no-opponent corner trajectories; full army, combat, graphics, UDP and CPU timing require separate checks.'])))
