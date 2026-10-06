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
    driver_generations=(C.c_uint*4).in_dll(lib,'vehicle_driver_generation')
    blocked=C.c_uint.in_dll(lib,'test_blocked'); partial=C.c_uint.in_dll(lib,'test_partial')
    calls=C.c_uint.in_dll(lib,'test_collision_calls'); cmode=C.c_uint.in_dll(lib,'test_collision_mode')
    budget=C.c_float.in_dll(lib,'test_collision_budget')
    surface=C.c_int.in_dll(lib,'test_surface');surface_calls=C.c_uint.in_dll(lib,'test_surface_calls')
    surface_radius=C.c_float.in_dll(lib,'test_surface_radius');surface_alignment=C.c_uint.in_dll(lib,'test_surface_alignment')
    lib.test_ground_step.argtypes=[C.c_uint,C.c_uint,C.POINTER(C.c_float)];lib.test_ground_step.restype=C.c_int
    lib.test_ground_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_ground_hash.restype=C.c_uint64
    checks=[]
    def reset(kind=1,heading=0):
        C.memset(C.addressof(entities),0,C.sizeof(entities)); count.value=1
        C.memset(C.addressof(drivers),255,C.sizeof(drivers));C.memset(C.addressof(players),0,C.sizeof(players))
        C.memset(C.addressof(claims),255,C.sizeof(claims));C.memset(C.addressof(vehicles),0,C.sizeof(vehicles))
        entities[0]=E(1000,1000,400,0,kind,0,0,7)
        for i in range(6):goals[i*2]=1000+math.sin(heading)*100;goals[i*2+1]=1000+math.cos(heading)*100
        blocked.value=partial.value=calls.value=surface_calls.value=0;surface.value=1
        lib.ground_init()
    def board():
        drivers[0]=0;claims[0]=0;vehicles[0]=0;vehicles[1]=entities[0].gen;vehicles[2]=0;vehicles[3]=1
        players[5]=100;players[11]=1;players[15]=11;driver_generations[0]=11
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
    approaches={}
    for kind,distance,cap in ((1,12,.5),(2,8,.2)):
        reset(kind);goal=(1000,1000+distance);maximum=1000;oldspeed=0
        for t in range(120):
            step(goal,cap)
            maximum=max(maximum,entities[0].z)
            assert entities[0].z<=goal[1]+.0002,'AI arrival overshot fixed destination'
            assert abs(states[0].speed-oldspeed)<= (.040001 if kind==1 else .025001)
            oldspeed=states[0].speed
        error=math.dist((entities[0].x,entities[0].z),goal)
        assert error<.001 and states[0].speed<.0002
        approaches[str(kind)]={'arrival_error':error,'maximum_forward_coordinate':maximum}
    checks.append('AI fixed-goal terminal braking converges without snap or overshoot')
    reset();board()
    for t in range(40):step((1000,2000),.6,1)
    start=(entities[0].x,entities[0].z)
    for t in range(30):step((entities[0].x,entities[0].z+1),.6,1)
    assert math.dist(start,(entities[0].x,entities[0].z))>17.99 and abs(states[0].speed-.6)<1e-6
    checks.append('driver local steering points retain full steady speed')
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
    reset();board()
    for t in range(35):step((1000,2000),.6,1)
    previous=states[0].speed;seen_zero=False;negative=False
    for t in range(80):
        step((1000,0),.6,1)
        s=states[0].speed
        if s==0:seen_zero=True
        if s<0:assert seen_zero;negative=True
        assert s>=-.180001 and abs(s-previous)<=.040001
        previous=s
    assert negative and abs(states[0].speed+.18)<1e-6 and abs(states[0].heading)<1e-5
    reverse['driver_tank']=states[0].speed
    checks.append('driver reverse bounded lower cap and braking through zero')
    for kind in (1,2):
        reset(kind)
        for t in range(220):
            oldh=states[0].heading;olds=states[0].speed
            step((1000,0),.5 if kind==1 else .2)
            assert states[0].speed>=0,'AI detour reversed instead of committed forward pivot'
            assert abs(angle(states[0].heading,oldh))<=(.06 if kind==1 and olds==0 else .04 if kind==1 else .025)+1e-6
        assert entities[0].z<995 and abs(abs(states[0].heading)-math.pi)<.02
    checks.append('AI rearward detours pivot forward instead of slow reverse oscillation')
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
        before=bytes(states);n=calls.value;ns=surface_calls.value;old=(entities[0].x,entities[0].z)
        p=step(publish=False,**kw)
        assert bytes(states)==before and calls.value==n and surface_calls.value==ns
        invalid+=1
    reset();board();step((1000,2000),.6,1)
    for value in (float('nan'),float('inf'),-float('inf'),-1):rejected(amount=value,mode=1)
    for value in (float('nan'),float('inf'),-8001,16001):
        rejected(goal=(value,1000),mode=1);rejected(goal=(1000,value),mode=1)
    rejected(source=(1001,1000),mode=1);rejected(ident=32768,mode=1);rejected(mode=2)
    count.value=32769;rejected(mode=1);count.value=1
    for array,index,value in ((players,5,0),(players,11,0),(players,15,0),(players,15,12),(driver_generations,0,12),(vehicles,0,1),(vehicles,1,8),(vehicles,2,1),(vehicles,3,0),(claims,0,-1),(drivers,0,-1)):
        old=array[index];array[index]=value;rejected(mode=1);array[index]=old
    for field,value in (('hp',0),('gen',0),('kind',0),('side',1),('front',3)):
        old=getattr(entities[0],field);setattr(entities[0],field,value);rejected(mode=1);setattr(entities[0],field,old)
    for field,value in (('heading',float('nan')),('speed',float('inf')),('turn',float('nan')),('vx',float('inf')),('vz',float('nan')),('heading',4),('speed',.7),('turn',.07),('vx',.7),('vz',.7)):
        old=getattr(states[0],field);setattr(states[0],field,value);rejected(mode=1);setattr(states[0],field,old)
    for x,z in ((-1,1000),(8001,1000),(1000,-1),(1000,8001),(-8000,1000),(16000,1000)):
        oldx,oldz=entities[0].x,entities[0].z
        entities[0].x,entities[0].z=x,z
        before_entities=bytes(entities)
        rejected(source=(x,z),goal=(1000,1000),mode=1)
        assert bytes(entities)==before_entities,'off-map request mutated army records'
        entities[0].x,entities[0].z=oldx,oldz
    checks.append('invalid count role generation claim pose finite inputs preserve state')
    for x,z in ((-1,1000),(8001,1000),(1000,-1),(1000,8001)):
        reset();entities[0].x,entities[0].z=x,z
        before_entities=bytes(entities)
        lib.ground_init()
        assert bytes(entities)==before_entities and bytes(states)==bytes(C.sizeof(states))
    checks.append('off-map initialized births skipped without sidecar seeding')
    reset(heading=math.pi/2);before=bytes(states);enabled.value=0
    p=step((1000,2000),.5)
    assert p==(1000,1000.5) and bytes(states)==before and calls.value==0 and surface_calls.value==0
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
    surface_cases=[]
    for kind,cap,rate,mult,radius in ((1,.5,.02,.8,3.55),(2,.2,.01,.7,4.49)):
        reset(kind);surface.value=0
        for t in range(60):
            oldspeed=states[0].speed;step((1000,2000),cap)
            assert states[0].speed-oldspeed<=rate*mult+1e-6
            assert surface_alignment.value==8 and abs(surface_radius.value-radius)<1e-6
        assert abs(states[0].speed-cap*mult)<1e-6
        surface_cases.append({'kind':kind,'offroad_forward':states[0].speed,'acceleration':rate*mult,'radius':surface_radius.value})
        surface.value=1
        oldspeed=states[0].speed;step((1000,2000),cap)
        assert abs(states[0].speed-oldspeed-rate)<1e-6
        for t in range(30):step((1000,2000),cap)
        assert abs(states[0].speed-cap)<1e-6
        surface.value=0
        before=states[0].speed;step((1000,2000),cap)
        assert abs(states[0].speed-(before-(.04 if kind==1 else .025)))<1e-6,'boundary clamped momentum'
        for t in range(30):step((1000,2000),cap)
        assert abs(states[0].speed-cap*mult)<1e-6
    checks.append('real-radius surface queries scale role targets/acceleration and brake across boundaries')
    reset();board();surface.value=0
    for t in range(60):step((1000,2000),.6,1)
    assert abs(states[0].speed-.48)<1e-6
    seen_zero=False
    for t in range(60):
        previous=states[0].speed;step((1000,0),.6,1)
        if states[0].speed==0:seen_zero=True
        if states[0].speed<0:assert seen_zero
        assert abs(states[0].speed-previous)<=.040001
    assert abs(states[0].speed+.144)<1e-6
    surface_cases.append({'driver_offroad_forward':.48,'driver_offroad_reverse':states[0].speed,'braked_through_zero':seen_zero})
    checks.append('off-road driver controls share policy and preserve braking through zero')
    reset();board()
    for t in range(35):step((1000,2000),.6,1)
    surface.value=0;drivers[0]=-1;claims[0]=-1;vehicles[3]=0
    step((1000,2000),.5)
    assert abs(states[0].speed-.56)<1e-6
    for t in range(10):step((1000,2000),.5)
    assert abs(states[0].speed-.4)<1e-6
    board();step((1000,2000),.6,1)
    assert abs(states[0].speed-.416)<1e-6
    checks.append('road-to-offroad AI/driver handoff retains momentum with bounded rates')
    for recycled in (False,True):
        reset();step((1000,2000))
        if recycled:entities[0].gen+=1
        surface.value=-1;before=bytes(states);n=calls.value;ns=surface_calls.value
        step((1000,2000),publish=False)
        assert bytes(states)==before and calls.value==n and surface_calls.value==ns+1
    checks.append('invalid surface result preserves existing and recycled sidecars')
    discrete_cases=0
    for kind,cap,b in ((1,.5,.04),(2,.2,.025)):
        for paved in (0,1):
            for heading in (0,math.pi/2):
                for distance in (.1,.3,.7,1.5,5,20):
                    for seeded in (False,True):
                        initial_speed=cap if paved else cap*(.8 if kind==1 else .7)
                        steps=math.ceil(initial_speed/b)
                        stopping=steps*initial_speed-b*steps*(steps-1)/2
                        if seeded and distance<stopping+.01:continue
                        reset(kind,heading);surface.value=paved
                        axis=1 if heading==0 else 0
                        goal=[1000.,1000.];goal[axis]=C.c_float(1000+distance).value
                        if seeded:
                            states[0].speed=initial_speed
                            states[0].vx=initial_speed if axis==0 else 0
                            states[0].vz=initial_speed if axis==1 else 0
                        maximum=1000.;late=None
                        for t in range(300):
                            old=states[0].speed;step(tuple(goal),cap)
                            maximum=max(maximum,(entities[0].x,entities[0].z)[axis])
                            assert abs(states[0].speed-old)<=b+1e-6
                            assert maximum<=goal[axis]+.0002,'discrete braking overshot reachable straight goal'
                            if t==290:late=(entities[0].x,entities[0].z)
                        assert math.dist((entities[0].x,entities[0].z),goal)<.001
                        assert math.dist(late,(entities[0].x,entities[0].z))<.0005
                        discrete_cases+=1
    checks.append('discrete stopping envelope converges from rest and physically stoppable full momentum across roles/surfaces/headings')
    actuator_report={'suite':'ground-motion-actuator','passed':True,'library_sha256':lib_sha,'checks':checks,
      'discrete_stopping_cases':discrete_cases,'surface_cases':surface_cases,'invalid_rejected_cases':invalid,'acceleration':acceleration,'turn':turn,'reverse':reverse,'approaches':approaches,
      'collision_evidence':'Explicit development clear/blocked/partial stub; not production collision or scale evidence',
      'runtime':'Actual NASM x86-64 SSE2 module; Python development observer'}
    print(json.dumps(actuator_report,sort_keys=True))
    # Independent production body/terrain path: same actuator, real collision code.
    real_objects=[]
    sources=('src/game/ground_motion.asm','src/nav/crowd.asm','src/nav/terrain.asm','src/nav/terrain_body.asm','src/nav/terrain_surface.asm','tests/ground_motion_probe.asm')
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
    rdriver_generations=(C.c_uint*4).in_dll(actual,'vehicle_driver_generation')
    actual.test_ground_step.argtypes=[C.c_uint,C.c_uint,C.POINTER(C.c_float)];actual.test_ground_step.restype=C.c_int
    def real_reset(rows):
        C.memset(C.addressof(re),0,C.sizeof(re));rn.value=len(rows);rtick.value=0
        C.memset(C.addressof(rd),255,C.sizeof(rd));C.memset(C.addressof(rp),0,C.sizeof(rp))
        C.memset(C.addressof(rc),255,C.sizeof(rc));C.memset(C.addressof(rv),0,C.sizeof(rv))
        for i,(x,z,k) in enumerate(rows):re[i]=E(x,z,400,0,k,0,0,i+7)
        for i in range(6):rw[i*2]=rows[0][0];rw[i*2+1]=rows[0][1]+100
        actual.terrain_body_init();actual.crowd_init();actual.ground_init()
        rd[0]=0;rc[0]=0;rv[0]=0;rv[1]=re[0].gen;rv[2]=0;rv[3]=1
        rp[5]=100;rp[11]=1;rp[15]=11;rdriver_generations[0]=11
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
    # Explicit paved interior for the original road-cap momentum gate.
    real_reset([(1100,1300,1)])
    rw[0]=2100;rw[1]=1300;actual.ground_init()
    for tick in range(40):real_step((2100,1300))
    rd[0]=-1;rc[0]=-1;rv[3]=0
    before=rg[0].speed
    real_step((2100,1300),.5,0)
    assert abs(before-.6)<1e-6 and abs(rg[0].speed-.56)<1e-6
    real_cases.append({'case':'actual-crowd-AI-handoff-preserves-bounded-momentum','before':before,'after':rg[0].speed})
    # Real stateless helper: road interiors attain original caps; adjacent full-body
    # off-road poses attain role caps without changing wall/body safety assertions.
    real_surfaces=[]
    for kind,cap,mult in ((1,.5,.8),(2,.2,.7)):
        for z,expected in ((1300,cap),(1320,cap*mult)):
            real_reset([(1100,z,kind)])
            rd[0]=-1;rc[0]=-1;rv[3]=0
            rw[0]=2100;rw[1]=z;actual.ground_init()
            for t in range(80):real_step((2100,z),cap,0)
            assert abs(rg[0].speed-expected)<.0001,(kind,z,expected,rg[0].speed,re[0].x,re[0].z,rg[0].heading)
            real_surfaces.append({'kind':kind,'z':z,'speed':rg[0].speed})
    print(json.dumps({'suite':'ground-motion-production-collision','passed':True,'library_sha256':hashlib.sha256(real_so.read_bytes()).hexdigest(),
      'cases':real_cases,'surfaces':real_surfaces,'scope':'Actual actuator plus production crowd/terrain kernels; no world hooks, network, graphics or scale acceptance'},sort_keys=True))
