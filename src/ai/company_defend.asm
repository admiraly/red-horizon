; Read-only physical defense destinations, independent of enemy ground truth.
%include "schemas/company_control.inc"
%include "schemas/entity.inc"
default rel
extern company_follow_place
section .rodata
margin: dd COMPANY_DEFEND_MARGIN
maximum: dd COMPANY_DEFEND_MAX_ANCHOR
base: dd COMPANY_DEFEND_RADIUS
spacing: dd COMPANY_DEFEND_SPACING
back: dd COMPANY_DEFEND_ARTY_BACK
half_columns: dd 3.5
; Clockwise stable octants; spacing is at least18m even on the inner ring.
directions: dd 1.0,0.0, 0.7071067812,0.7071067812, 0.0,1.0, -0.7071067812,0.7071067812
 dd -1.0,0.0, -0.7071067812,-0.7071067812, 0.0,-1.0, 0.7071067812,-0.7071067812
section .text
global company_defend_anchor,company_defend_goal
; XMM0/1 validated accepted waypoint -> effective formation anchor. No writes.
company_defend_anchor:
 maxss xmm0,[margin]
 minss xmm0,[maximum]
 maxss xmm1,[margin]
 minss xmm1,[maximum]
 ret
; EDI stable actor ID, RDX validated own ground entity, XMM0/1 waypoint.
; Return0 terrain-valid movement goal or1 hold if bounded projection fails.
; Caller has already checked ownership, generation, lifetime and raw point.
company_defend_goal:
 ; Inline clamp avoids a call and leaves caller's actor pointer intact.
 maxss xmm0,[margin]
 minss xmm0,[maximum]
 maxss xmm1,[margin]
 minss xmm1,[maximum]
 mov eax,edi
 and eax,127
 mov ecx,eax
 shr eax,3
 and ecx,7
 cvtsi2ss xmm2,eax
 mulss xmm2,[spacing]
 cmp dword [rdx+ENTITY_KIND],2
 je .artillery
 addss xmm2,[base]
 lea rax,[directions]
 movss xmm3,[rax+rcx*8]
 mulss xmm3,xmm2
 addss xmm0,xmm3
 movss xmm3,[rax+rcx*8+4]
 mulss xmm3,xmm2
 addss xmm1,xmm3
 jmp .place
.artillery:
 ; Artillery stays behind the perimeter rather than occupying its near ring.
 addss xmm2,[back]
 cmp dword [rdx+ENTITY_SIDE],0
 jne .east
 subss xmm0,xmm2
 jmp .lateral
.east:
 addss xmm0,xmm2
.lateral:
 cvtsi2ss xmm2,ecx
 subss xmm2,[half_columns]
 mulss xmm2,[spacing]
 addss xmm1,xmm2
.place:
 mov edi,[rdx+ENTITY_KIND]
 jmp company_follow_place
section .note.GNU-stack noalloc noexec nowrite progbits
