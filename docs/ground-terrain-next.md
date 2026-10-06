# Next terrain-dependent vehicle slice — sampler prepared, integration pending

The current hull batch adds physical heading and momentum. The next coherent
slice should make surface handling authoritative and show the same roads to the
player. This note records a read-only source audit during frozen integration;
it supplies no road, steep-slope or wheeled-vehicle acceptance.

CPU terrain_height and both vertex shaders share a quadratic bowl plus triangular
ridge. Its gradient norm is below0.023, approximately1.31degrees. battle.frag's
cosmetic gravel strips cross three solid walls; adopting those strips as physical
routes would be incorrect. Collision/navigation currently remains available
independently of rendering, which the new surface data must preserve.

The isolated sampler at worker commit `2a70494` accepts finite in-map X/Z and returns height,
analytic X/Z derivatives and center surface class. A single canonical road table
should generate NASM and GLSL constants offline. Verified standalone geometry is
19 segments: three five-segment east-west front roads, plus four north-south
connectors atX1000/7000. Each front road atZ1300/3900/6500 follows:

```
(1000,z) -> (3800,z) -> (3920,z-250) -> (4080,z-250)
         -> (4200,z) -> (7000,z)
```

The ridge crossing sits50m beyond the wall end. A 10m paved half-width
accommodates current conservative hull radii. Independent segment/rectangle
checks include the 4.49m maximum hull radius and measure at least 35.51m
clearance from all five static walls. These checks do not establish clearance
from dynamic actors or road-preferring navigation.
Replace cosmetic strips with this exact shared geometry. Static table/handling
changes require a content fingerprint change, not new entity/ground/wire strides.

Surface multipliers can change desired speed and acceleration before existing
hull evolution. Retain the current maximum envelopes and bounded braking when
crossing a boundary; do not instantly clamp retained momentum. Center class alone
is insufficient evidence of full-hull road contact. Define footprint sampling or
conservative whole-shape classification, measure boundary behavior, and retain
terrain/body collision, public controls, replay and8k/16k useful movement. Current
steady-speed fixtures should explicitly name their surface when this policy changes.

Steep-slope acceptance needs meaningful authoritative geometry. A continuous
raised patch away from dense initial encounters could have a steep80m ramp rising
64m and a gentle200m ramp reaching the same height. Tests must drive the real
actuator along both, retain useful movement on the gentle approach and reject the
steep approach without body slides or teleportation. The entire footprint segment
needs a bounded grade test; level endpoints can conceal a steep intervening ramp.
Derivatives and heights must agree with rendered geometry. Uphill/downhill and
reverse cases need separate outcomes, not a uniform role-speed constant.

Navigation currently has22 nodes derived from five obstacles and shares
artillery-conservative corridor checks. Adding a grade rejection without contour
or bypass nodes can strand otherwise reachable vehicles. Keep the static road
slice independent, then introduce steep geometry with explicit reachability,
bounded path work and meaningful role constraints. Oriented hulls, vertical
interactions, suspension and wheeled roles remain further required work.

If a terrain profile becomes selectable or mutable, it affects future authority:
initialize, hash and save it, advertise compatibility on join and reject mismatches.
Cosmetic weather is unsuitable storage. Do not start parallel implementation until
root defines and owns sampler/grade/generated-content contracts and isolates
worker file ownership.

Prepared source and focused evidence are recorded in
`docs/evidence/terrain-surface-prepared.json`. The real assembly sampler passed
2,806 valid samples and eight invalid-input cases; 27 malformed generator inputs
preserved both existing outputs. NASM/GLSL/canonical/runtime tables agree, and
the helper compiled with glslangValidator. The worker is clean. None of its nine
new files are integrated into root yet.

For the next integration, classify road contact conservatively: a circular hull
is on-road only when it fits inside at least one paved capsule. Check distance
to that segment against half-width minus role radius. A union junction may give
a conservative off-road result even when the circle fits across several capsules;
this is acceptable if documented and measured, and avoids claiming center-only
classification proves full contact. Keep road/off-road acceleration and desired
speed within the existing envelopes; boundary crossings brake retained momentum
through the current actuator. Apply the same generated distance helper to gravel
and shoulder material, with exact-road interior and explicit visual shoulders.

Root will own build dependencies, standalone probe dependencies, physical
actuator hooks, content compatibility and shader embedding. Focused outcomes must
include same-role road/off-road differences, boundary crossing, stationary turning,
reverse, driver-to-AI handoff, full-footprint classification at bends, camera
independence and replay. Validate actual painted doglegs in GL. Freeze the whole
batch only after those outcomes and unchanged scale/health/collision checks pass.
