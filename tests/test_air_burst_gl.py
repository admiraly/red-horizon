#!/usr/bin/env python3
"""Actual embedded GPU particle motion/bounds/seed oracle; dev C/GLX only."""
import importlib.util,json,math,os,pathlib,select,struct,subprocess,sys,tempfile,hashlib
R=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief',R/'tests/test_relief_gl.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
DRIVER=r'''
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
extern const char battle_vertex_source[];
static float bits(uint32_t x){float f;memcpy(&f,&x,4);return f;}
int main(){Display*d=XOpenDisplay(0);if(!d)return 2;int attrs[]={GLX_RGBA,GLX_RED_SIZE,8,None};XVisualInfo*v=glXChooseVisual(d,DefaultScreen(d),attrs);if(!v)return 3;XSetWindowAttributes a={0};a.colormap=XCreateColormap(d,RootWindow(d,v->screen),v->visual,AllocNone);Window w=XCreateWindow(d,RootWindow(d,v->screen),0,0,32,32,0,v->depth,InputOutput,v->visual,CWColormap,&a);GLXContext c=glXCreateContext(d,v,0,True);if(!c||!glXMakeCurrent(d,w,c))return 4;
 GLuint s=glCreateShader(GL_VERTEX_SHADER);const char*source=battle_vertex_source;glShaderSource(s,1,&source,0);glCompileShader(s);GLint ok;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char b[16000];glGetShaderInfoLog(s,sizeof b,0,b);fprintf(stderr,"%s",b);return 5;}GLuint p=glCreateProgram();glAttachShader(p,s);const char*names[]={"worldPosition","colour","effectAlpha","effectUV","effectType"};glTransformFeedbackVaryings(p,5,names,GL_INTERLEAVED_ATTRIBS);glLinkProgram(p);glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok)return 6;glUseProgram(p);GLuint vao,buffer;glGenVertexArrays(1,&vao);glBindVertexArray(vao);glGenBuffers(1,&buffer);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,buffer);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,buffer);glEnable(GL_RASTERIZER_DISCARD);glUniform1i(glGetUniformLocation(p,"terrain"),7);glUniform2f(glGetUniformLocation(p,"projection"),1,1);glUniform3f(glGetUniformLocation(p,"camera"),2000,150,1900);glUniform2f(glGetUniformLocation(p,"angle"),0,0);
 int n;if(scanf("%d",&n)!=1)return 7;for(int j=0;j<n;j++){int kind,identity,instances,map;float ttl;if(scanf("%d %d %d %d %f",&kind,&identity,&instances,&map,&ttl)!=5)return 8;glUniform1i(glGetUniformLocation(p,"tactical"),map);glVertexAttrib4f(0,2000,150,2000,ttl);glVertexAttrib4f(1,kind==1?2010:8,kind==1?150:bits(identity),kind==1?2000:0,bits(kind));glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,instances*96*40,0,GL_STREAM_READ);glBeginTransformFeedback(GL_POINTS);glDrawArraysInstanced(GL_POINTS,0,96,instances);glEndTransformFeedback();float*data=malloc(instances*96*40);glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,instances*96*40,data);if(fwrite((char*)data+(instances-1)*96*40,40,96,stdout)!=96)return 9;free(data);}int error=glGetError();glXMakeCurrent(d,None,0);glXDestroyContext(d,c);XDestroyWindow(d,w);XFree(v);XCloseDisplay(d);return error?10:0;}
'''
exe=pathlib.Path(sys.argv[1]);shader=helper.compose(R/'shaders/battle.vert');assert helper.embedded(exe,'battle_vertex_source')==shader
cases=[]
for kind in (8,9):
 for age in (0,.2,.5,1,2,3,5,6):
  for identity in (3,400123):cases.append((kind,identity,1,0,(6 if kind==8 else 3)-age))
