#!/usr/bin/env python3
"""Real recorded bank/mixer plus deterministic pose-routing fixtures."""
import argparse,ctypes,hashlib,json,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]

def run(nasm):
    with tempfile.TemporaryDirectory(prefix='rh-footsteps-') as temp:
        work=pathlib.Path(temp)
        stub=work/'fixture.asm'
        stub.write_text('''default rel
section .bss align=16
global sim_players,sim_player_vehicle,player_motion
sim_players: resb 256
sim_player_vehicle: resd 4
player_motion: resb 128
section .text
global terrain_height
terrain_height:
 xorps xmm0,xmm0
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
''')
        objects=[]
        for path in [ROOT/'src/audio/audio.asm',ROOT/'src/audio/footsteps.asm',stub]:
            obj=work/(path.stem+'.o');objects.append(str(obj))
            subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(path),'-o',str(obj)],check=True)
        so=work/'test.so'
        subprocess.run(['gcc','-shared','-Wl,-Bsymbolic',*objects,'-lasound','-o',str(so)],check=True)
        lib=ctypes.CDLL(str(so))
        lib.audio_load_kind.argtypes=[ctypes.c_uint,ctypes.c_char_p]
        lib.audio_emit_kind.argtypes=[ctypes.c_uint]+[ctypes.c_float]*4
        lib.audio_listener.argtypes=[ctypes.c_float]*5
        lib.audio_footsteps_update.argtypes=[ctypes.c_uint,ctypes.c_float]
        lib.audio_mix_stereo.argtypes=[ctypes.POINTER(ctypes.c_int16),ctypes.c_size_t]
        players=(ctypes.c_ubyte*256).in_dll(lib,'sim_players')
        motion=(ctypes.c_ubyte*128).in_dll(lib,'player_motion')
        vehicle=(ctypes.c_int32*4).in_dll(lib,'sim_player_vehicle')
        counter=lambda name:ctypes.c_uint64.in_dll(lib,name).value
        def put(offset,value,fmt='f'):
            data=struct.pack('<'+fmt,value)
            for i,b in enumerate(data):players[offset+i]=b
        def mp(offset,value):
            for i,b in enumerate(struct.pack('<I',value)):motion[offset+i]=b
        def pose(x=1000,y=1.8,z=1000,gen=1,connected=1,hp=100,ground=1,initialized=1,motion_gen=None):
            put(0,x);put(4,y);put(8,z);put(20,hp,'i');put(44,connected,'I');put(60,gen,'I')
            mp(8,gen if motion_gen is None else motion_gen);mp(16,ground);mp(20,initialized)
        def update(dt=1/60):
            before=(bytes(players),bytes(motion),bytes(vehicle))
            lib.audio_footsteps_update(0,dt)
            assert before==(bytes(players),bytes(motion),bytes(vehicle)), 'router changed authority/motion'
        def reset():
            lib.audio_footsteps_reset();vehicle[0]=-1;pose();update()
        assert lib.audio_listener(1000,1.8,1000,1,0)==0
        for bank,path in enumerate(['rifle.pcm','explosion.pcm','footstep.pcm']):
            assert lib.audio_load_kind(bank,str(ROOT/'content/audio'/path).encode())==0
        assert lib.audio_load_kind(3,b'/no-file')==1
        asset=next(a for a in json.loads((ROOT/'content/asset-manifest.json').read_text())['assets'] if a['id']=='footstep-recorded')
        raw=(ROOT/asset['destination']).read_bytes();source=(ROOT/asset['source_file']).read_bytes()
        assert asset['recorded'] and hashlib.sha256(raw).hexdigest()==asset['derived_sha256']
        assert hashlib.sha256(source).hexdigest()==asset['original_sha256']
        assert 0<len(raw)<=384000 and len(raw)%2==0
        wave=struct.unpack('<'+str(len(raw)//2)+'h',raw);assert max(wave)>100 and min(wave)<-100
        assert lib.audio_emit_kind(2,1000,1.8,1000,1)==0
        output=(ctypes.c_int16*1600)()
        assert lib.audio_mix_stereo(output,800)==800
        assert list(output)==[v>>1 for v in wave[:800] for _ in range(2)], 'actual recorded PCM differs'
        assert lib.audio_emit_kind(3,1000,1.8,1000,1)==-1
        for i in range(200):assert lib.audio_emit_kind(i%3,1000,1.8,1000,1)==0
        assert lib.audio_active()==128 and counter('audio_replaced')>=73
        # Constant actual path sampled at render rates;32m total ->17footfalls.
        counts={}
        for hz in [30,60,120]:
            reset()
            for frame in range(1,hz*4+1):
                pose(x=1000+frame*8/hz);update(1/hz)
            counts[hz]=counter('audio_footsteps_emitted')
        assert len(set(counts.values()))==1 and counts[30]==17, counts
        # Simulation30Hz stepped poses on faster render: no repeated frozen steps.
        reset()
        for frame in range(1,481):
            pose(x=1000+(frame//4)*(8/30));update(1/120)
        assert counter('audio_footsteps_emitted')==17
        reset()
        for _ in range(300):update()
        assert counter('audio_footsteps_emitted')==0
        for kwargs in [dict(connected=0),dict(hp=0),dict(y=3,ground=0),dict(ground=0),dict(y=1.1,ground=0),dict(y=float('nan'))]:
            reset()
            for i in range(20):pose(x=1000+i*.5,**kwargs);update()
            assert counter('audio_footsteps_emitted')==0,kwargs
        reset();vehicle[0]=4
        for i in range(20):pose(x=1000+i*.5);update()
        assert counter('audio_footsteps_emitted')==0
        reset();pose(x=2000);update();pose(x=2000.1);update()
        assert counter('audio_footsteps_emitted')==0,'teleport replay'
        reset();pose(x=1001.7);update();pose(x=1002,gen=2);update();pose(x=1002.2,gen=2);update()
        assert counter('audio_footsteps_emitted')==0,'generation reused accumulator'
        for dt in [0,-1,float('nan'),float('inf')]:
            reset();pose(x=1001.7);update();pose(x=1002);update(dt);update()
            assert counter('audio_footsteps_emitted')==0
        # Network-style poses lack a valid movement sidecar; exact successive
        # standing/crouch height gates preserve co-op movement, not airborne audio.
        for eye in [1.8,1.1]:
            reset();pose(y=eye,initialized=0);update()
            for i in range(1,21):pose(x=1000+i*.2,y=eye,initialized=0);update()
            assert counter('audio_footsteps_emitted')==2
        reset()
        for i in range(1,21):pose(x=1000+i*.2,y=2.2,initialized=0);update()
        pose(x=1004.2,y=1.8,initialized=0);update()
        assert counter('audio_footsteps_emitted')==0,'airborne landing replay'
        reset();pose(x=1003);update(1000)
        assert counter('audio_footsteps_emitted')<=2
        return {'suite':'footsteps','passed':True,'recorded_samples':len(wave),'source_sha256':asset['original_sha256'],'derived_sha256':asset['derived_sha256'],'footfalls_by_render_hz':counts,'voice_budget':128,'authority_unchanged':True,'limitation':'Null/CPU fixtures do not establish audible quality or real co-op output.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--nasm',default='nasm');args=parser.parse_args()
    print(json.dumps(run(args.nasm)))
