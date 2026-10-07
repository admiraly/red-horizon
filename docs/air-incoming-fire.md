# Visible incoming cannon fire

Aircraft now observe actual opposing cannon traces before damage and commit the
existing defensive manoeuvre when a visible round is approaching within750m.
The observer uses the aircraft's actual XYZ velocity, a forward120degree cone,
terrain/world line of sight, and relative closest approach within30ticks and the
round's remaining lifetime. A predicted pass within10m is a warning, not a new
collision radius. Existing projectile collision and HP rules are unchanged.

One fixed512slot scan builds a250m spatial grid each air tick. Each eligible
actor examines at most49cells,64round records and2LOS calls. Cell priority rotates
with tick and stable physical ID. Selection is deterministic among examined
visible candidates; bounded work can miss threats or a globally earlier threat.
No enemy shooter pose or intended target is read. A valid conserved round can
remain dangerous after its shooter dies. Stale generations, invalid metadata,
nonfinite coordinates/velocity and stale indexes are rejected.

Warning commits the same nonrenewing48tick fighter/90tick bomber break used by
the surviving-damage hook, with150/210tick refractory intervals. The direction
is chosen away from the predicted lateral pass, with stable-ID tie breaking,
and is included in the authority checksum. Fighter bank reverses halfway
through the manoeuvre; boundary protection still wins. Private grid and metrics
are derived and excluded from authority. No ammunition, HP, clocks or generations
are renewed. Content fingerprint0x2a371472 rejects mixed policy peers; UDPv39 and
public entity/aircraft/player layouts are unchanged.

`tests/test_air_threats.py` assembles the real NASM runtime plus a query-disabled
control. It verifies815 independent geometry cases, ABI/stack/output guards,
authority read-only queries, eleven malformed metadata cases, dead shooter and
hidden shooter controls, stale-index rejection, actual terrain occlusion,
labels-only faction mirroring and127 genuine producer rounds under query caps.
Its initial producer call does not debit FSM-owned ammunition. Subsequent public
flight updates use real finite stores without world writes. The80tick head-on
fixture reacts at tick1 before HP loss, banks before damage, and ends at152HP
versus32HP in the warning-disabled control; both take their first hit at17.
Both traces replay exactly. This proves one bounded encounter, not general
survival advantage or complete combat tactics.

Focused aircraft regressions retain original8192 natural flight and finite
weapons, sparse combat, admission/fairness and physical guidance coverage. Real
GL verifies production bombing, cannon contact, bank, trails and destruction.
These observations do not establish spectacular presentation or full flight
physics. Fixed cruise, limited vertical envelope, level-turn approximation,
missing aerodynamic energy/fuel/stall/landing systems and broader coordinated
tactics remain limitations. Full-game specification acceptance remains open.
