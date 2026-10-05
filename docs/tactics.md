# Terrain and tactics implementation evidence

## Shared terrain slice

`src/nav/terrain.asm` provides the ABI in `docs/next-contracts.md`. The authoritative SSE2 height is `12 + (x-4000)^2*0.000001 + (z-4000)^2*0.0000005 + max(0,1-abs(x-4000)/800)*18`, in metres. The client shader must use this same expression; matching source equations do not establish bit-identical CPU/GPU results.

Five fixed 32-byte obstacle records are exported as `terrain_obstacles`, with `terrain_obstacle_count=5`. They contain three central wall spans and two bunkers; bounds/base/height are physical and shared with rendering. Initial seeded ground spawns do not overlap any solid. Aircraft bypass ground solids, but remain subject to physical ray occlusion.

`terrain_los` sweeps each obstacle using a three-axis segment/AABB slab test, and additionally checks seven interior analytic-ground samples. Thin authored walls cannot be tunneled by the ray. Ground sampling is bounded rather than an exact continuous intersection proof for arbitrary long rays. Ground actors target at terrain height+2 m; aircraft add90 m. These queries now gate actual army target selection and therefore damage.

`terrain_move` first checks the segment toward the destination against the five solid boxes. For a blocked corridor it selects an outside corner four metres from the obstacle edge, progresses along that edge, then resumes the goal. Movement is capped by the requested step, clamps map coordinates and rejects any resulting solid overlap. This bounded local corridor steering is integrated into actual advance and retreat. It is not a global path search or a proof that every arrangement of obstacles is navigable; the authored isolated rectangles are the tested envelope. No terrain slope constraints, unit-unit collision, dynamic destruction or navigation rebakes exist.

All functions preserve SysV nonvolatile registers, use caller-saved integer/SSE scratch, and allocate no memory. Query inputs are finite world coordinates supplied by validated simulation/player state. `terrain_move` returns x/z in XMM0/XMM1, so `tests/terrain_probe.asm` is a development-only return-value bridge for ctypes; it is not gameplay logic.

`tests/test_terrain.py` passes formula samples, ground blocking and aircraft bypass, exact wall occlusion/elevated clear rays, bounded corner detour without overlap, an actual world fixture where hidden opponents acquire no targets and take no damage, actual army detour/arrival after1200 ticks, and all32768 initial spawns outside solids. Existing simulation, operation and waypoint suites pass with the real terrain module linked. Player integration and strategic/squad behavior are a separate pending slice; no stub player or AI implementation was used for these claims.

Fresh terrain-integrated throughput evidence on Intel i7-1355U, seed1,600ticks: 8192units alive3291/3267, engaged667, checksum98dcd0a3b52ac857, mean4.042290ms/p954.339853ms; 16384units alive6600/6549, engaged1439, checksum9bc327084a1b2ae0, mean8.267412ms/p959.150734ms. Timings include authoritative solid/ground LOS queries; no GPU/network/player-loop performance claim.
