#!/usr/bin/env python3
"""Independent crash snapshots exercise actual NASM cache, ordering and ABI."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Crash(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz','heading','pitch','bank')]+[(n,C.c_uint) for n in ('role','side','entity','generation','birth','sequence','state')]+[('reserved',C.c_uint*8)]
def record(slot=0,**kw):
 f=dict(x=100,y=200,z=100,vx=0,vy=-1,vz=7,heading=.4,pitch=.1,bank=-.2,role=0,side=0,entity=12,generation=1,birth=0,sequence=1,state=1,reserved=(C.c_uint*8)());f.update(kw)
 return struct.pack('<I',slot)+bytes(Crash(**f))
with tempfile.TemporaryDirectory(prefix='rh-crash-remote-') as d:
 td=pathlib.Path(d);source=(R/'src/sim/air_crash_remote.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objects=[]
  for i,p in enumerate((asm,R/'tests/probe_air_crash_remote.asm')):
   obj=td/f'{tag}{i}.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True);l=C.CDLL(str(so));l.probe_air_crash_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p];return l,so
 l,so=build('candidate');cache=(Crash*128).in_dll(l,'net_air_crashes');count=C.c_uint.in_dll(l,'net_air_crash_count');calls=0
 def arena():return C.string_at(C.addressof(cache),128*96+4+128*5)
 def receive(payload,tick=10,expected=None,which=l,size=None,null=False):
  global calls
  b=C.create_string_buffer(payload);before=b.raw;regs=C.create_string_buffer(56);rc=which.probe_air_crash_receive(None if null else b,len(payload) if size is None else size,tick,regs)
  assert b.raw==before and struct.unpack('<6Q',regs.raw[:48])==tuple(0x123401+i for i in range(6))
  if expected is not None:assert rc==expected,(rc,expected)
  calls+=1;return rc
 l.air_crash_remote_reset();virgin=arena();bad=[]
 for f,v in [('x',-1),('z',8001),('y',math.nan),('vx',math.inf),('vy',33),('pitch',17),('bank',math.nan),('role',2),('side',2),('entity',32768),('generation',0),('sequence',0),('state',3),('state',0),('birth',11)]:bad.append(record(**{f:v}))
 reserved=(C.c_uint*8)();reserved[7]=1
 bad += [record(reserved=reserved),record(slot=128),record(state=2),record()+record(),record()+record(slot=1,x=math.nan),record()*12,b'',record()[:-1],record()+b'X']
 for p in bad:receive(p,expected=-1);assert arena()==virgin
 receive(record(),null=True,expected=-1);receive(record(),size=0xffffffff,expected=-1);assert arena()==virgin
 for begin in range(0,128,11):
  rows=[record(slot=i,sequence=i+1,entity=i,role=i%2,side=i%2) for i in range(begin,min(128,begin+11))];receive(b''.join(reversed(rows)),tick=0,expected=len(rows))
 assert count.value==128
 # Newer motion updates accepted; same-tick conflict and immutable identity reject atomically.
 receive(record(entity=0,x=107,y=199),tick=1,expected=1);before=arena()
 receive(record(entity=0,x=108,y=199),tick=1,expected=-1);assert arena()==before
 receive(record(slot=1,sequence=200,birth=2)+record(entity=1,x=108),tick=2,expected=-1);assert arena()==before
 receive(record(entity=0),tick=0,expected=0);assert arena()==before
 landed=record(entity=0,x=200,y=10,vy=0,vz=0,pitch=0,bank=0,state=2)
 receive(landed,tick=100,expected=1);before=arena()
 receive(record(entity=0,x=200),tick=101,expected=-1);assert arena()==before
 receive(record(entity=0,x=201,y=10,vy=0,vz=0,pitch=0,bank=0,state=2),tick=101,expected=-1);assert arena()==before
 receive(landed,tick=101,expected=1)
 # Slot replacement retires old sequence even if historical packet has a newer source tick.
 receive(record(entity=0,sequence=200,birth=102,generation=2),tick=102,expected=1);saved=bytes(cache[0])
 receive(record(entity=0),tick=103,expected=0);assert bytes(cache[0])==saved
 l.air_crash_remote_expire(1799);assert count.value==128
 l.air_crash_remote_expire(1800);assert count.value==1
 before=bytes(cache[1]);receive(record(slot=1,sequence=2,entity=1,role=1,side=1),tick=1799,expected=0);assert bytes(cache[1])==before
 receive(record(slot=1,sequence=2,entity=1,role=1,side=1,state=0),tick=1800,expected=1)
 l.air_crash_remote_expire(1902);assert count.value==0
 l.air_crash_remote_reset();receive(record(sequence=0xfffffff0,birth=0xfffffff0),tick=0xfffffff5,expected=1)
 receive(record(sequence=1,birth=0xfffffff8,generation=2),tick=3,expected=1)
 saved=bytes(cache[0]);receive(record(sequence=0xfffffff0,birth=0xfffffff0),tick=4,expected=0);assert bytes(cache[0])==saved
 l.air_crash_remote_expire((0xfffffff8+1800)&0xffffffff);assert count.value==0
 l.air_crash_remote_reset();assert arena()==virgin
 actual_calls=calls;negatives=[]
 for tag,text in [('stale_tick',source.replace(' js .next',' nop',1)),('no_expiry',source.replace(' mov dword [rsi+AIR_CRASH_STATE],0',' nop')),('duplicate_slot',source.replace(' cmp eax,[rdx]\n je .invalid',' cmp eax,[rdx]\n nop'))]:
  mutant,_=build(tag,text);mutant.air_crash_remote_reset()
  if tag=='stale_tick':receive(record(),tick=10,expected=1,which=mutant);receive(record(sequence=2),tick=9,expected=1,which=mutant)
  elif tag=='no_expiry':receive(record(),which=mutant,expected=1);mutant.air_crash_remote_expire(1800);assert C.c_uint.in_dll(mutant,'net_air_crash_count').value==1
  else:receive(record()+record(),which=mutant,expected=2)
  negatives.append(tag)
 print(json.dumps(dict(suite='air-crash-remote-lifecycle',passed=True,calls=actual_calls,slots=128,malformed_atomic_packets=len(bad)+2,negative_controls=negatives,ABI_preserved=True,mutable_falling_immutable_landed=True,whole_packet_conflict_atomic=True,expiry_retirement_reuse_no_revival=True,modular_wrap=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),library_sha256=hashlib.sha256(so.read_bytes()).hexdigest(),scope='Native cache only; transport/server/draw acceptance separate')))
