# Learning `Cli.roc`: parsing arguments as a pure state machine

Read alongside [the source](../../src/Cli.roc). The examples describe the pinned
Roc nightly and `basic-cli` 0.25.0 used by this project. Start with
[main.roc](main.roc.md) for the program's overall flow.

## What the parser produces

`Cli.parse` converts `List(OsStr)` into either a `Command` or `Err(Usage)`.
It performs no filesystem or stream I/O. Importing the platform's native argument
type does not itself make the parser effectful.

Three associated type aliases describe the public result:

| Type | Meaning |
| --- | --- |
| `Source` | `Stdin` or `File(OsStr)`. |
| `Operation` | `Inspect`, `Count`, `Tail(U32)`, `Where({ key: Str, text: Str })`, `Help`, or `Version`. |
| `Command` | A record containing `source: Source`, `operation: Operation`, and `progress: Bool`. |

The annotation `parse : List(OsStr) -> Try(Command, [Usage])` can now be read
without repeating the full nested command shape. These aliases name existing
shapes; they do not introduce nominal wrappers around the result.

The `progress` field defaults to `False` and is an independent modifier; it does
not select an operation. Separating source and operation lets options appear
before or after the input.
Parsing describes a requested operation. Inspection, count, and tail now run
through the shared reader; filtering still returns an unfinished-operation
message when dispatched by `main!`.

## The outer declaration

```roc
Cli :: {}.{
```

This declares a nominal type named `Cli` with an empty-record representation and
an associated block of definitions. The application uses `Cli.parse`,
`Cli.help_text`, and the associated aliases such as `Cli.Command`. No `Cli`
instance needs to be constructed to call these functions.

This is the headerless module pattern used in this checkout: the filename and
main type name agree, and the public API lives in that type's associated block.
The parser's implementation helpers and private types live outside it. The same
organization appears in `Jsonl` and `Operations`.

The colon in `Command : ...` defines an alias for a type shape; `::` introduces
a nominal type. The colon in `parse : ...` annotates a value's function type.

## `Argument` and `decode_argument`: decode once, retain the original

Operating-system arguments use `OsStr`. A native filename can contain data that
cannot be decoded as a Roc `Str`. Option names, counts, and filter operands must
be valid UTF-8 for this CLI.

The private `Argument` type holds both representations:

```roc
Argument : { native : OsStr, text : Try(Str, [Usage]) }
```

`decode_argument` creates this record:

```roc
decode_argument = |native| { native, text: native.to_str_try().map_err(|_| Usage) }
```

`native` uses record shorthand for `native: native`. `to_str_try()` performs
strict conversion, and `map_err` maps a conversion error to the parser's `Usage`
tag. There is exactly one conversion site, called once for each supplied argument.

An `Err(Usage)` stored in `text` does not immediately reject the argument. It
means that it cannot be used where text is required. `File(arg.native)` can still
preserve it as a filename. No lossy replacement string is introduced.

`OsStr.from_str` constructs arguments in the tests. The implementation no longer
needs to reconstruct option tokens to normalize equals forms.

## `parse`: standalone information commands and defaults

The first step is `args.map(decode_argument)`, producing a list of `Argument`
records. All later decisions reuse each argument's stored text result.

The first guarded pattern is:

```roc
[{ text: Ok(text), .. }] if text == "--help" or text == "-h"
```

The list pattern requires exactly one record. Its record pattern requires a
successful text conversion and binds the string as `text`; `..` ignores `native`.
The guard accepts either help spelling. The next branch similarly recognizes
version. Both return `source: Stdin` for a consistent command shape, but the
application never reads stdin for them.

Other inputs start general parsing with:

```roc
parse_args(arguments, { source: Stdin, operation: Inspect, progress: False, options_ended: False, has_input: False })
```

No input means stdin; no operation flag means inspection. Combined information
commands such as `--help events.jsonl` reach the general parser and are rejected
as unknown options rather than being treated as standalone help.

## `ParseState` and `parse_args`: carry named decisions forward

