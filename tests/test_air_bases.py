#!/usr/bin/env python3
"""Native runway geometry, owned facility policy and real public diversion flight."""
import ctypes as C
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NASM = os.environ['RED_HORIZON_NASM']
RUNWAYS = json.loads((ROOT/'content/terrain/airbases.json').read_text())['runways']
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
    _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]

with tempfile.TemporaryDirectory(prefix='rh-air-bases-') as folder:
    temp=Path(folder);objects=[]
    sources=sorted(p for group in ('sim','nav','ai','game')for p in (ROOT/'src'/group).glob('*.asm'))+[ROOT/'tests/terrain_probe.asm',ROOT/'tests/probe_air_bases.asm']
    for source in sources:
        obj=temp/(source.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
    def link(path, inputs):
        subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,inputs),'-lm'],check=True,capture_output=True)
    candidate=temp/'candidate.so';link(candidate,objects)
    text=(ROOT/'src/ai/air_bases.asm').read_text();assert text.count('air_base_goal:\n')==1
    control_text=text.replace('air_base_goal:\n','air_base_goal:\n mov eax,-1\n ret\n',1)
    asm=temp/'control.asm';asm.write_text(control_text);obj=temp/'control.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
    control=temp/'control.so';link(control,[obj if p.name=='air_bases.asm.o'else p for p in objects])
    def bind(path):
        lib=C.CDLL(str(path));lib.sim_checksum.restype=C.c_uint64;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
        lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
        lib.probe_air_base_goal.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
        lib.air_runway_body.argtypes=[C.c_float]*3
        lib.air_world_sweep.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*6
        return lib,(Entity*32768).in_dll(lib,'sim_entities'),(Air*32768).in_dll(lib,'sim_aircraft'),((C.c_uint*8)*12).in_dll(lib,'sim_sites')
    lib,entities,air,sites=bind(candidate)
    def reset(side=0,front=1,role=1):
        assert lib.sim_init(64,42)==0
        for i in range(64):entities[i].hp=0
        for team in (0,1):
            for region in range(3):assert lib.sim_order(team,region,1)==0
        assert lib.sim_waypoint(side,front,7000. if side==0 else 1000.,4000.)==0
        speed=(5.,7.)[role];x=(3500.,4500.)[side];z=2000.*(front+1)
        entities[31]=Entity(x,z,50,side,3,front,-1,1)
        air[31]=Air(lib.terrain_height(x,z)+(110.,140.)[role],(-math.pi/2,math.pi/2)[side],0,0,speed,role,0,-1,0,(8,180)[role],1,(-speed,speed)[side],0,0,0,1)
    def query(ident=31):
        before=lib.sim_checksum();output=(C.c_float*4)(123,0,0,456);regs=(C.c_uint64*9)()
        result=lib.probe_air_base_goal(ident,81.,-17.,0.,C.byref(output,4),regs)
        assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,0x88008,0x99009)
        assert output[0]==123 and output[3]==456 and lib.sim_checksum()==before
        if result==-1:assert tuple(output)[1:3]==(81.,-17.)
        return result,tuple(output)[1:3]
    records=(C.c_ubyte*(6*32)).in_dll(lib,'air_bases')
    expected=b''.join(struct.pack('<4f4I',r['x'],r['z'],r['half_length'],r['half_width'],r['site'],r['side'],r['front'],0)for r in RUNWAYS)
    assert bytes(records)==expected
    cases=[]
    for side in (0,1):
        for front in range(3):
            reset(side,front);base=RUNWAYS[side*3+front]
            assert query()==(base['id'],(base['x'],base['z']))
            for field,bad in ((8//4,side^1),(16//4,2),(20//4,0),(20//4,2),(24//4,0),(24//4,1001),(28//4,4),(28//4,8)):
                old=sites[base['site']][field];sites[base['site']][field]=bad
                eligible=[r for r in RUNWAYS if sites[r['site']][2]==side and sites[r['site']][4]<=1 and sites[r['site']][5]==1 and 0<sites[r['site']][6]<=1000 and sites[r['site']][7]&~3==0]
                expected_base=min(eligible,key=lambda r:((r['x']-entities[31].x)**2+(r['z']-entities[31].z)**2,r['id']))
                assert query()==(expected_base['id'],(expected_base['x'],expected_base['z']))
                sites[base['site']][field]=old;cases.append(dict(side=side,front=front,field=field,bad=bad))
    reset();normal=query()
    entities[63]=Entity(math.nan,math.inf,0,1,3,2,-1,999);air[63].y=math.nan
    for r in RUNWAYS:
        if sites[r['site']][2]==1:sites[r['site']][6]=0xffffffff
    assert query()==normal
    # Captured usable enemy-side authored runway is an eligible own facility.
    for r in RUNWAYS:sites[r['site']][5]=0
    sites[7][2]=0;sites[7][5]=1;sites[7][6]=1000
    assert query()==(4,(6000.,4000.))
    sites[7][5]=0;assert query()[0]==-1
    for ident in (64,32768,0xffffffff):assert query(ident)[0]==-1
    for group,field,bad in ((entities[31],'x',math.nan),(entities[31],'z',-1),(entities[31],'hp',0),(entities[31],'side',2),(entities[31],'front',3),(entities[31],'gen',0),(air[31],'gen',2),(air[31],'role',2),(air[31],'flags',0)):
        old=getattr(group,field);setattr(group,field,bad);assert query()[0]==-1;setattr(group,field,old)
    count=C.c_uint.in_dll(lib,'sim_count');count.value=32769;assert query()[0]==-1;count.value=64
    # Exact Fraction reference detects even the smallest f32 positive edge radius.
    relief=json.loads((ROOT/'content/terrain/relief.json').read_text())['fields'][0]
    obstacles=C.c_uint.in_dll(lib,'terrain_obstacle_count').value
    solid_records=((C.c_float*8)*obstacles).in_dll(lib,'terrain_obstacles')
    for row in RUNWAYS:
        bounds=(row['x']-row['half_length']-4,row['z']-row['half_width']-4,row['x']+row['half_length']+4,row['z']+row['half_width']+4)
        assert bounds[2]<3200 or bounds[0]>4800  # All strip hulls avoid ridge breaks.
        assert bounds[2]<relief['x'][0] or bounds[0]>relief['x'][3] or bounds[3]<relief['z'][0] or bounds[1]>relief['z'][3]
        for obstacle in solid_records:
            assert bounds[2]<obstacle[0] or bounds[0]>obstacle[2] or bounds[3]<obstacle[1] or bounds[1]>obstacle[3]
    body_cases=0;strip_clearance=[]
    for row in RUNWAYS:
        for radius in (0.,2**-149,3.55,4.49,40.,40.01,600.,8000.):
            for dx,dz in ((0,0),(600,0),(-600,0),(0,40),(0,-40),(596,35),(601,0),(0,41)):
                x,z,rad=(C.c_float(v).value for v in (row['x']+dx,row['z']+dz,radius))
                fit=any(Fraction(r['half_length'])-abs(Fraction(x)-Fraction(r['x']))>=Fraction(rad) and Fraction(r['half_width'])-abs(Fraction(z)-Fraction(r['z']))>=Fraction(rad) for r in RUNWAYS)
                before=bytes(records);assert lib.air_runway_body(x,z,rad)==int(fit) and bytes(records)==before;body_cases+=1
        # Actual smooth ground +4.3m body-centre path over the entire runway,
        # not an exempt collision plane. Grade and world sweeps use production NASM.
        for dz in (-35.,0.,35.):
            x0=row['x']-row['half_length'];x1=row['x']+row['half_length'];z=row['z']+dz
            y0=lib.terrain_height(x0,z)+4.3;y1=lib.terrain_height(x1,z)+4.3
            output=C.create_string_buffer(b'Z'*16,16);assert lib.air_world_sweep(output,16,x0,y0,z,x1,y1,z)==0 and output.raw==b'Z'*16
            # Independent analytic gradient: strips avoid ridge/relief footprints.
            maximum_grade=max(math.hypot((x-4000)*.000002,(z-4000)*.000001)for x in (x0,x1))
            assert maximum_grade<.02
            strip_clearance.append(dict(base=row['id'],cross_offset=dz,max_grade=maximum_grade))
    for xyz in ((math.nan,2000,0),(2000,math.inf,0),(2000,2000,-1),(2000,2000,math.nan),(8001,2000,0)):
        assert lib.air_runway_body(*xyz)==-1
    outcomes=[]
    for side in (0,1):
        pair=[]
        for label,path in (('candidate',candidate),('omitted-facility-policy',control)):
            lib,entities,air,sites=bind(path);reset(side)
            home=RUNWAYS[side*3+1];sites[home['site']][6]=0  # One permanent initial site destruction.
            destination=(2000. if side==0 else 6000.,2000.)
            closest=math.dist((entities[31].x,entities[31].z),destination);hashes=[]
            for tick in range(1,1801):
                old=(entities[31].x,air[31].y,entities[31].z);old_speed=air[31].speed;lib.sim_tick()
                assert abs(math.dist(old,(entities[31].x,air[31].y,entities[31].z))-air[31].speed)<.002
                assert 5<=air[31].speed<=7 and -.012002<=air[31].speed-old_speed<=.010002
                assert entities[31].hp==50 and air[31].ammo==180
                closest=min(closest,math.dist((entities[31].x,entities[31].z),destination))
                if tick%300==0:hashes.append(f'{lib.sim_checksum():016x}')
            pair.append(dict(policy=label,closest_diversion_gap_m=closest,hp=entities[31].hp,ammo=air[31].ammo,mode=air[31].mode,hashes=hashes))
        assert pair[0]['closest_diversion_gap_m']<150 and pair[1]['closest_diversion_gap_m']>800,pair
        outcomes.append(dict(side=side,paired=pair))
    print(json.dumps(dict(suite='air-bases-native',passed=True,facility_policy_cases=len(cases),exact_runway_body_cases=body_cases,terrain_clearance=strip_clearance,public_diversion=outcomes,ABI_GPR_R8_R9_XMM_stack_and_authority_preserved=True,library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),negative_control_sha256=hashlib.sha256(control_text.encode()).hexdigest(),scope='Native six runway rectangles, owned current facility selection, exact body boundaries and actual static ground/solid sweeps. Two public1800-tick fighter diversion comparisons; one initial site destruction, no live body/health/ammo/fuel/clock renewal. Not landing/refill/repair/traffic/wreck-clearance/whole-operation acceptance.')))
