#!/usr/bin/env python3
"""Actual embedded plume shader: independent ballistic trail, cap and expiry."""
import importlib.util,json,math,os,pathlib,select,struct,subprocess,sys,tempfile,hashlib
R=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief',R/'tests/test_relief_gl.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
DRIVER='\n#define GL_GLEXT_PROTOTYPES\n#include <GL/gl.h>\n#include <GL/glext.h>\n#include <GL/glx.h>\n#include <X11/Xlib.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <stdint.h>\n#include <string.h>\nextern const char battle_vertex_source[];\nstatic float bits(uint32_t x){float f;memcpy(&f,&x,4);return f;}\nint main(){Display*d=XOpenDisplay(0);if(!d)return 2;int attrs[]={GLX_RGBA,GLX_RED_SIZE,8,None};XVisualInfo*v=glXChooseVisual(d,DefaultScreen(d),attrs);if(!v)return 3;XSetWindowAttributes a={0};a.colormap=XCreateColormap(d,RootWindow(d,v->screen),v->visual,AllocNone);Window w=XCreateWindow(d,RootWindow(d,v->screen),0,0,32,32,0,v->depth,InputOutput,v->visual,CWColormap,&a);GLXContext c=glXCreateContext(d,v,0,True);if(!c||!glXMakeCurrent(d,w,c))return 4;\n GLuint s=glCreateShader(GL_VERTEX_SHADER);const char*source=battle_vertex_source;glShaderSource(s,1,&source,0);glCompileShader(s);GLint ok;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char b[16000];glGetShaderInfoLog(s,sizeof b,0,b);fprintf(stderr,"%s",b);return 5;}GLuint p=glCreateProgram();glAttachShader(p,s);const char*names[]={"worldPosition","colour","effectAlpha","effectUV","effectType"};glTransformFeedbackVaryings(p,5,names,GL_INTERLEAVED_ATTRIBS);glLinkProgram(p);glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok)return 6;glUseProgram(p);GLuint vao,buffer;glGenVertexArrays(1,&vao);glBindVertexArray(vao);glGenBuffers(1,&buffer);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,buffer);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,buffer);glEnable(GL_RASTERIZER_DISCARD);glUniform1i(glGetUniformLocation(p,"terrain"),15);glUniform2f(glGetUniformLocation(p,"projection"),1,1);glUniform3f(glGetUniformLocation(p,"camera"),2000,150,1900);glUniform2f(glGetUniformLocation(p,"angle"),0,0);\n int n;if(scanf("%d",&n)!=1)return 7;for(int j=0;j<n;j++){int kind,identity,instances,map;float ttl;if(scanf("%d %d %d %d %f",&kind,&identity,&instances,&map,&ttl)!=5)return 8;glUniform1i(glGetUniformLocation(p,"tactical"),map);glVertexAttrib4f(0,2000,150,2000,ttl);glVertexAttrib4f(1,0,kind==1?-.12:0,kind==1?7:0,bits(identity));glVertexAttrib4f(2,bits(kind),0,0,0);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,instances*120*40,0,GL_STREAM_READ);glBeginTransformFeedback(GL_POINTS);glDrawArraysInstanced(GL_POINTS,0,120,instances);glEndTransformFeedback();float*data=malloc(instances*120*40);glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,instances*120*40,data);if(fwrite((char*)data+(instances-1)*120*40,40,120,stdout)!=120)return 9;free(data);}int error=glGetError();glXMakeCurrent(d,None,0);glXDestroyContext(d,c);XDestroyWindow(d,w);XFree(v);XCloseDisplay(d);return error?10:0;}\n'
exe=pathlib.Path(sys.argv[1]);shader=helper.compose(R/'shaders/battle.vert');assert helper.embedded(exe,'battle_vertex_source')==shader
cases=[(state,identity,1,map,age)for state in (1,2)for identity in (1,4294967295)for map in (0,1)for age in (0.,1.,3.,6.,18.,19.,20.)]+[(1,1,32,0,3.)]
read,write=os.pipe();server=None
try:
 with tempfile.TemporaryDirectory(prefix='rh-plume-gl-')as d:
  td=pathlib.Path(d);server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','64x64x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(write);write=-1;assert select.select([read],[],[],10)[0];display=os.read(read,32).decode().strip();os.close(read);read=-1
  (td/'driver.c').write_text(DRIVER);subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','-I',str(R)+'/',str(R/'src/render/shaders.asm'),'-o',str(td/'shader.o')],cwd=R,check=True);subprocess.run(['cc','-O2',str(td/'driver.c'),str(td/'shader.o'),'-lGL','-lX11','-o',str(td/'driver')],check=True)
  env=dict(os.environ,DISPLAY=':'+display,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
  run=subprocess.run([str(td/'driver')],input=(str(len(cases))+'\n'+'\n'.join(' '.join(map(str,c))for c in cases)+'\n').encode(),env=env,capture_output=True,timeout=30);assert run.returncode==0,run.stderr.decode();assert len(run.stdout)==len(cases)*120*40
  maximum=0.;outputs=[]
  for i,(state,identity,instances,map,age)in enumerate(cases):
   rows=[struct.unpack_from('<9fi',run.stdout,(i*120+j)*40)for j in range(120)];outputs.append(rows)
   assert all(all(math.isfinite(x)for x in row[:9])for row in rows)
   hidden=map or age>=20
   assert all((r[1]<-9000)==bool(hidden)for r in rows)
   for particle in range(20):
    part=rows[particle*6:particle*6+6];assert all(0<=r[6]<=.720001 for r in part)
    if particle<16:assert all(r[6]<=.060001 for r in part)
    if hidden:continue
    h=(identity*1664525+particle*1013904223)&0xffffffff;h^=h>>16;h=(h*2246822519)&0xffffffff;h^=h>>13;seed=(h&65535)/65535
    fire=particle>=16;lag=0 if fire else min(age,particle/15*.6);steps=lag*30
    x=2000+lag*(1+seed);y=150+lag*(2+seed*2);z=2000
    if state==1:y+=.12*steps-.0109*steps*(steps+1)*.5;z-=7*steps
    if fire:
     phase=age*(7+seed*4)+seed*6.2831853;x+=math.cos(phase)*.9;y+=3.+seed*1.5;z+=math.sin(phase)*.9
    centre=tuple(sum(r[k]for r in part)/6 for k in range(3));error=max(abs(a-b)for a,b in zip(centre,(x,y,z)));maximum=max(maximum,error);assert error<.002,(i,particle,error)
  assert outputs[-1]==outputs[cases.index((1,1,1,0,3.))],'pool slot changed seed geometry'
  print(json.dumps(dict(suite='air-crash-plume-embedded-GL',passed=True,cases=len(cases),vertices=len(cases)*120,maximum_centre_error_m=maximum,smoke_alpha_max=.06,finite_source_age=True,map_and_expiry_hidden=True,slot_independent=True,logical_quad_cap=640,scope='Actual embedded vertex shader under software GL, independent analytic centres. Full client pixels/quality/timing are separate.')))
finally:
 if read>=0:os.close(read)
 if write>=0:os.close(write)
 if server is not None:server.terminate();server.wait(timeout=5)
