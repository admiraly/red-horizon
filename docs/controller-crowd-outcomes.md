# Production controller/body collision observer

`python3 tests/test_controller_crowd_outcomes.py LIB [--legacy] [--report PATH]`
uses the actual authoritative assembly `sim_tick`, validated `player_input`,
actual waypoint/orders, player join/leave, and legitimate allied-tank boarding.
It does not invoke the crowd kernel's candidate routines or inspect its scratch.
The development-only observer computes the minimum distance between two moving
planar centers over each whole tick independently and compares nominal physical
radius sums (human/infantry0.55m, tank3.55m, artillery4.49m), with2mm float tolerance.
Manual inputs retain norm, signs and individual requested component bounds.

The29 controlled120-tick cases cover humans and driven tanks against held
infantry, tanks, artillery and humans; near-contact diagonal free-axis sliding;
preexisting inward/outward contact; opposing moving humans; death, disconnect
and generation/position changes; AI movement against held/moving humans, and opposing legitimately driven tanks.
All29 controlled fixtures repeat exactly, including physical trace and
checksum. AI physical traces also compare swapped army faction labels without
changing IDs, positions, goals, fronts or commands. Straight blockades need useful
approach but may hold at contact; the observer does not demand manual autopilot.
Outward overlap fixtures require eventual clearance and useful recovery. Existing
penetration must not deepen. Boarded drivers remain attached to their actual hull.

Four additional120-tick arrangements send four humans or four legitimately
boarded tanks toward a common intersection, each in forward and reversed slot
assignment. Every pair receives a relative swept-circle check and each controller
retains its requested input components and useful approach. Each arrangement
repeats exactly. Physical per-body trace equivalence between slot orders is
reported explicitly, since the contract permits bounded late-stage live-human
queries; safety, input fidelity and useful progress must hold in both orders.

Placement controls occupy all12 authored site positions and8 front0 near-field
candidate positions; a live publication overlapping the artillery body is rejected.
A second control surrounds every current tank exit candidate with artillery placed
4.5m from the proposed human endpoint: legacy4m center exclusion misses the5.04m
combined footprint. A failed safe exit must preserve the legitimate boarded claim.
These tests concern the current authored deployment/exit rules, not world streaming.

The60-tick8,192/16,384 hotspot census retains real combat, losses and initial army
positions. Three humans approach existing allied infantry while a fourth human
legitimately boards an existing allied tank. Every living controller is checked
against living same-generation army bodies with a conservative independent
coordinate broadphase. Complexity is O(4N) per tick, not army allpairs. The boarded
human/hull pair is excluded. All six controller/controller pairs also receive
independent relative sweeps each tick. Initial overlap samples are recorded separately;
new relative swept overlap is a candidate failure. Useful controller movement and
actual army HP loss are required, so freezing the whole simulation cannot pass.

The preextension source is8317f00cbb8bd9aeb32761aa83d8b6ed13642ecd. Its actual
built library was copied before candidate changes to `/tmp/controller-crowd-preextension.so`,
SHA25681c5782fece521c7acd424ba2d2dc34d1759bc0a5d7dbf71d2748950415af394.
`--legacy` sets production `crowd_enabled=0`; this also disables army mutual crowd
avoidance and is a causal control, not an alternative accepted physical policy.
The baseline records all eight straight controller body penetrations, AI/human
collisions, and unsafe deployment/exit publication. Diagonal safety negatives
remain in the report rather than requiring every fixture to expose a fault.

The census checks controller-to-army pairs, not every army mutual pair or every
rendered mesh vertex. Planar circles do not establish limb, oriented hull, vertical,
slope, suspension or realistic steering acceptance. Four-player rendered/co-op
collision and target-GPU performance require separate integration evidence.
