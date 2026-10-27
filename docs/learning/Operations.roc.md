# Learning `Operations.roc`: summaries, bounded diagnostics, and report text

Read alongside [the source](../../src/Operations.roc). See
[Jsonl](Jsonl.roc.md) for the numbered lines this module consumes and
[main.roc](main.roc.md) for the code that writes its result.

The current implementation contains shared validation summaries, inspection and
count rendering, bounded tail retention, streaming filter selection, data
diagnostics, and progress/error policies. The guide describes the pinned Roc
version used by this checkout.

## The module boundary

The only imported project module is `Jsonl`. The `Operations :: {}.{ ... }`
associated block contains public summary types, constants, and functions.
Private rendering, detail-retention, byte-escaping, and test helpers appear outside it.

This module never opens a file, reads a stream, or writes text. `report` returns
a `Str`; the caller decides where to send it. That keeps the report format and
aggregation behavior testable through exact value comparisons.

## `Summary` and `start`: what inspection needs to remember

The source defines this record shape:

```roc
ErrorDetail : { number : U64, reason : Jsonl.Reason }
Summary : { records : U64, valid : U64, invalid : U64, errors : List(ErrorDetail) }
```

| Field | Meaning |
| --- | --- |
| `records` | Number of framed physical lines consumed. |
| `valid` | Lines classified as valid JSONL records. |
| `invalid` | Lines classified as malformed. |
| `errors` | First 100 malformed physical line numbers and reasons. |

`start` is the initial value with three zero counters and an empty detail list.
There is no filename or raw record body in the summary.

For summaries produced by the reducer, `records == valid + invalid` and
`errors.len() <= 100`. The record type itself does not prove those arithmetic
relationships: they follow from how `start` and `inspect_line` construct values.
`report` relies on that construction rather than revalidating the summary.

`U64` gives counters an explicit large nonnegative range. The production
`consume_checked` wrapper detects exhausted counters before incrementing; seeded
near-limit tests verify the boundary without trying to exhaust the machine.

## `inspect_line`: a reducer passed as a function value

```roc
inspect_line : Summary, Jsonl.Line -> Summary
```

The function receives the previous summary and one physical line, calls
`Jsonl.classify`, and returns the next summary. The `->` type is pure.

`inspect_line` delegates classification and counting to the private
`record_classification` helper. The production stream consumer shares that helper
and classifies only once. After classification, the helper increments `records`
once in a record named `counted`. Both outcomes build on it, so the common
increment has one definition. For `Valid`, it then increments `valid`:

```roc
counted = { ..summary, records: summary.records + 1 }
{ ..counted, valid: counted.valid + 1 }
```

retains the remaining fields and replaces the named ones. It describes a new
value rather than a mutation visible to another caller.

For `Invalid(reason)`, it increments `invalid` and passes an `ErrorDetail` to
`retain_error`. This helper appends the detail only if fewer than 100 have been
retained; otherwise it returns the existing list. Naming the detail's type avoids
repeating its record shape in function signatures. The `reason` field in
`{ number: line.number, reason }` uses record shorthand.

The line's own physical number is preserved. An input line numbered 42 produces
an error detail at 42 even if the supplied summary starts at zero. The reducer
does not infer line numbers from its own record count.

### Trace a mixed input

For `{}\n\nnot-json\nnull`, the framer supplies these steps:

| Line | Classification | Records | Valid | Invalid | Retained details |
| --- | --- | --- | --- | --- | --- |
| Before input | — | 0 | 0 | 0 | None |
| 1: `{}` | `Valid` | 1 | 1 | 0 | None |
| 2: empty body | `Invalid(Blank)` | 2 | 1 | 1 | Line 2, `Blank` |
| 3: `not-json` | `Invalid(InvalidJson)` | 3 | 1 | 2 | Lines 2 and 3 |
| 4: `null` | `Valid` | 4 | 2 | 2 | Same details |

An invalid line is data to aggregate, not an error that stops the reducer. That
is why later valid lines still contribute to the report.

### Why retain only 100 details?

With millions of malformed lines, an uncapped detail list would grow with the
input. The reducer retains the first 100 locations in encounter order while
continuing to count every line.

It stores only a number and a reason for each detail. Large or sensitive record
bodies do not become part of the report. The total reader's memory still depends
on line length; the cap bounds diagnostic storage, not all application memory.

## `report`, `report_header`, and `render_error`: construct the inspection string

```roc
report : Str, Summary -> Str
```

The first argument is a display label such as a filename or `<stdin>`. The
function escapes it, delegates the four-line header to `report_header`, and
returns early with that header if `invalid == 0`.

