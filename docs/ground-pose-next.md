# Terrain-supported ground presentation — contract and next response

The stateless frame and renderer are integrated at 646ea71 with focused proof;
full checkpoint 86ca2085d678 passed 540.59s/84 reports with 183 matched inputs. See ground-support-rendering.md.
The following historical implementation contract records the cc90b6d audit
before support integration. At that revision, near and mid instances
are populated at meshes.asm:.appendarmy. .ground_pose copies the stamped physical
heading after checking role, generation and active flag, and leaves pitch/bank
zero. mesh.vert banks/pitches sourced geometry only through animation.w/scale.w;
world height is added at the entity centre. Distant/map glyphs encode direction
through the same pose. The raised terrain therefore exposes upright vehicle hulls
on inclines even though translation now has useful slope admission.

Keep physical heading, planar bodies and movement contracts owned by ground_motion
and terrain_body. Ground presentation must read them without changing entity,
player, vehicle ownership or motion state. Reuse the existing 64-byte render
instance contract only after establishing explicit role dispatch: aircraft pitch,
bank and absolute Y must keep their current meaning; props, humans and weapon
instances must not accidentally acquire vehicle tilt. No network authority field
is needed for a stateless pose derived from compatible world height and heading.

The first bounded component should sample four support points at the actual
chassis corners in heading space and construct an orthonormal support frame.
Inputs are finite map coordinates, heading and positive half-width/half-length;
validate every support point and output sizing before writing. Output centre
height and a right/up/forward frame in a caller-owned fixed buffer. Sample real
CPU terrain_height; preserve its established registers and aligned-call contract.
Use SSE2 with stable normalization and guard degenerate vectors. Corner heights
must determine a plane fit across crests/cusps; a centre derivative with the
sampler's zero-at-break convention cannot establish support. The frame is derived
cosmetic data, not suspension dynamics or oriented physical collision.

Root owns the support ABI and renderer integration. A kernel worker can own the
stateless component/probe and independent mathematical test in an isolated tree.
A renderer worker follows only a verified frame contract. Keep at most one
speculative component slice before validation. Define chassis dimensions from the
actual scaled source bounds and document art versus physical-envelope differences.
Do not silently grow the swept body or create authoritative vertical collisions.

Acceptance must compare the actual assembly frame to an independent four-corner
height fit on flat ground, gentle ascent/descent, cross slopes, combined corners,
crest/cusp transitions and map limits. Verify full orthonormality, handedness,
finite/bounded outputs, unchanged inputs/authority, ABI and malformed preservation.
Then test actual sourced-mesh pixels and transformed normals at near/mid ranges,
distant/map heading, driver handoff and stale generations; omission/axis-sign
negative controls must fail. Match CPU/GPU derivation or upload the verified frame;
independent approximations without a comparison are insufficient. Continuous
controls outside the relief retain current behavior. Exact replay remains required.

Static support alignment does not satisfy wheel/track suspension, damage/wreck
states, terrain-oriented physical hulls, airborne vehicle response or complete
realistic vehicle acceptance. Follow with an explicit cosmetic suspension model
and separately versioned physical collision decisions, preserving scale and UDP
coverage at each coherent integration checkpoint.

Read-only geometry audit `evidence/ground-support-audit.json` measures all clip
frames at actual renderer scale: high/low tank maximum planar radius
3.5122/3.5051 m versus nominal physical circle 3.55 m; artillery
4.2900/4.2580 m versus 4.49 m. Low-detail body extents differ, so use one shared
physical support definition rather than deriving different chassis per visual LOD.
The lower tenth is a geometry band, not a semantic track/wheel collider.

`evidence/ground-support-contact-audit.json` applies the audited current upright
shader placement equation to frame0 source vertices and actual immutable CPU
height. At (5750,5200), heading toward +X, the tank/artillery minimum ground
gaps are -0.820/-0.930 m; shallow and plateau controls have no vertex below
the 0.027 m terrain tolerance. The world checksum stays unchanged across all
queries. This calculated source-placement diagnostic identifies a cosmetic
support defect; it is not sampled GPU geometry or accepted contact physics.
