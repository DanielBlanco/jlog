# Contributing to jlog

Start with the [specification](docs/specs/jlog-v0.1.md),
[current progress](docs/plans/jlog-v0.1-progress.md), and
[repository guidance](AGENTS.md). v0.1 covers inspection, validation, count,
bounded tail, string-only top-level filtering, and inspection progress.
`--field` remains v0.2 work. Keep changes within the agreed task.

## Prepare a checkout

Follow the [README source-build instructions](README.md#build-and-install).
Use Roc `nightly-2026-10-09-258ab27` and Rust 1.99.0. Before Roc commands, run:

```sh
python3 scripts/build_platform.py
```

The [platform lock and reviewed host patch](platform/README.md) are part of the
build. Do not replace them with a moving release or edit a global package cache.
Generated `platform/basic-cli/`, compiler caches and build outputs stay out of
Git. Python tests need only the standard library and must run as an ordinary user
so permission fixtures are meaningful.

## Make and document a change

Keep I/O and exits in `src/main.roc`. Pure argument parsing belongs in `Cli.roc`,
framing/JSON validation in `Jsonl.roc`, and reductions/rendering in `Operations.roc`.
See the [code map](README.md#code-map) and [learning guides](docs/learning/main.roc.md).

For a behavior change, execute a small failing assertion, make the minimum fix,
then refactor and rerun the relevant regressions. Record the task ID, actual
failure, passing checks and remaining limits in the progress log. Already-passing
coverage and documentation verification need no fabricated application RED.
Keep the existing JSON grammar adapter, original-byte output, malformed-line
recovery, bounded diagnostics and incremental processing contracts.

Document every named Roc function with `##` comments and Python helpers/tests
with docstrings. Use `roc fmt` on explicit application paths. Help lives in
`src/help.txt`, is embedded at build time, and must retain its final newline.

## Verify before review

The [README](README.md#test-development-and-optimized-builds) lists individual
commands. The shared native driver runs check/format, both optimization suites,
native builds, ordinary/strict executable tests and tooling unit checks:

```sh
# macOS ARM64; native Linux x86-64 uses --target x64musl.
python3 tests/ci/verify.py --target arm64mac --output /tmp/jlog-review-evidence
```

The output directory must be new. Every command must pass, including the strict
descriptor suite; do not weaken assertions or skip failing cases. The full
inline count includes 273 project checks and 213 checks from the local platform.
Executable tests use `JLOG_BIN` and never build implicitly.

Verify README examples and a temporary user installation against the optimized
binary when changing usage/build documentation:

```sh
python3 tests/verify_readme.py --binary /tmp/jlog-review-evidence/jlog-speed
```

This reads the documented command blocks, runs them in an isolated directory,
and checks outputs/statuses, pipeline failures and the installed binary. The
optional `--source-checks` flag also executes the README's Roc build/check/test
blocks in this checkout, rebuilding ignored `dist/jlog`; it requires the prepared
toolchain. Native CI enables it. A source-build procedure is additionally verified
from a fresh checkout for M4-04. Resource
measurements and native CI details are linked from the README; rerun expensive
matrices when relevant code or platform changes warrant them.

## Submit a reviewable change

Use a concise imperative commit subject. A PR should explain the concrete problem
and resulting behavior, link the task, list actual validation results and call
out remaining limitations. Include screenshots only for visible interface changes.
Document any toolchain/platform change and its native verification explicitly.

Release archives, license/notices, minimum OS support and publication have their
own M4 tasks. Passing source tests is not a published release or archive smoke test.
