#!/usr/bin/env python3
"""Real geometry/index/casualty/query and publicly launched projectile outcomes."""
import ctypes as C,hashlib,itertools,json,math,os,pathlib,struct,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];PATH=pathlib.Path(sys.argv[1]).resolve();NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
def bounds(w):
 corners=[]
 for a,b,c in itertools.product((-1,1),repeat=3):
  x,y,z=a*1.895,1.31645+b*1.30455,c*3
  sb,cb=math.sin(w.bank),math.cos(w.bank);x,y=cb*x-sb*y,sb*x+cb*y
  sp,cp=math.sin(w.pitch),math.cos(w.pitch);y,z=cp*y+sp*z,-sp*y+cp*z
  sh,ch=math.sin(w.heading),math.cos(w.heading);x,z=ch*x+sh*z,-sh*x+ch*z
  corners.append((x+w.x,y+w.y,z+w.z))
 return tuple(min(c[i] for c in corners)-.002 for i in range(3))+tuple(max(c[i] for c in corners)+.002 for i in range(3))
class Event(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z')]+[(n,C.c_uint) for n in ('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
with tempfile.TemporaryDirectory(prefix='rh-world-contact-outcomes-') as folder:
 td=pathlib.Path(folder);asm=td/'probe.asm';asm.write_text((ROOT/'tests/probe_world_contact.asm').read_text().replace('call world_contact_query','call world_contact_query wrt ..plt'));obj=td/'probe.o';subprocess.run([NASM,'-f','elf64',str(asm),'-o',str(obj)],check=True);so=td/'probe.so';subprocess.run(['cc','-shared',str(obj),str(PATH),'-Wl,-rpath,'+str(PATH.parent),'-o',str(so)],check=True)
 lib=C.CDLL(str(PATH));probe=C.CDLL(str(so));probe.probe_world_contact_query.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*6
 lib.sim_init.argtypes=[C.c_uint]*2;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_checksum.restype=C.c_uint64;lib.projectile_launch.argtypes=[C.c_uint]*2+[C.c_float]*3
 entities=(E*32768).in_dll(lib,'sim_entities');alive=(C.c_uint*2).in_dll(lib,'sim_alive');wrecks=(W*1024).in_dll(lib,'sim_wrecks');events=(Event*256).in_dll(lib,'sim_events');ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo');count=C.c_uint.in_dll(lib,'sim_projectile_count');rows=[];calls=0
 def reset(births):
  assert lib.sim_init(64,42)==0
  for e in entities[:64]:e.hp=0
  alive[0]=alive[1]=0;C.c_uint.in_dll(lib,'hazard_enabled').value=0
  for side in (0,1):
   for front in range(3):assert lib.sim_order(side,front,1)==0
  for i,x,z,side,kind,hp in births:entities[i]=E(x,z,hp,side,kind,0,-1,42);alive[side]+=1;ammo[i]=0
  lib.ground_init();lib.sim_tick() # build the actual index from declared initial births
 def query(start,end,kind,identity=None):
  global calls
  out=C.create_string_buffer(24);regs=C.create_string_buffer(56);before=lib.sim_checksum();rc=probe.probe_world_contact_query(out,24,0,regs,*start,*end)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert lib.sim_checksum()==before
  assert rc==1;result=struct.unpack('<f5I',out.raw);assert result[1]==kind,(result,start,end)
  if identity is not None:assert result[2]==identity,(result,identity)
  calls+=1;return result
 reset([(24,5160,1570,1,0,100)]);y=lib.terrain_height(5160,1570)+1.8
 first=query((5150,y,1570),(5200,y,1570),4,24);rows.append({'case':'actor_before_later_solid','result':first})
 reset([(24,5190,1570,1,0,100)]);y=lib.terrain_height(5170,1570)+1.8
 first=query((5150,y,1570),(5220,y,1570),2,3);assert abs(first[0]-(5170-5150)/70)<1e-6;rows.append({'case':'solid_before_later_actor','result':first})
 reset([]);first=query((0,60,5000),(8000,60,5000),1,0);assert .65<first[0]<.73;rows.append({'case':'narrow_relief_before_clear_endpoint','result':first})
 reset([(12,5140,1570,1,1,1),(24,5190,1570,1,0,100)]);lib.sim_air_damage(12,1);w=wrecks[0];saved=bytes(w);y=w.y+1.5
 first=query((5130,y,1570),(5220,y,1570),3,12);assert first[3:5]==(42,w.sequence);assert bytes(w)==saved;rows.append({'case':'genuine_wreck_before_solid_and_actor','result':first})
 reset([(0,5120,1570,0,1,400),(12,5140,1570,1,1,1),(24,5155,1570,1,0,100)]);lib.sim_air_damage(12,1);w=wrecks[0];saved=bytes(w);ammo[0]=1
 assert lib.projectile_launch(0,1,5155,w.y+1,1570)==0
 for _ in range(12):
  lib.projectile_tick()
  if not count.value:break
 assert count.value==0 and bytes(w)==saved
 impacts=[e for e in events if e.kind==3];assert len(impacts)==1;impact=impacts[0];assert abs(impact.x-bounds(w)[0])<.002,(impact.x,bounds(w));assert bounds(w)[1]<=impact.y<=bounds(w)[4] and bounds(w)[2]<=impact.z<=bounds(w)[5]
 assert entities[24].hp==100;rows.append({'case':'public_tank_shell_stops_at_genuine_wreck','impact_xyz':[impact.x,impact.y,impact.z],'actor_behind_hp':entities[24].hp})
 print(json.dumps({'suite':'production-world-contact-outcomes','passed':True,'query_calls':calls,'cases':rows,'readonly_query_checksum_ABI':True,'library_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'scope':'Actual authored solids/continuous relief/current sampled actor index/genuine casualty wreck and publicly launched tank shell. No mid-flight health/pose/projectile renewal. No wreck blast shielding/body/navigation/remote prediction acceptance.'}))
