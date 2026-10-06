# Raised terrain and whole-body grade — next integration

The canonical road/handling batch is integrated at `53d2211`; its current full
verification status and exact evidence are in `status.md`. The original sampler
preparation at `2a70494` is historical. Roads use 19 clear capsule segments, a
10 m paved half-width and a 2 m cosmetic shoulder. Whole-circle containment in
one capsule determines physical contact; junctions may conservatively classify
off-road. Road/off-road factors alter desired speed, acceleration and reverse,
while retaining braking, yaw, collision envelopes and inherited momentum.
Road-preferring route planning remains absent.

The authoritative bowl/ridge alone has gradient norm below 0.023, about 1.31
degrees. It cannot prove useful slope admission. The next isolated prerequisite
is contract commit `c5b0cd3` plus component commit `90706d5` in the clean
`/mnt/titan_nv3/projects/red-horizon-workers/terrain-relief` worktree. Its exact
source hashes and focused terminal evidence are in
`evidence/terrain-relief-prepared.json` and `evidence/terrain-relief-prepared.log`.
This component is not part of root authority, navigation or rendering yet.

The field is a product of two continuous trapezoids: X breaks
5400/5480/5620/5820, Z breaks 4800/5000/5400/5600 and height 64 m.
The rising X ramp is 80 m at derivative 0.8; the falling X ramp and Z fades
are 200 m at magnitude 0.32. Combined corners are steeper than either central
axis: (5479,4999) gives gradient (0.796,0.316), about 40.58 degrees.
The sampler's chosen zero derivative at exact factor breaks is a cusp convention,
not a grade-clearance guarantee.

Root must define one grade contract before further worker implementation. A
conservative query should cover the full swept body, including intervals crossing
factor breaks and both one-sided gradients at cusps. Level endpoints can conceal
a steep intervening ramp. Within each relief facet the total gradient is affine;
its squared norm is convex. Clipping an expanded body-segment bounding rectangle
against each facet and checking the corners gives a bounded conservative maximum.
It may reject a safe diagonal segment; measure and document those false positives.
Include the existing bowl/ridge gradient, invalid-input preservation and a fixed
facet-work bound. Terrain/loading/camera state must not affect admission.

Suggested initial design limits are 35 degrees for the tracked tank and 25 degrees
for artillery, with foot motion considered separately. These are implementation
choices to validate, not numerical requirements taken from the specification.
The central steep ramp should reject tracked motion while the gentle ramp permits
useful uphill/downhill and reverse. No uniform speed multiplier or isolated
center derivative can establish whole-body slope behavior.

World height, LOS, projectiles, ground surface samples and both rendered terrain
height functions must consume the same relief. The CPU height entry is
`src/nav/terrain.asm:terrain_height`; derivatives currently live separately in
`src/nav/terrain_surface.asm`. Both `shaders/battle.vert` and `shaders/mesh.vert`
define the current height expression. Production projectiles, aircraft clearance,
player eye/motion and nav waypoints already call the CPU height entry. Audit the
actual register assumptions when inserting a new helper call: the present leaf
height routine clobbers XMM0–3, and some callers may retain values in other
caller-saved SIMD registers. A SysV-valid callee alone cannot prove those callers
remain correct. Preserve established behavior or repair and verify each caller. Extend the content fingerprint with
canonical relief and grade policy. Static data needs no mutable profile state;
if profiles later become selectable, initialize, hash and save that authority and
advertise join compatibility. Do not store physical policy in cosmetic weather.

Navigation needs reachable bypasses and role constraints alongside grade rejection.
The current 22-node graph is derived from five solid obstacles and uses shared
artillery-conservative corridor checks. Rejecting a ramp without routes around it
can strand vehicles that can reach the plateau from its gentle side. Preserve
bounded path work, original arrival deadlines and real actor health; do not move
or flatten hazards to manufacture progress. Independent proofs must include full
body edges, intermediate steep crossings, cusp sides, useful ascent/descent,
reverse, invalid inputs, player-to-AI handoff, exact replay and unchanged 8k/16k
95% useful motion and 400-tick health symmetry.

The isolated component passed 6,201 actual NASM height/gradient samples, ten invalid
inputs, 52 generator negatives preserving both outputs, read-only/ABI checks,
deterministic generated record identity and real GLSL compilation. Two actual-NASM
negative candidates were rejected. Compilation is not GPU execution; this proof
establishes no integrated slope or rendered-height behavior.

Oriented hulls, vertical interactions, suspension, wheeled chassis, traffic/road
preferences, damage handling and useful wreck cover remain required independently.
The complete operation, army intelligence, streaming, Windows, runtime jobs,
recorded audiovisual craft and four-client hardware acceptance also remain open.
