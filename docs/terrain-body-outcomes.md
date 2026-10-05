# Independent production terrain-footprint outcomes

`tests/test_terrain_body_outcomes.py LIB` drives actual assembly `sim_tick`, manual
army waypoints, human input and a legitimately boarded tank. Python observes and
checks the authoritative state; it does not replace movement, write endpoints
between ticks, grant movement, or fabricate events/damage. Initial controlled
placements and role conversions are explicit fixtures. Friendly-only surviving
actors, explicit holds for all other fronts, and disabled hazard steering remove
combat and hazard confounds while retaining production navigation and terrain.

The observer reads only obstacle bounds and ground-solid flags from the runtime,
then independently intersects each actual motion segment with rectangles expanded
by infantry/player0.55m, tank3.55m or artillery4.49m. Map bounds are inset by the
same radius. This is the conservative expanded-AABB contract, including its corner
overconservatism; it does not establish an oriented-hull or vertical collision model.
The2mm tolerance covers float32 subtraction at kilometre coordinates. Controlled
clear-start cases never treat an existing overlap as proof of clearance.

The matrix exercises short wall-skirt routes, long wall/structure detours, actual
navigation cache intermediates, useful advance toward unreachable center-edge
goals, walking/sprinting/jumping/crouching, tank driving at0.6m/tick, and a player
initialized with a shallow invalid body overlap. The latter must hold or recover
without deepening penetration and may never reenter after becoming clear; it is
separate from clear-start acceptance. Wall-skirt player movement crosses the full
wall span at genuine controller speed. Direct wall approaches are safety controls:
legacy point movement already happens to stop sufficiently far away for the human
radius, so those controls are not claimed as historical failure reproductions.

Each controlled case is repeated from initialization with exact per-tick physical
trace and final checksum equality. Army cases additionally exchange only faction
labels while keeping IDs, coordinates, fronts and actual goals fixed; every physical
movement tick must agree. Player/driver cases remain allied because the current
boarding policy requires allied tanks. Kind2 artillery cannot be boarded in the
existing controller, so no driven-artillery support is claimed.

Natural8192/16384-entity hotspot censuses retain actual mixed-army initialization,
combat and casualties. They report starting/final footprint-invalid ground actors,
invalid movement segments, clear-start reentries, surviving actors moving over1m,
alive counts and replay checksum. Initial authored placement overlap is reported
separately, rather than silently classified as valid. This census observes planar
static terrain only and does not prove all bodies are mutually separated, complete
operation reachability, graphical quality or hardware frame budgets.

`--legacy` disables `terrain_body_enabled` if the module is present, otherwise uses
the actual pre-module library. The historical record asserts positive footprint
fault counts in every causal fixture, while retaining the direct human wall
approaches as safety controls. Candidate mode requires the production policy
symbol, zero clear-start swept violations, bounded speeds, useful route arrivals,
controller progress up to obstruction, no invalid-overlap deepening, exact replay
and faction invariance, and no natural clear-start reentry.

Historical baseline evidence is `docs/evidence/terrain-body-worker-baseline.json`.
Its library and oracle SHA-256 values identify the measured executable and observer.
Root integration owns runtime callers, suite registration and final acceptance.
