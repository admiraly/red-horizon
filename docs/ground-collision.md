# Exact ground-hull collision segments

`crowd_hull_step` is the crowd contract v3 entry for an actuator's already
computed world-space segment. EDI is a living tank/artillery ID; ESI is AI mode
0 or legitimate allied tank-driver mode 1. XMM0/1 are the exact snapshot source,
XMM2/3 the desired endpoint, and XMM4 the maximum segment length. It returns the
same original endpoint or the source, never a normalized, clipped, rotated or
component-slid substitute. It writes no authoritative entity, player or ownership
records. SysV preserved integer registers follow the existing crowd contract.

Sources, generations, roles, driver links, finite map coordinates and positive
finite budgets are checked before querying. The endpoint length must fit the
budget and the role's envelope (tank 0.6m, artillery 0.2m), with an explicit
0.001m allowance for world-coordinate float quantization. This allowance only
accepts or rejects the caller's original floats; it never increases them. Tiny
representable nonzero segments remain exact. Policy-off controls retain source
snapshot validation and the full static footprint/segment test.

The query uses the existing fixed grid and four bounded human records, sharing
the 512 inspected-record limit including distant, invalid or empty human
records. It checks one candidate. Saturation safely holds with diagnostics.
AI mode keeps unchanged-generation immutable human snapshots; driver mode uses
current humans. Generation changes and late join use the existing live fallback.
Terrain rejection or a blocked body sweep holds the whole segment. Existing
partial body overlaps can recover only along a genuinely outward exact segment;
static terrain overlap holds. All tank neighbor snapshots now anticipate 0.6m
regardless of claim, so driver-to-AI braking cannot expose a 0.5m clearance hole.
This may conservatively reduce progress near tanks. Ordinary crowd_move role
speed limits, AI detours and crowd_step controller component slides are unchanged.

Verification uses production NASM crowd, terrain and terrain-body modules through
an independently authored C ABI probe in the development-only Python harness:

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_crowd.py
```

The existing strict crowd gates passed with universal tank anticipation. Added
checks passed for AI tank, driver tank and AI artillery exact short/tiny motion,
zero/invalid inputs, budget/role caps, generation recycling, snapshot mismatch,
invalid count 32769, read-only state and ABI; eleven malformed driver claims;
whole diagonal body blocking with a legal free component; whole diagonal terrain
blocking under both policy settings; retained snapshot validation under policy
off; an unclaimed 0.6m moving-tank neighbor; opposing independent tank proposals;
all ground neighbor roles; immutable AI versus current-driver humans and late
join/generation changes; exact outward overlap recovery; 512-record saturation;
and exact six-record counts translated over three unrelated grid rows.

Kernel logs: `/tmp/rh-ground-collision-oldgates.log` and
`/tmp/rh-ground-collision-exact.log`. Both runs exited 0. The earlier development
run `/tmp/rh-ground-collision-initial.log` exited 1 when a missing jump let the
old controller path fall through into the new exact terrain path; that error was
fixed before both passing runs. Kernel-only timing excludes the full simulation,
renderer, networking and Python per-query assertions. Production actuator hooks,
full replay/scale/graphics/network checkpoints and vehicle steering acceptance
remain integrator responsibilities. No new future state or replay bytes were
introduced; snapshots and diagnostics remain derived and unchecksummed.

Frozen focused integration check at `51cdb7d6f92f3d9dc7f32d40f817957e8476cca3`
(authored source suffix `aa00b12abaaf599c`):

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tools/dev.py test --suite crowd --extended
```

Session 19821 exited 0; `/tmp/rh-ground-collision-focused.log` contains five
explicit passing reports: strict kernel, real-world crowd observer default and
legacy, and controller observer default and legacy. The unchanged current-pose
army census ended with zero sampled overlapping pairs at 8,192-unit FRONT and
HOTSPOT after 120 ticks (initially 110 and 315); this is sampled final-pose
recovery evidence, not universal all-tick collision acceptance. The existing
three-human/one-driver 60-tick checks at 8,192 and 16,384 recorded 226/225 nearby
relative sweeps and 360 controller pair sweeps each, with zero new observed
overlap ticks and 199/200 moving controller ticks. Old production callers are
still in this worker tree; the new actuator itself is exercised only by the
strict exact-segment kernel cases until the integrator installs its hooks.
