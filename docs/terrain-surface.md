# Stateless terrain surface data and sampler

This bounded standalone slice adds canonical roads, deterministic generated
NASM/GLSL tables and a real NASM surface sampler. It does not alter existing
terrain, movement, navigation, rendering, network or build hooks.

The root-owned v1 contract is `schemas/terrain_surface.inc`:
`terrain_surface(XMM0 X,XMM1 Z)` returns the existing terrain height in XMM0,
analytic partial derivatives in XMM1/XMM2 and EAX center class: 0 off-road,
1 paved road, -1 invalid. Coordinates must be finite and inside [0,8000]. Invalid
inputs return three canonical +0 floats. SysV preserved integer registers remain
intact and the sole `terrain_height` call is stack aligned. There are no heap
allocations, persistent scratch, authoritative writes or new future state.

The sampler calls the unchanged production `terrain_height`. Its gradient is
that height's smooth quadratic derivative plus the triangular ridge derivative.
At the ridge apex X4000 and its nondifferentiable endpoints X3200/X4800, the
ridge component's derivative is explicitly chosen as zero; the quadratic base
derivative remains. This chosen value cannot establish conservative slope or
footprint clearance. Current terrain remains shallow, below approximately 1.31°.

`content/terrain/roads.json` authors 19 capsule segments with paved half-width
10m. Three front roads at Z1300/3900/6500 each have five segments:

```
(1000,z) -> (3800,z) -> (3920,z-250) -> (4080,z-250) -> (4200,z) -> (7000,z)
```

Four connector segments at X1000/X7000 join Z1300→3900→6500. The doglegs route
around the existing ridge walls rather than classifying the currently painted
straight gravel strips through those walls as traversable roads. Classification
uses the closest clamped point on each segment and an inclusive capsule radius.
It describes the queried center, not the fraction of a hull in road contact.

`tools/terrain_surfaces.py` validates the complete document before writing either
output. It accepts schema v1, 1..19 records, finite float32 map endpoints, paved
half-width 0.001..8000m and segment length at least 0.001m after float32 rounding.
Flags must be exactly integer 1. Zero, rounded-zero and sub-millimeter segments,
underflow/oversized widths, NaN/Inf, booleans, incorrect shapes and unknown fields
are rejected. Numeric lower bounds keep squared segment lengths normal and
squared widths finite in SSE2 and GLSL. Both temporary outputs are prepared
before per-file atomic replacement; malformed input leaves both old outputs
unchanged. This is not a crash-atomic transaction across two separate files.

Generated `schemas/terrain_roads.inc` exports read-only `terrain_road_count` and
`terrain_road_segments` with six fields per 24-byte record. Its count is checked
against the compile-time 19-record limit. Generated `shaders/terrain_roads.glsl`
contains identical records and a bounded distance/contains helper, ready for
later embedding by the integrator. Neither existing production shader includes
it yet. Regenerate or verify with:

```
python3 tools/terrain_surfaces.py
python3 tools/terrain_surfaces.py --check
```

Focused evidence:

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_terrain_surface.py
```

Final session 91660 exited 0; log `/tmp/rh-terrain-surface-bounded.log`. The
harness assembled the real sampler and unchanged terrain module, linked a private
shared library and checked 2,806 valid points: 19 centers, 42 inside/exact edges,
38 outside edges, 152 endpoint-cap points, 38 junctions, eight explicit off-road
points, 2,500 independent seeded random points and nine ridge cusp points.
Height matched production terrain bitwise; analytic gradients matched independent
double-precision math. Eight invalid-input cases returned -1 and canonical zeros.
SysV register preservation and read-only road bytes passed throughout.

Independent segment/rectangle geometry verified every canonical road capsule,
including the full paved width plus the largest current hull radius 4.49m,
against all five original solid AABBs and map insets. Minimum remaining solid
clearance was 35.51m. That evidence applies to these 19 canonical records, not
every future generator-valid road table, dynamic bodies or site structures.

Twenty-seven malformed generator cases left both existing output files identical.
Positive controls accepted the 0.001m length/width boundary and finite 8000m
maximum width. Independently parsed canonical, generated NASM, generated GLSL
and assembled runtime records matched. Real regeneration was byte deterministic;
`glslangValidator` compiled the helper in a GLSL450 fragment wrapper.

Earlier sessions 62755 and 65728 also exited 0, logs
`/tmp/rh-terrain-surface-first.log` and `/tmp/rh-terrain-surface-final.log`; the
final run adds arithmetic range guards requested during root review. All sessions
were collected. No production integration, road speed, road-preferring navigation,
steep-map acceptance, terrain-profile state, network compatibility or full-scale
checkpoint is claimed. Root owns the eventual hook integration and NET_CONTENT
change; current wire/entity/ground-motion layouts are untouched.
