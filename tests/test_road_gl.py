#!/usr/bin/env python3
"""Development-only actual embedded terrain-fragment material/road proof.

The temporary C driver is GL/X11 test tooling, not project CPU runtime. It links
the production NASM shader object and renders deterministic flat terrain/textures
to isolate road geometry from camera perspective, lighting and texture detail.
Optional client argument checks its embedded fragment against this tested source.
"""
from xvfb_display import read_display_number
import hashlib
import json
import math
import os
import pathlib
import select
import struct
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = r'''
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
extern const char battle_fragment_source[];
static const char vertex[] =
 "#version 450 core\n"
 "uniform vec2 origin,extent; out vec3 colour; out float distanceFog;"
 "out float effectAlpha; out vec2 effectUV; flat out int effectType;"
 "out vec3 worldPosition; flat out int materialMode;"
 "void main(){const vec2 v[3]=vec2[3](vec2(-1,-1),vec2(3,-1),vec2(-1,3));"
 "vec2 p=v[gl_VertexID]; gl_Position=vec4(p,0,1);"
 "worldPosition=vec3(origin.x+p.x*extent.x,0,origin.y+p.y*extent.y);"
 "colour=vec3(1); distanceFog=0;effectAlpha=1;effectUV=vec2(0);"
 "effectType=0;materialMode=1;}";
static GLuint shader(GLenum type,const char *source){
 GLuint id=glCreateShader(type);glShaderSource(id,1,&source,0);glCompileShader(id);
 GLint good;glGetShaderiv(id,GL_COMPILE_STATUS,&good);
 if(!good){char text[8192];glGetShaderInfoLog(id,sizeof text,0,text);fprintf(stderr,"%s\n",text);exit(2);}return id;
}
int main(int argc,char **argv){
 Display *display=XOpenDisplay(0);if(!display)return 3;
 int attrs[]={GLX_RGBA,GLX_RED_SIZE,8,GLX_GREEN_SIZE,8,GLX_BLUE_SIZE,8,None};
 XVisualInfo *visual=glXChooseVisual(display,DefaultScreen(display),attrs);if(!visual)return 4;
 XSetWindowAttributes wa={0};wa.colormap=XCreateColormap(display,RootWindow(display,visual->screen),visual->visual,AllocNone);
 Window window=XCreateWindow(display,RootWindow(display,visual->screen),0,0,512,512,0,visual->depth,InputOutput,visual->visual,CWColormap,&wa);
 GLXContext context=glXCreateContext(display,visual,0,True);if(!context||!glXMakeCurrent(display,window,context))return 5;
 fprintf(stderr,"GL renderer: %s\nGL version: %s\n",glGetString(GL_RENDERER),glGetString(GL_VERSION));
 GLuint program=glCreateProgram();glAttachShader(program,shader(GL_VERTEX_SHADER,vertex));glAttachShader(program,shader(GL_FRAGMENT_SHADER,battle_fragment_source));glLinkProgram(program);
 GLint good;glGetProgramiv(program,GL_LINK_STATUS,&good);if(!good){char text[8192];glGetProgramInfoLog(program,sizeof text,0,text);fprintf(stderr,"%s\n",text);return 6;}
 glUseProgram(program);GLuint vao;glGenVertexArrays(1,&vao);glBindVertexArray(vao);
 GLuint texture;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D_ARRAY,texture);
 // Equal total albedo avoids introducing derivative lighting differences.
 unsigned char layers[]={0,255,0,255,0,255,0,255,255,0,0,255,0,255,0,255};
 glTexImage3D(GL_TEXTURE_2D_ARRAY,0,GL_RGBA8,1,1,4,0,GL_RGBA,GL_UNSIGNED_BYTE,layers);
 glTexParameteri(GL_TEXTURE_2D_ARRAY,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D_ARRAY,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glUniform1i(glGetUniformLocation(program,"terrainTextures"),0);
 glUniform4f(glGetUniformLocation(program,"weather"),0,0,0,0);
 glDrawBuffer(GL_FRONT);glReadBuffer(GL_FRONT);glPixelStorei(GL_PACK_ALIGNMENT,1);
 int n; if(scanf("%d",&n)!=1)return 7;
 for(int i=0;i<n;i++){
  float x,z;if(scanf("%f %f",&x,&z)!=2)return 8;
  glViewport(0,0,65,65);glUniform2f(glGetUniformLocation(program,"origin"),x,z);
  glUniform2f(glGetUniformLocation(program,"extent"),.5,.5);
  glUniform3f(glGetUniformLocation(program,"camera"),x,100,z);
  glDrawArrays(GL_TRIANGLES,0,3);unsigned char rgb[3];glReadPixels(32,32,1,1,GL_RGB,GL_UNSIGNED_BYTE,rgb);
  printf("%u %u %u\n",rgb[0],rgb[1],rgb[2]);
 }
 // Actual production material path with diagnostic textures, top-down dogleg.
 glViewport(0,0,512,512);glUniform2f(glGetUniformLocation(program,"origin"),4000,1150);
 glUniform2f(glGetUniformLocation(program,"extent"),400,200);
 glUniform3f(glGetUniformLocation(program,"camera"),4000,100,1150);
 glDrawArrays(GL_TRIANGLES,0,3);unsigned char *pixels=malloc(512*512*3);
 glReadPixels(0,0,512,512,GL_RGB,GL_UNSIGNED_BYTE,pixels);
 FILE *out=fopen(argv[1],"wb");if(!out)return 9;fprintf(out,"P6\n512 512\n255\n");
 for(int y=511;y>=0;y--)fwrite(pixels+y*512*3,1,512*3,out);fclose(out);free(pixels);
 if(glGetError()!=GL_NO_ERROR)return 10;
 glXMakeCurrent(display,None,0);glXDestroyContext(display,context);XDestroyWindow(display,window);XFree(visual);XCloseDisplay(display);return 0;
}
'''


