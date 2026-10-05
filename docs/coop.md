# Actual authoritative cooperative world transport (UDP v4)

This path links the dedicated server to the same assembly army, operation,
terrain, AI and four-player modules used locally. The server alone advances the
world at 30 fixed ticks/s. Network clients apply authoritative snapshots and
never call `sim_tick`. The prior standalone UDP proof remains a separate target.

Build integration requires `src/net/coop_server.asm` plus the shared modules and
`-lm`; the actual graphical client instead links `src/net/client.asm`. The
integrator owns these targets in the development CLI. Dedicated arguments are
`--port N --ticks N --units N`, defaulting to `7777`, `0`, and `8192`. Tick zero hosts until interruption; positive ticks bound development runs. Port zero
reports an ephemeral port. The server binds IPv4 on all local interfaces for
Direct IP/LAN. It is not a public authenticated internet service.

The server uses monotonic absolute deadlines, 33,333,333 ns apart, with 64
incoming datagrams maximum before each simulation tick. There is no camera-based
simulation gating: all configured army entities retain authoritative updates.
Clients receive all four player records and all twelve site records, both sides'
resources, operation state, and authoritative tick/count at 10 Hz. Each client
also receives at most two entity chunks per snapshot, 32 records each, selected
within 1200 metres of its player. A persistent per-client cursor cycles through
all nearby stable IDs rather than sending only the first records. A bounded full
interest census measures nearby actors and never-replicated backlog. Regional snapshots do not apply tactical fog-of-war; nearby enemy records may be received behind walls. Offscreen
army intelligence is absent from this slice, and the client keeps nonreceived
army health zero. No fabricated full army is displayed in network mode.

The 40-byte header is ten little-endian u32 fields: magic `0x52484332`, version
`4`, schema fingerprint, content fingerprint, type, player ID, command sequence,
server tick, payload bytes, and session generation. The canonical field layouts
are in `src/net/schema.txt`, with assembly constants in `src/net/protocol.inc`.
The schema fingerprint is the first 32 bits of SHA256 of that canonical file:
`bb315959fd2e712f33722db6a3225c110444cdaffef05f09f944e63f716f3b86`.
The content fingerprint comes from SHA256 of `content/asset-manifest.json`:
`99af0be8365d168fb5a5e488861cbba374e100167ee94a719158b57c7ea3a507`.
These truncated compatibility hashes are not authentication or cryptography.
Version/hash mismatches are rejected before gameplay payload parsing; compatible
changes must deliberately update the pinned canonical data and constants.

Packet types: join `1` has no payload and uses ID `0xffffffff`, sequence one and
zero generation. ACK `2` has four u32 fields (status, front, count, requisition).
Input `3` has buttons followed by wish x/z and yaw/pitch floats. Order `4` has
front/mode u32 followed by goal x/z floats. Leave `5` has no payload. State `100`
is exactly 848 bytes including header. Entity chunk `101` contains a u32 count
and up to 32 records, each stable index u32 plus the existing 32-byte entity;
its maximum is 1196 bytes. State appends four32-byte vehicle ownership records and four signed player-to-entity mappings after the unchanged player/site region. Cosmetic event packet `102` carries at most32 actual32-byte events (1068bytes total), filtered within1200m. The server scans at most256 ring slots per client snapshot; late joins start at the current event sequence. Events are unreliable decoration and cannot apply damage. Whole event packets validate bounds, finite coordinates, kinds and monotonic sequences before publishing any ring entry; duplicate sequences do not replay effects. The client drops older reordered cosmetic batches and reports the number of actually retained records in the latest256-sequence window; interest filtering and loss can leave holes. Actual datagram size is checked using `MSG_TRUNC`
before any header read, with fixed 1200-byte buffers and exact payload sizes.

The server assigns player slots tied to UDP endpoints and increments a session
generation whenever a freed slot is claimed. Slots zero through two own the
corresponding army fronts. Slot three supports front zero and cannot issue
primary orders. Orders validate ownership, mode and finite `0..8000` goals,
reject ground-solid destinations, then synchronously charge five allied requisition and apply army mode/waypoint.
Clients never submit health, position, damage, hit or resource claims. Inputs
are validated by the common authoritative player module. Unknown button bits
are rejected; FIRE/RELOAD/SPRINT/ENTER/EXIT are accepted; ENTER/EXIT edges are applied by the authoritative vehicle module.

Commands use stop-and-wait sequencing. The next valid authenticated sequence is
consumed even if its payload is rejected; duplicates replay the cached status
without applying input/order/spending again. Future/old sequences and mismatched
endpoint/session generations are ignored. There is one input accepted attempt
per slot per tick, and at least fifteen ticks between successful orders. ACK
status: zero success, one malformed/invalid input, five ownership, six resources,
seven scheduling rate. The adapter retries the exact pending datagram every
100 ms when polled. It sends only one pending command, so callers must retain
and retry an order while the API returns busy. Outbound cap is five snapshot
packets per client per three ticks plus bounded ACK responses.

Endpoint ownership expires after 90 authoritative ticks without valid traffic.
Explicit leave releases the player immediately; lost leave falls back to that
three-second timeout. Slots become claimable again with a new session generation.
Server snapshots alone do not keep endpoint ownership alive: the client should
send current input, including zero intent, at approximately 30 Hz. The adapter
marks disconnected after three seconds without accepted server packets.

