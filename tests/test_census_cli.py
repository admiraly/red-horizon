#!/usr/bin/env python3
"""Bounded optional capture CLI rejection before creating a context."""
import json,pathlib,subprocess,sys,os
exe=pathlib.Path(sys.argv[1]).resolve();env=dict(os.environ);env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None)
cases=[['--census'],['--census','--frames','0'],['--census','--frames','10001'],['--census','--frames','-1'],['--census','--frames','2junk'],['--census','--frames','NaN'],['--census','--frames','2147483648'],['--census','--frames','2','--census'],['--census-map','actors.raw','--frames','2'],['--census','--frames','2','--census-map'],['--census','--frames','2','--census-map',''],['--census','--frames','2','--census-map','a','--census-map','b']]
for args in cases:
 run=subprocess.run([str(exe),*args],cwd=exe.parent,env=env,capture_output=True,text=True,timeout=10)
 assert run.returncode!=0,args
 # Invalid options should never attempt GLFW/window/context initialization.
 assert not run.stderr.strip(),(args,run.stderr)
help_run=subprocess.run([str(exe),'--help'],cwd=exe.parent,env=env,capture_output=True,text=True,timeout=10)
assert help_run.returncode==0 and '--census-map' in help_run.stdout
print(json.dumps({'suite':'census_cli','passed':True,'pre_context_invalid_cases':len(cases),'valid_capture':'separately covered by production GL oracle'}))
