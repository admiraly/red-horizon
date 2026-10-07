#!/usr/bin/env python3
"""Development-only GL4.5 core proof of assembled HDR target/present/census.
Uses production fragment sources embedded in the actual linked client; artificial
input radiance and fullscreen fragment fixtures are declared, not gameplay.
"""
import ctypes as C, hashlib, importlib.util, json, math, os, pathlib, select, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief_gl',ROOT/'tests/test_relief_gl.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def main():
 exe=pathlib.Path(sys.argv[1]).resolve();hardware='--hardware' in sys.argv
 for name,file in [('hdr_vertex_source','present.vert'),('hdr_fragment_source','present.frag')]:assert helper.embedded(exe,name)==(ROOT/'shaders'/file).read_bytes()
 read,write=os.pipe();server=None;fw=None;win=None
 try:
  with tempfile.TemporaryDirectory(prefix='rh-hdr-gl-') as temp:
   folder=pathlib.Path(temp)
   if hardware:
    assert os.environ.get('DISPLAY'),'Native hidden-context check requires DISPLAY'
    os.environ.pop('LIBGL_ALWAYS_SOFTWARE',None)
   else:
    with (folder/'xvfb.log').open('wb') as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x480x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
    os.close(write);write=-1;assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
    os.environ['DISPLAY']=':'+number;os.environ['LIBGL_ALWAYS_SOFTWARE']='1'
   nasm=os.environ['RED_HORIZON_NASM'];objects=[]
   for name,source in [('hdr','src/render/hdr.asm'),('census','src/render/visibility_census.asm'),('probe','tests/probe_visibility_reduce.asm')]:
    obj=folder/(name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],cwd=ROOT,check=True,capture_output=True);objects.append(str(obj))
   libpath=folder/'libhdr.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(libpath),*objects,'-lGL'],check=True,capture_output=True)
   lib=C.CDLL(str(libpath));gl=C.CDLL('libGL.so.1');fw=C.CDLL('libglfw.so.3')
   def bind(name,types,result=None):
    fun=getattr(gl,name);fun.argtypes=types;fun.restype=result;return fun
   U,I,F,P=C.c_uint,C.c_int,C.c_float,C.c_void_p
   fw.glfwCreateWindow.argtypes=[I,I,C.c_char_p,P,P];fw.glfwCreateWindow.restype=P;fw.glfwMakeContextCurrent.argtypes=[P];fw.glfwDestroyWindow.argtypes=[P]
   assert fw.glfwInit()==1
   for a,b in [(0x22002,4),(0x22003,5),(0x22008,0x32001),(0x20004,0)]:fw.glfwWindowHint(a,b)
   win=fw.glfwCreateWindow(320,240,b'HDR private core proof',None,None);assert win;fw.glfwMakeContextCurrent(win)
   getString=bind('glGetString',[U],C.c_char_p);renderer=getString(0x1f01).decode();context=renderer+' / '+getString(0x1f02).decode()
   if hardware:assert not any(name in renderer.lower() for name in ('llvmpipe','softpipe','swrast','swiftshader')),renderer
   clear=bind('glClearBufferfv',[U,I,C.POINTER(F)]);clearID=bind('glClearBufferuiv',[U,I,C.POINTER(U)])
   readPixels=bind('glReadPixels',[I,I,I,I,U,U,P]);readBuffer=bind('glReadBuffer',[U]);getError=bind('glGetError',[],U)
   getState=bind('glGetIntegerv',[U,C.POINTER(I)]);bindTexture=bind('glBindTexture',[U,U]);getLevel=bind('glGetTexLevelParameteriv',[U,I,U,C.POINTER(I)])
   bind('glViewport',[I,I,I,I])(0,0,320,240);disable=bind('glDisable',[U]);enable=bind('glEnable',[U]);use=bind('glUseProgram',[U])
   def state(key):v=I();getState(key,C.byref(v));return v.value
   def pixel():
    a=(F*4)();readPixels(160,120,1,1,0x1908,0x1406,a);return tuple(a)
   def integer(name):return U.in_dll(lib,name)
   enabled=integer('hdr_enabled');linear=integer('hdr_world_linear');count=integer('hdr_present_count')
   lib.hdr_begin.argtypes=[U];lib.hdr_present.argtypes=[U,U]
   lib.hdr_begin(0);lib.hdr_present(0,0);assert linear.value==count.value==0
   assert lib.hdr_init()==0;texture=integer('hdr_scene_texture').value;fbo=integer('hdr_scene_fbo').value
   assert texture and fbo and lib.hdr_init()==0 and integer('hdr_scene_texture').value==texture
   assert state(0x8ca6)==0
   bindTexture(0xde1,texture);fmt=I();getLevel(0xde1,0,0x1003,C.byref(fmt));assert fmt.value==0x881a
   def decode(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
   def encode(v):return 12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055
   def expected(rgb,exposure=1):
    rgb=[max(0,v)*exposure for v in rgb];lum=sum(v*w for v,w in zip(rgb,(.2126,.7152,.0722)))
    return tuple(encode(min(1,v*(1+lum/16)/(1+lum))) for v in rgb)
   radiance_cases=[(v,v,v) for v in (0,.001,.01,.05,.1,.5,1,2,3,4,8)]+[(4,2,.5),(16,.125,.25),(.13,.8,2)]
   maximum=0;display=[]
   for rgb in radiance_cases:
    lib.hdr_begin(0);assert linear.value==1 and state(0x8ca6)==fbo
    clear(0x1800,0,(F*4)(*rgb,1));stored=pixel();assert max(abs(a-b) for a,b in zip(stored[:3],rgb))<.001
    lib.hdr_present(0,0);assert linear.value==0 and integer('hdr_frame_presented').value==1 and state(0x8ca6)==0
    readBuffer(0x405);shown=pixel();error=max(abs(a-b) for a,b in zip(shown[:3],expected(rgb)));maximum=max(maximum,error);assert error<.0041,(rgb,shown,expected(rgb))
    display.append(shown[0]);assert getError()==0
   assert all(a<b for a,b in zip(display[:9],display[1:10])) and display[10]==1
   exposure=F.in_dll(lib,'hdr_exposure');exposure.value=.5;lib.hdr_begin(0);clear(0x1800,0,(F*4)(1,1,1,1));lib.hdr_present(0,0);assert max(abs(a-b) for a,b in zip(pixel()[:3],expected((1,1,1),.5)))<.0041;exposure.value=1
   lib.hdr_begin(1);assert linear.value==0;clear(0x1800,0,(F*4)(.17,.52,.81,1));lib.hdr_present(0,1);assert max(abs(a-b) for a,b in zip(pixel()[:3],(.17,.52,.81)))<.0041
   old=count.value;enabled.value=0;lib.hdr_begin(0);lib.hdr_present(0,0);assert state(0x8ca6)==0 and count.value==old and linear.value==0;enabled.value=1
   # Production battle fragment receives artificial fullscreen effect inputs.
   createShader=bind('glCreateShader',[U],U);shaderSource=bind('glShaderSource',[U,I,C.POINTER(C.c_char_p),C.POINTER(I)]);compileShader=bind('glCompileShader',[U]);getShader=bind('glGetShaderiv',[U,U,C.POINTER(I)])
   createProgram=bind('glCreateProgram',[],U);attach=bind('glAttachShader',[U,U]);link=bind('glLinkProgram',[U]);getProgram=bind('glGetProgramiv',[U,U,C.POINTER(I)])
   location=bind('glGetUniformLocation',[U,C.c_char_p],I);uniform=bind('glUniform1i',[I,I]);draw=bind('glDrawArrays',[U,I,I]);genVAO=bind('glGenVertexArrays',[I,C.POINTER(U)]);bindVAO=bind('glBindVertexArray',[U]);deleteVAO=bind('glDeleteVertexArrays',[I,C.POINTER(U)])
   vs=b'''#version 450 core
out vec3 colour;out float distanceFog;out float effectAlpha;out vec2 effectUV;flat out int effectType;out vec3 worldPosition;flat out int materialMode;uniform int fixtureKind;
void main(){const vec2 p[3]=vec2[3](vec2(-1,-1),vec2(3,-1),vec2(-1,3));gl_Position=vec4(p[gl_VertexID],0,1);colour=vec3(1.,.45,.08);distanceFog=500.;effectAlpha=.5;effectUV=vec2(0);effectType=fixtureKind;worldPosition=vec3(4000,100,4000);materialMode=7;}'''
   fs=helper.embedded(exe,'battle_fragment_source');program=createProgram();stages=[]
   for kind,source in [(0x8b31,vs),(0x8b30,fs)]:
    s=createShader(kind);stages.append(s);raw=C.c_char_p(source);shaderSource(s,1,C.byref(raw),None);compileShader(s);ok=I();getShader(s,0x8b81,C.byref(ok));assert ok.value==1,'production fragment compile failed';attach(program,s)
   link(program);ok=I();getProgram(program,0x8b82,C.byref(ok));assert ok.value==1
   vao=U();genVAO(1,C.byref(vao));emission=[]
   for kind,gain in [(2,8),(10,8),(1,3),(9,4),(3,None)]:
    for mode in (0,1):
     lib.hdr_begin(0);disable(0xb71);disable(0xbe2);use(program);bindVAO(vao.value);uniform(location(program,b'hdrOutput'),mode);uniform(location(program,b'fixtureKind'),kind);draw(4,0,3);rgba=pixel()
     if kind!=3:assert abs(rgba[3]-.5)<.001,(kind,rgba)
     else:assert .25<rgba[3]<.51,(kind,rgba,'smoke billow alpha')
     if gain is not None:
      target=tuple(decode(v)*gain if mode else v for v in (1,.45,.08));assert max(abs(a-b) for a,b in zip(rgba[:3],target))<.005,(kind,mode,rgba,target)
     else:assert max(rgba[:3])<=1.21,(kind,rgba)
     emission.append({'effect_kind':kind,'hdr_output':mode,'scene_rgba':rgba})
   # Two additive fire fragments remain sixteen in the scene rather than clipping.
   lib.hdr_begin(0);clear(0x1800,0,(F*4)(0,0,0,0));disable(0xb71);enable(0xbe2);bind('glBlendFunc',[U,U])(1,1);use(program);bindVAO(vao.value);uniform(location(program,b'hdrOutput'),1);uniform(location(program,b'fixtureKind'),10);draw(4,0,3);draw(4,0,3);summed=pixel();assert summed[0]==16 and summed[3]==1,summed
   lib.hdr_present(0,0);use(0);bind('glDeleteProgram',[U])(program)
   for stage in stages:bind('glDeleteShader',[U])(stage)
   deleteVAO(1,C.byref(vao));assert getError()==0
   # Census and tone mapping use the same floating scene, with independent IDs.
   entities=(U*(32768*8)).in_dll(lib,'sim_entities');entities[2]=100;entities[7]=1;assert lib.visibility_init()==0
   lib.hdr_begin(0);lib.visibility_begin_hdr();clear(0x1800,0,(F*4)(2,2,2,1));clearID(0x1800,1,(U*4)(0x10001,0,0,0));lib.visibility_world_end();clearID(0x1800,1,(U*4)(0,0,0,0))
   external=integer('visibility_colour_texture').value;lib.hdr_present(external,0);before=pixel();assert abs(before[0]-expected((2,2,2))[0])<.0041
   # Declared HUD-like display-space pixel write must survive later ID readback.
   clear(0x1800,0,(F*4)(.8,.2,.1,1));hud=pixel();assert lib.visibility_finish_hdr()==0 and pixel()==hud
   assert integer('visibility_actors').value==integer('visibility_high').value==1
   pixels=(U*(320*240)).in_dll(lib,'visibility_pixels');assert set(pixels)=={0x10001};assert state(0x8ca6)==0 and getError()==0
   lib.visibility_begin();clear(0x1800,0,(F*4)(.3,.4,.5,1));lib.visibility_world_end();assert lib.visibility_finish()==0;assert max(abs(a-b) for a,b in zip(pixel()[:3],(.3,.4,.5)))<.0041
   lib.visibility_shutdown();lib.hdr_shutdown();lib.hdr_shutdown();assert getError()==0
   assert not bind('glIsTexture',[U],C.c_ubyte)(texture) and not bind('glIsFramebuffer',[U],C.c_ubyte)(fbo)
   width=integer('view_width');height=integer('view_height')
   for bad in (0,319,3841,0xffffffff):width.value=bad;assert lib.hdr_init()==-1
   width.value=320
   for bad in (0,239,2161,0xffffffff):height.value=bad;assert lib.hdr_init()==-1
   height.value=240;assert lib.hdr_init()==0;lib.hdr_begin(0);lib.hdr_present(0,0);lib.hdr_shutdown();assert getError()==0
   print(json.dumps({'suite':'hdr-production-core-gl','passed':True,'context':context,'native_hidden_context':hardware,'scene_format':'RGBA16F','dimensions':[320,240],'radiance_cases':len(radiance_cases),'display_max_error':maximum,'emission_samples':emission,'additive_fire_scene_rgba':summed,'tactical_passthrough':True,'disabled_passthrough':True,'census_integer_ids_preserved':True,'census_readback_keeps_display_hud':True,'legacy_census_blit':True,'lifecycle_and_invalid_dimensions':True,'present_count':count.value,'client_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'fragment_sha256':hashlib.sha256(fs).hexdigest(),'scope':'Real GL4.5 core and assembled renderer, artificial radiance and production fragment inputs; isolated GL-only census stub. Native flag tests a hidden hardware context only, not army scene/GPU performance/art acceptance.'}))
 finally:
  if win:fw.glfwDestroyWindow(win)
  if fw:fw.glfwTerminate()
  if read>=0:os.close(read)
  if write>=0:os.close(write)
  if server:server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
