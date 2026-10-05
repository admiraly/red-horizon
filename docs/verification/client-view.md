# Linux client view settings

The assembled client accepts startup-only `--width`, `--height`, `--fov`, and
`--sensitivity`. Dimensions are integer pixels (width 320–3840, height 240–2160).
Vertical FOV is 35–110 degrees; sensitivity is 0.00001–0.05 radians per cursor
pixel. Defaults remain 1280×720, approximately 56.2713 degrees, and 0.002
radians/pixel. The exact old default projection coefficients 1.05/1.87 remain
bit-identical. Aspect changes scale the horizontal coefficient relative to the
old calibrated aspect. Both battle and mesh shaders receive the same projection;
first-person weapon geometry uses that projection too. Distant marker size uses
the configured viewport. Tactical cursor conversion uses configured half sizes.

`view_settings_parse` rejects missing values, duplicate setting flags, fractional
dimensions, non-finite or out-of-range floats, hex, whitespace and trailing junk.
Decimal/scientific values are accepted. Invalid settings fail before simulation
or GLFW initialization with a message describing the valid ranges. Runtime CPU
implementation is NASM; libc `strtof` supplies conversion and libm `tanf` supplies
the platform math primitive. Settings are cosmetic and startup-only.

The GLFW window remains nonresizable. Viewport/readback dimensions and PPM header,
row stride and vertical flip follow configured dimensions. RGB storage is bounded
at 24,883,200 bytes (3840×2160×3), with no hot-path allocation. This increases the
static virtual/BSS reservation from 2,764,800 bytes; screenshot readback touches
only the configured region. No persistent configuration, remapping, in-game
settings screen, adaptive scaling or HiDPI framebuffer callback is claimed.
These are Linux settings; Windows parity remains separate work.

## Verification

- Linked actual client; both battle and mesh shader pairs pass
  `glslangValidator -l` and compile/link in actual software OpenGL contexts.
- `tests/test_view_settings_kernel.py LIB`: actual assembly parser, finite/range
  checks, duplicate rejection, exact default coefficients, 1920×1080 half-size
  960/540, configured 90-degree projection approximately 0.5614973/1.0.
- `tests/test_view_settings.py EXE`: 23 malformed/missing/duplicate CLI cases;
  actual 1280×720, 1920×1080, 800×600 screenshots with exact PPM dimensions and
  RGB lengths. All four 1080p corners contain rendered sky/terrain; tactical
  1080p also renders successfully. Every run submits 8192 actors. Different
  startup runs may advance different simulation ticks during shader compilation,
  so their raw framebuffer equality is diagnostic only.
- `tests/test_client_view_projection.py EXE`: private Xvfb, development-only
  initial aircraft/observer fixture, frozen simulation. Actual source mesh at
  FOV 45 occupies 3496 pixels versus 590 at FOV 90. Entity, aircraft, authoritative
  projectile and player arrays remain byte-identical across projection changes.
- Existing actual aircraft regression retains bomber 8908 pixels, bank change
  12052 pixels and distinct-model silhouette IoU 0.6224 at the default projection.
- Routine `python3 tools/dev.py test --suite fast` passed. These checks establish
  parser/projection/framebuffer behavior, not target-GPU performance or complete
  game acceptance. Root integration runs the frozen extended suite and hardware
  measurements separately.

For the kernel test, link the actual object:

```sh
gcc -shared -Wl,-Bsymbolic -o build/lib-view-settings.so build/src_render_view_settings.asm.o -lm
python3 tests/test_view_settings_kernel.py build/lib-view-settings.so
```

The integrator owns forwarding flags through `tools/dev.py` and integrating the
new tests into the normal client verification suite.