def embedded_fragment(executable):
    """Read actual executable LOAD segment rather than trusting source presence."""
    symbols = subprocess.check_output(['nm', '-n', str(executable)], text=True)
    address = next(int(line.split()[0], 16) for line in symbols.splitlines()
                   if line.split()[-1:] == ['battle_fragment_source'])
    data = executable.read_bytes()
    assert data[:5] == b'\x7fELF\x02' and data[5] == 1
    phoff = struct.unpack_from('<Q', data, 32)[0]
    entsize, count = struct.unpack_from('<HH', data, 54)
    for i in range(count):
        kind, _, offset, virtual, _, size, _, _ = struct.unpack_from('<II6Q', data, phoff+i*entsize)
        if kind == 1 and virtual <= address < virtual+size:
            begin = offset+address-virtual
            return data[begin:data.index(0, begin)]
    raise AssertionError('shader source outside executable LOAD segments')


def distance(point, segment):
    x,z = point; a,b,c,d = segment['from']+segment['to']
    dx,dz = c-a,d-b
    t = max(0.,min(1.,((x-a)*dx+(z-b)*dz)/(dx*dx+dz*dz)))
    return math.hypot(x-a-t*dx,z-b-t*dz)-segment['half_width']


def main():
    template = (ROOT/'shaders/battle.frag').read_bytes()
    assert template[:18] == b'#version 450 core\n', 'assembly prefix length changed'
    fragment = template[:18]+(ROOT/'shaders/terrain_roads.glsl').read_bytes()+(ROOT/'shaders/airbases.glsl').read_bytes()+template[18:]
    if len(sys.argv)>1:
        assert embedded_fragment(pathlib.Path(sys.argv[1]).resolve()) == fragment, 'client fragment differs from tested NASM source'
    roads = json.loads((ROOT/'content/terrain/roads.json').read_text())['roads']
    points = []
    # Every canonical segment midpoint, with normal cross-section around the
    # authoritative 10 m edge and the explicitly cosmetic 2 m shoulder.
    for index, road in enumerate(roads):
        a,b = road['from'],road['to']; dx,dz = b[0]-a[0],b[1]-a[1]
        norm=math.hypot(dx,dz); centre=((a[0]+b[0])/2,(a[1]+b[1])/2)
        for offset in (0.,9.5,10.,10.5,11.,11.5,12.1,20.):
            points.append((f'segment-{index}-offset-{offset}',(centre[0]-dz/norm*offset,centre[1]+dx/norm*offset)))
    for z in (1300.,3900.,6500.):
        points.append((f'old-wall-crossing-{z}',(4000.,z)))
        points.append((f'dogleg-{z}',(4000.,z-250.)))
    # Capsule cap in isolation, plus all four cross-front connector interiors.
    for x in (1000.,7000.):
        for z in (2600.,5200.): points.append((f'connector-{x}-{z}',(x,z)))
    # Outside both segments at a dogleg corner: the union has a true circular
    # capsule cap here, independently of the straight side boundaries.
    for z in (1050.,3650.,6250.):
        for offset in (0.,9.5,10.,10.5,11.,11.5,12.1,20.):
            points.append((f'corner-cap-{z}-{offset}',(3920.-offset/math.sqrt(2),z-offset/math.sqrt(2))))
    read_fd,write_fd=os.pipe(); server=None
    try:
        with tempfile.TemporaryDirectory(prefix='rh-road-gl-') as folder:
            folder=pathlib.Path(folder)
            with (folder/'xvfb.log').open('wb') as log:
                server=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','512x512x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=log,stderr=log)
            os.close(write_fd);write_fd=-1

            display=read_display_number(read_fd,10);assert display.isdigit()
            os.close(read_fd);read_fd=-1
            env=dict(os.environ,DISPLAY=':'+display,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
            (folder/'driver.c').write_text(DRIVER)
            nasm=os.environ.get('RED_HORIZON_NASM','nasm')
            subprocess.run([nasm,'-f','elf64','src/render/shaders.asm','-o',str(folder/'shaders.o')],cwd=ROOT,check=True,capture_output=True)
            subprocess.run(['cc','-O2',str(folder/'driver.c'),str(folder/'shaders.o'),'-lGL','-lX11','-o',str(folder/'driver')],check=True,capture_output=True)
            screenshot=pathlib.Path(tempfile.gettempdir())/'red-horizon-road-dogleg.ppm'
            payload=str(len(points))+'\n'+''.join(f'{p[0]} {p[1]}\n' for _,p in points)
            result=subprocess.run([str(folder/'driver'),str(screenshot)],input=payload,env=env,text=True,capture_output=True,timeout=30)
            assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
            assert 'llvmpipe' in result.stderr.lower() or 'softpipe' in result.stderr.lower(), result.stderr
            samples=[list(map(int,line.split())) for line in result.stdout.splitlines()]
            assert len(samples)==len(points)
            reports=[]
            for (label,point),rgb in zip(points,samples):
                edge=min(distance(point,road) for road in roads if road['flags']&1)
                t=max(0.,min(1.,edge/2.)); corridor=1.-t*t*(3.-2.*t)
                # Rock variation can dilute the gravel by at most 25%; site
                # material remains unchanged and may contribute independently.
                objective_point=((point[0]%2000)-1000,(point[1]%2600)-1300)
                d=math.hypot(*objective_point); t=max(0.,min(1.,(d-28.)/47.))
                objective=1.-t*t*(3.-2.*t)
                blend=max(corridor*.72,objective*.8)
                ratio=rgb[0]/max(1,rgb[0]+rgb[1])
                assert blend*.75-.025<=ratio<=blend+.025,(label,point,edge,blend,rgb,ratio)
                if label.startswith('old-wall'): assert ratio<.02,(label,rgb)
                if label.startswith(('dogleg','connector')): assert ratio>.52,(label,rgb)
                reports.append(dict(label=label,world_xz=point,edge_metres=edge,rgb=rgb,gravel_fraction=ratio))
            print(json.dumps(dict(suite='canonical-road-material-gl',passed=True,software_rendered=True,context=result.stderr.strip(),embedded_fragment_sha256=hashlib.sha256(fragment).hexdigest(),client_embedded_source_checked=len(sys.argv)>1,canonical_segments=len(roads),samples=len(points),shoulder_metres=2,old_wall_stripes_absent=3,connectors_visible=4,fixture='real production NASM-embedded fragment, flat test geometry and diagnostic equal-albedo textures; not gameplay or art acceptance',screenshot=str(screenshot),measurements=reports)))
    finally:
        if read_fd>=0:os.close(read_fd)
        if write_fd>=0:os.close(write_fd)
        if server is not None:
            server.terminate()
            try:server.wait(timeout=3)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)


if __name__=='__main__': main()
