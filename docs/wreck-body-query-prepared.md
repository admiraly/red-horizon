# Prepared conservative body query and overlap escape

Isolated feature/wreck-body-query builds on the measured62.5m grid. It retains
the existing point query unchanged in observed behavior and adds wreck_body_query:
result24/capacity, startXZ/endXZ and radius0..4.491. The world AABB projects toXZ
and inflates both axes, matching the existing conservative planar-body approach.
This is a square Minkowski approximation for nominal circles, not oriented hull,
vertical capsule, mesh contact, jump or vault collision. Terrain/map/body-grade
validation stays with the eventual actor movement caller. Remote cache/context
support and actual actor/nav/controller hooks are not activated.

A newly created conservative wreck box may include a nearby actor that was outside
its previous living body's circle. Blanket start-inside rejection would trap that
actor until expiry. The prepared query ignores such an overlap only for nonzero
movement with nonincreasing distance to at least one initially nearest face. Face
distances along a straight path are affine; the minimum can then never exceed its
initial depth. This permits outward escape or a parallel slide without deepening,
while rejecting movement through the center toward the opposite face. Zero motion
still returns occupied. Every other wreck remains an independent swept blocker;
allowed escape from one cannot bypass contact with a second.

The actual NASM observer verifies2514calls/2500seeded paths using original sweep
radii0/.551/3.551/4.491, explicit outgoing/inward/slide/zero/cross-center cases,
readonly authority, SysV/helper alignment and malformed radii. Independent closed
interval contacts match exactly at float result precision.821allowed overlaps
also have101sampled continuous depth checks each. Three assembled negatives omit
inflation, allow arbitrary deeper escape or clear zero-motion occupation; all are
exposed. The original point observer also passes2063calls/1024transformed boxes/
8628actual frame0 vertices, including its three assembled controls.

This remains a prepared query, not evidence that the army can move around wrecks.
Integration must seed local detours/coalesce invalidation, maintain shared driver/
AI physical hull reachability, preserve original arrival/recovery/army motion and
health/symmetry gates, and match connected-client prediction with remote cover.
Vertical gameplay and oriented physical geometry remain open requirements.

Prepared follow-up f263e33 adds explicit caller-owned source/count/revision
variants for point and planar body queries. Cache identity includes source pointer
and derived revision, so sequential authority/remote searches cannot reuse another
source's bounds even at equal revisions. Existing wrappers continue to select
authoritative state.389calls cover128same-revision source switches, immutable
sources/authority, declared retirement/replacement, invalid source/count and two
assembled missing-key faults. Original point/body observers still pass.

The context API does not select net_wrecks, publish its revision, or activate
connected-client movement. Caller storage must be valid and stable; every source
mutation must advance its derived revision. Shared scratch/cache is sequential
simulation-safe-point state. Concurrent use requires independent query contexts.

An additional isolated follow-up exports net_wreck_query_revision outside the
existing remote record/validity arena. It advances after changed accepted records,
actual expiry and reset, while identical heartbeat/stale/invalid/no-op expiry
preserves it. The actual remote NASM receive/expiry/reset functions now drive the
explicit query context in395calls, including delayed no-revival and replacement.
The original97-call remote observer and its three assembled faults still pass.
This verifies cache lifecycle plumbing, not connected-client movement hooks.

Prepared5c12613 retains a65536-byte derived exact-record memo. A rebuild still
validates/indexes the1024-slot bounded source and active count, but previously
validated identical active bytes reuse their slot bounds. Changed records are
fully validated and transformed. A512-active fixture records transform counts
512/0/1/0/0/0 across first load, unchanged revision refresh, one changed slot,
identical source switch, expiry and exact-pose reactivation.401context calls and
three assembled faults pass, including omitted pose bytes in the memo comparison.
The original point/body regressions pass against this prepared query. No full
enabled-cover tick budget or concurrent cache use is established.
