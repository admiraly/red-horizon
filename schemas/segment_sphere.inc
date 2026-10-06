; Closed3D sphere first-entry primitive, SSE2 double intermediates.
%ifndef SEGMENT_SPHERE_INC
%define SEGMENT_SPHERE_INC
%define SEGMENT_SPHERE_BYTES 16
%define SEGMENT_SPHERE_COORD_LIMIT 16000.0
%define SEGMENT_SPHERE_RADIUS_MIN 0.001
%define SEGMENT_SPHERE_RADIUS_MAX 4096.0
; RDI readable centerXYZ/radius16, ESI capacity; XMM0..5 segmentXYZ endpoints.
; EAX1hit,0clear,-1invalid. XMM0 first t only on hit, otherwise original startX.
; Closed tangent/endpoints; start-inside t0; zero-length outside clear.
; No source writes, allocation, calls or nonvolatile register changes.
; Does not define actor hitbox/fuse policy, broadphase or damage.
%endif
