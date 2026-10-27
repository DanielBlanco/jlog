# M4-03 native CI execution

On 2026-10-27 the user authorized native CI alongside M4-02 Linux x86-64
measurements. [Run 40549245469](https://github.com/DanielBlanco/jlog/actions/runs/40549245469)
executed both required architectures at commit
`48c9aa9ab1e4ea05f950288a247bd27fce0a7c7f` on `ci/native-m4`. Both resource
matrices pass; both jobs correctly finish **failed** because the existing strict
descriptor contract remains unsatisfied. Native automation is implemented and
executed; full M4-01/M4-03 conformance remains open.

## Native environments

| Job | Linux x86-64 | macOS ARM64 |
| --- | --- | --- |
| Runner label | `ubuntu-24.04` | `macos-15` |
| Asserted native architecture | `x86_64` | `arm64` |
| OS observed | Ubuntu 24.04.5, Linux 6.17.0-1022-azure | macOS 15.7.9, Darwin 24.6.0 |
| Image version | `20261023.334.3` | `20260907.0337.1` |
| Reported CPU | AMD EPYC 7763, 4 logical CPUs | Apple M1 (Virtual), 3 logical CPUs |
| Reported RAM | 16,766,414,848 bytes | 7,516,192,768 bytes |
| Ordinary user | UID 1001 | UID 501 |
| Explicit build target | `x64musl` | `arm64mac` |

The runner assertions, exact compiler archive checksums and version checks pass
on both hosts. Application source hashes agree across both jobs and the local
checkout. Both use Roc `nightly-2026-10-09-258ab27` and basic-cli 0.25.0. There is
no emulated execution, cross-target substitution, setup action or pin upgrade.
The tested OS versions are observations, not established minimum support levels.

## Executed checks

Every row below executes independently on both native jobs:

| Check | Result on each architecture |
| --- | --- |
| `roc check` and explicit-source `roc fmt --check` | Pass. |
| Measurement timing-unit suite | Three pass. |
| Dev pure checks and native build | 273 pass; build passes. |
| Dev ordinary executable suite | 63 methods pass, no skips. |
| Dev strict descriptor suite | Three methods/15 subcases fail, status 1. |
| Speed pure checks and native build | 273 pass; build passes. |
| Speed ordinary executable suite | 63 methods pass, no skips. |
| Speed strict descriptor suite | Three methods/15 subcases fail, status 1. |
| Optimized M4-02 resource matrix | All 70 cases pass; input/binary hashes unchanged. |
| Evidence upload | Pass. |

The failures are the previously recorded write-only stdin and read-only
stdout/stderr cases. No other command fails. The workflow has no skipped or
expected-failure treatment for these tests, and no `continue-on-error` override.
A separately conditioned measurement step runs after the failed verification
step only when the optimized pure/ordinary/driver checks succeed. Both jobs keep
their failure conclusion.

The [Linux x86-64 report](../measurements/m4-02-linux-x86_64-ci.md) and
[JSON](../measurements/m4-02-linux-x86_64-ci.json) provide the missing native
resource evidence. The [macOS CI JSON](../measurements/m4-02-macos-arm64-ci.json)
preserves a second native 70-case matrix. Its optimized binary SHA-256 equals
the earlier local macOS baseline exactly:
`0bf01d6835fa99f8dec215c922be8bd8f68601653dae1a0a326a01cb24c6ed77`.
All seven fixture hashes agree with the earlier macOS/Linux ARM64 fixtures.

## Automation and artifacts

See [the workflow](../../.github/workflows/native-ci.yml) and
[driver instructions](../../tests/ci/README.md). Checkout/upload actions are
pinned by full commit SHA. A small installer verifies fixed compiler archive
hashes directly instead of depending on a setup action. Each job starts with a
fresh compiler/package cache, checks as an ordinary user, and records all command
statuses, source/binary hashes and runner provenance.

Artifacts `native-linux-x86_64` and `native-macos-arm64` retain both tested
executables, command logs, provenance, normalized measurements and raw time/stderr
files until 2026-11-10. The downloaded ZIP digests match GitHub's artifact
metadata. Compact JSON results and verification statuses are retained in this
checkout; raw downloads and job logs are under `/private/tmp/jlog-m403-artifacts`.
Generated JSONL fixtures, large stdout and compiler/cache data are excluded.

The workflow was committed and pushed on a separate CI branch. Both local and
remote `master` remain unchanged; existing pending measurement/documentation
work is preserved. No PR, release, archive installation or license decision is
part of this execution. The descriptor gate and later M4-04/05/06 release work
remain open.
