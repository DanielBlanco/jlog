# jlog v0.1 Implementation Plan — TDD

## Scope and starting point

Implement the approved [reduced specification](../specs/jlog-v0.1.md): inspection,
count, tail, string-only filtering, file/stdin input, diagnostics, and exit codes.
`--field` is unsupported in v0.1 (usage error, exit 2); its original contract and
coverage are retained in the v0.2 roadmap. No query language, custom JSON parser,
serialization framework, platform, FFI, or new runtime dependency is needed.

Preserve arbitrary JSON validation, including numbers beyond U128 and `1e9999`.
Do not decode these numbers into finite numeric types. Retain depth 128, strict
blank-line handling, full-input validation, and original record bytes in tail and
filter output, normalizing only line terminators to LF.

Use Roc `nightly-2026-10-09-258ab27` with the existing `basic-cli` 0.25.0 URL.
[Feasibility research](../roc-feasibility.md) supplies executed compatibility
probes; [the JSONL introduction](../jsonl.md) supplies format background.
Those probes are not application acceptance tests.

The existing `src/main.roc` is a file-size example, not a jlog implementation.
There are no application tests or build wrappers. `AGENTS.md` describes an older
checkout layout: discover the actual compiler with `command -v roc`; do not use
the nonexistent compiler directory blindly. Its Roc formatting/testing guidance
still applies. This planning task creates no code, fixtures, harness, or CI files.

## Small architecture and test ownership

Application sources now live in `src/`; commands below use the current paths.
Initial-checkout observations describe the historical planning baseline. Add a
module only when an actual responsibility warrants it:

| Proposed file | Responsibility and tests |
| --- | --- |
| `src/main.roc` | Pinned platform declaration; native arguments/paths; buffered file/stdin effects; operation loop; stdout/stderr; final error/exit mapping. Tested through the compiled executable. |
| `src/Cli.roc` | Pure argument interpretation, operation/source selection, usage errors. Native `OsStr` conversion may use pure platform helpers; no filesystem or stream effects. Owns CLI `expect`s. |
| `src/Jsonl.roc` | Pure byte framing, UTF-8/BOM/blank classification, depth resource precheck, builtin JSON validation, string-or-other top-level lookup adapter. Owns framing/validation/lookup `expect`s. |
| `src/Operations.roc` | Pure counters, capped error locations, report/diagnostic rendering, matching, and bounded tail state. Owns transformation `expect`s. |
| `tests/test_cli.py` | Python stdlib `unittest`, `subprocess`, `tempfile`, and OS descriptor helpers. Exercises the actual binary; owns byte/exit/transport acceptance tests. |

Use headerless Roc type modules consistent with filenames. Import each tested
pure module from the application so `roc test src/main.roc` reaches its checks.
Use records, tagged errors/operations, pattern matching, and explicit `Try` results.
Choose integer types deliberately for counts and N.

For files, `File.open_reader!` / `Reader.read_line!` return raw bytes, including
LF; empty bytes mean EOF. For stdin, `Stdin.bytes!` returns chunks of at most
16,384 bytes and reports `EndOfFile`. Feed both through common pure framing and
classification, retaining only an incomplete line between reads. Decode UTF-8
after framing. Do not collect files, stdin, or streams into one list.

Validate with the verified skip-only `parser_for` adapter and `Json.parse` after
the small quote/escape-aware depth precheck. For filtering, the verified
`Dict(Str, Field)` record-based adapter retains strings and skips other values.
It is a classification adapter, not a general JSON value tree. A valid non-object
is a non-match; an unexpected decoder failure on a validated object is a blocker
to investigate, not a reason to label the record malformed or quietly skip it.

## Mandatory execution protocol

Work on one task and one milestone at a time. Every production change follows
**RED → GREEN → REFACTOR → VERIFY**. Table rows identify coherent behaviors;
add parameterized cases within a row one at a time, repeating the cycle.

1. **RED:** Write the smallest test first and execute it. Record the assertion,
   actual/expected result, command, and nonzero status demonstrating missing
   behavior. A malformed test, missing import, compiler crash, unavailable binary,
   or unconfigured runner is not application RED. Build the existing example
   successfully before the first executable RED. If a new pure function needs an
   interface, add only a compiling placeholder with an explicitly wrong result
   after writing its test; an executed assertion must fail before implementing it.
   Do not use `crash "TODO"` or syntax errors as substitutes.
2. **GREEN:** Implement only that missing behavior. Execute the focused test and
   all existing pure/executable regressions; record both results. Do not implement
   another row, future milestone, or unrequested abstraction during GREEN.
