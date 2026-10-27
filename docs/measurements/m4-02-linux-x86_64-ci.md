# M4-02 native Linux x86-64 resource measurements

Recorded 2026-10-27 on a GitHub-hosted x86-64 VM. All **70 cases** pass exact
output/status/hash checks. This supplies the required native Linux x86-64
resource evidence alongside the [macOS baseline](m4-02-macos-arm64.md).
No application source or compiler/platform pin changed. Full conformance still
fails the known standard-descriptor cases.

The [JSON artifact](m4-02-linux-x86_64-ci.json) retains every measurement and
command, fixture size/max-line bytes, N, elapsed/user/system time, normalized
peak RSS, statuses, hashes, host/image identity and verification statuses.
The [native CI report](../plans/m4-03-native-ci.md) covers both architectures.

## Execution and integrity

| Item | Recorded value |
| --- | --- |
| Run | [40549245469, attempt 1](https://github.com/DanielBlanco/jlog/actions/runs/40549245469), branch `ci/native-m4`, commit `48c9aa9ab1e4ea05f950288a247bd27fce0a7c7f`. |
| Runner | `ubuntu-24.04`, image `20261023.334.3`, native `x86_64`. |
| OS | Ubuntu 24.04.5 LTS; Linux 6.17.0-1022-azure; tools use glibc 2.39. |
| Resources | AMD EPYC 7763 model reported by VM; 4 logical CPUs; 16,766,414,848 bytes reported RAM. |
| Limits | 4,096-byte pages; 16,777,216-byte stack soft limit; UID 1001. |
| Compiler | `nightly-2026-10-09-258ab27`; exact x86-64 asset verified before extraction. |
| Application | basic-cli 0.25.0; optimized `x64musl`, statically linked x86-64 ELF. |
| Timing | Native GNU `/usr/bin/time -v`; maximum-RSS KiB converted to bytes. |

Compiler archive SHA-256:
`dcb99abdf17d062246c05e394357ad682b883a6bcff7b2e581e20564ea88ffc4`.
Measured executable SHA-256:
`c7a3e08ad74a6d5b1508e1160fd1f3379566eb4795fbf261abb8457325915d78`.
The downloaded tested executable is retained locally as ignored
`dist/jlog-linux-x86_64`; no second release build was made.

Both dev and speed pass check/format, 273 pure checks and 63 ordinary executable
methods without skips. Three timing-unit checks pass. Raw invalid-UTF-8 filename
opening, unprivileged permission tests, broken pipes and actual mid-stream
WouldBlock execute on Linux. The strict descriptor suite separately fails three
methods/15 subcases per build with status 1; the workflow correctly remains red.

All seven fixture hashes match the macOS and Linux ARM64 definitions. The
measurement driver, application sources, downloaded binary and artifact ZIP
hashes were checked locally against their recorded identities. Inputs and the
binary remain unchanged across the full matrix. There is no emulation or
container layer in this job; runtime networking was not separately disabled.

## Results

The matrix covers 100,000/1,000,000 valid 1,024-byte records, all-invalid
equivalents, single 1 MiB/8 MiB bodies and a two-record maximum-N input. Every
fixture runs through file input and redirected stdin. Valid data includes
inspect/count/filter and tail N=0/1/64/4096/16384; invalid data includes the same
data modes with tail N=0/16384. Large lines use all modes and tail N=1.

Native elapsed seconds and peak RSS in MiB for valid file input:

| Mode | 100,000 time | 100,000 RSS | 1,000,000 time | 1,000,000 RSS |
| --- | ---: | ---: | ---: | ---: |
| Inspect | 1.04 | 0.39 | 10.36 | 0.39 |
| Count | 1.03 | 0.39 | 10.27 | 0.39 |
| Filter | 1.53 | 0.39 | 15.27 | 0.39 |
| Tail 0 | 1.02 | 0.39 | 10.30 | 0.39 |
| Tail 1 | 1.01 | 0.39 | 10.10 | 0.39 |
| Tail 64 | 1.98 | 0.52 | 19.84 | 0.52 |
| Tail 4096 | 1.06 | 5.14 | 10.39 | 5.14 |
| Tail 16384 | 1.09 | 19.52 | 10.47 | 19.39 |

At fixed N, retained memory stays bounded as input grows tenfold. Redirected
stdin tail N=4096 stays at 5.14 MiB, and N=16384 ranges from 19.27 to 19.52 MiB.
The larger filter emits exactly 512,000,000 bytes, checked by golden hash.
The maximum-U32-N tiny fixture emits exactly its two records at 0.39 MiB,
without allocating N slots in advance.

All-invalid cases stay at 0.39–0.52 MiB, retain exactly 100 diagnostic details,
report the correct omission count and return 4. Counts are zero; tail/filter
emit no records. Single large-line peak RSS across all four modes:

| Body size | File RSS | Stdin RSS |
| --- | ---: | ---: |
| 1 MiB | 2.46 MiB | 1.39 MiB |
| 8 MiB | 16.46–17.39 MiB | 8.57–9.85 MiB |

All long-line cases finish with exact output/status and no observed stack
failure under the recorded limit. The measurements show no retention/scaling
violation requiring an application optimization. Tail 64 takes longer than
larger N in both sizes; this observation is preserved without assigning an
unverified cause.

These are single sequential warm-cache observations on a shared VM. RSS excludes
the Python parent and filesystem cache, and gives a whole-run maximum rather
than a phase timestamp. Times are not throughput guarantees, minimum OS support
claims or controlled cross-platform performance comparisons.

## Reproduce and retained evidence

Use [native CI](../../tests/ci/README.md), or run its verification driver on an
actual Linux x86-64 host with `--target x64musl`, then:

```sh
python3 tests/measure_resources.py \
  --binary /tmp/jlog-native-evidence/jlog-speed \
  --environment /tmp/jlog-native-evidence/environment.json
```

GitHub artifact `native-linux-x86_64` (ID `12754293151`) contains tested binaries,
logs, JSON and raw time/stderr files, expiring 2026-11-10. Its ZIP SHA-256 is
`89972ee4b0b82772f35d15d611a7d132d4b4b4eab7857dbbb8611e7851e42271`.
Downloaded raw evidence remains under
`/private/tmp/jlog-m403-artifacts/native-linux-x86_64`; compact results are
preserved in the repository JSON beyond the upload retention period. Huge
fixtures/stdout and compiler caches are excluded. This is CI evidence, not a
release archive or offline-install verification.
