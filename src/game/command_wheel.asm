; Pure bounded client command selection/terrain ray. No authority writes.
default rel
extern terrain_height,terrain_los
section .rodata
align 16
absolute_mask: dd 0x7fffffff,0x7fffffff,0x7fffffff,0x7fffffff
zero: dd 0.0
one: dd 1.0
maximum: dd 8000.0
height_limit: dd 10000.0
norm_min: dd 0.99
norm_max: dd 1.01
deadzone_squared: dd 1444.0
step: dd 4.0
half: dd 0.5
surface_margin: dd 0.05
section .text
global command_wheel_select,command_terrain_point
; XMM0/1 finite screen dx/dy -> EAX mode0move,1hold,2retreat,3follow;
; -1 center/cancel. Screen Y grows down. Boundary ties favor vertical.
command_wheel_select:
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 andps xmm2,[absolute_mask]
 andps xmm3,[absolute_mask]
 ucomiss xmm2,[height_limit]
 jp .none
 ja .none
 ucomiss xmm3,[height_limit]
 jp .none
 ja .none
 movaps xmm4,xmm2
 movaps xmm5,xmm3
 mulss xmm4,xmm4
 mulss xmm5,xmm5
 addss xmm4,xmm5
 comiss xmm4,[deadzone_squared]
 jb .none
 comiss xmm2,xmm3
 ja .horizontal
 xor eax,eax
 comiss xmm1,[zero]
 jb .done
 mov eax,2
 ret
.horizontal:
 mov eax,1
 comiss xmm0,[zero]
 jb .done
 mov eax,3
.done: ret
.none: mov eax,-1
 ret

; RDI -> six finite floats: originXYZ, normalized directionXYZ.
; EAX0/XMM0X/XMM1Z first terrain intersection; -1 no visible bounded hit.
; 512 four-metre steps (2,048m), then12 bisections. Exact authored static-solid
; slab LOS rejects a point hidden by a wall. The terrain height query uses the
; same world as authority. Calls preserve GPR ABI and use private stack scratch.
command_terrain_point:
 push rbx
 sub rsp,80
 mov rbx,rdi
 xor ecx,ecx
.validate:
 movss xmm0,[rbx+rcx*4]
 andps xmm0,[absolute_mask]
 ucomiss xmm0,[height_limit]
 jp .miss
 ja .miss
 movss [rsp+rcx*4],xmm0
 inc ecx
 cmp ecx,6
 jb .validate
 ; Preserve signed inputs after finite validation.
 movups xmm0,[rbx]
 movups [rsp],xmm0
 movq xmm0,[rbx+16]
 movq [rsp+16],xmm0
 movss xmm0,[rsp]
 comiss xmm0,[zero]
 jb .miss
 comiss xmm0,[maximum]
 ja .miss
 movss xmm1,[rsp+8]
 comiss xmm1,[zero]
 jb .miss
 comiss xmm1,[maximum]
 ja .miss
 movss xmm2,[rsp+12]
 mulss xmm2,xmm2
 movss xmm3,[rsp+16]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 movss xmm3,[rsp+20]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[norm_min]
 jb .miss
 comiss xmm2,[norm_max]
 ja .miss
 call terrain_height
 comiss xmm0,[rsp+4]
 jae .miss
 mov dword [rsp+24],0 ; previous positive ray distance
 mov dword [rsp+28],0 ; current ray distance
 mov ebx,512
.advance:
 movss xmm0,[rsp+28]
 movss [rsp+24],xmm0
 addss xmm0,[step]
 movss [rsp+28],xmm0
 call .sample
 test eax,eax
 js .miss
 test eax,eax
 jz .refine
 dec ebx
 jnz .advance
 jmp .miss
.refine:
 mov ebx,12
.bisect:
 movss xmm0,[rsp+24]
 addss xmm0,[rsp+28]
 mulss xmm0,[half]
 movss [rsp+32],xmm0
 call .sample
 test eax,eax
 js .miss
 movss xmm0,[rsp+32]
 jz .lower
 movss [rsp+24],xmm0
 jmp .next
.lower:
 movss [rsp+28],xmm0
.next:
 dec ebx
 jnz .bisect
 ; Re-sample final distance for finite hit coordinates and exact height.
 movss xmm0,[rsp+28]
 call .sample
 test eax,eax
 js .miss
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+36]
 movss xmm4,[rsp+48]
 addss xmm4,[surface_margin]
 movss xmm5,[rsp+44]
 call terrain_los
 test eax,eax
 jz .miss
 movss xmm0,[rsp+36]
 movss xmm1,[rsp+44]
 xor eax,eax
 jmp .done
.miss:
 mov eax,-1
.done:
 add rsp,80
 pop rbx
 ret
; XMM0 distance, private parent scratch ->1 above,0 at/below,-1 out of map.
.sample:
 ; Called from an aligned parent; private helper uses caller scratch at+8.
 movss xmm2,[rsp+8+12]
 mulss xmm2,xmm0
 addss xmm2,[rsp+8]
 movss [rsp+8+36],xmm2
 movss xmm3,[rsp+8+16]
 mulss xmm3,xmm0
 addss xmm3,[rsp+8+4]
 movss [rsp+8+40],xmm3
 movss xmm1,[rsp+8+20]
 mulss xmm1,xmm0
 addss xmm1,[rsp+8+8]
 movss [rsp+8+44],xmm1
 movaps xmm0,xmm2
 comiss xmm0,[zero]
 jb .outside
 comiss xmm0,[maximum]
 ja .outside
 comiss xmm1,[zero]
 jb .outside
 comiss xmm1,[maximum]
 ja .outside
 sub rsp,8
 call terrain_height
 add rsp,8
 movss [rsp+8+48],xmm0
 xor eax,eax
 comiss xmm0,[rsp+8+40]
 setb al
 ret
.outside:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