3. **REFACTOR:** Simplify without changing behavior. Prefer pure helpers and
   shared classification over duplicate readers or parsers. Execute the tests
   again, plus `roc check` and formatting checks.
4. **VERIFY:** Keep one concise entry per task in a proposed
   `docs/plans/jlog-v0.1-progress.md`: task ID; failing assertion and command with a
   brief mismatch/status; passing focused/regression tests and commands; and
   refactor/compiler/format verification status with outstanding limitations.
   Record the toolchain once and update it only if it changes. Full logs and
   per-assertion reports are unnecessary; a commit per cycle is not required.
   Close a checkpoint only with executed evidence. Never edit expectations to
   accommodate incorrect behavior or claim unexecuted checks passed.

If a newly added test already passes, record it as regression coverage; do not
fabricate RED or change production code for it. Select the next missing behavior.
No task requiring new production behavior may close without meaningful RED.
Compatibility spikes and measurement/review-only checks record observations;
they do not masquerade as feature RED/GREEN cycles. Missing release artifacts
can be intended RED for packaging checks, not for application behavior.

Preserve existing tests. On unsupported APIs, compiler crashes, or mandatory-test
reproducibility failures, stop the dependent task, retain the reproducer, and
report the blocker. The best-effort read-fault investigation follows S-IO instead.
Do not change the pin or contract as an implementation shortcut. The existing
`src/main.roc` fails `roc fmt --check src/main.roc`; record this inherited failure before
editing, separately from new regressions and meaningful RED evidence. Format
touched project sources during refactoring; resolve their inherited failures
before closing the checkpoint. Record any untouched inherited failure explicitly
rather than silently treating the check as passing.

## Verification commands and harness rules

These are future commands for proposed files, not tests executed by this planning
task. Their Roc flags were checked against the installed compiler's help.

**P — focused pure test and pure regression:** run the owning module, since no
per-`expect` selector has been established. Identify the failing check by file/line.

```sh
roc test --main=src/main.roc --verbose src/Cli.roc
roc test --verbose src/main.roc
```

Substitute `src/Jsonl.roc` or `src/Operations.roc` for the focused module as appropriate.

**I — build and execute focused/all integration checks:** test names contain the
task ID using underscores, such as `test_m1_01_version`. `JLOG_BIN` is read by the
future harness; it must not silently build or substitute a different executable.

```sh
mkdir -p dist
roc build --opt=dev --output=dist/jlog src/main.roc
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -k m1_01 -v
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v
```

**V — refactoring and milestone verification:** run P and I regressions, then:

```sh
roc check src/main.roc
roc fmt --check src/main.roc src/Cli.roc src/Jsonl.roc src/Operations.roc
```

Include only project source paths that exist at that checkpoint: start with
`src/main.roc`, then append the named modules as introduced. Do not check `.` or
compiler/cache directories. The pinned compiler's `roc fmt --help` confirms
`--check` and file-path arguments; formatting and checking two explicit temporary
copies succeeded during this revision. Use `roc fmt` with the same explicit paths
to fix touched sources, then rerun the check. The inherited `src/main.roc` check failed
with status 1; no repository source was formatted during this planning revision.

At each milestone boundary also run the completed tests against optimized code:

```sh
roc test --opt=speed --no-cache --verbose src/main.roc
roc build --opt=speed --output=dist/jlog src/main.roc
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v
```

Create only fixtures needed by a first failing test; generate large fixtures in
temporary storage. Python must assert hand-specified bytes/statuses and exercise
real files, stdin, pipes, and redirects. It must not reimplement jlog's framer,
validator, filter, tail buffer, or exit reducer. A JSON parser can independently
check emitted JSONL, but byte assertions remain authoritative; use exact integers
or `decimal.Decimal` for large numeric oracles rather than floats.

Use finite subprocess timeouts, drain both output streams, and capture each
process's status in pipeline tests. Assert exact stderr for specified diagnostics;
for OS-dependent I/O text assert the source, category, stream, and status. Native
permission tests must run unprivileged; a root-only or skipped test is not release
evidence. Do not depend on pipe writes coinciding with read boundaries: pure
framing tests provide deterministic chunk coverage.

## M1 — CLI foundation and JSONL inspection

**Objective:** a useful inspect command with correct bytes, line accounting,
classification, reports, and information/usage paths. **Complexity: high.**

**Deliverables:** the application boundary and small pure modules; initial stdlib
harness; CLI, framing, validation, and report tests. **Dependencies:** exact pins,
a successful baseline build, and writable compiler cache. If necessary, use a
writable `ROC_CACHE_DIR` as documented in feasibility; never change system/home
variables or weaken tests to bypass cache failures.

### M1-A — CLI and framing (M1-01 through M1-08)

