; Prepared immutable wreck -> existing mesh shader instance, not draw activation.
%ifndef WRECK_INSTANCE_INC
%define WRECK_INSTANCE_INC
%define WRECK_INSTANCE_BYTES 64
; wreck_instance(RDI output,ESI bytes>=64,RDX source,ECX bytes>=64)
; EAX0 instance,-1 invalid,-2 inactive. No output writes on rejection.
; Source has wreck.inc layout. Pose copied verbatim; frameA/B/blend zero;
; pitch/bank from death pose, unit scale, absolute height, role1/2.
; Identity ID=-1/side3 excludes dead wrecks from living army census.
; High mesh frame0 at every wreck mesh LOD is the initial matched geometry
; policy; this helper does not select descriptors, draw, replicate or add cover.
; Output/source may overlap; source is read completely before output commit.
; SysV GPR/stack preserved, SSE2 only, no globals/calls/allocation.
%endif
