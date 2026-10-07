#!/usr/bin/env python3
"""Owned recovery policy/ABI and genuine-projectile-triggered public withdrawal."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
class Observation(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in ('owner_gen','target','target_gen','tick','known')]+[('reserved',C.c_uint*5)]

with tempfile.TemporaryDirectory(prefix='rh-air-recovery-') as folder:
 td=pathlib.Path(folder);objects=[]
 for source in [p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]+[R/'tests/terrain_probe.asm',R/'tests/probe_air_recovery.asm']:
  obj=td/(source.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True)
 so=td/'candidate.so';link(so,objects)
 source=(R/'src/ai/air_recovery.asm').read_text();control_source=source.replace('air_recovery_goal:\n','air_recovery_goal:\n cmp edi,31\n jne .normal\n xor eax,eax\n ret\n.normal:\n',1);(td/'control.asm').write_text(control_source)
 obj=td/'control.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(td/'control.asm'),'-o',str(obj)],check=True)
 control=td/'control.so';link(control,[obj if p.name=='air_recovery.asm.o'else p for p in objects])
 def bind(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];l.probe_air_recovery.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft')
 l,e,a=bind(so)
 def reset(l,e,a):
  assert l.sim_init(64,42)==0
  # Initial unavailable-facility fixture preserves original home-holding gates.
  # Usable-base approaches are independently covered by test_air_approach.py.
  sites=((C.c_uint*8)*12).in_dll(l,'sim_sites')
  for site in (0,4,8,3,7,11):sites[site][6]=0
  for i in range(64):e[i].hp=0
  for side in (0,1):
   for front in range(3):assert l.sim_order(side,front,1)==0
  assert l.sim_waypoint(0,0,7000.,4000.)==0 and l.sim_waypoint(1,0,1000.,4000.)==0
 def plane(e,a,i,x,side,hp,ammo,role=1):
  speed=(5,7)[role];e[i]=Entity(x,4000,hp,side,3,1,-1,1);a[i]=Air(200,math.pi/2,0,0,speed,role,0,-1,0,ammo,1,speed,0,0,0,1)
 def query(i=31,hash_sample=True):
  out=(C.c_float*4)(123,0,0,456);abi=(C.c_uint64*7)();before=l.sim_checksum()if hash_sample else None;physical=(C.string_at(C.addressof(e),64*C.sizeof(Entity)),C.string_at(C.addressof(a),64*C.sizeof(Air)));rc=l.probe_air_recovery(i,81.,-17.,0.,C.byref(out,4),abi)
  assert out[0]==123 and out[3]==456 and tuple(abi)==tuple(0x123401+i for i in range(6))+(0,) and (not hash_sample or l.sim_checksum()==before)
  assert physical==(C.string_at(C.addressof(e),64*C.sizeof(Entity)),C.string_at(C.addressof(a),64*C.sizeof(Air)))
  return rc,tuple(out)[1:3]
 reset(l,e,a);plane(e,a,31,4000,0,200,180)
 cases=0
 for role in (0,1):
  a[31].role=role
  for side in (0,1):
   e[31].side=side
   for front in range(3):
    e[31].front=front
    for hp in range(1,201):
     e[31].hp=hp
     for ammo in (0,1,8,180):
      a[31].ammo=ammo;expected=(1,((2000.,6000.)[side],2000.*(front+1)))if hp<=60 or ammo==0 else(0,(81.,-17.));assert query(hash_sample=cases%128==0)==expected;cases+=1
 guards=[]
 for owner,field,bad in [(e[31],'hp',0),(e[31],'kind',0),(e[31],'side',2),(e[31],'front',3),(e[31],'gen',0),(a[31],'gen',2),(a[31],'flags',0),(a[31],'role',2)]:
  reset(l,e,a);plane(e,a,31,4000,0,60,180);old=getattr(owner,field);setattr(owner,field,bad);assert query()==(0,(81.,-17.));setattr(owner,field,old);guards.append(field)
 for idx in (64,32768,0xffffffff):assert query(idx)==(0,(81.,-17.))
 reset(l,e,a);plane(e,a,31,4000,0,60,180);before=query();e[63]=Entity(math.nan,8001,0,1,3,2,-1,999);a[63].y=math.inf;assert query()==before
 empty=[]
 for role in (0,1):
  for side in (0,1):
   reset(l,e,a);plane(e,a,31,4000,side,200,0,role);closest=2000.;travel=0.
   for tick in range(1200):
    old=(e[31].x,a[31].y,e[31].z);l.sim_tick();step=math.dist(old,(e[31].x,a[31].y,e[31].z));assert abs(step-(5,7)[role])<.001;travel+=step
    assert a[31].ammo==0 and e[31].hp==200 and a[31].target==-1 and a[31].mode==3
    assert 0<=e[31].x<=8000 and 0<=e[31].z<=8000
    closest=min(closest,math.dist((e[31].x,e[31].z),((2000,6000)[side],4000)))
   assert closest<150,(role,side,closest)
   empty.append({'role':role,'side':side,'ticks':1200,'closest_recovery_gap_m':closest,'travel_m':travel,'remaining_rounds':a[31].ammo,'hp':e[31].hp,'checksum':hex(l.sim_checksum())})
 reports=[]
 for tag,path in [('recovery',so),('owner_recovery_disabled',control)]:
  repeats=[]
  for repeat in range(2):
   ll,ee,aa=bind(path);reset(ll,ee,aa);plane(ee,aa,31,4000,0,200,180);plane(ee,aa,63,3900,1,60,180);aa[63].target=31
   # Six real initial producer rounds; API does not debit FSM stores. Critical
   # shooter withdraws in both policies; only owner31 recovery is disabled.
   for _ in range(6):assert ll.projectile_air_launch(63,4)==0
   ammo={31:180,63:180};critical_tick=return_tick=None;initial_return_gap=None;max_step_error=0;closest_gap=math.inf;samples=[];shots=set();events=(C.c_uint*(256*8)).in_dll(ll,'sim_events')
   for tick in range(1,1201):
    old={i:(ee[i].x,aa[i].y,ee[i].z)for i in ammo};ll.sim_tick()
    for i in ammo:
     if ee[i].hp:max_step_error=max(max_step_error,abs(math.dist(old[i],(ee[i].x,aa[i].y,ee[i].z))-7))
     assert aa[i].ammo<=ammo[i];ammo[i]=aa[i].ammo
    if ee[31].hp<=60 and critical_tick is None:critical_tick=tick
    if aa[31].mode==3 and return_tick is None:return_tick=tick;initial_return_gap=math.dist((ee[31].x,ee[31].z),(2000,4000))
    closest_gap=min(closest_gap,math.dist((ee[31].x,ee[31].z),(2000,4000)))
    if tick%100==0:samples.append([tick,ee[31].x,ee[31].z,ee[31].hp,aa[31].mode,aa[31].ammo])
    for j in range(256):
     if events[j*8+3]==8 and events[j*8+7]:shots.add(events[j*8+7])
   repeats.append({'critical_tick':critical_tick,'return_tick':return_tick,'initial_return_gap':initial_return_gap,'closest_gap_m':closest_gap,'final_gap_m':math.dist((ee[31].x,ee[31].z),(2000,4000)),'hp':ee[31].hp,'ammo':ammo,'maximum_step_error_m':max_step_error,'samples':samples,'retained_gun_births':len(shots),'checksum':hex(ll.sim_checksum())})
  assert repeats[0]==repeats[1]
  reports.append({'policy':tag,**repeats[0]})
 good,bad=reports
 assert good['critical_tick']==bad['critical_tick']==5 and good['return_tick']==53 and bad['return_tick']is None
 assert good['hp']==bad['hp']==56
 assert good['ammo']=={31:180,63:180} and bad['ammo'][63]==180 and 0<=bad['ammo'][31]<=180
 assert good['retained_gun_births']==6
 assert bad['retained_gun_births']==6+180-bad['ammo'][31]
 assert good['maximum_step_error_m']<.001 and bad['maximum_step_error_m']<.001
 assert good['closest_gap_m']<150 and bad['final_gap_m']>3000
 print(json.dumps({'suite':'air-recovery','passed':True,'policy_cases':cases,'physical_records_readonly_every_query':True,'full_checksum_readonly_samples':75,'empty_store_public_flight':empty,'invalid_metadata_cases':len(guards)+3,'ABI_readonly_and_hidden_enemy_independence':True,'public_traces':reports,'control_source_sha256':hashlib.sha256(control_source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Six initial genuine producer rounds do not debit FSM stores; subsequent public stores monotone, no in-flight HP/pose/ammo/generation/clock writes.','Recovery arrival measured by closest gap; later holding is checked separately. Not landing, rearming, safe survival or universal tactics.']}))
