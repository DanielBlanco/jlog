# jlog 0.1.0 release audit

The user's wrap-up request authorizes finishing M4-05/06 release preparation.
**M4-06 is complete.** Application behavior and final native archive verification
pass on both release targets; the exact release set is finalized and checksummed.
This audit does not merge the existing PR, create a tag or publish a release.

## Scope and implementation

v0.1 provides inspection/validation, count, bounded tail, top-level string-only
filtering, file/stdin input and opt-in inspection progress. `--field`, nested
queries, follow mode, a TUI and input modification remain outside this release.
No application code, Roc compiler pin or platform patch changes during closeout.

Roc remains `nightly-2026-10-09-258ab27`; the approved corrected basic-cli 0.25.0
host is built with Rust 1.99.0. Source, archive, patch, Cargo.lock and generated
platform hashes are checked by the bootstrap, native verifier and packager.
Finalization rechecks those identities against the current reviewed inputs.

## License and notice review

| Component | Reviewed evidence and preserved terms |
| --- | --- |
| Project code | The user approved MIT with the proposed `Copyright (c) 2026 Daniel Blanco`; root `LICENSE` contains that text. Repository commit authorship is attributed to Daniel Blanco. |
| basic-cli 0.25.0 | Original UPL copyright/permission notice is preserved. Upstream commit `6e787d231017e9888027330de5d651f388e807fd`, archives, patch and source hashes are locked. The notice index describes the local descriptor-access modification and its source path. |
| Roc | The compiler archive's UPL and `legal_details` are copied verbatim; the official archive checksum and copied bytes were independently verified. The compiler itself is not shipped. |
| Rust standard library | The complete Rust 1.99.0 `COPYRIGHT-library.html` is preserved, including its dependency notices. Rust is not a runtime installation requirement. |
| Host dependency crates | The union of native Cargo graphs contains 87 pinned crates. All crate checksums match Cargo.lock; all 165 original license/notice files match their recorded hashes and appear verbatim in the combined document. |
| Static Linux support | The published platform's third-party document preserves musl's MIT terms and LLVM libunwind's Apache-2.0 with LLVM Exceptions text. |

The dependency collection retains original terms, including BSD, Unicode and
CDLA notices; the project's MIT choice does not relicense dependencies. It
conservatively includes build-only dependencies and code the linker may discard.
The six full documents and inventory are protected by hashes. No license text
is trimmed or reformatted to satisfy whitespace checks.

## Supported environments

[`release/SUPPORT.md`](../../release/SUPPORT.md) records the release baselines:
macOS 15.7.9 ARM64, also tested on macOS 27.0.1 ARM64, and Ubuntu 24.04.5 x86-64
on the recorded native CI kernel. Support is limited to tested configurations;
earlier macOS and other Linux distributions/kernel combinations are unverified.
The Mach-O deployment target and static musl linking do not establish broader
minimum-version compatibility. Debian 12 Linux ARM64 Docker evidence remains
supplemental and does not add a release archive.

## Acceptance and resource evidence

| Gate | Evidence |
| --- | --- |
| CLI, JSONL validation, operation/error transitions and exact byte contracts | [M4-01 traceability audit](m4-01-audit.md), the corrected native sequence and the final native CI run. |
| Former standard-descriptor failures | Both dev/speed strict suites retain every exit-3 assertion, with no skips or expected failures. |
| Actual mid-stream read errors and pipelines | The nonblocking-pipe regression exercises all operations; filtering keeps only its complete emitted prefix and deferred modes emit no completed result. |
| Bounded resource behavior | [M4-02 native measurements](../measurements/m4-02-macos-arm64.md), corrected-host matrices and 70 final resource cases per native target. Shared-runner timings are observations, not a throughput promise. |
| Clean source build and documented installation | [M4-04 report](m4-04-docs-verification.md); native CI repeats all five actual documented source blocks and usage/install cases. |
| Archives without compiler/runtime downloads | [M4-05 archive report](m4-05-archive-verification.md); eight native runtime cases under network-denying isolation, read-only fixtures and verified input/binary/archive hashes. |

The finalizer requires the entire native test sequence, successful README/source
blocks, all 70 resource cases and all eight archive smoke cases for each target.
It checks that the report, archive contents and optimized executable have the
same identity. Missing or duplicated targets, failed smoke results and mixed
source/version/platform/license/notice/support inputs are rejected.

New finalizer tests initially fail because the tool is absent, then pass with
the implementation. All 80 Python methods pass locally, as do check/format and
486 inline checks in each optimization mode. This is new release-tooling
coverage, not a fabricated application bug or an application optimization.

## Final artifacts and publication boundary

The final release set preserves the exact native-tested archives, their
checksum sidecars, a combined `SHA256SUMS` and `manifest.json`. The manifest
records version, source/platform/binary/document identities, native run URLs,
archive hashes, support policy and verification totals. It explicitly records
an unpublished verified release candidate. No second untested build is made.

Code commit `7f92f8c` passes both
[PR run 40608149721](https://github.com/DanielBlanco/jlog/actions/runs/40608149721)
and [push run 40608143058](https://github.com/DanielBlanco/jlog/actions/runs/40608143058).
The selected artifacts use merge checkout `26081f3`; their application source
hashes match the current tree. Each target passes 486 pure checks per mode,
64 ordinary methods and all 15 strict descriptor subcases per mode, all 13 tooling
methods, five documented source blocks, 70 resource cases and eight offline
archive cases. Full documented discovery runs 80 Python methods per build.

The [native evidence](../verification/m4-05-native-archives.json) preserves
artifact ZIP digests, native statuses, original README commands/output hashes,
offline cases, exact archive members and all resource observations. The
[license audit JSON](../verification/m4-06-license-audit.json) records the
verified inventory and document hashes. Original notice files remain unchanged.

[`scripts/finalize_release.py`](../../scripts/finalize_release.py) successfully
rechecks the two downloaded real artifacts and creates ignored
`dist/jlog-0.1.0-release/`. A failed smoke report, changed archive hash or missing
smoke case is rejected when tested against a copy of the real macOS artifact.
Combined checksums pass for both archives and the manifest. The durable
[manifest](../verification/jlog-0.1.0-release-manifest.json) and
[checksum file](../verification/jlog-0.1.0-SHA256SUMS) exactly match that release set.

All v0.1 implementation and verification tasks are closed. Publication, tagging
and merging remain separate actions for the repository owner. This is an
unpublished verified release candidate.
