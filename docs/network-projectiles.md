# Cooperative projectile trajectories

Gameplay UDP v5 introduced type104; current UDPv6 retains that record layout. It transmits a count and up to18 records, each
an authoritative pool index followed by the first60 bytes of `PROJECTILE_STRIDE`.
The fields include real pool/source generations, XYZ, velocity, kind, side,
remaining TTL and active state. The largest datagram is1196 bytes. A separate
per-client fair cursor examines at most512 slots per snapshot and filters by the
same1200m horizontal interest radius as entity replication. Generated inactive
slots remain eligible so authoritative death can clear received trajectories.
Moving bombs, shells, artillery and aerial gun rounds are eligible immediately
on join, independently of aircraft/entity packet warmup.

`net_projectiles` is a separate512x64 cosmetic array. The renderer must bind it
in network mode and call `net_projectiles_update(XMM0=elapsed_seconds)` after
polling. `net_projectile_count` is the active census after this update. Packet
application and render updates never mutate `sim_projectiles` or apply damage.
The complete packet validates before any slot changes, including finite bounds,
indices, generations, lifetime, kind and duplicate indices. Session generations,
per-slot ticks and projectile generations reject stale/reused slot updates.
Once a generation is dead or expires, later live records of that generation
cannot resurrect it. Opening, closing and receive timeout clear the pool.

Render prediction catches up delayed records to the newest received server tick,
then advances with elapsed render time. Tank and aerial gun motion is linear;
artillery and bombs follow the authority's position-before-gravity trajectory,
with gravity0.0109 metres per fixed30Hz tick squared. Both remaining TTL and a
120tick refresh horizon bound prediction even when impact packets are lost.
Authority tombstones stop motion immediately when received. Cosmetic motion does
not perform damage or fabricate collision/impact events.

Verification commands:

```
RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tools/dev.py test --suite network
python3 tests/test_net_projectiles.py build/libcoopclient.so build/red-horizon-coop-server
```

The trajectory test loads the real assembly adapter. It checks21 malformed
batches with whole-pool immutability; duplicate/stale/session rejection; slot
reuse; reordered live records after death; linear and gravity motion; remaining
TTL, server-tick catchup and delayed/lost refresh expiry; authority immutability;
explicit close and timeout clearing. Its dedicated64-actor fixture writes only
actor positions and a bomber's initial pose. Launch, stores, flight trajectories,
impact damage and inactive records remain actual server results. The test checks
moving bomb samples on both wire and assembly adapter, delayed target damage and
generation-matched death. Captured authentic bomb records are then replayed over
UDP with delayed/reordered/duplicate samples and a deliberately lost inactive
record; the real adapter rejects stale samples and expires the unrefreshed shot.
Existing dedicated8192-entity, aircraft malformed,
vehicle-authority and combat-event tests also run.

Limitations: rendering integration and graphics evidence belong to the client
host integration. This is bounded unreliable sampling, not reliable launch
history. A short aerial gun round can launch and die between snapshots, and dense
pools can delay sampling behind generated inactive slots. Such rounds are not
invented. In the full512-slot case, an18-record fair sweep takes29 snapshots,
about2.9 seconds at the current10Hz snapshot rate. Lost impact records may leave
bounded cosmetic prediction until TTL/horizon expires; clients never infer
server damage from the predicted path. Final content fingerprint is reconciled
with the integrated licensed asset manifest.

The integrated renderer now uploads `net_projectiles` in co-op and calls its cosmetic update after polling with actual render time. The two-client actual GL test acquires an authoritative driven-armor shell, pauses the owned server, freezes only cosmetic prediction and compares visible/hidden draws:9changed shell pixels with exact client authority bytes unchanged in the focused run. The superseding check also restores visibility and requires the same changed gold pixels within12pixels of the projected real sample; it does not assume a minimum apparent shell size. The full checkpoint records its own result separately. Development draw/clock flags default to ordinary rendering/prediction and have no player-facing control.