for kind in range(1,8):cases.append((kind,3,1,0,.12 if kind==1 else .3))
cases += [(8,3,7,0,5),(9,3,7,0,2),(8,3,1,1,5),(9,3,1,1,2)]
read,write=os.pipe();server=None
try:
 with tempfile.TemporaryDirectory(prefix='rh-air-burst-gl-') as tmp:
  t=pathlib.Path(tmp);log=(t/'xvfb.log').open('wb');server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','64x64x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log);os.close(write);write=-1;assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();os.close(read);read=-1;assert number.isdigit()
  (t/'driver.c').write_text(DRIVER);subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','-I',str(R)+'/',str(R/'src/render/shaders.asm'),'-o',str(t/'shader.o')],cwd=R,check=True)
  subprocess.run(['cc','-O2',str(t/'driver.c'),str(t/'shader.o'),'-lGL','-lX11','-o',str(t/'driver')],check=True)
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
  run=subprocess.run([str(t/'driver')],input=(str(len(cases))+'\n'+'\n'.join(' '.join(map(str,c))for c in cases)+'\n').encode(),env=env,capture_output=True,timeout=30);assert run.returncode==0,run.stderr.decode();assert len(run.stdout)==len(cases)*96*40
  results=[[struct.unpack_from('<9fi',run.stdout,(i*96+j)*40)for j in range(96)]for i in range(len(cases))]
  for case,rows in zip(cases,results):
   kind,identity,instances,map,ttl=case
   assert all(all(math.isfinite(v)for v in row[:9])for row in rows),case
   for j,row in enumerate(rows):
    hidden=ttl<=0 or (kind>=8 and map) or (kind==8 and j>=48) or (kind<8 and j>=6)
    assert (row[1]<-9000)==bool(hidden),(case,j,row)
    assert 0<=row[6]<=1,(case,j,row)
    if kind==8:assert row[6]<=.095001,('decorative smoke opacity',case,j,row)
   if kind in (8,9) and ttl>0 and not map:
    assert all(abs(row[0]-2000)<70 and abs(row[2]-2000)<70 and abs(row[1]-150)<100 for row in rows if row[1]>-9000),case
  # Same real-event identity has identical particle geometry in a different slot.
  for kind,ttl in ((8,5),(9,2)):
   original=results[cases.index((kind,3,1,0,ttl))];shifted=results[cases.index((kind,3,7,0,ttl))];assert original==shifted
  # Independent analytic ejection centre, derived from event ID rather than slot.
  maximum_centre_error=0
  for case,rows in zip(cases,results):
   kind,identity,instances,map,ttl=case
   if kind!=9 or ttl<=0 or map:continue
   age=3-ttl
   for particle in range(16):
    h=(identity*1664525+particle*1013904223+1013904223)&0xffffffff
    h^=h>>16;h=(h*2246822519)&0xffffffff;h^=h>>13
    seed=(h&65535)/65535;phase=particle*2.399963+seed*1.8
    oracle=(2000+math.cos(phase)*(6+seed*10)*age,150+(3+seed*12)*age-4.905*age*age,2000+math.sin(phase)*(6+seed*10)*age)
    centre=tuple((rows[particle*6][axis]+rows[particle*6+2][axis])*.5 for axis in range(3))
    error=max(abs(x-y)for x,y in zip(oracle,centre));maximum_centre_error=max(maximum_centre_error,error);assert error<.001,(case,particle,centre,oracle,error)
  a=results[cases.index((9,3,1,0,2.5))];b=results[cases.index((9,3,1,0,2))];assert a!=b,'debris static'
  changed=results[cases.index((8,400123,1,0,5))];assert changed!=results[cases.index((8,3,1,0,5))],'event seed ignored'
  print(json.dumps({'suite':'air-burst-embedded-GL','passed':True,'cases':len(cases),'vertices':len(cases)*96,'finite_positions_and_alpha':True,'legacy_extra_quads_hidden':True,'expired_and_map_hidden':True,'event_seed_slot_independent':True,'particle_motion':True,'maximum_independent_ejection_centre_error_m':maximum_centre_error,'maximum_smoke_alpha_per_puff':.095,'worst_eight_puff_combined_opacity':1-(1-.095)**8,'shader_sha256':hashlib.sha256(shader).hexdigest(),'limits':['Actual embedded vertex shader under software GL, bounded geometry/alpha and state controls; no human quality or target GPU frame-budget claim.']}))
finally:
 for fd in (read,write):
  if fd>=0:os.close(fd)
 if server is not None:server.terminate();server.wait(timeout=3)
