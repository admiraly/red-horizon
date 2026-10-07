#!/usr/bin/env python3
"""Independent angular/vertical confidence-guidance oracle and NASM ABI."""
import ctypes as C,hashlib,json,math,os,pathlib,random,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
with tempfile.TemporaryDirectory(prefix='rh-air-pursuit-') as folder:
 td=pathlib.Path(folder);objects=[]
 for name in ('src/ai/air_pursuit.asm','tests/probe_air_pursuit.asm'):
  obj=td/(pathlib.Path(name).name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(R/name),'-o',str(obj)],check=True);objects.append(obj)
 so=td/'pursuit.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objects)],check=True)
 l=C.CDLL(str(so));l.probe_air_pursuit.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
 def call(kind,mission,pursuit,confidence):
  out=(C.c_float*3)(123,789,456);abi=(C.c_uint64*7)();rc=l.probe_air_pursuit(kind,mission,pursuit,confidence,C.byref(out,4),abi)
  assert out[0]==123 and out[2]==456 and tuple(abi)==tuple(0x123401+i for i in range(6))+(0,)
  return rc,out[1]
 rng=random.Random(794732);maximum=0;counts=[0,0]
 for kind in (0,1):
  limit=(math.pi,.5)[kind]
  for i in range(5000):
   mission,pursuit,weight=(C.c_float(v).value for v in (rng.uniform(-limit,limit),rng.uniform(-limit,limit),rng.random()))
   rc,out=call(kind,mission,pursuit,weight);assert rc==0
   if kind==0:
    # Complex rotation gives an independent shortest-arc orientation oracle.
    delta=math.atan2(math.sin(pursuit-mission),math.cos(pursuit-mission));expected=math.atan2(math.sin(mission+weight*delta),math.cos(mission+weight*delta));error=abs(math.atan2(math.sin(out-expected),math.cos(out-expected)))
   else:expected=(1-weight)*mission+weight*pursuit;error=abs(out-expected)
   maximum=max(maximum,error);assert error<1e-6,(kind,mission,pursuit,weight,out,expected,error);counts[kind]+=1
 # Exact endpoints and declared deterministic antipodal tie policy.
 pi=C.c_float(math.pi).value
 for kind,limit in ((0,pi),(1,.5)):
  for mission,pursuit in ((-limit,limit),(limit,-limit),(-limit,0),(0,limit)):
   assert call(kind,mission,pursuit,0)==(0,mission)
   assert call(kind,mission,pursuit,1)==(0,pursuit)
 assert call(0,0,pi,.5)==(0,pi*.5)
 assert call(0,0,-pi,.5)==(0,-pi*.5)
 seam=call(0,3.1,-3.1,.5)[1];assert abs(abs(seam)-math.pi)<1e-6
 invalid=[(2,0,0,.5),(0xffffffff,0,0,.5),(0,3.2,0,.5),(0,0,-3.2,.5),(1,.51,0,.5),(1,0,-.51,.5),(0,0,0,-.01),(1,0,0,1.01)]
 for kind in (0,1):
  for index in (1,2,3):
   for value in (math.nan,math.inf,-math.inf):
    row=[kind,0,0,.5];row[index]=value;invalid.append(row)
 for row in invalid:assert call(*row)==(-1,0),row
 print(json.dumps({'suite':'air-confidence-guidance','passed':True,'independent_heading_cases':counts[0],'independent_vertical_cases':counts[1],'invalid_ABI_cases':len(invalid),'maximum_oracle_error':maximum,'exact_endpoints_antipodal_ties_and_seam':True,'nonvolatile_registers_stack_and_output_guards':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Pure guidance interpolation math; physical pursuit, tactics, scale, graphics and network are separate checks.'}))
