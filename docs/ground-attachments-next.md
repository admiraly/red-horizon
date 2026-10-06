# Ground attachments: measured next implementation slice

Read-only audit of root `71c61c74c8a9514dcccddb92934db673db60762a` on
2026-10-06. This document changes no runtime or current frozen verification.
It does not claim driver attachment, turret articulation or barrel-aligned fire
already exists.

## Current authoritative and rendered discrepancy

[vehicles.asm](../src/game/vehicles.asm) defines `hull_eye=3.0`. Entry (around
line224) and every driver movement (line461) set PLAYER_Y to
`terrain_height(entity XZ)+3`; PLAYER_XZ are the entity centre. Entry's LOS
check targets that same upright eye. Exit chooses one of eight ±6 m centre-based
XZ candidates and uses terrain+1.8, independently of rendered tilt. Claims require
matching vehicle/entity generation, reverse ownership, player generation,
allied side and tank kind1; players cannot currently drive artillery kind2.

[projectiles.asm](../src/sim/projectiles.asm:212) independently defines
`muzzle_height=3.0` and launches kind1/2 shells from entity-centre XZ and upright
terrain+3. Direct aim normalizes full XYZ toward the validated aim target;
artillery uses bounded discrete ballistic time. Player cannon targets come from
world PLAYER_YAW/PITCH, 600 m range, centre hull XZ and PLAYER_Y. They do not use
rendered hull heading, tilt, turret yaw, barrel geometry or a muzzle socket.
Launch stock/cooldown and projectile source generation remain authoritative.

[meshes.asm](../src/render/meshes.asm:625) uses generation/kind/active-stamped
GROUND_HEADING and `ground_visual` to publish absolute supported Y and smoothed
pitch/bank in the existing 64-byte instance. [mesh.vert](../shaders/mesh.vert:36)
rotates the entire authored mesh and its normals bank, then pitch, then heading.
The frame columns are right/up/forward; world point is
`entity(X,baseY,Z)+right*localX+up*localY+forward*localZ`.
The unit instance scales are one. No turret subset receives a separate transform.

Therefore the legacy eye/muzzle at `(entityX,terrain+3,entityZ)` is generally not
the transformed local point `(0,3,0)`: the latter is
`(entityX,contactY,entityZ)+3*up`, including horizontal offsets. This is a
mathematical discrepancy, not a measured cockpit socket: 3 m is the existing
legacy gameplay offset. The current local driver's hull is skipped before the
renderer ground-pose call (meshes.asm around487), so simply reading that hull's
render cache for a new camera attachment would read absent/stale presentation.

[client.asm](../src/platform/linux/client.asm:1856) derives camera XYZ from received
PLAYER_XYZ and smooths corrections, snapping on generation/large XZ jumps. The
one-tick network preview preserves authoritative vehicle eye Y; it does not
construct a tilted eye. View yaw/pitch remain world look inputs; camera roll is
absent. No aim should be derived from render-time springs or visual recoil.

## Actual baked geometry, and metadata which is missing

Executed binary inspection of `content/models/battle.rham`, SHA-256
`1ffff4417fbac3f42af83b3450a32048f45162ac35c93b55ca3384ce5be3d4a9`.
RHAMv1 stores mesh/clip descriptors and expanded position/normal/colour vec4s.
All four inspected tank/artillery descriptors have three reserved u32s equal
zero. There are no object IDs, submesh ranges, bone identities, turret pivots,
eye sockets or muzzle sockets in this format or shader instance contract.

Measurements below are **frame0 geometry**, in normalized local metres,
forward +Z, base Y0; values are rounded only for readability. A component is
formed by exact shared-position adjacency of triangles. The thin high-forward
component is geometrically barrel-like; this algorithm does not recover source
object identity or a verified pivot.

| Role/LOD | Triangles/frames | Thin high-forward component bounds X;Y;Z | Front surface observation |
|---|---:|---|---|
| Tank high | 1322/10 | [-.097287,.099028];[1.255816,1.450898];[-.274041,3] (26 triangles) | vertices (-.090339,1.352039,3),(.087541,1.330816,2.995479) |
| Tank low | 96/10 | [-.097797,.097798];[1.318653,1.473282];[-.060131,3] (16 triangles) | vertex (.00000035,1.395967,3) |
| Artillery high | 1362/10 | [-.085659,.143069];[2.377689,2.608320];[1.028696,3.5] (36 triangles) | vertices (.047872,2.566321,3.5),(.078715,2.434961,3.498235),(-.037135,2.469445,3.496332) |
| Artillery low | 96/10 | no comparable thin high-forward component established | foremost component is side running-gear geometry X[1.433583,2.402212],Y[.040582,.405698],Z[3.163082,3.5] |

Tank high overall frame0 bounds are X±1.770876,Y[.011945,2.620309],Z±3;
artillery high X±2.527609,Y[.016321,3.199802],Z±3.5. Clip-union bounds differ:
the [bake report](../content/models/bake-report.json) records tank high
Z[-3.048255,3], artillery high Z[-3.565934,3.518411]. Forward motion has ten
distinct baked frames at12Hz for each role. Its animation does not establish
controllable turret yaw/elevation. Artillery is explicitly a second tank source,
not a howitzer model.

[bake_models.py](../tools/bake_models.py:135) maps original source forward -X to
normalized +Z, subtracts the reference XZ centre and minimum Y, scales to the
chosen 6/7 m size, removes source root motion and applies one clip-union ground
offset per LOD. Thus a future socket/pivot must undergo **exactly that transform**;
copying a Blender coordinate directly would be incorrect. The current report
records only root bone `Root`, not attachment identities. Source files are pinned
by [model-sources.json](../content/model-sources.json), but the documented root
`.tools/asset-sources` directory was absent during this audit. This is evidence
about that lookup path, not a claim the sources are absent everywhere on host.

