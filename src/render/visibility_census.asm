; Optional final-frame opaque-world census. SysV AMD64 / GL 4.5.
; All public hooks preserve callee-saved registers. Only private cosmetic state
; is written. Init needs a current context; shutdown before context destruction.
; begin/end/finish assume the client's normal default framebuffer state.
; reduce(RDI uint32 pixels, ESI count) -> EAX 0/-1, max 3840*2160 words.
; Zero is background. Bits 0..15 = actor index+1, bits 16..17 = detail 1/2/3.
; Invalid inputs reset counters and fail without dereferencing pixel memory.
default rel
%include "schemas/entity.inc"
%define MAX_PIXELS (3840*2160)
extern view_width,view_height,sim_count,sim_tick_count,sim_entities
extern glGenFramebuffers,glBindFramebuffer,glDeleteFramebuffers,glCheckFramebufferStatus
extern glGenTextures,glBindTexture,glTexStorage2D,glDeleteTextures,glFramebufferTexture2D
extern glGenRenderbuffers,glBindRenderbuffer,glRenderbufferStorage,glFramebufferRenderbuffer,glDeleteRenderbuffers
extern glDrawBuffers,glClearBufferfv,glClearBufferuiv,glClear,glColorMaski,glDepthMask
extern glReadBuffer,glDrawBuffer,glReadPixels,glBlitFramebuffer,glPixelStorei
extern clock_gettime,printf,fopen,fwrite,fclose,sim_checksum
section .rodata
map_mode: db "wb",0
buffers: dd 0x8ce0,0x8ce1
clear_color: dd 0.34,0.42,0.46,1.0
zero: dd 0
million: dq 1000000.0
format: db '{"visibility_census":true,"visible_actors":%u,"visible_high":%u,"visible_low":%u,"visible_markers":%u,"individually_detailed_actors":%u,"width":%u,"height":%u,"source_tick":%u,"invalid_codes":%u,"readback_reduce_ms":%.6f,"scope":"opaque world depth before translucent cosmetics and HUD; opaque weapon occlusion included","authority_readonly":true,"authority_before":"%016lx","authority_after":"%016lx"}',10,0
global visibility_pixels,visibility_actor_flags,visibility_width,visibility_height,visibility_capture_count
section .bss
visibility_capture_count: resd 1
fbo: resd 1
textures: resd 2
depth: resd 1
ready: resd 1
active: resd 1
visibility_width: resd 1
visibility_height: resd 1
frame_tick: resd 1
started: resq 2
finished: resq 2
elapsed: resq 1
authority_before: resq 1
authority_after: resq 1
global visibility_actors,visibility_high,visibility_low,visibility_markers,visibility_models,visibility_invalid
visibility_actors: resd 1
visibility_high: resd 1
visibility_low: resd 1
visibility_markers: resd 1
visibility_models: resd 1
visibility_invalid: resd 1
visibility_actor_flags: resb ENTITY_CAPACITY
alignb 16
visibility_pixels: resd MAX_PIXELS
section .text
global visibility_write_map
global visibility_init,visibility_begin,visibility_world_end,visibility_finish,visibility_report,visibility_shutdown,visibility_reduce
visibility_reduce:
 push rbx
 push r12
 mov r12,rdi
 mov ebx,esi
 xor eax,eax
 lea rdi,[visibility_actors]
 mov ecx,6
 rep stosd
 lea rdi,[visibility_actor_flags]
 mov ecx,ENTITY_CAPACITY
 rep stosb
 cmp ebx,MAX_PIXELS
 ja .bad
 test ebx,ebx
 jz .ok
 test r12,r12
 jz .bad
 mov r8d,[sim_count]
 cmp r8d,ENTITY_CAPACITY
 ja .bad
 lea r9,[sim_entities]
 lea r10,[visibility_actor_flags]
.loop:
 mov eax,[r12]
 add r12,4
 test eax,eax
 jz .next
 test eax,0xfffc0000
 jnz .invalid
 mov edx,eax
 shr edx,16
 test edx,edx
 jz .invalid
 and eax,65535
 test eax,eax
 jz .invalid
 dec eax
 cmp eax,r8d
 jae .invalid
 mov ecx,eax
 shl ecx,5
 cmp dword [r9+rcx+ENTITY_HP],0
 jle .invalid
 cmp dword [r9+rcx+ENTITY_SIDE],1
 ja .invalid
 cmp dword [r9+rcx+ENTITY_KIND],3
 ja .invalid
 cmp dword [r9+rcx+ENTITY_GENERATION],0
 je .invalid
 movzx esi,byte [r10+rax]
 test esi,esi
 jnz .has_actor
 inc dword [visibility_actors]
