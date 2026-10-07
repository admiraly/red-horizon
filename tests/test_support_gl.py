#!/usr/bin/env python3
"""Actual embedded sourced-mesh shader transform feedback; development only.
Uses four-corner CPU support frame as shader input, with independent source-vertex
placement/lighting observations. Client instance hooks are verified separately.
"""
from xvfb_display import read_display_number
import ctypes as C,hashlib,importlib.util,json,math,os,pathlib,select,struct,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief_gl',ROOT/'tests/test_relief_gl.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
DRIVER=r'''
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
extern const char mesh_vertex_source[];
static GLuint shader(){GLuint s=glCreateShader(GL_VERTEX_SHADER);const char *p=mesh_vertex_source;glShaderSource(s,1,&p,0);glCompileShader(s);GLint ok;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char b[16000];glGetShaderInfoLog(s,sizeof b,0,b);fprintf(stderr,"%s",b);exit(2);}return s;}
int main(int argc,char **argv){Display *d=XOpenDisplay(0);if(!d)return 3;int a[]={GLX_RGBA,GLX_RED_SIZE,8,None};XVisualInfo *v=glXChooseVisual(d,DefaultScreen(d),a);if(!v)return 4;XSetWindowAttributes wa={0};wa.colormap=XCreateColormap(d,RootWindow(d,v->screen),v->visual,AllocNone);Window w=XCreateWindow(d,RootWindow(d,v->screen),0,0,32,32,0,v->depth,InputOutput,v->visual,CWColormap,&wa);GLXContext c=glXCreateContext(d,v,0,True);if(!c||!glXMakeCurrent(d,w,c))return 5;fprintf(stderr,"%s / %s\n",glGetString(GL_RENDERER),glGetString(GL_VERSION));GLuint p=glCreateProgram();glAttachShader(p,shader());const char *names[]={"gl_Position","colour"};glTransformFeedbackVaryings(p,2,names,GL_INTERLEAVED_ATTRIBS);glLinkProgram(p);GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok)return 6;glUseProgram(p);GLuint vao,ssbo,feedback;glGenVertexArrays(1,&vao);glBindVertexArray(vao);glGenBuffers(1,&ssbo);glGenBuffers(1,&feedback);
 FILE *f=fopen(argv[1],"rb");if(!f)return 7;fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);unsigned char *pack=malloc(size);if(fread(pack,1,size,f)!=size)return 8;fclose(f);unsigned int *head=(unsigned int *)(pack+4);unsigned int mo=head[5],vo=head[7];glBindBuffer(GL_SHADER_STORAGE_BUFFER,ssbo);glBufferData(GL_SHADER_STORAGE_BUFFER,size-vo,pack+vo,GL_STATIC_DRAW);glBindBufferBase(GL_SHADER_STORAGE_BUFFER,3,ssbo);
 glUniform1i(glGetUniformLocation(p,"meshMode"),0);glUniform1i(glGetUniformLocation(p,"tactical"),0);glUniform2f(glGetUniformLocation(p,"projection"),1,1);glUniform3f(glGetUniformLocation(p,"camera"),0,0,0);glUniform2f(glGetUniformLocation(p,"angle"),0,0);glUniform4f(glGetUniformLocation(p,"weather"),0,0,0,0);glEnable(GL_RASTERIZER_DISCARD);int n;if(scanf("%d",&n)!=1)return 9;
 for(int i=0;i<n;i++){int descriptor,frame;float x,y,z,yaw,pitch,bank,absolute;if(scanf("%d %d %f %f %f %f %f %f %f",&descriptor,&frame,&x,&y,&z,&yaw,&pitch,&bank,&absolute)!=9)return 10;unsigned int *m=(unsigned int *)(pack+mo+descriptor*64);unsigned int count=m[2];float scale=*((float *)m+8);glUniform2i(glGetUniformLocation(p,"meshGeometry"),m[4],count);glUniform1f(glGetUniformLocation(p,"meshScale"),scale);glVertexAttrib4f(0,x,y,z,yaw);glVertexAttrib4f(1,frame,frame,0,pitch);glVertexAttrib4f(2,1,1,1,bank);glVertexAttrib4f(3,0,0,m[0],absolute);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,feedback);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,count*28,0,GL_STREAM_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,feedback);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,count);glEndTransformFeedback();void *bytes=malloc(count*28);glGetBufferSubData(GL_TRANSFORM_FEEDBACK_BUFFER,0,count*28,bytes);char file[4096];snprintf(file,sizeof file,"%s/%d.bin",argv[2],i);FILE *out=fopen(file,"wb");if(!out)return 11;fwrite(bytes,28,count,out);fclose(out);free(bytes);}
 int error=glGetError();free(pack);glXMakeCurrent(d,None,0);glXDestroyContext(d,c);XDestroyWindow(d,w);XFree(v);XCloseDisplay(d);return error?12:0;}
'''
def main():
    executable=pathlib.Path(sys.argv[1]).resolve();library=pathlib.Path(sys.argv[2]).resolve();legacy='--legacy' in sys.argv
    shader=helper.compose(ROOT/'shaders/mesh.vert');assert helper.embedded(executable,'mesh_vertex_source')==shader
    world=C.CDLL(str(library));world.sim_init.argtypes=[C.c_uint,C.c_uint];world.sim_init(8192,42);world.sim_checksum.restype=C.c_uint64
    world.terrain_height.argtypes=[C.c_float,C.c_float];world.terrain_height.restype=C.c_float
    before=world.sim_checksum()
    if not legacy:world.ground_support.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_float,C.c_float,C.c_float];world.ground_support.restype=C.c_int
    if not legacy:world.ground_contact.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*5;world.ground_contact.restype=C.c_int
    pack=(ROOT/'content/models/battle.rham').read_bytes();header=struct.unpack_from('<4s8I',pack);mo,vo=header[6],header[8];cases=[];queries=[]
    for index in range(header[4]):
        role,lod,count,frames,base,*_=struct.unpack_from('<8I',pack,mo+index*64)
        if role not in (1,2):continue
        scale=struct.unpack_from('<f',pack,mo+index*64+32)[0]
        for frame in (0,frames-1):
            for label,x,z,yaw in (('shallow',1000.,1000.,0.),('gentle_forward',5750.,5200.,math.pi/2),('gentle_cross',5750.,5200.,0.),('crest',5620.,5200.,math.pi/2),('combined',5700.,5475.,.65),('plateau',5550.,5200.,1.2)):
                yaw=C.c_float(yaw).value;sy,cy=math.sin(yaw),math.cos(yaw)
                if legacy:
                    y,pitch,bank,absolute=0.,0.,0.,0.;axes=((cy,0,-sy),(0,1,0),(sy,0,cy));height=world.terrain_height(x,z)
                else:
                    output=(C.c_float*16)();assert world.ground_support(output,role,64,x,z,yaw)==0
                    y,pitch,bank=output[:3];absolute=1.;height=y;axes=(tuple(output[4:7]),tuple(output[8:11]),tuple(output[12:15]))
                cases.append((label,role,lod,frame,count,base,scale,x,z,height,axes));queries.append((index,frame,x,y,z,yaw,pitch,bank,absolute))
                if not legacy:
                    for fraction in (.25,.5,.75):
                        contact=(C.c_float*16)();assert world.ground_contact(contact,role,64,x,z,yaw,pitch*fraction,bank*fraction)==0
                        yy,pp,bb=contact[:3];aa=(tuple(contact[4:7]),tuple(contact[8:11]),tuple(contact[12:15]))
                        cases.append((label+'-intermediate-'+str(fraction),role,lod,frame,count,base,scale,x,z,yy,aa));queries.append((index,frame,x,yy,z,yaw,pp,bb,1.))
    read,write=os.pipe();server=None
    try:
        with tempfile.TemporaryDirectory(prefix='rh-support-gl-') as tmp:
            folder=pathlib.Path(tmp)
            with (folder/'xvfb.log').open('wb') as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','64x64x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
            os.close(write);write=-1;number=read_display_number(read,10);assert number.isdigit();os.close(read);read=-1
            env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
            (folder/'driver.c').write_text(DRIVER);nasm=os.environ.get('RED_HORIZON_NASM',str(ROOT/'.tools/nasm/nasm'))
            subprocess.run([nasm,'-f','elf64','src/render/mesh_shaders.asm','-o',str(folder/'shader.o')],cwd=ROOT,check=True,capture_output=True)
            subprocess.run(['cc','-O2',str(folder/'driver.c'),str(folder/'shader.o'),'-lGL','-lX11','-o',str(folder/'driver')],check=True,capture_output=True)
            payload=str(len(queries))+'\n'+''.join(' '.join(map(str,q))+'\n' for q in queries)
            run=subprocess.run([str(folder/'driver'),str(ROOT/'content/models/battle.rham'),str(folder)],input=payload,text=True,capture_output=True,env=env,timeout=45);assert run.returncode==0,(run.returncode,run.stderr)
            rows=[];faults=0;total=0
            light=(.35,.85,-.2);ln=math.sqrt(sum(v*v for v in light));light=tuple(v/ln for v in light)
            for i,(label,role,lod,frame,count,base,scale,x,z,height,axes) in enumerate(cases):
                outputs=list(struct.iter_unpack('<7f',(folder/f'{i}.bin').read_bytes()));assert len(outputs)==count;minimum=1e9;position_error=colour_error=0.
                for j,out in enumerate(outputs):
                    offset=vo+(base+frame*count*3+j*3)*16;local=struct.unpack_from('<3f',pack,offset);normal=struct.unpack_from('<3f',pack,offset+16);material=struct.unpack_from('<3f',pack,offset+32)
                    expected=tuple((x,height,z)[a]+sum(local[k]*scale*axes[k][a] for k in range(3)) for a in range(3));actual=(out[0],out[1],out[3]);position_error=max(position_error,max(abs(a-b) for a,b in zip(actual,expected)))
                    nn=math.sqrt(sum(v*v for v in normal));normal=tuple(v/nn for v in normal);normal=tuple(sum(normal[k]*axes[k][a] for k in range(3)) for a in range(3));illum=.35+.65*max(0.,sum(a*b for a,b in zip(normal,light)));colour=tuple((material[k]*.78+(.16,.55,.85)[k]*.22)*illum for k in range(3));colour_error=max(colour_error,max(abs(a-b) for a,b in zip(out[4:],colour)))
                    minimum=min(minimum,actual[1]-world.terrain_height(actual[0],actual[2]))
                assert position_error<.002 and colour_error<.0001,(label,role,lod,position_error,colour_error)
                if label in ('gentle_forward','gentle_cross','crest','combined') and minimum<-.027:faults+=1
                if not legacy:assert minimum>=-.027,(label,role,lod,frame,minimum)
                rows.append({'fixture':label,'role':role,'lod':lod,'frame':frame,'vertices':count,'minimum_ground_gap':minimum,'position_max_error':position_error,'lighting_max_error':colour_error});total+=count
            assert not legacy or faults>=8,('upright negative failed to expose missing support',faults)
            assert world.sim_checksum()==before,'terrain support/GL query changed authority'
            print(json.dumps({'suite':'ground-support-actual-gl','passed':True,'legacy':legacy,'shader_sha256':hashlib.sha256(shader).hexdigest(),'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'vertices':total,'cases':rows,'detected_upright_faults':faults,'authority_unchanged':True,'software_context':run.stderr.strip(),'scope':'Actual embedded shader/source geometry/frame inputs and transformed normals, includes contact-corrected intermediate angles; not actual instance-hook or natural physical suspension acceptance'}))
    finally:
        if read>=0:os.close(read)
        if write>=0:os.close(write)
        if server is not None:server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