| Task / tests to write first | Intended RED | Minimum GREEN | Refactoring opportunity |
| --- | --- | --- | --- |
| M1-01 (I): standalone version and alias emit exactly `jlog 0.1.0\n`, empty stderr, status 0. Begin with `--version`. | Existing file-size executable treats the option as a path and fails the output/status assertion. | Recognize the standalone version invocation and return through the platform normally. | Extract a small renderer; keep the entry point readable. |
| M1-02 (P): filename selects inspection; absent input / `-` selects stdin; `./-` is a filename. | Source/operation assertion fails against the compiling placeholder. | Pure default/source selection, with one input. | A small operation/source union; no option framework. |
| M1-03 (P): flags before/after input, spaced/equals operands, `--`, and dash-leading operands parse as specified. | Parsed command/source differs. | Recognize only the supported tokens and operand rules. | Share operand consumption without a general parser library. |
| M1-04 (P): unknown flags including `--field`, extra paths, repeated/incompatible operations, missing operands, invalid N, and missing `=` in `--where` are usage errors. | A rejected case is accepted or misclassified. | Preflight validation; N is digits-only, 0..4294967295, with leading zeros allowed. | One explicit usage-error type; avoid duplicated validation in dispatch. |
| M1-05 (P): textual options reject invalid UTF-8, while filename OS bytes are preserved. | Invalid text is accepted or native path bytes change. | Use pure `OsStr.to_str_try` for text and preserve native path representation. | Keep display conversion separate from path opening. |
| M1-06 (P/I): help/aliases describe reduced scope; information flags are standalone, and extra arguments are errors. | Wrong stream/status/content or accepting combinations. | Help text and standalone information-command rules. | Centralize usage text; do not expose internal architecture. |
| M1-07 (P): LF/EOF framing for zero bytes, one record, `\n`, `{}\n\n`, and final bytes without LF. | Wrong physical lines, numbering, or phantom final record. | A small feed/EOF state retaining only unfinished bytes. | Separate framing from JSON interpretation. |
| M1-08 (P): split CRLF, lone CR, split UTF-8, and arbitrary chunk cuts frame identically. | Results depend on chunk boundaries or CR is treated as a separator. | Remove only LF and its preceding CR; defer decoding until a whole line exists. | Reuse the same framer for file and stdin bytes. |

**M1-A review checkpoint:** review concise cycle evidence for M1-01..08, run
existing P/I regressions and V on introduced sources, and resolve failures before
M1-B. This checkpoint covers CLI/framing, not completed inspection acceptance.

### M1-B — Validation and executable inspection (M1-09 through M1-18)

| Task / tests to write first | Intended RED | Minimum GREEN | Refactoring opportunity |
| --- | --- | --- | --- |
| M1-09 (P): blank and JSON-whitespace-only lines classify as `blank line`; whitespace around a value remains allowed. | Blank input is skipped or counted valid. | Exact JSON whitespace classification. | Avoid broad Unicode trimming rules. |
| M1-10 (P): invalid UTF-8, initial BOM, U+FEFF inside/outside strings, and defect precedence classify correctly. | Wrong reason or lossy replacement makes invalid bytes valid. | Validate UTF-8, detect the first-line BOM, then continue classification; preserve the original bytes. | A single ordered classifier. |
| M1-11 (P): depths 128/129 for arrays/objects, quoted delimiters, escaped quotes/backslashes, and malformed-but-shallow input. | 129 passes or string contents are counted as nesting. | The documented bounded quote/escape precheck before JSON parsing; builtin still decides grammar. | Three small state fields, no tokenizer or AST. |
| M1-12 (P): all six value kinds, heterogeneous/nested values, Unicode/surrogate pairs, and huge numbers validate. | Correct JSON is rejected or narrowed to objects/finite numbers. | Adapt `Json.skip_json_value` through `Json.parse`, without numeric conversion. | Encapsulate the adapter so it is easy to recheck on pin changes. |
| M1-13 (P): comments, trailing commas, leading zeros, bad escapes, lone surrogates, extra values, truncated/multiline values, and control bytes fail validation. | Invalid record passes. | Propagate builtin validation failure as `invalid JSON` after earlier classification priorities. | Share the classifier; do not add JSON grammar rules. |
| M1-14 (P): totals equal valid+invalid, physical numbering includes bad lines, and only first 100 error details are retained. | Wrong totals/order, missing bad lines, or 101 details retained. | Incremental summary and capped locations with omitted count. | Keep retained state independent of total input length. |
| M1-15 (P): exact empty/valid/mixed reports, optional malformed section, decimal formatting, `<stdin>`, escaped source controls, and omitted-detail line. | Byte/string mismatch in the rendered report. | Pure report rendering with specified spacing and final LF; no malformed duplication on stderr. | Share number/source rendering with later diagnostics. |
| M1-16 (I): file inspection for single and representative mixed records, native-byte filenames, and inaccessible input. | Executable still prints sizes, mangles a path, or returns the wrong stream/status. | Buffered byte reads, pure processing, report only after EOF; catch basic open/read failures with stderr and exit 3. | Keep I/O orchestration small; drop reader references on completion/error. |
| M1-17 (I): absent input and explicit `-` match file results, including empty stdin, CRLF, malformed bytes, and long/final lines. | Wrong result, prompt output, truncated line, or waiting past EOF. | Raw stdin chunks with common framing and one EOF flush. | Share line processing while keeping EOF conventions explicit. |
| M1-18 (I): invalid arguments/help/version finish with stdin held open; invalid arguments plus inaccessible paths produce usage errors before I/O. | Process blocks reading or reports a file error instead of usage. | Parse/validate completely before opening/consuming input. | One command dispatch boundary; replace legacy file-size behavior. |

