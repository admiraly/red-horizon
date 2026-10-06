#!/usr/bin/env python3
"""Independent finite-store query fixtures against frozen actual assembly core."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];core=pathlib.Path(sys.argv[1]if len(sys.argv)>1 else '/mnt/titan_nv3/projects/red-horizon')
nasm=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
with tempfile.TemporaryDirectory(prefix='rh-depot-report-')as directory:
 td=pathlib.Path(directory);objects=[];hashes={}
 for folder in ('sim','nav','ai','game'):
  for p in (core/'src'/folder).glob('*.asm'):
   if p.name in ('depot_supply.asm','depot_supply_remote.asm'):continue
   name=str(p.relative_to(core)).replace('/','_')+'.o';data=(core/'build'/name).read_bytes();frozen=td/name;frozen.write_bytes(data);objects.append(str(frozen));hashes[name]=hashlib.sha256(data).hexdigest()
 for name,path in [('report','src/ai/depot_supply.asm'),('probe','tests/probe_depot_supply.asm'),('remote','src/sim/depot_supply_remote.asm')]:
  obj=td/(name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(root/path),'-o',str(obj)],check=True);objects.append(str(obj))
 library=td/'report.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects,'-lm'],check=True)
 l=C.CDLL(str(library));l.sim_checksum.restype=C.c_uint64;l.probe_depot_supply.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_void_p]
 sites=(C.c_uint*96).in_dll(l,'sim_sites');stocks=(C.c_uint*48).in_dll(l,'depot_ammunition');players=(C.c_uint*64).in_dll(l,'sim_players');calls=0
 def report(owner=0,size=304,expected=0):
  global calls
  buf=(C.c_ubyte*320)(*([0xa7]*320));registers=(C.c_uint64*7)();before=l.sim_checksum();rc=l.probe_depot_supply(owner,C.byref(buf,8),size,registers);calls+=1
  assert rc==expected and l.sim_checksum()==before
  assert tuple(registers)==tuple(0x123401+i for i in range(6))+(0,)
  if expected:assert bytes(buf)==bytes([0xa7]*320);return
  assert bytes(buf[:8])+bytes(buf[312:])==bytes([0xa7]*16)
  payload=bytes(buf[8:312]);header=struct.unpack_from('<4I',payload);n=header[2]
  assert header[:2]==(owner,players[owner*16+15])and header[3]==0 and n<=12
  assert not any(payload[16+n*24:]);return [list(struct.unpack_from('<6I',payload,16+i*24))for i in range(n)]
 assert l.sim_init(8192,73)==0 and l.player_join(0,0)==0
 initial=report();own=[i for i in range(12)if sites[i*8+2]==0 and sites[i*8+4]==1]
 assert [r[0]for r in initial]==own and all(r[1:4]==[12000,0,12000]and r[4]&1 for r in initial)
 # Finite debit uses actual store API on a declared available fixture, no renewal.
 ident=own[0];sites[ident*8+5]=1;sites[ident*8+6]=1000;sites[ident*8+7]=0
 assert l.depot_ammunition_take(ident,0,90)==90
 debit=report();r=next(r for r in debit if r[0]==ident);assert r==[ident,11910,90,12000,19,0]
 states=[]
 for field,value,flag in [(5,0,1),(7,4,7),(6,0,11)]:
  prior=sites[ident*8+field];sites[ident*8+field]=value;r=next(r for r in report()if r[0]==ident);assert r[1:4]==[11910,90,12000]and r[4]==flag;states.append(r);sites[ident*8+field]=prior
 # No refill: exhaust through real debit calls; capture away hides inventory,
 # capture back exposes the same empty physical store.
 for _ in range(133):l.depot_ammunition_take(ident,0,90)
 empty=next(r for r in report()if r[0]==ident);assert empty==[ident,0,12000,12000,3,0]
 sites[ident*8+2]=1;assert ident not in [r[0]for r in report()]
 sites[ident*8+2]=0;assert next(r for r in report()if r[0]==ident)==empty
 malformed=[]
 for field,value in [(0,12001),(1,12001),(2,1),(3,1),(0,1)]:
  prior=stocks[ident*4+field];stocks[ident*4+field]=value;r=next(r for r in report()if r[0]==ident);assert r==[ident,0,0,0,2,0];malformed.append([field,value]);stocks[ident*4+field]=prior
 # Unknown enemy store data is not accessed or disclosed by this owner view.
 foreign=next(i for i in range(12)if sites[i*8+2]==1 and sites[i*8+4]==1);stocks[foreign*4+3]=1;assert report()==[empty]+[r for r in report()if r[0]!=ident]
 players[5]=0;assert report();players[11]=0;report(expected=-1);players[11]=1
 for index in (10,15):
  old=players[index];players[index]=3 if index==10 else 0;report(expected=-1);players[index]=old
 for owner in (4,0xffffffff):report(owner=owner,expected=-1)
 for size in (0,303):report(size=size,expected=-1)
 regs=(C.c_uint64*7)();assert l.probe_depot_supply(0,None,304,regs)==-1
 # Remote validation is independently fed serialized actual authority reports.
 l.net_depot_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint]
 l.net_depot_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint]
 rows=report();gen=players[15]
 def wire(values=rows):return struct.pack('<4I',0,gen,len(values),0)+b''.join(struct.pack('<6I',*r)for r in values)+bytes((12-len(values))*24)
 payload=wire();remote=(C.c_ubyte*304).in_dll(l,'net_depot_records');valid=C.c_uint.in_dll(l,'net_depot_valid');clock=C.c_uint.in_dll(l,'net_depot_tick')
 baseline=bytes(remote);authority=l.sim_checksum();bad=[]
 for offset,value in [(0,1),(4,0),(8,13),(12,1),(16,12),(16+20,1),(16+16,32),(16+4,1),(16+12,1),(16+24,ident),(16+48,1)]:
  changed=bytearray(payload);struct.pack_into('<I',changed,offset,value);bad.append(changed)
 for b in bad:
  buf=C.create_string_buffer(bytes(b));assert l.net_depot_receive(buf,304,10,0)==-1 and bytes(remote)==baseline and not valid.value and l.sim_checksum()==authority
 buf=C.create_string_buffer(payload)
 for size in (0,303,305):assert l.net_depot_receive(buf,size,10,0)==-1
 assert l.net_depot_receive(None,304,10,0)==-1
 assert l.net_depot_receive(buf,304,10,0)==0 and bytes(remote)==payload and l.sim_checksum()==authority
 for stamp in (9,10):assert l.net_depot_receive(buf,304,stamp,0)==-1 and clock.value==10
 tick=C.c_uint.in_dll(l,'sim_tick_count');tick.value=10
 def remote_report(expected=0):
  out=(C.c_ubyte*320)(*([0xd9]*320));before=l.sim_checksum();rc=l.net_depot_report(0,C.byref(out,8),304);assert rc==expected and l.sim_checksum()==before
  if expected:assert bytes(out)==bytes([0xd9]*320)
  else:assert bytes(out[8:312])==payload and bytes(out[:8])+bytes(out[312:])==bytes([0xd9]*16)
 remote_report()
 for arr,index,value in [(players,10,3),(players,11,0),(players,15,gen+1),(sites,ident*8+2,1),(sites,ident*8+4,0),(sites,ident*8+5,0),(sites,ident*8+6,0),(sites,ident*8+7,4)]:
  prior=arr[index];arr[index]=value;remote_report(-1);arr[index]=prior
 # Newly acquired depot absent from older inventory also hides incomplete view.
 sites[foreign*8+2]=0;remote_report(-1);sites[foreign*8+2]=1
 tick.value=101;remote_report(-1);tick.value=100;remote_report();tick.value=9;remote_report(-1)
 l.net_depot_reset();assert not valid.value and not clock.value and not any(remote)
 print(json.dumps({'suite':'depot-supply-remote','passed':True,'malformed_packets':len(bad)+4,'atomic_stale_rejection':True,'authority_checksum_preserved':True,'body_ownership_role_availability_and_complete_site_set_gates':True,'age_and_reset':True,'limits':['Direct NASM cache API, not actual UDP or framebuffer.']}))
 print(json.dumps({'suite':'depot-supply-report','passed':True,'initial':initial,'actual_finite_debit':debit,'cut_contested_destroyed':states,'actual_exhaustion_capture_preserves_empty':empty,'malformed_stocks_unknown':malformed,'guard_bytes_atomic_failures_readonly_checksum':True,'abi_calls':calls,'copied_core_object_hashes':hashes,'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'limits':['Declared API availability/ownership/counter query fixtures, not live combat or supply-route acceptance.','No wire/HUD hooks yet; not integrated.']}))
