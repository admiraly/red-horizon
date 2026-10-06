#!/usr/bin/env python3
"""Independent analytical response and malformed-state ABI proof; development only."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
OMEGA=(20.,16.,18.);PLIM=(2000.,math.pi/2,math.pi/2);VLIM=(200.,8.,8.)
def f(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def state(p=(0,0,0),v=(0,0,0),gen=7,kind=1,time=0,flags=1,padding=(0x12345678,0xabcdef12)):
 return C.create_string_buffer(struct.pack('<6f2If3I',*p,*v,gen,kind,time,flags,*padding)+b'\xa5'*16,64)
def unpack(s):return struct.unpack('<6f2If3I',s.raw[:48])
def oracle(p,v,target,dt):
 out=[];vel=[]
 for a,b,t,w,pl,vl in zip(p,v,target,OMEGA,PLIM,VLIM):
  q=a-t;k=b+w*q;e=math.exp(-w*dt)
  out.append(max(-f(pl),min(f(pl),t+(q+k*dt)*e)))
  vel.append(max(-vl,min(vl,(b-w*k*dt)*e)))
 return out+vel
with tempfile.TemporaryDirectory(prefix='rh-suspension-') as name:
 td=pathlib.Path(name)
 source=(ROOT/'src/render/suspension.asm').read_text()
 def build(tag,text=source):
  src=td/(tag+'.asm');src.write_text(text);objs=[]
  for i,s in enumerate((src,ROOT/'tests/probe_suspension.asm')):
   obj=td/f'{tag}{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(s),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-Wl,--wrap=expf',*objs,'-lm','-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.probe_suspension.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_float];lib.probe_suspension.restype=C.c_int
  return lib,so
 lib,so=build('suspension');calls=0;invalid=0;maxerr=[0.]*6
 def call(lib,s,t,dt,gen=7,kind=1,cap=48,expected=0):
  global calls
  before=s.raw;target=t if isinstance(t,(C.Array,C.c_void_p)) else (C.c_float*3)(*t);target_before=bytes(target) if isinstance(target,C.Array) else None
  regs=(C.c_uint64*6)();ec=C.c_uint64.in_dll(lib,'suspension_exp_calls');prior=ec.value
  ret=lib.probe_suspension(s,target,gen,kind,cap,regs,dt)
  assert ret==expected,(ret,expected,unpack(s),dt)
  assert tuple(regs)==tuple(0x123401+i for i in range(6)),'nonvolatile/stack corruption'
  assert C.c_uint64.in_dll(lib,'suspension_alignment_errors').value==0,'unaligned expf call'
  assert s.raw[48:]==before[48:],'state capacity overrun'
  if target_before is not None:assert bytes(target)==target_before,'target modified'
  if expected==-1:assert s.raw==before,'invalid modified state';assert ec.value==prior,'invalid called expf'
  calls+=1
  return before,ec.value-prior
 def verify(p,v,t,dt,time=0):
  s=state(p,v,time=time);initial=unpack(s);t=list(map(f,t));dt=f(dt);before,n=call(lib,s,t,dt)
  actual=unpack(s);want=oracle(initial[:3],initial[3:6],t,dt)
  if dt==0:assert s.raw==before and n==0;return
  assert n==3
  for i,(a,b) in enumerate(zip(actual[:6],want)):
   maxerr[i]=max(maxerr[i],abs(a-b));assert math.isclose(a,b,rel_tol=4e-6,abs_tol=5e-4 if i in (0,3) else 2e-6),(i,a,b)
  assert actual[6:8]==(7,1) and actual[9:]==(1,0,0)
  assert abs(actual[8]-min(86400,f(initial[8]+dt)))==0
  assert all(abs(actual[i])<=f(PLIM[i]) for i in range(3)) and all(abs(actual[i+3])<=VLIM[i] for i in range(3))
 rng=random.Random(382921)
 for _ in range(2500):
  p=[rng.uniform(-lim,lim) for lim in PLIM];v=[rng.uniform(-lim,lim) for lim in VLIM];t=[rng.uniform(-lim,lim) for lim in PLIM]
  verify(p,v,t,rng.uniform(0,.1),rng.uniform(0,86400))
 for dt in (0,-0.,.000001,1/144,1/60,1/30,.1):
  for sign in (-1,1):verify([sign*x for x in PLIM],[sign*x for x in VLIM],[-sign*x for x in PLIM],dt,86400)
 # Outward initial velocity at the position boundary must clamp after evaluation.
 for sign in (-1,1):verify([sign*x for x in PLIM],[sign*x for x in VLIM],[sign*x for x in PLIM],.1)
 # Closed-form step response at multiple elapsed times without active clamps.
 for dt in (1/144,1/60,1/30,.1):
  s=state();target=(1.,.1,-.1);elapsed=0.
  for _ in range(round(2/dt)):
   call(lib,s,target,dt);elapsed+=f(dt)
   actual=unpack(s)
   for i,(t,w) in enumerate(zip(target,OMEGA)):
    expected=t*(1-(1+w*elapsed)*math.exp(-w*elapsed));ev=t*w*w*elapsed*math.exp(-w*elapsed)
    assert abs(actual[i]-expected)<2e-6 and abs(actual[i+3]-ev)<8e-6,'analytical step response'
  assert max(abs(a-b) for a,b in zip(unpack(s)[:3],target))<2e-6,'did not settle'
 # Same elapsed duration partitions: valid only where no bounding clamp fires.
 final=[]
 for count in (10,20,30,60,120,144):
  s=state((.3,.02,-.04),(.1,-.05,.03));target=(1.,.1,-.1)
  for _ in range(count):call(lib,s,target,1/count)
  final.append(unpack(s)[:6])
 partition=max(abs(a-b) for row in final for a,b in zip(row,final[0]));assert partition<3e-6,partition
 # Stale/inactive lifecycle ignores poisoned prior dynamic fields, canonicalizes padding.
 for flags,oldgen,oldkind in ((0,7,1),(1,6,1),(1,7,2)):
  s=state((math.nan,math.inf,-math.inf),(math.nan,math.inf,-math.inf),oldgen,oldkind,math.nan,flags)
  _,n=call(lib,s,(12,.4,-.3),0);assert n==0
  assert unpack(s)==(12,f(.4),f(-.3),0,0,0,7,1,0,1,0,0)
 # Alias target to positions, and separately to overlapping velocity storage.
 for off in (0,12):
  s=state((10,.2,-.1),(.2,.1,-.1));vals=unpack(s);t=vals[off//4:off//4+3]
  reference=state(vals[:3],vals[3:6]);call(lib,reference,t,.05)
  pointer=C.c_void_p(C.addressof(s)+off);call(lib,s,pointer,.05);assert s.raw==reference.raw,'overlap mishandled'
 s=state((10,.2,-.1),(.2,.1,-.1));before=s.raw;call(lib,s,C.c_void_p(C.addressof(s)),0);assert s.raw==before
 # Complete byte preservation for bad args and every live scalar bound.
 cases=[]
 for dt in (math.nan,math.inf,-math.inf,-.01,.10001):cases.append((state(),(1,0,0),dt,7,1,48))
 for gen in (0,):cases.append((state(),(1,0,0),.05,gen,1,48))
 for kind in (0,3,0xffffffff):cases.append((state(),(1,0,0),.05,7,kind,48))
 for cap in (0,1,47):cases.append((state(),(1,0,0),.05,7,1,cap))
 for flags in (2,0xffffffff):cases.append((state(flags=flags),(1,0,0),.05,7,1,48))
 for i,lim in enumerate(PLIM):
  for bad in (math.nan,math.inf,-math.inf,lim*1.001,-lim*1.001):
   t=[0,0,0];t[i]=bad;cases.append((state(),t,.05,7,1,48))
 for i,lim in enumerate(PLIM+VLIM+(86400.,)):
  for bad in (math.nan,math.inf,-math.inf,lim*1.001,-lim*1.001):
   p=[0,0,0];v=[0,0,0];time=0
   if i<3:p[i]=bad
   elif i<6:v[i-3]=bad
   else:time=bad
   cases.append((state(p,v,time=time),(1,0,0),0 if len(cases)%2 else .05,7,1,48))
 for s,t,dt,gen,kind,cap in cases:call(lib,s,t,dt,gen,kind,cap,-1);invalid+=1
 regs=(C.c_uint64*6)();s=state();before=s.raw
 for st,tar in ((None,(C.c_float*3)(0,0,0)),(s,None)):
  assert lib.probe_suspension(st,tar,7,1,48,regs,.05)==-1
  assert s.raw==before;invalid+=1
 # Actual assembly causal negatives must fail independent mathematical/state gates.
 mutations={'linear_step':source.replace('call expf wrt ..plt','movss xmm0,[max_dt]'), 'wrong_velocity':source.replace('subss xmm1,xmm2','addss xmm1,xmm2'),'stale_reads':source.replace('cmp dword [rdi+SUSPENSION_FLAGS],0\n je .initialize','cmp dword [rdi+SUSPENSION_FLAGS],0\n nop')};neg=[]
 for tag,text in mutations.items():
  assert text!=source;bad,_=build(tag,text)
  try:
   if tag=='stale_reads':call(bad,state((math.nan,0,0),flags=0),(1,0,0),.05)
   else:
    s=state((1,.1,-.1),(.1,.2,-.3));call(bad,s,(0,0,0),.05);want=oracle((1,f(.1),f(-.1)),(f(.1),f(.2),f(-.3)),(0,0,0),f(.05));assert max(abs(a-b) for a,b in zip(unpack(s)[:6],want))<2e-6
  except AssertionError:neg.append(tag)
  else:raise AssertionError('fault escaped '+tag)
 print(json.dumps({'suspension_calls':calls,'invalid_cases':invalid,'maximum_single_step_error':maxerr,'maximum_partition_difference':partition,'causal_negatives':neg,'alignment_errors':C.c_uint64.in_dll(lib,'suspension_alignment_errors').value,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'isolated cosmetic response; no renderer/terrain contact correction or physical/game suspension acceptance'},sort_keys=True))
