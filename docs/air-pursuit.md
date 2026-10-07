# Confidence-weighted fighter pursuit

A fresh sighting remains a strong pursuit goal. As the fighter's own sighting
confidence declines over the existing90tick memory lifetime, yaw guidance
interpolates along the shortest angular arc toward its own mission or friendly
escort goal. It blends directions, not distant world positions: a far waypoint
cannot dominate merely because it is farther away. The deterministic antipodal
tie keeps the signed180degree difference. Exact0/1 confidence endpoints preserve
the mission/pursuit headings. Boundary heading recovery bypasses this blend;
visible-fire/damage defensive heading still overrides it afterward.

Vertical guidance blends the separately clamped pursuit and own terrain-clearance
vertical requests, each bounded to0.5m/tick. Emergency climb bypasses the blend,
including its final countdown tick. The existing vertical acceleration limits,
physical bank/yaw limits and total XYZ cruise speed remain. No body, HP, stores,
generations or clocks are written by the pure blend helper. Guidance uses the
same private observed snapshot; no hidden enemy reads are introduced. Existing
finite cannon and bomber admission/flight paths remain.

Observation policy version2 records this gameplay change in compatibility
content0x5d86b7ad. Build canonicalization and independent co-op expectations match.
UDP39/schema0x212cb081/public record layouts are unchanged. Matching policies
are required when restarting client and server.

The independent native probe tests5000 angular cases using complex rotation as
the shortest-arc oracle,5000 vertical cases,26 malformed input/ABI cases, exact
endpoints, signed antipodal ties and the heading seam. Maximum oracle error is
0.000000503. A separate matched360tick initial-birth-only public flight comparison
uses a full-strength-pursuit NASM control. Both repeat exactly, retain two genuine
rounds,176HP and179rounds each, and178 memory-only samples. Emergency sample30
is identical. At observation ages75..89, the weighted fighter's mean mission
heading error is lower by more than0.3radians. This demonstrates a bounded return
toward its mission; it does not prove general combat effectiveness or survival.

The hidden-body steering control now preserves cached confidence while replacing
only observed XYZ/velocity with live body data. Its separate getter fixture uses
opposing10m vertical alternatives after20ticks, within the existing displacement
envelope; it does not claim these alternatives are physically flown. Candidate
steering is unchanged; the control changes climb direction. The previous control
omitted confidence and its first run failed; it was corrected, not waived.

Fixed cruise speeds, approximate level turns, limited climb, lack of aerodynamic
energy/fuel/stall/landing, full sensor fusion, wing coordination and broader
operational tactics remain open. This is not spectacular art or whole-game
specification acceptance. Actual graphs, scale and network have separate scoped
evidence; full extended integration is a separate checkpoint.