**Verification:** use P for each owning module and I for each transport/CLI task;
run V and the optimized milestone suite. Preserve the specification's empty,
representative, and malformed reports as exact executable expectations.
Review M1-B evidence and the full M1 Definition of Done before advancing to M2.

**Definition of Done:** all M1 checks have recorded cycles; inspection reaches
EOF incrementally, yields accurate totals/first-100 diagnostics and 0/4 statuses,
and does not emit a report on read failure. UTF-8, numeric syntax, depth, framing,
standalone commands, and preflight behavior are covered. Basic I/O errors already
fail explicitly; M2 completes failure-category and precedence coverage. No code
claims count/tail/filter acceptance before their milestones pass.

## M2 — Count, tail, and errors

**Objective:** scriptable count/tail and complete error contracts with bounded
storage. **Complexity: medium to high**, primarily tail ownership and I/O tests.

**Deliverables:** pure operation/error transitions, bounded tail, data diagnostics,
and real executable failure tests. **Dependencies:** M1 complete; verified normal
file/output failure fixtures and storage API spikes where needed (see risks).
Deterministic mid-stream read-failure injection is advanced, best-effort
verification, not a dependency or unconditional release blocker. Production
read-error handling and pure error-transition coverage remain mandatory.

| Task / tests to write first | Intended RED | Minimum GREEN | Refactoring opportunity |
| --- | --- | --- | --- |
| M2-01 (P): count renders valid count only at EOF, including zero and invalid records. | Wrong count/text or premature result. | Reuse validated-record totals and emit one ungrouped integer plus LF at completion. | Share counting state with inspection. |
| M2-02 (P): data-mode stderr diagnostics use exact source/line/reason, cap at 100, and report K suppressed details after EOF. | Wrong stream text, cap, ordering, or omission count. | Pure diagnostic events/rendering; keep inspection's separate report contract. | Reuse source escaping; avoid storing record content. |
| M2-03 (I): count on file/stdin, clean and malformed input, matches the spec including count output with exit 4. | Headers, wrong count/status, or diagnostics on stdout. | Wire count and data diagnostics into the existing read loop. | Share EOF/result handling. |
| M2-04 (P): empty/zero-N tail emits nothing and retains no records; one/fewer-than-N records retain input order. | Wrong empty/order/size state. | Minimal bounded tail state growing with records received, not requested N. | Keep valid-record inclusion distinct from validation of all lines. |
| M2-05 (P): appending beyond N evicts the oldest valid record; large N with a tiny input never allocates N slots. | Old records remain, ordering changes, or maximum N fails through eager allocation. | A grow-as-needed bounded ring or equivalent verified storage; retain at most N bodies. | Consume state without retaining snapshots or rebuilding an N-element list each insertion. |
| M2-06 (I): tail 0/1/large/leading-zero/max-N; invalid N before input; bad records outside the selected suffix; CRLF/final-LF normalization. | Wrong bytes/status, skipped validation, eager allocation, or early output. | Emit selected original bodies only after successful input EOF; skip bad records but retain exit 4. | One output path normalizing only terminators. |
| M2-07 (P): final statuses 0/1/2/3/4, I/O failure overriding previous invalid records, and detected counter/resource exhaustion. | Wrong error precedence or wrapped generic host exit. | Explicit failure classification and `Err(Exit(code))`; exercise overflow with seeded near-limit state, not gigantic input. | Centralize exit mapping at the effect boundary. |
| M2-08 (I): nonexistent, unreadable, and directory input produce exit 3, empty stdout, and source/category on stderr. | Generic/incorrect status, partial deferred result, or missing category. | Map the actual platform's open/read errors; retain OS-specific details only where allowed. | Share file/stdin failure formatting; keep native paths intact. |
| M2-09 (P; advanced I best effort): read failure after a prefix suppresses inspect/count/tail results and overrides malformed status. Test the production error transition purely; attempt deterministic executable injection via S-IO. | The pure failure transition retains deferred output or status 4; an executable fault may expose a hang/wrong result. An unavailable injector is not RED. | Stop on read error, discard deferred output, and return 3. Keep mandatory pure coverage; record any unverified executable scenario. | Explicit EOF versus failure transitions; no duplicated recovery logic. |
| M2-10 (I): actual broken stdout pipe/write failure returns 3 for every completed output path, including help/version and after malformed input; stderr write failure is handled without recursion. | Success, wrong status, generic exit, or retry/diagnostic loop. | Propagate writes and stop; make failure diagnostics best effort when stderr itself is unavailable. | Keep write failures outside record-validation errors. |

