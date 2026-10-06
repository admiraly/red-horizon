# Owned-company supply report prerequisite

Isolated feature/company-supply-report, based on depot merge99a6e5f. The NASM
read-only API validates the actual bidirectional player/body-generation lease
and player front, then visits at most128 physical IDs in that own company.
It excludes dead bodies, other fronts/sides and non-infantry roles. Output40
bytes contains player, body generation, company, living infantry, low/empty
counts, known rounds and unknown-stock count; two reserved words are zero.
Low means30 carried rounds or fewer and includes empty. Generation-mismatched
or malformed stock data is unknown, never silently full or empty.

Caller provides a disjoint writable40-byte buffer and a sequential authority
safe point. Failure preserves the entire output. Successful publication follows
complete local staging. No source state, ownership, clock, pose or stocks change.
A downed connected owner retains a report during the deployment interval.

Independent static query fixtures on actual assembly authority pass: initial
four infantry/480 rounds; two low, one empty, one unknown/140 known rounds;
death/front changes exclude actual members; unknown source and foreign-side
records cannot enter totals. Invalid owner/lease/body/front/count/size/null
checks are atomic and caller guard bytes survive. Evidence:
evidence/company-supply-prerequisite.log, including exact frozen core object
and report-module hashes. Initial attempt to link ordinary RIP-relative assembly
against an external shared dependency failed ELF PC32 relocation; the corrected
fixture links frozen copies of the real core objects together, matching normal
project linkage. Failure is retained separately.

Not integrated, not HUD/network shortage support. Remaining: ABI probe, original
scale/real ownership changes, bounded versioned owned-company/depot packet,
atomic remote validation and reset/stale handling, solo/co-op truthful HUD with
unknown/unavailable/low/empty states, actual rendered and fault tests. Then
supply-aware routes must preserve primary orders, hazards and finite inventory.
