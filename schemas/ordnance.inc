; Private ground ordnance admission contract v1; entity/wire layouts unchanged.
%define ORDNANCE_GROUPS 4
%define ORDNANCE_REQUEST_STRIDE 16
%define ORDNANCE_TARGET 0
%define ORDNANCE_SOURCE_GENERATION 4
%define ORDNANCE_TARGET_GENERATION 8
%define ORDNANCE_NEXT 12
; ordnance_init(): resets private cursors/diagnostics and enables admission.
; ordnance_begin(): clears derived queues, once before target acquisition.
; ordnance_request(EDI source,ESI target): EAX0 accepted/-1invalid, only actual
; same-tick acquired opposing ground weapon targets, ready ammo/cooldown.
; ordnance_flush(): interleaves side*2+(kind-1), rotates group tick and starts
; each group's linked list after last admitted source ID. Calls production
; projectile_spawn; no forged trajectories/stores/damage/events.
; ordnance_hash(RAX accumulator,R8 FNV multiplier): enabled+4success cursors.
; ordnance_enabled u32 defaults1, explicit legacy negative control at0.
; ordnance_metrics 4groups*4u64 (group-major): submitted,admitted,
; capacity denied,invalidated. Derived queues/diagnostics excluded from hash.
; World queues armor/artillery before infantry's 8tick phase. Their existing
; real30/90tick cooldowns govern cadence. Legacy mode preserves old phase/order.
