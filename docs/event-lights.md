# Event surface lighting

Eight nearest active event flashes now illuminate terrain, opaque unit/prop models,
and the first-person weapon in the floating HDR scene. The existing presentation
then applies restrained bloom and tone mapping before the HUD. CPU selection and
uniform upload are NASM x86-64; material illumination is GLSL. This is cosmetic:
no authority, physical damage, visibility, network layout or content policy change.

`event_lights_update(XMM0/1/2 = camera XYZ)` returns zero, or -1 for an invalid
camera/gain. It clears the previous output on every call and reads the existing
64 × 32-byte effects pool. Only live type2 flashes qualify. Stable nearest-eight
selection uses squared 3D distance to the original source and lower-slot ties.
Positions must be finite, X/Z within0..8000 and Y within-1000..1000; radius must
be within0.25..12, remaining lifetime within(0,0.45]. The camera's absolute XYZ
components must be at most16000. Disabled lighting clears the pool successfully.

`event_light_count:u32`, `event_light_positions[8]:vec4` and
`event_light_colours[8]:vec4` expose the selected outputs; diagnostic
`event_light_slots[8]:u32` contains source indices, unused slots0xffffffff.
Influence radius is max(8, sourceRadius×6), at most72m. Source height lifts by
max(0.5, sourceRadius×0.35). Explosion energy is linear RGB(8,1.4,0.08), rifle
energy(3,1.2,0.4), multiplied by squared remaining-life fraction and
`event_lights_gain:f32` within0..1. Rifle lifetime0.065s is identified by its
existing0.25m radius; other flash lifetime0.45s. `event_lights_enabled:u32`
defaults1, gain defaults1. These are internal controls, not a completed settings
UI or repeated-flash accessibility treatment.

`event_lights_apply(EDI = valid linked program)` performs three bounded uniform
lookups and DSA uploads. It preserves current program, framebuffer, VAO, active
texture and texture bindings. It owns no GL resources or location cache; context
and program lifecycle belong to the caller. Client selection follows effects
update; terrain and mesh programs upload the same selected scene lights. Invalid
records are omitted individually. The producer's finite event ages and normal
pool recycling remain in force: late delivery cannot renew a flash.

The shaders apply finite radial attenuation, a quadratic radius edge and
Lambert diffuse response using world-space positions/normals. The visible weapon
surface is transformed from view back to world space, including camera yaw/pitch.
Markers, sky, HUD and hdrOutput0 legacy/tactical output retain their original
behaviour. No allocation, gameplay query, receiver identity or hidden-target data
is added. Both GLSL loops clamp their iteration count to eight.

Verified evidence is in `docs/evidence/event-lights-focused.json` and associated
raw logs. The focused effects suite passes, including50 native selection,
invalid-input, nearest/tie, lifecycle and real producer cases, source/authority
hashes and six preserved SysV registers/stack. Actual embedded production shader
checks pass36 draws each on llvmpipe and Intel Arc A770/Mesa26.2.3. Synthetic
surface controls show near light delta≈0.49071, quarter energy at half lifetime,
zero distant/disabled/expired changes, unchanged integer IDs/bindings and
legacy/map/sky controls. Separate paired actual production mesh vertex/fragment
draws change model/rotated-camera weapon pixels and leave map markers unchanged.

The whole-client development observer freezes presentation and authority clocks,
sets a camera fixture, and copies unchanged effects from a separate genuine
production cannon impact. It retains the client's8192 army. Pairing only the
lighting toggle changes3147 pixels; repeated/tactical comparisons change zero.
Authority and effect records remain byte-identical. This is an integration pixel
proof, not live authority/client synchronisation or artistic acceptance.

A native600-frame local air-battle sample at1920×1080/FOV70/cap60 and ALSA null
on i7-14700K/Arc A770 reports CPU work p95/p9916.547017/17.752963ms and GPU draw
1.382135/1.406250ms. Final census852 actors,413 individually detailed, zero invalid
IDs and unchanged authority hash. Readback/reduction7.343075ms is excluded from
CPU work. Concurrent verification load is uncontrolled; local simulation runs
on the render thread. This is not a matched lighting cost, sustained1024-detail
or full-frame/operation/platform performance acceptance. PNGs were inspected.

These lights are unshadowed and do not query solid-cover occlusion; they may
illuminate across cover. Directional shadows, bounded dynamic casters, persistent
wreck-fire lights, richer weapon-specific art, selectable quality/accessibility
and full spectacle/performance acceptance remain open. The whole game goal and
owner-pending code licence remain incomplete.
