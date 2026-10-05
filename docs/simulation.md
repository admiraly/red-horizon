# Simulation prototype

`src/sim/world.asm` implements ABI v1 in docs/interfaces.md. `sim_init` accepts even counts 2–32768, divides entities equally between two sides, and seeds three fronts on the 8 km coordinate plane. Invalid initialization leaves all state unchanged. Calls before initialization safely leave an empty world. Initialization restores orders, health, counters, targets and generation 1. Unit mix: 75% infantry, 12.5% armour, 6.25% artillery, 6.25% aircraft. Health, movement per fixed 1/30 s tick, targeting radius and shot damage differ by role.

Each tick runs movement, grid rebuild, targeting, and deferred damage passes. Advance moves toward the opposing side and holds an existing firing position; defend stops movement; retreat moves away while still allowing defensive fire. There is no camera input. All live entities are individually stored, queried, targeted, damaged and counted. Dead entities remain allocated with zero health. Target references are observational and can refer to an entity killed in that tick's damage pass; the next targeting pass clears them.

The spatial grid has 32×32 cells of 250 metres, with a bounded 24-ID reservoir per cell. A deterministic tick/entity hash selects replacement entries while the grid is rebuilt; target sampling rotates each tick. Targeting visits the containing cell and its eight neighbors and at most 24 entries per cell. Thus dense cells cannot cause quadratic work: at most 216 candidates per live actor, plus linear grid/movement/damage passes. Sampling can miss relevant targets, particularly at artillery ranges exceeding one neighbor cell. This is a measured scale foundation, not validated squad intelligence. Geometry, terrain, LOS, cover, ammo, supply, projectiles, blast damage, morale, navigation and strategic objectives are not implemented here.

`sim_checksum` returns FNV-1a over all active 32-byte records followed by the tick counter and six orders; checksums are verified for same-build repeated runs. No cross-platform determinism claim. `sim_engaged` counts living actors acquiring an opposing target during the targeting pass, before casualties are applied; it can include actors killed later that tick.

`sim_fire(EDI=entity_index, ESI=damage)` is a local solo prototype API returning 0 on a successful hit, -1 otherwise. It accepts only living side-1 targets and damage 1–100. Bounds/ownership-like side guards prevent allied damage and double casualty counting. The client selects a target by local aim. This does not validate a network shot and must not be exposed as trusted client damage input.

All entry points preserve SysV RBX/RBP/R12–R15, clobber caller-saved integer/SSE registers, allocate no memory and own their static bounded state. Initialization replaces the current world. Operations are serial and not thread safe. Entity pointers stay stable until process exit; no pointers into code are stored.

The Linux headless entry accepts `--units`, `--ticks` (1–100000) and `--seed` (u32), with defaults 8192/600/1. It prints one JSON object including active capacity, living counts, engaged count, deterministic checksum, mean and p95 milliseconds per tick. Times use CLOCK_MONOTONIC around sim_tick, excluding initialization, checksum, sorting and output. p95 uses sorted sample index floor((ticks−1)*0.95). Headless links libc only for platform timing, argument conversion, sorting metrics and output; simulation remains assembly.

Development validation: assemble world/headless with NASM ELF64; link headless using `gcc -no-pie`; link a testable shared world object using `gcc -shared -Wl,-Bsymbolic`; run `python3 tests/test_simulation.py HEADLESS LIBSIM`. Python is solely a test driver. The suite exercises baseline/stretch replay, state invariants, distinct roles and fronts, order movement, casualties, guarded local shooting, invalid inputs and JSON output. Run times are machine-specific evidence, not target GPU performance.

## Local acceptance evidence (2026-10-05)

NASM 2.16.03, ELF64 DWARF; GCC linker; Intel Core i7-1355U, Linux x86-64, single simulation thread. Seed 1, 600 ticks, default advance:

| Units | Alive side 0/1 | Engaged final | Checksum | Mean tick ms | p95 tick ms |
|---|---|---|---|---|---|
| 8192 | 1439/200 | 958 | bdd82a912e7e5454 | 1.490117 | 2.228279 |
| 16384 | 5771/158 | 189 | a171de353b916bb3 | 3.426404 | 4.782913 |

The complete development test suite passes on both populations, repeated same-seed replay, 2/32768 capacity edges, empty-state guards, counts/position/target/generation invariants, orders, local-fire rejection and malformed CLI. Timing varies with simultaneous development load. These historical linked-list measurements exposed a substantial later-ID candidate truncation bias and were superseded by the reservoir follow-up below. They do not validate balance, operational AI or player experience. No GPU, audio, network or Windows coverage is claimed.