.has_actor:
 mov ecx,edx
 dec ecx
 mov edi,1
 shl edi,cl
 test esi,edi
 jnz .next
 cmp edx,1
 jne .not_high
 inc dword [visibility_high]
 jmp .model
.not_high:
 cmp edx,2
 jne .marker
 inc dword [visibility_low]
.model:
 test esi,3
 jnz .save
 inc dword [visibility_models]
 jmp .save
.marker:
 inc dword [visibility_markers]
.save:
 or esi,edi
 mov [r10+rax],sil
 jmp .next
.invalid:
 inc dword [visibility_invalid]
.next:
 dec ebx
 jnz .loop
.ok:
 xor eax,eax
 jmp .exit
.bad:
 mov eax,-1
.exit:
 pop r12
 pop rbx
 ret

visibility_init:
 push rbx
 cmp dword [ready],0
 jne .success
 mov eax,[view_width]
 cmp eax,320
 jb .fail
 cmp eax,3840
 ja .fail
 mov [visibility_width],eax
 mov eax,[view_height]
 cmp eax,240
 jb .fail
 cmp eax,2160
 ja .fail
 mov [visibility_height],eax
 mov edi,1
 lea rsi,[fbo]
 call glGenFramebuffers wrt ..plt
 mov edi,0x8d40
 mov esi,[fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,2
 lea rsi,[textures]
 call glGenTextures wrt ..plt
 xor ebx,ebx
.texture:
 mov edi,0x0de1
 lea rax,[textures]
 mov esi,[rax+rbx*4]
 call glBindTexture wrt ..plt
 mov edi,0x0de1
 mov esi,1
 mov edx,0x8058 ; RGBA8
 test ebx,ebx
 jz .storage
 mov edx,0x8236 ; R32UI
.storage:
 mov ecx,[visibility_width]
 mov r8d,[visibility_height]
 call glTexStorage2D wrt ..plt
 mov edi,0x8d40
 lea esi,[rbx+0x8ce0]
 mov edx,0x0de1
 lea rax,[textures]
 mov ecx,[rax+rbx*4]
 xor r8d,r8d
 call glFramebufferTexture2D wrt ..plt
 inc ebx
 cmp ebx,2
 jb .texture
 mov edi,1
 lea rsi,[depth]
 call glGenRenderbuffers wrt ..plt
 mov edi,0x8d41
 mov esi,[depth]
 call glBindRenderbuffer wrt ..plt
 mov edi,0x8d41
 mov esi,0x81a6 ; DEPTH_COMPONENT24
 mov edx,[visibility_width]
 mov ecx,[visibility_height]
 call glRenderbufferStorage wrt ..plt
 mov edi,0x8d40
 mov esi,0x8d00
 mov edx,0x8d41
 mov ecx,[depth]
 call glFramebufferRenderbuffer wrt ..plt
 mov edi,2
 lea rsi,[buffers]
 call glDrawBuffers wrt ..plt
 mov edi,0x8d40
 call glCheckFramebufferStatus wrt ..plt
 cmp eax,0x8cd5
 jne .cleanup
 mov dword [ready],1
 call .unbind
.success:
 xor eax,eax
 pop rbx
 ret
.cleanup:
 call visibility_shutdown
.fail:
 mov eax,-1
 pop rbx
 ret
.unbind:
 sub rsp,8
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,0x0de1
 xor esi,esi
 call glBindTexture wrt ..plt
 mov edi,0x8d41
 xor esi,esi
 call glBindRenderbuffer wrt ..plt
 add rsp,8
 ret
visibility_begin:
 sub rsp,8
 cmp dword [ready],1
 jne .done
 mov edi,0x8d40
 mov esi,[fbo]
 call glBindFramebuffer wrt ..plt
 mov edi,2
 lea rsi,[buffers]
 call glDrawBuffers wrt ..plt
 xor edi,edi
 call mask_on
 mov edi,1
 call mask_on
 mov edi,0x1800
 xor esi,esi
 lea rdx,[clear_color]
 call glClearBufferfv wrt ..plt
 mov edi,0x1800
 mov esi,1
 lea rdx,[zero]
 call glClearBufferuiv wrt ..plt
 mov edi,1
 call glDepthMask wrt ..plt
 mov edi,0x100
 call glClear wrt ..plt
 mov eax,[sim_tick_count]
 mov [frame_tick],eax
 call sim_checksum
 mov [authority_before],rax
 mov dword [active],1
.done:
 add rsp,8
 ret
mask_on:
 mov esi,1
 mov edx,1
 mov ecx,1
 mov r8d,1
 jmp glColorMaski wrt ..plt
visibility_world_end:
 sub rsp,8
 cmp dword [active],1
 jne .done
 mov edi,1
 xor esi,esi
 xor edx,edx
 xor ecx,ecx
 xor r8d,r8d
 call glColorMaski wrt ..plt
.done:
 add rsp,8
 ret
visibility_finish:
 sub rsp,40
 cmp dword [active],1
 jne .done
 mov edi,1
 lea rsi,[started]
 call clock_gettime wrt ..plt
 mov edi,0x8ce1
 call glReadBuffer wrt ..plt
 mov edi,0x0d05 ; PACK_ALIGNMENT
 mov esi,4
 call glPixelStorei wrt ..plt
 xor edi,edi
 xor esi,esi
 mov edx,[visibility_width]
 mov ecx,[visibility_height]
 mov r8d,0x8d94 ; RED_INTEGER
 mov r9d,0x1405 ; UNSIGNED_INT
 lea rax,[visibility_pixels]
 mov [rsp],rax
 call glReadPixels wrt ..plt
 lea rdi,[visibility_pixels]
 mov esi,[visibility_width]
 imul esi,[visibility_height]
 call visibility_reduce
 mov edi,1
 lea rsi,[finished]
 call clock_gettime wrt ..plt
 mov rax,[finished]
 sub rax,[started]
 imul rax,1000000000
 add rax,[finished+8]
 sub rax,[started+8]
 cvtsi2sd xmm0,rax
 divsd xmm0,[million]
 movsd [elapsed],xmm0
 mov edi,0x8ce0
 call glReadBuffer wrt ..plt
 mov edi,0x8ca9 ; DRAW_FRAMEBUFFER
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,0x0405 ; BACK
 call glDrawBuffer wrt ..plt
 xor edi,edi
 xor esi,esi
 mov edx,[visibility_width]
 mov ecx,[visibility_height]
 xor r8d,r8d
 xor r9d,r9d
 mov eax,[visibility_width]
 mov [rsp],rax
 mov eax,[visibility_height]
 mov [rsp+8],rax
 mov qword [rsp+16],0x4000
 mov qword [rsp+24],0x2600
 call glBlitFramebuffer wrt ..plt
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,0x0405
 call glReadBuffer wrt ..plt
 mov edi,0x0405
 call glDrawBuffer wrt ..plt
 mov edi,1
 call mask_on
 mov dword [active],0
 call sim_checksum
 mov [authority_after],rax
 inc dword [visibility_capture_count]
.done:
 add rsp,40
 ret
visibility_report:
 sub rsp,56
 cmp dword [ready],1
 jne .done
 lea rdi,[format]
 mov esi,[visibility_actors]
 mov edx,[visibility_high]
 mov ecx,[visibility_low]
 mov r8d,[visibility_markers]
 mov r9d,[visibility_models]
 mov eax,[visibility_width]
 mov [rsp],rax
 mov eax,[visibility_height]
 mov [rsp+8],rax
 mov eax,[frame_tick]
 mov [rsp+16],rax
 mov eax,[visibility_invalid]
 mov [rsp+24],rax
 mov rax,[authority_before]
 mov [rsp+32],rax
 mov rax,[authority_after]
 mov [rsp+40],rax
 movsd xmm0,[elapsed]
 mov eax,1
 call printf wrt ..plt
.done:
 add rsp,56
 ret
visibility_shutdown:
 sub rsp,8
 mov edi,0x8d40
 xor esi,esi
 call glBindFramebuffer wrt ..plt
 mov edi,1
 lea rsi,[fbo]
 call glDeleteFramebuffers wrt ..plt
 mov edi,2
 lea rsi,[textures]
 call glDeleteTextures wrt ..plt
 mov edi,1
 lea rsi,[depth]
 call glDeleteRenderbuffers wrt ..plt
 xor eax,eax
 mov [fbo],eax
 mov [textures],rax
 mov [depth],eax
 mov [ready],eax
 mov [active],eax
 add rsp,8
 ret
; write_map(RDI path/null) -> EAX 0/-1; writes captured native little-endian
; R32UI words, no header. Dimensions and source tick are in census JSON.
visibility_write_map:
 push rbx
 push r12
 sub rsp,8
 test rdi,rdi
 jz .ok
 cmp dword [visibility_capture_count],0
 je .fail
 lea rsi,[map_mode]
 call fopen wrt ..plt
 test rax,rax
 jz .fail
 mov rbx,rax
 lea rdi,[visibility_pixels]
 mov esi,4
 mov edx,[visibility_width]
 imul edx,[visibility_height]
 mov r12d,edx
 mov rcx,rbx
 call fwrite wrt ..plt
 cmp rax,r12
 sete r12b
 mov rdi,rbx
 call fclose wrt ..plt
 test eax,eax
 jnz .fail
 test r12b,r12b
 jz .fail
.ok:
 xor eax,eax
 jmp .done
.fail:
 mov eax,-1
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
