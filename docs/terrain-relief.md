# Stateless raised-relief component

This component implements the root-owned `schemas/terrain_relief.inc` v1 and
canonical `content/terrain/relief.json`. It is an isolated prerequisite. It has
no hooks into world height, navigation, movement, terrain surface classification,
renderer shaders, content compatibility or development build lists.

The single field uses X breaks 5400/5480/5620/5820 and Z breaks
4800/5000/5400/5600, with height 64 metres. Additional height is the product of
two continuous piecewise linear trapezoids and that height. The 80-metre central
rising X ramp has derivative 0.8; the 200-metre falling X ramp has derivative
−0.32. Each 200-metre Z fade has magnitude at most 0.32. These individual-axis
slopes do not bound combined gradient magnitude: actual point (5479,4999) has
(dX,dZ)=(0.796,0.316), approximately 40.58 degrees. A future whole-body grade
query must account for both components and for intervals crossing factor breaks.

`terrain_relief` takes X/Z in XMM0/XMM1. It returns additional height, dH/dX,
dH/dZ in XMM0/XMM1/XMM2 and EAX=0. Invalid non-finite or outside-[0,8000]
coordinates return EAX=−1 and three canonical positive-zero scalar floats.
Exact factor breaks choose factor derivative zero; this defines a sample result
at a cusp and does **not** establish grade clearance there. Runtime code is NASM
x86-64/SSE2, with private stack only, no allocations, authority writes or future
state. It preserves SysV nonvolatile registers. Call-site alignment is maintained
by a 40-byte frame; the internal factor routine is the only callee. Generated
count and 40-byte field records live in read-only data.

The Python generator is development tooling. It accepts exactly schema 1 and one
field with exactly X/Z four-number lists, height and flags. Float32-rounded axes
must be ordered within the operation, with at least one metre in each ramp.
Plateau width can be zero. Height must remain positive after float32 rounding and
at most 1000; flags must be integer 1. Booleans, non-finite numbers, collapsed
ramps, underflowed height, unknown fields and malformed arrays are rejected.
All parsing, validation and text generation finish before either output changes.
Both temporary outputs are prepared before publication, then individually replaced
atomically. Publication is not a crash-atomic transaction spanning both files.

Commands:

```
python3 tools/terrain_relief.py
python3 tools/terrain_relief.py --check
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_terrain_relief.py
```

The terminal focused run `/tmp/rh-terrain-relief-focused.log` passed 6201 actual
NASM height/gradient samples against an independent double-precision observer,
including all factor breaks, nearby left/right points, combined corners, seeded
regional points and full-map points. Ten invalid coordinate cases returned the
specified canonical zeros; the probe checks all SysV nonvolatile integer registers
and confirms the read-only record bytes remain unchanged. Actual peak is 64 m;
central rising gradient is 0.800000012 (38.659809 degrees), falling gradient
−0.319999993 (17.744671 degrees). Maximum absolute height error is
0.000004365 m, gradient errors below 0.000000059.

The generator rejected 52 malformed documents while preserving both existing
outputs byte for byte. Repeated generation is identical. Canonical floats,
generated NASM/GLSL constants and assembled 40-byte records agree. The generated
helper compiled as an actual GLSL 450 compute shader with `glslangValidator`;
this is compilation evidence, not rendering or GPU execution evidence.

Two private actual-NASM negative candidates establish observer sensitivity:
flat missing relief is rejected for height and rising derivative; inverted rising
derivative is rejected despite the correct height. Their observed values and
library hashes are retained in the same JSON report. Neither candidate is a
production source change.

Verified component source SHA256:
`d565359b13a2bbad4bfd3dfe5146f09ba827216b644a28a768185a8174d5f83f`.
Actual focused library SHA256:
`23fb533858280b20002b303c473d6ead22fa2e70486f8e4e61d1a8a965e2c1dc`.
All launched commands completed terminal before handoff. The original road-motion
worktree remains separate and clean.

Remaining acceptance belongs to the next integration batch: meaningful raised
world terrain, matching actual rendered relief, conservative whole-body/path
slope clearance, role-specific traversal limits, reachable AI bypasses, projectile
and LOS use of raised heights, coherent content-version changes and scale/replay
verification. File presence and this isolated proof establish none of those paths.
