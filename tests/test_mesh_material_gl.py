#!/usr/bin/env python3
"""Production embedded mesh vertex+fragment raster proof; development-only GLX.
Camera/weather paired controls and rotated-normal invariance exercise material
response without changing gameplay. The previous fragment is a negative control.
This is a software-rendered diagnostic, not HDR, target GPU or artistic acceptance.
"""
import hashlib, importlib.util, json, math, os, pathlib, select, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief_gl',ROOT/'tests/test_relief_gl.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
DRIVER=r'''
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <X11/Xlib.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
extern const char mesh_vertex_source[],mesh_fragment_source[];
const char *oldFragment="#version 450 core\nin vec3 colour;in float distanceFog;uniform vec4 weather;uniform int meshMode;layout(location=0)out vec4 outputColour;flat in uint actorCode;layout(location=1)out uint outputActorCode;void main(){outputActorCode=actorCode;float fog=(meshMode==1||meshMode==2)?0.:1.-exp(-distanceFog*(.00018+weather.w));vec3 fogColour=mix(vec3(.49,.61,.68),vec3(.49,.53,.55),weather.y);outputColour=vec4(mix(colour,fogColour,fog),1);}";
GLuint stage(GLenum t,const char *source){GLuint s=glCreateShader(t);glShaderSource(s,1,&source,0);glCompileShader(s);GLint ok;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char log[16000];glGetShaderInfoLog(s,sizeof log,0,log);fprintf(stderr,"%s",log);exit(2);}return s;}
GLuint program(const char *fragment){GLuint p=glCreateProgram();glAttachShader(p,stage(GL_VERTEX_SHADER,mesh_vertex_source));glAttachShader(p,stage(GL_FRAGMENT_SHADER,fragment));glLinkProgram(p);GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok){char log[16000];glGetProgramInfoLog(p,sizeof log,0,log);fprintf(stderr,"%s",log);exit(3);}return p;}
int main(){Display *d=XOpenDisplay(0);if(!d)return 4;int a[]={GLX_RGBA,GLX_RED_SIZE,8,None};XVisualInfo *v=glXChooseVisual(d,DefaultScreen(d),a);if(!v)return 5;XSetWindowAttributes wa={0};wa.colormap=XCreateColormap(d,RootWindow(d,v->screen),v->visual,AllocNone);Window w=XCreateWindow(d,RootWindow(d,v->screen),0,0,64,64,0,v->depth,InputOutput,v->visual,CWColormap,&wa);GLXContext c=glXCreateContext(d,v,0,True);if(!c||!glXMakeCurrent(d,w,c))return 6;fprintf(stderr,"%s / %s\n",glGetString(GL_RENDERER),glGetString(GL_VERSION));GLuint programs[]={program(mesh_fragment_source),program(oldFragment)};
 GLuint vao,buffer,fbo,textures[2];glGenVertexArrays(1,&vao);glBindVertexArray(vao);glGenBuffers(1,&buffer);glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffer);glBindBufferBase(GL_SHADER_STORAGE_BUFFER,3,buffer);
 glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glGenTextures(2,textures);glBindTexture(GL_TEXTURE_2D,textures[0]);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,64,64,0,GL_RGBA,GL_FLOAT,0);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[0],0);glBindTexture(GL_TEXTURE_2D,textures[1]);glTexImage2D(GL_TEXTURE_2D,0,GL_R32UI,64,64,0,GL_RED_INTEGER,GL_UNSIGNED_INT,0);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT1,GL_TEXTURE_2D,textures[1],0);GLenum attachments[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(2,attachments);if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return 7;glViewport(0,0,64,64);
 int count;if(scanf("%d",&count)!=1)return 8;
 for(int i=0;i<count;i++){float nx,ny,nz,vx,vy,vz,cloud,rain,yaw,pitch,bank;int role,side,mode;if(scanf("%f %f %f %f %f %f %f %f %d %d %d %f %f %f",&nx,&ny,&nz,&vx,&vy,&vz,&cloud,&rain,&role,&side,&mode,&yaw,&pitch,&bank)!=14)return 9;
 float vertices[36]={0};float x[]={-2000,2000,0},z[]={-2000,-2000,2000};for(int k=0;k<3;k++){vertices[k*12]=mode==2?x[k]*.00015:x[k];vertices[k*12+1]=mode==2?z[k]*.00015:0;vertices[k*12+2]=mode==2?0:z[k];vertices[k*12+4]=nx;vertices[k*12+5]=ny;vertices[k*12+6]=nz;vertices[k*12+8]=.3;vertices[k*12+9]=.35;vertices[k*12+10]=.4;}
 glBufferData(GL_SHADER_STORAGE_BUFFER,sizeof vertices,vertices,GL_STREAM_DRAW);
 for(int j=0;j<2;j++){GLuint p=programs[j];glUseProgram(p);glUniform1i(glGetUniformLocation(p,"meshMode"),mode);glUniform1i(glGetUniformLocation(p,"tactical"),1);glUniform1i(glGetUniformLocation(p,"censusDetail"),1);glUniform2i(glGetUniformLocation(p,"meshGeometry"),0,3);glUniform1f(glGetUniformLocation(p,"meshScale"),1);glUniform2f(glGetUniformLocation(p,"halfViewport"),32,32);glUniform2f(glGetUniformLocation(p,"projection"),1,1);glUniform4f(glGetUniformLocation(p,"weather"),0,cloud,rain,0);
 // Centre sample lies at this exact world position in the tactical projection.
 float planeX=-cosf(yaw)*sinf(bank)-sinf(yaw)*cosf(bank)*sinf(pitch);
 float planeY=cosf(bank)*cosf(pitch),planeZ=sinf(yaw)*sinf(bank)-cosf(yaw)*cosf(bank)*sinf(pitch);
 float heightOffset=-(planeX+planeZ)*67.1875f/planeY;
 glUniform3f(glGetUniformLocation(p,"camera"),4067.1875f+vx*1000,100+heightOffset+vy*1000,4067.1875f+vz*1000);
 glVertexAttrib4f(0,4000,100,4000,yaw);glVertexAttrib4f(1,0,0,0,pitch);glVertexAttrib4f(2,1,1,1,bank);glVertexAttrib4f(3,7,side,role,1);
 float clear[4]={0,0,0,0};GLuint zero[4]={0};glClearBufferfv(GL_COLOR,0,clear);glClearBufferuiv(GL_COLOR,1,zero);glDrawArrays(GL_TRIANGLES,0,3);float rgba[4];GLuint id;int px=mode==2?40:32,py=mode==2?18:32;glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(px,py,1,1,GL_RGBA,GL_FLOAT,rgba);glReadBuffer(GL_COLOR_ATTACHMENT1);glReadPixels(px,py,1,1,GL_RED_INTEGER,GL_UNSIGNED_INT,&id);printf("%.9g %.9g %.9g %.9g %u%s",rgba[0],rgba[1],rgba[2],rgba[3],id,j?"\n":" ");}
 }
 int error=glGetError();glXMakeCurrent(d,None,0);glXDestroyContext(d,c);XDestroyWindow(d,w);XFree(v);XCloseDisplay(d);return error?10:0;}
'''
def unit(a):
    length=math.sqrt(sum(v*v for v in a));return tuple(v/length for v in a)
