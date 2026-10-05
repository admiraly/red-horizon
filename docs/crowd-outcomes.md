# Production physical crowd outcome oracle

`tests/test_crowd_outcomes.py LIB [--legacy] [--report PATH]` drives the real
assembly `sim_tick`, explicit side/front orders, shared navigation and swept terrain
movement. Python is only an external development oracle. Initial deployments and
orders are controlled; no expected endpoint, post-tick movement, collision event
or damage is fabricated. Fixtures use one faction to remove gunfire confounds,
while whole production world ticks remain active. Global label swaps keep actual
ground poses and explicit waypoints fixed.

The private physical collision contract uses radii 0.55 m infantry, 3.55 m tank,
4.49 m artillery. The vehicle discs conservatively enclose the scale-one authored
meshes: `src/render/meshes.asm` `.unit_scale` writes1.0 XYZ; the maximum baked
radii across both LODs are3.5499566554 m tank and4.4887285215 m artillery in
`content/models/bake-report.json`. LOD0 X/Z dimensions are3.541751×6.048255 m
and5.055217×7.084345 m respectively. The oracle asserts these bounds rather than
shrinking physical separation to prototype dimensions. Infantry0.55 m is a torso
steering footprint, not its full animated weapon envelope.
Every controlled world tick checks actual role speed (0.12/0.5/0.2 m), finite map
bounds, terrain endpoints, and independent segment/rectangle intersection against
all five authored solid records. Relative swept pair segments detect two bodies
crossing between endpoints. Normal encounters require zero overlapping pair-ticks
within 0.002 m tolerance. Held actors must stay exactly fixed. Initial-overlap
recovery permits existing penetration but requires that clear pairs stay clear,
no pair deepen beyond 0.003 m tolerance, full final separation and useful advance.
Solo and opposing explicit goals require arrival within 0.6 m. Shared-goal convoys
require over 40 m advance per actor; infantry cohorts over 10 m. This avoids the
physically impossible requirement that multiple bodies occupy one exact goal.

Eleven encounters cover held infantry, tank and artillery; opposing infantry
waypoints; a five-tank convoy; a wall-edge pass and actual detour across the central
solid wall; a partly overlapping five-infantry cohort; a held driven tank obstacle;
aircraft accompanying ground movement; and a source generation change at tick61
without changing its physical pose. The generation case proves fresh world-tick
rebuild behavior, not a stale-snapshot API rejection (which needs a kernel probe).
Aircraft continue their own production flight; label invariance checks only ground
movement because the faction patrol policy differs. This companion case is weaker
than the isolated kernel proof that an overhead aircraft never enters the body grid.
The tank convoy begins8 m apart, leaving0.9 m disc clearance. The held artillery
fixture begins12 m from its blocker, with a35 m goal rather than the older20 m
goal;360ticks permit72 m movement rather than48 m to allow the larger physical
detour without lowering speed or clearance. Each case runs twice identically plus a physical label swap. Complete per-tick
ground pose trace hashes must match across that swap, not merely final endpoints.
The legacy control must reproduce body traversal in all ten body fixtures and
stacked final convoy/cohort outcomes, rather than only print diagnostics.

Both actual dense scenario modes are measured: mode2 `scale-front`, mode3
`scale-hotspot`, 8,192 initialized entities, seed42, 120 production ticks by default,
each repeated from fresh initialization. An independent development-only 8 m
spatial-bin census with5×5neighbor coverage finds nearby living ground actor pairs
(up to16 m guaranteed reach, exceeding8.98 m largest body sum plus4 m reporting
margin); airborne and driven
actors are excluded from this census. Current-pose gaps are not swept collision
proof. Real initial overlaps, deaths and combat movement confound changes in pair
counts, so this report explicitly does not claim collision-free dense acceptance.
It records living counts, surviving ground actors that moved, final engaged count,
and authority checksum. These armies are not reduced to the controlled fixture size.

## Retained old-runtime negative control

`docs/evidence/crowd-worker-baseline.json` is from worker source base
`869f6c88cedc4604ed67be85a84cfe1349e03253`, with the crowd module absent.
`tools/dev.py test --suite waypoints` built the real library and passed existing
waypoint scenarios; then the oracle ran `--legacy`. Library and final oracle SHA256
are embedded in the artifact. It establishes the actual old behavior with current authored-size footprints,
not candidate acceptance. Earlier659e794/856df56 reports used prototype tank2.5 m
and artillery2.0 m radii and are superseded historical evidence inGit; their gap
and overlap counts must not be substituted for this refreshed artifact:

| Encounter | Overlapping pair-ticks | Minimum swept gap (m) |
| --- | ---: | ---: |
| Held infantry | 19 | -1.1 |
| Generation reuse | 19 | -1.1 |
| Held tank | 30 | -7.1 |
| Held artillery | 90 | -8.98 |
| Opposing infantry | 10 | -1.1 |
| Five-tank convoy | 870 | -7.1 |
| Wall-edge pass | 30 | -7.1 |
| Actual wall detour | 24 | -2.917882 |
| Initial infantry overlap | 3,533 | -1.1 |
| Driven tank obstacle | 69 | -4.1 |

The convoy and initial-overlap cohort end stacked at their common goal. All old
movement still meets role-speed, terrain collision, deterministic replay and ground
label invariance. Body traversal, not terrain or movement speed, is the demonstrated
fault.

Natural front: initially110 overlapping living ground pairs, finally439; 6,804
surviving ground actors moved; final alive3,635/3,675, engaged2,512; checksum
`7931e154948edb30`. Natural hotspot: initially315 overlapping pairs, finally954;
6,658 surviving ground actors moved; final alive3,567/3,595, engaged3,311; checksum
`47891e38fe31b744`. These are separate exact scenario measurements.

Candidate completion requires running this oracle against a source-matched library
with `crowd_enabled=1`, with all assertions passing. Existing physical terrain and
speed assertions are not weakened to make body steering pass. No claim here covers
player-owned collision, full vehicle driving, broad combined-arms traffic,
pathological dense-pool overload, target-GPU performance, rendered readability or a
complete operation.
