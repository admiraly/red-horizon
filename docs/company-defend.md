# Defend an area

Default `5` orders the selected owned company to defend its accepted waypoint,
using the player's position if no waypoint exists. Hold the command wheel and
release in the upper-right diagonal sector to defend the visible crosshair
terrain point instead. `defend` is a saved, remappable action. An accepted command
costs five requisition; rejected commands do not spend. Network feedback appears
after the authoritative acknowledgement, with no optimistic ownership changes.

Living owned infantry and tanks take stable positions around the selected point:
eight directions per ring, starting24m out and adding12m per row of eight stable
company IDs. Artillery occupies a12m grid240–420m behind the perimeter in worldX.
The effective anchor is clamped480–7520m on each map axis to leave space for the
formation and its bounded placement search. The accepted raw point stays stored;
the tactical marker shows the effective anchor. Owner movement or mouse aim does
not move or rotate the defense.

Each position uses the actor's actual role footprint, terrain solids and slope
limits. The search tries the original destination followed by at most four12m
westward alternatives. An actor holds when none is valid and rechecks normally.
Defense uses existing movement, navigation, cover and crowd handling. Actors
still acquire and fight observed targets with existing finite ammunition;
incoming explosive hazards have priority over their defensive destination.
Disconnect restores autonomous command. Stale owner/body generations cannot
issue or sustain an owned command. Explicit transfers retain the stored intent.

This is a fixed physical defense formation. It does not establish adaptive
entrenchment, globally optimal cover, arbitrary terrain reachability, universal
nonoverlap after projection, complete squad tactics or survival against every
shell. The remaining contextual order roster, shared assault planning, full
operation, Windows parity and hardware/human quality acceptance remain open.

Compatibility: company-control policy3 and UDP27; record sizes stay unchanged.
Both peers must use schema0x24a8a531 and content0x00ac549b. Old peers fail the
existing compatibility gates rather than interpreting mode4 differently.
Exact scoped results and pending full checkpoints belong to `docs/status.md`.

Compatibility note: infantry ammunition advances current peers to UDP29/schema
0xc400bad2/content0x5964d91f. Earlier version numbers above describe the
original verified batch, not current peer compatibility.
