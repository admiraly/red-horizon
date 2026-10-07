# Mesh material lighting

Production source meshes now light their interpolated world normals in the
fragment stage. The sun direction agrees with the existing terrain sun. A warm
direct component and cool sky/ground ambient response are combined with a bounded
view-dependent dielectric highlight. Cloud coverage softens the direct light and
highlight. Rain narrows and strengthens the highlight on intact painted equipment.
Infantry cloth, trees, fortifications and buildings retain a matte response.
Destroyed armour, artillery, bombers and fighters retain charred albedo and no
polished highlight. Neutral scenery shares the side-3 tag with wrecks, so charred
shading also requires one of those four vehicle roles.

Role defaults are cosmetic shader policy, not authored physically based material
maps. The existing animated source normals still receive infantry aim, bank,
pitch, heading and inverse instance-scale transforms before interpolation. The
old vertex `colour` remains available for independent geometry/normal diagnostics;
the production fragment uses surface albedo/normal/position. No CPU uniform or
instance-layout changes are needed: the assembly renderer already supplies the
camera and weather. Map/distant glyphs and first-person weapon presentation retain
their existing colour path. Both colour and integer visibility attachments are
written by the same fragments as before.

`tests/test_mesh_material_gl.py` reads the exact vertex/fragment strings embedded
in the linked client and links those production sources in a real GL context. Its
196 declared synthetic source-triangle cases rasterize into float colour and
integer actor-ID attachments. Paired camera, rain, cloud, role/side, matte wreck,
neutral scenery, camera-coincident and transformed-normal cases are covered.
The preceding production fragment is linked as a negative control: it has no
camera-dependent response. Marker/weapon colours match that control exactly and
actor codes match for every case. Twenty rotated-normal pairs agree within
4.5e-8 RGB. Dry camera response is approximately .0204 for matte surfaces, .0735
for armour/artillery/rifle and .1306 for aircraft; wet intact equipment .1959.
Wreck response remains zero. Aircraft cloud responses decrease from .1306 through
.0784 to .0261. These are controlled pixel differences, not light-calibration or
perceptual quality scores. Context is llvmpipe/Mesa software OpenGL.

Initial test setup invoked the wrong output path, then a rotation fixture used
the opposite pitch sign and an incorrect tilted-plane camera height. Its .0598
invariance failure was retained in evidence as a development fixture error; the
corrected test changes no shader to pass that check. The initial neutral-tag
policy was tightened before the final 196-case run to avoid charred scenery.

Exact focused logs/source hashes and linked-client SHA are in
`docs/evidence/mesh-material-focused.json`. Actual-client regression results and
immutable checkpoint scopes are recorded in `docs/status.md` after completion.
This is bounded LDR lighting. HDR, directional shadows, bloom, authored material
textures, full scene artistic acceptance and reference-GPU frame times remain
unimplemented or unverified by this batch. Existing army-scale and network gates
are preserved; shader diagnostics do not replace them.
