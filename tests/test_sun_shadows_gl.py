#!/usr/bin/env python3
"""Production NASM depth map and actual embedded caster/receiver shaders.
Synthetic source triangle and texture/albedo controls declared; not gameplay art.
"""
from xvfb_display import read_display_number
import ctypes as C,hashlib,importlib.util,json,math,os,pathlib,select,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relief',ROOT/'tests/test_relief_gl.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
spec=importlib.util.spec_from_file_location('lights',ROOT/'tests/test_event_lights_gl.py');lights=importlib.util.module_from_spec(spec);spec.loader.exec_module(lights)
def main():
 exe=pathlib.Path(sys.argv[1]).resolve();hardware='--hardware'in sys.argv
 sources={n:h.embedded(exe,n)for n in('mesh_vertex_source','mesh_fragment_source','battle_fragment_source')}
 assert sources['mesh_vertex_source']==h.compose(ROOT/'shaders/mesh.vert')
 assert sources['mesh_fragment_source']==(ROOT/'shaders/mesh.frag').read_bytes()
 battle=(ROOT/'shaders/battle.frag').read_bytes();assert sources['battle_fragment_source']==battle[:18]+(ROOT/'shaders/terrain_roads.glsl').read_bytes()+battle[18:]
 read,write=os.pipe();server=fw=win=None
 try:
  with tempfile.TemporaryDirectory(prefix='rh-sun-shadows-')as tmp:
   folder=pathlib.Path(tmp)
   if hardware:assert os.environ.get('DISPLAY');os.environ.pop('LIBGL_ALWAYS_SOFTWARE',None)
   else:
    with(folder/'xvfb.log').open('wb')as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','320x240x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
    os.close(write);write=-1;number=read_display_number(read,10);assert number.isdigit();os.close(read);read=-1
    os.environ['DISPLAY']=':'+number;os.environ['LIBGL_ALWAYS_SOFTWARE']='1'
   (folder/'host.asm').write_text('section .data\nglobal hdr_enabled\nhdr_enabled: dd 1\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
   objects=[]
   for i,source in enumerate((ROOT/'src/render/sun_shadows.asm',ROOT/'tests/probe_sun_shadows.asm',folder/'host.asm')):
    obj=folder/f'{i}.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(str(obj))
   subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(folder/'shadows.so'),*objects,'-lGL'],check=True,capture_output=True)
   l=C.CDLL(str(folder/'shadows.so'));l.sun_shadows_matrix.argtypes=[C.c_float]*3;l.sun_shadows_begin.argtypes=[C.c_uint]+[C.c_float]*3;l.sun_shadows_apply.argtypes=[C.c_uint]
   matrix=(C.c_float*16).in_dll(l,'sun_shadow_matrix');ready=C.c_uint.in_dll(l,'sun_shadow_ready');enabled=C.c_uint.in_dll(l,'sun_shadows_enabled');hdr=C.c_uint.in_dll(l,'hdr_enabled');pass_=C.c_uint.in_dll(l,'sun_shadow_pass');frames=C.c_uint.in_dll(l,'sun_shadow_frames')
   observations=(C.c_uint64*6)();l.probe_sun_shadows_matrix.argtypes=[C.c_void_p]+[C.c_float]*3
   assert l.probe_sun_shadows_matrix(observations,2000,100,2000)==0 and list(observations)==list(range(0x123401,0x123407))
   assert l.sun_shadows_matrix(2000,100,2000)==0 and matrix[15]==1
   def project(p):return [sum(matrix[col*4+row]*p[col]for col in range(3))+matrix[12+row]for row in range(3)]
   assert max(abs(v)for v in project((2000,100,2000)))<1e-6
   sun=[v/math.sqrt(.35**2+.85**2+.2**2)for v in(.35,.85,-.2)]
   toward=project(tuple(v+100*s for v,s in zip((2000,100,2000),sun)));assert abs(toward[0])+abs(toward[1])<1e-6 and abs(toward[2]+100/1024)<1e-6
   before=bytes(matrix)
   for camera in ((float('nan'),0,0),(0,float('inf'),0),(0,0,16001)):
    assert l.sun_shadows_matrix(*camera)==-1 and bytes(matrix)==before
   assert l.sun_shadows_matrix(2003,100,2003)==0 and bytes(matrix)==before,'unstable within snapped cell'
   gl=C.CDLL('libGL.so.1');fw=C.CDLL('libglfw.so.3');U,I,F,P=C.c_uint,C.c_int,C.c_float,C.c_void_p
   def bind(name,args,result=None):f=getattr(gl,name);f.argtypes=args;f.restype=result;return f
   fw.glfwCreateWindow.argtypes=[I,I,C.c_char_p,P,P];fw.glfwCreateWindow.restype=P;fw.glfwMakeContextCurrent.argtypes=[P];fw.glfwDestroyWindow.argtypes=[P]
   assert fw.glfwInit()==1
   for a,b in((0x22002,4),(0x22003,5),(0x22008,0x32001),(0x20004,0)):fw.glfwWindowHint(a,b)
   win=fw.glfwCreateWindow(320,240,b'directional shadows private proof',None,None);assert win;fw.glfwMakeContextCurrent(win)
   getString=bind('glGetString',[U],C.c_char_p);renderer=getString(0x1f01).decode();context=renderer+' / '+getString(0x1f02).decode()
   if hardware:assert not any(x in renderer.lower()for x in('llvmpipe','softpipe','swrast','swiftshader'))
   getState=bind('glGetIntegerv',[U,C.POINTER(I)]);getError=bind('glGetError',[],U);bindTexture=bind('glBindTexture',[U,U]);active=bind('glActiveTexture',[U]);viewport=bind('glViewport',[I,I,I,I]);enable=bind('glEnable',[U]);disable=bind('glDisable',[U]);bindFbo=bind('glBindFramebuffer',[U,U])
   def state(key):v=I();getState(key,C.byref(v));return v.value
   def rect():v=(I*4)();getState(0xba2,v);return tuple(v)
   def integer(name):return U.in_dll(l,name)
   def generate(name):v=U();bind(name,[I,C.POINTER(U)])(1,C.byref(v));return v.value
   viewport(0,0,320,240);active(0x84c3);assert l.sun_shadows_init()==0 and state(0x84e0)==0x84c3 and state(0x8ca6)==0
   texture=integer('sun_shadow_texture').value;fbo=integer('sun_shadow_fbo').value;assert texture and fbo and l.sun_shadows_init()==0 and integer('sun_shadow_texture').value==texture
   active(0x84ce);bindTexture(0xde1,texture);getLevel=bind('glGetTexLevelParameteriv',[U,I,U,C.POINTER(I)])
   values=[]
   for key in(0x1000,0x1001,0x1003):v=I();getLevel(0xde1,0,key,C.byref(v));values.append(v.value)
   assert values==[2048,2048,0x81a6],values
   create=bind('glCreateShader',[U],U);source=bind('glShaderSource',[U,I,C.POINTER(C.c_char_p),P]);compile_=bind('glCompileShader',[U]);getShader=bind('glGetShaderiv',[U,U,C.POINTER(I)]);shaderLog=bind('glGetShaderInfoLog',[U,I,P,P])
   def stage(kind,text):
    shader=create(kind);s=C.c_char_p(text if isinstance(text,bytes)else text.encode());source(shader,1,C.byref(s),None);compile_(shader);ok=I();getShader(shader,0x8b81,C.byref(ok));log=C.create_string_buffer(16000);shaderLog(shader,16000,None,log);assert ok.value,log.value;return shader
   createProgram=bind('glCreateProgram',[],U);attach=bind('glAttachShader',[U,U]);link=bind('glLinkProgram',[U]);getProgram=bind('glGetProgramiv',[U,U,C.POINTER(I)]);programLog=bind('glGetProgramInfoLog',[U,I,P,P]);use=bind('glUseProgram',[U]);location=bind('glGetUniformLocation',[U,C.c_char_p],I)
   def program(vertex,fragment):
    p=createProgram();attach(p,stage(0x8b31,vertex));attach(p,stage(0x8b30,fragment));link(p);ok=I();getProgram(p,0x8b82,C.byref(ok));log=C.create_string_buffer(16000);programLog(p,16000,None,log);assert ok.value,log.value;return p
   caster=program(sources['mesh_vertex_source'],'#version 450 core\nvoid main(){}')
   l.probe_sun_shadows_apply.argtypes=[U,P];assert l.probe_sun_shadows_apply(caster,observations)!=-99 and list(observations)==list(range(0x123401,0x123407))
   receivers={name:program(lights.VERTEX.replace('vec2(0,20)','vec2(.58,.09)'),sources[name+'_fragment_source'])for name in('mesh','battle')}
   vao=generate('glGenVertexArrays');bind('glBindVertexArray',[U])(vao)
   buffer=generate('glGenBuffers');bindBuffer=bind('glBindBuffer',[U,U]);bindBuffer(0x90d2,buffer);bind('glBindBufferBase',[U,U,U])(0x90d2,3,buffer)
   vertices=[]
   for x,z in((-8,-8),(8,-8),(0,8)):vertices.extend((x,0,z,0,0,1,0,0,.3,.35,.4,0))
   data=(F*len(vertices))(*vertices);bind('glBufferData',[U,C.c_ssize_t,P,U])(0x90d2,C.sizeof(data),data,0x88e4)
   target=generate('glGenFramebuffers');bindFbo(0x8d40,target);attachTex=bind('glFramebufferTexture2D',[U,U,U,U,I]);image=bind('glTexImage2D',[U,I,I,I,I,I,U,U,P])
   for attachment,internal,fmt,typ in((0x8ce0,0x8814,0x1908,0x1406),(0x8ce1,0x8236,0x8d94,0x1405)):
    tex=generate('glGenTextures');bindTexture(0xde1,tex);image(0xde1,0,internal,320,240,0,fmt,typ,None);attachTex(0x8d40,attachment,0xde1,tex,0)
   bind('glDrawBuffers',[I,C.POINTER(U)])(2,(U*2)(0x8ce0,0x8ce1));assert bind('glCheckFramebufferStatus',[U],U)(0x8d40)==0x8cd5
   active(0x84c0);tex=generate('glGenTextures');bindTexture(0x8c1a,tex);data=(F*12)(*([.3,.35,.4]*4));bind('glTexImage3D',[U,I,I,I,I,I,I,U,U,P])(0x8c1a,0,0x8814,1,1,4,0,0x1907,0x1406,data);parameter=bind('glTexParameteri',[U,U,I]);parameter(0x8c1a,0x2801,0x2600);parameter(0x8c1a,0x2800,0x2600)
   uniformI=bind('glUniform1i',[I,I]);uniformF=bind('glUniform1f',[I,F]);uniform2I=bind('glUniform2i',[I,I,I]);uniform3=bind('glUniform3f',[I,F,F,F]);uniform4=bind('glUniform4f',[I,F,F,F,F]);attrib=bind('glVertexAttrib4f',[U,F,F,F,F]);draw=bind('glDrawArrays',[U,I,I]);readPixels=bind('glReadPixels',[I,I,I,I,U,U,P]);readBuffer=bind('glReadBuffer',[U]);draws=0
   def make_map(x=2000,y=104):
    nonlocal draws
    enable(0xb71);bind('glDepthMask',[C.c_ubyte])(1);viewport(3,5,320,240);active(0x84c2);use(caster);bindFbo(0x8ca8,0)
    assert l.sun_shadows_begin(0,2000,100,2000)==1 and pass_.value==1 and ready.value==0 and rect()==(0,0,2048,2048)
    assert integer('sun_shadow_budget').value==1024 and integer('sun_shadow_casters').value==0
    l.sun_shadows_apply(caster);assert state(0x8b8d)==caster and state(0x84e0)==0x84c2 and state(0x85b5)==vao
    uniformI(location(caster,b'meshMode'),0);uniform2I(location(caster,b'meshGeometry'),0,3);uniformF(location(caster,b'meshScale'),1)
    attrib(0,x,y,2000,0);attrib(1,0,0,0,0);attrib(2,1,1,1,0);attrib(3,0,0,3,1);draw(4,0,3);draws+=1
    depth=F();readPixels(1024,1024,1,1,0x1902,0x1406,C.byref(depth));l.sun_shadows_end()
    assert ready.value==1 and pass_.value==0 and state(0x8ca6)==target and state(0x8caa)==0 and rect()==(3,5,320,240)
    return depth.value
   def sample(name,mode=0,hdr_output=1,on=True):
    nonlocal draws
    disable(0xb71);bindFbo(0x8d40,target);viewport(0,0,320,240);p=receivers[name];use(p);ready.value=int(on);l.sun_shadows_apply(p)
    for key,value in(('meshMode',mode),('fixtureMode',mode),('hdrOutput',hdr_output),('terrainTextures',0)):uniformI(location(p,key.encode()),value)
    uniformF(location(p,b'fixtureNormal'),1);uniform3(location(p,b'camera'),2000,110,2000);uniform4(location(p,b'weather'),0,0,0,0)
    draw(4,0,3);draws+=1;rgba=(F*4)();actor=U();readBuffer(0x8ce0);readPixels(160,120,1,1,0x1908,0x1406,rgba);readBuffer(0x8ce1);readPixels(160,120,1,1,0x8d94,0x1405,C.byref(actor));assert rgba[3]==1 and actor.value==(65544 if name=='mesh'else 0)and getError()==0;return tuple(rgba)[:3]
   delta=lambda a,b:max(abs(x-y)for x,y in zip(a,b))
   depth=make_map();assert depth<.5 and frames.value==1,depth
   results={}
   for name,mode in(('mesh',0),('battle',1)):
    lit=sample(name,mode,on=False);shadow=sample(name,mode);change=delta(lit,shadow);assert change>.025 and all(a>b for a,b in zip(lit,shadow)),(name,lit,shadow)
    assert delta(sample(name,mode,hdr_output=0),sample(name,mode,hdr_output=0,on=False))<1e-6
    results[name]={'lit':lit,'shadow':shadow,'delta':change}
   assert delta(sample('mesh',1),sample('mesh',1,on=False))<1e-6
   assert delta(sample('mesh',2),sample('mesh',2,on=False))<1e-6
   assert delta(sample('battle',9),sample('battle',9,on=False))<1e-6
   make_map(x=2050)
   for name,mode in(('mesh',0),('battle',1)):assert delta(sample(name,mode),results[name]['lit'])<1e-6,'moving caster leaves stale shadow'
   make_map(y=100)
   for name,mode in(('mesh',0),('battle',1)):assert delta(sample(name,mode),results[name]['lit'])<1e-4,'coplanar terrain self-shadows'
   make_map(y=96)
   for name,mode in(('mesh',0),('battle',1)):assert delta(sample(name,mode),results[name]['lit'])<1e-6,'geometry behind receiver casts toward light'
   for control in('tactical','disabled','HDR off','invalid'):
    enabled.value=0 if control=='disabled'else 1;hdr.value=0 if control=='HDR off'else 1
    before=(state(0x8ca6),rect(),frames.value);result=l.sun_shadows_begin(int(control=='tactical'),float('nan')if control=='invalid'else 2000,100,2000)
    assert result==(-1 if control=='invalid'else 0)and ready.value==pass_.value==0 and (state(0x8ca6),rect(),frames.value)==before
   enabled.value=hdr.value=1;old=texture;l.sun_shadows_shutdown();l.sun_shadows_shutdown();assert integer('sun_shadow_texture').value==integer('sun_shadow_fbo').value==0 and ready.value==pass_.value==0
   assert l.sun_shadows_init()==0;new=integer('sun_shadow_texture').value;assert new and l.sun_shadows_init()==0 and integer('sun_shadow_texture').value==new
   l.sun_shadows_shutdown();assert getError()==0
   print(json.dumps(dict(suite='sun-shadows-production-gl',passed=True,hardware=hardware,context=context,draws=draws,depth=depth,receivers=results,dimensions_format=values,matrix_snapping_invalid_inputs=True,moving_and_behind_caster_controls=True,coplanar_receiver_lit=True,separate_read_draw_framebuffers_preserved=True,HDR_map_marker_weapon_sky_bypass=True,lifecycle_and_bindings=True,integer_ids_preserved=True,register_stack_ABI=True,source_sha256={k:hashlib.sha256(v).hexdigest()for k,v in sources.items()},scope='Actual production NASM resource/frame/matrix/DSA and embedded mesh caster vertex + mesh/terrain receiver fragments. Declared synthetic source triangle/albedo/texture/surface positions. Whole-client casters, budget/authority/animation and artistic/performance acceptance separate.')))
 finally:
  if win:fw.glfwMakeContextCurrent(None);fw.glfwDestroyWindow(win)
  if fw:fw.glfwTerminate()
  if read>=0:os.close(read)
  if write>=0:os.close(write)
  if server:server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
