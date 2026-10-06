; Finite physical depot stores; prerequisite, not yet hooked into world.
%include "schemas/depot_ammunition.inc"
default rel
extern sim_sites
section .bss align=64
global depot_ammunition
depot_ammunition: resb DEPOT_AMMUNITION_SITES*DEPOT_AMMUNITION_STRIDE
section .text
global depot_ammunition_init,depot_ammunition_take,depot_ammunition_hash
; Explicit fresh-operation init only. Clobbers caller-saved GPRs, no calls.
; Depot role1 starts with declared finite stock. Capture/repair cannot reset it.
depot_ammunition_init:
 lea rdi,[depot_ammunition]
 xor eax,eax
 mov ecx,DEPOT_AMMUNITION_SITES*DEPOT_AMMUNITION_STRIDE/8
 rep stosq
 lea rdx,[sim_sites]
 lea r8,[depot_ammunition]
 mov ecx,DEPOT_AMMUNITION_SITES
.loop:
 cmp dword [rdx+16],1
 jne .next
 cmp dword [rdx+8],1
 ja .next
 mov dword [r8],DEPOT_AMMUNITION_INITIAL
 mov dword [r8+8],DEPOT_AMMUNITION_INITIAL
.next:
 add rdx,32
 add r8,DEPOT_AMMUNITION_STRIDE
 dec ecx
 jnz .loop
 xor eax,eax
 ret
; EDI site,ESI own side,EDX requested rounds1..90 ->EAX taken0..90,
; or-1 malformed identity/request/store. Valid unavailable sources return0.
; Caller must validate living actor, proximity and capacity BEFORE this debit.
; Atomic leaf, no credit/actor mutation; preserves every nonvolatile register.
depot_ammunition_take:
 cmp edi,DEPOT_AMMUNITION_SITES
 jae .invalid
 cmp esi,1
 ja .invalid
 test edx,edx
 jz .invalid
 cmp edx,DEPOT_AMMUNITION_MAX_TAKE
 ja .invalid
 mov eax,edi
 shl eax,5
 lea r9,[sim_sites]
 add r9,rax
 shl edi,4
 lea r8,[depot_ammunition]
 add r8,rdi
 cmp dword [r8+8],0
 je .unavailable
 cmp dword [r8+8],DEPOT_AMMUNITION_INITIAL
 jne .invalid
 cmp dword [r8+12],0
 jne .invalid
 cmp dword [r8],DEPOT_AMMUNITION_INITIAL
 ja .invalid
 cmp dword [r8+4],DEPOT_AMMUNITION_INITIAL
 ja .invalid
 mov eax,[r8]
 add eax,[r8+4]
 cmp eax,DEPOT_AMMUNITION_INITIAL
 jne .invalid
 cmp dword [r9+16],1
 jne .unavailable
 cmp [r9+8],esi
 jne .unavailable
 cmp dword [r9+20],0
 je .unavailable
 cmp dword [r9+24],0
 je .unavailable
 test dword [r9+28],4
 jnz .unavailable
 mov eax,[r8]
 cmp eax,edx
 jbe .debit
 mov eax,edx
.debit:
 sub [r8],eax
 add [r8+4],eax
 ret
.unavailable:
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
; RAX hash,R8 FNV prime. No world hook until integration contract is verified.
depot_ammunition_hash:
 lea rsi,[depot_ammunition]
 mov ecx,DEPOT_AMMUNITION_SITES*DEPOT_AMMUNITION_STRIDE
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
