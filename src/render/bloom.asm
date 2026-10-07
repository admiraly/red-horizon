; Half-resolution RGBA16F bright extraction and separable Gaussian bloom.
; Assembly owns all resources; cosmetic only, fixed startup viewport.
default rel
extern hdr_compile,hdr_vertex_source
extern glCreateProgram,glAttachShader,glLinkProgram,glGetProgramiv,glGetProgramInfoLog
extern glDeleteProgram,glDeleteShader,glGetUniformLocation,glUniform1i,glUseProgram
extern glGenTextures,glBindTexture,glTexStorage2D,glTexParameteri,glDeleteTextures
extern glGenFramebuffers,glBindFramebuffer,glFramebufferTexture2D,glCheckFramebufferStatus,glDeleteFramebuffers
extern glGenVertexArrays,glBindVertexArray,glDeleteVertexArrays,glDrawBuffer,glDrawArrays,glViewport,glActiveTexture,puts
section .rodata
global bloom_fragment_source
bloom_fragment_source: incbin "shaders/bloom.frag"
db 0
source_name: db 'sourceImage',0
pass_name: db 'pass',0
section .data
global bloom_enabled,bloom_strength
bloom_enabled: dd 1
bloom_strength: dd 0.12
section .bss
global bloom_textures,bloom_fbos,bloom_width,bloom_height,bloom_pass_count,bloom_frame_count
bloom_textures: resd 2
bloom_fbos: resd 2
bloom_width: resd 1
bloom_height: resd 1
bloom_pass_count: resd 1
bloom_frame_count: resd 1
vertex: resd 1
fragment: resd 1
program: resd 1
vao: resd 1
ready: resd 1
status: resd 1
source_loc: resd 1
pass_loc: resd 1
log: resb 4096
section .text
global bloom_init,bloom_render,bloom_shutdown
; EDI full width, ESI full height. 0success/-1error; init idempotent.
bloom_init:
 push rbx
 cmp dword [ready],1
 je .success
 cmp edi,320
 jb .fail
 cmp edi,3840
 ja .fail
 cmp esi,240
 jb .fail
 cmp esi,2160
 ja .fail
 inc edi
 shr edi,1
 mov [bloom_width],edi
 inc esi
 shr esi,1
 mov [bloom_height],esi
 mov edi,0x8b31
 lea rsi,[hdr_vertex_source]
 call hdr_compile
 mov [vertex],eax
 test eax,eax
 jz .cleanup
 mov edi,0x8b30
 lea rsi,[bloom_fragment_source]
 call hdr_compile
 mov [fragment],eax
 test eax,eax
 jz .cleanup
 call glCreateProgram wrt ..plt
 mov [program],eax
 mov edi,eax
 mov esi,[vertex]
 call glAttachShader wrt ..plt
 mov edi,[program]
 mov esi,[fragment]
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
 lea rsi,[source_name]
 call glGetUniformLocation wrt ..plt
 mov [source_loc],eax
 mov edi,[program]
 lea rsi,[pass_name]
 call glGetUniformLocation wrt ..plt
 mov [pass_loc],eax
 mov edi,1
 lea rsi,[vao]
 call glGenVertexArrays wrt ..plt
 mov edi,2
 lea rsi,[bloom_textures]
 call glGenTextures wrt ..plt
 mov edi,2
 lea rsi,[bloom_fbos]
 call glGenFramebuffers wrt ..plt
 mov edi,0x84c0
 call glActiveTexture wrt ..plt
 xor ebx,ebx
