# Terrain integration and next vehicle work

Source cc90b6d integrates canonical raised relief into CPU height/derivatives,
physical LOS/projectiles/player eye/air clearance, full swept-body grade admission,
bounded bypass navigation and both actual embedded GPU height shaders. Focused
kernel, production-caller and independent public-path proofs pass. Full extended
checkpoint 3d022b3c7d8e passed 533.82s/81reports with 177 matching authored
inputs; status.md owns scoped acceptance.

The field is a product of trapezoids, X 5400/5480/5620/5820 and
Z 4800/5000/5400/5600, maximum added height 64 m. The central rising gradient
is 0.8; the gentle ramp magnitude is 0.32. Combined corner gradients reach about
40.58 degrees. The zero derivative convention at exact factor breaks does not
establish clearance: nine closed facets inspect both sides, full inflated bodies,
intermediate terrain, combined bowl/relief derivatives and a squared-norm guard.
Expanded segment rectangles are conservative and can reject valid diagonal paths.
Foot/tank/artillery limits 45/35/25 degrees are design choices. Read-only canonical
geometry adds no mutable future state; protocol content fingerprint includes it.

The original 22-node obstacle graph expands to at most 27 nodes with four hill
corners and one gentle-side entrance. Cached routes remain artillery-conservative;
actual actuator queries retain the moving role. Public tanks and artillery reach
the plateau through safe bypasses and climb/descend its gentle side. The tank can
reach a fringe the artillery rejects. No shortest-route or road-preference claim.
Original army movement/health/replay and arrival deadlines remain required.

The linked renderer replaces exactly 112 coarse cells with a localized 5 m,
105,000-vertex patch. Actual GL triangle interpolation stays below 0.027 m error;
outer vertices join the old mesh. Build guards reject fields that leave that
verified fixed tile or exceed its interpolation bound. This is one authored
profile; global coarse ridge interpolation and arbitrary terrain are not accepted.
The inspected normal-texture client screenshot is a frozen camera fixture,
not natural combat, human art acceptance or target-GPU performance.

Terrain-aligned stateless presentation is now integrated at 646ea71, with
actual CPU/GPU/client proof and a passing full checkpoint, 86ca2085d678. See
ground-support-rendering.md. Current geometry has pitch/roll from a shared
five-height chassis frame, matching all visual LODs without authority writes.
Next is bounded cosmetic suspension response with resampled contact for its
intermediate angles; a verified response kernel is isolated and not integrated.
Driver seats/projectile origins remain governed by their original physical
contracts. Visual tilt does not establish oriented/vertical body collision.

Road-preferring navigation, wheeled roles, oriented physical hulls, vertical
interactions, safe formation spacing, traffic recovery, damage states and useful
wreck cover remain required. Complete operation/intelligence, streaming, runtime
jobs/reload/snapshots, Windows, recorded audiovisual craft and sustained four-client
hardware performance remain independent full-game requirements. License approval
and human playtest gates do not prevent implementation of these next systems.
