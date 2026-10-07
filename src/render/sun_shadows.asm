; Bounded current-frame directional depth map. CPU runtime is NASM/SSE2.
default rel
extern hdr_enabled
extern glGenFramebuffers,glBindFramebuffer,glDeleteFramebuffers,glCheckFramebufferStatus
extern glGenTextures,glBindTexture,glTexStorage2D,glTexParameteri,glTexParameterfv,glDeleteTextures,glFramebufferTexture2D
extern glDrawBuffer,glReadBuffer,glGetIntegerv,glViewport,glClear,glActiveTexture
extern glGetUniformLocation,glProgramUniform1i,glProgramUniformMatrix4fv
section .data
global sun_shadows_enabled
sun_shadows_enabled: dd 1
section .rodata
size: dd 2048
white: dd 1.0,1.0,1.0,1.0
quarter: dd 0.25
four: dd 4.0
; Column-major orthographic basis; existing normalised sun (.35,.85,-.2).
basis: dd -0.000969021363978,-0.00153221140641,-0.000363325978923,0,0,0.000836922196779,-0.00088236309167,0,-0.00169578738696,0.000875549375092,0.000207614845099,0,0,0,0,1.0
matrix_name: db 'sunShadowMatrix',0
pass_name: db 'sunShadowPass',0
ready_name: db 'sunShadowReady',0
section .bss align=16
global sun_shadow_texture,sun_shadow_fbo,sun_shadow_ready,sun_shadow_pass,sun_shadow_budget,sun_shadow_casters,sun_shadow_frames,sun_shadow_matrix
sun_shadow_texture: resd 1
sun_shadow_fbo: resd 1
sun_shadow_ready: resd 1
sun_shadow_pass: resd 1
sun_shadow_budget: resd 1
sun_shadow_casters: resd 1
sun_shadow_frames: resd 1
alignb 16
sun_shadow_matrix: resd 16
centre: resd 3
filter_camera: resd 3
saved_fbo: resd 1
saved_read_fbo: resd 1
saved_viewport: resd 4
saved_active: resd 1
ready: resd 1
section .text
global sun_shadows_init,sun_shadows_shutdown,sun_shadows_begin,sun_shadows_end,sun_shadows_apply,sun_shadows_matrix
; Pure CPU camera XYZ ->0/-1; output matrix unchanged on invalid input.
sun_shadows_matrix:
 movd eax,xmm0
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .invalid
 movd eax,xmm1
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .invalid
 movd eax,xmm2
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .invalid
 movss [filter_camera],xmm0
 movss [filter_camera+4],xmm1
 movss [filter_camera+8],xmm2
 mulss xmm0,[quarter]
 cvttss2si eax,xmm0
 cvtsi2ss xmm0,eax
 mulss xmm0,[four]
 movss [centre],xmm0
 movss [centre+4],xmm1
 mulss xmm2,[quarter]
 cvttss2si eax,xmm2
 cvtsi2ss xmm2,eax
 mulss xmm2,[four]
 movss [centre+8],xmm2
 lea rsi,[basis]
 lea rdi,[sun_shadow_matrix]
 mov ecx,8
 rep movsq
 xor ecx,ecx
.row:
 lea rdx,[sun_shadow_matrix]
 movss xmm0,[rdx+rcx*4]
 mulss xmm0,[centre]
 movss xmm1,[rdx+rcx*4+16]
 mulss xmm1,[centre+4]
 addss xmm0,xmm1
 movss xmm1,[rdx+rcx*4+32]
 mulss xmm1,[centre+8]
 addss xmm0,xmm1
 xorps xmm1,xmm1
 subss xmm1,xmm0
 movss [rdx+rcx*4+48],xmm1
 inc ecx
 cmp ecx,3
 jb .row
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
sun_shadows_init:
 push rbx
 cmp dword [ready],1
 je .success
 mov edi,0x84e0
 lea rsi,[saved_active]
 call glGetIntegerv wrt ..plt
 mov edi,0x8ca6
 lea rsi,[saved_fbo]
 call glGetIntegerv wrt ..plt
 mov edi,0x8caa
 lea rsi,[saved_read_fbo]
 call glGetIntegerv wrt ..plt
 mov edi,0x84ce ; reserved texture unit14; bloom owns15
 call glActiveTexture wrt ..plt
 mov edi,1
 lea rsi,[sun_shadow_texture]
 call glGenTextures wrt ..plt
 mov edi,0xde1
 mov esi,[sun_shadow_texture]
 call glBindTexture wrt ..plt
 mov edi,0xde1
 mov esi,1
 mov edx,0x81a6 ; DEPTH_COMPONENT24
 mov ecx,2048
 mov r8d,2048
 call glTexStorage2D wrt ..plt