**Verification:** P on operations/CLI, including production read-error transitions,
plus I on count, tail, normal file errors, and actual output failures; V and
optimized regression. Attempt advanced mid-stream read-fault integration where
reproducible, recording platform, command, result, and any unverified scenario.
Check status 1 using controlled pure/error boundary tests, not OS memory
exhaustion. An EOF, timeout, unlink, chmod on an already open descriptor, or
fabricated Python exception is not proof of an executable read failure.

**Definition of Done:** count/tail satisfy exact data/diagnostic contracts through
EOF; N=0 still validates; large N is not preallocated; bounded storage preserves
order. All exits, pure read-error transitions, normal file errors (including native
permission errors), and actual output failures have executed evidence, with no
deferred result on input failure. Advanced mid-stream injection is attempted best
effort; an unavailable fixture leaves an explicit, nonblocking verification gap.
A demonstrated production error-handling defect still blocks completion.
Memory/time measurements remain M4.

## M3 — String-only filtering

**Objective:** exact, top-level string matching with byte-preserving JSONL output.
**Complexity: medium.** **Dependencies:** M1/M2 complete and the documented
record-based dictionary classification adapter passes on the pin.

**Deliverables:** pure lookup/matching checks and executable streaming, recovery,
redirect, and pipeline tests. No general value representation or extraction.

| Task / tests to write first | Intended RED | Minimum GREEN | Refactoring opportunity |
| --- | --- | --- | --- |
| M3-01 (P): a validated object with `status:"failed"` matches literal text `failed`. | Expected match is false or lookup is absent. | Decode top-level string-or-other dictionary entries and perform exact lookup. | Encapsulate the small adapter; avoid a DOM/scanner. |
| M3-02 (P): missing/non-string fields and every non-object value are non-matches, including huge valid numbers. | Type coercion, match, or error where a non-match is required. | Skip non-strings and validated non-objects without numeric conversion. | Distinguish non-match from unexpected decoder failure. |
| M3-03 (P): case, whitespace, Unicode normalization differences, quotes/backslashes, and decoded JSON escapes obey exact string comparison. | A coerced/normalized value matches or equivalent decoded escapes fail. | Compare decoded strings against unchanged TEXT from CLI parsing. | Keep shell processing out of matching. |
| M3-04 (P): empty/Unicode/space/dotted/bracket keys are literal; `=x`, `a=`, and `a=x=y` preserve first-`=` semantics. | Nested-path interpretation, unwanted trimming, or split of the RHS. | Use parsed literal key/text with dictionary lookup; no query syntax. | Share parser operands already covered in M1. |
| M3-05 (P): last decoded duplicate key wins, including string→null/number and number→string. | Earlier string wins or escaped aliases are treated differently. | Rely on the verified dictionary overwrite behavior and classification result. | Keep duplicate handling in existing JSON facilities. |
| M3-06 (I): selected records keep exact body bytes, whitespace, escapes, nested data, and huge numbers; only CRLF/final terminators change to LF. | Reserialization, headers, precision loss, or missing final LF. | Write validated original matching bodies plus LF as they arrive. | Keep parsing for decisions separate from output bytes. |
| M3-07 (P/I; advanced read-fault I best effort): executable tests cover no matches exiting 0 and malformed records before/after matches yielding 4. Pure production transitions cover read failure preserving only an emitted valid prefix and exiting 3; attempt real injection via S-IO. | Early termination, invalid record leakage, lost prefix, or wrong status. | Continue through EOF, share diagnostic caps, and preserve failure precedence. Record any unverified injected scenario. | Reuse M2 error/EOF transitions. |
| M3-08 (I): real filter→jlog-count pipeline and redirected file contain only valid JSONL; upstream malformed exit is checked independently and source hashes stay unchanged. | Polluted data, incorrect downstream count, changed input, or upstream failure mistaken for success. | Connect the existing commands without special pipeline behavior. | Simplify harness descriptor cleanup; keep both stderr streams separate. |

