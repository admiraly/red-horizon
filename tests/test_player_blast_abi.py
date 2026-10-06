#!/usr/bin/env python3
"""Actual blast/damage/motion helpers preserve SysV registers and invalid state."""
import ctypes as C,hashlib,json,os,pathlib,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];source=pathlib.Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='rh-blast-abi-')as directory:
 folder=pathlib.Path(directory);core=folder/'core.so';core.write_bytes(source.read_bytes());l=C.CDLL(str(core),mode=C.RTLD_GLOBAL);l.sim_checksum.restype=C.c_uint64
 obj=folder/'probe.o';subprocess.run([os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm')),'-f','elf64',str(root/'tests/probe_player_blast.asm'),'-o',str(obj)],check=True);probe=folder/'probe.so';subprocess.run(['gcc','-shared','-o',str(probe),str(obj)],check=True);p=C.CDLL(str(probe));p.probe_player_blast.argtypes=[C.c_uint]*4+[C.c_void_p]+[C.c_float]*4;p.probe_player_blast.restype=C.c_int
 assert l.sim_init(32,47)==0 and l.player_join(0,1)==0
 calls=0
 def invoke(entry,ident,amount,side,x=2000.,z=3900.,radius=18.,y=20.):
  global calls
  regs=(C.c_uint64*7)();rc=p.probe_player_blast(entry,ident,amount,side,regs,x,z,radius,y);calls+=1
  assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,),(entry,rc,tuple(regs))
  return rc
 for entry in range(3):
  for ident in (4,0xffffffff):
   before=l.sim_checksum();assert invoke(entry,ident,20,1)==-1 and before==l.sim_checksum()
 for amount in (0,1001,0xffffffff):
  for entry in (0,1):
   before=l.sim_checksum();assert invoke(entry,0,amount,1)==-1 and before==l.sim_checksum()
 before=l.sim_checksum();assert invoke(0,0,20,0)==0 and before==l.sim_checksum()
 before=l.sim_checksum();assert invoke(1,0,20,1)==0 and before==l.sim_checksum()
 assert invoke(0,0,20,1)==1
 assert (C.c_uint*64).in_dll(l,'sim_players')[5]==80
 pose=(C.c_float*64).in_dll(l,'sim_players')
 assert invoke(1,1,20,0,pose[0],pose[2],18.,pose[1])==1
 assert (C.c_uint*64).in_dll(l,'sim_players')[5]==60
 assert invoke(2,0,0,0)==0
 print(json.dumps({'suite':'player-blast-ABI','passed':True,'entry_points':3,'calls':calls,'six_nonvolatile_registers_and_aligned_stack':True,'invalid_and_friendly_full_checksum_unchanged':True,'positive_real_direct_and_blast_damage':[20,20],'core_sha256':hashlib.sha256(core.read_bytes()).hexdigest(),'limits':['Development assembly wrapper; physical ordnance flight, wire and GL outcomes are separate.']}))
