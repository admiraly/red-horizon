# Aircraft cosmetic trails and impact layers

`air_trails_update(EDI local player, XMM0 render seconds)` is a read-only NASM
consumer of live entitykind3 plus generation-matching `AIR_ACTIVE` aircraft
sidecars. It exports `air_trails_records` (128records×32bytes),
`air_trails_active` and cumulative `air_trails_emitted`. Upload the entire fixed
4096-byte pool using the existing terrain7 effect attributes and draw
6vertices×128instances. The old effects64×32 ABI is unchanged.

Records use XYZ/remaining lifetime, radius/0/0/type. Type6 is a subdued .8second
engine wisp; type7 is2.5second dark smoke only for actual health below100
(aircraft full health200). Origins follow current absolute altitude and actual
velocity,1.4fixed velocity steps aft. No fabricated weapon fire is emitted.
The first implementation samples one central exhaust point; it does not identify
specific engines on source meshes, compute vortex physics or contrail weather.

A .1second cosmetic clock samples at most32aircraft per update using a rotating
entity scan. Each update scans at most the bounded32768entity array and the
128cosmetic records; no actor-pair search exists. Time is nonnegative, rejects
NaN/infinity and clips finite stalls to .25seconds. Sampling collapses missed
intervals, and unchanged authority tick cannot repeat samples. Trail history is
invalidated immediately for dead/recycled/inactive aircraft, absent actors,
disconnected observers and positions beyond1200metres. Pool replacement loses
cosmetic history without affecting gameplay. Generation counters protect each
history record individually. Trails are hidden on the tactical map.

Actual bomb impact7 and aircraft destruction9 now layer two smoke puffs and
four independently directed analytic fragments onto the hot expanding flash.
Ground bomb impacts additionally produce a low expanding dust layer (type5).
Fragments briefly glow then cool and follow shader-only ballistic arcs; smoke
rises/expands with procedural billow shading. These effects share the bounded
64record pool with existing combat cosmetics. Event range700metres, exact
sequence deduplication and event age are retained. No physical debris, dynamic
light, collision, damage, cover or authority writes are implied.

Verification in the isolated worker tree:
- `python3 tools/dev.py test --suite effects`: passed genuine production tank
  impact consumption,360render updates, expiry and unchanged authority checksum.
- `python3 tests/test_air_trails.py build/libairtrails.so`: passed10samples at
  each30/60/120Hz; exact entity/aircraft/event/projectile/player bytes and checksum
  unchanged; invalid/nonfinite times, finite stall clipping, recycled generation,
  inactive sidecar, death, range, disconnect, frozen-tick dedup, expiry and
  late event age without flash resurrection.
  A1,024aircraft production sidecar fixture emitted exactly32records per update
  and saturated at128live records. Layer tests invoke the production event
  emitter as a development fixture, rather than claiming a battle encounter.
- Linked full client build and `glslangValidator -l shaders/battle.vert
  shaders/battle.frag` passed.

The separate trail upload/call is owned by the client integrator. A standalone
linked worker client does not call that hook, so its graphical test cannot prove
visible trails. The production aircraft encounter GL test passed on private Xvfb/Mesa26.2.3
software rendering: genuine bomb launch at tick34, impact at tick176, air gun
at tick1 and destruction at tick29. Paired cosmetic controls preserved authority
bytes and changed2,147impact pixels /422destruction pixels (RGB difference>10).
The complete report is [air-vfx-gl.json](evidence/air-vfx-gl.json), with authentic
[bomb impact](evidence/air-vfx-bomb-impact.png) and
[aircraft destruction](evidence/air-vfx-aircraft-destruction.png) captures.
Software GL does not establish target-GPU frame budgets or human art/readability
acceptance.
