# Company retreat display

The tactical marker now follows the effective retreat home shared with the
production company controller. The accepted waypoint stays separate, so changing
back to advance resumes the previous waypoint. Own and other-player company
views use the same validated replicated mode. No UDP contract or authority
movement/spending policy changes.

Focused evidence: docs/evidence/company-retreat-focused.json and raw logs.
Actual solo input/GL proves home marker and restoration. Two actual UDP/render
clients prove both fronts, each owner's marker and the other player's view,
with zero local simulation ticks. The original fast suite passes. Initial new
co-op fixture failures are preserved: second command was too early for the
existing 15-tick server order limit. Corrected fixture waits for authority time;
the production limit remains intact. Full scale/extended and hardware quality
acceptance remain separate.
