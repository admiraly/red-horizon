#!/usr/bin/env python3
"""Production CPU caster compaction guards/budget/ABI; declared scratch records."""
import ctypes as C,json,os,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory(prefix='rh-shadow-filter-')as temp:
  folder=pathlib.Path(temp);(folder/'host.asm').write_text('section .data\nglobal hdr_enabled\nhdr_enabled: dd 1\nsection .note.GNU-stack noalloc noexec nowrite progbits\n');objects=[]
  for i,source in enumerate((ROOT/'src/render/sun_shadows.asm',ROOT/'tests/probe_sun_shadows.asm',folder/'host.asm')):
   obj=folder/f'{i}.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(str(obj))
  subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(folder/'native.so'),*objects,'-lGL'],check=True,capture_output=True)
  l=C.CDLL(str(folder/'native.so'));l.sun_shadows_matrix.argtypes=[C.c_float]*3;l.sun_shadows_filter.argtypes=[C.c_void_p,C.c_uint,C.c_uint];l.probe_sun_shadows_filter.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]
  budget=C.c_uint.in_dll(l,'sun_shadow_budget');casters=C.c_uint.in_dll(l,'sun_shadow_casters');pass_=C.c_uint.in_dll(l,'sun_shadow_pass');pass_.value=1;assert l.sun_shadows_matrix(2000,100,2000)==0
  class Scratch(C.Structure):_fields_=[('prefix',C.c_ubyte*32),('records',(C.c_float*16)*256),('suffix',C.c_ubyte*32)]
  s=Scratch();C.memset(C.addressof(s),0x55,C.sizeof(s));r=s.records;pointer=C.addressof(r);guard=bytes(s.prefix)+bytes(s.suffix);cases=0
  def reset():
   budget.value=1024;casters.value=0;pass_.value=1
   for i in range(256):r[i][:]=[2000,100,2000,0,0,0,0,0,1,1,1,0,float(i),0,0,1]
  reset()
  for batch in range(8):
   assert l.sun_shadows_filter(pointer,256,256)==128;cases+=1
   assert budget.value==1024-(batch+1)*128 and casters.value==(batch+1)*128
   assert bytes(s.prefix)+bytes(s.suffix)==guard
  before=bytes(r);assert l.sun_shadows_filter(pointer,256,256)==0 and bytes(r)==before;cases+=1
  # Original source order, all64 bytes retained, invalid/outside slots skipped.
  reset();r[0][0]=3000;r[1][0]=float('nan');r[2][8]=77;r[3][2]=float('inf');r[4][1]=float('nan');r[5][0]=2640;r[6][0]=2640.01
  expected=[bytes(row)for i,row in enumerate(r[:20])if i not in(0,1,3,4,6)]
  assert l.sun_shadows_filter(pointer,20,256)==len(expected);cases+=1
  assert [bytes(r[i])for i in range(len(expected))]==expected
  assert bytes(s.prefix)+bytes(s.suffix)==guard
  reset();budget.value=17;casters.value=1007;assert l.sun_shadows_filter(pointer,256,256)==17 and budget.value==0 and casters.value==1024;cases+=1
  for p,count,cap in((None,1,1),(pointer,2,1),(pointer,32773,32773),(pointer,1,32773),(pointer,0xffffffff,256),(0xfffffffffffffff0,1,1)):
   reset();before=bytes(s);assert l.sun_shadows_filter(p,count,cap)==-1 and bytes(s)==before and budget.value==1024 and casters.value==0;cases+=1
  for field,value in((budget,1025),(budget,0xffffffff),(casters,1),(casters,1025),(pass_,0)):
   reset();field.value=value;before=(bytes(s),budget.value,casters.value);assert l.sun_shadows_filter(pointer,256,256)==-1 and (bytes(s),budget.value,casters.value)==before;cases+=1
  reset();assert l.sun_shadows_filter(pointer,0,256)==0 and budget.value==1024 and casters.value==0;cases+=1
  observations=(C.c_uint64*6)();assert l.probe_sun_shadows_filter(pointer,256,256,observations)==128;assert list(observations)==list(range(0x123401,0x123407));cases+=1
  print(json.dumps(dict(suite='sun-shadows-native-filter',passed=True,cases=cases,global_cap=1024,batch_cap=128,saturated_batches=8,stable_complete_records=True,invalid_inputs_and_budget_atomic=True,canaries_and_register_stack_ABI=True,scope='Production NASM in-place compaction of private renderer scratch, declared synthetic poses, no GL context/gameplay simulation. No whole-client/shader/performance acceptance.')))
if __name__=='__main__':main()
