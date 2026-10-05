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

Independent first-candidate review used the root's immutable
`/tmp/rh-controller-candidate-first.so`, source snapshot
`6944b87-1783c72d59f967f3`, library SHA256
db19dcea2400339f6f14dc38fa9339d7f0858a71663d8f3a228cdcaffdd21c41.
The29 controlled scenarios, four intersection arrangements and two placement
controls passed. Both scale cases had zero new controller/army or
controller/controller swept overlaps:219/218 near-army checks,360 controller-pair
checks each,199/200 moving-controller ticks, and570/660 real army deaths. Slot
physical trace invariance was false for humans and drivers; exact same-slot replay,
input fidelity, safety and useful motion passed in both assignments. Sequential
controller ordering is therefore a measured limitation, not a symmetry claim.

A direct-public-API malformed-state negative then changed `sim_count` from32 to
32769 after valid initialization/player join, rebuilt derived snapshots, and
requested human source32768 to step from(3500,2000) toward(3501,2000) by0.3m.
The first candidate returnedX3500.300048828125 rather than holdingX3500. This test
does not run `sim_tick` or scan past entity storage. The negative establishes a
missing fail-closed invalid-count check on the human source path; army sources
and occupancy already rejected this count. Exact evidence is retained in
`docs/evidence/controller-crowd-invalid-count-negative.log`. Final acceptance must
rerun against the corrected immutable library; the first-candidate results do
not establish malformed-count acceptance.

The later full-checkpoint co-op death/redeployment failure was reproduced on
immutable source snapshot`d70896e5fe72f59ba9fb5f92b2ca776be38bda19-9690f7ac5be055f4`,
server SHA2567cff00b80d68a163c06755a1fba776f20621dcbf7591d598fce8ce7a6689e799
and library SHA2561eed8319f49cedacfa0c4d41dc0e48ced9817cf7dc27dc8f366d230912cc15ca.
The test's position-only setup collapsed all4,096 allied actorX positions onto
X1000, which is also every owned rear deployment site'sX coordinate. During
failed respawn attempts those sites were body-occupied. The three ownedX3000
sites were body-clear but actual enemy aircraft inside160m had clear LOS; private
inspection copied current aircraft state and used production`sim_entity_height`
and`terrain_los`. Deployment correctly rejected those unsafe choices. A rear
site eventually cleared near tick265, while the next respawn attempt was tick280,
outside the original9-second observation window. Increasing that window would
hide the fixture's conflicting physical assumptions.

Replacing only the position write`X=1000` with a coherent`X=oldX-1800` translation
preserves allied pair separation and distances the unrelated army from the one
fixture threat. For initialseed42 all4,096 actors translate toX1600..2111;
all3,840 ground bodies remain static-terrain-valid, and the nearest ground body
is601.52m from a rear deployment site. Three independent realUDP/server runs of
the original death/redeployment function with this single position-write change
passed its unchanged9-second assertions and exited naturally at330ticks. HP,
damage, respawn timers, generations, site ownership/resources and runtime code
were unchanged. Exact condensed diagnostic snapshots and repeat results are in
`docs/evidence/controller-crowd-coop-death-fixture-diagnosis.json`. This proposes
a geometry correction to the integration fixture; it does not prove general
operation recovery under every army/air threat arrangement.
