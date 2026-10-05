#!/usr/bin/env python3
"""Actual NASM RHTX rejection and cosmetic-only bounded weather state."""
import ctypes as C
import json,os,struct,sys,tempfile
from pathlib import Path
lib=C.CDLL(str(Path(sys.argv[1]).resolve()));source=Path(sys.argv[2]).read_bytes()
lib.environment_select.argtypes=[C.c_int,C.c_int]
lib.environment_step.argtypes=[C.c_float]
lib.environment_parse.argtypes=[C.c_char_p]
weather=(C.c_float*4).in_dll(lib,'environment_weather')
old=os.getcwd();rejected=0
with tempfile.TemporaryDirectory() as folder:
 os.chdir(folder);path=Path('content/textures/terrain.rhtx');path.parent.mkdir(parents=True)
 try:
  path.write_bytes(source);assert lib.texture_asset_load()==0
  for offset,value in ((0,0),(4,2),(8,len(source)-1),(12,0),(12,1024),(16,511),(20,3),(24,0xffffffff),(28,2)):
   bad=bytearray(source);struct.pack_into('<I',bad,offset,value);path.write_bytes(bad)
   assert lib.texture_asset_load()==-1,(offset,value);rejected+=1
  for bad in (source[:31],source[:-1],source+b'x'):
   path.write_bytes(bad);assert lib.texture_asset_load()==-1;rejected+=1
  path.unlink();assert lib.texture_asset_load()==-1;rejected+=1
  path.write_bytes(source);assert lib.texture_asset_load()==0
 finally:os.chdir(old)
for i,name in enumerate((b'clear',b'overcast',b'rain',b'fog')):
 assert lib.environment_parse(name)==i
assert lib.environment_parse(b'thunder')==-1
lib.environment_select(0,1);start=list(weather)
lib.environment_select(2,0);assert list(weather)==start,'preset jumped without transition'
lib.environment_step(.05);assert 0<weather[2]<.1
for _ in range(200):lib.environment_step(.05)
assert .99<weather[2]<=1 and .95<weather[1]<.97
saved=list(weather);assert lib.environment_select(99,1)==-1 and list(weather)==saved
print(json.dumps({'suite':'texture-assets','passed':True,'actual_bytes':len(source),'malformed_missing_rejected':rejected,'smooth_weather_state':True}))
