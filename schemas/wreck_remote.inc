%ifndef WRECK_REMOTE_INC
%define WRECK_REMOTE_INC
%define WRECK_REMOTE_VERSION 1
%define WRECK_WIRE_STRIDE 68
%define WRECK_WIRE_MAX 17
%define WRECK_PRESENTATION_VERSION 1
%define WRECK_PRESENTATION_FRAME 0
%define WRECK_PRESENTATION_LOD 0
; wreck_receive(RDI payload,ESI bytes multiple68 in[68,1156],EDX source tick)
; ->EAX applied record count, or-1 invalid entire packet (no cache mutation).
; Caller validates endpoint/session/version/header first. Payload slot:u32+record64.
; Immutable pose/identity, duplicate slots rejected, modular tick/sequence guards.
; Equal sequence cannot change immutable fields or resurrect inactive state.
; wreck_remote_expire(EDI latest accepted server tick) clears expired ACTIVE only.
; wreck_remote_reset clears all client records/validity/timestamps/count.
; Dedicated client cache, never authoritative sim_wrecks/hash, no allocation.
%endif
