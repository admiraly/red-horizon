# Terrain-supported tracked presentation

Root source 646ea71 integrates the verified ground_support v1 kernel into the
actual sourced-mesh renderer. Physical movement, damage, projectile origins,
camera/driver height and UDP record strides are unchanged. The existing 64-byte
render instance carries absolute support Y, pitch and bank in fields already
used for aircraft; the existing yaw × pitch × bank shader transforms both source
geometry and normals. Ground support is applied only to a living tank/artillery
with matching kind, generation and active motion sidecar. Aircraft, infantry,
props and the first-person weapon retain their established paths. Invalid support,
stale generations and inactive records keep the prior upright relative-height
fallback. No authoritative record is changed by this renderer.

Four chassis corners fit longitudinal/lateral slopes and a fifth centre height
bounds the support base. The same measured chassis definition serves both visual
LODs: tank half-width/length 1.75/2.55 m, local Z offset -0.45 m; artillery
2.40/3.43 m, offset -0.01 m. These derive from high-detail lower source geometry,
not cannon-inclusive overall bounds, and stay inside nominal collision circles.
The fit covers the sampled plane corners/centre; it does not prove continuous
chassis or arbitrary mesh clearance everywhere. Tilt remains cosmetic and stateless.

Focused frozen job 361553e92439 passed in 13.912s at
6c8bc78ef0e164d578a25fabfc57204500b2ba16-1d1c6916dffe4340. It executes the
actual assembly kernel, linked client, production vertex shader and real GL.
Full extended job 86ca2085d678 passed 540.59s/84 recorded reports at
646ea71e98ed7412a77d122e262126249b41d94f-1d1c6916dffe4340, with all 183 authored
inputs matching root. Source hashes/results are in evidence/ground-support-jobs.json.

The kernel's independent proof covers 9,712 production-height observations,
58 malformed cases, all frame axes, orthonormality/handedness, ABI/stack alignment,
exactly five height queries per success and unchanged full-world checksum. Three
actual assembled faults are rejected. See ground-support.md for source/library
hashes, exact tolerances and the preserved initial negative-fixture diagnostic.

Real GL transform feedback checks 103,536 sourced vertices across 48 cases:
both chassis, high/low meshes, source frames 0/9, shallow ground, forward/cross
slopes, crest, combined corner and plateau. The actual ELF vertex string matches
the production shader being executed. Positions match the independently transformed
CPU frame within 0.000487 m; transformed-normal lighting matches within 7.35e-8.
Minimum canonical terrain gap is +0.00783 m in this corpus, above the unchanged
-0.027 m penetration gate. The immutable pre-support client exposes 24 upright
faults under the same source-vertex/GL observer. These are canonical CPU-height
vertex checks, not a universal mesh/terrain-triangle intersection proof.

A separate actual-client fixture reads the produced 64-byte instances and renders
normal textures/lighting at near, mid, distant and map ranges. Changed actor pixels
are 1005/2227 for near tank/artillery, 3/6 at mid distance, two distant marker
pixels each and nine map pixels each. Both role heights/pitch/bank agree with the
actual kernel. Complete entity/motion pools and player records remain byte-identical
and simulation ticks remain frozen across captures. Stale/inactive fixtures return
to upright relative-height fallback. Existing ground-heading GL regression passes.
These declared sparse frozen fixtures are not natural gameplay or human art tests.

Compatibility 0x0fb51f27 now includes support ABI/chassis policy alongside prior
assets, roads, handling, relief, grade and render tile. Independent co-op
reconstruction retains protocol schema/wire version 7. Changing support dimensions
requires a new content fingerprint. Helpers use NASM/SSE2 and permitted platform
libm; temporary C/GLX/Python are development-only. Software GL is llvmpipe/Mesa;
no target-GPU frame budget or physical listening acceptance is inferred.

Next work is bounded cosmetic suspension response and contact height for the
intermediate smoothed frame. Applying a spring to these angles without resampling
contact can reintroduce penetration. Driver seats/cannon origins still follow the
current authority contract, not a tilted-hull attachment. Oriented/vertical physical
collision, wheels/tracks, damage/wreck cover, full roster and complete vehicle/game
realism remain required independently.

Separate live software client observation: 120 frames, 1280×720, seed42,
actual 8,192-actor hotspot, ALSA null, private Xvfb/llvmpipe. Final pixel census
finds 1,058 visible army actors: 56 high source, 556 low source and 446 markers
(612 individually detailed). Recorded independent peaks are 4,453 engaged,
480 projectiles, 64 effect records, 128 trails and 128 audio voices; 117 frames
have projectiles/effects/voices simultaneously. Peaks need not coincide. CPU
frame mean/p95/p99 54.031/72.001/77.270 ms and GPU draw 24.201/35.621/36.317 ms
are software rendering under concurrent verification, include startup and final
census drawing, and miss hardware acceptance goals. GPU timers exclude
presentation and the last eight pending samples. No isolated support overhead or
optimization is established. Result/screenshot are ground-support-software-budget.json
and ground-support-hotspot-software.png under evidence/.

Headless 900tick seed42 samples at identical candidate runtime/content inputs:
8k mean/p95 4.344/6.658ms; 16k 12.859/13.892ms. Both replay checksums exactly
match the preceding accepted terrain checkpoint. These single-thread concurrent
CPU observations render/replicate zero actors, not four-client performance.

Next bounded critical-damping prerequisite is verified in isolated e639ebb
contract plus component 3a3a6ae, recorded in evidence/suspension-prepared.json.
Its 3,462 calls include analytical step/settling, malformed full-byte preservation,
frame-time partitions, clamps, generation reset, aliasing and three assembled
causal faults. It remains outside root; this mathematical cache updater is not
accepted gameplay suspension or terrain contact. Root must derive height for
the intermediate smoothed frame and test actual renderer behavior before integration.
