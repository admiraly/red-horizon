# Observed incoming explosives

`src/ai/hazards.asm` predicts ground interception for actual active artillery
(kind 2) and bomb (kind 3) records. It never reads opposing entity positions,
player state or camera state. The transient cache does not create projectiles,
damage, intelligence about firing units, or impact guarantees.

At 30 Hz, prediction advances `x + vx*t`, `z + vz*t`, and
`y + vy*t - 0.0109*t*(t-1)/2`, matching production position-before-gravity order.
The horizon is the lesser of projectile TTL and 120 ticks. Samples at four-tick
intervals locate a ground crossing; individual ticks refine the last interval.
This is a bounded sampled ground estimate. It does not predict interception by
actors, obstacle slabs, or terrain crests entirely crossed between coarse samples.
Positions, velocities and radius must be finite. Radii above 50 m are rejected;
the current production blast radius plus a 20 m danger margin fits this bound.

Each of 512 cache records follows `schemas/hazard.inc`. Predicted circles enter
overlapping cells of a 32 by 32 grid (250 m cells). Each cell retains at most eight
indices. Overflow replaces bounded entries in rotating deterministic order;
the scan origin rotates with tick number to avoid permanently starving indices.
Spatial overflow may omit a threat and is reported, rather than claiming complete
perception of all overlapping shells.

`hazard_query(side, eyeX, eyeY, eyeZ)` is read-only. It tests at most eight local
candidates, requiring hostile side, live matching projectile generation/kind/side,
finite current projectile state, nonzero TTL, proximity to the predicted circle,
current projectile within 300 m in three dimensions, and actual terrain LOS from
the supplied eye to the current projectile. It returns the first observed eligible
hazard and estimated impact X/Z, radius and ETA in ticks; no observation writes,
metrics increments, or authority changes occur. A query can therefore be used for
player-facing warnings without camera-dependent simulation. Cached estimates
refresh once per authoritative tick, so intervening projectile movement may make
an estimate one tick old; current visibility gates still inspect actual state.

Entities observe on `(entity ID + tick) & 7 == 0`. The total LOS budget is 1,024
calls per tick. A query is skipped when fewer than eight calls remain. A rotating
entity scan origin distributes this budget across the whole army. Ground units
with no driver may commit a helper-selected dispersion or shelter goal for 40
continuous ticks. Death, generation mismatch, aircraft conversion and boarding
invalidate the goal. Access to committed goals is read-only. The steering helper
owns traversability and shelter choice; this module alone does not establish that
units reach their goal or survive a strike.

`hazard_enabled` defaults to one and offers an explicit disabled comparison.
Disabling and ticking clears all goal states. FNV replay state includes this flag
and the 32-byte sidecars for all initialized world entity records; derived caches
and diagnostic counters are excluded. Sidecars reset through `hazard_init`.

`hazard_metrics` is eight unsigned 64-bit counters: cumulative predictions at byte
0, tile overflow 8, goals acquired 16, dispersion selections 24, shelter selections
32, observation LOS calls 40, budget skips 48, and current active goals 56.

`tests/test_hazards.py LIB` checks the NASM implementation's discrete intercept,
hostile/local visibility gates, read-only queries, finite input, stale generations,
expiry, full-pool bounds/fairness and committed-state lifecycle. A controlled flat
terrain/LOS kernel harness supplies focused evidence; actual terrain, integrated
steering, enabled/disabled survival, army timing and replay require separate
production-world checks and are not implied by this focused kernel test.