**Verification:** P on JSON lookup/matching and I on filtering, source parity,
pipeline/redirect, and read-only input; mandatory P on prefix-failure transitions,
with injected read-fault I best effort. Run V and optimized suite.
Verify the representative fixture selects original lines 2 and 3, with empty
stderr and status 0; verify raw numeric spellings survive unchanged in output.

**Definition of Done:** matching is exact and string-only, literal/duplicate keys
work, non-objects remain valid non-matches, and matching output is byte-preserved
JSONL. Every line is validated, including after matches. All malformed and I/O
paths share the approved contracts. `--field` remains rejected with exit 2.

## M4 — Release readiness

**Objective:** evidence-backed public release on native macOS ARM64 and Linux
x86-64. **Complexity: medium to high**, depending on native CI availability.

**Deliverables:** complete regressions, recorded resource measurements, README,
build/install/contribution guidance, chosen license/notices, pinned CI, and tested
archives/checksums. **Dependencies:** M1–M3 complete; native runners and exact
compiler archives available. Documentation/packaging work follows test-first
executable acceptance checks; verification-only work must not fabricate RED.

| Task / tests to write first | Intended RED / observation | Minimum GREEN or completion | Refactoring opportunity |
| --- | --- | --- | --- |
| M4-01: close the traceability matrix with P/I regressions and exact published examples across all modes/sources. | Any previously uncovered contract case fails; already-passing additions are recorded coverage-only. | Fix only the exposed behavior through its own RED/GREEN cycle. | Remove duplicated expectations/setup without losing assertions. |
| M4-02: measure optimized runs with 100,000/1,000,000 roughly-1-KiB records, a single 8-MiB line, all-invalid data, and varying tail N. | Record baseline first. Growth with total file size at fixed line size/N, per-record O(N) work, unbounded diagnostics, or stack failure violates the requirements. | If a violation exists, introduce a focused regression, then minimally correct retention/scaling; otherwise make no optimization change. Record bytes, maximum line size, N, machine, time, peak RSS, statuses, and exact results. | Remove accidental retained snapshots/slices; no concurrency or speculative tuning. |
| M4-03: execute the entire check/build/test sequence natively on each required architecture and automate it in CI. | Actual native workflow commands fail for missing/wrong pins, platform incompatibility, or test failures; absent setup is not application RED. | Confirm runner architecture/assets, pin setup action/compiler/platform, then run P/I/V and optimized tests in CI. Stop rather than substitute another nightly. | Cache by compiler/platform identity, avoiding hidden version drift. |
| M4-04: execute README usage and source-build/install instructions against the actual binary in a clean temporary location. | Documented commands/options/results disagree or installation instructions cannot produce the binary. | Write accurate reduced-scope usage, exit/partial-output/pipefail guidance, prerequisites, pins, and measured platform support. | Keep documentation concise; update stale `AGENTS.md` layout/commands and add a short contribution guide. |
| M4-05: fresh release archive passes install/run/help/version/filter→count/offline checks with Roc absent from the test environment. | Missing/mispackaged executable, wrong architecture/permissions, runtime dependency, or bad checksums fails the smoke test. | Package the tested optimized binary, chosen license and required notices, checksums, and instructions. Verify input hashes/read-only behavior and no runtime downloads. | Reuse the tested build artifact; avoid a second untested release build. |
| M4-06: audit completion evidence, supported OS versions, licenses/notices, scope, and release manifest. | Missing required evidence or failed acceptance blocks release; review-only gaps are not application RED. | Resolve each gap without weakening requirements. Recommend MIT for project code, confirm ownership/copyright before publishing, and preserve dependency terms. | Remove stale five-command guidance and unnecessary packaging/framework dependencies. |

**Verification:** use V and the optimized suite on native macOS ARM64 and Linux
x86-64, then rerun archive smoke checks on those actual artifacts. Build with
`roc build --opt=speed --target=arm64mac --output=dist/jlog src/main.roc` on macOS and
`--target=x64musl` on Linux. Do not execute these two output commands concurrently
in a shared directory. Cross-build success alone never satisfies native tests.
Record resource measurements with host tools such as macOS `/usr/bin/time -l`
and Linux `/usr/bin/time -v`; verify tool availability/output before relying on it.
Set no invented throughput promise or absolute RSS threshold after seeing results.

**Definition of Done / final release checklist:**

