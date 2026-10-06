# Bounded physical ground steering

`src/nav/crowd.asm` implements private `schemas/crowd.inc` without changing entity,
player, or wire layouts. Infantry/armor/artillery center radii are 0.55/3.55/4.49 m.
Vehicle circles conservatively cover the authored model spheres (tank3.550 m,
artillery4.489 m), replacing the initial prototype2.5/2 m circles. Infantry radius
covers the torso rather than every extending gun/limb; oriented hulls remain future
work if less conservative vehicle passing is needed.
AI source steps stay at 0.12/0.5/0.2 m/tick. Living driven armor remains a physical
obstacle; its conservative neighbor step is 0.6 m/tick, matching the existing
vehicle control path. The v2 controller extension adds direct body collision for
driven sources and independent human players; see [controller crowd](controller-crowd.md)
and [actual-world outcomes](controller-crowd-outcomes.md). AI long-goal steering
and direct controller steps retain distinct policies.

`crowd_begin` takes immutable tick-start ground X/Z, radius, role, generation and
maximum-step snapshots. Aircraft, dead actors, zero generations, unsupported roles
and nonfinite/out-of-map positions are excluded. The 8 m grid has 1001² heads;
only previously occupied heads (at most 32768) clear each begin. Initial setup
clears the full grid. Snapshot storage is (32768+4)×32 B, with a 32768-entry occupied
cell list; no hot-path allocation. Infantry queries check at most nine neighboring cells and filter centers to 8 m.
Vehicle queries check at most25 cells and filter centers to16 m. Four bounded human checks supplement indexed army neighbors. Either query
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
lockstep cannot count as recovery. Exactly coincident moving bodies use their actual navigation intent. Physical-ID
priority allows one actor to begin separating while its peer yields that tick;
priority alternates using immutable authoritative tick parity so a coincident
explicit held neighbor cannot starve either physical ID forever. The cached parity
is derived from `sim_tick_count` at begin and is already represented by the world
checksum; no private future commitments are introduced. No side labels,
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

## Wall-adjacent recovery correction

Root's production-world oracle exposed a real regression after mesh-sized circles:
`wall_edge_pass` (armor3978,1094→4030,1094, held armor4000,1094) ended at
3994.4197,1099.7109 after240 ticks, arrival error36.0357 m despite preserving body
separation. Independent production probing also found the longer actual terrain
route (3970,1300→4030,1300 beside that held body) oscillating near the z1100 wall
edge after1600 ticks. Safe single-tick endpoints did not prove navigation recovery.

Two causes are corrected in the worker kernel. The uncorrected forward candidate
now supplies the caller's actual long navigation/hazard goal to `terrain_move`,
preserving its corridor/corner route rather than substituting a short pseudo-goal
that repeatedly alternated against the wall. Its actual returned endpoint remains
subject to the same swept body tests. In that intermediate revision exactly coincident recovery still used a short
fixed-direction goal; the intent correction below supersedes that tie policy. For corrected sidesteps, a bounded production
`terrain_path_clear` query screens the next12 m in the proposed direction before
accepting the short terrain-safe endpoint. This rejects wall-facing detours when
the other side of a held body is open. Ten candidate directions remain bounded;
no future commitments or new hash bytes are introduced.

The self-built NASM/production-terrain regression fixtures now reach both original
wall-route goals exactly after240/1600 normal-step ticks. All prior ABI, swept body,
vehicle-role, overlap recovery, convoy and causal controls remain passing. Final
isolated8192-infantry mean3.445204 ms/p953.461469 ms with the same32,905,152
inspections and zero truncations. Whole-world acceptance still belongs to root's
independent integration oracle. The12 m corrected-direction screen is conservative:
complex local mazes with body obstruction may still require richer route recovery;
these two fixtures do not prove universal navigation convergence.

## Preserve cooperative intent during coincident recovery

The intermediate fixed-world-direction tie caused an actual existing tactics
regression: allied flank actors1/17 started together at3500,1300. Their real first
navigation goals were5000,700 and5000,1900, then cached corridors3984,1096 and
3984,1504. The old lower-ID +Z/higher-ID −Z tie immediately placed them on opposite
sides from their assigned goals and body constraints blocked their subsequent
crossing. After89 ticks they remained at3510.3691,1300.5844 and
3510.3691,1299.4156, respectively. Reversing a fixed handedness passed this one
fixture but did not solve reversed real intents, so that trial was superseded.

The final coincident policy follows actual navigation goals and uses deterministic
physical-ID priority solely to decide which actor first moves away. Each begin
snapshots authoritative tick parity: one phase allows the highest coincident ID,
the other allows the lowest. Other coincident actors yield unchanged. Once any
positive separation exists, the existing strictly outward radial and relative
swept checks govern gradual overlap recovery. Alternation prevents an explicitly
held coincident actor at either ID from permanently blocking its moving peer.
All state derives from already-hashed world tick, living generation-safe body
snapshots, and actual caller intent. Snapshot phase, lists and diagnostics remain
read-only derived data; private hash still covers only the enabled word.

The final actual NASM/terrain oracle passes both original and reversed divergent
flank goals, shared-goal coincident recovery (gap1.3199664 m after40 ticks), and
moving-vs-held coincidence at either ID (>4 m progress in50 ticks, held record
unchanged). Exact coincident cohorts of3/5/8 actors recover in160 ticks to minimum
center gaps1.2459924/1.2460523/1.2460523 m; every small-cohort relative sweep retains
already-recovered separation and all actors move more than1 m. The noncoincident
five-actor partial-overlap chain remains at minimum1.2222231 m, with existing
outward-only body rules unchanged. Wall regressions still reach their original
240/1600-tick goals exactly. Final isolated8192 mean3.542698 ms/p953.589564 ms,
max143 inspections/query and zero truncation; timing varies with concurrent work.

A development shadow library copied the16 already-built root integration objects
at root e95c5225708b46571a2477497d706243dbc5d196, replacing only the crowd object
with the worker's final source. Both the entire unchanged `tests/test_tactics.py`
and `tests/test_crowd_outcomes.py` passed. Tactics includes physical scouting,
opaque-wall reconnaissance/capture, opposing real flank corridors, firing bounds,
observed-threat/supply retreat, explicit holds, replay, and default8192/16384
army movement. The ≥95% per-front distance gates and ≥90% forward progress at300
ticks were retained. Actual initial player-bubble moving counts were415/415,
435/435,468/468 at8k ticks30/120/300 and846/846,883/883,949/949 at16k. The whole-world
crowd oracle retained all11 encounters, dense outcomes, physical label swap and
replay. This isolated replacement evidence does not substitute for root's required
source-matched full frozen integration checkpoint.