`report_header` accepts an already escaped label. Its list places each output
line on a separate source line, then `Str.join_with` joins them with LF. A final
empty element supplies the trailing LF. This keeps the report layout readable
without changing its bytes.

Within the header helper, interpolation inserts expressions with `${...}`. For example,
`${summary.records.to_str()}` converts the counter to decimal text and inserts
it. `\n` in the source string creates an actual LF in the report.

For invalid input, `summary.errors.fold` starts with the header and a blank line
plus `Malformed records:`. For each detail, its callback appends the string from
`render_error`. That helper formats the physical line number, calls
`Operations.reason_text`, and adds the trailing LF. The accumulator is the report
text built so far, and the fold preserves error order.

Then `omitted = summary.invalid - summary.errors.len()` counts malformed lines
whose details were not retained. A positive value appends the omission message.
It is computed from all invalid records, not all physical records.

For 101 blank lines followed by one valid line, there are 102 records, 101 invalid
records, 100 stored details, and one omitted invalid detail.

For the four-line example above, `report("mixed.jsonl", summary)` produces:

```text
File: mixed.jsonl
Records: 4
Valid: 2
Invalid: 2

Malformed records:
  line 2: blank line
  line 3: invalid JSON
```

Every path through `report` produces a final LF. Labels, spacing, ordering, and
decimal formatting are part of the output contract, verified by exact tests.
The caller emits this report only after successful EOF. The renderer itself
cannot tell whether reading has completed.

## `reason_text`: separate classification from presentation

The function matches a `Jsonl.Reason` and returns its stable display message:

| Reason | Message |
| --- | --- |
| `Blank` | `blank line` |
| `InvalidUtf8` | `invalid UTF-8` |
| `Bom` | `BOM is not allowed` |
| `TooDeep` | `nesting exceeds 128` |
| `InvalidJson` | `invalid JSON` |

This keeps JSON byte/grammar rules in `Jsonl` and report language in
`Operations`. The reason tags do not carry or reproduce the malformed record.

## `count_report` and `data_diagnostics`: data-mode completion

`count_report(summary)` formats the shared valid total as one ungrouped decimal
integer plus LF. Invalid records contribute zero; an empty input produces `0`
plus LF. It does not inspect input or decide whether EOF occurred. The effectful
driver calls it only after a successful completion transition, verified by a
held-open stdin test. A framing test also confirms that an unterminated last
record joins the total only when `Jsonl.finish` emits it.

`data_diagnostics(source, summary)` formats retained errors as
`jlog: SOURCE: line N: REASON`, with one LF per detail. It escapes the source label
once, preserves physical ordering, and appends `jlog: SOURCE: K more invalid
records` when details were omitted. Empty/valid summaries produce an empty string.
Inspection's errors remain inside its stdout report; count, tail, and filtering
write this diagnostic string to stderr and reserve stdout for data.

## `Tail`, `tail_start`, `tail_push`, and `tail_lines`: a growing ring

`Tail` has three fields: `limit`, the widened U64 version of CLI N; `next`, the
slot that will be replaced when full; and `bodies`, a list of original byte lists.
`tail_start` initializes an empty list even for N=4294967295. It allocates no N-slot
buffer in advance.

`tail_push` accepts an already-valid body. For N=0 it retains nothing. Before
the list reaches N, it appends. Once full, indexed `List.set` replaces the oldest
slot and the index advances, wrapping to zero at N. It does not shift the whole
list on every insertion. The checked set result also makes an impossible index
violation explicit as an internal crash rather than silently losing a record.

For N=2, receiving 1 and 2 stores `[1, 2]`, next=0. Receiving 3 stores `[3, 2]`,
next=1: the physical storage order differs from input order. `tail_lines` restores
input order once at EOF by joining the suffix starting at `next` with the prefix
before it. This produces `[2, 3]`. Record bodies are not decoded/re-encoded for
output, so numeric spellings, duplicate keys, whitespace, and Unicode survive.

Roc values remain semantically immutable. A test retaining an older tail snapshot
still observes its old contents after a push. Production keeps only the current
state so storage can be reused; the ring API and an insertion smoke probe were
checked on the pinned compiler. These checks are not full resource benchmarks.

## Shared streaming state and checked consumption

`StreamState` contains `summary: Summary`, `tail: Tail`, and
`matches: List(List(U8))`. `stream_start(limit)` starts counters and tail with an
empty match buffer. Inspection, count, and filtering use a zero tail limit; tail
uses its N. All modes share validation totals and capped malformed-line details.

