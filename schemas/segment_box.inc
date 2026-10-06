; Prepared read-only finite3D swept point/AABB clip, SysV/SSE2 v1.
%ifndef SEGMENT_BOX_INC
%define SEGMENT_BOX_INC
%define SEGMENT_BOX_VERSION 1
%define SEGMENT_BOX_BYTES 24
%define SEGMENT_BOX_COORD_LIMIT 16000.0
; segment_box(RDI caller-owned box24 minXYZ/maxXYZ,ESI bytes>=24,
; XMM0/1/2 startXYZ,XMM3/4/5 endXYZ)->EAX1hit,0clear,-1invalid.
; Hit returns first t in XMM0 float32 in[0,1]. Non-hit preserves originalXMM0.
; Closed faces/edges: grazing and start-inside are hits, including zero motion.
; Box minima<=maxima; all12coords finite within+-16000. Capacity/null rejects
; before pointer reads. No writes, heap, global scratch or external calls.
; Exact f32 inputs convert to double before differences/division (SSE2).
; Preserves SysV nonvolatile GPRs/stack; caller-saved GPR/XMM scratch.
; This primitive alone is NOT registry spatial search, physical wreck cover,
; oriented hull/mesh contact, renderer or network integration.
%endif
