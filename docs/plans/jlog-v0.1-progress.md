# jlog v0.1 progress

Layout note (2026-10-26): Roc sources now live in `src/`. Earlier entries and
commands retain their original paths as historical verification evidence. Use
the [README](../../README.md#for-developers) for current commands.

M1-A is complete; current authorization is M1-B only. M2 is not authorized.
Toolchain: Roc `nightly-2026-10-09-258ab27`,
existing basic-cli 0.25.0 content-addressed URL; native Darwin ARM64.

Commands below run at repository root. Prefix Roc build/check/test commands with
`env ROC_CACHE_DIR=/private/tmp/jlog-research/cache` in this sandbox; the default
cache caused `PermissionDenied`, while the preexisting writable research cache
successfully built the unchanged example. This is an environment workaround,
not a platform change. `main.roc` initially failed its formatting check; formatting
it during M1-01 resolved that inherited failure. No inherited application tests.

Command abbreviations (the owning source is substituted for MODULE):

- **P:** `roc test --main=main.roc --verbose MODULE`; regression: `roc test --verbose main.roc`.
- **I:** `roc build --opt=dev --output=dist/jlog main.roc`, then
  `JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v`;
  focus with `-k m1_01` (substitute task ID).
- **V:** rerun P/I after refactoring, `roc check main.roc`, and
  `roc fmt --check` with explicit existing project source paths.

## Completed cycles

| Task | Executed RED (status 1) | GREEN / regression / refactor verification |
| --- | --- | --- |
| M1-01 | I `-k m1_01`: version stdout was empty, expected `jlog 0.1.0\n`; subsequent alias assertion returned file error/status 1 instead of version/status 0. | Recognized standalone version/alias using text conversion (native OsStr representation differs from UTF-8 literals). I: 2/2 pass; P: 0 checks; V passes after formatting main. No data behavior added. |
| M1-02 | P Cli.roc: filename assertion failed (`Err(Usage)` vs inspected file), then absent input and `-` each failed before their changes (1 failing check per run). | Pure default/source selection; `./-` already passed as regression. P: 4/4; I: 2/2; V passes after formatting. |
| M1-03 | P Cli.roc: new count, spaced tail, spaced where, equals-tail, equals-where and `--` assertions each failed before the corresponding parser change (one failing assertion/run, no compiler errors). | Parse operation values only; first-`=` text preserved. P: 16/16; I: 2/2; V passes. Order/dash-leading/empty operands added as passing regression coverage. A nonexistent Try method and a syntax error were corrected during GREEN; neither counted as RED. |
| M1-04 | P Cli.roc: unknown option, extra input, repeated count, missing filter `=`, and signed tail `+1` each produced one failing assertion before its change (all status 1, zero compiler errors). | Added explicit usage rejection, one-input/one-operation tracking, and digit/range checks. P: 45/45; I: 2/2; V passes. Boundary/rejection variants passed as regressions. A temporary recursive-call arity mistake was corrected; not RED evidence. |
| M1-05 | P Cli.roc: invalid UTF-8 in spaced `--where` and then equals-form option each failed rejection assertions before their changes (45/46 and 46/47 passed respectively). | Strict `OsStr.to_str_try` for text; original OsStr retained for paths, including raw Unix bytes and UTF-16 units. Removed lossy display calls; used List.all for digit checks. P: 53/53; I: 2/2; V passes. Native executable path opening remains M1-B. |
| M1-06 | P Cli.roc: help, help alias, version selection each failed before their change. I `-k m1_06`: help produced file error/empty stdout, then extra help arguments returned 1 instead of 2. | Centralized pure help/parser and effectful dispatch; removed file-size example. P: 67/67; I: 7/7; V passes. Public functions moved into associated declarations after compiler diagnostics exposed private module functions; diagnostics/crashing error artifact were not RED and were replaced by a clean checked build. Data invocations explicitly fail as unfinished, pending M1-B+. |
| M1-07 | P Jsonl.roc: LF assertion emitted no line (67/68 passed); EOF assertion then retained `pending` instead of emitting the final line (68/69 passed). Both executed assertion failures, no compiler errors. | Pure callback-based feed/finish, physical numbering, unfinished byte state, idempotent EOF. P/root regressions: 76/76; I: 7/7; V passes. Test-only collector retains lines; production framer does not accumulate them. |
| M1-08 | P Jsonl.roc: split `{}\r` / `\n` retained CR in the emitted body (76/77 passed, status 1, zero compiler errors). | Strip one CR only before LF. Lone CR/EOF, split Unicode/raw bytes, every two-chunk cut plus bytewise chunks, and a 32,769-byte body pass. P: 85/85; I: 7/7; V passes. No UTF-8 record classification or JSON validation implemented. |

## M1-A checkpoint verification

Executed on the pinned native macOS ARM64 toolchain, all exit 0:

| Command (cache prefix as above) | Result |
| --- | --- |
| `roc test --main=main.roc --verbose Cli.roc` | 85 passed, 0 failed |
| `roc test --main=main.roc --verbose Jsonl.roc` | 85 passed, 0 failed |
| `roc test --verbose main.roc` | 85 passed, 0 failed |
| `roc check main.roc` | No errors |
| `roc fmt --check main.roc Cli.roc Jsonl.roc` | All formatting valid |
| `roc build --opt=dev --output=dist/jlog main.roc` followed by I harness | 0 compiler errors/warnings; 7 unittest methods passed, 0 failures/skips |
| `roc test --opt=speed --no-cache --verbose main.roc` | 85 passed, 0 failed |
| `roc build --opt=speed --output=dist/jlog main.roc` followed by I harness | 0 compiler errors/warnings; 7 unittest methods passed, 0 failures/skips |

There are 67 CLI and 18 framing `expect`s, not 255 distinct tests: the module
commands also include checks reachable through the `--main` application context.
Integration tests make 20 executable invocations per suite, including subtests;
they assert actual stdout/stderr/status and do not reproduce the parser/framer.
`dist/jlog` is the final optimized artifact. Existing specification, plan,
research documents, JSONL guide, contributor instructions, and tool pins were
preserved byte-for-byte.

## M1-A decisions and remaining limitations (checkpoint snapshot)

- `Cli` exposes pure parsing/help through associated declarations. Sources and
  operations are tagged unions in records; failures use `Try`/`Usage`. Native
  paths retain their `OsStr`; only option text is decoded strictly.
- `Jsonl` emits numbered raw-byte bodies through a pure consumer callback, with
  explicit EOF flushing and only unfinished bytes in framing state. It never
  decodes or validates a record. The collector/chunk-split helpers are test-only.
- Only `main.roc` performs effects, via basic-cli `Stdout`/`Stderr`; platform exit
  mapping uses `Exit(I32)`. No custom platform, JSON parser, FFI, or dependencies.
- No unresolved M1-A blocker. The default cache restriction requires a writable
  cache; the recorded temporary cache is machine-local and not a build dependency.
- Inspection/count/tail/filter currently return empty stdout, an explicit
  unfinished-operation diagnostic, and exit 1. This is a checkpoint placeholder,
  not a revision to their approved release contracts. No input file/stdin reads,
  record UTF-8/BOM/blank classification, depth/JSON validation, summaries, or data
  operations have been implemented. M1-B and later acceptance is not claimed.
- Framing integration with actual input I/O, native file opening, output fault
  injection, Linux execution, and memory/performance measurements remain assigned
  to their original later tasks. Pure raw Windows-unit cases do not establish
  Windows executable support.

M1-01 through M1-08 are complete. Stop at M1-A; M1-B requires another instruction.


## M1-B execution evidence

Baseline rerun: 85 pure checks and 7 executable unittest methods passed. M1-A
source/tests were snapshotted for preservation checks. P below is
`roc test --main=main.roc MODULE` (same checks without verbose output), with
`roc test main.roc` regressions. I remains the existing dev build + Python harness.
Every GREEN and REFACTOR reruns focused P, root P and I. V also runs
`roc check main.roc` and explicit-path formatting checks, including Operations.roc
once introduced. The writable cache prefix remains unchanged.

| Task | Executed RED (status 1, zero compiler errors unless noted) | GREEN / REFACTOR / VERIFY |
| --- | --- | --- |
| M1-09 | P Jsonl.roc: empty line classified Valid; after fixing that, JSON-whitespace-only line also classified Valid instead of Invalid(Blank). | Exact JSON whitespace bytes only; nonblank handling remains staged until JSON tasks. GREEN and formatted REFACTOR: P 88/88, I 7/7; V passes. |
| M1-10 | P Jsonl.roc: raw 255 classified Valid instead of InvalidUtf8; first-line UTF-8 BOM then classified Valid instead of Bom. | Strict Str.from_utf8; exact initial BOM only after UTF-8 succeeds. Includes overlong/truncated/surrogate/out-of-range bytes and precedence. GREEN/REFACTOR P 99/99, I 7/7; V passes. U+FEFF is not globally stripped; final outside-string grammar rejection is exercised in M1-13 after the JSON adapter exists. |
| M1-11 | P Jsonl.roc: 129 nested arrays classified Valid instead of TooDeep (99/100 passed). | Reused the report's bounded quote/escape-aware precheck; arrays/objects at 128/129, string delimiters/escapes, shallow malformed input and UTF-8/BOM precedence covered. GREEN/REFACTOR P 110/110, I 7/7; V passes. Grammar remains builtin's responsibility in M1-12/13. |
| M1-12 | P Jsonl.roc: valid_json("{}") failed against compiling False interface (110/111 passed). | Verified skip-only AnyJson.parser_for adapter; all kinds, nested heterogeneous/duplicate data, escapes, surrogate pairs, >U128, 1e9999, 2,000-digit integer accepted without numeric decoding. GREEN/REFACTOR P 128/128, I 7/7; V passes. M1-13 connects grammar failure to classification. |
| M1-13 | P Jsonl.roc: not-json classified Valid instead of InvalidJson (128/129 passed). | Propagated builtin JSON failure after blank/UTF-8/BOM/depth priorities; 35 grammar/Unicode/control/multiline regressions also pass, including outside-string U+FEFF and lone surrogates. GREEN/REFACTOR P 164/164, I 7/7; V passes. No custom JSON grammar rules. |
| M1-14 | P Operations.roc: valid line left totals unchanged; blank line then incremented valid instead of invalid; 101 blanks retained 101 details instead of 100. Each RED was an executed assertion. | Incremental inspection summary, accurate physical line references, first-100 details, totals continue after cap. GREEN/REFACTOR P 171/171, I 7/7; V passes. Command --count remains unimplemented. |
| M1-15 | P Operations.roc: empty report differed; mixed report lacked malformed section; 101 blanks lacked omitted count; control-bearing source leaked literal line breaks. Each asserted before its change. | Exact headers/details/reasons/decimal counts/LF and omitted count; pure C0/DEL/C1 source escaping, ordinary Unicode retained. GREEN/REFACTOR P 182/182, I 7/7; V passes. Raw malformed bodies never enter report state. |
| M1-16 | I `-k m1_16`: real one-record file returned empty stdout instead of its completed report (1 failure). | Buffered File.open_reader!/read_line!, common pure framing/classification/summary, EOF-only report, explicit input-error exit 3. GREEN/REFACTOR P 182/182, I 18/18; V passes. Exact valid/malformed/empty/CRLF/recovery/100-cap reports, native-byte paths, source escaping, unchanged input, real missing/permission/directory errors covered. Fixture creation for invalid UTF-8 filenames failed; /private/tmp probe confirmed EILSEQ. Harness now tests supported UTF-8 native bytes and explicit failure for unavailable Darwin names; actual raw invalid-name opening remains mandatory on a supporting Linux filesystem, with existing raw-byte pure coverage retained. No app requirement was changed. |
| M1-17 | I `-k m1_17`: empty implicit stdin returned unfinished-operation exit 1/empty stdout instead of zero-count inspection (1 failure). | Raw Stdin.bytes!, EOF flush; implicit/explicit - parity, CRLF, hostile bytes, caps and multi-read long/Unicode/final lines. Refactored file/stdin through one effect loop and a small EOF-normalizing transport adapter. GREEN/REFACTOR P 182/182, I 23/23; V passes. One mutable-assignment branch syntax error was corrected during GREEN, not counted as RED. |
| M1-18 | New executable preflight tests passed immediately: M1-A dispatch already validates before effects. Per the plan's inherited-coverage rule, no RED was fabricated and no production change was made for this row. | Held-open stdin cannot delay help/version/usage errors; invalid arguments beat inaccessible paths. Focused I: 2/2; full GREEN/REFACTOR P 182/182, I 26/26; V passes. M1-17 also gained a verified directory-stdin read-error regression. |

## M1-B platform investigations and limitations

- **Native filenames:** creating a raw `native-\xff.jsonl` filename in
  `/private/tmp` fails with `EILSEQ` on this Darwin filesystem (the repository
  sandbox also rejected it). Valid UTF-8 native-byte paths open correctly.
  The integration test retains successful raw invalid-name opening assertions
  for supporting filesystems; on this Darwin host it checks the observed fixture
  restriction and jlog's explicit inaccessible-input failure. It does not claim
  successful raw invalid-name opening here. Native Linux execution remains a gate.
- **Unusable stdin descriptor:** an exploratory test expected write-only stdin to
  produce a read error; it instead produced an empty report and status 0. An
  independent pinned Roc probe returned `Err(EndOfFile)` three times, while
  Python `os.read(0, 10)` on the same setup returned `EBADF`. This is not evidence
  of jlog receiving and ignoring a `StdinErr`. The original exploratory assertion
  is retained in `/private/tmp/jlog-m1-b/unsupported-ebadf-test.txt`.
  The integration fixture was corrected to a directory descriptor: the independent
  probe returned `StdinErr(IsADirectory)`, and jlog returned 3 with empty stdout.
  Its error-status/no-report assertions were preserved; no application code was
  changed to satisfy the replacement fixture.
- The platform's EOF result cannot be distinguished from actual empty stdin by
  the selected `Stdin.bytes!` API. Thus write-only stdin currently yields a zero
  report/status 0; it is a known compatibility gap for M2/release review, not a
  claim that every invalid descriptor is detected. Current Rust standard-library
  [stdio source](https://doc.rust-lang.org/src/std/io/stdio.rs.html#98-101)
  also maps `EBADF` reads to empty reads, consistent with the observation; the
  packaged host's Rust version/implementation was not established. No platform,
  FFI workaround, dependency, pin, specification, or plan change was introduced.
- Actual propagated file/stdin read errors suppress completed reports. Mid-stream
  fault injection remains best effort in its original M2 task. Counter/resource
  exhaustion coverage, data-mode operations, full-scale RSS/time measurements,
  Linux execution, and packaging remain in later milestones.

The descriptor observation is reproducible against the actual executable:

```python
import os, subprocess
read_fd, write_fd = os.pipe()
try:
    result = subprocess.run(["dist/jlog"], stdin=write_fd,
                            capture_output=True, timeout=3)
    print(result.returncode, result.stdout, result.stderr)
finally:
    os.close(read_fd)
    os.close(write_fd)
```

Observed: status 0, `File: <stdin>\nRecords: 0\nValid: 0\nInvalid: 0\n`, empty stderr.
This special case is explicitly uncorrected; the ordinary directory read-error
fixture passes with status 3 and empty stdout.

## M1-B final verification

All commands below executed with the recorded writable-cache environment:

| Command | Result |
| --- | --- |
| Focused `roc test --main=main.roc` on Jsonl.roc / Operations.roc after their GREEN and REFACTOR steps | Passed; final shared root reaches all 182 checks |
| `roc test --main=main.roc Cli.roc` | 182 passed, 0 failed |
| `roc test --opt=dev --no-cache main.roc` | 182 passed, 0 failed |
| Dev build + existing Python discovery command I | 26 methods passed, 0 failures/errors/skips |
| `roc test --opt=speed --no-cache main.roc` | 182 passed, 0 failed |
| `roc build --opt=speed --output=dist/jlog main.roc` + I | 0 compiler errors/warnings; 26 methods passed, 0 failures/errors/skips |
| `roc check main.roc` | No errors |
| `roc fmt --check main.roc Cli.roc Jsonl.roc Operations.roc` | All formatting valid |

The 182 pure checks comprise 67 CLI, 97 framing/classification/JSON, and 18
inspection-summary/rendering checks. All original 85 M1-A checks still pass.
An AST/content audit confirmed all seven original executable test bodies, all
original framing tests, and the entire Cli.roc module remain unchanged. The
specification, implementation plan, research documents, JSONL guide, AGENTS.md,
and tool pin were preserved byte-for-byte. No tests are skipped; the two
platform-specific verification limits above remain explicit.

`Jsonl` owns pure classification/depth/skip-adapter validation; `Operations`
owns pure bounded inspection summaries and reports. `main.roc` owns buffered
file/raw stdin effects, normalizes their EOF conventions, feeds the shared framer,
and emits a report only after successful EOF. Original record bytes are used for
classification without lossy decoding; numeric values are never converted.

## Executed inspection demonstrations

The final optimized executable was run from `/private/tmp/jlog-m1-b/demo` with
relative fixture names (absolute binary path). Every stderr was empty:

| Input / invocation | Exact stdout (LF shown as `\n`) | Status |
| --- | --- | --- |
| `jlog valid.jsonl`, bytes `{}\nnull\n1e9999\n` | `File: valid.jsonl\nRecords: 3\nValid: 3\nInvalid: 0\n` | 0 |
| `jlog mixed.jsonl`, bytes `{}\n\nnot-json\nnull` | `File: mixed.jsonl\nRecords: 4\nValid: 2\nInvalid: 2\n\nMalformed records:\n  line 2: blank line\n  line 3: invalid JSON\n` | 4 |
| `jlog empty.jsonl`, zero bytes | `File: empty.jsonl\nRecords: 0\nValid: 0\nInvalid: 0\n` | 0 |
| `cat valid.jsonl \| jlog` | `File: <stdin>\nRecords: 3\nValid: 3\nInvalid: 0\n` | Both processes 0 |

Scope smoke checks executed `--count`, `--tail 1`, and `--where status=failed`:
all still return the unfinished-operation diagnostic, empty stdout, status 1.
Only their existing CLI parsing is available; no M2/M3 processing was added.

Changed sources: Jsonl.roc, main.roc, tests/test_cli.py; added Operations.roc;
updated this progress record. Generated dist/jlog is the optimized tested binary.
M1-09 through M1-18 are complete with the disclosed platform limitation and
inherited M1-18 coverage. Stop after M1-B; do not advance to M2.

## Source layout and function documentation — 2026-10-26

Moved all four application modules into `src/`, added `##` documentation to all
26 named Roc functions and docstrings to all 30 Python helpers/test methods,
and updated README, repository guidance, and documentation paths. Existing
`docs/plans/` and `docs/specs/` moves were preserved. This is a behavior-preserving
maintenance change; no milestone behavior or new tests were added. A source
comparison excluding Roc comments/blank lines and a Python AST comparison
excluding docstrings confirmed executable code is unchanged.

Fresh native macOS ARM64 verification used the pinned compiler/platform and the
same writable `ROC_CACHE_DIR` recorded above. All commands exited 0:

| Command | Result |
| --- | --- |
| `roc check src/main.roc` | No errors. |
| `roc fmt --check src/main.roc src/Cli.roc src/Jsonl.roc src/Operations.roc` | All formatting valid after applying `roc fmt`. |
| `roc test --opt=dev --no-cache src/main.roc` | 182 passed. |
| `roc build --opt=dev --output=dist/jlog src/main.roc` | 0 errors/warnings. |
| `JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v` | Development binary: 26 passed, no skips. |
| `roc test --opt=speed --no-cache src/main.roc` | 182 passed. |
| `roc build --opt=speed --output=dist/jlog src/main.roc` | 0 errors/warnings. |
| `JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py'` | Optimized binary: 26 passed, no skips. |
| `roc test --main=src/main.roc src/Jsonl.roc` | 182 passed through the application context. |
| `roc run src/main.roc -- --help` | Help printed successfully. |

All local Markdown file links resolve. The earlier stdin-descriptor limitation
and pending Linux/resource/release verification remain unchanged. `dist/jlog`
contains the tested optimized build.

## Editable embedded help — 2026-10-26

Moved the existing help bytes into `src/help.txt` and imported them at compile
time with `import "help.txt" as usage_text : Str`. `Cli.help_text` remains a pure
constant, and help output is byte-for-byte unchanged. Updated repository guidance,
README, and the CLI learning guide. This is a refactor; no behavior RED or new
application tests were needed.

On the pinned toolchain with the same writable cache, `roc check src/main.roc`
and explicit-source `roc fmt --check` passed. Dev and speed pure test runs each
passed 182 checks; both builds completed without errors/warnings, and the Python
executable suite passed all 26 tests against each binary. An isolated build probe
confirmed that normal cached rebuilds pick up text edits and that a relocated
binary prints help after its temporary source tree, including `help.txt`, is
removed. `dist/jlog` remains the tested optimized build. Milestone scope and
previously recorded platform limitations are unchanged.

## Readability refactor — 2026-10-26

Refactored all four modules without adding operation behavior. `Cli` decodes each
argument once while retaining native values, names command/state types, and shares
input selection, operand consumption, operation selection, and operand validation.
`Jsonl` names classification/depth helpers and shares line emission between LF
and EOF paths. `Operations` shares the physical-record increment, names error
details, and extracts bounded detail retention and readable report rendering.
`main` centralizes stdout writes and stderr failure reporting. Updated all four
learning guides to explain the new structure and documented every helper.

The existing 182 pure checks and 26 executable tests passed before refactoring;
all existing `expect` bodies and the Python suite were preserved. This is a
refactor with inherited behavior coverage; no artificial RED or feature tests
were introduced. An isolated differential check compared the new and original
CLI parsers on 25,260 argument lists of length 0 through 3, including dash-leading
operands, empty/equals forms, invalid UTF-8, and native Unix/Windows arguments.
All results matched; that temporary comparison is separate from the 182 project
checks and is not counted as a new permanent suite.

Final verification on the pinned native toolchain and recorded writable cache:

- `roc check src/main.roc` and explicit-source `roc fmt --check` passed.
- Dev and speed `roc test --no-cache src/main.roc` each passed all 182 checks.
- Dev and speed builds of `src/main.roc` completed with zero errors/warnings;
  the Python suite passed 26 tests against each build, without skips.
- A manual optimized-binary check confirmed unchanged usage-diagnostic bytes.
- An extra output-fault probe expected exit 3 but observed help exit 0 with a
  read-only `/dev/null` stdout descriptor, and usage exit 2 with an equivalent
  stderr descriptor. Python `os.write` confirmed EBADF. Rebuilding the original
  source snapshot reproduced both outcomes exactly. This is an existing
  output-error detection gap, not a refactor regression or evidence that the
  exit-3 contract is satisfied for these descriptors. No platform or contract
  change was made; retain it for the pending output-failure work.
- All 40 named functions have documentation and learning-guide coverage; local
  Markdown links and linked heading anchors resolve.

`dist/jlog` is the tested optimized binary. Existing milestone boundaries remain
unchanged; the additional observed output limitation is recorded above.

## Optional inspection progress — 2026-10-26

The user separately authorized opt-in progress; this is an explicit extension to
the earlier no-progress contract, not advancement into the pending data modes.
The specification is in `docs/specs/inspection-progress.md`, and the v0.1 contract
now permits the modifier. `--progress` emits newline-delimited stderr counts at
most about once per second as physical lines advance, plus a final `(complete)`
snapshot after successful EOF. Ordinary inspection stdout/stderr and status
behavior remain unchanged; help and usage advertise the new modifier.

**RED:** `JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p
'test_cli.py' -k progress -v` ran the new mixed file/stdin acceptance method
against the existing binary. It failed all five invocation subcases: file cases
returned usage status 2 instead of malformed-input status 4; stdin cases returned
usage output instead of the report and progress snapshot. This was an executed
behavior failure, not a compiler failure. The baseline pure suite passed 182
checks before implementation.

**GREEN / REFACTOR:** added a command/state boolean, strict one-use modifier
parsing, pure monotonic scheduling/rendering, and effectful progress coordination
in the shared read loop. The pinned platform supplies `Monotonic.now! : () => U64`
in nanoseconds; its inspected APIs provide no terminal detection. Plain stderr
lines therefore work consistently without FFI, dependency, or toolchain changes.
Factored stderr line writing so progress and failure diagnostics share one policy.
Default runs read no clock and write no progress. Read errors return before
completion; progress write errors reported by the platform propagate as exit 3.

**Final verification:** all commands used the recorded writable cache and pinned
native macOS ARM64 toolchain. Both dev and speed `roc test --no-cache src/main.roc`
passed **202** checks: 77 CLI, 97 JSONL, and 28 inspection/progress. Both builds
completed with zero errors/warnings. Python discovery against each build passed
**33** methods with no skips. The seven new executable methods cover file/stdin
parity, empty/unterminated input, opt-in/argument boundaries, literal filenames,
input failures without completion, unfinished operations, and live progress.
The live pipe test holds stdin open, observes a progress line before EOF, asserts
stdout is still empty, then checks the final report/count/status. Pure policy
checks cover exact interval boundaries, unchanged counts, and backwards timestamps.

`roc check src/main.roc`, explicit-source formatting checks, and diff whitespace
checks passed. The README sample produced its exact six-record stdout report and
stderr completion line. Earlier CLI assertions were retained with an explicit
false modifier default; existing JSONL/summary assertions remain intact. All new
functions have documentation and learning-guide explanations; Markdown links and
heading anchors resolve. `dist/jlog` is the tested optimized binary.

Updates are checked after input reads; blocked reads and very long records can
delay snapshots. No background heartbeat, percentage, or terminal animation was
added. Existing stdin/output-descriptor gaps and pending Linux/resource/release
verification remain. Count, tail, and filtering are still unimplemented.

## M2 implementation — authorized 2026-10-26

The user requested starting M2 using the existing specification and plan. Work
proceeds one task at a time; previous M1-only resume text is historical. Pending
progress/fixture changes in the working tree are preserved. Baseline: 202 pure
checks and 33 executable methods passed on the pinned native toolchain.

| Task | Executed RED | GREEN / refactor verification |
| --- | --- | --- |
| M2-01 | Focused `roc test --main=src/main.roc src/Operations.roc` failed the new empty-count assertion: placeholder returned empty text instead of `0\n`; 202 passed, 1 failed, zero compiler errors. | `count_report` renders only the shared summary's valid total plus LF. Empty, valid, all-invalid, mixed, final unterminated, ungrouped large, and maximum-U64 cases pass. Framing checks confirm the pending final record joins the count only at finish; executable EOF gating belongs to M2-03. Focused/regression P: 209 passed; dev build: zero errors/warnings; I: 33 passed. |
| M2-02 | The same focused command failed mixed-input diagnostics against the empty placeholder: 209 passed, 1 failed, zero compiler errors. | `data_diagnostics` renders source/physical line/reason, uses shared escaping, and reports omitted invalid details after the first 100. Empty/valid input is quiet; mixed/control-label/capped cases pass. P: 214 passed; check/format clean; dev build: zero errors/warnings; I: 33 passed. |
| M2-03 | Executable `-k m2_03` failed all 12 initial file/stdin cases: unfinished-operation status 1 rather than count status 0/4. | Count now uses the same native-source reader/framer/summary pipeline as inspection. It defers count and capped data diagnostics until EOF, includes the final unterminated line, accepts all JSON kinds/huge numbers, and preserves exit 4 for malformed input. A held-open stdin test proves no premature stdout/stderr. P: 214 passed; dev I: 37 passed; build/check/format clean. Inspection-only progress remains quiet in count mode; its previous unfinished-count expectation was replaced by count-contract coverage. |
| M2-04 | A one-record tail assertion failed against the compiling no-storage placeholder: 214 passed, 1 failed, zero compiler errors. | Tail starts empty and appends only received valid bodies within N. Empty, zero-N, one, fewer-than-N, order, and maximum-N/tiny-input cases pass without preallocation. P: 220 passed; dev I: 37 passed; check/format/build clean. Eviction remains the next task. |
| M2-05 | The first full-tail eviction assertion failed: limit 2 retained records 1/2 instead of 2/3; 220 passed, 1 failed, zero compiler errors. | Indexed ring replacement evicts the oldest body, wraps its index, and restores input order only at completion. Repeated wraps, N=1, immutable snapshots, bounded length, and maximum-N/tiny input pass. P: 224 passed; dev I: 37 passed; check/format/build clean. |
| M2-06 | Executable `-k m2_06` failed 12 initial file/stdin/N cases: unfinished status 1 rather than malformed status 4. | Tail now shares single-pass classification and capped summaries with inspection/count. Zero-N still validates; output preserves original bodies/order and normalizes only terminators after EOF. Empty/max-N, repeated wraps, huge numbers, Unicode, duplicate keys, leading zeroes, malformed records outside the suffix, and held-open stdin pass. P: 224 passed; dev I: 40 passed; build/check/format clean. |
| M2-07 | A seeded maximum-counter assertion failed against the compiling checked-consumer placeholder: 224 passed, 1 failed, zero compiler errors. | The production consumer propagates sticky resource failures and checks totals before incrementing. Framing records line-number exhaustion without wrapping and stops consuming further bytes; the driver exits 1 before output. Pure checks cover near/max counters, failure categories 0/1/2/3/4, EOF framing exhaustion, and sticky failure. P: 237 passed; dev I: 40 passed; check/format/build clean. A test-local name initially shadowed `framed`; its warnings were corrected during GREEN, not counted as RED. |
| M2-08 | New cross-mode missing/unreadable/directory tests passed immediately: the shared source reader already maps these failures correctly. Inherited coverage; no RED fabricated. | Real unprivileged permission fixtures and empty deferred outputs are asserted for inspect/count/tail, including N=0. Dev I: 41 passed. |
| M2-09 | A prefix read-failure transition failed against a compiling completion placeholder: 237 passed, 1 failed, zero compiler errors. | `complete_stream` resolves EOF versus read failure; the actual reader routes both through `finish_input!`, which emits progress/results only for success. Seeded valid/malformed prefixes prove deferred data is dropped and I/O overrides exit 4. Directory-stdin tests exercise actual reported read errors in all modes. P: 240 passed; check/format/build clean. Advanced prefix fault attempt is recorded below. |
| M2-10 | Closed-pipe acceptance tests passed immediately using existing error-propagating writers; these are inherited coverage, not artificial RED. | Eight real closed stdout cases cover help/version/inspect/count/tail and valid/malformed input; five closed stderr cases cover usage, unimplemented filtering, progress, count/tail diagnostics. All return 3 without crashes, recursion, or deferred stdout after stderr failure. EBADF descriptor ambiguities remain a separately disclosed contract gap. |

S-IO preliminary probe: a closed-reader stdout pipe with help and a closed-reader
stderr pipe with a usage error both yielded exit 3 on the pinned platform. These
are distinct from the earlier EBADF descriptor gap, which remains recorded.

S-tail API probe: the pinned compiler passed five isolated checks for indexed
`List.set`, out-of-bounds results, list retrieval/slicing, and widening U32 to U64.
This establishes the ring-storage API without assuming current online docs match
the pin. Production insertion and ownership behavior are verified in M2-05.

S-tail ownership smoke probe: an optimized, argument-driven program used the
actual production `tail_push` for 200,000 insertions while retaining only its
current state. N=64/4096/16384 retained exactly N bodies and correct ring indexes;
observed single-run times were 0.156/0.019/0.015 seconds, including startup. These
noisy smoke timings rule out an obvious full-list copy on each insertion in this
probe; they are not release throughput/RSS benchmarks or cross-platform evidence.

Advanced S-IO attempt: a raw pseudo-terminal delivered a malformed/valid prefix;
the running inspection emitted `3 lines inspected, 1 invalid` before EOF with
stdout still empty. Closing the slave then yielded EOF, a completed report, and
exit 4 rather than a read error. This is **not** a mid-stream read-fault injection
or evidence of that executable scenario; it remains unverified. The mandatory
pure production transition and ordinary executable read failures are covered.

Strict descriptor-edge conformance remains unresolved on this platform: write-only
stdin is exposed as EOF, and EBADF stdout/stderr writes can be suppressed by the
platform. The specification has not been weakened. The available APIs cannot
distinguish these results from genuine EOF/success; custom platform/FFI or pin
changes remain outside the implementation plan. Count/tail and the tested M2
error paths are implemented, but do not describe the full I/O contract as proven
for these edge cases or silently close that compatibility gate.

Final native M2 verification: `roc check src/main.roc` and explicit-source
`roc fmt --check` passed. Dev and optimized pure runs each passed **240** checks
(77 CLI, 99 JSONL, 64 operations). Both builds completed without errors/warnings;
the Python suite passed **44** methods with no skips against each binary. The dev
verification binary was `/private/tmp/jlog-m2-storage-dagtny5m/jlog-dev`, selected
explicitly with `JLOG_BIN`; `dist/jlog` remains the tested optimized artifact.
All 63 named functions have comments and learning-guide coverage. Local Markdown
links/anchors resolve, and README count/tail examples were verified against the
12,000-record fixture, including exact original bytes for the tail suffix.

README, repository guidance, handoff, and learning guides now describe implemented
count/tail and the shared checked stream architecture. M2's strict descriptor-edge
gate is explicitly left open; filtering/M3 was not started. No commit, push, PR,
platform upgrade, new dependency, or FFI change was made.

## M3 implementation — authorized 2026-10-26

The user requested committing the current work and starting M3. The preceding
changes were committed as `f174c25`; the working tree was clean afterward. This
explicit M3 instruction supersedes the earlier scope checkpoint while retaining
the unresolved M2 platform descriptor gate. No specification or I/O guarantee is
weakened. Baseline: 240 pure checks and 44 executable methods passed.

The pinned record-based dictionary capability probe freshly passed its nine
checks. Integration then exposed a declaration-order compiler crash: a custom
field decoder declared after a function using `Dict(Str, Field)` causes SIGSEGV
in checking/testing. Moving the decoder above the consumer passes unchanged
behavior assertions. The minimized reproducer and observations are preserved in
`docs/repros/m3-dict-parser-order.md`; the pin and decoder semantics are unchanged.
Compiler crashes/timeouts are investigation evidence, not feature RED results.

| Task | Executed RED | GREEN / regression / refactor verification |
| --- | --- | --- |
| M3-01 | Focused `roc test --main=src/main.roc src/Jsonl.roc` failed the positive string match against `Ok(False)`: 240 passed, 1 failed, zero compiler errors. | A record-backed marker retains decoded strings and skips other values; typed dictionary lookup compares the literal key/text. After resolving the ordering issue, check/build were clean, P: 241 passed, dev I: 44 passed. |
| M3-02 | A huge valid scalar returned `LookupFailure` instead of a non-match: 241 passed, 1 failed, zero compiler errors. | A first-significant-byte check bypasses object decoding for valid scalars/arrays. Missing and non-string fields, huge numbers, whitespace-wrapped objects, and unexpected object decoder failures are distinct and tested. Shared JSON-whitespace recognition avoids separate trim rules. P: 247 passed; check/build clean; dev I: 44 passed. |
| M3-03 | Exact-comparison regression cases passed immediately using the builtin string decoder; inherited coverage, no artificial RED. | Case, surrounding whitespace, decoded Unicode/newline escapes, quotes/backslashes, literal quotes in TEXT, and Unicode-normalization differences pass. |
| M3-04 | Literal-key regression cases passed immediately; existing CLI first-equals assertions remain covered. | Empty keys/values, RHS equals signs, spaces, Unicode-escaped keys, dots/brackets, and nested-path non-matches pass. |
| M3-05 | Duplicate-key regression cases passed immediately using the verified dictionary overwrite semantics. | Last string wins; escaped aliases overwrite; null/number/array/object replace an earlier string marker, and a later string replaces a non-string. After M3-03..05: P 268 passed, dev I 44 passed, check/format/build clean. |
| M3-06 | Executable `-k m3_06` initially failed all four source/flag forms: unfinished-operation status 1 instead of 0. | Filtering now selects valid string matches through the shared framer, drains current-read bodies, and writes original bytes plus LF before the next read. The representative fixture selects exact original lines 2/3; file/stdin, CRLF, final lone CR/unterminated bodies, literal operands, escaped values, huge numeric spellings, and live output before EOF pass. P 268 passed; the three focused executable methods passed; full dev regression is recorded under M3-08. Check/build clean. |
| M3-07 | New failure/recovery assertions passed immediately using M3-06 selection and the M2 completion/error policies. Inherited coverage; no artificial RED. | No-match and every malformed-kind recovery/cap tests pass. Production pure transitions verify drained prefixes, discarded deferred state on read failure, I/O-over-malformed status, sticky lookup/resource failures, and exhausted counters. Existing real file/stdin error and closed stdout matrices now include filtering; a broken stderr test preserves already-emitted matches with status 3. P reached 274; removing the obsolete unfinished-operation category/assertion leaves 273. The three focused M3-07 executable methods passed; full cross-mode regression is recorded under M3-08. The advanced read-fault attempt is described below. |
| M3-08 | Pipeline and redirected-output assertions passed immediately; no special pipeline implementation or artificial RED was needed. | Real filter→count processes have independently checked statuses/stderr, including upstream malformed status 4 with downstream successful count 2. Redirected output is checked by Python's JSON parser and exact raw bytes; SHA-256 source hashes remain unchanged. Full dev I 52 passed. |

Advanced M3 S-IO attempt: a raw pseudo-terminal delivered a malformed line and a
matching object. Filtering emitted the original matching body plus LF while the
input was open. Closing the slave produced EOF, one invalid-line diagnostic, and
status 4; no additional stdout appeared. As with the M2 attempt, this is **not**
a mid-stream read-fault injection. That executable scenario remains unverified;
the mandatory pure production prefix-failure transition and ordinary executable
read errors pass. Existing strict descriptor-edge gaps remain open.

Final native M3 verification: `roc check src/main.roc` and explicit-source
`roc fmt --check` passed. Dev and speed `roc test --no-cache src/main.roc` each
passed **273** checks (77 CLI, 127 JSONL, 69 operations). Both builds completed
with zero errors/warnings. Python discovery against each fresh binary passed
**52** methods with no skips; the optimized artifact remains at `dist/jlog`.

The 12,000-record sample selects **706** failed-status records. File and stdin
output exactly equal those original bodies plus LF, downstream count is 706,
and the fixture's SHA-256 is unchanged. Executable help equals `src/help.txt`.
All 71 named Roc functions have comments and learning-guide coverage; Python
functions have docstrings. Changed Markdown links/anchors and code fences, and
diff whitespace checks pass. README, repository guidance, handoff, and all four
learning guides reflect filtering and current checked stream state.

M3-01 through M3-08 are implemented and verified within the recorded native
scope. The unresolved M2 descriptor gate, actual mid-stream executable read-fault
scenario, native Linux checks, and large-file resource/release work remain open.
No M4 work, platform/pin/FFI/dependency change, push, or PR was performed. M3
changes were left uncommitted at the implementation checkpoint; the preceding-
work commit is `f174c25`. The user authorized committing M3 on 2026-10-27.

## M4-01 coverage audit — authorized 2026-10-27

After M3 was committed as `d1a0d20`, the user requested the next step and
authorized starting M4-01: audit the specification's behavioral coverage,
published examples, and remaining I/O gaps. Work starts from a clean tree on
native Darwin ARM64 with the unchanged compiler/platform pins. Fresh baseline:
273 pure checks and 52 executable methods passed. Already-passing additions are
coverage-only; no production change or artificial RED is required for them.

Added eleven `test_m4_01_*` executable methods covering the exact published
representative/malformed fixtures across all modes and sources, validation and
defect precedence, long data records across stdin reads, safe data-mode labels,
literal filenames/operands, held-open-stdin usage rejection, redirected data from
malformed sources, SIGTERM, README samples, and actual prefix read failure.
The new source-variant helper substitutes labels into hand-specified bytes and
checks hashes; it does not reproduce application logic. Independent JSON oracles
now use exact integers/Decimal. All eleven additions pass without production
changes. An initial usage-hint expectation accidentally omitted the existing
help-hint line; its fixture was corrected, not recorded as production RED.

The S-IO nonblocking-pipe mechanism is now verified on native macOS. A pipe is
prefilled with a malformed line, a complete matching record, and an incomplete
body; its read descriptor is nonblocking and the parent keeps the writer open.
After consuming the prefix, the actual executable reports WouldBlock and exits
3. Inspect/progress/count/tail 0/tail 2 emit no deferred result or completion;
filtering emits only the complete matching prefix. A parent OS read confirms
the descriptor was drained and returns EAGAIN/EWOULDBLOCK rather than EOF.
The retained regression passes in both dev and optimized builds. Earlier
pseudo-terminal attempts remain historical, not evidence of a fault. Native
Linux execution of this fixture is still pending.

The strict descriptor gate is retained in `tests/test_io_contract.py`: three
methods, **15 failing subcases** on both builds. Python OS reads/writes establish
EBADF on the same descriptors; jlog instead returns 0 for write-only stdin and
read-only stdout, and 2/0/4 for read-only stderr. Expectations remain status 3,
without skips or expected-failure markers. An independent freshly built pinned
Roc probe returns `Err(EndOfFile)` / `Ok({})` for those cases. Public API inspection
found no standard-descriptor validation or explicit flush operation. The probe,
observations, and replay commands are preserved in
`docs/repros/stdio-descriptor-errors.md`. This is an unresolved platform gate,
not a completed RED/GREEN fix or a reason to weaken the application contract.

Final checks, using `ROC_CACHE_DIR=/private/tmp/jlog-research/cache` for Roc and
`PYTHONDONTWRITEBYTECODE=1` plus the selected `JLOG_BIN` for Python:

| Command / target | Result |
| --- | --- |
| `roc check src/main.roc` | No errors. |
| `roc fmt --check src/main.roc src/Cli.roc src/Jsonl.roc src/Operations.roc` | All formatting valid. |
| `roc test --opt=dev --no-cache src/main.roc` | 273 passed. |
| `roc test --opt=speed --no-cache src/main.roc` | 273 passed. |
| `roc build --opt=dev --output=/private/tmp/jlog-m4-audit-n7rhvmo8/jlog-dev src/main.roc` | Zero errors/warnings. |
| `roc build --opt=speed --output=dist/jlog src/main.roc` | Zero errors/warnings. |
| `python3 -m unittest discover -s tests -p 'test_cli.py'` against each binary | **63 methods passed** per build; no skips. |
| `python3 -m unittest discover -s tests -p 'test_io_contract.py'` against each binary | Status 1; three methods fail, 15 failing subcases per build. |

The README big-sample filter→count pipeline prints 706, with both processes
exiting 0, both stderr streams empty, and the source SHA-256 unchanged. README
small-sample outputs are now permanent executable assertions. Help matches the
embedded `src/help.txt` bytes. Changed Markdown links/anchors/fences, Python
syntax/docstrings, the documented independent probe source, and diff whitespace
were checked. The tested optimized artifact remains at `dist/jlog`; full
descriptor logs and the probe are machine-local under the temporary audit path.

The [audit](m4-01-audit.md) maps specification/traceability groups to actual tests.
The native macOS coverage audit is complete, but **M4-01 remains open** for strict
descriptor conformance and native Linux execution. Resource measurements, native
CI, installation/packaging, license/notices, and supported OS versions remain
M4-02 through M4-06. No application source, specification, platform/pin/FFI,
dependency, release, or push change was made. The work was left uncommitted at
the audit checkpoint; the user subsequently requested committing all changes.

## M4-02 resource measurements — authorized 2026-10-27

After audit commit `816f65c`, the user requested the next task. M4-02 proceeds
with optimized resource measurements, preserving the M4-01 strict descriptor and
native Linux gates. No platform/pin/contract change is implied. The working tree
was clean; the native host is a MacBookPro18,1 with Apple M1 Pro, 32 GiB RAM,
macOS 27.0.1 (26A434), Darwin ARM64, and an 8,176-KiB stack soft limit.

The sandbox blocks `/usr/bin/time -l`'s `kern.clockrate` query. The approved
unsandboxed control `/usr/bin/time -l /usr/bin/true` exits 0 and reports elapsed,
user/system time, and maximum resident set size in bytes. Hardware metadata was
also read with approved `sysctl -n`. This is tooling setup, not application RED.
Large fixtures and raw measurement artifacts will be generated in temporary
storage, with exact output/status/hash checks independent of the measurements.

Added the stdlib-only `tests/measure_resources.py` driver. A 62-case small-input
run verified fixture templates, all output/status oracles, cap/omission text,
native timing parsing, and unchanged input/binary hashes before full measurement.
The same 62-case shape passed again after refactoring targeted `--cases`
selection, which generates only the required fixtures. Setup/syntax work on the
driver is not application RED; no production behavior needed a RED/GREEN cycle.

The optimized native baseline ran **70 cases** sequentially: 100,000/1,000,000
valid and all-invalid 1,024-byte records through file and redirected stdin;
inspect/count/filter and varying tail N=0/1/64/4096/16384; single 1 MiB/8 MiB
bodies in all four modes; and a two-record input with maximum U32 tail N.
Every case passed golden output byte-count/SHA-256, exact stderr/status, and
final input/binary hash verification. Verified large stdout files are removed;
fixtures and raw timing/diagnostic artifacts remain outside the checkout.

Two initial inspection cases were repeated to investigate elapsed/CPU timing
differences, retaining both observations. A separate fixed-N=16384 follow-up
used 4,000,000 records (4,096,000,000 bytes) through file and stdin to investigate
tail RSS variation. The total **74 measured cases** all pass. The original
baseline driver snapshot/hash is retained; the later driver adds targeted case
selection without changing the application's binary or default matrix.

Observed file count RSS is 2.83 MiB for both 102.4 MB and 1.024 GB inputs;
filter RSS is 3.25 MiB for both, while emitting 51.2 MB and 512 MB respectively.
All-invalid RSS stays within 2.66–3.02 MiB across measured sizes, modes, and
sources, with exactly 100 details and correct omitted counts. Tail memory grows
with retained data; fixed N=16384 peaks at 68.92/101.95/92.66 MiB for file inputs
of 100,000/1,000,000/4,000,000 records, and 76.94/78.75/99.41 MiB for stdin.
The larger-input check does not show RSS tracking total bytes. Maximum-N tiny
inputs peak near 2 MiB without preallocation. Native 8 MiB-body cases complete
without stack failure, at 31.05–31.30 MiB file RSS and 14.83–15.08 MiB stdin RSS.

No measured retention/scaling or stack violation required a production change,
and no speculative optimization or post-hoc absolute RSS threshold was added.
The measurements are single-host sequential observations with no cache eviction,
CPU isolation, or universal throughput/complexity claim. The timer prints
hundredths; elapsed/CPU discrepancies and tiny rounded times are preserved.
See the [report](../measurements/m4-02-macos-arm64.md) and
[74-case JSON artifact](../measurements/m4-02-macos-arm64.json) for exact commands,
input/max-line bytes, N, host, native real/user/system time, peak RSS, statuses,
output hashes, interpretation and reproducibility limits.

Final verification: optimized `roc build` completed without errors/warnings;
`roc check src/main.roc` and explicit-source `roc fmt --check` passed. Optimized
`roc test --no-cache src/main.roc` passed **273** checks, and the actual measured
optimized artifact passed **63** ordinary executable methods with no skips.
Its SHA-256 remains
`0bf01d6835fa99f8dec215c922be8bd8f68601653dae1a0a326a01cb24c6ed77`.
Driver syntax/docstrings, both smoke matrices, archived data integrity, current
and baseline driver identities, local Markdown links/anchors/fences, and diff
whitespace were verified. No application source was edited.

Native macOS M4-02 measurements are recorded; native Linux resource verification
remains pending, and the driver currently requires macOS `time -l`. The earlier
M4-01 strict descriptor failures remain unresolved and were not weakened or
claimed fixed. Native CI, install/packaging, license/notices, and OS support
remain later tasks. No platform/pin/FFI/dependency change, release publication,
push, or commit was made. The work is uncommitted.

M4-02 follow-up requested by the user's questions about copies and peak phase:
the whole-run timer cannot locate a peak, so a read-only native Mach probe gates
EOF and final stdout on the unchanged binary. Four trials use 100,000/1,000,000
records at N=16384 through stdin and a FIFO on the File.Reader path. The probe
confirms an empty input queue and no output before EOF, reads current/high-water
RSS, then blocks stdout after EOF before draining/verifying the exact tail.
Per-child `wait4.ru_maxrss` records the final maximum. Source/binary hashes stay
unchanged. The raw probe/traces remain in temporary storage; the compact
[summary](../measurements/m4-02-tail-phases.json) and report preserve the results.

For 1,000,000 records, stdin is 88.66 MiB before EOF and peaks at 89.14 MiB after
EOF (about 0.48 MiB extra). The FIFO/file-reader probe peaks at 76.61 MiB during
processing, with output-blocked current RSS 75.59 MiB and no higher final peak.
The smaller trials show the same distinction. These are controlled pipe/FIFO
probes, not retrospective phase timestamps for the earlier regular-file runs.

The exact pinned Roc runtime source at
`258ab27f79bef726d501e3b79ce2e47e54e83f9d` was inspected. `listSet` updates a
unique outer list or shallow-copies outer elements with nested increfs when
shared, and decrefs the displaced element. This does not recursively duplicate
record payloads. Which compiled calls take the uniqueness path and the exact
cause of the remaining RSS overhead were not allocation-profiled. No application
or platform source was modified and no memory-cause claim is inferred from RSS.

## M4-02 Linux container measurements — authorized 2026-10-27

The user requested Linux resource measurements and suggested Docker. Existing
macOS artifacts and pending changes are preserved. Docker Desktop reports a
native ARM64 Linux VM (10 virtual CPUs, 8,214,851,584 bytes RAM) on the Apple
Silicon host. Native ARM64 container measurements proceed as supplemental Linux
evidence; they do not close the planned native x86-64 release gate. No emulated
x86-64 performance is presented as native. The architecture choice was surfaced
to the user; native ARM64 is the stated default while awaiting optional steering.

The exact nightly release contains both Linux ARM64 and x86-64 compiler assets.
The ARM64 archive's release digest is
`9750ce89a820d3cdeadd751996d26c70b68584ca9428e52f43a1bb20702c54e5`.
The driver initially rejected GNU time verbose data with ValueError; the new
format test reproduces that missing driver behavior. Linux parsing/normalization
is then added while retaining the passing macOS byte-unit assertion. Three
driver checks now pass, including invalid-data rejection. This is driver work,
not a production application RED/GREEN change.

The Docker image uses Debian base manifest
`7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8`, verifies the
compiler archive SHA-256 before extraction, and runs the unchanged compiler pin
successfully. The built ARM64 image ID is
`77bae4abc313f331d62956145c843235a20d82f7729b7d5d76ff2c70fa5fa6f5`.
The source mount is read-only; builds, cache, fixtures and outputs are inside
the Linux filesystem. UID 1000 executes all permission fixtures. Docker's bridge
is disconnected before the timer controls, smoke matrix and full measurements;
`NetworkSettings.Networks` is verified as `{}`. Source module hashes, image/host
provenance, page/stack sizes, cgroup limits and package versions are archived.

Native ARM64 Linux verification: `roc check`, explicit-source formatting, 273
dev and 273 speed pure checks pass. Both fresh Linux builds pass all **63**
ordinary executable methods without skips, including raw invalid-UTF-8 filename
opening and actual prefix WouldBlock. Three driver unit checks pass on both
Linux and macOS. The strict descriptor suite is separately captured for both
Linux builds: three methods, **15 failing subcases** each, status 1. No skipped
or expected-failure annotations, contract change, or claim of full I/O
conformance was introduced.

GNU time (`time` Debian package 1.9-0.2) controls report 828 KiB RSS for `true`
and 39,788 KiB for a Python process touching a 32 MiB allocation. The 62-case
small matrix passes native-format parsing, output/status/hash checks and final
input/binary integrity. The full **70-case** matrix then passes all cases on
the unchanged optimized ARM64 ELF. Its seven fixture hashes exactly match the
macOS baseline. GNU RSS is normalized from KiB to bytes. A final two-case macOS
smoke also passes after the cross-platform driver changes.

Observed Linux file count/filter peak RSS stays about 0.4 MiB from 102.4 MB to
1.024 GB input. Tail N=4096 stays at 5.13 MiB; N=16384 stays at 19.38 MiB for
file input and 19.51 MiB for redirected stdin across both sizes. All-invalid
cases remain near 0.39–0.42 MiB with exactly 100 details and correct omissions.
The 8 MiB body passes all modes without stack failure: 17.18–17.56 MiB file
RSS, 8.48–10.04 MiB stdin RSS. The maximum-N tiny input emits exactly its two
records without preallocation. No measured violation requires a production
change or another large-input follow-up. Raw timing variance is preserved;
these are single-observation shared-VM results, not a throughput promise or
an explanation of cross-OS allocator differences.

The [Linux ARM64 report](../measurements/m4-02-linux-arm64-docker.md),
[70-case JSON](../measurements/m4-02-linux-arm64-docker.json), and
[Docker instructions](../../tests/docker/README.md) record the exact context,
replay procedure and limits. The Linux ELF is retained as ignored
`dist/jlog-linux-arm64`, SHA-256
`e279601f4160b9b4830e34f37340a472680ba492eaf3225f8c9ff9ec24504f25`;
the measured macOS `dist/jlog` is unchanged. The task container is stopped after
export, retaining raw artifacts for review. Native Linux x86-64, full native CI,
strict descriptor conformance and later release work remain open. No application
source, platform/FFI/pin, release publication, push or commit was changed.

## M4-03 native CI — authorized 2026-10-27

The user proposed using CI to obtain the required native Linux x86-64 evidence
and explicitly tackling M4-03 alongside M4-02. The new workflow uses independent
`ubuntu-24.04` x86-64 and `macos-15` ARM64 jobs. Installation asserts the actual
OS/architecture, verifies the exact pinned archive SHA-256 and compiler version,
and preserves basic-cli 0.25.0. Checkout/upload actions use full commit pins;
there is no moving setup action or shared dependency cache.

The shared CI driver records command logs/statuses, source/binary hashes and
runner/image provenance. Both dev and speed run pure checks, native builds,
ordinary executable tests and the unchanged strict descriptor suite. Strict
failures are real failed CI steps; a separately conditioned step still measures
an optimized build whose pure/ordinary/driver checks passed. Upload retains small
evidence files and tested binaries, excluding generated fixtures/stdout/cache.

Local preparation: `actionlint` 1.7.12 and shell/Python syntax checks pass. The
actual macOS installer downloads and verifies archive SHA-256
`aa6339579730fcea4753940bec21f5d8cf8be8e25659ec001abccbc3463a60b2`, then confirms
the exact nightly. The CI driver passes check/format, three measurement-unit
tests, 273 pure checks and 63 ordinary CLI methods for each optimization. Its
status is correctly **1**, with only `io-contract-dev` and `io-contract-speed`
failing (15 strict subcases each). Source hashes stay unchanged; a one-case
measurement smoke verifies the new environment artifact. These local logs live
under `/private/tmp/jlog-m403-local-evidence` and
`/private/tmp/jlog-m403-local-measure-smoke`.

Workflow/tooling commit `48c9aa9` is pushed to the separate `ci/native-m4` branch;
local and remote `master` are unchanged. The HTTPS OAuth credential lacks workflow
scope, so the push uses the already authenticated SSH transport without changing
the remote URL or credential scopes. No release or PR is published. Native
execution and measured results are pending the actual GitHub run; preparation
does not close either release gate.

Execution follow-up: [run 40549245469, attempt 1](https://github.com/DanielBlanco/jlog/actions/runs/40549245469)
finishes on both native targets at `48c9aa9`. Linux is `x86_64`, Ubuntu 24.04.5,
kernel 6.17.0-1022-azure, image `20261023.334.3`, four logical CPUs and UID 1001.
macOS is ARM64 15.7.9, image `20260907.0337.1`, three logical CPUs and UID 501.
Exact native compiler installation passes on both. Each build passes 273 pure
checks and 63 ordinary CLI methods without skips; formatting/check and all three
driver unit checks pass. The only nonzero command statuses are the two strict
descriptor suites per job, each with the same 15 failing subcases. Both jobs
correctly conclude **failure**; no waiver or application fix was introduced.

Both optimized resource steps and both artifact uploads succeed. Each native
matrix verifies **70/70** outputs/statuses/diagnostics and final input/binary
hashes. All seven fixture hashes match the earlier macOS/Linux ARM64 baselines.
Downloaded ZIP digests match GitHub metadata; source/driver/tested executable
hashes are checked locally. macOS's optimized binary matches the earlier local
baseline exactly. The native x86-64 static ELF is retained as ignored
`dist/jlog-linux-x86_64`, SHA-256
`c7a3e08ad74a6d5b1508e1160fd1f3379566eb4795fbf261abb8457325915d78`.

Native x86-64 file count/filter peaks at 0.39 MiB across 100,000/1,000,000
1-KiB records. Tail N=4096 stays at 5.14 MiB; N=16384 stays at 19.39–19.52 MiB
for files and 19.27–19.52 MiB for stdin. Invalid data stays at 0.39–0.52 MiB
with exact capped diagnostics. An 8 MiB body passes all modes without stack
failure, using 16.46–17.39 MiB file RSS or 8.57–9.85 MiB stdin RSS under the
16-MiB stack limit. No measured violation justifies production optimization.
Single shared-VM timings remain observations, not throughput guarantees.

The [native CI report](m4-03-native-ci.md),
[Linux x86-64 report/JSON](../measurements/m4-02-linux-x86_64-ci.md), and
[macOS CI JSON](../measurements/m4-02-macos-arm64-ci.json) retain durable compact
evidence. Downloaded raw logs/artifacts remain under
`/private/tmp/jlog-m403-artifacts`; GitHub uploads expire 2026-11-10. M4-02 now
has resource evidence on both required native architectures. M4-03 automation
is implemented and executed, but full native conformance and M4-01 remain open
because the strict descriptor gate fails. M4-04/05/06, release publication and
minimum OS support decisions remain later work. The CI workflow/tooling is
committed/pushed; measurement reports and documentation updates remain pending.

## Descriptor failure investigation — 2026-10-27

The user supplied the GitHub `io-contract-speed` failure output. The unchanged
optimized binary freshly reproduces all 15 subcases locally. Source inspection
traces this to Rust's intentional `handle_ebadf` standard-stream behavior, used
by basic-cli 0.25.0. The [descriptor reproducer](../repros/stdio-descriptor-errors.md#root-cause-and-isolated-correction-2026-10-27)
now records the exact cause and a tested candidate correction.

A temporary basic-cli 0.26.0 / minimum compiler October-12 upgrade passes 961
inline checks but still fails all 15 descriptor subcases. Six ordinary
WouldBlock-injection subcases also time out. Its native backend explicitly
preserves EBADF suppression and waits on EAGAIN. The experiment stops after
these mandatory failures; no active project pin is changed.

A narrow [patch](../../platform/patches/stdio-access.patch) for the exact 0.25.0
host instead checks descriptor access before calling Rust's standard streams.
It preserves empty-write no-ops, buffering, existing errors and the hosted ABI.
The isolated patched platform uses the original pinned Roc compiler and a
temporary application copy with only its platform path changed. Both dev and
speed pass 486 inline checks (273 project + 213 local-platform), all 63 ordinary
CLI methods and all 15 descriptor subcases. Six silent-stream controls also
pass across the two builds. Check and explicit-source formatting pass; the patch
applies cleanly to the original release source and reproduces the tested source.
Source/archive/patch/host/binary identities are retained in the
[candidate JSON](../repros/basic-cli-stdio-candidate.json).

This is a proven native macOS candidate, not a fixed GitHub workflow. Native
Linux execution, reproducible dependency integration and resource remeasurement
remain pending adoption. The active source/platform/compiler/CI pins and test
assertions remain unchanged, so the existing release blocker is still open.

## Adopt the basic-cli descriptor correction — authorized 2026-10-27

The user approved integrating the tested 0.25.0 platform correction in local
builds and CI, then verifying native Linux. This supersedes the original
official-archive-only constraint, preserving Roc `nightly-2026-10-09-258ab27`
and the unchanged strict exit-3 expectations. The correction moves to
`platform/patches/stdio-access.patch`; a lock file pins both upstream archives,
source commit, original/patched Rust source hashes, patch checksum and Rust 1.99.0.

`scripts/build_platform.py` verifies downloads and the exact patched source,
builds the native host with Cargo.lock enforced, and prepares ignored
`platform/basic-cli/`. Every generated file is recorded in a manifest and checked
before reuse. CI verifies that manifest before and after both build suites,
retains it in artifacts and uses native musl tooling on Linux. Docker uses the
same bootstrap from a writable copy of the read-only source mount.

Local macOS integration passes check/format, 486 dev and speed inline checks
(273 project + 213 local-platform), **64** ordinary CLI methods and all 15 strict
descriptor subcases per build. Three timing-unit and two platform-integrity
checks pass. The new ordinary method preserves the three previously passing
silent-output controls; it is regression coverage rather than fabricated RED.
The two platform checks reject corrupted artifacts and mismatched input/target
identities. The bootstrap is exercised from verified cached archives, then its
reuse path verifies every generated file. Raw local results are retained under
`/private/tmp/jlog-patched-local-evidence`. Native CI/Docker results follow.

Integration is committed and pushed as `cf08c48`. Both the
[push run 40560321503](https://github.com/DanielBlanco/jlog/actions/runs/40560321503)
and [PR run 40560329965](https://github.com/DanielBlanco/jlog/actions/runs/40560329965)
finish **success** on Linux x86-64 and macOS ARM64. Durable artifacts use the PR
run's actual merge checkout `0fb8a1d86b78a3e315b1de9bdc4758a2f7d15157`; source
hashes match the pushed head/local checkout. Each build passes 486 inline and
64 ordinary methods plus all 15 unchanged strict descriptor subcases, with no
skips. All five tooling unit checks and every verification command pass.

Both corrected optimized hosts pass **70/70** resource cases, with all seven
fixture hashes matching the original baselines. Input/binary hashes remain
unchanged, and platform integrity is checked around verification. Downloaded
ZIP digests match GitHub metadata; source/driver/tested executable hashes are
checked locally. Native x86-64 count/filter peak at 0.41 MiB for both input sizes,
tail 4096 at 5.16 MiB and tail 16384 at 19.53 MiB. Native macOS count/filter stay
near 1.7–1.8 MiB, tail 4096 near 20 MiB and tail 16384 at 44.91–50.47 MiB.
Every 8-MiB line passes without observed stack failure and invalid diagnostics
remain capped/exact. No measured violation requires a production optimization;
shared-VM timings are not attributed to the patch or advertised as guarantees.

The updated pinned Docker image also builds and verifies as UID 1000 on native
Linux ARM64. Both dev/speed pass 486 inline, 64 ordinary and all 15 strict
subcases; five tooling unit checks and a 62-case small measurement smoke pass.
The original source mount stays read-only; the generated platform uses the
writable `/work/source` copy. The container is stopped after artifact export.
This is supplemental ARM64 evidence, not a new full resource baseline.

The [correction report](m4-03-stdio-correction.md) links the new native and Docker
JSON evidence. The known M2 descriptor gap and M4-01/M4-03 native blockers are
closed; M4-02 is refreshed for the corrected host. Next are M4-04 docs/install
verification, M4-05 archives/offline checks and M4-06 license/notices/OS/final
audit. The existing PR was neither created nor merged by this work, and no
release or upstream platform publication was performed.

## M4-04 documentation/build/install verification — authorized 2026-10-27

The user confirmed CI green and requested M4-04. No application, compiler or
platform change is needed. Two actual documentation failures are reproduced:
the README's default clone selects `master` at `76ff743`, where
`python3 scripts/build_platform.py` exits 2 because the script does not exist;
the exit-code block exits 1 in `/bin/zsh` with `read-only variable: status`.
These are documentation failures, not fabricated application RED.

The README now explicitly selects the current development branch, separates
native prerequisites/build/install steps, uses `jlog_status`, and accepts
`JLOG_INSTALL_PREFIX` for an isolated user install. It adds an executable
malformed-pipeline example and partial-output/signal guidance, and records
tested OS/architecture versions without declaring unverified minimums.
`CONTRIBUTING.md` supplies scoped development, function documentation, test/pin
and review guidance. Broad Python discovery is documented for both builds,
including the strict descriptor gate and tooling units.

The new `tests/verify_readme.py` reads the actual fenced command blocks rather
than maintaining copied shell examples. It verifies exact outputs/statuses,
redirected bytes, documented sample counts, pipefail versus default pipeline
status, a path-with-spaces install and runtime with no Roc/Rust on PATH. The
optional `--source-checks` explicitly runs five documented Roc/build/test blocks;
the default remains binary-only. Native CI executes both modes' coverage and
retains its JSON report.

A fresh remote `ci/native-m4` checkout at `f05f326` in
`/private/tmp/jlog-m404-clean-source` starts without generated platform/cache/dist
outputs. Current documentation and the verifier are overlaid for this working
tree check. With installed exact prerequisites, the documented bootstrap downloads
and verifies both archives, rebuilds the corrected host and produces the optimized
executable. Cargo's registry and the existing external HTTP package cache are
reused; this is a clean source build, not an empty-OS or hermetic-cache claim.

That clean macOS ARM64 checkout passes all **19** usage/install cases and all
**five** source blocks. Full documented regressions pass 486 inline checks and
72 Python methods (64 ordinary + three strict + five tooling) against each build;
the focused strict suite also passes. Source dev progress reports exactly 12,000
records at completion. The installed mode is 0755 and binary/input hashes match.
Raw cases, source stdout/stderr and JSON are under
`/private/tmp/jlog-m404-clean-verification`. Native CI results follow.

M4-04 changes are committed/pushed as `9c76b4c`. Both
[PR run 40571638408](https://github.com/DanielBlanco/jlog/actions/runs/40571638408)
and [push run 40571627911](https://github.com/DanielBlanco/jlog/actions/runs/40571627911)
finish **success** on native Linux x86-64 and macOS ARM64. The retained PR
artifacts use merge checkout `cb0e0f304e441a2b5e9f015ade095be4d915980c` and
identify head `9c76b4c`. Linux passes 16 usage/install cases; macOS passes 19,
including the three zsh cases. Each target passes all five documented source
blocks, in addition to the existing compiler/tests/strict/resource sequence.
The installed binary matches the tested binary byte-for-byte; application,
platform and fixture integrity checks pass. All 70 existing resource cases pass
per architecture; no resource code or baseline requirement changed.

The [M4-04 report](m4-04-docs-verification.md) links the clean-local and native
JSON evidence in `docs/verification/`. Artifact ZIP digests match GitHub metadata,
and binary/source hashes are verified locally. The optimized artifacts match
the earlier corrected-host binaries. Raw CI downloads are under
`/private/tmp/jlog-m404-ci-artifacts`; upload retention ends 2026-11-10.

M4-04 is complete. M4-05 release archives/checksums/offline smoke tests and M4-06
license/notices/OS support/final manifest remain. No application/platform/compiler
change, release archive, upstream publication or PR merge is part of this task.

## M4-05 archive preparation — authorized 2026-10-27, in progress

The user requested starting the next task after M4-04. Packaging now reuses the
tested optimized native executable, requires passing verification (including
both strict descriptor suites), verifies source/compiler/platform/binary hashes
and writes deterministic archives with executable permissions, notices, install
instructions, build provenance and checksum sidecars. Five tooling regression
methods reject failed/absent strict evidence, altered identities, corrupted
archives, lost executable permissions and missing licenses.

Notice collection preserves basic-cli/Roc/Rust upstream documents and the
conservative union of 87 native host dependency crates. Every downloaded crate
checksum matches the pinned Cargo.lock before its full notice files are copied.
The official Roc archive checksum and copied legal documents are independently
verified. `release/notices.json` records original paths/hashes and identities;
the final M4-06 audit remains separate from mechanical notice collection.

Private fixture archives outside the checkout use an explicit test-only license
marker while the project's license remains unchosen. They reuse the unchanged
M4-04 CI binaries and reproduce byte-for-byte in a second packaging directory.
Native macOS passes bundled installation and all eight runtime cases with
network access denied and no toolchains available to the process. The original
fixture/input/binary hashes remain unchanged. The initial shell probe assumed a
particular `command -v` failure status; an explicit conditional fixes that
harness issue. This is not application RED or a distributable release candidate.

Full Python discovery passes **77 methods** against the corrected local binary.
Roc check/format, both sets of 486 inline checks, Python 3.9 syntax/docstrings,
notice integrity and workflow actionlint pass. The workflow is prepared to
package only after native regressions, README checks and resource measurements
succeed, then execute the native offline smoke: a compiler-free `FROM scratch`
image with no network on Linux, and a network/toolchain-denying sandbox on macOS.

The [preparation report](m4-05-archive-verification.md) and
[private-fixture summary](../verification/m4-05-preparation-macos-arm64.json)
record exact scope and evidence. License selection/ownership confirmation is
pending via the proposed MIT / `Copyright (c) 2026 Daniel Blanco` question.
The production packager correctly stops at the missing root LICENSE. No actual
release-candidate/native Linux archive verification is claimed, and the pending
workflow has not been pushed while that gate cannot pass. M4-05 remains open;
M4-06 audit and public release remain later tasks.

### MIT approval and clean commit checkpoint

The user requested committing everything and leaving a clean state, then
approved MIT. The proposed license is now root `LICENSE`, with
`Copyright (c) 2026 Daniel Blanco`; the redundant proposal file is removed.
Both actual archive candidates package successfully from the tested M4-04
optimized artifacts. The MIT macOS archive passes installation and all eight
local offline runtime cases, with unchanged input/binary/archive hashes.
The [candidate JSON](../verification/m4-05-mit-macos-arm64-local.json) retains
the approved license hash, both candidate checksums and local smoke evidence.

Generated archives/checksum sidecars remain ignored under `dist/release/`.
Upstream notice documents retain their original bytes and whitespace; staged
source/documentation whitespace checks exclude those verbatim documents, whose
recorded hashes still match. Source, notice inventory, documentation, workflow
and verification records are included in the requested commit. No push is part
of this local checkpoint. M4-05's actual native archive CI results and M4-06 final
audit/publication work remain pending; the license-selection prerequisite is
resolved.

## Wrap-up — M4-05/06 complete, 2026-10-27

The user asked to wrap up the project and implement the remaining part where
possible. This authorizes finishing archive verification and the final release
audit; merging, tagging and public release remain separate actions.

`scripts/finalize_release.py` now validates the two downloaded native artifacts,
full verification/README/resource/offline results, exact archive contents/modes,
current source/platform pins and approved license/notice/support documents.
It rejects failed/missing/duplicate targets and differing shared release inputs,
copies the exact tested archives and writes `manifest.json` plus `SHA256SUMS`.
No second untested application build is used. Three new unit methods initially
fail because the finalizer is absent, then pass with the implementation.
All **80** Python methods pass locally; check/format and 486 inline checks per
optimization mode pass. Source/platform/compiler inputs remain unchanged.

`release/SUPPORT.md` records macOS 15.7.9 ARM64 (also locally tested on 27.0.1)
and Ubuntu 24.04.5 x86-64 on the recorded native CI kernel. Support is limited to
tested configurations; no older-macOS, wider Linux kernel/libc or supplemental
ARM64 release promise is inferred. Each final archive includes this policy.
The license review independently rechecks 87 crate archives against Cargo.lock,
165 original notice files and all six bundled documents. Original license bytes,
copyrights and dependency terms remain intact. MIT is the approved project license.

Commit `7f92f8c079ff3ccfed13fd2d977e2eda252420af` is pushed to `ci/native-m4`.
Both [PR run 40608149721](https://github.com/DanielBlanco/jlog/actions/runs/40608149721)
and [push run 40608143058](https://github.com/DanielBlanco/jlog/actions/runs/40608143058)
finish **success**. The selected PR artifacts identify merge checkout
`26081f3f4d9926fe8e3b519d16e1a766264c921a`, with matching current application
hashes. Each native target passes 486 pure checks per mode, 64 ordinary methods
and all 15 strict descriptor subcases per mode, all 13 tooling methods, every
README/source/install check, all 70 resource cases and all eight offline archive
cases. Documented broad discovery runs all 80 Python methods per build.
Earlier `022fe6f` CI runs were superseded/cancelled before this final execution.

Native macOS 15.7.9 runs the installed binary under a network/toolchain-denying
sandbox; the socket-denial probe passes. Native Linux runs the installed static
binary in a compiler/shell/runtime-free `FROM scratch` image with network disabled,
UID 65534 and a read-only root. Both verify original bytes and a real filter→count
pipeline. Input, platform, executable and archive hashes remain unchanged.

Downloaded ZIP digests match GitHub metadata. The finalizer successfully checks
both real native artifacts and creates ignored `dist/jlog-0.1.0-release/`.
Checksums pass for both archives and the manifest. A copied real artifact is
rejected after failed smoke status, an incorrect archive hash or a missing
smoke case. The final binary hashes equal the earlier corrected CI artifacts.
The release set contains exact tested archives/sidecars, `manifest.json` and
`SHA256SUMS`; durable copies of the manifest/checksums and native/license evidence
are in `docs/verification/`. Raw downloads are under
`/private/tmp/jlog-closeout-*`; GitHub artifacts expire 2026-11-11.

[M4-05](m4-05-archive-verification.md) and [M4-06](m4-06-release-audit.md) are
complete. The plan checklist, README, contribution guide, repository instructions
and handoff now record the finished v0.1 state. No implementation or verification
task remains. The verified release candidate is unpublished; new features,
merging, tagging and publication require their own subsequent request.

## Publish v0.1.0 — authorized 2026-10-27

The user confirmed PR #1 merged, then explicitly requested the README fix,
commit, push and publication of 0.1.0. Merge commit `f387bff` passes native
master CI [40615855991](https://github.com/DanielBlanco/jlog/actions/runs/40615855991).
The local master is fast-forwarded without replacing local history.

Source instructions now clone `master`; README release links, bundled install
wording and the handoff are updated for publication. Versioned release notes
describe the implemented scope, installation, platforms, error codes and license.
The bundled wording change requires fresh native archive verification before
publishing; application/platform/compiler inputs remain unchanged. The user has
authorized tagging, uploading the exact verified assets and publishing the release.
The final publication result is recorded after those actions succeed.

### v0.1.0 published — 2026-10-28

Commit `96ebc1d0d96a4403db9ec40bd393367d5a2f89f5` fixes source checkout
instructions to use `master`, removes unpublished wording from the bundled
installation guide and adds versioned release notes. It is committed/pushed to
master. All 19 local README/install checks pass, and the exact documented clone
command succeeds in a fresh temporary directory at that commit.

Native master [run 40619313436](https://github.com/DanielBlanco/jlog/actions/runs/40619313436)
finishes **success** on Linux x86-64 and macOS ARM64, including full dev/speed
regressions, strict descriptors, README/source/install blocks, 70 resource cases
and eight offline archive cases per target. Native artifact ZIP checksums match
GitHub metadata, and the finalizer revalidates the exact new archives against
the tested binaries and current release documents. No application/platform or
compiler input changes.

Annotated tag `v0.1.0` is pushed with tag object
`9fad1bd46e6b9f5ad3e97818a0b7a435be543fb5`, resolving to verified commit
`96ebc1d`. The release is created as a draft with both platform archives, their
two checksum sidecars, `manifest.json` and `SHA256SUMS`. All six uploads are
downloaded and compared byte-for-byte by SHA-256 before publication. The combined
checksum check passes. Publication adds release URL/tag/state metadata and
regenerates the manifest checksum; native-tested archive bytes are unchanged.

**[jlog v0.1.0](https://github.com/DanielBlanco/jlog/releases/tag/v0.1.0) is
published as latest**, not a draft or prerelease, at `2026-10-28T16:34:52Z`.
The unauthenticated public latest-release endpoint confirms the state, all six
asset sizes/server digests match, release notes match the committed file and a
public manifest download matches the verified bytes.

Published archive SHA-256 values:

- Linux x86-64: `639185cab8ff2432b6fa9535887efd230ea67938b2f5e23b9f00111b7a535a49`.
- macOS ARM64: `8814a1e145f83e0700ebc3d5cb1879bda7d2a7902ae8575c708aef16cec1b775`.

The [publication record](../verification/jlog-0.1.0-publication.json),
[published manifest](../verification/jlog-0.1.0-published-manifest.json) and
[published checksums](../verification/jlog-0.1.0-published-SHA256SUMS) preserve
the tagged source, native evidence and exact asset identities. The local
published set is under ignored `dist/jlog-0.1.0-publish/`; earlier candidate
snapshots remain historical. Repository guidance, README and handoff record
the completed publication. No requested v0.1.0 work remains.