Adapter ABI is documented in `docs/next-contracts.md`: open queues the join and
returns zero; `net_connected` becomes one only after accepted ACK. Input/order
return zero when queued and minus one when disconnected, invalid or busy. Poll
returns accepted packet count and never ticks local world. Additional diagnostic
`net_last_status` records the latest command ACK status; read-only `net_pending` is the queued datagram length (zero after completion/close). Callers waiting on an order ACK must also require `net_connected`, and hold later inputs until its result has been consumed. Player/session/tick
validation precedes state application; entity indices, finite coordinates,
enums and generations are checked. Older tick data is ignored. Unrefreshed
entity health expires after a worst-case complete count/640Hz refresh cycle plus
90 server ticks. Actors outside the current player interest radius are immediately
hidden. Dense regions may need several seconds for a complete cycle under the
explicit bandwidth cap; this is sparse authoritative state, not smooth full-army
replication.

Verification entry point:

```sh
python3 tests/test_coop.py --server build/coop-server
# Optional shared object containing net adapter plus shared assembly modules:
python3 tests/test_coop.py --server build/coop-server --client-lib build/client-net.so
```

Verification on 2026-10-05 passed with the actual shared terrain/world/player
modules (core player commit 0590eeb, hooks 65143cf, terrain 0a1a884). The real UDP
suite ran 8192 entities for 180 ticks and reported 69116 bytes in, 603368 bytes out,
12,416 entity records, 11 rejected packets, 2 timed-out ownership releases, and 10,902
distinct client/entity pairs across sessions. It verified authoritative movement
and rifle shots, finite input/button rejection, ownership/order spending and
cached duplicate ACKs after deliberately discarding an ACK, reordered commands,
MTU/hash rejection, four-player/site snapshots, join in progress, explicit leave,
and generation-guarded slot recovery. The actual assembly adapter shared-library
test also passed real join/input/state application, initially zero entity HP,
regional records, and no autonomous local simulation tick. The latest final
interest census was taken only from active slots. These are headless automated
outcomes, not graphical playtest evidence.
Physical two-client graphical play, interpolated remote actors, dense-front
bandwidth/latency budgets, reconnect state continuation,
world join chunk completion, public security, Windows, and full-game acceptance
remain separate evidence requirements. This limited regional replication path
must not be described as full 8192-record replication per client.


Extended verification (`--extended`) now passes actual network death/redeployment
and the real UDP delay/loss/reorder matrix. The development driver pauses its own
server child and positions existing army records: allies move away from the
fixture threat, and one living armoured enemy moves 80m from the authoritative
player. It writes only entity positions, never player position, HP, damage,
respawn or timers. Normal shared simulation and player combat then produce
HP0, a nonzero redeployment delay, a safe new position and increased player
generation, observed entirely in UDP snapshots. This is a controlled developer
fixture, not evidence of normal-scenario difficulty or pacing. It requires Linux
`/proc/PID/mem` access to the test's own child and `nm` symbols; failure is explicit.
No production encounter flag or client-authorized damage path was added.

The development-only UDP relay runs at 0/50/100/150ms nominal one-way delay,
with +/-10ms jitter, every 20th received datagram dropped, and every 7th forwarded
datagram given an extra 60ms to reorder arrivals. Actual measurements:

| One-way delay (ms) | Datagram count | Dropped | Delayed for reorder | Accepted inputs |
| --- | --- | --- | --- | --- |
| 0 | 203 | 10 | 28 | 24 |
| 50 | 204 | 10 | 28 | 14 |
| 100 | 197 | 9 | 27 | 9 |
| 150 | 196 | 9 | 27 | 7 |

All four fixtures preserved join and authoritative movement through retries.
The finite observed drop fractions are 4.6–4.9%; every 20th rule approaches 5%.
Higher RTT reduces command throughput under the current stop-and-wait policy;
held authoritative intent still advances at 30Hz. This verifies recovery in these
bounded headless scenarios, not smooth graphical prediction, all possible network
faults, production congestion control, or target-machine bandwidth/latency goals.
All subprocesses and relay threads are reconciled before the driver exits.

```sh
python3 tools/dev.py test --suite network --extended
```

Aircraft packet `103` adds at most one 1196-byte packet per client snapshot.
Its independent cursor examines at most the simulated entity count and sends
at most 32 already-replicated, live kind 3 actors within 1200 m. Records carry
index/generation, height, heading, pitch, bank, speed, role and mode. Speed is
metres per fixed 30 Hz tick (`0..10`), preserving the simulation convention.
Entity32 and state848 remain unchanged.

Clients validate the entire packet for finite values, bounds and enums before
applying any sidecar field. Exact entity generation and a known living kind 3
record are required. Aircraft packets arriving ahead of entity chunks are
skipped until a later refresh. Per-aircraft ticks and entity ticks reject stale
poses; session guards apply as for all snapshots. Kinds `6..9` add cosmetic bomb
launch/impact, air gun and aircraft destruction events. Damage remains
server-authoritative. The dedicated report includes transmitted aircraft record
count, separate from entity records.
