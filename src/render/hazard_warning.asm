; Local threat HUD adapter, SysV x86-64/SSE2. Authority is strictly read-only.
; update(EDI player slot,XMM0 cameraX,XMM1 cameraY,XMM2 cameraZ,XMM3 yaw).
; Outputs private vec4(active,bearing/pi,ETA seconds,radius metres), zero on failure.
; Clobbers caller-saved registers; preserves callee-saved. No allocation.
default rel
%include "schemas/player.inc"
extern sim_players,hazard_query,sinf,cosf,atan2f
global hazard_warning_update,hazard_warning_uniform,hazard_warning_frames
section .rodata
zero: dd 0.
one: dd 1.
pi: dd 3.14159265358979323846
ticks_second: dd 30.
max_eta: dd 120.
max_radius: dd 512.
section .bss
align 16
hazard_warning_uniform: resd 4
hazard_warning_frames: resq 1
section .text
hazard_warning_update:
 push rbx
 sub rsp,48
 xorps xmm4,xmm4
 movaps [hazard_warning_uniform],xmm4
 cmp edi,PLAYER_CAPACITY
 jae .done
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .done
 cmp dword [rbx+PLAYER_HP],0
 jle .done                       ; authoritative HP is signed integer
 ; Validate all camera components including yaw before calling perception.
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 xor ecx,ecx
.validate_camera:
 mov eax,[rsp+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .done
 inc ecx
 cmp ecx,4
 jb .validate_camera
 xor edi,edi                     ; humans belong to allied side zero
 call hazard_query
 test eax,eax
 js .done
 movss [rsp+16],xmm0
 movss [rsp+20],xmm1
 movss [rsp+24],xmm2
 movss [rsp+28],xmm3
 xor ecx,ecx
.validate_threat:
 mov eax,[rsp+16+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .done
 inc ecx
 cmp ecx,4
 jb .validate_threat
 comiss xmm2,[zero]
 jbe .done
 comiss xmm3,[zero]
 jb .done
 movss xmm0,[rsp+12]
 call sinf wrt ..plt
 movss [rsp+32],xmm0
 movss xmm0,[rsp+12]
 call cosf wrt ..plt
 ; Rotate impact displacement into camera space. This avoids wrap loops on
 ; arbitrarily large but finite yaw and matches battle.vert's camera transform.
 movss xmm1,[rsp+16]
 subss xmm1,[rsp]
 movss xmm2,[rsp+20]
 subss xmm2,[rsp+8]
 movaps xmm3,xmm1
 mulss xmm3,xmm0
 movaps xmm4,xmm2
 mulss xmm4,[rsp+32]
 subss xmm3,xmm4                  ; camera-right displacement
 mulss xmm1,[rsp+32]
 mulss xmm2,xmm0
 addss xmm1,xmm2                  ; camera-forward displacement
 movaps xmm0,xmm3
 call atan2f wrt ..plt           ; atan2(right,forward), -pi..pi
 divss xmm0,[pi]
 movd eax,xmm0
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .done                       ; overflowed camera-relative arithmetic
 movss [hazard_warning_uniform+4],xmm0
 movss xmm0,[rsp+28]
 minss xmm0,[max_eta]
 divss xmm0,[ticks_second]
 movss [hazard_warning_uniform+8],xmm0
 movss xmm0,[rsp+24]
 minss xmm0,[max_radius]
 movss [hazard_warning_uniform+12],xmm0
 mov eax,[one]
 mov [hazard_warning_uniform],eax
 inc qword [hazard_warning_frames]
.done:
 add rsp,48
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
