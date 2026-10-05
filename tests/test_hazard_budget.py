#!/usr/bin/env python3
"""Reproducible development-only controlled NASM hazard observation budget test.
Uses the real hazard implementation with flat terrain and forced blocked LOS.
It deliberately does not establish production terrain, steering or survival.
"""
import argparse
import ctypes as C
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
STUB=r'''
default rel
section .bss
global sim_count,sim_entities,sim_tick_count,sim_projectiles,vehicle_entity_driver
sim_count: resd 1
sim_entities: resb 32768*32
sim_tick_count: resd 1
sim_projectiles: resb 512*64
vehicle_entity_driver: resd 32768
global los_blocked,los_observations
los_blocked: resd 1
los_observations: resd 1
section .text
global terrain_height,terrain_los,hazard_choose_goal,test_init,test_query_los
extern hazard_init,hazard_query
terrain_height:
 xorps xmm0,xmm0
 ret
terrain_los:
 inc dword [los_observations]
 mov eax,[los_blocked]
 xor eax,1
 ret
hazard_choose_goal:
 addss xmm0,xmm2
 xor eax,eax
 mov edx,1
 ret
test_init:
 lea rdi,[vehicle_entity_driver]
 mov eax,-1
 mov ecx,32768
 rep stosd
 jmp hazard_init
test_query_los:
 sub rsp,8
 call hazard_query
 mov eax,edx
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''

class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','generation')]
class Projectile(C.Structure):
    _fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint) for n in ('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint) for n in ('source','generation','active','source_generation','reserved')]

def verify(library):
    lib=C.CDLL(str(library))
    entities=(Entity*32768).in_dll(lib,'sim_entities')
    pool=(Projectile*512).in_dll(lib,'sim_projectiles')
    metrics=(C.c_uint64*8).in_dll(lib,'hazard_metrics')
    count=C.c_uint.in_dll(lib,'sim_count')
    tick=C.c_uint.in_dll(lib,'sim_tick_count')
    los=C.c_uint.in_dll(lib,'los_observations')
    count.value=8192
    lib.test_init()
    for e in entities[:8192]:
        e.x,e.z,e.hp,e.side,e.kind,e.generation=1000,1300,100,0,0,1
    for p in pool[:8]:
        p.x,p.y,p.z,p.vy=1000,25,1300,-1
        p.ttl,p.side,p.kind,p.damage,p.radius,p.generation,p.active=120,1,3,100,35,17,1
    C.c_uint.in_dll(lib,'los_blocked').value=1
    lib.hazard_tick() # first tick initializes all generation sidecars
    reports=[]
    for frame in (1,8,17,64,255):
        tick.value=frame
        before=(metrics[5],metrics[6],los.value)
        lib.hazard_tick()
        actual_los=los.value-before[2]
        metric_los=metrics[5]-before[0]
        skips=metrics[6]-before[1]
        assert actual_los==metric_los==1024,(frame,actual_los,metric_los)
        assert skips==896,(frame,skips)
        assert metrics[2]==0 and metrics[7]==0
        reports.append({'tick':frame,'actual_LOS_calls':actual_los,'metric_LOS_calls':metric_los,'budget_skips':skips})
    # A direct cosmetic query uses <=8 LOS calls and does not mutate authority.
    lib.test_query_los.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float]
    states=(C.c_uint*(32768*8)).in_dll(lib,'hazard_states')
    before=(bytes(states),tuple(metrics))
    assert lib.test_query_los(0,1000,2,1300)==8
    assert before==(bytes(states),tuple(metrics))
    return {'suite':'hazard-budget','passed':True,'scope':'real NASM hazard core; controlled flat terrain and blocked LOS; no production survival claim','initialized_actors':8192,'actual_projectiles':8,'per_query_LOS_bound':8,'observations':reports,'query_authority_unchanged':True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--nasm',default=os.environ.get('RED_HORIZON_NASM'))
    args=parser.parse_args()
    nasm=args.nasm or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
    with tempfile.TemporaryDirectory(prefix='red-horizon-hazard-budget-') as temp:
        output=pathlib.Path(temp)
        (output/'stub.asm').write_text(STUB)
        for source,name in ((ROOT/'src/ai/hazards.asm','hazards'),(output/'stub.asm','stub')):
            subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(source),'-o',str(output/(name+'.o'))],check=True)
        library=output/'kernel.so'
        subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(output/'hazards.o'),str(output/'stub.o'),'-o',str(library)],check=True)
        # Preserve all kernel branches, including controlled visibility failures.
        result=subprocess.run([os.sys.executable,str(ROOT/'tests/test_hazards.py'),str(library)],check=True,capture_output=True,text=True)
        focused=json.loads(result.stdout.strip().splitlines()[-1])
        assert focused['passed'] is True
        report=verify(library)
        report['focused_kernel_checks']=focused
        print(json.dumps(report,sort_keys=True))

if __name__=='__main__':main()
