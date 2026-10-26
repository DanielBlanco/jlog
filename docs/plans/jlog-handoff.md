# jlog development handoff

Snapshot: 2026-10-18, native macOS ARM64. Development is paused.

Layout update (2026-10-26): application modules and their inline checks now live
in `src/`; the entry point is `src/main.roc`. Plans and the specification live
in `docs/plans/` and `docs/specs/`. Historical verification commands below retain
the paths used when executed. For current build/test commands, see the
[README](../../README.md#for-developers). This move adds no milestone behavior.

## Current project status

**M1-A and M1-B are already implemented and verified.** The handoff request's
expected next checkpoint, M1-B, is stale for this checkout. Preserve the existing
implementation; do not restart those tasks or manufacture failing tests. The
first unimplemented task is **M2-01**, which needs separate authorization. The
resume prompt below deliberately stays within M1-B verification and genuine gaps.

`jlog` is a small Unix JSONL explorer for inspection/validation, count, tail, and
top-level string-only equality filtering, with one file or stdin input. It is a
learning project, not a jq replacement. `--field` is deferred to v0.2.

- Branch: `master`.
- HEAD: `1d21676cdfb0b7de87dfde38038c9fee98625181` —
  `Add jlog inspection CLI, tests, and project documentation`.
- Working tree was clean before this handoff. Handoff-only changes: modified
  `AGENTS.md`; new/untracked `plans/jlog-handoff.md`; nothing staged. No application
  source, test, specification, plan, or progress-log changes. `dist/jlog` is ignored
  and was rebuilt; the final artifact is optimized. No commit/push/PR was made.
- Compiler: Roc `nightly-2026-10-09-258ab27`, currently
  `/Users/dblanco/.local/roc/roc` (`command -v roc` and `roc version` checked).
- Platform: `basic-cli` 0.25.0, pinned in `main.roc` to
  `https://github.com/roc-lang/basic-cli/releases/download/0.25.0/CZsY7tYZwR3rj9kYbpaCfxki2yVAaRL8bBwMLvB2xkbA.tar.zst`.

Read the [specification](../specs/jlog-v0.1.md), [implementation plan](jlog-v0.1-plan.md),
[progress record](jlog-v0.1-progress.md), and [feasibility report](../roc-feasibility.md).
Their initial-checkout statements are historical: application sources/tests and
Git now exist, the compiler is outside the checkout, and `main.roc` is no longer
the file-size example. `.tool-versions` pins Node, not Roc; Node is not needed.
The added status section in `AGENTS.md` points here without replacing its guidance.

## Completed work

### M1-A — M1-01 through M1-08

| Task | Implemented behavior |
| --- | --- |
| M1-01 | `--version` / `-V`: exact `jlog 0.1.0\n`, empty stderr, exit 0. |
| M1-02 | Default inspection; filename, implicit stdin, `-`, and literal `./-` selection. |
| M1-03 | Options before/after input, spaced/equals operands, `--`, dash-leading operands, first-`=` filter splitting. |
| M1-04 | One input/operation; reject unknown/repeated/incompatible flags, missing operands, invalid N and filter syntax. N accepts ASCII digits, 0..4294967295. |
| M1-05 | Strict UTF-8 option text via `OsStr.to_str_try`; retain native path representation. |
| M1-06 | Standalone help/aliases, usage errors on stderr with exit 2; parse before effects. |
| M1-07 | Pure numbered physical-line framing, blank physical lines, LF/EOF, final unterminated line, no phantom trailing record. |
| M1-08 | Split CRLF/Unicode/chunks; strip CR only before LF and retain lone CR. |

### M1-B — M1-09 through M1-18

These capabilities are implemented, not placeholders:

| Tasks | Current implementation and acceptance coverage |
| --- | --- |
| M1-09/10 | JSON-whitespace-only lines invalid; strict record UTF-8; initial first-line BOM rejection; diagnostic precedence and U+FEFF handling. |
| M1-11..13 | Quote/escape-aware depth-128 resource precheck, followed by builtin JSON grammar validation through the skip-only `AnyJson.parser_for` adapter. All value kinds, Unicode/surrogates, huge integers/exponents, malformed grammar and recovery tested. No numeric conversion or custom parser. |
| M1-14/15 | Pure inspection totals, physical line references, first 100 error details plus omitted count, exact reports and escaped source controls. |
| M1-16/17 | Buffered file and raw incremental stdin reads through the same framer/consumer; EOF-only report; propagated read errors yield exit 3 without a completed report. Empty/malformed/CRLF/final/long lines and file/stdin parity tested. |
| M1-18 | Executable preflight with stdin held open and inaccessible paths. Already satisfied by M1-A; recorded as inherited coverage, not invented RED. |

`src/Cli.roc` owns pure arguments/help; `src/Jsonl.roc` owns pure framing/classification/
depth/JSON validation; `src/Operations.roc` owns pure bounded summaries/rendering.
`src/main.roc` owns effects, native paths, shared reader loop, EOF/error normalization,
stdout/stderr, and exits. It uses `File.open_reader!`, `Reader.read_line!`, and
`Stdin.bytes!`. The Python stdlib harness executes the supplied binary and asserts
bytes/statuses; it never builds implicitly or reproduces application logic.

Inspection exits 0 for valid/empty input or 4 for malformed records, continuing
through EOF. Malformed details belong in the stdout report, not duplicated on
stderr. Native path display is separate from opening the original native path.

## Verification state

**Fresh handoff checks**, executed from repository root on 2026-10-18; every
command below exited 0. These results are separate from historical TDD evidence
in the progress log. Both integration runs included real unprivileged permission
tests and had zero failures, errors, or skips.

| Exact command | Fresh result |
| --- | --- |
| `env ROC_CACHE_DIR=/private/tmp/jlog-research/cache roc check main.roc` | No errors. |
| `roc fmt --check main.roc Cli.roc Jsonl.roc Operations.roc` | All formatting valid. |
| `env ROC_CACHE_DIR=/private/tmp/jlog-research/cache roc test --opt=dev --no-cache main.roc` | 182 passed, 0 failed. |
| `env ROC_CACHE_DIR=/private/tmp/jlog-research/cache roc build --opt=dev --output=dist/jlog main.roc` | Built; 0 errors/warnings. |
| `env PYTHONDONTWRITEBYTECODE=1 JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v` | Dev binary: 26 methods passed. |
| `env ROC_CACHE_DIR=/private/tmp/jlog-research/cache roc test --opt=speed --no-cache main.roc` | 182 passed, 0 failed. |
| `env ROC_CACHE_DIR=/private/tmp/jlog-research/cache roc build --opt=speed --output=dist/jlog main.roc` | Built; 0 errors/warnings. |
| `env PYTHONDONTWRITEBYTECODE=1 JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v` | Optimized binary: 26 methods passed. |

There are 67 CLI, 97 framing/classification/JSON, and 18 inspection/rendering
`expect`s. The original 85 M1-A checks and seven executable tests remain included.
Module-focused checks can use `roc test --main=src/main.roc src/Jsonl.roc` (or the owning
module); this toolchain may include all modules reached through the main context.
Do not add repeated run counts as distinct tests.

The writable cache above already contained the pinned packages. Its location and
temporary logs under `/private/tmp/jlog-handoff-759trpna` are machine-local, not
required repository assets. If absent, establish a writable `ROC_CACHE_DIR` and
obtain the exact pinned packages through normal compiler downloads or an existing
cache; investigate cache/download failures rather than changing pins. The default
cache write failure and original formatting failure are historical; neither was
reintroduced here. `roc fmt --help` freshly confirms `--check` and path arguments;
continue using explicit existing project paths rather than recursive `.`.

## Remaining work

No M1-B feature is awaiting its initial implementation on this HEAD. Resume its
verification/reconciliation only if instructed; preserve the coverage above.

- **M2 pending:** next unimplemented task is **M2-01**, pure valid-record count
  rendering after EOF. Then data diagnostics, executable count, bounded tail,
  error precedence, detected resource/counter exhaustion and output failures.
- **M3 pending:** top-level string-only filtering, duplicate-key/non-object
  handling, original-record output and executable pipeline acceptance.
- **M4 pending:** full release matrix, large-file RSS/time/stack measurements,
  native macOS ARM64/Linux x86-64 verification, README/build/install/contribution
  guidance, license/notices, CI, packaging and offline archive checks.

The plan/specification and historical RED evidence remain unchanged. Starting M2
requires a separate instruction; this handoff does not authorize it.

## Known limitations and risks

- Fresh smoke checks confirm `--count`, `--tail 1`, and `--where status=failed`
  remain parsing-only: empty stdout, `jlog: data operations are not implemented
  yet` on stderr, exit 1. Help describes the intended release, not full completion.
  `--field skill` freshly returns usage exit 2; extraction remains v0.2.
- **Known stdin gap, freshly reproduced:** passing a write-only pipe descriptor
  as stdin yields an empty inspection report/status 0. Historical independent Roc
  probes showed the pinned platform exposes this as EOF, unlike Python's EBADF.
  `Stdin.bytes!` cannot distinguish it from real EOF. Do not advertise all invalid
  descriptors as detected or silently weaken the exit-3 contract. The progress
  log includes a reproducer. Directory stdin does propagate a read error and its
  no-report/exit-3 integration test freshly passes. Review the gap before release;
  no custom platform/FFI or toolchain upgrade is authorized by this handoff.
- Darwin rejects raw invalid-UTF-8 filenames with EILSEQ; the integration suite
  covers that branch here and retains successful opening assertions for supporting
  filesystems. Pure native-byte preservation is covered. Actual successful opening
  of such a filename on Linux remains unverified.
- No current check fails. Native Linux application execution, large-file resource
  behavior, tail allocation, full output-fault coverage and packaging are not
  established by these macOS tests. U64 counter/resource exhaustion handling is
  still an M2 task. Mid-stream read-fault injection is best effort; production
  error handling and ordinary file/output failure tests remain mandatory.
- Feasibility reports record an earlier compiler crash with a different JSON
  union adapter. Preserve the successful skip adapter; M3 should use the verified
  record-based string classification approach. Retain reproducers and investigate
  compiler crashes/unsupported APIs instead of bypassing tests.

## Exact resume instructions

This prompt preserves the requested M1-B-only boundary while accounting for its
existing implementation. It does not instruct a fresh session to redo completed
work or start the next milestone:

```text
Resume jlog within M1-B (M1-09 through M1-18) ONLY.

Read AGENTS.md, docs/specs/jlog-v0.1.md, docs/plans/jlog-v0.1-plan.md,
docs/plans/jlog-v0.1-progress.md, docs/plans/jlog-handoff.md,
docs/roc-feasibility.md, src/*.roc, and tests/test_cli.py. Inspect branch, HEAD and working tree.
Preserve unrelated changes and every completed M1-A/M1-B behavior and test.

The handoff HEAD already implements M1-B. First rerun and reconcile its acceptance
coverage. If everything is present, record fresh verification and STOP; do not
reimplement tasks, fabricate RED, or advance to M2. Report the documented platform
limits explicitly. Do not silently alter the specification or plan.

Only if a genuine in-scope M1-B gap is demonstrated, work on ONE TDD task at a
time: RED (execute a meaningful failing assertion; test syntax/compiler errors
are not RED) -> minimum GREEN -> REFACTOR -> VERIFY. Keep evidence concise in
docs/plans/jlog-v0.1-progress.md: task ID, failing assertion/command, passing focused
and regression tests, compiler/format status and outstanding limitations.
Already-passing tests are inherited coverage; commits per cycle are not required.

Use Roc nightly-2026-10-09-258ab27 and basic-cli 0.25.0 at the pinned URL.
Reuse the pure CLI/framer, skip-only JSON adapter and depth precheck. No custom
JSON parser, platform, FFI, dependency, numeric narrowing or whole-input loading.
Investigate and report genuine blockers rather than inventing success.

Run focused tests and regressions after every GREEN and REFACTOR. Before stopping,
run roc check; development and optimized Roc tests/builds; the existing Python
executable suite against EACH binary; and roc fmt --check with explicit project
source paths. Use the README's current src/ paths with the handoff's cache
guidance. Never claim an unexecuted check passed. Preserve malformed-line recovery, physical numbering,
original bytes, first-100 diagnostics, EOF-only reporting and pipeline safety.

Do not implement --count, --tail or --where beyond existing parsing, or --field
(deferred to v0.2). Do not advance to M2. Leave the repository buildable, formatted
and tested, summarize actual results and remaining limits, then stop. Do not
commit, push or create a PR unless separately instructed.
```
