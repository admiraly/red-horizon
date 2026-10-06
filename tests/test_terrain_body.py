#!/usr/bin/env python3
"""Build and exercise the actual NASM body module against an independent double slab oracle."""
import ctypes as C, json, math, os, pathlib, random, struct, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm'))
with tempfile.TemporaryDirectory(prefix='rh-body-') as out:
    objs=[]
    for source in ('src/nav/terrain_body.asm','src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/terrain_grade.asm','tests/terrain_body_probe.asm'):
        obj=pathlib.Path(out)/(pathlib.Path(source).stem+'.o');objs.append(str(obj))
        subprocess.run([nasm,'-f','elf64','-I',str(root/'schemas')+'/',str(root/source),'-o',str(obj)],check=True)
    library=pathlib.Path(out)/'body.so'
    subprocess.run(['gcc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(library)],check=True)
    lib=C.CDLL(str(library))
    lib.test_body_move.argtypes=[C.c_float]*5+[C.c_uint];lib.test_body_move.restype=C.c_uint64
    lib.test_body_step.argtypes=[C.c_float]*5+[C.c_uint];lib.test_body_step.restype=C.c_uint64
    lib.test_body_blocked.argtypes=[C.c_float]*2+[C.c_uint]
    lib.test_body_path.argtypes=[C.c_float]*4+[C.c_uint]
    lib.test_body_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_body_hash.restype=C.c_uint64
    lib.test_body_abi.argtypes=[C.c_float]*5+[C.c_uint]
    lib.test_body_step_abi.argtypes=[C.c_float]*5+[C.c_uint]
    lib.terrain_body_init()
    enabled=C.c_uint.in_dll(lib,'terrain_body_enabled')
    raw=(C.c_float*40).in_dll(lib,'terrain_obstacles');before=bytes(raw)
    boxes=[tuple(raw[i*8:i*8+4]) for i in range(5)]
    radii=(.55,3.55,4.49,0)
    def f(v):return C.c_float(v).value
    def move(p,g,s,k):return struct.unpack('<ff',struct.pack('<Q',lib.test_body_move(*p,*g,s,k)))
    def controller(p,g,s,k):return struct.unpack('<ff',struct.pack('<Q',lib.test_body_step(*p,*g,s,k)))
    field=json.loads((root/'content/terrain/relief.json').read_text())['fields'][0]
    def grade_safe(p,q,k):
        if k in (0,3):return True # canonical max<45deg; air bypasses ground
        r=f((.551,3.551,4.491)[k])
        low=[min(a,b)-r for a,b in zip(p,q)];high=[max(a,b)+r for a,b in zip(p,q)]
        xs,zs=field['x'],field['z']
        if high[0]<xs[0] or low[0]>xs[-1] or high[1]<zs[0] or low[1]>zs[-1]:return True
        # Independent factor/one-sided derivative evaluation at all rectangle
        # and field breaks; no generated coefficients or production helper.
        def factor(v,axis):
            a,b,c,d=axis
            if v<a or v>d:return 0.,(0.,)
            if v==a:return 0.,(0.,1/(b-a))
            if v==b:return 1.,(1/(b-a),0.)
            if v==c:return 1.,(0.,-1/(d-c))
            if v==d:return 0.,(-1/(d-c),0.)
            if v<b:return (v-a)/(b-a),(1/(b-a),)
            if v>c:return (d-v)/(d-c),(-1/(d-c),)
            return 1.,(0.,)
        xc=sorted(set([max(low[0],xs[0]),min(high[0],xs[-1])]+[v for v in xs if low[0]<=v<=high[0]]))
        zc=sorted(set([max(low[1],zs[0]),min(high[1],zs[-1])]+[v for v in zs if low[1]<=v<=high[1]]))
        limit=math.tan(math.radians((45,35,25)[k]))**2
        for x in xc:
            fx,dxs=factor(x,xs)
            for z in zc:
                fz,dzs=factor(z,zs)
                for dx in dxs:
                    for dz in dzs:
                        gx=(x-4000)*f(.000002)+field['height']*dx*fz
                        gz=(z-4000)*f(.000001)+field['height']*fx*dz
                        if gx*gx+gz*gz+1e-6>limit:return False
        return True
    def blocked(p,k):
        r=radii[k]
        return not all(r<=v<=8000-r for v in p) or (k!=3 and any(a-r<=p[0]<=c+r and b-r<=p[1]<=d+r for a,b,c,d in boxes)) or not grade_safe(p,p,k)
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
        assert grade_safe(p,q,k),(p,q,k,'whole-body grade sweep')
        return q
    rng=random.Random(19381);samples=0
    for k in range(4):
        for _ in range(1500):
            p=tuple(f(v) for v in (rng.uniform(2500,5500),rng.uniform(500,7000)))
            q=tuple(f(v) for v in (rng.uniform(2500,5500),rng.uniform(500,7000)))
            expected=not blocked(p,k) and not blocked(q,k) and (k==3 or not any(hit(p,q,b,radii[k]) for b in boxes)) and grade_safe(p,q,k)
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
            if g==(4050.,1000.):
                assert tick+1 < math.ceil(600/s)+50,('wall-edge unnecessary creep',k,s,tick+1)
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
    # Rounded outward upper insets must not be advertised as safe point births.
    # Actual manual endpoints round inward within the original .001m gate.
    for k,r in enumerate((.551,3.551,4.491)):
        radius=f(r);upper=f(8000-radius)
        if upper+radius>8000:assert lib.test_body_blocked(upper,2000,k)==1
    # Real controller direction must remain commanded even while touching walls.
    controller_ticks=0
    for k,s in ((0,.3),(1,.6)):
        p=(3980.,1300.)
        for _ in range(90):
            q=controller(p,(p[0]+5,p[1]),s,k)
            assert q[1]==1300.,('uncommanded controller Z',k,p,q)
            assert not blocked(q,k) and not any(hit(p,q,b,radii[k]) for b in boxes)
            assert 0<=q[0]-p[0]<=s+.001
            p=q;controller_ticks+=1
        assert p[0]>3980 and p[0]<3988-radii[k]
        p=(3980.,1300.)
        slid=False
        for _ in range(90):
            q=controller(p,(p[0]+5,p[1]+5),s,k)
            assert not blocked(q,k) and not any(hit(p,q,b,radii[k]) for b in boxes)
            assert math.dist(p,q)<=s+.001
            assert q[0]>=p[0] and q[1]>=p[1]
            assert q[1]-p[1]<=s/math.sqrt(2)+.001
            if q[0]==p[0] and q[1]>p[1]:slid=True
            p=q;controller_ticks+=1
        assert slid and p[1]>1310
        p=tuple(map(f,(radii[k]+1,radii[k]+1)))
        for _ in range(20):
            q=controller(p,(0,p[1]),s,k)
            assert q[1]==p[1] and not blocked(q,k)
            p=q;controller_ticks+=1
        for bad in (float('nan'),float('inf'),-8001,16001):
            assert controller((3980,1300),(bad,1300),s,k)==(3980,1300)
        assert controller((3980,1300),(4000,1300),float('nan'),k)==(3980,1300)
    # Normalize real direction before clipping endpoints at every map edge.
    edge_ticks=0
    for k,s in ((0,.3),(1,.6)):
        r=radii[k]
        for axis in (0,1):
            for sign in (-1,1):
                for free in (-1,0,1):
                    p=[2000.,2000.];p[axis]=r+.25 if sign<0 else 8000-r-.25
                    p=tuple(map(f,p))
                    for _ in range(30):
                        direction=[free,free];direction[axis]=sign
                        g=tuple(p[i]+direction[i] for i in range(2))
                        q=controller(p,g,s,k)
                        norm=math.hypot(*direction)
                        for i in range(2):
                            delta=q[i]-p[i]
                            assert abs(delta)<=s*abs(direction[i])/norm+.001,('amplified edge axis',k,p,q,direction)
                            assert delta*direction[i]>=-.00001
                            if direction[i]==0:assert delta==0
                        assert math.dist(p,q)<=s+.001 and not blocked(q,k)
                        p=q;edge_ticks+=1
                    assert abs(p[axis]-(r+.001 if sign<0 else 8000-r-.001))<.001
        for sx in (-1,1):
            for sz in (-1,1):
                p=tuple(map(f,(r+.25 if sx<0 else 8000-r-.25,r+.25 if sz<0 else 8000-r-.25)))
                for _ in range(10):
                    q=controller(p,(p[0]+sx,p[1]+sz),s,k)
                    assert not blocked(q,k) and math.dist(p,q)<=s+.001
                    for i,sgn in enumerate((sx,sz)):
                        assert (q[i]-p[i])*sgn>=-.00001
                        assert abs(q[i]-p[i])<=s/math.sqrt(2)+.001
                    p=q;edge_ticks+=1
        # Exact local goal outside map is accepted; non-finite/absurd is not.
        p=tuple(map(f,(r+.1,2000.)))
        q=controller(p,(-1,2000),s,k)
        assert q[0]<p[0] and q[1]==p[1] and not blocked(q,k)
    # Control proves formerly point-clear footprint penetration.
    assert lib.test_body_blocked(3986,1300,1)==1
    enabled.value=0
    for k in range(4):
        assert controller((3980,1300),(4050,1300),.6,k)==move((3980,1300),(4050,1300),.6,k)
    assert lib.test_body_blocked(3986,1300,1)==0
    for k,s in ((0,.3),(1,.6)):
        p=(radii[k]+.25,2000.)
        expected=p[1]+s/math.hypot(-1-p[0],1)
        assert math.isclose(controller(p,(-1,2001),s,k)[1],expected,abs_tol=.001)
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
        assert lib.test_body_step_abi(3950,1300,4050,1300,.6,k)==1
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
    print(json.dumps({'suite':'terrain-body','passed':True,'seed':19381,'random_sweeps':samples,'route_ticks':routes,'controller_ticks':controller_ticks,'controller_edge_ticks':edge_ticks,'radii':radii,'invalid_start_policy':'safe hold','geometry':'expanded AABBs'}))
