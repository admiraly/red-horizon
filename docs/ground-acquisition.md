# Ground target acquisition candidate

Tanks now search a2-cell envelope and artillery a3-cell envelope, matching
existing450m/650m planar acquisition range in250m cells. Infantry stays at1;
bomber approach search remains5. Nearest physically visible target selection,
24-ID per-cell reservoir, weapon range, actual LOS, fire cadence, finite stores,
projectile travel, damage, movement and side knowledge remain unchanged.
Runtime is NASM/SSE2; schemas/acquisition.inc policy2 is independently included
in build-time and co-op test fingerprints. Private UDPv18 changes compatibility
without changing packet layouts. Main remains accepted v14.

Actual150tick public fixtures test both side labels and four cardinal directions.
Tanks launch tick1 and damage a449m target at45; artillery launches tick1 and
hits649m targets at107–109. Ammunition is finite (5tank/2artillery releases).
Identical initial fixtures replay identically.451m/651m and diagonal beyond-range
cases never launch or damage; a400m target behind the bunker wall stays unharmed.
The original accepted library fails the unchanged distant tank assertion.
Initial sparse positions/health/ammunition are fixture setup only, never renewed.
The focused tactics suite retains its original8k/16k motion/replay and1200tick
wall recovery; fast exits0 with the new outcome fixture registered. Exact logs
and source/library hashes are in docs/evidence/ground-acquisition-*.

Range completeness here means all potentially relevant cells are searched;
24-ID reservoirs can still omit eligible targets in dense cells. This is not
exhaustive per-actor visibility, support designation, protected bombing,
strategic intelligence or completed AI acceptance.

Concurrent300tick alternating-order timing: original/candidate p95ms is
10.756/14.752 (8k open),39.477/54.916 (8k hotspot),22.400/29.813 (16k open).
Changed acquisition changes actual combat workloads and checksums; this does
not isolate query cost or meet hotspot33.3ms acceptance. No rendering/replication.
Both full verification checkpoints were active during the initial comparison.

A generated NASM near-first heavy-weapon loop preserves original cell/sample
rank for equal-distance ties. Every30tick authoritative checksum and all entity
bytes match the simple envelope through300ticks for8kopen/hotspot/16kopen.
It lowers hotspot mean32.667→28.174ms and p9553.490→48.542ms, but open timing
slightly worsens and the hotspot still fails its budget. The earlier all-role
ring experiment is retained separately. The final generated source/library
hashes are in acquisition-order-probe.json. Neither loop is promoted: more
cost diagnosis, causal controls and original full-scale gates remain required.
Full combined routing/assault/compatibility verification precedes integration.

Continuation: exact nearest-visible selection now uses a bounded2904-entry
private stack heap (23360-byte world frame). Eligible candidates retain their
original f32 distance and inverse original cell/sample rank; the first physically
visible heap result is therefore the same nearest target and equal-distance
winner. No stored targeting/intel policy or weapon range changes. Malformed
capacity cannot overrun scratch; candidate cells/samples remain bounded.

The generated loop matches full authoritative checksums and all entity bytes
every30ticks through900 for8kopen/hotspot/16kopen, without pose/health/store/clock
renewal. Paired p95ms is17.700→19.679,67.333→65.724,40.071→43.831 respectively;
means14.896→16.604,53.090→48.453,31.718→34.895. The300tick mean benefit did not
establish long-operation cost; hotspot and stretch remain over33.3ms. The900tick
report completed at12:50:14+02 before production-library relinking at12:52:06+02;
there was no live-artifact replacement overlap. Source/library hashes and sampled
states are retained in acquisition-heap-900.json.

80 sparse fixtures per paired comparison pass exhaustive nearest-visible
checks, mirrored labels, original tie preference, a hidden nearer versus visible
farther target, stale initial hints and a second real tick. An independent single
production-library oracle is now registered in fast/simulation/combat. The
physical449m/649m travel/hit and range/LOS negatives pass on the heap prototype.
The production heap passes the complete fast suite after replacing numeric frame
sizes with equivalent named scratch constants; canonical acquisition policy2
compatibility remains unchanged. Fast source is static throughout.

Revalidated previous-target and conservative cell-side-mask prototypes also
preserve sampled authority, but give only small gains in these workloads and
add complexity. Their source, reports and logs are retained; neither is promoted.
The next coherent candidate combines this range/selection implementation with
accepted main's query/deployment/quit fixes and the ground company slice. Full
combined verification and additional measured query/decision cost work remain.

Causal priority control reverses only the heap root comparison. The unchanged
public nearest-visible fixture rejects its wrong equal-distance target with
AssertionError; exact source/library hashes and terminal output are retained.
The superseded near-first development tool reads the verified archived simple
source explicitly, with a source hash/precondition check, rather than silently
transforming the now different production loop. This tooling repair is outside
the preceding fast run; it changes no runtime source.
