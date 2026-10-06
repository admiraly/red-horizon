#!/usr/bin/env python3
"""Atomic file parsing, defaults and real platform input routing with ABI probes."""
import ctypes as C,hashlib,json,os,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-bindings-') as name:
 td=pathlib.Path(name);obj=td/'bindings.o';so=td/'bindings.so'
 subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','-I',str(root)+'/',str(root/'src/platform/linux/input_bindings.asm'),'-o',str(obj)],check=True)
 probe=td/'probe.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(root/'tests/probe_input_bindings.asm'),'-o',str(probe)],check=True)
 platform=td/'platform.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(root/'tests/bindings_platform_stub.asm'),'-o',str(platform)],check=True)
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),str(obj),str(probe),str(platform)],check=True)
 l=C.CDLL(str(so));l.bindings_load.argtypes=[C.c_char_p];l.bindings_label.argtypes=[C.c_uint];l.bindings_label.restype=C.c_char_p
 codes=(C.c_uint*30).in_dll(l,'binding_codes');labels=lambda:[l.bindings_label(i).decode()for i in range(30)]
 defaults=list(codes);default_labels=labels();assert len(set(defaults))==30
 def path_load(path):
  out=(C.c_float*2)();regs=(C.c_uint64*7)();rc=l.probe_bindings_load(os.fsencode(path),out,regs)
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,)
  return rc
 def load(data):
  p=td/'saved bindings.cfg';p.write_bytes(data);return path_load(p)
 assert load((root/'content/bindings-default.cfg').read_bytes())==0 and list(codes)==defaults
 assert load(b'# saved overrides\r\n forward = UP \r\n back=DOWN\n left=LEFT\n right=RIGHT\n command_wheel=F12\n command_cancel=X\n quit=MMB')==0
 assert list(codes)[:4]==[265,264,263,262] and labels()[12:15]==['F12','X','MMB']
 good=(list(codes),labels())
 invalid=[b'forward=unknown',b'unknown=W',b'forward=UP\nforward=DOWN',b'forward=S',b'quit=F12\ncommand_wheel=F12',b'fire=',b'=W',b'forward UP',b'forward=UP=DOWN',b'forward=up',b'forward=UP\x00back=DOWN',b'forward='+b'A'*4096,b'reload=R # comment',b'#'+b'a'*4096]
 for data in invalid:
  assert load(data)==-1,data[:40]
  assert (list(codes),labels())==good,'failed load changed a published binding'
 for path in (td/'missing',td):assert path_load(path)==-1 and (list(codes),labels())==good
 fifo=td/'pipe';os.mkfifo(fifo);assert path_load(fifo)==-1,'nonregular file accepted'
 assert (list(codes),labels())==good
 assert load(b'')==0 and list(codes)==defaults and labels()==default_labels
 assert load(b'#'+b'x'*4095)==0,'exact4096 byte comment failed'
 l.bindings_down.argtypes=[C.c_void_p,C.c_uint]
 for action,code in enumerate(defaults):
  assert l.bindings_down(C.c_void_p(0x123400),action)==1
  assert C.c_uint.in_dll(l,'probe_binding_device').value==bool(code&65536)
  assert C.c_uint.in_dll(l,'probe_binding_code').value==(code&7 if code&65536 else code)
  assert C.c_uint64.in_dll(l,'probe_binding_window').value==0x123400
 assert l.bindings_down(None,30)==0 and l.bindings_down(None,0xffffffff)==0
 assert l.bindings_label(30)==b'' and l.bindings_label(0xffffffff)==b''
 print(json.dumps({'suite':'input-bindings-file','passed':True,'actions':30,'malformed_preserve_cases':len(invalid)+3,'partial_CRLF_no_final_newline':True,'regular_file_only':True,'exact4096_boundary':True,'published_atomic':True,'nonvolatile_ABI':True,'thirty_action_platform_dispatch':True,'headless_no_graphics_library':True,'default_labels':default_labels,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Startup-only Linux file parser; real input/GL and network behavior verified separately.']}))