`parse_args` takes a remaining argument list and a `ParseState` record. The
record makes each decision visible by name instead of passing several positional
parameters and booleans:

| Field | Meaning |
| --- | --- |
| `source` | Selected input, initially stdin. |
| `operation` | Selected operation, initially inspection. |
| `progress` | Whether `--progress` was explicitly supplied; initially false. |
| `options_ended` | Whether `--` ended option parsing. |
| `has_input` | Whether an input argument was explicitly supplied. |

`has_input` is necessary because default stdin and an explicit `-` both yield
`Stdin`, while a second input after an explicit dash must be rejected.

`[]` finishes by returning the source, operation, and progress command fields. `[arg, .. as rest]` takes
one argument and binds the remaining list. If `options_ended` is true, the
argument goes directly to `parse_input` without option interpretation.

Otherwise, the parser examines:

```roc
arg.text.map_ok(|text| text.split_on("="))
```

`map_ok` transforms only successful text. It keeps a failed conversion as an
error, so native filenames do not need invented textual substitutes. List
patterns then distinguish these cases:

| Pattern | Action |
| --- | --- |
| `Ok(["--"])` | Mark options as ended and recurse. |
| `Ok(["--count"])` | Select `Count`. |
| `Ok(["--progress"])` | Enable progress once; reject a repeated modifier. |
| `Ok(["--tail", .. as inline])` | Obtain an operand, validate a tail size, and select `Tail(size)`. |
| `Ok(["--where", .. as inline])` | Obtain an operand, validate a filter, and select `Where(filter)`. |
| Anything else | Ask `parse_input` to select a filename or reject an unknown option. |

Branches run in order. Exact list patterns matter: `--count=x` does not match
`["--count"]`, and `--=x` does not match `["--"]`.

## `--progress`: an independent modifier

`--progress` is handled before input selection: its branch enables the state's
boolean and recurses, or returns `Usage` if it is already enabled. The exact
`["--progress"]` pattern rejects a value such as `--progress=true`. Help and
version remain standalone, so combining either with progress is a usage error.

The flag is independent of `Operation`. Count and tail preserve their data-mode contracts without inspection progress.
Filtering may parse with it but still returns its unfinished-operation failure
without starting inspection. After `--`, the same token can be a literal filename.
As an operand, `--where --progress=x` is a filter request: consuming an operand
does not dispatch it as another option.

## `parse_input`: one place for filename selection

This helper rejects a second explicit input. Before `--`, it also rejects a
native argument whose first byte is 45, ASCII `-`, unless the argument is the
exact decoded string `-`. This covers both unknown flags and undecodable
option-like tokens.

After `--`, dash-leading arguments can be filenames. In either mode, the exact
`-` selects stdin; all other accepted inputs become `File(arg.native)`. Use `./-`
for a file literally named `-`.

The recursive call updates state with `{ ..state, source, has_input: True }`.
The spread retains the other fields, and `source` is shorthand for the new
`source: source` field. This is a new record value, not shared mutation.

| Arguments | Meaning |
| --- | --- |
| `-- --count` | Inspect the file named `--count`. |
| `-- -` | Inspect stdin. |
| `./-` | Inspect a file named `-`. |
| `events.jsonl --` | Keep the file; there are no more arguments. |
| `events.jsonl -- other.jsonl` | Usage error: a second input. |

## `option_operand`: share spaced and equals forms

This helper takes `inline`, the parts after the option name, and the remaining
native argument records. It returns operand text and the arguments left over.

| Token | Inline parts | Operand source |
| --- | --- | --- |
| `--tail` | `[]` | Consume the next argument's `text`. |
| `--tail=10` | `["10"]` | Join inline parts; consume no additional argument. |
| `--tail=` | `[""]` | An explicitly empty operand. |
| `--where=a=x=y` | `["a", "x", "y"]` | Rejoin to `a=x=y`. |

For a spaced operand, `arg.text?` unwraps successful text or immediately returns
its stored `Usage` error. An absent next argument is also `Usage`.

