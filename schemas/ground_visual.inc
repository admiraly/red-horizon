; Root-owned generation-safe derived ground presentation cache ABI v1.
%ifndef GROUND_VISUAL_INC
%define GROUND_VISUAL_INC
%include "schemas/suspension.inc"
%define VISUAL_VERSION 1
%define VISUAL_STRIDE 64
%define VISUAL_FRAME 48
%define VISUAL_X 52
%define VISUAL_Z 56
%define VISUAL_MAX_DT 0.1
%define VISUAL_JUMP_SQ 16.0
; ground_visual(RDI writable cache64,RSI writable support64,EDX generation>0,
; ECX kind1/2,R8D nonzero render frame,XMM0 X,XMM1 Z,XMM2 heading,XMM3 dt)
; -> EAX0/-1. Cache starts zero. Authoritative data is NEVER written.
; Support and contact validate coordinates/angles. Finite dt>=0 required.
; On failure output unchanged, cache active flag cleared to prevent stale reuse.
; Consecutive frames damp; skipped frames, dt>.1, displacement>4m reset.
; Generation/kind mismatch resets through suspension_step. Same-frame identical
; pose query reuses the spring, preventing multiple LOD draws advancing time.
; Smoothed pitch/bank determine exact rotated contact floor. Raise Y to floor;
; cancel downward Y velocity when raised. Cache and output Y agree.
; Store last frame/XZ only after success; reserved cache word60 canonical0.
; Five-point support and five-point contact, NOT whole-mesh physical collision.
%endif
