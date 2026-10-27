# M4-01 contract and coverage audit

Audit date: 2026-10-27. Application baseline: `d1a0d20` (M3). Host: native
macOS ARM64; Roc `nightly-2026-10-09-258ab27`, basic-cli 0.25.0. The user
authorized starting M4 with this audit. No application source or pin changed.

The native macOS coverage audit has executed; **M4-01 is still open**. Strict
descriptor conformance fails and the required native Linux execution has not
run. Passing ordinary error fixtures does not close those release gates.

## Coverage added

Eleven `test_m4_01_*` methods in [the executable suite](../../tests/test_cli.py)
close coverage gaps with hand-specified byte/status expectations:

- Exact representative and malformed fixtures from specification §7, across
  all four modes, file argument positions, implicit stdin, and explicit `-`.
- Shared validation/recovery, physical numbering, defect precedence, depth
  boundaries, surrogate escapes, and huge numbers in every operation callback.
- Long UTF-8 filter/count/tail records spanning stdin reads, CRLF, and a final
  unterminated body containing a lone CR. These are transport checks; large-file
  memory/time measurements still belong to M4-02.
- Escaped source labels and absence of malformed record contents in data stderr.
- Literal `./-` and option-like filenames, arbitrary extensions, dash-leading
  filter operands, and rejected arguments while stdin remains held open.
- Redirected tail/filter data from malformed sources, independently parsed with
  exact integers and `decimal.Decimal`, alongside authoritative byte assertions
  and unchanged source hashes.
- Normal SIGTERM termination after observing a live filter prefix.
- README sample count, exact tail bodies, and progress output.
- Real mid-stream read failure from a prefilled nonblocking pipe whose writer
  remains open. It covers inspect/progress/count/tail 0/tail 2/filter, including
  an incomplete final body that must never be flushed as EOF.

The existing redirected-filter parser oracle also uses `Decimal` for huge
exponents rather than a floating-point conversion. The shared test helper only
runs source variants, substitutes a display label in supplied expectations, and
checks source hashes; it does not implement framing, filtering, or tail logic.

All eleven ordinary coverage additions pass against the existing implementation.
The strict descriptor gate below remains failing. One initial usage-hint
expectation omitted the existing `Try ... --help` line; the test fixture was
corrected to include the existing short hint. This was a test-authoring error,
not production RED. No production behavior was rewritten to create a RED cycle.

## Executed traceability

