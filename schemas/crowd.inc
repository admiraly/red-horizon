; Private AI ground crowd movement contract v1. Entity/player/wire ABIs unchanged.
; crowd_init(): enabled1, reset private state and diagnostics.
; crowd_begin(): once after air/hazard updates, before any ground movement;
; build fixed bounded spatial index of immutable living ground actor snapshots.
; Include driven vehicles as physical obstacles, exclude overhead aircraft.
; crowd_move: EDI stable source ID; XMM0/1 actual current X/Z, XMM2/3 actual
; navigation or hazard goal X/Z, XMM4 maximum metres/tick. Returns XMM0/1 actual
; terrain-safe endpoint. No authoritative entity/HP/order/ammo/target writes.
; Source kind/generation/living state must match snapshot and valid live actor.
; Respect requested step and role limits0.12/0.5/0.2; keep terrain_body_move swept
; collision and map bounds on every candidate. Query only nearby physical bodies.
; Deterministic role-sized separation, bounded side steps/yielding and gradual
; overlap recovery; no teleportation, unchecked count/ID, heap or O(N^2) scans.
; Stable snapshot queries must not depend on prior same-tick actor movement or
; camera/side labels. Simultaneous opposing motion needs conservative sweep
; clearance using neighbor step bounds; bound all cell/neighbor/candidate work.
; Explain any truncation/overlap recovery limits and expose exact diagnostics.
; Caller keeps explicit/AI hold untouched. Driven sources use existing vehicle
; control path; this module does not claim player collision/steering acceptance.
; enabled0 delegates terrain_body_move (EDI kind) without actor avoidance;
; terrain_body_enabled0 separately selects legacy point terrain as a control.
; crowd_hash(RAX,R8 FNV): enabled and all private future-affecting commitments;
; derived snapshot/index/diagnostics excluded. No silent future state omission.
; Kernel owns layout/constants/storage except this shared API contract.
; crowd_metrics: eight u64 cumulative diagnostics, in order:
; snapshot actors, move queries, inspected neighbors, corrected endpoints,
; yielded moves, overlap recoveries, truncated queries, maximum inspected/query.
