# Raised terrain rendering

Both production vertex shaders now add the canonical generated relief height.
Their assembly source strings embed the 18-byte `#version 450 core\n` line,
`shaders/terrain_relief.glsl`, then the rest of the vertex template. Raw
`battle.vert` and `mesh.vert` require this composition for standalone compilation.
No existing test compiles those raw templates directly; `test_tools.py` exercises
the ordinary vertex-file dependency, and NASM tracks the additional incbin helper.

The Linux terrain draw adds a bounded 5 m tile over X 5375–5875 and Z 4750–5625.
Mode 11 emits 100 × 175 cells, six vertices per cell (105,000 vertices), and keeps
the existing terrain material mode 1. The original draw clips exactly the 112
coarse cells that the tile replaces: X cell indices 86–93 and Z indices 76–89.
Other coarse cells remain present. Refined outer-edge vertices interpolate the
original 62.5 m edge heights, joining the old mesh instead of leaving the bowl's
sub-2 mm interpolation cracks. Interior relief breakpoints remain unchanged.

The hill has X breaks 5400, 5480, 5620, 5820 and Z breaks 4800, 5000, 5400, 5600,
with 64 m maximum added height. All breaks align with the 5 m tile. In the steep
corner facet the mixed derivative magnitude is 64/(80 × 200) = 0.004, giving a
5 m triangle interpolation error bound of 0.025 m. Bowl interpolation contributes
at most 0.000009375 m; matching an outer coarse edge contributes at most
0.0009765625 m. The complete geometry gate remains 0.027 m. Root owns the canonical
content/build guard that keeps changed relief within the fixed tile and error
envelope; this worker does not introduce arbitrary relocatable terrain profiles.

Verified worker source:
`44ac2783929a3a04151c3d95ed05c179bfc15a9e-4c50044fccf21c1d`.
Real linked-client build job `433c5d2b167d` passed and was collected, exit 0,
0.431434996 s. All foreground test sessions reached terminal status.

`tests/test_relief_gl.py CLIENT` passed using real GL transform feedback and
triangle rasterization. It compares the ELF client's actual embedded vertex
strings byte-for-byte with the production NASM source tested by GL. The temporary
C/GLX driver is development tooling, not game runtime. It uses the production
vertex shaders unchanged; its diagnostic geometry stage only remaps the viewport,
retaining actual vertex heights and triangle interpolation.

| Observation | Result |
| --- | --- |
| Refined production vertices | 105,000 |
| Coarse vertices clipped | Exactly 672, belonging to the 112 replaced cells |
| Refined vertex maximum height error | 0.0000072144 m |
| Outer seam maximum height error | 0.0000009156 m |
| Mesh shader height samples | 1,051, including breaks/corners, seeded random points and absolute-Y air bypass |
| Mesh maximum height error | 0.0001913033 m |
| Actual raster pixels checked | 1,750,000; every pixel covered |
| Raster maximum canonical height error | 0.0247730259 m, below 0.027 m |
| Terrain material mode | Preserved as mode 1 |

Context: private Xvfb, llvmpipe LLVM 22.1.8, Mesa 26.2.3, OpenGL 4.6 compatibility
profile for the diagnostic driver. The actual assembly client uses its normal
OpenGL 4.5 core context. Vertex source SHA-256 values:

- Battle: `144f90ba06805e9ef7aeb40c118e872f5d8f3d962ef32b5bc13c3952191e4336`.
- Mesh: `d3b2378d6eb7db6274d2b4d16c38fec01e29a55ff8d3c200adf16b1961f4870b`.

Two isolated real-GL negative fixtures were rejected: omitting mesh relief
produced a 64 m height discrepancy, and restoring 62.5 m tile spacing failed the
actual vertex geometry check. These fixtures changed temporary copies only.

The same test captures the real assembly client's raised hill with normal terrain
textures and lighting from a frozen development camera at (5550, 100, 4700).
The client executes the real coarse and mode-11 draws. Player records, the complete
entity pool and ground-motion sidecars remain byte-identical across rendering;
the simulation clock remains frozen. The image was visually inspected:
`/home/levy/optane-tmp/red-horizon-raised-hill-client.ppm`. The actual raster
height-tinted geometry diagnostic is
`/home/levy/optane-tmp/red-horizon-raised-terrain.ppm`. These are declared rendering
fixtures, not natural gameplay or human art acceptance. An initial screenshot
fixture incorrectly treated a GLFW object pointer as an X drawable and failed
with BadDrawable; it was corrected to query the actual private X window, then
the complete test passed without changing runtime code.

Existing actual-client regressions also passed against that linked client:

- Graphics: first-person and tactical screenshots, input checks, 8,192 submitted
  entities. This is software rendering, not target GPU performance.
- Ground heading: 2,960 source hull pixels, 2,843 changed stationary-pivot pixels,
  near/mid/distant/map, stale/inactive fallback and authority unchanged.
- Environment: all weather presets, real F4 input, source texture detail, rain
  motion and player authority unchanged.
- Census CLI: 12 malformed pre-context argument cases.
- Production visibility GL: visible classes, offscreen/behind-camera/below-terrain
  exclusion, prop and actor occlusion, zero-army and remote-human cases, actor ID
  classes and authority unchanged. These existing fixtures lie outside the hill;
  they do not claim a new raised-hill census occlusion scenario.

Logs: `/tmp/rh-relief-gl-client.log`, `/tmp/rh-relief-gl-negative.log`,
`/tmp/rh-relief-client-graphics.log`, `/tmp/rh-relief-ground-heading.log`,
`/tmp/rh-relief-client-environment.log`, `/tmp/rh-relief-census-cli.log`,
`/tmp/rh-relief-census-gl.log`.

This worker proves GPU geometry/material integration and rendering regressions.
CPU terrain height was not yet hooked in this worker snapshot, so comparisons
use independent canonical mathematical height rather than a CPU/GPU integration
claim. Root integration must verify CPU height, collision, grade, navigation,
network compatibility and replay together. Outside this tile, existing coarse
bowl/ridge triangle approximation remains a separate limitation. No target GPU
frame-rate, Windows draw parity, streaming, suspension or complete terrain/game
acceptance is claimed.
