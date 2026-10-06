# Raised terrain integration contracts

Root owns height/body/navigation/compatibility/build contracts and integration.
The stateless relief prerequisite is integrated as source, not yet hooked into
world height or rendering. No slope feature is accepted from source presence.

Grade worker owns only terrain_grade.asm, terrain_grade_data.inc, terrain_grade.py,
probe/test_terrain_grade and its verification document. Contract is
schemas/terrain_grade.inc: whole swept circle, conservative expanded rectangle,
closed facets/cusp sides and combined total gradient. Exact sweep radius macros
are shared with terrain_body. Root alone hooks body blocked/path/manual translation.

Height worker owns terrain.asm and terrain_surface.asm plus independent integrated
height/LOS/projectile tests/docs. Preserve terrain_height's existing observable
register behavior: old leaf preserves every GPR and XMM4–15. Relief currently
clobbers RAX/RDI/XMM0–2; do not expose those GPR clobbers to existing callers.
Integrate extra height once, analytic derivatives once; no profile state or ABI
stride changes. Validate old outside-map/nonfinite behavior and actual callers.

Renderer worker owns battle.vert,mesh.vert,shaders.asm,mesh_shaders.asm and the
localized terrain draw block in platform/linux/client.asm. Embed canonical relief
helper after first18bytes #version. Both height functions include extra height.
Existing 62.5m triangles cannot represent the steep hill faithfully: use a bounded
5m local patch over grid-aligned X5375..5875,Z4750..5625 (100x175cells,105000vertices),
terrain mode11. Hide replaced original cells only; tile boundaries must join the
original surface. All relief breakpoints align with5m. Verify actual geometry,
not just function compilation: interpolation relief error bound0.025m, plus bowl
error/float roundoff; target<=0.027m in new patch. Preserve material mode and census
occlusion. Capture real GL heights/material/render evidence and no authority writes.
Global existing bowl/ridge mesh interpolation limitations remain separate.

Root adds bounded nav bypasses, canonical content fingerprint and build hooks;
public oracle owns separate production outcomes after root hooks. Preserve source
caps/braking/yaw/radii, arrival deadlines, health, 8k/16k95%motion and400tick symmetry.
Canonical hill admits gentle approaches and rejects the central steep ramp for
vehicles. No road-preferring route, wheeled roster, suspension or full realism claim.
