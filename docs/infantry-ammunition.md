# Army infantry ammunition

Army infantry carries a30-round rifle magazine and90 spare rounds. Each actual
range/LOS-gated shot spends one round before its existing three-point damage
is queued. The existing eight-tick staggered firing schedule is retained.
An empty magazine automatically starts a60-tick reload; completion transfers
up to30 rounds from carried reserves. No damage occurs during reload or after
all120 rounds are exhausted. Invalid, dead, friendly, out-of-range and obscured
targets do not spend ammunition through the world combat path.

These stocks belong to the stable actor and body generation. Ordinary side,
front, ownership or goal changes do not replenish them. Death freezes stocks
and pending reload. A genuinely new living body generation receives its declared
initial equipment once. Corrupt stock/count records are rejected or left intact,
not silently replenished. Persistent magazine/reserve/reload/shot/empty-tick
records are part of the authoritative simulation checksum. NPC movement, weapon
range, damage, projectile handling and player/vehicle stores are unchanged.

Policy values are canonical NASM data in schemas/infantry_weapon.inc and are
covered by the content fingerprint. UDP28/schema0x7ce46b6e/content0x6974e792
rejects incompatible peers. Current entity/player wire records stay unchanged;
NPC stock records remain server-only. Remote firing outcomes remain authoritative.

This closes the infinite infantry-round source, not the full logistics or weapon
roster requirements. Depot resupply, shortage presentation, NPC reload animation,
stock replication, alternate infantry weapons and target hardware/playtesting
remain outstanding. Exhausted units still move, scout, occupy sites and react
to danger, but cannot inflict rifle damage until a future legitimate resupply
path is implemented. No hidden regeneration or replacement bodies are used.
Exact scoped tests, source hashes and pending checkpoints are in status.md.
