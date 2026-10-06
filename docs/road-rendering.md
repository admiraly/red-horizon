# Canonical road materials

Root integration supplement: source `a429a7d` passed full frozen extended job
`2804557c94cf` (497.18s, 76 reports, 158 matched authored inputs).
Exact current scope, archived public traces and remaining limits are in
`status.md` and `evidence/ground-surfaces-session.json`. The worker-only proofs
below retain their original source scope. The earlier held-artillery failure is
resolved by bounded steering preview at root; road-preferring routing and steep
slope handling remain unimplemented.


The terrain material now follows the generated canonical 19-segment capsule
network instead of three unbounded straight stripes. The three east–west roads
follow the authored doglegs around the walls, and the four north–south connectors
are visible. The shader uses each enabled segment's exact centreline distance and
half-width. Inside a physical road the existing gravel material weight remains
0.72; the weight fades smoothly over a **2 m cosmetic shoulder** outside its edge.
The shoulder does not classify as a road for authoritative traction. Site gravel,
terrain height, textures, weather, fog, lights and other material paths remain
unchanged.

`shaders/battle.frag` is a shader template. Its first line is exactly
`#version 450 core\n` (18 bytes). `src/render/shaders.asm` embeds that line, the
generated `shaders/terrain_roads.glsl` helper, and the remainder of the template in
one contiguous null-terminated `battle_fragment_source`. This keeps `#version`
first and uses the canonical generated helper verbatim. Standalone compilation
must compose those three parts; the raw template is not a self-contained fragment
shader. NASM's actual incbin dependencies include the helper.

Verification on the worker's frozen source
`2fe0f1ce8289bc64134f65c515a5b01532c82ade-17ba20637fae687e`:

- Client build job `362871284c47` passed and was collected, exit 0, 0.381181834 s.
  This is a real linked client build, not an objects-only assembly check.
- `tests/test_road_gl.py CLIENT` passed 186 real framebuffer colour samples using
  the production NASM-embedded fragment. It checks every segment's interior,
  physical edge and narrow shoulder, exterior dogleg capsule caps, all four
  connectors, and absence of the old stripe at all three wall centres. It also
  reads the provided ELF client's actual embedded shader and requires byte-for-
  byte equality with the shader tested by GL. Fragment SHA-256:
  `ff6c23d88b561f710a27dabf45dba2121a6700f37091a43fa195922f3bf53b29`.
  Context: llvmpipe LLVM 22.1.8, Mesa 26.2.3, OpenGL 4.6 compatibility profile,
  isolated private Xvfb. The temporary C driver is development-only GL/X11
  tooling; all production CPU rendering remains NASM assembly.
- Two isolated negative fixtures were rejected by the same real GL colour
  assertions: restoring the old straight stripes and disabling the four
  connectors. No production/helper files were changed for those controls.
- `tests/test_ground_gl.py CLIENT` passed against that actual assembly client:
  2,956 hull pixels, 2,772 changed pixels for a stationary authoritative pivot,
  near/mid/distant/map heading paths, stale/inactive fallback, and unchanged
  entity/ground authority across real GL rendering.
- `tests/test_client_environment.py CLIENT` passed against the same actual client:
  clear/overcast/rain/fog materials, real F4 preset input, sourced texture detail,
  rain motion, and unchanged player authority during cosmetic preset changes.

Worker logs: `/tmp/rh-road-gl-client.log`, `/tmp/rh-road-gl-negative.log`,
`/tmp/rh-road-client-authority.log`, `/tmp/rh-road-client-environment.log`.
The road test writes `/home/levy/optane-tmp/red-horizon-road-dogleg.ppm`, a top-down
diagnostic of the real production fragment with controlled equal-albedo textures;
the dogleg and narrow edges were visually inspected. This image is a development
geometry/material fixture, not a natural gameplay screenshot or art acceptance.

This proves matching material geometry and existing rendering regressions. It
does not prove road traction, slope admission, network content compatibility,
target GPU performance, human visual quality, streaming, or a completed terrain
system. Those require integrated authoritative/runtime evidence. No CPU authority,
terrain sampler, generated helper, schema or content files changed in this worker.
