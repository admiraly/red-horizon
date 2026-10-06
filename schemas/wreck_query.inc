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
; 128x128 center-bucket grid, 62.5m cells; query XZ rectangle padded6m.
; <=16384 cells and1024 candidate records; short paths visit nearby buckets.
; Prepared wreck_body_query: same result/capacity, XMM0/1 startXZ,
; XMM2/3 endXZ,XMM4 radius0..4.491. Projects world boxes toXZ and inflates
; both axes (conservative circle/body approximation). Ignores a start-overlap
; only for nonzero motion with a nonincreasing initial nearest-face depth.
; Zero motion remains occupied; crossing deeper to leave the far face is blocked.
; No body/nav/controller/remote query hook activation or vertical capsule claim.
; Cache rebuilt after accepted register/expiry/init; not authority or checksum.
; Single-thread simulation safe point only. No heap. SysV preserved GPR/stack.
; Diagnostic wreck_query_candidates counts the most recent valid caller search.
%endif

; Prepared explicit source variants wreck_query_context/wreck_body_query_context:
; RDI result24,ESI capacity,RDX readable1024x64 records,ECX active count<=1024,
; R8 caller-derived revision; endpoints/radius match corresponding legacy ABI.
; Source immutable throughout call; caller advances revision after any mutation.
; Cache key includes source pointer+revision. No remote/world selection implied.
; Invalid caller checked before source; source storage validity is caller-owned.
; Shared derived cache supports sequential safe-point calls, not concurrency.
