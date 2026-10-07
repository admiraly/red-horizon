#!/usr/bin/env python3
"""Production warning/GL proof; development-only preload controls fixed fixture.

Actual projectile_launch/projectile_tick/hazard_tick create the threat. The test
never writes a hazard record or a warning flag. A private Xvfb prevents desktop
interaction. Rendering is compared with an otherwise identical friendly shell.
"""
from xvfb_display import read_display_number
import argparse,hashlib,json,os,pathlib,select,shutil,signal,subprocess,sys,tempfile
parser=argparse.ArgumentParser();parser.add_argument('executable');parser.add_argument('--artifacts',type=pathlib.Path);args=parser.parse_args()
EXE=pathlib.Path(args.executable).resolve()
SYMBOLS={}
for line in subprocess.check_output(['nm','-n',str(EXE)],text=True).splitlines():
 fields=line.split()
 if len(fields)==3:
  name=fields[2]
  functions={'sim_init','terrain_height','projectile_launch','projectile_tick','hazard_tick','sim_checksum'}
  if name not in functions or fields[1] in ('t','T'):SYMBOLS[name]=int(fields[0],16)
C_SOURCE=r'''
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <math.h>
#include <sys/mman.h>
#include <unistd.h>
@DEFINES@
#define U32(n) (*(uint32_t*)(uintptr_t)A_##n)
#define F32(n) (*(float*)(uintptr_t)A_##n)
#define F64(n) (*(double*)(uintptr_t)A_##n)
#define FN(n,t) ((t)(uintptr_t)A_##n)
struct entity { float x,z; uint32_t hp,side,kind,front,target,generation; };
static int ready,reported,launch;
static uint64_t before;
static unsigned initial_local_ticks;
static float actual_eye;
void glfwPollEvents(void) {
 static void (*real)(void);
 if(!real)real=dlsym(RTLD_NEXT,"glfwPollEvents");
 real();
 if(!ready && U32(frame_count)>=4){
  ready=1;
  long pagesize=sysconf(_SC_PAGESIZE);
  if(mprotect((void*)(A_maxdt & ~(uintptr_t)(pagesize-1)),pagesize,PROT_READ|PROT_WRITE)!=0)abort();
  F64(maxdt)=0.;F64(accum)=0.;
  if(FN(sim_init,int(*)(unsigned,unsigned))(32,42)!=0)abort();
  struct entity *e=(void*)(uintptr_t)A_sim_entities;
  for(int i=0;i<32;i++)e[i].hp=0;
  e[14].x=3500.;e[14].z=1900.;e[14].hp=160;
  e[14].kind=2;e[14].side=atoi(getenv("RH_WARNING_SIDE"));
  uint32_t *alive=(void*)(uintptr_t)A_sim_alive;alive[0]=!e[14].side;alive[1]=e[14].side;
  float ground=FN(terrain_height,float(*)(float,float))(3500.,2000.);
  actual_eye=ground+1.8f;
  unsigned char *p=(void*)(uintptr_t)A_sim_players;memset(p,0,256);
  float *pf=(void*)p;pf[0]=3500.;pf[1]=actual_eye;pf[2]=2000.;
  uint32_t *pi=(void*)p;pi[5]=100;pi[6]=30;pi[11]=1;pi[15]=100;
  float *cam=(void*)(uintptr_t)A_camera;cam[0]=pf[0];cam[1]=pf[1];cam[2]=pf[2];
  F32(yaw)=0.;F32(pitch)=0.;U32(last_hp)=100;U32(last_shots)=0;U32(last_hits)=0;
  F32(damage_flash)=0.;F32(recoil)=0.;F32(hit_flash)=0.;F32(shot_flash)=0.;
  float *weather=(void*)(uintptr_t)A_environment_weather;weather[0]=0.;weather[1]=.15;weather[2]=0.;weather[3]=.00008;
  F32(mesh_clock)=0.;
  memset((void*)(uintptr_t)A_effects_records,0,2048);
  memset((void*)(uintptr_t)A_air_trails_records,0,4096);
  launch=FN(projectile_launch,int(*)(unsigned,unsigned,float,float,float))(14,2,3508.,ground,2000.);
  if(launch!=0){fprintf(stderr,"launch=%d hp=%u kind=%u source x=%g z=%g ground=%g\n",launch,e[14].hp,e[14].kind,e[14].x,e[14].z,ground);abort();}
  for(int i=0;i<4;i++)FN(projectile_tick,void(*)(void))();
  FN(hazard_tick,void(*)(void))();
  before=FN(sim_checksum,uint64_t(*)(void))();
  initial_local_ticks=U32(local_sim_ticks);
  U32(frame_limit)=18;
 }
 if(ready && !reported && U32(frame_count)>=14){
  reported=1;
  uint64_t after=FN(sim_checksum,uint64_t(*)(void))();
  float *w=(void*)(uintptr_t)A_hazard_warning_uniform;
  float *cam=(void*)(uintptr_t)A_camera;
  unsigned char *h=(void*)(uintptr_t)A_hazards;
  unsigned active=0;for(int i=0;i<512;i++)active+=*(uint32_t*)(h+i*64+44)==1;
  fprintf(stdout,"{\"warning_gl_fixture\":true,\"launch_result\":%d,\"predicted_hazards\":%u,\"uniform\":[%.9g,%.9g,%.9g,%.9g],\"eye\":[%.9g,%.9g,%.9g],\"expected_eye_y\":%.9g,\"authority_before\":\"%016lx\",\"authority_after\":\"%016lx\",\"simulation_tick\":%u,\"local_ticks\":%u,\"initial_local_ticks\":%u}\n",launch,active,w[0],w[1],w[2],w[3],cam[0],cam[1],cam[2],actual_eye,before,after,U32(sim_tick_count),U32(local_sim_ticks),initial_local_ticks);
  fflush(stdout);
 }
}
'''
def terminate(process):
 if process is not None and process.poll() is None:
  process.terminate()
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
def run_case(env,folder,side):
 image=folder/f'side-{side}.ppm';process=None
 try:
  command=[str(EXE),'--frames','100','--screenshot',str(image)]
  process=subprocess.Popen(command,cwd=EXE.parent,
    env=dict(env,RH_WARNING_SIDE=str(side)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  out,err=process.communicate(timeout=25)
  assert process.returncode==0,(process.returncode,out,err)
  reports=[json.loads(l) for l in out.splitlines() if l.startswith('{') and 'warning_gl_fixture' in l]
  assert len(reports)==1,out
  report=reports[0]
  assert report['launch_result']==0 and report['predicted_hazards']==1,report
  assert report['authority_before']==report['authority_after'],report
  assert report['simulation_tick']==0 and report['local_ticks']==report['initial_local_ticks'],report
  assert abs(report['eye'][1]-report['expected_eye_y'])<1e-5,report
  assert report['uniform'][0]==side,report
  if side:assert -1<=report['uniform'][1]<=1 and 0<report['uniform'][2]<=4 and report['uniform'][3]==35,report
  else:assert report['uniform']==[0,0,0,0],report
  header,body=image.read_bytes().split(b'\n255\n',1)
  assert header==b'P6\n1280 720' and len(body)==1280*720*3
  report['image_sha256']=hashlib.sha256(body).hexdigest()
  return report,body
 finally:terminate(process)
read_fd,write_fd=os.pipe();server=None
try:
 server=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x720x24','-nolisten','tcp'],
  pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 os.close(write_fd);write_fd=None

 number=read_display_number(read_fd,10);assert number.isdigit()
 with tempfile.TemporaryDirectory(prefix='rh-warning-gl-') as directory:
  folder=pathlib.Path(directory)
  names=['frame_count','maxdt','thirty','accum','sim_init','sim_entities','sim_alive','terrain_height','sim_players','camera','yaw','pitch','last_hp','last_shots','last_hits','damage_flash','recoil','hit_flash','shot_flash','environment_weather','mesh_clock','terrain_obstacle_count','projectile_launch','projectile_tick','hazard_tick','sim_checksum','frame_limit','hazard_warning_uniform','hazards','sim_tick_count','local_sim_ticks','effects_records','air_trails_records']
  source=folder/'fixture.c';source.write_text(C_SOURCE.replace('@DEFINES@','\n'.join(f'#define A_{n} 0x{SYMBOLS[n]:x}UL' for n in names)))
  shared=folder/'fixture.so';subprocess.run(['cc','-shared','-fPIC','-O2',str(source),'-ldl','-o',str(shared)],check=True)
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null',LD_PRELOAD=str(shared))
  env.pop('WAYLAND_DISPLAY',None)
  quiet,a=run_case(env,folder,0);threat,b=run_case(env,folder,1)
  changed=[i//3 for i in range(0,len(a),3) if a[i:i+3]!=b[i:i+3]]
  assert changed,'incoming warning was not visible'
  coords=[(i%1280,i//1280) for i in changed]
  bounds=[min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords)]
  # Screenshot rows are top-down. Only the compact top HUD
  # strip may change: no screen wash or unrelated world silhouette changes.
  assert all(450<=x<=830 and 44<=y<=100 for x,y in coords),(len(changed),bounds)
  assert len(changed)>=100,(len(changed),bounds)
  report={'suite':'hazard-warning-actual-gl','passed':True,'cases':{'friendly_shell':quiet,'enemy_shell':threat},'changed_pixels':len(changed),'changed_bounds_top_down':bounds,'render_authority_unchanged':True,'executable':str(EXE),'executable_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'scope':'Private Xvfb software GL; actual production projectile launch, four physical flight steps, hazard prediction/query and HUD; frozen render clocks; paired friendly/enemy threat. No gameplay performance, network warning or listening claim.'}
  if args.artifacts:
   args.artifacts.mkdir(parents=True,exist_ok=True)
   for side in (0,1):shutil.copy2(folder/f'side-{side}.ppm',args.artifacts/f'side-{side}.ppm')
   (args.artifacts/'report.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report))
finally:
 if read_fd is not None:os.close(read_fd)
 if write_fd is not None:os.close(write_fd)
 terminate(server)
