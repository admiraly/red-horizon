#!/usr/bin/env python3
"""Development-only incoming trace oracle, ABI and public-tick evasion controls."""
import ctypes as C, hashlib, json, math, os, pathlib, random, subprocess, tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
class Round(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in ('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint)for n in ('source','gen','active','source_gen','reserved')]
with tempfile.TemporaryDirectory(prefix='rh-air-threat-') as folder:
 td=pathlib.Path(folder);objects=[]
 for s in [p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]+[R/'tests/terrain_probe.asm',R/'tests/probe_air_threat.asm']:
  o=td/(s.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(s),'-o',str(o)],check=True);objects.append(o)
 def link(path,objs):subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True)
 so=td/'candidate.so';link(so,objects)
 source=(R/'src/ai/air_threats.asm').read_text().replace('air_threat_query:\n','air_threat_query:\n xorps xmm0,xmm0\n mov eax,-1\n ret\n',1)
 neg=td/'negative.asm';neg.write_text(source);obj=td/'negative.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(neg),'-o',str(obj)],check=True)
 control=td/'control.so';link(control,[obj if p.name=='air_threats.asm.o' else p for p in objects])
 def bind(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.probe_air_threat.argtypes=[C.c_uint,C.c_void_p,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),(Round*512).in_dll(l,'sim_projectiles'),(C.c_uint64*8).in_dll(l,'air_threat_metrics')
 l,e,a,p,m=bind(so)
 def setup(l,e,a,p):
  assert l.sim_init(64,7)==0
  for i in range(64):e[i].hp=0
  for i,side,z,h in ((31,0,4000,0),(63,1,4600,math.pi)):
   e[i].x,e[i].z,e[i].hp,e[i].kind,e[i].side=4000,z,200,3,side
  l.air_init();l.air_tick();l.projectile_init()
  for i,z,h in ((31,4000,0),(63,4600,math.pi)):
   e[i].x,e[i].z=4000,z;a[i].y=200;a[i].heading=h;a[i].pitch=0;a[i].speed=7;a[i].vx=0;a[i].vy=0;a[i].vz=7 if i==31 else -7;a[i].target=63 if i==31 else 31;a[i].ammo=180;a[i].cooldown=0
  assert l.projectile_air_launch(63,4)==0
  return next(i for i,r in enumerate(p)if r.active)
 def query(index=31):
  out=(C.c_float*3)(123,0,456);abi=(C.c_uint64*7)();before=l.sim_checksum();rc=l.probe_air_threat(index,C.byref(out,4),abi)
  assert tuple(abi)==tuple(0x123401+i for i in range(6))+(0,)
  assert out[0]==123 and out[2]==456 and l.sim_checksum()==before
  return rc,out[1]
 slot=setup(l,e,a,p);assert query()==(-1,0.)
 l.air_threats_build();assert query()[0]==slot
 # Independent geometry fixtures alter an isolated born trace before a fresh
 # index/query. These are kernel fixtures, never public gameplay encounters.
 rng=random.Random(8012);accepted=0
 cases=[(x,0,z,0,0,-28,40)for x in (-11,-9,0,9,11)for z in (100,600,751)]
 cases += [(rng.uniform(-5,5),rng.uniform(-5,5),rng.uniform(30,700),0,0,-28,40)for _ in range(200)]
 cases += [(rng.uniform(-500,500),rng.uniform(-30,30),rng.uniform(-800,800),0,0,-28,rng.randrange(1,41))for _ in range(600)]
 for x,y,z,vx,vy,vz,ttl in cases:
  p[slot].x,p[slot].y,p[slot].z=4000+x,200+y,4000+z;p[slot].vx,p[slot].vy,p[slot].vz=vx,vy,vz;p[slot].ttl=ttl
  w=(vx,vy,vz-7);r=(x,y,z);rr=sum(v*v for v in r);dot=z*7;t=-sum(v*q for v,q in zip(r,w))/sum(v*v for v in w)
  miss=sum((v+t*q)**2 for v,q in zip(r,w));expected=rr<=750**2 and dot>0 and dot**2>=rr*49*.25 and 0<t<=min(30,ttl) and miss<=100
  l.air_threats_build();rc,direction=query();assert (rc>=0)==expected,(r,t,miss,expected,rc)
  if expected:accepted+=1;assert direction in (-1,1)
  else:assert direction==0
 invalid=[('active',2),('kind',3),('damage',25),('radius',1),('gen',0),('ttl',0),('ttl',41),('side',0),('source_gen',999),('x',math.nan),('vy',math.inf)]
 for field,value in invalid:
  slot=setup(l,e,a,p);setattr(p[slot],field,value);l.air_threats_build();assert query()==(-1,0.),field
 slot=setup(l,e,a,p);e[63].x=9000;a[63].y=math.nan;a[63].target=-1;l.air_threats_build();assert query()[0]==slot,'hidden shooter pose influenced warning'
 slot=setup(l,e,a,p);e[63].hp=0;l.air_threats_build();assert query()[0]==slot,'dead shooter discarded conserved round'
 slot=setup(l,e,a,p);l.air_threats_build();C.c_uint.in_dll(l,'sim_tick_count').value+=1;assert query()==(-1,0.)
 # Actual terrain LOS blocks a below-ground trace, same physical geometry.
 slot=setup(l,e,a,p);a[31].y=p[slot].y=1;l.air_threats_build();assert query()==(-1,0.) and m[5]==1
 slot=setup(l,e,a,p);e[31].side=1;e[63].side=0;p[slot].side=0;l.air_threats_build();assert query()[0]==slot
 # Dense index built from127 genuine producer rounds and original fighter IDs.
 assert l.sim_init(4096,7)==0
 for i in range(4096):e[i].hp=200 if i%32==31 else 0
 l.air_init();l.air_tick();l.projectile_init()
 fighters=list(range(31,4096,32))
 for i in fighters:
  e[i].x,e[i].z,e[i].side=4000,4000 if i==31 else 4600,0 if i==31 else 1
  a[i].y=200;a[i].heading=0 if i==31 else math.pi;a[i].speed=7;a[i].vx=a[i].vy=0;a[i].vz=7 if i==31 else -7;a[i].target=31;a[i].ammo=180;a[i].cooldown=0
 for i in fighters[1:]:assert l.projectile_air_launch(i,4)==0
 l.air_threats_build();assert query()[0]>=0
 budget=list(m);assert budget[0]==512 and budget[1]==127 and budget[3]<=49 and budget[4]==64 and budget[5]<=2 and budget[7]==1,budget
 # Actual public flight: identical initial births and real producer round;
 # thereafter no world writes. Negative control disables warning only.
 encounters=[]
 for path in (so,control,so,control):
  ll,ee,aa,pp,mm=bind(path);setup(ll,ee,aa,pp);trace=[];previous={31:180,63:180}
  for tick in range(1,81):
   ll.sim_tick()
   for i in previous:assert aa[i].ammo<=previous[i];previous[i]=aa[i].ammo
   trace.append((tick,ee[31].hp,aa[31].mode,aa[31].bank,aa[31].y))
  if path==so:assert any(h==200 and abs(bank)>.001 for t,h,mode,bank,y in trace),'no bank before damage'
  encounters.append({'control':path==control,'first_tick':trace[0],'first_damage_tick':next((t for t,h,*_ in trace if h<200),None),'final_hp':ee[31].hp,'rounds':previous,'checksum':hex(ll.sim_checksum())})
 assert encounters[:2]==encounters[2:],'public trace replay diverged'
 assert encounters[0]['first_tick'][1]==200 and encounters[0]['first_tick'][2]!=encounters[1]['first_tick'][2],encounters
 print(json.dumps({'suite':'air-visible-incoming-fire','passed':True,'geometry_cases':len(cases),'accepted':accepted,'invalid_metadata_cases':len(invalid),'ABI_and_authority_unchanged':True,'dead_shooter_round_retained':True,'encounters':encounters,'dense_query_metrics':budget,'terrain_occlusion_and_label_mirror':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Controlled initial encounter and isolated geometry fixtures; no graphics, global optimal threat selection, full gameplay scale budget or spectacle acceptance.','Initial producer round does not debit FSM stores; subsequent public-tick firing stores remain finite and monotone.']}))