- [ ] Mandatory coverage in every v0.1 traceability row executes and passes on
  both native targets, including normal file/permission errors, output failures,
  and pure read-error transitions; no silent skips or probe-only success claims.
- [ ] Advanced mid-stream read-failure injection is attempted best effort;
  unverified scenarios are documented and are not unconditional release blockers.
  Known production error-handling defects remain blockers.
- [ ] Every production task has RED, GREEN, regression, refactor, and verification
  evidence; preexisting failures and actual blockers are accounted for.
- [ ] `roc check`, `roc test`, optimized tests, formatting, and executable suites
  pass with the pinned compiler/platform; help/version and scope are consistent.
- [ ] Incremental operation, bounded diagnostics/tail, record order, numeric byte
  fidelity, and measured memory/stack/scaling behavior satisfy the specification.
- [ ] Native architecture and supported OS versions are recorded; no unsupported
  platform, generic speed claim, or unverified dependency is advertised.
- [ ] README, source-build/install/contribution guidance, license/notices,
  checksums, and CI describe the tested artifacts and reduced scope accurately.
- [ ] Clean offline archive smoke tests pass without Roc; source inputs are
  unchanged; no compiler caches, huge fixtures, or unintended build artifacts ship.
- [ ] All deferred field-extraction requirements remain in v0.2, outside v0.1
  implementation and release tests. Publishing is a separate authorized action.

## Requirement and acceptance traceability

These references name specification sections and matrix cases, not claims of
completed tests. P/I indicate pure and executable coverage. M4-01 reruns every
behavioral row's mandatory coverage on both platforms; only deterministic
mid-stream read-failure injection is advanced, best-effort verification.

| Specification requirement / acceptance case | First owning tasks and coverage |
| --- | --- |
| §1 goals and reduced scope; §8 non-goals | M1-04 (P/I unsupported flags including `--field`); M4-04/06 usage and scope/dependency review. Structural exclusions such as “no plugin architecture” require review, not artificial behavior tests. |
| §2 filename/default/stdin/`-`/`./-`, one input, arbitrary extensions | M1-02 (P), M1-16/17 (I). |
| §2 option order, `--`, equals/spaced operands, dash operands | M1-03/04 (P), M1-18 and M2-06 (I). |
| §2 unknown/repeated/incompatible flags, missing operands, UTF-8 option text/native path bytes | M1-04/05 (P), M1-16/18 (I). |
| §2 help/version/aliases/standalone forms and no I/O before preflight | M1-01/06/18 (P/I). |
| §3 all value kinds, JSON whitespace, blank/malformed input | M1-09/12/13 (P); M1-16/17, M2-03/06, M3-07 (I). |
| §3 UTF-8, BOM/U+FEFF, escapes, Unicode/surrogates, error priority | M1-10/12/13 (P), M1-16/17 (I), M3-03/06/07 (P/I). |
| §3 LF/CRLF/lone CR, physical numbering, final line, no phantom record | M1-07/08/14 (P), M1-16/17 and M2-06 (I). |
| §3 depth 128/129; huge/exact number syntax without finite conversion | M1-11/12 (P), M2-03/06 and M3-02/06 (I/P); M4-02 measures large lines. |
| §3 duplicate decoded keys; no coercion/normalization | M3-02/03/05 (P), M3-06/07 (I). |
| §4 inspection; §7 representative/malformed reports | M1-14/15 (P), M1-16/17 (I). |
| §4 count; §7 representative/malformed counts | M2-01/03 (P/I). |
| §4 tail, fewer than N, zero/max/invalid N, full validation | M1-04, M2-04/05/06 (P/I). |
| §4 where first `=`, literal empty text/key, case-sensitive decoded strings, unsupported equals in keys | M1-03/04 and M3-01/03/04 (P); M3-06/07 (I). |
| §4 missing/non-string/non-object non-matches and duplicate overwrite | M3-02/05 (P), M3-07 (I). |
| §5 stdout/stderr separation, no colors/decorations, LF and raw bodies | M1-01/06/15/16/17, M2-02/03/06, M3-06/08 (P/I byte assertions). |
| §5 100-details cap, suppressed count, stable reasons, source escaping, no raw-record leakage | M1-10/11/13/14/15, M2-02, M3-07 (P/I); M4-02 stress. |
| §5 exits 0/1/2/3/4, failure precedence, no deferred result, streaming prefix | M1-04/16/18, M2-07/08/09/10, M3-07/08 (P/I). Read-error transitions require P; injected mid-stream I is advanced best effort. |
| §5 pipelines, partial write limitation, normal OS signals | M2-10 and M3-08 (I); M4-04 docs. Do not convert signal termination or a truncated failed write into a success claim. |
| §6 one-line memory, bounded retained bytes/tail, linear work, no total-size cap | M1-07/08/14 and M2-04/05 (P); M4-02 actual RSS/time measurements. |
| §6 read-only input, offline runtime, required native targets/no Roc runtime | M3-08 and M4-03/05 (I), M4-06 review. |
| §7 Empty / one-record input | M1-07/15/16/17; M2-03/04/06; M3-07 (P/I). |
| §7 Nested objects, mixed arrays, all scalars | M1-11/12; M2-03/06; M3-02/06 (P/I). |
| §7 Escapes and Unicode | M1-08/10/12/13; M3-03/04/05/06 (P/I). |
| §7 Whitespace / CRLF; Invalid grammar; UTF-8 / BOM / surrogate / depth | M1-07..13 and M1-16/17; reused by M2-03/06 and M3-07. |
| §7 Missing / mixed field types; Literal / duplicate keys; Literal filter operands | M1-03/04, M3-01..05 and M3-06/07 (P/I). |
| §7 Tail boundaries; Many invalid lines | M1-14/15, M2-02/04/05/06, M3-07 (P/I). |
| §7 Missing / unreadable / directory source; Mid-read / write failure | M1-16, M2-07..10, M3-07 (P/I); S-IO. Normal file/output failure I and production read-error transition P are mandatory; injected mid-stream I is advanced best effort. |
| §7 CLI validation; Help / version | M1-01..06/18 and M2-06 (P/I). |
| §7 Stdin parity; Pipeline safety | M1-07/08/17, M2-03/06/09, M3-06/07/08 (P/I). |
| §7 Large input; §10 release gates | M4-01..06 and the final checklist. |
| §9 deferred `--field` requirements | Retained v0.2 backlog; deliberately no v0.1 implementation task. |

