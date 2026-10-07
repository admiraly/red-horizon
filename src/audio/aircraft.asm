; Nearest living initialized aircraft engines, same128-voice physical pool.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/audio_aircraft.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,network_mode,net_connected
extern audio_loop_begin,audio_loop_submit,audio_loop_end
section .data
global audio_aircraft_enabled
audio_aircraft_enabled: dd 1
section .bss align=16
global audio_aircraft_selected,audio_aircraft_candidates
audio_aircraft_selected: resd 1
audio_aircraft_candidates: resd 1
ids: resd AUDIO_AIRCRAFT_SOURCES
distances: resd AUDIO_AIRCRAFT_SOURCES
section .rodata
range2: dd AUDIO_AIRCRAFT_RANGE_SQ
gain: dd AUDIO_AIRCRAFT_GAIN
section .text
global audio_aircraft_update
; XMM0/1/2 listenerXYZ. Frame-thread only; full capped army scan,8 source submits.
; Death/cache eviction/disconnect/invalid generation retires next frame.
audio_aircraft_update:
 push rbx
 push r12
 push r13
 sub rsp,16
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 call audio_loop_begin
 mov dword [audio_aircraft_selected],0
 mov dword [audio_aircraft_candidates],0
 lea rdi,[ids]
 mov eax,-1
 mov ecx,AUDIO_AIRCRAFT_SOURCES
 rep stosd
 cmp dword [audio_aircraft_enabled],0
 je .done
 cmp dword [network_mode],0
 je .local
 cmp dword [net_connected],0
 je .done
.local:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .done
 xor r12d,r12d
.scan:
 cmp r12d,[sim_count]
 jae .submit
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .next
 cmp dword [rbx+ENTITY_KIND],3
 jne .next
 cmp dword [rbx+ENTITY_SIDE],1
 ja .next
 mov eax,r12d
 shl eax,6
 lea r13,[sim_aircraft]
 add r13,rax
 mov eax,[rbx+ENTITY_GENERATION]
 test eax,eax
 jz .next
 cmp eax,[r13+AIR_GENERATION]
 jne .next
 test dword [r13+AIR_FLAGS],AIR_ACTIVE
 jz .next
 cmp dword [r13+AIR_ROLE],1
 ja .next
 ; Raw finite bounds also protect distance sort against NaN/Inf.
 mov eax,[rbx+ENTITY_X]
 test eax,eax
 js .next
 cmp eax,__float32__(8000.0)
 ja .next
 mov eax,[rbx+ENTITY_Z]
 test eax,eax
 js .next
 cmp eax,__float32__(8000.0)
 ja .next
 mov eax,[r13+AIR_Y]
 and eax,0x7fffffff
 cmp eax,__float32__(1000.0)
 ja .next
 movss xmm0,[rbx+ENTITY_X]
 subss xmm0,[rsp]
 mulss xmm0,xmm0
 movss xmm1,[r13+AIR_Y]
 subss xmm1,[rsp+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss xmm1,[rbx+ENTITY_Z]
 subss xmm1,[rsp+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[range2]
 jp .next
 jae .next
 inc dword [audio_aircraft_candidates]
 xor ecx,ecx
.find:
 lea rdx,[ids]
 cmp dword [rdx+rcx*4],-1
 je .insert
 lea rdx,[distances]
 ucomiss xmm0,[rdx+rcx*4]
 jb .insert ; ascending scan gives stable ID tie break
 inc ecx
 cmp ecx,AUDIO_AIRCRAFT_SOURCES
 jb .find
 jmp .next
.insert:
 mov edx,AUDIO_AIRCRAFT_SOURCES-1
.shift:
 cmp edx,ecx
 jbe .store
 lea r8,[ids]
 mov eax,[r8+rdx*4-4]
 mov [r8+rdx*4],eax
 lea r8,[distances]
 mov eax,[r8+rdx*4-4]
 mov [r8+rdx*4],eax
 dec edx
 jmp .shift
.store:
 lea rdx,[ids]
 mov [rdx+rcx*4],r12d
 lea rdx,[distances]
 movss [rdx+rcx*4],xmm0
.next:
 inc r12d
 jmp .scan
.submit:
 xor r12d,r12d
.sources:
 lea rdx,[ids]
 mov edi,[rdx+r12*4]
 cmp edi,-1
 je .done
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 shl eax,1
 lea r13,[sim_aircraft]
 add r13,rax
 mov esi,[rbx+ENTITY_GENERATION]
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[r13+AIR_Y]
 movss xmm2,[rbx+ENTITY_Z]
 movss xmm3,[gain]
 call audio_loop_submit
 test eax,eax
 jnz .source_next
 inc dword [audio_aircraft_selected]
.source_next:
 inc r12d
 cmp r12d,AUDIO_AIRCRAFT_SOURCES
 jb .sources
.done:
 call audio_loop_end
 add rsp,16
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
