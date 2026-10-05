# Linux M0 reload proof

This standalone NASM host verifies compatible code and validated parameter changes
without restarting its persistent state. It is a foundation experiment, not a
live game/session reload implementation.

Run the development-only builder and black-box suite:

```sh
python3 tests/test_reload.py --nasm nasm --build-dir build/reload
```

The test produces `reload-proof`, `v1.so`, `v2.so`, `bad.so` (incompatible schema),
and `no_symbol.so` (missing API). Build outputs are local to the selected directory.
The linker driver is `cc`; all authored runtime logic and shared modules are NASM.
The executable uses libc printing and POSIX loader services; no C source is used.

Run the proof directly with six paths:

```sh
build/reload/reload-proof build/reload/v1.so build/reload/v2.so \
  build/reload/bad.so build/reload/missing.so \
  build/reload/valid.params build/reload/invalid.params
```

The executable emits six JSON lines. With valid parameters `5\n` and invalid
parameters `0\n`, observed persistent values are `1,3,5,7,17,27`, and tick counts
are `1,2,3,4,5,6`. Status `1` means accepted, `0` means load/symbol/parameter
failure, and `-1` means incompatible code ABI/schema. A failed initial module
exits `1` without ticking; bad argument count exits `2`.

`src/reload/abi.inc` owns this experiment's layout. The exported data symbol
`rh_module_table` contains three 64-bit fields: ABI version `1`, schema fingerprint
`0x5248535441544531`, and a signed offset from the table to the update function.
The table therefore needs no dynamic relocation or writable executable memory.
The update function receives the host-owned state pointer in RDI, returns void,
and preserves SysV nonvolatile registers. State fields are 64-bit tick count,
accumulated value, and parameter step. Compatible v1 adds one step; v2 adds two.
The persistent state contains no module pointers. The host owns its current loader
handle and update pointer separately.

Each update call finishes before reload begins. The host opens the candidate
with `RTLD_NOW | RTLD_LOCAL`, resolves and validates the table, publishes the
new handle/function, and then closes the old handle. Load, symbol, or compatibility
failures close the candidate when present and keep the old implementation usable.
These are trusted local modules: `dlopen` can execute constructors before schema
validation. The proof does not sandbox malformed or hostile DSOs.

Parameters are strict decimal integers `1..100`, optionally followed by one LF.
Leading zeroes are allowed. Validation rejects empty input, signs, spaces, embedded
NUL, trailing data, extra newlines, out-of-range values, and files of 32 bytes or
more. The host reads into separate bounded scratch storage and publishes a single
aligned 64-bit step only after complete validation. Invalid data leaves the prior
step and ongoing state intact.

Verification on 2026-10-05: Linux `7.2.6-201.nobara.fc44.x86_64`, x86-64,
NASM `2.16.03`, GCC linker driver `16.2.1`. The command using
`/tmp/red-horizon-tools/nasm-2.16.03/nasm` passed 19 black-box cases in
`0.055672` seconds including assembly/link and all subprocess tests. Cases cover
compatible swap and continuous state, incompatible/missing/symbol-less modules,
11 malformed parameter forms, three accepted parameter forms, failed initial
load, and usage failure. `readelf -d v2.so` showed no dynamic relocations.
This wall-clock result is a local observation, not a stable performance guarantee
or a measurement of isolated reload latency.

Remaining integration work: connect reload to the real game host and generated
shared schema; validate parameters off-thread; quiesce worker/audio callbacks at
a barrier; handle compatible network content versions; Windows loaded-file naming;
schema migration or snapshot restart; loader error messages and isolated reload
latency metrics. The proof is single-threaded and synchronous, has no simulation
workers/audio callbacks, and does not establish Windows or live co-op safety.
