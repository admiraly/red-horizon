; Root-owned intermediate-pose terrain contact ABI v1, cosmetic only.
%ifndef GROUND_CONTACT_INC
%define GROUND_CONTACT_INC
%include "schemas/ground_support.inc"
%define CONTACT_VERSION 1
; ground_contact(RDI writable support64,ESI kind1/2,EDX capacity>=64,
; XMM0 entity X,XMM1 entity Z,XMM2 heading[-pi,pi],
; XMM3 pitch[-pi/2,pi/2],XMM4 bank[-pi/2,pi/2]) -> EAX0/-1.
; Finite XZ[0,8000], finite angles. Output unchanged on invalid.
; Exact yaw*pitch*bank frame; same SUPPORT_* chassis rectangle, local Y=0.
; Rotate local corners (+-width,0,centerZ+-length) using full frame.
; Validate all projected corner XZ on map BEFORE any terrain query.
; Output Y=max(terrain_height(entity center), terrain_height(corner XZ)
; minus rotated corner localY for all four corners). Output pitch/bank
; are supplied angles, flags SUPPORT_VALID, right/up/forward vec4 w=+0.
; Exactly five terrain calls on valid input, zero on invalid coordinates.
; Validate finite samples/output before one publication phase.
; No global writes, no authoritative state/collision changes, no allocation.
; SysV nonvolatile GPRs preserved and external calls aligned.
; Platform sinf/cosf permitted; CPU runtime implementation NASM/SSE2.
; Five-point contact floor only; entire mesh clearance is NOT guaranteed.
%endif
