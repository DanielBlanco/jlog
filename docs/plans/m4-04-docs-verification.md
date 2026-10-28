# M4-04 documentation, source-build and installation verification

Authorized 2026-10-27 after the native descriptor correction went green. This
task verifies documentation against the real CLI and adds contribution guidance;
it changes no application code, platform patch or compiler pin.

## Observed documentation failures

Two existing instructions failed when executed:

| Instruction | Actual result | Correction |
| --- | --- | --- |
| Default `git clone`, then the documented bootstrap | The remote default branch is `master` at `76ff743`; `scripts/build_platform.py` is absent and Python exits 2. | Select `ci/native-m4` explicitly until the work is merged. |
| Exit-code block in `/bin/zsh` | Exit 1: `read-only variable: status`. | Use the task-specific `jlog_status` variable. |

These are documentation failures, not application RED. The implementation and
all existing acceptance expectations remain unchanged.

## Delivered documentation and verification

The [README](../../README.md) separates source checkout, prerequisites, building
and installation. It documents an overridable user prefix, a malformed pipeline
whose status demonstrates `pipefail`, partial/truncated output, normal signal
termination and measured native OS versions. It distinguishes tested versions
from minimum support promises. Broad unittest discovery now runs ordinary,
strict descriptor and tooling suites against both build modes.

[CONTRIBUTING.md](../../CONTRIBUTING.md) covers setup, the pinned platform,
module ownership, function documentation, the TDD/verification record and review
expectations. AGENTS.md and the handoff point to the current workflow.

[The README verifier](../../tests/verify_readme.py) reads the actual fenced
commands. It checks exact reports/help/version, literal paths, stdin forms,
progress completions, malformed records, counts/tail/filter bytes, redirects and
documented numeric sample results. It checks both the malformed pipeline's exit
4 with `pipefail` and exit 0 without it. macOS additionally runs the exit-code
and pipeline snippets under zsh. Runtime installation uses a prefix containing
spaces, verifies mode 0755 and binary hashes, then invokes the executable from
outside the checkout with neither Roc nor Rust on PATH.

The default verifier uses only the supplied binary. Explicit `--source-checks`
also executes five documented blocks: optimized build, run/check/format,
development progress, development/speed regressions and focused descriptor
tests. This mode rebuilds ignored `dist/jlog`; it does not silently add a build
to executable-only testing. Native CI enables it and uploads `readme.json`.

## Clean local source verification

The [local JSON](../verification/m4-04-clean-macos-arm64.json) preserves the
commands, statuses, output hashes, original failures and installation evidence.
A fresh remote branch checkout at `f05f326` in
`/private/tmp/jlog-m404-clean-source` begins without generated platform/cache/dist
outputs. The working M4-04 documentation/verifier is overlaid; application and
platform build inputs stay unchanged.

On native macOS 27.0.1 ARM64, installed prerequisites satisfy the exact Roc pin
and Rust 1.99.0 (selected through the checked `stable` alias). The documented
bootstrap downloads and verifies both pinned archives and rebuilds the host;
the README's optimized build produces `jlog 0.1.0`. Cargo's registry and the
external HTTP package cache are reused. This verifies a clean project source
build with available prerequisites, not provisioning an empty OS or a hermetic
dependency cache.

All **19** usage/install cases and **five** source blocks pass. The full source
regression block passes 486 inline checks and 72 Python methods per build:
64 ordinary methods, three strict methods covering 15 descriptor subcases, and
five tooling checks. The 486 inline checks comprise 273 project and 213 local
platform checks. Development progress completes at 12,000 records. Installed,
source-binary and fixture hashes match. Raw source stdout/stderr and example
outputs remain under `/private/tmp/jlog-m404-clean-verification`.

## Native CI

Commit `9c76b4cc1b029f90b8306be859d70d24433dbd2f` adds the README checks to the
existing native workflow. The README/source verification step passes on both
Linux x86-64 and macOS ARM64 in
[PR run 40571638408](https://github.com/DanielBlanco/jlog/actions/runs/40571638408).

Both that PR run and
[push run 40571627911](https://github.com/DanielBlanco/jlog/actions/runs/40571627911)
finish **success** on both native targets. The PR artifacts identify merge
checkout `cb0e0f304e441a2b5e9f015ade095be4d915980c` with head `9c76b4c`.

| Native check | Linux x86-64 | macOS ARM64 |
| --- | --- | --- |
| README usage/install cases | 16 pass | 19 pass, including three zsh cases |
| Documented source blocks | All five pass | All five pass |
| Check/format and original dev/speed verification | Pass | Pass |
| Documented broad Python regression discovery | Pass against both builds | Pass against both builds |
| Strict descriptor gate | All 15 subcases per build pass | All 15 subcases per build pass |
| Existing resource matrix | 70/70 pass | 70/70 pass |
| Source/platform/input/binary integrity and uploads | Pass | Pass |

The [Linux CI JSON](../verification/m4-04-linux-x86_64-ci.json) and
[macOS CI JSON](../verification/m4-04-macos-arm64-ci.json) retain every README
script, status, output hash, installed binary identity, native verification
statuses and artifact metadata. Downloaded ZIP digests match GitHub metadata;
tested binaries and application sources are checked locally. The optimized
binary hashes match the preceding corrected-host CI artifacts exactly.

Raw downloads remain under `/private/tmp/jlog-m404-ci-artifacts`; GitHub uploads
expire 2026-11-10. Source command stdout/stderr for the clean local build remains
under the local workspace recorded above. The per-case scripts and hashes in
repository JSON survive the ephemeral CI workers and upload retention window.

**M4-04 is complete.** M4-05 archive/checksum/offline installation tests and
M4-06 licensing/notices/OS support/final manifest remain.

## Scope boundary

This verifies source and user-prefix installation. It does not create or publish
release archives, choose a project license, certify minimum OS versions, merge
the existing PR or claim an offline archive smoke test. Those remain M4-05/06
and separately authorized publication work.
