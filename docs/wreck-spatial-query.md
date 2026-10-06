# Captured-pose wreck query foundation

The NASM `wreck_query` ABI is in schemas/wreck_query.inc. It sweeps a point
through closed conservative world AABBs and returns the first contact and stable
wreck identity. It does not yet obstruct bodies, sight, rifles or shells, and is
not a renderer or UDP change. Activating those consumers requires visibly matched
wreck geometry, body inflation/height policy, navigation updates and replication.

A32×32 grid covers the8km map with250m cells. Each of the1024 records belongs to
one center bucket. A segment's XZ rectangle is padded6m and visits only intersected
buckets; both cell and candidate visits are bounded1024. The worst long diagonal
can visit all records; this is not a DDA or constant-time global ray claim.
Short paths in the seeded one-record-per-cell observer visit at most four records.
Coincident1024-record cases intentionally visit1024.

Bounds derive from the actual battle.rham frame0 high/low union audited in
`evidence/wreck-cover-mesh-bounds.json`: tank X±1.895,Y[.0119,2.621],Z±3;
artillery X±2.528,Y[.0163,3.200],Z±3.5, rounded outward. Each captured immutable
heading/pitch/bank transforms the local box by yaw*pitch*bank. Absolute matrix
extents produce a conservative world AABB; a2mm skin accounts for float rounding.
The source corner radii4.411/5.374m fit the6m grid margin under rotation. These are
conservative boxes, not oriented mesh contact, exact physical hulls or verified
cockpit/muzzle sockets. Low-detail vehicle roofs currently differ from high detail
by.9204/1.2990m; shrinking cover to hide that gap is not an acceptable solution.

An un-hashed derived revision changes only on registry reset, accepted death
registration or actual expiry. Queries lazily rebuild after a mutation, including
same-clock reset/re-registration and full-ring replacement. The cached grid and
bounds do not affect the registry hash. Queries preserve the full existing
persistent registry arena and all observed world checksums. This is a single
simulation-thread safe-point interface; concurrent mutation is not supported.

Caller pointer/capacity and finite bounded endpoint validation precede cache
refresh. Invalid calls return-1; malformed active source pose/identity/count
returns-2, with no result write. Hits return t,slot,entity,generation,sequence;
clear paths return0 without modifying output. Equal float t resolves by entity,
generation,sequence, independent of faction or list order. Queries do not inflate
boxes for body or projectile radii yet. Full-body contacts need a separate policy.

`test_segment_box.py` independently verifies the actual NASM double-intermediate
interval primitive. `test_wreck_query.py` rotates corners in three explicit stages
and independently scans all records for the nearest contact. It covers1024 poses,
2000 seeded paths, coincident ties/side mirrors, malformed inputs, original source
lifecycle, SysV preservation/alignment and assembled padding/nearest/cache negatives.
`test_wreck_scale.py` now queries genuine unmodified8k/16k battlefield casualties
and compares each sampled contact to an all-record interval oracle, while ensuring
world checksums remain unchanged. Detailed frozen outcomes are in the evidence
manifest; software/kernel checks do not establish visible cover or GPU budgets.

Integrated570b6ee full frozen4febd559b935 passed576.9970s/95reports, with216
authored inputs matched. All six frozen jobs and four extra exec sessions are
terminal/reconciled. Earlier NASM-setup and shared-relocation failures are retained
with exact limitations; final source/job/artifact scope is in
evidence/wreck-spatial-query-jobs.json and wreck-spatial-query-session.json.
