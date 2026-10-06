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
