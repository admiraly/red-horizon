#!/usr/bin/env python3
"""Production input-event capture: short taps, held release, repeat and snapshots."""
import ctypes as C,hashlib,json,os,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
with tempfile.TemporaryDirectory(prefix='rh-input-frames-')as folder:
 td=pathlib.Path(folder);obj=td/'bindings.o';stub=td/'platform.o';so=td/'frames.so'
 subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(root/'src/platform/linux/input_bindings.asm'),'-o',str(obj)],check=True)
 subprocess.run([nasm,'-f','elf64',str(root/'tests/bindings_platform_stub.asm'),'-o',str(stub)],check=True)
 probe=td/'probe.o';subprocess.run([nasm,'-f','elf64',str(root/'tests/probe_input_frames.asm'),'-o',str(probe)],check=True)
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),str(obj),str(stub),str(probe)],check=True)
 l=C.CDLL(str(so));l.bindings_event.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int];l.bindings_event.restype=None;l.bindings_frame_begin.restype=None;l.bindings_frame_down.argtypes=[C.c_void_p,C.c_uint]
 codes=(C.c_uint*31).in_dll(l,'binding_codes')
 def event(code,action):l.bindings_event(None,code,0,action,0)
 def down(action):return l.bindings_frame_down(None,action)
 def states():return tuple(down(i)for i in range(31))
 for action,code in enumerate(codes):
  event(code,1);event(code,0);assert states()==(0,)*31
  l.bindings_frame_begin();expected=tuple(int(i==action)for i in range(31));assert states()==expected and states()==expected
  l.bindings_frame_begin();assert states()==(0,)*31
  event(code,1);l.bindings_frame_begin();assert states()==expected
  event(code,2);l.bindings_frame_begin();assert states()==expected
  event(code,0);l.bindings_frame_begin();assert states()==(0,)*31,'release added a sticky held frame'
  event(code,2);l.bindings_frame_begin();assert states()==(0,)*31,'repeat manufactured a press'
 # Coalesced same-frame presses, and simultaneous independent action pulses.
 for code in(codes[19],codes[20]):
  for _ in range(3):event(code,1);event(code,0)
 l.bindings_frame_begin();assert states()==tuple(int(i in(19,20))for i in range(31));l.bindings_frame_begin();assert states()==(0,)*31
 for code,action in[(-1,1),(65544,1),(codes[19],-1),(codes[19],3)]:event(code,action)
 l.bindings_frame_begin();assert states()==(0,)*31
 assert down(31)==0 and down(0xffffffff)==0
 # Verify nonvolatile registers and aligned caller stack on every helper path.
 l.probe_input_frames.argtypes=[C.c_uint,C.c_uint,C.c_int,C.POINTER(C.c_uint64)]
 for helper,code,action in[(0,codes[19],1),(0,codes[19],0),(0,0xffffffff,1),(0,codes[19],-1),(1,0,0),(2,19,0),(2,31,0),(2,0xffffffff,0)]:
  regs=(C.c_uint64*7)();l.probe_input_frames(helper,code,action,regs)
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,),('nonvolatile ABI',helper,tuple(regs))
 print(json.dumps({'suite':'input-frame-events','passed':True,'mapped_keyboard_mouse_actions':31,'short_taps_survive_once':31,'stable_repeated_reads':True,'held_release_has_no_extra_frame':31,'repeat_has_no_new_edge':31,'simultaneous_and_coalesced_pulses':True,'invalid_events_ignored':4,'nonvolatile_ABI_calls':8,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Actual NASM event/snapshot helpers, development platform stub; real GLFW/GUI/quit/authority behavior remains separate.'}))