## Fair sampling follow-up

The grid now uses tick-varying deterministic reservoir samples rather than the first entries of reverse insertion chains. The core entity layout is imported from generated `schemas/entity.inc`. The full suite passes, including a seed-19, 8192-actor, 400-tick stationary side-label-swap fixture: identical per-actor health and exactly exchanged casualty totals. This fixture verifies that team labels do not alter targeting; it does not prove general battle balance.

Fresh seed-1, 600-tick measurements on the same i7-1355U:

| Units | Alive side 0/1 | Engaged final | Checksum | Mean tick ms | p95 tick ms |
|---|---|---|---|---|---|
| 8192 | 559/947 | 1430 | 8507096c7fd762f1 | 1.541101 | 2.465844 |
| 16384 | 1794/2038 | 3823 | 409163e45d7ba1e0 | 3.689628 | 5.228087 |

Candidate work remains capped at 216 per actor and grid rebuild remains linear. Hash-modulo reservoir selection has minor statistical modulo bias; it is a practical bounded targeting sample, not a proof of uniform random sampling. Limited neighbor radius and missing LOS/terrain remain unchanged.

## Real-time headless pacing

`--realtime` optionally paces completed ticks to absolute CLOCK_MONOTONIC deadlines with `clock_nanosleep(TIMER_ABSTIME)` at 30 Hz. EINTR retries the same deadline. Default headless execution remains throughput mode. When a tick exceeds its deadline the subsequent sleep returns immediately; there is no skipped simulation tick or hidden outcome change. Tick timing still excludes sleeps. The suite verifies that three paced ticks consume at least 90 ms and produce exactly the unpaced checksum; baseline/stretch 30-tick paced runs were separately measured at approximately one second wall time. Pacing is single-threaded and does not claim a server networking loop.

## Formation waypoint movement

`sim_waypoint(EDI=side, ESI=front, XMM0=x, XMM1=z) -> EAX=0/-1` sets the specified formation's host-owned shared destination. Side must be 0/1, front 0/1/2, and both coordinates must be finite within 0–8000 inclusive. Invalid calls leave destinations unchanged. The routine preserves SysV nonvolatile registers, clobbers caller-saved registers, allocates no memory, and does not change membership or orders. `sim_waypoints` exports six x/z f32 pairs, indexed `side*3+front`, stride 8. Initialization sets allied goals to x=5000 and enemy goals to x=3000, at z=1300/3900/6500. Destinations are included in the replay checksum; entity ABI v1 remains unchanged.

Advance now moves living entities toward their side/front goal with a normalized SSE2 step. If the remaining distance is no larger than the step, the entity arrives exactly and stays there. Existing combat hold remains: an actor with a living acquired target temporarily holds its firing position. Defend/hold pauses only the chosen side/front; retreat retains the outward x-axis movement with coordinate clamps. Dead entities do not move. This is direct steering without obstacle navigation, collision avoidance, cover, routes or sightlines.

Speeds per fixed 1/30-second tick are infantry 0.12 m, armour 0.5 m, artillery 0.2 m, aircraft 5 m: respectively 3.6/15/6/150 metres per second. Earlier ground speeds were incorrectly large (45/66/15 metres per second) and have been corrected. At infantry speed a kilometre takes approximately 278 seconds before combat holds, emphasizing the future need for transport/deployment rather than artificially fast marching.

`python3 tests/test_waypoints.py build/libsim.so` passes NaN/Inf/bounds rejection without mutation, checksum sensitivity, side/front goal isolation, all four measured per-tick speeds, exact diagonal arrival without overshoot, persistent arrival, hold while another formation moves, and real world-tick movement followed by hold completing hostile-site capture. The baseline/stretch and operation suites also pass.

Fresh seed 1, 600-tick results on the same i7-1355U after movement changes:

| Units | Alive side0/1 | Engaged final | Checksum | Mean tick ms | p95 tick ms |
|---|---|---|---|---|---|
|8192|2267/2564|674|03af2b6b5aaf3848|2.155239|2.938412|
|16384|5003/5466|1498|eb260d54d97c9577|4.426580|5.538509|

Both runs remain ongoing with capacity 600/600 and requisition 880/460. These twenty-second throughput fixtures verify physical movement and casualties; slower marching means they do not demonstrate autonomous captures at default distant goals. The explicit arrival/capture scenario provides that path separately.
