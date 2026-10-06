; Shared authoritative ground-hull motion ABI v1. Entity32/player64 unchanged.
; Root owns this contract. CPU implementation remains NASM/SSE2.
%define GROUND_STRIDE 32
%define GROUND_HEADING 0       ; radians, zero+Z, positive rotates toward+X
%define GROUND_SPEED 4         ; signed metres/fixed30Hz tick
%define GROUND_TURN 8          ; actual radians applied this tick
%define GROUND_VX 12           ; actual accepted world-X metres/tick
%define GROUND_VZ 16           ; actual accepted world-Z metres/tick
%define GROUND_GENERATION 20
%define GROUND_KIND 24         ; tank1 or self-propelled artillery2
%define GROUND_FLAGS 28
%define GROUND_ACTIVE 1
%define GROUND_AI 0
%define GROUND_DRIVER 1
; sim_ground_motion[ENTITY_CAPACITY] is authoritative, generation-stamped.
; ground_init(): enabled1, zero private state, seed living valid vehicle headings
; from assigned initial waypoints (no motion), independent of camera/rendering.
; ground_step(EDI entityID, ESI modeAI0/driver1, XMM0/1 actual currentXZ,
; XMM2/3 desired steering pointXZ, XMM4 desired maxforwardstep) -> XMM0/1 endpoint.
; Mode1 requires a valid living allied tank with bidirectional driver claim.
; Validate count, ID, kind, generation, all finite input and source pose before
; mutation. Preserve invalid input state. Normal AI speed caps tank0.5/arty0.2;
; driver cap0.6. Shared physical tank envelope0.6 permits bounded braking across
; AI/driver handoff; no instant reversal or camera-driven sideways translation.
; No desired movement applies bounded braking; keep stopped hull heading.
; Desired heading changes by bounded turn, sharp turns reduce target speed.
; Reverse uses a bounded lower cap and brakes through zero before reversing.
; Collision uses crowd_hull_step with ONLY the physically reachable segment;
; accepted movement parallel to the actual hull axis, no X/Z component slide or
; autonomous endpoint rotation. Contact may stop speed immediately for safety,
; while bounded heading turning allows stationary tracked pivots.
; Recycled generation/kind resets heading/motion safely before normal evolution.
; AI and driver share the same state; boarding/exiting never reinitializes it.
; ground_enabled0 is an explicit development causal control for old movement.
; ground_hash(RAX accumulator,R8 FNV prime) includes policy and EVERY persistent
; future-affecting field. Derived diagnostics must not masquerade as future state.
; Renderer/network read the same stamped heading even while stationary.
; Current circles remain conservative; oriented hull, suspension, turret mesh,
; wheeled chassis, road/slope semantics require separate implemented evidence.
