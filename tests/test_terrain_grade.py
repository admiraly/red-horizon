#!/usr/bin/env python3
"""Independent whole-body grade evidence using actual NASM; development only."""
import ctypes as C
import hashlib,json,math,os,random,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'content/terrain/relief.json'
GEN=ROOT/'tools/terrain_grade.py'
OUTPUT=ROOT/'schemas/terrain_grade_data.inc'
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
field=json.loads(SOURCE.read_text())['fields'][0]
xs=list(map(f32,field['x']));zs=list(map(f32,field['z']));height=f32(field['height'])
radii=tuple(map(f32,(.551,3.551,4.491)))
limits=(1.,.49029059656570206,.21744283205399903)
# Compute gradients directly from the piecewise field factors, independently of
# generated coefficients and the runtime's cross-term representation.
def factor(p,breaks,piece):
    if piece==0:return (p-breaks[0])/(breaks[1]-breaks[0]),1/(breaks[1]-breaks[0])
    if piece==1:return 1.,0.
    return (breaks[3]-p)/(breaks[3]-breaks[2]),-1/(breaks[3]-breaks[2])
def norm(x,z,ix,iz,h=height):
    fx,dx=factor(x,xs,ix);fz,dz=factor(z,zs,iz)
    gx=.000002*(x-4000)+h*dx*fz
    gz=.000001*(z-4000)+h*fx*dz
    return gx*gx+gz*gz

def reference(role,points,radius=None,h=height):
    if role not in range(4) or any(not math.isfinite(v) or not 0<=v<=8000 for v in points):return -1
    if role==3:return 1
    radius=radii[role] if radius is None else radius
    sx,sz,ex,ez=points
    xa,za,xb,zb=min(sx,ex)-radius,min(sz,ez)-radius,max(sx,ex)+radius,max(sz,ez)+radius
    if xa<0 or za<0 or xb>8000 or zb>8000:return 0
    for ix in range(3):
        for iz in range(3):
            x0,x1=max(xa,xs[ix]),min(xb,xs[ix+1])
            z0,z1=max(za,zs[iz]),min(zb,zs[iz+1])
            if x0>x1 or z0>z1:continue
            if any(norm(x,z,ix,iz,h)+1e-6>limits[role] for x in (x0,x1) for z in (z0,z1)):return 0
    return 1
