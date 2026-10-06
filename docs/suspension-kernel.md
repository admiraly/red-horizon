# Cosmetic critical-damping kernel prerequisite

`src/render/suspension.asm` implements the root-owned `schemas/suspension.inc`
v1 ABI unchanged. It updates only caller-owned, derived presentation state.
Three independent axes use the specified closed-form critically damped position
and velocity response, with platform `expf` and NASM x86-64/SSE2 arithmetic.
Post-evaluation position/velocity clamps and elapsed-time saturation remain
bounded. No allocation, simulation state, authoritative motion or renderer hook
is introduced.

Targets are copied before publishing, including overlap with state. Validation
covers pointer presence, capacity, stamps, flags, dt, target scalars and matching
active state scalars. Inactive/stale stamps initialize directly without reading
old dynamic values. Matching active `dt=0`, including negative zero, preserves
every byte after validation; initializing a stale state remains allowed at dt0.
All rejected calls preserve the complete state. Nonzero updates and initialization
canonicalize padding, with generation/kind/flags retained or stamped as specified.

Focused proof command:

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_suspension.py
```

Verified on 2026-10-06 in isolated `suspension-kernel` worktree, base `e639ebb`:

- 3,462 kernel/probe calls cover 2,500 seeded analytical single-step cases,
  dt boundaries, extreme positions/velocities, explicit outward boundary clamps,
  time saturation, settling, aliases, stamp recycling and invalid inputs.
- Independent double closed-form expectations use `rel_tol=4e-6`; absolute
  tolerance is `5e-4` for Y/vertical velocity and `2e-6` for angular quantities.
  Maximum single-step absolute errors (Y, pitch, bank, then velocities):
  `[0.0004602474932653422, 3.3220884221307756e-07,
  3.5099082928979897e-07, 3.9264536241034875e-05,
  1.3739384439048763e-06, 1.6893837484488472e-06]`.
  These tolerances describe float computation, not terrain contact allowance.
- Repeated analytical step response and settling run at 144/60/30/10 Hz.
  Equal-duration partitions of 10/20/30/60/120/144 updates differ by at most
  `1.0056843962047424e-06` against a `3e-6` gate. This partition property is
  tested only without active clamps; nonlinear clamping does not preserve it.
- Sixty-six malformed/null cases preserve every state byte, make no `expf`
  call, and cover every live scalar, dt, role/capacity/flag restrictions.
  Inactive/stale states with poisoned positions, velocities and time initialize
  successfully; matching active zero dt preserves arbitrary padding bytes.
- Alias cases cover target=state positions and target overlapping velocity
  storage. State guards and separately allocated target bytes remain unchanged.
- Assembly probes verify all six SysV nonvolatile GPRs and caller stack.
  Actual `expf` link wrappers report zero misaligned entries; nonzero active
  steps call `expf` exactly three times; initialization/zero dt call it zero times.
- Three actual assembled faults are rejected: replacing exponential response,
  reversing the damping velocity term, and reading inactive poisoned dynamics.
  The initial stale-reading mutation bypassed the loop initialization rather
  than exercising the intended fault and escaped its fixture. The initial log
  is retained; correcting that mutation made the causal control reject. The
  production kernel and acceptance tolerances did not change.

Final JSON/log: `/tmp/rh-suspension-kernel.log`.
Initial negative-control diagnostic: `/tmp/rh-suspension-kernel-initial-negative.log`.
All proof commands completed; no background jobs or sessions remain.

Kernel source SHA-256:
`3e5fb2c016ef2a9651319b012774994d39167e9c2a200487e464984b248663df`.
Executed focused proof library SHA-256:
`9878f637df806b952792906c1d6e835297304c1ef261b463936183038d1e87d2`.
The development observer builds immutable temporary proof libraries, reports
executed artifact hashes, then removes them. Hashes do not assert retained binary
availability or reproducible linked bytes across temporary source filenames.

This is an isolated cosmetic response prerequisite. It does not establish real
vehicle suspension, terrain contact, gameplay physics, integrated rendering,
Windows support, full-suite safety, target-GPU quality or human visual acceptance.
**Root must recompute support/contact height for the smoothed angles before
rendering.** Smoothing the prior support Y alone cannot ensure terrain clearance.
