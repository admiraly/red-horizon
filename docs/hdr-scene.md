# HDR scene and display presentation

The Linux assembly client owns a reusable RGBA16F scene texture with a24-bit depth
buffer. The terrain, source meshes, projectiles and translucent particles render
into it; a fullscreen shader applies fixed-exposure, luminance-based extended
Reinhard tone mapping with a linear white point of4, followed by the sRGB transfer
function. The HUD and command panel render afterward in display space. Tactical
view uses its existing encoded colours and bypasses tone mapping. All shader
colour/actor-ID outputs still describe the same geometry and depth.

`src/render/hdr.asm` initializes and destroys GL objects, clears/selects the scene
at frame begin and presents either its own texture or the optional census colour
texture. Objects allocate at startup, not per frame. Dimensions follow the existing
startup320..3840 by240..2160 range. RGBA16F colour plus depth24 requests12bytes per
pixel before driver overhead; this is an allocation-format calculation, not peak
memory measurement. No resize/context recovery path is claimed. Exposure defaults
to1 and is fixed: no camera-driven exposure adaptation or pumping.

The existing assembly camera/weather application also publishes the private
`hdrOutput` flag. Source-mesh albedo and terrain textures decode display colours
before material lighting; fog, procedural sky and artistic effect colours decode
before linear composition. Existing diagnostics may leave this uniform0 to observe
the preceding encoded path. Fire/flash effect kinds2/10 gain8times linear radiance,
tracers kind1 gain3 and burning debris kind9 gain4. Smoke/dust do not acquire that
emission gain. Event birth, age, identity, authority and budgets are unchanged.
No environmental lighting from those emissions, bloom or shadows is implemented.

The optional visibility census now also owns an RGBA16F colour attachment and the
same separate R32UI actor attachment. It masks IDs after opaque world rendering.
Tone presentation samples its colour texture. `visibility_finish_hdr` explicitly
binds that FBO for integer readback and restores default state without blitting
over the already presented HUD. The old begin/finish/blit APIs remain for diagnostic
compatibility. Actual production census tests retain exact actor classes, physical
occluders, authority hashes and normal-versus-census colour gates.

`tests/test_hdr_gl.py` creates a real OpenGL4.5 core context, calls the assembled
HDR/census APIs and checks14 artificial radiance values, exposure, tactical/disabled
paths, lifecycle, invalid dimensions and resource destruction. It links the exact
battle fragment from the client with explicitly artificial fullscreen effect inputs.
Fire stores8.0 in the scene; two additive fire fragments store16.0. The old encoded
path stores1.0. Display output agrees with an independent scalar mapping within
.001954 RGB, including quantization. IDs survive cosmetics; a declared HUD-like
pixel write survives later census readback. This is a software-GL correctness proof,
not GPU performance or cinematic acceptance.

The first native smoke fixture incorrectly expected fixed alpha.5; existing billow
produced.30005, and the test corrected that assumption without changing the shader.
The first client census failed because the caller did not reload its program
argument after a GL call; the explicit SysV reload fixes it, with unchanged gates.
Failures, exact source hashes, actual-client scope and logs are retained in
`docs/evidence/hdr-scene-focused.json`. Initial literal-format assembly failure is
also recorded. Full integration and checkpoint scopes are recorded in status.md.

The final coupled HDR/feedback candidate also passes the same core diagnostic in a
hidden native Arc A770 context (Mesa26.2.3/OpenGL4.6), selected with `--hardware`.
No visible desktop window is created. Default CI remains private software GL.
This proves the concrete hardware shader/target/lifecycle path, not the reference
1920x1080 army frame-time target. Exact coupled tests and both renderer outputs
are in `docs/evidence/hdr-scene-coupled-focused.json`.
