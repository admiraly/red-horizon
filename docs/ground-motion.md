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
steering error above 60 degrees requests zero target speed, producing a tracked
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
Source X/Z must remain within playable [0,8000] metres even when the request
exactly matches a malformed stored entity position; only finite local steering
goals use the wider [-8000,16000] allowance. Initialization skips off-map births.
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

The terminal worker run `/tmp/rh-ground-motion-worker.log` passed 15 actuator
groups and 48 malformed cases. The first library deliberately stubs collision
with explicit clear/blocked/partial results and legacy normalized movement; it
proves actuator math, ABI, state preservation, ownership, handoff, generation
recycling and byte-for-byte FNV behavior, **not production collision**.

A second independently linked library uses the actual production crowd, terrain
and terrain-body modules. Five scenarios passed: 100 ticks each against held
infantry/tank/artillery (minimum swept gaps 4.239990, 7.719971 and 8.260010 m),
150 ticks approaching the production terrain wall (tank ends X3984.433594 before
wall X3988 with radius3.55), and driver-to-AI momentum 0.600000→0.560000 m/tick.
The observer checks actual hull-axis motion with coordinate rounding tolerance
0.0003 m and physical step tolerance0.0005 m, below the collision API's documented
0.001 m allowance. No test mutates authoritative army positions inside the
actuator; the development harness publishes returned endpoints between ticks.
These prove linked kernels, not world hooks, network, graphics, scale or target
hardware acceptance. Root must add the module to those actual paths and verify.

Remaining physical scope includes oriented hull footprints, suspension, wheeled
chassis, slopes, wreck collision and damage-dependent
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

AI arrival applies a range-proportional terminal target speed (0.15 times remaining
metres per tick) before ordinary bounded braking. Remaining range is measured
against the original navigation steering destination, before crowd avoidance
reduces it to a one-tick steering intent. This avoids full-speed goal overshoot
and subsequent long tracked U-turns. Human controls use local wish points, so the
arrival taper applies only to AI. A 60-degree forward steering arc permits tracked
movement while turning toward reachable detours; larger errors still brake and
pivot. Every translated segment still follows the hull axis and passes unchanged
exact body/terrain collision. There is no endpoint snap or arrival teleport.

Terminal followup evidence: `/tmp/rh-ground-motion-approach-focused.log` passed
15 actuator groups, 48 malformed cases and five production-kernel scenarios.
Both roles approached straight fixed destinations over120ticks with0.000183m
remaining error and no overshoot; a human tank using moving1m steering points
retained18m of steady travel over30ticks. These tests distinguish actual arrival
from human wish-point controls.

The unchanged `tests/test_crowd_outcomes.py` ran against frozen private actual
world library SHA256
`1dd16f62e477f999ecfcb4670e11b53d706caf8e2a589fd23f771003d64b6de5`
and passed all original controlled encounter, step, terrain, body sweep, deadline,
arrival, replay and faction-label-swap gates, plus120tick8k dense scenarios.
`/tmp/rh-ground-motion-arrival-crowd.log` records tank240tick arrival error0.000984m,
artillery360tick0.007426m, wall-edge240tick0.000819m and wall-route1600tick0.000953m.
No deadline, target or acceptance bound was changed. Unchanged actual-world
`test_tactics.py` also passed wall recovery1200ticks, physical scouting/defender
capture and8k/16k95%movement/replay gates in
`/tmp/rh-ground-motion-approach-tactics.log`. `test_vehicles.py` retained9.297428m
initial30tick acceleration and18m/s steady drive in
`/tmp/rh-ground-motion-approach-vehicles.log`. These private-world proofs precede
root's latest renderer/protocol/kernel integration; they are not final full
checkpoint or target-GPU acceptance evidence. All worker jobs were collected
terminal before handoff.


Tracked surface handling derives from actual authoritative X/Z using the stateless
`terrain_road_body` helper and the root-owned `schemas/ground_surfaces.inc` v1.
The whole conservative circle must fit inside a single paved capsule: tank radius
3.55 m, artillery radius 4.49 m. Junctions can conservatively classify off-road.
Tank off-road desired speed, acceleration and reverse caps use multiplier 0.8;
artillery uses 0.7. Thus ordinary tank/artillery targets are 0.4/0.14 m/tick off-road,
legitimate driver tank forward 0.48 and reverse 0.144. Road tuning remains unchanged.
Braking, turning, contact and maximum physical envelopes retain their original limits.
A road-to-off-road transition retains momentum and brakes toward its new target;
there is no instantaneous speed clamp. Both AI and driver use the same query.

Malformed count/source/input/claim/current-state requests never call the helper.
Policy-off legacy movement also bypasses it. Valid generation/role resets are deferred
until the surface query succeeds, so an invalid helper return preserves the existing
sidecar even during recycling. Classification is derived without new future-affecting
state, allocations or hash fields. This slice does not implement slope limits,
wheeled chassis, suspension or damage-dependent handling.

The surface unit probe deliberately controls road/off-road/invalid returns, checks
actual body radius and call-site alignment, and clobbers all caller-saved SIMD and
integer registers. Original 15 actuator groups and 48 malformed requests remain;
four surface groups add role targets/rates, boundary braking, reverse through zero,
AI/driver handoff and invalid-helper generation preservation. Production collision
proof links the actual stateless helper, not that stub. Its original five body/wall/
handoff gates remain, with the steady road-cap handoff explicitly placed inside a
paved front corridor; four further real-kernel cases compare tank/artillery forward
speed on that corridor with an adjacent off-road pose. Integration, actual rendered
pavement, UDP content compatibility, army-scale movement and target GPU acceptance
still require the integrator's frozen checkpoint.

Terminal surface run `/tmp/rh-road-motion-focused.log` passed both proof libraries.
The dependency was frozen from road-body commit
`3615cf3e1327d1c85a953e2b34225eec48d44839`, source SHA256
`4e529a4aef451601e6bb9cd8929175c709eab7a82206c71d91ae53c4f8c08acf`.
It was temporarily transplanted for verification and restored afterward; this
worker commit owns no helper or shared-contract changes. Actual production-library
SHA256 is `6aa942fc40481d416b1ea770b7de255114268f1e31a0da7682243a26931d5dd0`.
Held infantry/tank/artillery minimum swept gaps were 4.224060/7.712036/8.240051 m;
the wall case ends X3984.443848, Z1301.425049 before the unchanged wall boundary.
The original road-cap handoff remains 0.600000 to 0.560000 m/tick. Real road/off-road
forward observations were tank 0.500000/0.400000 and artillery 0.199951/0.140000.
The new artillery road observation permits 0.0001 m/tick world-coordinate float
rounding from the crowd intent endpoint; no original body, wall, handoff, deadline
or arrival bound changed. All commands completed terminal before handoff.
