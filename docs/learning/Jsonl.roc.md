# Learning `Jsonl.roc`: turning arbitrary byte chunks into validated lines

Read alongside [the source](../../src/Jsonl.roc). This guide follows the pinned
Roc nightly used by the project. See [main.roc](main.roc.md) for I/O and
[Operations](Operations.roc.md) for what happens to each classified line.

The source places classification first. This guide starts with framing because
the program must establish a physical line before it can validate that record.

## Three separate jobs

| Job | Definitions | Result |
| --- | --- | --- |
| Framing | `State`, `Line`, `start`, `feed`, `finish`, `emit_line`, `without_final_cr` | Numbered physical lines from byte chunks. |
| Classification | `Reason`, `classify`, `is_blank`, `has_initial_bom` | A valid line or one stable defect reason. |
| JSON validation | `within_depth`, `scan_depth`, `valid_json`, `AnyJson.parser_for` | A resource precheck followed by builtin grammar validation. |

Everything in this file is pure. It accepts values and produces values; callers
supply bytes and handle output. `Jsonl :: {}.{ ... }` groups associated types and
functions under the public `Jsonl` name. [Cli's guide](Cli.roc.md#the-outer-declaration)
explains that declaration pattern.

## `State`, `Line`, and `start`

```roc
State : { pending : List(U8), next_line : U64 }
Line : { number : U64, body : List(U8) }
```

These describe record-shaped types. `pending` contains bytes after the most
recent LF that have not yet formed a complete line. `next_line` starts at 1.
An emitted `Line` carries its physical number and body bytes.

`U8` is an unsigned 8-bit integer, suitable for bytes. `U64` is an unsigned
64-bit integer, used for line numbers. These choices express different ranges
and purposes rather than relying on a default numeric type.

`start` is a value, not a function call:

```roc
start = { pending: [], next_line: 1 }
```

The state contains no input filename, JSON syntax state, or inspection totals.
Framing is independent of all three.

## `feed`: reduce a chunk one byte at a time

```roc
feed : State, List(U8), a, (a, Line -> a) -> { state : State, value : a }
```

Lowercase `a` is a type variable. It means that the framer can carry any consumer
state, provided the callback accepts that state and a line and returns the same
state type. In production, `a` is `Operations.Summary`; in framing tests it is a
list of emitted lines.

`emit` is the callback parameter. “Emit” here means call that function; it does
not mean perform I/O. The callback itself has a pure `->` function type.

`bytes.fold(initial, step)` visits bytes in order, passing the accumulated value
to the next step. Here the accumulator combines `{ state, value }`. That record
uses shorthand for `{ state: state, value: value }`.

For each byte:

1. If it is `10` (LF), build a line from the pending bytes, removing a final CR
   if present. Call `emit` with the consumer state and line. Clear `pending` and
   increment `next_line`.
2. Otherwise, append the byte to `pending` and leave the consumer state alone.

This record update appears in the second branch:

```roc
{ ..current, state: { ..current.state, pending: current.state.pending.append(byte) } }
```

`..current` retains the existing record fields, and `state:` replaces one field.
The inner update retains `next_line` while replacing `pending`. These expressions
produce updated values; they do not mutate a record visible to the caller.
The compiler may optimize storage reuse without changing that meaning.

### A trace across chunks

Suppose the transport supplies `"{}\r"`, then `"\nnull"`:

| Point | Pending bytes, shown as text | Next line | Emitted lines |
| --- | --- | --- | --- |
| Start | Empty | 1 | None |
| After the first chunk | `{}\r` | 1 | None |
| After the LF in the second chunk | Empty | 2 | Line 1, body `{}` |
| After the second chunk | `null` | 2 | No additional line yet |
| After `finish` | Empty | 3 | Line 2, body `null` |

The framer handles CRLF even when the two bytes arrive in different reads.

### `emit_line`: share the state transition

Both LF handling in `feed` and EOF handling in `finish` call `emit_line`. It
constructs a numbered line, invokes the reducer, clears pending bytes, and
increments `next_line`. Keeping that transition in one helper gives both emission
paths the same numbering and clearing rules.

The caller passes the body explicitly: `feed` removes a final CR, while `finish`
supplies the pending bytes unchanged. Sharing emission preserves their different
terminator rules. The generic callback and consumer value remain pure.

## `without_final_cr`: remove exactly the CR that belongs to CRLF

This helper is called only after finding an LF. It checks whether the body ends
with byte `13` (CR) and drops one byte if so. It first handles an empty body so
`bytes.len() - 1` is never evaluated for an empty list.

`bytes.get(index)` returns `Ok(byte)` or an out-of-bounds error. Comparing its
result with `Ok(13)` checks the last byte without an unchecked index operation.

| Physical bytes | Emitted body |
| --- | --- |
| `{}\n` | `{}` |
| `{}\r\n` | `{}` |
| `\r\r\n` | One CR remains. |
| `{}\r` followed by EOF | CR remains; `finish` does not call this helper. |

This is precise terminator handling. Trimming whitespace would change the
original record body and could hide meaningful input differences.

## `finish`: EOF is an event, not another newline

If `pending` is empty, `finish` returns the state and consumer value unchanged.
Otherwise, it emits those pending bytes as one final line, clears them, and
advances the line number. It does not strip a final CR.

This distinguishes an empty input from a blank physical line:

| Input | Lines |
| --- | --- |
| Empty bytes | Zero. |
| `\n` | One blank line. |
| `{}\n` | One line; no extra record after the final LF. |
| `{}\n\n` | Two lines, the second blank. |
| `null` | One final unterminated line. |

Calling `finish` again on its returned state emits nothing further. Use the
returned state: applying `finish` twice to the same original pending state would
describe the same original input twice.

## Why framing works on bytes

UTF-8 characters can span transport chunks. For example, the bytes `[195]` and
`[169, 10]` together contain `é` followed by LF. Decoding the first chunk alone
would incorrectly report an incomplete UTF-8 sequence.

The framer stores bytes until a physical line is complete. A subsequent strict
UTF-8 conversion can then validate the whole line. LF is byte 10 and cannot occur
inside a valid UTF-8 multibyte character.

Likewise, the two characters backslash and `n` in a JSON string do not terminate
a record. Only an actual LF byte does. Pretty-printed JSON spanning physical
lines is therefore not a valid single JSONL record.

## `Reason` and `classify`: deterministic diagnostics

```roc
Reason : [Blank, InvalidUtf8, Bom, TooDeep, InvalidJson]
```

These tags describe defects without embedding user data or display text. A
different module maps the reason to a report message.

`classify` applies the following checks in order and returns the first failure:

| Order | Check | Reason |
| --- | --- | --- |
| 1 | Every byte is JSON whitespace: space, tab, LF, or CR. | `Blank` |
| 2 | Strict `Str.from_utf8` conversion. | `InvalidUtf8` |
| 3 | First physical line starts with bytes `[239, 187, 191]`. | `Bom` |
| 4 | Unquoted nesting would exceed 128. | `TooDeep` |
| 5 | Builtin JSON grammar validation fails. | `InvalidJson` |

`is_blank` names the byte-whitespace predicate. Its `all` call returns true for
an empty list, so a zero-byte body is classified as blank.
The whitespace rule does not accept every Unicode whitespace character.

`has_initial_bom` names the first-line prefix check. It recognizes the UTF-8 byte-order mark
at the beginning of physical line 1. U+FEFF inside a quoted JSON string is valid.
The same bytes at the start of line 2, or after leading whitespace, fall through
to grammar validation and are invalid JSON there.

Order determines precedence. A first-line BOM followed by invalid UTF-8 produces
`InvalidUtf8`, because conversion fails before the BOM check. A BOM followed by
excessive nesting produces `Bom`. This keeps diagnostics stable when a line has
more than one defect.

Early returns in `classify` make that sequence visible without nesting another
match for every failure. Returning from a pure function does not make it
effectful; it still computes a classification from the supplied line.

## `within_depth`: a small scanner protecting the parser

The accumulator has `depth`, `quoted`, and `escaped` fields. `within_depth`
initializes it and passes the named callback `scan_depth` to `fold_try`. The fold
walks the UTF-8 bytes and stops as soon as the callback returns `Err(TooDeep)`.

`scan_depth` describes the transition for exactly one byte. Extracting it keeps
the fold's setup separate from its quote/escape/container rules and removes a
large nested anonymous function from `within_depth`.

Inside a quoted string:

1. If the preceding byte was an unconsumed backslash, clear `escaped` and treat
   the current byte as string content.
2. Otherwise, a backslash sets `escaped`.
3. Otherwise, a double quote ends the quoted section.
4. All remaining bytes leave the state unchanged.

Outside a string, a double quote enters the quoted state. `{` and `[` increment
depth, unless depth is already 128. `}` and `]` decrement positive depth; other
bytes leave it unchanged. ASCII byte values 34, 92, 123, 91, 125, and 93 encode
those punctuation characters.

This protects the subsequent parser from excessive recursive nesting while
ignoring brackets in string content. An array of depth 128 passes; attempting
to open level 129 fails.

It is intentionally not a JSON parser. It does not check matching bracket kinds,
valid escapes, closing depth, or completed strings. The test
`Jsonl.within_depth("[[}") == Ok({})` illustrates this separation: its depth is
acceptable, but `valid_json` rejects its grammar.

The final `.map_ok(|_| {})` discards the scanner state on success and retains
any error. The caller needs only “within the limit” or “too deep.”

## `valid_json` and `AnyJson.parser_for`: validate without decoding numbers

`Json.parse` normally produces a value of a requested target type. Here:

```roc
parsed : Try(AnyJson, _)
parsed = Json.parse(text)
```

constrains that target to `AnyJson`. The `_` leaves the error type for inference.
`parsed.is_ok()` converts the result into the boolean the classifier needs.

`AnyJson` is a nominal type with an empty-record representation. Its associated
parser tells the builtin JSON machinery how to produce that type:

```roc
parser_for = |encoding| |state| {
    rest = Json.skip_json_value(encoding, state)?
    Ok({ value: AnyJson.{}, rest })
}
```

This is a function that returns another function: `|encoding|` takes the encoding
context; `|state|` accepts the parser state when the resulting parser is called.
`Json.skip_json_value` validates and consumes one JSON value. `?` propagates its
error. The returned record contains an empty marker value and the remaining
parser state. `AnyJson.{}` constructs the nominal marker, and `rest` is shorthand
for `rest: rest`.

Skipping does not mean accepting arbitrary text without validation. The builtin
routine checks JSON syntax; `Json.parse` also checks completion, so trailing
values such as `{}null` fail.

This adapter avoids constructing an application value tree or converting numbers
into a finite numeric type. Valid numbers such as `1e9999` and integers above
U128 are accepted. Converting everything to floating point would lose precision
and reject some valid JSON numbers. The adapter cannot extract or serialize the
skipped data: its value is only a success marker.

`classify` calls the depth precheck before this function. A direct call to
`valid_json` alone does not enforce the application's depth limit. The
[feasibility report](../roc-feasibility.md) records the adapter experiments and
why arbitrary field extraction remains deferred.

## The test helpers and regression groups

`framed` feeds a list of chunks through the real `feed` and `finish`, using a list
as the consumer state. Collecting every line is useful in a small test fixture;
production instead reduces each line into a summary.

`all_cuts_match` checks the expected lines at every two-chunk split, including
empty chunks, and checks byte-at-a-time input. Its `offset: 0.U64` explicitly
types the numeric literal. `sublist` and `drop_first` construct the two chunks.
These tests demonstrate that framing is independent of transport boundaries.

The module has 97 top-level `expect` checks covering framing, EOF, CRLF, invalid
UTF-8, diagnostic precedence, depth boundaries, and positive/negative JSON
grammar. Cases include huge numbers, escaped Unicode surrogate pairs, invalid
lone surrogates, duplicate keys, and malformed-line recovery. M1 labels in comments
refer to tasks in the [implementation plan](../plans/jlog-v0.1-plan.md).

```sh
roc test --main=src/main.roc src/Jsonl.roc
```

The main context can cause all 182 project checks to run. Line-number and summary
counter overflow handling remains future work; U64 provides a large range, not
an implemented exhaustion policy. Long-line resource measurements are also pending.

As an exercise, predict the lines for chunks `"{}\r"`, `"\n\nnu"`, and `"ll"`.
After EOF there are three: `{}`, an empty body, and `null`. The classifier marks
the middle line invalid without preventing the final valid record from being read.
