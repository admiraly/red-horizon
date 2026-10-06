# Saved input bindings

Launch the client with `--bindings /absolute/path/profile.cfg`, or use
`python3 tools/dev.py run --client --bindings profile.cfg`. The development
runner resolves the path before launching the revision-specific client. Copy
`content/bindings-default.cfg` as a starting profile. Keeping that file saves
your choices across launches; no in-game editor or runtime reload is provided.
Omit the flag to retain the existing defaults.

The file contains one `action=KEY` per line. Partial overrides are allowed;
all unspecified actions use defaults. Action names are case-sensitive lowercase,
and key names are uppercase. Blank lines, full-line `#` comments, whitespace
around names/equals and CRLF are accepted. Inline comments are not accepted.
Example:

```
forward=UP
back=DOWN
left=LEFT
right=RIGHT
command_wheel=C
command_cancel=X
```

All30 current actions are configurable: forward/back/left/right, sprint, crouch,
jump, reload, enter_vehicle, exit_vehicle, fire, tactical_map, command_wheel,
command_cancel, quit, advance, hold, retreat, follow, front_1/front_2/front_3,
weather, exchange_0/exchange_1/exchange_2/exchange_3, exchange_accept,
exchange_decline and exchange_cancel. `fire` also triggers a tactical waypoint
at the current map cursor. A wheel binding is held during selection and
released to commit; it may be a keyboard key or mouse button. `quit` cancels an
open wheel, and otherwise quits. `command_cancel` only cancels a wheel.

Physical inputs: A–Z,0–9,F1–F12, SPACE, ESC, ENTER, TAB, BACKSPACE, INSERT,
DELETE, RIGHT, LEFT, DOWN, UP, PAGEUP, PAGEDOWN, HOME, END, LSHIFT, LCTRL, LALT,
RSHIFT, RCTRL, RALT, LMB (left), RMB (right), MMB (middle), MOUSE4–MOUSE8.
Bindings are single inputs; chords, gamepads and layout-independent scancodes
are not implemented. GLFW interprets the named keyboard inputs.

Every action must have a distinct physical input. To swap inputs used by two
actions, override both in the same file. A repeated action, unknown action/key,
empty value, embedded NUL, nonregular/unreadable file, more than4096 bytes,
conflict with an overridden or default input, or repeated `--bindings` flag
fails before window initialization. Parsing stages defaults plus overrides and
publishes codes and labels only after the entire file passes. Failure preserves
the previous published table in the isolated API. Reported line is the current
parse line, or the final validation position for conflicts;0 denotes file IO,
type or size. No options are silently ignored.

The client prints all31 loaded bindings at startup. Company order, exchange,
weather, vehicle and wheel-cancel hints use the loaded labels. General help
labels its fixed controls as defaults. A delivered key or mouse quit press
survives press/release in one event batch; inside the wheel it cancels instead.
Default controls continue to use the same physical inputs. Client-local
bindings do not change UDPv27, costs, ownership, entity layouts or server policy;
cooperating clients may use different profiles.

NASM owns file parsing and dispatch. Disk access and formatting happen at
startup or existing UI updates, with fixed buffers and no input-tick allocation.
The headless parser oracle uses a development-only platform call recorder rather
than depending on graphics libraries; real GLFW/input/render behavior is checked
separately with private Xvfb and read-only authority observers. The existing
complete-game, contextual roster, adaptive tactics, platform/hardware and human
quality requirements remain open. Scoped fast64 reports (63 explicit passes plus hazard outcomes) and final seven
focused checks pass. Exact epochs, executable/library hashes, malformed cases,
fault counts and corrected read-only fixtures:
docs/evidence/input-bindings-focused.json. Main matching/full evidence is recorded
in docs/status.md; no whole-game completion is implied.

Binding contract2 appends `defend` as action30, default5. Existing action IDs
remain stable. Profiles remapping advance to5 must also remap defend to avoid
a conflict. The complete test profile uses defend9. The co-op transfer controller
stops at exchange_cancel rather than treating newly appended actions as
transfer responses. Defend authority policy and scoped evidence are described
in company-defend.md and status.md.

Compatibility note: infantry ammunition advances current peers to UDP28/schema
0x7ce46b6e/content0x6974e792. Earlier version numbers above describe the
original verified batch, not current peer compatibility.
