#!/usr/bin/env python3
"""Independent static-road/analytic-surface evidence; development-only harness."""
import ctypes as C
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
GENERATOR=ROOT/'tools/terrain_surfaces.py'
SOURCE=ROOT/'content/terrain/roads.json'
NASM=ROOT/'schemas/terrain_roads.inc'
GLSL=ROOT/'shaders/terrain_roads.glsl'
spec=importlib.util.spec_from_file_location('terrain_generator',GENERATOR)
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
canonical=json.loads(SOURCE.read_text())
# Independent expected records, never the generator's validate/render result.
records=[]
for row in canonical['roads']:
    records.append(tuple(struct.unpack('<f',struct.pack('<f',v))[0] for v in (*row['from'],*row['to'],row['half_width']))+(row['flags'],))
assert canonical['version']==1 and len(records)==19
assert all(row[4]==10 and row[5]==1 for row in records)
nasm_records=[]
for line in NASM.read_text().splitlines():
    if line.startswith(' dd '):
        values=line[4:].split(',')
        nasm_records.append(tuple(float(v) for v in values[:5])+(int(values[5]),))
glsl_text=GLSL.read_text()
segments=[tuple(float(v) for v in row.split(',')) for row in re.findall(r' vec4\(([^)]+)\)',glsl_text)]
widths=[float(v) for v in re.search(r'terrainRoadHalfWidths\[terrainRoadCount\] = float\[terrainRoadCount\]\(\s*([^)]*)\)',glsl_text).group(1).split(',')]
flags=[int(v.strip().removesuffix('u')) for v in re.search(r'terrainRoadFlags\[terrainRoadCount\] = uint\[terrainRoadCount\]\(\s*([^)]*)\)',glsl_text).group(1).split(',')]
assert nasm_records==records==[(*a,b,c) for a,b,c in zip(segments,widths,flags)]
subprocess.run([sys.executable,str(GENERATOR),'--check'],check=True,capture_output=True)

def point_segment(point,a,b):
    dx,dz=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dz)/(dx*dx+dz*dz)))
    return math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dz)

def reference_class(point):
    return int(any(point_segment(point,row[:2],row[2:4])<=row[4] for row in records))

def reference_surface(point):
    x,z=point[0]-4000,point[1]-4000
    h=12+x*x*.000001+z*z*.0000005+max(0,1-abs(x)/800)*18
    gx=x*.000002
    if 0<abs(x)<800:gx+=.0225 if x<0 else -.0225
    return h,gx,z*.000001

