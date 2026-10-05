# Bounded damage-driven aerial defense

`air_hit(EDI stable actor index)` accepts only a living kind-3 actor with an active
sidecar whose generation matches the entity. The integrator must invoke it only
after actual positive damage leaves positive HP in `sim_air_damage`. It has no
shooter argument and reads no shooter coordinates. CPU implementation is NASM;
entity32 and aircraft64 layouts, roles and wire modes remain unchanged.

Private fixed arrays add 256 KiB: commitment ticks and refractory ticks per actor.
`air_init` clears them; aircraft generation initialization clears that actor's
entry. `air_hash` includes them. The hook does not extend an existing refractory
window. Fighters commit for 48 ticks, with opposite bounded turns in the two
halves and a 0.5 m/tick climb. Bombers abort their current pass for 90 ticks,
turn for 45 ticks and hold the resulting egress heading for the rest. Existing
role speeds and yaw caps still apply. Boundary steering overrides the break.
During commitment aircraft clear the attack target and suppress acquisition and
firing; afterwards normal observed-target acquisition and attack resume. Mode
uses existing `AIR_EGRESS` (2); no new network mode is required.

Focused evidence from `python3 tools/dev.py test --suite aircraft`, using
`RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm`:

- Fighter: 24 m physical climb over 48 ticks, 1.92 radians total absolute yaw,
  peak bank 0.72 radians. Final XZ separation versus an otherwise identical
  unhit patrol was 407.655 m; this includes the patrol's different goal steering.
- Bomber: 45 m physical climb over 90 ticks, 1.125 radians total absolute yaw,
  peak bank 0.45 radians. Final XZ separation versus unhit patrol was 658.462 m.
- Each tick retained 7 m fighter / 5 m bomber horizontal displacement, existing
  0.04 / 0.025 radians yaw caps, and at most 0.5 m vertical displacement.
- Calls on every maneuver tick did not prolong it. Invalid indices, dead actors,
  nonair actors and generation mismatches did not change the checksum.
- Generation reuse resets private state; repeated hit schedules replay exactly.
- Repeated boundary hits remained inside the 8 km operation over 400 ticks;
  the fighter reacquired its separately observed opposing aircraft after jinking.
- Existing forward-cone gun, bombing, finite-ammo, perception and replay fixtures
  passed; default 8,192-entity 900-tick run retained actual air events.

Routine `python3 tools/dev.py test --suite fast` also passed on the final worker
tree (headless build identity `c259b11bd4094dff6138bc8e7ba0edcaa459c5cc-8d15c240625be092`).
The expected malformed texture-pack rejection diagnostics were emitted by the
asset tests. No asynchronous verification jobs remain.

These are direct ABI probes, not evidence that production damage invokes the
hook: that integration belongs to the integrator's `sim_air_damage` change.
No imminent-projectile perception, threat-direction inference, coordinated
wingman tactics, terrain-ahead planning, or target-GPU visual verification is
implemented or claimed by this change. The maneuver has a deterministic actor
index based direction rather than a shooter-informed turn. Full scale/network/
graphics checkpoint verification remains the integrator's responsibility.

Integration: `sim_air_damage` now calls `air_hit` after positive surviving aircraft damage. Zero damage preserves authority; production gun contact triggers a bounded defensive turn and climb on a surviving200HP aircraft. Focused aircraft and fast suites pass. Full integration evidence is recorded separately in docs/evidence/air-spectacle-session.json.
