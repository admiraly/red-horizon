#!/usr/bin/env python3
"""Real software-GL framebuffer plumbing smoke; no geometry/occlusion claim. Usage: TEST LIB."""
import ctypes as C,os,subprocess,tempfile,json,sys
r,w=os.pipe();proc=subprocess.Popen(['Xvfb','-displayfd',str(w),'-screen','0','640x480x24','-nolisten','tcp'],pass_fds=(w,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(w)
try:
 display=os.read(r,32).decode().strip();os.environ['DISPLAY']=':'+display;os.environ['LIBGL_ALWAYS_SOFTWARE']='1'
 fw=C.CDLL('libglfw.so.3');gl=C.CDLL('libGL.so.1');lib=C.CDLL(sys.argv[1])
 fw.glfwCreateWindow.argtypes=[C.c_int,C.c_int,C.c_char_p,C.c_void_p,C.c_void_p];fw.glfwCreateWindow.restype=C.c_void_p
 fw.glfwMakeContextCurrent.argtypes=[C.c_void_p];fw.glfwDestroyWindow.argtypes=[C.c_void_p]
 assert fw.glfwInit()==1
 for a,b in [(0x22002,4),(0x22003,5),(0x22008,0x32001),(0x20004,0)]:fw.glfwWindowHint(a,b)
 win=fw.glfwCreateWindow(320,240,b'census framebuffer smoke',None,None);assert win;fw.glfwMakeContextCurrent(win)
 entities=(C.c_uint32*(32768*8)).in_dll(lib,'sim_entities');entities[2]=100;entities[7]=1
 assert lib.visibility_init()==0
 lib.visibility_begin()
 gl.glClearBufferuiv.argtypes=[C.c_uint,C.c_int,C.POINTER(C.c_uint)]
 gl.glClearBufferuiv(0x1800,1,(C.c_uint*1)(0x10001))
 lib.visibility_world_end()
 # Masked cosmetic clear cannot erase opaque IDs.
 gl.glClearBufferuiv(0x1800,1,(C.c_uint*1)(0))
 lib.visibility_finish()
 assert C.c_uint32.in_dll(lib,'visibility_actors').value==1
 assert C.c_uint32.in_dll(lib,'visibility_high').value==1
 pixels=(C.c_uint32*(320*240)).in_dll(lib,'visibility_pixels');assert set(pixels)=={0x10001}
 state=C.c_int();gl.glGetIntegerv(0x8ca6,C.byref(state));assert state.value==0
 assert gl.glGetError()==0
 lib.visibility_write_map.argtypes=[C.c_char_p]
 with tempfile.TemporaryDirectory(prefix='rh-census-fbo-') as temp:
  path=temp+'/map.raw';assert lib.visibility_write_map(path.encode())==0
  assert os.path.getsize(path)==320*240*4
 assert lib.visibility_write_map(b'/nonexistent/rh-census.raw')==-1
 lib.visibility_report();lib.visibility_shutdown();assert gl.glGetError()==0
 width=C.c_uint32.in_dll(lib,'view_width');height=C.c_uint32.in_dll(lib,'view_height')
 for bad in [0,319,3841,0xffffffff]:
  width.value=bad;assert lib.visibility_init()==-1
 width.value=320
 for bad in [0,239,2161,0xffffffff]:
  height.value=bad;assert lib.visibility_init()==-1
 height.value=240
 assert lib.visibility_init()==0
 lib.visibility_begin();lib.visibility_world_end();lib.visibility_finish()
 assert C.c_uint32.in_dll(lib,'visibility_actors').value==0
 assert set(pixels)=={0}
 assert C.c_uint32.in_dll(lib,'visibility_capture_count').value==2
 lib.visibility_shutdown();assert gl.glGetError()==0
 fw.glfwDestroyWindow(win);fw.glfwTerminate()
 print(json.dumps({'suite':'visibility_framebuffer','passed':True,'real_gl_fbo_smoke':True,'software':True,'resolution':[320,240],'integer_attachment_readback':True,'masked_cosmetics_preserve_ids':True,'default_fbo_restored':True,'map_bytes':320*240*4,'gl_errors':0}))
finally:
 os.close(r);proc.terminate();proc.wait(timeout=5)
