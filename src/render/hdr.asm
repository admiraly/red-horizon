; Assembly-owned RGBA16F scene target and display tone pass. Cosmetic only.
; Current GL context required; fixed startup viewport 320..3840 x 240..2160.
; hdr_begin(EDI tactical) selects linear world output; hdr_present(EDI optional
; external colour texture, ESI tactical) draws to the default framebuffer. The
; caller restores its program/VAO before HUD. Init/shutdown are idempotent.
default rel
extern bloom_init,bloom_render,bloom_shutdown,bloom_strength
extern glViewport
extern view_width,view_height
extern glGenFramebuffers,glBindFramebuffer,glDeleteFramebuffers,glCheckFramebufferStatus
extern glGenTextures,glBindTexture,glTexStorage2D,glTexParameteri,glDeleteTextures,glFramebufferTexture2D
extern glGenRenderbuffers,glBindRenderbuffer,glRenderbufferStorage,glFramebufferRenderbuffer,glDeleteRenderbuffers
extern glGenVertexArrays,glBindVertexArray,glDeleteVertexArrays
extern glCreateShader,glShaderSource,glCompileShader,glGetShaderiv,glGetShaderInfoLog,glDeleteShader
extern glCreateProgram,glAttachShader,glLinkProgram,glGetProgramiv,glGetProgramInfoLog,glDeleteProgram
extern glUseProgram,glGetUniformLocation,glUniform1i,glUniform1f,glActiveTexture
extern glDrawBuffer,glReadBuffer,glClearBufferfv,glClear,glDepthMask,glDisable,glEnable,glDrawArrays,puts
section .rodata
global hdr_vertex_source,hdr_fragment_source
hdr_vertex_source: incbin "shaders/present.vert"
db 0
hdr_fragment_source: incbin "shaders/present.frag"
db 0
scene_name: db 'scene',0
exposure_name: db 'exposure',0
bloom_name: db 'bloomImage',0
bloom_strength_name: db 'bloomStrength',0
zero: dd 0.0
passthrough_name: db 'passthrough',0
clear_linear: dd 0.09463,0.14732,0.17887,1.0 ; approximate decoded legacy clear
clear_display: dd 0.34,0.42,0.46,1.0
section .data
global hdr_enabled,hdr_exposure
hdr_enabled: dd 1
hdr_exposure: dd 1.0
section .bss
global hdr_scene_texture,hdr_scene_fbo,hdr_world_linear,hdr_width,hdr_height,hdr_present_count,hdr_frame_presented
hdr_scene_texture: resd 1
hdr_scene_fbo: resd 1
hdr_world_linear: resd 1
hdr_width: resd 1
hdr_height: resd 1
hdr_present_count: resd 1
hdr_frame_presented: resd 1
depth: resd 1
vao: resd 1
program: resd 1
vertex_shader: resd 1
fragment_shader: resd 1
ready: resd 1
active: resd 1
status: resd 1
scene_loc: resd 1
exposure_loc: resd 1
passthrough_loc: resd 1
bloom_loc: resd 1
bloom_strength_loc: resd 1
log: resb 4096
section .text
global hdr_init,hdr_begin,hdr_present,hdr_shutdown
hdr_init:
 push rbx
 cmp dword [ready],1
 je .success
 mov eax,[view_width]
 cmp eax,320
 jb .fail
 cmp eax,3840
 ja .fail
 mov [hdr_width],eax
 mov eax,[view_height]
 cmp eax,240
 jb .fail
 cmp eax,2160
 ja .fail
 mov [hdr_height],eax
 mov edi,0x8b31
 lea rsi,[hdr_vertex_source]
 call hdr_compile
 mov [vertex_shader],eax
 test eax,eax
 jz .cleanup
 mov edi,0x8b30
 lea rsi,[hdr_fragment_source]
 call hdr_compile
 mov [fragment_shader],eax
 test eax,eax
 jz .cleanup
 call glCreateProgram wrt ..plt
 mov [program],eax
 mov edi,eax
 mov esi,[vertex_shader]
 call glAttachShader wrt ..plt
 mov edi,[program]
 mov esi,[fragment_shader]
 call glAttachShader wrt ..plt
 mov edi,[program]
 call glLinkProgram wrt ..plt
 mov edi,[program]
 mov esi,0x8b82
 lea rdx,[status]
 call glGetProgramiv wrt ..plt
 cmp dword [status],1
 jne .linkfail
 mov edi,[program]
 lea rsi,[scene_name]
 call glGetUniformLocation wrt ..plt
 mov [scene_loc],eax
 mov edi,[program]
 lea rsi,[exposure_name]
 call glGetUniformLocation wrt ..plt
 mov [exposure_loc],eax
 mov edi,[program]
 lea rsi,[passthrough_name]
 call glGetUniformLocation wrt ..plt
 mov [passthrough_loc],eax
 mov edi,[program]
 lea rsi,[bloom_name]
 call glGetUniformLocation wrt ..plt
 mov [bloom_loc],eax
 mov edi,[program]
 lea rsi,[bloom_strength_name]
 call glGetUniformLocation wrt ..plt
 mov [bloom_strength_loc],eax
 mov edi,1
 lea rsi,[vao]
 call glGenVertexArrays wrt ..plt
 mov edi,1
 lea rsi,[hdr_scene_fbo]
 call glGenFramebuffers wrt ..plt
 mov edi,0x8d40
 mov esi,[hdr_scene_fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,1
 lea rsi,[hdr_scene_texture]
 call glGenTextures wrt ..plt
 mov edi,0xde1
 mov esi,[hdr_scene_texture]
 call glBindTexture wrt ..plt
 mov edi,0xde1
 mov esi,1
 mov edx,0x881a ; RGBA16F preserves above-display scene radiance
 mov ecx,[hdr_width]
 mov r8d,[hdr_height]
 call glTexStorage2D wrt ..plt
 mov edi,0xde1
 mov esi,0x2801
 mov edx,0x2600 ; NEAREST; texelFetch is exact at the fixed viewport
 call glTexParameteri wrt ..plt
 mov edi,0xde1
 mov esi,0x2800
 mov edx,0x2600
 call glTexParameteri wrt ..plt
 mov edi,0x8d40
 mov esi,0x8ce0
 mov edx,0xde1
 mov ecx,[hdr_scene_texture]
 xor r8d,r8d
 call glFramebufferTexture2D wrt ..plt
 mov edi,1
 lea rsi,[depth]
 call glGenRenderbuffers wrt ..plt
 mov edi,0x8d41
 mov esi,[depth]
 call glBindRenderbuffer wrt ..plt
 mov edi,0x8d41
 mov esi,0x81a6
 mov edx,[hdr_width]
 mov ecx,[hdr_height]
 call glRenderbufferStorage wrt ..plt
 mov edi,0x8d40
 mov esi,0x8d00
 mov edx,0x8d41
 mov ecx,[depth]
 call glFramebufferRenderbuffer wrt ..plt
 mov edi,0x8ce0
 call glDrawBuffer wrt ..plt
 mov edi,0x8d40
 call glCheckFramebufferStatus wrt ..plt
 cmp eax,0x8cd5
 jne .cleanup
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,0xde1
 xor esi,esi
 call glBindTexture wrt ..plt
 mov edi,0x8d41
 xor esi,esi
 call glBindRenderbuffer wrt ..plt
 mov edi,[hdr_width]
 mov esi,[hdr_height]
 call bloom_init
 test eax,eax
 jnz .cleanup
 mov dword [ready],1
.success:
 xor eax,eax
 pop rbx
 ret
.linkfail:
 mov edi,[program]
 mov esi,4096
 xor edx,edx
 lea rcx,[log]
 call glGetProgramInfoLog wrt ..plt
 lea rdi,[log]
 call puts wrt ..plt
.cleanup:
 call hdr_shutdown
.fail:
 mov eax,-1
 pop rbx
 ret
global hdr_compile
hdr_compile:
 push rbx
 sub rsp,16
 mov [rsp],rsi
 call glCreateShader wrt ..plt
 mov ebx,eax
 mov edi,eax
 mov esi,1
 lea rdx,[rsp]
 xor ecx,ecx
 call glShaderSource wrt ..plt
 mov edi,ebx
 call glCompileShader wrt ..plt
 mov edi,ebx
 mov esi,0x8b81
 lea rdx,[status]
 call glGetShaderiv wrt ..plt
 mov eax,ebx
 cmp dword [status],1
 je .done
 mov edi,ebx
 mov esi,4096
 xor edx,edx
 lea rcx,[log]
 call glGetShaderInfoLog wrt ..plt
 lea rdi,[log]
 call puts wrt ..plt
 mov edi,ebx
 call glDeleteShader wrt ..plt
 xor eax,eax
.done:
 add rsp,16
 pop rbx
 ret
hdr_begin:
 push rbx
 mov ebx,edi
 mov dword [hdr_world_linear],0
 mov dword [hdr_frame_presented],0
 cmp dword [ready],1
 jne .done
 cmp dword [hdr_enabled],0
 je .done
 mov edi,0x8d40
 mov esi,[hdr_scene_fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,0x8ce0
 call glDrawBuffer wrt ..plt
 lea rdx,[clear_display]
 test ebx,ebx
 jnz .clear
 mov dword [hdr_world_linear],1
 lea rdx,[clear_linear]
.clear:
 mov edi,0x1800
 xor esi,esi
 call glClearBufferfv wrt ..plt
 mov edi,1
 call glDepthMask wrt ..plt
 mov edi,0x100
 call glClear wrt ..plt
 mov dword [active],1
.done:
 pop rbx
 ret
hdr_present:
 push rbx
 push r12
 push r13
 mov r12d,edi
 mov r13d,esi
 cmp dword [active],1
 jne .done
 test r12d,r12d
 jnz .texture
 mov r12d,[hdr_scene_texture]
.texture:
 mov edi,0xb71
 call glDisable wrt ..plt
 mov edi,0xbe2
 call glDisable wrt ..plt
 mov edi,0x8db9 ; FRAMEBUFFER_SRGB: encode explicitly for the current display
 call glDisable wrt ..plt
 xor ebx,ebx
 test r13d,r13d
 jnz .no_bloom
 mov edi,r12d
 call bloom_render
 mov ebx,eax
.no_bloom:
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,0x405
 call glDrawBuffer wrt ..plt
 mov edi,0x405
 call glReadBuffer wrt ..plt
 xor edi,edi
 xor esi,esi
 mov edx,[hdr_width]
 mov ecx,[hdr_height]
 call glViewport wrt ..plt
 ; Fragment texture unit15 is reserved for bloom; material units are unchanged.
 mov edi,0x84cf
 call glActiveTexture wrt ..plt
 mov edi,0xde1
 mov esi,ebx
 call glBindTexture wrt ..plt
 mov edi,0x84c0
 call glActiveTexture wrt ..plt
 mov edi,0xde1
 mov esi,r12d
 call glBindTexture wrt ..plt
 mov edi,[program]
 call glUseProgram wrt ..plt
 mov edi,[scene_loc]
 xor esi,esi
 call glUniform1i wrt ..plt
 mov edi,[exposure_loc]
 movss xmm0,[hdr_exposure]
 call glUniform1f wrt ..plt
 mov edi,[bloom_loc]
 mov esi,15
 call glUniform1i wrt ..plt
 mov edi,[bloom_strength_loc]
 movss xmm0,[zero]
 test ebx,ebx
 jz .strength
 movss xmm0,[bloom_strength]
.strength:
 call glUniform1f wrt ..plt
 mov edi,[passthrough_loc]
 mov esi,r13d
 call glUniform1i wrt ..plt
 mov edi,[vao]
 call glBindVertexArray wrt ..plt
 mov edi,4
 xor esi,esi
 mov edx,3
 call glDrawArrays wrt ..plt
 mov edi,0x84cf
 call glActiveTexture wrt ..plt
 mov edi,0xde1
 xor esi,esi
 call glBindTexture wrt ..plt
 mov edi,0x84c0
 call glActiveTexture wrt ..plt
 mov edi,0xde1
 xor esi,esi
 call glBindTexture wrt ..plt
 mov edi,0xb71
 call glEnable wrt ..plt
 mov dword [active],0
 mov dword [hdr_world_linear],0
 mov dword [hdr_frame_presented],1
 inc dword [hdr_present_count]
.done:
 pop r13
 pop r12
 pop rbx
 ret
hdr_shutdown:
 sub rsp,8
 call bloom_shutdown
 xor edi,edi
 call glUseProgram wrt ..plt
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,1
 lea rsi,[hdr_scene_fbo]
 call glDeleteFramebuffers wrt ..plt
 mov edi,1
 lea rsi,[hdr_scene_texture]
 call glDeleteTextures wrt ..plt
 mov edi,1
 lea rsi,[depth]
 call glDeleteRenderbuffers wrt ..plt
 mov edi,1
 lea rsi,[vao]
 call glDeleteVertexArrays wrt ..plt
 mov edi,[program]
 test edi,edi
 jz .vertex
 call glDeleteProgram wrt ..plt
.vertex:
 mov edi,[vertex_shader]
 test edi,edi
 jz .fragment
 call glDeleteShader wrt ..plt
.fragment:
 mov edi,[fragment_shader]
 test edi,edi
 jz .clear
 call glDeleteShader wrt ..plt
.clear:
 xor eax,eax
 mov [hdr_scene_fbo],eax
 mov [hdr_scene_texture],eax
 mov [depth],eax
 mov [vao],eax
 mov [program],eax
 mov [vertex_shader],eax
 mov [fragment_shader],eax
 mov [ready],eax
 mov [active],eax
 mov [hdr_world_linear],eax
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
