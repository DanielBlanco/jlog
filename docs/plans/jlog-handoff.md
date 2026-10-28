# jlog development handoff

Historical snapshot: 2026-10-18, native macOS ARM64. Later updates below record
the user-authorized development through M4-03 and its descriptor correction on 2026-10-27.

Latest verified checkpoint: the approved corrected platform passes native
macOS ARM64 and Linux x86-64 CI, including all 15 descriptor subcases per build
and all 70 resource cases per target. See the
[correction report](m4-03-stdio-correction.md). M4-01/02/03 are verified;
M4-04 documentation/source-build/install verification is now complete; next is
M4-05 packaging and offline archive verification (now started). Historical failures and scoped resume prompts below
remain snapshots, not current instructions to preserve the unpatched defect.

M4-05 preparation: tested-binary packaging, checksum/inventory gates, collected
notices and native offline smoke tooling are implemented. Private fixture
archives package deterministically, and all eight macOS runtime cases pass with
network/toolchain access denied. All 77 Python methods pass. The user subsequently
approved MIT, now applied in root `LICENSE`. Both native candidates are packaged;
the MIT macOS archive passes all eight local offline cases. Actual native CI
release-candidate archive evidence remains pending.
The user requested committing everything and leaving a clean working tree. See the
[preparation report](m4-05-archive-verification.md); do not mark M4-05 complete
from the fixture smoke check or publish its private test-only archives.

M4-04 preparation: documented clone instructions must select `ci/native-m4`
until the current work reaches `master`. The original default-branch clone
could not find the bootstrap, and zsh rejected the README's `status` variable.
Both documentation gaps are corrected; clean macOS source build and documented
usage/install/source checks pass. Native CI also runs the new README verifier.
See the latest progress entry for final verification and remaining release tasks.

M4-04 completion: [native run 40571638408](m4-04-docs-verification.md) passes on
both release targets. Linux verifies 16 usage/install cases; macOS verifies 19
with zsh coverage. Both execute five documented source blocks, full regressions
and all existing resource cases. Source, platform and runtime hashes are checked.
`CONTRIBUTING.md` and the README verifier are in place. Do not start license,
archive publication or minimum-OS decisions as part of this finished docs task.

