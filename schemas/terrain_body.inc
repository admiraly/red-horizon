; Private footprint-aware static terrain contract v1; CPU implementation NASM.
; Role radii infantry/player0.55m, tank3.55m, artillery4.49m, air0.0m.
; Ground footprints conservatively enclose both authored scale-one vehicle LODs.
; terrain_body_init(): default enabled1; reset diagnostic/private state.
; terrain_body_blocked: EDI role0..3, XMM0/1 XZ -> EAX1 blocked/invalid,0clear.
; terrain_body_path_clear: EDI role, XMM0/1 startXZ,XMM2/3 endXZ -> EAX1clear,0blocked.
; terrain_body_move: EDI role, XMM0/1 startXZ,XMM2/3 actuallonggoalXZ,
; XMM4 requestedstep -> XMM0/1 actualendpoint. Finite inputs/role/step validation;
; bounded static-solid sweep, map inset, route/detour and component recovery;
; preserve step bound, no teleport/body/table/HP/order writes or heap allocations.
; Already-invalid starting footprints must not teleport or deepen penetration;
; document gradual recovery vs safe hold. Do not accept invalid starting overlap
; as clearance evidence. Each accepted sweep from a clear start must remain clear.
; Use actual long goal for route planning; don't substitute only a tiny endpoint.
; Conservative expanded AABBs may be used; disclose corner overconservatism.
; terrain_body_step: same signature/return/source/step bounds asmove; directmanualcontroller
; collision-and-component slides only, no autonomous detour/corner steering.
; Pure-axis input must not produce orthogonal movement; diagonal slides remain
; within requested signs/components and step bound. Preserve original intent
; direction before clipping actual endpoints to body map insets. Step goals may
; be finite outside map within[-8000,16000] for locally generated edge intents;
; source/AI goals retain[0,8000]. Rootplayer/driven callstep, AI calls move.
; Ground-solid flags govern body terrain, LOS/projectile point paths stay distinct.
; Air retains original continuous independent flight behavior and finite validation.
; No entity/player/network layout change or camera/faction-dependent movement.
; terrain_body_enabled0 delegates legacy point terrain APIs for causal controls.
; terrain_body_hash(RAX,R8 FNV): enabled/all future commitments; diagnostics,
; stateless derived scratch excluded. Immutable radii/code belong build identity.
; Root owns runtime callers/nav/hashing/suite registration; worker owns module.
%ifndef TERRAIN_BODY_INC
%define TERRAIN_BODY_INC
%define BODY_INF_RADIUS 0.55
%define BODY_TANK_RADIUS 3.55
%define BODY_ARTY_RADIUS 4.49
%endif
