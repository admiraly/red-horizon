# Optional opaque-world visibility census

`src/render/visibility_census.asm` owns an opt-in, final-frame GL 4.5 framebuffer:
normal RGBA8 colour at attachment 0, R32UI actor identity at attachment 1, and
DEPTH_COMPONENT24. It allocates only when requested, requires framebuffer
completeness, and releases owned objects on failed initialization or shutdown.
CPU storage is fixed: 8,294,400 uint32 words (33,177,600 bytes) and 32,768 class
flags. No per-frame allocation occurs.

All routines use SysV AMD64 and preserve nonvolatile registers. Initialization
and shutdown require the current client GL context. `visibility_init()` returns
0 or -1 for invalid dimensions/incomplete framebuffer. Accepted dimensions are
320–3840 by 240–2160. Begin binds/clears the census framebuffer and snaps the
simulation tick/checksum. Existing opaque terrain, world and weapon rendering
must run before `visibility_world_end()`, which masks attachment 1 for subsequent
translucent cosmetics and HUD. Finish reads the integer attachment, reduces it,
blits normal colour to default BACK, restores default read/draw BACK and the
attachment 1 colour mask, and snapshots the authoritative checksum again.
`visibility_finish()` returns0/-1; changed authority, invalid identity pixels or
a GL error reject the capture.

The shader identity contract is low 16 bits = entity index + 1 (1–32768), bits
16–17 = detail class 1 high, 2 low model, 3 marker. Zero is background or non-actor
occlusion. Every other encoding is invalid. The reducer checks index against the
actual army count, positive living health, valid side/kind and nonzero generation
before counting. It does not infer visibility from submission, distance or living
entity totals. A living but fully occluded actor contributes zero. The encoded
pixel cannot independently prove generation identity; stable same-frame authority
and renderer generation validation are required.

`visibility_reduce(RDI pixels, ESI words)` returns 0 or -1. It resets counters
and flags per invocation; null with zero words is valid. Oversized and nonempty
null inputs fail before dereferencing. Each actor is counted once; class counts
are independent unions. `individually_detailed_actors` is the union of high/low,
which equals high+low when production geometry assigns one class per actor.
`visibility_actor_flags` exposes the exact union (bits 1/2/4). `visibility_pixels`,
`visibility_width`, `visibility_height`, and `visibility_capture_count` expose the
captured readback for independent probes. Only private census state is written.

`visibility_report()` prints one JSON row with `visibility_census`,
`visible_actors`, `visible_high`, `visible_low`, `visible_markers`,
`individually_detailed_actors`, `width`, `height`, `source_tick`, `invalid_codes`,
`readback_reduce_ms`, scope, and before/after authoritative checksum hex strings.
Readback/reduction timing includes the blocking integer readback and CPU reducer;
it excludes colour blit, map writing, formatting and checksum calls. Finish must
run after the normal CPU frame meter ends. The census rendering itself replaces
the final normal framebuffer and is not a claim that normal frame timing excludes
its MRT draw cost. Opaque weapon occlusion is included; translucent cosmetics and
HUD do not erase identities. This is a depth-visible opaque-world count, not a
claim of perception through smoke or artistic readability.

`visibility_write_map(RDI path)` returns 0/-1. Null path is a no-op. Otherwise a
completed capture is required and the raw little-endian R32UI words are written
without a header; dimensions/tick come from JSON. Failed write/close is reported.
Shutdown restores framebuffer 0 and deletes only owned GL objects. These hooks
assume the client's documented normal framebuffer/pack state; they are not a
general state-preserving GL library.

Worker verification: actual NASM assembly succeeded. `test_visibility_reduce.py`
ran against the actual module linked with `probe_visibility_reduce.asm` authority
fixtures and native GL library entry points; no GL context was exercised by that
kernel test. Tests cover repeats, exact class flags, absent actors, mixed-class
unions, malformed encodings, count bounds, dead/invalid authority, resets, null/
oversized pointers, maximum 8,294,400 pixel input and highest valid entity ID.
Real framebuffer/shader/client verification remains an integration obligation.

Additional worker verification: `test_visibility_framebuffer.py` used a private
Xvfb display and a real hidden GLFW GL 4.5 software context with the actual
assembly module. At 320×240 it verified R32UI clear/readback, 76,800 identical
encoded high-detail pixels reduced to exactly one actor, attachment-1 masking
preventing later clears from erasing IDs, framebuffer 0 restoration, zero GL
errors, exact 307,200-byte raw map output, failed-path handling, invalid dimension
rejection, and a second empty capture resetting all visibility state. This
plumbing test uses clear-generated identities; it does not prove production
geometry, depth occlusion, actor detail selection, target-GPU speed or readability.

Integrator verification also exercises production geometry with eight independent
realGL cases: exact high/low/marker identity sets; offscreen, behind-camera and
below-terrain exclusions; opaque bunker/aircraft occlusion; empty army and remote
human exclusion. The test caught and reproduced a marker instance ID alias,
fixed by writing each stable entity index into the marker identity. Normal colour
comparison allows at most2/255 channel error, with exact counts/IDs and unchanged
authority required. This is a measured capture limitation, not byte-identical
normal presentation.
