# jlog v0.1 Specification

## 1. Summary and goals

`jlog` is a lightweight JSONL/NDJSON explorer written in Roc for developers
working with logs and record collections. It validates, counts, tails, and filters
through predictable Unix commands. Build a useful JSONL
explorer, not a replacement for `jq`.

This is the proposed implementation contract, researched on 2026-10-18. Use
Roc `nightly-2026-10-09-258ab27` and `basic-cli` 0.25.0. Feasibility probes passed
on macOS ARM64; Linux cross-compilation passed, but Linux execution remains a
release gate. No application implementation is part of this specification.

Approved reduced scope: `--field KEY` is deferred to v0.2. Inspection, counting,
tailing, and string-only filtering retain their existing contracts. All JSON
value kinds and syntactically valid huge numbers remain valid input. The depth
limit remains 128; no custom JSON parser or serializer is part of v0.1.

## 2. Commands and argument rules

```text
jlog [INPUT] [--count | --tail N | --where KEY=TEXT]
jlog --help
jlog --version
```

- One input only. A filename alone selects inspection. No input, or input `-`,
  selects stdin and reads until EOF without a prompt. Use `./-` for a file named `-`.
- Options may precede or follow the input. `--` ends option parsing, allowing
  filenames beginning with `-`. File extensions are unrestricted.
- Exactly one operation at most; operations cannot be combined or repeated.
- Accept both `--tail 10` and `--tail=10`, and equivalent forms for `--where`.
  An operand is consumed as one argument, even if it starts with `-`.
- `--field` is unsupported in v0.1 and follows the usage-error contract.
- `--help`/`-h` and `--version`/`-V` are standalone invocations. Help describes
  stdin, operations, string comparisons, malformed-input handling, and exit codes.
  Version outputs exactly `jlog 0.1.0\n` for the first release.
- Unknown options, extra inputs, missing operands, and incompatible/repeated flags
  are usage errors. Validate arguments before opening or consuming input.
- Option names and operands must be valid UTF-8. Preserve native filesystem path
  bytes; do not convert paths through a lossy display string.

Stdin belongs in v0.1: it enables pipelines and decompression by another tool.
It adds line-framing tests, but the selected platform exposes raw chunk reads.
An invocation in a terminal may wait for EOF; users can request help explicitly.

## 3. Record validity and line numbering