`consume_line(state, line)` classifies once and delegates to `record_validated`.
That helper calls `record_classification`, pushes a body into the tail only for
`Valid`, and preserves the match buffer. Even N=0 classifies every physical line.
The older `inspect_line` helper lets small pure summary tests use the same
classification/counting logic without carrying tail storage.

The actual application selects `consume_checked` or `filter_checked`. Their
accumulator is `StreamResult`, an alias for `Try(StreamState, StreamFailure)`.
`StreamFailure` distinguishes `ResourceFailure` from `LookupFailure(U64)`, whose
payload is the physical line number.

Both consumers call private `checked_line`. It propagates earlier failures,
checks all counters against `U64.highest`, classifies once, then returns
`{ state, valid }` using `record_validated`. `consume_checked` keeps only the
updated state; filtering also needs the validity decision. This avoids repeating
validation or counter rules in the two consumers. Exhaustion contains no deferred
state, so it cannot become a partial successful count or tail. The low-level
reducers assume counters fit; production always uses checked consumption.

## `filter_checked` and `drain_matches`: selection with bounded retention

`filter_checked(current, line, filter)` first calls `checked_line`. Invalid lines
update diagnostics and return without lookup. Valid lines use
`Jsonl.matches_valid(body, key, text)`; a nonmatch returns the counted state, while
a match appends the original byte body to `state.matches`. A decoder disagreement
becomes `LookupFailure(line.number)`, which the driver treats as internal exit 1.
Neither an invalid line nor a legitimate nonmatch is a fatal lookup failure.

Framing callbacks are pure, so they cannot write each match directly.
`drain_matches(state)` returns `{ bodies, state }`: it hands the buffered bodies
to the effectful writer and returns the next state with an empty buffer. The
reader calls it after each read and before reading again. This bounds retention
to the current read plus a potentially large line spanning earlier reads. It
does not accumulate all matches. Tail and other modes leave this buffer empty.

For example, a read containing a match, `bad`, and another match records three
physical lines, one invalid detail, and two original bodies. The driver writes
the two bodies plus LF, then stores the drained state. The next read starts with
the same totals but no previously emitted bodies. A final unterminated match is
selected by `Jsonl.finish` and written during EOF completion.

## `exit_code` and `complete_stream`: completion and failure policy

`Failure` names usage, I/O, resource, and internal failures.
`exit_code` maps completed validation to 0 or 4, usage to 2, I/O to 3, and the
other fatal categories to 1. The effectful boundary wraps the result in `Exit`.

`complete_stream(state, event)` distinguishes `Eof` from `ReadError(reason)`.
EOF returns the completed state. A reported read failure returns only the error,
discarding the deferred summary, tail, and any pending matches. Both terminal
paths use this pure decision through `finish_input!`; that caller writes final
results only on success. Earlier filter bodies were handed off by draining and
may already have been written; an input error cannot retract that prefix.

Tests seed a prefix containing valid/invalid records and retained bodies, then
assert that failure cannot yield completed output or malformed-input status 4.
Real directory-stdin failures and closed-pipe writes are checked separately. A
pseudo-terminal closure was observed as EOF on this platform in both inspection
and filtering. M4-01 later establishes an actual executable prefix read failure
using a nonblocking pipe kept open by its writer. Deferred results are empty;
filtering preserves its already-emitted valid prefix and returns status 3.
Pure tests separately verify that draining keeps this prefix outside discarded
state and that I/O status 3 overrides malformed status 4.

## `Progress`, `progress_start`, `progress_due`, and `progress_text`

Inspection progress uses the existing summary counters, so it does not store
input records or a second set of validation totals. Its scheduling state is:

```roc
Progress : { last_update_ns : U64, records : U64 }
```

`last_update_ns` is a monotonic timestamp from the most recent periodic snapshot,
or from startup before the first snapshot. `records` is the number of lines shown
in that snapshot, initially zero. The pure `progress_start(now_ns)` constructs
this initial state from a timestamp supplied by the effectful caller.

`progress_due(previous, now_ns, summary)` requires both an advanced record count
and at least 1,000,000,000 elapsed nanoseconds: one second. It first rejects a
backwards timestamp so unsigned subtraction cannot underflow. It therefore avoids
repeating unchanged counts or printing on every physical line. Deterministic
tests can supply timestamps directly, including the exact interval boundary.

`progress_text(summary, complete)` returns a plain message such as
`jlog: 42 lines inspected, 2 invalid`. A true completion argument adds
` (complete)`. The renderer does not add a newline, read a clock, or decide
whether input actually reached EOF: `main.roc` owns those effects and decisions.

