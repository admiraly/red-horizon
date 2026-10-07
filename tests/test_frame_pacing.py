#!/usr/bin/env python3
"""Native absolute-deadline callback: real sleep, lateness, EINTR and limits."""
import ctypes as C,json,os,pathlib,signal,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-pacing-') as temp:
 folder=pathlib.Path(temp);objects=[]
 for source in ('src/platform/linux/frame_pacing.asm','tests/probe_frame_pacing.asm'):
  obj=folder/(pathlib.Path(source).name+'.o');subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],cwd=ROOT,check=True,capture_output=True);objects.append(str(obj))
 library=folder/'libpacing.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects],check=True,capture_output=True);lib=C.CDLL(str(library))
 cap=C.c_uint.in_dll(lib,'client_frame_cap');waits=C.c_uint.in_dll(lib,'client_pacing_waits');rebases=C.c_uint.in_dll(lib,'client_pacing_rebases');errors=C.c_uint.in_dll(lib,'client_pacing_errors');results=[]
 for fps in (30,60,240):
  cap.value=fps;lib.client_pacing_init();start=time.monotonic();cpu=time.process_time()
  for _ in range(8):lib.client_frame_pace()
  elapsed=time.monotonic()-start;cost=time.process_time()-cpu
  assert elapsed>=8/fps-.002,(fps,elapsed)
  assert cost<elapsed*.3,(fps,cost,elapsed,'pacing spun CPU')
  assert waits.value>0 and errors.value==0,(fps,waits.value,errors.value)
  results.append({'requested_fps':fps,'calls':8,'wall_seconds':elapsed,'process_CPU_seconds':cost,'waits':waits.value,'late_rebases':rebases.value})
 cap.value=60;lib.client_pacing_init();time.sleep(.05);lib.client_frame_pace();assert rebases.value==1 and errors.value==0
 start=time.monotonic();lib.client_frame_pace();assert time.monotonic()-start>=1/60-.002,'late frame caused catch-up burst'
 cap.value=30;lib.client_pacing_init();observed=[];previous=signal.signal(signal.SIGALRM,lambda *_:observed.append(True))
 try:
  signal.setitimer(signal.ITIMER_REAL,.005);start=time.monotonic();lib.client_frame_pace();elapsed=time.monotonic()-start
  assert observed and elapsed>=1/30-.002 and errors.value==0,(observed,elapsed,errors.value)
 finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
 for invalid in (29,241,0xffffffff):
  cap.value=invalid;lib.client_pacing_init();lib.client_frame_pace();assert errors.value==1 and waits.value==rebases.value==0
 cap.value=0;lib.client_pacing_init();lib.client_frame_pace();assert errors.value==waits.value==rebases.value==0
 print(json.dumps({'suite':'native-real-frame-pacing','passed':True,'real_clock_cases':results,'late_frame_rebased':True,'EINTR_same_deadline_retry':True,'disabled_and_invalid_cap':True,'scope':'Native assembly with real monotonic kernel deadlines and no-spin process CPU gate; isolated cosmetic cap stub, not renderer/authority/frame-quality acceptance.'}))
