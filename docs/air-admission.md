# Aircraft release admission

The private v1 contract in `schemas/air_admission.inc` leaves entity32, aircraft64,
projectile records and network layouts intact. `src/sim/air_admission.asm` queues
already acquired, geometrically eligible aircraft releases; it performs no target
search, LOS, movement, damage or synthetic projectile work. Root integration owns
the acquisition call sites, initialization and authority hash chain.

Each accepted source has a fixed 16-byte node containing the submitted target,
both entity generations, and next source ID. Four queues represent side × role.
The caller submits ascending stable source IDs once per tick. Request validates
living opposing sides 0/1, nonzero entity generations, actual aircraft kind 3,
active sidecar with matching generation, role 0/1, matching target, attack mode,
positive finite ammo and zero cooldown/pass ticks. Bombers require nonair targets;
fighters require air targets. Flush repeats this validation and compares the
submitted generation snapshots before calling unchanged `projectile_air_launch`.
Target aircraft need not have an active sidecar under the existing contract;
actual production launch retains its own checks and fallback height behavior.

The request array is 524,288 bytes (512 KiB), fully cleared on begin. Fixed queue,
iterator, rank, persistent cursor and metric arrays add bounded storage. There
are no allocations. Four group ranks sort by lowest submitted physical source ID
(empty queues last), then rotate by tick&3. Within each queue traversal begins
after its last successful source, wraps and visits each node exactly once. Ranking
by physical ID makes the complete attempt sequence invariant under global side
label changes. Work is O(entity capacity + submissions), with constant four-way
sorting and O(1) rejection before production pool scans when the air ceiling is
already reached. Actual launch capacity remains the existing total-count 480 air
ceiling within 512 physical projectiles; ground and air still compete in that pool.

Only an EAX 0 launch success consumes one finite round and sets cooldown 3. Bomber
success sets egress/pass 210/target −1; fighter success retains attack/target state.
Refusal leaves stores, cooldown, mode, pass, target and success cursors unchanged.
A primitive refusal when the pre-call total count is ≥480 records capacity denial;
other primitive refusals and queued validation failures record invalidation.
Diagnostics are four group-major submitted/admitted/capacity-denied/invalidated
u64 rows. Non-ready request rejection is not an accepted submission. Hashing adds
only enabled policy 4 bytes and success cursors 16 bytes, excluding derived queues
and diagnostics. Init resets enabled 1, cursors −1 and diagnostics; enabled 0 preserves
an explicit legacy immediate-launch path owned by the integrator.

## Controlled evidence

Run `RED_HORIZON_NASM=/path/to/nasm python3 tests/test_air_admission.py`. This
self-builds the actual admission NASM module plus a development-only controlled
launch primitive. It does **not** establish production flight, impacts, bomb
geometry, dogfight acquisition, scale performance, visuals, or UDP behavior.

Verified cases:

- All 32,768 actors as valid fighters submit distinct requests; exactly 32,768 launch
  attempts visit each source once, 480 succeed, and 32,288 fail at capacity. With two
  fighter queues each receives 240 successes.
- Mixed 32,764 aircraft plus four living nonair bomber targets fill the complete
  entity capacity. All 32,764 sources are attempted once, with 120 successes per
  side/role group and 8,071 capacity refusals per group. A valid mixed fixture cannot
  make all 32,768 entities aircraft sources because bombers need nonair targets.
- 128 one-slot-pressure rounds grant 128 distinct aircraft in deterministic order;
  repeating identical state and commands reproduces the final policy hash.
- Complete attempted source sequences, mapped cursors and diagnostics match across
  global side label flips at 128 and 32,764 sources for 24 pressure ticks, including
  changing sparse eligibility and empty queues. A temporary fixed-side-priority
  NASM variant fails the symmetry assertion at `(128, False)`; it is not shipped.
- Malformed IDs/counts, duplicate submissions, dead actors, zero/stale generations,
  sides, kind, mismatched/inactive sidecars, invalid roles/modes, different targets,
  empty/negative ammo, cooldown/pass state and incompatible role/target kind reject.
  Accepted nodes becoming invalid before flush never reach the launch primitive.
- Actual module success commits finite stores and exact bomber/fighter FSM state.
  Capacity refusal and noncapacity primitive failure preserve FSM/store state;
  success cursor never advances on failure. Begin drops stale requests.
- Exact little-endian 20-byte FNV chaining, diagnostics/scratch hash exclusion,
  six SysV callee-saved registers, and 16-byte outgoing-call stack alignment pass.

The probe intentionally re-arms pass/cooldown eligibility between pressure ticks
and uses a controlled capacity result. These tests isolate admission policy;
production combined-arms and scale acceptance require separate integrated checks.
