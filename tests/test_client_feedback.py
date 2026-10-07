#!/usr/bin/env python3
"""Development-only controlled wall-clock hitch and actual HUD uniform capture.
The shim delays glfwGetTime by100ms, reads existing cosmetic hit sequence, and
observes production glUniform4f; no authority/body/clock writes by the shim.
The existing gameplay fixture performs its declared initial staging and real fire.
"""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
SHIM=r'''
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static unsigned int weaponProgram,currentProgram;static int weaponLocation=-1;static unsigned int lastHit;
double glfwGetTime(void){static double(*real)(void);if(!real)real=dlsym(RTLD_NEXT,"glfwGetTime");usleep(100000);return real();}
int glGetUniformLocation(unsigned int p,const char *name){static int(*real)(unsigned int,const char*);if(!real)real=dlsym(RTLD_NEXT,"glGetUniformLocation");int location=real(p,name);if(!strcmp(name,"weaponState")){weaponProgram=p;weaponLocation=location;}return location;}
void glUseProgram(unsigned int p){static void(*real)(unsigned int);if(!real)real=dlsym(RTLD_NEXT,"glUseProgram");currentProgram=p;real(p);}
void glUniform4f(int location,float x,float y,float z,float w){static void(*real)(int,float,float,float,float);if(!real)real=dlsym(RTLD_NEXT,"glUniform4f");if(currentProgram==weaponProgram&&location==weaponLocation){const char *address=getenv("RH_FEEDBACK_SEQUENCE_ADDRESS");if(address){unsigned int seq=*(volatile unsigned int *)(uintptr_t)strtoull(address,0,10);if(seq>lastHit){lastHit=seq;FILE *f=fopen(getenv("RH_FEEDBACK_CAPTURE"),"a");if(f){fprintf(f,"{\"hit_sequence\":%u,\"hit_flash_sent_to_HUD\":%.9g,\"shot_flash_sent_to_HUD\":%.9g}\n",seq,z,w);fclose(f);}}}}real(location,x,y,z,w);}
'''
def main():
 exe=pathlib.Path(sys.argv[1]).resolve();legacy='--legacy' in sys.argv
 symbols={line.split()[2]:int(line.split()[0],16) for line in subprocess.check_output(['nm','-n',str(exe)],text=True).splitlines() if len(line.split())==3}
 with tempfile.TemporaryDirectory(prefix='rh-feedback-') as temp:
  folder=pathlib.Path(temp);source=folder/'shim.c';source.write_text(SHIM);shim=folder/'shim.so';capture=folder/'capture.jsonl'
  subprocess.run(['cc','-shared','-fPIC','-O2',str(source),'-ldl','-o',str(shim)],check=True,capture_output=True)
  env=dict(os.environ,LD_PRELOAD=str(shim),RH_FEEDBACK_SEQUENCE_ADDRESS=str(symbols['last_hits']),RH_FEEDBACK_CAPTURE=str(capture))
  run=subprocess.run([sys.executable,str(ROOT/'tests/test_client_gameplay.py'),str(exe)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90)
  rows=[json.loads(line) for line in capture.read_text().splitlines()] if capture.exists() else []
  assert rows,(run.returncode,run.stdout,run.stderr,'no actual hit HUD uniform observed')
  if legacy:
   assert all(0<r['hit_flash_sent_to_HUD']<.3 for r in rows),rows
   assert run.returncode==0 or 'authoritative hit did not produce HUD feedback' in run.stderr,(run.returncode,run.stderr)
  else:
   assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
   assert all(abs(r['hit_flash_sent_to_HUD']-1)<1e-6 for r in rows),rows
  print(json.dumps({'suite':'actual-client-fresh-feedback','passed':True,'legacy_negative_control':legacy,'client_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'hitch_wall_clock_ms_per_glfw_time_query':100,'actual_HUD_uniform_samples':rows,'underlying_gameplay_test_exit':run.returncode,'shim_authority_writes':False,'scope':'Actual8192 assembled client, genuine finite rifle damage and HUD uniform; delayed real wall clock, development-only initial gameplay staging. Fresh-hit amplitude proof, not perceptual quality, rendered-pixel persistence or physical-device timing.'}))
if __name__=='__main__':main()
