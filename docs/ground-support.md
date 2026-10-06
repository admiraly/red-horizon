# Stateless ground support kernel

This worker implements the root-owned `schemas/ground_support.inc` v1 ABI in
`src/nav/ground_support.asm`. It publishes a 64-byte cosmetic pose only after
validating kind, capacity, finite position/heading, every rotated corner's map
bounds, and finite final output. Four actual CPU terrain heights fit longitudinal
and lateral slopes; a fifth at the entity centre sets a minimum support height.
The fitted base is raised to cover positive corner residuals. Tank/artillery
support dimensions and the frame order come from the shared ABI unchanged.

The axes are the columns of yaw × pitch × bank, exactly matching the existing
mesh shader convention. Their fourth lanes are canonical positive zero. No
writable module data, authoritative motion state, collision changes, entities,
network record or persistent sidecar are introduced. `sinf`, `cosf` and `atan2f`
are existing permitted platform libm calls; all project CPU code here is NASM
x86-64/SSE2.

Focused proof command (development Python only):

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_ground_support.py
```

Verified on 2026-10-06 in isolated worktree `ground-support-kernel`, base
`f8232ef`, with no runtime caller integration:

- 9,712 actual production-height observations across both chassis, four headings,
  shallow world terrain, ridge and relief breaks, central rising/gentle falling
  hill faces, combined corners and seeded full-map/local samples.
- Eight exact flat-height stub observations separately exercise zero tilt. They
  are explicitly not world-terrain observations.
- Independent double mathematical terrain checks and fitted-plane observations
  using actual CPU-height samples; maximum base/pitch/bank differences were
  `1.0042908641594295e-05` metres, `1.0530724088853027e-06` radians and
  `1.2796113554869315e-06` radians. Actual queried binary32 positions are retained
  because rounding kilometre coordinates changes samples.
- All three axes agree with independent matrix multiplication within `3e-7`;
  dot products and right-handed cross products within `5e-7`. Each tested fitted
  corner and centre satisfies its sampled-height support bound within `3e-5` m.
- Fifty-eight invalid cases including null output preserve the output; capacity,
  roles, infinities/NaNs, bounds and off-map rotated corners are covered. Invalid
  cases make no terrain queries. Successful calls make exactly five queries.
- The assembly probe checks all six SysV nonvolatile GPRs and unchanged caller
  stack. Actual link wrappers record zero misaligned terrain/libm entries.
- Three independently assembled faulty implementations are rejected: flat pitch,
  wrong forward-axis sign, and centre-only height. The first development negative
  fixture did not distinguish centre-only height at one local face; the preserved
  initial log records that failure. Adding actual cusp/ridge samples distinguished
  the fault; production implementation and acceptance tolerances were unchanged.
- A separately linked complete simulation with 8,192 real entities and eight
  ticks retains world checksum `a7d5f9699df660cc` across valid/invalid support
  queries. This is read-only evidence, not a throughput/scale benchmark.

Final focused JSON/log: `/tmp/rh-ground-support-kernel.log`; initial diagnostic:
`/tmp/rh-ground-support-kernel-initial-negative-fixture.log`. All commands were
foreground terminal jobs and returned zero for the final proof; none remain live.

Kernel source SHA-256:
`bb6dbe014a499c309c3f9991aebe21e595e9cdfe6fe993f6649f7c06fd0d9651`.
Focused proof library SHA-256:
`bf416a8f4c419c3df32ff8b3a00e5ca5a65d1becd033315608595e628c4615af`.
Complete-world proof library SHA-256:
`262f3800137e19538c0540fcad2e8039d0bc62639eceecd34548957bece70934`.
The observer creates immutable temporary libraries, prints their hashes, and
removes them after completion; these hashes identify executed artifacts, not
retained binaries.

This is a verified prerequisite kernel. It does not itself tilt rendered vehicles,
provide suspension, move players/cameras, implement oriented collision, change
physics or networking, or prove entire mesh clearance between five sample points.
It makes no renderer, target-GPU, Windows, human craft or full-suite claim. Root
owns integration and its matching whole-system verification.
