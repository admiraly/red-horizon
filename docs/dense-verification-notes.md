# Dense scenario verification

`tests/test_dense_scenarios.py LIBSIM` checks the actual assembly simulation,
independently of the fixture's selected counters and `sim_engaged`. It preserves
8,192 initial entities with 4,096 per side and the 3,072 infantry / 512 armour /
256 artillery / 256 aircraft mix per side. It checks health, role, generation,
front and target preservation; unchanged projectile/event pools and ground
ammunition/cooldowns; terrain-valid finite initial positions; and a concentrated
regional relocation containing at least 1,024 ground actors per side.

At ticks 1, 8, 16 and 30 it counts relocated living ground actors that actually
have living enemy ground targets. The oracle independently checks squared
weapon range and queries the production terrain LOS function. A scenario must
reach at least 2,048 such actors in an early sample, with both sides represented.
This is an early engagement requirement; it does not assert that the count stays
above 2,048 for the entire run. Over 120 genuine simulation ticks, the oracle
requires movement of at least 1,024 regional actors, actual damage, tank and
artillery launches and impacts, and a nonempty real projectile pool. It checks
living counts against records and repeats each run to verify the entire measured
result and final authoritative checksum. Invalid modes, nonfresh worlds and
worlds below the 8,192 threshold (including 8,190) must preserve state.

The per-kind event counts are actual events retained in the bounded ring and
sampled each tick. Events overwritten before sampling cannot be recovered by
this oracle; the aggregate emitted sequence is reported separately. Pool drops
are explicitly reported. Neither this headless test nor a submitted instance
count establishes visible pixels, individually detailed actors, simultaneous
audio voices, GPU performance, or the complete SCALE-HOTSPOT acceptance.
