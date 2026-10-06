# Intermediate-pose five-point contact prerequisite

`src/nav/ground_contact.asm` implements the frozen root-owned
`schemas/ground_contact.inc` v1 ABI. For supplied heading, pitch and bank it
constructs the exact yaw × pitch × bank frame, rotates both chassis rectangles
including their local Y displacement, and validates every projected corner
before querying terrain. The contact floor is the maximum of centre height and
four actual projected-corner terrain heights minus their rotated local Y.

The 64-byte result preserves supplied pitch/bank, sets the valid flag, publishes
all three frame axes, and canonicalizes each vector's fourth lane to positive
zero. The output publication follows input, corner, terrain-sample and final
finite checks. Invalid input preserves every output byte; malformed coordinates
or off-map projected corners make zero terrain queries. Valid cases make exactly
five queries. There is no writable module data, authority mutation, allocation,
physics change, persistent sidecar, tool hook or renderer integration.

Focused proof command (development Python only):

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_ground_contact.py
```

Verified on 2026-10-06 in isolated `ground-contact` worktree, root contract base
`299ec6f`:

- 7,296 actual CPU-height observations across tank/artillery dimensions, world
  and local seeded samples, ridge/relief cusps, crests, gentle/rising faces,
  combined corners, intermediate angles and both pitch/bank angle boundaries.
  Eight hundred observations use independently seeded random intermediate angles.
- Independent matrix multiplication checks the entire frame within `3e-7`;
  orthonormal dot products and right-handed cross products within `5e-7`.
  Projected-corner terrain samples independently match the mathematical authored
  world height within `2.5e-5` m.
- The strict CPU contact observer retains actual binary32 projected coordinates
  and the independently verified output frame. Maximum contact-floor difference
  is `3.814697265625e-06` m, against a `2e-5` gate. A separate double matrix and
  analytic-height observer has maximum difference `0.0002111147449568307` m,
  against a `0.0007` gate: kilometre-coordinate binary32 rounding changes steep
  face sample heights. This latter allowance is coordinate arithmetic, not an
  accepted vehicle penetration budget.
- Sixty-eight malformed/null/off-map cases preserve the complete 96-byte output
  guard record and make zero terrain calls. Role/capacity, each finite coordinate
  and angle, angle limits and projected-corner bounds are covered.
- A separately assembled nonfinite-height stub is rejected without publication;
  its ABI and stack alignment also remain intact. It is explicitly a fault
  fixture, not evidence about authored terrain.
- Assembly probes check all six SysV nonvolatile GPRs and unchanged caller stack.
  Actual `sinf`, `cosf` and terrain-call link wrappers report zero misalignment.
- Three actual assembled faulty kernels are rejected: upright-only contact frame,
  omitted rotated local Y, and wrong bank rotation. These controls exercise the
  intermediate-pose requirement, rather than validating a named code path.

Final executed proof JSON/log: `/tmp/rh-ground-contact.log`.
Initial probe-assembly diagnostic: `/tmp/rh-ground-contact-initial-probe.log`.
That initial development attempt retained an obsolete one-argument test wrapper
macro while adapting the prior ABI probe. Removing the unused wrapper fixed the
probe; no production contract or acceptance gate changed. Every command has
finished; no background sessions or jobs remain.

Kernel source SHA-256:
`46c3f632099fa0957bc7d3e0d072c7e4a080e631d896457cb0bb5ba40b799ed6`.
Executed focused proof library SHA-256:
`d6dfb5daa4631ce1bb5bbbd7af7a5533bfc6b285f62ddaf2308dbf6c3561ebc1`.
The observer builds frozen temporary proof libraries, prints the executed hashes,
and removes the temporary artifacts afterward. It does not claim retained binary
availability or identical linked bytes across toolchains.

This is a verified prerequisite for correcting the rendered height after cosmetic
angle smoothing. It is still only a five-point contact floor: it does not prove
clearance of the complete chassis mesh between samples, physical suspension,
oriented collision, renderer/LOD integration, Windows, target-GPU performance,
human craft acceptance or whole-game suspension completion. Root owns integration
and system-level verification.
