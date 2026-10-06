; Root-owned cosmetic critically damped response ABI v1; NOT integrated.
%ifndef SUSPENSION_INC
%define SUSPENSION_INC
%define SUSPENSION_VERSION 1
%define SUSPENSION_STRIDE 48
%define SUSPENSION_POSITION 0 ; three floats: support Y,pitch,bank
%define SUSPENSION_VELOCITY 12 ; three floats per second
%define SUSPENSION_GENERATION 24
%define SUSPENSION_KIND 28
%define SUSPENSION_TIME 32 ; elapsed cosmetic seconds
%define SUSPENSION_FLAGS 36
%define SUSPENSION_ACTIVE 1
%define SUSPENSION_Y_OMEGA 20.0
%define SUSPENSION_PITCH_OMEGA 16.0
%define SUSPENSION_BANK_OMEGA 18.0
%define SUSPENSION_Y_LIMIT 2000.0
%define SUSPENSION_ANGLE_LIMIT 1.5707963267948966
%define SUSPENSION_Y_VELOCITY_LIMIT 200.0
%define SUSPENSION_ANGLE_VELOCITY_LIMIT 8.0
; suspension_step(RDI state48,RSI target12,EDX nonzero generation,ECX kind1/2,
; R8D capacity>=48,XMM0 finite dt[0,.1])->EAX0/-1 invalid preserving state.
; Caller owns writable state and readable target pointers; null rejects. Copy
; targets before publishing, including when target aliases state positions.
; Finite target Y[-2000,2000], pitch/bank[-pi/2,pi/2]. flags must be0 or1.
; Inactive/stale generation/kind resets positions to target, velocities/time0,
; stamp/flags to valid and padding40/44 canonical0. Do not read stale pos/vel.
; Matching active state validates finite pos/vel inside same bounds and time
; finite[0,86400]. Invalid state/target/dt must preserve EVERY state byte.
; dt0 on matching active state preserves EVERY byte; stale initialization allowed.
; For each axis q=p-target,k=v+omega*q,e=exp(-omega*dt),
; p'=target+(q+k*dt)*e,v'=(v-omega*k*dt)*e (critical damping closed form).
; Clamp each position and velocity to the stated bounds AFTER evaluation.
; Time=min(86400,time+dt), stamp/flags unchanged, padding40/44 canonical0.
; SSE2, existing platform libm expf allowed, SysV nonvolatiles/call alignment.
; Writes only caller-provided derived presentation state, no authority/allocations.
; This kernel does NOT ensure terrain clearance for intermediate angles; root
; must recompute support height/contact for the smoothed frame before rendering.
%endif
