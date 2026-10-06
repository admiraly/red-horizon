# Whole-body terrain grade kernel

This isolated prerequisite implements the root-owned v1 contract in
`schemas/terrain_grade.inc`; it does not hook production movement or navigation.
`terrain_grade_clear(EDI role, XMM0/XMM1 startXZ, XMM2/XMM3 endXZ)` returns 1
clear, 0 blocked, or -1 invalid. Roles are 0 infantry, 1 tank, 2 artillery,
3 aircraft. All four float32 coordinates must be finite and inside [0,8000].
Aircraft bypass ground constraints after validation. Ground circles extending
outside the map return blocked.

The helper conservatively encloses the entire swept circle in an expanded
segment AABB, using precisely the shared float32 inflated sweep-radius macros
from `terrain_body.inc`: 0.551m, 3.551m and 4.491m. It clips that AABB against
all nine CLOSED relief facets and checks all four corners of every intersection.
Closed facets check both one-sided derivatives at outer edges and plateau cusps,
rather than treating the height sampler's chosen zero cusp derivative as a
traversability guarantee. Zero-length sweeps still evaluate the full footprint.

Within each facet, the combined bowl-plus-relief gradient is affine:

```
dx = 0.000002 * (x-4000) + a*z + b
dz = 0.000001 * (z-4000) + a*x + c
```

Squared norm of an affine vector is convex, so its maximum on the clipped
rectangle is attained at a corner. The actual acceptance check is total
`dx*dx + dz*dz + 0.000001 <= roleLimitSquared`, using baseline scalar SSE2 double
geometry. The guard accounts for float32 sampler error. The root policies are
proposed practical 45° infantry, 35° tank and 25° artillery limits, rather than
angles specified by the product document. This is conservative: diagonal/corner
AABBs contain terrain outside the actual swept capsule and can block otherwise
traversable sweeps. It is not a general triangle-mesh collision solver.

The NASM routine has no calls, heap allocations, authority writes, persistent
state or mutable scratch. It preserves SysV callee-saved integer registers;
caller-saved integer/XMM registers may change. Work is bounded by nine facets
and four corners per facet. Generated records are read-only 64-byte rows with
seven float64 coordinates/coefficients and one uint64 active flag.

## Canonical generation invariant

`tools/terrain_grade.py` imports the existing development-only relief validator,
so the breakpoints and height first undergo precisely the canonical float32
conversion. It expands the nine piecewise bilinear patches into analytic
coefficients and emits round-trip float64 literals. The generator rejects
malformed input before replacing its output, uses a temporary file plus atomic
replacement, and supports `--check` without writes. Output bytes are deterministic.

Grade-valid support must lie entirely outside the triangular ridge interior
X3200..4800. The canonical hill at X5400..5820 satisfies that invariant. A generic
height-generator-valid field crossing the ridge is rejected by this generator,
since its nine-facet formula would otherwise omit the ridge derivative. Root
must run both height and grade generation checks during integration. Left-of-ridge
support ending at X3200 and right-of-ridge support starting at X4800 remain valid.

Outside relief, the existing bowl/ridge derivative norm is bounded by
`sqrt(0.0225² + 0.004²) = 0.02285278976405288`, below 0.023 and far below all
role limits. Inside the ridge, bowl slope opposes the triangular ridge component;
outside it the bowl X derivative is at most 0.008. The generator reads the
root-owned base/cap/guard constants and rejects an incompatible base formula,
negative/nonfinite guard or policies too low to safely clear this global shallow
base. This does not infer a steep-terrain restriction from the cusp sampler alone.

## Exact focused evidence

Final focused command:

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_terrain_grade.py
```

Session 15340 exited 0 and was collected. Log `/tmp/rh-terrain-grade-final.log`;
actual temporary NASM shared-library SHA256:
`cdfb2c226c8c737e60158c70b1fd97ca44a16169e79553c70519b796b0dfa0bb`.
Worker base is `44ac278`; runtime source SHA256:
`6b0054c2196a2fe96c303df9d9df002e560fa22ccd8d854c0c24d3340f3ac072`.
Generated table SHA256:
`83b27c6515c2774af01aea59a57663be68920a20f0f7d86bc133e96e4681b36f`.

The harness assembled the real NASM helper and ABI probe and checked 4,193 actual
calls: 3,819 clear, 292 blocked and 82 invalid. Independent expected gradients
are calculated from piecewise field factors, rather than the generated runtime
coefficients. Evidence includes 4,000 seeded local sweeps, every pair of four X/Z
breakpoints for all four roles, map-footprint bounds, invalid role/NaN/Inf/off-map
arguments, gentle south/east approaches, steep central ramp, closed cusp sides,
combined gradient components and intermediate steep terrain with BOTH endpoints
independently verified clear. Input bytes and all nine read-only facets/count
remain unchanged; SysV preservation is checked on every call. Assembled
coefficients match independently expanded canonical float32 source values.

Actual private NASM causal variants establish the negative controls:

- Replacing only footprint radii with zero accepts plateau centers at (5482,5200)
  that the real tank/artillery circles correctly reject.
- A tiny canonical relief height accepts the central ramp that the actual 64m
  relief rejects for a tank.
- Removing only the 1e-6 guard accepts a generated near-limit tank corner that
  the real guarded helper blocks.

Nineteen malformed source cases, including ridge-intersecting support, leave the
old generated output byte-identical. Three incompatible private cap/base/guard
contracts also reject without replacing the old output. Deterministic regeneration,
stale-output rejection and positive left/right ridge-boundary controls pass.
Earlier focused sessions 50274, 34900 and 53089 also exited 0 and were collected;
only the final log above is the complete current-source proof. No background
handles remain live.

Root owns body/path/manual movement hooks, bypass navigation, actual integrated
height, renderer, content compatibility, build registration and full checkpoints.
This standalone kernel establishes none of those production or 8k/16k scale
acceptance claims by file presence.
