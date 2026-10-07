#!/usr/bin/env python3
"""Independent vertical-flight oracle, reversal response and actual NASM ABI."""
import ctypes as C,hashlib,json,math,os,pathlib,random,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
with tempfile.TemporaryDirectory(prefix='rh-air-vertical-') as folder:
 td=pathlib.Path(folder);objects=[]
 for name,source in [('flight','src/ai/air_vertical.asm'),('probe','tests/probe_air_vertical.asm')]:
  obj=td/(name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(root/source),'-o',str(obj)],check=True);objects.append(obj)
 so=td/'vertical.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objects),'-lm'],check=True)
 l=C.CDLL(str(so));l.probe_air_vertical.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
 def call(role,wanted,speed,old):
  out=(C.c_float*5)(123,456,789,0,321);regs=(C.c_uint64*7)()
  rc=l.probe_air_vertical(role,wanted,speed,old,C.byref(out,4),regs)
  assert out[0]==123 and out[4]==321,'output guard overwritten'
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,),tuple(regs)
  return rc,tuple(out)[1:4]
 rng=random.Random(714271);maximum_error=0
 cases=[(role,w,s,v) for role in (0,1) for w in (-.5,0,.5) for s in (5,7) for v in (-.5,0,.5)]
 cases += [(rng.randrange(2),rng.uniform(-.5,.5),rng.uniform(5,7),rng.uniform(-.5,.5)) for _ in range(2000)]
 cases += [(role,w,s,v)for role in (0,1)for w in (-.5,0,.5)for s in (1,1.6,2.2,3,4.99)for v in (-.5,0,.5)]
 for role,wanted,speed,old in cases:
  wanted,speed,old=(C.c_float(x).value for x in (wanted,speed,old));rc,(vy,horizontal,pitch)=call(role,wanted,speed,old);assert rc==0
  a=C.c_float((.012,.024)[role]).value;oracle=old+max(-a,min(a,wanted-old));h=math.sqrt(speed*speed-oracle*oracle);p=math.atan2(oracle,h)
  error=max(abs(vy-oracle),abs(horizontal-h),abs(pitch-p));maximum_error=max(maximum_error,error);assert error<2e-6,(role,wanted,speed,old,(vy,horizontal,pitch),(oracle,h,p))
  assert abs(math.hypot(vy,horizontal)-speed)<1e-6
  assert abs(vy-old)<=a+1e-7
  assert min(old,wanted)-1e-7<=vy<=max(old,wanted)+1e-7
 invalid=[(2,0,5,0),(0xffffffff,0,5,0),(0,.50001,5,0),(1,-.50001,7,0),(0,0,0.99,0),(1,0,7.01,0),(0,0,5,.50001),(1,0,7,-.50001)]
 for index in (1,2,3):
  for bad in (float('nan'),float('inf'),-float('inf')):
   args=[0,0,5,0];args[index]=bad;invalid.append(tuple(args))
 for args in invalid:
  rc,out=call(*args);assert rc==-1 and out==(0.,0.,0.),(args,rc,out)
 responses=[]
 for role in (0,1):
  vy=.5;trace=[];speed=(5,7)[role]
  for tick in range(1,101):
   rc,(vy,h,p)=call(role,-.5,speed,vy);assert rc==0;trace.append(vy)
  assert trace[0]>0 and trace[-1]==-.5,'instant reversal or failed response'
  responses.append({'role':role,'first_response_vy':trace[0],'crossed_level_tick':next(i+1 for i,v in enumerate(trace) if v<=0),'reached_descent_tick':next(i+1 for i,v in enumerate(trace) if v==-.5)})
 print(json.dumps({'suite':'air-vertical-motion','passed':True,'independent_math_cases':len(cases),'invalid_ABI_cases':len(invalid),'maximum_error':maximum_error,'reversal_response':responses,'nonvolatile_registers_stack_and_guarded_output':True,'total_airspeed_conserved':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Pure bounded vertical actuator; level-turn approximation, airborne1..7 speeds and existing0.5m/tick climb envelope remain. No lift/drag, fuel/stall, landing, obstacle avoidance, flight tactics or visual acceptance claim.']}))