def rotate(a,yaw,pitch,bank):
    x,y,z=a;cb,sb,cp,sp,cy,sy=math.cos(bank),math.sin(bank),math.cos(pitch),math.sin(pitch),math.cos(yaw),math.sin(yaw)
    x,y=cb*x-sb*y,sb*x+cb*y;y,z=cp*y+sp*z,-sp*y+cp*z
    return (cy*x+sy*z,y,-sy*x+cy*z)
def delta(a,b):return max(abs(x-y) for x,y in zip(a[:3],b[:3]))
def main():
    exe=pathlib.Path(sys.argv[1]).resolve()
    sources={'mesh_vertex_source':helper.compose(ROOT/'shaders/mesh.vert'),'mesh_fragment_source':(ROOT/'shaders/mesh.frag').read_bytes()}
    for name,source in sources.items():assert helper.embedded(exe,name)==source,(name,'client differs from tested production source')
    sun=unit((.35,.85,-.2));normal=(0,1,0);reflection=(-sun[0],sun[1],-sun[2]);away=unit((1,.08,1))
    cases=[];labels={}
    def add(label,n=normal,view=reflection,cloud=0,rain=0,role=3,side=0,mode=0,yaw=0,pitch=0,bank=0):
        labels[label]=len(cases);cases.append((*n,*view,cloud,rain,role,side,mode,yaw,pitch,bank))
    for role in (0,1,2,3,4,5,6,7,8):
        for side in (0,1,2,3):
            for wet in (0,1):
                for view in ('peak','away'):
                    add(f'{role}-{side}-{wet}-{view}',view=reflection if view=='peak' else away,role=role,side=side,rain=wet)
    for cloud in (0,.5,1):
        for view in ('peak','away'):add(f'cloud-{cloud}-{view}',cloud=cloud,view=reflection if view=='peak' else away)
    add('back-lit',n=tuple(-v for v in sun),view=tuple(-v for v in sun));add('camera-at-surface',view=(0,0,0))
    for mode in (1,2):
        for wet in (0,1):add(f'mode-{mode}-{wet}',rain=wet,mode=mode)
    for i in range(20):
        n=unit((math.sin(i*.7),.75,math.cos(i*.7)));yaw=(i-10)*.12;pitch=(i%3-1)*.1;bank=(i%5-2)*.08
        add(f'rotation-{i}',n=n,yaw=yaw,pitch=pitch,bank=bank)
        add(f'normal-{i}',n=rotate(n,yaw,pitch,bank))
    read,write=os.pipe();server=None
    try:
        with tempfile.TemporaryDirectory(prefix='rh-material-gl-') as tmp:
            folder=pathlib.Path(tmp)
            with (folder/'xvfb.log').open('wb') as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','64x64x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
            os.close(write);write=-1;assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
            env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
            (folder/'driver.c').write_text(DRIVER)
            subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','src/render/mesh_shaders.asm','-o',str(folder/'shaders.o')],cwd=ROOT,check=True,capture_output=True)
            subprocess.run(['cc','-O2',str(folder/'driver.c'),str(folder/'shaders.o'),'-lGL','-lX11','-lm','-o',str(folder/'driver')],check=True,capture_output=True)
            payload=str(len(cases))+'\n'+''.join(' '.join(map(str,c))+'\n' for c in cases)
            run=subprocess.run([str(folder/'driver')],input=payload,text=True,capture_output=True,env=env,timeout=45);assert run.returncode==0,(run.returncode,run.stderr)
            rows=[tuple(map(float,line.split())) for line in run.stdout.splitlines()];assert len(rows)==len(cases)
            for case,row in zip(cases,rows):
                assert len(row)==10 and all(math.isfinite(v) for v in row) and row[3]==row[8]==1,(case,row)
                expected=65544 if case[9] in (0,1) and case[10]!=2 else 0
                assert row[4]==row[9]==expected,(case,row,'visibility ID changed')
                assert all(0<=v<=1 for v in row[:3]),(case,row,'bounded material output')
            get=lambda label:rows[labels[label]]
            effects={}
            for role in (0,1,2,3,4,5,6,7,8):
                for side in (0,1,2,3):
                    dry=delta(get(f'{role}-{side}-0-peak'),get(f'{role}-{side}-0-away'))
                    wet=delta(get(f'{role}-{side}-1-peak'),get(f'{role}-{side}-1-away'))
                    assert delta(get(f'{role}-{side}-0-peak')[5:],get(f'{role}-{side}-0-away')[5:])==0,'old shader camera negative control failed'
                    assert delta(get(f'{role}-{side}-0-peak')[5:],get(f'{role}-{side}-1-peak')[5:])==0,'old shader rain negative control failed'
                    if side==3 and role in (1,2,3,8):assert dry==wet==0,'wreck acquired polished highlight'
                    elif role in (0,5,6,7):assert .01<dry<.03 and abs(wet-dry)<1e-6,'cloth acquired rain coating'
                    else:assert dry>.03 and wet>dry+.025,(role,side,dry,wet,'camera/rain response missing')
                    effects[f'{role}-{side}']={'dry_view_delta':dry,'wet_view_delta':wet}
            cloud_deltas=[delta(get(f'cloud-{c}-peak'),get(f'cloud-{c}-away')) for c in (0,.5,1)]
            assert cloud_deltas[0]>cloud_deltas[1]>cloud_deltas[2]>0 and cloud_deltas[2]<cloud_deltas[0]*.25,cloud_deltas
            rotation_error=max(delta(get(f'rotation-{i}'),get(f'normal-{i}')) for i in range(20));assert rotation_error<.00002,rotation_error
            for mode in (1,2):
                for wet in (0,1):assert delta(get(f'mode-{mode}-{wet}'),get(f'mode-{mode}-{wet}')[5:])==0,'marker/weapon presentation changed'
            assert delta(get('back-lit'),get('camera-at-surface'))>.01
            print(json.dumps(dict(suite='mesh-material-production-gl',passed=True,cases=len(cases),draws=len(cases)*2,source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in sources.items()},software_context=run.stderr.strip(),role_side_responses=effects,cloud_view_deltas=cloud_deltas,rotated_normal_max_error=rotation_error,actor_ids_preserved=True,marker_weapon_unchanged=True,old_fragment_camera_negative_control=True,scope='Actual embedded vertex/fragment raster with declared synthetic source triangles, float colour and integer actor attachments; no authority modification, HDR/shadows/target GPU/performance or artistic quality claim')))
    finally:
        if read>=0:os.close(read)
        if write>=0:os.close(write)
        if server is not None:server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
