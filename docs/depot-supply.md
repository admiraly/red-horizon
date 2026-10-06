# Finite depot inventory reports

NASM authority query returns304 staged bytes: connected player/body generation,
count and twelve zero-padded24-byte records. Only current allied-owned role1
sites enter the report. Enemy inventory is not read. Each record contains site,
remaining rounds, issued rounds, declared initial stock and availability flags.
Known inventory conserves remaining+issued=12000 (or explicit zero-initial/zero
stock); malformed counters report UNKNOWN with no fabricated quantities.
CONNECTED, CONTESTED and DESTROYED are distinct; AVAILABLE requires known,
positive, connected, uncontested, living store. Downed connected owners retain
access. No allocation, debit, regeneration, clock or world-state mutation.

Independent API fixtures against real frozen core objects verify finite90-round
debit, cut/contest/destruction flags, actual exhaustion and capture away/back
preserving empty stock. Invalid stocks become unknown, foreign stores stay out,
invalid player/front/generation/output checks preserve caller buffers. ABI probe
checks six nonvolatile GPRs, stack restoration and caller guard bytes. Direct
remote parser tests validate whole-buffer atomicity, conservation, padding,
indices/order/duplicates, availability flags, owner/generation, stale ticks and
reset. Display additionally corroborates the complete current owned role1 site
set and each site's connectivity/contest/health; incomplete reordered views hide
until coherent. Source body/front and90-tick age gate availability.

UDP31/schema0x4ae7e53c/content0xf2a0dc69 adds depot packet109 with304-byte
payload/344-byte datagram. Existing entity/player/state layouts stay unchanged.
Recipient/session is authenticated by existing transport. Close/open/timeout
clears cache; no enemy store disclosure. Live unchanged8192/four-endpoint test
corroborates server reports. Fourteen malformed depot datagrams reject atomically
through actual UDP alongside existing company supply faults.

Tactical map uses authority query in solo and only the server cache in co-op.
The bounded list states visible/total depots, remaining rounds and READY/EMPTY/
CUT/CONTESTED/DOWN/UNKNOWN, or DEPOTS UNAVAILABLE. Normal-size map labels D4/D8
identify the real corresponding site markers. At320x240, two rows fit above the
company HUD and counts state any clipping; map-marker labels are omitted below
640px width. Inventory outside those rows is not scrollable yet. Real GL checks
cover solo, two co-op clients, actual READY inventory, map D8 glyphs at their
projected site, minimum window and real stopped-server timeout. Exhausted/unknown/
cut/contested/destroyed report flags are independently verified; exhaustive
rendered state fixtures remain open.

Earlier depot extended checkpoint1433fa199da8 failed the transfer-fault queue
observation, not this new feature. The corrected development relay holds actual
ACK delivery until queued input is observed, preserving the500ms delayed movement
request and queue requirement. Same immutable old client/server and candidate
client/server pass that focused fixture. Default random loss/reorder behavior
stays active. Raw full failure remains failed; no source in the frozen job changes.

Initial registered fast attempt failed due duplicate remote-module symbols in
the private query fixture. Excluding both replaced module objects fixes linkage;
no runtime or acceptance requirement changed. Raw failure is retained. Final
fast/network and source/binary epochs are recorded separately in focused evidence.
No simulation HP/pose/ammunition renewal is used to sustain encounters.

Not full logistics: supply-aware detours preserving primary intent, physical
convoys, production, player/vehicle/air rearming remain open. Exact whole-world
stock-to-wire oracle, inventory-list scrolling and exhaustive all-state visual
acceptance remain open. No hardware-budget, Windows or complete-game claim.
No publication; code license pending owner approval.
