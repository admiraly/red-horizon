# In-game company feedback

NASM now submits bounded command text to the existing OpenGL shader layer.
An authored5x7 glyph set provides company identity, selected front, default
order controls, current order/connection feedback and current exchange offer
controls directly in the framebuffer. The panel renders in first-person and
tactical views. Remote identity comes from the same validated company mirror;
it never predicts transfers or changes company authority. Timeout feedback
uses the disconnected state. Visibility census masks its actor attachment before overlays as before;
text changes the colour view without inflating army visibility.

At most128 ASCII characters are read for each line, further clipped to viewport
width; lowercase is normalized for the compact font. Three16-pixel rows sit
above the existing health/ammo HUD. This is readable command/status feedback,
not the full contextual wheel, remappable controls or complete tactical interface.
Narrow views clip long messages; layout/accessibility/human-quality acceptance
remain open. No hardware GPU performance claim follows from software GL tests.

Independent framebuffer checks read expected letter strokes from actual client
windows: solo company/accepted order; two-client incoming exchange and acceptance.
Existing command/control/authority checks remain intact. Focused and broader
verification evidence is recorded in docs/evidence/command-hud-focused.json
after the complete scoped jobs are collected.
