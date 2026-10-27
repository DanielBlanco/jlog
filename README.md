# jlog

📄 **Inspect JSONL files, find malformed records, and understand what you have.**

`jlog` is a small command-line explorer written in [Roc](https://www.roc-lang.org/).
Give it a file or pipe in a stream to get record totals and useful validation
errors. It reads incrementally and leaves your input unchanged.

> 🚧 **Current status:** inspection, validation, count, tail, help, and version work
> with file/stdin input. Filtering still returns an unfinished-operation message
> and exit 1. Known platform descriptor edge cases remain under review; field
> extraction is deferred to v0.2.

## Table of contents

- [Quick start](#quick-start)
- [Using jlog](#using-jlog)
  - [Inspect a file](#inspect-a-file)
  - [Read from stdin](#read-from-stdin)
  - [Show inspection progress](#show-inspection-progress)
  - [Find malformed records](#find-malformed-records)
  - [Count valid records](#count-valid-records)
  - [Show the last valid records](#show-the-last-valid-records)
  - [Use exit codes in scripts](#use-exit-codes-in-scripts)
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

The examples use the locally built `./dist/jlog`. After installing it on your
`PATH`, use `jlog` instead.

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
count and tail keep their data-mode output contracts without progress. Filtering
remains unfinished. Without the flag, stderr is quiet on successful inspection.

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

### Use exit codes in scripts

| Code | Meaning |
| --- | --- |
| `0` | Operation completed with valid input, including empty input. |
| `1` | Internal/resource failure, or currently unfinished filtering. |
| `2` | Invalid arguments. |
| `3` | Input open/read error or reported output write error. |
| `4` | Operation completed with malformed JSONL records. |

Capture the status immediately; invalid input still produces a useful report:

```sh
status=0
./dist/jlog events.jsonl > report.txt || status=$?
case "$status" in
  0) echo 'All records are valid.' ;;
  4) echo 'Malformed records found; see report.txt.' ;;
  *) echo "jlog failed with exit $status" >&2 ;;
esac
```

For pipelines, enable `set -o pipefail` in shells that support it so producer
failures are visible too.

## JSONL rules

- Each physical line must contain exactly one JSON value. Objects, arrays,
  strings, numbers, booleans, and `null` are all accepted.
- Use UTF-8 without a BOM. Blank/whitespace-only lines, comments, trailing commas,
  and values spread across multiple physical lines are invalid.
- LF and CRLF work. A final newline is optional; a lone CR is not a separator.
- Objects/arrays may nest up to 128 levels. Brackets inside strings do not count.
- Valid huge integers and exponents such as `1e9999` are checked without
  conversion to floating point. Unicode surrogate escapes must form valid pairs.

**Known platform edge case:** the pinned platform exposes a write-only stdin
descriptor as EOF, so that unusual setup currently reports empty input with exit
0. Actual propagated read errors are handled separately. See the
[handoff](docs/plans/jlog-handoff.md#known-limitations-and-risks) for this gap and the
remaining native Linux/resource verification work.

The pinned platform can also suppress EBADF errors when stdout/stderr uses an
unusable descriptor. Real closed-pipe write failures return 3 in the executable
tests, but strict detection of every descriptor failure remains unresolved.
See the [progress record](docs/plans/jlog-v0.1-progress.md#m2-implementation--authorized-2026-10-26)
for the compatibility gate; the specified I/O contract has not been relaxed.

## Build and install

### Prerequisites

- **Roc `nightly-2026-10-09-258ab27`** from the
  [pinned nightly release](https://github.com/roc-lang/nightlies/releases/tag/nightly-2026-10-09-258ab27).
  Unpack the matching compiler archive and put its directory on your `PATH`.
- **basic-cli 0.25.0** is already pinned by URL in `src/main.roc`; the compiler resolves
  it during the build. Initial dependency downloads need network access.
- **Python 3** is needed for executable tests only. No third-party Python packages
  or Node/npm setup are required.

Native builds/tests have been verified on **macOS ARM64**. **Linux x86-64** is an
initial release target whose native application verification is still pending.
Use the exact compiler pin: Roc syntax and APIs are evolving.

### Build an optimized executable

```sh
git clone https://github.com/DanielBlanco/jlog.git
cd jlog

roc version
# Expected: Roc compiler version nightly-2026-10-09-258ab27

mkdir -p dist
roc build --opt=speed --output=dist/jlog src/main.roc
./dist/jlog --version
```

Use `dist/jlog` directly; running the compiled tool does not require Roc.
To install for your user account:

```sh
mkdir -p "$HOME/.local/bin"
install -m 755 dist/jlog "$HOME/.local/bin/jlog"
export PATH="$HOME/.local/bin:$PATH"
jlog --version
```

The `export` applies to the current shell; add it to your shell configuration if
needed. Build outputs are ignored by Git.

If the compiler cannot write its default cache, choose a writable location before
building, for example `export ROC_CACHE_DIR="$PWD/.cache/roc"`. A fresh cache must
download the pinned dependencies; do not rely on the temporary research cache
paths recorded in earlier development sessions.

## For developers

Start with [AGENTS.md](AGENTS.md) and the [development handoff](docs/plans/jlog-handoff.md).
M1-A and M1-B are implemented. Work on one agreed TDD task at a time, preserving
existing behavior and tests.

### Code map

| Path | Responsibility |
| --- | --- |
| `src/main.roc` | File/stdin effects, shared input loop, output, and exit mapping. |
| `src/Cli.roc` | Pure argument parsing and help text. |
| `src/help.txt` | Editable help text, embedded into the executable at compile time. |
| `src/Jsonl.roc` | Pure framing, UTF-8/BOM classification, depth precheck, and builtin JSON validation adapter. |
| `src/Operations.roc` | Pure inspection summaries, capped details, and report rendering. |
| `tests/test_cli.py` | Python stdlib tests against the actual executable. |
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
roc run src/main.roc -- --help
roc check src/main.roc
roc fmt --check src/main.roc src/Cli.roc src/Jsonl.roc src/Operations.roc
```

To apply formatting, run `roc fmt` with those same explicit source paths.

### Test development and optimized builds

Roc's top-level `expect` checks cover pure behavior. The Python harness checks
actual stdout/stderr bytes and exit codes. Build before invoking the harness;
`JLOG_BIN` selects the executable and the harness never builds it for you.

```sh
mkdir -p dist

# Development mode
roc test --opt=dev --no-cache src/main.roc
roc build --opt=dev --output=dist/jlog src/main.roc
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v

# Optimized mode: repeat executable tests against this new build
roc test --opt=speed --no-cache src/main.roc
roc build --opt=speed --output=dist/jlog src/main.roc
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v
```

Run permission tests as an ordinary user; the harness deliberately rejects a
root-only run. A focused pure check can use
`roc test --main=src/main.roc src/Jsonl.roc`; this compiler may also run checks reachable
through the application context. Focus executable tests with `-k m1_16` before
`-v` in the discovery command above.

### Keep the TDD loop honest

1. **RED:** write and execute a small behavior test; confirm its assertion fails
   for the missing behavior. Test syntax errors are not RED.
2. **GREEN:** implement the minimum change, then run focused and regression tests.
3. **REFACTOR:** simplify without changing behavior; rerun tests and checks.
4. **VERIFY:** record the task ID, failing assertion/command, passing results,
   compiler/format status, and limitations in the [progress log](docs/plans/jlog-v0.1-progress.md).

Already-passing coverage needs no artificial RED or production rewrite. Keep I/O
at the boundary, reuse the verified JSON adapter, and investigate compiler/API
failures instead of weakening tests. PRs should explain the behavior change and
include the commands and results used to verify it.

## Roadmap

| Milestone | Status |
| --- | --- |
| M1: CLI, framing, file/stdin inspection and validation | ✅ Implemented. |
| M2: `--count`, `--tail N`, and expanded error handling | Count/tail and tested failure paths implemented; handling some invalid standard descriptors remains unresolved. |
| M3: `--where KEY=TEXT`, string-only top-level equality | Planned; flag currently parses only. |
| M4: resource measurements, native targets, CI, docs, licensing, and release packaging | Pending. |
| v0.2: `--field KEY` | Deferred; currently rejected with exit 2. |

The [implementation plan](docs/plans/jlog-v0.1-plan.md) contains the ordered tasks.
There is no TUI, query language, nested-field query syntax, follow mode, or file
modification in v0.1 scope.

## Further reading

- [JSONL introduction](docs/jsonl.md) — format, examples, and reference links.
- [v0.1 specification](docs/specs/jlog-v0.1.md) — commands, edge cases, and output contracts.
- [Roc feasibility](docs/roc-feasibility.md) — verified APIs, probes, and compatibility risks.
- [Development handoff](docs/plans/jlog-handoff.md) — checkpoint history and resume instructions.
