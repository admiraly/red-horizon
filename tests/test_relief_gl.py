#!/usr/bin/env python3
"""Development GL proof of production vertex heights and actual 5 m triangles.
Temporary C/GLX tooling is not project runtime. GPU transform feedback reads both
embedded production vertex shaders; the geometry shader only remaps the terrain
patch into a diagnostic viewport, leaving real vertex heights/triangles intact.
"""
from xvfb_display import read_display_number
import array
import ctypes as C
import ctypes.util
import hashlib
import json
import math
import os
import pathlib
import random
import select
import signal
import struct
import subprocess
import sys
import tempfile
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
DRIVER=r'''
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
extern const char battle_vertex_source[],mesh_vertex_source[];
static const char pixel[]="#version 450 core\nin vec3 sampleWorld;layout(location=0)out vec4 record;void main(){record=vec4(sampleWorld,1);}";
static const char geom[]="#version 450 core\nlayout(triangles)in;layout(triangle_strip,max_vertices=3)out;in vec3 worldPosition[];out vec3 sampleWorld;void main(){for(int i=0;i<3;i++){sampleWorld=worldPosition[i];gl_Position=vec4((sampleWorld.x-5625)/250,(sampleWorld.z-5187.5)/437.5,0,1);EmitVertex();}EndPrimitive();}";
static GLuint shader(GLenum type,const char *source){GLuint id=glCreateShader(type);glShaderSource(id,1,&source,0);glCompileShader(id);GLint good;glGetShaderiv(id,GL_COMPILE_STATUS,&good);if(!good){char text[16384];glGetShaderInfoLog(id,sizeof text,0,text);fprintf(stderr,"%s\n",text);exit(2);}return id;}
static GLuint program(const char *source,int feedback,int geometry){GLuint id=glCreateProgram();glAttachShader(id,shader(GL_VERTEX_SHADER,source));if(geometry){glAttachShader(id,shader(GL_GEOMETRY_SHADER,geom));glAttachShader(id,shader(GL_FRAGMENT_SHADER,pixel));}if(feedback){const char *names[]={"worldPosition","gl_Position","materialMode"};const char *mesh[]={"gl_Position"};glTransformFeedbackVaryings(id,feedback==1?3:1,feedback==1?names:mesh,GL_INTERLEAVED_ATTRIBS);}glLinkProgram(id);GLint good;glGetProgramiv(id,GL_LINK_STATUS,&good);if(!good){char text[16384];glGetProgramInfoLog(id,sizeof text,0,text);fprintf(stderr,"%s\n",text);exit(3);}return id;}
static void save(const char *folder,const char *name,void *bytes,size_t count){char path[4096];snprintf(path,sizeof path,"%s/%s",folder,name);FILE *out=fopen(path,"wb");if(!out)exit(4);if(fwrite(bytes,1,count,out)!=count)exit(5);fclose(out);}
static void terrainFeedback(GLuint id,GLuint buffer,int mode,int count,const char *folder,const char *name){glUseProgram(id);glUniform1i(glGetUniformLocation(id,"terrain"),mode);glUniform1i(glGetUniformLocation(id,"tactical"),1);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,buffer);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,(size_t)count*32,0,GL_STREAM_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,buffer);glEnable(GL_RASTERIZER_DISCARD);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,count);glEndTransformFeedback();glDisable(GL_RASTERIZER_DISCARD);void *bytes=malloc((size_t)count*32);glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,(size_t)count*32,bytes);save(folder,name,bytes,(size_t)count*32);free(bytes);}
int main(int argc,char **argv){Display *display=XOpenDisplay(0);if(!display)return 6;int attrs[]={GLX_RGBA,GLX_RED_SIZE,8,GLX_GREEN_SIZE,8,GLX_BLUE_SIZE,8,None};XVisualInfo *visual=glXChooseVisual(display,DefaultScreen(display),attrs);if(!visual)return 7;XSetWindowAttributes wa={0};wa.colormap=XCreateColormap(display,RootWindow(display,visual->screen),visual->visual,AllocNone);Window window=XCreateWindow(display,RootWindow(display,visual->screen),0,0,1000,1750,0,visual->depth,InputOutput,visual->visual,CWColormap,&wa);GLXContext context=glXCreateContext(display,visual,0,True);if(!context||!glXMakeCurrent(display,window,context))return 8;fprintf(stderr,"GL renderer: %s\nGL version: %s\n",glGetString(GL_RENDERER),glGetString(GL_VERSION));GLuint vao;glGenVertexArrays(1,&vao);glBindVertexArray(vao);GLuint buffer;glGenBuffers(1,&buffer);
 GLuint terrain=program(battle_vertex_source,1,0);terrainFeedback(terrain,buffer,11,105000,argv[1],"patch.bin");terrainFeedback(terrain,buffer,1,98304,argv[1],"coarse.bin");
 GLuint mesh=program(mesh_vertex_source,2,0);glUseProgram(mesh);glUniform1i(glGetUniformLocation(mesh,"meshMode"),1);glUniform1i(glGetUniformLocation(mesh,"tactical"),1);glUniform2f(glGetUniformLocation(mesh,"halfViewport"),640,360);glVertexAttrib4f(1,0,0,0,0);glVertexAttrib4f(2,1,1,1,0);glEnable(GL_RASTERIZER_DISCARD);int n;if(scanf("%d",&n)!=1)return 9;for(int i=0;i<n;i++){float x,y,z,absolute;if(scanf("%f %f %f %f",&x,&y,&z,&absolute)!=4)return 10;glVertexAttrib4f(0,x,y,z,0);glVertexAttrib4f(3,0,0,1,absolute);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,buffer);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,48,0,GL_STREAM_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,buffer);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,3);glEndTransformFeedback();float bytes[12];glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,48,bytes);printf("%.9g\n",-bytes[2]*1000.);}glDisable(GL_RASTERIZER_DISCARD);
 GLuint raster=program(battle_vertex_source,0,1);glUseProgram(raster);glUniform1i(glGetUniformLocation(raster,"terrain"),11);glUniform1i(glGetUniformLocation(raster,"tactical"),1);GLuint fbo,texture;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1000,1750,0,GL_RGBA,GL_FLOAT,0);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);GLenum attachment=GL_COLOR_ATTACHMENT0;glDrawBuffers(1,&attachment);glReadBuffer(attachment);if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return 11;glViewport(0,0,1000,1750);glClearColor(0,0,0,0);glClear(GL_COLOR_BUFFER_BIT);glDrawArrays(GL_TRIANGLES,0,105000);float *pixels=malloc(1000*1750*4*sizeof(float));glReadPixels(0,0,1000,1750,GL_RGBA,GL_FLOAT,pixels);save(argv[1],"raster.bin",pixels,1000*1750*4*sizeof(float));free(pixels);if(glGetError()!=GL_NO_ERROR)return 12;glXMakeCurrent(display,None,0);glXDestroyContext(display,context);XDestroyWindow(display,window);XFree(visual);XCloseDisplay(display);return 0;}
'''


