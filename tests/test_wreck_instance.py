#!/usr/bin/env python3
"""Prepared NASM immutable wreck-instance packing and actual shader vertices."""
import ctypes as C,hashlib,importlib.util,json,math,os,pathlib,random,select,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
spec=importlib.util.spec_from_file_location('glprobe',ROOT/'tests/test_support_gl.py');gl=importlib.util.module_from_spec(spec);spec.loader.exec_module(gl)
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
def record():return W(5481,70,4999,.7,.1,-.2,1,0,12,1,0,1800,1,1,0,0)
with tempfile.TemporaryDirectory(prefix='rh-wreck-instance-') as name:
 td=pathlib.Path(name);objects=[]
 for i,src in enumerate(('src/render/wreck_instance.asm','tests/probe_wreck_instance.asm')):
  obj=td/f'{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/src),'-o',str(obj)],check=True);objects.append(str(obj))
 so=td/'instance.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_wreck_instance.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p]
 calls=0;poses=[];rng=random.Random(755289)
 def observe(w,output=None,source=None,cap=64,sourcecap=64,expected=0,nullout=False,nullsource=False):
  global calls
  out=output if output is not None else C.create_string_buffer(b'Z'*64,64);src=source if source is not None else C.byref(w);before=C.string_at(out,64);original=bytes(w);regs=C.create_string_buffer(56)
  rc=lib.probe_wreck_instance(None if nullout else out,cap,None if nullsource else src,sourcecap,regs);assert rc==expected,(rc,expected)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6))
  if rc==0:
   wanted=struct.pack('<16f',w.x,w.y,w.z,w.heading,0,0,0,w.pitch,1,1,1,w.bank,-1,3,w.kind,1)
   assert C.string_at(out,64)==wanted
  else:assert C.string_at(out,64)==before
  if source is None:assert bytes(w)==original
  calls+=1;return C.string_at(out,64)
 for i in range(1024):
  w=record();w.kind=1+i%2;w.side=i%2;w.x=rng.uniform(0,8000);w.z=rng.uniform(0,8000);w.heading=rng.uniform(-math.pi,math.pi);w.pitch=rng.uniform(-.8,.8);w.bank=rng.uniform(-.8,.8);w.flags=1 if i%2 else 3
  poses.append((w,observe(w)))
 for offset in range(-63,64):
  w=record();buffer=C.create_string_buffer(192);source=C.addressof(buffer)+64;C.memmove(source,C.byref(w),64);observe(w,output=source+offset,source=source)
 for field,value in [('x',-1),('z',8001),('y',math.nan),('heading',math.inf),('pitch',17),('bank',math.nan),('kind',0),('side',2),('entity',32768),('generation',0),('sequence',0),('flags',5),('reserved0',1)]:
  w=record();setattr(w,field,value);observe(w,expected=-1)
 for cap in (0,63):observe(record(),cap=cap,expected=-1);observe(record(),sourcecap=cap,expected=-1)
 observe(record(),nullout=True,expected=-1);observe(record(),nullsource=True,expected=-1)
 for flag in (0,2):w=record();w.flags=flag;observe(w,expected=-2)
 for field in ('x','z'):w=record();setattr(w,field,-0.);observe(w)
 # Actual assembly controls reject lost pitch, live animation and army identity.
 negatives=[];candidate_calls=calls;source=(ROOT/'src/render/wreck_instance.asm').read_text();candidate_lib=lib
 for tag,text in [('lost_pitch',source.replace(' mov eax,[rsp+WRECK_PITCH]',' xor eax,eax')),('live_frame',source.replace(' mov qword [rdi+16],0',' mov qword [rdi+16],0x3f800000')),('army_identity',source.replace(' mov dword [rdi+48],__float32__(-1.0)',' mov dword [rdi+48],__float32__(12.0)'))]:
  asm=td/(tag+'.asm');asm.write_text(text);obj=td/(tag+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True);dest=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(obj),objects[1],'-o',str(dest)],check=True)
  lib=C.CDLL(str(dest));lib.probe_wreck_instance.argtypes=candidate_lib.probe_wreck_instance.argtypes
  try:observe(record())
  except AssertionError:negatives.append(tag)
  else:raise AssertionError('assembly negative escaped '+tag)
 lib=candidate_lib
 # Use actual prepared64-byte instances as vertex attributes in the retained shader.
 shader=ROOT/'src/render/mesh_shaders.asm';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(shader),'-o',str(td/'shader.o')],cwd=ROOT,check=True)
 driver=gl.DRIVER.replace('const char *names[]={"gl_Position","colour"};glTransformFeedbackVaryings(p,2,names','const char *names[]={"gl_Position","colour","actorCode"};glTransformFeedbackVaryings(p,3,names').replace('count*28','count*32').replace('fwrite(bytes,28,count,out)','fwrite(bytes,32,count,out)')
 a=driver.index('int descriptor,frame;float x,y,z,yaw,pitch,bank,absolute;');b=driver.index('unsigned int *m=',a)
 driver=driver[:a]+'''int descriptor;float instance[16];if(scanf("%d",&descriptor)!=1)return 10;for(int k=0;k<16;k++)if(scanf("%f",&instance[k])!=1)return 10;'''+driver[b:]
 a=driver.index('glVertexAttrib4f(0,x,y,z,yaw);');b=driver.index('glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER',a)
 driver=driver[:a]+'''for(int k=0;k<4;k++)glVertexAttrib4fv(k,instance+k*4);'''+driver[b:]
 # Enable actual census output: negative ID/scenery excludes these dead records.
 driver=driver.replace('glEnable(GL_RASTERIZER_DISCARD);','glUniform1i(glGetUniformLocation(p,"censusDetail"),1);glEnable(GL_RASTERIZER_DISCARD);')
 (td/'driver.c').write_text(driver);subprocess.run(['cc','-O2',str(td/'driver.c'),str(td/'shader.o'),'-lGL','-lX11','-o',str(td/'driver')],check=True)
 pack=(ROOT/'content/models/battle.rham').read_bytes();h=struct.unpack_from('<12I',pack);descriptors={}
 for i in range(h[3]):
  d=struct.unpack_from('<8I5f3I',pack,h[6]+i*64)
  if d[0] in (1,2) and d[1]==0:descriptors[d[0]]=(i,d)
 cases=[(w,data,descriptors[w.kind]) for w,data in poses[:32]]
 read,write=os.pipe();server=None
 try:
  server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','64x64x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(write);write=-1;assert select.select([read],[],[],10)[0];display=os.read(read,32).decode().strip();os.close(read);read=-1
  env=dict(os.environ,DISPLAY=':'+display,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
  payload=str(len(cases))+'\n'+''.join(str(desc[0])+' '+' '.join(map(str,struct.unpack('<16f',data)))+'\n' for w,data,desc in cases)
  run=subprocess.run([str(td/'driver'),str(ROOT/'content/models/battle.rham'),str(td)],input=payload,text=True,capture_output=True,env=env,timeout=45);assert run.returncode==0,(run.returncode,run.stderr)
  vertices=0;maximum=0.
  for index,(w,data,(descriptor,d)) in enumerate(cases):
   sh,ch=math.sin(w.heading),math.cos(w.heading);sp,cp=math.sin(w.pitch),math.cos(w.pitch);sb,cb=math.sin(w.bank),math.cos(w.bank)
   outputs=list(struct.iter_unpack('<7fI',(td/f'{index}.bin').read_bytes()));assert len(outputs)==d[2]
   for j,out in enumerate(outputs):
    x,y,z=struct.unpack_from('<3f',pack,h[8]+d[4]*16+j*48);x,y,z=x*d[8],y*d[8],z*d[8];x,y=cb*x-sb*y,sb*x+cb*y;y,z=cp*y+sp*z,-sp*y+cp*z;x,z=ch*x+sh*z,-sh*x+ch*z
    expected=(x+w.x,y+w.y,z+w.z);actual=(out[0],out[1],out[3]);error=max(abs(a-b) for a,b in zip(expected,actual));maximum=max(maximum,error);assert error<.002,(index,error);assert out[7]==0,'wreck counted as a living actor';vertices+=1
  print(json.dumps({'suite':'prepared-wreck-instance','passed':True,'cpu_calls':candidate_calls,'negative_controls':negatives,'overlapping_alias_cases':127,'actual_gl_cases':len(cases),'actual_gl_vertices':vertices,'maximum_world_vertex_error':maximum,'excluded_from_living_census':True,'software_context':run.stderr.strip(),'source_sha256':hashlib.sha256((ROOT/'src/render/wreck_instance.asm').read_bytes()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Prepared isolated immutable instance packing/actual existing shader geometry only; no client draw hooks, descriptor selection, visible wreck cover or UDP integration.'}))
 finally:
  if read>=0:os.close(read)
  if write>=0:os.close(write)
  if server is not None:server.terminate();server.wait(timeout=5)
