# Prepared immutable wreck rendering input

Root-owned isolated feature/wreck-instance prepares a stateless NASM helper from
an active64-byte authoritative wreck record into the existing64-byte mesh shader
instance. Captured XYZ/heading/pitch/bank stay immutable; animation is fixed at
frame0 with no terrain, ground spring, observer state or live-entity access.
Unit scale and absolute height preserve the actual support/contact capture.
Negative actor ID and scenery side3 exclude destroyed vehicles from living army
visibility counts. The helper is single-thread/read-only with copy-before-commit
alias safety and rejection without caller writes. It is not activated by the
client, not a descriptor selector, not replicated and not gameplay cover.

Initial presentation policy should select actual high-detail frame0 geometry for
all wreck mesh distances, retaining the audited high/low union collider. A live
unit's shortened low-detail roof must not silently replace the solid wreck roof.
Subsequent simplified wreck geometry needs measured bounds/silhouette fidelity.
Distance culling/markers, charred materials, wreck fire, instance budgets and
hardware performance remain separate work. A conservative AABB also covers empty
corners outside an oriented mesh; that physical approximation remains explicit.

The prepared observer verifies1024poses,127 overlapping source/output offsets,
invalid/inactive inputs and SysV register/stack preservation. Three actually
assembled controls lose pitch, select a live frame or restore an army identity;
the observer rejects each. Actual existing mesh shader transform feedback uses
32 packed instances and high-detail frame0 tank/artillery geometry, with128832
transformed vertices and maximum world-position error0.0004868m. Every emitted
census actorCode is0. This is llvmpipe GL4.6 on Mesa26.2.3, not hardware budgets or
visible draw-hook/real combat/replication acceptance.

The first development GL observer wrote28-byte feedback records after adding the
32-byte actorCode layout. Correcting its fwrite stride fixed reporting; the NASM
helper was unchanged. Final report is retained by the integrator separately from
the main query foundation's frozen full-checkpoint evidence.
