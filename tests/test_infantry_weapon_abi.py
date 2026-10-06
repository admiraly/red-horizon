#!/usr/bin/env python3
"""NASM public-entry preserved registers, alignment and invalid atomic gates."""
import ctypes as C,hashlib,json,os,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-infantry-abi-')as directory:
 td=pathlib.Path(directory);probe=td/'probe.o';terrain=td/'terrain.o';so=td/'weapon.so'
 for source,obj in [('tests/probe_infantry_weapon.asm',probe),('tests/terrain_probe.asm',terrain)]:subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(root/source),'-o',str(obj)],check=True)
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o'))for folder in ('sim','nav','ai','game')for p in (root/'src'/folder).glob('*.asm')]
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*objects,str(probe),str(terrain),'-lm'],check=True)
 l=C.CDLL(str(so));l.sim_checksum.restype=C.c_uint64
 def probe_call(which,actor):
  output=(C.c_uint64*7)();rc=l.probe_infantry_weapon(which,actor,output)
  assert tuple(output)==tuple(0x123401+j for j in range(6))+(0,),tuple(output)
  return rc
 assert l.sim_init(32,3)==0
 assert probe_call(0,0)==0 and probe_call(1,0)==0 and probe_call(2,0)==0 and probe_call(3,0)==0 and probe_call(4,0)==0
 count=C.c_uint.in_dll(l,'sim_count');count.value=32769
 for which in (0,1,2,3,4):
  before=l.sim_checksum();assert probe_call(which,0)==-1 and l.sim_checksum()==before
 count.value=32
 for actor in (12,14,15,32,32768,0xffffffff):
  before=l.sim_checksum();assert probe_call(2,actor)==-1 and l.sim_checksum()==before
 print(json.dumps({'suite':'infantry-weapon-ABI','passed':True,'entry_points':5,'invalid_atomic_calls':11,'six_nonvolatile_registers_preserved':True,'aligned_call_frames':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Isolated CPU ABI and public gate proof; physical reload/combat verified separately.']}))