with tempfile.TemporaryDirectory(prefix='rh-terrain-surface-') as directory:
    directory=Path(directory)
    nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
    objects=[]
    for source in ('src/nav/terrain_surface.asm','src/nav/terrain.asm','tests/probe_terrain_surface.asm'):
        output=directory/(Path(source).stem+'.o')
        subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(output)],check=True)
        objects.append(str(output))
    library=directory/'surface.so'
    subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(library)],check=True)
    lib=C.CDLL(str(library))
    lib.test_surface.argtypes=[C.POINTER(C.c_float)];lib.test_surface.restype=C.c_int
    lib.test_height.argtypes=[C.POINTER(C.c_float)]
    road_count=C.c_uint.in_dll(lib,'terrain_road_count')
    road_blob=(C.c_byte*(19*24)).in_dll(lib,'terrain_road_segments')
    initial_roads=bytes(road_blob)
    expected_blob=b''.join(struct.pack('<5fI',*record) for record in records)
    assert road_count.value==19 and initial_roads==expected_blob
    points=[]
    category_counts={name:0 for name in ('center','inner_edge','outer_edge','end_cap','junction','offroad','random','cusp')}
    def check(point,category,expected=None):
        data=(C.c_float*5)(*point,0,0,0)
        actual_point=tuple(data[:2])
        result=lib.test_surface(data)
        assert result in (0,1),('ABI or valid classification',actual_point,result)
        if expected is None:expected=reference_class(actual_point)
        assert result==expected,('surface class',category,actual_point,result,expected)
        production=(C.c_float*3)(*actual_point,0)
        lib.test_height(production)
        assert struct.pack('<f',data[2])==struct.pack('<f',production[2]),'height differs from production terrain'
        analytical=reference_surface(actual_point)
        assert abs(data[2]-analytical[0])<=.00003,('height',actual_point,data[2],analytical)
        assert abs(data[3]-analytical[1])<=5e-9 and abs(data[4]-analytical[2])<=1e-9,('gradient',actual_point,tuple(data[3:]),analytical)
        assert bytes(road_blob)==initial_roads and road_count.value==19,'sampler wrote rodata'
        category_counts[category]+=1
        points.append(actual_point)
    for row in records:
        a,b=row[:2],row[2:4];dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
        normal=(-dz/length,dx/length);middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
        check(middle,'center',1)
        for sign in (-1,1):
            check(tuple(middle[k]+sign*normal[k]*9.98 for k in range(2)),'inner_edge',1)
            p=tuple(middle[k]+sign*normal[k]*10.02 for k in range(2))
            check(p,'outer_edge')
        check(a,'junction',1);check(b,'junction',1)
        # The independently classified endpoint circle can also overlap another
        # legitimate segment; test the union rather than assuming isolated caps.
        for end in (a,b):
            for offset in ((9.98,0),(-9.98,0),(0,9.98),(0,-9.98)):
                check((end[0]+offset[0],end[1]+offset[1]),'end_cap',1)
    for p in ((1000,1290),(2400,1290),(2400,1310),(7000,6510)):
        check(p,'inner_edge',1) # exact inclusive boundaries on axis-aligned roads
    for p in ((500,500),(4000,1300),(4000,3900),(4000,6500),(2800,3570),(5200,1570),(8000,8000),(0,0)):
        check(p,'offroad',0)
    for x in (3200,4000,4800):
        for z in (0,4000,8000):check((x,z),'cusp')
    rng=random.Random(20261006)
    for _ in range(2500):
        point=(rng.uniform(0,8000),rng.uniform(0,8000))
        # Avoid a few ULPs around boundaries when comparing a float32 closest
        # point calculation with independent double precision geometry.
        if min(abs(point_segment(point,r[:2],r[2:4])-r[4]) for r in records)<.003:continue
        check(point,'random')
    invalid=[]
    for point in ((math.nan,1000),(1000,math.nan),(math.inf,1000),(1000,-math.inf),(-.001,1000),(1000,-.001),(8000.001,1000),(1000,8000.001)):
        data=(C.c_float*5)(*point,123,123,123)
        assert lib.test_surface(data)==-1
        assert bytes(data)[8:]==b'\0'*12,'invalid outputs not canonical zero'
        assert bytes(road_blob)==initial_roads
        invalid.append(str(point))
    obstacle_count=C.c_uint.in_dll(lib,'terrain_obstacle_count').value
    obstacles=(C.c_float*(obstacle_count*8)).in_dll(lib,'terrain_obstacles')
    boxes=[tuple(obstacles[i*8:i*8+4]) for i in range(obstacle_count)]
    # Exact segment/rectangle distance: intersections give zero, otherwise the
    # minimum endpoint-to-box or corner-to-segment distance. Capsule radius is
    # paved half-width + largest current ground hull radius, 4.49m.
    def point_box(p,box):
        return math.hypot(max(box[0]-p[0],0,p[0]-box[2]),max(box[1]-p[1],0,p[1]-box[3]))
    def segment_box(a,b,box):
        low,high=0.,1.
        for index,mn,mx in ((0,box[0],box[2]),(1,box[1],box[3])):
            delta=b[index]-a[index]
            if delta==0:
                if not mn<=a[index]<=mx:break
            else:
                t0,t1=(mn-a[index])/delta,(mx-a[index])/delta
                low=max(low,min(t0,t1));high=min(high,max(t0,t1))
                if low>high:break
        else:return 0.
        corners=((box[0],box[1]),(box[0],box[3]),(box[2],box[1]),(box[2],box[3]))
        return min(point_box(a,box),point_box(b,box),*(point_segment(p,a,b) for p in corners))
    minimum_clearance=math.inf
    for row in records:
        radius=row[4]+4.49
        assert all(radius<=value<=8000-radius for value in row[:4]),('map inset',row)
        for box in boxes:
            clearance=segment_box(row[:2],row[2:4],box)-radius
            assert clearance>0,('road+hull intersects actual solid',row,box,clearance)
            minimum_clearance=min(minimum_clearance,clearance)
    # Reject complete malformed inputs before either previously generated output
    # is touched. Exercise the actual command and imported development API.
    cases=[]
    def malformed(name,modify):
        document=json.loads(SOURCE.read_text());modify(document);cases.append((name,document))
    malformed('version',lambda d:d.update(version=2))
    malformed('empty',lambda d:d.update(roads=[]))
    malformed('count20',lambda d:d['roads'].append(d['roads'][0]))
    malformed('nan',lambda d:d['roads'][-1]['from'].__setitem__(0,math.nan))
    malformed('infinity',lambda d:d['roads'][-1]['to'].__setitem__(1,math.inf))
    malformed('outside',lambda d:d['roads'][-1]['to'].__setitem__(1,8000.01))
    malformed('negative',lambda d:d['roads'][-1]['from'].__setitem__(0,-1))
    malformed('zero_width',lambda d:d['roads'][-1].update(half_width=0))
    malformed('negative_width',lambda d:d['roads'][-1].update(half_width=-1))
    malformed('nan_width',lambda d:d['roads'][-1].update(half_width=math.nan))
    malformed('float_underflow_width',lambda d:d['roads'][-1].update(half_width=1e-80))
    malformed('zero_segment',lambda d:d['roads'][-1].update(to=d['roads'][-1]['from'][:]))
    malformed('rounded_zero_segment',lambda d:d['roads'][-1].update(to=[7000.000001,3900]))
    malformed('bad_flags',lambda d:d['roads'][-1].update(flags=3))
    malformed('bool_flags',lambda d:d['roads'][-1].update(flags=True))
    malformed('bool_coordinate',lambda d:d['roads'][-1]['from'].__setitem__(0,True))
    malformed('wrong_endpoint_shape',lambda d:d['roads'][-1].update(to=[7000]))
    malformed('unknown_field',lambda d:d['roads'][-1].update(extra=1))
    malformed('huge_integer',lambda d:d['roads'][-1]['from'].__setitem__(0,10**400))
    malformed('string_coordinate',lambda d:d['roads'][-1]['from'].__setitem__(0,'1000'))
    malformed('non_list_roads',lambda d:d.update(roads={'wrong':1}))
    malformed('bool_version',lambda d:d.update(version=True))
    malformed('float_flags',lambda d:d['roads'][-1].update(flags=1.0))
    malformed('huge_width',lambda d:d['roads'][-1].update(half_width=1e38))
    malformed('tiny_width',lambda d:d['roads'][-1].update(half_width=1e-30))
    malformed('tiny_nonzero_segment',lambda d:d['roads'][-1].update({'from':[0,0],'to':[1e-30,0]}))
    malformed('below_minimum_segment',lambda d:d['roads'][-1].update({'from':[0,0],'to':[.0009,0]}))
    out_nasm=directory/'old.inc';out_glsl=directory/'old.glsl';bad_source=directory/'bad.json'
    for name,document in cases:
        out_nasm.write_bytes(b'old nasm output\n');out_glsl.write_bytes(b'old glsl output\n')
        bad_source.write_text(json.dumps(document))
        result=subprocess.run([sys.executable,str(GENERATOR),'--source',str(bad_source),'--nasm',str(out_nasm),'--glsl',str(out_glsl)],capture_output=True)
        assert result.returncode==2,(name,result.stdout,result.stderr)
        assert out_nasm.read_bytes()==b'old nasm output\n' and out_glsl.read_bytes()==b'old glsl output\n',('partial malformed publication',name)
    # Exact lower arithmetic bounds remain supported; upper width is finite
    # when squared. These controls prove the guard is a range check, not a
    # rejection of every unfamiliar authored record.
    for width in (.001,8000):
        document={'version':1,'roads':[{'from':[0,0],'to':[.001,0],'half_width':width,'flags':1}]}
        accepted=generator.validate(document)
        assert len(accepted)==1 and accepted[0][2]>0 and accepted[0][4]>0
    # Deterministic output bytes through a separate real generation invocation.
    subprocess.run([sys.executable,str(GENERATOR),'--source',str(SOURCE),'--nasm',str(out_nasm),'--glsl',str(out_glsl)],check=True,capture_output=True)
    assert out_nasm.read_bytes()==NASM.read_bytes() and out_glsl.read_bytes()==GLSL.read_bytes()
    glsl_validator=shutil.which('glslangValidator')
    glsl_checked=False
    if glsl_validator:
        shader=directory/'roads.frag'
        shader.write_text('#version 450 core\n'+GLSL.read_text()+'\nlayout(location=0) out vec4 c;void main(){c=vec4(terrainRoadContains(gl_FragCoord.xy)?1.:0.);}\n')
        subprocess.run([glsl_validator,'-S','frag',str(shader)],check=True,capture_output=True)
        glsl_checked=True
    print(json.dumps({'suite':'terrain-surface','passed':True,'road_records':19,'samples_by_category':category_counts,'invalid_inputs':len(invalid),
                      'height_matches_real_terrain_bitwise':True,'sysv_preservation':True,'readonly_road_bytes':True,
                      'minimum_road_plus_4_49m_hull_solid_clearance':minimum_clearance,'map_inset_clear':True,
                      'malformed_generator_rejections':len(cases),'generated_bytes_deterministic':True,'canonical_nasm_glsl_records_equal':True,'glsl_helper_compiled':glsl_checked,
                      'limitations':['Center-surface classification only; no footprint traction or conservative slope clearance.',
                                     'Ridge cusp derivative is explicitly chosen, not a physical grade acceptance.',
                                     'Sampler and generated GLSL helper are not yet wired to production runtime or renderer.',
                                     'No road speed, navigation preference, terrain-profile, network or full-scale acceptance claim.']}))
