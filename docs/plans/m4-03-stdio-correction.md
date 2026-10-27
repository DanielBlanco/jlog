# Native verification after the basic-cli descriptor correction

Recorded 2026-10-27. Both native CI jobs are **green**, including the strict
descriptor suites that blocked M4-01/M4-03. The user approved adopting the tested
basic-cli 0.25.0 host correction; Roc remains at `nightly-2026-10-09-258ab27`.
No acceptance assertion was relaxed or skipped.

## Implementation and provenance

Commit `cf08c48b221270e7501fe82523cb55b673e5b12a` integrates the
[reviewed patch](../../platform/patches/stdio-access.patch),
[lock file](../../platform/basic-cli.lock.json) and
[native bootstrap](../../scripts/build_platform.py). The only Roc source change
selects the prepared local platform. Framing, validation, reducers, output bytes
and exit mapping remain in the existing application code.

The bootstrap verifies upstream archives and original/patched host source hashes,
enforces Rust 1.99.0 and Cargo.lock, and rebuilds the native host. It keeps the
published Roc modules and Linux libc/unwind support. Generated files and caches
are ignored; a manifest identifies every prepared file. CI verifies that manifest
around both optimization suites. Upstream license and third-party notices
accompany the generated platform.

The correction checks descriptor access with `fcntl(F_GETFL)` before Rust's
standard streams can suppress `EBADF`. Empty writes remain no-ops. Buffering,
16-KiB stdin reads and existing errors are retained. See the
[investigation and rejected upgrade experiment](../repros/stdio-descriptor-errors.md).

## Actual native runs

- [Push run 40560321503](https://github.com/DanielBlanco/jlog/actions/runs/40560321503): success on both architectures at `cf08c48`.
- [PR run 40560329965](https://github.com/DanielBlanco/jlog/actions/runs/40560329965): success on both architectures. Artifacts below come from this run, whose tested merge checkout is `0fb8a1d86b78a3e315b1de9bdc4758a2f7d15157` with head `cf08c48`.

The PR already existed; this work did not create, merge or comment on it.

| Check | Linux x86-64 | macOS ARM64 |
| --- | --- | --- |
| Asserted native architecture | `x86_64` | `arm64` |
| OS | Ubuntu 24.04.5, Linux 6.17.0-1022-azure | macOS 15.7.9, Darwin 24.6.0 |
| Image version | `20261023.334.3` | `20260907.0337.1` |
| CPU reported by VM | AMD EPYC 9V45, 4 logical CPUs | Apple M1 (Virtual), 3 logical CPUs |
| Unprivileged UID | 1001 | 501 |
| Pinned compiler/platform preparation | Pass | Pass |
| Check / explicit-source formatting | Pass | Pass |
| Dev inline checks / ordinary CLI methods | 486 / 64 pass | 486 / 64 pass |
| Speed inline checks / ordinary CLI methods | 486 / 64 pass | 486 / 64 pass |
| Strict descriptor gate, each build | All three methods / 15 subcases pass | All three methods / 15 subcases pass |
| Timing / platform-integrity unit checks | 3 / 2 pass | 3 / 2 pass |
| Optimized resource matrix | 70/70 pass | 70/70 pass |
| Source/platform/input/binary integrity | Pass | Pass |
| Evidence upload | Pass | Pass |

The 486 inline checks comprise 273 project checks and 213 checks included by the
local platform import. The new ordinary method covers three silent-output
controls that already passed on the original platform. Permissions, broken
pipes, native filename bytes and actual prefix WouldBlock run without skips.
Every recorded verification command exits zero.

## Updated resource evidence

The [Linux x86-64 JSON](../measurements/m4-03-stdio-fixed-linux-x86_64.json) and
[macOS ARM64 JSON](../measurements/m4-03-stdio-fixed-macos-arm64.json) retain all
70 measurements, fixture/output hashes, commands/statuses, host identity, build
provenance and verification results. All seven fixture hashes match earlier
baselines. Downloaded ZIP digests match GitHub metadata; source/driver/tested
binary hashes are verified locally.

Selected valid-file observations after the correction, RSS in MiB:

| Target / operation | 100,000 RSS | 1,000,000 RSS | 1,000,000 elapsed seconds |
| --- | ---: | ---: | ---: |
| Linux count | 0.41 | 0.41 | 6.47 |
| Linux filter | 0.41 | 0.41 | 10.03 |
| Linux tail 4096 | 5.16 | 5.16 | 6.40 |
| Linux tail 16384 | 19.53 | 19.53 | 6.43 |
| macOS count | 1.70 | 1.70 | 10.14 |
| macOS filter | 1.77 | 1.80 | 16.55 |
| macOS tail 4096 | 20.02 | 20.03 | 11.47 |
| macOS tail 16384 | 44.91 | 50.47 | 10.19 |

All-invalid diagnostics remain capped and exact. Maximum-N tiny input emits its
two records; every 8-MiB-body case passes without observed stack failure. Linux
8-MiB-line RSS spans 16.42–17.54 MiB for files and 8.47–9.79 MiB for stdin;
macOS spans 30.42–30.63 MiB and 14.42–14.58 MiB. No measured retention/scaling
violation requires an application optimization.

These are sequential single observations on shared VMs. CPU, allocator/toolchain
and host conditions differ from earlier runs; timing differences are not
attributed to the patch or presented as throughput guarantees. RSS is a whole-run
maximum, not a timestamp identifying its processing/output phase.

Tested optimized executable SHA-256:

- Linux x86-64: `9b8271f8771b3686311504e172f96ef66bbc60a0b0dc57350efc969608a2ac14`.
- macOS ARM64: `c43bbc634256da04ef0123a1f1defd5df6580c54f72299760a5a7a51dfe240c1`.

GitHub artifacts expire 2026-11-10. Compact JSON remains in the repository;
downloaded logs/binaries/manifests are under `/private/tmp/jlog-patched-ci-artifacts`.
The Linux ELF is also retained as ignored `dist/jlog-linux-x86_64`. Local
`dist/jlog` uses the tested local corrected build; previous binaries are retained
with `jlog-unpatched-*` names. Packaging must reuse an identified tested artifact.

## Supplemental Docker verification

The updated image pins Rust 1.99.0 and base manifest
`2c3a22f0a5533ea2dd5a16627bc841228151faa2d4de2644ac9987e4a2f1f2fa`.
The built native ARM64 image ID is
`sha256:2f7fc918581cea8df3752c20d77fbef11a80b09a0d2f2c8172470e5404775f7d`.
UID 1000 executes both suites from `/work/source` while `/src` stays read-only.
Each build passes 486 inline, 64 ordinary and all 15 strict subcases; five tooling
checks pass. A 62-case small measurement smoke also passes with unchanged input/
binary hashes. This is supplemental ARM64 evidence; no new full ARM64 resource
baseline is claimed.

The [Docker JSON](../measurements/m4-03-stdio-fixed-linux-arm64-docker.json) records
the manifest, image/engine context, checks and smoke matrix. The container is
stopped after export, retaining raw artifacts.

## Remaining release work

The known M2 descriptor compatibility gap and M4-01/M4-03 native verification
blockers are closed by the executed unchanged assertions. M4-02 has refreshed
evidence for the corrected host. Remaining work is M4-04 clean documentation/
installation verification and contribution guidance, M4-05 release archives/
checksums/offline smoke tests, and M4-06 licensing/notices, OS support and final
manifest audit. No release or upstream platform publication was performed.
