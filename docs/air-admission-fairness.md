# Production aircraft release allocation oracle

`python3 tests/test_air_admission_fairness.py build/libsim.so --legacy`
captures the existing immediate fixed-ID release behavior. Without `--legacy`,
the oracle requires the integrated `air_admission_enabled` policy and checks
balanced real releases among simultaneously ready side/role groups.

The oracle calls production `air_combat_tick`, which actually acquires targets,
checks range, terrain LOS, forward cone or bomb lead/cross-track geometry, and
calls production `projectile_air_launch`. Initial deployment is controlled,
while original aircraft stable IDs, bomber/fighter role, generations and finite
8-bomb/180-gun stores remain intact. One `air_tick` initializes real sidecars;
then development poses place opposing populations in separate neighboring250m
cells. The real fighter target index retains only8 samples per cell, so putting
both sides in one cell would test a different acquisition limitation.

Bombers use opposing live ground targets at terrain-dependent ballistic lead.
Fighters acquire opposing real aircraft through the production index. The
initial side-label swap preserves every physical deployment and velocity; it
changes only side labels. Both modes assert identical retained physical source
IDs under the swap and exact same-build replay, rather than swapping pose blocks.
All releases are independently checked against finite ammunition expenditure,
retained source ID/generation/kind/side, cooldown3, and real projectile count.
Successful bombers must enter egress with pass210 and cleared target; denied ready
bombers retain stores, pass, cooldown and acquired target.

The recorded baseline at runtime parent `f8117e8` with library SHA256
`b4b6eb0078060e3c148b176cb12e6a61f49b13e742222378c858249a3318ef7e`
is in [worker evidence](evidence/air-admission-worker-legacy.json). Sixteen-thousand
initialized entities contain1,024 retained living original aircraft in the mixed
fixture:512 per side,256 bombers and256 fighters each. Actual480-cap admission
is480:0, with240 bombs and240 gun rounds to the first physical-ID side. Pure-role
fixtures contain512 total aircraft and admit256:224. At32,768 initialized IDs,
mixed2,048 aircraft and pure1,024 aircraft both admit480:0. Side-label swaps reverse
reported side counts without moving sources. These are initialized ID envelopes,
not living full-army scale acceptance.

Fourteen negative controls cover empty stores, cooldown, bomber pass, backward
heading, stale sidecar generation, dead sources and blocked wall LOS across both
roles. Every control yields zero actual air projectiles and zero capacity drops.
A production preload of416 real original tank launches leaves64 air slots,
allocated64:0 in legacy mixed mode. This proves the existing416 ground,480 air
and512 physical thresholds are total-count ceilings, not independent pools.
Cross-class allocation remains outside this oracle's fairness assertion.

A separate480-air-pressure control launches32 actual direct weapon projectiles
using32 original tank actors with untouched64-round stores. Each consumes one
round and sets cooldown30, filling the512 physical pool. The513th launch fails
without consuming ammunition or changing cooldown. This verifies primitive
reservation headroom; it does not exercise a player GUI action.

Sparse original-role aircraft subsequently run the real world without forced
projectile retirement or damage callbacks. The bomber fixture first damages its
opposing ground target on tick143; the fighter fixture first damages a real
opposing aircraft on tick8. Damage to unrelated actors is deliberately excluded
from these contact checks. Exact replay is checked for each case. The existing
`test_aircraft.py` supplies the broader continuous flight/interception/defense
behavior checks.

Natural seed42 `scale-front` and `scale-hotspot` fixtures preserve all8,192
initial army entities and run120 real world ticks with hazard response enabled.
Active projectile generations are sampled, and original finite aircraft stores
independently count all launches. Baseline front retained samples by
side0-bomb/side0-gun/side1-bomb/side1-gun are27/585/2/301; finite stores show
27/643/2/321 actual launches. Hotspot samples15/623/7/360 compare with finite-store
launches15/668/7/379. Samples omit same-tick launch/retirement, so sampling is not
an exact firing total. Both natural fixtures replay exactly.

Same-side actors deliberately overlap in the allocation fixture. This is no
crowd, navigation, graphical, audio, network, combined-arms operation or complete
massive-game acceptance. Direct combat-phase allocation tests isolate readiness
from flight movement; natural world samples and sparse delayed contacts have
separate scope. Candidate results require the root integrator's runtime and
focused/full integration verification; this worker's evidence establishes the
legacy causal baseline only.
