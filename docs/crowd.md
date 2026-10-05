# Bounded physical ground steering

`src/nav/crowd.asm` implements private `schemas/crowd.inc` without changing entity,
player, or wire layouts. Infantry/armor/artillery center radii are 0.55/3.55/4.49 m.
Vehicle circles conservatively cover the authored model spheres (tank3.550 m,
artillery4.489 m), replacing the initial prototype2.5/2 m circles. Infantry radius
covers the torso rather than every extending gun/limb; oriented hulls remain future
work if less conservative vehicle passing is needed.
AI source steps stay at 0.12/0.5/0.2 m/tick. Living driven armor remains a physical
obstacle; its conservative neighbor step is 0.6 m/tick, matching the existing
vehicle control path. This module does not steer driven sources or separate the
independent human player records.

`crowd_begin` takes immutable tick-start ground X/Z, radius, role, generation and
maximum-step snapshots. Aircraft, dead actors, zero generations, unsupported roles
and nonfinite/out-of-map positions are excluded. The 8 m grid has 1001² heads;
only previously occupied heads (at most 32768) clear each begin. Initial setup
clears the full grid. Snapshot storage is 32768×32 B, with a 32768-entry occupied
cell list; no hot-path allocation. Infantry queries check at most nine neighboring cells and filter centers to 8 m.
Vehicle queries check at most25 cells and filter centers to16 m. Either query
inspects at most512 linked records. An omitted body cannot intersect the maximum
ground sweep: infantry against the largest artillery circle needs at most
0.55+4.49+0.12+0.2=5.36 m; the largest role pair (two artillery) needs
4.49+4.49+0.2+0.2=9.38 m. The respective grid neighborhoods guarantee8/16 m
coverage even when the source lies at a cell edge.

Source ID/count/HP/kind/generation and input validity are checked; live retired or
reused neighbor generations do not retain stale bodies. Valid queries use cached
positions even after earlier same-tick entities have moved. Ten directions are
bounded: goal-forward, ±30/60/90/135 degrees, then backward. Every candidate calls
the production swept `terrain_move`, retains the role/requested step bound, and
is tested against nearby body segments before acceptance. The normal fast path
accepts the first forward terrain-safe candidate. Head-on clearance includes the
neighbor's next role step. Already inside that anticipation margin, nonclosing
outward/tangent movement is allowed rather than freezing everyone.

Existing overlaps recover gradually. Noncoincident pairs require a genuine
outward radial component and no deeper swept overlap; merely moving parallel in
lockstep cannot count as recovery. Exactly coincident bodies break symmetry using
an antisymmetric physical ID choice in a fixed world direction. No side labels,
camera state, random stream, HP/order/ammo writes or teleportation enter steering.
No future-affecting commitments exist: `crowd_hash` includes only the enabled
policy word; derived snapshots, index and cumulative metrics are excluded.
`enabled=0` delegates original terrain-only movement as an explicit causal control.

The eight cumulative u64 diagnostics are snapshot actors, move queries, inspected
neighbors, accepted corrected endpoints, yielded moves, accepted overlap recovery
moves, truncated queries, and maximum inspected/query. Snapshot count accumulates
per begin, including held/driven obstacles. Inspected count includes valid linked
records before distance/liveness filtering; accepted recovery counts individual
source decisions, not proof that a whole crowd has separated.

## Worker verification

`RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_crowd.py`
self-builds actual NASM plus production terrain and a development-only ABI/bulk
probe. It passed held infantry bypass to (1010,1000), driven-tank bypass with
4.10 m body clearance, a 2.4 m clear lane between two tank footprints (9.5 m center spacing), real
opposing movement to swapped endpoints with minimum gap 1.1203613 m, coincident
pair recovery to 1.2318115 m, and five partially overlapping infantry recovery to
minimum gap 1.2222231 m. Actual head-on tanks and artillery also reach swapped endpoints: minimum center
gaps7.3112310 m and9.0399308 m, respectively, above7.10/8.98 m body sums.
Small simultaneous movement fixtures test relative swept
separation, source role step bounds, read-only authoritative records, physical
ID/order/side-label invariance and replay. It also checks ABI preservation, finite
input rejection, stale generations, source-kind mutation, FNV policy bytes, wall
collision, a progressing eight-actor convoy, and maximum-count malformed inputs.
The same held-ally route with disabled steering physically enters the held body.

An all-coincident 32768-actor pathological query yields unchanged with exactly
512 inspections, one truncation, and maximum inspected/query 512. No unbounded
chain scan or unchecked allocation occurs. This is an explicit acceptance limit:
more than 512 records in the nine-cell infantry or25-cell vehicle neighborhood conservatively yield, even
if some records are farther than the source query radius. A pathological unsatisfiable crowd may remain
blocked, and broad initial-overlap layouts are not proved to resolve universally.

A 30-tick assembly-loop isolated benchmark at 2 m infantry lattice spacing measured
128 actors mean 0.021514 ms/p95 0.022443 ms and 8192 actors mean 3.4439282 ms/p95
3.462451 ms on the current worker host. The latter inspected 32,905,152 records,
max 143/query, zero truncations. Timings include snapshot rebuild and actual
terrain/crowd movement, two Python calls per tick, and exclude per-actor Python
copies. They are not complete world, graphics, network, native-job or dense combined
arms acceptance. Root integration must verify actual nav/hazard inputs and army
pressure before reporting a broader result.

The universal5×5 candidate considered during body-size correction was measured
at8192 infantry mean10.087073 ms/p9510.20287 ms with87,183,168 inspections,
max399/query and zero truncations. The final role-sized neighborhood avoids that
unnecessary infantry work while retaining the larger vehicle body/sweep bound.
Positive-infinite requested steps and zero-generation sources also reject safely.
