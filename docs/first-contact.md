# Projectile actor first entry and pending cover arbitration

The shared shell/air-gun actor query now selects the earliest entry among its
sampled opposing live actors. Previously it returned the first sampled actor
whose center was within4m of the segment. The retained4m proximity envelope is
explicitly not an oriented mesh hitbox. Sampling remains at most216actors from
nine neighboring start cells; dense cells can omit actors. Friendly actors still
are excluded by the existing policy. These are remaining physical fidelity gaps.

The closed sphere primitive uses double SSE2 intermediates and closest-line
projection to avoid distant discriminant cancellation. Start-inside gives t0;
tangency/endpoints are included. Finite coordinates and positive bounded radius
are validated before arithmetic. It writes no input and preserves SysV state.
Production contact XYZ is interpolated from first t, returned inXMM3. Ties use
physical ID, keeping faction labels out of the tie rule. A conservative swept XZ
rectangle filters far samples before costly height queries.

A real production-index observer uses only initial declared births and one public
tick, then readonly queries. It catches the prior build selecting a farther low-ID
actor and verifies the corrected nearest contact, reverse rays, physical ties,
zero motion, friendly exclusion and grazing.207calls/200paths pass. The primitive
also passes5086calls/5000independent80-digit reference paths and three assembled
faults, with maximum first-t error2.961e-8.

The policy is fingerprinted in UDPv9/schema0xf90d92f8/content0x10001089. Wire
payload layouts are unchanged. Full extended cb0726815280 passes644.1174s with
103reports and234matching authored inputs, retaining original scale/replay,
health/label symmetry, arrival/recovery, real GL/audio and UDP fault scopes.
Exact evidence and focused snapshot differences are under evidence/first-contact-*.

Remaining arbitration: projectile_tick still checks the whole terrain segment
before asking for actor contact. A nearer actor can therefore be ignored when a
wall lies farther along the path. Wrecks are not physical blockers yet. The next
resolver must compare typed first contacts across terrain, wrecks and actors,
prevent retired wreck IDs from reaching live damage, preserve exact impact XYZ,
and supply coherent blast LOS and body/navigation behavior. Old eight-step
terrain bisection and seven height samples do not establish exact surface entry.

Prepared isolated8c6791e terrain_solid_query finds exact closed first entry across
the five authored terrain boxes. Its3068calls/3000paths include readonly/SysV,
flags/ties, malformed-source atomicity and four assembled faults. It excludes
analytic ground, actors and wrecks and activates no runtime hooks. Future ground
contact must handle the shared raised height field and ridge without claiming
that fixed-solid box math proves the full terrain surface.
