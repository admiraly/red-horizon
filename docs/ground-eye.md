# Prepared terrain-supported legacy eye kernel

`src/nav/ground_eye.asm` implements the frozen root-owned
`schemas/ground_eye.inc` v1 ABI. It queries unsmoothed `ground_support`, queries
`ground_contact` using those exact angles, chooses the greater support/contact
base Y, and transforms the retained local `(0,3,0)` gameplay eye with the support
frame's UP column. The 3 m value is inherited gameplay policy, not a measured
cockpit socket.

The query writes only its caller's 12-byte XYZ result, after finite/map/height
checks. Null/capacity rejection occurs before helper calls. Support/contact
validate role, entity XZ, heading and their respective projected footprint.
No entity/player generation is supplied to this stateless ABI: a future caller
must validate ownership, live player/entity generations and motion stamp first.
There is no authority/cache write, allocation, dt, spring, renderer or vehicle
hook in this prepared component. External helper calls retain SysV alignment and
nonvolatile GPRs; all authored CPU arithmetic is NASM x86-64/SSE2.

Focused command (development-only observer):

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_ground_eye.py
```

Verified on 2026-10-06 in isolated `ground-eye` worktree, root-owned contract
base `38ae5f4` (runtime base `71c61c7`):

- 6,488 actual queries across both retained chassis dimensions, four headings,
  full-world/local seeded samples, ridge and relief cusps, crests, combined
  corners, rising/gentle faces. Every successful query made exactly ten terrain
  calls before the development observer's separate reference queries.
- Independent double fitted-plane and matrix expectations use actual CPU
  terrain samples, independently checked against the authored analytic height.
  Maximum XYZ differences were `[0.0002460007244735607,
  0.0001194279703966572, 0.00024721088993828744]` m, within `0.001` m.
  Kilometre-scale binary32 coordinate arithmetic accounts for this allowance.
- A separate strict composition check requires bitwise float equality to
  `entityXZ + 3*UP.xz` and `max(actualSupportY,actualContactY)+3*UP.y`.
  This supplements, rather than replaces, the mathematical reference.
- Actual rotated contact corrected the support base by as much as
  `0.05292510986328125` m at tank X5478.416015625/Z5376.85693359375,
  heading float32 pi. Thus omitting the corrected contact floor is observably
  wrong on the authored world, not only on a fabricated dependency fixture.
- Fifty-eight malformed/null/off-map cases preserve every output/guard byte
  and make zero terrain calls. Role, capacity, finite/bounded XZ/heading and
  rotated support footprint bounds are covered. Valid output is finite with
  XZ[0,8000] and Y[-2000,2000].
- Four explicitly hostile helper fixtures exercise final NaN, out-of-map X/Z
  and excessive Y rejection without publication. A separate helper-composition
  fixture tests a greater contact floor. These are dependency fault tests,
  not additional actual-terrain observations.
- Assembly probes verify all six SysV nonvolatile GPRs and unchanged caller
  stack. Actual helper/terrain/libm link wrappers record zero misaligned calls.
- Three actual assembled faults are rejected on authored terrain: upright eye,
  forward-axis substitution, and omitted contact floor. The last uses the
  recorded actual positive correction case, above the mathematical allowance.

Final JSON/log: `/tmp/rh-ground-eye.log`.
Initial optional-fixture diagnostic:
`/tmp/rh-ground-eye-initial-contact-fixture.log`. That development assertion
incorrectly assumed the largest contact correction would exceed0.1 m; measured
correction was0.052925 m. The production implementation was unchanged. The final
negative control uses the actual recorded case, requiring a correction above the
existing0.001 m observer allowance, and rejects the omitted-contact fault.
No pre-existing project acceptance gate was weakened. All commands are terminal;
no sessions/jobs remain live.

Kernel source SHA-256:
`e276a00e08d989e8c62f8bf57288444a8dfcf2370781454efda011b27aa235ec`.
Executed focused library SHA-256:
`5fd75289a37b5009d8b6ee522616f72ba890e0dd4876f54442d3186b6a7e66b6`.
The observer assembles frozen temporary artifacts and prints their executed
hashes before removing them. It does not claim retained binaries or identical
linked bytes across temporary source filenames/toolchains.

This component remains **prepared and isolated**. It does not change entry LOS,
boarded player position, cannon targeting/origin, exit policy, prediction, visual
camera, UDP data, replay hashes, chassis sockets or turret articulation. It does
not prove integrated driver behaviour, a physical cockpit, whole-mesh contact,
Windows, target-GPU quality or full-game acceptance. Root owns integration after
the current verified checkpoint and the caller's stale-generation policy.