Only periodic snapshots use the rate limiter. The final EOF snapshot is always
emitted when requested, including for zero records or a short run. A read error
must never call the completion path. See [main.roc](main.roc.md#optional-progress-in-the-read-loop)
for the effectful coordination.

## `escape_source`: labels must remain readable on one line

Filenames can contain newlines, tabs, and other controls. Inserting them directly
could turn one source label into several apparent report lines.

`escape_source` converts the valid Roc string to UTF-8 bytes, calls `escape_bytes`
with an empty output list, and converts the resulting bytes back to a string.

That final conversion is still checked. Its `Err` branch uses `crash`, because
invalid UTF-8 would mean the escaping implementation broke an internal invariant.
Input record validation uses recoverable reasons instead: malformed user data is
expected there. This crash branch is not a general technique for input errors.

The escaping preserves ordinary Unicode and literal backslashes. It is a report
display convention, not a JSON string encoder, shell quoting routine, or reversible
native-path encoding. The original native path is opened in `main.roc` before
its display label is escaped.

## `escape_bytes`: recursive list matching

The helper carries `remaining` input bytes and an output accumulator `out`:

```roc
escape_bytes = |remaining, out| match remaining {
```

`[]` ends recursion by returning `out`. Otherwise the function consumes input
bytes, appends their escaped representation, and calls itself with the rest.

The first nonempty pattern is special:

```roc
[194, byte, .. as rest] if byte >= 128 and byte <= 159
```

In valid UTF-8, `194` is hexadecimal `C2`; together with a continuation byte from
`80` to `9F`, it encodes a C1 control character U+0080 through U+009F. Matching this
case before the one-byte case lets the function escape the character as a whole.

The general `[byte, .. as rest]` branch then handles:

| Input | Output characters |
| --- | --- |
| LF, CR, tab, backspace, form feed | `\n`, `\r`, `\t`, `\b`, `\f` respectively. |
| Other C0 controls, values below 32 | A six-character `\u00xx` escape. |
| DEL, value 127 | `\u007f`. |
| Other bytes | The original byte. |

The displayed escapes are literal characters. In Roc source, `"\\n"` creates
backslash plus `n`, whereas `"\n"` creates one newline character. Ordinary UTF-8
sequences pass through unchanged, which keeps labels such as `café` readable.

## `control_escape` and `hex_digit`: build ASCII escapes

`control_escape(byte)` returns six bytes:

```roc
[92, 117, 48, 48, hex_digit(U8.shr_wrap(byte, 4)), hex_digit(U8.bitwise_and(byte, 15))]
```

The first four are backslash, `u`, `0`, and `0`. Shifting right by four extracts
the high hexadecimal digit; bitwise AND with 15 extracts the low digit. Each is
a nibble, a value from 0 through 15.

`hex_digit` maps 0..9 to ASCII `0`..`9` by adding 48, and 10..15 to lowercase
`a`..`f` by adding 87. For byte 31, hexadecimal `1f`, the result is the six bytes
for `\u001f`.

These byte operations are narrowly scoped to control-character rendering. They
do not implement general Unicode processing or a JSON codec.

## `summarize` and the inline tests

The private `summarize(bytes)` helper runs the real framer with
`Operations.inspect_line` as its callback, then calls `finish`. It returns the
final `.value`, which is the summary. It gives tests a concise way to exercise
the production pipeline without reading a file or duplicating classification.

The module has 69 top-level `expect` checks for initial/valid/mixed summaries,
physical numbering, first-100 limits, omission counts, exact reports, large
decimal counters, control escaping, Unicode preservation, and absence of raw
record text from diagnostics.

Ten of those checks cover progress initialization, interval boundaries, unchanged
counts, backwards timestamps, and exact progress rendering without using a real
clock. The Python suite separately tests real progress before EOF.

The M2 additions cover count/data formatting, tail boundaries and ring wraparound,
near-limit counters, EOF versus prefix read failure, and explicit exit categories.
M3 checks add shared validation/selection, draining, sticky failures, exhausted
counters, and read failure after an emitted prefix. The obsolete unfinished-
operation category was removed now that every v0.1 operation is implemented.
These pure checks complement the executable permission, EOF-gating, and broken
pipe tests rather than simulating operating-system faults with ordinary EOF.

```sh
roc test --main=src/main.roc src/Operations.roc
```

The compiler can include the entire application's 273 checks through the main
context. Exact rendering tests complement the executable tests: one checks the
returned string, and the other checks which stream receives it and the status.

As an exercise, follow 103 blank lines through the reducer. All counters still
advance, only details for lines 1 through 100 are stored, and the report says
`... 3 more invalid records`. Then consider a filename containing an actual tab:
its report label contains the two visible characters backslash and `t`.
