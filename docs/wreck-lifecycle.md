# Authoritative ground wreck lifecycle foundation

The shared NASM registry captures actual tank/artillery deaths from both genuine
casualty paths: deferred infantry damage in sim_tick and the shared
sim_air_damage path used by physical projectiles/blasts. Registration occurs
once after the real HP-to-zero transition and living-count decrement. Infantry
and airborne roles do not become ground wrecks. Existing damage, shell/ammo,
crew cleanup and casualty accounting are retained.

A 64-byte record captures source ID/generation, kind/side, death tick, immutable
XYZ/heading/pitch/bank, expiry, sequence and active/fallback flags. Matching active
motion uses unsmoothed five-height support plus rotated five-point contact floor.
Unavailable/stale/hostile motion or unsupported edge footprints produce an
explicitly flagged upright terrain-height fallback. This is the established
five-point support approximation; no universal mesh clearance is claimed.

Initial reversible policy: 1,024 records, 1,800 ticks at30Hz (60s). Deterministic
FIFO retirement follows actual accepted registration order, independent of side
labels. Retired/expired source generations stay deduplicated in a bounded32,768
entry table. New generations produce independent history; they never update the
old death pose. The clock comparison uses modular unsigned elapsed age, including
u32 wrap. Expiry preserves the record's sequence/identity tombstone. Sequence
wrap skips zero. Explicit init clears records, history and metadata. The complete
persistent arena is196,620bytes; no heap allocation or camera-dependent rules.

Registry records/history/count/cursor/sequence participate in sim_checksum.
Invalid/duplicate registration preserves the entire arena. Normal world ticks
expire records before AI/movement passes. No collision, LOS, weapon interception,
rendering or wreck packets consume this registry yet; it is the shared lifecycle
foundation for those next required integrations, not accepted useful wreck cover.
Readable damage states, debris/fire/audio and artist-quality destroyed models
also remain required. Existing dead source entity records alone provide no cover.

Ground content now includes WRECK_VERSION/CAPACITY/LIFETIME_TICKS and independently
reconstructs that policy in the co-op compatibility observer:0x10d280ea,
canonical SHA25610d280ea5eea59761e98575249a6f1ff6d0b5616882109ba419f755acf45c9da.
UDPv7/schema remain unchanged because wreck records are not replicated yet.
Future self-contained generation/sequence-safe wreck messages must cover late
join, retirement/expiry and whole-packet validation before remote cover works.

## Focused evidence

In the isolated root-owned feature/wreck-lifecycle worktree, frozen focused
f8029d1f67a7 passed3.7800s and frozen fast230f98a33d8d passed126.5333s,
source83af40266a24b200710fa75e3e37643fe4a8261c-e4b9f538bb763277.
The standalone actual-assembly test runs102,496register calls across32,768IDs,
capacity retirement, duplicate rejection after retirement/expiry, clock/sequence
wrap, recycled sources,32pose composition cases,5fallback cases,12invalid
arena-preservation cases, exactFNV and SysV register/stack alignment. Three actual
assembly variants expose missing dedup, late expiry and lost pitch.

Public gameplay observers verify four kind/side lethal paths, excluded roles,
actual staggered infantry death at tick8, real tank-shell impact/blast at tick6,
boarded crew/claim cleanup, real world expiry at tick1800, replay and checksum
coverage. Only declared initial births are modified; no movement/HP renewal occurs
after combat starts. The explicit checksum adversary modifies one record birth
only after replay measurement.

Unmodified seeded8k/16k hotspot combat over120ticks creates113/97actual vehicle
casualties and113/97active records, with exact identity/pose/time/source and
capacity checks at every tick. Original total populations and real HP losses
remain; no casualty injection or health reset. Observed tick p95 is7.570/14.241ms
in the overlapping focused job, including ctypes; this is not a graphics or
hardware performance acceptance claim. Separate old/new module comparisons find
every observed entity/motion/air/player/projectile/ammo/cooldown/event/count arena
byte equal at every tick at both scales; the new registry is deliberately excluded.
Exact library/source identities and final integration results belong in root's
wreck-lifecycle evidence manifest and status.md.

## Next coherent integration

Build bounded spatial cover from captured poses, with validated world bounds and
nearest swept/ray contact. Do not use an all-wreck scan per army actor. Body
obstruction/recovery, actual LOS/rifle/shell cover, navigation invalidation and
paired expiry controls must preserve original density/health/arrival deadlines.
Render visible persistent wrecks from the same captured pose with a distinguishable
prototype damage treatment, then replicate the authoritative lifecycle and cover
semantics. A cosmetic mesh alone cannot establish useful cover. Continue the
full specification; this foundation does not close vehicle realism or the game.

Final root full checkpoint089664de8436 passed584.1588s/93reports with all207
authored inputs matched at143247ed8e672e0c27695ba5adabfeb971c5017c-e4b9f538bb763277.
Five frozen jobs and two extra exec sessions are terminal. Natural900tick
hotspot census at8k/16k observes813/930vehicle casualties and active records;
all immutable registry fields match real deaths. Capacity is not reached in
those natural runs; the standalone32k-ID pressure establishes retirement.

A subsequent exact pack audit identifies frame0 top-height LOD differences of
0.9204m tank and1.2990m artillery. Near/mid wreck silhouettes must match chosen
physical cover bounds before cover/render acceptance. Existing models/physics
are unchanged. First-contact math is prepared and verified separately in
feature/wreck-sweep atd238ea8; it is outside this accepted root checkpoint.
