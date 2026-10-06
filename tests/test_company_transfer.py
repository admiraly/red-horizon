#!/usr/bin/env python3
"""Explicit consent, stale generations/leases, preserved physical orders, ABI.
World setup occurs only before traces; no live health/ammo/pose/clock renewals.
"""
import ctypes as C,hashlib,json,os,pathlib,subprocess,tempfile,math
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm'))
with tempfile.TemporaryDirectory(prefix='rh-transfer-')as directory:
 td=pathlib.Path(directory);probe=td/'probe.o';terrain=td/'terrain.o';so=td/'transfer.so'
 for source,dest in [('tests/probe_company_transfer.asm',probe),('tests/terrain_probe.asm',terrain)]:subprocess.run([nasm,'-f','elf64',str(root/source),'-o',str(dest)],check=True)
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o'))for folder in ('sim','nav','ai','game')for p in (root/'src'/folder).glob('*.asm')]
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*objects,str(probe),str(terrain),'-lm'],check=True)
 l=C.CDLL(str(so));l.sim_checksum.restype=C.c_uint64;l.company_control_order.argtypes=[C.c_uint]*3+[C.c_float]*2
 E=(C.c_ubyte*(32768*32)).in_dll(l,'sim_entities');P=(C.c_uint*64).in_dll(l,'sim_players');A=(C.c_uint*16).in_dll(l,'player_companies');D=(C.c_ubyte*(1536*32)).in_dll(l,'company_controls');T=(C.c_uint*48).in_dll(l,'company_transfers');funds=(C.c_uint*2).in_dll(l,'sim_requisition')
 def api(who,other,action,sequence=0):
  registers=(C.c_uint64*7)();rc=l.probe_company_transfer(who,other,action,sequence,registers)
  assert tuple(registers)==tuple(0x123401+i for i in range(6))+(0,)
  return rc
 def prepare():
  import struct
  assert l.sim_init(256,42)==0;l.player_init()
  for i in range(256):C.c_uint.from_buffer(E,i*32+8).value=0
  for start,front,x,z in [(1,0,1800.,1800.),(33,1,1800.,3900.),(65,2,1800.,6500.),(129,0,2100.,1800.)]:
   for j in range(16):E[(start+j)*32:(start+j+1)*32]=struct.pack('<2f6I',x+(j%8)*4,z+(j//8)*6,100,0,0,front,0xffffffff,1)
  for i,front in enumerate((0,1,2,0)):assert l.player_join(i,front)==0
  keys=[l.company_for_player(i)for i in range(4)];assert len(set(keys))==4
  return keys
 def unchanged(call,expected):
  h=l.sim_checksum();assert call()==expected;assert l.sim_checksum()==h
 keys=prepare()
 for who,other,action,sequence in [(4,0,0,0),(0,4,0,0),(0,0,0,0),(0,1,4,0),(0,1,0,1),(1,0,1,0),(1,0,2,0),(0,1,3,0)]:unchanged(lambda:api(who,other,action,sequence),-1 if action>3 or who>3 or other>3 or who==other or action==0 else -2)
 balances=tuple(funds);before=bytes(D);leases=tuple(A);players=bytes(P)
 assert api(0,1,0)==0 and tuple(funds)==balances and bytes(D)==before and tuple(A)==leases and bytes(P)==players
 assert T[0]==1 and T[1]==1 and T[2:4]==keys[:2] and T[8]==450 and T[9]==1
 # A third party, wrong sequence, or sender cannot silently approve a request.
 for args in [(2,0,1,1),(0,1,1,1),(1,0,1,2),(2,0,2,1),(0,2,3,1)]:unchanged(lambda:api(*args),-2)
 assert api(1,0,2,1)==0 and T[0]==0 and T[9]==1 and not any(T[:9])
 assert api(0,1,0)==0 and T[9]==2
 assert api(0,1,3,2)==0 and not T[0]
 # Replaced offers are identified by sequence, not by requester alone.
 assert api(0,1,0)==0;seq=T[9];assert api(0,2,0)==0 and T[9]==seq+1
 unchanged(lambda:api(1,0,1,seq),-2);assert api(2,0,2,T[9])==0
 # Generation/lease invalidation occurs through ordinary authoritative ticks.
 keys=prepare();assert api(0,1,0)==0
 assert l.player_leave(1)==0;unchanged(lambda:api(1,0,1,1),-2);l.sim_tick();assert not T[0]
 assert l.player_join(1,1)==0
 assert api(0,1,0)==0;seq=T[9]
 P[15]+=1 # isolated corruption check, distinct from all physical traces.
 unchanged(lambda:api(1,0,1,seq),-2);l.company_transfer_tick();assert not T[0]
 keys=prepare();assert api(0,1,0)==0
 A[6]+=1 # isolated stale target lease, no physical trace mutation.
 unchanged(lambda:api(1,0,1,1),-2);l.company_transfer_tick();assert not T[0]
 keys=prepare();assert api(0,1,0)==0
 for _ in range(450):l.sim_tick()
 assert T[0]==0 and T[9]==1
 unchanged(lambda:api(1,0,1,1),-2)
 # Current accepted orders are company state and survive the ownership exchange.
 def physical():
  import struct
  keys=prepare();assert l.company_control_order(0,keys[0],1,1800.,1800.)==0
  assert l.company_control_order(1,keys[1],0,2200.,3900.)==0
  intent=[bytes(D[k*32+8:k*32+32])for k in keys];poses=[bytes(P)[i*64:(i+1)*64]for i in range(4)]
  serials=[A[i*4+2]for i in range(4)];balance=tuple(funds)
  # A competing offer involving either accepted participant is invalidated.
  assert api(2,0,0)==0 and api(0,1,0)==0
  assert api(1,0,1,T[9])==0
  assert [l.company_for_player(i)for i in range(4)]==[keys[1],keys[0],keys[2],keys[3]]
  assert [P[i*16+10]for i in range(4)]==[1,0,2,0]
  for i in range(4):
   actual=bytes(P)[i*64:(i+1)*64];assert actual[:40]==poses[i][:40] and actual[44:]==poses[i][44:]
  assert tuple(funds)==balance and all(bytes(D[k*32+8:k*32+32])==value for k,value in zip(keys,intent))
  assert A[2]==serials[0]+1 and A[6]==serials[1]+1 and not T[0] and not T[24]
  unchanged(lambda:api(1,0,1,T[9]),-2)
  # Old owner commands reject; new owner may command their actual cohort.
  h=l.sim_checksum();assert l.company_control_order(0,keys[0],0,2200.,1800.)==-2 and l.sim_checksum()==h
  assert l.company_control_order(1,keys[0],1,1800.,1800.)==0
  start=[struct.unpack_from('<2f',E,i*32)for i in (1,33)]
  for _ in range(200):l.sim_tick()
  travel=[math.dist(x,struct.unpack_from('<2f',E,i*32))for x,i in zip(start,(1,33))]
  assert travel[0]<.001 and travel[1]>15,travel
  return {'keys_after':[A[i*4]for i in range(4)],'physical_displacements_m':travel,'checksum':f'{l.sim_checksum():016x}'}
 first=physical();assert physical()==first
 print(json.dumps({'suite':'company-consented-transfer','passed':True,'physical':first,'explicit_accept_required':True,'cross_front_exchange_without_teleport':True,'one_company_per_connected_player':True,'orders_and_funds_preserved':True,'stale_sequence_generation_lease_rejected':True,'competing_offers_invalidated':True,'decline_cancel_expiry':True,'ABI_preserved':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Controlled API world; UDP, client presentation and broad scale/full checkpoint remain separate.','One company per player is preserved by exchange; individual squad splitting, assistance and recruitment remain separate.']}))
