# Falling airframes — authority, rendering and replication

The authoritative aircraft casualty path now captures a dead body into a
separate128record pool before its flight state can be reused. Each96byte record
contains death XYZ/velocity/heading/pitch/bank, role, faction, physical source ID
and generation, birth tick, sequence and falling/landed state. Living army counts
are not inflated and no living body, HP, stores or generation is renewed.

Fixed public ticks conserve inherited horizontal velocity, add inherited VY and
existing gravity, gradually pitch/roll the dead airframe and clamp horizontal
map exits. Terrain contact uses the body centre, stops velocity and leaves a
stationary record until1800tick expiry. It is a ballistic/contact approximation:
no drag, aerodynamic glide, footprint/obstacle collision, gameplay cover or crash
blast is implemented. Ground impact currently settles pitch/bank flat. At most128
records update per tick, no allocation; oldest registration is retired under
pressure. Source-generation dedup survives retirement, new generations can
register, reserved bytes are zero and same-tick calls cannot advance twice.
Record bytes, dedup, cursor, count, sequence and last-update tick are hashed.

Independent native verification passes18 malformed/atomic cases, nonvolatile
register/stack and living-record preservation,201 pressure registrations with
128retained records, duplicate rejection and source reuse. A genuine initial
producer cannon round kills an already damaged aircraft at tick5; its actual
pose/velocity is captured exactly. Public flight reaches centre-to-terrain
contact at180, becomes stationary, expires at1805 and replays identically across
1805ticks. Maximum closed-form ballistic position error is0.016988m, from float
accumulation. The initial producer call does not debit FSM stores; no in-flight
pose/HP/ammo/generation/clock fixture writes occur.

Core evidence is air-crash-core-focused.json/.log. Frozen core-only fast
3f3fc6313036 PASSED exit0 in481.937895s and was collected. Content0x9118562d
includes seven crash policy fields; public entity/aircraft/player layouts stay
unchanged. The coherent batch is integrated on main0a1eb12 after aircraft and ordinary
network suites pass. Prior main checkpoints exclude it. All473authored inputs
match immutable full extended40b03f364420, which remains running, not passed.

The renderer builds readonly64byte instances from validated96byte snapshots.
It uses high source geometry at frame0: role3 bomber and role8 fighter, saved
heading/pitch/bank and absolute altitude, darkened wreck shading. Actor ID-1 and
side3 exclude dead airframes from living census and living mesh counters. It
uses the existing projected-span detail threshold, with a fixed128record scan
per role; tactical view also draws them. No living body or crash record is
modified by packing/drawing. Native1206calls,159 overlapping aliases, three
assembled negative controls and actual32GL poses/130080vertices pass; maximum
world vertex error0.000484m and every census code is zero.

UDP40 adds type119: slot plus full96byte current state, max11entries/1140bytes
including header. Independent fair cursors for four peers repeatedly stream all
used128slots and expiry tombstones, irrespective of camera. Whole-packet
validation rejects malformed/duplicate slots and current identity conflicts
before any cache/timestamp mutation. Modular source-tick/sequence ordering drops
stale history. Same sequence fixes source/role/faction/generation/birth, same
tick repeats exact state/pose, and landed geometry cannot move/resume flight.
Latest accepted server ticks expire records; close/timeout/reset clears history.
Clients draw accepted snapshots only: no local physics/extrapolation, so loss
can visibly hold/step motion. There is no reliable completion barrier.

Native53cache calls cover26malformed atomic packets, lifecycle and
wrap guards, ABI and three assembled negative controls. Unchanged production
sender over real UDP recovers all128slots for each of four peers in12snapshot
opportunities; max packet1140bytes, source readonly, virgin silence and tombstone
stream retained. Its capacity fixture admits initially dead physical records
through the helper and sets one standalone expiry clock; this is separate from
actual real-time combat.

Actual8192unit server aircraft FSM spends finite cannon ammunition and destroys
a declared initial24HP target. Two initial matching-generation aircraft births
are the only process writes. First peer sees falling state, second joins after
casualty and recovers it, both see landed state. Genuine packets replay through
actual client adapter under drops/reordering/duplicates. Ordinary run proves
falling/landed and source-byte matches; real-time1800tick expiry is claimed only
when the extended focused run passes. That run now PASSED:978authentic
packets,815exact source matches, actual falling/landed/expired phases, late join
and1140byte maximum retained, genuine FSM store debit. No real-time clock writes.

Actual client GL local and UDP fixtures display both genuine public-cannon
casualty roles at death,30ticks later and terrain contact, then draw no mesh at
expiry. Eight paired samples retain source bytes, living counts and frozen local
ticks; visible meshes change351..698pixels, expiry zero. These are frozen
cosmetic client fixtures from separate genuine authority replays, not live
server/client synchronisation or spectacle acceptance. Paired backgrounds clear
presentation cache; UDP then receives through actual parser before completed
draw. Independent role fixtures relocate only birth/sequence in the transport.

Four setup failures are retained in evidence: first producer fixture omitted
its required target; UDP cosmetic fixture set sim_count0 despite the existing
client replica loop requiring nonzero admitted count and exited with SIGSEGV;
fixture now uses one dead actor as the pre-existing wreck observer does. A
production sender label typo prevented the first server assembly; fixed before
transport tests. An ad-hoc library link used wrong object filenames; corrected
to actual .asm.o build outputs. No underlying zero-army runtime fix is claimed.

No aerodynamic drag/glide, footprint/obstacle collision, cover/crash blast,
authored destroyed geometry, energy/fuel/stall/landing, full tactics or spectacle
acceptance follows from this batch. The complete game goal remains active.