The next token belongs to the option even if it starts with a dash. Consequently,
`--where -key=-value` has a valid operand; `--tail -1` obtains an operand but
fails its numeric grammar. `--` in operand position is an operand, not an option
terminator.

Sharing this step avoids duplicated conversion and token-consumption logic.
Both syntaxes reach the same validation functions without synthesizing a new
native argument list or repeating option dispatch.

## `parse_tail_size`: validate grammar, then range

The helper requires a nonempty UTF-8 byte list containing only values 48 through
57: ASCII digits `0` through `9`. `U32.from_str` then checks numeric range, and
its error is mapped to `Usage`.

| Operand | Result |
| --- | --- |
| `0`, `10`, `00010` | Accepted; leading zeroes do not change the value. |
| `4294967295` | Accepted: maximum U32. |
| `4294967296` | Rejected: outside U32's range. |
| `+1`, `-1`, `1.0`, whitespace, empty text | Rejected by the digit rule. |
| Non-ASCII numeral characters | Rejected even if they look like digits. |

These checks serve different purposes. Keeping them together gives both spaced
and inline tail arguments the same deliberately narrow grammar.

## `parse_filter`: split at the first equals sign

The helper splits the operand, then matches:

```roc
[key, .. as parts] if !parts.is_empty()
```

There must be a first part and at least one following part, demonstrating that
an equals separator exists. It rejoins the following parts with `=` so later
equals signs remain part of the comparison text. A missing separator returns
`Usage`; there is no fallback empty key for an unreachable list case.

| Operand | Key | Text |
| --- | --- | --- |
| `status=failed` | `status` | `failed` |
| `a=x=y` | `a` | `x=y` |
| `=x` | Empty string | `x` |
| `a=` | `a` | Empty string |
| `missing` | Usage error | No separator. |

This describes literal string equality. The parser introduces no nested-query
syntax or type coercion.

## `select_operation`: enforce one operation in one place

All operation branches call this helper. It requires that `state.operation`
still be `Inspect`, the default indicating that no flag has selected an
operation. Otherwise it returns `Usage`, rejecting both repeated and conflicting
flags. On success it recurses with `{ ..state, operation }`.

Operand validation happens before this selection for tail and filter options.
Every failure still produces the same generic `Usage` result; parsing is pure,
so neither validation nor selection opens a file or reads stdin.

For `events.jsonl --tail=00010`, the steps are:

1. Decode each native argument once.
2. `parse_input` selects the file and marks `has_input` true.
3. Option dispatch recognizes `--tail` and passes `["00010"]` to `option_operand`.
4. `parse_tail_size` produces 10, and `select_operation` stores `Tail(10)`.
5. An empty remaining list returns the command record.

## `help_text` and the inline tests

The prose lives in [src/help.txt](../../src/help.txt), edited as ordinary text.
The module imports it at compile time:

```roc
import "help.txt" as usage_text : Str
```

The path is relative to `Cli.roc`, `as usage_text` names the imported value, and
`: Str` requests a string. The executable includes the contents and needs no
help file at runtime. `help_text = usage_text` exposes the constant through
`Cli.help_text`.

Edit the file and rebuild to change help. Keep the final newline: `main!` passes
the text to `write_stdout!`, which adds no newline. Executable tests independently
verify its exact bytes, so intentional wording changes require updating their
expected help. Filtering is still unfinished; count and tail are implemented, as the
[README](../../README.md) explains.

The module's 77 top-level `expect` checks cover valid forms, defaults, ordering,
conflicts, boundaries, native filenames, invalid text, and standalone help/version.
The new cases also cover progress defaults, placement, repetition, equals-form
rejection, and literal filenames/operands. They assert public behavior rather
than depending on the private helper layout.

```sh
roc test --main=src/main.roc src/Cli.roc
```

This compiler may include all modules reached through the main context, so it
can report 240 checks rather than only this module's 77.

As an exercise, trace `- events.jsonl`: the first argument marks stdin as an
explicit input, so `parse_input` rejects the second. Then compare `--tail` with
`--tail=`: one lacks a next argument, while the other supplies empty text; both
ultimately yield `Usage` through different validation steps.
