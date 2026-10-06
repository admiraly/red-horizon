#!/usr/bin/env python3
"""Strict pre-context binding CLI and development-driver path forwarding."""
import importlib.util,json,os,pathlib,subprocess,sys,tempfile,types
exe=pathlib.Path(sys.argv[1]).resolve();root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-bind-cli-')as name:
 td=pathlib.Path(name);good=td/'profile with spaces.cfg';good.write_bytes((root/'content/bindings-default.cfg').read_bytes())
 bad=td/'bad.cfg';bad.write_text('forward=S\n')
 env=dict(os.environ);env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None)
 invalid=[['--bindings'],['--bindings',str(td/'missing')],['--bindings',str(td)],['--bindings',str(bad)],['--bindings',str(good),'--bindings',str(good)]]
 for args in invalid:
  p=subprocess.run([str(exe),*args],cwd=exe.parent,env=env,capture_output=True,text=True,timeout=5)
  assert p.returncode!=0 and 'Invalid bindings file' in p.stdout,(args,p.stdout,p.stderr)
  assert 'GLFW' not in p.stderr,'invalid binding started graphics'
 spec=importlib.util.spec_from_file_location('rh_binding_dev',root/'tools/dev.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 args=types.SimpleNamespace(width=None,height=None,fov=None,sensitivity=None,bindings=str(good))
 assert module.client_view_args(args)==['--bindings',str(good.resolve())]
 print(json.dumps({'suite':'input-bindings-cli','passed':True,'pre_context_invalid_cases':len(invalid),'driver_absolute_path_with_spaces':True,'limits':['Valid client binding parsing/input is covered by real solo/co-op tests.']}))