def embedded(executable,name):
    data=executable.read_bytes()
    symbols=subprocess.check_output(['nm','-n',str(executable)],text=True)
    address=next(int(line.split()[0],16) for line in symbols.splitlines() if line.split()[-1:]==[name])
    assert data[:6]==b'\x7fELF\x02\x01'
    offset=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
    for i in range(count):
        kind,_,start,virtual,_,length,_,_=struct.unpack_from('<II6Q',data,offset+i*size)
        if kind==1 and virtual<=address<virtual+length:
            begin=start+address-virtual;return data[begin:data.index(0,begin)]
    raise AssertionError('source outside ELF LOAD segment')


def compose(path):
    source=path.read_bytes();assert source[:18]==b'#version 450 core\n'
    return source[:18]+(ROOT/'shaders/terrain_relief.glsl').read_bytes()+source[18:]


def factor(p,b):
    if p<=b[0] or p>=b[3]:return 0.
    if p<b[1]:return (p-b[0])/(b[1]-b[0])
    if p>b[2]:return (b[3]-p)/(b[3]-b[2])
    return 1.


def base(x,z):return 12+(x-4000)**2*.000001+(z-4000)**2*.0000005+max(0.,1.-abs(x-4000)/800)*18


def client_diagnostic(executable,env):
    """Real production draw/material screenshot, frozen private camera fixture."""
    symbols={line.split()[2]:int(line.split()[0],16) for line in subprocess.check_output(['nm','-n',str(executable)],text=True).splitlines() if len(line.split())==3}
    xlib=C.CDLL(ctypes.util.find_library('X11'));D=C.c_void_p;W=C.c_ulong
    xlib.XOpenDisplay.argtypes=[C.c_char_p];xlib.XOpenDisplay.restype=D
    xlib.XGetImage.argtypes=[D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int];xlib.XGetImage.restype=D
    xlib.XGetPixel.argtypes=[D,C.c_int,C.c_int];xlib.XGetPixel.restype=W
    xlib.XDestroyImage.argtypes=[D];xlib.XCloseDisplay.argtypes=[D]
    xlib.XDefaultRootWindow.argtypes=[D];xlib.XDefaultRootWindow.restype=W
    xlib.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)]
    xlib.XFetchName.argtypes=[D,W,C.POINTER(C.c_char_p)];xlib.XFree.argtypes=[D]
    display=xlib.XOpenDisplay(env['DISPLAY'].encode());assert display
    process=None;memory=None
    try:
        with tempfile.TemporaryFile() as log:
            child_env=dict(env,RH_AUDIO_DEVICE='null')
            process=subprocess.Popen([str(executable),'--width','640','--height','360'],cwd=executable.parent,env=child_env,stdout=log,stderr=log)
            memory=os.open(f'/proc/{process.pid}/mem',os.O_RDWR)
            def u32(name):
                try:return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
                except (OSError,struct.error):return 0
            def until(predicate):
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    if predicate():return
                    assert process.poll() is None,'diagnostic client exited';time.sleep(.02)
                raise AssertionError('diagnostic client frame timeout')
            def stop():
                os.kill(process.pid,signal.SIGSTOP);_,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
            until(lambda:u32('frame_count')>=4)
            stop();os.pwrite(memory,struct.pack('<d',1e30),symbols['thirty']);os.pwrite(memory,struct.pack('<d',0),symbols['accum'])
            frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3);stop()
            os.pwrite(memory,struct.pack('<5f',5550,100,4700,0,-.06),symbols['sim_players'])
            os.pwrite(memory,struct.pack('<f',0),symbols['yaw']);os.pwrite(memory,struct.pack('<f',-.06),symbols['pitch'])
            os.pwrite(memory,struct.pack('<I',0),symbols['sim_count']);os.pwrite(memory,struct.pack('<I',0),symbols['sim_projectile_count'])
            os.pwrite(memory,bytes(2048),symbols['effects_records']);os.pwrite(memory,struct.pack('<I',0),symbols['air_trails_visible'])
            authority=tuple(os.pread(memory,size,symbols[name]) for name,size in (('sim_players',256),('sim_entities',1048576),('sim_ground_motion',1048576)))
            ticks=u32('local_sim_ticks');frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+8);stop()
            assert ticks==u32('local_sim_ticks'),'fixture simulation advanced'
            assert authority==tuple(os.pread(memory,size,symbols[name]) for name,size in (('sim_players',256),('sim_entities',1048576),('sim_ground_motion',1048576))),'hill rendering changed authority'
            # The CPU `window` is a GLFW object pointer, not an X drawable.
            root,parent,children,count=W(),W(),C.POINTER(W)(),C.c_uint()
            xlib.XQueryTree(display,xlib.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
            window=0
            for child in list(children[:count.value]):
                name=C.c_char_p()
                if xlib.XFetchName(display,child,C.byref(name)) and name:
                    if name.value.startswith(b'RED HORIZON'):window=child
                    xlib.XFree(C.cast(name,D))
            if children:xlib.XFree(children)
            assert window,'private client X drawable not found'
            image=xlib.XGetImage(display,window,0,0,640,360,W(-1).value,2);assert image
            pixels=bytearray()
            for y in range(360):
                for x in range(640):
                    value=xlib.XGetPixel(image,x,y);pixels.extend(((value>>16)&255,(value>>8)&255,value&255))
            xlib.XDestroyImage(image)
            screenshot=pathlib.Path(tempfile.gettempdir())/'red-horizon-raised-hill-client.ppm';screenshot.write_bytes(b'P6\n640 360\n255\n'+pixels)
            assert len(set(pixels))>80,'blank diagnostic hill screenshot'
            return dict(screenshot=str(screenshot),render_authority_unchanged=True,fixture='real assembly client terrain/material draws; frozen camera at (5550,100,4700), simulation-only development fixture; no natural gameplay or CPU height match claim')
    finally:
        if memory is not None:os.close(memory)
        if process is not None and process.poll() is None:
            os.kill(process.pid,signal.SIGCONT);process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        xlib.XCloseDisplay(display)


def main():
    field=json.loads((ROOT/'content/terrain/relief.json').read_text())['fields'][0]
    def height(x,z):return base(x,z)+field['height']*factor(x,field['x'])*factor(z,field['z'])
    sources={name:compose(ROOT/file) for name,file in (('battle_vertex_source','shaders/battle.vert'),('mesh_vertex_source','shaders/mesh.vert'))}
    if len(sys.argv)>1:
        executable=pathlib.Path(sys.argv[1]).resolve()
        for name,source in sources.items():assert embedded(executable,name)==source, 'client embedded '+name+' mismatch'
    queries=[(x,3,z,0) for x in (5375,5400,5480,5550,5620,5820,5875) for z in (4750,4800,5000,5200,5400,5600,5625)]
    rng=random.Random(731)
    queries += [(rng.uniform(5375,5875),3,rng.uniform(4750,5625),0) for _ in range(1000)]
    queries += [(5550,120,5200,1),(5550,120,5200,0)]
    read_fd,write_fd=os.pipe();server=None
    try:
        with tempfile.TemporaryDirectory(prefix='rh-relief-gl-') as temp:
            folder=pathlib.Path(temp)
            with (folder/'xvfb.log').open('wb') as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1000x1750x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=log,stderr=log)
            os.close(write_fd);write_fd=-1;
            number=read_display_number(read_fd,10);assert number.isdigit();os.close(read_fd);read_fd=-1
            env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
            (folder/'driver.c').write_text(DRIVER)
            nasm=os.environ.get('RED_HORIZON_NASM','nasm')
            for name in ('shaders','mesh_shaders'):subprocess.run([nasm,'-f','elf64',f'src/render/{name}.asm','-o',str(folder/(name+'.o'))],cwd=ROOT,check=True,capture_output=True)
            subprocess.run(['cc','-O2',str(folder/'driver.c'),str(folder/'shaders.o'),str(folder/'mesh_shaders.o'),'-lGL','-lX11','-o',str(folder/'driver')],check=True,capture_output=True)
            payload=str(len(queries))+'\n'+''.join(' '.join(map(str,q))+'\n' for q in queries)
            run=subprocess.run([str(folder/'driver'),str(folder)],input=payload,env=env,text=True,capture_output=True,timeout=45)
            assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
            assert 'llvmpipe' in run.stderr.lower() or 'softpipe' in run.stderr.lower(),run.stderr
            mesh=list(map(float,run.stdout.splitlines()));assert len(mesh)==len(queries)
            mesh_error=max(abs(actual-(y if absolute else y+height(x,z))) for (x,y,z,absolute),actual in zip(queries,mesh))
            assert mesh_error<.0004,mesh_error
            patch=list(struct.iter_unpack('<7fI',(folder/'patch.bin').read_bytes()));assert len(patch)==105000
            def seam_height(x,z):
                if x in (5375,5875):
                    a=math.floor(z/62.5)*62.5;t=(z-a)/62.5;return height(x,a)*(1-t)+height(x,a+62.5)*t
                if z in (4750,5625):
                    a=math.floor(x/62.5)*62.5;t=(x-a)/62.5;return height(a,z)*(1-t)+height(a+62.5,z)*t
                return height(x,z)
            vertex_error=seam_error=0.
            corner=((0,0),(1,0),(1,1),(0,0),(1,1),(0,1))
            for i,record in enumerate(patch):
                x,y,z,*_,mode=record;cell,v=divmod(i,6);off=corner[v]
                assert x==5375+(cell%100+off[0])*5 and z==4750+(cell//100+off[1])*5,(i,record)
                assert mode==1,'refined patch lost terrain material'
                error=abs(y-seam_height(x,z));vertex_error=max(vertex_error,error)
                if x in (5375,5875) or z in (4750,5625):seam_error=max(seam_error,error)
            assert vertex_error<.0001 and seam_error<.0001,(vertex_error,seam_error)
            coarse=list(struct.iter_unpack('<7fI',(folder/'coarse.bin').read_bytes()));assert len(coarse)==98304
            hidden=0
            for i,record in enumerate(coarse):
                cell=i//6;replaced=86<=cell%128<94 and 76<=cell//128<90
                if replaced:
                    hidden+=1;assert record[3:7]==(0.,0.,2.,1.),record
                else:
                    x,y,z=record[:3];assert abs(y-height(x,z))<.0001,(i,record)
            assert hidden==112*6,hidden
            pixels=array.array('f');pixels.frombytes((folder/'raster.bin').read_bytes());assert len(pixels)==1000*1750*4
            maximum=0.;where=None; covered=0
            for i in range(0,len(pixels),4):
                x,y,z,alpha=pixels[i:i+4];assert alpha==1.,'uncovered refined terrain pixel';covered+=1
                error=abs(y-height(x,z))
                if error>maximum:maximum=error;where=(x,y,z)
            assert maximum<=.027,(maximum,where)
            # Top-down height-tinted view of the actually rasterized hill. This is
            # a geometry diagnostic, not production material/art acceptance.
            image=bytearray()
            for row in range(1749,-1,-1):
                for col in range(1000):
                    i=(row*1000+col)*4;x,y,z=pixels[i:i+3];t=max(0.,min(1.,(y-base(x,z))/64))
                    image.extend((int(45+175*t),int(90+95*t),int(55+125*t)))
            screenshot=pathlib.Path(tempfile.gettempdir())/'red-horizon-raised-terrain.ppm';screenshot.write_bytes(b'P6\n1000 1750\n255\n'+image)
            client=client_diagnostic(executable,env) if len(sys.argv)>1 else None
            print(json.dumps(dict(suite='terrain-relief-geometry-gl',passed=True,software_rendered=True,context=run.stderr.strip(),client_embedded_sources_checked=len(sys.argv)>1,vertex_source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in sources.items()},patch_vertices=len(patch),coarse_vertices_hidden=hidden,mesh_height_samples=len(queries),mesh_height_max_error_metres=mesh_error,vertex_max_error_metres=vertex_error,seam_max_error_metres=seam_error,raster_pixels=covered,raster_height_max_error_metres=maximum,raster_max_error_world=where,gate_metres=.027,material_mode_preserved=True,screenshot=str(screenshot),client_diagnostic=client,fixture='production NASM vertex shaders, real GL transform feedback and actual triangle raster interpolation; viewport-only diagnostic geometry stage, height-tinted output; no CPU height integration or target GPU/art claim')))
    finally:
        if read_fd>=0:os.close(read_fd)
        if write_fd>=0:os.close(write_fd)
        if server is not None:
            server.terminate()
            try:server.wait(timeout=3)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)


if __name__=='__main__':main()
