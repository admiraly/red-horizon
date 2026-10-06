; Root-owned read-only terrain-supported legacy driver eye ABI v1.
%ifndef GROUND_EYE_INC
%define GROUND_EYE_INC
%define EYE_VERSION 1
%define EYE_STRIDE 12
%define EYE_LOCAL_HEIGHT 3.0
; ground_eye(RDI writable outXYZ12,ESI kind1/2,EDX capacity>=12,
; XMM0 entity X,XMM1 entity Z,XMM2 stamped hull heading[-pi,pi]) -> EAX0/-1.
; Call unsmoothed ground_support, then ground_contact with its pitch/bank.
; BaseY=max(supportY,contactY); exact support frame right/up/forward.
; World point=(entityX,baseY,entityZ)+EYE_LOCAL_HEIGHT*up.
; The 3m legacy gameplay anchor is retained, NOT a measured cockpit socket.
; Reject nonfinite or out-of-map result XZ or Y outside[-2000,2000].
; Output unchanged on invalid; pointers/capacity ownership as support ABI.
; No global/authority writes, allocations, dt or presentation cache reads.
; Caller validates live entity/player generations, ownership and motion stamp.
; Platform trig used by support/contact; NASM/SSE2 CPU only, SysV preserved.
; This prerequisite does NOT integrate entry/driver/LOS/aim/client camera hooks.
%endif