Layout update (2026-10-26): application modules and their inline checks now live
in `src/`; the entry point is `src/main.roc`. Plans and the specification live
in `docs/plans/` and `docs/specs/`. Historical verification commands below retain
the paths used when executed. For current build/test commands, see the
[README](../../README.md#for-developers). This move adds no milestone behavior.

Feature update (2026-10-26): the user separately authorized `--progress` for
inspection. It emits plain stderr snapshots at most about once per second as
input advances and a final snapshot at EOF. See the
[progress specification](../specs/inspection-progress.md) and the latest progress
record for implementation/verification. Historical totals and commands below
remain snapshot evidence; count, tail, and filtering were still unimplemented
when that extension was added. The later M2 update follows.

## Current project status

Current implementation update (2026-10-26): the user authorized M2. Count and
bounded tail, capped data diagnostics, checked counters, EOF/read-failure
transitions, and actual closed-pipe error paths are implemented. See the latest
progress record for task-by-task RED/GREEN evidence and current test totals.
Write-only stdin and suppressed EBADF output errors remain unresolved platform
compatibility gaps; do not claim strict full-descriptor conformance on the
strength of ordinary I/O tests.

Later M3 update (2026-10-26): the user requested committing the existing work and
starting M3. M2/progress/fixture work was committed as `f174c25`. That explicit
authorization supersedes the earlier milestone checkpoint while leaving the M2
descriptor gate open. String-only `--where` filtering is now implemented with
original-byte streaming, capped diagnostics, and filter-to-count pipeline tests.
The latest progress record contains current verification totals and the new
[compiler declaration-order reproducer](../repros/m3-dict-parser-order.md).
The snapshot and M1-only prompt below are historical; M4 has not been started.

M4-01 update (2026-10-27): after M3 commit `d1a0d20`, the user authorized starting
the contract/coverage audit. See the [audit](m4-01-audit.md) and latest progress
record for actual test totals. The native macOS audit adds exact cross-mode
fixtures, transport/redirect checks, and explicit strict descriptor tests. The
latter still fail the specified exit-3 contract; native Linux remains pending.
A prefilled nonblocking pipe now establishes a real mid-stream read failure
after a consumed prefix: deferred modes emit no result and filtering keeps only
its complete valid prefix, with status 3. Earlier pseudo-terminal observations
remain historical evidence and are not mistaken for injected read failures.
Do not mark M4-01 or release readiness complete from the ordinary passing suite.
No platform/pin/FFI/dependency change or release publication was made.

M4-02 update (2026-10-27): after audit commit `816f65c`, the user requested the
next task. Optimized native macOS resource measurements now cover 100,000 and
1,000,000 roughly-1-KiB records, all-invalid equivalents, 1 MiB/8 MiB lines,
varying tail N, and a 4,000,000-record fixed-N follow-up. All 74 measured cases
have exact output/status/hash verification. See the
[report and JSON artifact](../measurements/m4-02-macos-arm64.md). No measured
scaling/retention/stack failure required an application change. The strict
descriptor and native Linux gates remain open; these observations do not
establish full release readiness. The initial driver supported native macOS.

Linux Docker update (2026-10-27): the user requested Linux resources using Docker.
The local engine is ARM64, so the explicitly stated default collects native
ARM64 guest execution while preserving the required x86-64 gate. A SHA-pinned
Debian/compiler image runs as UID 1000 with read-only sources and Linux-local
temporary data. Both dev and speed pass 273 pure checks and 63 ordinary CLI
methods; the strict descriptor gate still fails 15 subcases per build. All 70
Linux resource cases pass, with identical fixture hashes to macOS and unchanged
input/binary hashes. See the
[Linux ARM64 report](../measurements/m4-02-linux-arm64-docker.md) and
[Docker workflow](../../tests/docker/README.md). The driver now supports GNU time
and records container provenance; no application or pin change was made.

Native CI update (2026-10-27): the user authorized M4-03 alongside the required
Linux x86-64 measurements. The [workflow](../../.github/workflows/native-ci.yml)
and [CI drivers](../../tests/ci/README.md) assert native architecture and exact
compiler checksums, run both optimization suites and the strict descriptor gate,
and retain measurement evidence even when that gate fails. Preparation alone
does not establish remote execution or complete either native release gate.

Execution follow-up: [run 40549245469](m4-03-native-ci.md) now executes on both
required native architectures at `48c9aa9` on `ci/native-m4`. Each build passes
273 pure checks and 63 ordinary CLI methods, and each architecture passes all 70
resource cases. The strict suite still fails 15 subcases per build, leaving both
CI jobs correctly red. The [native x86-64 report](../measurements/m4-02-linux-x86_64-ci.md)
closes the missing M4-02 architecture evidence; full descriptor/M4-03 conformance
and M4-04/05/06 remain open. Tested artifacts/provenance are downloaded; source,
input and binary hashes are verified. Local/remote `master` were not changed;
the prior pending measurement/docs work remains present on the CI branch.

Descriptor correction update: after receiving the failing CI output and reviewing
an isolated fix, the user approved integrating the basic-cli 0.25.0 host patch
and native verification. The original Roc pin remains mandatory. Prepare the
corrected platform with `python3 scripts/build_platform.py` before Roc commands;
see [platform prerequisites/provenance](../../platform/README.md). This approval
supersedes earlier prohibitions on a platform change for this specific patch.
Local dev/speed now pass 486 inline checks, 64 ordinary methods and all 15 strict
subcases. Native CI results are recorded in the latest progress entries; do not
infer native Linux success from the local candidate alone.

**M1-A and M1-B are already implemented and verified.** The handoff request's
expected next checkpoint, M1-B, is stale for this checkout. Preserve the existing
implementation; do not restart those tasks or manufacture failing tests. The
first unimplemented task at that snapshot was **M2-01**. The
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

## Historical remaining work (2026-10-18)

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

- At the 2026-10-18 snapshot, smoke checks confirmed `--count`, `--tail 1`, and `--where status=failed`
  remain parsing-only: empty stdout, `jlog: data operations are not implemented
  yet` on stderr, exit 1. Help describes the intended release, not full completion.
  `--field skill` returned usage exit 2; extraction remains v0.2. Later M2 work
implemented count/tail and M3 implemented filtering. See the latest progress
  record for current validation and descriptor-edge conformance gaps.
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
  established by these macOS tests. Later M2 work added checked U64 line/summary
  exhaustion and pure production read-error transitions. Advanced executable
  mid-stream read-fault injection remains unverified; production
  error handling and ordinary file/output failure tests remain mandatory.
- Feasibility reports record an earlier compiler crash with a different JSON
  union adapter. Preserve the successful skip adapter; M3 should use the verified
  record-based string classification approach. M3 exposed a separate declaration-
  order crash; keep the custom `StringField` decoder above its dictionary consumer
  and preserve its reproducer. Investigate compiler crashes/unsupported APIs
  instead of bypassing tests.

## Historical M1-only resume instructions

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
