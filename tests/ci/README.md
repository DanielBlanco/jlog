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
commit SHA. The application retains its basic-cli 0.25.0 content-addressed URL.
There is no shared compiler/package cache in this initial workflow.

`verify.py` runs as an ordinary user and records each command and status:

1. Compiler check, explicit-source formatting and measurement-driver unit checks.
2. Dev pure checks, native build, executable acceptance and strict descriptor suite.
3. The same pure/build/executable/descriptor sequence with speed optimization.
4. Source integrity and binary hashes, runner/image identity and source commit.

Any failed command fails verification and the CI job. The strict descriptor suite
currently exposes known platform failures; it is run normally, without skips or
expected-failure annotations. The driver still checks the other optimization
after a conformance failure. If the optimized pure/build/ordinary/driver checks
pass, the separate measurement step runs despite that failure. The job remains
failed, and the strict results stay in its logs and `verification.json`.

Measurements use the full 70-case M4-02 matrix sequentially on each native runner.
Fixtures and temporary stdout live under `RUNNER_TEMP`, outside the checkout.
Each measurement checks exact output/status/diagnostics and final input/binary
hashes. The workflow uploads logs, provenance, both tested executables, the JSON
matrix and raw timing/stderr files for 14 days. It excludes generated JSONL files,
large stdout, compiler/cache data and release archives. These are verification
artifacts, not a published release. Single shared-runner timings do not promise
throughput or establish a minimum supported OS version.

To run the verification driver locally with the existing pinned compiler:

```sh
# macOS ARM64; on native Linux x86-64 use --target x64musl.
export ROC_CACHE_DIR="/tmp/jlog-native-cache"
python3 tests/ci/verify.py --target arm64mac --output /tmp/jlog-native-evidence
```

The output directory must be new. A status of 1 with only the two
`io-contract-*` commands failing is the known conformance gap, not a successful
release gate. Run measurements separately against that optimized executable when
the ordinary tests pass:

```sh
python3 tests/measure_resources.py \
  --binary /tmp/jlog-native-evidence/jlog-speed \
  --environment /tmp/jlog-native-evidence/environment.json
```
