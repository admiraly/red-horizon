#!/usr/bin/env python3
"""Independent integrated height/gradient and actual caller proof; development only."""
import ctypes as C,hashlib,json,math,os,pathlib,random,shutil,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
field=json.loads((ROOT/'content/terrain/relief.json').read_text())['fields'][0]
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def factor(p,b):
    if p<=b[0] or p>=b[3]:return 0.,0.
    if p==b[1] or p==b[2]:return 1.,0.
    if p<b[1]:return (p-b[0])/(b[1]-b[0]),1/(b[1]-b[0])
    if p>b[2]:return (b[3]-p)/(b[3]-b[2]),-1/(b[3]-b[2])
    return 1.,0.
def extra(x,z):
    a,da=factor(x,field['x']);b,db=factor(z,field['z']);h=field['height']
    return a*b*h,da*b*h,a*db*h
def base(x,z):return 12+(x-4000)**2*.000001+(z-4000)**2*.0000005+max(0,1-abs(x-4000)/800)*18
class Surface(C.Structure):_fields_=[('h',C.c_float),('dx',C.c_float),('dz',C.c_float),('road',C.c_int)]
class Entity(C.Structure):_fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','gen')]
class Projectile(C.Structure):_fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint) for n in ('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint) for n in ('source','gen','active','source_gen','reserved')]
class Event(C.Structure):_fields_=[(n,C.c_float) for n in ('x','y','z')]+[(n,C.c_uint) for n in ('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
class Player(C.Structure):_fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','gen')]
class Motion(C.Structure):_fields_=[('feet',C.c_float),('step',C.c_float)]+[(n,C.c_uint) for n in ('gen','latch','grounded','initialized')]+[('eye',C.c_float),('reserved',C.c_uint)]
class Air(C.Structure):_fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint) for n in ('role','mode','target','cooldown','ammo','gen')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[(n,C.c_uint) for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-terrain-height-') as td:
    td=pathlib.Path(td)
    def assemble(source,suffix=''):
        obj=td/(source.replace('/','_')+suffix+'.o');subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],check=True);return str(obj)
    sources=['src/nav/terrain.asm','src/nav/terrain_surface.asm','src/nav/terrain_relief.asm','tests/probe_terrain_height.asm']
    objs=[assemble(s) for s in sources];so=td/'height.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True)
    lib=C.CDLL(str(so));lib.test_terrain_height.argtypes=[C.c_float,C.c_float,C.c_void_p];lib.test_terrain_surface.argtypes=[C.c_float,C.c_float,C.c_void_p]
    def height(x,z):
        record=C.create_string_buffer(320);lib.test_terrain_height(x,z,record)
        assert struct.unpack_from('<15Q',record.raw,8)==tuple(0x123400+i for i in range(15)),'terrain_height GPR behavior changed'
        assert record.raw[128:320]==b''.join(struct.pack('<4I',*[(i+1)*101+j for j in range(4)]) for i in range(12)),'terrain_height XMM4..15 behavior changed'
        return struct.unpack_from('<f',record.raw)[0]
    def surface(x,z):r=Surface();lib.test_terrain_surface(x,z,C.byref(r));return r
    points=[(5440,5200),(5500,5200),(5720,5200),(5479,4999),(4000,4000),(3200,3900),(4800,3900)]
    for x in field['x']:
        for z in field['z']:
            for delta in (-.01,0,.01):points.append((f32(x+delta),f32(z+delta)))
    rng=random.Random(98434);points.extend((f32(rng.uniform(5300,5900)),f32(rng.uniform(4700,5700))) for _ in range(2500));points.extend((f32(rng.uniform(0,8000)),f32(rng.uniform(0,8000))) for _ in range(500))
    maximum=[0.,0.,0.]
    for x,z in points:
        e,dx,dz=extra(x,z);h=height(x,z);r=surface(x,z)
        assert h==r.h,'surface height disagrees with production terrain_height'
        wants=(base(x,z)+e,(x-4000)*.000002+(-.0225 if 4000<x<4800 else .0225 if 3200<x<4000 else 0)+dx,(z-4000)*.000001+dz)
        for i,(actual,want) in enumerate(zip((h,r.dx,r.dz),wants)):
            maximum[i]=max(maximum[i],abs(actual-want));assert math.isclose(actual,want,abs_tol=1.6e-5,rel_tol=3e-6),(x,z,i,actual,want)
    # Frozen exact legacy leaf for bitwise outside-relief and invalid behavior.
    # Fixed pre-integration leaf; deliberately independent of candidate source.
    old_source=td/'old-height.asm';old_source.write_text("""default rel
section .rodata
center: dd 4000.0
xscale: dd 0.000001
zscale: dd 0.0000005
ridge_scale: dd 0.00125
ridge_height: dd 18.0
base: dd 12.0
one: dd 1.0
zero: dd 0.0
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global old_height
old_height:
 subss xmm0,[center]
 subss xmm1,[center]
 movaps xmm2,xmm0
 andps xmm2,[abs_mask]
 mulss xmm2,[ridge_scale]
 movss xmm3,[one]
 subss xmm3,xmm2
 maxss xmm3,[zero]
 mulss xmm3,[ridge_height]
 mulss xmm0,xmm0
 mulss xmm0,[xscale]
 mulss xmm1,xmm1
 mulss xmm1,[zscale]
 addss xmm0,xmm1
 addss xmm0,[base]
 addss xmm0,xmm3
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
""")
    old_obj=td/'old.o';old_so=td/'old.so';subprocess.run([nasm,'-f','elf64',str(old_source),'-o',str(old_obj)],check=True);subprocess.run(['cc','-shared',str(old_obj),'-o',str(old_so)],check=True)
    legacy=C.CDLL(str(old_so));legacy.old_height.argtypes=[C.c_float,C.c_float];legacy.old_height.restype=C.c_float
    controls=[(0,0),(8000,8000),(-1,5200),(8001,5200),(5500,-1),(5500,8001),(math.nan,5200),(math.inf,5200),(-math.inf,5200),(5500,math.nan),(5500,math.inf)]
    for x,z in controls:
        oldh=legacy.old_height(x,z);newh=height(x,z)
        assert struct.pack('<f',oldh)==struct.pack('<f',newh),(x,z,oldh,newh)
        if not (math.isfinite(x) and math.isfinite(z) and 0<=x<=8000 and 0<=z<=8000):
            r=surface(x,z);assert r.road==-1 and bytes(r)[:12]==bytes(12)
    # Full production callers, not helper-derived mock movement.
    objects=[assemble(str(p.relative_to(ROOT)),'-world') for folder in ('sim','nav','ai','game') for p in sorted((ROOT/'src'/folder).glob('*.asm'))]
    world_so=td/'world.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-lm','-o',str(world_so)],check=True);world=C.CDLL(str(world_so))
    world.terrain_height.argtypes=[C.c_float,C.c_float];world.terrain_height.restype=C.c_float;world.terrain_los.argtypes=[C.c_float]*6
    entities=(Entity*32768).in_dll(world,'sim_entities');projectiles=(Projectile*512).in_dll(world,'sim_projectiles');events=(Event*256).in_dll(world,'sim_events');players=(Player*4).in_dll(world,'sim_players');motion=(Motion*4).in_dll(world,'player_motion');air=(Air*32768).in_dll(world,'sim_aircraft')
    def reset():
        assert world.sim_init(64,7)==0
        for e in entities[:64]:e.hp=0
        for side in (0,1):
            for front in range(3):world.sim_order(side,front,1)
        C.c_uint.in_dll(world,'hazard_enabled').value=0
    # A real production shell launch travels toward the plateau. Its muzzle and
    # collision impact must use raised heights, while no enemy actor supplies contact.
    reset();e=entities[0];e.x,e.z,e.hp,e.kind,e.side=5430,5200,400,1,0;world.projectile_init()
    world.projectile_launch.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float,C.c_float]
    source_height=world.terrain_height(e.x,e.z)
    assert world.projectile_launch(0,1,5550,world.terrain_height(5550,5200)+1,5200)==0
    active=next(p for p in projectiles if p.active);assert abs(active.y-(source_height+3))<1e-5
    impact=None
    for tick in range(100):
        world.projectile_tick()
        found=[ev for ev in events if ev.sequence and ev.kind==3]
        if found:impact=found[-1];break
    assert impact is not None and impact.y>base(impact.x,impact.z)+10,'raised ground not used by actual projectile collision'
    assert abs(impact.y-world.terrain_height(impact.x,impact.z))<.05,(impact.x,impact.y,impact.z,world.terrain_height(impact.x,impact.z))
    impact_observed=[impact.x,impact.y,impact.z]
    assert world.terrain_los(5360,40,5200,5860,40,5200)==0
    assert world.terrain_los(5360,110,5200,5860,110,5200)==1
    # Actual grounded player update establishes foot and eye on the raised plateau.
    reset();assert world.player_join(0,0)==0
    p=players[0];p.x,p.z,p.y=5500,5200,world.terrain_height(5500,5200)+1.8
    world.player_tick();assert abs(motion[0].feet-world.terrain_height(p.x,p.z))<1e-5
    assert abs(p.y-motion[0].feet-1.8)<1e-5 and motion[0].grounded==1
    player_feet_observed=motion[0].feet
    player_eye_observed=p.y
    # Actual continuously flying bomber crosses the new hill with bounded vertical
    # motion. Clearance is measured against authority, not assigned from a formula.
    reset();e=entities[15];e.x,e.z,e.hp,e.kind,e.side,e.front,e.target=5360,5200,200,3,0,0,0xffffffff;world.air_init()
    minimum=math.inf;raised_samples=0;previous_y=None;flight=[]
    for tick in range(110):
        old=(e.x,e.z);world.air_tick();ground=world.terrain_height(e.x,e.z);clearance=air[15].y-ground;minimum=min(minimum,clearance)
        assert clearance>40 and abs(math.dist(old,(e.x,e.z))-5)<.001
        if previous_y is not None:assert abs(air[15].y-previous_y)<=.5001
        if extra(e.x,e.z)[0]>50:raised_samples+=1
        previous_y=air[15].y
        if tick%20==0:flight.append([e.x,e.z,air[15].y,ground,clearance])
    assert raised_samples>5
    print(json.dumps({'suite':'terrain-height-integration','passed':True,'valid_samples':len(points),'legacy_bitwise_controls':len(controls),'protected_GPRs':15,'protected_XMM_registers':list(range(4,16)),'maximum_absolute_errors':maximum,'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources},'height_library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'world_library_sha256':hashlib.sha256(world_so.read_bytes()).hexdigest(),'projectile_impact':impact_observed,'projectile_muzzle_height':source_height+3,'player_feet':player_feet_observed,'player_eye':player_eye_observed,'minimum_bomber_clearance':minimum,'raised_air_samples':raised_samples,'flight_samples':flight,'scope':'actual authoritative height/gradient/LOS/projectile/player/aircraft paths; no grade traversal/nav bypass/render/net/scale acceptance'},sort_keys=True))
