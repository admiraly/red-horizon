# Next gameplay batch: finite player rifle reserves

This is an implementation contract, not a completed feature. Current player.asm
reload completion writes30 unconditionally. NPC infantry already uses finite
carried reserves and depot inventories. Spec sections6/8 require useful weapons
and local ammunition/logistics; remove this remaining player infinite source.

Preserve the public64-byte player record and existing movement, cadence, partial
magazine reload, suppression, body deployment and ownership behavior. Add a
private32-byte authoritative record per player: generation0, reserve4, spent8,
received12, last successful supply tick16, declared initial rounds20, reserved
zeros24/28. Fresh actual body births equip30+90 exactly once, only after successful
spawn and correct generation publication. Failed spawns, capture, front/lease
changes and malformed stock must never equip/refill. Dead/disconnected records
freeze until an explicit genuine new body. player_init clears the private records;
player_hash includes their entire persistent state. Public lifetime shot stats
remain distinct from per-body expenditure.

Validate generation/reserved fields and magazine0..30/reserve0..90, then require
magazine+reserve+spent=120+received. Cap cumulative credit by the same finite
store-domain bound used for infantry. Query helpers are read-only and return
unknown for stale/corrupt stock. Public reload still takes60 ticks and preserves
unspent magazine rounds during the animation. Completion transfers only
min(30-magazine,reserve), rather than creating a full magazine. Empty reserve
cannot start another reload; firing atomically consumes one magazine round and
records one spent round. Unknown stocks cannot fire/reload/mint, while movement
and death processing continue normally.

Nearby on-foot player rearming uses the existing finite depot transaction:
current allied role1, healthy, connected, uncontested, real proximity and physical
LOS. Reserve room is validated before debit and credit follows actual debit.
Keep a bounded once-per-successful-player/tick guard and at most4 player checks;
boarding/death/invalid poses prevent transfer. Stock capture/repair does not
regenerate inventories. NPC and player receipts must jointly explain depot
issued counts in new conservation observers. Existing NPC-only scenes with
fully equipped non-firing players retain their original acceptance requirements.

Report actual own stock, including explicit unknown, through a bounded server
packet and client-only validated cache. Include owner ID/body generation, stock
quantities/conservation declaration and flags; validate full payload before
publication, monotonic packet tick, finite bounds, current connected body and
age. Open/close/timeout must clear cached data. Reordered stale generations may
never restore old reserves. Keep the public player record unchanged, version
and hash the new wire/policy together, and use remote data only in co-op HUD.
Display magazine plus reserve and a readable empty/unknown state in solo/co-op.

Required evidence: actual120 shots followed by inability to reload/fire; partial
reload conservation; finite depot debit/exhaustion/LOS/capture/boarding gates;
new-body-only equipment; checksum/ABI/invalid atomic queries; real UDP own-stock
parser ordering/generation/session/timeout tests and authority correspondence;
actual solo/co-op HUD/empty feedback; original scale and broad regressions.
Static malformed fixtures must be distinct from genuine tick encounters. Preserve
all original scale/recovery/symmetry tests and record every source/binary epoch.
No broader weapon roster, vehicle/air rearm, convoys or complete-spec claim from
this batch alone. Licence remains pending; no remote publication authorization.