The following groups cover the behavioral rows in the
[plan matrix](jlog-v0.1-plan.md#requirement-and-acceptance-traceability). `P` means
inline Roc checks; method names refer to the executable suite unless stated.

| Specification / matrix cases | Executed coverage | Native macOS status |
| --- | --- | --- |
| §1/§8 reduced scope, unsupported flags and `--field` | CLI P; `m1_06_usage_regressions`, `m4_01_usage_does_not_read_stdin`; source/import review. | Pass; no field extraction, custom parser, runtime network use, or new dependency added. |
| §2 one input/default/`-`/`./-`, option order, terminator, arbitrary extensions and operands | CLI P; `m1_18_*`; `m4_01_literal_paths_and_dash_operand`; both `m4_01_published_*` methods. | Pass. |
| §2 UTF-8 arguments and native path preservation | CLI P; `m1_05_invalid_utf8_text_regressions`, `m1_16_native_path_bytes`, `m1_16_non_utf8_native_path`. | Supported UTF-8 native paths pass; Darwin rejects creation of raw invalid-UTF-8 names. Successful raw-name opening must run on Linux. |
| §2 help/version/aliases, standalone forms, parse before effects | CLI P; `m1_01_*`, `m1_06_*`, `m1_18_*`, `m4_01_usage_does_not_read_stdin`. | Pass for usable output; see descriptor gate below. |
| §3 all JSON kinds, whitespace, grammar, UTF-8/BOM, escapes/surrogates, depth and diagnostic priority | JSONL P; `m1_16_defects_and_recovery`, `m1_17_stdin_validation`, `m3_07_filter_defects_recovery_and_cap`, `m4_01_validation_precedence_all_modes`. | Pass. |
| §3 LF/CRLF/lone CR, physical lines, final bytes, no phantom record | Framer P including every split; `m1_16_crlf_and_numbering`, `m1_17_stdin_records_and_eof`, `m4_01_long_records_data_modes`. | Pass across both sources and all consumers. |
| §3/§4 huge numbers, duplicates, literal keys, exact strings and no coercion/normalization | JSONL/CLI P; `m3_06_*`, `m3_07_filter_no_matches`, `m4_01_validation_precedence_all_modes`, redirected-data tests. | Pass; raw numeric spellings survive. |
| §4/§7 inspect/count/tail/filter, representative and malformed output | Operations P; M1/M2/M3 executable groups; `m4_01_published_representative_all_modes`, `m4_01_published_malformed_all_modes`. | Pass, including no matches with status 0 and malformed recovery with status 4. |
| §4/§7 tail N=0/1/max, fewer-than-N, leading zeros, rejection boundaries, full validation | CLI/tail P; `m2_06_*`, `m4_01_usage_does_not_read_stdin`, `m4_01_validation_precedence_all_modes`. | Pass; resource scaling is still M4-02. |
| §5 stdout/stderr separation, original bodies, LF, capped details, omitted count and safe labels | Renderer P; `m1_16_first_100_errors`, `m1_17_stdin_error_cap`, `m2_03_count_values_and_error_cap`, `m3_07_*`, `m4_01_data_diagnostics_escape_source`. | Pass. |
| §5 progress modifier and completion | CLI/progress P; `test_progress_*`; `m4_01_readme_sample`. | Pass for timing, live output, quiet data modes, read-error suppression and redirected text. |
| §5 exits 0/1/2/3/4, counter exhaustion, EOF/read error and output failures | Operations/framer P; `m2_08_*`, `m2_09_*`, `m2_10_*`, `m3_07_filter_diagnostic_failure_keeps_emitted_prefix`. | Reported errors pass; strict descriptor errors fail in the separate conformance suite. |
| §5 mid-stream read failure after emitted prefix | Production-transition P; `m4_01_mid_read_failure_all_modes` with an actual nonblocking pipe. | Pass: I/O status 3 overrides malformed status, deferred modes emit nothing, filtering retains only its complete valid prefix. The parent independently confirms the pipe was drained and still reports WouldBlock rather than EOF. Native Linux remains pending. |
| §5/§7 pipeline safety, redirects and normal signals | `m3_08_*`, `m4_01_redirected_data_with_malformed_source`, `m4_01_sigterm_preserves_normal_termination`. | Pass; upstream/downstream statuses checked independently; signal status remains negative SIGTERM. |
| §6/§7 incremental memory, bounded diagnostics/tail, long lines, linear work | State/boundary P and long-line executable tests; source review. | Functional checks pass; RSS/time/stack/scaling measurements remain M4-02. No performance conclusion inferred. |
| §6 read-only input, runtime independence and native support | SHA-256/byte assertions in M3/M4 executable tests; static imports/effect review. | Source preservation passes. Native Linux, clean offline archives, OS minimums and runtime isolation remain M4-03/05/06. |
| §7 exact published examples | `m4_01_published_*`, `m4_01_readme_sample`; README big-sample filter→count smoke check. | Pass on this host; build/install instructions are still M4-04. |
| §9 deferred extraction; §10 release gates | Unsupported-flag tests and scope review; this audit and remaining M4 tasks. | `--field` still exits 2; release is not complete. |

## Strict I/O gate

[test_io_contract.py](../../tests/test_io_contract.py) asserts the original exit-3
contract for write-only stdin and read-only stdout/stderr. Three methods currently
fail with 15 failing subcases. This is separate from the ordinary suite so its
known failure is explicit in focused development runs; **both suites must pass
for release**. Unrestricted `unittest discover` will include the failing gate.
There are no expected-failure annotations, skips, or substituted success codes.

An independent pinned platform probe returns `Err(EndOfFile)` for unreadable stdin
and `Ok({})` for unwritable stdout/stderr. Public API inspection found no standard-
descriptor validation or explicit flush hook. See the complete
[reproducer](../repros/stdio-descriptor-errors.md). The application cannot infer
the missing error from these returned values. A platform correction needs a
separate tested change; the pin, FFI boundary, and contract were preserved.

## Verification and remaining gates

Exact final commands/results are recorded in the
[progress log](jlog-v0.1-progress.md#m4-01-coverage-audit--authorized-2026-10-27).
Native Linux has not run; a cross-build would not satisfy that requirement.
Measurements, native CI, installation/release packaging, license/notices and
supported OS versions remain M4-02 through M4-06. No release was published.

Subsequent update: the user authorized M4-02 next. Native macOS resource
measurements are now [recorded](../measurements/m4-02-macos-arm64.md); they do not
close the strict descriptor or native Linux gates described above.

The later [Linux ARM64 Docker run](../measurements/m4-02-linux-arm64-docker.md)
passes all 63 ordinary executable methods on both builds, including actual raw
invalid-UTF-8 filename opening and prefix read failures. Strict descriptor checks
still fail 15 subcases per build. This supplemental guest architecture does not
close the required native x86-64 gate.

The subsequent [native CI run](m4-03-native-ci.md) executes the entire sequence
on Linux x86-64 and macOS ARM64. Each build passes 273 pure checks and 63 ordinary
executable methods without skips; each architecture passes 70 resource cases.
Successful raw-name opening and actual mid-stream WouldBlock are now verified
on the required Linux target. Strict descriptor checks still fail the same 15
subcases per build on both hosts, so M4-01/full native conformance remains open.
