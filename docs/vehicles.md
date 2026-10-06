# Authoritative player-operated armor

`src/game/vehicles.asm` owns four 32-byte per-player vehicle records, four
entity-index mappings, a fixed 32768-entry entity-driver lookup, four cannon-shot
counters, and private interaction edge history. All runtime logic is NASM/SSE2
on the single authoritative simulation thread. Layouts remain in
`schemas/combat.inc`; driver IDs always equal their record index, even inactive.
There are no allocations, device calls, or client-authored damage/position fields.

ABI: `vehicle_init()` resets claims, lookup, counters and edges.
`vehicle_enter(EDI=id)` and `vehicle_exit(EDI=id)` return EAX zero or minus one.
`vehicle_detach(EDI=id)` releases ownership and resets interaction history for
join/leave/death cleanup, without spending or refilling ammo. Invalid IDs fail
safely. `vehicle_tick_player(EDI=id,ESI=buttons,XMM0=wishx,XMM1=wishz)` consumes
ENTER/EXIT edges exactly once, including while dead or disconnected. EXIT takes
precedence. It returns one while driving or during hull destruction, preventing
an additional infantry movement/rifle pass, and zero when detached. Integration
must not process these edges separately. `vehicle_hash(RAX=hash,R8=prime)` extends
the replay hash over ownership, driver lookup, shot counters and edge state.

Boarding chooses a nearest living allied armor entity within eight metres, with
unclaimed ownership, valid ground placement and a solid-clear player/hull LOS.
A second driver cannot steal a claimed hull. Every tick verifies entity index,
kind/side, ownership and generation. Actor recycling releases stale ownership
without killing the player or controlling the replacement entity. The exported
`vehicle_entity_driver` lookup lets the army pass skip human-owned hull movement
and fire; simulation integration owns those checks and player hooks.

Manual driving advances at most 0.6 metres per fixed tick (18 m/s at 30 Hz),
using the existing vehicle-kind terrain movement/solid queries. This deliberate
prototype speed is separate from the current autonomous armor speed of 15 m/s.
The player follows the actual hull position and terrain height plus three metres.
Later ground-motion integration adds authoritative yaw, acceleration, braking,
bounded turning, reverse and conservative whole-body terrain/crowd contact.
Canonical road/off-road handling has a recorded full checkpoint; raised height,
whole-sweep role grade limits and reachable bypasses are integrated with focused
proof and full checkpoint 3d022b3c7d8e (533.82s/81reports). See status.md for source-specific evidence.
Suspension, terrain-supported pitch/roll, oriented/vertical physical collision
and wheeled chassis remain required; ground-pose-next.md measures the next gap.

The cannon uses the player's authoritative finite yaw/pitch to aim a 600-metre
ray endpoint, then launches a real shared tank shell through `projectile_launch`.
Terrain/map-bounded aiming never submits client damage claims; the shared moving
projectile handles swept ground/wall/actor contact and enemy-only blast damage.
It consumes the entity's persistent `sim_shell_ammo` and `sim_shell_cooldown`.
Reboarding never refills/reset these fields. Vehicle snapshots mirror current
ammo/cooldown, and `vehicle_shots[4]` records successful cannon launches. Rifle
shots, hits and magazine counters are unchanged by cannon fire.

Exit tests eight nearby candidates, rejecting map bounds, authored solids,
blocked player-to-exit LOS, living ground actor occupancy within four metres,
and other living player occupancy within two metres. A failed exit keeps every
claim and position intact. Aircraft do not block ground exits. Hull destruction
kills its live driver, starts the existing 30-tick safe-redeployment delay,
increments player deaths once, emits one `EVENT_VEHICLE_DESTROYED`, and detaches.
Disconnect/death detach independently; no destroyed hull can remain AI-owned by
a stale driver. Safe respawn is handled by the shared player module.

Verification: `python3 tests/test_vehicles.py PATH_TO_REAL_CORE_SHARED_LIBRARY`
passed on 2026-10-05 against actual world/operation/player/terrain/AI/projectile
objects plus this module, linked with `-lm`. Tests cover exclusive ownership,
invalid IDs/liveness/enemy/nonarmor/distance rejection, measured 18-metre travel
in 30 ticks and actual height, invalid direct movement, physical cannon launches
and enemy damage, no rifle counter changes, cooldown and ammo surviving reboard,
held interaction edges, single hull death/event, generation/disconnect cleanup,
authored wall movement, guarded/occupied exit failure and subsequent recovery,
and actual cannon wall impacts. Development fixtures set initial state only;
all tested movement, damage, resources and lifecycle transitions execute assembly.

Remaining evidence: integrated player/world/network/client hooks are owned by
the integrator and simulation worker. Physical graphical driving playtests,
vehicle-specific recorded sound, wreck cover, repairs, armor penetration, turret
limits, passenger seats, terrain traction and tuned vehicle balance remain future
work. This adds one existing armor role, not the complete combined-arms roster.

Direct-helper validation now precedes all interaction history and state changes.
Unknown buttons, nonfinite wishes, and wishes outside `[-1,1]` return one for an
existing valid boarded claim, zero when detached, and preserve authoritative
records, ammo/cooldown, events, counters, replay hash and private edge history.
Focused tests pass rejected ENTER/EXIT scenarios while checking complete relevant
state and checksum; the immediately following valid held interaction succeeds,
proving the rejected attempt did not consume its edge. The common player API
already rejected these values, but direct helper callers now have the same guard.
