#!/usr/bin/env python3
"""Prepared explicit source-context isolation; development-only observer."""
import ctypes as C,json,os,pathlib,struct,subprocess,tempfile,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
with tempfile.TemporaryDirectory(prefix='rh-wreck-context-') as name:
 td=pathlib.Path(name);objs=[]
 for i,src in enumerate(('src/sim/wrecks.asm','src/nav/wreck_query.asm','src/nav/segment_box.asm','src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/ground_support.asm','src/nav/ground_contact.asm','tests/probe_wrecks.asm')):
  obj=td/f'{i}.o';subprocess.run([NASM,'-f','elf64','-D','WRECK_STANDALONE=1','-I',str(ROOT)+'/',str(ROOT/src),'-o',str(obj)],check=True);objs.append(str(obj))
 so=td/'query.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,*['-Wl,--wrap='+s for s in ('ground_support','ground_contact','terrain_height','sinf','cosf','atan2f')],'-lm','-o',str(so)],check=True)
 lib=C.CDLL(str(so));local=(C.c_byte*196620).in_dll(lib,'sim_wrecks');lib.wreck_init();before=bytes(local)
 point=lib.wreck_query_context;body=lib.wreck_body_query_context
 common=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_uint64]
 point.argtypes=common+[C.c_float]*6;body.argtypes=common+[C.c_float]*5
 sources=[C.create_string_buffer(65536) for _ in range(2)]
 def record(x,entity,seq):return struct.pack('<6f10I',x,100,1000,0,0,0,1,0,entity,1,0,1800,seq,1,0,0)
 for i,src in enumerate(sources):C.memmove(src,record(1000+100*i,12+i,i+1),64)
 saved=[s.raw for s in sources];calls=0
 def query(fn,source,count,revision,coords,wanted):
  global calls
  out=C.create_string_buffer(b'Z'*24,24);rc=fn(out,24,source,count,revision,*coords);calls+=1;assert rc==wanted,(rc,wanted)
  if rc!=1:assert out.raw==b'Z'*24
  assert bytes(local)==before
  return struct.unpack('<f5I',out.raw) if rc==1 else None
 # Same revision across distinct sources must never reuse another source's grid.
 for _ in range(64):
  for i,src in enumerate(sources):
   hit=query(point,src,1,1,(990,101,1000,1110,101,1000),1);assert hit[2]==12+i
   query(point,src,1,1,(990,101,1000,1010,101,1000),1-i)
   hit=query(body,src,1,1,(990,1000,1110,1000,.551),1);assert hit[2]==12+i
 assert [s.raw for s in sources]==saved
 # Source revision changes after mutation, including expiry and ring replacement.
 C.memmove(sources[0],record(1200,99,3),64)
 hit=query(point,sources[0],1,2,(1190,101,1000,1210,101,1000),1);assert hit[2:5]==(99,1,3)
 C.memset(C.addressof(sources[0])+52,0,4)
 query(point,sources[0],0,3,(1190,101,1000,1210,101,1000),0)
 # Invalid caller/source preserves output and every authoritative byte.
 query(point,None,0,0,(0,0,0,1,1,1),-1)
 query(point,sources[1],1025,0,(0,0,0,1,1,1),-1)
 query(point,sources[1],0,2,(1090,101,1000,1110,101,1000),-2)
 # Legacy wrappers continue to use authority even after remote-context searches.
 lib.wreck_query.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*6
 out=C.create_string_buffer(24);assert lib.wreck_query(out,24,1090,101,1000,1110,101,1000)==0
 assert bytes(local)==before
 # A revision refresh scans/reindexes but transforms only changed valid slots.
 large=C.create_string_buffer(65536)
 for i in range(512):C.memmove(C.addressof(large)+i*64,record(1000+i*10,i,i+1),64)
 query(point,large,512,1,(990,101,1000,1010,101,1000),1)
 transforms=C.c_uint.in_dll(lib,'wreck_query_transforms');assert transforms.value==512
 query(point,large,512,2,(990,101,1000,1010,101,1000),1);assert transforms.value==0
 C.memmove(C.addressof(large)+511*64,record(7000,511,1024),64)
 hit=query(point,large,512,3,(6990,101,1000,7010,101,1000),1);assert hit[2]==511;assert transforms.value==1
 # Same bytes in another source remain correct with reused per-slot bounds.
 duplicate=C.create_string_buffer(large.raw[:65536],65536)
 hit=query(point,duplicate,512,3,(6990,101,1000,7010,101,1000),1);assert hit[2]==511;assert transforms.value==0
 # Deactivation needs no trigonometry, and reactivation of exact pose reuses it.
 C.memset(C.addressof(large)+511*64+52,0,4)
 query(point,large,511,4,(6990,101,1000,7010,101,1000),0);assert transforms.value==0
 C.memmove(C.addressof(large)+511*64,record(7000,511,1024),64)
 query(point,large,512,5,(6990,101,1000,7010,101,1000),1);assert transforms.value==0
 # Actual remote lifecycle drives the supplied context revision, without authority writes.
 obj=td/'remote.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/sim/wreck_remote.asm'),'-o',str(obj)],check=True)
 dll=td/'remote.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(obj),'-o',str(dll)],check=True)
 remote=C.CDLL(str(dll));remote.wreck_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint];remote.wreck_remote_expire.argtypes=[C.c_uint]
 cache=(C.c_byte*65536).in_dll(remote,'net_wrecks');count=C.c_uint.in_dll(remote,'net_wreck_count');revision=C.c_uint64.in_dll(remote,'net_wreck_query_revision')
 remote.wreck_remote_reset();initial_revision=revision.value
 payload=C.create_string_buffer(struct.pack('<I',0)+record(1000,12,1));assert remote.wreck_receive(payload,68,0)==1;first_revision=revision.value;assert first_revision!=initial_revision
 def remote_query(wanted):return query(point,C.addressof(cache),count.value,revision.value,(990,101,1000,1010,101,1000),wanted)
 remote_query(1);assert remote.wreck_receive(payload,68,1)==1;assert revision.value==first_revision;remote_query(1)
 remote.wreck_remote_expire(1799);assert revision.value==first_revision
 remote.wreck_remote_expire(1800);assert revision.value!=first_revision;remote_query(0);expiry_revision=revision.value
 remote.wreck_remote_expire(1801);assert revision.value==expiry_revision
 # Malformed packet is atomic across cache, validity/timestamps and derived revision.
 malformed=C.create_string_buffer(struct.pack('<I',1024)+record(1000,12,1));old=C.string_at(C.addressof(cache),70660)
 assert remote.wreck_receive(malformed,68,1800)==-1;assert revision.value==expiry_revision;assert C.string_at(C.addressof(cache),70660)==old
 # Delayed active snapshot cannot revive server-clock-expired geometry.
 assert remote.wreck_receive(payload,68,1)==0;assert revision.value==expiry_revision;remote_query(0)
 replacement=bytearray(record(1000,99,2));struct.pack_into('<2I',replacement,40,2000,3800);payload2=C.create_string_buffer(struct.pack('<I',0)+replacement)
 assert remote.wreck_receive(payload2,68,2000)==1;hit=remote_query(1);assert hit[2:5]==(99,1,2)
 replacement_revision=revision.value;remote.wreck_remote_reset();assert revision.value!=replacement_revision;remote_query(0)
 assert bytes(local)==before
 # Actual assembled faults must expose cross-source and lifecycle cache mistakes.
 negatives=[];source=(ROOT/'src/nav/wreck_query.asm').read_text()
 for tag,text in [('source_key_omitted',source.replace(' cmp rax,[cache_source]\n jne .refresh',' nop\n nop')),('revision_key_omitted',source.replace(' cmp rax,[cache_revision]\n je .cached',' jmp .cached')),('pose_memo_omitted',source.replace(' xor ecx,ecx\n.memo:',' mov ecx,3\n.memo:'))]:
  asm=td/(tag+'.asm');asm.write_text(text);obj=td/(tag+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True)
  altered=list(objs);altered[1]=str(obj);dll=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*altered,*['-Wl,--wrap='+s for s in ('ground_support','ground_contact','terrain_height','sinf','cosf','atan2f')],'-lm','-o',str(dll)],check=True)
  bad=C.CDLL(str(dll));fn=bad.wreck_query_context;fn.argtypes=point.argtypes;rows=[C.create_string_buffer(65536) for _ in range(2)]
  for i,src in enumerate(rows):C.memmove(src,record(1000+100*i,12+i,i+1),64)
  out=C.create_string_buffer(24);assert fn(out,24,rows[0],1,1,990,101,1000,1010,101,1000)==1
  if tag=='source_key_omitted':rc=fn(out,24,rows[1],1,1,990,101,1000,1010,101,1000);assert rc==1
  else:
   C.memmove(rows[0],record(1200,12,1) if tag=='pose_memo_omitted' else record(1200,99,3),64);rc=fn(out,24,rows[0],1,2,1190,101,1000,1210,101,1000);assert rc==0
  negatives.append(tag)
 print(json.dumps({'suite':'wreck-explicit-query-context','passed':True,'calls':calls,'512_slot_refresh_transforms':[512,0,1,0,0,0],'assembled_negatives':negatives,'same_revision_source_switches':128,'local_authority_unchanged':True,'actual_remote_receive_expire_retire_reset_revision':True,'identical_heartbeat_retains_geometry_revision':True,'independent_sources_unchanged_except_declared_lifecycle_fixture':True,'query_source_sha256':hashlib.sha256((ROOT/'src/nav/wreck_query.asm').read_bytes()).hexdigest(),'scope':'Prepared caller-owned stable records/count/revision API. Actual remote-cache lifecycle revision is verified; no connected-client prediction hooks, actor movement, cover or scale acceptance.'}))
