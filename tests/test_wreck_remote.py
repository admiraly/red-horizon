#!/usr/bin/env python3
"""Actual NASM whole-packet immutable remote lifecycle, independent fixtures."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
def record(slot=0,seq=1,birth=0,flags=1,**kw):
 fields=dict(x=100,y=30,z=100,heading=.4,pitch=.1,bank=-.2,kind=1,side=0,entity=12,generation=1,birth=birth,expiry=(birth+1800)&0xffffffff,sequence=seq,flags=flags,reserved0=0,reserved1=0);fields.update(kw)
 w=W(**fields);return struct.pack('<I',slot)+bytes(w)
with tempfile.TemporaryDirectory(prefix='rh-wreck-remote-') as name:
 td=pathlib.Path(name);objs=[];source=(ROOT/'src/sim/wreck_remote.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objects=[]
  for i,path in enumerate((asm,ROOT/'tests/probe_wreck_remote.asm')):
   obj=td/f'{tag}{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(path),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_wreck_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p];return lib,so
 lib,so=build('candidate');Wrecks=(W*1024).in_dll(lib,'net_wrecks');count=C.c_uint.in_dll(lib,'net_wreck_count');regs=C.create_string_buffer(56);calls=0
 def arena(lib=lib):return C.string_at(C.addressof(C.c_byte.in_dll(lib,'net_wrecks')),70660)
 def receive(payload,tick=10,expected=None,which=lib,size=None,null=False):
  global calls
  buf=C.create_string_buffer(payload);before=buf.raw;rc=which.probe_wreck_receive(None if null else buf,len(payload) if size is None else size,tick,regs);assert buf.raw==before
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6))
  if expected is not None:assert rc==expected,(rc,expected)
  calls+=1;return rc
 lib.wreck_remote_reset();virgin=arena();bad=[]
 for field,value in [('x',-1),('z',8001),('y',math.nan),('heading',math.inf),('pitch',17),('bank',math.nan),('kind',0),('side',2),('entity',32768),('generation',0),('sequence',0),('flags',5),('reserved0',1),('expiry',1801)]:bad.append(record(**{field:value}))
 bad.extend([record(slot=1024),record(flags=3),record(flags=0),record(birth=11),record()+record(),record()+record(slot=1,x=math.nan),record()*18,b'',record()[:-1],record()+b'Z'])
 for payload in bad:receive(payload,expected=-1);assert arena()==virgin
 receive(record(),size=0xffffffff,expected=-1);receive(record(),null=True,expected=-1);assert arena()==virgin
 # Full physical capacity, reordered batches, zero timestamp valid, no duplicates.
 for begin in range(0,1024,17):
  rows=[record(slot=i,seq=i+1,entity=i,side=i%2,kind=1+i%2) for i in range(begin,min(1024,begin+17))]
  receive(b''.join(reversed(rows)),tick=0,expected=len(rows))
 assert count.value==1024 and {w.sequence for w in Wrecks}==set(range(1,1025))
 accepted=arena();receive(record(slot=0,x=200),tick=0,expected=-1);assert arena()==accepted
 receive(record(slot=0),tick=0xffffffff,expected=-1);assert arena()==accepted # stale tick
 # Slot retirement/new sequence followed by stale history and source reuse.
 receive(record(slot=0,seq=1025,birth=11,x=200,generation=2),tick=11,expected=1);saved=bytes(Wrecks[0])
 receive(record(slot=0),tick=12,expected=0);assert bytes(Wrecks[0])==saved
 # Equal-sequence conflicts reject a complete otherwise-valid mixed batch.
 before=arena();receive(record(slot=1,seq=2048,birth=12)+record(slot=0,seq=1025,birth=11,x=201,generation=2),tick=12,expected=-1);assert arena()==before
 # Expiry is server-clock based; old valid packets cannot undo local expiry.
 lib.wreck_remote_expire(1799);assert count.value==1024
 lib.wreck_remote_expire(1800);assert count.value==1
 before=bytes(Wrecks[1]);receive(record(slot=1,seq=2,entity=1,side=1,kind=2),tick=1799,expected=0);assert bytes(Wrecks[1])==before
 receive(record(slot=1,seq=2,entity=1,side=1,kind=2,flags=0),tick=1800,expected=1)
 lib.wreck_remote_expire(1811);assert count.value==0
 # Modular tick, birth, expiry and sequence wrap keep independent valid records.
 lib.wreck_remote_reset();receive(record(seq=0xfffffff0,birth=0xfffffff0),tick=0xfffffff5,expected=1)
 receive(record(seq=1,birth=0xfffffff8,x=200,generation=2),tick=3,expected=1);saved=bytes(Wrecks[0])
 receive(record(seq=0xfffffff0,birth=0xfffffff0),tick=4,expected=0);assert bytes(Wrecks[0])==saved
 lib.wreck_remote_expire((0xfffffff8+1799)&0xffffffff);assert count.value==1
 lib.wreck_remote_expire((0xfffffff8+1800)&0xffffffff);assert count.value==0
 lib.wreck_remote_reset();assert arena()==virgin
 # Assembled controls expose partial-apply, stale replacement and missing expiry.
 production_calls=calls;negatives=[]
 for tag,text in [('stale_tick',source.replace(' js .next',' nop',1)),('no_expiry',source.replace(' and dword [rsi+WRECK_FLAGS],~WRECK_ACTIVE',' nop')),('duplicate_slot',source.replace(' cmp eax,[rdx]\n je .invalid',' cmp eax,[rdx]\n nop'))]:
  badlib,_=build(tag,text);badlib.wreck_remote_reset()
  if tag=='stale_tick':
   receive(record(seq=1),tick=10,expected=1,which=badlib);assert receive(record(seq=2,birth=0),tick=9,which=badlib)==1
  elif tag=='no_expiry':receive(record(),tick=10,expected=1,which=badlib);badlib.wreck_remote_expire(1800);assert C.c_uint.in_dll(badlib,'net_wreck_count').value==1
  else:assert receive(record()+record(),which=badlib)==2
  negatives.append(tag)
 print(json.dumps({'suite':'wreck-remote-lifecycle','passed':True,'calls':production_calls,'slots':1024,'malformed_atomic_packets':len(bad)+2,'whole_packet_conflict_atomic':True,'expiry_retirement_reuse_no_revival':True,'modular_wrap':True,'ABI_preserved':True,'negative_controls':negatives,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Actual dedicated remote cache/packet validation/clock lifecycle; real transport, server stream and client graphics acceptance separate'}))
