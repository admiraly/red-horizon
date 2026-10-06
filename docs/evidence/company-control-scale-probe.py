import ctypes as C,json,pathlib,tempfile,time,hashlib,math
root=pathlib.Path('/mnt/titan_nv3/projects/red-horizon');worker=pathlib.Path('/mnt/titan_nv3/projects/red-horizon-workers/company-ownership')
class Entity(C.Structure):_fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):_fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint) for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint) for n in ('cooldown','ammo','generation')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[(n,C.c_uint) for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-mission-scale-') as name:
 td=pathlib.Path(name);paths=[]
 for tag,source in [('baseline',root/'build/libsim.so'),('candidate',worker/'build/libsim.so')]:
  p=td/(tag+'.so');p.write_bytes(source.read_bytes());paths.append(p)
 libs=[C.CDLL(str(p)) for p in paths]
 for lib in libs:lib.sim_checksum.restype=C.c_uint64
 reports=[]
 for n,scenario in [(8192,0),(8192,3),(16384,0)]:
  for lib in libs:
   assert lib.sim_init(n,42)==0
   if scenario:assert lib.sim_scenario(scenario)==0
  times=[[],[]];samples=[[],[]]
  for tick in range(1,901):
   for i in ([0,1] if tick%2 else [1,0]):
    start=time.perf_counter_ns();libs[i].sim_tick();times[i].append((time.perf_counter_ns()-start)/1e6)
   if tick%30==0:
    for i,lib in enumerate(libs):
     e=(Entity*32768).in_dll(lib,'sim_entities');a=(Air*32768).in_dll(lib,'sim_aircraft');air=[j for j in range(n) if e[j].kind==3 and e[j].hp];mission=sum(lib.air_escort_goal(j)==1 for j in air if a[j].role==1)
     samples[i].append({'tick':tick,'checksum':f'{lib.sim_checksum():016x}','army_alive':[sum(e[j].hp>0 and e[j].side==side for j in range(n)) for side in (0,1)],'air_alive':len(air),'air_stores':sum(a[j].ammo for j in air),'active_valid_escorts':mission,'entity_bytes_sha256':hashlib.sha256(bytes(e)[:n*32]).hexdigest()})
  assert all(a['entity_bytes_sha256']==b['entity_bytes_sha256'] for a,b in zip(samples[0],samples[1])), 'uncommanded army changed'
  report={'units':n,'scenario':scenario,'ticks':900,'timings':[{'mean_ms':sum(t)/len(t),'p95_ms':sorted(t)[math.ceil(.95*len(t))-1]} for t in times],'samples':samples};reports.append(report);print(json.dumps(report),flush=True)
 result={'passed':True,'library_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],'candidate_escort_source_sha256':hashlib.sha256((worker/'src/ai/air_escort.asm').read_bytes()).hexdigest(),'reports':reports,'limits':['Actual production public ticks, original army layouts, finite stores and immutable copied libraries.','No human leases/commands: all living/dead entity bytes must match at30tick samples; hash differs from additional private ownership state.','Concurrent frozen fast verification; local CPU wall time only, no GPU/network/human-quality acceptance.']}
 (worker/'docs/evidence/company-control-scale.json').write_text(json.dumps(result,indent=2)+'\n')
