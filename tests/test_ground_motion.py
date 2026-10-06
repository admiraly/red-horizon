#!/usr/bin/env python3
"""Development-only actual NASM hull actuator proof; collision is an explicit stub."""
import ctypes as C
import hashlib,json,math,os,pathlib,shutil,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
with tempfile.TemporaryDirectory(prefix='rh-ground-motion-') as td:
    objects=[]
    for source in ('src/game/ground_motion.asm','tests/ground_motion_probe.asm'):
        obj=pathlib.Path(td)/(pathlib.Path(source).stem+'.o')
        subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],check=True)
        objects.append(str(obj))
    so=pathlib.Path(td)/'ground.so'
    subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-lm','-o',str(so)],check=True)
    lib=C.CDLL(str(so)); lib_sha=hashlib.sha256(so.read_bytes()).hexdigest()
    class E(C.Structure):
        _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','gen')]
    class G(C.Structure):
        _fields_=[(n,C.c_float) for n in ('heading','speed','turn','vx','vz')]+[(n,C.c_uint) for n in ('gen','kind','flags')]
    entities=(E*32768).in_dll(lib,'sim_entities'); states=(G*32768).in_dll(lib,'sim_ground_motion')
    count=C.c_uint.in_dll(lib,'sim_count'); enabled=C.c_uint.in_dll(lib,'ground_enabled')
    goals=(C.c_float*12).in_dll(lib,'sim_waypoints'); drivers=(C.c_int*32768).in_dll(lib,'vehicle_entity_driver')
    players=(C.c_uint*64).in_dll(lib,'sim_players'); claims=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
    vehicles=(C.c_uint*32).in_dll(lib,'sim_vehicles')
    blocked=C.c_uint.in_dll(lib,'test_blocked'); partial=C.c_uint.in_dll(lib,'test_partial')
    calls=C.c_uint.in_dll(lib,'test_collision_calls'); cmode=C.c_uint.in_dll(lib,'test_collision_mode')
    budget=C.c_float.in_dll(lib,'test_collision_budget')
    lib.test_ground_step.argtypes=[C.c_uint,C.c_uint,C.POINTER(C.c_float)];lib.test_ground_step.restype=C.c_int
    lib.test_ground_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_ground_hash.restype=C.c_uint64
    checks=[]
    def reset(kind=1,heading=0):
        C.memset(C.addressof(entities),0,C.sizeof(entities)); count.value=1
        C.memset(C.addressof(drivers),255,C.sizeof(drivers));C.memset(C.addressof(players),0,C.sizeof(players))
        C.memset(C.addressof(claims),255,C.sizeof(claims));C.memset(C.addressof(vehicles),0,C.sizeof(vehicles))
        entities[0]=E(1000,1000,400,0,kind,0,0,7)
        for i in range(6):goals[i*2]=1000+math.sin(heading)*100;goals[i*2+1]=1000+math.cos(heading)*100
        blocked.value=partial.value=calls.value=0
        lib.ground_init()
    def board():
        drivers[0]=0;claims[0]=0;vehicles[0]=0;vehicles[1]=entities[0].gen;vehicles[2]=0;vehicles[3]=1
        players[5]=100;players[11]=1;players[15]=11
    def step(goal=None,amount=.5,mode=0,ident=0,source=None,publish=True):
        e=entities[0];before=bytes(entities)
        a=(C.c_float*5)(*(source or (e.x,e.z)),*(goal or (e.x,e.z)),amount)
        assert lib.test_ground_step(ident,mode,a)==1,'callee-saved ABI'
        assert bytes(entities)==before,'actuator mutated army records'
        if publish and ident==0: e.x,e.z=a[0],a[1]
        return tuple(a[:2])
    def angle(a,b):return (a-b+math.pi)%(2*math.pi)-math.pi
    reset(heading=math.pi/2)
    assert abs(states[0].heading-math.pi/2)<1e-5 and states[0].speed==0
    assert states[0].gen==7 and states[0].kind==1 and states[0].flags==1
    checks.append('route-seeded stationary heading')
    acceleration={}
    for kind,cap,rate in ((1,.5,.02),(2,.2,.01)):
        reset(kind)
        speeds=[]
        for t in range(35):
            old=(entities[0].x,entities[0].z); oldspeed=states[0].speed
            p=step((1000,2000),cap)
            s=states[0]
            assert 0<=s.speed<=cap+1e-6 and abs(s.speed-oldspeed)<=rate+1e-6
            assert abs(p[0]-old[0])<1e-6 and abs((p[1]-old[1])-s.speed)<.00007
            assert abs(s.vx-(p[0]-old[0]))<1e-6 and abs(s.vz-(p[1]-old[1]))<1e-6
            speeds.append(s.speed)
        assert abs(speeds[-1]-cap)<1e-6
        acceleration[str(kind)]={'first_speed':speeds[0],'last_speed':speeds[-1]}
    checks.append('role acceleration and distinct forward caps')
    reset(); board()
    for t in range(35):step((1000,2000),.6,1)
    assert abs(states[0].speed-.6)<1e-6
    drivers[0]=-1;claims[0]=-1;vehicles[3]=0
    step((1000,2000),.5)
    assert .55<states[0].speed<.6 and abs(states[0].speed-.56)<1e-6
    for t in range(5):step((1000,2000),.5)
    assert abs(states[0].speed-.5)<1e-6
    board();step((1000,2000),.6,1)
    assert .519<states[0].speed<.521
    checks.append('AI driver handoff shares momentum without initialization')
    reset();board()
    for t in range(35):step((1000,2000),.6,1)
    coast=0
    for t in range(20):
        old=(entities[0].x,entities[0].z); oldspeed=states[0].speed; oldheading=states[0].heading
        p=step(amount=0,mode=1)
        assert 0<=states[0].speed<=oldspeed and oldspeed-states[0].speed<=.040001
        assert states[0].heading==oldheading and states[0].turn==0
        coast+=math.dist(old,p)
    assert states[0].speed==0 and coast>3.5
    checks.append('released input brakes with bounded coasting and stopped facing')
    turn={}
    for kind,limit in ((1,.06),(2,.025)):
        reset(kind)
        progress=0;maximum=0
        for t in range(100):
            old=(entities[0].x,entities[0].z);h=states[0].heading;s=states[0].speed
            p=step((2000,1000),.5 if kind==1 else .2)
            g=states[0];maximum=max(maximum,abs(angle(g.heading,h)))
            assert abs(angle(g.heading,h))<= (limit if s==0 else (.04 if kind==1 else .025))+1e-6
            assert abs(g.turn-angle(g.heading,h))<1e-6
            delta=(p[0]-old[0],p[1]-old[1]);axis=(math.sin(g.heading),math.cos(g.heading))
            assert abs(delta[0]*axis[1]-delta[1]*axis[0])<.00009,'strafe'
            assert math.dist(old,p)<=abs(g.speed)+.0001
            progress+=math.dist(old,p)
        assert entities[0].x>1005 and maximum>limit-.001
        turn[str(kind)]={'maximum_turn':maximum,'travel':progress}
    checks.append('tracked pivots bounded turns hull axis translation useful progress')
    reverse={}
    for kind,cap in ((1,.18),(2,.08)):
        reset(kind)
        for t in range(30):step((1000,2000),.5)
        previous=states[0].speed;seen_zero=False;negative=False
        for t in range(80):
            step((1000,0),.5)
            s=states[0].speed
            if s==0:seen_zero=True
            if s<0:assert seen_zero;negative=True
            assert s>=-cap-1e-6
            assert abs(s-previous)<= (.040001 if kind==1 else .025001)
            previous=s
        assert negative and abs(states[0].speed+cap)<1e-6 and abs(states[0].heading)<1e-5
        reverse[str(kind)]=states[0].speed
    checks.append('reverse bounded lower cap and braking through zero')
    reset();board()
    for t in range(30):step((1000,2000),.6,1)
    old=(entities[0].x,entities[0].z);blocked.value=1
    assert step((2000,1000),.6,1)==old
    assert states[0].speed==0 and states[0].vx==0 and states[0].vz==0
    assert states[0].turn!=0 and cmode.value==1 and budget.value<=.6
    blocked.value=0;partial.value=1
    assert step((1000,2000),.6,1)==old and states[0].speed==0
    checks.append('contact holds exact position stops speed and permits pivot; partial query rejected')
    reset();step((1000,2000));entities[0].gen=8
    goals[0]=2000;goals[1]=1000
    step((2000,1000))
    assert states[0].gen==8 and abs(states[0].heading-math.pi/2)<1e-5 and states[0].speed<.021
    entities[0].kind=2;step((2000,1000),.2)
    assert states[0].kind==2 and states[0].speed<.011
    checks.append('generation kind recycle resets seed and momentum safely')
    invalid=0
    def rejected(**kw):
        global invalid
        before=bytes(states);n=calls.value;old=(entities[0].x,entities[0].z)
        p=step(publish=False,**kw)
        assert bytes(states)==before and calls.value==n
        invalid+=1
    reset();board();step((1000,2000),.6,1)
    for value in (float('nan'),float('inf'),-float('inf'),-1):rejected(amount=value,mode=1)
    for value in (float('nan'),float('inf'),-8001,16001):
        rejected(goal=(value,1000),mode=1);rejected(goal=(1000,value),mode=1)
    rejected(source=(1001,1000),mode=1);rejected(ident=32768,mode=1);rejected(mode=2)
    count.value=32769;rejected(mode=1);count.value=1
    for array,index,value in ((players,5,0),(players,11,0),(players,15,0),(vehicles,0,1),(vehicles,1,8),(vehicles,2,1),(vehicles,3,0),(claims,0,-1),(drivers,0,-1)):
        old=array[index];array[index]=value;rejected(mode=1);array[index]=old
    for field,value in (('hp',0),('gen',0),('kind',0),('side',1),('front',3)):
        old=getattr(entities[0],field);setattr(entities[0],field,value);rejected(mode=1);setattr(entities[0],field,old)
    for field,value in (('heading',float('nan')),('speed',float('inf')),('turn',float('nan')),('vx',float('inf')),('vz',float('nan')),('heading',4),('speed',.7),('turn',.07),('vx',.7),('vz',.7)):
        old=getattr(states[0],field);setattr(states[0],field,value);rejected(mode=1);setattr(states[0],field,old)
    checks.append('invalid count role generation claim pose finite inputs preserve state')
    reset(heading=math.pi/2);before=bytes(states);enabled.value=0
    p=step((1000,2000),.5)
    assert p==(1000,1000.5) and bytes(states)==before and calls.value==0
    checks.append('policy off genuine immediate legacy movement causal control')
    reset();seed=14695981039346656037;prime=1099511628211
    def reference(data):
        h=seed
        for b in data:h=((h^b)*prime)&((1<<64)-1)
        return h
    expected=reference(struct.pack('<I',enabled.value)+bytes(states))
    assert lib.test_ground_hash(seed,prime)==expected
    raw=(C.c_ubyte*C.sizeof(states)).from_address(C.addressof(states))
    for offset in (0,4,8,12,16,20,24,28,C.sizeof(states)-1):
        raw[offset]^=1; assert lib.test_ground_hash(seed,prime)!=expected;raw[offset]^=1
    enabled.value=0;assert lib.test_ground_hash(seed,prime)!=expected
    checks.append('FNV policy and every persistent state field including inactive tail')
    actuator_report={'suite':'ground-motion-actuator','passed':True,'library_sha256':lib_sha,'checks':checks,
      'invalid_rejected_cases':invalid,'acceleration':acceleration,'turn':turn,'reverse':reverse,
      'collision_evidence':'Explicit development clear/blocked/partial stub; not production collision or scale evidence',
      'runtime':'Actual NASM x86-64 SSE2 module; Python development observer'}
    print(json.dumps(actuator_report,sort_keys=True))
    # Independent production body/terrain path: same actuator, real collision code.
    real_objects=[]
    sources=('src/game/ground_motion.asm','src/nav/crowd.asm','src/nav/terrain.asm','src/nav/terrain_body.asm','tests/ground_motion_probe.asm')
    for source in sources:
        obj=pathlib.Path(td)/(pathlib.Path(source).stem+'-real.o')
        subprocess.run([nasm,'-f','elf64','-DGROUND_REAL_COLLISION=1','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],check=True)
        real_objects.append(str(obj))
    real_so=pathlib.Path(td)/'ground-real.so'
    subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*real_objects,'-lm','-o',str(real_so)],check=True)
    actual=C.CDLL(str(real_so))
    re=(E*32768).in_dll(actual,'sim_entities'); rg=(G*32768).in_dll(actual,'sim_ground_motion')
    rn=C.c_uint.in_dll(actual,'sim_count');rtick=C.c_uint.in_dll(actual,'sim_tick_count')
    rw=(C.c_float*12).in_dll(actual,'sim_waypoints');rd=(C.c_int*32768).in_dll(actual,'vehicle_entity_driver')
    rp=(C.c_uint*64).in_dll(actual,'sim_players');rc=(C.c_int*4).in_dll(actual,'sim_player_vehicle')
    rv=(C.c_uint*32).in_dll(actual,'sim_vehicles')
    actual.test_ground_step.argtypes=[C.c_uint,C.c_uint,C.POINTER(C.c_float)];actual.test_ground_step.restype=C.c_int
    def real_reset(rows):
        C.memset(C.addressof(re),0,C.sizeof(re));rn.value=len(rows);rtick.value=0
        C.memset(C.addressof(rd),255,C.sizeof(rd));C.memset(C.addressof(rp),0,C.sizeof(rp))
        C.memset(C.addressof(rc),255,C.sizeof(rc));C.memset(C.addressof(rv),0,C.sizeof(rv))
        for i,(x,z,k) in enumerate(rows):re[i]=E(x,z,400,0,k,0,0,i+7)
        for i in range(6):rw[i*2]=rows[0][0];rw[i*2+1]=rows[0][1]+100
        actual.terrain_body_init();actual.crowd_init();actual.ground_init()
        rd[0]=0;rc[0]=0;rv[0]=0;rv[1]=re[0].gen;rv[2]=0;rv[3]=1
        rp[5]=100;rp[11]=1;rp[15]=11
    def real_step(goal,amount=.6,mode=1):
        rtick.value+=1;actual.crowd_begin(); e=re[0];old=(e.x,e.z)
        a=(C.c_float*5)(e.x,e.z,*goal,amount);before=bytes(re)
        assert actual.test_ground_step(0,mode,a)==1 and bytes(re)==before
        e.x,e.z=a[0],a[1]
        delta=(e.x-old[0],e.z-old[1]);axis=(math.sin(rg[0].heading),math.cos(rg[0].heading))
        assert abs(delta[0]*axis[1]-delta[1]*axis[0])<.0003
        assert math.dist(old,(e.x,e.z))<=.6005
        return old,(e.x,e.z)
    real_cases=[]
    for k,radius in ((0,.55),(1,3.55),(2,4.49)):
        real_reset([(1000,1000,1),(1000,1012,k)])
        minimum=math.inf
        for tick in range(100):
            old,new=real_step((1000,1100))
            dx,dz=new[0]-old[0],new[1]-old[1];qx,qz=old[0]-re[1].x,old[1]-re[1].z
            dd=dx*dx+dz*dz;t=max(0,min(1,-(qx*dx+qz*dz)/dd)) if dd else 0
            gap=math.hypot(qx+t*dx,qz+t*dz);minimum=min(minimum,gap)
            assert gap>=3.55+radius-.0002
        assert 1000.5<re[0].z<1012 and rg[0].speed==0
        real_cases.append({'case':'driven-tank-vs-held-kind-'+str(k),'ticks':100,'minimum_swept_gap':minimum,'end':[re[0].x,re[0].z]})
    real_reset([(3970,1300,1)])
    # Actual vertical wall spans X3988..4012 and Z1100..1500.
    for tick in range(150):real_step((4050,1300))
    assert re[0].x<=3988-3.55+.001 and re[0].x>3971
    real_cases.append({'case':'driven-tank-vs-production-terrain-wall','ticks':150,'end':[re[0].x,re[0].z]})
    real_reset([(1000,1000,1)])
    for tick in range(40):real_step((1000,2000))
    rd[0]=-1;rc[0]=-1;rv[3]=0
    before=rg[0].speed
    real_step((1000,2000),.5,0)
    assert abs(before-.6)<1e-6 and abs(rg[0].speed-.56)<1e-6
    real_cases.append({'case':'actual-crowd-AI-handoff-preserves-bounded-momentum','before':before,'after':rg[0].speed})
    print(json.dumps({'suite':'ground-motion-production-collision','passed':True,'library_sha256':hashlib.sha256(real_so.read_bytes()).hexdigest(),
      'cases':real_cases,'scope':'Actual actuator plus production crowd/terrain kernels; no world hooks, network, graphics or scale acceptance'},sort_keys=True))
