# jlog

📄 **Inspect JSONL files, find malformed records, and understand what you have.**

`jlog` is a small command-line explorer written in [Roc](https://www.roc-lang.org/).
Give it a file or pipe in a stream to get record totals and useful validation
errors. It reads incrementally and leaves your input unchanged.

> 🚧 **Current status:** inspection, validation, count, tail, string filtering,
> help, and version work with file/stdin input. Release preparation is underway;
> field extraction is deferred to v0.2.

## Table of contents

- [Quick start](#quick-start)
- [Using jlog](#using-jlog)
  - [Inspect a file](#inspect-a-file)
  - [Read from stdin](#read-from-stdin)
  - [Show inspection progress](#show-inspection-progress)
  - [Find malformed records](#find-malformed-records)
  - [Count valid records](#count-valid-records)
  - [Show the last valid records](#show-the-last-valid-records)
  - [Filter by a string field](#filter-by-a-string-field)
  - [Use exit codes in scripts](#use-exit-codes-in-scripts)
  - [Preserve pipeline failures](#preserve-pipeline-failures)
- [JSONL rules](#jsonl-rules)
- [Build and install](#build-and-install)
- [For developers](#for-developers)
- [Roadmap](#roadmap)
- [Further reading](#further-reading)

## Quick start

[Build the binary](#build-and-install), then create a tiny log to try:

```sh
cat > events.jsonl <<'JSONL'
{"level":"info","message":"Started"}
{"level":"error","message":"Connection failed","retry":1}
JSONL

./dist/jlog events.jsonl
```

```text
File: events.jsonl
Records: 2
Valid: 2
Invalid: 0
```

New to the format? [What is JSONL?](docs/jsonl.md) explains the basics.

## Using jlog

Run these Bash or zsh examples from the repository root after building
`./dist/jlog`. After installing it on your `PATH`, use `jlog` instead.

### Inspect a file

```sh
./dist/jlog events.jsonl
./dist/jlog --help
./dist/jlog --version
```

A filename alone selects inspection. The report appears after the whole input
has been read. `Records` counts physical lines, including malformed and blank
lines; it always equals `Valid + Invalid`. An empty file reports three zeros.

Only one input is accepted. For filenames beginning with a dash, end option
parsing with `--`; for a file literally named `-`, use `./-`:

```sh
./dist/jlog -- -events.jsonl
./dist/jlog ./-
```

### Read from stdin

Omit the filename, or pass `-` explicitly:

```sh
cat events.jsonl | ./dist/jlog
./dist/jlog - < events.jsonl
printf '%s\n' '{"level":"info"}' 'null' | ./dist/jlog
```

The report labels the input `<stdin>`. In an interactive terminal, send EOF
(usually Ctrl-D on an empty line) when you are done.

Inspection stdout is a human-readable report. Redirect it to save a summary;
it is not a JSONL data stream:

```sh
./dist/jlog events.jsonl > report.txt
```

### Show inspection progress

Add `--progress` to see counts on stderr while the final report stays on stdout:

```sh
./dist/jlog --progress tests/sample.jsonl
cat events.jsonl | ./dist/jlog --progress
./dist/jlog --progress events.jsonl > report.txt
```

```text
jlog: 125000 lines inspected, 42 invalid
jlog: 250000 lines inspected, 65 invalid
jlog: 250018 lines inspected, 65 invalid (complete)
```

Counts include all inspected physical lines, including malformed ones. Updates
appear at most about once per second as input advances. A final count is always
printed at EOF, so short or empty inputs may show only the completion line.
For `tests/sample.jsonl`, that line is `jlog: 6 lines inspected, 0 invalid (complete)`.

For a larger example, `tests/sample-big.jsonl` contains 12,000 valid log records
in about 5.5 MiB, with varied statuses, services, Unicode, and nested data. An
optimized build may finish before the first periodic update. A development run
makes intermediate progress easier to see without a much larger fixture:

```sh
roc run --opt=dev src/main.roc -- --progress tests/sample-big.jsonl
```

Progress is plain newline-delimited text, suitable for a terminal or redirected
stderr. It has no colors or cursor controls. Updates can pause during blocked
reads or a very long individual record; there is no background heartbeat.
Open/read failures produce no completion line. The flag applies to inspection;
count, tail, and filtering keep their data-mode output contracts without progress.
Without the flag, stderr is quiet on successful inspection.

### Find malformed records

```sh
printf '{}\n\nnot-json\nnull' > mixed.jsonl
./dist/jlog mixed.jsonl
```

```text
File: mixed.jsonl
Records: 4
Valid: 2
Invalid: 2

Malformed records:
  line 2: blank line
  line 3: invalid JSON
```

This invocation exits **4**, and validation continues after each bad line.
The report lists the first 100 invalid lines, then an omitted-detail count if
needed. Inspection includes malformed-line details on stdout; input/output
errors go to stderr. A propagated input read error produces no completed report.

### Count valid records

```sh
./dist/jlog --count tests/sample.jsonl
cat events.jsonl | ./dist/jlog --count
```

The sample prints `6` followed by a newline. Count waits for EOF, counts only valid
records, and prints zero for empty input. Malformed input still produces its valid
count and exits 4; the first 100 invalid-line diagnostics and any omitted count
go to stderr. An open/read failure produces no count.

### Show the last valid records

```sh
./dist/jlog --tail 2 tests/sample.jsonl
./dist/jlog tests/sample.jsonl --tail=0002
cat events.jsonl | ./dist/jlog --tail 10 > recent.jsonl
```

Tail outputs the last N valid records in input order after EOF, preserving their
original bodies and adding LF terminators. It validates the entire input, including
malformed records outside the suffix. Invalid-line diagnostics go to stderr and
cause exit 4 even when valid records were emitted.

N accepts ASCII digits from 0 through 4294967295, with leading zeroes allowed.
Zero outputs no records but still validates. Storage grows only as records arrive;
a large N with a tiny input does not preallocate N slots. Tail memory depends on
the retained record bytes as well as the current line and capped diagnostics.

### Filter by a string field

```sh
./dist/jlog --where status=failed tests/sample-big.jsonl
./dist/jlog tests/sample-big.jsonl --where=status=failed > failed.jsonl
set -o pipefail
./dist/jlog --where status=failed tests/sample-big.jsonl | ./dist/jlog --count
```

The pipeline prints `706`. Filtering compares a literal top-level key with an
exact decoded JSON string. It is case-sensitive, with no type coercion or Unicode
normalization. Missing keys, non-string values, and non-object records are valid
nonmatches. For duplicate keys, the last decoded key wins.

Quote operands containing spaces or shell characters. The first `=` separates
key and text; later equals signs belong to the text. Empty keys and text work
(`=x`, `a=`). A key such as `request.status` is literal, not a nested query.

Matches stream to stdout as input arrives, preserving original bodies and adding
LF terminators. Every line is validated, even after a match. Malformed lines are
skipped; capped diagnostics go to stderr at EOF and the command exits 4. No
matches with valid input exits 0 with empty stdout. A later I/O failure exits 3
and may leave an already-emitted prefix. Filtering retains the current read and
line, temporary decoded fields, and capped diagnostics rather than all matches.

### Use exit codes in scripts

| Code | Meaning |
| --- | --- |
| `0` | Operation completed with valid input, including empty input. |
| `1` | Internal/resource failure. |
| `2` | Invalid arguments. |
| `3` | Input open/read error or reported output write error. |
| `4` | Operation completed with malformed JSONL records. |

Capture the status immediately; invalid input still produces a useful report:

```sh
jlog_status=0
./dist/jlog events.jsonl > report.txt || jlog_status=$?
case "$jlog_status" in
  0) echo 'All records are valid.' ;;
  4) echo 'Malformed records found; see report.txt.' ;;
  *) echo "jlog failed with exit $jlog_status" >&2 ;;
esac
```

### Preserve pipeline failures

In Bash or zsh, `pipefail` makes an upstream failure affect the whole pipeline:

```sh
set -o pipefail
./dist/jlog --where status=failed mixed.jsonl | ./dist/jlog --count
```

With `mixed.jsonl` above, this prints `0`, emits malformed-line diagnostics on
stderr, and exits **4**. Without `pipefail`, the downstream count succeeds and
the pipeline status is 0, hiding the filter's malformed-input status.

Filtering may leave an emitted prefix if a later input or output error occurs.
Count, tail and inspection defer their result until EOF; a read failure produces
no completed result. A failed write can leave partial output, including a
truncated JSONL record. Check the exit status before treating output as complete.
OS signals retain their normal termination behavior; a shell may report a signal
status outside the application's 0–4 exit-code table.

## JSONL rules

- Each physical line must contain exactly one JSON value. Objects, arrays,
  strings, numbers, booleans, and `null` are all accepted.
- Use UTF-8 without a BOM. Blank/whitespace-only lines, comments, trailing commas,
  and values spread across multiple physical lines are invalid.
- LF and CRLF work. A final newline is optional; a lone CR is not a separator.
- Objects/arrays may nest up to 128 levels. Brackets inside strings do not count.
- Valid huge integers and exponents such as `1e9999` are checked without
  conversion to floating point. Unicode surrogate escapes must form valid pairs.

## Build and install

Download [jlog v0.1.0](https://github.com/DanielBlanco/jlog/releases/tag/v0.1.0)
for macOS ARM64 or Linux x86-64. The release includes verified archives,
checksum sidecars and a manifest. Follow the bundled
[installation instructions](release/INSTALL.md); running the binary requires
neither Roc nor Rust. Source builds and the
[archive verification workflow](release/README.md) are documented below.
Project code uses the [MIT license](LICENSE); dependencies retain the terms in
the [third-party notices](release/THIRD_PARTY_NOTICES.md).

### Prerequisites for source builds

- **Roc `nightly-2026-10-09-258ab27`** from the
  [pinned nightly release](https://github.com/roc-lang/nightlies/releases/tag/nightly-2026-10-09-258ab27).
  Unpack the matching compiler archive and put its directory on your `PATH`.
- **Rust 1.99.0 with rustup**, a native C compiler, Python 3.9+, Git, curl and tar
  prepare the platform. Linux also needs musl-tools, zstd and the native musl Rust
  target. No third-party Python packages or Node/npm setup are required.
- **basic-cli 0.25.0 with the approved descriptor-access patch** is pinned in
  [the platform lock](platform/basic-cli.lock.json). The bootstrap verifies both
  upstream archives and the patch before rebuilding the native host. Initial
  downloads require network access. See [platform details](platform/README.md).

Native builds, pure/ordinary tests and resource measurements run on **macOS
ARM64** and **Linux x86-64** in CI, with supplemental **Linux ARM64 Docker**
results. The published platform hid some descriptor errors; this checkout uses
the corrected native host and retains the strict regression tests. See the
[native CI evidence](docs/plans/m4-03-native-ci.md).
Use the exact compiler pin: Roc syntax and APIs are evolving.

The verified native environments are macOS **15.7.9 and 27.0.1 ARM64**, and
Ubuntu **24.04.5 x86-64** with a statically linked musl executable. Debian 12
ARM64 Docker results are supplemental. v0.1 support is limited to these tested
configurations; earlier OS versions and other distributions are unverified.
See the [support policy](release/SUPPORT.md) for the release baselines and limits.

On macOS, the native C compiler comes from Xcode or its Command Line Tools;
`xcode-select -p` checks that a developer directory is selected. Install the
pinned Rust toolchain if it is not already available:

```sh
rustup toolchain install 1.99.0 --profile minimal
```

On Ubuntu/Debian **x86-64**, also prepare the native musl tools and Rust target:

```sh
sudo apt-get update
sudo apt-get install --yes musl-tools zstd
rustup target add --toolchain 1.99.0 x86_64-unknown-linux-musl
```

### Get the sources

Clone the `master` branch:

```sh
git clone --branch master https://github.com/DanielBlanco/jlog.git
cd jlog
```

### Build an optimized executable

```sh
roc version
# Expected: Roc compiler version nightly-2026-10-09-258ab27

python3 scripts/build_platform.py

mkdir -p dist
roc build --opt=speed --no-cache --output=dist/jlog src/main.roc
./dist/jlog --version
```

### Install the executable

Running the compiled tool requires neither Roc nor Rust. Install to your user
prefix, or set `JLOG_INSTALL_PREFIX` to a different directory first:

```sh
JLOG_INSTALL_PREFIX="${JLOG_INSTALL_PREFIX:-$HOME/.local}"
mkdir -p "$JLOG_INSTALL_PREFIX/bin"
install -m 755 dist/jlog "$JLOG_INSTALL_PREFIX/bin/jlog"
export PATH="$JLOG_INSTALL_PREFIX/bin:$PATH"
jlog --version
```

This prints `jlog 0.1.0`. The `export` applies to the current shell; add your
chosen bin directory to your shell configuration for later sessions. Build
outputs and generated platform files are ignored by Git.

If the compiler cannot write its default cache, choose a writable location before
building, for example `export ROC_CACHE_DIR="$PWD/.cache/roc"`. A fresh cache must
download the pinned dependencies; do not rely on the temporary research cache
paths recorded in earlier development sessions.

## For developers

Start with [AGENTS.md](AGENTS.md) and the [development handoff](docs/plans/jlog-handoff.md).
M1 through M4 implementation and release preparation are complete. Work on
one agreed TDD task at a time, preserving existing behavior and tests. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the contribution and verification workflow.

### Code map

| Path | Responsibility |
| --- | --- |
| `src/main.roc` | File/stdin effects, shared input loop, output, and exit mapping. |
| `src/Cli.roc` | Pure argument parsing and help text. |
| `src/help.txt` | Editable help text, embedded into the executable at compile time. |
| `src/Jsonl.roc` | Pure framing, UTF-8/BOM classification, depth precheck, builtin JSON validation, and string-field lookup. |
| `src/Operations.roc` | Shared summaries, bounded tail/filter buffers, diagnostics, progress, and exit policy. |
| `tests/test_cli.py` | Python stdlib tests against the actual executable. |
| `tests/test_io_contract.py` | Strict descriptor regressions, including errors hidden by the original platform. |
| `tests/verify_readme.py` | Executed README examples and temporary user-install verification. |
| `scripts/package_release.py`, `scripts/finalize_release.py`, `tests/verify_release.py`, `release/` | Tested-binary archives, release manifest/checksums, license inventory and native offline smoke tests. |
| `platform/`, `scripts/build_platform.py` | Checksums, host patch and bootstrap for the ignored local platform. |
| `tests/measure_resources.py` | macOS/Linux resource measurements, with normalized RSS units and environment provenance. |
| `tests/test_measure_resources.py`, `tests/docker/` | Timing-unit checks and a pinned unprivileged Linux Docker workflow. |
| `.github/workflows/native-ci.yml`, `tests/ci/` | Native Linux x86-64/macOS ARM64 CI, exact compiler installation and retained verification evidence. |
| `docs/specs/`, `docs/plans/`, `docs/` | Behavior contracts, TDD tasks/evidence, and research. |

Learning Roc through this project? Read the detailed source walkthroughs in
this order: [main.roc](docs/learning/main.roc.md),
[Cli.roc](docs/learning/Cli.roc.md), [Jsonl.roc](docs/learning/Jsonl.roc.md), and
[Operations.roc](docs/learning/Operations.roc.md). Each explains the syntax,
data flow, design choices, and related tests.

Roc application sources and their inline `expect` checks live in `src/`. Run
the commands below from the repository root. Document each named function with
a `##` comment describing its behavior and any relevant input or error contract;
use docstrings for Python test helpers and methods.

To edit `--help`, change `src/help.txt` and rebuild. Preserve its final newline;
the compiled executable includes the text and needs no separate help file at runtime.

### Run locally and check sources

```sh
python3 scripts/build_platform.py
roc run src/main.roc -- --help
roc check src/main.roc
roc fmt --check src/main.roc src/Cli.roc src/Jsonl.roc src/Operations.roc
```

To apply formatting, run `roc fmt` with those same explicit source paths.

### Test development and optimized builds

Roc's top-level `expect` checks cover pure behavior. The prepared local platform
adds 213 platform checks to the 273 project checks, giving 486 in the current
full run. The Python harness checks
actual stdout/stderr bytes and exit codes. Build before invoking the harness;
`JLOG_BIN` selects the executable and the harness never builds it for you.
Discovery below runs the ordinary CLI, strict descriptor, and tooling unit suites.

```sh
python3 scripts/build_platform.py
mkdir -p dist

# Development mode
roc test --opt=dev --no-cache src/main.roc
roc build --opt=dev --no-cache --output=dist/jlog src/main.roc
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -v

# Optimized mode: repeat executable tests against this new build
roc test --opt=speed --no-cache src/main.roc
roc build --opt=speed --no-cache --output=dist/jlog src/main.roc
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -v
```

Run permission tests as an ordinary user; the harness deliberately rejects a
root-only run. A focused pure check can use
`roc test --main=src/main.roc src/Jsonl.roc`; this compiler may also run checks reachable
through the application context. Focus executable tests with `-k m1_16` before
`-v` in the discovery command above.

The strict descriptor suite is included above. To run it on its own:

```sh
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_io_contract.py' -v
```

These three methods cover 15 subcases involving write-only stdin and read-only
stdout/stderr. They require exit 3 without skips or expected-failure markers.
The corrected host preserves these errors; ordinary tests also cover broken
pipes, directory reads, silent streams and actual mid-stream failures. Both
suites must pass for release. See the
[M4-01 audit](docs/plans/m4-01-audit.md) and
[reproducer](docs/repros/stdio-descriptor-errors.md).

### Native CI

The [native workflow](.github/workflows/native-ci.yml) checks both development and
optimized builds on Linux x86-64 and macOS ARM64, then collects resource
measurements. Compiler downloads are checksum-verified; actions are pinned by
commit. Strict descriptor failures fail the job while allowing independent
resource evidence to be collected. See [CI details](tests/ci/README.md) for the
command sequence and artifact contents. CI rebuilds the same pinned platform as
local development and verifies its hashes around both optimization suites.
The [execution report](docs/plans/m4-03-native-ci.md) retains native results,
including the original unpatched failure evidence.
The [corrected native run](https://github.com/DanielBlanco/jlog/actions/runs/40560329965)
is green on both architectures, with all descriptor assertions and resource
cases passing; see the [correction report](docs/plans/m4-03-stdio-correction.md).

CI also executes README usage/install examples and the documented source-command
blocks. M4-04's [verification report](docs/plans/m4-04-docs-verification.md)
records clean source builds, Bash/zsh status handling and user-prefix installs
on the native targets.

The [final native run](https://github.com/DanielBlanco/jlog/actions/runs/40608149721)
also passes all offline archive checks on both targets. The
[release audit](docs/plans/m4-06-release-audit.md) records final completion;
the [durable manifest](docs/verification/jlog-0.1.0-release-manifest.json)
identifies the pre-publication candidate artifacts. The
[v0.1.0 release](https://github.com/DanielBlanco/jlog/releases/tag/v0.1.0)
contains the published archives, manifest and checksums.

### Measure resources

Build the optimized binary first, then run the standard-library measurement driver:

```sh
python3 tests/measure_resources.py --binary dist/jlog
```

It generates temporary 100,000- and 1,000,000-record fixtures with 1,024 bytes per
record, all-invalid equivalents, 1 MiB/8 MiB lines, and a tiny input with maximum
tail N. It measures file and redirected-stdin runs sequentially with native
`/usr/bin/time`, checking exact output bytes/hashes, status, diagnostics, and
unchanged inputs. Peak RSS and CPU exclude the Python driver. Large stdout files
are removed after verification; raw timing/diagnostic files and `results.json`
remain in the printed temporary directory. Allow roughly 3 GiB of free disk space.

The runner uses macOS `time -l` or Linux GNU `time -v` and normalizes RSS to
bytes. For a container build and run, follow the
[Docker instructions](tests/docker/README.md). A small validation run can use:

```sh
python3 tests/measure_resources.py --binary dist/jlog --sizes 100 1000 --tail-sizes 0 1 8 --long-lines 1024 4096
```

`--cases 'valid-*-file-inspect'` selects named cases for focused repeats and
generates only the fixtures they need. `--work-dir` selects a new directory
outside the checkout. A failed output check
or timeout stops the matrix and preserves its artifacts; a timeout is an
inconclusive measurement, not a successful run. These are sequential warm-cache
observations on one host, not a throughput promise or a substitute for the strict
I/O gate.

The [macOS measurements](docs/measurements/m4-02-macos-arm64.md),
[native Linux x86-64 measurements](docs/measurements/m4-02-linux-x86_64-ci.md) and
supplemental [Linux ARM64 Docker measurements](docs/measurements/m4-02-linux-arm64-docker.md)
include the full fixture matrix and machine-readable results. A second native
macOS matrix is retained with the [CI evidence](docs/plans/m4-03-native-ci.md).

### Keep the TDD loop honest

Follow the behavior-test, minimal-fix, refactor and verification workflow in
[CONTRIBUTING.md](CONTRIBUTING.md). Already-passing coverage and documentation
checks need no artificial application RED. Record actual evidence and limitations
in the [progress log](docs/plans/jlog-v0.1-progress.md).

## Roadmap

| Milestone | Status |
| --- | --- |
| M1: CLI, framing, file/stdin inspection and validation | ✅ Implemented. |
| M2: `--count`, `--tail N`, and expanded error handling | Implemented; the approved host patch closes the known descriptor gap on both native targets. |
| M3: `--where KEY=TEXT`, string-only top-level equality | Implemented and tested on both native targets, including streaming and pipelines. |
| M4: resource measurements, native targets, CI, docs, licensing, and release packaging | Complete through M4-06: native regressions, offline archives and [final release audit](docs/plans/m4-06-release-audit.md) pass. MIT is applied; see [v0.1.0](https://github.com/DanielBlanco/jlog/releases/tag/v0.1.0). |
| v0.2: `--field KEY` | Deferred; currently rejected with exit 2. |

The [implementation plan](docs/plans/jlog-v0.1-plan.md) contains the ordered tasks.
There is no TUI, query language, nested-field query syntax, follow mode, or file
modification in v0.1 scope.

## Further reading

- [JSONL introduction](docs/jsonl.md) — format, examples, and reference links.
- [v0.1 specification](docs/specs/jlog-v0.1.md) — commands, edge cases, and output contracts.
- [Roc feasibility](docs/roc-feasibility.md) — verified APIs, probes, and compatibility risks.
- [Development handoff](docs/plans/jlog-handoff.md) — checkpoint history and resume instructions.