.target:
 lea rax,[bloom_textures]
 mov esi,[rax+rbx*4]
 mov edi,0xde1
 call glBindTexture wrt ..plt
 mov edi,0xde1
 mov esi,1
 mov edx,0x881a
 mov ecx,[bloom_width]
 mov r8d,[bloom_height]
 call glTexStorage2D wrt ..plt
 mov edi,0xde1
 mov esi,0x2801
 mov edx,0x2601
 call glTexParameteri wrt ..plt
 mov edi,0xde1
 mov esi,0x2800
 mov edx,0x2601
 call glTexParameteri wrt ..plt
 mov edi,0xde1
 mov esi,0x2802
 mov edx,0x812f
 call glTexParameteri wrt ..plt
 mov edi,0xde1
 mov esi,0x2803
 mov edx,0x812f
 call glTexParameteri wrt ..plt
 lea rax,[bloom_fbos]
 mov esi,[rax+rbx*4]
 mov edi,0x8d40
 call glBindFramebuffer wrt ..plt
 mov edi,0x8d40
 mov esi,0x8ce0
 mov edx,0xde1
 lea rax,[bloom_textures]
 mov ecx,[rax+rbx*4]
 xor r8d,r8d
 call glFramebufferTexture2D wrt ..plt
 mov edi,0x8ce0
 call glDrawBuffer wrt ..plt
 mov edi,0x8d40
 call glCheckFramebufferStatus wrt ..plt
 cmp eax,0x8cd5
 jne .cleanup
 inc ebx
 cmp ebx,2
 jb .target
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,0xde1
 xor esi,esi
 call glBindTexture wrt ..plt
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
 call bloom_shutdown
.fail:
 mov eax,-1
 pop rbx
 ret
; EDI scene texture. EAX bloom texture/0disabled. Caller restores full viewport.
; Depth/blend must already be disabled. Three passes, no read/write feedback.
bloom_render:
 push rbx
 push r12
 push r13
 mov r13d,edi
 cmp dword [ready],1
 jne .disabled
 cmp dword [bloom_enabled],0
 je .disabled
 xor edi,edi
 xor esi,esi
 mov edx,[bloom_width]
 mov ecx,[bloom_height]
 call glViewport wrt ..plt
 mov edi,[program]
 call glUseProgram wrt ..plt
 mov edi,[source_loc]
 xor esi,esi
 call glUniform1i wrt ..plt
 mov edi,[vao]
 call glBindVertexArray wrt ..plt
 mov edi,0x84c0
 call glActiveTexture wrt ..plt
 xor r12d,r12d
.pass:
 mov ebx,r12d
 and ebx,1
 lea rax,[bloom_fbos]
 mov esi,[rax+rbx*4]
 mov edi,0x8d40
 call glBindFramebuffer wrt ..plt
 mov edi,0x8ce0
 call glDrawBuffer wrt ..plt
 mov esi,r13d
 test r12d,r12d
 jz .input
 mov ebx,r12d
 dec ebx
 and ebx,1
 lea rax,[bloom_textures]
 mov esi,[rax+rbx*4]
.input:
 mov edi,0xde1
 call glBindTexture wrt ..plt
 mov edi,[pass_loc]
 mov esi,r12d
 call glUniform1i wrt ..plt
 mov edi,4
 xor esi,esi
 mov edx,3
 call glDrawArrays wrt ..plt
 inc dword [bloom_pass_count]
 inc r12d
 cmp r12d,3
 jb .pass
 inc dword [bloom_frame_count]
 mov eax,[bloom_textures]
 jmp .done
.disabled:
 xor eax,eax
.done:
 pop r13
 pop r12
 pop rbx
 ret
bloom_shutdown:
 sub rsp,8
 xor edi,edi
 call glUseProgram wrt ..plt
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,2
 lea rsi,[bloom_fbos]
 call glDeleteFramebuffers wrt ..plt
 mov edi,2
 lea rsi,[bloom_textures]
 call glDeleteTextures wrt ..plt
 mov edi,1
 lea rsi,[vao]
 call glDeleteVertexArrays wrt ..plt
 mov edi,[program]
 test edi,edi
 jz .vertex
 call glDeleteProgram wrt ..plt
.vertex:
 mov edi,[vertex]
 test edi,edi
 jz .fragment
 call glDeleteShader wrt ..plt
.fragment:
 mov edi,[fragment]
 test edi,edi
 jz .clear
 call glDeleteShader wrt ..plt
.clear:
 xor eax,eax
 mov qword [bloom_fbos],rax
 mov qword [bloom_textures],rax
 mov [vao],eax
 mov [program],eax
 mov [vertex],eax
 mov [fragment],eax
 mov [ready],eax
 mov [bloom_width],eax
 mov [bloom_height],eax
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
