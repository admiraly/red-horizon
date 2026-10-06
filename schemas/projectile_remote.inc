%ifndef PROJECTILE_REMOTE_INC
%define PROJECTILE_REMOTE_INC
%define PROJECTILE_REMOTE_POLICY_VERSION 2
%define PROJECTILE_OWNED_PRIORITY_MAX 4
%define PROJECTILE_WIRE_MAX 18
; Packet record64 is slot4 + the first60 bytes of authoritative projectile64.
; At most4 freshest live current-generation owned cannon samples, then fair
; nearby source-independent ring records (including tombstones), no duplicates.
; At least14 general entries remain when the priority allowance is full.
; Interest and physical projectile state are unchanged; no reliable delivery
; or sample guarantee for trajectories shorter than the 10Hz snapshot period.
%endif
