# Renderer platform choice: GLFW + OpenGL core

The first Linux assembly client uses GLFW 3.4 as a platform service for X11/GLX window/context creation and input polling. `glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_X11)` explicitly selects X11, including XWayland sessions. OpenGL 4.5 core is required; failure exits with a diagnostic. This is a deviation from directly calling Xlib/GLX, chosen to deliver and verify the renderer quickly. GLFW implements no project gameplay. Project-authored input, camera, draw submission, terrain-height sampling, timing, aim selection and commands remain NASM x86-64. GPU shaders are GLSL.

Linux dependencies: libc, libm, libGL, libglfw.so.3 **version 3.4 or newer**. No project C/C++ runtime or embedded scripting VM. The renderer has a fixed 1280x720 nonresizable viewport. Windows bindings and lower GL versions remain unimplemented.
