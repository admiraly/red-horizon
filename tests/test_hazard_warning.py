#!/usr/bin/env python3
"""Development-only wrapper probe. Stub perception; no production hazard claim."""
import argparse, ctypes as C, json, math, pathlib, struct, subprocess, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
STUB='''default rel
global sim_players,hazard_query,query_calls,query_eye,query_side,query_result,query_values
section .data
query_result: dd 0
query_values: dd 100.,200.,12.,60.
section .bss
sim_players: resb 256
query_calls: resd 1
query_side: resd 1
query_eye: resd 3
section .text
hazard_query:
 inc dword [query_calls]
 mov [query_side],edi
 movss [query_eye],xmm0
 movss [query_eye+4],xmm1
 movss [query_eye+8],xmm2
 mov eax,[query_result]
 movss xmm0,[query_values]
 movss xmm1,[query_values+4]
 movss xmm2,[query_values+8]
 movss xmm3,[query_values+12]
 xor edx,edx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
def run(nasm):
 with tempfile.TemporaryDirectory(prefix='rh-hazard-warning-') as tmp:
  tmp=pathlib.Path(tmp);stub=tmp/'stub.asm';stub.write_text(STUB)
  objects=[]
  for i,source in enumerate([ROOT/'src/render/hazard_warning.asm',stub]):
   obj=tmp/f'{i}.o';objects.append(str(obj))
   subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(source),'-o',str(obj)],check=True)
  so=tmp/'probe.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-lm','-o',str(so)],check=True)
  lib=C.CDLL(str(so));fn=lib.hazard_warning_update
  fn.argtypes=[C.c_uint32,*([C.c_float]*4)];fn.restype=None
  players=(C.c_ubyte*256).in_dll(lib,'sim_players')
  uniform=(C.c_float*4).in_dll(lib,'hazard_warning_uniform')
  calls=C.c_uint32.in_dll(lib,'query_calls');frames=C.c_uint64.in_dll(lib,'hazard_warning_frames')
  eye=(C.c_float*3).in_dll(lib,'query_eye');side=C.c_uint32.in_dll(lib,'query_side')
  result=C.c_int32.in_dll(lib,'query_result');values=(C.c_float*4).in_dll(lib,'query_values')
  def player(slot,connected=1,hp=100):
   struct.pack_into('i',players,slot*64+20,hp);struct.pack_into('I',players,slot*64+44,connected)
  def check_reset(slot=0,x=10.,y=23.,z=20.,yaw=0.,query=False):
   before=calls.value;old=frames.value;fn(slot,x,y,z,yaw)
   assert list(uniform)==[0.,0.,0.,0.]
   assert frames.value==old
   assert calls.value==before+int(query)
  player(0);snapshot=bytes(players)
  fn(0,10.,23.,20.,0.)
  assert list(eye)==[10.,23.,20.] and side.value==0
  assert uniform[0]==1 and abs(uniform[1]-math.atan2(90.,180.)/math.pi)<1e-6
  assert list(uniform[2:])==[2.,12.] and frames.value==1
  # Compass directions use actual camera convention, including behind the eye.
  for dx,dz,yaw,expected in [(0,10,0,0),(10,0,0,.5),(-10,0,0,-.5),(0,-10,0,1),(10,0,math.pi/2,0),(0,10,math.pi/2,-.5)]:
   values[0]=10+dx;values[1]=20+dz;fn(0,10.,23.,20.,yaw)
   assert abs(uniform[1]-expected)<1e-6,(dx,dz,yaw,list(uniform))
  values[2]=9999;values[3]=9999;fn(0,10.,23.,20.,1e20)
  assert uniform[0]==1 and -1<=uniform[1]<=1 and list(uniform[2:])==[4.,512.]
  result.value=-1;check_reset(query=True);result.value=0
  for index in range(4):
   old=values[index];values[index]=float('nan');check_reset(query=True);values[index]=old
   values[index]=float('inf');check_reset(query=True);values[index]=old
  values[2]=0.;check_reset(query=True);values[2]=12.
  values[3]=-1.;check_reset(query=True);values[3]=0.
  fn(0,10.,23.,20.,0);assert uniform[0]==1 and uniform[2]==0.
  for index in range(4):
   args=[10.,23.,20.,0.];args[index]=float('nan');check_reset(x=args[0],y=args[1],z=args[2],yaw=args[3])
   args[index]=float('inf');check_reset(x=args[0],y=args[1],z=args[2],yaw=args[3])
  check_reset(slot=4);check_reset(slot=0xffffffff)
  player(0,connected=0);check_reset();player(0,connected=2);check_reset()
  for hp in [0,-1,-2147483648]:
   player(0,hp=hp);check_reset()
  player(0);player(3);before=bytes(players)
  fn(3,10.,23.,20.,0.)
  assert bytes(players)==before,'wrapper must not mutate player authority'
  assert uniform[0]==1 and frames.value>1
  player(3,connected=0);check_reset(slot=3)
  player(3,hp=0);player(0)
  assert bytes(players[:64])==snapshot[:64]
  return {'suite':'hazard-warning','passed':True,'scope':'assembled HUD adapter with perception stub; production LOS/hazards/GL not exercised','checks':['actual eye coordinates and allied-side query','camera-relative cardinal and behind bearing','finite validation','ETA/radius bounds','death/disconnect/expiry reset','slot bounds','player authority unchanged','success-only cosmetic frame counter']}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--nasm',default='nasm');args=parser.parse_args()
 print(json.dumps(run(args.nasm)))
