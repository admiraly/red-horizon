#!/usr/bin/env python3
"""Native source-aged emitters: ABI/alias/atomic expiry/source and cap guards."""
import ctypes as C,json,os,pathlib,struct,subprocess,tempfile,math
R=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-plume-')as d:
 td=pathlib.Path(d);objects=[]
 for f in ('src/render/air_crash_plume.asm','src/render/air_crash_instance.asm','src/sim/air_crash_remote.asm','tests/probe_air_crash_plume.asm'):
  p=td/(pathlib.Path(f).name+'.o');subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','-I',str(R)+'/',str(R/f),'-o',str(p)],check=True);objects.append(str(p))
 # Standalone authority pool only; production updater reads exactly this ABI.
 asm=td/'pool.asm';asm.write_text('section .bss\nglobal sim_air_crashes\nsim_air_crashes: resb 128*96\nsection .note.GNU-stack noalloc noexec nowrite progbits\n');obj=td/'pool.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(asm),'-o',str(obj)],check=True)
 so=td/'plume.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,str(obj),'-o',str(so)],check=True);l=C.CDLL(str(so));l.probe_air_crash_plume.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_uint,C.c_void_p];l.air_crash_plumes_update.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float,C.c_float]
 def record(state=1,seq=1):return struct.pack('<9f7I8I',4000,200,4000,0,-.12,7,.4,.1,-.2,1,0,31,1,5,seq,state,*([0]*8))
 calls=0
 def check(src,tick,expected,alias=None):
  global calls
  buf=C.create_string_buffer(256);C.memmove(C.addressof(buf)+64,src,96);out=C.addressof(buf)+(0 if alias is None else 64+alias);before=C.string_at(out,64);regs=(C.c_uint64*7)();rc=l.probe_air_crash_plume(out,64,C.addressof(buf)+64,96,tick,regs);assert rc==expected and tuple(regs[:6])==tuple(0x123401+i for i in range(6))
  if rc:assert C.string_at(out,64)==before
  else:
   f=struct.unpack('<9f7I8I',src);wanted=struct.pack('<4f3fI8I',*f[:3],(tick-f[13])/30,*f[3:6],f[14],f[15],*([0]*7));assert C.string_at(out,64)==wanted
  if alias is None:assert C.string_at(C.addressof(buf)+64,96)==src
  calls+=1
 for age in range(601):check(record(),5+age,0 if age<600 else 1)
 for offset in range(-63,96):check(record(),35,0,offset)
 check(record(),4,-1)
 for offset,value in ((0,math.nan),(16,math.inf),(32,17.)):
  b=bytearray(record());struct.pack_into('<f',b,offset,value);check(bytes(b),35,-1)
 check(record(state=0),35,-1);check(record(state=2),35,-1)
 local=(C.c_ubyte*(128*96)).in_dll(l,'sim_air_crashes');remote=(C.c_ubyte*(128*96)).in_dll(l,'net_air_crashes');out=(C.c_ubyte*2048).in_dll(l,'air_crash_plume_records');count=C.c_uint.in_dll(l,'air_crash_plume_count')
 for i in range(128):C.memmove(C.addressof(local)+i*96,record(seq=i+1),96)
 before=bytes(local);l.air_crash_plumes_update(0,35,4000,200,4000);assert count.value==32 and bytes(local)==before
 saved=bytes(out);l.air_crash_plumes_update(0,35,4000,200,4000);assert bytes(out)==saved
 l.air_crash_plumes_update(1,35,4000,200,4000);assert count.value==0 and not any(out) and not any(remote)
 l.air_crash_plumes_update(0,605,4000,200,4000);assert count.value==0 and not any(out)
 l.air_crash_plumes_update(0,35,0,200,0);assert count.value==0
 print(json.dumps(dict(suite='air-crash-plume-native',passed=True,calls=calls,alias_cases=159,capacity=32,source_readonly=True,source_selection=True,same_tick_no_restart=True,cosmetic_cutoff_ticks=600,scope='Native kernel/updater only; initial registry fixture, actual GL/public casualty separate.')))
