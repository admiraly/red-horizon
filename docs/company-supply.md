# Owned-company ammunition report and presentation

Assembly authority produces a read-only40-byte company report, scanning at most
128 physical entity IDs. Actual bidirectional lease, owner body generation and
front gate membership. Dead, enemy, other-front and non-infantry bodies are
excluded. Generation-mismatched or malformed stock is UNKNOWN. Low means30
carried rounds or fewer and includes empty; known rounds exclude unknown stocks.
Failure preserves caller output; success publishes locally staged bytes.

Independent fixtures verify initial4 infantry/480 rounds, mixed2 low/1 empty/
1 unknown/140 rounds, death/front exclusions, malformed stocks and atomic
invalid input.37 ABI calls preserve six nonvolatile GPRs and stack alignment.
Independent exhaustive membership/stock oracles match unchanged8192/16384
worlds before/after actual consented company exchange. No gameplay renewal.

UDP30/schema0xb1751128/content0xcb303189 adds recipient-only supply108:
44-byte payload (lease serial plus report),84-byte datagram. Existing entity,
player and state layouts stay unchanged. Server emits after company metadata;
failed report emits no inventory. No enemy or other-owner stock is included.
Client validates the entire payload before cache writes, exact size/owner/key/
generation/serial/reserved/counts and attainable round totals. Healthy stocks
require31..120 rounds, nonempty low1..30, empty0; unknown adds no known rounds.
Equal/older ticks cannot overwrite newer data. Display separately corroborates
current connected body/front, company key/generation/lease serial and age<=90
server ticks. Close/reconnect/transport timeout clears cache. Packet reception
advances the existing remote clock; direct parser/query preserves authority.

Solo uses the actual authority report. Co-op uses only the server cache, never
unreplicated local NPC stocks. The own-company HUD shows LOW/EMPTY and RDS/
UNKNOWN on two compact rows, or OWN AMMO UNAVAILABLE. It reports own company
when another front is selected. Real GL framebuffer checks pass for solo and
two co-op clients at1280x720 and320x240, including actual stopped-server timeout.
Read-only observers and ordinary worlds; PNGs show minimum-size rendered rows.
Low/empty/unknown arithmetic is independently tested; constructed shortage
visual fixtures and broad UI quality/human acceptance remain open.

Final network suite passes22 explicit reports, including20 malformed/foreign
supply packets, all-empty/all-unknown acceptance and production four-endpoint
snapshots. Focused evidence is in evidence/company-supply-focused.json and logs.
Core fast passes70 reports (69 explicit plus hazard outcomes); it began before
final remote sum-bound strengthening, which final network tests verify. Source
and binary epochs are separate in the evidence; do not treat them as identical.
Prior full depot checkpoint is independent and pending at its frozen epoch.

Harness corrections: fake join ACK must echo sequence1; successful transport
updates the existing clock, so checksum purity is tested through direct receive;
Peer closes its socket, and independent framebuffer font expectations needed
U/K/B strokes. Early launch from the build directory lacked packaged content;
actual graphics use immutable revision executables and their content. These
attempts were failures, not feature acceptance. No acceptance constraint was
weakened and no live HP/pose/stock renewal was added.

Still open: finite depot inventory presentation, supply-aware return routes,
player/vehicle/air rearming, production/convoys, exact world-to-wire stock oracle
and transfer-specific loss/reordering coverage. Full-spec game, Windows,
hardware budgets and art/play acceptance remain incomplete. No publication;
code license pending owner approval.
