# Authoritative grounded player movement

The production `player_tick` path adds crouch and a grounded jump without changing
`PLAYER_STRIDE=64`, the entity ABI, or the replicated `PLAYER_Y` field. Runtime
implementation is NASM/SSE2 with static storage and no allocations.

`INPUT_CROUCH=32` and `INPUT_JUMP=64` extend the existing input bits. The player
input validator accepts bits 0–6 and rejects bit 128 and higher, NaN/Inf, and all
existing coordinate/aim bounds failures without mutating player records.
Root integration owns the matching vehicle/network masks, versioned protocol,
and client key bindings. This isolated worktree deliberately retains the old
vehicle input mask; crouch/jump infantry works, but driving with those bits is
rejected until the integrator widens that mask.

Standing eye height is 1.8 m; crouched eye is 1.1 m. Walking remains 5 m/s and sprinting
9 m/s. Crouch is 2.5 m/s and overrides sprint. Existing `terrain_move` normalizes
planar speed and checks swept solids on both ground and airborne ticks. This
jump cannot bypass walls and is not vaulting. Terrain grounding remains the
existing analytic terrain; there is no new walkable ceiling/roof geometry.

Standing jump uses 6 m/s initial upward speed, 9.8 m/s² gravity, and a capped 50 m/s
fall speed at the fixed 30 Hz simulation timestep. Integration advances world-space
feet by current velocity before applying gravity. On flat ground the measured
peak is between 1.9 and 2.0 m and landing occurs by tick 38. The jump edge is consumed
once: holding through landing, death, respawn, boarding, or disembarking requires
release before another jump. A crouched jump edge is consumed without takeoff.
Crouching in flight adjusts the eye without changing foot motion. These are
practical kinematics, without an unrestricted flight input.

`player_motion` is a diagnostic export of four 32-byte private authoritative
records: feet-Y float +0, vertical-per-tick step float +4, player generation u32 +8,
jump latch u32 +12, grounded u32 +16, initialized u32 +20, last eye float +24, and
reserved u32 +28. Consumers must check initialized 1 and matching player generation
before trusting grounded. It is not a wire record and must not be written by
render/audio code. Its complete bytes participate in `player_hash`; init/join/
leave clear it. Dead/boarded authoritative ticks clear momentum and consume the
held jump bit. Respawn/generation reuse reconstructs grounding. Restored public
poses cannot resurrect old airborne momentum. Nonfinite/out-of-range private
motion resets grounded; nonfinite/out-of-range actual positions enter safe
redeployment and immediately become finite during the recovery delay.

## Evidence

`RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tools/dev.py test --suite player`
passed against the assembled production core. `tests/test_player.py` covers the
existing firing/reload/LOS/suppression/deployment behavior plus actual crouch
speed/height, sprint override, normalized diagonal motion, jump parabola,
held/released edges, crouch in flight, ground following on slopes, terrain-
independent airborne integration, landing, swept wall occupancy, private NaN/
Inf/overflow recovery, poisoned public positions, generation reuse, death,
boarding, private-state checksum sensitivity, and two identical 8192-actor input
replays. Invalid public inputs remain nonmutating.

Focused logs: `runs/player-movement-final.log`. Full fast regression log:
`runs/player-movement-fast-final.log` passed with exit 0 on the final runtime
source tree. All worker process handles have completed and been reconciled. Fast checks do not establish graphics,
network prediction/reconciliation, dense-front performance, Windows parity, or
playtest quality. The root integration checkpoint owns those checks. Vaulting,
weapon roster expansion, and local movement prediction remain separate spec work.
