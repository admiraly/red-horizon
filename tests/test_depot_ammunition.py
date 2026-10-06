#!/usr/bin/env python3
"""Isolated finite-store prerequisite; no claim of integrated actor resupply."""
import ctypes as C,json,os,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
with tempfile.TemporaryDirectory(prefix='rh-depot-')as d:
 d=pathlib.Path(d);(d/'fixture.asm').write_text('section .bss align=64\nglobal sim_sites\nsim_sites: resb 384\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
 for src,out in [(root/'src/sim/depot_ammunition.asm',d/'depot.o'),(d/'fixture.asm',d/'fixture.o')]:subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(src),'-o',str(out)],check=True)
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(d/'depot.so'),str(d/'depot.o'),str(d/'fixture.o')],check=True)
 l=C.CDLL(str(d/'depot.so'));sites=(C.c_uint*96).in_dll(l,'sim_sites');stocks=(C.c_uint*48).in_dll(l,'depot_ammunition')
 l.depot_ammunition_take.argtypes=[C.c_uint]*3;l.depot_ammunition_take.restype=C.c_int
 for i in range(12):sites[i*8+2]=i%2;sites[i*8+4]=1;sites[i*8+5]=1;sites[i*8+6]=1000
 assert l.depot_ammunition_init()==0
 assert sum(stocks[i*4]for i in range(12))==144000
 def take(i,side,n):
  before=bytes(stocks);r=l.depot_ammunition_take(i,side,n)
  if r<=0:assert bytes(stocks)==before
  return r
 for i in range(12):
  assert take(i,1-i%2,90)==0
  for offset,value in ((5,0),(6,0),(7,4),(4,2)):
   old=sites[i*8+offset];sites[i*8+offset]=value;assert take(i,i%2,90)==0;sites[i*8+offset]=old
  got=[take(i,i%2,90)for _ in range(134)]
  assert got==[90]*133+[30] and take(i,i%2,90)==0
  assert tuple(stocks[i*4:i*4+4])==(0,12000,12000,0)
  sites[i*8+2]=1-i%2;assert take(i,1-i%2,90)==0,'capture fabricated inventory'
 assert sum(stocks[i*4+1]for i in range(12))==144000
 for args in ((12,0,1),(0xffffffff,0,1),(0,2,1),(0,0,0),(0,0,91),(0,0,0xffffffff)):assert take(*args)==-1
 for offset,value in ((0,12001),(1,12001),(2,12001),(3,1),(0,1)):
  old=stocks[offset];stocks[offset]=value;assert take(0,1,90)==-1;stocks[offset]=old
 print(json.dumps({'suite':'depot-finite-store-prerequisite','passed':True,'declared_stores':12,'initial_rounds':144000,'successful_debits':1608,'cut_destroy_contest_role_owner_gates':True,'capture_does_not_refill':True,'malformed_request_and_stock_atomic':True,'scope':'Isolated module with declared sites; actor proximity/credit, world hooks, replay/ABI/full scale/UDP and supply-aware routes remain unimplemented.'}))