Follow the [JSON Lines format](https://jsonlines.org/) and
[JSON grammar in RFC 8259](https://www.rfc-editor.org/rfc/rfc8259), with the
Unicode and nesting limits below.

- Each physical line contains exactly one JSON value, allowing surrounding JSON
  whitespace. Objects, arrays, strings, numbers, booleans, and `null` are accepted.
- Use UTF-8 without a BOM. Invalid UTF-8 invalidates its physical line, without
  replacement characters or aborting subsequent lines.
  A BOM prefix on the first line receives the BOM diagnostic; U+FEFF inside a
  quoted string is ordinary content, and outside strings elsewhere is invalid JSON.
- Blank and whitespace-only lines are invalid records. Comments, trailing commas,
  extra values, and pretty-printed values spanning lines are invalid.
- LF separates physical lines; CRLF is accepted. A lone CR is whitespace, not a
  line separator. Count physical lines from 1, including invalid and blank lines.
- A nonempty final byte sequence without LF is a line. A trailing LF creates no
  additional line: zero bytes means zero records; `\n` means one invalid record;
  `{}\n\n` means one valid and one invalid record.
- Escaped newlines do not split records. Strings and keys must decode to Unicode
  scalar values: reject unpaired surrogate escapes; accept valid surrogate pairs.
- Allow at most 128 simultaneously nested objects/arrays; scalars have depth 0.
  A deeper line is invalid. This is an application limit, not a JSONL rule.
- Accept duplicate object keys; top-level lookup uses the last occurrence after
  decoding key escapes. Do not normalize Unicode or coerce value types.
- Validate number syntax without conversion to floating point. Preserve large
  integers and exponents, including syntactically valid `1e9999`.

`Records` means physical lines, and `Records = Valid + Invalid`. Every operation
validates the entire input through EOF unless an I/O or fatal error prevents it.

## 4. Functional requirements

### Inspect and validate

`jlog events.jsonl` emits this report to stdout after EOF:

```text
File: events.jsonl
Records: 4
Valid: 2
Invalid: 2

Malformed records:
  line 3: blank line
  line 4: invalid JSON
```

Use decimal integers without grouping or locale dependence. For stdin the source
label is `<stdin>`. Omit the blank separator and malformed section when there
are no invalid records. List invalid lines in ascending order, up to the first
100. If more exist, append `  ... K more invalid records`, substituting the omitted
count. Malformed-input details are part of this report; do not duplicate them on
stderr. An empty file produces zero for all three counts and succeeds.

### Count

`jlog events.jsonl --count` outputs the number of **valid records**, followed by
LF, after EOF. Invalid lines contribute zero. The count is still emitted when
malformed records exist, with diagnostics on stderr and exit 4. Consumers requiring
a wholly valid source must check the exit status. No labels or grouping separators.

### Tail

`jlog events.jsonl --tail N` emits the last N valid records in input order after
EOF. Invalid lines are skipped and reported, including invalid lines outside the
selected suffix. Fewer than N valid records emits all of them.

N must contain ASCII digits only and be in `0..4294967295`; leading zeros are
accepted. Zero emits no records but still validates the input. Negative values,
signs, decimals, empty operands, and overflow are usage errors. Allocate storage
as records arrive rather than reserving N slots immediately.

### Filter

`jlog events.jsonl --where status=failed` selects objects whose top-level `status`
value is the JSON string `"failed"`.

- Split the operand at its first `=`. Absence of `=` is a usage error. The key
  and comparison text may be empty; preserve their whitespace exactly.
- TEXT is literal text after shell processing, not a JSON literal. `code=42`
  matches `"42"`, not `42`; `active=true` matches `"true"`, not `true`.
  Quotes and backslashes in TEXT are literal characters.
- Compare decoded JSON strings exactly, case-sensitively. No numeric, boolean,
  null, array, or object comparison in v0.1; those field types do not match.
- Missing fields and non-object records do not match and are not errors.
- Keys are literal, case-sensitive names: dots, brackets, spaces, and Unicode
  have no path meaning. Quote operands containing shell metacharacters, for
  example `--where 'request.status=failed'`. A key containing `=` cannot be
  represented by this filter syntax in v0.1; there is no escape language.
- Preserve matching record bytes except the line terminator, which becomes LF.
  No matches produces empty stdout and exit 0 if the input is otherwise valid.

## 5. Output and error contracts

| Invocation | stdout | stderr |
| --- | --- | --- |
| Inspect | Human-readable report, including malformed lines | I/O/fatal errors |
| Count | One decimal integer and LF | Malformed-line and I/O/fatal diagnostics |
| Tail / filter | JSONL data only | Malformed-line and I/O/fatal diagnostics |
| Help / version | Requested information only | Empty on success |
| Usage error | Empty | Error followed by a short usage hint |

No colors, progress indicators, implicit summaries, or decorations. Successful
data output always ends each emitted record with LF. Tail and filter do not
reserialize whole records.

For data modes, report the first 100 invalid lines on stderr as
`jlog: SOURCE: line N: REASON`. After EOF, report any suppressed count as
`jlog: SOURCE: K more invalid records`. Stable reasons are `blank line`,
`invalid UTF-8`, `BOM is not allowed`, `nesting exceeds 128`, and `invalid JSON`.
For multiple defects on one line, use that order of precedence. Escape control
characters in source labels; never reproduce raw record contents in diagnostics.

| Exit | Meaning |
| --- | --- |
| 0 | Complete operation on valid input, including empty input or no matches |
| 1 | Unexpected internal failure or detected resource/counter exhaustion |
| 2 | Invalid CLI arguments |
| 3 | Input open/read error or output write error, including broken pipe |
| 4 | EOF reached with at least one invalid JSONL record |

Malformed lines do not stop processing; skip them in data output and retain exit
4. Input/output errors stop processing and take precedence over malformed input.
Diagnostics for inaccessible files identify the source and error category, such
as not found, permission denied, or directory input; OS-specific details may vary.

Inspect, count, and tail produce no result if input reading fails before EOF.
Filter may already have emitted valid records; output is not
transactional. A failed stdout write may leave a truncated last record. Exit
status must be checked before treating output as complete. Shell users should
enable `pipefail` when they need upstream failures to determine pipeline status.
Signals retain normal operating-system behavior.

## 6. Non-functional requirements

- Process incrementally. Inspection, counting, and filtering retain
  memory proportional to the largest physical line, plus fixed I/O buffers and
  at most 100 diagnostics. Avoid collecting the input or all error locations.
- Tail retains at most N valid records, plus the current line and fixed buffers.
  Its memory depends on retained bytes, not just the number of records.
- Target linear work in input bytes, plus output bytes. Tail insertion must not
  repeatedly copy or traverse all N records. Validate these properties through
  measurement; do not advertise a throughput figure before benchmarking.
- No fixed total-file size limit, compression support, or single-record size cap
  in v0.1. A single very large line still requires proportional memory. Detected
  exhaustion exits 1; an OS-level out-of-memory termination cannot be guaranteed
  to produce a diagnostic.
- Read only; never alter input. No network access at application runtime.
- Initial release targets: macOS ARM64 and Linux x86-64, conditional on executable
  tests passing on each. Linux ARM64 is an optional follow-up target. Users of
  release binaries should not need the Roc compiler or a separate language runtime.

## 7. Acceptance criteria

### Representative fixture

Given `events.jsonl`, with LF after every line and no blank lines:

```jsonl
{"status":"ok","skill":"Roc","detail":{"attempts":[1,2]}}
{"status":"failed","skill":"café\nλ"}
{"status":"failed","skill":null}
{"status":false}
42
```

All commands below have exit 0 and empty stderr. Every displayed stdout ends in LF.

| Command | Expected stdout |
| --- | --- |
| `jlog events.jsonl` | `File: events.jsonl\nRecords: 5\nValid: 5\nInvalid: 0\n` |
| `jlog events.jsonl --count` | `5\n` |
| `jlog events.jsonl --tail 2` | `{"status":false}\n42\n` |
| `jlog events.jsonl --where status=failed` | Original fixture lines 2 and 3 |
| `cat events.jsonl \| jlog --count` | `5\n` |

In the table, separator `\n` denotes an output LF. Inside a JSON string, escaped
`\n` remains two characters and does not create a physical line boundary.

### Malformed fixture

Given `mixed.jsonl` with exact bytes `{}\n\nnot-json\nnull`:

```text
$ jlog mixed.jsonl
File: mixed.jsonl
Records: 4
Valid: 2
Invalid: 2

Malformed records:
  line 2: blank line
  line 3: invalid JSON
```

Inspection exits 4 with empty stderr. Count outputs `2\n`; tail 10 outputs
`{}\nnull\n`. Both exit 4, with exactly these stderr diagnostics:

```text
jlog: mixed.jsonl: line 2: blank line
jlog: mixed.jsonl: line 3: invalid JSON
```

### Required test matrix

| Case | Observable acceptance |
| --- | --- |
| Empty / one-record input | Empty count is 0; empty data output; one record with or without final LF counts once; inspection totals agree |
| Nested objects, mixed arrays, all scalars | Valid at depth ≤128; count includes every value; filter skips non-objects |
| Escapes and Unicode | Escaped quotes, backslashes, braces/commas inside strings, newline escapes, UTF-8 text, and paired surrogate escapes survive; filter compares decoded strings |
| Whitespace / CRLF | Surrounding JSON whitespace accepted; whitespace-only line invalid; CRLF counts once; data output uses LF |
| Invalid grammar | Reject comments, trailing commas, leading-zero numbers, invalid escapes, two values on one line, truncated structures, and unescaped control characters; later valid lines still processed |
| UTF-8 / BOM / surrogate / depth | Invalid byte line does not corrupt later numbering; BOM rejected; lone surrogate rejected; depth 128 accepted, 129 invalid |
| Missing / mixed field types | Missing, null, and non-string fields do not match; numeric and string values remain distinct; filter only matches strings |
| Literal / duplicate keys | `a.b` differs from nested `a`; spaces, Unicode, empty key, and escaped key names resolve literally; last duplicate wins; equals-containing keys are not expressible by the filter syntax |
| Literal filter operands | `--where '=x'` matches empty key; `--where 'a=x=y'` compares text `x=y`; `--where 'a='` compares empty string; no `=` is usage error |
| Tail boundaries | N=0 still validates; N=1, N greater than valid count, and leading zeros work; invalid N variants exit 2 before reading input |
| Many invalid lines | 101 blank lines yields Records=101, Invalid=101, exit 4; exactly 100 line details and omitted count 1; count emits 0 |
| Missing / unreadable / directory source | Exit 3, empty stdout, source/category on stderr; permission fixture executed as an unprivileged user |
| Mid-read / write failure | Exit 3 overrides earlier malformed input; deferred modes emit no result on read failure; streaming prefix may remain |
| CLI validation | Unknown/repeated/incompatible flags, extra paths, missing operands, and invalid UTF-8 operands exit 2 with empty stdout; `--` permits dash-prefixed paths |
| Help / version | Exact version line; help covers the contract; neither reads stdin; extra arguments with either exit 2 |
| Stdin parity | Empty input, CRLF, invalid UTF-8, unterminated final line, and lines crossing chunk/Unicode boundaries behave identically to file input |
| Pipeline safety | Redirected tail/filter stdout parses one JSON value per line, including when invalid source lines cause exit 4; no diagnostics appear there |
| Large input | Compare 100,000 and 1,000,000 records of roughly 1 KiB; verify counts, selection/order, bounded RSS at fixed record size/N, and no stack growth with record count |

Pure unit checks cover argument interpretation, line classification, JSON grammar,
field lookup, string matching, tail state, and rendering. Executable integration
tests capture stdout bytes, stderr bytes, and exit status separately, including
OS errors, stdin chunk boundaries, broken pipes, and redirected output. Measure
optimized binaries for large-input tests; record machine, bytes, time, and peak
RSS. These are future acceptance tests, not claims of completed application tests.

### Milestones and test ownership

This is a short delivery sequence, not an implementation plan. Tests begin with
each milestone; M4 consolidates and reruns them rather than postponing testing.

| Milestone | Scope and required tests before completion |
| --- | --- |
| M1 | File/stdin reading, validation, and inspection. Test empty/one-record files, every JSON value kind, nesting, escapes/Unicode, whitespace/blank lines, grammar errors and recovery, UTF-8/BOM/surrogates/depth, physical numbering, CRLF/final lines, stdin chunk boundaries, capped diagnostics, inspection read errors, and baseline CLI/help/version behavior. |
| M2 | Count, tail, and error handling. Extend M1 fixtures to counts and tail; test N boundaries/overflow/zero, valid-record selection/order, malformed lines outside the suffix, diagnostic caps, missing/permission/directory errors, read/write/broken-pipe failures and precedence, argument combinations, and all applicable exit/stream contracts. Test pure error mapping for detected resource/counter exhaustion; do not deliberately exhaust the OS. |
| M3 | String-only filtering. Test missing/null/mixed types, exact string equality, unusual/empty/escaped/duplicate keys, literal operands, non-object skipping, nested values, valid huge numbers without numeric conversion, original-record byte preservation, malformed-line continuation, partial output, and pipeline-safe JSONL. No field extraction. |
| M4 | Integration tests, large-file validation, cross-platform builds, and release preparation. Run the entire matrix for all operations on both required native targets, including hostile bytes and I/O failures; measure large-file memory/time and varying-N tail, verify bounded diagnostics and stack use, and test packaged binaries without Roc installed. |

Every v0.1 row in the required test matrix remains mandatory: input/validation
rows start in M1 and are reused in M2/M3; count/tail/error cases start in M2;
string lookup cases start in M3; full-scale and cross-platform checks finish in M4.
Field extraction coverage is retained separately in the v0.2 roadmap.
Unit `expect` checks and executable stream/status checks accompany each milestone.

## 8. Explicit non-goals

No GUI/TUI, interactive exploration, query language, SQL expressions, nested-field
paths, multiple input files, remote sources/network requests, file modification,
persistent indexes/databases, plugins, continuous follow mode, multithreading, or
premature optimization. No sorting, aggregation beyond counts, typed filter
literals, automatic decompression, field extraction, or raw-string output in v0.1.

## 9. Future roadmap

### v0.2 candidate: field extraction (deferred contract)

`--field KEY` is not a v0.1 feature. Reconsider it only when a compatible API or
small abstraction can retain and encode arbitrary values without numeric loss;
do not introduce a complete parser or serialization framework to meet a date.
The following original requirements are retained for that release:

`jlog events.jsonl --field skill` emits one JSON-encoded value per object containing
the exact top-level key. Strings are quoted JSON strings with required escaping;
arrays, objects, numbers, booleans, and explicit `null` are supported. Missing
fields and non-object records emit nothing, without diagnostics. An empty key and keys containing `=`
are supported. Dots and brackets remain literal.

Emit semantically equivalent valid JSON on one physical line, followed by LF.
Whitespace, escape spelling, object member order, and number spelling may change.
Strings must retain their decoded Unicode content, arrays their order, and numbers
their exact mathematical value: rounding through `F64` is not acceptable. Objects
retain the same decoded-key/last-wins mapping, recursively. Duplicate members may
therefore be collapsed. Do not emit bare strings or placeholders for missing keys.

For example, extracting `[ 1, "\u0061" ]` may emit `[1,"a"]`. Extracting
`9007199254740993` must not emit `9007199254740992`; extracting `1e9999` must not
emit `null` or infinity. Preserving raw tokens is allowed if supported easily by
the selected APIs, but is not a reason to build a custom parser or serializer.


Deferred acceptance criteria:

- Extract strings, booleans, null, arrays, and nested objects as one JSON value
  per line; preserve decoded Unicode/escape meaning and array order.
- Missing fields and non-object records emit nothing; explicit null emits `null`.
- Literal keys include empty names, spaces, dots, brackets, Unicode, and `=`;
  escaped duplicate names use the last decoded key, including mixed value types.
- Test `9007199254740993`, numbers beyond U128, and `1e9999` for exact numeric
  meaning; equivalent whitespace, escaping, object order, and number spelling
  are allowed. A floating-point oracle is not sufficient for these checks.
- Reuse malformed-line recovery, diagnostics, exit status, CRLF/final-line,
  file/stdin, partial-output, bounded-memory, and pipeline-safe output tests.
- For the representative fixture, `--field skill` would emit values equivalent
  to `"Roc"`, `"café\nλ"`, and `null`, each JSON-encoded on its own line.

### Other future candidates

After usage feedback: typed scalar comparisons, opt-in raw string output, schema
summaries, and compressed-input convenience. Consider nested paths or additional
targets only with a small, independently specified scope. Preserve pipeline-safe
defaults; a general query language remains outside the project's purpose.

## 10. Open questions and release gates

The reduced v0.1 scope is approved. `--field` alone is moved to v0.2; the remaining
command syntax, string-only comparisons, validation, stream destinations, exit
codes, malformed-line handling, and non-goals are preserved. No arbitrary-value
extraction work blocks v0.1. The verified small nesting precheck supports the
unchanged depth-128 rule.

Final release gates: the entire v0.1 acceptance matrix passes on native macOS
ARM64 and Linux x86-64; large-file measurements establish bounded memory/stack
use and practical tail scaling; packaged offline binaries, license/notices,
checksums, installation instructions, and supported OS versions are verified.
Any toolchain change requires repeating JSON/API probes and all relevant tests.
The implementation plan defines how to execute these gates; this document does
not claim that application acceptance tests have already passed.
