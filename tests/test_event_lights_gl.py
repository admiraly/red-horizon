#!/usr/bin/env python3
"""Actual embedded production fragments + NASM DSA upload; declared surface fixture.
Private GL4.5 context, RGBA32F/integer readback. Development only, no game runtime.
"""
import ctypes as C, hashlib, importlib.util, json, os, pathlib, select, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief',ROOT/'tests/test_relief_gl.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
VERTEX='''#version 450 core
out vec3 colour;out float distanceFog;out vec3 surfaceAlbedo;out vec3 surfaceNormal;out vec3 surfacePosition;flat out vec2 surfaceResponse;flat out uint actorCode;
out float effectAlpha;out vec2 effectUV;flat out int effectType;out vec3 worldPosition;flat out int materialMode;
uniform int fixtureMode;uniform float fixtureNormal;
void main(){vec2 q=vec2((gl_VertexID<<1)&2,gl_VertexID&2)*2.-1.;gl_Position=vec4(q,0,1);worldPosition=vec3(2000.+q.x*4.,100.,2000.+q.y*4.);surfacePosition=worldPosition;surfaceNormal=vec3(0,fixtureNormal,0);surfaceAlbedo=vec3(.3,.35,.4);colour=surfaceAlbedo;surfaceResponse=vec2(0,20);actorCode=65544u;distanceFog=0.;effectAlpha=1.;effectUV=vec2(0);effectType=0;materialMode=fixtureMode;}
'''
def main():
 exe=pathlib.Path(sys.argv[1]).resolve();hardware='--hardware'in sys.argv
 sources={name:h.embedded(exe,name)for name in ('mesh_fragment_source','battle_fragment_source','mesh_vertex_source','battle_vertex_source')}
 assert sources['mesh_fragment_source']==(ROOT/'shaders/mesh.frag').read_bytes()
 assert sources['mesh_vertex_source']==h.compose(ROOT/'shaders/mesh.vert')
 battle=(ROOT/'shaders/battle.frag').read_bytes()
 assert sources['battle_fragment_source']==battle[:18]+(ROOT/'shaders/terrain_roads.glsl').read_bytes()+battle[18:]
 read,write=os.pipe();server=fw=win=None
 try:
  with tempfile.TemporaryDirectory(prefix='rh-event-light-gl-')as tmp:
   folder=pathlib.Path(tmp)
   if hardware:assert os.environ.get('DISPLAY');os.environ.pop('LIBGL_ALWAYS_SOFTWARE',None)
   else:
    with(folder/'xvfb.log').open('wb')as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','64x64x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
    os.close(write);write=-1;assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
    os.environ['DISPLAY']=':'+number;os.environ['LIBGL_ALWAYS_SOFTWARE']='1'
   # Only effect storage is a declared fixture; tested lighting code is production.
   (folder/'records.asm').write_text('section .bss\nglobal effects_records\neffects_records: resb 2048\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
   objects=[]
   for i,source in enumerate((ROOT/'src/render/event_lights.asm',ROOT/'tests/probe_event_lights.asm',folder/'records.asm')):
    obj=folder/f'{i}.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(str(obj))
   subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(folder/'lights.so'),*objects,'-lGL'],check=True,capture_output=True)
   l=C.CDLL(str(folder/'lights.so'));l.event_lights_update.argtypes=[C.c_float]*3;l.event_lights_apply.argtypes=[C.c_uint]
   gl=C.CDLL('libGL.so.1');fw=C.CDLL('libglfw.so.3');U,I,F,P=C.c_uint,C.c_int,C.c_float,C.c_void_p
   def bind(name,args,result=None):f=getattr(gl,name);f.argtypes=args;f.restype=result;return f
   fw.glfwCreateWindow.argtypes=[I,I,C.c_char_p,P,P];fw.glfwCreateWindow.restype=P;fw.glfwMakeContextCurrent.argtypes=[P];fw.glfwDestroyWindow.argtypes=[P]
   assert fw.glfwInit()==1
   for a,b in ((0x22002,4),(0x22003,5),(0x22008,0x32001),(0x20004,0)):fw.glfwWindowHint(a,b)
   win=fw.glfwCreateWindow(64,64,b'event lighting private proof',None,None);assert win;fw.glfwMakeContextCurrent(win)
   getString=bind('glGetString',[U],C.c_char_p);renderer=getString(0x1f01).decode();context=renderer+' / '+getString(0x1f02).decode()
   if hardware:assert not any(x in renderer.lower()for x in ('llvmpipe','softpipe','swrast','swiftshader'))
   create=bind('glCreateShader',[U],U);source=bind('glShaderSource',[U,I,C.POINTER(C.c_char_p),P]);compile_=bind('glCompileShader',[U]);getShader=bind('glGetShaderiv',[U,U,C.POINTER(I)]);shaderLog=bind('glGetShaderInfoLog',[U,I,P,P])
   def stage(kind,text):
    shader=create(kind);s=C.c_char_p(text if isinstance(text,bytes)else text.encode());source(shader,1,C.byref(s),None);compile_(shader);ok=I();getShader(shader,0x8b81,C.byref(ok))
    log=C.create_string_buffer(16000);shaderLog(shader,16000,None,log);assert ok.value,log.value;return shader
   # Also compile actual production vertex sources, including new weapon transform.
   for name in ('mesh_vertex_source','battle_vertex_source'):stage(0x8b31,sources[name])
   createProgram=bind('glCreateProgram',[],U);attach=bind('glAttachShader',[U,U]);link=bind('glLinkProgram',[U]);getProgram=bind('glGetProgramiv',[U,U,C.POINTER(I)]);programLog=bind('glGetProgramInfoLog',[U,I,P,P]);use=bind('glUseProgram',[U]);location=bind('glGetUniformLocation',[U,C.c_char_p],I)
   def program(fragment):
    p=createProgram();attach(p,stage(0x8b31,VERTEX));attach(p,stage(0x8b30,fragment));link(p);ok=I();getProgram(p,0x8b82,C.byref(ok));log=C.create_string_buffer(16000);programLog(p,16000,None,log);assert ok.value,log.value;return p
   programs={name:program(sources[name+'_fragment_source'])for name in ('mesh','battle')}
   def generate(name):v=U();bind(name,[I,C.POINTER(U)])(1,C.byref(v));return v.value
   vao=generate('glGenVertexArrays');bind('glBindVertexArray',[U])(vao)
   fbo=generate('glGenFramebuffers');bind('glBindFramebuffer',[U,U])(0x8d40,fbo)
   bindTexture=bind('glBindTexture',[U,U]);image=bind('glTexImage2D',[U,I,I,I,I,I,U,U,P]);attachTex=bind('glFramebufferTexture2D',[U,U,U,U,I])
   for attachment,internal,fmt,typ in ((0x8ce0,0x8814,0x1908,0x1406),(0x8ce1,0x8236,0x8d94,0x1405)):
    tex=generate('glGenTextures');bindTexture(0xde1,tex);image(0xde1,0,internal,64,64,0,fmt,typ,None);attachTex(0x8d40,attachment,0xde1,tex,0)
   bind('glDrawBuffers',[I,C.POINTER(U)])(2,(U*2)(0x8ce0,0x8ce1));assert bind('glCheckFramebufferStatus',[U],U)(0x8d40)==0x8cd5
   # Solid texture-array albedo, declared fixture for production terrain material.
   tex=generate('glGenTextures');bindTexture(0x8c1a,tex);data=(F*12)(*([.3,.35,.4]*4));bind('glTexImage3D',[U,I,I,I,I,I,I,U,U,P])(0x8c1a,0,0x8814,1,1,4,0,0x1907,0x1406,data)
   parameter=bind('glTexParameteri',[U,U,I]);parameter(0x8c1a,0x2801,0x2600);parameter(0x8c1a,0x2800,0x2600)
   bind('glViewport',[I,I,I,I])(0,0,64,64)
   uniformI=bind('glUniform1i',[I,I]);uniformF=bind('glUniform1f',[I,F]);uniform3=bind('glUniform3f',[I,F,F,F]);uniform4=bind('glUniform4f',[I,F,F,F,F]);draw=bind('glDrawArrays',[U,I,I]);readPixels=bind('glReadPixels',[I,I,I,I,U,U,P]);readBuffer=bind('glReadBuffer',[U]);getState=bind('glGetIntegerv',[U,C.POINTER(I)]);getError=bind('glGetError',[],U)
   def state(key):v=I();getState(key,C.byref(v));return v.value
   class Record(C.Structure):_fields_=[(n,F)for n in('x','y','z','ttl','radius')]+[('seed',U),('reserved',U),('kind',U)]
   records=(Record*64).in_dll(l,'effects_records');enabled=U.in_dll(l,'event_lights_enabled');gain=F.in_dll(l,'event_lights_gain');draws=0
   def sample(name,mode=0,hdr=1,normal=1,on=1,x=2000,ttl=.45,gain_value=1):
    nonlocal draws
    C.memset(C.addressof(records),0,C.sizeof(records));records[0]=Record(x,101,2000,ttl,2,1,0,2);enabled.value=on;gain.value=gain_value;assert l.event_lights_update(2000,100,2000)==0
    p=programs[name];use(p)
    for key,value in (('meshMode',mode),('fixtureMode',mode),('hdrOutput',hdr),('terrainTextures',0)):uniformI(location(p,key.encode()),value)
    uniformF(location(p,b'fixtureNormal'),normal);uniform3(location(p,b'camera'),2000,110,2000);uniform4(location(p,b'weather'),0,0,0,0)
    # Updating a different program preserves program, framebuffer, VAO, active texture.
    before=tuple(state(k)for k in (0x8b8d,0x8ca6,0x85b5,0x84e0,0x8069,0x8c1d))
    l.event_lights_apply(programs['battle'if name=='mesh'else'mesh']);assert before==tuple(state(k)for k in(0x8b8d,0x8ca6,0x85b5,0x84e0,0x8069,0x8c1d))
    l.event_lights_apply(p);assert before==tuple(state(k)for k in(0x8b8d,0x8ca6,0x85b5,0x84e0,0x8069,0x8c1d))
    draw(4,0,3);draws+=1;rgba=(F*4)();actor=U();readBuffer(0x8ce0);readPixels(32,32,1,1,0x1908,0x1406,rgba);readBuffer(0x8ce1);readPixels(32,32,1,1,0x8d94,0x1405,C.byref(actor));assert getError()==0 and rgba[3]==1
    assert actor.value==(65544 if name=='mesh'else 0);return tuple(rgba)[:3]
   observations=(C.c_uint64*6)();l.probe_event_lights_apply.argtypes=[U,P]
   assert l.probe_event_lights_apply(programs['mesh'],observations)!=-99
   assert list(observations)==list(range(0x123401,0x123407))
   delta=lambda a,b:max(abs(x-y)for x,y in zip(a,b))
   outcomes={}
   for name,mode in (('mesh',0),('mesh',2),('battle',1)):
    off=sample(name,mode,on=0);on=sample(name,mode);half=sample(name,mode,ttl=.225);far=sample(name,mode,x=2050);zero=sample(name,mode,gain_value=0);expired=sample(name,mode,ttl=0)
    change=delta(on,off);assert change>.08,(name,mode,off,on)
    assert abs(delta(half,off)/change-.25)<.0001,(name,mode,half)
    assert delta(far,off)<1e-6 and delta(zero,off)<1e-6 and delta(expired,off)<1e-6
    assert delta(sample(name,mode,hdr=0),sample(name,mode,hdr=0,on=0))<1e-6,'legacy/tactical path changed'
    outcomes[f'{name}-{mode}']={'near_delta':change,'half_life_ratio':delta(half,off)/change,'far_delta':delta(far,off)}
   assert delta(sample('mesh',normal=-1),sample('mesh',normal=-1,on=0))<1e-6,'back face receives light'
   assert delta(sample('mesh',mode=1),sample('mesh',mode=1,on=0))<1e-6,'map marker illuminated'
   assert delta(sample('battle',mode=9),sample('battle',mode=9,on=0))<1e-6,'sky illuminated'
   # Paired actual production mesh vertex+fragment draws (including weapon mode2).
   spec=importlib.util.spec_from_file_location('material',ROOT/'tests/test_mesh_material_gl.py');material=importlib.util.module_from_spec(spec);spec.loader.exec_module(material)
   driver=material.DRIVER.replace('program(oldFragment)','program(mesh_fragment_source)')
   driver=driver.replace('glUseProgram(p);glUniform1i', 'glUseProgram(p);glUniform1i(glGetUniformLocation(p,"hdrOutput"),1);glUniform1i(glGetUniformLocation(p,"eventLightCount"),j);glUniform4f(glGetUniformLocation(p,"eventLightPositions[0]"),4067.1875f,106,4067.1875f,72);glUniform4f(glGetUniformLocation(p,"eventLightColours[0]"),8,1.4,.08,0);glUniform2f(glGetUniformLocation(p,"angle"),.7,.3);glUniform1i')
   (folder/'actual.c').write_text(driver)
   subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','src/render/mesh_shaders.asm','-o',str(folder/'mesh.o')],cwd=ROOT,check=True,capture_output=True)
   subprocess.run(['cc','-O2',str(folder/'actual.c'),str(folder/'mesh.o'),'-lGL','-lX11','-lm','-o',str(folder/'actual')],check=True,capture_output=True)
   cases=[(0,1,0,0,0,0,0,0,3,0,mode,0,0,0)for mode in (0,1,2)]
   payload=str(len(cases))+'\n'+''.join(' '.join(map(str,row))+'\n'for row in cases)
   run=subprocess.run([str(folder/'actual')],input=payload,text=True,capture_output=True,timeout=45);assert run.returncode==0,(run.returncode,run.stderr)
   rows=[tuple(map(float,line.split()))for line in run.stdout.splitlines()];assert len(rows)==3
   actual_deltas=[delta(row[:3],row[5:8])for row in rows]
   assert actual_deltas[0]>.08 and actual_deltas[1]==0 and actual_deltas[2]>.08,actual_deltas
   assert all(row[4]==row[9]==(0 if mode==2 else 65544)for mode,row in enumerate(rows))
   print(json.dumps(dict(suite='event-lights-production-gl',passed=True,context=context,hardware=hardware,draws=draws+6,outcomes=outcomes,actual_mesh_marker_weapon_deltas=actual_deltas,actual_weapon_camera_angle=[.7,.3],source_sha256={k:hashlib.sha256(v).hexdigest()for k,v in sources.items()},production_nasm_upload=True,bindings_and_integer_ids_preserved=True,register_stack_abi=True,scope='Production embedded fragments and NASM upload; synthetic surface positions/albedo/terrain texture fixture. Additional paired actual production mesh vertex/fragment draws cover models, map markers and rotated-camera weapon. No shadows/occlusion/artistic/full-frame performance acceptance.')))
 finally:
  if win:fw.glfwMakeContextCurrent(None);fw.glfwDestroyWindow(win)
  if fw:fw.glfwTerminate()
  if read>=0:os.close(read)
  if write>=0:os.close(write)
  if server:server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
