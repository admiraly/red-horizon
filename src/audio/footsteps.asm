; Frame-thread recorded local footfall router; no simulation writes or allocation.
; Uses validated movement grounded sidecar locally; network-only poses fall
; back to consecutive narrow terrain-relative standing/crouch baselines.
default rel
%include "schemas/player.inc"
extern sim_players,sim_player_vehicle,player_motion,terrain_height,audio_emit_kind
section .rodata
zero: dd 0.0
max_dt: dd 0.25
standing: dd 1.8
crouched: dd 1.1
tolerance: dd 0.04
max_delta2: dd 9.0
stride: dd 1.8
gain: dd 0.7
align 16
abs_mask: dd 0x7fffffff,0x7fffffff,0x7fffffff,0x7fffffff
world_max: dd 8000.0
section .data
selected: dd -1
section .bss align=16
previous: resd PLAYER_CAPACITY*4 ; x,z,generation,valid
travel: resd PLAYER_CAPACITY
global audio_footsteps_emitted
audio_footsteps_emitted: resq 1
section .text
global audio_footsteps_update,audio_footsteps_reset
; reset() clears cosmetic baselines and diagnostics only; call off update.
audio_footsteps_reset:
 lea rdi,[previous]
 xor eax,eax
 mov ecx,PLAYER_CAPACITY*5
 rep stosd
 mov dword [selected],-1
 mov qword [audio_footsteps_emitted],0
 ret
; update(EDI local player0..3,XMM0 render elapsed seconds)->void.
; Invalid/nonpositive dt resets local baseline; finite dt capped0.25s.
; Actual planar motion accumulates1.8m per footfall across frames (not timer).
; Joining/recycling, teleport>3m, death, airborne, vehicle, stance mismatch
; resets accumulated travel. At most2 emits/update in shared128voice pool.
; Preserves SysV nonvolatile registers; volatile GPR/XMM clobbered.
audio_footsteps_update:
 cmp edi,PLAYER_CAPACITY
 jae .return
 push rbx
 push r12
 push r13
 push r14
 sub rsp,8
 mov r12d,edi
 lea rbx,[sim_players]
 mov eax,edi
 shl eax,6
 add rbx,rax
 lea r13,[previous]
 mov eax,edi
 shl eax,4
 add r13,rax
 cmp edi,[selected]
 je .same
 mov [selected],edi
 mov dword [r13+12],0
.same:
 ucomiss xmm0,[zero]
 jp .invalid
 jbe .invalid
 ucomiss xmm0,[max_dt]
 jp .invalid
 ; Positive infinity is invalid rather than clipped.
 movd eax,xmm0
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .invalid
 minss xmm0,[max_dt]
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .invalid
 cmp dword [rbx+PLAYER_HP],0
 jle .invalid
 cmp dword [rbx+PLAYER_GENERATION],0
 je .invalid
 lea rax,[sim_player_vehicle]
 cmp dword [rax+r12*4],-1
 jne .invalid
 lea rax,[player_motion]
 mov edx,r12d
 shl edx,5
 add rax,rdx
 cmp dword [rax+20],1
 jne .height
 mov edx,[rbx+PLAYER_GENERATION]
 cmp [rax+8],edx
 jne .height
 cmp dword [rax+16],1
 jne .invalid
.height:
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 ucomiss xmm0,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[world_max]
 ja .invalid
 ucomiss xmm1,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[world_max]
 ja .invalid
 call terrain_height
 movss xmm1,[rbx+PLAYER_Y]
 subss xmm1,xmm0
 movaps xmm2,xmm1
 subss xmm2,[standing]
 andps xmm2,[abs_mask]
 ucomiss xmm2,[tolerance]
 jp .invalid
 jbe .ground
 subss xmm1,[crouched]
 andps xmm1,[abs_mask]
 ucomiss xmm1,[tolerance]
 jp .invalid
 ja .invalid
.ground:
 mov eax,[rbx+PLAYER_GENERATION]
 cmp eax,[r13+8]
 jne .baseline
 cmp dword [r13+12],1
 jne .baseline
 movss xmm0,[rbx+PLAYER_X]
 subss xmm0,[r13]
 mulss xmm0,xmm0
 movss xmm1,[rbx+PLAYER_Z]
 subss xmm1,[r13+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[max_delta2]
 ja .baseline
 sqrtss xmm0,xmm0
 lea rax,[travel]
 addss xmm0,[rax+r12*4]
 movss [rax+r12*4],xmm0
 ; Store baseline before calls; emit cannot affect observed motion.
 call .save_position
 xor r14d,r14d
.emit:
 lea rax,[travel]
 movss xmm0,[rax+r12*4]
 ucomiss xmm0,[stride]
 jb .done
 subss xmm0,[stride]
 movss [rax+r12*4],xmm0
 mov edi,2
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Y]
 movss xmm2,[rbx+PLAYER_Z]
 movss xmm3,[gain]
 call audio_emit_kind
 test eax,eax
 jnz .next
 inc qword [audio_footsteps_emitted]
.next:
 inc r14d
 cmp r14d,2
 jb .emit
 jmp .done
.invalid:
 mov dword [r13+12],0
 lea rax,[travel]
 mov dword [rax+r12*4],0
 jmp .done
.baseline:
 lea rax,[travel]
 mov dword [rax+r12*4],0
 call .save_position
.done:
 add rsp,8
 pop r14
 pop r13
 pop r12
 pop rbx
.return:
 ret
.save_position:
 mov eax,[rbx+PLAYER_X]
 mov [r13],eax
 mov eax,[rbx+PLAYER_Z]
 mov [r13+4],eax
 mov eax,[rbx+PLAYER_GENERATION]
 mov [r13+8],eax
 mov dword [r13+12],1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
