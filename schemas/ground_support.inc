; Root-owned read-only terrain support ABI v1, no physical collision/state change.
%ifndef GROUND_SUPPORT_INC
%define GROUND_SUPPORT_INC
%define SUPPORT_VERSION 1
%define SUPPORT_STRIDE 64
%define SUPPORT_Y 0
%define SUPPORT_PITCH 4
%define SUPPORT_BANK 8
%define SUPPORT_FLAGS 12
%define SUPPORT_RIGHT 16
%define SUPPORT_UP 32
%define SUPPORT_FORWARD 48
%define SUPPORT_VALID 1
; Chassis support rectangles chosen from measured high-detail bottom geometry.
; Shared across visual LODs; samples remain inside nominal physical body circles.
%define SUPPORT_TANK_HALF_WIDTH 1.75
%define SUPPORT_TANK_HALF_LENGTH 2.55
%define SUPPORT_TANK_CENTER_Z -0.45
%define SUPPORT_ARTY_HALF_WIDTH 2.40
%define SUPPORT_ARTY_HALF_LENGTH 3.43
%define SUPPORT_ARTY_CENTER_Z -0.01
; ground_support(RDI out,ESI kind1/2,EDX capacity>=64,XMM0 x,XMM1 z,
; XMM2 heading[-pi,pi])->EAX0success/-1invalid, output unchanged on invalid.
; Nonnull output pointer is caller-owned writable capacity. Finite XZ[0,8000].
; Validate every support corner is on map BEFORE terrain queries/output writes.
; Output: Y, pitch, bank, flags=1 then three vec4 right/up/forward (w=0).
; Heading convention zero+Z, positive toward+X. R=(cos,0,-sin),F=(sin,0,cos).
; Sample four corners center+R*(+-width)+F*(centerZ+-length).
; rSlope=(h++ +h+- -h-+ -h--)/(4width),
; fSlope=(h++ +h-+ -h+- -h--)/(4length).
; base at ENTITY center = mean(h)-centerZ*fSlope, raised by max positive
; corner residual and then at least actual terrain_height(entity center).
; This supports five sample heights; it does NOT prove entire mesh clearance.
; pitch=atan2(fSlope,1), bank=atan2(rSlope,sqrt(1+fSlope*fSlope)).
; Frame exactly yaw*pitch*bank, matching current mesh.vert rotation order.
; SSE2 implementation, existing platform libm sinf/cosf/atan2f permitted.
; Preserve SysV nonvolatile GPRs, align all calls, no global/state/output on fail.
; Padding w lanes canonical+0, finite output and stable orthonormal handed frame.
; Stateless cosmetic pose only. No suspension, oriented collision or authority.
%endif
