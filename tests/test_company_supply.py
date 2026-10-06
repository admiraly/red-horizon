#!/usr/bin/env python3
"""Independent read-only supply snapshot on actual assembly company authority."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,tempfile,sys
root=pathlib.Path(__file__).resolve().parents[1]
core_root=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else pathlib.Path('/mnt/titan_nv3/projects/red-horizon')
source=core_root/'build/libsim.so'
with tempfile.TemporaryDirectory(prefix='rh-company-supply-')as directory:
 td=pathlib.Path(directory);base=td/'libsim.so';base.write_bytes(source.read_bytes());obj=td/'supply.o';lib=td/'supply.so'
 subprocess.run([os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm'),'-f','elf64','-I',str(root)+'/',str(root/'src/ai/company_supply.asm'),'-o',str(obj)],check=True)
 objects=[];core_hashes={}
 for folder in ('sim','nav','ai','game'):
  for src in (core_root/'src'/folder).glob('*.asm'):
   if src.name=='company_supply.asm':continue
   name=str(src.relative_to(core_root)).replace('/','_')+'.o';data=(core_root/'build'/name).read_bytes();frozen=td/name;frozen.write_bytes(data);objects.append(str(frozen));core_hashes[name]=hashlib.sha256(data).hexdigest()
 probe=td/'terrain_probe.o';probe.write_bytes((core_root/'build/terrain_probe.o').read_bytes())
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(lib),str(obj),*objects,str(probe),'-lm'],check=True)
 l=C.CDLL(str(lib));l.sim_checksum.restype=C.c_uint64;l.company_supply_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint];l.company_supply_report.restype=C.c_int
 entities=(C.c_uint*262144).in_dll(l,'sim_entities');weapons=(C.c_uint*262144).in_dll(l,'infantry_weapons');players=(C.c_uint*64).in_dll(l,'sim_players');assignments=(C.c_uint*16).in_dll(l,'player_companies');controls=(C.c_uint*12288).in_dll(l,'company_controls');count=C.c_uint.in_dll(l,'sim_count')
 assert l.sim_init(32,73)==0 and l.player_join(0,1)==0
 def report(player=0,size=40,expected=0):
  buf=(C.c_ubyte*64)(*([0xa7]*64));before=l.sim_checksum();rc=l.company_supply_report(player,C.byref(buf,8),size);assert rc==expected and l.sim_checksum()==before
  if expected:assert bytes(buf)==bytes([0xa7]*64);return
  assert bytes(buf[:8])==bytes([0xa7]*8) and bytes(buf[48:])==bytes([0xa7]*16)
  return struct.unpack('<10I',bytes(buf[8:48]))
 initial=report();key=assignments[0];generation=players[15]
 assert initial==(0,generation,key,4,0,0,480,0,0,0),initial
 # Independently declared counters, not a renewed gameplay encounter.
 weapons[1*8+1]=20;weapons[1*8+2]=0;weapons[1*8+4]=100
 weapons[4*8+1]=0;weapons[4*8+2]=0;weapons[4*8+4]=120
 weapons[7*8]=2
 # These unrelated empty stocks must never enter this owner's totals.
 for i in (0,16):weapons[i*8+1]=0;weapons[i*8+2]=0;weapons[i*8+4]=120
 mixed=report();assert mixed==(0,generation,key,4,2,1,140,1,0,0),mixed
 # Death and front membership change exclude the actual body, not just ammo.
 entities[7*8+2]=0;entities[1*8+5]=0
 narrowed=report();assert narrowed==(0,generation,key,2,1,1,120,0,0,0),narrowed
 # Downed connected primary owner retains useful deployment-interval report.
 players[5]=0;assert report()==narrowed
 for ident in (4,0xffffffff):report(ident,expected=-1)
 for size in (0,39):report(size=size,expected=-1)
 before=l.sim_checksum();assert l.company_supply_report(0,None,40)==-1 and l.sim_checksum()==before
 # Both directions of the body-generation lease and actual player front gate.
 for array,index in ((assignments,1),(controls,key*8+1),(players,10)):
  saved=array[index];array[index]=saved+1;report(expected=-1);array[index]=saved
 assert l.player_leave(0)==0;report(expected=-1)
 # Malformed count rejects before source iteration/output writes. No unsafe
 # checksum call while count itself is deliberately out of bounds.
 saved=count.value;count.value=32769;buf=(C.c_ubyte*40)(*([0xb9]*40))
 assert l.company_supply_report(0,buf,40)==-1 and bytes(buf)==bytes([0xb9]*40);count.value=saved
 print(json.dumps({'suite':'company-supply-report-prerequisite','passed':True,'initial':initial,'mixed_low_empty_unknown':mixed,'death_front_exclusions':narrowed,'read_only_authority':True,'owner_down_report_preserved':True,'invalid_lease_front_count_output_atomic':True,'output_guard_bytes_preserved':True,'core_reference_library_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'actual_copied_core_objects_sha256':core_hashes,'module_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'limits':['Actual assembly company/body/stock authority with independent static query fixtures.','No network/HUD/depot presentation, ABI probe, scale or supply-aware route acceptance yet; not integrated.']}))