**Uncovered v0.1 behavioral requirements:** none in planned ownership. All tasks
are initially unexecuted. Structural scope and legal/notices checks are explicit
reviews, not automated proof. Tail allocation behavior, runner availability,
measurements, and OS support remain unverified until their gates run. Advanced
mid-stream fault injection may remain explicitly unverified at release; this
does not waive production handling or mandatory unit/integration coverage.

## Focused spikes and remaining risks

Spikes are bounded compatibility investigations before dependent implementation,
not invitations to expand scope. Record source, command, result, and limitations.
Any resulting production fix still requires its own RED/GREEN cycle.

- **S-IO, before M2-09/10:** verify normal file errors and actual output failures;
  these remain mandatory. Make a bounded, best-effort attempt at deterministic
  mid-stream read-failure injection, without custom platform/FFI machinery. Candidate:
  prefill an OS pipe, keep its writer open, set its read descriptor nonblocking
  with Python stdlib, and use that descriptor as the child's stdin. Verify the
  platform propagates `WouldBlock` after the prefix rather than treating it as
  EOF or retrying forever. For write faults, close all pipe readers before
  launching the child with the write end as stdout. These mechanisms are not yet
  verified on either required native host. If the read fixture is unsuitable,
  record the attempt and unverified scenario; another simple OS fixture may be
  tried, but injector availability does not block release. Do not accept a timeout
  or substitute Python logic for the binary. Mandatory pure tests exercise the
  production read-error transitions, not a duplicate Python reducer. Keep any
  reproducible executable fault test as regression coverage. Actual output-failure
  evidence remains a release gate.
- **S-tail, before M2-05:** check the chosen builtin list/ring operations, grow-as-
  needed capacity, retained byte ownership, and unique accumulator updates with
  a small compiled probe. Avoid accidental O(N) rebuilding and retention of old
  states. Do not infer O(1) updates solely from a passing ordering test; M4 measures
  scaling and RSS using the actual executable.
- **S-native, before M4-03:** verify exact compiler archive availability, setup
  action pin, runner architecture, and platform cache/build on native Linux and
  macOS. macOS execution and Linux cross-build probes already exist; native Linux
  application execution remains unverified. No platform migration is authorized.
- **Compiler/API risk:** reproduce the record-based string classification adapter
  rather than the earlier exploratory crashing union design. Keep the JSON/depth
  probes available for regressions, but write application expectations first.
  Stop dependent work on a crash or unexpected decode failure.
- **Resource and release risk:** a single large line needs proportional memory;
  OS OOM termination cannot promise a diagnostic. License choice, dependency
  notices, minimum OS versions, and packaging requirements must be resolved from
  actual artifacts before release. No speculative optimizations or benchmarks are
  part of M1–M3.

Stop after creating and reviewing this plan. Application implementation, fixtures,
CI configuration, and release actions require the subsequent execution task.