subprocess.run([sys.executable,str(GEN),'--check'],check=True,capture_output=True)
with tempfile.TemporaryDirectory(prefix='rh-terrain-grade-') as temporary:
    temporary=Path(temporary)
    nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
    def build(name,source=None,table=None):
        folder=temporary/name;folder.mkdir();(folder/'schemas').mkdir()
        if table is not None:(folder/'schemas/terrain_grade_data.inc').write_text(table)
        asm=folder/'grade.asm';asm.write_text(source if source is not None else (ROOT/'src/nav/terrain_grade.asm').read_text())
        objects=[]
        for src in (asm,ROOT/'tests/probe_terrain_grade.asm'):
            output=folder/(src.stem+'.o')
            subprocess.run([nasm,'-f','elf64','-I',str(folder)+'/', '-I',str(ROOT)+'/',str(src),'-o',str(output)],cwd=folder,check=True)
            objects.append(str(output))
        so=folder/'grade.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True)
        lib=C.CDLL(str(so));lib.test_grade.argtypes=[C.c_uint,C.POINTER(C.c_float)];lib.test_grade.restype=C.c_int
        return lib,hashlib.sha256(so.read_bytes()).hexdigest()
    lib,library_sha=build('actual')
    count=C.c_uint.in_dll(lib,'terrain_grade_count');blob=(C.c_byte*(9*64)).in_dll(lib,'terrain_grade_facets')
    initial=bytes(blob);assert count.value==9
    # Check assembled records against independent canonical polynomial expansion.
    expected=[]
    for ix in range(3):
        for iz in range(3):
            x=xs[ix];z=zs[iz]
            fx,kx=factor(x,xs,ix);fz,kz=factor(z,zs,iz)
            mx=fx-kx*x;mz=fz-kz*z
            expected.append((*xs[ix:ix+1],z,xs[ix+1],zs[iz+1],height*kx*kz,height*kx*mz,height*kz*mx,1))
    for i,row in enumerate(expected):
        actual=struct.unpack_from('<7dQ',initial,i*64)
        assert actual[:4]==row[:4] and actual[7]==1
        assert all(abs(actual[k]-row[k])<=1e-12 for k in range(4,7)),('coefficient',actual,row)
    counts={'clear':0,'blocked':0,'invalid':0}
    cases=[]
    def check(role,points,expected=None,name='random'):
        data=(C.c_float*4)(*points);before=bytes(data);values=tuple(data)
        result=lib.test_grade(role,data)
        if expected is None:expected=reference(role,values)
        assert result==expected,('grade or ABI',name,role,values,result,expected)
        assert bytes(data)==before and bytes(blob)==initial and count.value==9,'grade sampler wrote caller/rodata'
        counts[{-1:'invalid',0:'blocked',1:'clear'}[result]]+=1
        if name!='random':cases.append({'name':name,'role':role,'points':list(map(str,values)),'result':result})
    for role in range(4):
        for points in ((1000,1000,1200,1300),(3200,4000,4800,4000),(6000,5200,6100,5200)):
            check(role,points,1,'shallow_base')
        check(role,(5440,5200,5440,5200),1 if role in (0,3) else 0,'steep_ramp')
        check(role,(5390,5200,5390,5200),1,'intermediate_start_clear')
        check(role,(5500,5200,5500,5200),1,'intermediate_end_clear')
        check(role,(5390,5200,5500,5200),1 if role in (0,3) else 0,'intermediate_steep')
        check(role,(5480,5200,5480,5200),1 if role in (0,3) else 0,'closed_cusp_both_sides')
        check(role,(5750,5200,5750,5200),1,'gentle_east_approach')
        check(role,(5560,4900,5560,4900),1,'gentle_south_approach')
        check(role,(0,0,8000,8000),1 if role==3 else 0,'map_footprint_bounds')
    for role in (1,2):
        check(role,(5482,5200,5482,5200),0,'footprint_center_plateau')
        assert reference(role,(5482,5200,5482,5200),radius=0)==1,'center-only negative setup'
    check(2,(5448,4908,5448,4908),0,'combined_gradient_corner')
    gx=.000002*(5448-4000)+height*(1/80)*((4908-4800)/200)
    gz=.000001*(4908-4000)+height*((5448-5400)/80)*(1/200)
    assert gx*gx<limits[2] and gz*gz<limits[2] and gx*gx+gz*gz>limits[2]
    for role in range(4):
        for axis in range(4):
            for value in (math.nan,math.inf,-math.inf,-.001,8000.001):
                values=[5500,5200,5600,5300];values[axis]=value;check(role,values,-1,'invalid_coordinate')
    for role in (4,0xffffffff):check(role,(5500,5200,5600,5300),-1,'invalid_role')
    rng=random.Random(20261006)
    for _ in range(4000):
        role=rng.randrange(4)
        start=(rng.uniform(5380,5840),rng.uniform(4780,5620))
        end=(start[0]+rng.uniform(-35,35),start[1]+rng.uniform(-35,35))
        check(role,(*start,*end))
    # Equal-endpoint footprints across every breakpoint verify zero-length
    # sweeps still inspect all closed adjacent facets instead of a chosen side.
    for x in xs:
        for z in zs:
            for role in range(4):check(role,(x,z,x,z),name='all_breakpoint_cusps')
    # Actual causal variants isolate missing height and center-only grade bugs.
    original=(ROOT/'src/nav/terrain_grade.asm').read_text()
    center,_=build('center-control',source=original.replace('radii: dd BODY_INF_SWEEP_RADIUS,BODY_TANK_SWEEP_RADIUS,BODY_ARTY_SWEEP_RADIUS','radii: dd 0.0,0.0,0.0'))
    data=(C.c_float*4)(5482,5200,5482,5200)
    assert center.test_grade(1,data)==1 and lib.test_grade(1,data)==0
    flat_source=temporary/'flat.json';flat=json.loads(SOURCE.read_text());flat['fields'][0]['height']=.001;flat_source.write_text(json.dumps(flat))
    flat_table=temporary/'flat.inc';subprocess.run([sys.executable,str(GEN),'--source',str(flat_source),'--nasm',str(flat_table)],check=True,capture_output=True)
    flat_lib,_=build('flat-control',table=flat_table.read_text());data=(C.c_float*4)(5440,5200,5440,5200)
    assert flat_lib.test_grade(1,data)==1 and lib.test_grade(1,data)==0
    # A canonical float32 height places the worst footprint corner less than
    # 1e-6 below the tank cap. Actual guard blocks it; removing only the guard
    # in a private NASM causal control accepts it.
    cap=limits[1];bx=.000002*(5440+radii[1]-4000);bz=.000001*(5200+radii[1]-4000)
    guarded_height=f32(80*(math.sqrt(cap-bz*bz-.5e-6)-bx))
    guarded=json.loads(SOURCE.read_text());guarded['fields'][0]['height']=guarded_height
    path=temporary/'guarded.json';path.write_text(json.dumps(guarded));table=temporary/'guarded.inc'
    subprocess.run([sys.executable,str(GEN),'--source',str(path),'--nasm',str(table)],check=True,capture_output=True)
    with_guard,_=build('guarded',table=table.read_text())
    no_guard,_=build('unguarded-control',source=original.replace('guard: dq GRADE_GUARD_SQ','guard: dq 0.0'),table=table.read_text())
    data=(C.c_float*4)(5440,5200,5440,5200)
    assert with_guard.test_grade(1,data)==0 and no_guard.test_grade(1,data)==1,'guard not exercised at actual corner threshold'
    # Development generator: reject before replacing the old complete output.
    malformed=[]
    def bad(name,change):
        doc=json.loads(SOURCE.read_text());change(doc);malformed.append((name,doc))
    bad('schema',lambda d:d.update(schema=2))
    bad('extra',lambda d:d.update(extra=1))
    bad('empty',lambda d:d.update(fields=[]))
    bad('two_fields',lambda d:d['fields'].append(d['fields'][0]))
    bad('nan',lambda d:d['fields'][0]['x'].__setitem__(0,math.nan))
    bad('infinite',lambda d:d['fields'][0]['z'].__setitem__(3,math.inf))
    bad('offmap',lambda d:d['fields'][0]['x'].__setitem__(3,8001))
    bad('unordered',lambda d:d['fields'][0]['x'].__setitem__(1,5900))
    bad('short_ramp',lambda d:d['fields'][0]['x'].__setitem__(1,5400.5))
    bad('rounded_ramp',lambda d:d['fields'][0]['x'].__setitem__(1,5400.000001))
    bad('bad_flags',lambda d:d['fields'][0].update(flags=0))
    bad('bool_flags',lambda d:d['fields'][0].update(flags=True))
    bad('zero_height',lambda d:d['fields'][0].update(height=0))
    bad('huge_height',lambda d:d['fields'][0].update(height=1001))
    bad('tiny_height',lambda d:d['fields'][0].update(height=1e-99))
    bad('bool_number',lambda d:d['fields'][0]['x'].__setitem__(0,True))
    bad('unknown_field',lambda d:d['fields'][0].update(unknown=1))
    bad('ridge_intersection',lambda d:d['fields'][0].update(x=[3000,3300,4500,5000]))
    bad('ridge_interior',lambda d:d['fields'][0].update(x=[3300,3500,4300,4500]))
    output=temporary/'old.inc';bad_source=temporary/'bad.json'
    for name,doc in malformed:
        bad_source.write_text(json.dumps(doc));output.write_bytes(b'old complete output\n')
        result=subprocess.run([sys.executable,str(GEN),'--source',str(bad_source),'--nasm',str(output)],capture_output=True)
        assert result.returncode==2 and output.read_bytes()==b'old complete output\n',('generator partial update',name)
    subprocess.run([sys.executable,str(GEN),'--nasm',str(output)],check=True,capture_output=True)
    assert output.read_bytes()==OUTPUT.read_bytes(),'non-deterministic generation'
    output.write_text('stale')
    result=subprocess.run([sys.executable,str(GEN),'--nasm',str(output),'--check'],capture_output=True)
    assert result.returncode==2 and output.read_text()=='stale','stale check modifies output'
    # Exercise safety rejection of incompatible grade policy contracts in a
    # private tool tree. Root-owned contract files are never edited.
    miniature=temporary/'policy-control';(miniature/'tools').mkdir(parents=True);(miniature/'schemas').mkdir()
    shutil.copyfile(GEN,miniature/'tools/terrain_grade.py')
    shutil.copyfile(ROOT/'tools/terrain_relief.py',miniature/'tools/terrain_relief.py')
    contract=(ROOT/'schemas/terrain_grade.inc').read_text()
    policy_cases=(('GRADE_ARTY_LIMIT_SQ 0.21744283205399903','GRADE_ARTY_LIMIT_SQ 0.0001'),
                  ('GRADE_BASE_X 0.000002','GRADE_BASE_X 0.000003'),
                  ('GRADE_GUARD_SQ 0.000001','GRADE_GUARD_SQ -0.1'))
    for old,new in policy_cases:
        (miniature/'schemas/terrain_grade.inc').write_text(contract.replace(old,new))
        output.write_bytes(b'old complete policy output')
        result=subprocess.run([sys.executable,str(miniature/'tools/terrain_grade.py'),'--source',str(SOURCE),'--nasm',str(output)],capture_output=True)
        assert result.returncode==2 and output.read_bytes()==b'old complete policy output','unsafe base/cap/guard published'
    # Left-of-ridge support and coincident plateau breaks remain legitimate.
    for breaks in ([2500,2600,2700,3200],[4800,4900,4900,5100]):
        positive=json.loads(SOURCE.read_text());positive['fields'][0]['x']=breaks
        path=temporary/'positive.json';path.write_text(json.dumps(positive))
        subprocess.run([sys.executable,str(GEN),'--source',str(path),'--nasm',str(output)],check=True,capture_output=True)
    print(json.dumps({'suite':'terrain-grade','passed':True,'library_sha256':library_sha,'facets':9,'maximum_facet_corner_checks':36,
        'samples':counts,'named_cases':cases,'readonly_inputs_and_facets':True,'sysv_preservation':True,'canonical_assembled_coefficients':True,
        'malformed_generator_rejections':len(malformed),'incompatible_policy_rejections':len(policy_cases),'generated_bytes_deterministic':True,'stale_output_rejected':True,
        'actual_flat_and_center_only_controls_rejected':True,'actual_guard_threshold_control_rejected':True,'outside_relief_gradient_upper_bound':math.hypot(.0225,.004),
        'limits':['Expanded sweep AABB may conservatively block diagonal/corner paths.',
                  'Grade-valid relief support must stay outside ridge interior X3200..4800.',
                  'Standalone stateless helper; no world/body/navigation/render/build hook or scale acceptance.']}))
