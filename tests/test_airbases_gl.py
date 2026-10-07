#!/usr/bin/env python3
"""Actual embedded terrain fragment displays six bounded authored runway surfaces."""
from xvfb_display import read_display_number
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('road_gl',ROOT/'tests/test_road_gl.py');road=importlib.util.module_from_spec(spec);spec.loader.exec_module(road)

def main():
    exe=Path(sys.argv[1]).resolve();hardware='--hardware' in sys.argv
    template=(ROOT/'shaders/battle.frag').read_bytes()
    expected=template[:18]+(ROOT/'shaders/terrain_roads.glsl').read_bytes()+(ROOT/'shaders/airbases.glsl').read_bytes()+template[18:]
    fragment=road.embedded_fragment(exe);assert fragment==expected
    records=json.loads((ROOT/'content/terrain/airbases.json').read_text())['runways']
    points=[];labels=[]
    for row in records:
        # Independent interior/paint/boundary coordinates. Endpoints/corners
        # are closed CPU rectangles; samples just outside must remain unchanged.
        for dx,dz,label in ((0,15,'asphalt'),(-20,0,'centre-paint'),(0,39.5,'edge-paint'),
                            (590,1,'threshold-paint'),(600,15,'end-edge'),
                            (600.25,15,'outside-end'),(0,40.25,'outside-side'),
                            (0,-40.25,'outside-side'),(-600.25,15,'outside-end')):
            points.append((row['x']+dx,row['z']+dz));labels.append((row['id'],label))
    read,write=os.pipe();server=None
    try:
        with tempfile.TemporaryDirectory(prefix='rh-airbases-gl-')as tmp:
            folder=Path(tmp);env=dict(os.environ)
            if hardware:
                assert env.get('DISPLAY');env.pop('LIBGL_ALWAYS_SOFTWARE',None)
            else:
                with(folder/'xvfb.log').open('wb')as log:
                    server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','512x512x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
                os.close(write);write=-1;number=read_display_number(read,10);os.close(read);read=-1
                env.update(DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
            driver=road.DRIVER.replace('4000,1150','2000,4000').replace('400,200','650,70').replace('4000,100,1150','2000,100,4000')
            (folder/'driver.c').write_text(driver)
            obj=folder/'production.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','src/render/shaders.asm','-o',str(obj)],cwd=ROOT,check=True,capture_output=True)
            old=fragment.replace(b'if(airbaseSurface(p,runwayAlbedo))',b'if(false)',1);assert old!=fragment
            (folder/'control.frag').write_bytes(old)
            (folder/'control.asm').write_text('section .rodata\nglobal battle_fragment_source\nbattle_fragment_source:\nincbin "'+str(folder/'control.frag')+'"\ndb 0\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
            control_obj=folder/'control.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(folder/'control.asm'),'-o',str(control_obj)],check=True,capture_output=True)
            payload=str(len(points))+'\n'+''.join(f'{x} {z}\n'for x,z in points)
            outputs=[];contexts=[]
            for name,object_ in (('production',obj),('omitted-runway',control_obj)):
                program=folder/name;subprocess.run(['cc','-O2',str(folder/'driver.c'),str(object_),'-lGL','-lX11','-lm','-o',str(program)],check=True,capture_output=True)
                run=subprocess.run([str(program),str(folder/(name+'.ppm'))],input=payload,capture_output=True,text=True,env=env,timeout=45);assert run.returncode==0,(run.returncode,run.stderr)
                contexts.append(run.stderr.strip());outputs.append([tuple(map(int,line.split()))for line in run.stdout.splitlines()])
            if hardware:assert not any(s in contexts[0].lower()for s in ('llvmpipe','softpipe','swrast','swiftshader'))
            assert len(outputs[0])==len(outputs[1])==54
            rows=[]
            for (base,label),on,off in zip(labels,*outputs):
                delta=max(abs(a-b)for a,b in zip(on,off))
                if label.startswith('outside'):assert delta==0,(base,label,on,off)
                else:
                    assert delta>20,(base,label,on,off)
                    if 'paint' in label:assert min(on)>130,(base,label,on)
                    else:assert max(on)<90 and max(on)-min(on)<20,(base,label,on)
                rows.append(dict(base=base,label=label,on=on,omitted=off,delta=delta))
            output=Path(os.environ.get('RH_AIRBASES_GL_IMAGE','/tmp/rh-airbases-'+('native'if hardware else'software')+'.ppm'))
            output.write_bytes((folder/'production.ppm').read_bytes())
            print(json.dumps(dict(suite='airbases-production-gl',passed=True,hardware=hardware,contexts=contexts,samples=rows,draws=108,runway_bounds_outside_unchanged=True,fragment_sha256=hashlib.sha256(fragment).hexdigest(),omitted_control_sha256=hashlib.sha256(old).hexdigest(),image=str(output),scope='Production embedded terrain fragment/NASM shader object, declared flat diagnostic terrain textures and UV positions. Both-side/all-six pavement, centre/edge/threshold paint and omitted-surface controls. No actual-client terrain/visibility/authority/gameplay/performance/landing acceptance.')))
    finally:
        if read>=0:os.close(read)
        if write>=0:os.close(write)
        if server:server.terminate();server.wait(timeout=5)

if __name__=='__main__':main()
