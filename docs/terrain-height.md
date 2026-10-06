# Authoritative raised height integration

`terrain_height` now adds the canonical stateless relief component once to the
existing bowl/ridge height. `terrain_surface` obtains that same total height and
adds the component's two analytic derivatives once to the original derivatives.
Road classification and whole-body road queries retain their existing rules.
No grade, navigation, actuator, renderer, tooling-registration or protocol change
belongs to this worker patch.

The old height leaf's observable register behavior is preserved: every GPR and
XMM4–15 remain unchanged. The wrapper saves the two actual GPR clobbers of the
current relief helper, RAX/RDI, and its input/base values in a 24-byte frame.
Call-site alignment remains 16 bytes. Relief uses only XMM0–2, while the base
computation retains its old XMM0–3 scratch behavior. No global or future state is
added. Outside-map and non-finite inputs still evaluate the original base math;
relief contributes canonical zero. The finite/map-invalid `terrain_surface`
contract remains EAX−1 and three canonical zero scalar outputs.

Verification command:

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_terrain_height.py
```

The terminal `/tmp/rh-terrain-height-focused.log` passes 3055 production height
and derivative samples, including combined corner slopes, relief cusps and base
ridge cusps. An independent double-precision observer verifies total height and
both derivatives. Maximum absolute height error is 0.000005819 m; derivative
errors stay below 0.000000077. Surface height agrees exactly with the public height
entry point. A dedicated probe snapshots all 15 non-stack GPRs and all 128 bits of
XMM4–15 for every height sample. Eleven controls compare outside-relief, outside-map
and non-finite behavior bit for bit with a fixed pre-integration assembly leaf,
independent of the candidate source.

The same test builds all actual production simulation/navigation/AI/game sources
and observes actual callers:

- A genuine tank-shell launch at (5430,5200) starts at the raised muzzle height
  41.764900 m and collides with rising terrain at
  (5436.176758,43.739201,5200). The impact is within 0.05 m of authoritative terrain
  height and more than 10 m above the original bowl. No enemy actor causes contact.
- Production `terrain_los` blocks a 40 m high ray across the relief and permits a
  110 m high ray. This proves the existing seven-sample ground path uses raised
  height; it does not establish conservative continuous heightfield ray clearance.
- An actual player tick initializes feet at plateau height 78.970001 m and eye at
  80.770004 m, preserving the standing 1.8 m offset and grounded state.
- A production bomber continuously flies for 110 ticks through the raised field:
  50 observed samples have more than 50 m additional relief. Minimum actual ground
  clearance is 54.811653 m, with unchanged 5 m horizontal steps and at most 0.5 m
  vertical change per tick. This is one measured flight path, not acceptance of all
  aircraft/terrain combinations or collision-avoiding flight planning.

Height-only library SHA256:
`2c3d47a1ce3a898ceedee795ab3726a74e391460361a1534ec2a396446f224fb`.
Actual production-world library SHA256:
`8c559e5a9d64ecd2f6a7cf48df0a754b9d30cf9f64d6e4a437b5b308fb75e457`.
The report records the terrain, surface, relief and probe source hashes.

Existing standalone link lists now require `src/nav/terrain_relief.asm` in addition
to terrain.asm. Root owns registrations in `tests/test_crowd.py`,
`tests/test_terrain_body.py`, `tests/test_ground_motion.py` and
`tests/test_terrain_surface.py`. A private development invocation added only that
link dependency to each original observer, leaving repository files unchanged.
Original crowd, terrain-body and ground-motion checks passed, logs
`/tmp/rh-terrain-height-test_crowd.py.log`,
`/tmp/rh-terrain-height-test_terrain_body.py.log` and
`/tmp/rh-terrain-height-test_ground_motion.py.log`.
The old surface observer correctly fails its base-only height expectation at
(5704.797363,4845.453125): actual raised height 23.641842 m versus old bowl
15.263730 m. This unresolved observer update remains recorded in
`/tmp/rh-terrain-height-test_terrain_surface.py.log`; it is not called passed and
requires the independent total-height expectation without weaker tolerances.

All launched commands reached terminal status before handoff. Original relief and
motion worktrees remain separate and clean. Full frozen root verification,
conservative grade rejection, reachable bypass routing, matching rendered relief,
network content compatibility, massive scale/health/replay and target-hardware
acceptance remain integration requirements. This patch establishes raised authority
and its measured existing callers, not complete vehicle slope behavior or full game
acceptance.
