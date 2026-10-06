; Derived captured-pose cover query v1, not yet a gameplay collision hook.
%ifndef WRECK_QUERY_INC
%define WRECK_QUERY_INC
%define WRECK_QUERY_BYTES 24
; wreck_query(RDI result24, ESI bytes>=24, XMM0..5 startXYZ/endXYZ)
; EAX1 hit,0 clear,-1 invalid caller,-2 malformed active registry.
; Hit result: float t@0, u32 slot@4, entity@8, generation@12, sequence@16,
; reserved0@20. No output writes otherwise. Invalid caller checked first.
; All endpoints finite abs<=16000. Closed conservative world AABBs transformed
; from frame0 high/low mesh union; 2mm rounding skin. No body inflation yet.
; Nearest t, equal float t resolved by entity then generation then sequence.
; 32x32 center-bucket grid, 250m cells; query XZ rectangle padded6m.
; <=1024 cells and1024 candidate records; short paths visit nearby buckets.
; Cache rebuilt after accepted register/expiry/init; not authority or checksum.
; Single-thread simulation safe point only. No heap. SysV preserved GPR/stack.
; Diagnostic wreck_query_candidates counts the most recent valid caller search.
%endif
