# Next coherent wreck-cover integration

Query570b6ee is a read-only prerequisite. Prepared instance2fcfe4e is isolated.
The next batch must activate physical cover together with visible and replicated
wreck state; partial local-only authority or invisible solid boxes are not enough.

Renderer: meshes.asm currently filters dead entities before appending army
instances. Add a separate immutable-wreck batch, using prepared wreck_instance,
actual high-detail frame0 tank/artillery descriptors and matching bounds at every
mesh distance. Do not let wrecks consume living high-instance budgets or inflate
army visible/detail census. Use separate wreck telemetry/budgets. Existing
animation/suspension must never alter a captured death pose. Test real local and
network client death, expiry and ring replacement with shader geometry/depth and
census exclusion. High geometry cost and useful far representation need measured
budgets; the preparation test only verifies transform input/output.

UDP: new self-contained records need slot and full64-byte wreck pose/identity.
A68-byte entry permits17 records in a40-byte-header1196-byte packet. Confirm the
actual current header before freezing a versioned wire contract. Carry source
tick/sequence, publish explicit tombstones and bound per-client fairness. Join in
progress needs complete state recovery with lost/reordered chunks; source-slot
retirement must clear old geometry without allowing a delayed old record to
resurrect it. Entity generation reuse must preserve old immutable wreck history.
Validate the entire packet before any registry mutation, reject old clock/sequence
with wrap-safe policy, clear state on disconnect and invalidate the derived query
cache whenever remote records change. Changing protocol/schema/content identity
is mandatory when these records become client-visible authority. Do not reuse the
query-cache revision as a wire authority sequence.

Vision: terrain_los currently owns swept fixed solids plus sampled ground checks.
A wreck ray can reject visibility using the shared conservative bounds, with
explicit-2 malformed-cover behavior. This must remain independent of camera,
render LOD, loaded assets and actor labels. Player rifle currently chooses the
nearest eligible target center inside a cone, then asks terrain_los to that
center; this is not an exact physical muzzle-ray hitscan. Preserve that stated
policy or implement/verify a deliberate real ray change rather than claiming
physical bullet interception from a target-center visibility check.

Shells: sim_shell_contact currently selects live actor contact; projectile_tick
uses its returned XYZ. Merge live actor/terrain/wreck first contact explicitly,
with deterministic tie policy and exact swept contact XYZ. A wreck must absorb a
shell without becoming a live actor/victim or awarding damage to an arbitrary
retired entity ID. Exercise a wreck before/after/behind a live target, start-inside,
grazing, reverse rays, zero motion and actual delayed blast. No health or pose
renewal during flight. Preserve finite ammo and admission symmetry.

Bodies/navigation: crowd/terrain_body use nominal planar body circles, with
original radii. The point query is not a body sweep: introduce bounded inflation
and a stated vertical/body-height policy before enabling body contact. Conservative
rotated world boxes can contain empty corners outside the original living body's
circle, so new wrecks can overlap an adjacent body at birth. Implement bounded
no-deepening escape and local path invalidation; do not trap actors until60s expiry
or relax arrival/recovery gates to hide the problem. Current jump does not provide
full capsule/wreck vertical collision or vault. Match local controller prediction
with server contact and test expire/retire/reuse recovery at genuine public ticks.

Checkpoint: preserve8192/16384>=95% army motion,400tick health/label symmetry,
360tick held artillery arrival,1200tick wall recovery and all original radii,
grades and speeds. Add naturally generated dense wreck cases without in-flight
HP/pose renewal. Measure actual query candidate cost with cover enabled; the
read-only Python probe's1.17–1.24us/query includes ctypes and establishes no full
server-tick budget. Full frozen scale/real graphics/audio/UDP fault verification
and hardware/human acceptance retain their existing roles.
