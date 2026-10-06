#!/usr/bin/env python3
"""Independent numeric and ABI oracle for real bounded terrain targeting."""
import ctypes as C,hashlib,json,math,os,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-wheel-') as name:
 td=pathlib.Path(name);probe=td/'probe.o';so=td/'wheel.so'
 subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(root/'tests/probe_command_wheel.asm'),'-o',str(probe)],check=True)
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (root/'src'/folder).glob('*.asm')]
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*objects,str(probe),'-lm'],check=True)
 l=C.CDLL(str(so));l.command_wheel_select.argtypes=[C.c_float,C.c_float];l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float;l.sim_checksum.restype=C.c_uint64
 l.sim_init(8192,42)
 def select(x,y):return l.command_wheel_select(x,y)
 cases=[(0,-80,0),(-80,0,1),(0,80,2),(80,0,3),(0,0,-1),(37.99,0,-1),(38,0,3),(40,-40,4),(40,-80,4),(80,-40,4),(39,-80,0),(81,-40,3),(40,40,2),(-40,-40,0),(-40,40,2),(float('nan'),0,-1),(0,float('inf'),-1)]
 for x,y,want in cases:assert select(x,y)==want,(x,y,want,select(x,y))
 def cast(origin,direction):
  ray=(C.c_float*6)(*origin,*direction);before=bytes(ray);out=(C.c_float*2)(-1,-1);regs=(C.c_uint64*7)();h=l.sim_checksum()
  rc=l.probe_command_terrain_point(ray,out,regs)
  assert bytes(ray)==before and l.sim_checksum()==h
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,),tuple(regs)
  return rc,tuple(out)
 def direction(yaw,pitch):return(math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch))
 hits=[]
 # Flat/bowl, relief plateau, near map edge; compare numeric geometric ray with
 # real terrain height, independently bisected at the observed hit's distance.
 for x,z,yaw,pitch in [(3500,1300,math.pi/2,-.15),(3780,3900,0,-.08),(6000,6000,math.pi,-.4),(7995,7000,-math.pi/2,-.5),(5520,5230,math.pi/2,-.4)]:
  origin=(x,l.terrain_height(x,z)+2,z);d=direction(yaw,pitch);rc,point=cast(origin,d);assert rc==0,(origin,d,rc)
  distance=(point[0]-x)/d[0] if abs(d[0])>.1 else (point[1]-z)/d[2]
  height=origin[1]+d[1]*distance;actual=l.terrain_height(*point)
  assert 0<distance<=2048 and abs(actual-height)<.002,(point,distance,height,actual)
  assert abs(point[0]-(x+d[0]*distance))<.003 and abs(point[1]-(z+d[2]*distance))<.003
  hits.append({'point':point,'distance':distance,'height_error':abs(actual-height)})
 for origin,d in [((3500,100,1300),(0,1,0)),((3500,10000,1300),(1,0,0)),((7999,100,1300),(1,0,0)),((float('nan'),50,1300),(0,-1,0)),((3500,50,1300),(0,-2,0)),((-1,50,1300),(0,-1,0)),((3500,l.terrain_height(3500,1300)-1,1300),(0,-1,0))]:assert cast(origin,d)[0]==-1,(origin,d)
 # Actual authored wall blocks the terrain point behind it; no fixture edits.
 origin=(3970,l.terrain_height(3970,1300)+3,1300);assert cast(origin,direction(math.pi/2,-.07))[0]==-1,'terrain selected through a wall'
 print(json.dumps({'suite':'command-wheel-targeting','passed':True,'selection_cases':len(cases),'terrain_hits':hits,'miss_cases':8,'static_wall_rejected':True,'readonly_ABI':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Bounded 2048m/4m terrain sampling and12 bisections; static walls reject rather than target structures.','Dynamic units/structures, full contextual roster and remapping remain separate.']}))
