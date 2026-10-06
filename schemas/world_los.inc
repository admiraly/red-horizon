%ifndef WORLD_LOS_INC
%define WORLD_LOS_INC
%define WORLD_LOS_VERSION 1
; world_los(XMM0..5 start/endXYZ) ->EAX1clear/0blocked.
; Authority wrapper selects sim_wrecks/count/revision. Explicit world_los_context
; accepts RDI stable1024x64records,ESI active count,RDX derived revision.
; Covers continuous current analytic ground, authored solids, captured wrecks.
; LOS uses any validated actual wreck blocker; body/projectile APIs retain closest contact.
; Any caller/source fault is blocked. No actor contact or start-inside escape.
; Readonly, SysV, sequential query safe point. Authoritative callers connected;
; explicit remote prediction/warning consumption remains separate.
%endif
