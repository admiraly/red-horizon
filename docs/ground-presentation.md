# Ground heading replication and presentation

The production server sends an independent NET_GROUND105 packet per client
snapshot. Each packet contains at most18 self-contained64-byte records, including
entity32 and heading/signed speed/applied turn/accepted planar velocity, live flag,
and a zero reserved word. Maximum UDP datagram size is1196bytes. The cursor is
independent of sparse entities, aircraft and projectiles, examines no more than
sim_count actors, and starts each bounded packet with a legitimate owned hull.
That priority validates both ownership directions, living allied tank identity,
entity generation and the owning player's stamped generation. It neither increases
the actor cap nor replicates the whole army to each client. Dead stamped hulls are
sent as tombstones with flag0 and zero speed/turn/velocity; retained heading is safe.

The assembly client validates a whole batch before changing entities, poses or
per-actor timestamps. It rejects duplicate IDs, nonzero reserved words, mismatched
live/dead flags, invalid generation/role/health/side/front/target, nonfinite or
out-of-map coordinates, and poses outside the wire envelope. Velocity uses a
planar norm bound, rather than two independent component bounds. Independent
records warm an unseen hull without requiring NET_ENTITIES first. Same/older-tick
sparse chunks cannot overwrite a received hull's pose or position. Generation
reuse replaces the old pose; explicit wire tombstones prevent equal-generation
revival through either packet type. An explicit death-generation stamp separates
actual server death from client interest hiding, so returning living actors can
re-enter interest. Close, reconnect and timeout clear hull poses and their stamps.
No client-only ground actuator advances these received records.

Both sourced near/mid hull instances and distant/tactical markers consume the
same kind/generation/active stamped authoritative heading. This includes tracked
pivots at unchanged XZ. Infantry and aircraft paths retain their existing behavior.
The renderer only reads the sidecar. Existing displacement-derived cosmetic
heading is fallback for unavailable/stale sidecars, not a claim of physics.

`tests/test_ground_network.py LIB SERVER` exercises the assembled parser and a
real2048-actor dedicated server. Its only server fixture write places a living
player beside an initialized allied tank; normal ENTER input establishes the
claim. It checks owned-first packets, fair refresh beyond18 distinct hulls,
authentic moving poses, bounded datagrams, and replay of captured ground packets
without sparse chunks under deliberate drop/reorder/duplication. Parser fixtures
also test malformed whole batches, schema/content/session rejection, generation
reuse/death, sparse precedence, interest return and disconnect/timeout clearing.

`tests/test_ground_gl.py CLIENT` uses a private Xvfb software OpenGL session and
the production sourced meshes. Development-only frozen entity/pose fixtures
isolate a stationary heading pivot; uploaded instance data and changed pixels
verify the same actual heading across near/mid/distant/map paths. It compares
entity/sidecar bytes before and after rendering to prove read-only presentation.
This is renderer evidence, not a demonstration of naturally produced physics,
GPU performance or artistic acceptance on the target Arc A770.

Private integration dependencies are ground collision51cdb7d, ground actuator
a07d91c and root world/vehicle hooks dcd5ddf, plus shared protocol575010f corrected
by d587016. Exact final verification results are reported with the worker commit;
root owns full frozen integration, Windows, scale and all-spec acceptance records.
The initial standalone parser probe used a static zero ground-array export solely
to test parsing before the actuator was available. Final tests use the real module.

Final private proof on the authored candidate (real module/hooks, no static stub):

- Dedicated-server/parser test exit0:26 malformed/header/session fixtures rejected;
  45 authentic ground packets,45 owned-first snapshots,127 moving hulls observed,
  799 wire records exactly matched contemporaneous real entity/sidecar bytes,
  including739 moving records; maximum datagram1196bytes. Ground-only warming,
  one intentionally dropped snapshot, reordered/duplicated captures, sparse
  tombstones, tick-zero death, and interest return all passed. Live reads can
  observe a later tick, so unmatched samples are not claimed as exact matches.
- Real-client software GL test exit0:2956 source-hull pixels against empty-scene
  control and2772 changed pixels for a stationary heading pivot. Both ground
  roles retained the same stamped heading at mid/distant/tactical detail; stale
  generation/inactive fallback and entity/sidecar read-only checks passed.
- Final private logs: `/tmp/ground-final-network.log`,
  `/tmp/ground-final-gl.log`, `/tmp/ground-final-coop-build.log`, and
  `/tmp/ground-final-client-build.log`. All foreground job handles were collected.
  These are focused worker proofs, not a new frozen full-suite, four-client scale,
  Windows or target-GPU acceptance claim. Root must verify the integrated SHA.
