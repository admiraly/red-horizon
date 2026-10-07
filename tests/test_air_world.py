#!/usr/bin/env python3
"""Actual terrain/hull contacts and causal public flight; development only."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,sys,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM'];path=pathlib.Path(sys.argv[1]).resolve()
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
def bind(p):
 l=C.CDLL(str(p));l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
 l.air_world_sweep.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*6;l.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
 return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft')
l,e,a=bind(path);cases=0
assert l.sim_init(64,42)==0
# Independent slab oracle for genuine published authored solids and the4m hull.
boxes=(C.c_float*40).in_dll(l,'terrain_obstacles')
def slab(start,end,box):
 low,high=0.,1.
 for axis in range(3):
  d=end[axis]-start[axis]
  if d==0:
   if not box[axis]<=start[axis]<=box[axis+3]:return None
  else:
   first,last=sorted(((box[axis]-start[axis])/d,(box[axis+3]-start[axis])/d));low=max(low,first);high=min(high,last)
   if low>high:return None
 return low
for slot in range(5):
 x0,z0,x1,z1,base,h=boxes[slot*8:slot*8+6];box=(x0-4,base-4,z0-4,x1+4,base+h+4,z1+4)
 for y in [base+h+3,base+h+4,base+h+4.01,base+h+8]:
  for reverse in [False,True]:
   coords=[x0-20,y,(z0+z1)/2,x1+20,y,(z0+z1)/2]
   if reverse:coords=coords[3:]+coords[:3]
   out=C.create_string_buffer(b'Z'*16,16);before=l.sim_checksum();rc=l.air_world_sweep(out,16,*coords);assert l.sim_checksum()==before
   expected=slab(coords[:3],coords[3:],box)
   if expected is None:assert rc==0,(slot,y,rc)
   else:
    t,kind,ident,res=struct.unpack('<f3I',out.raw);assert rc==1 and kind==2 and ident==slot and res==0 and abs(t-expected)<1e-5,(slot,y,rc,out.raw,expected)
   cases+=1
# Remote relief must not enlarge contact for a low flight on distant flat terrain.
y=l.terrain_height(1040,2000)+6
out=C.create_string_buffer(b'Z'*16,16);before=l.sim_checksum()
assert l.air_world_sweep(out,16,1040,y,2000,1045,y,2000)==0 and out.raw==b'Z'*16 and l.sim_checksum()==before;cases+=1
# True fast crossing and a zero-length overlap cannot tunnel through a solid.
for coords in [(3950,50,1300,4050,50,1300),(3984,50,1300,3984,50,1300),(5400,35,5200,5700,35,5200),(2000,0,2000,2010,0,2000)]:
 out=C.create_string_buffer(16);assert l.air_world_sweep(out,16,*coords)==1;cases+=1
# Clear/error leaves output canaries unchanged. Caller validation includes NaN/Inf.
for coords in [(1000,200,1000,1100,200,1000),(-1,200,1000,1100,200,1000),(1000,math.nan,1000,1100,200,1000),(1000,200,1000,8001,200,1000),(1000,200,1000,1100,math.inf,1000)]:
 out=C.create_string_buffer(b'Z'*16,16);rc=l.air_world_sweep(out,16,*coords);assert rc== (0 if coords[0]==1000 and all(math.isfinite(v)and 0<=v<=8000 for v in coords)else -1);assert out.raw==b'Z'*16;cases+=1
for cap in [0,15]:
 out=C.create_string_buffer(b'Z'*16,16);assert l.air_world_sweep(out,cap,1000,200,1000,1100,200,1000)==-1 and out.raw==b'Z'*16;cases+=1
assert l.air_world_sweep(None,16,1000,200,1000,1100,200,1000)==-1;cases+=1
# Corrupted static records reject atomically even when another source already hits.
libc=C.CDLL(None);libc.mprotect.argtypes=[C.c_void_p,C.c_size_t,C.c_int];page=os.sysconf('SC_PAGE_SIZE');addr=C.addressof(boxes);start=addr//page*page;span=((addr+C.sizeof(boxes)+page-1)//page)*page-start;assert libc.mprotect(start,span,3)==0
original=bytes(boxes)
try:
 for offset,value in [(4,math.nan),(2,boxes[0]-1),(5,-1)]:
  boxes[offset]=value;out=C.create_string_buffer(b'Z'*16,16);assert l.air_world_sweep(out,16,2000,0,2000,2010,0,2000)==-2 and out.raw==b'Z'*16;C.memmove(addr,original,len(original));cases+=1
finally:C.memmove(addr,original,len(original));assert libc.mprotect(start,span,1)==0
with tempfile.TemporaryDirectory(prefix='rh-air-world-control-') as folder:
 td=pathlib.Path(folder);sources=[p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]
 objects=[]
 for source in sources:
  obj=td/(str(source.relative_to(R)).replace('/','_')+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True);objects.append(obj)
 probe=td/'probe.o';subprocess.run([nasm,'-f','elf64',str(R/'tests/probe_air_world.asm'),'-o',str(probe)],check=True)
 abi_so=td/'abi.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(abi_so),*map(str,objects),str(probe),'-lm'],check=True)
 abi_lib=C.CDLL(str(abi_so));abi_lib.probe_air_world_sweep.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*6
 for coords in [(3950,50,1300,4050,50,1300),(1000,200,1000,1100,200,1000),(1000,math.nan,1000,1100,200,1000)]:
  regs=C.create_string_buffer(56);out=C.create_string_buffer(16);rc=abi_lib.probe_air_world_sweep(out,16,0,regs,*coords);assert rc!=-99 and struct.unpack('<6Q',regs.raw[:48])==tuple(0x123401+i for i in range(6))
 source=(R/'src/ai/aircraft.asm').read_text();controls={}
 for name,needle in [('no_warning','call air_world_warning'),('no_contact','call air_world_sweep')]:
  assert source.count(needle)==1;changed=source.replace(needle,'xor eax,eax',1);asm=td/(name+'.asm');asm.write_text(changed);obj=td/(name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(asm),'-o',str(obj)],check=True)
  so=td/(name+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(so),*[str(obj if p.name=='src_ai_aircraft.asm.o'else p)for p in objects],'-lm'],check=True);controls[name]=bind(so)
 def reset(state,x,y,z=5200):
  q,en,air=state;assert q.sim_init(64,42)==0
  for v in en[:64]:v.hp=0
  alive=(C.c_uint*2).in_dll(q,'sim_alive');alive[0]=1;alive[1]=0
  for side in (0,1):
   for front in range(3):assert q.sim_order(side,front,1)==0
  assert q.sim_waypoint(0,0,7000,z)==0
  en[31]=Entity(x,z,200,0,3,0,-1,1);air[31]=Air(y,math.pi/2,0,0,7,1,0,-1,0,180,1,7,0,0,0,1)
 def flight(state,x,y,z=5200,ticks=150):
  reset(state,x,y,z);q,en,air=state;travel=0.;maximum_y=0.;last=(x,y,z);death=None
  for t in range(ticks):
   old=last;oldvy=air[31].vy;oldbank=air[31].bank;q.sim_tick();last=(en[31].x,air[31].y,en[31].z);step=math.dist(old,last);travel+=step;maximum_y=max(maximum_y,last[1]);assert step<=7.001
   assert abs(air[31].vy-oldvy)<=.024002 and abs(air[31].bank-oldbank)<=.100002
   assert air[31].ammo==180 and en[31].gen==1
   if en[31].hp==0:death=t+1;break
   assert abs(step-7)<.001
  return {'death_tick':death,'last_xyz':last,'travel':travel,'maximum_y':maximum_y,'hp':en[31].hp,'ammo':air[31].ammo,'alive':(C.c_uint*2).in_dll(q,'sim_alive')[0],'crashes':C.c_uint.in_dll(q,'sim_air_crash_count').value,'events':C.c_uint.in_dll(q,'sim_event_sequence').value}
 # Late unavoidable wall entry creates one actual casualty/event/wreck, at first hull contact.
 wall=flight((l,e,a),3980,46,1300,ticks=1);wall_control=flight(controls['no_contact'],3980,46,1300,ticks=1)
 assert wall['hp']==0 and wall['alive']==0 and wall['crashes']==1 and wall['events']==1 and abs(wall['last_xyz'][0]-3984)<.01,wall
 assert wall_control['hp']==200 and wall_control['crashes']==0 and wall_control['last_xyz'][0]>3984,wall_control
 # Earlier terrain warning must improve a genuine low-flight ridge encounter.
 ridge=flight((l,e,a),4800,35);ridge_control=flight(controls['no_warning'],4800,35)
 assert ridge['hp']==200 and ridge_control['hp']==0,(ridge,ridge_control)
 late=flight((l,e,a),5100,50);late_control=flight(controls['no_warning'],5100,50)
 assert late['hp']==0 and late_control['hp']==0,(late,late_control)
 # Replay traces are deterministic; no body/HP/clock renewal after the initial birth.
 assert flight((l,e,a),4800,35)==ridge
 print(json.dumps({'suite':'air-world-contact-flight','passed':True,'contact_cases':cases,'six_register_stack_ABI':True,'wall':wall,'omitted_contact_control':wall_control,'ridge':ridge,'late_unavoidable_ridge':late,'late_omitted_warning_control':late_control,'omitted_warning_control':ridge_control,'library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'limits':['Conservative4m axis-aligned hull; ground slope bound can contact before precise mesh intersection.','Own-velocity120tick forward prediction and bounded right-turn/climb, not full route planning, aerodynamic energy or universal avoidance.','Initial births only during causal public traces; no in-flight pose/HP/ammo/generation/clock writes.','No aircraft-to-aircraft physical contact, dynamic wreck contact, crashed-body solid response, GPU/UDP/performance/whole-game acceptance.']}))
