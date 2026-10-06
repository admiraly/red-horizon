# Finite depot resupply

The authoritative NASM world owns12 bounded16-byte physical-site inventories:
remaining0, issued4, declaredInitial8, reserved12. Fresh operation init seeds
only depot-role sites with12000 rounds. The current authored operation has four
such sites and48000 depot rounds, separate from connected supply capacity.
Capture, repair, role changes and route restoration never create inventory.
remaining+issued equals declaredInitial; malformed records fail atomically.

Living matching-generation army infantry may transfer rounds into carried
reserves, up to its missing90-round capacity, once per authority tick. It must
be within60m of an owned healthy connected uncontested depot, with valid finite
coordinates and actual clear ground/solid/wreck LOS. Depot debit precedes the
non-failing actor credit; no allocation, HP/pose/order/generation change or hidden
enemy query occurs. Reload timing and existing firing cadence remain unchanged.
Normal actor conservation is magazine+reserve+shots=120+received. The received
counter is bounded by all12 possible declared initial stores (144000 rounds).
Both received/lastSupplyTick and every depot record participate in world checksum.

Automatic checks stagger by physical actor ID every30 ticks after operation
capture/connectivity evaluation; at mostceil(N/30) actors are visited each tick.
Operation ownership/connectivity/contest records update once per second; this
is not a zero-latency occupancy detector. Cutting a route blocks further transfer
while carried stocks remain usable. Inventory depletion does not kill a unit.
UDP29/schema0xc400bad2/content0x5964d91f rejects incompatible peers. Packet
layouts are unchanged; NPC and depot stocks remain authoritative server-only.

Focused world evidence: real combat receives30 rounds at ticks300/600/900/1200,
fires134 rounds and kills its400HP target at1296. Actual occupation restores an
initially cut command-root path at600, immediately permitting90 rounds. Genuine
contested occupation and captured exhausted stores do not replenish actors.
An independent135-request fixture exhausts one12000-round store with a final
30-round partial transfer. Sparse combat/route/capture traces have no live pose/
health/ammunition/clock renewal; direct API/corruption fixtures are separate.
An original8192/four-endpoint read-only observer verifies global conservation;
a separate explicit two-position/unarmed-target startup encounter measures
actual30-round transfer and resumed shots on the real server. No observer writes
or freezes occur after that setup, and all8192 identities/health remain intact.
Exact tests, hashes, failures and current verification status: status.md.

This is army rifle resupply, not complete logistics. Missing: shortage UI/stock
replication, autonomous supply-aware return routes, player/vehicle/air rearm,
convoys, production/recruitment, broader site capability roster and target-machine/
human operation quality acceptance. No depot regeneration or hidden replacements.
