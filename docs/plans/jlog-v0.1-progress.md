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
