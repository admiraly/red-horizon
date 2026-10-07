#!/usr/bin/env python3
"""Independent 3D constant-velocity cannon intercept math and SysV ABI oracle."""
import ctypes as C, hashlib, json, math, os, pathlib, random, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-air-gun-intercept-') as folder:
 td=pathlib.Path(folder);obj=td/'probe.o'
 subprocess.run([os.environ.get('RED_HORIZON_NASM','nasm'),'-f','elf64',str(root/'tests/probe_air_gun.asm'),'-o',str(obj)],check=True)
 objects=[root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o') for d in ('sim','nav','ai','game') for p in sorted((root/'src'/d).glob('*.asm'))]
 so=td/'probe.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objects),str(root/'build/terrain_probe.o'),str(obj),'-lm'],check=True)
 lib=C.CDLL(str(so));lib.sim_checksum.restype=C.c_uint64;assert lib.sim_init(8192,42)==0
 probe=lib.probe_air_gun_intercept;probe.argtypes=[C.c_void_p,C.c_void_p]+[C.c_float]*6;probe.restype=C.c_int
 baseline=lib.sim_checksum();rng=random.Random(4281);maximum=0.;cases=0
 def call(r,v):
  out=(C.c_float*4)(*([-777.]*4));regs=(C.c_uint64*7)();rc=probe(out,regs,*r,*v)
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,)
  assert lib.sim_checksum()==baseline
  if rc:assert tuple(out)==(-777.,)*4
  return rc,tuple(out)
 for _ in range(2000):
  r=tuple(C.c_float(rng.uniform(-450,450)).value for _ in range(3));v=tuple(C.c_float(rng.uniform(-4,4)).value for _ in range(3))
  # Independent double-precision positive root for |r+v*t|=28*t.
  rr=sum(x*x for x in r);rv=sum(x*y for x,y in zip(r,v));vv=sum(x*x for x in v)
  t=(rv+math.sqrt(rv*rv+(784-vv)*rr))/(784-vv);expected=tuple(x+y*t for x,y in zip(r,v))+(t,)
  rc,out=call(r,v);assert rc==0
  error=max(abs(x-y) for x,y in zip(out,expected));maximum=max(maximum,error);assert error<.00015,(r,v,out,expected,error)
  assert abs(math.sqrt(sum(x*x for x in out[:3]))-28*out[3])<.0002
  cases+=1
 invalid=[((0,0,0),(0,0,0)),((2000,0,0),(0,0,0)),((14000,0,0),(0,0,0)),((250,0,0),(9,0,0))]
 for axis in range(6):
  for value in (math.nan,math.inf,-math.inf):
   values=[250.,0.,0.,0.,0.,0.];values[axis]=value;invalid.append((values[:3],values[3:]))
 for r,v in invalid:assert call(r,v)[0]==-1,(r,v)
 # Vertical crossing prediction must change Y and time, not merely X/Z.
 rc,out=call((0,0,250),(0,.5,0));assert rc==0 and out[1]>4 and out[3]>250/28
 print(json.dumps({'suite':'air-gun-intercept','passed':True,'independent_math_cases':cases,'invalid_atomic_output_cases':len(invalid),'maximum_position_or_time_error':maximum,'vertical_crossing':out,'nonvolatile_registers_stack_and_authority_unchanged':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Native constant-velocity prediction math; target manoeuvres after observation are not predicted.'}))
