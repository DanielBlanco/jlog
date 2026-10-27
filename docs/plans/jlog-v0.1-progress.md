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
