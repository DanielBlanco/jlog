# What is JSONL?

JSONL (JSON Lines) stores structured data as one complete JSON value per line.
It is also commonly called newline-delimited JSON (NDJSON), with files usually
named `.jsonl` or `.ndjson`. Objects are common for logs, but arrays, strings,
numbers, booleans, and `null` are valid records too.

## Format and example

A log file named `events.jsonl` might contain:

```jsonl
{"timestamp":"2026-10-18T10:00:00Z","level":"info","message":"Started"}
{"timestamp":"2026-10-18T10:00:01Z","level":"error","message":"Connection failed","retry":1}
```

Each line stands alone. There is no enclosing array and no comma between records.
Nested objects and arrays fit inside a record, provided the entire value stays
on one physical line.

Follow the [JSON Lines format documentation](https://jsonlines.org/):

- Encode the file as UTF-8 without a byte order mark (BOM).
- Put exactly one valid JSON value on each line; blank lines are invalid.
- Separate records with a newline (`\n`); Windows line endings (`\r\n`) also work.
- End the final record with a newline when possible. It is recommended, not required.

JSON syntax still applies: use double-quoted keys and strings, and omit comments
and trailing commas. Represent a newline inside a string with the escape `\n`,
rather than a physical line break. Some readers skip blank lines, but that
tolerance does not make those lines valid records.

## JSONL compared with JSON

Ordinary JSON represents one value for the entire document. For example, the
same two messages could be stored as a JSON array:

```json
[
  {"level":"info","message":"Started"},
  {"level":"error","message":"Connection failed"}
]
```

JSONL represents a sequence of independent values. A reader parses each line
separately; parsing a multi-record file with a single `JSON.parse()` call fails.
JSONL makes incremental processing straightforward, while JSON arrays can also
be processed incrementally with a suitable streaming parser.

## When it is useful

JSONL suits application logs, event streams, data exports, and training datasets.
Readers can process records as they arrive without retaining the whole file.
Writers can append a record after ensuring the previous record ends with a
newline. A malformed record can be identified by its line number; the reader
must decide whether to stop or continue.

Use ordinary JSON for a configuration file or another document consumed as one
value. JSONL does not define required fields or a schema, so consumers still
need to validate each record's structure.

## Inspecting files

Standard shell tools can inspect records:

```sh
head -n 5 events.jsonl
tail -f events.jsonl
```

If `jq` is installed, filter objects while keeping one output record per line:

```sh
jq -c 'select(.level == "error")' events.jsonl
```

`jq` accepts a stream of JSON values; this command does not enforce JSONL's
one-value-per-line rule. Strict validation must parse each physical line separately.

## Further reading

- [JSONL.co: What is JSONL?](https://jsonl.co/guide/what-is-jsonl) — examples and common uses.
- [JSONLint: JSON Lines (JSONL) and NDJSON](https://jsonlint.com/json-lines) — reading, writing, and validation examples.
- [Dave Taubler: JSONL: The Format We Didn't Know We Needed](https://levelup.gitconnected.com/jsonl-the-format-we-didnt-know-we-needed-405e3ed407ab) — additional perspective; the full article requires Medium membership.
