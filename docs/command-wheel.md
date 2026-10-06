# First-person contextual command wheel

Hold the middle mouse button in first person. Move the cursor toward MOVE
(up), HOLD (left), RETREAT (down) or FOLLOW (right), then release to send that
order. The centre cancels. Right click, Escape or switching to the tactical
map cancels without charging. A held middle button cannot reopen after cancel;
it must be released first. Escape outside the wheel still quits.

MOVE captures the terrain under the crosshair when the wheel opens, using the
actual displayed camera and aim including recoil. A normalized ray takes at
most512 four-metre samples over2048m, then12 bisections against the authored
terrain height. Actual static-solid slab LOS rejects a terrain point behind a
wall. Nonfinite/outside-map/non-normalized/below-ground inputs fail. A missed
terrain point denies MOVE visibly and issues no authority request. Other orders
retain the accepted waypoint, or use the actual local player's point before
any waypoint exists. The tactical marker/first-person acknowledgement remains
the existing accepted authority view; no ownership or order prediction is added.

Selection freezes mouse aim; movement and the battlefield continue. Direct
order-key edges and shooting are consumed while the menu owns input. A key held
through closing cannot become another charged order. The cursor returns to the
normal captured first-person mode with seeded deltas to prevent an aim snap.
The event callback consumes an Escape press inside the menu even if press and
release arrive in one slow-frame event batch; it preserves quick quit outside.

The radial overlay uses pixel dimensions and four highlighted sectors, with
four labels and release/cancel guidance through the bounded shared NASM font.
Its radius follows small viewports and caps at120pixels. Menu text owns the HUD
area while open, so the underlying company text does not cross the labels at
small resolutions. Actor-census outputs remain zero for cosmetic UI.

The existing company lease, exclusive ownership, finite point validation,
atomic five-requisition cost and reliable UDP acknowledgement remain authority
owned. UDPv26 and content0xb5f51cbd are unchanged: this is client input/rendering
plus a pure read-only terrain query, using the existing order payload.

This implements the four currently supported commands. Attack, defend, suppress,
flank, regroup, embark/disembark and support selection, remappable controls,
unit/structure target selection and adaptive formations still need implementation.
The ray samples terrain rather than intersecting dynamic actors or structures;
static walls deny a hidden ground point instead of selecting the wall. A narrow
terrain crossing between samples may be missed. Captured terrain intent stays
fixed while the owner moves or genuinely redeploys with the menu open.
Hardware performance and human usability/art acceptance remain unverified.

Scoped tests pass: fast63 reports (62 explicit passes plus hazard outcomes),
final matching ray/solo/small/fault-UDP4 reports, prior-refinement GUI regressions6,
and original/new binary local/UDP wreck recovery4. Exact epochs, hashes, reports,
fixture corrections and limitations: docs/evidence/command-wheel-focused.json.
The minimum-viewport capture is docs/evidence/command-wheel-small.png. Wheel tests use private
libraries/Xvfb with actual NASM controllers, linked OpenGL clients,8192 authority,
real UDP delay/loss/reorder and read-only process observers. These input/target
tests do not renew live health, positions, ammunition or ticks. Separate legacy
wreck recovery checks retain their declared stopped-clock cosmetic geometry
fixtures; they do not establish natural movement, casualty or hardware quality.
