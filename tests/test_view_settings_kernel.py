#!/usr/bin/env python3
"""Development-only ABI/parser/projection test of actual assembled settings module."""
import ctypes as C,json,math,struct,sys
lib=C.CDLL(sys.argv[1]);lib.view_settings_parse.argtypes=[C.c_char_p,C.c_char_p];lib.view_settings_parse.restype=C.c_int
width=C.c_uint32.in_dll(lib,'view_width');height=C.c_uint32.in_dll(lib,'view_height');projection=(C.c_float*2).in_dll(lib,'view_projection');half=(C.c_float*2).in_dll(lib,'view_half_size');sens=C.c_float.in_dll(lib,'view_sensitivity')
lib.view_settings_apply()
assert struct.pack('2f',*projection)==struct.pack('2f',1.05,1.87)
assert list(half)==[640.,360.]
assert lib.view_settings_parse(b'--not-a-setting',None)==0
assert lib.view_settings_parse(b'--width',None)==-1
for text in [b'NaN',b'Inf',b'-Inf',b'1e999',b'1e-999',b' 1920',b'1920 ',b'1920x',b'0x780',b'1919.5',b'0',b'-1920']:
 assert lib.view_settings_parse(b'--width',text)==-1,text
assert width.value==1280
assert lib.view_settings_parse(b'--width',b'1.92e3')==1
assert lib.view_settings_parse(b'--height',b'1080')==1
assert lib.view_settings_parse(b'--fov',b'90')==1
assert lib.view_settings_parse(b'--sensitivity',b'1e-3')==1
assert lib.view_settings_parse(b'--width',b'1280')==-1
assert width.value==1920
lib.view_settings_apply()
assert list(half)==[960.,540.]
assert abs(projection[1]-1.)<1e-6
assert abs(projection[0]-(1.05/1.87))<1e-6
assert abs(sens.value-.001)<1e-9
print(json.dumps({'strict_parser':True,'duplicate_rejection':True,'default_projection_bit_exact':True,'configured_projection':list(projection),'half_viewport':list(half)}))
