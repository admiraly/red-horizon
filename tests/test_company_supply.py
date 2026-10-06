#!/usr/bin/env python3
"""Independent read-only supply snapshot on actual assembly company authority."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,tempfile,sys
root=pathlib.Path(__file__).resolve().parents[1]
core_root=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else pathlib.Path('/mnt/titan_nv3/projects/red-horizon')
source=core_root/'build/libsim.so'
with tempfile.TemporaryDirectory(prefix='rh-company-supply-')as directory:
 td=pathlib.Path(directory);base=td/'libsim.so';base.write_bytes(source.read_bytes());obj=td/'supply.o';lib=td/'supply.so';abi=td/'abi.o'
 subprocess.run([os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm'),'-f','elf64','-I',str(root)+'/',str(root/'src/ai/company_supply.asm'),'-o',str(obj)],check=True)
 subprocess.run([os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm'),'-f','elf64',str(root/'tests/probe_company_supply.asm'),'-o',str(abi)],check=True)
 objects=[];core_hashes={}
 for folder in ('sim','nav','ai','game'):
  for src in (core_root/'src'/folder).glob('*.asm'):
   if src.name=='company_supply.asm':continue
   name=str(src.relative_to(core_root)).replace('/','_')+'.o';data=(core_root/'build'/name).read_bytes();frozen=td/name;frozen.write_bytes(data);objects.append(str(frozen));core_hashes[name]=hashlib.sha256(data).hexdigest()
 probe=td/'terrain_probe.o';probe.write_bytes((core_root/'build/terrain_probe.o').read_bytes())
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(lib),str(obj),str(abi),*objects,str(probe),'-lm'],check=True)
 l=C.CDLL(str(lib));l.sim_checksum.restype=C.c_uint64;l.company_supply_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint];l.company_supply_report.restype=C.c_int
 l.probe_company_supply.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_void_p];l.probe_company_supply.restype=C.c_int
 abi_calls=0
 def checked_report(player,buf,size):
  global abi_calls
  registers=(C.c_uint64*7)();rc=l.probe_company_supply(player,buf,size,registers)
  assert tuple(registers)==tuple(0x123401+i for i in range(6))+(0,)
  abi_calls+=1;return rc
 entities=(C.c_uint*262144).in_dll(l,'sim_entities');weapons=(C.c_uint*262144).in_dll(l,'infantry_weapons');players=(C.c_uint*64).in_dll(l,'sim_players');assignments=(C.c_uint*16).in_dll(l,'player_companies');controls=(C.c_uint*12288).in_dll(l,'company_controls');count=C.c_uint.in_dll(l,'sim_count')
 assert l.sim_init(32,73)==0 and l.player_join(0,1)==0
 def report(player=0,size=40,expected=0):
  buf=(C.c_ubyte*64)(*([0xa7]*64));before=l.sim_checksum();rc=checked_report(player,C.byref(buf,8),size);assert rc==expected and l.sim_checksum()==before
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
 before=l.sim_checksum();assert checked_report(0,None,40)==-1 and l.sim_checksum()==before
 # Both directions of the body-generation lease and actual player front gate.
 for array,index in ((assignments,1),(controls,key*8+1),(players,10)):
  saved=array[index];array[index]=saved+1;report(expected=-1);array[index]=saved
 assert l.player_leave(0)==0;report(expected=-1)
 # Malformed count rejects before source iteration/output writes. No unsafe
 # checksum call while count itself is deliberately out of bounds.
 saved=count.value;count.value=32769;buf=(C.c_ubyte*40)(*([0xb9]*40))
 assert checked_report(0,buf,40)==-1 and bytes(buf)==bytes([0xb9]*40);count.value=saved
 # Independent exhaustive membership/count oracle, not the production bucket
 # walk, on original8k/16k worlds before/after actual consented ownership swap.
 large=[]
 for n in (8192,16384):
  assert l.sim_init(n,73)==0
  for player,front in enumerate((0,1,2,0)):assert l.player_join(player,front)==0
  def oracle(player):
   key=assignments[player*4];front=key//256;bucket=key%256;inf=low=empty=rounds=unknown=0
   for i in range(n):
    e=entities[i*8:i*8+8]
    if e[2]==0 or e[3]!=0 or e[4]!=0 or e[5]!=front or e[7]==0 or i//128!=bucket:continue
    inf+=1;w=weapons[i*8:i*8+8]
    if w[0]!=e[7] or w[1]>30 or w[2]>90 or w[3]>60 or w[6]>144000 or w[1]+w[2]+w[4]!=120+w[6] or (w[3] and w[1]):unknown+=1;continue
    available=w[1]+w[2];rounds+=available;low+=available<=30;empty+=available==0
   return (player,players[player*16+15],key,inf,low,empty,rounds,unknown,0,0)
  before=[report(i)for i in range(4)];assert before==[oracle(i)for i in range(4)]
  keys=[assignments[i*4]for i in range(4)];assert len(set(keys))==4
  # Explicit recipient consent invokes the actual atomic exchange API.
  assert l.company_transfer(0,1,0,0)==0
  transfers=(C.c_uint*48).in_dll(l,'company_transfers');sequence=transfers[9]
  assert l.company_transfer(1,0,1,sequence)==0
  after=[report(i)for i in range(4)];assert after==[oracle(i)for i in range(4)]
  assert after[0][2]==keys[1] and after[1][2]==keys[0]
  large.append({'units':n,'before':[list(x)for x in before],'after':[list(x)for x in after]})
 # All malformed stock dimensions remain unknown, never healthy or zero data.
 malformed=[]
 for field,value in ((1,31),(2,91),(3,61),(3,1),(4,144121),(6,144001),(6,1)):
  assert l.sim_init(32,73)==0 and l.player_join(0,1)==0
  weapons[8+field]=value;r=report();assert r[3]==4 and r[7]==1 and r[6]==360 and r[4]==r[5]==0,(field,value,r)
  malformed.append([field,value])
 print(json.dumps({'suite':'company-supply-report-prerequisite','passed':True,'initial':initial,'mixed_low_empty_unknown':mixed,'death_front_exclusions':narrowed,'read_only_authority':True,'owner_down_report_preserved':True,'invalid_lease_front_count_output_atomic':True,'output_guard_bytes_preserved':True,'six_nonvolatile_registers_preserved':True,'aligned_call_frames':True,'abi_calls':abi_calls,'original_scale_consented_exchange':large,'malformed_stock_classified_unknown':malformed,'core_reference_library_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'actual_copied_core_objects_sha256':core_hashes,'module_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'limits':['Actual assembly company/body/stock authority with independent static query fixtures.','Read-only original8k/16k snapshots and actual ownership exchange; not world-motion/performance acceptance. No network/HUD/depot presentation or supply-aware routes; not integrated.']}))