## Smallest coherent next slice

Implement **terrain-supported driver eye** first, explicitly retaining the legacy
3 m eye offset as a gameplay anchor, not claiming a measured cockpit socket.
Root should define a read-only attachment helper which consumes a validated
support frame plus local point and returns finite bounded world XYZ. For gameplay,
obtain the unsmoothed `ground_support` frame using the generation-safe live
GROUND_HEADING. Do not use `ground_visual` cache or dt in authority. Update entry
LOS, boarded PLAYER_XYZ and driver aim-target XYZ consistently. Preserve world
look yaw/pitch; a chassis bank must not forcibly roll the player's view. Keep
exit candidates centred on the hull, not the horizontally offset eye.

This changes player position/eye and potentially shell aim outcomes, even if
binary record sizes remain unchanged. Preserve the current shell source until a
verified barrel/socket contract exists; document that muzzle attachment remains
unimplemented. Do not describe this eye-only slice as articulated turret firing.
If a separate cosmetic eye uses smoothed chassis pose, request that pose even for
the otherwise hidden driven hull through the same frame/generation-safe cache;
never permit repeated draws to advance it twice or let its XYZ drive authority.
Using received authoritative eye only is an acceptable first coherent eye slice
and avoids adding a second, unchecked source of aim position.

Then acquire/locate hash-matching original Tank/Tank3 sources and inspect actual
objects, parent/bone transforms, turret pivot and barrel elevation axis. Extend
the offline bake with source-derived sockets and triangle/object groups shared
across LODs. Validate that critical turret/barrel geometry survives simplification
(the current artillery low LOD does not establish that). Authoritative muzzle
poses and client turret articulation should consume the same validated attachment
policy; geometry extrema above cannot substitute for pivot/eye metadata.

World aim must be converted through the transpose of the chassis frame into local
turret coordinates; yaw about local up, elevation about the measured barrel
hinge, with authored traverse/elevation/rate limits. Which units can slew, how AI
chooses aim and whether firing waits for alignment are gameplay policies requiring
root-owned data. Do not invent rate limits or silently force the hull to match
PLAYER_YAW. The first exact socket transform can be stateless; persistent slew
angles/velocity would require an explicitly stamped, hashed authoritative
sidecar and a replicated presentation contract.

## Required proof and compatibility consequences

Eye proof must exercise actual entry/drive/exit, CPU support at cusp/gentle/rising
terrain, stationary pivots, reverse, ownership transfer, entity recycle, player
respawn/death and disconnect. Check eye XYZ against independent matrix/actual
terrain samples, no rejected-query writes, no stale pose adoption, and preserve
original useful movement/arrival/combat-health gates. Verify replay outcomes and
validate camera position without changing world look/recoil semantics.

Retain invalid/null/finite/capacity tests, aligned external calls and nonvolatile
ABI probes for any helper. Render proof should inspect the actual driven camera
and visible remote chassis, including repeated same-frame high/low/map queries,
frame gaps and large teleports. Assembly negative controls should reject upright
terrain+3 eye, a swapped frame axis and stale entity/player generations. Turret
proof additionally needs measured source pivot/hinge/socket export, high/low
silhouette/axis agreement, visible muzzle origin and actual authoritative shell
origin/direction in player and AI paths. A cosmetic flash at a socket alone is
insufficient.

UDPv7 currently uses entity32/player64/vehicle32 plus NET_GROUND105's stamped
heading/speed/turn/velocity records; schema SHA starts `4e2ac49b`, content
`0x2df28e7c`. Player64 already transports eye XYZ, so the stateless eye migration
need not change packet sizes; it **must** change canonical content policy and
reject mismatched clients because its gameplay semantics differ. Add explicit
anchor/frame policy to `ground_content.py` and its independent test reconstruction.
Any new replicated turret fields change the canonical schema/version as root
decides. A new authoritative turret sidecar belongs in simulation/replay hashes;
presentation-only cache remains excluded. Rebaked attachment/group metadata
requires a validated pack version or separately hash-bound sidecar, asset-manifest
refresh and content mismatch/reload evidence. Do not reinterpret current reserved
zeros as existing socket fields.

## Inspection identity and limits

Root source SHA-256s used for this audit:

- vehicles: `12088ffbf5e5dc03209d198d1e36948974343aa255c349708e91b73614183027`
- projectiles: `341e8b7b4243fd820d697f4beae138523cfb8ff0dce16a4ad889bf9574822c5c`
- meshes: `2d2bf66b6440110ecd4b24a58cb5d8076b4428a4342df9cb2d6b8956a217a96d`
- mesh shader: `355bb4866bc96dab453795acb715e4fd87854d7e39c0080a94857cf1de935b6a`
- client: `ea6e2a0196ae0b7e815a0fa1c41ee8afb5393579f3b85f534181869fd985e281`

All inspection commands were terminal foreground reads and finished. One initial
report lookup requested a nonexistent `source_objects` field and failed; a
subsequent complete descriptor/report read established that metadata is missing.
No runtime edits, asset conversion, tests or full-suite acceptance occurred in
this audit. Root's frozen full job is independently owned and was not altered or
claimed passed here.

Root followup preparation: bounded downloads from both pinned Drive URLs and
the public file-content endpoint each returned2009bytes with mismatching SHA256,
so no source was accepted or baked assets changed. Exact requests/digests are in
evidence/ground-attachment-source-fetch.json and its alternate report. This
leaves verified turret/pivot extraction pending; it does not block the prepared
legacy driver-eye transform or the remaining independent gameplay streams.
Ignored scratch/source locations were also inspected by filename; unrelated
project assets were not opened or reused.
