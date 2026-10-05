# Ground ordnance admission

`src/sim/ordnance_admission.asm` queues actual same-tick acquired armor/artillery
targets in four groups, `side*2+(kind-1)`. It does not acquire targets, infer hidden
positions, launch extra weapons, replenish ammunition, or change physical pools.
Root world hooks must submit source IDs in ascending order, once per source per
tick, then flush before air combat. Infantry damage staggering remains separate.

Each group starts after its last successfully admitted source ID, wrapping to its
head. Flush ranks the four groups by their lowest physical submitted source ID
(unsigned empty sentinel sorts last), then visits each source once while cycling
canonical ranks beginning at `sim_tick_count & 3`. Side-label changes therefore
preserve the complete physical spawn attempt order. Actual cursors and diagnostics
retain their side/kind group indices. Ranking is a constant bounded four-way sort;
eligibility changes can legitimately change the canonical order. At the production AI limit of 416, it still calls the existing
`projectile_spawn`: that routine already refuses immediately, preserving its real
capacity-drop diagnostic without scanning the physical pool. The 480-air and
512-physical limits and reserved human headroom remain outside this module.

Requests require bounded IDs/count, living source/target with nonzero generations,
valid opposing sides, source kind armor/artillery, no driver, ammunition and zero
cooldown. Flush repeats the checks and matches both queued generations and the
original group. Only successful production spawning updates the persistent group
cursor. A production refusal below the AI capacity threshold is an invalidated
request rather than a capacity denial. Metrics are accepted submitted, admitted,
capacity-denied and invalidated u64 counters per group; request-time ordinary
not-ready rejections are not submitted or invalidated events.

Fixed storage holds 32,768 sixteen-byte nodes and four groups of metadata; no heap
allocation occurs. Begin clears the full 512 KiB request area, preventing stale
queues even if the entity count changes. This is a measured performance cost to
include in whole-world benchmarks, not a claim of free scheduling. Flush performs
one bounded cursor search plus one pass over submitted requests. Source queues
are same-tick derived scratch and excluded from checksums. The enabled policy and
four success cursors are private future-affecting state included in `ordnance_hash`.
The caller can set enabled=0 for the explicit legacy comparison; init resets it=1.
No entity or network layout changes.

`RED_HORIZON_NASM=/absolute/nasm python3 tests/test_ordnance_admission.py` assembles
this module and a development-only controlled spawn probe in an isolated temporary
directory. It verifies 32,768 distinct requests visited once, four groups receiving
104 grants each at a controlled 416-slot limit, 128 one-free-slot rounds admitting
all 128 sources, deterministic replay ordering/hash, full spawn-attempt and remapped cursor/metric
symmetry under global side-label flips (including sparse queues), exact policy/cursor hashing,
SysV preserved registers, duplicate/ID/side/health/kind/generation/ammo/cooldown/
boarding rejection, queued-state invalidation, and diagnostic classification.
It also accepts the resulting controlled-probe library as its first argument.
These checks establish queue correctness, not production trajectories, physical
damage, combined-arms scheduling or dense-scenario performance. The independent
production oracle and integrator evidence cover those separately.

Equal submitted opportunity does not promise equal firing when acquisitions,
ammunition, cooldowns or actor survival differ. Air admission remains independent;
this module does not solve air-role allocation or all weapon capacity contention.
