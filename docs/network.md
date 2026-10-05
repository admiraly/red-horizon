# Authoritative Linux UDP transport proof

`src/net/server.asm` is a standalone NASM Linux UDP server bound exclusively to
127.0.0.1. It demonstrates bounded parsing, server-owned assignments and resource
spending, ordered sequence acknowledgments, and four independent endpoints. It
does not implement a playable cooperative game or connect to the simulation.

Build and verify:

```sh
python3 tests/test_net.py --nasm nasm
nasm -f elf64 -g -F dwarf src/net/server.asm -o build/server.o
cc build/server.o -o build/udp-proof
build/udp-proof --port 0 --packets 45
```

Port zero selects an ephemeral UDP port; startup prints and flushes JSON with
its assigned port and protocol version. `--packets` accepts 1..10000 datagrams,
including rejected packets. The server reports received/rejected totals and exits
zero after that bound, or exits three after two seconds without traffic. Bad CLI
arguments exit two; socket/bind/receive failures exit one. All resources close on
normal, timeout, and reported error exits. Runtime uses Linux socket syscalls;
libc supports CLI string comparison and diagnostics only.

Protocol version 1 uses exactly eight unsigned little-endian 32-bit words:

| Offset | Request | Response |
| --- | --- | --- |
| 0 | Magic `0x52484e31` | Same canonical magic |
| 4 | Version `1` | Version `1` |
| 8 | Assigned client ID; zero for join | Server-assigned client ID when known |
| 12 | Sequence starting at `1` | Echoed sequence |
| 16 | Operation: join `1`, spend/order `2`, snapshot `3` | Operation with high bit set |
| 20 | Company for order; zero otherwise | Status |
| 24 | Spend amount for order; zero otherwise | Assigned company when state returned |
| 28 | Target coordinate for order; zero otherwise | Current resource balance when state returned |

Each endpoint is the source IPv4 address and UDP port. Join requires client zero,
sequence one, and zero payload. The server allocates a free slot and assigns its
company/client ID in `1..4`, with a balance of 100. The client cannot select an
owner. Additional endpoints receive capacity status. Join/snapshot responses are
minimal assignment/resource snapshots; they do not contain spawned game entities.

An order requires the endpoint's assigned client ID, its own company, a spend
of `1..100`, a coordinate of `0..8000`, and sufficient remaining resources.
The sequential authoritative loop checks then subtracts the balance once, without
client-supplied damage or ownership authority. It does not yet execute a movement
order in a world. Each client may attempt at most 16 orders per proof session;
additional orders are rejected. This is a bounded command budget, not a measured
per-second rate limiter or a production abuse-control policy.

Sequences must equal the previous authenticated sequence plus one. The immediate
previous sequence receives duplicate status and current state without repeating
spending. Older or future sequences are rejected. Commands with the next sequence
consume it even if their payload/ownership/resource/budget validation fails.
Invalid protocol versions and wrong client IDs do not consume a sequence. There
is no sliding receive window or acknowledgment bitmap in this proof.

Status values: `0` accepted, `1` malformed/version/op/payload, `2` duplicate,
`3` out of order, `4` unauthorized identity/endpoint, `5` company ownership,
`6` insufficient resources, `7` command budget, `8` client capacity. State is
returned for accepted, duplicate, ownership, resource and budget responses.
Other rejected responses may return zero state; clients can request a snapshot.

Receive storage is fixed at 1200 bytes (the MTU contract). `recvfrom` uses
`MSG_TRUNC` to observe the actual datagram size before parsing any fields. The
fixed version accepts only exactly 32 bytes. Empty/short/long messages, including
1200-, 1201-, and 65000-byte datagrams, reject safely without reading outside the
buffer. Client records and output packets use fixed storage; no hot-loop allocations.

Verification on 2026-10-05: Linux `7.2.6-201.nobara.fc44.x86_64`, NASM `2.16.03`,
GCC driver `16.2.1`. The test passed 45 real UDP datagrams plus inactivity timeout
and five invalid CLI cases in `2.040496` seconds including assembly/link. Four
real sockets join and operate independently; a fifth is denied. Tests verify
length/version bounds, endpoint identity spoofing, company ownership, insufficient
resources, coordinate/cost bounds, duplicate and stale acknowledgments, rejection
of a future sequence followed by successful ordered retransmission, and the fixed
command budget. The driver deliberately discards one successful ACK, retransmits
the order, and verifies the balance changes only once. Reordering is produced by
sending the future sequence before the missing sequence over actual UDP sockets.

Limitations: loopback only, no discovery/NAT/public authentication or encryption,
no client prediction/interpolation, entity spawn/replication, join-in-progress
world snapshot, disconnect/reconnect ownership recovery, selective reliability,
fragment reassembly, latency/jitter/loss emulator matrix, or bandwidth benchmark.
The protocol is an isolated proof contract, not the shared game's final schema.
No claim of playable co-op, four-player gameplay, or internet security follows.
