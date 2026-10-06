#!/usr/bin/env python3
"""Development-only frozen-runtime/finer-grid controlled comparison."""
import ctypes as C,hashlib,json,os,pathlib,statistics,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1];original=pathlib.Path(sys.argv[1]).resolve();build=original.parent
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
with tempfile.TemporaryDirectory(prefix='rh-wreck-grid-') as name:
 td=pathlib.Path(name);obj=td/'fine.o';subprocess.run([os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm'),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/'src/nav/wreck_query.asm'),'-o',str(obj)],check=True)
 objs=sorted(p for p in build.glob('*.o') if p.name.startswith(('src_sim_','src_nav_','src_game_','src_ai_')) and p.name!='src_nav_wreck_query.asm.o');objs.append(build/'terrain_probe.o');fine=td/'fine.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*[str(p) for p in objs],str(obj),'-lm','-o',str(fine)],check=True)
 libs=[C.CDLL(str(p)) for p in (original,fine)];outputs=[C.create_string_buffer(24) for _ in libs];wrecks=[(W*1024).in_dll(lib,'sim_wrecks') for lib in libs];candidates=[C.c_uint.in_dll(lib,'wreck_query_candidates') for lib in libs]
 for lib in libs:lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_checksum.restype=C.c_uint64;lib.wreck_query.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*6
 rows=[]
 for population in (8192,16384):
  for lib in libs:assert lib.sim_init(population,42)==0 and lib.sim_scenario(3)==0
  for tick in range(900):
   for lib in libs:lib.sim_tick()
   if tick%30==0:assert libs[0].sim_checksum()==libs[1].sim_checksum()
  before=[lib.sim_checksum() for lib in libs];assert before[0]==before[1]
  assert bytes(wrecks[0])==bytes(wrecks[1]);poses=[(w.x,w.y+1,w.z) for w in wrecks[0] if w.flags&1]
  visits=[[],[]];times=[[],[]];contacts=[]
  for index,lib in enumerate(libs):
   for x,y,z in poses:
    assert lib.wreck_query(outputs[index],24,x-10,y,z,x+10,y,z)==1;visits[index].append(candidates[index].value)
    if index==0:contacts.append(outputs[index].raw)
    else:assert outputs[index].raw==contacts[len(visits[index])-1]
  for group in range(40):
   for index in (group%2,1-group%2):
    start=time.perf_counter_ns()
    for x,y,z in poses:assert libs[index].wreck_query(outputs[index],24,x-10,y,z,x+10,y,z)==1
    times[index].append((time.perf_counter_ns()-start)/1e6)
  assert [lib.sim_checksum() for lib in libs]==before
  rows.append({'units':population,'ticks':900,'seed':42,'scenario':'scale-hotspot','actual_wrecks':len(poses),'first_contacts_byte_equal':True,'authority_equal_and_unchanged':True,'groups_per_variant':40,'query_count_per_variant':len(poses)*41,'variants':[{'cell_metres':cell,'grid_cells':cells,'mean_candidates':statistics.mean(visits[i]),'peak_candidates':max(visits[i]),'warm_group_mean_ms':statistics.mean(times[i]),'warm_group_p95_ms':sorted(times[i])[37]} for i,(cell,cells) in enumerate(((250,1024),(62.5,16384)))]})
 print(json.dumps({'suite':'prepared-wreck-grid-comparison','passed':True,'cases':rows,'original_library_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'prepared_library_sha256':hashlib.sha256(fine.read_bytes()).hexdigest(),'prepared_source_sha256':hashlib.sha256((ROOT/'src/nav/wreck_query.asm').read_bytes()).hexdigest(),'unchanged_frozen_objects':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in objs},'scope':'Prepared isolated grid variation, exact original physical world/casualties and nearest contact bytes; Python/ctypes timings include call/assert overhead, exclude initial rebuild and alternate variant order. Not full cover/body/rifle/server or graphics acceptance.'}))