%macro PARAM 2
 mov edi,0xde1
 mov esi,%1
 mov edx,%2
 call glTexParameteri wrt ..plt
%endmacro
 PARAM 0x2801,0x2601
 PARAM 0x2800,0x2601
 PARAM 0x2802,0x812d
 PARAM 0x2803,0x812d
 PARAM 0x884c,0x884e
 PARAM 0x884d,0x203
 mov edi,0xde1
 mov esi,0x1004
 lea rdx,[white]
 call glTexParameterfv wrt ..plt
 mov edi,1
 lea rsi,[sun_shadow_fbo]
 call glGenFramebuffers wrt ..plt
 mov edi,0x8d40
 mov esi,[sun_shadow_fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,0x8d40
 mov esi,0x8d00
 mov edx,0xde1
 mov ecx,[sun_shadow_texture]
 xor r8d,r8d
 call glFramebufferTexture2D wrt ..plt
 xor edi,edi
 call glDrawBuffer wrt ..plt
 xor edi,edi
 call glReadBuffer wrt ..plt
 mov edi,0x8d40
 call glCheckFramebufferStatus wrt ..plt
 cmp eax,0x8cd5
 jne .cleanup
 mov dword [ready],1
 call restore_init
.success:
 xor eax,eax
 pop rbx
 ret
.cleanup:
 call restore_init
 call sun_shadows_shutdown
 mov eax,-1
 pop rbx
 ret
restore_init:
 sub rsp,8
 mov edi,0x8ca9
 mov esi,[saved_fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,0x8ca8
 mov esi,[saved_read_fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,[saved_active]
 call glActiveTexture wrt ..plt
 add rsp,8
 ret
; EDI tactical and camera XYZ ->1 begun/0disabled/-1invalid. Caller depth test
; and writes enabled, original colour target preserved; no program/VAO changes.
sun_shadows_begin:
 push rbx
 mov dword [sun_shadow_ready],0
 mov dword [sun_shadow_pass],0
 mov dword [sun_shadow_casters],0
 mov dword [sun_shadow_budget],1024
 test edi,edi
 jnz .skip
 cmp dword [ready],1
 jne .skip
 cmp dword [sun_shadows_enabled],0
 je .skip
 cmp dword [hdr_enabled],0
 je .skip
 call sun_shadows_matrix
 test eax,eax
 jnz .done
 mov edi,0x8ca6
 lea rsi,[saved_fbo]
 call glGetIntegerv wrt ..plt
 mov edi,0x8caa
 lea rsi,[saved_read_fbo]
 call glGetIntegerv wrt ..plt
 mov edi,0xba2
 lea rsi,[saved_viewport]
 call glGetIntegerv wrt ..plt
 mov edi,0x8d40
 mov esi,[sun_shadow_fbo]
 call glBindFramebuffer wrt ..plt
 xor edi,edi
 xor esi,esi
 mov edx,2048
 mov ecx,2048
 call glViewport wrt ..plt
 mov edi,0x100
 call glClear wrt ..plt
 mov dword [sun_shadow_pass],1
 mov eax,1
 jmp .done
.skip:
 xor eax,eax
.done:
 pop rbx
 ret
sun_shadows_end:
 push rbx
 cmp dword [sun_shadow_pass],1
 jne .done
 mov edi,0x8ca9
 mov esi,[saved_fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,0x8ca8
 mov esi,[saved_read_fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,[saved_viewport]
 mov esi,[saved_viewport+4]
 mov edx,[saved_viewport+8]
 mov ecx,[saved_viewport+12]
 call glViewport wrt ..plt
 mov dword [sun_shadow_pass],0
 mov dword [sun_shadow_ready],1
 inc dword [sun_shadow_frames]
.done:
 pop rbx
 ret
; Valid linked program. DSA uniforms; texture unit14 reserved, active restored.
sun_shadows_apply:
 push rbx
 mov ebx,edi
 lea rsi,[pass_name]
 call glGetUniformLocation wrt ..plt
 mov edi,ebx
 mov esi,eax
 mov edx,[sun_shadow_pass]
 call glProgramUniform1i wrt ..plt
 mov edi,ebx
 lea rsi,[ready_name]
 call glGetUniformLocation wrt ..plt
 mov edi,ebx
 mov esi,eax
 mov edx,[sun_shadow_ready]
 call glProgramUniform1i wrt ..plt
 mov edi,ebx
 lea rsi,[matrix_name]
 call glGetUniformLocation wrt ..plt
 mov edi,ebx
 mov esi,eax
 mov edx,1
 xor ecx,ecx
 lea r8,[sun_shadow_matrix]
 call glProgramUniformMatrix4fv wrt ..plt
 mov edi,0x84e0
 lea rsi,[saved_active]
 call glGetIntegerv wrt ..plt
 mov edi,0x84ce
 call glActiveTexture wrt ..plt
 mov edi,0xde1
 xor esi,esi
 cmp dword [sun_shadow_pass],0
 jne .bind
 mov esi,[sun_shadow_texture]
.bind:
 call glBindTexture wrt ..plt
 mov edi,[saved_active]
 call glActiveTexture wrt ..plt
 pop rbx
 ret
; Private renderer scratch64/count/capacity records -> kept/-1; stable in-place
; compaction, caller-saved only,128 per batch and1024 per frame. CPU-only.
global sun_shadows_filter
sun_shadows_filter:
 cmp dword [sun_shadow_pass],1
 jne .bad
 cmp esi,32772
 ja .bad
 cmp edx,32772
 ja .bad
 cmp esi,edx
 ja .bad
 test rdi,rdi
 jz .bad
 mov eax,esi
 shl rax,6
 add rax,rdi
 jc .bad
 mov r10d,[sun_shadow_budget]
 cmp r10d,1024
 ja .bad
 mov eax,[sun_shadow_casters]
 cmp eax,1024
 ja .bad
 add eax,r10d
 cmp eax,1024
 jne .bad
 mov r8,rdi
 mov r9,rdi
 xor ecx,ecx
 xor eax,eax
.candidate:
 cmp eax,esi
 jae .filtered
 cmp ecx,128
 jae .filtered
 cmp ecx,r10d
 jae .filtered
 movss xmm0,[r8]
 subss xmm0,[filter_camera]
 mulss xmm0,xmm0
 movss xmm1,[r8+8]
 subss xmm1,[filter_camera+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 mov edx,__float32__(409600.0)
 movd xmm1,edx
 ucomiss xmm0,xmm1
 jp .next
 ja .next
 mov edx,[r8+4]
 and edx,0x7fffffff
 cmp edx,__float32__(16000.0)
 ja .next
 movups xmm0,[r8]
 movups xmm1,[r8+16]
 movups xmm2,[r8+32]
 movups xmm3,[r8+48]
 movups [r9],xmm0
 movups [r9+16],xmm1
 movups [r9+32],xmm2
 movups [r9+48],xmm3
 add r9,64
 inc ecx
.next:
 add r8,64
 inc eax
 jmp .candidate
.filtered:
 sub [sun_shadow_budget],ecx
 add [sun_shadow_casters],ecx
 mov eax,ecx
 ret
.bad:
 mov eax,-1
 ret
sun_shadows_shutdown:
 push rbx
 cmp dword [sun_shadow_pass],1
 jne .idle
 call sun_shadows_end
.idle:
 mov dword [ready],0
 mov dword [sun_shadow_ready],0
 mov dword [sun_shadow_pass],0
 mov edi,1
 lea rsi,[sun_shadow_fbo]
 call glDeleteFramebuffers wrt ..plt
 mov edi,1
 lea rsi,[sun_shadow_texture]
 call glDeleteTextures wrt ..plt
 mov dword [sun_shadow_fbo],0
 mov dword [sun_shadow_texture],0
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
