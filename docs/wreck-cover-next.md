# Next vehicle slice: authoritative temporary wreck cover

Read-only root audit at89b957e while the eye checkpoint runs. This is a proposed
implementation dependency map, not feature acceptance. Spec section6 requires
readable vehicle damage states and destruction leaving useful temporary wreck
cover. No matching wreck-specific source/schema/test symbol was found in the
inspected src, schemas and tests. That search is only an inventory observation.
The concrete existing kill, collision and rendering behavior below explains the
gap.

## Current paths requiring a shared contract

`world.asm` has two genuine casualty paths. Its deferred ground damage apply loop
sets entity HP to zero and decrements sim_alive directly. The public
`sim_air_damage` function, despite its name, also kills ground targets; its
special cosmetic destroy event only applies to kind3 aircraft. Projectile lethal
blast damage reaches the latter path. A wreck hook placed only in player
`vehicle_tick_player.destroyed` would miss ordinary AI tanks/artillery and could
repeat when different driver cleanup paths observe the same death. A hook must
cover both physical casualty paths and deduplicate by entity ID/generation.

Dead entities retain XZ/generation/kind in the entity table. Existing movement,
crowd snapshot/neighbor inspection and normal army mesh passes skip zero HP.
Therefore retaining a dead entity record alone provides neither moving-body
obstruction nor a visible wreck. `terrain_body` currently considers immutable
terrain obstacle AABBs with role inflation and map bounds; point LOS/projectile
terrain tests use the original obstacle table. Wreck cover needs actual authority
in all relevant collision/visibility paths, not only a cosmetic dead mesh.

The eye helper rejects dead hulls, and driver claim cleanup already handles
physical destruction. Those checks must remain. A wreck must not be driveable,
counted as a living unit, adopted through a recycled source generation, or allowed
to emit multiple casualty events. Keep all accepted eye/motion ownership tests.

## Coherent implementation order

Root should define a bounded stamped wreck record with immutable death XZ,
heading, kind/source generation, creation/expiry tick, supported pose and cover
shape. Capacity/retirement and expired/recycled identity rules affect gameplay
and must be deterministic, documented and included in the authoritative hash.
Choose final capacity/duration and collision envelope from measured density and
actual model geometry; this audit deliberately assigns no accepted tunables.

First unify/deduplicate death registration across the two actual kill paths,
without changing health, blast policy, ammo, alive accounting or aircraft wreck
policy accidentally. Next add a bounded spatial query shared by relevant body
sweeps, LOS, rifle nearest obstruction and shell contact. The same physical cover
shape must explain visual obstruction. Whole-circle body inflation is the current
movement approximation; do not call it oriented wreck collision. Any point LOS
and shell query must retain nearest swept contact rather than blindly stopping
at the first registry entry. Initial overlap created by a death needs an explicit
safe escape/hold policy and independent relative sweeps.

Then render wrecks from the captured immutable death pose with a distinguishable
bounded damage/burn treatment. A darkened tank is a prototype wreck surrogate,
not licensed destroyed-vehicle art. The existing hidden driven-hull rendering
rule must not hide the wreck after claim release. Add generation/tick-safe
self-contained wreck replication, late-join warmup, expiry and whole-packet
validation. Ground entity HP zero packets alone cannot transport persistent wreck
identity/expiry. Changes require canonical schema/content compatibility, replay
hashes and truthful visibility census categories; preserve actor counts.

## Required proof

Exercise ordinary AI tank and artillery deaths, player cannon/blast deaths and
boarded cleanup; verify exactly one registration and living-count decrement,
no duplicate resources/events, source reuse and deterministic expiry/capacity.
Place a real wreck between observer and target and independently observe useful
LOS cover, rifle nearest-hit rejection, actual projectile impact and role-sized
swept movement obstruction/recovery. Compare cover expiry with a paired control,
not private endpoint or HP renewal after movement starts. Preserve original
8k/16k progress, health/symmetry, crowd arrival and wall recovery deadlines.

Inspect actual local/remote visible wrecks and received cleanup, real UDP
warmup/reordering/malformed/timeout paths, independent GL obstruction pixels and
unchanged sampled authority from presentation. Benchmark registry query costs
under genuine mass casualties, not only one wreck. A complete full checkpoint,
actual hardware budget and human visual/audio acceptance remain separate gates.

The missing verified cockpit/muzzle/turret asset metadata does not block this
independent gameplay slice. It still blocks a credible asset-derived articulated
turret/muzzle implementation; extrema of baked geometry are not accepted sockets.

## Inspected input identities

- `src/sim/world.asm`: `ec81d9bba4f6a6a0b1954dc3be61101f0d73cdc1703d52622bdba53e872d66b1`
- `src/sim/projectiles.asm`: `341e8b7b4243fd820d697f4beae138523cfb8ff0dce16a4ad889bf9574822c5c`
- `src/game/vehicles.asm`: `96932c3d9f68930f7d44b0d3affa14c69d755ed665841b4860786b190dd22a36`
- `src/nav/crowd.asm`: `2842c8578972415742549082113047ad1774fdb98e1371cb7b6a384389e8a833`
- `src/nav/terrain_body.asm`: `7560ab2ddca3d24070e49341bab36a02eb1100a50f74d87d9d941fa34f413f41`
- `src/nav/terrain.asm`: `106d2f28ab5999e008a8a344cd7a4979b83ad3c9b22b2f3cd4daeeb844c8a13d`
- `src/render/meshes.asm`: `2d2bf66b6440110ecd4b24a58cb5d8076b4428a4342df9cb2d6b8956a217a96d`
- `src/net/schema.txt`: `4e2ac49b631d84e1e39c01507e20bf969177c47b9271bc0ed98f8175e7ab7ec7`
