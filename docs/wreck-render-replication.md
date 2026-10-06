# Immutable wreck rendering and UDP lifecycle

UDPv8 adds NET_WRECKS106. The actual40-byte header is followed by slot+record64
entries without a count prefix; payload length determines1..17 entries, for a
maximum1196bytes. Server snapshots send one additional bounded fair global packet
per connected client, including used inactive slots/tombstones. Virgin sequence0
slots are skipped. Every full registry slot can be visited within61snapshot
opportunities absent loss. This is repeated unreliable state, not a reliable
late-join completion barrier or guaranteed per-wreck latency under packet loss.
It is camera/distance independent. Live entity32/state848 sizes are unchanged.

Version/schema/content identity changes explicitly; content includes static
presentation and wire policy. A dedicated client cache keeps immutable pose,
source identity, birth/expiry and per-slot source tick/sequence. Entire payload,
duplicate slots, finite/bounded pose, role/side/generation/sequence, canonical
upright fallback, reserved fields and age/expiry validate before any mutation.
Nonstale same-sequence immutable conflicts reject the complete packet. Modular
source-tick/sequence guards reject old slot history; equal sequence cannot revive
an inactive record. Client clock expiry follows latest accepted server tick,
without local simulation/pose prediction. Timeout/disconnect clears the cache.
New generations may leave old death history in other slots. The cache is excluded
from authoritative registry/hash; it is not consumed by collision yet.

The renderer uses captured XYZ/heading/pitch/bank and high-detail frame0 source
geometry, with a restrained darkened material. No live clips, terrain resampling
or spring alter death pose. Wrecks have a separate instance count, negative army
census ID and scenery side3; they do not consume living high-detail budgets or
inflate living army counters. Local draws read sim_wrecks; connected draws read
net_wrecks. A800m source-mesh range culls distant first-person wrecks; tactical
view submits them, but tiny geometry need not produce a surviving map pixel.
Physical cover is not activated by this change: body/LOS/rifle/shell/navigation
hooks, far cover representation and near-priority/reliable recovery for predictive
collision remain required before complete useful-cover acceptance.

Tests verify actual NASM whole-packet/cache/lifetime behavior,1024slots, hostile
batches, immutable conflicts, retirement/reuse/wrap, SysV and three assembled
controls. Actual adapter tests exercise session/version/schema/content rejection,
remote-only warmup, stale/retired history, clock expiry, timeout/disconnect and
unchanged authority. Actual8192-unit server combat creates a vehicle casualty
from two declared births; no later HP/pose/clock writes occur. A client joining
later receives that existing distant wreck, authentic packets replay with drops/
reorder/duplicates, and extended verification observes real1800-world-tick expiry
on the wire. The original UDP fault matrix remains a separate full checkpoint.

Actual local/controlled-UDP graphical clients verify tank/artillery near/mid/map/
far instance selection and immutable captured pose, with959/2370near and9/23mid
changed pixels in the frozen640×360 fixture. Map instances submit but produce0
measured changed pixels;900m wrecks are culled. Living mesh counts remain unchanged.
The fixture uses actual registry-helper geometry and a stopped cosmetic clock;
UDP camera/player fields are a labelled display fixture, not natural networking
or gameplay acceptance. Separate real-server death/expiry tests provide lifecycle
evidence. Existing shader transform feedback verifies128832vertices and zero
living census IDs. All these graphical observations are softwareGL, not target
hardware/1080p60 budgets or human audiovisual quality.

The first co-op adapter freeze fixture assumed one poll drained all final queued
packets. New streams exposed the backlog; it now receives the server's actual
final snapshot before asserting no local ticks. The32-packet budget is unchanged,
and final authoritative tick equality is additionally required. Other original
physical/scale/health/arrival/symmetry checks are retained.

Frozen extended checkpoint e9a99f39beb8 passed659.9070seconds/101reports at
5a4965590aff4492729e112ff5c9eb7ae791bce0-1d14e8137c7509f0, with all227authored
inputs matching the checkout. Seven batch frozen jobs are terminal. The original
scale, health, label symmetry, arrival/recovery and UDP fault gates remain intact.
Exact snapshots, reports, retained failures and selected actual client images are
under evidence/wreck-render-replication-*.

A separate synthetic full1024-slot fixture exercises the actual serializer and
cache:61snapshot packets cover the ring; reverse authentic-payload replay keeps
the cache unchanged. It does not establish1024natural casualties. Prior accepted
and current simulation modules match every observed authoritative arena and
checksum at every tick of120tick8k/16k comparisons, including the complete
196620-byte wreck registry/history/metadata arena.

The expiry/capacity observers initially discarded snapshots inside command ACK
waits. RecordingPeer retains them. The extended server now runs2160rather than
1890ticks to leave a complete post-expiry sweep window; lifetime remains1800ticks.
A subsequent UDP graphical observer stopped amid reset draw telemetry. It now
waits for the received record, then five frames and required stable pose/count
before readback. Three repeated actual UDP draw checks and the final full frozen
run pass. Failed logs remain in the ledger.

Prepared5c12613 body/source-context work is isolated and documented in
wreck-body-query-prepared.md. It includes no-deepening planar overlap escape,
explicit local/remote source context, remote mutation revisions and memoized
validated transforms. None activates movement, weapon, LOS or navigation cover.
Near-player replication freshness, useful far/map presentation and enabled-cover
budgets remain part of the next coherent integration.
