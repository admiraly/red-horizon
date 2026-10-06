%ifndef WORLD_BODY_INC
%define WORLD_BODY_INC
%define WORLD_BODY_VERSION 1
; Ground-only composition, roles0/1/2 at original swept radii.
; world_body_path_clear(EDI role,XMM0..3 startXZ/endXZ)->EAX1clear/0blocked.
; world_body_blocked(EDI role,XMM0/1 XZ)->EAX1blocked/0clear (zero motion).
; Explicit *_context: EDI role,RSI stable1024x64wreck records,EDX active count,
; RCX derived revision. Identical revisions across distinct sources stay distinct.
; Terrain body/map/grade validation and planar wreck query; faults block.
; Wreck start overlap may escape only by the query's non-deepening rule;
; zero-motion occupation still blocks. All sources/authority are readonly.
; world_body_step[_context]: same context + XMM0/1 startXZ,
; XMM2/3 manual goalXZ,XMM4 requestedstep ->XMM0/1 actual candidate endpoint.
; Original terrain manual actuator, then complete and X/Z component sweeps.
; No autonomous detour, touch-distance clipping or vehicle pose application.
; Gameplay hooks use actual fragment sweeps; wreck_nav is a separate proposal
; policy. Connected foot preview selects the admitted remote source explicitly.
%endif
