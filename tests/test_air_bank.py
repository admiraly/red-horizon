#!/usr/bin/env python3
"""Independent coordinated-turn equation, roll continuity, invalid inputs and ABI."""
import ctypes as C,hashlib,json,math,os,pathlib,random,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm'))
f32=lambda x:C.c_float(x).value

def expected(role,emergency,error,speed,bank):
 yaw=max(-(.025,.04)[role],min((.025,.04)[role],error*.08))
 limit=((1.35,1.45),(1.4,1.45))[emergency][role]
 desired=max(-limit,min(limit,-math.atan2(speed*yaw,.0109)))
 roll=(.06,.1)[role]
 new=bank+max(-roll,min(roll,desired-bank))
 return -.0109*math.tan(new)/speed,new

def load(path):
 lib=C.CDLL(str(path));fn=lib.probe_air_bank
 fn.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p];fn.restype=C.c_int
 return fn

def observe(fn,args):
 output=(C.c_float*2)();regs=(C.c_uint64*7)();rc=fn(*args,output,regs)
 assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,),tuple(regs)
 return rc,tuple(output)

with tempfile.TemporaryDirectory(prefix='rh-bank-oracle-') as temporary:
 td=pathlib.Path(temporary);wrapper=td/'wrapper.o'
 subprocess.run([nasm,'-f','elf64',str(root/'tests/probe_air_bank.asm'),'-o',str(wrapper)],check=True)
 source=(root/'src/ai/air_bank.asm').read_text()
 def compile_variant(name,text):
  asm=td/(name+'.asm');obj=td/(name+'.o');so=td/(name+'.so');asm.write_text(text)
  subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(asm),'-o',str(obj)],check=True)
  subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),str(obj),str(wrapper),'-lm'],check=True)
  return load(so)
 fn=compile_variant('production',source);rng=random.Random(72931);cases=[]
 for role in (0,1):
  for emergency in (0,1):
   for error,speed,bank in [(0,5,0),(1,7,0),(-1,5,0),(0,6,1.4),(0,6,-1.4)]+[(rng.uniform(-math.pi,math.pi),rng.uniform(5,7),rng.uniform(-1.45,1.45)) for _ in range(500)]:
    args=(role,emergency,*map(f32,(error,speed,bank)));rc,out=observe(fn,args);assert rc==0
    oracle=expected(*args)
    assert abs(out[0]-oracle[0])<2e-7 and abs(out[1]-oracle[1])<5e-7,(args,out,oracle)
    assert abs(out[1]-args[4])<=(.060001,.100001)[role]
    cases.append(args)
 invalid=[(2,0,0,6,0),(0,2,0,6,0)]
 for field,values in [(2,[math.nan,math.inf,-math.inf,3.2,-3.2]),(3,[math.nan,math.inf,-math.inf,4.99,7.01]),(4,[math.nan,math.inf,-math.inf,1.46,-1.46])]:
  for value in values:
   args=[0,0,0,6,0];args[field]=value;invalid.append(tuple(args))
 for args in invalid:
  rc,out=observe(fn,args);assert rc==-1 and out==(0.,0.)
 # Continuous roll reversal must initially retain the old turn direction.
 rc,(yaw,bank)=observe(fn,(1,0,1.,7.,1.));assert bank>0 and yaw<0
 # Actual assembled causal controls, each rejected by the same equation oracle.
 controls={}
 for name,changed in [('wrong_sign',source.replace('mulss xmm1,[negative]\n divss xmm1,[rsp+4]','divss xmm1,[rsp+4]',1)),('instant_roll',source.replace('subss xmm0,[rsp+8]\n lea rcx,[roll]','subss xmm0,[rsp+8]\n lea rcx,[emergency_bank]',1))]:
  assert changed!=source;bad=compile_variant(name,changed);misses=0
  for args in cases:
   rc,out=observe(bad,args);oracle=expected(*args)
   misses+=rc!=0 or abs(out[0]-oracle[0])>=2e-7 or abs(out[1]-oracle[1])>=5e-7
  assert misses>100,(name,misses);controls[name]={'mismatches':misses,'source_sha256':hashlib.sha256(changed.encode()).hexdigest()}
 print(json.dumps({'suite':'air-bank','passed':True,'equation_cases':len(cases),'invalid_cases':len(invalid),'assembled_negative_controls':controls,'ABI_preserved':True,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'limits':['Pure flight helper; does not establish bombing, air combat, boundary trajectories, graphics or performance.']}))
