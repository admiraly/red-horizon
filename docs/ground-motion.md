# Shared tracked ground-hull motion

`src/game/ground_motion.asm` implements the root-owned 32-byte
`schemas/ground_motion.inc` contract for living tanks and self-propelled artillery.
It has no allocations and uses NASM x86-64/SSE2, with platform `atan2f`, `sinf`
and `cosf` calls. It preserves SysV nonvolatile registers and maintains 16-byte
call-site stack alignment. Root owns world/driver integration and build lists;
this worker module alone does not establish that the operation uses it.

At 30 fixed ticks/second, ordinary tank/artillery forward limits are 0.5/0.2
metres per tick; a legitimate human tank driver may request 0.6. Tank acceleration
is 0.02 and braking 0.04 metres per tick per tick; artillery uses 0.01/0.025.
Human tank reverse is limited to 0.18. The artillery tuning reserves 0.08
for future explicit reverse-capable control; the current strict human claim accepts
only tanks. An opposite signed driver request first brakes through
zero; no-input requests brake rather than erase momentum. Shared physical tank
speed up to 0.6 survives driver/AI handoff and returns to the AI target through
bounded braking. Boarding and exiting do not reset the sidecar.

Heading zero faces +Z and positive rotates toward +X. Stopped tanks can pivot
0.06 radians/tick, moving tanks 0.04; artillery uses 0.025 in either case. A
steering error above 0.7 radians requests zero target speed, producing a tracked
pivot after braking. Human requests more than 135 degrees behind the hull select slow
reverse with a bounded steering adjustment. AI navigation detours always select
forward pivots, so rearward local avoidance intent does not lock opposing vehicles
into slow reverse/brake oscillation at a wall. Steering does not use a camera;
root passes the intended world steering point. Clear displacement follows the
actual post-turn hull axis, with world-coordinate float rounding. Stopped hulls
keep their facing. Zero values are canonicalized to positive zero.

Initial/recycled valid tank and artillery records seed headings toward their
actual side/front route waypoint. Generation or role recycling clears momentum
and stamps the new record. A same-generation AI/driver transition uses existing
heading and speed. Invalid count, ID, living state, role, side/front, finite input,
source pose, requested step or driver claim leaves persistent state unchanged.
A driver must have a connected living generated player, allied living tank,
matching entity generation, the stamped driver player generation and all
bidirectional ownership records. Same-slot recycled players cannot inherit control. Corrupted
same-generation sidecar floats, limits or flags also hold without mutation.

AI uses the existing bounded `crowd_move` result only as a local steering intent.
The actuator then turns/accelerates and calls `crowd_hull_step` with the complete
physically reachable segment, mode and absolute signed-speed budget. It accepts
only the exact endpoint, never a component slide or a normalized substitute.
Contact holds source position, zeros speed/velocity immediately for safety, and
retains the bounded heading pivot. Returned partial or malformed query endpoints
also hold. Policy `ground_enabled=0` calls actual legacy `crowd_move`/`crowd_step`
and leaves sidecar state unchanged, providing a development causal control.

`ground_hash` hashes the policy and every byte of all 32,768 persistent records,
including inactive tails, into the caller FNV accumulator. This adds 1 MiB of
checksummed authoritative state; its total integrated checksum/tick cost requires
root scale measurement. Diagnostics are not invented as future state.

Verification command:

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tests/test_ground_motion.py
```

The terminal worker run `/tmp/rh-ground-motion-worker.log` passed 12 actuator
groups and 42 malformed cases. The first library deliberately stubs collision
with explicit clear/blocked/partial results and legacy normalized movement; it
proves actuator math, ABI, state preservation, ownership, handoff, generation
recycling and byte-for-byte FNV behavior, **not production collision**.

A second independently linked library uses the actual production crowd, terrain
and terrain-body modules. Five scenarios passed: 100 ticks each against held
infantry/tank/artillery (minimum swept gaps 4.239990, 7.719971 and 8.260010 m),
150 ticks approaching the production terrain wall (tank ends X3984.429688 before
wall X3988 with radius3.55), and driver-to-AI momentum 0.600000→0.560000 m/tick.
The observer checks actual hull-axis motion with coordinate rounding tolerance
0.0003 m and physical step tolerance0.0005 m, below the collision API's documented
0.001 m allowance. No test mutates authoritative army positions inside the
actuator; the development harness publishes returned endpoints between ticks.
These prove linked kernels, not world hooks, network, graphics, scale or target
hardware acceptance. Root must add the module to those actual paths and verify.

Remaining physical scope includes oriented hull footprints, suspension, wheeled
chassis, road/off-road traction, slopes, wreck collision and damage-dependent
handling. This tracked approximation does not claim those features or complete
vehicle realism. Finite same-build math does not establish cross-platform
bit-identical floating-point replay. Actual screenshot/GL appearance, packet
heading replication and Windows runtime calls require root integration evidence.

Followup wall recovery uses the unchanged actual-world 1200-tick tactics fixture:
two tanks begin X3984, Z1300/1330 against the solid X3988..4012. AI forward-pivot
preference allows both to traverse bounded clear segments around opposite wall
ends; observed final X4221.823730/X4215.236816. The old automatic AI reverse
selection oscillated and failed that original recovery gate. Driver reverse
semantics are unchanged. Full tactics and integration evidence belongs to root.
