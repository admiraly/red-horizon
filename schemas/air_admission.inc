; Private same-tick aircraft release admission v1. No entity/wire layout change.
%define AIR_ADMISSION_GROUPS 4
%define AIR_ADMISSION_REQUEST_STRIDE 16
%define AIR_ADMISSION_TARGET 0
%define AIR_ADMISSION_SOURCE_GENERATION 4
%define AIR_ADMISSION_TARGET_GENERATION 8
%define AIR_ADMISSION_NEXT 12
; air_admission_init(): enabled=1, success cursors=-1, diagnostics reset.
; air_admission_begin(): clear derived queues before aircraft acquisition.
; air_admission_request(EDI source,ESI acquired target): EAX0/-1. Caller must
; already have checked real LOS, flight alignment and bomb release geometry;
; submit ascending stable IDs, once/source/tick. Require valid opposing sides,
; living nonzero generations, active matching aircraft sidecar, role0/1,
; AIR_TARGET matching submitted target, attack mode, ammo>0,cooldown=pass_ticks=0.
; Bombers target nonair; fighters target air. Revalidate all on flush plus
; submitted generations. No additional target search, movement or LOS work.
; air_admission_flush(): four side*2+role queues; rank by lowest submitted
; physical ID (empty last), rotate canonical rank tick&3, each queue starts
; after its last successful source cursor. Call actual projectile_air_launch
; with role+3. Only success consumes one finite round, sets cooldown3 and
; bomber egress/pass210/target=-1; failed release preserves stores/pass/target.
; All requests visited once; existing480 air/512 physical ceilings unchanged.
; air_admission_hash(RAX,R8 FNV): policy4B then four success cursors16B.
; air_admission_enabled u32 defaults1; 0 selects existing immediate legacy path.
; air_admission_metrics four group-major rows of four u64: submitted, admitted,
; capacity_denied, invalidated. Non-ready rejects are not accepted submissions.
; Derived requests/metrics excluded from hash. Ground/air class competition
; remains governed by production total-count thresholds, not separate pools.
