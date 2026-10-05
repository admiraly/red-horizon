#!/usr/bin/env python3
"""Build and exercise the actual NASM body module against an independent double slab oracle."""
import ctypes as C, json, math, os, pathlib, random, struct, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm'))
with tempfile.TemporaryDirectory(prefix='rh-body-') as out:
    objs=[]
    for source in ('src/nav/terrain_body.asm','src/nav/terrain.asm','tests/terrain_body_probe.asm'):
        obj=pathlib.Path(out)/(pathlib.Path(source).stem+'.o');objs.append(str(obj))
        subprocess.run([nasm,'-f','elf64','-I',str(root/'schemas')+'/',str(root/source),'-o',str(obj)],check=True)
    library=pathlib.Path(out)/'body.so'
    subprocess.run(['gcc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(library)],check=True)
    lib=C.CDLL(str(library))
    lib.test_body_move.argtypes=[C.c_float]*5+[C.c_uint];lib.test_body_move.restype=C.c_uint64
    lib.test_body_blocked.argtypes=[C.c_float]*2+[C.c_uint]
    lib.test_body_path.argtypes=[C.c_float]*4+[C.c_uint]
    lib.test_body_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_body_hash.restype=C.c_uint64
    lib.test_body_abi.argtypes=[C.c_float]*5+[C.c_uint]
    lib.terrain_body_init()
    enabled=C.c_uint.in_dll(lib,'terrain_body_enabled')
    raw=(C.c_float*40).in_dll(lib,'terrain_obstacles');before=bytes(raw)
    boxes=[tuple(raw[i*8:i*8+4]) for i in range(5)]
    radii=(.55,3.55,4.49,0)
    def f(v):return C.c_float(v).value
    def move(p,g,s,k):return struct.unpack('<ff',struct.pack('<Q',lib.test_body_move(*p,*g,s,k)))
    def blocked(p,k):
        r=radii[k]
        return not all(r<=v<=8000-r for v in p) or (k!=3 and any(a-r<=p[0]<=c+r and b-r<=p[1]<=d+r for a,b,c,d in boxes))
    def hit(p,q,box,r):
        low,high=0.,1.
        for x,y,a,b in ((p[0],q[0],box[0]-r,box[2]+r),(p[1],q[1],box[1]-r,box[3]+r)):
            delta=y-x
            if delta==0:
                if not a<=x<=b:return False
            else:
                first,last=sorted(((a-x)/delta,(b-x)/delta));low=max(low,first);high=min(high,last)
                if low>high:return False
        return True
    def safe(p,g,s,k):
        q=move(p,g,s,k)
        assert math.dist(p,q)<=s+.001,(p,q,s,k)
        assert not blocked(q,k),(p,q,k,'endpoint')
        assert k==3 or not any(hit(p,q,b,radii[k]) for b in boxes),(p,q,k,'sweep')
        return q
    rng=random.Random(19381);samples=0
    for k in range(4):
        for _ in range(1500):
            p=tuple(f(v) for v in (rng.uniform(2500,5500),rng.uniform(500,7000)))
            q=tuple(f(v) for v in (rng.uniform(2500,5500),rng.uniform(500,7000)))
            expected=not blocked(p,k) and not blocked(q,k) and (k==3 or not any(hit(p,q,b,radii[k]) for b in boxes))
            assert bool(lib.test_body_path(*p,*q,k))==expected,(p,q,k)
            if not blocked(p,k):safe(p,q,rng.choice((.12,.2,.5,.6,1000,8000)),k);samples+=1
    routes=[]
    fixtures=[((3950.,1300.),(4050.,1300.)),((4050.,1300.),(3950.,1300.)),((4000.,1506.),(4050.,1000.)),((5243.89,1564.115),(3125.113,5204.443))]
    for k,s in ((0,.12),(1,.5),(2,.2),(1,.6)):
        for p,g in fixtures:
            p=tuple(map(f,p));g=tuple(map(f,g))
            for tick in range(math.ceil(8000/s)):
                p=safe(p,g,s,k)
                if math.dist(p,g)<.001:break
            assert math.dist(p,g)<.001,('route stalled',k,s,p,g)
            routes.append(tick+1)
    # Map inset, wall/front/side/corner rejection and invalid-start safe holding.
    for k in range(3):
        r=radii[k]
        for p in ((0,0),(3988-r/2,1300),(4000,1500+r/2),(3988-r/2,1100-r/2)):
            assert lib.test_body_blocked(*p,k)==1
            assert move(p,(4500,1800),.6,k)==tuple(map(f,p))
        p=(r+1,r+1)
        for _ in range(20):p=safe(p,(0,0),.6,k)
        assert p[0]>=r and p[1]>=r
    for bad in (float('nan'),float('inf'),-float('inf'),-1,8001):
        assert lib.test_body_blocked(bad,1300,0)==1
        assert lib.test_body_path(3900,1300,bad,1300,0)==0
        assert move((3900,1300),(bad,1300),.5,0)==(3900,1300)
    for step in (-1,0,float('nan'),float('inf')):
        assert move((3900,1300),(4050,1300),step,1)==(3900,1300)
    assert lib.test_body_blocked(3900,1300,4)==1
    assert move((3900,1300),(4050,1300),.5,4)==(3900,1300)
    # Control proves formerly point-clear footprint penetration.
    assert lib.test_body_blocked(3986,1300,1)==1
    enabled.value=0
    assert lib.test_body_blocked(3986,1300,1)==0
    seed=14695981039346656037;prime=1099511628211
    def fnv(data):
        h=seed
        for b in data:h=((h^b)*prime)&((1<<64)-1)
        return h
    assert lib.test_body_hash(seed,prime)==fnv(struct.pack('<I',0))
    enabled.value=1
    assert lib.test_body_hash(seed,prime)==fnv(struct.pack('<I',1))
    for k in range(4):
        assert lib.test_body_abi(3950,1300,4050,1300,.6,k)==1
    # Nominal tangent is conservatively rejected; 2mm clearance remains passable.
    for k,r in enumerate(radii[:3]):
        assert lib.test_body_path(3970,1100-r,4030,1100-r,k)==0
        assert lib.test_body_path(3970,1100-r-.002,4030,1100-r-.002,k)==1
        p=(3970.,1100-r-.002)
        for _ in range(3000):
            p=safe(p,(4030,1100-r-.002),.12 if k==0 else .5 if k==1 else .2,k)
            if math.dist(p,(4030,1100-r-.002))<.001:break
        assert math.dist(p,(4030,1100-r-.002))<.001
    assert bytes(raw)==before
    print(json.dumps({'suite':'terrain-body','passed':True,'seed':19381,'random_sweeps':samples,'route_ticks':routes,'radii':radii,'invalid_start_policy':'safe hold','geometry':'expanded AABBs'}))
