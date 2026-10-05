# Incoming explosive HUD adapter

`src/render/hazard_warning.asm` implements the SysV cosmetic adapter
`hazard_warning_update(EDI localPlayer, XMM0 eyeX, XMM1 eyeY, XMM2 eyeZ,
XMM3 yaw)`. It accepts one of the four connected living allied players and a
finite render-camera pose, then calls the authoritative cache's read-only
`hazard_query(0, eyeX, eyeY, eyeZ)`. The wrapper writes no player, projectile,
hazard cache, LOS diagnostic, or gameplay state. Its only writes are private HUD
output and a cosmetic successful-warning frame counter.

`hazard_warning_uniform` is a four-float vector: active (zero or one),
camera-relative horizontal bearing divided by pi (-1 through 1), estimated
remaining flight time in seconds (zero through four), and blast radius in
metres (positive, capped at 512). The bearing matches `battle.vert`'s camera
rotation. Behind-camera threats appear at the strip edges. The ETA is an
estimate from observed trajectory, not an assurance of impact timing. Invalid
slot, disconnected/dead player, nonfinite inputs/results, expired/missing query,
and invalid radius clear the complete vector immediately. The counter counts
warning render updates, not distinct projectiles or simulation events.

The shader adds `incomingThreat`, with bars 44–46 consisting of a compact
bearing arrow, a dark time-strip background, and a shrinking amber-to-red fill.
These require **282 HUD vertices**, up from 264. There is no blinking, camera
shake, mandatory sound, or screen wash. Client integration must call the wrapper
with the actual rendered eye position and set this uniform before drawing the
HUD. The indicator remains visible in the tactical map for a living player.
The actor visibility census excludes HUD rendering as before.

Worker verification: `python3 tests/test_hazard_warning.py --nasm PATH` compiles
and executes the actual assembly adapter against a perception stub. It checks
query coordinates/side, cardinal and behind-camera bearings, finite guards,
bounds, absence/death/disconnect reset, slot guards, success-only cosmetic
counter, and unchanged player bytes. `glslangValidator -S vert
shaders/battle.vert` validates shader syntax. These checks do **not** establish
production projectile prediction, LOS gating, or visible OpenGL rendering.

Integration limitations: no new network hazard replication is provided by this
adapter. A remote client's empty authority hazard cache yields no warning until
a separate replicated/observed-client path is implemented. There is no incoming
recorded sound asset in this change. Weapon-specific spotting/designation and
blast-area world overlays remain separate work. Production hazard and paired
visible/hidden OpenGL evidence must be recorded by integration before claiming
player-facing warnings work end to end.
