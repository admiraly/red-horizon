Historical preparation evidence: primitive integrated at686d20f, spatial query
at570b6ee, full checkpoint4febd559b935. Original isolated scope follows.

# Prepared swept segment/AABB contact primitive

This isolated follow-on dependency consumes a caller-owned minXYZ/maxXYZ box
and start/end XYZ. Actual NASM/SSE2 validates pointer/capacity, coordinate
magnitudes/finite values and box ordering before clipping. It returns hit/clear/
invalid plus the first parametric contact on a hit. Closed faces, endpoint
contacts, start-inside and zero movement are explicit semantics. Double SSE2
intermediates evaluate the exact float32 inputs before returning float32 t.
All inputs are bounded to ±16,000, enclosing the current8km world and its cover
bounds. It writes no input/global state and preserves SysV nonvolatile registers
and stack. It is not a physical wreck implementation or oriented shape contact.

The independent interval oracle passes10,085candidate cases,1,515hits and
67invalid cases with unchanged input boxes/first input on rejection. First-t
error is at most2.966619327970932e-8. Coverage includes all three axes, reverse
motion, degenerate boxes, grazing, parallel misses, tiny deltas, signed zeros,
10,000seeded arbitrary boxes/segments, bad bounds/coordinates/capacity and null.
Actual assembly variants removing Z, rejecting grazing or returning the last
contact all fail the same oracle. Six preserved-register sentinels/stack probes
pass. Kernel SHA17c77f6ac2838eb17237bd4f29e40f2c539e4dfbd8944613a513d539bb495a99.
The initial reporting wrapper mixed the intentional last-contact negative's
0.25error into its candidate metric; candidate assertions themselves passed.
The corrected wrapper snapshots candidate metrics before running negatives.
Root retains both reports with that distinction; no runtime change was needed.

This remains isolated in feature/wreck-sweep, based on143247e. It is not in the
root full-checkpoint sources. Before integration, define captured-pose cover
bounds, bounded spatial search and nearest identity/sequence selection. Use this
first-contact primitive for candidate boxes, then verify actual LOS/rifle/shell
and body behavior, expiry and physical recovery. Renderer and UDP lifecycle still
need coherent implementation. A direct all-wreck scan per army actor is unsuitable;
prepared clipping tests cannot establish useful cover, scale or remote rendering.
