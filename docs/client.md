# Linux client prototype

Build `src/platform/linux/client.asm` and `src/render/shaders.asm` using NASM ELF64 from the repository root (shader sources are embedded with `incbin`). Link the simulation assembly object with libc, libm, libGL and libglfw.so.3. GLFW 3.4+ is required. The build-tool integrator owns the exact CLI.

Controls: WASD ground movement, left Shift sprint, mouse aim, left mouse single shot, Tab tactical overview, 1 advance / 2 hold / 3 retreat for allied front **0**, Escape exit. Window title reports mode and last command. Tactical mode does not pause simulation. Startup seeds mouse state after the first event poll to avoid cursor-capture orientation jumps.

CLI: `--frames N` exits after N rendered frames (positive integer); `--screenshot PATH.ppm` writes a vertically corrected binary PPM before swapping the final frame; `--tactical` starts in overview. Screenshot requires `--frames` to trigger an export. Invalid options and screenshot write failures return nonzero.

Implemented: 8192 live simulation records uploaded per render frame; instanced two-piece role silhouettes (infantry, armour/artillery, aircraft), procedural 8km terrain, terrain-following eye height, distance fog, perspective camera, crosshair and tactical overview. Each simulation record is a separate draw instance; dead entities are clipped. Tactical icons enlarge silhouettes for readability. Submitted count is not a measured visible pixel count. No CPU/GPU visibility culling or LOD yet.

Simulation is advanced through a 30Hz accumulator, with elapsed intervals capped at 100ms after long stalls. Render state and camera never affect AI selection. Local shooting selects the nearest living opposing entity within a 3D aim cone and 1000m and calls guarded `sim_fire(index,34)`. It has no terrain/cover occlusion, ammunition/reload, rate limiting beyond click edges, recoil, hit feedback, player damage, or multiplayer authority. The cone is a prototype, not a weapon-complete raycast. Camera does not collide with units/buildings. Terrain geometry is visual and eye-height only; it does not affect the simulation's navigation or sightlines. Tactical overview exposes ground truth and has no selection/intelligence interface. No vehicles can be driven.

## Worker verification, 2026-10-05

NASM 2.16.03 assembled the final sources. Linked against actual simulation object `/tmp/red-horizon-sim/build/world.o`, SHA256 `0095e7c578b8b4d49104ab8995433668df67581c1940308f91f0cf3432d2d522`; no stub was used. DISPLAY=:0 on the local XWayland session returned `4.6 (Core Profile) Mesa 26.2.3`.

Both `--frames 30 --screenshot /tmp/red-horizon-first-person.ppm` and `--frames 30 --tactical --screenshot /tmp/red-horizon-tactical.ppm` exited 0 and reported `submitted_entities=8192`. PPM files were decoded to PNG and visually inspected: first person showed both armies and aircraft; tactical overview showed all three fronts. These are smoke evidence, not target-hardware frame-budget or visible-count measurements.

A development-only Python/Xlib test sent events to the specifically named client window: held W, pressed 2, clicked left mouse, then Escape. Process exited 0; camera position changed; `shots=1`, `hits=1`, `last_order=1` were observed in the final run. `hits` increments only when guarded `sim_fire` returns success, verifying one accepted mouse-selected damage request. Input was synthetic, not a human engagement playtest. No test processes remain running.

Invalid `--frames 0` and nonexistent screenshot directory returned 1. Audio is integrated independently by the integrator; this worker test linked no audio implementation. All runtime CPU source in this change is NASM. Full game, art quality, intelligent behaviour, hardware performance and co-op remain unverified.
