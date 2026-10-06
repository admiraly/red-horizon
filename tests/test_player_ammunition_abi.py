#!/usr/bin/env python3
"""SysV ABI and read-only/invalid preservation for actual player ammo helpers."""
import ctypes as C,hashlib,json,os,pathlib,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];source=pathlib.Path(sys.argv[1]).resolve();calls=0
with tempfile.TemporaryDirectory(prefix='rh-player-ammo-abi-')as directory:
 folder=pathlib.Path(directory);core=folder/'core.so';core.write_bytes(source.read_bytes());l=C.CDLL(str(core),mode=C.RTLD_GLOBAL);l.sim_checksum.restype=C.c_uint64
 obj=folder/'probe.o';subprocess.run([os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm')),'-f','elf64',str(root/'tests/probe_player_ammunition.asm'),'-o',str(obj)],check=True);probe=folder/'probe.so';subprocess.run(['gcc','-shared','-o',str(probe),str(obj)],check=True);p=C.CDLL(str(probe));p.probe_player_ammunition.argtypes=[C.c_uint,C.c_uint,C.c_void_p,C.c_void_p];p.probe_player_ammunition.restype=C.c_int
 assert l.sim_init(2,73)==0 and l.player_join(0,1)==0
 for ident in (0,4,0xffffffff):
  for entry in range(7):
   out=(C.c_ubyte*56)(*([0xa7]*56));regs=(C.c_uint64*7)();before=l.sim_checksum();rc=p.probe_player_ammunition(ident,entry,C.byref(out,8),regs);calls+=1
   assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
   assert bytes(out[:8])+bytes(out[48:])==bytes([0xa7]*16)
   if ident!=0:assert rc==-1 and l.sim_checksum()==before and bytes(out)==bytes([0xa7]*56)
   elif entry in (0,3,4,5,6):assert l.sim_checksum()==before
   if entry!=5 or ident!=0:assert bytes(out)==bytes([0xa7]*56)
 print(json.dumps({'suite':'player-ammunition-ABI','passed':True,'entry_points':7,'calls':calls,'six_nonvolatile_registers_and_stack_preserved':True,'readonly_invalid_hash_and_output_guards':True,'core_sha256':hashlib.sha256(core.read_bytes()).hexdigest(),'limits':['Development ABI wrapper; runtime input/tick, UDP and graphics outcomes are separate.']}))
