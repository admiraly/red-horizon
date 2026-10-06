; Root-owned immutable whole-body grade contract v1, NASM/SSE2/SysV.
%ifndef TERRAIN_GRADE_INC
%define TERRAIN_GRADE_INC
%include "schemas/terrain_body.inc"
%define TERRAIN_GRADE_VERSION 1
%define TERRAIN_GRADE_LIMIT 9
%define TERRAIN_GRADE_STRIDE 64
%define GRADE_INF_LIMIT_SQ 1.0
%define GRADE_TANK_LIMIT_SQ 0.49029059656570206
%define GRADE_ARTY_LIMIT_SQ 0.21744283205399903
%define GRADE_GUARD_SQ 0.000001
%define GRADE_BASE_X 0.000002
%define GRADE_BASE_Z 0.000001
; Limits are proposed practical 45/35/25 degree design policies, not spec numbers.
; terrain_grade_clear(EDI role0..3,XMM0/1startXZ,XMM2/3endXZ)->EAX1clear,
; 0grade/footprint blocked,-1invalid. Finite coordinates[0,8000], integerrole.
; Air bypasses ground grade after validation; all helpers preserve SysV GPRs.
; Entire actual sweep circle enclosed by expanded segment AABB, clipped against
; every CLOSED height facet. Both one-sided cusp gradients must be checked.
; Conservative false positives at diagonal/corner boxes must be documented.
; No state/allocation/authority writes. Max9facets*4corners, SSE2 double geometry.
; Outside relief existing bowl/ridge norm<.023, far below all declared caps.
; Inside relief combined dx=BASE_X*(x-4000)+a*z+b,
; dz=BASE_Z*(z-4000)+a*x+c. Squared norm convex: rectangle corners bound it.
; Require normSquared+GUARD_SQ<=roleLimitSquared, account for float sampler error.
; Generated read-only9records: xmin,zmin,xmax,zmax,a,b,c as7f64 + flagsu64.
; Canonical source content/terrain/relief.json. Generated labels
; terrain_grade_count,terrain_grade_facets; flags1 enabled. Root owns body hooks,
; height/derivative calls, routes, compatibility/build/test integration.
%define GRADE_XMIN 0
%define GRADE_ZMIN 8
%define GRADE_XMAX 16
%define GRADE_ZMAX 24
%define GRADE_CROSS 32
%define GRADE_XCONST 40
%define GRADE_ZCONST 48
%define GRADE_FLAGS 56
%endif
