# Native CI

[The workflow](../../.github/workflows/native-ci.yml) runs on pushes, pull requests
and manual dispatches. Its two independent jobs use `ubuntu-24.04` for Linux
x86-64 and `macos-15` for macOS ARM64. Both assert the actual OS and architecture
before downloading a compiler; emulated or cross-built execution does not satisfy
this matrix. Runner labels follow the
[GitHub runner documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job).

`install-roc.sh` checks the native compiler archive's SHA-256 against the pinned
nightly release before extracting it, then checks `roc version`. No setup action
or moving nightly is used. Checkout and artifact-upload actions are pinned by full
commit SHA. CI installs Rust 1.99.0 and prepares the approved
[checksum-pinned basic-cli host correction](../../platform/README.md) with the
same bootstrap as local development. Linux uses its native musl C/Rust target.
There is no shared cross-run compiler/package cache.

The [first native execution](../../docs/plans/m4-03-native-ci.md) passes ordinary
tests and all 70 measurements per architecture. Those initial jobs retain their
failure status for the original strict descriptor cases; later correction
results are recorded separately in that report.
The [corrected native execution](../../docs/plans/m4-03-stdio-correction.md) is
green on both targets, including all strict descriptor assertions and resource cases.

`verify.py` runs as an ordinary user and records each command and status:

1. Platform integrity, compiler check, explicit-source formatting and driver/platform/release unit checks.
2. Dev pure checks, native build, executable acceptance and strict descriptor suite.
3. The same pure/build/executable/descriptor sequence with speed optimization.
4. Source/platform integrity and binary hashes, runner/image identity and source commit.

The following README step executes the actual usage/install blocks in a fresh
temporary workspace against the tested optimized binary. It also explicitly
runs the documented source-build/check/dev-progress/test blocks, including broad
Python discovery against both builds. On macOS it checks the exit-code and
pipeline snippets with zsh too. Installation uses a temporary prefix containing
spaces, then exercises the installed executable with neither Roc nor Rust on
`PATH`. `evidence/readme.json` retains every script, status and output hash.

Any failed command fails verification and the CI job. The strict descriptor suite
checks the published platform's former failures; it runs normally, without skips
or expected-failure annotations. The driver still checks the other optimization
after a conformance failure. If the optimized pure/build/ordinary/driver checks
pass, the separate measurement step runs despite that failure. The job remains
failed, and the strict results stay in its logs and `verification.json`.

Measurements use the full 70-case M4-02 matrix sequentially on each native runner.
Fixtures and temporary stdout live under `RUNNER_TEMP`, outside the checkout.
Each measurement checks exact output/status/diagnostics and final input/binary
hashes. The workflow uploads logs, provenance, both tested executables, the JSON
matrix, platform build log/manifest and raw timing/stderr files for 14 days.
It excludes generated JSONL files, large stdout and compiler/cache data. These are verification
artifacts, not a published release. Single shared-runner timings do not promise
throughput or establish a minimum supported OS version.

After successful native verification, README checks and measurements, CI packages
the tested optimized executable and runs the [archive smoke test](../../release/README.md).
It checks installation, help/version, raw records, read-only inputs and a real
filter→count pipeline. Linux uses a network-disabled `FROM scratch` Docker image
with no compiler or runtime; macOS uses a network-denying sandbox and a PATH
containing only the installed binary. Archives, per-archive checksums and
`evidence/release.json` accompany the existing artifacts. Packaging is gated by
the full verification result, including both strict descriptor suites; successful
independent measurements cannot authorize packaging after a conformance failure.

To run the verification driver locally with the existing pinned compiler:

```sh
# macOS ARM64; on native Linux x86-64 use --target x64musl.
export ROC_CACHE_DIR="/tmp/jlog-native-cache"
python3 scripts/build_platform.py
python3 tests/ci/verify.py --target arm64mac --output /tmp/jlog-native-evidence
```

The output directory must be new. Every command, including both strict
descriptor suites, must pass for a green job. Run measurements separately
against that optimized executable:

```sh
python3 tests/measure_resources.py \
  --binary /tmp/jlog-native-evidence/jlog-speed \
  --environment /tmp/jlog-native-evidence/environment.json
```
