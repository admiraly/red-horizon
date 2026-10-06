# Ground body movement and dynamic wreck routes

The body/routing implementation is integrated on main at f8d80b8.
Frozen full43b83242e4da passed946.8517s; all authored inputs match this
integrated runtime. Extended network
634d5a189315 passed131.7513s. The source snapshot is
09c6ce82aa24871bacf0170522ebe413aed980e7-999ea2bdc1f0b1d9.

world_body_path_clear/block/step compose original terrain/map/grade and captured
wreck sweeps with .551/3.551/4.491m radii. Actual crowd AI/manual/hull candidates,
component slides and crowd-disabled moves are checked; deployment/exit occupancy
uses the same cover. Continuous controller heading, signed speed and momentum
remain owned by the existing ground policy. Air motion is unchanged. Connected
foot preview selects net_wrecks/count/revision explicitly, preserving received Y.
It cannot promise parity before cover arrives through the existing fair stream.

wreck_nav_goal follows the existing static/cover-selected goal. A32m local probe
requests a persistent per-actor route only when actual wreck cover obstructs it.
The512-entry FIFO coalesces pending identity/goal updates and builds at most8
routes per tick. A build uses a64m local endpoint, extending in8m increments to
at most96m if the clipped endpoint lies inside cover, never beyond the actual
goal. It adds four padded corners for up to8 relevant wrecks and local authored
solid corners, with54 nodes and28 retained waypoints. Every edge and selected
leg is checked by the original-role world-body query. Routes release at their
local endpoint. A new obstruction causing a reached intermediate point triggers
replanning; deaths elsewhere do not globally invalidate corridors. All future
commitments and queue state enter the authority hash; no heap allocations.

23 public-tick fixtures pass. Single-wreck infantry/tank/artillery arrive and
hold at338/124/326ticks, identically for swapped labels, replay and crowd enabled/
disabled. Multiple-wreck routes, three initial-overlap escapes, a longer route
whose64m endpoint is inside another wreck, new intervening casualty (397ticks,
two builds), and genuine tick1800 expiry/manual recovery pass independent
closed-slab observation. No in-flight pose, HP, ordnance or clock renewal occurs.
The actual router-omitted control stalls all three crowd-disabled roles; a first
control incorrectly assumed every crowd-enabled narrow-wreck route stalls, and
was corrected because local crowd steering can eventually route some cases.

The actual module contract passes1,035 requests,512 admissions and512 safe queue
overflows;64 drains at8 builds/tick reach the final FIFO entry. Pending generation/
role/goal reuse is coalesced. Invalid ID/count/generation/goal/liveness/air role
preserve the entire route-state hash. Wreck records and SysV GPRs/stack remain
unchanged. These contracts establish bounded work and correctness in the stated
fixtures, not complete-operation performance or streamed navigation.

A concurrent natural900tick observer measured tick p95 at11.556ms (8k open),
26.519ms (16k open) and39.742ms (8k hotspot). It observed real casualties, active
wrecks and bounded queues/builds without altering simulation inputs. These are
concurrent single-thread timings, not an isolated target-GPU acceptance run.
The hotspot exceeds33.3ms. Many local windows exceed8 wrecks and currently fail
safely; graph failures and local overflow remain reported, not hidden. A separate
unintegrated relevance prototype selects bounded useful vertices while retaining
complete obstruction checks, and already reaches the nine-wreck fixture. It
requires its own checkpoint before integration.

Integrated compatibility: UDPv14/schema0xda94decc/content0xd30d7e25, canonical SHA
 d30d7e25453a94308b2f9fd2ba2ab309cb148be0f22f12205abefa162425ddbf.
No packet layout changes. Body and all dynamic-route policy constants enter the
content fingerprint. Earlier auxiliary UDP graphics sent obsolete v13 fixture
constants and timed out; the fixture is corrected. Superseded full90d07272f604
and91331b33bda2 were deliberately cancelled before integration for those fixture
corrections; they are not passed checkpoints. Initial exploratory fast verification
mixed pre/post-fix local builds and is excluded from final-source acceptance.

A real keyboard-driven UDP/software-GL preview fixture also passes. It uses a
genuine casualty and150 public ticks reaching contact, then frozen snapshots
and synthetic freshness/expiry ticks: empty cache advances0.16675m, admitted
cover holds exact XZ, retired cover advances again. Received authority except
transport clock is unchanged; local simulation does not tick. This is client
preview/render-source proof, not natural server/controller or lossy freshness
acceptance. Local and corrected UDP draw pairs pass all eight role/distance
fixtures, retaining map-zero/cull limitations. Exact reports and source hashes:
docs/evidence/wreck-body-routing-jobs.json.

Remaining: reliable relevant-cover freshness, overflow/performance improvement, oriented and
vertical physical hulls, streamed hierarchy, remote hazard warning and human art/
playtest acceptance. Existing high/low roof mismatch, map zero wreck pixels and
800m rendering cull remain explicit. These checks cannot prove the full game.
