; Private AI ground crowd movement contract v2. Entity/player/wire ABIs unchanged.
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

; Controller/body extension v2: root owns hooks; isolated kernel worker owns code.
; Include living connected nonboarded humans as bounded physical bodies. Stable
; virtual body ID ENTITY_CAPACITY+slot(0..3); radius0.55m, maxstep0.3m/tick.
; At most four humans may be checked directly alongside indexed army neighbors;
; total inspected records/query <=512, including distant/stale inspected records.
; Do not require O(N) scans per movement query or expand entity/player/wire ABIs.
; Resolve live HP, generation, kind and boarding validity before using snapshots.
; crowd_step: EDI living human virtualID or legitimately driven tank entityID;
; XMM0/1 currentXZ, XMM2/3 original local goalXZ, XMM4 requestedstep.
; Return XMM0/1 actualendpoint; controller source caps0.3human/0.6tank.
; Finite local goals may lie[-8000,16000] like terrain_body_step. Keep requested
; signs/components/norm; full step then legal component slides or safe hold,
; no autonomous detours/rotations/pushing/damage/teleportation. Ground body sweep
; must honor both terrain and nearby role-sized bodies, including moving humans,
; AI actors and driven hulls. Already-overlapped sources require outward recovery;
; clear starts must not introduce swept overlap. Exclude boarded duplicate human.
; crowd_occupied: EDI ignored bodyID(-1none), ESI groundrole0..2,
; XMM0/1 candidateXZ -> EAX1 occupied/invalid/truncated,0clear. Nonmutating
; bounded indexed occupancy for deployment/exits; do not ignore hull on exit.
; Root refreshes snapshots before player stage/placement and keeps actual live
; generation/boarding/death transitions valid. New/changed human bodies must be
; covered through bounded live-four fallback or equivalent safe handoff.
; AI retains normal role steps, long-goal detours and immutable tick-start queries.
; Controller queries may use current human records conservatively for late join/
; exit/earlier controller changes; no unchecked stale body or missing-body hole.
; Policy off uses terrain_body_step/move and occupied0 only for causal controls.
; Derived snapshots/metrics remain unchecksummed; enabled policy is sole future
; state unless additional commitments are explicitly included in crowd_hash.
; Diagnostics must count the actual visited-record local, not grid coordinates.

; Ground-hull actuator extension v3 (root contract, isolated kernel owner).
; crowd_hull_step(EDI validtank/artyID,ESI AI0/legitimate driver1,
; XMM0/1currentXZ,XMM2/3physically reachable exactendpointXZ,XMM4stepbudget)
; -> XMM0/1endpoint. Query ONLY this whole segment: full acceptance or safehold,
; never normalize a shorter segment to a larger step, no component slides or
; sideways avoidance. Validate source/snapshot/generation/kind and driver claim;
; bound all record/candidate work as before; malformed/saturated safehold.
; Tank physical sweep envelope0.6m/tick for gradual driver->AI braking even after
; ownership clears, artillery0.2. Immutable AI snapshots and current late human
; queries retain their existing phase distinction. Nearby tank anticipation must
; cover0.6m even when no claim is present. Legacy control still checks full terrain
; footprint and exact segment (not a terrain detour). No authoritative actor writes.
; Driver claim readers additionally compare privatevehicle_driver_generation[slot]
; to currentnonzeroPLAYER_GENERATION; entitygeneration alone does not bind a human.
