#!/usr/bin/env python3
"""Actual embedded GL shader: fixed legs, independently aimed authored upper body."""
import hashlib,json,math,os,pathlib,select,struct,subprocess,sys,tempfile
from test_support_gl import DRIVER,helper,ROOT
shader=helper.compose(ROOT/'shaders/mesh.vert');exe=pathlib.Path(sys.argv[1]).resolve();assert helper.embedded(exe,'mesh_vertex_source')==shader
# Same actual GL capture harness, using each descriptor's validated shoot clip.
driver=DRIVER.replace('glUniform2i(glGetUniformLocation(p,"meshGeometry"),m[4],count);','unsigned int co=head[6]; unsigned int start=0,length=0; for(unsigned int j=m[5];j<m[5]+m[6];j++){unsigned int *clip=(unsigned int *)(pack+co+j*16);if(clip[3]==3){start=clip[0];length=clip[1];break;}} glUniform2i(glGetUniformLocation(p,"meshAimClip"),start,length);glUniform2i(glGetUniformLocation(p,"meshGeometry"),m[4],count);')
pack=(ROOT/'content/models/battle.rham').read_bytes();h=struct.unpack_from('<12I',pack);mo,co,vo=h[6:9];queries=[];cases=[]
for index in range(h[3]):
 role,lod,n,frames,base,first,count=struct.unpack_from('<7I',pack,mo+index*64)
 if role!=0:continue
 shoot,length=next(struct.unpack_from('<2I',pack,co+c*16)for c in range(first,first+count)if struct.unpack_from('<I',pack,co+c*16+12)[0]==3)
 for frame in (0,27):
  for age in (0,3,7):
   control=len(queries);queries.append((index,frame,100.,30.,100.,.4,0.,0.,1))
   active=len(queries);queries.append((index,frame,100.,30.,100.,.4,.15,-1.2,13+(age<<4)))
   cases.append((control,active,lod,n,base,frame,shoot,length,age))
read,write=os.pipe();server=None
try:
 with tempfile.TemporaryDirectory(prefix='rh-aim-gl-')as directory:
  td=pathlib.Path(directory)
  with (td/'xvfb.log').open('wb')as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','64x64x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
  os.close(write);write=-1;assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1');env.pop('WAYLAND_DISPLAY',None)
  (td/'driver.c').write_text(driver);nasm=os.environ.get('RED_HORIZON_NASM',str(ROOT/'.tools/nasm/nasm'))
  subprocess.run([nasm,'-f','elf64','src/render/mesh_shaders.asm','-o',str(td/'shader.o')],cwd=ROOT,check=True,capture_output=True)
  subprocess.run(['cc','-O2',str(td/'driver.c'),str(td/'shader.o'),'-lGL','-lX11','-o',str(td/'driver')],check=True,capture_output=True)
  run=subprocess.run([str(td/'driver'),str(ROOT/'content/models/battle.rham'),str(td)],input=str(len(queries))+'\n'+''.join(' '.join(map(str,q))+'\n'for q in queries),text=True,capture_output=True,env=env,timeout=45);assert run.returncode==0,(run.returncode,run.stderr)
  lower=upper=0;error=0.
  for control,active,lod,n,base,frame,shoot,length,age in cases:
   baseline=list(struct.iter_unpack('<7f',(td/f'{control}.bin').read_bytes()));aimed=list(struct.iter_unpack('<7f',(td/f'{active}.bin').read_bytes()))
   phase=min(age*length/8.,length-1);a=shoot+int(phase);b=min(a+1,shoot+length-1);f=phase-int(phase)
   for v,(old,new)in enumerate(zip(baseline,aimed)):
    offset=vo+base*16+(frame*n+v)*48;local=struct.unpack_from('<3f',pack,offset);weight=struct.unpack_from('<f',pack,offset+28)[0]
    if weight==0:assert old==new,('lower leg changed',lod,frame,age,v);lower+=1
    pointA=struct.unpack_from('<3f',pack,vo+base*16+(a*n+v)*48);pointB=struct.unpack_from('<3f',pack,vo+base*16+(b*n+v)*48)
    p=[local[k]*(1-weight)+(pointA[k]*(1-f)+pointB[k]*f)*weight for k in range(3)]
    c,s=math.cos(.15*weight),math.sin(.15*weight);y,z=p[1]-1.35,p[2];p[1],p[2]=c*y+s*z+1.35,-s*y+c*z
    c,s=math.cos(-1.2*weight),math.sin(-1.2*weight);x,z=p[0],p[2];p[0],p[2]=c*x+s*z,-s*x+c*z
    c,s=math.cos(.4),math.sin(.4);expected=(100+c*p[0]+s*p[2],30+p[1],100-s*p[0]+c*p[2]);actual=(new[0],new[1],new[3]);error=max(error,max(abs(a-b)for a,b in zip(expected,actual)))
    if weight==1 and old!=new:upper+=1
  assert error<.0001 and upper and lower,(error,upper,lower)
  print(json.dumps({'suite':'infantry-aim-actual-shader-GL','passed':True,'cases':len(cases),'lower_vertices_bit_identical':lower,'upper_vertices_changed':upper,'maximum_position_error_metres':error,'shader_sha256':hashlib.sha256(shader).hexdigest(),'context':run.stderr.strip(),'scope':'Actual embedded shader, both infantry LODs, idle/walk lower clips and three actual shoot ages. Fixed lower vertex positions/lighting and independent upper yaw/pitch; reference mask, not bone IK.'}))
finally:
 if read>=0:os.close(read)
 if write>=0:os.close(write)
 if server is not None:server.terminate();server.wait(timeout=5)
