# Simulation prototype

`src/sim/world.asm` implements ABI v1 in docs/interfaces.md. `sim_init` accepts even counts 2–32768, divides entities equally between two sides, and seeds three fronts on the 8 km coordinate plane. Invalid initialization leaves all state unchanged. Calls before initialization safely leave an empty world. Initialization restores orders, health, counters, targets and generation 1. Unit mix: 75% infantry, 12.5% armour, 6.25% artillery, 6.25% aircraft. Health, movement per fixed 1/30 s tick, targeting radius and shot damage differ by role.

Each tick runs movement, grid rebuild, targeting, and deferred damage passes. Advance moves toward the opposing side and holds an existing firing position; defend stops movement; retreat moves away while still allowing defensive fire. There is no camera input. All live entities are individually stored, queried, targeted, damaged and counted. Dead entities remain allocated with zero health. Target references are observational and can refer to an entity killed in that tick's damage pass; the next targeting pass clears them.

The spatial grid has 32×32 cells of 250 metres, with a linked list per cell. Targeting visits the containing cell and its eight neighbors and at most 24 entries per cell. Thus dense cells cannot cause quadratic work: at most 216 candidates per live actor, plus linear grid/movement/damage passes. This limit truncates crowded cells and biases target selection toward later entity indices. It can miss relevant targets, particularly at artillery ranges exceeding one neighbor cell. This is a measured scale foundation, not validated squad intelligence. Geometry, terrain, LOS, cover, ammo, supply, projectiles, blast damage, morale, navigation and strategic objectives are not implemented here.

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

The complete development test suite passes on both populations, repeated same-seed replay, 2/32768 capacity edges, empty-state guards, counts/position/target/generation invariants, orders, local-fire rejection and malformed CLI. Timing varies with simultaneous development load. Large side imbalance is a prototype limitation, including bounded candidate truncation bias; these results do not validate balance, operational AI or player experience. No GPU, audio, network or Windows coverage is claimed.
