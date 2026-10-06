#!/usr/bin/env python3
"""Independent actual NASM raised relief component proof, development only."""
import copy,ctypes as C,hashlib,importlib.util,json,math,os,pathlib,random,re,shutil,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief_generator',ROOT/'tools/terrain_relief.py');gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
doc=json.loads((ROOT/'content/terrain/relief.json').read_text());rows=gen.validate(doc);record=rows[0]
assert gen.generate(ROOT/'content/terrain/relief.json',ROOT/'schemas/terrain_relief_data.inc',ROOT/'shaders/terrain_relief.glsl',True)==1
nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def factor(p,b):
    if p<=b[0] or p>=b[3]:return 0.,0.
    if p==b[1] or p==b[2]:return 1.,0.
    if p<b[1]:return (p-b[0])/(b[1]-b[0]),1/(b[1]-b[0])
    if p>b[2]:return (b[3]-p)/(b[3]-b[2]),-1/(b[3]-b[2])
    return 1.,0.
def oracle(x,z):
    fx,dx=factor(x,record[:4]);fz,dz=factor(z,record[4:8]);h=record[8]
    return fx*fz*h,dx*fz*h,fx*dz*h
with tempfile.TemporaryDirectory(prefix='rh-terrain-relief-') as td:
    td=pathlib.Path(td);objs=[]
    for source in ('src/nav/terrain_relief.asm','tests/probe_terrain_relief.asm'):
        obj=td/(pathlib.Path(source).stem+'.o');subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],check=True);objs.append(str(obj))
    so=td/'relief.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True)
    lib=C.CDLL(str(so));lib.test_terrain_relief.argtypes=[C.c_float,C.c_float,C.c_void_p];lib.test_terrain_relief.restype=C.c_int
    data=(C.c_ubyte*40).in_dll(lib,'terrain_relief_fields');count=C.c_uint.in_dll(lib,'terrain_relief_count')
    assert count.value==1 and bytes(data)==struct.pack('<9fI',*record)
    before=bytes(data)+struct.pack('<I',count.value)
    class Result(C.Structure):_fields_=[('h',C.c_float),('dx',C.c_float),('dz',C.c_float),('status',C.c_int)]
    def query(x,z):
        result=Result();assert lib.test_terrain_relief(x,z,C.byref(result))==1,'nonvolatile ABI'
        return result
    points=[(0,0),(8000,8000),(5500,5200),(5440,5200),(5720,5200)]
    xs=[0.,8000.,5400.,5480.,5620.,5820.];zs=[0.,8000.,4800.,5000.,5400.,5600.]
    for x in record[:4]:xs.extend([f32(x-.01),f32(x+.01)])
    for z in record[4:8]:zs.extend([f32(z-.01),f32(z+.01)])
    points.extend((x,z) for x in xs for z in zs)
    rng=random.Random(98433)
    points.extend((f32(rng.uniform(5300,5900)),f32(rng.uniform(4700,5700))) for _ in range(5000))
    points.extend((f32(rng.uniform(0,8000)),f32(rng.uniform(0,8000))) for _ in range(1000))
    maximum_error=[0.,0.,0.]
    for x,z in points:
        r=query(x,z);expected=oracle(x,z);assert r.status==0
        for i,(actual,want) in enumerate(zip((r.h,r.dx,r.dz),expected)):
            maximum_error[i]=max(maximum_error[i],abs(actual-want))
            assert math.isclose(actual,want,abs_tol=1e-5,rel_tol=2e-6),(x,z,i,actual,want)
        assert 0<=r.h<=64.00001
    invalid=[]
    for bad in (math.nan,math.inf,-math.inf,-1,8001):invalid.extend([(bad,5200),(5500,bad)])
    for x,z in invalid:
        r=query(x,z);assert r.status==-1 and bytes(r)[:12]==bytes(12)
    assert bytes(data)+struct.pack('<I',count.value)==before,'readonly field mutated'
    steep=query(5440,5200);gentle=query(5720,5200);peak=query(5500,5200);corner=query(5479,4999)
    assert abs(corner.dx-.796)<1e-6 and abs(corner.dz-.316)<1e-6
    assert peak.h==64 and abs(steep.dx-.8)<1e-6 and abs(gentle.dx+.32)<1e-6
    continuity=[]
    for axis,breaks,other in ((0,record[:4],5200),(1,record[4:8],5500)):
        for edge in breaks:
            samples=[]
            for delta in (-.01,0,.01):
                p=[other,other];p[axis]=f32(edge+delta);samples.append(query(*p))
            assert max(r.h for r in samples)-min(r.h for r in samples)<.009
            assert (samples[1].dx if axis==0 else samples[1].dz)==0
            continuity.append({'axis':axis,'break':edge,'heights':[r.h for r in samples]})
    # Exact generated constants must match canonical floats and assembled bytes.
    nasm_text=(ROOT/'schemas/terrain_relief_data.inc').read_text();values=nasm_text.split(' dd ')[-1].strip().split(',')
    assert struct.pack('<9fI',*[float(v) for v in values[:9]],int(values[9]))==before[:40]
    glsl=(ROOT/'shaders/terrain_relief.glsl').read_text()
    for label,values in (('terrainReliefX',record[:4]),('terrainReliefZ',record[4:8])):
        text=re.search(label+r'=vec4\(([^)]+)\)',glsl).group(1)
        assert struct.pack('<4f',*[float(v) for v in text.split(',')])==struct.pack('<4f',*values)
    assert f32(float(re.search(r'terrainReliefHeight=([^;]+);',glsl).group(1)))==record[8]
    assert 'terrainReliefFlags=1u;' in glsl and 'terrainReliefCount=1;' in glsl
    compiler=shutil.which('glslangValidator');assert compiler,'GLSL compiler required for component proof'
    shader=td/'relief.comp';shader.write_text('#version 450 core\n'+glsl+'\nlayout(local_size_x=1) in; layout(std430,binding=0) buffer O { vec4 o; }; void main(){ o=vec4(terrainRelief(vec2(5440.,5200.)),1.); }\n')
    subprocess.run([compiler,'-S','comp',str(shader)],check=True,capture_output=True,text=True)
    source=td/'source.json';nasm_out=td/'data.inc';glsl_out=td/'data.glsl';source.write_text(json.dumps(doc))
    gen.generate(source,nasm_out,glsl_out);original=(nasm_out.read_bytes(),glsl_out.read_bytes())
    gen.generate(source,nasm_out,glsl_out);assert original==(nasm_out.read_bytes(),glsl_out.read_bytes())
    bad_docs=[None,[],{}, {'schema':1,'fields':[]},{'schema':1,'fields':[doc['fields'][0]]*2}]
    for value in (True,0,2,1.0,'1'):
        d=copy.deepcopy(doc);d['schema']=value;bad_docs.append(d)
    for key in ('extra',):
        d=copy.deepcopy(doc);d[key]=1;bad_docs.append(d);d=copy.deepcopy(doc);d['fields'][0][key]=1;bad_docs.append(d)
    for axis in ('x','z'):
        for value in (None,{},[1,2,3],['bad',5480,5620,5820],[True,5480,5620,5820],[-1,5480,5620,5820],[5400,5480,5620,8001],[5400,5400.5,5620,5820],[5400,5400+1e-5,5620,5820],[5400,5480,5620,5620.5],[5400,5480,5470,5820],[5400,5480,5620,math.inf],[math.nan,5480,5620,5820]):
            d=copy.deepcopy(doc);d['fields'][0][axis]=value;bad_docs.append(d)
    for value in (True,0,-1,1001,math.nan,math.inf,1e40,1e-50,'64'):
        d=copy.deepcopy(doc);d['fields'][0]['height']=value;bad_docs.append(d)
    for value in (True,0,2,1.,'1'):
        d=copy.deepcopy(doc);d['fields'][0]['flags']=value;bad_docs.append(d)
    for d in bad_docs:
        source.write_text(json.dumps(d))
        try:gen.generate(source,nasm_out,glsl_out)
        except ValueError:pass
        else:raise AssertionError(('malformed relief accepted',d))
        assert original==(nasm_out.read_bytes(),glsl_out.read_bytes()),'malformed generator changed output'
    # Deliberate actual NASM fault candidates establish observer sensitivity.
    # They are development-only private artifacts; production outputs stay intact.
    controls=[]
    runtime_source=(ROOT/'src/nav/terrain_relief.asm').read_text()
    mutants={
        'flat-missing-relief':runtime_source.replace(' test dword [terrain_relief_fields+RELIEF_FLAGS],RELIEF_ACTIVE',' jmp .empty\n test dword [terrain_relief_fields+RELIEF_FLAGS],RELIEF_ACTIVE'),
        'rising-gradient-sign-inverted':runtime_source.replace(' movss xmm2,[one]\n divss xmm2,xmm1',' movss xmm2,[zero]\n subss xmm2,[one]\n divss xmm2,xmm1')}
    for name,text in mutants.items():
        source=td/(name+'.asm');source.write_text(text);obj=td/(name+'.o');bad_so=td/(name+'.so')
        subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(source),'-o',str(obj)],check=True)
        subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(obj),objs[1],'-o',str(bad_so)],check=True)
        candidate=C.CDLL(str(bad_so));candidate.test_terrain_relief.argtypes=[C.c_float,C.c_float,C.c_void_p];candidate.test_terrain_relief.restype=C.c_int
        result=Result();assert candidate.test_terrain_relief(5440,5200,C.byref(result))==1
        expected=oracle(5440,5200)
        faulty=[i for i,(actual,want) in enumerate(zip((result.h,result.dx,result.dz),expected)) if not math.isclose(actual,want,abs_tol=1e-5,rel_tol=2e-6)]
        assert faulty,('causal negative failed to expose defect',name)
        controls.append({'name':name,'rejected_components':faulty,'observed':[result.h,result.dx,result.dz],'expected':expected,'library_sha256':hashlib.sha256(bad_so.read_bytes()).hexdigest()})
    print(json.dumps({'suite':'terrain-relief-component','passed':True,'runtime':'actual NASM x86-64 SSE2, Python development observer','causal_negative_controls':controls,'combined_corner_gradient':[corner.dx,corner.dz],'combined_corner_degrees':math.degrees(math.atan(math.hypot(corner.dx,corner.dz))),'valid_samples':len(points),'invalid_samples':len(invalid),'generator_rejections':len(bad_docs),'maximum_absolute_error':maximum_error,'peak_height':peak.h,'steep_gradient':steep.dx,'steep_degrees':math.degrees(math.atan(abs(steep.dx))),'gentle_gradient':gentle.dx,'gentle_degrees':math.degrees(math.atan(abs(gentle.dx))),'continuity':continuity,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'src/nav/terrain_relief.asm').read_bytes()).hexdigest(),'glsl':'actual GLSL450 compute-helper compilation; no rendering/GPU execution claim','scope':'isolated stateless component; no world terrain, navigation, grade clearance, surface/motion, protocol, scale or visual acceptance'},sort_keys=True))
