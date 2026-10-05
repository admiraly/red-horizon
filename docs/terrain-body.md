# Static terrain body sweeps

`src/nav/terrain_body.asm` implements the private footprint APIs in
`schemas/terrain_body.inc`. Point terrain, line-of-sight and projectile APIs are
unchanged. The module reads the authored static obstacle table and ground-solid
flag, uses closed segment slabs against expanded XZ AABBs, and keeps ground
centers inside the map by their footprint radius. Nominal infantry/player, tank
and artillery radii are 0.55, 3.55 and 4.49 metres. The terrain queries inflate
these by one millimetre to prevent float rounding into nominal tangent geometry.
Air has radius zero, finite/map validation, and delegates its existing direct
movement without ground-solid collision.

Movement retains the actual long goal, selects the nearest intersecting expanded
box, approaches a corner outside its footprint, crosses the far corner, and
resumes toward the goal. A start above/below a wall but inside its X
projection first rounds the current-side corner instead of creeping sideways
against the wall toward the far edge. Corner clearance is another 0.5m. Each accepted full
step or component slide receives an independent body sweep before it is returned.
The requested step bounds actual distance; inputs reject invalid roles,
non-finite positions, coordinates outside [0,8000], and nonpositive, non-finite
or greater-than-8000m steps. Goals at the map edge are clamped to the body inset.
Already body-invalid starts hold their original position; no teleport or
penetration recovery is claimed. Obstacle-interior goals can be approached by
detours/slides, but arrival inside an obstacle is deliberately impossible and
progress to every such goal is not guaranteed.

The conservative AABB enlargement rejects some rounded corner paths that an
exact circle could traverse. Terrain height/slope physics and oriented vehicle
hulls are not implemented by this module. Multi-obstacle maze completeness is
not proved; the current authored five-box routes are covered. Runtime cost is
bounded by the static obstacle count, without allocation or persistent routing
commitments. The sole hashed state is the four bytes of `terrain_body_enabled`;
initialization restores 1. Setting it to zero delegates the existing point
terrain APIs, which supplies an explicit causal control. No diagnostics or
shared table writes are introduced.

Verification command:

```sh
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_terrain_body.py
```

The self-building development test assembles the actual module, existing terrain
and NASM probe into a private temporary shared library. Seed 19381 checks 6,000
random path-query inputs and 5,987 actual movement sweeps with an independent
double-precision expanded-box oracle. Sixteen routes arrive across the central
wall, from its edge, and past the nearer bunker and central wall, at infantry
0.12, tank 0.5, artillery 0.2 and driven-tank 0.6m steps. Exact successful route
tick counts are emitted in the JSON report. Additional checks cover nominal
wall tangency and 2mm clear parallel travel, wall faces/sides/corners, map insets,
invalid starts, malformed/non-finite input, air bypass, nominal footprint versus
legacy point collision, nonvolatile SysV registers, exact enabled-state FNV
bytes and unchanged static obstacle bytes. These are module-level results;
production integration, world navigation, player/driver collision and large-army
performance belong to separate root verification.

The wall-edge route from (4000,1506) to (4050,1000) additionally has a useful
travel bound of 600m plus 50 normal steps. A verified correction reduced its
arrival ticks from infantry 15,154/tank 3,873/artillery 10,006/driven tank 3,236
to 4,302/1,043/2,614/870, while retaining independent swept clearance on every
step and every other route/random/ABI/hash/input check. This is isolated module
evidence, not a measured full-world performance claim.

`terrain_body_step` supplies controller movement with the same input validation,
map inset, normalized step bound, complete swept-body checks, component slides,
invalid-start holding and legacy control. It skips autonomous corner routing:
pure X or Z commands cannot introduce the other axis, and diagonal commands may
slide only along their requested components. Its mode is stack scratch, not new
hashed state. The actual NASM probe verifies 400 controller ticks: infantry at
0.3m and tank at 0.6m approach a wall with exact unchanged Z, diagonal input
slides along the wall, and map-edge approach preserves the uncommanded axis.
Both APIs pass callee-saved ABI checks; disabled controller calls match legacy
point movement exactly. Existing route/random sweeps remain green. Production
controller wiring and world outcomes still require root integration checks.
